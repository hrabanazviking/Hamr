"""
Stub Bones — Create missing VRM 1.0 humanoid bones.

MB-Lab generates 22 of the 25 required VRM humanoid bones.
The missing three are jaw, leftEye, and rightEye.
This module creates micro-stub bones (1mm) at the correct anatomical
positions relative to the head bone, parents them correctly, and returns
a mapping dict for VRM bone mapping integration.

AD-11.1: Stub bone strategy — micro-bones parented to head,
tagged with _hamr_stub=True custom property.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from hamr.core.constants import VRM_25_BONE_NAMES

logger = logging.getLogger("hamr.rigs.stub_bones")

try:
    import bpy  # type: ignore

    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False

# ── Stub bone definitions ────────────────────────────────────────────
# Each required stub bone is defined with:
#   - vrm_name: VRM 1.0 humanoid bone name
#   - blender_name: the name we give the bone in Blender's armature
#   - parent: which existing bone to parent to
#   - offset_from_head: (x, y, z) offset in metres relative to head bone HEAD
#     Z=up convention (Blender default)

STUB_BONE_DEFS: list[dict[str, Any]] = [
    {
        "vrm_name": "jaw",
        "blender_name": "jaw",
        "parent": "head",
        "offset_from_head": (0.0, 0.0, -0.07),  # Below chin — 7cm below head center
        "length": 0.005,  # 5mm micro-bone
        "description": "Jaw stub — positioned at chin",
    },
    {
        "vrm_name": "leftEye",
        "blender_name": "leftEye",
        "parent": "head",
        "offset_from_head": (0.03, 0.04, 0.03),  # Left eye — ~3cm L, 4cm forward, 3cm up
        "length": 0.005,
        "description": "Left eye stub — positioned at left eye socket",
    },
    {
        "vrm_name": "rightEye",
        "blender_name": "rightEye",
        "parent": "head",
        "offset_from_head": (-0.03, 0.04, 0.03),  # Right eye — ~3cm R, 4cm forward, 3cm up
        "length": 0.005,
        "description": "Right eye stub — positioned at right eye socket",
    },
]


def detect_missing_bones(existing_bone_names: set[str]) -> set[str]:
    """Detect which VRM-required bones are missing from an armature.

    Pure-Python function — does not require Blender.

    Args:
        existing_bone_names: Set of bone names currently in the armature.

    Returns:
        Set of VRM bone names that are missing.
    """
    # Bones that are commonly missing and need to be stubbed
    bones_that_need_stubs = {d["vrm_name"] for d in STUB_BONE_DEFS}

    # Also check any of the 25 required bones that are completely absent
    missing = set()
    for vrm_name in VRM_25_BONE_NAMES:
        # Check both the VRM name and common Blender equivalents
        if vrm_name not in existing_bone_names:
            # Check if MB-Lab-named equivalent exists
            mb_lab_name = _vrm_to_mblab(vrm_name)
            if mb_lab_name not in existing_bone_names:
                missing.add(vrm_name)

    # But we only return the ones we can stub (jaw, eyes)
    # Other missing bones are a structural problem
    stubbable = bones_that_need_stubs & missing
    return stubbable


def _vrm_to_mblab(vrm_name: str) -> str:
    """Map a VRM bone name to its MB-Lab Blender equivalent.

    FP-2: Uses canonical MB_LAB_BONE_MAP from hamr.core.constants.
    Pure-Python — falls back to identity mapping for unknown bones.
    """
    from hamr.core.constants import MB_LAB_BONE_MAP
    return MB_LAB_BONE_MAP.get(vrm_name, vrm_name)


def compute_stub_position(
    bone_name: str,
    head_head: tuple[float, float, float],
    head_tail: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Compute where a stub bone should be placed relative to the head bone.

    Pure-Python function — does not require Blender.

    The head bone runs from head_head (base of head/neck top)
    to head_tail (top of skull). Stub positions are calculated
    relative to this bone's extent.

    Args:
        bone_name: VRM bone name ('jaw', 'leftEye', 'rightEye').
        head_head: (x, y, z) world position of head bone HEAD (neck top).
        head_tail: (x, y, z) world position of head bone TAIL (skull top).

    Returns:
        (x, y, z) world position for the stub bone's head (root).
    """
    # Find the stub definition
    stub_def = None
    for d in STUB_BONE_DEFS:
        if d["vrm_name"] == bone_name:
            stub_def = d
            break

    if stub_def is None:
        # Unknown bone — default to midpoint of head
        return (
            (head_head[0] + head_tail[0]) / 2.0,
            (head_head[1] + head_tail[1]) / 2.0,
            (head_head[2] + head_tail[2]) / 2.0,
        )

    # Midpoint of the head bone (approximate eye-level)
    mid_x = (head_head[0] + head_tail[0]) / 2.0
    mid_y = (head_head[1] + head_tail[1]) / 2.0
    mid_z = (head_head[2] + head_tail[2]) / 2.0

    offset = stub_def["offset_from_head"]
    return (
        mid_x + offset[0],
        mid_y + offset[1],
        mid_z + offset[2],
    )


@dataclass
class StubBoneResult:
    """Result from stub bone creation."""

    created_bones: dict[str, str]  # VRM bone name → Blender bone name
    existing_bones: list[str]  # Bones that already existed (not stubbed)
    armature_name: str


def create_missing_bones(
    armature_name: str,
    base_type: str = "mblab",
) -> StubBoneResult:
    """Create stub bones for VRM 1.0 required humanoid bones that don't
    exist in the base mesh armature.

    Must run inside Blender (bpy available).

    Strategy (AD-11.1):
    - jaw: Rooted below head bone midpoint, parented to head,
           5mm length, tagged _hamr_stub=True
    - leftEye: Rooted at left eye socket position, parented to head,
               5mm length, tagged _hamr_stub=True
    - rightEye: Rooted at right eye socket position, parented to head,
                5mm length, tagged _hamr_stub=True

    Args:
        armature_name: Name of armature object in Blender scene.
        base_type: 'mblab' or 'turbosquid' — determines vertex group
                   naming conventions for finding head/eye positions.

    Returns:
        StubBoneResult with created bone mappings and metadata.

    Raises:
        RuntimeError: If bpy is not available (not running inside Blender).
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — create_missing_bones() must run inside Blender")

    armature = bpy.data.objects.get(armature_name)
    if armature is None or armature.type != "ARMATURE":
        logger.error(f"Armature '{armature_name}' not found or not an armature")
        return StubBoneResult(
            created_bones={},
            existing_bones=[],
            armature_name=armature_name,
        )

    # Collect existing bone names
    existing_bone_names = {b.name for b in armature.data.bones}
    missing = detect_missing_bones(existing_bone_names)

    if not missing:
        logger.info(f"All {len(VRM_25_BONE_NAMES)} VRM bones present in armature — no stubs needed")
        return StubBoneResult(
            created_bones={},
            existing_bones=list(existing_bone_names),
            armature_name=armature_name,
        )

    logger.info(f"Missing VRM bones: {missing} — creating stubs")

    # Get head bone position for calculating stub positions
    head_bone = armature.data.bones.get("head")
    if head_bone is None:
        logger.error("Head bone not found — cannot position stub bones")
        return StubBoneResult(
            created_bones={},
            existing_bones=list(existing_bone_names),
            armature_name=armature_name,
        )

    # Calculate head bone positions in world space
    # Head bone HEAD is at the base (neck top), TAIL is at the top (skull top)
    head_head = _bone_head_world(armature, head_bone)
    head_tail = _bone_tail_world(armature, head_bone)

    # Switch to EDIT mode to create bones
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")

    created_bones: dict[str, str] = {}
    existing_found: list[str] = []

    for stub_def in STUB_BONE_DEFS:
        vrm_name = stub_def["vrm_name"]
        blender_name = stub_def["blender_name"]

        if vrm_name not in missing:
            # Bone already exists — skip
            existing_found.append(blender_name)
            logger.debug(f"  {vrm_name} already exists as '{blender_name}' — skipping")
            continue

        # Compute position
        pos = compute_stub_position(vrm_name, head_head, head_tail)
        bone_length = stub_def.get("length", 0.005)

        # Create the stub bone in edit mode
        edit_bone = armature.data.edit_bones.new(blender_name)

        # Position: head at computed position, tail offset slightly along local Y (forward)
        edit_bone.head = (pos[0], pos[1], pos[2])
        # Tail extends forward (Y+) from head by bone_length
        edit_bone.tail = (pos[0], pos[1] + bone_length, pos[2])

        # Parent to head bone
        parent_bone_name = stub_def["parent"]
        parent_edit_bone = armature.data.edit_bones.get(parent_bone_name)
        if parent_edit_bone is not None:
            edit_bone.parent = parent_edit_bone
        else:
            logger.warning(f"  Parent bone '{parent_bone_name}' not found for {blender_name}")

        logger.debug(f"  Created stub: {blender_name} at ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

        created_bones[vrm_name] = blender_name

    # Switch back to OBJECT mode
    bpy.ops.object.mode_set(mode="OBJECT")

    # Tag created bones with custom property
    for vrm_name, blender_name in created_bones.items():
        pose_bone = armature.pose.bones.get(blender_name)
        if pose_bone is not None:
            pose_bone["_hamr_stub"] = True
            logger.debug(f"  Tagged {blender_name} as _hamr_stub")
        else:
            # Try the data bone
            data_bone = armature.data.bones.get(blender_name)
            if data_bone is not None:
                data_bone["_hamr_stub"] = True

    logger.info(
        f"Created {len(created_bones)} stub bones: "
        f"{list(created_bones.keys())}"
    )

    return StubBoneResult(
        created_bones=created_bones,
        existing_bones=existing_found + [b for b in existing_bone_names if b not in created_bones.values()],
        armature_name=armature_name,
    )


def _bone_head_world(
    armature: Any, bone: Any
) -> tuple[float, float, float]:
    """Get bone head position in world space."""
    # Bone head in local space, transformed by armature matrix
    head_local = bone.head_local
    if head_local is not None:
        return tuple(head_local)  # type: ignore[return-value]
    # Fallback: multiply by armature matrix
    arm_matrix = armature.matrix_world
    return tuple(arm_matrix @ bone.head_local)  # type: ignore[return-value]


def _bone_tail_world(
    armature: Any, bone: Any
) -> tuple[float, float, float]:
    """Get bone tail position in world space."""
    tail_local = bone.tail_local
    if tail_local is not None:
        return tuple(tail_local)  # type: ignore[return-value]
    arm_matrix = armature.matrix_world
    return tuple(arm_matrix @ bone.tail_local)  # type: ignore[return-value]


def find_vertex_center(
    mesh_obj: Any,
    vertex_group_name: str,
) -> tuple[float, float, float]:
    """Find the center position of vertices in a named vertex group.

    Used to position stub bones accurately on the mesh.

    Args:
        mesh_obj: Blender mesh object.
        vertex_group_name: Name of vertex group to find center of.

    Returns:
        (x, y, z) world-space coordinates of the vertex group center.

    Raises:
        RuntimeError: If bpy is not available.
        ValueError: If vertex group not found on mesh.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — find_vertex_center() must run inside Blender")

    # Find the vertex group
    vgroup = None
    for vg in mesh_obj.vertex_groups:
        if vg.name == vertex_group_name:
            vgroup = vg
            break

    if vgroup is None:
        raise ValueError(f"Vertex group '{vertex_group_name}' not found on '{mesh_obj.name}'")

    # Get world matrix for coordinate transformation
    world_matrix = mesh_obj.matrix_world

    # Sum positions of all vertices in this group
    total_x, total_y, total_z = 0.0, 0.0, 0.0
    count = 0

    for vert in mesh_obj.data.vertices:
        for group in vert.groups:
            if group.group == vgroup.index:
                # Transform vertex to world space
                world_pos = world_matrix @ vert.co
                total_x += world_pos.x
                total_y += world_pos.y
                total_z += world_pos.z
                count += 1
                break

    if count == 0:
        raise ValueError(f"No vertices found in vertex group '{vertex_group_name}'")

    return (total_x / count, total_y / count, total_z / count)


def get_stub_bone_map() -> dict[str, str]:
    """Return the VRM name → Blender bone name mapping for all stub bones.

    Pure-Python function — does not require Blender.

    This is used to merge stub bone entries into the main bone map
    for VRM export.
    """
    return {d["vrm_name"]: d["blender_name"] for d in STUB_BONE_DEFS}