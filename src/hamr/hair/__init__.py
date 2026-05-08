"""
Hair Forge — Procedural and library-based hair generation.

Hair is the crown of the avatar. The Hair Forge takes a HairSpec
and produces the configuration that the Blender build script applies:
material assignments, texture tinting targets, and spring bone physics.

Phase 7:  Complete. The forge breathes.
Phase 11: Hair mesh generation added (mesh.py) — guide curves → Bezier → mesh pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

from hamr.core.models import HairSpec, HairColorSpec, HairStyle, HairLength, HairPhysicsSpec
from hamr.core.textures import generate_hair_texture

logger = logging.getLogger("hamr.hair")


# ── Hair Style Templates ─────────────────────────────────────────────────────
# Each style defines metadata for the Blender build script:
#   - shell_count: how many mesh shell layers for volume
#   - length_factor: multiplier on default hair length
#   - curl_map: shape key overrides for curl tightness
#   - requires_mesh: whether this style uses a separate hair mesh

HAIR_STYLE_TEMPLATES: dict[str, dict] = {
    "wild-curly": {
        "shell_count": 8,
        "length_factor": 1.2,
        "default_curl": 0.75,
        "requires_mesh": True,
        "keywords": ["curly", "wild", "voluminous"],
    },
    "straight": {
        "shell_count": 4,
        "length_factor": 1.0,
        "default_curl": 0.0,
        "requires_mesh": False,
        "keywords": ["straight", "sleek", "flat"],
    },
    "wavy": {
        "shell_count": 6,
        "length_factor": 1.1,
        "default_curl": 0.4,
        "requires_mesh": True,
        "keywords": ["wavy", "beach", "flowing"],
    },
    "braided": {
        "shell_count": 3,
        "length_factor": 0.8,
        "default_curl": 0.0,
        "requires_mesh": True,
        "keywords": ["braid", "plait", "woven"],
    },
    "bun": {
        "shell_count": 2,
        "length_factor": 0.5,
        "default_curl": 0.0,
        "requires_mesh": True,
        "keywords": ["bun", "updo", "formal"],
    },
    "ponytail": {
        "shell_count": 4,
        "length_factor": 1.0,
        "default_curl": 0.1,
        "requires_mesh": True,
        "keywords": ["ponytail", "sporty", "swept"],
    },
}


# ── Hair Length Presets ────────────────────────────────────────────────────────

HAIR_LENGTH_TABLE: dict[str, float] = {
    "short": 0.15,        # Above ears
    "medium": 0.35,      # Jaw-length
    "shoulder": 0.55,    # Shoulder-length
    "shoulder-plus": 0.70,  # Below shoulders
    "long": 0.85,        # Mid-back
    "very-long": 1.0,   # Waist+ length
}


# ── Hair Color Gradient Presets ────────────────────────────────────────────────

HAIR_GRADIENT_PRESETS: dict[str, dict[str, str]] = {
    "platinum_blonde": {"roots": "#D4C098", "mid": "#E8D8B8", "tips": "#F5EFE0"},
    "honey_blonde": {"roots": "#C4A265", "mid": "#D4B87A", "tips": "#F5E6B8"},
    "strawberry_blonde": {"roots": "#B86840", "mid": "#D48E60", "tips": "#F0C0A0"},
    "chestnut": {"roots": "#5C3A1E", "mid": "#7A4E28", "tips": "#A06830"},
    "auburn": {"roots": "#6B2E1A", "mid": "#8B4028", "tips": "#B05838"},
    "raven": {"roots": "#1A1A2E", "mid": "#252540", "tips": "#3A3A55"},
    "silver": {"roots": "#8A8A9A", "mid": "#B0B0C0", "tips": "#D8D8E8"},
    "ice_blue": {"roots": "#4060A0", "mid": "#6080C0", "tips": "#90B0E8"},
    "emerald": {"roots": "#1A5040", "mid": "#2A6858", "tips": "#40A080"},
    "fire_red": {"roots": "#8B1A1A", "mid": "#C03030", "tips": "#E85858"},
}


@dataclass
class HairBuildResult:
    """Result from the Hair Forge — everything the Blender script needs."""

    style_template: dict
    length_factor: float
    normalized_length: float
    shell_count_override: int | None
    color_roots_hsv: tuple[float, float, float]
    color_tips_hsv: tuple[float, float, float]
    gradient_preset: str | None
    curl_tightness: float
    volume: float
    physics_config: dict
    material_targets: list[str]  # Material names to tint

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert HSV tuples to lists for JSON serialization
        d["color_roots_hsv"] = list(self.color_roots_hsv)
        d["color_tips_hsv"] = list(self.color_tips_hsv)
        return d


def resolve_hair(spec: HairSpec) -> HairBuildResult:
    """
    Resolve a HairSpec into a HairBuildResult that the Blender script can apply.

    This is the main entry point for the Hair Forge.
    """
    from hamr.core.textures import hex_to_hsv

    # Resolve style
    style_name = spec.style if spec.style in HAIR_STYLE_TEMPLATES else "wavy"
    template = HAIR_STYLE_TEMPLATES[style_name]

    # Resolve length
    length_key = spec.length if spec.length in HAIR_LENGTH_TABLE else "shoulder-plus"
    normalized_length = HAIR_LENGTH_TABLE[length_key]
    length_factor = normalized_length * template.get("length_factor", 1.0)

    # Resolve curl
    curl = spec.curl_tightness if spec.curl_tightness is not None else template.get("default_curl", 0.0)

    # Resolve color
    color = spec.color
    roots_hsv = hex_to_hsv(color.roots)
    tips_hsv = hex_to_hsv(color.tips)

    # Check if the color matches a known preset
    gradient_preset = _match_gradient_preset(color)

    # Physics
    physics = {
        "stiffness": spec.volume * 0.3 + 0.2,
        "gravity": 0.3,
        "drag": 0.4,
        "collider_radius": 0.02,
    }
    if hasattr(spec, "physics") and spec.physics is not None:
        if hasattr(spec.physics, "stiffness"):
            physics["stiffness"] = spec.physics.stiffness
            physics["gravity"] = spec.physics.gravity
            physics["drag"] = spec.physics.drag

    # Shell count override
    shell_override = spec.shell_layers if spec.shell_layers != template.get("shell_count", 6) else None

    # Material targets (will be matched at Blender level)
    material_targets = ["hair"]  # Generic target, Blender script classifies

    return HairBuildResult(
        style_template=template,
        length_factor=length_factor,
        normalized_length=normalized_length,
        shell_count_override=shell_override,
        color_roots_hsv=roots_hsv,
        color_tips_hsv=tips_hsv,
        gradient_preset=gradient_preset,
        curl_tightness=curl,
        volume=spec.volume,
        physics_config=physics,
        material_targets=material_targets,
    )


def _match_gradient_preset(color: HairColorSpec) -> str | None:
    """Check if a HairColorSpec closely matches a known gradient preset."""
    from hamr.core.textures import hex_to_hsv

    best_match = None
    best_distance = float("inf")

    for preset_name, preset_colors in HAIR_GRADIENT_PRESETS.items():
        roots_hsv = hex_to_hsv(color.roots)
        preset_hsv = hex_to_hsv(preset_colors["roots"])
        distance = sum((a - b) ** 2 for a, b in zip(roots_hsv, preset_hsv))

        if distance < best_distance:
            best_distance = distance
            best_match = preset_name

    # Only return preset if it's close enough (within ~10% color distance)
    if best_distance < 0.05:
        return best_match
    return None


def list_hair_presets() -> dict[str, dict]:
    """List all available hair style presets with their metadata."""
    return {
        name: {
            "shell_count": tmpl["shell_count"],
            "length_factor": tmpl["length_factor"],
            "default_curl": tmpl["default_curl"],
            "keywords": tmpl["keywords"],
        }
        for name, tmpl in HAIR_STYLE_TEMPLATES.items()
    }


def list_gradient_presets() -> dict[str, dict[str, str]]:
    """List all available hair color gradient presets."""
    return dict(HAIR_GRADIENT_PRESETS)


# ── Phase 11: Hair mesh generation re-exports ────────────────────────────────
# Import pure-Python geometry functions and Blender-dependent classes from
# the mesh sub-module.  This keeps the config layer (above) intact while
# exposing the mesh layer to consumers.

from hamr.hair.mesh import (  # noqa: E402
    HAIR_MESH_STYLES,
    HAIR_LENGTH_SCALE,
    GuideCurve,
    HairMeshResult,
    BLENDER_AVAILABLE,
    generate_guide_curves,
    compute_strand_count,
    interpolate_curve_points,
    apply_wave_to_curve,
    HairMeshGenerator,
    create_hair_material,
)

__all__ = [
    # Config layer (Phase 7)
    "HAIR_STYLE_TEMPLATES",
    "HAIR_LENGTH_TABLE",
    "HAIR_GRADIENT_PRESETS",
    "HairBuildResult",
    "resolve_hair",
    "list_hair_presets",
    "list_gradient_presets",
    # Mesh layer (Phase 11)
    "HAIR_MESH_STYLES",
    "HAIR_LENGTH_SCALE",
    "GuideCurve",
    "HairMeshResult",
    "BLENDER_AVAILABLE",
    "generate_guide_curves",
    "compute_strand_count",
    "interpolate_curve_points",
    "apply_wave_to_curve",
    "HairMeshGenerator",
    "create_hair_material",
]