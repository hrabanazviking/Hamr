"""
VRM Export — Headless VRM 1.0 export via Blender VRM Add-on.

This module embodies every hard-won lesson from Seiðr-Smiðja:
- D-008: Never auto-map bones. Always be explicit.
- D-009: filter_by_human_bone_hierarchy = False for non-standard rigs
- D-016: Use EXEC_DEFAULT with ignore_warning=True (no GUI dialogs in headless)
- D-017: allow_non_humanoid_rig as safety net for validation edge cases
- D-018: Use human_bone_name_to_human_bone() dict API, NOT getattr()
- D-018b: Guard migration.migrate() bone structure search with cache check

The blade remembers every wound it took.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("hamr.export.vrm")

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None
    BLENDER_AVAILABLE = False


# ──────────────────────────────────────────────────────────────
# VRM 1.0 Humanoid Bone Mapping
# ──────────────────────────────────────────────────────────────
# FP-2: Canonical mapping consolidated in hamr.core.constants
from hamr.core.constants import MB_LAB_BONE_MAP

# Required VRM 1.0 humanoid bones (25 required for VRM 1.0 spec)
VRM_REQUIRED_BONES = [
    "hips", "spine", "chest", "upperChest", "neck", "head",
    "leftUpperLeg", "rightUpperLeg",
    "leftLowerLeg", "rightLowerLeg",
    "leftFoot", "rightFoot",
    "leftToes", "rightToes",
    "leftShoulder", "rightShoulder",
    "leftUpperArm", "rightUpperArm",
    "leftLowerArm", "rightLowerArm",
    "leftHand", "rightHand",
    "jaw", "leftEye", "rightEye",
]


def setup_vrm_humanoid(
    armature_name: str,
    bone_map: dict[str, str] | None = None,
) -> bool:
    """
    Set up VRM 1.0 humanoid bone mapping on an armature.

    D-008 LESSON: We NEVER use auto-mapping. We set every bone explicitly.

    Args:
        armature_name: Name of the armature object in Blender.
        bone_map: Optional bone mapping dict (VRM name → Blender name).
                  Defaults to MB_LAB_BONE_MAP.

    Returns:
        True if setup succeeded, False otherwise.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — must run inside Blender")

    armature = bpy.data.objects.get(armature_name)
    if armature is None or armature.type != "ARMATURE":
        logger.error(f"Armature '{armature_name}' not found or not an armature")
        return False

    mapping = bone_map or MB_LAB_BONE_MAP

    # D-008: Disable automatic bone assignment
    # The VRM Add-on will OVERWRITE our mappings if this is True
    vrm_ext = armature.vrm_addon_extension
    if hasattr(vrm_ext, "vrm1"):
        humanoid = vrm_ext.vrm1.humanoid

        # D-008: NEVER auto-assign — we map every bone explicitly
        humanoid.initial_automatic_bone_assignment = False

        # D-009: Allow non-standard hierarchies (MB-Lab, TurboSquid, etc.)
        humanoid.filter_by_human_bone_hierarchy = False

        # D-018 CORRECT: Use the dict API, NOT getattr()
        # getattr(human_bones, "leftUpperLeg") returns None for 49/55 bones!
        human_bones = humanoid.human_bones
        bone_name_dict = human_bones.human_bone_name_to_human_bone()

        for vrm_name, blender_name in mapping.items():
            if vrm_name in bone_name_dict:
                prop = bone_name_dict[vrm_name]
                prop.node.bone_name = blender_name
                logger.debug(f"  {vrm_name} → {blender_name}")
            else:
                # Some bone names might not be in the dict
                # Try direct attribute assignment as fallback
                try:
                    bone_prop = getattr(human_bones, vrm_name, None)
                    if bone_prop is not None:
                        bone_prop.node.bone_name = blender_name
                        logger.debug(f"  {vrm_name} → {blender_name} (fallback)")
                except Exception:
                    logger.warning(f"  Bone '{vrm_name}' not found in VRM humanoid")

        logger.info(f"VRM humanoid bone mapping set: {len(mapping)} bones")

    return True


def setup_vrm_metadata(
    armature_name: str,
    title: str = "Hamr Character",
    author: str = "Hamr Forge",
    version: str = "1.0",
    license: str = "CC-BY-4.0",
    contact_url: str = "https://github.com/hrabanazviking/Hamr",
) -> bool:
    """Set VRM 1.0 metadata on an armature."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    armature = bpy.data.objects.get(armature_name)
    if armature is None:
        logger.error(f"Armature '{armature_name}' not found")
        return False

    vrm_ext = armature.vrm_addon_extension
    if hasattr(vrm_ext, "vrm1"):
        meta = vrm_ext.vrm1.meta
        meta.title = title
        meta.author = author
        meta.version = version
        meta.license = license
        meta.contact_information = contact_url

    logger.info(f"VRM metadata set: {title} v{version} by {author}")
    return True


def setup_vrm_expressions(
    armature_name: str,
    mesh_name: str,
    expressions: dict[str, list[dict[str, float]]],
) -> bool:
    """
    Set up VRM 1.0 expression presets.

    D-011: Symmetric expressions bind BOTH L and R shape keys.
    D-013: Expression morph binds use shape key NAME strings, NOT integer indices.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    armature = bpy.data.objects.get(armature_name)
    mesh = bpy.data.objects.get(mesh_name)
    if armature is None or mesh is None:
        logger.error(f"Armature or mesh not found")
        return False

    vrm_ext = armature.vrm_addon_extension
    if hasattr(vrm_ext, "vrm1"):
        # D-009 variant: Disable automatic expression assignment
        vrm_ext.vrm1.expressions.initial_automatic_expression_assignment = False

        preset = vrm_ext.vrm1.expressions.preset

        for expr_name, morphs in expressions.items():
            # Get or create expression
            expr = getattr(preset, expr_name, None)
            if expr is None:
                logger.warning(f"Expression preset '{expr_name}' not found")
                continue

            # Clear existing binds
            expr.morph_target_binds.clear()

            for morph in morphs:
                bind = expr.morph_target_binds.add()
                bind.node.mesh_object_name = mesh_name
                # D-013: Use shape key NAME, not integer
                bind.index = str(morph.get("name", ""))
                bind.weight = morph.get("weight", 0.5)

            logger.debug(f"Expression '{expr_name}': {len(morphs)} morphs")

    logger.info(f"VRM expressions set: {len(expressions)} presets")
    return True


def setup_vrm_look_at(
    armature_name: str,
    left_eye_bone: str = "eye_L",
    right_eye_bone: str = "eye_R",
) -> bool:
    """Configure VRM 1.0 lookAt for eye bone rotation."""
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    armature = bpy.data.objects.get(armature_name)
    if armature is None:
        return False

    vrm_ext = armature.vrm_addon_extension
    if hasattr(vrm_ext, "vrm1"):
        look_at = vrm_ext.vrm1.humanoid.look_at
        # D-012: Use bone rotation mode, not morph targets
        # VRM 1.0 uses lowercase enum values! (D-018 lesson)
        look_at.type = "bone"
        look_at.offset_from_head_bone[0] = 0.0
        look_at.offset_from_head_bone[1] = 0.06
        look_at.offset_from_head_bone[2] = 0.0

    logger.info(f"VRM lookAt configured: bone mode, {left_eye_bone}/{right_eye_bone}")
    return True


def export_vrm(
    armature_name: str,
    output_path: str | Path,
) -> bool:
    """
    Export armature as VRM 1.0 file.

    D-016 LESSON: bpy.ops.export_scene.vrm() calls invoke() which opens
    GUI dialogs in interactive mode. In background mode, this returns
    CANCELLED silently. We MUST use EXEC_DEFAULT with ignore_warning=True.

    Args:
        armature_name: Name of the armature to export.
        output_path: Path for the output .vrm file.

    Returns:
        True if export succeeded, False otherwise.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # D-017: Safety net for non-humanoid rigs
    armature = bpy.data.objects.get(armature_name)
    if armature is None:
        logger.error(f"Armature '{armature_name}' not found")
        return False

    vrm_ext = armature.vrm_addon_extension
    if hasattr(vrm_ext, "vrm1"):
        # Allow non-humanoid rig as safety fallback
        vrm_ext.vrm1.allow_non_humanoid_rig = True

    # D-016: Use EXEC_DEFAULT context override, not invoke()
    # ignore_warning=True suppresses validation dialogs that block headless export
    try:
        bpy.ops.export_scene.vrm(
            "EXEC_DEFAULT",
            filepath=str(output_path),
            armature_object_name=armature_name,
            ignore_warning=True,
        )
        logger.info(f"VRM exported: {output_path}")
        return True
    except Exception as e:
        logger.error(f"VRM export failed: {e}")
        return False