"""
Validation — Ensure specs are well-formed before they reach the forge.

No malformed spec shall pass through the gates.
"""

from __future__ import annotations

from hamr.core.models import CharacterSpec


# Valid option sets for constrained fields
VALID_BUILDS = {
    "athletic-slender", "athletic", "slender", "curvy", "average",
    "muscular", "petite", "tall", "plus-size",
}

VALID_JAW_SHAPES = {"V-shape", "round", "square", "heart", "oval"}

VALID_EYE_SHAPES = {"cat-tilt", "round", "narrow", "droopy", "almond"}

VALID_HAIR_STYLES = {
    "wild-curly", "curly", "wavy", "straight", "braided",
    "bun", "ponytail", "bob", "pixie", "long-straight",
    "tousled", "messy-bun", "twin-tails", "half-up",
}

VALID_HAIR_LENGTHS = {
    "short", "medium", "shoulder-plus", "long", "very-long",
}

VALID_EXPORT_FORMATS = {"vrm1", "glb", "blend"}

VALID_SKIN_UNDERTONES = {"warm", "cool", "neutral"}


def validate_spec(spec: CharacterSpec) -> list[str]:
    """
    Validate a CharacterSpec and return a list of error messages.

    Returns an empty list if the spec is valid.
    """
    errors: list[str] = []

    # Name
    if not spec.name or not spec.name.strip():
        errors.append("name: must not be empty")

    # Body
    if spec.body.build not in VALID_BUILDS:
        errors.append(
            f"body.build: '{spec.body.build}' not in valid builds: {VALID_BUILDS}"
        )

    if not (100.0 <= spec.body.height_cm <= 250.0):
        errors.append(
            f"body.height_cm: {spec.body.height_cm} outside range [100, 250]"
        )

    for key, value in spec.body.proportions.items():
        if not (0.0 <= value <= 1.0):
            errors.append(
                f"body.proportions.{key}: {value} outside range [0.0, 1.0]"
            )

    # Skin
    if spec.body.skin.undertone not in VALID_SKIN_UNDERTONES:
        errors.append(
            f"body.skin.undertone: '{spec.body.skin.undertone}' not in {VALID_SKIN_UNDERTONES}"
        )

    if not (0.0 <= spec.body.skin.tan_level <= 1.0):
        errors.append(
            f"body.skin.tan_level: {spec.body.skin.tan_level} outside range [0.0, 1.0]"
        )

    # Hex colors — basic validation
    hex_fields = [
        ("body.skin.base_hex", spec.body.skin.base_hex),
        ("face.eyes.iris_hex", spec.face.eyes.iris_hex),
        ("hair.color.roots", spec.hair.color.roots),
        ("hair.color.mid", spec.hair.color.mid),
        ("hair.color.tips", spec.hair.color.tips),
    ]
    for field_path, value in hex_fields:
        if not _is_valid_hex(value):
            errors.append(f"{field_path}: '{value}' is not a valid hex color (#RRGGBB)")

    # Face
    if spec.face.jaw not in VALID_JAW_SHAPES:
        errors.append(
            f"face.jaw: '{spec.face.jaw}' not in {VALID_JAW_SHAPES}"
        )

    if spec.face.eyes.shape not in VALID_EYE_SHAPES:
        errors.append(
            f"face.eyes.shape: '{spec.face.eyes.shape}' not in {VALID_EYE_SHAPES}"
        )

    if not (0.3 <= spec.face.eyes.size <= 2.0):
        errors.append(
            f"face.eyes.size: {spec.face.eyes.size} outside range [0.3, 2.0]"
        )

    if not (0.0 <= spec.face.lip_fullness <= 1.0):
        errors.append(
            f"face.lip_fullness: {spec.face.lip_fullness} outside range [0.0, 1.0]"
        )

    # Hair
    if spec.hair.style not in VALID_HAIR_STYLES:
        errors.append(
            f"hair.style: '{spec.hair.style}' not in {VALID_HAIR_STYLES}"
        )

    if spec.hair.length not in VALID_HAIR_LENGTHS:
        errors.append(
            f"hair.length: '{spec.hair.length}' not in {VALID_HAIR_LENGTHS}"
        )

    if not (0.0 <= spec.hair.volume <= 1.0):
        errors.append(
            f"hair.volume: {spec.hair.volume} outside range [0.0, 1.0]"
        )

    if not (0.0 <= spec.hair.curl_tightness <= 1.0):
        errors.append(
            f"hair.curl_tightness: {spec.hair.curl_tightness} outside range [0.0, 1.0]"
        )

    if not (2 <= spec.hair.shell_layers <= 10):
        errors.append(
            f"hair.shell_layers: {spec.hair.shell_layers} outside range [2, 10]"
        )

    # Physics
    if not (0.0 <= spec.physics.hair.stiffness <= 1.0):
        errors.append(
            f"physics.hair.stiffness: {spec.physics.hair.stiffness} outside [0.0, 1.0]"
        )

    if not (0.0 <= spec.physics.hair.gravity <= 1.0):
        errors.append(
            f"physics.hair.gravity: {spec.physics.hair.gravity} outside [0.0, 1.0]"
        )

    if not (0.0 <= spec.physics.hair.drag <= 1.0):
        errors.append(
            f"physics.hair.drag: {spec.physics.hair.drag} outside [0.0, 1.0]"
        )

    # Clothing hex colors
    for i, outfit in enumerate(spec.clothing):
        for color_field in ("primary_hex", "accent_hex", "trim_hex"):
            value = getattr(outfit, color_field)
            if not _is_valid_hex(value):
                errors.append(
                    f"clothing[{i}].{color_field}: '{value}' is not a valid hex color"
                )

    # Export
    if spec.export.format not in VALID_EXPORT_FORMATS:
        errors.append(
            f"export.format: '{spec.export.format}' not in {VALID_EXPORT_FORMATS}"
        )

    return errors


def _is_valid_hex(value: str) -> bool:
    """Check if a string is a valid hex color (#RRGGBB)."""
    if not isinstance(value, str):
        return False
    if not value.startswith("#"):
        return False
    if len(value) != 7:
        return False
    try:
        int(value[1:], 16)
        return True
    except ValueError:
        return False