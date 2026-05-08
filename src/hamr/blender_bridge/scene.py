"""
Scene Manager — Blender scene setup and teardown.

Creates clean scenes, manages objects, and ensures no leftover state
between forge runs. The forge leaves no ash.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("hamr.blender_bridge.scene")

# This module is designed to run INSIDE Blender (imported by scripts
# that execute in Blender's Python environment). It uses bpy directly.
# When imported outside Blender, bpy will not be available — that's fine,
# the module just won't be callable.

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore
    BLENDER_AVAILABLE = False


def new_scene(name: str = "HamrForge") -> None:
    """Create a new clean scene, removing all existing objects."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — this function must run inside Blender")

    # Delete all objects in all collections
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    # Delete all orphan data
    _purge_orphans()

    # Rename the scene
    if bpy.context.scene:
        bpy.context.scene.name = name

    logger.info(f"Scene created: {name}")


def clean_scene() -> None:
    """Remove all objects and orphan data from the current scene."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    # Select all objects
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    # Purge orphans
    _purge_orphans()

    logger.info("Scene cleaned")


def _purge_orphans() -> None:
    """Remove all orphan data blocks (meshes, materials, textures, etc.)."""
    # Purge orphan data
    for block_type in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.textures,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.shape_keys,
    ):
        for block in block_type:
            if block.users == 0:
                block_type.remove(block)

    logger.debug("Orphan data purged")


def get_armature(scene: Any = None) -> Any | None:
    """Find the first armature object in the scene."""
    if not BLENDER_AVAILABLE:
        return None

    scene = scene or bpy.context.scene
    for obj in scene.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def get_mesh_objects(scene: Any = None) -> list[Any]:
    """Find all mesh objects in the scene."""
    if not BLENDER_AVAILABLE:
        return []

    scene = scene or bpy.context.scene
    return [obj for obj in scene.objects if obj.type == "MESH"]


def set_scene_defaults() -> None:
    """Set sensible defaults for character generation scenes."""
    if not BLENDER_AVAILABLE:
        return

    # Use Cycles for baking (fall back to Eevee for speed)
    bpy.context.scene.render.engine = "BLENDER_EEVEE"

    # Unit settings (metric, 1 unit = 1 meter)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    logger.debug("Scene defaults set: Eevee, metric, 1u=1m")


def clean_blend_backups(output_dir: str | None = None) -> list[str]:
    """Clean up .blend1/.blend2 backup files."""
    import os
    from pathlib import Path

    cleaned = []
    search_dirs = [Path(".")]
    if output_dir:
        search_dirs.append(Path(output_dir))

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for backup_pattern in ("*.blend1", "*.blend2"):
            for f in search_dir.glob(backup_pattern):
                f.unlink()
                cleaned.append(str(f))

    if cleaned:
        logger.info(f"Cleaned {len(cleaned)} backup files")
    return cleaned