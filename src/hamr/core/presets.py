"""
Character Presets — VRoid-style quick templates.

Six ready-made character specs that cover common anime archetypes.
Each preset fully specifies a CharacterSpec so users can start from
a known-good baseline and override individual parameters.

Phase 11 (T7): The forge breathes presets.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from copy import deepcopy

from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    HairColorSpec,
    EyeSpec,
    SkinSpec,
    ClothingSpec,
    ExpressionSpec,
    PhysicsSpec,
    ExportSpec,
)


# ── Spec-to-Dict Helper ─────────────────────────────────────────────────────

def _normalize_value(value):
    """Recursively convert dataclass instances within a dict to plain dicts."""
    if hasattr(value, "to_dict"):
        return value.to_dict()
    try:
        from dataclasses import is_dataclass
        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
    except Exception:
        pass
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    return value


def spec_to_dict(spec: dict | CharacterSpec) -> dict:
    """Recursively convert a CharacterSpec (or nested dataclass) to a plain dict.

    Accepts either a plain dict (returned as a *deep copy* with any nested
    dataclass instances normalized to plain dicts) or a CharacterSpec
    dataclass instance (converted via ``asdict()`` or ``.to_dict()``).

    This normalization layer lets ``validate_preset()`` and downstream
    consumers always work on plain dicts regardless of whether the
    caller provides a CharacterSpec or a raw spec dict — even if that
    dict has been contaminated with dataclass instances from a previous
    ``CharacterSpec.from_dict()`` call.

    Args:
        spec: A CharacterSpec dataclass instance or a plain dict.

    Returns:
        A plain dict suitable for dict-style access and mutation.
    """
    if isinstance(spec, dict):
        return _normalize_value(spec)
    if hasattr(spec, "to_dict"):
        return spec.to_dict()
    # Fallback: dataclass → asdict
    return asdict(spec)


# ── Character Presets ──────────────────────────────────────────────────────────

CHARACTER_PRESETS: dict[str, dict] = {
    "anime_girl_default": {
        "name": "anime_girl_default",
        "display_name": "Anime Girl — Default",
        "description": "Standard anime schoolgirl with long straight brown hair, medium build, and a cute face.",
        "spec": {
            "name": "Default Schoolgirl",
            "body": {
                "height_cm": 158.0,
                "build": "average",
                "skin": {
                    "base_hex": "#F5D6C3",
                    "undertone": "warm",
                    "freckles": False,
                    "tan_level": 0.4,
                },
                "proportions": {
                    "shoulder_width": 0.35,
                    "bust": 0.55,
                    "waist": 0.30,
                    "hip_width": 0.60,
                    "leg_length": 0.55,
                },
            },
            "face": {
                "jaw": "V-shape",
                "cheekbones": "high",
                "eyes": {
                    "iris_hex": "#8B5E3C",
                    "shape": "round",
                    "size": 1.3,
                },
                "nose_size": "small",
                "nose_bridge": "narrow",
                "lip_fullness": 0.6,
                "default_expression": "soft-half-smile",
            },
            "hair": {
                "style": "straight",
                "length": "long",
                "volume": 0.7,
                "curl_tightness": 0.0,
                "color": {
                    "roots": "#5C3A1E",
                    "mid": "#7A4E28",
                    "tips": "#A06830",
                },
                "shell_layers": 4,
            },
            "clothing": [
                {
                    "name": "school_uniform",
                    "type": "full-outfit",
                    "primary_hex": "#1A1A3E",
                    "accent_hex": "#FFFFFF",
                    "trim_hex": "#C0392B",
                },
            ],
            "expressions": {
                "defaults": {
                    "blink": "subtle",
                    "blush": "always-on",
                },
                "custom": [],
            },
            "physics": {
                "hair": {
                    "stiffness": 0.30,
                    "gravity": 0.25,
                    "drag": 0.35,
                },
                "breast": {
                    "stiffness": 0.25,
                    "drag": 0.60,
                },
            },
        },
    },

    "anime_girl_warrior": {
        "name": "anime_girl_warrior",
        "display_name": "Anime Girl — Warrior",
        "description": "Warrior protagonist with twin-tails, athletic build, and a determined expression.",
        "spec": {
            "name": "Warrior Protagonist",
            "body": {
                "height_cm": 165.0,
                "build": "athletic",
                "skin": {
                    "base_hex": "#E8C4A0",
                    "undertone": "neutral",
                    "freckles": False,
                    "tan_level": 0.5,
                },
                "proportions": {
                    "shoulder_width": 0.45,
                    "bust": 0.50,
                    "waist": 0.35,
                    "hip_width": 0.55,
                    "leg_length": 0.58,
                },
            },
            "face": {
                "jaw": "V-shape",
                "cheekbones": "high",
                "eyes": {
                    "iris_hex": "#E03030",
                    "shape": "cat-tilt",
                    "size": 1.2,
                },
                "nose_size": "small",
                "nose_bridge": "narrow",
                "lip_fullness": 0.5,
                "default_expression": "serious",
            },
            "hair": {
                "style": "ponytail",
                "length": "long",
                "volume": 0.8,
                "curl_tightness": 0.1,
                "color": {
                    "roots": "#1A1A2E",
                    "mid": "#252540",
                    "tips": "#3A3A55",
                },
                "shell_layers": 5,
            },
            "clothing": [
                {
                    "name": "warrior_armor",
                    "type": "full-outfit",
                    "primary_hex": "#2C3E50",
                    "accent_hex": "#C0392B",
                    "trim_hex": "#FFD700",
                },
            ],
            "expressions": {
                "defaults": {
                    "blink": "subtle",
                    "blush": "off",
                },
                "custom": [],
            },
            "physics": {
                "hair": {
                    "stiffness": 0.45,
                    "gravity": 0.35,
                    "drag": 0.40,
                },
                "breast": {
                    "stiffness": 0.30,
                    "drag": 0.55,
                },
            },
        },
    },

    "anime_girl_mage": {
        "name": "anime_girl_mage",
        "display_name": "Anime Girl — Mage",
        "description": "Mystical mage with long wavy silver hair, slender build, and a mysterious expression.",
        "spec": {
            "name": "Silver Enchantress",
            "body": {
                "height_cm": 162.0,
                "build": "slender",
                "skin": {
                    "base_hex": "#F0E0D0",
                    "undertone": "cool",
                    "freckles": False,
                    "tan_level": 0.2,
                },
                "proportions": {
                    "shoulder_width": 0.35,
                    "bust": 0.45,
                    "waist": 0.30,
                    "hip_width": 0.50,
                    "leg_length": 0.60,
                },
            },
            "face": {
                "jaw": "V-shape",
                "cheekbones": "high",
                "eyes": {
                    "iris_hex": "#6080C0",
                    "shape": "narrow",
                    "size": 1.15,
                },
                "nose_size": "small",
                "nose_bridge": "narrow",
                "lip_fullness": 0.6,
                "default_expression": "neutral",
            },
            "hair": {
                "style": "wavy",
                "length": "very-long",
                "volume": 0.85,
                "curl_tightness": 0.4,
                "color": {
                    "roots": "#8A8A9A",
                    "mid": "#B0B0C0",
                    "tips": "#D8D8E8",
                },
                "shell_layers": 6,
            },
            "clothing": [
                {
                    "name": "mage_robes",
                    "type": "full-outfit",
                    "primary_hex": "#2A1A4E",
                    "accent_hex": "#90B0E8",
                    "trim_hex": "#FFD700",
                },
            ],
            "expressions": {
                "defaults": {
                    "blink": "subtle",
                    "blush": "off",
                },
                "custom": [],
            },
            "physics": {
                "hair": {
                    "stiffness": 0.20,
                    "gravity": 0.20,
                    "drag": 0.30,
                },
                "breast": {
                    "stiffness": 0.20,
                    "drag": 0.60,
                },
            },
        },
    },

    "anime_boy_default": {
        "name": "anime_boy_default",
        "display_name": "Anime Boy — Default",
        "description": "Standard anime boy with short brown hair, medium build, and a neutral expression.",
        "spec": {
            "name": "Default Schoolboy",
            "body": {
                "height_cm": 175.0,
                "build": "average",
                "skin": {
                    "base_hex": "#E8C4A0",
                    "undertone": "warm",
                    "freckles": False,
                    "tan_level": 0.5,
                },
                "proportions": {
                    "shoulder_width": 0.50,
                    "bust": 0.40,
                    "waist": 0.40,
                    "hip_width": 0.45,
                    "leg_length": 0.55,
                },
            },
            "face": {
                "jaw": "square",
                "cheekbones": "medium",
                "eyes": {
                    "iris_hex": "#5C4033",
                    "shape": "round",
                    "size": 1.0,
                },
                "nose_size": "medium",
                "nose_bridge": "medium",
                "lip_fullness": 0.4,
                "default_expression": "neutral",
            },
            "hair": {
                "style": "straight",
                "length": "short",
                "volume": 0.5,
                "curl_tightness": 0.0,
                "color": {
                    "roots": "#5C3A1E",
                    "mid": "#7A4E28",
                    "tips": "#A06830",
                },
                "shell_layers": 3,
            },
            "clothing": [],
            "expressions": {
                "defaults": {
                    "blink": "subtle",
                    "blush": "off",
                },
                "custom": [],
            },
            "physics": {
                "hair": {
                    "stiffness": 0.40,
                    "gravity": 0.30,
                    "drag": 0.45,
                },
                "breast": {
                    "stiffness": 0.25,
                    "drag": 0.60,
                },
            },
        },
    },

    "anime_boy_warrior": {
        "name": "anime_boy_warrior",
        "display_name": "Anime Boy — Warrior",
        "description": "Fierce warrior with spiky red hair, athletic build, and an intense expression.",
        "spec": {
            "name": "Crimson Blade",
            "body": {
                "height_cm": 178.0,
                "build": "athletic",
                "skin": {
                    "base_hex": "#D4A874",
                    "undertone": "warm",
                    "freckles": False,
                    "tan_level": 0.6,
                },
                "proportions": {
                    "shoulder_width": 0.55,
                    "bust": 0.40,
                    "waist": 0.45,
                    "hip_width": 0.50,
                    "leg_length": 0.55,
                },
            },
            "face": {
                "jaw": "square",
                "cheekbones": "high",
                "eyes": {
                    "iris_hex": "#E03030",
                    "shape": "narrow",
                    "size": 1.05,
                },
                "nose_size": "medium",
                "nose_bridge": "medium",
                "lip_fullness": 0.4,
                "default_expression": "serious",
            },
            "hair": {
                "style": "wild-curly",
                "length": "short",
                "volume": 0.9,
                "curl_tightness": 0.6,
                "color": {
                    "roots": "#8B1A1A",
                    "mid": "#C03030",
                    "tips": "#E85858",
                },
                "shell_layers": 6,
            },
            "clothing": [
                {
                    "name": "warrior_light_armor",
                    "type": "full-outfit",
                    "primary_hex": "#1A1A3E",
                    "accent_hex": "#C0392B",
                    "trim_hex": "#FFD700",
                },
            ],
            "expressions": {
                "defaults": {
                    "blink": "subtle",
                    "blush": "off",
                },
                "custom": [],
            },
            "physics": {
                "hair": {
                    "stiffness": 0.50,
                    "gravity": 0.35,
                    "drag": 0.45,
                },
                "breast": {
                    "stiffness": 0.25,
                    "drag": 0.60,
                },
            },
        },
    },

    "chibi_cute": {
        "name": "chibi_cute",
        "display_name": "Chibi — Cute",
        "description": "Chibi proportions with big eyes, pastel hair, and a round face. Maximum cuteness.",
        "spec": {
            "name": "Chibi Cutie",
            "body": {
                "height_cm": 120.0,
                "build": "petite",
                "skin": {
                    "base_hex": "#FAE0D2",
                    "undertone": "warm",
                    "freckles": False,
                    "tan_level": 0.2,
                },
                "proportions": {
                    "shoulder_width": 0.50,
                    "bust": 0.50,
                    "waist": 0.50,
                    "hip_width": 0.50,
                    "leg_length": 0.35,
                },
            },
            "face": {
                "jaw": "round",
                "cheekbones": "medium",
                "eyes": {
                    "iris_hex": "#C090E0",
                    "shape": "round",
                    "size": 1.6,
                },
                "nose_size": "small",
                "nose_bridge": "narrow",
                "lip_fullness": 0.7,
                "default_expression": "slight-smile",
            },
            "hair": {
                "style": "wavy",
                "length": "shoulder",
                "volume": 0.9,
                "curl_tightness": 0.3,
                "color": {
                    "roots": "#E0A0C0",
                    "mid": "#F0C0D8",
                    "tips": "#F8E0F0",
                },
                "shell_layers": 5,
            },
            "clothing": [
                {
                    "name": "cute_dress",
                    "type": "full-outfit",
                    "primary_hex": "#FFB6C1",
                    "accent_hex": "#FFFFFF",
                    "trim_hex": "#FF69B4",
                },
            ],
            "expressions": {
                "defaults": {
                    "blink": "subtle",
                    "blush": "always-on",
                },
                "custom": [],
            },
            "physics": {
                "hair": {
                    "stiffness": 0.25,
                    "gravity": 0.20,
                    "drag": 0.30,
                },
                "breast": {
                    "stiffness": 0.20,
                    "drag": 0.60,
                },
            },
        },
    },
}

# ── Preset Categories ──────────────────────────────────────────────────────────

PRESET_CATEGORIES: dict[str, list[str]] = {
    "female": ["anime_girl_default", "anime_girl_warrior", "anime_girl_mage"],
    "male": ["anime_boy_default", "anime_boy_warrior"],
    "chibi": ["chibi_cute"],
}


# ── CharacterPreset Dataclass ──────────────────────────────────────────────────

@dataclass
class CharacterPreset:
    """A VRoid-style character preset — name, description, and full spec dict."""
    name: str
    display_name: str
    description: str
    spec: dict


# ── Pure-Python Functions ──────────────────────────────────────────────────────

def get_preset(name: str) -> CharacterPreset:
    """Look up a preset by internal name.

    Returns a :class:`CharacterPreset` whose ``.spec`` is always a plain
    dict — never a dataclass.  Callers may freely mutate the returned
    spec without affecting the global CHARACTER_PRESETS store.

    Raises:
        KeyError: If no preset exists with the given name.
    """
    if name not in CHARACTER_PRESETS:
        raise KeyError(f"Unknown character preset: {name!r}. "
                       f"Available: {', '.join(sorted(CHARACTER_PRESETS))}")
    entry = CHARACTER_PRESETS[name]
    # spec_to_dict recursively normalizes any nested dataclass instances
    # to plain dicts and returns a fresh copy — callers can mutate freely.
    spec = spec_to_dict(entry["spec"])
    return CharacterPreset(
        name=entry["name"],
        display_name=entry["display_name"],
        description=entry["description"],
        spec=spec,
    )


def list_presets() -> list[CharacterPreset]:
    """Return all available character presets."""
    return [get_preset(name) for name in CHARACTER_PRESETS]


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*.

    - Dicts are merged recursively.
    - Other types (including lists) are simply replaced by the override value.
    - Returns a new dict; neither input is mutated.
    - Dataclass instances are converted to plain dicts before merging.
    """
    # Normalize any dataclass objects to plain dicts so item-assignment works.
    base = spec_to_dict(base) if not isinstance(base, dict) else base
    override = spec_to_dict(override) if not isinstance(override, dict) else override

    result = deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def resolve_preset(name: str, overrides: dict | None = None) -> dict:
    """Merge a preset with user-provided overrides.

    If *overrides* is None or empty, returns a deep copy of the base preset spec.
    Otherwise, *overrides* is deep-merged into the base spec, allowing partial
    overrides like ``{"body": {"height_cm": 170.0}}``.

    The result is always a plain dict — nested dataclass objects are never
    included, so callers can freely use dict item-assignment.
    """
    base = get_preset(name).spec
    if not overrides:
        return base
    result = deep_merge(base, overrides)
    # Normalize to guarantee no nested dataclass objects remain.
    return spec_to_dict(result)


def sanitize_preset(name_or_dict: str | dict) -> dict:
    """Accept either a preset name (str) or a raw spec dict and return a valid spec dict.

    If a string is given and it matches a known preset, the preset's spec is returned.
    If a dict is given, it is returned as-is (caller is responsible for validity).
    Raises:
        KeyError: If a string is given but doesn't match any preset.
        TypeError: If the input is neither a str nor a dict.
    """
    if isinstance(name_or_dict, str):
        return get_preset(name_or_dict).spec
    if isinstance(name_or_dict, dict):
        return deepcopy(name_or_dict)
    raise TypeError(
        f"sanitize_preset expects a str or dict, got {type(name_or_dict).__name__}"
    )


# ── Validation ─────────────────────────────────────────────────────────────────

# Ranges for numeric fields
_NUMERIC_RANGES: dict[str, tuple[float, float]] = {
    "height_cm": (100.0, 220.0),
    "volume": (0.0, 1.0),
    "curl_tightness": (0.0, 1.0),
    "lip_fullness": (0.0, 1.0),
    "tan_level": (0.0, 1.0),
    "size": (0.5, 2.0),
    "shell_layers": (1, 12),
}

# Required top-level keys a spec dict should have
_REQUIRED_SPEC_KEYS = {"body", "face", "hair"}

# Hex color pattern (6 digits after #)
import re as _re
_HEX_PATTERN = _re.compile(r"^#[0-9a-fA-F]{6}$")

# Allowed values for enum-like strings
_ALLOWED_STRINGS: dict[str, set[str]] = {
    "build": {"athletic-slender", "athletic", "slender", "curvy", "average", "tall", "petite", "muscular"},
    "jaw": {"V-shape", "round", "square", "heart"},
    "cheekbones": {"high", "low", "medium"},
    "nose_size": {"small", "medium", "large"},
    "nose_bridge": {"narrow", "wide", "medium"},
    "eye_shape": {"cat-tilt", "round", "narrow", "droopy"},
    "style": {"wild-curly", "straight", "wavy", "braided", "bun", "ponytail"},
    "length": {"short", "medium", "shoulder", "shoulder-plus", "long", "very-long"},
    "undertone": {"warm", "cool", "neutral"},
}


def validate_preset(spec: dict | CharacterSpec) -> list[str]:
    """Return a list of validation warnings for a spec dict or CharacterSpec.

    Accepts either a plain dict or a CharacterSpec dataclass instance.
    If a CharacterSpec is provided, it is converted to a plain dict via
    :func:`spec_to_dict` before validation proceeds.

    Warnings include:
      - Missing required top-level keys
      - String values outside allowed enums
      - Numeric values outside valid ranges
      - Malformed hex color strings
    """
    spec = spec_to_dict(spec)
    warnings: list[str] = []

    # ── Missing required keys ──────────
    for key in _REQUIRED_SPEC_KEYS:
        if key not in spec:
            warnings.append(f"Missing required key: {key}")

    # ── Validate body subtree ──────────
    body = spec.get("body")
    if isinstance(body, dict):
        if "height_cm" in body:
            val = body["height_cm"]
            lo, hi = _NUMERIC_RANGES["height_cm"]
            if not isinstance(val, (int, float)) or not (lo <= val <= hi):
                warnings.append(f"body.height_cm out of range ({lo}–{hi}): {val}")

        if "build" in body:
            if body["build"] not in _ALLOWED_STRINGS["build"]:
                warnings.append(f"body.build unknown: {body['build']!r}")

        if "proportions" in body:
            for pname, pval in body["proportions"].items():
                if not isinstance(pval, (int, float)) or not (0.0 <= pval <= 1.0):
                    warnings.append(f"body.proportions.{pname} out of range (0.0–1.0): {pval}")

        skin = body.get("skin")
        if isinstance(skin, dict):
            if "base_hex" in skin and not _HEX_PATTERN.match(str(skin["base_hex"])):
                warnings.append(f"body.skin.base_hex invalid hex: {skin['base_hex']!r}")
            if "undertone" in skin and skin["undertone"] not in _ALLOWED_STRINGS["undertone"]:
                warnings.append(f"body.skin.undertone unknown: {skin['undertone']!r}")
            if "tan_level" in skin:
                lo, hi = _NUMERIC_RANGES["tan_level"]
                if not isinstance(skin["tan_level"], (int, float)) or not (lo <= skin["tan_level"] <= hi):
                    warnings.append(f"body.skin.tan_level out of range ({lo}–{hi}): {skin['tan_level']}")

    # ── Validate face subtree ──────────
    face = spec.get("face")
    if isinstance(face, dict):
        if "jaw" in face and face["jaw"] not in _ALLOWED_STRINGS["jaw"]:
            warnings.append(f"face.jaw unknown: {face['jaw']!r}")
        if "cheekbones" in face and face["cheekbones"] not in _ALLOWED_STRINGS["cheekbones"]:
            warnings.append(f"face.cheekbones unknown: {face['cheekbones']!r}")
        if "nose_size" in face and face["nose_size"] not in _ALLOWED_STRINGS["nose_size"]:
            warnings.append(f"face.nose_size unknown: {face['nose_size']!r}")
        if "nose_bridge" in face and face["nose_bridge"] not in _ALLOWED_STRINGS["nose_bridge"]:
            warnings.append(f"face.nose_bridge unknown: {face['nose_bridge']!r}")
        if "lip_fullness" in face:
            lo, hi = _NUMERIC_RANGES["lip_fullness"]
            if not isinstance(face["lip_fullness"], (int, float)) or not (lo <= face["lip_fullness"] <= hi):
                warnings.append(f"face.lip_fullness out of range ({lo}–{hi}): {face['lip_fullness']}")

        eyes = face.get("eyes")
        if isinstance(eyes, dict):
            if "iris_hex" in eyes and not _HEX_PATTERN.match(str(eyes["iris_hex"])):
                warnings.append(f"face.eyes.iris_hex invalid hex: {eyes['iris_hex']!r}")
            if "shape" in eyes and eyes["shape"] not in _ALLOWED_STRINGS["eye_shape"]:
                warnings.append(f"face.eyes.shape unknown: {eyes['shape']!r}")
            if "size" in eyes:
                lo, hi = _NUMERIC_RANGES["size"]
                if not isinstance(eyes["size"], (int, float)) or not (lo <= eyes["size"] <= hi):
                    warnings.append(f"face.eyes.size out of range ({lo}–{hi}): {eyes['size']}")

    # ── Validate hair subtree ──────────
    hair = spec.get("hair")
    if isinstance(hair, dict):
        if "style" in hair and hair["style"] not in _ALLOWED_STRINGS["style"]:
            warnings.append(f"hair.style unknown: {hair['style']!r}")
        if "length" in hair and hair["length"] not in _ALLOWED_STRINGS["length"]:
            warnings.append(f"hair.length unknown: {hair['length']!r}")
        if "volume" in hair:
            lo, hi = _NUMERIC_RANGES["volume"]
            if not isinstance(hair["volume"], (int, float)) or not (lo <= hair["volume"] <= hi):
                warnings.append(f"hair.volume out of range ({lo}–{hi}): {hair['volume']}")
        if "curl_tightness" in hair:
            lo, hi = _NUMERIC_RANGES["curl_tightness"]
            if not isinstance(hair["curl_tightness"], (int, float)) or not (lo <= hair["curl_tightness"] <= hi):
                warnings.append(f"hair.curl_tightness out of range ({lo}–{hi}): {hair['curl_tightness']}")
        if "shell_layers" in hair:
            lo, hi = _NUMERIC_RANGES["shell_layers"]
            if not isinstance(hair["shell_layers"], int) or not (lo <= hair["shell_layers"] <= hi):
                warnings.append(f"hair.shell_layers out of range ({lo}–{hi}): {hair['shell_layers']}")

        color = hair.get("color")
        if isinstance(color, dict):
            for ckey in ("roots", "mid", "tips"):
                if ckey in color and not _HEX_PATTERN.match(str(color[ckey])):
                    warnings.append(f"hair.color.{ckey} invalid hex: {color[ckey]!r}")

    return warnings