"""
Body Presets — Named body type configurations.

Each preset maps to a set of proportion slider values.
The forge resolves these early so every parameter is explicit.
"""

from hamr.core.constants import BODY_PRESETS

# Re-export for convenience
__all__ = ["BODY_PRESETS", "BODY_PRESET_ALIASES"]

# Aliases — common names that map to canonical presets
BODY_PRESET_ALIASES: dict[str, str] = {
    "slim": "athletic-slender",
    "fit": "athletic",
    "thin": "slender",
    "curvy": "curvy",
    "normal": "average",
    "default": "athletic-slender",
    "thick": "curvy",
    "tall": "tall",
    "short": "petite",
    "buff": "muscular",
}