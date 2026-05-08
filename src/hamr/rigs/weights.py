"""
Weight Paint Engine — Automatic weight painting for smooth deformations.

Every vertex shall move smooth. Every weight gradient, true.
The forge knows the weight of every bone upon every vertex,
and makes the boundaries gentle.

AD-11.4: Weight painting engine (smooth, normalize, quality score, transfer).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("hamr.rigs.weights")

try:
    import bpy  # type: ignore

    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False

# ── Joint regions that need smooth weight transitions ───────────────
# Keys are joint region names; values are lists of vertex group / bone
# names that should influence the boundary vertices.
SMOOTH_REGIONS: dict[str, list[str]] = {
    "neck": ["head", "neck", "spine_02", "spine_03"],
    "left_shoulder": ["clavicle_L", "upper_arm_L", "spine_02"],
    "right_shoulder": ["clavicle_R", "upper_arm_R", "spine_02"],
    "left_hip": ["thigh_L", "pelvis", "spine"],
    "right_hip": ["thigh_R", "pelvis", "spine"],
    "left_knee": ["thigh_L", "calf_L", "shin_L"],
    "right_knee": ["thigh_R", "calf_R", "shin_R"],
    "left_elbow": ["upper_arm_L", "forearm_L", "lowerarm_L"],
    "right_elbow": ["upper_arm_R", "forearm_R", "lowerarm_R"],
}


# ── Dataclasses ─────────────────────────────────────────────────────
@dataclass
class WeightPaintReport:
    """Quality report for weight painting."""

    avg_groups_per_vertex: float
    min_groups_per_vertex: int
    max_weight_variance: float
    normalization_rate: float  # fraction of verts summing to 1.0
    score: float  # 0.0–1.0 composite quality score


# ── Pure-Python helpers (no bpy) ────────────────────────────────────

def compute_quality_score(
    vertex_groups: dict[str, list[tuple[int, float]]],
    bone_names: list[str],
) -> float:
    """Compute a 0–1 quality score for weight painting from vertex group data.

    Pure-Python — requires no Blender.

    The score is a composite of three sub-scores:
      - coverage:  0.4 × min(avg_groups_per_vertex / 4.0, 1.0)
      - normalisation: 0.3 × (fraction of vertices whose weight groups sum ≈ 1.0)
      - gradient:  0.3 × (1.0 − max_weight_variance)

    Args:
        vertex_groups: dict mapping vertex_group_name to a list of
            (vertex_index, weight) pairs.
        bone_names: List of bone names to consider (filters vertex groups).

    Returns:
        Float 0.0–1.0 quality score. Higher is better.
    """
    if not vertex_groups or not bone_names:
        return 0.0

    # Build per-vertex weight map: vertex_index → {group_name: weight}
    vert_weights: dict[int, dict[str, float]] = {}
    bone_set = set(bone_names)

    for group_name, assignments in vertex_groups.items():
        # Only consider groups corresponding to known bones
        if group_name not in bone_set:
            # Also allow common naming conventions (e.g., with .L/.R suffix)
            # or exact match
            continue
        for vert_idx, weight in assignments:
            if weight <= 0.0:
                continue
            if vert_idx not in vert_weights:
                vert_weights[vert_idx] = {}
            vert_weights[vert_idx][group_name] = weight

    if not vert_weights:
        return 0.0

    # ── 1. Coverage: avg groups per vertex ───────────────────────────
    groups_per_vert = [len(vw) for vw in vert_weights.values()]
    avg_groups = sum(groups_per_vert) / len(groups_per_vert)
    coverage_score = min(avg_groups / 4.0, 1.0)

    # ── 2. Normalisation: fraction of verts whose weights sum to ~1.0 ─
    normalised_count = 0
    epsilon = 0.05  # tolerance for sum deviation from 1.0
    for vw in vert_weights.values():
        total = sum(vw.values())
        if abs(total - 1.0) < epsilon:
            normalised_count += 1
    norm_score = normalised_count / len(vert_weights) if vert_weights else 0.0

    # ── 3. Gradient smoothness (1.0 − max weight concentration) ─────
    # Lower variance = smoother gradient
    # We measure: for each vertex, what fraction of total weight is on the
    # dominant bone? High concentration (>0.8) indicates rigid single-bone
    # weighting, which is bad for smooth deformation.
    max_concentrations: list[float] = []
    for vw in vert_weights.values():
        total = sum(vw.values())
        if total > 0 and len(vw) > 1:
            dominant = max(vw.values())
            concentration = dominant / total
            max_concentrations.append(concentration)
        elif total > 0 and len(vw) == 1:
            max_concentrations.append(1.0)  # single-bone, max concentration

    if max_concentrations:
        avg_concentration = sum(max_concentrations) / len(max_concentrations)
        # A concentration of 0.5 (2 bones equal) is ideal, 1.0 (single bone) is worst
        # Map: 0.5 → 1.0, 1.0 → 0.0
        variance_score = max(0.0, 1.0 - (avg_concentration - 0.5) / 0.5)
    else:
        variance_score = 0.0

    # ── Composite ───────────────────────────────────────────────────
    score = 0.4 * coverage_score + 0.3 * norm_score + 0.3 * variance_score
    return round(max(0.0, min(1.0, score)), 4)


def classify_deformation_quality(score: float) -> str:
    """Classify a weight paint quality score into a human-readable label.

    Pure-Python — requires no Blender.

    Args:
        score: Quality score from compute_quality_score (0.0–1.0).

    Returns:
        One of "poor", "acceptable", "good", "excellent".
    """
    if score < 0.4:
        return "poor"
    elif score < 0.6:
        return "acceptable"
    elif score < 0.8:
        return "good"
    else:
        return "excellent"


def smooth_weight_map(
    weights: list[float],
    iterations: int = 3,
    radius: float = 0.3,
) -> list[float]:
    """Pure-Python iterative weight smoothing on a weight list.

    Applies a simple weighted-average smoothing where each weight is
    blended toward its neighbours' average.  The `radius` parameter
    controls how strongly each weight is pulled toward the local average:
    0.0 = no change, 1.0 = full average replacement.

    Pure-Python — requires no Blender.

    Args:
        weights: List of float weights to smooth.
        iterations: Number of smoothing passes.
        radius: Blending factor (0.0–1.0) toward the local average.

    Returns:
        New list of smoothed weights (never modifies input).
    """
    if not weights or iterations <= 0:
        return list(weights)

    result = list(weights)
    n = len(result)

    # Edge case: single vertex
    if n < 2:
        return result

    for _ in range(iterations):
        prev = list(result)
        for i in range(n):
            # Neighbourhood: previous and next vertex (cyclic for the list)
            neighbours = []
            if i > 0:
                neighbours.append(prev[i - 1])
            if i < n - 1:
                neighbours.append(prev[i + 1])

            if neighbours:
                local_avg = sum(neighbours) / len(neighbours)
                result[i] = result[i] * (1.0 - radius) + local_avg * radius

    return result


# ── Blender-dependent engine class ──────────────────────────────────

class WeightPaintEngine:
    """Automatic weight painting for smooth deformations (AD-11.4).

    All methods that interact with Blender objects require a running
    Blender instance (bpy available).  Pure-Python analysis functions
    are provided as module-level helpers above.
    """

    def paint_smooth(
        self,
        armature_name: str,
        mesh_name: str,
        bone_name: str | None = None,
        influence_radius: float = 0.3,
        iterations: int = 3,
    ) -> None:
        """Smooth vertex weights around bone joints for smoother deformations.

        Must run inside Blender.

        Pipeline:
        1. Select the mesh and enter weight-paint mode
        2. For the given bone (or all key joints), find boundary vertices
        3. Blend each boundary vertex's weights toward the local average
        4. Ensure smooth transitions across joint regions
        5. Normalize all groups after smoothing

        Args:
            armature_name: Name of the armature object in the scene.
            mesh_name: Name of the mesh object to smooth weights on.
            bone_name: Specific bone to smooth around.  If None, smooth
                all joints listed in SMOOTH_REGIONS.
            influence_radius: Blending factor (0.0–1.0) for each smoothing
                iteration.  Higher = more aggressive smoothing.
            iterations: Number of smoothing passes.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "bpy not available — paint_smooth() must run inside Blender"
            )

        mesh_obj = bpy.data.objects.get(mesh_name)
        armature = bpy.data.objects.get(armature_name)

        if mesh_obj is None:
            logger.error(f"Mesh '{mesh_name}' not found in scene")
            return
        if armature is None or armature.type != "ARMATURE":
            logger.error(f"Armature '{armature_name}' not found or not armature")
            return

        # Ensure the mesh is parented to the armature
        if mesh_obj.parent != armature:
            logger.warning(f"Mesh '{mesh_name}' is not parented to '{armature_name}'")

        # Determine which regions/bones to smooth
        if bone_name is not None:
            target_bones = [bone_name]
        else:
            # Collect all bones from SMOOTH_REGIONS
            target_bones = []
            for region_bones in SMOOTH_REGIONS.values():
                target_bones.extend(region_bones)
            target_bones = list(set(target_bones))

        logger.info(
            f"Smoothing weights for {len(target_bones)} bone(s) "
            f"on mesh '{mesh_name}' ({iterations} iterations, "
            f"radius={influence_radius})"
        )

        # Get bone name set for filtering vertex groups
        arm_bone_names = {b.name for b in armature.data.bones}

        # Perform smoothing per vertex group
        for target_bone in target_bones:
            # Find the corresponding vertex group
            vg_idx = None
            for vg in mesh_obj.vertex_groups:
                if vg.name == target_bone or vg.name in arm_bone_names:
                    if vg.name == target_bone:
                        vg_idx = vg.index
                        break

            if vg_idx is None:
                # Try to find a vertex group matching the bone
                for vg in mesh_obj.vertex_groups:
                    if vg.name == target_bone:
                        vg_idx = vg.index
                        break

            if vg_idx is None:
                logger.debug(f"  No vertex group for bone '{target_bone}' — skipping")
                continue

            vg = mesh_obj.vertex_groups[vg_idx]

            # Collect vertices with weight in this group
            vert_indices: list[int] = []
            for vert in mesh_obj.data.vertices:
                for group in vert.groups:
                    if group.group == vg_idx and group.weight > 0.001:
                        vert_indices.append(vert.index)
                        break

            if len(vert_indices) < 3:
                logger.debug(
                    f"  Bone '{target_bone}' has only {len(vert_indices)} "
                    f"weighted vertices — skipping"
                )
                continue

            # Smooth iteration: blend each vertex weight toward the average
            # of its neighbours in this group
            for _iter in range(iterations):
                # Build weight map for this group
                weight_map: dict[int, float] = {}
                for vi in vert_indices:
                    try:
                        w = vg.weight(vi)
                        weight_map[vi] = w
                    except Exception:
                        continue

                # Smooth: for each vertex, blend toward neighbour average
                for vi in vert_indices:
                    if vi not in weight_map:
                        continue
                    current = weight_map[vi]
                    # Find neighbours: +/- 1 in index (vertices are
                    # sequential in typical meshes)
                    neighbours = []
                    for offset in [-1, 1]:
                        ni = vi + offset
                        if ni in weight_map:
                            neighbours.append(weight_map[ni])

                    if neighbours:
                        avg = sum(neighbours) / len(neighbours)
                        new_weight = current * (1.0 - influence_radius) + avg * influence_radius
                        # Clamp to valid range
                        new_weight = max(0.0, min(1.0, new_weight))
                        try:
                            vg.add([vi], new_weight, "REPLACE")
                        except Exception:
                            # Vertex may not be in group — use assign instead
                            try:
                                vg.add([vi], new_weight, "ADD")
                            except Exception:
                                pass

            logger.debug(f"  Smoothed weights for '{target_bone}'")

        # Normalize all vertex groups after smoothing
        self.normalize_weights(armature_name, mesh_name)
        logger.info(f"Weight smoothing complete for '{mesh_name}'")

    def transfer_weights(
        self,
        source_mesh: str,
        target_mesh: str,
        method: str = "nearest_vertex",
    ) -> None:
        """Transfer weight paint from body mesh to clothing/hair mesh.

        Uses Blender's data transfer modifier for vertex group mapping.

        Must run inside Blender.

        Args:
            source_mesh: Name of the source (body) mesh object with existing
                vertex groups.
            target_mesh: Name of the target (clothing/hair) mesh to receive
                weights.
            method: Transfer method.  One of:
                - 'nearest_vertex': Nearest vertex mapping (default, fastest)
                - 'nearest_face': Nearest face interpolation
                - 'projection': Ray-cast projection along normals

        Raises:
            RuntimeError: If bpy is not available.
            ValueError: If invalid method specified.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "bpy not available — transfer_weights() must run inside Blender"
            )

        valid_methods = {"nearest_vertex", "nearest_face", "projection"}
        if method not in valid_methods:
            raise ValueError(
                f"Invalid transfer method '{method}'. "
                f"Must be one of: {valid_methods}"
            )

        source = bpy.data.objects.get(source_mesh)
        target = bpy.data.objects.get(target_mesh)

        if source is None:
            logger.error(f"Source mesh '{source_mesh}' not found in scene")
            return
        if target is None:
            logger.error(f"Target mesh '{target_mesh}' not found in scene")
            return

        # Ensure source has vertex groups to transfer
        if not source.vertex_groups:
            logger.error(f"Source mesh '{source_mesh}' has no vertex groups")
            return

        logger.info(
            f"Transferring weights from '{source_mesh}' to '{target_mesh}' "
            f"using method '{method}'"
        )

        # Map our method names to Blender's data transfer vertex mapping
        method_map = {
            "nearest_vertex": "NEAREST_VERTEX",
            "nearest_face": "NEAREST_FACE",
            "projection": "PROJECTION",
        }

        # Add data transfer modifier
        mod = target.modifiers.new(name="HamrWeightTransfer", type="DATA_TRANSFER")

        mod.use_vert_data = True
        mod.data_types_verts = {"VGROUP_WEIGHTS"}
        mod.vert_mapping = method_map[method]

        mod.object = source
        mod.use_object_transform = True

        # Vgroup match by name
        mod.use_vgroup_weights_from = True

        # Apply the modifier
        # We need to set target as active object first
        bpy.context.view_layer.objects.active = target
        target.select_set(True)

        # Apply modifier
        bpy.ops.object.modifier_apply(modifier=mod.name)

        logger.info(
            f"Weight transfer complete: "
            f"{len(target.vertex_groups)} vertex groups on '{target_mesh}'"
        )

    def get_quality_score(
        self,
        armature_name: str,
        mesh_name: str,
    ) -> WeightPaintReport:
        """Compute a 0–1 quality score for weight painting on a mesh.

        Must run inside Blender.

        Score formula (AD-11.4):
        - 0.4 × (avg_groups_per_vertex / 4.0), capped at 1.0
        - 0.3 × normalization_rate
        - 0.3 × (1.0 − max_weight_variance)

        A score ≥ 0.7 means PASS.

        Args:
            armature_name: Name of the armature object.
            mesh_name: Name of the mesh object to score.

        Returns:
            WeightPaintReport with detailed metrics.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "bpy not available — get_quality_score() must run inside Blender"
            )

        mesh_obj = bpy.data.objects.get(mesh_name)
        armature = bpy.data.objects.get(armature_name)

        if mesh_obj is None:
            logger.error(f"Mesh '{mesh_name}' not found")
            return WeightPaintReport(
                avg_groups_per_vertex=0.0,
                min_groups_per_vertex=0,
                max_weight_variance=0.0,
                normalization_rate=0.0,
                score=0.0,
            )

        # Get bone names from armature
        bone_names: list[str] = []
        if armature is not None:
            bone_names = [b.name for b in armature.data.bones]
        else:
            # Fallback: use all vertex group names as bone names
            bone_names = [vg.name for vg in mesh_obj.vertex_groups]

        # Collect vertex group data into format for compute_quality_score
        vertex_groups: dict[str, list[tuple[int, float]]] = {}
        for vg in mesh_obj.vertex_groups:
            assignments: list[tuple[int, float]] = []
            for vert in mesh_obj.data.vertices:
                for group in vert.groups:
                    if group.group == vg.index and group.weight > 0.0:
                        assignments.append((vert.index, group.weight))
            vertex_groups[vg.name] = assignments

        # Compute scores using pure-Python helper
        score = compute_quality_score(vertex_groups, bone_names)

        # Compute detailed metrics for the report
        vert_group_counts: list[int] = []
        normalised_count = 0
        epsilon = 0.05

        for vert in mesh_obj.data.vertices:
            bone_groups = [
                g for g in vert.groups
                if g.weight > 0.001 and mesh_obj.vertex_groups[g.group].name in bone_names
            ]
            vert_group_counts.append(len(bone_groups))

            total_weight = sum(g.weight for g in bone_groups)
            if abs(total_weight - 1.0) < epsilon or len(bone_groups) == 0:
                normalised_count += 1

        total_verts = len(mesh_obj.data.vertices)
        avg_groups = sum(vert_group_counts) / total_verts if total_verts else 0.0
        min_groups = min(vert_group_counts) if vert_group_counts else 0

        # Max weight variance: for each vertex, what fraction is on the dominant bone
        concentrations: list[float] = []
        for vert in mesh_obj.data.vertices:
            bone_weights = [
                g.weight for g in vert.groups
                if g.weight > 0.001 and mesh_obj.vertex_groups[g.group].name in bone_names
            ]
            if bone_weights:
                total = sum(bone_weights)
                if total > 0:
                    concentrations.append(max(bone_weights) / total)

        max_weight_variance = max(concentrations) if concentrations else 1.0
        norm_rate = normalised_count / total_verts if total_verts else 0.0

        return WeightPaintReport(
            avg_groups_per_vertex=round(avg_groups, 2),
            min_groups_per_vertex=min_groups,
            max_weight_variance=round(max_weight_variance, 4),
            normalization_rate=round(norm_rate, 4),
            score=score,
        )

    def normalize_weights(
        self,
        armature_name: str,
        mesh_name: str,
    ) -> None:
        """Ensure all vertex weight groups sum to 1.0; fix over/under-weighted vertices.

        Must run inside Blender.

        Uses Blender's built-in normalize all groups operation, then
        does a second pass to catch any vertices with zero total weight
        (assigns them to the nearest bone's group with minimal weight).

        Args:
            armature_name: Name of the armature object.
            mesh_name: Name of the mesh object to normalize.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "bpy not available — normalize_weights() must run inside Blender"
            )

        mesh_obj = bpy.data.objects.get(mesh_name)

        if mesh_obj is None:
            logger.error(f"Mesh '{mesh_name}' not found")
            return

        logger.info(f"Normalizing weights on '{mesh_name}'")

        # Use Blender's built-in normalize operation
        # Set the mesh as active object
        bpy.context.view_layer.objects.active = mesh_obj
        mesh_obj.select_set(True)

        # Select all vertices
        bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
        bpy.ops.mesh.select_all(action="SELECT")

        # Normalize all groups (Lock-Free)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)

        bpy.ops.object.mode_set(mode="OBJECT")

        # Second pass: fix zero-weight vertices
        # Vertices with zero total weight should be assigned to at least one group
        armature = bpy.data.objects.get(armature_name)
        if armature is None:
            logger.warning(f"Armature '{armature_name}' not found for zero-weight fix")
            return

        bone_names = {b.name for b in armature.data.bones}
        zero_count = 0

        for vert in mesh_obj.data.vertices:
            total_weight = sum(g.weight for g in vert.groups)
            if total_weight < 0.001:
                # Zero-weight vertex — find the nearest bone-based group
                # and assign minimal weight
                for vg in mesh_obj.vertex_groups:
                    if vg.name in bone_names:
                        vg.add([vert.index], 0.001, "ADD")
                        zero_count += 1
                        break

        if zero_count > 0:
            logger.info(f"Fixed {zero_count} zero-weight vertices")
            # Re-normalize after fixing zero-weight vertices
            bpy.context.view_layer.objects.active = mesh_obj
            mesh_obj.select_set(True)
            bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.object.vertex_group_normalize_all(lock_active=False)
            bpy.ops.object.mode_set(mode="OBJECT")

        logger.info(f"Weight normalization complete for '{mesh_name}'")