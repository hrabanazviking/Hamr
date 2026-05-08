"""
Anime Materials — Eevee-optimized material definitions and generators.

This module provides:
- AnimeMaterialSpec: Dataclass defining an anime material's properties
- Preset dictionaries: ANIME_SKIN_PRESETS, ANIME_EYE_PRESETS, ANIME_HAIR_PRESETS
- EMBLEMATIC_COLORS: Named HSV color tuples for preset composition
- Pure-Python color utilities: hsv_to_rgb, rgb_to_hex, hsv_to_hex, blend_colors
- Pure-Python introspection: compute_material_summary, validate_material_spec
- Blender-dependent AnimeMaterialGenerator: Creates Eevee node trees

Design principles (AD-12.2):
- All materials use Principled BSDF with Eevee-compatible features only
- No Cycles nodes, no ray-traced SSS
- Skin uses Principled BSDF Subsurface Weight/Radius (Eevee approximation)
- Eyes use alpha-blend cornea + HSV-tinted iris
- Hair uses Clearcoat + Sheen for anisotropic approximation
- Clothing uses roughness-modulated Principled BSDF with subtle normal maps

Every vertex, every slider, every algorithm is yours.
"""

from __future__ import annotations

import colorsys
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("hamr.materials.anime")

# ──────────────────────────────────────────────────────────────
# Blender availability guard
# ──────────────────────────────────────────────────────────────
try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore
    BLENDER_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# EMBLEMATIC COLORS — Named HSV tuples for anime palette
# ═══════════════════════════════════════════════════════════════
# HSV values are in 0-1 range as per colorsys convention.
# These are the fixed reference points; parameters flow around them.

EMBLEMATIC_COLORS: dict[str, tuple[float, float, float]] = {
    # ── Skin tones ──
    "porcelain": (0.08, 0.12, 0.95),
    "ivory": (0.10, 0.18, 0.92),
    "fair": (0.08, 0.25, 0.90),
    "light": (0.07, 0.35, 0.88),
    "warm_light": (0.08, 0.40, 0.85),
    "medium": (0.07, 0.50, 0.78),
    "tan": (0.07, 0.55, 0.70),
    "olive": (0.10, 0.45, 0.65),
    "dark": (0.06, 0.55, 0.45),
    "deep": (0.05, 0.50, 0.30),
    # ── Eye colors ──
    "brown_eye": (0.07, 0.70, 0.55),
    "blue_eye": (0.58, 0.65, 0.85),
    "green_eye": (0.33, 0.60, 0.65),
    "red_eye": (0.98, 0.75, 0.70),
    "violet_eye": (0.78, 0.55, 0.70),
    "gold_eye": (0.12, 0.80, 0.90),
    "amber_eye": (0.10, 0.75, 0.75),
    "sclera": (0.12, 0.03, 0.96),
    "pupil": (0.67, 0.80, 0.12),
    # ── Hair colors ──
    "black_hair": (0.00, 0.00, 0.10),
    "dark_brown_hair": (0.06, 0.65, 0.25),
    "brown_hair": (0.07, 0.55, 0.40),
    "chestnut_hair": (0.06, 0.60, 0.50),
    "auburn_hair": (0.03, 0.70, 0.45),
    "red_hair": (0.98, 0.70, 0.65),
    "strawberry_hair": (0.03, 0.50, 0.75),
    "blonde_hair": (0.12, 0.55, 0.90),
    "platinum_hair": (0.13, 0.15, 0.95),
    "silver_hair": (0.60, 0.05, 0.88),
    "white_hair": (0.00, 0.00, 0.97),
    "blue_hair": (0.60, 0.65, 0.75),
    "dark_blue_hair": (0.62, 0.70, 0.45),
    "pink_hair": (0.93, 0.50, 0.85),
    "light_pink_hair": (0.93, 0.35, 0.92),
    "purple_hair": (0.78, 0.55, 0.65),
    "green_hair": (0.33, 0.55, 0.60),
    # ── Clothing / fabric ──
    "navy": (0.63, 0.80, 0.25),
    "charcoal": (0.60, 0.05, 0.25),
    "crimson": (0.98, 0.85, 0.55),
    "forest": (0.33, 0.60, 0.30),
    "gold_fabric": (0.12, 0.75, 0.85),
    "cotton_white": (0.00, 0.02, 0.95),
    "denim": (0.61, 0.55, 0.50),
    # ── Misc ──
    "blush": (0.98, 0.45, 0.92),
    "lip_pink": (0.96, 0.50, 0.80),
    "shadow": (0.65, 0.15, 0.20),
}


# ═══════════════════════════════════════════════════════════════
# AnimeMaterialSpec dataclass
# ═══════════════════════════════════════════════════════════════

VALID_MATERIAL_TYPES = {"skin", "eyes", "hair", "clothing"}
VALID_DETAIL_LEVELS = {"minimal", "medium", "high"}


@dataclass
class AnimeMaterialSpec:
    """Specification for an anime-style Eevee material.

    Attributes:
        material_type: One of "skin", "eyes", "hair", "clothing".
        primary_hsv: Primary color as (hue, saturation, value) in 0-1 range.
        secondary_hsv: Secondary/accent color as (hue, saturation, value).
        detail_level: Detail complexity — "minimal", "medium", "high".
        subsurface: Enable subsurface scattering (skin only).
        anisotropic: Enable anisotropic shading hint (hair only).
        metallic: Metallic value 0-1 (0 = dielectric, 1 = fully metallic).
        roughness: Roughness 0-1 (0 = mirror-smooth, 1 = completely rough).
        alpha: Opacity 0-1 (1 = fully opaque, 0 = invisible).
        emission_hsv: Optional emission color for glow effects (magic eyes etc).
    """

    material_type: str = "skin"
    primary_hsv: tuple[float, float, float] = (0.07, 0.35, 0.88)
    secondary_hsv: tuple[float, float, float] = (0.0, 0.0, 0.0)
    detail_level: str = "medium"
    subsurface: bool = False
    anisotropic: bool = False
    metallic: float = 0.0
    roughness: float = 0.5
    alpha: float = 1.0
    emission_hsv: tuple[float, float, float] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary, handling None and tuple serialization."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> AnimeMaterialSpec:
        """Create from dictionary, ignoring unknown keys."""
        if "emission_hsv" in data and isinstance(data["emission_hsv"], list):
            data["emission_hsv"] = tuple(data["emission_hsv"])
        for key in ("primary_hsv", "secondary_hsv"):
            if key in data and isinstance(data[key], list):
                data[key] = tuple(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════
# Presets — Curated anime material presets
# ═══════════════════════════════════════════════════════════════

ANIME_SKIN_PRESETS: dict[str, AnimeMaterialSpec] = {
    "light": AnimeMaterialSpec(
        material_type="skin",
        primary_hsv=EMBLEMATIC_COLORS["light"],
        secondary_hsv=EMBLEMATIC_COLORS["blush"],
        detail_level="medium",
        subsurface=True,
        roughness=0.45,
        alpha=1.0,
    ),
    "medium": AnimeMaterialSpec(
        material_type="skin",
        primary_hsv=EMBLEMATIC_COLORS["medium"],
        secondary_hsv=EMBLEMATIC_COLORS["warm_light"],
        detail_level="medium",
        subsurface=True,
        roughness=0.50,
        alpha=1.0,
    ),
    "dark": AnimeMaterialSpec(
        material_type="skin",
        primary_hsv=EMBLEMATIC_COLORS["dark"],
        secondary_hsv=EMBLEMATIC_COLORS["olive"],
        detail_level="medium",
        subsurface=True,
        roughness=0.55,
        alpha=1.0,
    ),
    "tan": AnimeMaterialSpec(
        material_type="skin",
        primary_hsv=EMBLEMATIC_COLORS["tan"],
        secondary_hsv=EMBLEMATIC_COLORS["medium"],
        detail_level="medium",
        subsurface=True,
        roughness=0.50,
        alpha=1.0,
    ),
    "pale": AnimeMaterialSpec(
        material_type="skin",
        primary_hsv=EMBLEMATIC_COLORS["ivory"],
        secondary_hsv=EMBLEMATIC_COLORS["blush"],
        detail_level="medium",
        subsurface=True,
        roughness=0.40,
        alpha=1.0,
    ),
}

ANIME_EYE_PRESETS: dict[str, AnimeMaterialSpec] = {
    "brown": AnimeMaterialSpec(
        material_type="eyes",
        primary_hsv=EMBLEMATIC_COLORS["brown_eye"],
        secondary_hsv=EMBLEMATIC_COLORS["pupil"],
        detail_level="high",
        roughness=0.15,
        alpha=1.0,
    ),
    "blue": AnimeMaterialSpec(
        material_type="eyes",
        primary_hsv=EMBLEMATIC_COLORS["blue_eye"],
        secondary_hsv=EMBLEMATIC_COLORS["pupil"],
        detail_level="high",
        roughness=0.10,
        alpha=1.0,
    ),
    "green": AnimeMaterialSpec(
        material_type="eyes",
        primary_hsv=EMBLEMATIC_COLORS["green_eye"],
        secondary_hsv=EMBLEMATIC_COLORS["pupil"],
        detail_level="high",
        roughness=0.12,
        alpha=1.0,
    ),
    "red": AnimeMaterialSpec(
        material_type="eyes",
        primary_hsv=EMBLEMATIC_COLORS["red_eye"],
        secondary_hsv=EMBLEMATIC_COLORS["pupil"],
        detail_level="high",
        roughness=0.10,
        alpha=1.0,
        emission_hsv=EMBLEMATIC_COLORS["red_eye"],
    ),
    "violet": AnimeMaterialSpec(
        material_type="eyes",
        primary_hsv=EMBLEMATIC_COLORS["violet_eye"],
        secondary_hsv=EMBLEMATIC_COLORS["pupil"],
        detail_level="high",
        roughness=0.10,
        alpha=1.0,
        emission_hsv=EMBLEMATIC_COLORS["violet_eye"],
    ),
    "gold": AnimeMaterialSpec(
        material_type="eyes",
        primary_hsv=EMBLEMATIC_COLORS["gold_eye"],
        secondary_hsv=EMBLEMATIC_COLORS["pupil"],
        detail_level="high",
        roughness=0.10,
        alpha=1.0,
        emission_hsv=EMBLEMATIC_COLORS["gold_eye"],
    ),
}

ANIME_HAIR_PRESETS: dict[str, AnimeMaterialSpec] = {
    "black": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["black_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["dark_brown_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.35,
        alpha=1.0,
    ),
    "brown": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["brown_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["chestnut_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.40,
        alpha=1.0,
    ),
    "blonde": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["blonde_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["platinum_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.45,
        alpha=1.0,
    ),
    "red": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["red_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["strawberry_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.45,
        alpha=1.0,
    ),
    "silver": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["silver_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["white_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.30,
        alpha=1.0,
        metallic=0.10,
    ),
    "blue": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["blue_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["dark_blue_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.40,
        alpha=1.0,
    ),
    "pink": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["pink_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["light_pink_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.45,
        alpha=1.0,
    ),
    "white": AnimeMaterialSpec(
        material_type="hair",
        primary_hsv=EMBLEMATIC_COLORS["white_hair"],
        secondary_hsv=EMBLEMATIC_COLORS["silver_hair"],
        detail_level="medium",
        anisotropic=True,
        roughness=0.30,
        alpha=1.0,
    ),
}


# ═══════════════════════════════════════════════════════════════
# Pure-Python color utility functions (no bpy dependency)
# ═══════════════════════════════════════════════════════════════

def hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    """Convert HSV (0-1 range) to RGB (0-1 range).

    Args:
        h: Hue in 0-1 range (wraps around).
        s: Saturation in 0-1 range (clamped).
        v: Value/brightness in 0-1 range (clamped).

    Returns:
        (r, g, b) tuple in 0-1 range.
    """
    # Clamp inputs to valid ranges
    h = h % 1.0
    s = max(0.0, min(1.0, s))
    v = max(0.0, min(1.0, v))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB (0-1 range) to hex color string (#RRGGBB).

    Args:
        r: Red channel 0-1.
        g: Green channel 0-1.
        b: Blue channel 0-1.

    Returns:
        Hex color string like "#ff8800".
    """
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convert HSV (0-1 range) directly to hex color string.

    Convenience function combining hsv_to_rgb and rgb_to_hex.

    Args:
        h: Hue in 0-1 range.
        s: Saturation in 0-1 range.
        v: Value/brightness in 0-1 range.

    Returns:
        Hex color string like "#ff8800".
    """
    r, g, b = hsv_to_rgb(h, s, v)
    return rgb_to_hex(r, g, b)


def blend_colors(
    hsv1: tuple[float, float, float],
    hsv2: tuple[float, float, float],
    factor: float,
) -> tuple[float, float, float]:
    """Linearly blend two HSV colors.

    Args:
        hsv1: First color as (h, s, v) in 0-1 range.
        hsv2: Second color as (h, s, v) in 0-1 range.
        factor: Blend factor — 0.0 = hsv1, 1.0 = hsv2, 0.5 = midpoint.

    Returns:
        Blended (h, s, v) tuple in 0-1 range.
    """
    factor = max(0.0, min(1.0, factor))
    h1, s1, v1 = hsv1
    h2, s2, v2 = hsv2

    # Hue blending through shortest arc
    diff = h2 - h1
    if diff > 0.5:
        # Shorter to go backward (e.g. 0.9 → 0.1 = go 0.2 back not 0.8 forward)
        h = (h1 + (diff - 1.0) * factor) % 1.0
    elif diff < -0.5:
        # Shorter to go forward (e.g. 0.1 → 0.9 = go 0.2 forward not 0.8 back)
        h = (h1 + (diff + 1.0) * factor) % 1.0
    else:
        # Direct interpolation is shortest path
        h = h1 + diff * factor

    # Ensure hue is in [0, 1)
    h = h % 1.0

    s = s1 + (s2 - s1) * factor
    v = v1 + (v2 - v1) * factor

    # Clamp saturation and value
    s = max(0.0, min(1.0, s))
    v = max(0.0, min(1.0, v))

    return (h, s, v)


def compute_material_summary(spec: AnimeMaterialSpec) -> dict:
    """Compute a summary dictionary of material properties for shader setup.

    This function is pure-Python and does not require bpy. It produces
    the parameter set needed for node tree creation.

    Args:
        spec: The material specification.

    Returns:
        Dictionary with keys: roughness, metallic, alpha, has_emission,
        material_type, primary_hex, secondary_hex, detail_level,
        subsurface_enabled, anisotropic_enabled.
    """
    primary_hex = hsv_to_hex(*spec.primary_hsv)
    secondary_hex = hsv_to_hex(*spec.secondary_hsv)
    emission_hex = hsv_to_hex(*spec.emission_hsv) if spec.emission_hsv else None

    # Eevee SSS approximation parameters (AD-12.2)
    subsurface_weight = 0.0
    subsurface_radius = (0.0, 0.0, 0.0)

    if spec.subsurface and spec.material_type == "skin":
        weight_map = {"minimal": 0.10, "medium": 0.20, "high": 0.30}
        subsurface_weight = weight_map.get(spec.detail_level, 0.20)
        # Subsurface radius based on skin tone — red scatters further
        _, saturation, _ = spec.primary_hsv
        if saturation < 0.3:
            # Pale skin: more red scattering
            subsurface_radius = (1.0, 0.2, 0.1)
        elif saturation < 0.5:
            # Medium skin: moderate red scattering
            subsurface_radius = (0.8, 0.4, 0.2)
        else:
            # Dark skin: less visible scattering
            subsurface_radius = (0.5, 0.3, 0.2)

    # Anisotropic hint parameters (Eevee: Clearcoat + Sheen approximation)
    clearcoat = 0.0
    sheen = 0.0
    if spec.anisotropic and spec.material_type == "hair":
        clearcoat_map = {"minimal": 0.2, "medium": 0.4, "high": 0.6}
        sheen_map = {"minimal": 0.3, "medium": 0.5, "high": 0.7}
        clearcoat = clearcoat_map.get(spec.detail_level, 0.4)
        sheen = sheen_map.get(spec.detail_level, 0.5)

    summary = {
        "roughness": spec.roughness,
        "metallic": spec.metallic,
        "alpha": spec.alpha,
        "has_emission": spec.emission_hsv is not None,
        "material_type": spec.material_type,
        "primary_hex": primary_hex,
        "secondary_hex": secondary_hex,
        "emission_hex": emission_hex,
        "detail_level": spec.detail_level,
        "subsurface_enabled": spec.subsurface,
        "subsurface_weight": subsurface_weight,
        "subsurface_radius": subsurface_radius,
        "anisotropic_enabled": spec.anisotropic,
        "clearcoat": clearcoat,
        "sheen": sheen,
    }

    return summary


def validate_material_spec(spec: AnimeMaterialSpec) -> list[str]:
    """Validate an AnimeMaterialSpec and return a list of warning strings.

    Returns an empty list if the spec is valid. Warnings are non-fatal
    issues that may produce unexpected results.

    Args:
        spec: The material specification to validate.

    Returns:
        List of warning message strings.
    """
    warnings: list[str] = []

    # Material type validation
    if spec.material_type not in VALID_MATERIAL_TYPES:
        warnings.append(
            f"Invalid material_type '{spec.material_type}'. "
            f"Expected one of: {sorted(VALID_MATERIAL_TYPES)}"
        )

    # Detail level validation
    if spec.detail_level not in VALID_DETAIL_LEVELS:
        warnings.append(
            f"Invalid detail_level '{spec.detail_level}'. "
            f"Expected one of: {sorted(VALID_DETAIL_LEVELS)}"
        )

    # Primary HSV range validation
    h, s, v = spec.primary_hsv
    if not (0.0 <= h <= 1.0):
        warnings.append(f"Primary hue {h} outside 0-1 range (will wrap)")
    if not (0.0 <= s <= 1.0):
        warnings.append(f"Primary saturation {s} outside 0-1 range")
    if not (0.0 <= v <= 1.0):
        warnings.append(f"Primary value {v} outside 0-1 range")

    # Secondary HSV range validation
    h2, s2, v2 = spec.secondary_hsv
    if not (0.0 <= h2 <= 1.0):
        warnings.append(f"Secondary hue {h2} outside 0-1 range (will wrap)")
    if not (0.0 <= s2 <= 1.0):
        warnings.append(f"Secondary saturation {s2} outside 0-1 range")
    if not (0.0 <= v2 <= 1.0):
        warnings.append(f"Secondary value {v2} outside 0-1 range")

    # Metallic range
    if spec.metallic < 0.0:
        warnings.append(f"Metallic {spec.metallic} is negative")
    if spec.metallic > 1.0:
        warnings.append(f"Metallic {spec.metallic} exceeds 1.0")

    # Roughness range
    if spec.roughness < 0.0:
        warnings.append(f"Roughness {spec.roughness} is negative")
    if spec.roughness > 1.0:
        warnings.append(f"Roughness {spec.roughness} exceeds 1.0")

    # Alpha range
    if spec.alpha < 0.0:
        warnings.append(f"Alpha {spec.alpha} is negative")
    if spec.alpha > 1.0:
        warnings.append(f"Alpha {spec.alpha} exceeds 1.0")

    # Emission HSV range
    if spec.emission_hsv is not None:
        eh, es, ev = spec.emission_hsv
        if not (0.0 <= eh <= 1.0):
            warnings.append(f"Emission hue {eh} outside 0-1 range")
        if not (0.0 <= es <= 1.0):
            warnings.append(f"Emission saturation {es} outside 0-1 range")
        if not (0.0 <= ev <= 1.0):
            warnings.append(f"Emission value {ev} outside 0-1 range")

    # Type-specific validation
    if spec.subsurface and spec.material_type != "skin":
        warnings.append(
            f"Subsurface enabled on material_type '{spec.material_type}' "
            f"(typically only used with 'skin')"
        )
    if spec.anisotropic and spec.material_type != "hair":
        warnings.append(
            f"Anisotropic enabled on material_type '{spec.material_type}' "
            f"(typically only used with 'hair')"
        )
    if spec.metallic > 0.5 and spec.material_type == "skin":
        warnings.append(
            f"Metallic {spec.metallic} is high for skin material"
        )

    # Zero-value primary color
    if spec.primary_hsv == (0.0, 0.0, 0.0) and spec.material_type != "hair":
        warnings.append("Primary HSV is (0,0,0) — pure black (may be intentional for hair)")

    return warnings


# ═══════════════════════════════════════════════════════════════
# Blender-dependent AnimeMaterialGenerator
# ═══════════════════════════════════════════════════════════════

class AnimeMaterialGenerator:
    """Generate Eevee-optimized Principled BSDF material node trees.

    This class requires bpy (Blender Python API). Creating an instance
    without bpy available will succeed, but calling generate() or any
    create_* method will raise RuntimeError.

    All materials are designed for Eevee viewport rendering on Pi 5.
    No Cycles nodes, no ray-traced SSS. The Principled BSDF node provides
    everything we need for anime-style materials.

    Usage:
        generator = AnimeMaterialGenerator()
        mat_name = generator.generate(skin_spec, "body_mesh")
    """

    def __init__(self) -> None:
        """Initialize the generator. Checks bpy availability."""
        self._blender_available = BLENDER_AVAILABLE

    def _require_blender(self) -> None:
        """Raise RuntimeError if bpy is not available."""
        if not BLENDER_AVAILABLE or bpy is None:
            raise RuntimeError(
                "bpy is not available — AnimeMaterialGenerator requires "
                "Blender's Python API. Run inside Blender or headless Blender."
            )

    def generate(self, material_spec: AnimeMaterialSpec, mesh_name: str) -> str:
        """Create an Eevee-optimized material and assign it to a mesh.

        Dispatches to the appropriate create_* method based on material_type.

        Args:
            material_spec: The material specification.
            mesh_name: Name of the mesh object to assign the material to.

        Returns:
            Name of the created material.

        Raises:
            RuntimeError: If bpy is not available.
        """
        self._require_blender()

        creators = {
            "skin": self.create_skin_material,
            "eyes": self.create_eye_material,
            "hair": self.create_hair_material,
            "clothing": self.create_clothing_material,
        }

        creator = creators.get(material_spec.material_type)
        if creator is None:
            logger.warning(
                f"Unknown material_type '{material_spec.material_type}', "
                f"falling back to clothing"
            )
            creator = self.create_clothing_material

        mat_name = creator(material_spec, mesh_name)
        return mat_name

    def create_skin_material(
        self, spec: AnimeMaterialSpec, mesh_name: str
    ) -> str:
        """Create skin material with SSS approximation for Eevee.

        Uses Principled BSDF with:
        - Subsurface Weight: 0.15-0.30 depending on detail_level
        - Subsurface Radius: (R, G, B) derived from skin tone
        - Subsurface Tint: Matches primary color
        - Roughness: From spec (typically 0.40-0.55)
        - Optional pore detail via noise texture (high detail_level)

        Args:
            spec: Material specification with subsurface=True.
            mesh_name: Target mesh object name.

        Returns:
            Name of the created material.
        """
        self._require_blender()

        summary = compute_material_summary(spec)
        mat_name = f"hamr_skin_{mesh_name}"

        # Create material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.use_backface_culling = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear default nodes
        nodes.clear()

        # ── Output node ──
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

        # ── Principled BSDF ──
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (0, 0)

        # Base color from primary HSV
        r, g, b = hsv_to_rgb(*spec.primary_hsv)
        principled.inputs["Base Color"].default_value = (r, g, b, 1.0)

        # Roughness
        principled.inputs["Roughness"].default_value = summary["roughness"]

        # SSS approximation for Eevee (AD-12.2)
        if summary["subsurface_enabled"]:
            principled.inputs["Subsurface Weight"].default_value = summary["subsurface_weight"]
            sr, sg, sb = summary["subsurface_radius"]
            principled.inputs["Subsurface Radius"].default_value = (sr, sg, sb)
            # Tint matches the skin color
            principled.inputs["Subsurface Scale"].default_value = 0.5
            # Blush/secondary tint for cheek areas
            r2, g2, b2 = hsv_to_rgb(*spec.secondary_hsv)
            principled.inputs["Subsurface Tint"].default_value = (r2, g2, b2, 1.0)

        # ── High detail: pore noise texture ──
        if spec.detail_level == "high":
            noise = nodes.new("ShaderNodeTexNoise")
            noise.location = (-400, 200)
            noise.inputs["Scale"].default_value = 50.0
            noise.inputs["Detail"].default_value = 8.0
            noise.inputs["Roughness"].default_value = 0.6

            # Mix noise into roughness
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = "FLOAT"
            mix.location = (-200, 100)
            mix.inputs[0].default_value = 0.15  # 15% noise influence on roughness
            mix.inputs[6].default_value = summary["roughness"]  # A
            mix.inputs[7].default_value = summary["roughness"] + 0.1  # B

            links.new(noise.outputs["Fac"], mix.inputs[2])
            links.new(mix.outputs[2], principled.inputs["Roughness"])

        # Link Principled BSDF → Output
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])

        # Assign material to mesh
        self._assign_material(mat, mesh_name)

        logger.info(
            f"Skin material '{mat_name}': roughness={summary['roughness']:.2f}, "
            f"sss_weight={summary['subsurface_weight']:.2f}"
        )
        return mat_name

    def create_eye_material(
        self, spec: AnimeMaterialSpec, mesh_name: str
    ) -> str:
        """Create eye material with iris highlight and refraction look.

        Uses Principled BSDF with:
        - Low roughness (0.10-0.15) for glassy cornea
        - IOR 1.38 for cornea refraction effect
        - Emission for magic/glowing eyes (if emission_hsv set)
        - Specular tint from secondary color (pupil)

        Args:
            spec: Material specification with material_type="eyes".
            mesh_name: Target mesh object name.

        Returns:
            Name of the created material.
        """
        self._require_blender()

        summary = compute_material_summary(spec)
        mat_name = f"hamr_eyes_{mesh_name}"

        # Create material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.use_backface_culling = False  # Eyes need inner faces

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear defaults
        nodes.clear()

        # ── Output ──
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (800, 0)

        # ── Principled BSDF for iris ──
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (200, 0)

        # Iris base color
        r, g, b = hsv_to_rgb(*spec.primary_hsv)
        principled.inputs["Base Color"].default_value = (r, g, b, 1.0)

        # Eye-specific: very low roughness for glassy look
        principled.inputs["Roughness"].default_value = summary["roughness"]

        # Index of refraction for cornea (1.38 is realistic)
        principled.inputs["IOR"].default_value = 1.38

        # Slight sheen for iris depth
        principled.inputs["Sheen Weight"].default_value = 0.3

        # ── Specular highlight ──
        # High specular gives anime eye "sparkle"
        principled.inputs["Specular IOR Level"].default_value = 0.8

        # ── Emission for magic eyes ──
        if summary["has_emission"]:
            er, eg, eb = hsv_to_rgb(*spec.emission_hsv)  # type: ignore
            principled.inputs["Emission Color"].default_value = (er, eg, eb, 1.0)
            principled.inputs["Emission Strength"].default_value = 0.5

        # ── Pupil overlay via mix shader ──
        if spec.detail_level in ("medium", "high"):
            # Create pupil color (dark, near-black)
            pr, pg, pb = hsv_to_rgb(*spec.secondary_hsv)
            pupil_color = nodes.new("ShaderNodeRGB")
            pupil_color.location = (-200, -200)
            pupil_color.outputs[0].default_value = (pr, pg, pb, 1.0)

            # Mix between iris and pupil
            mix_shader = nodes.new("ShaderNodeMixShader")
            mix_shader.location = (500, 0)

            pupil_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            pupil_bsdf.location = (200, -200)
            pupil_bsdf.inputs["Base Color"].default_value = (pr, pg, pb, 1.0)
            pupil_bsdf.inputs["Roughness"].default_value = 0.05

            # Mix factor: 0 = iris, 1 = pupil (controlled per-vertex)
            mix_shader.inputs[0].default_value = 0.3

            links.new(principled.outputs["BSDF"], mix_shader.inputs[1])
            links.new(pupil_bsdf.outputs["BSDF"], mix_shader.inputs[2])
            links.new(mix_shader.outputs["Shader"], output.inputs["Surface"])
        else:
            links.new(principled.outputs["BSDF"], output.inputs["Surface"])

        # Assign to mesh
        self._assign_material(mat, mesh_name)

        logger.info(
            f"Eye material '{mat_name}': roughness={summary['roughness']:.2f}, "
            f"emission={summary['has_emission']}"
        )
        return mat_name

    def create_hair_material(
        self, spec: AnimeMaterialSpec, mesh_name: str
    ) -> str:
        """Create hair material with anisotropic highlight approximation.

        Eevee does not support true anisotropic shading. We approximate using:
        - Clearcoat: 0.2-0.6 for specular highlight layer
        - Sheen: 0.3-0.7 for rim-lighting effect
        - Root-to-tip gradient via vertex colors (if detail_level >= medium)

        Args:
            spec: Material specification with material_type="hair".
            mesh_name: Target mesh object name.

        Returns:
            Name of the created material.
        """
        self._require_blender()

        summary = compute_material_summary(spec)
        mat_name = f"hamr_hair_{mesh_name}"

        # Create material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.use_backface_culling = False  # Hair often has inverted faces

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear defaults
        nodes.clear()

        # ── Output ──
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

        # ── Principled BSDF ──
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (0, 0)

        # Hair base color
        r, g, b = hsv_to_rgb(*spec.primary_hsv)
        principled.inputs["Base Color"].default_value = (r, g, b, 1.0)

        # Roughness
        principled.inputs["Roughness"].default_value = summary["roughness"]

        # Anisotropic approximation via clearcoat (AD-12.2)
        if summary["anisotropic_enabled"]:
            principled.inputs["Clearcoat Weight"].default_value = summary["clearcoat"]
            principled.inputs["Clearcoat Roughness"].default_value = 0.15
            principled.inputs["Sheen Weight"].default_value = summary["sheen"]
            # Tint sheen toward secondary color for root-to-tip gradient hint
            r2, g2, b2 = hsv_to_rgb(*spec.secondary_hsv)
            principled.inputs["Sheen Tint"].default_value = (r2, g2, b2, 1.0)

        # Metallic hint (for silver/white hair)
        if summary["metallic"] > 0.0:
            principled.inputs["Metallic"].default_value = summary["metallic"]

        # ── Root-to-tip gradient (medium/high detail) ──
        if spec.detail_level in ("medium", "high") and spec.secondary_hsv != (0.0, 0.0, 0.0):
            # Color mix node: blend between primary and secondary
            # In production, this would connect to vertex color UVs
            # For Eevee, we set up the node and let vertex colors drive it
            color2 = nodes.new("ShaderNodeRGB")
            color2.location = (-400, 200)
            r2, g2, b2 = hsv_to_rgb(*spec.secondary_hsv)
            color2.outputs[0].default_value = (r2, g2, b2, 1.0)

            mix_color = nodes.new("ShaderNodeMix")
            mix_color.data_type = "RGBA"
            mix_color.location = (-200, 0)
            mix_color.inputs[0].default_value = 0.3  # 30% tip color blend
            mix_color.inputs[6].default_value = (r, g, b, 1.0)  # Primary
            # Input 7 would be the tip color, connected from color2

            links.new(color2.outputs[0], mix_color.inputs[7])
            links.new(mix_color.outputs[2], principled.inputs["Base Color"])

        # Link Principled BSDF → Output
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])

        # Assign to mesh
        self._assign_material(mat, mesh_name)

        logger.info(
            f"Hair material '{mat_name}': roughness={summary['roughness']:.2f}, "
            f"clearcoat={summary['clearcoat']:.2f}, sheen={summary['sheen']:.2f}"
        )
        return mat_name

    def create_clothing_material(
        self, spec: AnimeMaterialSpec, mesh_name: str
    ) -> str:
        """Create clothing material with fabric weave pattern hint.

        Uses Principled BSDF with:
        - Roughness from spec (typically 0.5-0.8 for fabric)
        - Subtle normal map for weave texture (medium/high detail)
        - Secondary color used for accent/thread detail

        Args:
            spec: Material specification with material_type="clothing".
            mesh_name: Target mesh object name.

        Returns:
            Name of the created material.
        """
        self._require_blender()

        summary = compute_material_summary(spec)
        mat_name = f"hamr_clothing_{mesh_name}"

        # Create material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.use_backface_culling = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear defaults
        nodes.clear()

        # ── Output ──
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

        # ── Principled BSDF ──
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (0, 0)

        # Fabric base color
        r, g, b = hsv_to_rgb(*spec.primary_hsv)
        principled.inputs["Base Color"].default_value = (r, g, b, 1.0)

        # Roughness — fabric is typically rough
        principled.inputs["Roughness"].default_value = summary["roughness"]

        # Metallic from spec (for armor/accessory materials)
        principled.inputs["Metallic"].default_value = summary["metallic"]

        # Alpha transparency (for sheer fabrics)
        if summary["alpha"] < 1.0:
            mat.blend_method = "CLIP" if hasattr(mat, "blend_method") else None  # Eevee blend
            principled.inputs["Alpha"].default_value = summary["alpha"]

        # ── Fabric texture: subtle noise for weave hint (medium/high) ──
        if spec.detail_level in ("medium", "high"):
            # Bump/normal from noise for fabric texture
            noise = nodes.new("ShaderNodeTexNoise")
            noise.location = (-400, 200)
            noise.inputs["Scale"].default_value = 100.0 if spec.detail_level == "high" else 40.0
            noise.inputs["Detail"].default_value = 4.0
            noise.inputs["Roughness"].default_value = 0.7

            # Normal map node
            normal_map = nodes.new("ShaderNodeNormalMap")
            normal_map.location = (-200, 200)
            normal_map.inputs["Strength"].default_value = 0.05  # Very subtle

            links.new(noise.outputs["Fac"], normal_map.inputs["Height"])
            links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])

        # ── Thread accent color (high detail) ──
        if spec.detail_level == "high" and spec.secondary_hsv != (0.0, 0.0, 0.0):
            # Mix fabric color with thread accent
            color2 = nodes.new("ShaderNodeRGB")
            color2.location = (-400, -200)
            r2, g2, b2 = hsv_to_rgb(*spec.secondary_hsv)
            color2.outputs[0].default_value = (r2, g2, b2, 1.0)

            mix = nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.location = (-200, -100)
            mix.inputs[0].default_value = 0.05  # 5% accent blend
            mix.inputs[6].default_value = (r, g, b, 1.0)

            links.new(color2.outputs[0], mix.inputs[7])
            links.new(mix.outputs[2], principled.inputs["Base Color"])

        # Link Principled BSDF → Output
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])

        # Assign to mesh
        self._assign_material(mat, mesh_name)

        logger.info(
            f"Clothing material '{mat_name}': roughness={summary['roughness']:.2f}, "
            f"metallic={summary['metallic']:.2f}"
        )
        return mat_name

    def _assign_material(self, material, mesh_name: str) -> None:
        """Assign a Blender material object to a mesh.

        Args:
            material: The bpy.types.Material to assign.
            mesh_name: Name of the mesh object in the scene.
        """
        self._require_blender()

        obj = bpy.data.objects.get(mesh_name)
        if obj is None:
            logger.warning(f"Mesh '{mesh_name}' not found in scene, material not assigned")
            return

        if obj.data is None:
            logger.warning(f"Object '{mesh_name}' has no mesh data")
            return

        # Assign material slot
        if len(obj.data.materials) == 0:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material

        # Make this the active material
        obj.active_material_index = len(obj.data.materials) - 1

        logger.debug(f"Material '{material.name}' assigned to mesh '{mesh_name}'")