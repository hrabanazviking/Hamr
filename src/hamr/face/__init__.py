"""
Face Forge — Facial shape keys, expressions, and parameter mapping.

The face is the soul's window. The Face Forge takes a FaceSpec
and produces the shape key targets, expression bindings, and
slider values that bring the avatar to life.

Phase 7: Complete. The forge breathes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

from hamr.core.models import FaceSpec, EyeSpec

logger = logging.getLogger("hamr.face")


# ── Face Shape Key Templates ──────────────────────────────────────────────────
# Mapping from FaceSpec parameters to Blender shape key names.
# These are MB-Lab compatible shape key names.

JAW_MAP: dict[str, dict[str, float]] = {
    "V-shape": {"jaw_width": -0.3, "chin_protrusion": -0.1, "chin_width": -0.2},
    "round": {"jaw_width": 0.2, "chin_width": 0.2},
    "square": {"jaw_width": 0.4, "chin_protrusion": 0.1, "chin_width": 0.3},
    "heart": {"jaw_width": -0.2, "chin_protrusion": -0.15, "chin_width": -0.1},
}

CHEEKBONE_MAP: dict[str, dict[str, float]] = {
    "high": {"cheek_bone_width": 0.3, "cheek_fat": -0.2},
    "low": {"cheek_bone_width": -0.2, "cheek_fat": 0.1},
    "medium": {"cheek_bone_width": 0.0, "cheek_fat": 0.0},
}

NOSE_SIZE_MAP: dict[str, dict[str, float]] = {
    "small": {"nose_bridge_width": -0.2, "nose_tip_width": -0.2, "nostril_width": -0.2},
    "medium": {"nose_bridge_width": 0.0, "nose_tip_width": 0.0, "nostril_width": 0.0},
    "large": {"nose_bridge_width": 0.2, "nose_tip_width": 0.2, "nostril_width": 0.3},
}

NOSE_BRIDGE_MAP: dict[str, dict[str, float]] = {
    "narrow": {"nose_bridge_width": -0.3, "nose_definition": 0.5},
    "wide": {"nose_bridge_width": 0.3, "nose_definition": 0.3},
    "medium": {"nose_bridge_width": 0.0, "nose_definition": 0.4},
}

EYE_SHAPE_MAP: dict[str, dict[str, float]] = {
    "cat-tilt": {"eye_tilt": 0.3, "eye_openness": 0.5, "eye_height": 0.1},
    "round": {"eye_tilt": 0.0, "eye_openness": 0.6, "eye_height": 0.2},
    "narrow": {"eye_tilt": 0.0, "eye_openness": -0.3, "eye_height": -0.1},
    "droopy": {"eye_tilt": -0.2, "eye_openness": 0.3, "eye_height": -0.1},
}

LIP_FULLNESS_MAP: dict[str, float] = {
    "thin": 0.0,
    "medium": 0.5,
    "full": 1.0,
}

DEFAULT_EXPRESSION_MAP: dict[str, dict[str, float]] = {
    "soft-half-smile": {"mouth_smile": 0.25, "mouth_open": 0.0},
    "neutral": {"mouth_smile": 0.0, "mouth_open": 0.0},
    "slight-smile": {"mouth_smile": 0.15, "mouth_open": 0.0},
    "serious": {"mouth_smile": -0.05, "mouth_open": 0.0, "brow_lower": 0.1},
    "surprised": {"mouth_open": 0.4, "eye_wide": 0.3, "brow_raise": 0.4},
}


@dataclass
class FaceBuildResult:
    """Result from the Face Forge — everything the Blender script needs."""

    shape_keys: dict[str, float]  # shape_key_name → weight
    eye_color_hsv: tuple[float, float, float]
    eye_size_factor: float
    lip_color_hsv: tuple[float, float, float]
    lip_fullness: float
    default_expression: dict[str, float]
    blush_color_hsv: tuple[float, float, float]
    cheekbone_width: float
    ear_elf_factor: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["eye_color_hsv"] = list(self.eye_color_hsv)
        d["lip_color_hsv"] = list(self.lip_color_hsv)
        d["blush_color_hsv"] = list(self.blush_color_hsv)
        return d


def resolve_face(spec: FaceSpec) -> FaceBuildResult:
    """
    Resolve a FaceSpec into a FaceBuildResult for the Blender script.

    This is the main entry point for the Face Forge.
    """
    from hamr.core.textures import hex_to_hsv

    shape_keys: dict[str, float] = {}

    # Jaw
    jaw_overrides = JAW_MAP.get(spec.jaw, JAW_MAP["V-shape"])
    shape_keys.update(jaw_overrides)

    # Cheekbones
    cheek_overrides = CHEEKBONE_MAP.get(spec.cheekbones, CHEEKBONE_MAP["medium"])
    shape_keys.update(cheek_overrides)

    # Nose size
    nose_overrides = NOSE_SIZE_MAP.get(str(spec.nose_size), NOSE_SIZE_MAP["medium"])
    shape_keys.update(nose_overrides)

    # Nose bridge
    bridge_overrides = NOSE_BRIDGE_MAP.get(spec.nose_bridge, NOSE_BRIDGE_MAP["medium"])
    shape_keys.update(bridge_overrides)

    # Eyes
    eye = spec.eyes
    eye_overrides = EYE_SHAPE_MAP.get(eye.shape, EYE_SHAPE_MAP["cat-tilt"])
    shape_keys.update(eye_overrides)
    shape_keys["eye_size"] = eye.size - 1.0  # 1.1 → 0.1 offset

    # Eye color
    eye_color_hsv = hex_to_hsv(eye.iris_hex)

    # Lip fullness
    lip_key = "medium"
    if spec.lip_fullness < 0.3:
        lip_key = "thin"
    elif spec.lip_fullness > 0.7:
        lip_key = "full"
    lip_fullness = LIP_FULLNESS_MAP.get(lip_key, 0.5)

    # Lip color — derive from FaceSpec if provided
    lip_color_hsv = hex_to_hsv("#C47070")  # Default warm lip

    # Default expression
    expression = DEFAULT_EXPRESSION_MAP.get(
        spec.default_expression, DEFAULT_EXPRESSION_MAP["soft-half-smile"]
    )

    # Blush — warm pink default
    blush_hsv = hex_to_hsv("#E0A0A0")

    # Cheekbone width for further adjustment
    cheekbone_width = cheek_overrides.get("cheek_bone_width", 0.0)

    # Ear elf factor (0 = human, 1+ = pointed)
    ear_elf_factor = getattr(spec, "ear_elf_factor", 0.0)

    return FaceBuildResult(
        shape_keys=shape_keys,
        eye_color_hsv=eye_color_hsv,
        eye_size_factor=eye.size,
        lip_color_hsv=lip_color_hsv,
        lip_fullness=lip_fullness,
        default_expression=expression,
        blush_color_hsv=blush_hsv,
        cheekbone_width=cheekbone_width,
        ear_elf_factor=ear_elf_factor,
    )


def list_jaw_presets() -> list[str]:
    """List available jaw shape presets."""
    return list(JAW_MAP.keys())


def list_eye_shape_presets() -> list[str]:
    """List available eye shape presets."""
    return list(EYE_SHAPE_MAP.keys())


def list_expression_presets() -> dict[str, dict[str, float]]:
    """List available default expression presets."""
    return dict(DEFAULT_EXPRESSION_MAP)


# ── Expression Blend Shape Binding (Phase 12 T5) ────────────────────────────
from hamr.face.expressions import (  # noqa: E402
    VRM_EXPRESSIONS,
    VRM_EXPRESSION_COUNT,
    SHAPE_KEY_ALIASES,
    ExpressionBinding,
    ExpressionSet,
    ExpressionBinder,
    build_expression_set,
)