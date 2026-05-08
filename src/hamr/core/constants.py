"""
Constants — Color defaults, bone maps, shader configs.

These are the fixed reference points.
The constants are unchanging; the parameters flow around them.
"""

from __future__ import annotations

# ── Skin Defaults ──────────────────────────────────────────────
SKIN_BASE_HEX = "#E8B87A"  # Golden-tan Runa default
SKIN_SHADED_HEX = "#C49A64"  # Shaded skin tone
SKIN_UNDERTONE_WARM = "#D4A06C"
SKIN_UNDERTONE_COOL = "#B89B8A"
SKIN_UNDERTONE_NEUTRAL = "#CEAA82"

# ── Eye Defaults ──────────────────────────────────────────────
IRIS_ICE_BLUE_HEX = "#B8D4E3"  # Runa's ice-blue eyes
SCLERA_WHITE_HEX = "#F5F5F0"
PUPIL_HEX = "#1A1A2E"

# ── Hair Defaults ─────────────────────────────────────────────
HAIR_ROOTS_HEX = "#C4A265"  # Golden-blonde roots
HAIR_MID_HEX = "#D4B87A"  # Mid-length blonde
HAIR_TIPS_HEX = "#F5E6B8"  # Light platinum tips
HAIR_SHADOW_HEX = "#8A7A4A"  # Shadow in curls

# ── VRM Bone Mapping ──────────────────────────────────────────
# Canonical VRM 1.0 humanoid bone names
VRM_HUMANOID_BONES = [
    "hips",
    "leftUpperLeg",
    "rightUpperLeg",
    "leftLowerLeg",
    "rightLowerLeg",
    "leftFoot",
    "rightFoot",
    "leftToes",
    "rightToes",
    "spine",
    "chest",
    "upperChest",
    "neck",
    "head",
    "leftShoulder",
    "rightShoulder",
    "leftUpperArm",
    "rightUpperArm",
    "leftLowerArm",
    "rightLowerArm",
    "leftHand",
    "rightHand",
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
    "jaw",
    "leftEye",
    "rightEye",
]

# VRChat-required AM visemes
VRM_VISEMES = [
    "sil", "PP", "FF", "TH", "DD",
    "kk", "CH", "SS", "nn", "RR",
    "E", "I", "O", "U",
    "aa",
]

# ── Shader Defaults (lilToon) ────────────────────────────────
LILTOON_DEFAULTS = {
    "render_queue": 2000,
    "cull_mode": "back",
    "outline_width": 0.05,
    "outline_color": "#000000",
}

# ── Physics Defaults ──────────────────────────────────────────
PHYSICS_DEFAULTS = {
    "hair": {
        "stiffness": 0.35,
        "gravity": 0.3,
        "drag": 0.4,
        "hit_radius": 0.05,
    },
    "breast": {
        "stiffness": 0.25,
        "gravity": 0.5,
        "drag": 0.6,
        "hit_radius": 0.12,
    },
    "cape": {
        "stiffness": 0.15,
        "gravity": 0.4,
        "drag": 0.5,
        "hit_radius": 0.08,
    },
}

# ── Build Presets ─────────────────────────────────────────────
BODY_PRESETS = {
    "athletic-slender": {
        "shoulder_width": 0.4,
        "bust": 0.55,
        "waist": 0.35,
        "hip_width": 0.65,
        "leg_length": 0.55,
    },
    "athletic": {
        "shoulder_width": 0.5,
        "bust": 0.6,
        "waist": 0.4,
        "hip_width": 0.6,
        "leg_length": 0.55,
    },
    "slender": {
        "shoulder_width": 0.35,
        "bust": 0.45,
        "waist": 0.3,
        "hip_width": 0.5,
        "leg_length": 0.6,
    },
    "curvy": {
        "shoulder_width": 0.45,
        "bust": 0.7,
        "waist": 0.35,
        "hip_width": 0.75,
        "leg_length": 0.5,
    },
    "average": {
        "shoulder_width": 0.45,
        "bust": 0.5,
        "waist": 0.4,
        "hip_width": 0.55,
        "leg_length": 0.5,
    },
}

# ── VRM Export Constants ──────────────────────────────────────
VRM_SPEC_VERSION = "1.0"
VRM_META_DEFAULTS = {
    "title": "Hamr Character",
    "author": "Hamr Forge",
    "version": "1.0",
    "license": "CC-BY-4.0",
    "contact_url": "https://github.com/hrabanazviking/Hamr",
}

# ── Texture Pipeline ──────────────────────────────────────────
TEXTURE_SIZE = 2048  # Default texture resolution
TEXTURE_BLEND_FACTOR = 0.75  # HSV blend: 75% new / 25% original