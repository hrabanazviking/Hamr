"""
Animation Preset Clips — VRM avatar animation presets.

Phase 13 (T4): Idle breathe, weight shift, look around, walk cycle reference.

Animation clips in VRM are stored as glTF Animation nodes with channels
targeting bone properties. These are NOT baked mesh animations — they are
bone rotation/position/scale references that VRChat-compatible systems
can layer onto avatars.

All pure-Python functions avoid bpy imports for testability.
The Blender-dependent clip_to_gltf_animation() is guarded.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from hamr.core.constants import VRM_25_BONE_NAMES

logger = logging.getLogger("hamr.export.animation_clips")

try:
    import bpy  # type: ignore

    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False


# ── Data structures ──────────────────────────────────────────────


@dataclass
class AnimationKeyframe:
    """A single keyframe: time + bone + transforms.

    Attributes:
        time: Time in seconds from clip start.
        bone: VRM humanoid bone name (e.g. "spine", "head", "hips").
        position: (x, y, z) position offset in metres.
        rotation: (x, y, z) Euler XYZ rotation in degrees.
        scale: (x, y, z) scale factors (default 1, 1, 1).
    """

    time: float
    bone: str
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class AnimationClip:
    """A named animation clip with keyframes.

    Attributes:
        name: Clip identifier (e.g. "idle_breathe").
        duration: Total duration in seconds.
        fps: Frames per second for frame <-> time conversion.
        loop: Whether the clip should loop.
        keyframes: Ordered list of keyframes.
    """

    name: str
    duration: float
    fps: int = 30
    loop: bool = True
    keyframes: list[AnimationKeyframe] = field(default_factory=list)


# ── Valid bone names ──────────────────────────────────────────────

# VRM 25 required bones + extended humanoid bones (finger bones) + MB-Lab aliases
_VALID_BONE_NAMES: set[str] = set(VRM_25_BONE_NAMES) | {
    # Extended humanoid bones (fingers)
    "leftThumbMetacarpal",
    "leftThumbProximal",
    "leftThumbDistal",
    "leftIndexProximal",
    "leftIndexDistal",
    "leftMiddleProximal",
    "leftMiddleDistal",
    "leftRingProximal",
    "leftRingDistal",
    "leftLittleProximal",
    "leftLittleDistal",
    "rightThumbMetacarpal",
    "rightThumbProximal",
    "rightThumbDistal",
    "rightIndexProximal",
    "rightIndexDistal",
    "rightMiddleProximal",
    "rightMiddleDistal",
    "rightRingProximal",
    "rightRingDistal",
    "rightLittleProximal",
    "rightLittleDistal",
    # MB-Lab Blender bone name aliases
    "pelvis",
    "spine_01",
    "spine_02",
    "clavicle_L",
    "clavicle_R",
    "upper_arm_L",
    "upper_arm_R",
    "forearm_L",
    "forearm_R",
    "hand_L",
    "hand_R",
    "thigh_L",
    "thigh_R",
    "shin_L",
    "shin_R",
    "foot_L",
    "foot_R",
    "toe_L",
    "toe_R",
}

# MB-Lab alias → VRM canonical name mapping
MB_LAB_TO_VRM: dict[str, str] = {
    "pelvis": "hips",
    "spine_01": "chest",
    "spine_02": "upperChest",
    "clavicle_L": "leftShoulder",
    "clavicle_R": "rightShoulder",
    "upper_arm_L": "leftUpperArm",
    "upper_arm_R": "rightUpperArm",
    "forearm_L": "leftLowerArm",
    "forearm_R": "rightLowerArm",
    "hand_L": "leftHand",
    "hand_R": "rightHand",
    "thigh_L": "leftUpperLeg",
    "thigh_R": "rightUpperLeg",
    "shin_L": "leftLowerLeg",
    "shin_R": "rightLowerLeg",
    "foot_L": "leftFoot",
    "foot_R": "rightFoot",
    "toe_L": "leftToes",
    "toe_R": "rightToes",
}


# ── Preset clip builders ─────────────────────────────────────────


def _build_idle_breathe() -> AnimationClip:
    """Gentle breathing cycle (2.5s).

    Spine subtle Y scale (inhale expand, exhale contract),
    head slight nod down on exhale.
    """
    return AnimationClip(
        name="idle_breathe",
        duration=2.5,
        fps=30,
        loop=True,
        keyframes=[
            # T=0: rest pose
            AnimationKeyframe(
                time=0.0, bone="spine", scale=(1.0, 1.0, 1.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
            # T=1.25: peak inhale — spine Y scale up, head slight nod
            AnimationKeyframe(
                time=1.25, bone="spine", scale=(1.0, 1.02, 1.0)
            ),
            AnimationKeyframe(
                time=1.25, bone="head", rotation=(-2.0, 0.0, 0.0)
            ),
            # T=2.5: return to rest
            AnimationKeyframe(
                time=2.5, bone="spine", scale=(1.0, 1.0, 1.0)
            ),
            AnimationKeyframe(
                time=2.5, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
        ],
    )


def _build_idle_shift_weight() -> AnimationClip:
    """Weight shift cycle (4s).

    Hips slight X/Z rotation (lean left/right),
    spine counter-rotates to keep head stable.
    """
    return AnimationClip(
        name="idle_shift_weight",
        duration=4.0,
        fps=30,
        loop=True,
        keyframes=[
            # T=0: rest pose
            AnimationKeyframe(
                time=0.0, bone="hips", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="spine", rotation=(0.0, 0.0, 0.0)
            ),
            # T=2: lean left — hips rotate Z-, spine counter Z+
            AnimationKeyframe(
                time=2.0, bone="hips", rotation=(-1.0, 0.0, -2.0)
            ),
            AnimationKeyframe(
                time=2.0, bone="spine", rotation=(0.0, 0.0, 1.5)
            ),
            # T=4: return to rest
            AnimationKeyframe(
                time=4.0, bone="hips", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=4.0, bone="spine", rotation=(0.0, 0.0, 0.0)
            ),
        ],
    )


def _build_idle_look_around() -> AnimationClip:
    """Head turn cycle (6s).

    Neck/head Y rotation sweeps from center → left (+15°)
    → center → right (-15°) → center.
    """
    return AnimationClip(
        name="idle_look_around",
        duration=6.0,
        fps=30,
        loop=True,
        keyframes=[
            # T=0: center
            AnimationKeyframe(
                time=0.0, bone="neck", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
            # T=1.5: look left (Y +15°)
            AnimationKeyframe(
                time=1.5, bone="neck", rotation=(0.0, 15.0, 0.0)
            ),
            AnimationKeyframe(
                time=1.5, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
            # T=3.0: center
            AnimationKeyframe(
                time=3.0, bone="neck", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=3.0, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
            # T=4.5: look right (Y -15°)
            AnimationKeyframe(
                time=4.5, bone="neck", rotation=(0.0, -15.0, 0.0)
            ),
            AnimationKeyframe(
                time=4.5, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
            # T=6.0: center
            AnimationKeyframe(
                time=6.0, bone="neck", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=6.0, bone="head", rotation=(0.0, 0.0, 0.0)
            ),
        ],
    )


def _build_walk_cycle_ref() -> AnimationClip:
    """Reference walk keyframes (0.8s).

    Hip bounce (Y position), arm swing (X rotation),
    leg alternation (X rotation).
    """
    return AnimationClip(
        name="walk_cycle_ref",
        duration=0.8,
        fps=30,
        loop=True,
        keyframes=[
            # ── T=0: left contact (left leg forward, right leg back) ──
            AnimationKeyframe(
                time=0.0,
                bone="hips",
                position=(0.0, 0.02, 0.0),
                rotation=(0.0, 0.0, 0.0),
            ),
            AnimationKeyframe(
                time=0.0, bone="leftUpperLeg", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="rightUpperLeg", rotation=(-20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="leftLowerLeg", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="rightLowerLeg", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="leftUpperArm", rotation=(-20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.0, bone="rightUpperArm", rotation=(30.0, 0.0, 0.0)
            ),
            # ── T=0.2: passing — legs vertical, hips at lowest ──
            AnimationKeyframe(
                time=0.2,
                bone="hips",
                position=(0.0, 0.0, 0.0),
                rotation=(0.0, 0.0, 0.0),
            ),
            AnimationKeyframe(
                time=0.2, bone="leftUpperLeg", rotation=(10.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.2, bone="rightUpperLeg", rotation=(10.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.2, bone="leftLowerLeg", rotation=(20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.2, bone="rightLowerLeg", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.2, bone="leftUpperArm", rotation=(10.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.2, bone="rightUpperArm", rotation=(-10.0, 0.0, 0.0)
            ),
            # ── T=0.4: right contact (right leg forward, left leg back) ──
            AnimationKeyframe(
                time=0.4,
                bone="hips",
                position=(0.0, 0.02, 0.0),
                rotation=(0.0, 0.0, 0.0),
            ),
            AnimationKeyframe(
                time=0.4, bone="leftUpperLeg", rotation=(-20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.4, bone="rightUpperLeg", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.4, bone="leftLowerLeg", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.4, bone="rightLowerLeg", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.4, bone="leftUpperArm", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.4, bone="rightUpperArm", rotation=(-20.0, 0.0, 0.0)
            ),
            # ── T=0.6: passing opposite ──
            AnimationKeyframe(
                time=0.6,
                bone="hips",
                position=(0.0, 0.0, 0.0),
                rotation=(0.0, 0.0, 0.0),
            ),
            AnimationKeyframe(
                time=0.6, bone="leftUpperLeg", rotation=(10.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.6, bone="rightUpperLeg", rotation=(10.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.6, bone="leftLowerLeg", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.6, bone="rightLowerLeg", rotation=(20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.6, bone="leftUpperArm", rotation=(-10.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.6, bone="rightUpperArm", rotation=(10.0, 0.0, 0.0)
            ),
            # ── T=0.8: return to start (loop point) ──
            AnimationKeyframe(
                time=0.8,
                bone="hips",
                position=(0.0, 0.02, 0.0),
                rotation=(0.0, 0.0, 0.0),
            ),
            AnimationKeyframe(
                time=0.8, bone="leftUpperLeg", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.8, bone="rightUpperLeg", rotation=(-20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.8, bone="leftLowerLeg", rotation=(0.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.8, bone="rightLowerLeg", rotation=(30.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.8, bone="leftUpperArm", rotation=(-20.0, 0.0, 0.0)
            ),
            AnimationKeyframe(
                time=0.8, bone="rightUpperArm", rotation=(30.0, 0.0, 0.0)
            ),
        ],
    )


# ── Build preset dict ────────────────────────────────────────────

PRESET_CLIPS: dict[str, AnimationClip] = {
    "idle_breathe": _build_idle_breathe(),
    "idle_shift_weight": _build_idle_shift_weight(),
    "idle_look_around": _build_idle_look_around(),
    "walk_cycle_ref": _build_walk_cycle_ref(),
}


# ── Convenience functions (pure-Python, no bpy) ───────────────────


def create_keyframe(
    time: float,
    bone: str,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> AnimationKeyframe:
    """Create an AnimationKeyframe with spec-convention argument order.

    The task spec puts rotation before position to match common animation
    tool conventions where rotation is the most frequently animated property.

    Args:
        time: Time in seconds from clip start.
        bone: VRM humanoid bone name.
        rotation: Euler XYZ rotation in degrees.
        position: (x, y, z) position offset in metres.
        scale: (x, y, z) scale factors.

    Returns:
        AnimationKeyframe instance.
    """
    return AnimationKeyframe(
        time=time,
        bone=bone,
        position=position,
        rotation=rotation,
        scale=scale,
    )


def create_clip(
    name: str,
    duration: float,
    fps: int = 30,
    loop: bool = True,
) -> AnimationClip:
    """Create an empty AnimationClip (no keyframes).

    Args:
        name: Clip name/identifier.
        duration: Total duration in seconds.
        fps: Frames per second (default 30).
        loop: Whether the clip loops (default True).

    Returns:
        AnimationClip with empty keyframes list.
    """
    return AnimationClip(
        name=name,
        duration=duration,
        fps=fps,
        loop=loop,
        keyframes=[],
    )


def validate_clip(clip: AnimationClip) -> list[str]:
    """Validate an AnimationClip for common errors.

    Checks:
    - Duration is positive
    - Keyframe times are within [0, duration]
    - Bone names are valid VRM humanoid bones or MB-Lab aliases

    Args:
        clip: AnimationClip to validate.

    Returns:
        List of warning/error messages. Empty list means the clip is valid.
    """
    warnings: list[str] = []

    if clip.duration <= 0:
        warnings.append(
            f"Clip '{clip.name}' has non-positive duration: {clip.duration}"
        )

    for kf in clip.keyframes:
        # Check time range
        if kf.time < 0:
            warnings.append(
                f"Clip '{clip.name}': keyframe for bone '{kf.bone}' "
                f"has negative time {kf.time}"
            )
        elif kf.time > clip.duration:
            warnings.append(
                f"Clip '{clip.name}': keyframe for bone '{kf.bone}' "
                f"at time {kf.time} exceeds duration {clip.duration}"
            )

        # Check bone name
        if kf.bone not in _VALID_BONE_NAMES:
            warnings.append(
                f"Clip '{clip.name}': unknown bone name '{kf.bone}' "
                f"(not in VRM humanoid bones or MB-Lab aliases)"
            )

    return warnings


def keyframes_to_dict(clip: AnimationClip) -> dict[str, Any]:
    """Convert an AnimationClip to a glTF animation dict structure.

    Produces a structured JSON-compatible dict following the glTF 2.0
    animation schema layout. This is a pure-Python representation;
    the Blender-dependent clip_to_gltf_animation() resolves bone names
    to node indices and creates actual glTF binary data.

    Output structure::

        {
            "name": <clip name>,
            "channels": [
                {
                    "sampler": <index>,
                    "target": {
                        "node": <bone name or index>,
                        "path": "rotation" | "translation" | "scale"
                    }
                },
                ...
            ],
            "samplers": [
                {
                    "input": <accessor ref for time>,
                    "output": <accessor ref for value>,
                    "interpolation": "LINEAR"
                },
                ...
            ],
            "keyframe_data": {
                "<bone>": {
                    "times": [0.0, 1.25, 2.5],
                    "rotations_euler_deg": [[x, y, z], ...],
                    "positions": [[x, y, z], ...],
                    "scales": [[x, y, z], ...],
                },
                ...
            },
            "duration": <float>,
            "fps": <int>,
            "loop": <bool>,
        }

    Args:
        clip: AnimationClip to convert.

    Returns:
        Dict with glTF animation structure.
    """
    # Group keyframes by bone
    bone_channels: dict[str, dict[str, Any]] = {}

    for kf in clip.keyframes:
        if kf.bone not in bone_channels:
            bone_channels[kf.bone] = {
                "times": [],
                "rotations_euler_deg": [],
                "positions": [],
                "scales": [],
            }

        channel = bone_channels[kf.bone]
        if kf.time not in channel["times"]:
            channel["times"].append(kf.time)
        channel["rotations_euler_deg"].append(list(kf.rotation))
        channel["positions"].append(list(kf.position))
        channel["scales"].append(list(kf.scale))

    # Build glTF channels and samplers
    # Only emit channels for properties that have non-default values
    channels: list[dict[str, Any]] = []
    samplers: list[dict[str, Any]] = []
    sampler_index = 0

    # glTF property paths and corresponding data keys
    property_paths: list[tuple[str, str, list[float]]] = [
        ("rotation", "rotations_euler_deg", [0.0, 0.0, 0.0]),
        ("translation", "positions", [0.0, 0.0, 0.0]),
        ("scale", "scales", [1.0, 1.0, 1.0]),
    ]

    for bone_name, bone_data in bone_channels.items():
        for path, data_key, default in property_paths:
            data = bone_data[data_key]
            # Include channel if ANY keyframe has a non-default value
            has_non_default = any(v != default for v in data)
            if not has_non_default:
                continue

            channels.append(
                {
                    "sampler": sampler_index,
                    "target": {
                        "node": bone_name,  # Resolved to index later
                        "path": path,
                    },
                }
            )
            samplers.append(
                {
                    "input": f"accessor_{bone_name}_{path}_time",
                    "output": f"accessor_{bone_name}_{path}_value",
                    "interpolation": "LINEAR",
                }
            )
            sampler_index += 1

    return {
        "name": clip.name,
        "channels": channels,
        "samplers": samplers,
        "keyframe_data": bone_channels,
        "duration": clip.duration,
        "fps": clip.fps,
        "loop": clip.loop,
    }


def get_preset_clips() -> dict[str, AnimationClip]:
    """Return all preset animation clips.

    Returns:
        Dict mapping clip name to AnimationClip instance.
    """
    return dict(PRESET_CLIPS)


# ── Blender-dependent functions ──────────────────────────────────


def clip_to_gltf_animation(
    clip: AnimationClip,
    armature_name: str,
) -> dict[str, Any]:
    """Convert an AnimationClip to a glTF animation data structure.

    Creates the glTF animation channels targeting bones in the given
    armature. This function must run inside Blender and requires the
    armature to exist in the current scene.

    Args:
        clip: AnimationClip to convert.
        armature_name: Name of the armature object in Blender.

    Returns:
        glTF animation dict with channels, samplers, and data.
        Node references are resolved from bone names to indices.

    Raises:
        RuntimeError: If bpy is not available.
        ValueError: If armature not found or not an armature.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError(
            "bpy not available — clip_to_gltf_animation() "
            "must run inside Blender"
        )

    armature = bpy.data.objects.get(armature_name)
    if armature is None or armature.type != "ARMATURE":
        raise ValueError(
            f"Armature '{armature_name}' not found or not an armature"
        )

    # Build bone name → node index mapping from the armature
    bone_to_index: dict[str, int] = {}
    for i, bone in enumerate(armature.data.bones):
        bone_to_index[bone.name] = i

    # Convert clip to dict structure first (pure-Python path)
    clip_dict = keyframes_to_dict(clip)

    # Resolve bone names to node indices in channels
    from hamr.export.vrm import MB_LAB_BONE_MAP

    for channel in clip_dict["channels"]:
        target = channel["target"]
        bone_name = target["node"]

        # Try direct lookup first, then VRM name mapping
        if bone_name in bone_to_index:
            target["node"] = bone_to_index[bone_name]
        else:
            # Try mapping VRM name to Blender name
            blender_name = MB_LAB_BONE_MAP.get(bone_name, bone_name)
            if blender_name in bone_to_index:
                target["node"] = bone_to_index[blender_name]
            else:
                logger.warning(
                    f"Bone '{bone_name}' not found in armature "
                    f"'{armature_name}'"
                )
                target["node"] = -1  # Invalid node — will be flagged

    # Convert Euler degrees to radians for quaternion conversion
    for bone_name, bone_data in clip_dict["keyframe_data"].items():
        euler_deg = bone_data["rotations_euler_deg"]
        euler_rad = [
            [math.radians(v) for v in rot] for rot in euler_deg
        ]
        bone_data["rotations_euler_rad"] = euler_rad

    logger.info(
        f"Clip '{clip.name}': {len(clip_dict['channels'])} channels, "
        f"{len(clip_dict['samplers'])} samplers"
    )

    return clip_dict