"""
First-Person Annotations — VRM 1.0 first-person view configuration.

In VR, you don't want to see the inside of your own face.
This module configures which meshes hide in first-person view
and which bone to anchor the camera to.

VRM 1.0 specifies per-mesh annotations:
  - "auto"           → VRM runtime decides
  - "both"           → Visible in both first and third person
  - "thirdPersonOnly" → Hidden in first-person (most body meshes)
  - "firstPersonOnly" → Visible only in first-person (e.g., simplified body)

Phase 11 (Alvíssmál): The forge knows what you should and shouldn't see.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from hamr.core.constants import VRM_25_BONE_NAMES

logger = logging.getLogger("hamr.export.first_person")

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None
    BLENDER_AVAILABLE = False


# ──────────────────────────────────────────────────────────────
# First-person annotation modes (VRM 1.0 spec)
# ──────────────────────────────────────────────────────────────

FP_AUTO = "auto"
FP_BOTH = "both"
FP_THIRD_PERSON_ONLY = "thirdPersonOnly"
FP_FIRST_PERSON_ONLY = "firstPersonOnly"

VALID_FP_ANNOTATIONS = {FP_AUTO, FP_BOTH, FP_THIRD_PERSON_ONLY, FP_FIRST_PERSON_ONLY}

# Mesh name patterns that should ALWAYS be third-person-only
# (head, face, hair — everything attached to or near the head)
THIRD_PERSON_ONLY_PATTERNS: list[str] = [
    "head",
    "face",
    "hair",
    "eye",
    "iris",
    "brow",
    "mouth",
    "teeth",
    "tongue",
    "nose",
    "ear",
    "horn",
    "antenna",
    "eyebrow",
]

# Mesh name patterns that should be visible in both views
# (body, hands, torso — essential geometry)
BOTH_VIEW_PATTERNS: list[str] = [
    "body",
    "torso",
    "hand",
    "arm",
    "leg",
    "foot",
    "clothes",
    "dress",
    "shirt",
    "pants",
    "skirt",
    "jacket",
]

# Mesh name patterns for first-person-only simplified meshes
FIRST_PERSON_ONLY_PATTERNS: list[str] = [
    "fp_body",
    "first_person_body",
    "fp_head",
    "fp_torso",
    "body_fp",
]


@dataclass
class FirstPersonConfig:
    """VRM 1.0 first-person annotation configuration.

    Defines which bone the camera anchors to during VR first-person view,
    and which meshes are visible/hidden in that view.
    """

    first_person_bone: str = "head"
    first_person_bone_offset: tuple[float, float, float] = (0.0, 0.06, 0.0)
    mesh_annotations: dict[str, str] = field(default_factory=dict)  # mesh_name → annotation
    render_body_from_first_person: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to VRM-compatible dict."""
        return {
            "first_person_bone": self.first_person_bone,
            "first_person_bone_offset": list(self.first_person_bone_offset),
            "mesh_annotations": dict(self.mesh_annotations),
            "render_body_from_first_person": self.render_body_from_first_person,
        }

    def validate(self) -> list[str]:
        """Validate the configuration, returning any errors.

        Returns:
            List of error strings. Empty list means valid config.
        """
        errors = []

        # Validate first person bone
        if not self.first_person_bone:
            errors.append("first_person_bone must not be empty")

        # Validate offset range (sanity check — should be small offsets in meters)
        for i, val in enumerate(self.first_person_bone_offset):
            if abs(val) > 1.0:
                errors.append(
                    f"first_person_bone_offset[{i}] = {val} is suspiciously large "
                    f"(offset should be in meters, typically <0.1)"
                )

        # Validate mesh annotations
        for mesh_name, annotation in self.mesh_annotations.items():
            if annotation not in VALID_FP_ANNOTATIONS:
                errors.append(
                    f"Invalid annotation '{annotation}' for mesh '{mesh_name}'. "
                    f"Must be one of: {sorted(VALID_FP_ANNOTATIONS)}"
                )

        return errors


# ──────────────────────────────────────────────────────────────
# Pure-Python configuration
# ──────────────────────────────────────────────────────────────

def classify_mesh_for_fp(mesh_name: str) -> str:
    """Classify a mesh name to a first-person annotation mode.

    Uses pattern matching on the mesh name to decide whether it should
    be visible in first-person view, hidden, or let the runtime decide.

    Args:
        mesh_name: Name of the mesh object.

    Returns:
        One of FP_AUTO, FP_BOTH, FP_THIRD_PERSON_ONLY, FP_FIRST_PERSON_ONLY.
    """
    name_lower = mesh_name.lower()

    # Check first-person-only patterns first (most specific)
    for pattern in FIRST_PERSON_ONLY_PATTERNS:
        if pattern in name_lower:
            return FP_FIRST_PERSON_ONLY

    # Head/face meshes must be hidden in first-person
    for pattern in THIRD_PERSON_ONLY_PATTERNS:
        if pattern in name_lower:
            return FP_THIRD_PERSON_ONLY

    # Body and clothing meshes generally visible in both
    for pattern in BOTH_VIEW_PATTERNS:
        if pattern in name_lower:
            return FP_BOTH

    # Default: let the runtime decide
    return FP_AUTO


def configure_first_person_pure(
    body_name: str = "",
    clothing_names: list[str] | None = None,
) -> FirstPersonConfig:
    """Configure first-person annotations using pure Python logic.

    Given the body mesh name and clothing mesh names, classifies each mesh
    into the appropriate first-person annotation mode.

    Args:
        body_name: Name of the main body mesh (without extension).
        clothing_names: List of clothing/accessory mesh names.

    Returns:
        FirstPersonConfig with all mesh annotations classified.
    """
    annotations: dict[str, str] = {}

    # Classify the body mesh
    if body_name:
        annotations[body_name] = classify_mesh_for_fp(body_name)

    # Classify clothing meshes
    if clothing_names:
        for name in clothing_names:
            annotations[name] = classify_mesh_for_fp(name)

    config = FirstPersonConfig(
        first_person_bone="head",
        first_person_bone_offset=(0.0, 0.06, 0.0),
        mesh_annotations=annotations,
        render_body_from_first_person=True,
    )

    # Validate and warn
    errors = config.validate()
    for error in errors:
        logger.warning(f"First-person config validation: {error}")

    return config


# ──────────────────────────────────────────────────────────────
# Blender-dependent configuration
# ──────────────────────────────────────────────────────────────

def configure_first_person(
    armature_name: str,
    mesh_names: list[str],
) -> FirstPersonConfig:
    """Configure first-person annotations from Blender scene data.

    Scans the given meshes in the Blender scene and classifies them for
    first-person visibility. Also sets the first-person bone offset from
    the head bone position in the armature.

    Args:
        armature_name: Name of the armature object.
        mesh_names: List of mesh object names to annotate.

    Returns:
        FirstPersonConfig with mesh annotations and bone offset.

    Raises:
        RuntimeError: If bpy is not available.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — must run inside Blender")

    annotations: dict[str, str] = {}

    # Classify each mesh
    for mesh_name in mesh_names:
        obj = bpy.data.objects.get(mesh_name)
        if obj is not None and obj.type == "MESH":
            # Use the mesh name for classification
            # Strip Blender suffixes like .001
            clean_name = mesh_name.split(".")[0]
            annotations[mesh_name] = classify_mesh_for_fp(clean_name)

    # Get head bone offset from armature
    offset = (0.0, 0.06, 0.0)  # Default: 6cm forward from head bone
    armature = bpy.data.objects.get(armature_name)
    if armature is not None and armature.type == "ARMATURE":
        bones = armature.data.bones
        head_bone = bones.get("head") or bones.get("Head")
        if head_bone is not None:
            # Use the head bone's head position for Y offset
            head_pos = head_bone.head_local
            offset = (0.0, round(head_pos[0], 4), 0.06)

    config = FirstPersonConfig(
        first_person_bone="head",
        first_person_bone_offset=offset,
        mesh_annotations=annotations,
        render_body_from_first_person=True,
    )

    # Apply to VRM extension
    armature = bpy.data.objects.get(armature_name)
    if armature is not None:
        vrm_ext = armature.vrm_addon_extension
        if hasattr(vrm_ext, "vrm1"):
            fp = vrm_ext.vrm1.first_person
            # Set first-person bone
            if hasattr(fp, "first_person_bone"):
                fp.first_person_bone.bone_name = config.first_person_bone
            if hasattr(fp, "first_person_bone_offset"):
                fp.first_person_bone_offset[0] = config.first_person_bone_offset[0]
                fp.first_person_bone_offset[1] = config.first_person_bone_offset[1]
                fp.first_person_bone_offset[2] = config.first_person_bone_offset[2]

            # Set mesh annotations
            if hasattr(fp, "mesh_annotations"):
                fp.mesh_annotations.clear()
                for mesh_name, annotation in config.mesh_annotations.items():
                    ann = fp.mesh_annotations.add()
                    ann.node.mesh_object_name = mesh_name
                    ann.type = annotation

    logger.info(
        f"First-person config applied: {len(annotations)} meshes annotated "
        f"on {armature_name}"
    )
    return config