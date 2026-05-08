"""
Spring Bone Forge — VRM 1.0 spring bone configuration (VRMC_vrm spring bone extension).

Hair sways, cloth drapes, accessories bob — spring bones bring avatars to life.
This module provides pure-Python configuration and Blender-dependent application
for VRM 1.0 spring bone groups and collider spheres.

Phase 11 (Alvíssmál): The forge speaks spring bone fluency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from hamr.core.models import HairPhysicsSpec, BreastPhysicsSpec, PhysicsSpec
from hamr.core.constants import PHYSICS_DEFAULTS

logger = logging.getLogger("hamr.rigs.spring_bones")

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None
    BLENDER_AVAILABLE = False


# ──────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────

@dataclass
class SpringBoneGroup:
    """A VRM 1.0 spring bone group (VRMC_springBone colliderGroup + spring).

    Each group defines physics parameters for a chain of bones
    (e.g., hair tips, skirt hems, breast joints).
    """

    name: str
    comment: str = ""
    stiff_force: float = 1.0       # 0–10, higher = stiffer
    gravity_power: float = 0.0      # 0–2, gravity influence
    gravity_dir: tuple[float, float, float] = (0.0, -1.0, 0.0)
    drag_force: float = 0.4         # 0–1, air resistance
    center: str | None = None       # Optional reference center bone
    collider_groups: list[str] = field(default_factory=list)
    # Bone chains in this group — VRM 1.0 stores these per-spring
    bone_chains: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to VRM-compatible dict."""
        return {
            "name": self.name,
            "comment": self.comment,
            "stiff_force": self.stiff_force,
            "gravity_power": self.gravity_power,
            "gravity_dir": list(self.gravity_dir),
            "drag_force": self.drag_force,
            "center": self.center,
            "collider_groups": list(self.collider_groups),
            "bone_chains": [list(chain) for chain in self.bone_chains],
        }


@dataclass
class SpringBoneCollider:
    """A VRM 1.0 spring bone collider sphere.

    Colliders prevent spring bones from passing through geometry
    (e.g., hair through shoulders, skirt through legs).
    """

    name: str
    bone: str                             # Which bone the collider is attached to
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Position offset from bone
    radius: float = 0.01                  # Collider sphere radius in Blender units

    def to_dict(self) -> dict[str, Any]:
        """Serialize to VRM-compatible dict."""
        return {
            "name": self.name,
            "bone": self.bone,
            "offset": list(self.offset),
            "radius": self.radius,
        }


# ──────────────────────────────────────────────────────────────
# Preset spring configurations
# ──────────────────────────────────────────────────────────────

HAIR_SPRING_PRESETS: dict[str, dict[str, Any]] = {
    "long": {
        "stiff_force": 0.5,
        "gravity_power": 0.6,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.5,
        "comment": "Long flowing hair — gentle sway, strong gravity",
        "bone_chains": [
            ["hair_01_L", "hair_02_L", "hair_03_L", "hair_04_L", "hair_05_L"],
            ["hair_01_R", "hair_02_R", "hair_03_R", "hair_04_R", "hair_05_R"],
            ["hair_back_01", "hair_back_02", "hair_back_03", "hair_back_04", "hair_back_05"],
        ],
    },
    "medium": {
        "stiff_force": 0.8,
        "gravity_power": 0.4,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.45,
        "comment": "Medium-length hair — moderate sway",
        "bone_chains": [
            ["hair_01_L", "hair_02_L", "hair_03_L"],
            ["hair_01_R", "hair_02_R", "hair_03_R"],
            ["hair_back_01", "hair_back_02", "hair_back_03"],
        ],
    },
    "short": {
        "stiff_force": 1.5,
        "gravity_power": 0.2,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.3,
        "comment": "Short hair — subtle bounce",
        "bone_chains": [
            ["hair_01_L", "hair_02_L"],
            ["hair_01_R", "hair_02_R"],
        ],
    },
    "twin_tails": {
        "stiff_force": 0.6,
        "gravity_power": 0.55,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.5,
        "comment": "Twin tails — twin chains with independent sway",
        "bone_chains": [
            ["twintail_01_L", "twintail_02_L", "twintail_03_L", "twintail_04_L"],
            ["twintail_01_R", "twintail_02_R", "twintail_03_R", "twintail_04_R"],
        ],
    },
}

BREAST_SPRING_PRESETS: dict[str, dict[str, Any]] = {
    "small": {
        "stiff_force": 1.5,
        "gravity_power": 0.1,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.6,
        "comment": "Small bust — subtle movement, quick settle",
        "bone_chains": [
            ["breast_L"],
            ["breast_R"],
        ],
    },
    "medium": {
        "stiff_force": 0.9,
        "gravity_power": 0.3,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.55,
        "comment": "Medium bust — anime-proportionate bounce",
        "bone_chains": [
            ["breast_01_L", "breast_02_L"],
            ["breast_01_R", "breast_02_R"],
        ],
    },
    "large": {
        "stiff_force": 0.5,
        "gravity_power": 0.5,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.65,
        "comment": "Large bust — pronounced physics with slow settle",
        "bone_chains": [
            ["breast_01_L", "breast_02_L", "breast_03_L"],
            ["breast_01_R", "breast_02_R", "breast_03_R"],
        ],
    },
}

CLOTHING_SPRING_PRESETS: dict[str, dict[str, Any]] = {
    "skirt": {
        "stiff_force": 0.3,
        "gravity_power": 0.5,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.55,
        "comment": "Skirt drape — gentle hang with wind response",
        "center": "spine_01",
        "bone_chains": [
            ["skirt_01_L", "skirt_02_L", "skirt_03_L"],
            ["skirt_01_R", "skirt_02_R", "skirt_03_R"],
            ["skirt_front_01", "skirt_front_02", "skirt_front_03"],
            ["skirt_back_01", "skirt_back_02", "skirt_back_03"],
        ],
    },
    "cape": {
        "stiff_force": 0.2,
        "gravity_power": 0.6,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.6,
        "comment": "Cape — dramatic flowing drape",
        "center": "upperChest",
        "bone_chains": [
            ["cape_01_L", "cape_02_L", "cape_03_L", "cape_04_L"],
            ["cape_01_R", "cape_02_R", "cape_03_R", "cape_04_R"],
            ["cape_back_01", "cape_back_02", "cape_back_03", "cape_back_04"],
        ],
    },
    "ribbon": {
        "stiff_force": 0.7,
        "gravity_power": 0.15,
        "gravity_dir": (0.0, -1.0, 0.0),
        "drag_force": 0.4,
        "comment": "Ribbon/accessory — light, fluttery movement",
        "bone_chains": [
            ["ribbon_01_L", "ribbon_02_L", "ribbon_03_L"],
            ["ribbon_01_R", "ribbon_02_R", "ribbon_03_R"],
        ],
    },
}

# Common collider definitions for anime avatars
DEFAULT_COLLIDERS: list[dict[str, Any]] = [
    {"name": "head_collider", "bone": "head", "offset": (0.0, 0.0, 0.0), "radius": 0.08},
    {"name": "upper_body_collider", "bone": "upperChest", "offset": (0.0, 0.0, 0.0), "radius": 0.12},
    {"name": "lower_body_collider", "bone": "spine", "offset": (0.0, 0.0, 0.0), "radius": 0.1},
    {"name": "left_shoulder_collider", "bone": "clavicle_L", "offset": (0.0, 0.0, 0.0), "radius": 0.05},
    {"name": "right_shoulder_collider", "bone": "clavicle_R", "offset": (0.0, 0.0, 0.0), "radius": 0.05},
]


# ──────────────────────────────────────────────────────────────
# Pure-Python configuration functions
# ──────────────────────────────────────────────────────────────

def configure_hair_spring(hair_spec: HairPhysicsSpec | None = None) -> SpringBoneGroup:
    """Configure a hair spring bone group from a HairPhysicsSpec.

    Uses HairPhysicsSpec values for stiffness, gravity, and drag,
    mapping them to VRM 1.0 spring bone parameters.

    Args:
        hair_spec: Optional HairPhysicsSpec. Uses defaults if None.

    Returns:
        SpringBoneGroup configured for hair physics.
    """
    spec = hair_spec or HairPhysicsSpec()

    # Map HairPhysicsSpec (0–1 range) to spring bone param ranges
    # stiffness: 0–1 → stiff_force 0.1–5.0 (exponential feel)
    stiff_force = 0.1 + spec.stiffness * 4.9
    # gravity: 0–1 → gravity_power 0.0–1.5
    gravity_power = spec.gravity * 1.5
    # drag: 0–1 → drag_force 0.2–0.8
    drag_force = 0.2 + spec.drag * 0.6

    # Choose hair preset based on physics character
    # Stiff hair ≈ short; very flowing ≈ long
    if spec.stiffness >= 1.2:
        preset_key = "short"
    elif spec.stiffness >= 0.6:
        preset_key = "medium"
    else:
        preset_key = "long"

    preset = HAIR_SPRING_PRESETS[preset_key]

    return SpringBoneGroup(
        name="hair_spring",
        comment=preset["comment"],
        stiff_force=stiff_force,
        gravity_power=gravity_power,
        gravity_dir=preset["gravity_dir"],
        drag_force=drag_force,
        center="head",
        collider_groups=["head_collider", "upper_body_collider"],
        bone_chains=preset["bone_chains"],
    )


def configure_breast_spring(body_spec: Any = None) -> SpringBoneGroup:
    """Configure a breast spring bone group.

    Uses BreastPhysicsSpec if available, or infers from body proportions.

    Args:
        body_spec: Optional BreastPhysicsSpec or dict with 'bust' key.
                   Falls back to PhysicalConstants defaults if None.

    Returns:
        SpringBoneGroup configured for breast physics.
    """
    physics_defaults = PHYSICS_DEFAULTS["breast"]

    if body_spec is None:
        # Use defaults from constants
        return SpringBoneGroup(
            name="breast_spring",
            comment=BREAST_SPRING_PRESETS["medium"]["comment"],
            stiff_force=physics_defaults["stiffness"] * 4.0 + 0.1,
            gravity_power=physics_defaults["gravity"] * 1.5,
            gravity_dir=(0.0, -1.0, 0.0),
            drag_force=physics_defaults["drag"],
            center="spine_01",
            collider_groups=["upper_body_collider"],
            bone_chains=BREAST_SPRING_PRESETS["medium"]["bone_chains"],
        )

    # Handle BreastPhysicsSpec instance
    if isinstance(body_spec, BreastPhysicsSpec):
        stiff_force = 0.1 + body_spec.stiffness * 4.9
        drag_force = 0.2 + body_spec.drag * 0.6
        return SpringBoneGroup(
            name="breast_spring",
            comment="Breast physics from BreastPhysicsSpec",
            stiff_force=stiff_force,
            gravity_power=0.3,  # Default for breasts
            gravity_dir=(0.0, -1.0, 0.0),
            drag_force=drag_force,
            center="spine_01",
            collider_groups=["upper_body_collider"],
            bone_chains=BREAST_SPRING_PRESETS["medium"]["bone_chains"],
        )

    # Handle dict-like body spec with 'bust' proportions
    bust = 0.5  # default medium
    if isinstance(body_spec, dict) and "bust" in body_spec:
        bust = body_spec["bust"]
    elif hasattr(body_spec, "proportions"):
        proportions = body_spec.proportions
        if isinstance(proportions, dict):
            bust = proportions.get("bust", 0.5)

    # Select preset based on bust proportion
    if bust <= 0.45:
        preset_key = "small"
    elif bust <= 0.65:
        preset_key = "medium"
    else:
        preset_key = "large"

    preset = BREAST_SPRING_PRESETS[preset_key]

    return SpringBoneGroup(
        name="breast_spring",
        comment=preset["comment"],
        stiff_force=preset["stiff_force"],
        gravity_power=preset["gravity_power"],
        gravity_dir=preset["gravity_dir"],
        drag_force=preset["drag_force"],
        center="spine_01",
        collider_groups=["upper_body_collider"],
        bone_chains=preset["bone_chains"],
    )


def configure_clothing_spring(
    clothing_name: str,
    cloth_type: str = "skirt",
) -> SpringBoneGroup:
    """Configure a clothing spring bone group.

    Args:
        clothing_name: Identifier for this clothing piece (used in group name).
        cloth_type: Type of clothing physics — one of "skirt", "cape", "ribbon".

    Returns:
        SpringBoneGroup configured for the clothing piece.
    """
    preset_key = cloth_type if cloth_type in CLOTHING_SPRING_PRESETS else "skirt"
    preset = CLOTHING_SPRING_PRESETS[preset_key]

    return SpringBoneGroup(
        name=f"{clothing_name}_spring",
        comment=preset["comment"],
        stiff_force=preset["stiff_force"],
        gravity_power=preset["gravity_power"],
        gravity_dir=preset["gravity_dir"],
        drag_force=preset["drag_force"],
        center=preset.get("center"),
        collider_groups=["lower_body_collider", "upper_body_collider"],
        bone_chains=preset["bone_chains"],
    )


# ──────────────────────────────────────────────────────────────
# Blender-dependent application
# ──────────────────────────────────────────────────────────────

def apply_spring_bones(
    armature_name: str,
    spring_groups: list[SpringBoneGroup],
    colliders: list[SpringBoneCollider],
) -> dict[str, Any]:
    """Apply spring bone configuration to a Blender armature for VRM 1.0 export.

    Configures the VRMC_springBone extension on the armature's VRM addon extension.

    Args:
        armature_name: Name of the armature object in Blender.
        spring_groups: List of SpringBoneGroup configs to apply.
        colliders: List of SpringBoneCollider sphere definitions.

    Returns:
        Dict with export data: spring groups and colliders applied.

    Raises:
        RuntimeError: If bpy is not available or armature not found.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — must run inside Blender")

    armature = bpy.data.objects.get(armature_name)
    if armature is None or armature.type != "ARMATURE":
        raise ValueError(f"Armature '{armature_name}' not found or not an armature")

    result: dict[str, Any] = {
        "armature": armature_name,
        "spring_groups": [],
        "colliders": [],
    }

    # Configure collider groups (VRMC_springBone)
    vrm_ext = armature.vrm_addon_extension
    if hasattr(vrm_ext, "vrm1"):
        # V-019: VRM 1.0 spring bone extension may not be present on all armatures
        # We store the configuration as export data for the VRM addon to consume
        for collider in colliders:
            collider_data = collider.to_dict()
            result["colliders"].append(collider_data)
            logger.debug(f"Collider: {collider.name} on {collider.bone} r={collider.radius}")

        for group in spring_groups:
            group_data = group.to_dict()
            result["spring_groups"].append(group_data)

            # Try to apply via VRM addon extension if available
            spring_bone = getattr(vrm_ext.vrm1, "spring_bone", None)
            if spring_bone is not None:
                try:
                    # Add collider group
                    collider_group_name = group.name + "_colliders"
                    if hasattr(spring_bone, "collider_groups"):
                        col_group = spring_bone.collider_groups.add()
                        col_group.name = collider_group_name
                        for collider in colliders:
                            cb = col_group.colliders.add()
                            cb.offset = list(collider.offset)
                            cb.radius = collider.radius
                            # Map bone name
                            cb.node.bone_name = collider.bone

                    # Add spring
                    spring = spring_bone.springs.add()
                    spring.name = group.name
                    spring.stiff_force = group.stiff_force
                    spring.gravity_power = group.gravity_power
                    spring.gravity_dir = list(group.gravity_dir)
                    spring.drag_force = group.drag_force

                    if group.center:
                        spring.center.bone_name = group.center

                    # Add bone chains
                    for chain in group.bone_chains:
                        for bone_name in chain:
                            bone_node = spring.bones.add()
                            bone_node.bone_name = bone_name

                    logger.debug(f"Spring group applied: {group.name}")
                except Exception as e:
                    logger.warning(f"Could not apply spring bone via addon: {e}")
                    # Still return data — can be applied manually or post-processed

    logger.info(
        f"Spring bones configured: {len(spring_groups)} groups, "
        f"{len(colliders)} colliders on {armature_name}"
    )
    return result