"""
Mesh Operations — Common Blender mesh operations.

These are the hammer blows of the forge. Not the artistry —
the craft. Shape keys, materials, transforms, and the like.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger("hamr.blender_bridge.mesh_ops")

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None
    BLENDER_AVAILABLE = False


def apply_shape_key(
    obj: Any,
    key_name: str,
    value: float,
) -> None:
    """Set a shape key value on a mesh object."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    if not obj.data.shape_keys:
        logger.warning(f"No shape keys on {obj.name}")
        return

    key_block = obj.data.shape_keys.key_blocks.get(key_name)
    if key_block is None:
        logger.warning(f"Shape key '{key_name}' not found on {obj.name}")
        return

    key_block.value = max(0.0, min(1.0, value))
    logger.debug(f"Shape key '{key_name}' on {obj.name} set to {value:.3f}")


def scale_armature(
    armature: Any,
    height_cm: float,
    axis: str = "Z",
) -> None:
    """Scale armature to a target height in centimeters."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    # Get current bounding box height
    bbox = armature.bound_box
    min_z = min(v[2] for v in bbox)
    max_z = max(v[2] for v in bbox)
    current_height_m = max_z - min_z
    current_height_cm = current_height_m * 100.0

    if current_height_cm <= 0:
        logger.warning(f"Armature {armature.name} has zero height — cannot scale")
        return

    scale_factor = height_cm / current_height_cm

    # Scale the armature and all child objects
    armature.scale = (
        scale_factor if axis == "X" else 1.0,
        scale_factor if axis == "Y" else 1.0,
        scale_factor if axis == "Z" else 1.0,
    )

    # Apply scale
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.transform_apply(scale=True)
    armature.select_set(False)

    logger.info(f"Scaled {armature.name} to {height_cm}cm (factor: {scale_factor:.3f})")


def get_all_materials(obj: Any) -> list[Any]:
    """Get all materials assigned to an object."""
    return [slot.material for slot in obj.material_slots if slot.material]


def find_material_by_name(obj: Any, name_pattern: str) -> Any | None:
    """Find a material by partial name match on an object."""
    name_lower = name_pattern.lower()
    for slot in obj.material_slots:
        if slot.material and name_lower in slot.material.name.lower():
            return slot.material
    return None


def duplicate_object(obj: Any, new_name: str | None = None) -> Any:
    """Duplicate a Blender object and return the copy."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    new_obj = obj.copy()
    new_obj.data = obj.data.copy()
    if new_name:
        new_obj.name = new_name
    bpy.context.collection.objects.link(new_obj)
    return new_obj


def join_objects(objects: list[Any], name: str = "Joined") -> Any:
    """Join multiple objects into one."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    if not objects:
        return None

    # Deselect all
    bpy.ops.object.select_all(action="DESELECT")

    # Select target objects
    for obj in objects:
        obj.select_set(True)

    # Set active object
    bpy.context.view_layer.objects.active = objects[0]

    # Join
    bpy.ops.object.join()

    joined = bpy.context.active_object
    joined.name = name

    logger.info(f"Joined {len(objects)} objects into {name}")
    return joined