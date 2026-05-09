"""
Pose Library — Pre-defined pose presets, blending, and VRM export.

Phase 16, Task T3 — The Forge Worker shapes the figure at rest and in motion.

BonePose stores per-bone transforms (position, Euler XYZ rotation degrees,
scale). PosePreset groups bones with optional blend shape weights. Pre-defined
presets cover rest poses (T-pose, A-pose), hand poses, and facial presets.

All logic is pure-Python — no bpy dependency. Validation checks bone names
against VRM_HUMANOID_BONES and blend shapes against VRM_EXPRESSIONS.
"""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from hamr.core.constants import VRM_HUMANOID_BONES

try:
    import bpy  # type: ignore

    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False

logger = logging.getLogger("hamr.rigs.poses")

# ── Valid blend shape names (VRM 1.0 expressions) ────────────────────────

VALID_BLEND_SHAPES: set[str] = {
    "happy", "angry", "sad", "surprised", "neutral",
    "blink", "blinkLeft", "blinkRight",
    # Additional common blend shape names used in face poses
    "eyeSquint", "eyeClose", "eyeWide", "eyeBrowDown", "eyeBrowUp",
    "aa", "oh", "mouthOpen", "mouthSmile",
}

# Canonical bone name set for validation
VALID_BONE_NAMES: set[str] = set(VRM_HUMANOID_BONES)


# ═══════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BonePose:
    """Per-bone transform for a single bone in a pose preset.

    Attributes:
        bone_name: VRM 1.0 humanoid bone name (e.g. 'leftUpperArm').
        position: (x, y, z) offset in metres — relative to rest pose.
        rotation: Euler XYZ rotation in degrees — relative to rest pose.
        scale: (x, y, z) scale factors — default (1, 1, 1).
    """

    bone_name: str
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Euler XYZ degrees
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class PosePreset:
    """A named pose consisting of bone transforms and blend shape weights.

    Attributes:
        name: Unique pose name (e.g. 't_pose', 'hand_fist').
        category: One of 'rest', 'hand', 'face', 'body', 'action'.
        description: Human-readable description.
        bones: List of BonePose entries for each bone in the pose.
        blend_shapes: Blend shape name → weight (0.0–1.0).
    """

    name: str
    category: str  # "rest", "hand", "face", "body", "action"
    description: str = ""
    bones: list[BonePose] = field(default_factory=list)
    blend_shapes: dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-defined Pose Presets
# ═══════════════════════════════════════════════════════════════════════════════

POSE_PRESETS: dict[str, PosePreset] = {}

# ── Rest Poses ─────────────────────────────────────────────────────────────

POSE_PRESETS["t_pose"] = PosePreset(
    name="t_pose",
    category="rest",
    description="T-pose — arms extended 90° from body, standard VRM rest pose",
    bones=[
        # Spine chain — identity (upright)
        BonePose(bone_name="hips", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="spine", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="chest", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="upperChest", rotation=(0.0, 0.0, 0.0)),
        # Neck and head
        BonePose(bone_name="neck", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="head", rotation=(0.0, 0.0, 0.0)),
        # Left arm — 90° abduction (Z-axis in Blender)
        BonePose(bone_name="leftShoulder", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftUpperArm", rotation=(0.0, 0.0, 90.0)),
        BonePose(bone_name="leftLowerArm", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftHand", rotation=(0.0, 0.0, 0.0)),
        # Right arm — 90° abduction (mirrored)
        BonePose(bone_name="rightShoulder", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightUpperArm", rotation=(0.0, 0.0, -90.0)),
        BonePose(bone_name="rightLowerArm", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightHand", rotation=(0.0, 0.0, 0.0)),
        # Left leg
        BonePose(bone_name="leftUpperLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftLowerLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftFoot", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftToes", rotation=(0.0, 0.0, 0.0)),
        # Right leg
        BonePose(bone_name="rightUpperLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightLowerLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightFoot", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightToes", rotation=(0.0, 0.0, 0.0)),
        # Head details
        BonePose(bone_name="jaw", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
        # Fingers — left hand
        BonePose(bone_name="leftThumbMetacarpal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(0.0, 0.0, 0.0)),
        # Fingers — right hand
        BonePose(bone_name="rightThumbMetacarpal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["a_pose"] = PosePreset(
    name="a_pose",
    category="rest",
    description="A-pose — arms ~60° from body, more natural rest for rigging",
    bones=[
        # Spine chain — identity
        BonePose(bone_name="hips", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="spine", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="chest", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="upperChest", rotation=(0.0, 0.0, 0.0)),
        # Neck and head
        BonePose(bone_name="neck", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="head", rotation=(0.0, 0.0, 0.0)),
        # Left arm — 60° abduction
        BonePose(bone_name="leftShoulder", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftUpperArm", rotation=(0.0, 0.0, 60.0)),
        BonePose(bone_name="leftLowerArm", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftHand", rotation=(0.0, 0.0, 0.0)),
        # Right arm — 60° abduction (mirrored)
        BonePose(bone_name="rightShoulder", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightUpperArm", rotation=(0.0, 0.0, -60.0)),
        BonePose(bone_name="rightLowerArm", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightHand", rotation=(0.0, 0.0, 0.0)),
        # Legs
        BonePose(bone_name="leftUpperLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftLowerLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftFoot", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftToes", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightUpperLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightLowerLeg", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightFoot", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightToes", rotation=(0.0, 0.0, 0.0)),
        # Head details
        BonePose(bone_name="jaw", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
        # Fingers — left hand
        BonePose(bone_name="leftThumbMetacarpal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(0.0, 0.0, 0.0)),
        # Fingers — right hand
        BonePose(bone_name="rightThumbMetacarpal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

# ── Hand Poses ─────────────────────────────────────────────────────────────

POSE_PRESETS["hand_open"] = PosePreset(
    name="hand_open",
    category="hand",
    description="Open hand — fingers spread, natural relaxed open position",
    bones=[
        # Left hand fingers — slight natural spread
        BonePose(bone_name="leftThumbMetacarpal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(0.0, -15.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(0.0, -10.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(-3.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(-3.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(-8.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(-8.0, 0.0, 0.0)),
        # Right hand fingers — mirrored
        BonePose(bone_name="rightThumbMetacarpal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(0.0, 15.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(0.0, 10.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(-3.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(-3.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(-8.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(-8.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["hand_fist"] = PosePreset(
    name="hand_fist",
    category="hand",
    description="Closed fist — all fingers curled tightly",
    bones=[
        # Left hand — all fingers curled
        BonePose(bone_name="leftThumbMetacarpal", rotation=(-30.0, -15.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(-40.0, -10.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(-30.0, -5.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(-70.0, 0.0, 0.0)),
        # Right hand — mirrored
        BonePose(bone_name="rightThumbMetacarpal", rotation=(-30.0, 15.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(-40.0, 10.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(-30.0, 5.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(-70.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["hand_point"] = PosePreset(
    name="hand_point",
    category="hand",
    description="Pointing — index finger extended, others curled",
    bones=[
        # Left hand — index extended, rest curled
        BonePose(bone_name="leftThumbMetacarpal", rotation=(-20.0, -15.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(-30.0, -10.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(-70.0, 0.0, 0.0)),
        # Right hand
        BonePose(bone_name="rightThumbMetacarpal", rotation=(-20.0, 15.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(-30.0, 10.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(-70.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["hand_peace"] = PosePreset(
    name="hand_peace",
    category="hand",
    description="Peace/V sign — index and middle extended, others curled",
    bones=[
        # Left hand — index and middle extended
        BonePose(bone_name="leftThumbMetacarpal", rotation=(-20.0, -15.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(-30.0, -10.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(-70.0, 0.0, 0.0)),
        # Right hand
        BonePose(bone_name="rightThumbMetacarpal", rotation=(-20.0, 15.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(-30.0, 10.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(-5.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(-90.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(-70.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["hand_grip"] = PosePreset(
    name="hand_grip",
    category="hand",
    description="Gripping pose — fingers curled around an imaginary cylinder",
    bones=[
        # Left hand — gripping curl
        BonePose(bone_name="leftThumbMetacarpal", rotation=(-15.0, -20.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(-25.0, -15.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(-20.0, -5.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(-60.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(-45.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(-65.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(-50.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(-55.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(-75.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(-55.0, 0.0, 0.0)),
        # Right hand — mirrored grip
        BonePose(bone_name="rightThumbMetacarpal", rotation=(-15.0, 20.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(-25.0, 15.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(-20.0, 5.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(-60.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(-45.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(-65.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(-50.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(-70.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(-55.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(-75.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(-55.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["hand_relax"] = PosePreset(
    name="hand_relax",
    category="hand",
    description="Relaxed hand — natural resting curl, fingers slightly bent",
    bones=[
        # Left hand — gentle natural curl
        BonePose(bone_name="leftThumbMetacarpal", rotation=(-10.0, -10.0, 0.0)),
        BonePose(bone_name="leftThumbProximal", rotation=(-15.0, -8.0, 0.0)),
        BonePose(bone_name="leftThumbDistal", rotation=(-10.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexProximal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="leftIndexDistal", rotation=(-15.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleProximal", rotation=(-25.0, 0.0, 0.0)),
        BonePose(bone_name="leftMiddleDistal", rotation=(-15.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingProximal", rotation=(-30.0, 0.0, 0.0)),
        BonePose(bone_name="leftRingDistal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleProximal", rotation=(-35.0, 0.0, 0.0)),
        BonePose(bone_name="leftLittleDistal", rotation=(-20.0, 0.0, 0.0)),
        # Right hand — mirrored
        BonePose(bone_name="rightThumbMetacarpal", rotation=(-10.0, 10.0, 0.0)),
        BonePose(bone_name="rightThumbProximal", rotation=(-15.0, 8.0, 0.0)),
        BonePose(bone_name="rightThumbDistal", rotation=(-10.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexProximal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="rightIndexDistal", rotation=(-15.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleProximal", rotation=(-25.0, 0.0, 0.0)),
        BonePose(bone_name="rightMiddleDistal", rotation=(-15.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingProximal", rotation=(-30.0, 0.0, 0.0)),
        BonePose(bone_name="rightRingDistal", rotation=(-20.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleProximal", rotation=(-35.0, 0.0, 0.0)),
        BonePose(bone_name="rightLittleDistal", rotation=(-20.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

# ── Face Poses ─────────────────────────────────────────────────────────────

POSE_PRESETS["face_neutral"] = PosePreset(
    name="face_neutral",
    category="face",
    description="Neutral face — all blend shapes at 0, default rest expression",
    bones=[
        BonePose(bone_name="jaw", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={},
)

POSE_PRESETS["face_smile"] = PosePreset(
    name="face_smile",
    category="face",
    description="Slight smile — happy 0.3, eyeSquint 0.1",
    bones=[
        BonePose(bone_name="jaw", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={
        "happy": 0.3,
        "eyeSquint": 0.1,
    },
)

POSE_PRESETS["face_blink"] = PosePreset(
    name="face_blink",
    category="face",
    description="Eyes closed — eyeClose 1.0 (full blink)",
    bones=[
        BonePose(bone_name="jaw", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={
        "eyeClose": 1.0,
    },
)

POSE_PRESETS["face_mouth_open"] = PosePreset(
    name="face_mouth_open",
    category="face",
    description="Mouth open — aa 0.5 (viseme/shape for open mouth)",
    bones=[
        BonePose(bone_name="jaw", rotation=(5.0, 0.0, 0.0)),  # Slight jaw drop
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={
        "aa": 0.5,
    },
)

POSE_PRESETS["face_angry"] = PosePreset(
    name="face_angry",
    category="face",
    description="Angry expression — angry 0.6, eyeBrowDown 0.3",
    bones=[
        BonePose(bone_name="jaw", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={
        "angry": 0.6,
        "eyeBrowDown": 0.3,
    },
)

POSE_PRESETS["face_surprise"] = PosePreset(
    name="face_surprise",
    category="face",
    description="Surprised — surprised 0.7, eyeWide 0.5, mouthOpen 0.4",
    bones=[
        BonePose(bone_name="jaw", rotation=(8.0, 0.0, 0.0)),  # Dropped jaw
        BonePose(bone_name="leftEye", rotation=(0.0, 0.0, 0.0)),
        BonePose(bone_name="rightEye", rotation=(0.0, 0.0, 0.0)),
    ],
    blend_shapes={
        "surprised": 0.7,
        "eyeWide": 0.5,
        "mouthOpen": 0.4,
    },
)


# ═══════════════════════════════════════════════════════════════════════════════
# Pure-Python Functions
# ═══════════════════════════════════════════════════════════════════════════════


def validate_pose(pose: PosePreset) -> list[str]:
    """Validate a PosePreset, returning a list of warning/error strings.

    Checks:
      - Each bone_name is in VALID_BONE_NAMES (VRM_HUMANOID_BONES).
      - Rotation values are within reasonable range (-360, 360).
      - Scale values are positive.
      - Blend shape names are in VALID_BLEND_SHAPES.
      - Blend shape weights are in [0.0, 1.0].

    Returns:
        List of error/warning strings. Empty list means the pose is valid.
    """
    errors: list[str] = []

    # Validate category
    valid_categories = {"rest", "hand", "face", "body", "action"}
    if pose.category not in valid_categories:
        errors.append(
            f"Invalid category '{pose.category}' — must be one of {valid_categories}"
        )

    # Validate bones
    seen_bones: set[str] = set()
    for bone_pose in pose.bones:
        if bone_pose.bone_name in seen_bones:
            errors.append(f"Duplicate bone '{bone_pose.bone_name}' in pose '{pose.name}'")
        seen_bones.add(bone_pose.bone_name)

        if bone_pose.bone_name not in VALID_BONE_NAMES:
            errors.append(
                f"Invalid bone name '{bone_pose.bone_name}' in pose '{pose.name}'"
            )

        rx, ry, rz = bone_pose.rotation
        if not (-360.0 <= rx <= 360.0 and -360.0 <= ry <= 360.0 and -360.0 <= rz <= 360.0):
            errors.append(
                f"Rotation out of range for bone '{bone_pose.bone_name}' "
                f"in pose '{pose.name}': ({rx}, {ry}, {rz})"
            )

        sx, sy, sz = bone_pose.scale
        if sx <= 0 or sy <= 0 or sz <= 0:
            errors.append(
                f"Scale must be positive for bone '{bone_pose.bone_name}' "
                f"in pose '{pose.name}': ({sx}, {sy}, {sz})"
            )

    # Validate blend shapes
    for shape_name, weight in pose.blend_shapes.items():
        if shape_name not in VALID_BLEND_SHAPES:
            errors.append(
                f"Invalid blend shape '{shape_name}' in pose '{pose.name}'"
            )
        if not (0.0 <= weight <= 1.0):
            errors.append(
                f"Blend shape '{shape_name}' weight {weight} out of range [0, 1] "
                f"in pose '{pose.name}'"
            )

    return errors


def create_pose(
    name: str,
    category: str,
    bones: list[BonePose],
    blend_shapes: Optional[dict[str, float]] = None,
    description: str = "",
) -> PosePreset:
    """Create a new PosePreset with the given parameters.

    Args:
        name: Unique name for the pose.
        category: One of 'rest', 'hand', 'face', 'body', 'action'.
        bones: List of BonePose entries.
        blend_shapes: Optional dict of blend shape name → weight (0–1).
        description: Optional human-readable description.

    Returns:
        A new PosePreset instance.
    """
    if blend_shapes is None:
        blend_shapes = {}

    return PosePreset(
        name=name,
        category=category,
        description=description,
        bones=bones,
        blend_shapes=dict(blend_shapes),
    )


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t


def _lerp_tuple(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    t: float,
) -> tuple[float, float, float]:
    """Linear interpolation between two 3-tuples."""
    return (
        _lerp(a[0], b[0], t),
        _lerp(a[1], b[1], t),
        _lerp(a[2], b[2], t),
    )


def blend_poses(a: PosePreset, b: PosePreset, t: float) -> PosePreset:
    """Linearly interpolate between two poses.

    Both poses must have the same bone set (matched by bone_name). Blend
    shape weights are also interpolated. At t=0 returns pose a; at t=1
    returns pose b.

    Args:
        a: Start pose.
        b: End pose.
        t: Blend factor (0.0 = pose a, 1.0 = pose b).

    Returns:
        A new PosePreset with interpolated bone transforms and blend shapes.

    Raises:
        ValueError: If the bone sets don't match.
    """
    t = max(0.0, min(1.0, t))  # Clamp to [0, 1]

    # Build lookup by bone name for b
    b_bones: dict[str, BonePose] = {bp.bone_name: bp for bp in b.bones}

    blended_bones: list[BonePose] = []
    for a_bone in a.bones:
        if a_bone.bone_name not in b_bones:
            raise ValueError(
                f"Bone '{a_bone.bone_name}' in pose '{a.name}' "
                f"not found in pose '{b.name}'"
            )
        b_bone = b_bones[a_bone.bone_name]

        blended_bones.append(BonePose(
            bone_name=a_bone.bone_name,
            position=_lerp_tuple(a_bone.position, b_bone.position, t),
            rotation=_lerp_tuple(a_bone.rotation, b_bone.rotation, t),
            scale=_lerp_tuple(a_bone.scale, b_bone.scale, t),
        ))

    # Check for bones in b not in a
    a_bone_names = {bp.bone_name for bp in a.bones}
    for b_bone in b.bones:
        if b_bone.bone_name not in a_bone_names:
            raise ValueError(
                f"Bone '{b_bone.bone_name}' in pose '{b.name}' "
                f"not found in pose '{a.name}'"
            )

    # Blend blend shapes
    blended_blend_shapes: dict[str, float] = {}
    all_shape_keys = set(a.blend_shapes.keys()) | set(b.blend_shapes.keys())
    for key in all_shape_keys:
        a_val = a.blend_shapes.get(key, 0.0)
        b_val = b.blend_shapes.get(key, 0.0)
        blended_blend_shapes[key] = round(_lerp(a_val, b_val, t), 6)

    # Name and category come from the dominant pose (a if t < 0.5, b otherwise)
    dominant = a if t < 0.5 else b

    return PosePreset(
        name=f"{a.name}_to_{b.name}_{t:.2f}",
        category=dominant.category,
        description=f"Blend of '{a.name}' and '{b.name}' at t={t:.2f}",
        bones=blended_bones,
        blend_shapes=blended_blend_shapes,
    )


def get_poses_by_category(category: str) -> list[PosePreset]:
    """Return all pose presets matching the given category.

    Args:
        category: One of 'rest', 'hand', 'face', 'body', 'action'.

    Returns:
        List of PosePreset objects in that category.
    """
    return [
        preset for preset in POSE_PRESETS.values()
        if preset.category == category
    ]


def get_pose(name: str) -> PosePreset:
    """Look up a pose preset by name.

    Args:
        name: The exact name of the pose preset.

    Returns:
        The matching PosePreset.

    Raises:
        KeyError: If no pose with that name exists.
    """
    if name not in POSE_PRESETS:
        raise KeyError(f"No pose preset named '{name}'. Available: {list(POSE_PRESETS.keys())}")
    return POSE_PRESETS[name]


def list_pose_names() -> list[str]:
    """Return a sorted list of all available pose preset names."""
    return sorted(POSE_PRESETS.keys())


def list_categories() -> list[str]:
    """Return sorted list of unique categories across all presets."""
    return sorted({preset.category for preset in POSE_PRESETS.values()})


def pose_to_vrm(pose: PosePreset) -> dict:
    """Convert a PosePreset to a VRM rest-pose extension dict.

    Produces a dict suitable for the VRM 1.0 humanoid.restPose field,
    with each bone's rotation expressed as Euler XYZ degrees.

    Args:
        pose: The PosePreset to convert.

    Returns:
        Dict with 'humanoid' key containing 'restPose' mapping of
        bone_name → {x, y, z} Euler degrees.
    """
    rest_pose: dict[str, dict[str, float]] = {}
    for bone in pose.bones:
        rest_pose[bone.bone_name] = {
            "x": bone.rotation[0],
            "y": bone.rotation[1],
            "z": bone.rotation[2],
        }

    vrm_dict: dict = {
        "extensions": {
            "VRMC_vrm": {
                "humanoid": {
                    "restPose": rest_pose,
                },
            },
        },
    }

    # Include blend shapes if present
    if pose.blend_shapes:
        vrm_dict["extensions"]["VRMC_vrm"]["expressions"] = {
            "preset": {
                shape_name: {"weight": weight}
                for shape_name, weight in pose.blend_shapes.items()
                if shape_name in {"happy", "angry", "sad", "surprised",
                                  "neutral", "blink", "blinkLeft", "blinkRight"}
            },
        }

    return vrm_dict