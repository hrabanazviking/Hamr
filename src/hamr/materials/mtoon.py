"""
MToon Shader System — VRM MToon cel-shading configuration and conversion.

MToon is the standard anime cel-shading shader for VRM avatars, defining
two-tone lighting, outline rendering, rim lighting, matcap, emission, and
transparency. This module provides pure-Python configuration, validation,
VRM/glTF conversion, presets, and blending — no bpy dependency.

Phase 16, T1: The forge remembers every parameter.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field, asdict, fields

logger = logging.getLogger("hamr.materials.mtoon")


# ═══════════════════════════════════════════════════════════════
# MToonConfig dataclass
# ═══════════════════════════════════════════════════════════════

# Valid enum values
VALID_RENDER_MODES = {"opaque", "cutout", "transparent"}
VALID_CULL_MODES = {"off", "front", "back"}


@dataclass
class MToonConfig:
    """Configuration for a VRM MToon shader material.

    MToon provides two-tone cel shading with lit/shade color split,
    outline rendering, rim lighting, emission, matcap, and UV transforms.

    Attributes:
        lit_color: Base color under direct light (RGB 0-1).
        shade_color: Color in shadow areas (RGB 0-1).
        lit_shade_shift: Shift threshold between lit and shade (-1 to 1).
        lit_shade_toony: Cel-shading sharpness (0=smooth, 1=full cel).
        outline_width: Outline thickness in Blender units.
        outline_color: Outline color (RGB 0-1).
        rim_lighting_mix: Blend factor for rim lighting (0=off, 1=full).
        rim_color: Color of the rim/fresnel highlight (RGB 0-1).
        rim_fresnel_power: Exponent for rim fresnel effect.
        emission_color: Emissive glow color (RGB 0-1).
        emission_intensity: Emission brightness multiplier.
        matcap_texture: Optional matcap texture path or name.
        uv_transform_scale: UV scale (U, V) — values > 1 tile, < 1 stretch.
        uv_transform_offset: UV offset (U, V) in 0-1 range.
        alpha_cutoff: Alpha threshold for cutout mode.
        render_mode: "opaque", "cutout", or "transparent".
        cull_mode: "off" (double-sided), "front", or "back".
        z_write: Whether to write to depth buffer.
        z_test: Whether to test against depth buffer.
    """

    lit_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    shade_color: tuple[float, float, float] = (0.8, 0.8, 0.8)
    lit_shade_shift: float = 0.0
    lit_shade_toony: float = 0.9
    outline_width: float = 0.0
    outline_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rim_lighting_mix: float = 0.0
    rim_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    rim_fresnel_power: float = 1.0
    emission_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    emission_intensity: float = 0.0
    matcap_texture: str | None = None
    uv_transform_scale: tuple[float, float] = (1.0, 1.0)
    uv_transform_offset: tuple[float, float] = (0.0, 0.0)
    alpha_cutoff: float = 0.5
    render_mode: str = "opaque"
    cull_mode: str = "back"
    z_write: bool = True
    z_test: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MToonConfig:
        """Create from dictionary, ignoring unknown keys."""
        # Convert lists back to tuples for tuple fields
        tuple_fields = {
            "lit_color", "shade_color", "outline_color",
            "rim_color", "emission_color",
            "uv_transform_scale", "uv_transform_offset",
        }
        for key in tuple_fields:
            if key in data and isinstance(data[key], list):
                data[key] = tuple(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════
# Preset MToon Configurations
# ═══════════════════════════════════════════════════════════════

PRESET_MTOON_CONFIGS: dict[str, MToonConfig] = {
    "anime_skin": MToonConfig(
        lit_color=(0.95, 0.80, 0.70),
        shade_color=(0.75, 0.58, 0.52),
        lit_shade_shift=0.0,
        lit_shade_toony=0.9,
        outline_width=0.02,
        outline_color=(0.10, 0.05, 0.02),
        rim_lighting_mix=0.1,
        rim_color=(1.0, 0.95, 0.90),
        rim_fresnel_power=2.5,
        emission_color=(0.0, 0.0, 0.0),
        emission_intensity=0.0,
        render_mode="opaque",
        cull_mode="back",
        z_write=True,
    ),
    "anime_hair": MToonConfig(
        lit_color=(0.45, 0.30, 0.22),
        shade_color=(0.18, 0.10, 0.08),
        lit_shade_shift=0.0,
        lit_shade_toony=0.7,
        outline_width=0.05,
        outline_color=(0.0, 0.0, 0.0),
        rim_lighting_mix=0.2,
        rim_color=(0.8, 0.7, 0.6),
        rim_fresnel_power=2.0,
        emission_color=(0.0, 0.0, 0.0),
        emission_intensity=0.0,
        render_mode="opaque",
        cull_mode="back",
        z_write=True,
    ),
    "anime_eyes": MToonConfig(
        lit_color=(1.0, 1.0, 1.0),
        shade_color=(0.7, 0.7, 0.75),
        lit_shade_shift=0.05,
        lit_shade_toony=0.95,
        outline_width=0.0,
        outline_color=(0.0, 0.0, 0.0),
        rim_lighting_mix=0.0,
        rim_color=(1.0, 1.0, 1.0),
        rim_fresnel_power=1.0,
        emission_color=(0.0, 0.0, 0.0),
        emission_intensity=0.0,
        render_mode="transparent",
        cull_mode="off",
        z_write=False,
        alpha_cutoff=0.5,
    ),
    "anime_outfit": MToonConfig(
        lit_color=(0.75, 0.35, 0.35),
        shade_color=(0.45, 0.18, 0.18),
        lit_shade_shift=0.0,
        lit_shade_toony=0.8,
        outline_width=0.03,
        outline_color=(0.05, 0.02, 0.02),
        rim_lighting_mix=0.1,
        rim_color=(0.9, 0.85, 0.80),
        rim_fresnel_power=1.5,
        emission_color=(0.0, 0.0, 0.0),
        emission_intensity=0.0,
        render_mode="opaque",
        cull_mode="back",
        z_write=True,
    ),
    "anime_accessory": MToonConfig(
        lit_color=(0.85, 0.82, 0.78),
        shade_color=(0.50, 0.48, 0.45),
        lit_shade_shift=0.1,
        lit_shade_toony=0.5,
        outline_width=0.0,
        outline_color=(0.0, 0.0, 0.0),
        rim_lighting_mix=0.3,
        rim_color=(1.0, 0.98, 0.90),
        rim_fresnel_power=3.0,
        emission_color=(0.0, 0.0, 0.0),
        emission_intensity=0.0,
        render_mode="opaque",
        cull_mode="back",
        z_write=True,
    ),
}


# ═══════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════

def _validate_color_tuple(name: str, value: tuple[float, float, float]) -> list[str]:
    """Validate a color tuple is length 3 with values in 0-1 range."""
    issues: list[str] = []
    if not isinstance(value, (tuple, list)):
        issues.append(f"{name} must be a tuple, got {type(value).__name__}")
        return issues
    if len(value) != 3:
        issues.append(f"{name} must have 3 components, got {len(value)}")
        return issues
    for i, c in enumerate(value):
        if not isinstance(c, (int, float)):
            issues.append(f"{name}[{i}] must be numeric, got {type(c).__name__}")
        elif c < 0.0 or c > 1.0:
            issues.append(f"{name}[{i}] = {c} out of range [0, 1]")
    return issues


def _validate_uv_tuple(name: str, value: tuple[float, float]) -> list[str]:
    """Validate a UV tuple is length 2."""
    issues: list[str] = []
    if not isinstance(value, (tuple, list)):
        issues.append(f"{name} must be a tuple, got {type(value).__name__}")
        return issues
    if len(value) != 2:
        issues.append(f"{name} must have 2 components, got {len(value)}")
        return issues
    for i, c in enumerate(value):
        if not isinstance(c, (int, float)):
            issues.append(f"{name}[{i}] must be numeric, got {type(c).__name__}")
    return issues


def validate_mtoon_config(config: MToonConfig) -> list[str]:
    """Validate an MToonConfig and return a list of issue strings.

    Returns:
        List of human-readable issue descriptions. Empty list means valid.
    """
    issues: list[str] = []

    # --- Color tuples ---
    for color_field in (
        "lit_color", "shade_color", "outline_color",
        "rim_color", "emission_color",
    ):
        issues.extend(_validate_color_tuple(color_field, getattr(config, color_field)))

    # --- UV tuples ---
    for uv_field in ("uv_transform_scale", "uv_transform_offset"):
        issues.extend(_validate_uv_tuple(uv_field, getattr(config, uv_field)))

    # --- Scalar ranges ---
    if not isinstance(config.lit_shade_shift, (int, float)):
        issues.append("lit_shade_shift must be numeric")
    elif config.lit_shade_shift < -1.0 or config.lit_shade_shift > 1.0:
        issues.append(
            f"lit_shade_shift = {config.lit_shade_shift} out of range [-1, 1]"
        )

    if not isinstance(config.lit_shade_toony, (int, float)):
        issues.append("lit_shade_toony must be numeric")
    elif config.lit_shade_toony < 0.0 or config.lit_shade_toony > 1.0:
        issues.append(
            f"lit_shade_toony = {config.lit_shade_toony} out of range [0, 1]"
        )

    if not isinstance(config.outline_width, (int, float)):
        issues.append("outline_width must be numeric")
    elif config.outline_width < 0.0:
        issues.append(f"outline_width = {config.outline_width} must be >= 0")

    if not isinstance(config.rim_lighting_mix, (int, float)):
        issues.append("rim_lighting_mix must be numeric")
    elif config.rim_lighting_mix < 0.0 or config.rim_lighting_mix > 1.0:
        issues.append(
            f"rim_lighting_mix = {config.rim_lighting_mix} out of range [0, 1]"
        )

    if not isinstance(config.rim_fresnel_power, (int, float)):
        issues.append("rim_fresnel_power must be numeric")
    elif config.rim_fresnel_power < 0.0:
        issues.append(f"rim_fresnel_power = {config.rim_fresnel_power} must be >= 0")

    if not isinstance(config.emission_intensity, (int, float)):
        issues.append("emission_intensity must be numeric")
    elif config.emission_intensity < 0.0:
        issues.append(f"emission_intensity = {config.emission_intensity} must be >= 0")

    if not isinstance(config.alpha_cutoff, (int, float)):
        issues.append("alpha_cutoff must be numeric")
    elif config.alpha_cutoff < 0.0 or config.alpha_cutoff > 1.0:
        issues.append(f"alpha_cutoff = {config.alpha_cutoff} out of range [0, 1]")

    # --- Enum values ---
    if config.render_mode not in VALID_RENDER_MODES:
        issues.append(
            f"render_mode = '{config.render_mode}' not in {sorted(VALID_RENDER_MODES)}"
        )

    if config.cull_mode not in VALID_CULL_MODES:
        issues.append(
            f"cull_mode = '{config.cull_mode}' not in {sorted(VALID_CULL_MODES)}"
        )

    # --- Semantic checks ---
    if config.render_mode == "transparent" and config.z_write:
        issues.append("transparent render_mode usually requires z_write=False")

    if config.render_mode == "cutout" and config.alpha_cutoff <= 0.0:
        issues.append("cutout render_mode requires alpha_cutoff > 0")

    return issues


# ═══════════════════════════════════════════════════════════════
# VRM Extension Conversion
# ═══════════════════════════════════════════════════════════════

def mtoon_config_to_vrm_properties(config: MToonConfig) -> dict:
    """Convert an MToonConfig to a VRM MToon extension property dict.

    This produces the schema expected by the VRM 1.0 MToon extension
    (VRMC_materials_mtoon). The output can be embedded in a glTF JSON's
    material.extensions dict.

    Args:
        config: The MToon configuration to convert.

    Returns:
        Dictionary matching VRMC_materials_mtoon schema.
    """
    render_mode_map = {
        "opaque": "Opaque",
        "cutout": "Cutout",
        "transparent": "Transparent",
    }
    cull_mode_map = {
        "off": "Off",
        "front": "Front",
        "back": "Back",
    }

    properties: dict = {
        "specVersion": 1,
        "color": {
            "lit": {
                "linear": list(config.lit_color),
            },
            "shade": {
                "linear": list(config.shade_color),
            },
        },
        "litAndShadeBlending": {
            "shift": config.lit_shade_shift,
            "toony": config.lit_shade_toony,
        },
        "outline": {
            "width": config.outline_width,
            "color": {
                "linear": list(config.outline_color),
            },
        },
        "rim": {
            "lightingMix": config.rim_lighting_mix,
            "color": {
                "linear": list(config.rim_color),
            },
            "fresnelPower": config.rim_fresnel_power,
        },
        "emission": {
            "color": {
                "linear": list(config.emission_color),
            },
            "intensity": config.emission_intensity,
        },
        "renderMode": render_mode_map.get(config.render_mode, "Opaque"),
        "cullMode": cull_mode_map.get(config.cull_mode, "Back"),
        "zWrite": config.z_write,
        "zTest": config.z_test,
    }

    # Alpha cutoff only relevant for cutout mode
    if config.render_mode == "cutout":
        properties["transparentWithZWrite"] = config.z_write
        properties["renderQueueOffset"] = 0
        properties["alphaCutoff"] = config.alpha_cutoff

    # Transparent mode needs z-write hint
    if config.render_mode == "transparent":
        properties["transparentWithZWrite"] = config.z_write
        properties["renderQueueOffset"] = 0

    # UV transform (only include if non-identity)
    scale_u, scale_v = config.uv_transform_scale
    offset_u, offset_v = config.uv_transform_offset
    if scale_u != 1.0 or scale_v != 1.0 or offset_u != 0.0 or offset_v != 0.0:
        properties["uvTransform"] = {
            "scale": [scale_u, scale_v],
            "offset": [offset_u, offset_v],
        }

    # Matcap texture (only if provided)
    if config.matcap_texture is not None:
        properties["matcap"] = {
            "texture": config.matcap_texture,
        }

    return properties


# ═══════════════════════════════════════════════════════════════
# glTF Material Conversion
# ═══════════════════════════════════════════════════════════════

def mtoon_config_to_glTF_material(config: MToonConfig) -> dict:
    """Convert an MToonConfig to a glTF 2.0 material dictionary.

    The MToon extension dict is embedded under the
    VRMC_materials_mtoon key. For fully unlit materials (toony=1.0,
    no rim, no emission), KHR_materials_unlit is also set as a hint.

    Args:
        config: The MToon configuration to convert.

    Returns:
        glTF 2.0 material dict with extensions.
    """
    material: dict = {
        "name": "MToonMaterial",
        "pbrMetallicRoughness": {
            "baseColorFactor": list(config.lit_color) + [1.0],
            "metallicFactor": 0.0,
            "roughnessFactor": 1.0 - config.lit_shade_toony * 0.5,
        },
        "alphaMode": {
            "opaque": "OPAQUE",
            "cutout": "MASK",
            "transparent": "BLEND",
        }.get(config.render_mode, "OPAQUE"),
        "alphaCutoff": config.alpha_cutoff if config.render_mode == "cutout" else None,
        "doubleSided": config.cull_mode == "off",
        "extensions": {
            "VRMC_materials_mtoon": mtoon_config_to_vrm_properties(config),
        },
    }

    # Clean up None values
    if material["alphaCutoff"] is None:
        del material["alphaCutoff"]

    # For fully toony materials (cel-shaded), add unlit extension hint
    # This helps glTF consumers that don't understand MToon
    is_effectively_unlit = (
        config.lit_shade_toony >= 0.99
        and config.rim_lighting_mix == 0.0
        and config.emission_intensity == 0.0
        and config.outline_width == 0.0
    )
    if is_effectively_unlit:
        material["extensions"]["KHR_materials_unlit"] = {}

    return material


# ═══════════════════════════════════════════════════════════════
# Preset Management
# ═══════════════════════════════════════════════════════════════

def create_mtoon_preset(name: str, **overrides) -> MToonConfig:
    """Create an MToonConfig from a named preset with optional overrides.

    Args:
        name: Preset name from PRESET_MTOON_CONFIGS.
        **overrides: Keyword arguments to override preset values.

    Returns:
        A new MToonConfig with preset defaults and overrides applied.

    Raises:
        ValueError: If the preset name is not found.
    """
    if name not in PRESET_MTOON_CONFIGS:
        raise ValueError(
            f"Unknown MToon preset '{name}'. "
            f"Available: {sorted(PRESET_MTOON_CONFIGS.keys())}"
        )

    # Deep-copy the preset to avoid mutation
    preset = copy.deepcopy(PRESET_MTOON_CONFIGS[name])

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(preset, key):
            setattr(preset, key, value)
        else:
            raise ValueError(
                f"Unknown MToonConfig field '{key}'. "
                f"Valid fields: {[f.name for f in fields(MToonConfig)]}"
            )

    return preset


def list_mtoon_presets() -> list[str]:
    """Return a sorted list of available MToon preset names."""
    return sorted(PRESET_MTOON_CONFIGS.keys())


# ═══════════════════════════════════════════════════════════════
# Blending
# ═══════════════════════════════════════════════════════════════

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * max(0.0, min(1.0, t))


def _lerp_tuple(
    a: tuple[float, ...], b: tuple[float, ...], t: float
) -> tuple[float, ...]:
    """Linear interpolation between two tuples of floats."""
    return tuple(_lerp(ai, bi, t) for ai, bi in zip(a, b))


def blend_mtoon_configs(
    a: MToonConfig, b: MToonConfig, t: float
) -> MToonConfig:
    """Linearly blend between two MToonConfig instances.

    Numeric and tuple fields are interpolated. String and enum fields
    snap to b when t >= 0.5 (majority vote). None fields stay None
    unless both are set.

    Args:
        a: Start configuration (t=0 returns this).
        b: End configuration (t=1 returns this).
        t: Blend factor in [0, 1].

    Returns:
        New MToonConfig with blended values.
    """
    t = max(0.0, min(1.0, t))

    result = MToonConfig()

    # Interpolatable color/uv tuples
    tuple_fields_3 = [
        "lit_color", "shade_color", "outline_color",
        "rim_color", "emission_color",
    ]
    for field_name in tuple_fields_3:
        setattr(
            result,
            field_name,
            _lerp_tuple(getattr(a, field_name), getattr(b, field_name), t),
        )

    tuple_fields_2 = ["uv_transform_scale", "uv_transform_offset"]
    for field_name in tuple_fields_2:
        setattr(
            result,
            field_name,
            _lerp_tuple(getattr(a, field_name), getattr(b, field_name), t),
        )

    # Interpolatable scalar fields
    scalar_fields = [
        "lit_shade_shift", "lit_shade_toony", "outline_width",
        "rim_lighting_mix", "rim_fresnel_power", "emission_intensity",
        "alpha_cutoff",
    ]
    for field_name in scalar_fields:
        setattr(
            result,
            field_name,
            _lerp(getattr(a, field_name), getattr(b, field_name), t),
        )

    # Snap fields (choose b when t >= 0.5)
    snap_fields = ["render_mode", "cull_mode"]
    for field_name in snap_fields:
        setattr(result, field_name, getattr(b if t >= 0.5 else a, field_name))

    # Boolean fields (choose b when t >= 0.5)
    bool_fields = ["z_write", "z_test"]
    for field_name in bool_fields:
        setattr(result, field_name, getattr(b if t >= 0.5 else a, field_name))

    # None-able fields
    if a.matcap_texture is not None and b.matcap_texture is not None:
        # Both set: snap to b when t >= 0.5
        result.matcap_texture = b.matcap_texture if t >= 0.5 else a.matcap_texture
    elif b.matcap_texture is not None:
        result.matcap_texture = b.matcap_texture
    else:
        result.matcap_texture = a.matcap_texture

    return result