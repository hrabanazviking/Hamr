"""
Materials Forge — Anime material system for Eevee-optimized VRM avatars.

Phase 12, Task T4: Material System Completion.
Phase 16, Task T1: MToon shader system added.

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

from hamr.materials.mtoon import (
    MToonConfig,
    PRESET_MTOON_CONFIGS,
    validate_mtoon_config,
    mtoon_config_to_vrm_properties,
    mtoon_config_to_glTF_material,
    create_mtoon_preset,
    list_mtoon_presets,
    blend_mtoon_configs,
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
    "MToonConfig",
    "PRESET_MTOON_CONFIGS",
    "validate_mtoon_config",
    "mtoon_config_to_vrm_properties",
    "mtoon_config_to_glTF_material",
    "create_mtoon_preset",
    "list_mtoon_presets",
    "blend_mtoon_configs",
]