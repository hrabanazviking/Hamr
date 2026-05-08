"""
Materials Forge — Anime material system for Eevee-optimized VRM avatars.

Phase 12, Task T4: Material System Completion.

Every material is a Principled BSDF node tree tuned for Eevee.
No Cycles nodes. No ray-traced SSS. The Pi renders in real-time or not at all.
"""

from __future__ import annotations

from hamr.materials.anime import (
    AnimeMaterialSpec,
    AnimeMaterialGenerator,
    ANIME_SKIN_PRESETS,
    ANIME_EYE_PRESETS,
    ANIME_HAIR_PRESETS,
    EMBLEMATIC_COLORS,
    hsv_to_rgb,
    rgb_to_hex,
    hsv_to_hex,
    blend_colors,
    compute_material_summary,
    validate_material_spec,
)

__all__ = [
    "AnimeMaterialSpec",
    "AnimeMaterialGenerator",
    "ANIME_SKIN_PRESETS",
    "ANIME_EYE_PRESETS",
    "ANIME_HAIR_PRESETS",
    "EMBLEMATIC_COLORS",
    "hsv_to_rgb",
    "rgb_to_hex",
    "hsv_to_hex",
    "blend_colors",
    "compute_material_summary",
    "validate_material_spec",
]