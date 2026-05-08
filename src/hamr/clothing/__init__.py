"""
Clothing Forge — Parametric clothing and outfit layer system.

The Clothing Forge takes ClothingSpec definitions and produces
material assignments, mesh layer configurations, and tinting
targets that the Blender build script applies.

Phase 7:  Complete. The forge breathes.
Phase 11: Clothing mesh generation added (mesh.py) — pattern resolve →
           region select → duplicate → offset → shrinkwrap → material → weight transfer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

from hamr.core.models import ClothingSpec

logger = logging.getLogger("hamr.clothing")


# ── Clothing Type Templates ───────────────────────────────────────────────────

CLOTH_TYPE_TEMPLATES: dict[str, dict] = {
    "full-outfit": {
        "layers": ["torso", "legs", "feet", "hands"],
        "mesh_pattern": "Outfit",
        "priority": 1,  # Applied first
    },
    "top": {
        "layers": ["torso", "arms"],
        "mesh_pattern": "Top|Shirt|Jacket",
        "priority": 2,
    },
    "bottom": {
        "layers": ["legs"],
        "mesh_pattern": "Bottom|Pants|Skirt",
        "priority": 3,
    },
    "dress": {
        "layers": ["torso", "legs"],
        "mesh_pattern": "Dress",
        "priority": 2,
    },
    "outerwear": {
        "layers": ["torso", "arms"],
        "mesh_pattern": "Jacket|Coat|Cloak",
        "priority": 4,
    },
    "accessories": {
        "layers": [],
        "mesh_pattern": "Accessory|Belt|Scarf|Hat",
        "priority": 5,
    },
    "footwear": {
        "layers": ["feet"],
        "mesh_pattern": "Shoe|Boot|Sandal",
        "priority": 3,
    },
    "jewelry": {
        "layers": [],
        "mesh_pattern": "Ring|Necklace|Earring|Bracelet",
        "priority": 6,
    },
}

# ── Material Categories ────────────────────────────────────────────────────────

MATERIAL_CATEGORIES: dict[str, dict] = {
    "fabric": {
        "roughness": 0.7,
        "metallic": 0.0,
        "subsurface": 0.0,
    },
    "leather": {
        "roughness": 0.5,
        "metallic": 0.0,
        "subsurface": 0.0,
    },
    "metal": {
        "roughness": 0.3,
        "metallic": 0.8,
        "subsurface": 0.0,
    },
    "silk": {
        "roughness": 0.4,
        "metallic": 0.1,
        "subsurface": 0.1,
    },
    "denim": {
        "roughness": 0.8,
        "metallic": 0.0,
        "subsurface": 0.0,
    },
    "fur": {
        "roughness": 0.9,
        "metallic": 0.0,
        "subsurface": 0.05,
    },
}


@dataclass
class ClothingBuildResult:
    """Result from the Clothing Forge — everything the Blender script needs."""

    name: str
    cloth_type: str
    template: dict
    primary_hsv: tuple[float, float, float]
    accent_hsv: tuple[float, float, float]
    trim_hsv: tuple[float, float, float]
    material_category: str
    material_properties: dict
    layer_order: int
    mesh_pattern: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["primary_hsv"] = list(self.primary_hsv)
        d["accent_hsv"] = list(self.accent_hsv)
        d["trim_hsv"] = list(self.trim_hsv)
        return d


def resolve_clothing(spec: ClothingSpec) -> ClothingBuildResult:
    """
    Resolve a ClothingSpec into a ClothingBuildResult for the Blender script.

    This is the main entry point for the Clothing Forge.
    """
    from hamr.core.textures import hex_to_hsv

    # Resolve type template
    cloth_type = spec.type if spec.type in CLOTH_TYPE_TEMPLATES else "full-outfit"
    template = CLOTH_TYPE_TEMPLATES[cloth_type]

    # Resolve colors
    primary_hsv = hex_to_hsv(spec.primary_hex)
    accent_hsv = hex_to_hsv(spec.accent_hex)
    trim_hsv = hex_to_hsv(spec.trim_hex)

    # Determine material category based on color values and type
    mat_category = _infer_material_category(spec, cloth_type)
    material_props = MATERIAL_CATEGORIES.get(mat_category, MATERIAL_CATEGORIES["fabric"])

    return ClothingBuildResult(
        name=spec.name,
        cloth_type=cloth_type,
        template=template,
        primary_hsv=primary_hsv,
        accent_hsv=accent_hsv,
        trim_hsv=trim_hsv,
        material_category=mat_category,
        material_properties=material_props,
        layer_order=template["priority"],
        mesh_pattern=template["mesh_pattern"],
    )


def _infer_material_category(spec: ClothingSpec, cloth_type: str) -> str:
    """Infer the material category from the clothing type and name."""
    name_lower = spec.name.lower()

    # Name-based inference
    if any(kw in name_lower for kw in ("metal", "chain", "plate", "armor")):
        return "metal"
    if any(kw in name_lower for kw in ("silk", "satin", "velvet")):
        return "silk"
    if any(kw in name_lower for kw in ("leather", "hide")):
        return "leather"
    if any(kw in name_lower for kw in ("fur", "fleece", "wool", "cloak")):
        return "fur"
    if any(kw in name_lower for kw in ("denim", "jean")):
        return "denim"

    # Type-based defaults
    type_defaults = {
        "jewelry": "metal",
        "footwear": "leather",
        "outerwear": "fabric",
        "accessories": "fabric",
    }
    return type_defaults.get(cloth_type, "fabric")


def list_clothing_types() -> dict[str, dict]:
    """List all available clothing type templates."""
    return {
        name: {
            "layers": tmpl["layers"],
            "priority": tmpl["priority"],
        }
        for name, tmpl in CLOTH_TYPE_TEMPLATES.items()
    }


def list_material_categories() -> dict[str, dict]:
    """List all available material categories with their properties."""
    return dict(MATERIAL_CATEGORIES)


# ── Phase 11: Clothing mesh generation re-exports ──────────────────────────────
# Import pure-Python pattern functions and Blender-dependent classes from
# the mesh sub-module.  This keeps the config layer (above) intact while
# exposing the mesh layer to consumers.

from hamr.clothing.mesh import (  # noqa: E402
    CLOTHING_PATTERNS,
    BODY_REGION_VERTEX_GROUPS,
    UV_REGION_MAP,
    _REQUIRED_PATTERN_KEYS,
    ClothingMeshResult,
    ClothingMeshGenerator,
    ClothingForge,
    BLENDER_AVAILABLE,
    resolve_clothing_pattern,
    compute_clothing_regions,
    estimate_triangle_count,
    classify_material_type,
)

__all__ = [
    # Config layer (Phase 7)
    "CLOTH_TYPE_TEMPLATES",
    "MATERIAL_CATEGORIES",
    "ClothingBuildResult",
    "resolve_clothing",
    "list_clothing_types",
    "list_material_categories",
    # Mesh layer (Phase 11)
    "CLOTHING_PATTERNS",
    "BODY_REGION_VERTEX_GROUPS",
    "UV_REGION_MAP",
    "ClothingMeshResult",
    "ClothingMeshGenerator",
    "ClothingForge",
    "BLENDER_AVAILABLE",
    "resolve_clothing_pattern",
    "compute_clothing_regions",
    "estimate_triangle_count",
    "classify_material_type",
]