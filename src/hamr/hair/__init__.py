"""
Hair Forge — Procedural and library-based hair generation.

Phase 2: Placeholder. The forge will be built.
Hair is VRoid's crown jewel — replicating it procedurally
is the hardest open-source challenge.
"""

from __future__ import annotations

import logging
from pathlib import Path

from hamr.core.models import HairColorSpec, HairStyleSpec

logger = logging.getLogger("hamr.hair")


def generate_hair_texture(spec: HairColorSpec, size: int = 1024) -> "Image":
    """Generate a procedural hair strand texture."""
    from hamr.core.textures import generate_hair_texture
    return generate_hair_texture(spec, size)


def apply_hair_style(spec: HairStyleSpec) -> None:
    """Apply a hair style. Placeholder for Phase 3."""
    raise NotImplementedError("Hair Style Forge coming in Phase 3")