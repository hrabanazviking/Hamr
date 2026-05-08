"""
Collision Mesh Forge — VRM 1.0 spring bone collider sphere generation.

Spring bones need collider meshes around the body so hair doesn't clip
through the torso. VRM 1.0 uses SpringBoneColliderGroup objects that
define sphere colliders positioned relative to armature bones.

This module provides:
- COLLIDER_REGIONS: body region → bone/radius/offset mapping
- Pure-Python config: compute radius, generate collider lists, validate
- Blender-dependent CollisionMeshGenerator: create sphere meshes in scene

Phase 12 (Yggdrasil): The roots draw from geometry. Every collider
protects a spring bone from clipping. Every sphere a shield.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("hamr.rigs.collision")

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
class CollisionMeshResult:
    """Result of creating a single collision mesh (collider sphere).

    Tracks whether the collider was created in the Blender scene,
    its position offset, and any warnings encountered.

    Attributes:
        collider_name: VRM collider name (e.g. "head_collider").
        mesh_name: Blender mesh object name (e.g. "collider_head_sphere").
        bone_name: Armature bone this collider is parented to.
        radius: Collider sphere radius in Blender units (meters).
        position: (x, y, z) offset from the bone head position.
        created: Whether the collider was successfully created in Blender.
        warnings: List of non-fatal issues encountered.
    """

    collider_name: str
    mesh_name: str
    bone_name: str
    radius: float
    position: tuple[float, float, float]
    created: bool = True
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# Collider Region Registry
# ──────────────────────────────────────────────────────────────

COLLIDER_REGIONS: dict[str, dict[str, Any]] = {
    "head": {
        "bone": "head",
        "radius": 0.08,
        "offset": (0.0, 0.0, 0.0),
    },
    "neck": {
        "bone": "neck",
        "radius": 0.04,
        "offset": (0.0, 0.0, 0.0),
    },
    "upper_chest": {
        "bone": "spine2",
        "radius": 0.10,
        "offset": (0.0, 0.0, 0.02),
    },
    "chest": {
        "bone": "spine1",
        "radius": 0.12,
        "offset": (0.0, 0.0, 0.05),
    },
    "spine": {
        "bone": "spine",
        "radius": 0.08,
        "offset": (0.0, 0.0, 0.0),
    },
    "hips": {
        "bone": "hips",
        "radius": 0.14,
        "offset": (0.0, 0.0, -0.02),
    },
    "left_shoulder": {
        "bone": "leftShoulder",
        "radius": 0.05,
        "offset": (0.0, 0.0, 0.0),
    },
    "right_shoulder": {
        "bone": "rightShoulder",
        "radius": 0.05,
        "offset": (0.0, 0.0, 0.0),
    },
    "left_upper_arm": {
        "bone": "leftUpperArm",
        "radius": 0.04,
        "offset": (0.0, 0.0, 0.0),
    },
    "right_upper_arm": {
        "bone": "rightUpperArm",
        "radius": 0.04,
        "offset": (0.0, 0.0, 0.0),
    },
    "left_thigh": {
        "bone": "leftUpperLeg",
        "radius": 0.06,
        "offset": (0.0, 0.0, 0.0),
    },
    "right_thigh": {
        "bone": "rightUpperLeg",
        "radius": 0.06,
        "offset": (0.0, 0.0, 0.0),
    },
}


# ──────────────────────────────────────────────────────────────
# Pure-Python Configuration Functions
# ──────────────────────────────────────────────────────────────

def compute_collider_radius(bone_name: str, body_scale: float = 1.0) -> float:
    """Look up and scale the collider radius for a given bone.

    Searches COLLIDER_REGIONS for a matching bone name and returns
    the radius scaled by ``body_scale``.

    Args:
        bone_name: Armature bone name (e.g. "head", "spine1").
        body_scale: Uniform body scale multiplier (default 1.0).

    Returns:
        Scaled radius in Blender units. Returns 0.05 (fallback)
        for unknown bones.
    """
    for _region, region_data in COLLIDER_REGIONS.items():
        if region_data["bone"] == bone_name:
            return region_data["radius"] * body_scale
    # Fallback for unknown bones — a small default collider
    logger.warning(f"Unknown bone '{bone_name}' for collider — using fallback radius 0.05")
    return 0.05 * body_scale


def generate_collider_list(
    spec: dict[str, Any] | None = None,
    body_scale: float = 1.0,
) -> list[CollisionMeshResult]:
    """Generate a full set of collision mesh results from spec or defaults.

    If *spec* is provided it must be a dict mapping region names
    (from COLLIDER_REGIONS) to override dicts with optional keys
    ``radius``, ``offset``, ``bone``, or ``enabled``.

    Args:
        spec: Optional per-region overrides.  Keys are region names
              (e.g. ``"head"``); values are dicts of overrides.
        body_scale: Uniform body scale multiplier (default 1.0).

    Returns:
        List of :class:`CollisionMeshResult` for all enabled colliders.
    """
    overrides = spec or {}
    results: list[CollisionMeshResult] = []

    for region_name, region_data in COLLIDER_REGIONS.items():
        region_overrides = overrides.get(region_name, {})

        # Allow disabling a region via enabled=False
        if region_overrides.get("enabled") is False:
            continue

        bone_name = region_overrides.get("bone", region_data["bone"])
        radius = region_overrides.get("radius", region_data["radius"]) * body_scale
        offset = region_overrides.get("offset", region_data["offset"])

        collider_name = f"{region_name}_collider"
        mesh_name = f"collider_{region_name}_sphere"

        result = CollisionMeshResult(
            collider_name=collider_name,
            mesh_name=mesh_name,
            bone_name=bone_name,
            radius=radius,
            position=offset,
            created=False,  # Not created in Blender until generate() is called
            warnings=[],
        )

        # Validate radius
        if radius <= 0:
            result.warnings.append(f"Non-positive radius {radius} for {region_name}")
        if radius > 1.0:
            result.warnings.append(f"Large radius {radius:.3f} for {region_name}")

        results.append(result)

    return results


def compute_collision_mesh_summary(
    collider_list: list[CollisionMeshResult],
) -> dict[str, Any]:
    """Compute a summary dict from a list of collision mesh results.

    Args:
        collider_list: List of :class:`CollisionMeshResult` objects.

    Returns:
        Dict with keys: ``count``, ``total_radius_avg``, ``regions``
        (mapping region index → radius).
    """
    if not collider_list:
        return {
            "count": 0,
            "total_radius_avg": 0.0,
            "regions": {},
        }

    total_radius = sum(c.radius for c in collider_list)
    regions = {
        c.collider_name: {"radius": c.radius, "bone": c.bone_name}
        for c in collider_list
    }

    return {
        "count": len(collider_list),
        "total_radius_avg": total_radius / len(collider_list),
        "regions": regions,
    }


def validate_collision_config(spec: dict[str, Any]) -> list[str]:
    """Validate a collision spec dict, returning a list of warning strings.

    Checks for:
    - Unknown region names
    - Invalid radius values (non-positive or excessively large)
    - Invalid offset tuples (wrong length or non-numeric)
    - Invalid bone names (empty strings)

    Args:
        spec: Dict mapping region names to override dicts.

    Returns:
        List of warning/error strings.  Empty list means valid.
    """
    warnings: list[str] = []

    for region_name, region_overrides in spec.items():
        if region_name not in COLLIDER_REGIONS:
            warnings.append(
                f"Unknown collider region '{region_name}' — "
                f"valid regions: {sorted(COLLIDER_REGIONS.keys())}"
            )
            continue

        if not isinstance(region_overrides, dict):
            warnings.append(
                f"Region '{region_name}' overrides must be a dict, "
                f"got {type(region_overrides).__name__}"
            )
            continue

        # Radius check
        if "radius" in region_overrides:
            r = region_overrides["radius"]
            if not isinstance(r, (int, float)):
                warnings.append(
                    f"Region '{region_name}': radius must be numeric, got {type(r).__name__}"
                )
            elif r <= 0:
                warnings.append(
                    f"Region '{region_name}': radius must be positive, got {r}"
                )
            elif r > 2.0:
                warnings.append(
                    f"Region '{region_name}': radius {r} is excessively large (max ~2.0)"
                )

        # Offset check
        if "offset" in region_overrides:
            off = region_overrides["offset"]
            if not isinstance(off, (tuple, list)) or len(off) != 3:
                warnings.append(
                    f"Region '{region_name}': offset must be a 3-element tuple/list, "
                    f"got {off!r}"
                )
            else:
                for i, v in enumerate(off):
                    if not isinstance(v, (int, float)):
                        warnings.append(
                            f"Region '{region_name}': offset[{i}] must be numeric, "
                            f"got {type(v).__name__}"
                        )

        # Bone name check
        if "bone" in region_overrides:
            bone = region_overrides["bone"]
            if not isinstance(bone, str) or not bone.strip():
                warnings.append(
                    f"Region '{region_name}': bone must be a non-empty string, "
                    f"got {bone!r}"
                )

    return warnings


# ──────────────────────────────────────────────────────────────
# Blender-dependent Collision Mesh Generator
# ──────────────────────────────────────────────────────────────

class CollisionMeshGenerator:
    """Generate collision meshes (collider spheres) in a Blender scene.

    Creates spherical collision proxies for each body region defined in
    :data:`COLLIDER_REGIONS` and parents them to the corresponding bones
    in the armature. These colliders are referenced by VRM 1.0
    SpringBoneColliderGroup objects.

    Requires ``bpy`` — raises :class:`RuntimeError` if Blender is not
    available.
    """

    def generate(
        self,
        spec: dict[str, Any] | None = None,
        armature_name: str | None = None,
    ) -> list[CollisionMeshResult]:
        """Create collider spheres in the Blender scene.

        Args:
            spec: Optional per-region overrides (see :func:`generate_collider_list`).
            armature_name: Name of the armature object in Blender. If
                provided, colliders are parented to their corresponding bones.

        Returns:
            List of :class:`CollisionMeshResult` — one per region.

        Raises:
            RuntimeError: If ``bpy`` is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "bpy not available — CollisionMeshGenerator requires Blender"
            )

        scene = bpy.context.scene
        results: list[CollisionMeshResult] = []

        # Generate the collider list from spec (pure-Python)
        collider_list = generate_collider_list(spec=spec)

        # Find armature object
        armature = None
        if armature_name:
            armature = bpy.data.objects.get(armature_name)
            if armature is None or armature.type != "ARMATURE":
                logger.warning(
                    f"Armature '{armature_name}' not found or not an armature — "
                    f"colliders will not be parented"
                )
                armature = None

        for collider_info in collider_list:
            result = self.create_collider_sphere(
                name=collider_info.collider_name,
                bone_name=collider_info.bone_name,
                radius=collider_info.radius,
                offset=collider_info.position,
            )
            results.append(result)

        # Parent colliders to armature bones
        if armature is not None:
            for result in results:
                mesh_obj = bpy.data.objects.get(result.mesh_name)
                if mesh_obj is not None:
                    bone = armature.data.bones.get(result.bone_name)
                    if bone is not None:
                        mesh_obj.parent = armature
                        mesh_obj.parent_type = "BONE"
                        mesh_obj.parent_bone = result.bone_name
                    else:
                        result.warnings.append(
                            f"Bone '{result.bone_name}' not found in armature "
                            f"'{armature_name}' — collider not parented"
                        )

        logger.info(
            f"CollisionMeshGenerator: created {sum(1 for r in results if r.created)} "
            f"collider spheres"
        )
        return results

    def create_collider_sphere(
        self,
        name: str,
        bone_name: str,
        radius: float,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> CollisionMeshResult:
        """Create a single collider sphere mesh in the Blender scene.

        Creates a UV sphere primitive with the given radius at the
        specified offset position. The sphere is a simplified collision
        proxy — low-poly (8 segments × 6 rings) for performance.

        Args:
            name: Collider name (e.g. ``"head_collider"``).
            bone_name: Armature bone to eventually parent to.
            radius: Sphere radius in Blender units.
            offset: (x, y, z) position offset from origin.

        Returns:
            :class:`CollisionMeshResult` with ``created=True`` on success.

        Raises:
            RuntimeError: If ``bpy`` is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "bpy not available — CollisionMeshGenerator requires Blender"
            )

        mesh_name = f"{name}_sphere"
        warnings: list[str] = []

        # Remove existing object if present
        existing = bpy.data.objects.get(mesh_name)
        if existing is not None:
            bpy.data.objects.remove(existing, do_unlink=True)

        # Remove orphaned mesh data
        existing_mesh = bpy.data.meshes.get(mesh_name)
        if existing_mesh is not None:
            bpy.data.meshes.remove(existing_mesh)

        # Use bmesh to create sphere for cleaner geometry
        import bmesh  # type: ignore

        bm = bmesh.new()
        # Low-poly sphere for collision: 8 segments, 6 rings
        bmesh.ops.create_uv_sphere(
            bm,
            u_segments=8,
            v_segments=6,
            radius=radius,
        )
        mesh_data = bpy.data.meshes.new(mesh_name)
        bm.to_mesh(mesh_data)
        bm.free()

        obj = bpy.data.objects.new(mesh_name, mesh_data)
        bpy.context.collection.objects.link(obj)

        # Position at offset
        obj.location = (offset[0], offset[1], offset[2])

        logger.debug(
            f"Created collider sphere: {mesh_name} "
            f"(bone={bone_name}, r={radius:.3f})"
        )

        return CollisionMeshResult(
            collider_name=name,
            mesh_name=mesh_name,
            bone_name=bone_name,
            radius=radius,
            position=offset,
            created=True,
            warnings=warnings,
        )