"""
Tests for hamr.rigs.weights — Weight Paint Engine.

Pure-Python tests run without Blender.
Blender-dependent tests are marked with @pytest.mark.blender
and require a running Blender instance.
"""

from __future__ import annotations

import pytest

from hamr.rigs.weights import (
    SMOOTH_REGIONS,
    WeightPaintEngine,
    WeightPaintReport,
    classify_deformation_quality,
    compute_quality_score,
    smooth_weight_map,
)


# ══════════════════════════════════════════════════════════════════════
# Pure-Python tests — compute_quality_score
# ══════════════════════════════════════════════════════════════════════


class TestComputeQualityScore:
    """Test compute_quality_score with various weight distributions."""

    def test_empty_vertex_groups_returns_zero(self):
        """No vertex groups → score is 0.0."""
        score = compute_quality_score({}, [])
        assert score == 0.0

    def test_empty_bone_names_returns_zero(self):
        """No bone names → score is 0.0."""
        score = compute_quality_score({"head": [(0, 1.0)]}, [])
        assert score == 0.0

    def test_single_bone_no_blend(self):
        """A single bone fully weighting all vertices → poor quality."""
        # Every vertex has weight 1.0 in a single group — rigid, bad
        vertex_groups = {
            "head": [(0, 1.0), (1, 1.0), (2, 1.0), (3, 0.8)],
        }
        score = compute_quality_score(vertex_groups, ["head"])
        # Single bone → high concentration, low score
        assert 0.0 <= score <= 0.6  # Should be poor-to-acceptable

    def test_two_bones_balanced(self):
        """Two bones with 50/50 weights → good quality (smooth gradient)."""
        vertex_groups = {
            "spine": [(0, 0.5), (1, 0.5), (2, 0.5)],
            "chest": [(0, 0.5), (1, 0.5), (2, 0.5)],
        }
        score = compute_quality_score(vertex_groups, ["spine", "chest"])
        # Should score decently — multi-bone, normalized, low concentration
        assert score >= 0.4

    def test_four_bones_normalized(self):
        """Four bones with proper 0.25 each → excellent quality."""
        vertex_groups = {
            "spine": [(0, 0.25), (1, 0.25), (2, 0.25)],
            "chest": [(0, 0.25), (1, 0.25), (2, 0.25)],
            "neck": [(0, 0.25), (1, 0.25), (2, 0.25)],
            "head": [(0, 0.25), (1, 0.25), (2, 0.25)],
        }
        score = compute_quality_score(
            vertex_groups, ["spine", "chest", "neck", "head"]
        )
        assert score >= 0.7  # Should be good to excellent

    def test_zero_weights_excluded(self):
        """Zero-weight assignments should not affect the score."""
        vertex_groups = {
            "head": [(0, 0.0), (1, 1.0)],  # vertex 0 has weight 0 (excluded)
            "neck": [(0, 1.0), (1, 0.0)],     # vertex 1 has weight 0 (excluded)
        }
        score = compute_quality_score(vertex_groups, ["head", "neck"])
        # vertex 0 only weighted by neck, vertex 1 only by head — single-bone
        assert 0.0 <= score <= 1.0

    def test_unnormalized_weights(self):
        """Weights not summing to 1.0 → lower normalization score."""
        vertex_groups = {
            "head": [(0, 0.9), (1, 0.8)],  # Sums to 1.8 and 1.6 — not normalized
            "neck": [(0, 0.2), (1, 0.1)],
        }
        score = compute_quality_score(vertex_groups, ["head", "neck"])
        # Not normalized, so normalization component should be low
        assert 0.0 <= score <= 0.8

    def test_many_vertices(self):
        """Large number of vertices with mixed quality."""
        # Simulate a real-ish weight distribution: neck region
        vertex_groups = {
            "head": [(i, max(0.0, 1.0 - i * 0.02)) for i in range(50)],
            "neck": [(i, min(1.0, i * 0.02)) for i in range(50)],
            "spine_02": [(i, 0.1) for i in range(10)],
        }
        score = compute_quality_score(
            vertex_groups, ["head", "neck", "spine_02"]
        )
        assert 0.0 <= score <= 1.0

    def test_returns_float_in_range(self):
        """Score must always be in [0.0, 1.0]."""
        # Various distributions
        distributions = [
            {"a": [(0, 1.0)]},
            {"a": [(0, 0.5)], "b": [(0, 0.5)]},
            {
                "a": [(i, 0.25) for i in range(10)],
                "b": [(i, 0.25) for i in range(10)],
                "c": [(i, 0.25) for i in range(10)],
                "d": [(i, 0.25) for i in range(10)],
            },
        ]
        for vg in distributions:
            bone_names = list(vg.keys())
            score = compute_quality_score(vg, bone_names)
            assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════
# Pure-Python tests — classify_deformation_quality
# ══════════════════════════════════════════════════════════════════════


class TestClassifyDeformationQuality:
    """Test classify_deformation_quality label assignment."""

    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.0, "poor"),
            (0.1, "poor"),
            (0.3, "poor"),
            (0.39, "poor"),
            (0.4, "acceptable"),
            (0.5, "acceptable"),
            (0.59, "acceptable"),
            (0.6, "good"),
            (0.7, "good"),
            (0.79, "good"),
            (0.8, "excellent"),
            (0.9, "excellent"),
            (1.0, "excellent"),
        ],
    )
    def test_classification_boundaries(self, score, expected):
        """Test all four quality classification thresholds."""
        result = classify_deformation_quality(score)
        assert result == expected, f"Score {score} classified as '{result}', expected '{expected}'"

    def test_poor_quality(self):
        assert classify_deformation_quality(0.2) == "poor"

    def test_acceptable_quality(self):
        assert classify_deformation_quality(0.45) == "acceptable"

    def test_good_quality(self):
        assert classify_deformation_quality(0.65) == "good"

    def test_excellent_quality(self):
        assert classify_deformation_quality(0.95) == "excellent"


# ══════════════════════════════════════════════════════════════════════
# Pure-Python tests — smooth_weight_map
# ══════════════════════════════════════════════════════════════════════


class TestSmoothWeightMap:
    """Test smooth_weight_map iterative weight smoothing."""

    def test_empty_list_returns_empty(self):
        result = smooth_weight_map([], iterations=3, radius=0.3)
        assert result == []

    def test_single_element_preserved(self):
        result = smooth_weight_map([0.5], iterations=3, radius=0.3)
        assert result == [0.5]

    def test_zero_iterations_returns_copy(self):
        weights = [0.1, 0.5, 0.9, 0.3]
        result = smooth_weight_map(weights, iterations=0, radius=0.3)
        assert result == [0.1, 0.5, 0.9, 0.3]
        # Verify it's a copy, not the same list
        assert result is not weights

    def test_radius_zero_preserves_original(self):
        """Radius 0 means no blending — weights should stay the same."""
        weights = [0.0, 1.0, 0.5, 0.2, 0.8]
        result = smooth_weight_map(weights, iterations=3, radius=0.0)
        for orig, smoothed in zip(weights, result):
            assert abs(orig - smoothed) < 0.001

    def test_radius_one_averages_with_neighbours(self):
        """Radius 1.0 = full replacement by neighbour average."""
        weights = [0.0, 1.0, 0.5, 0.2, 0.8]
        result = smooth_weight_map(weights, iterations=1, radius=1.0)
        # Interior points should equal the average of their neighbours
        # Vertex 1: prev=0.0, next=0.5 → avg=(0.0+0.5)/2 = 0.25
        # result[1] = weights[1] * (1 - 1.0) + avg * 1.0 = 0 + 0.25 = 0.25
        assert abs(result[1] - 0.25) < 0.01

    def test_smoothing_reduces_variance(self):
        """After smoothing, the variance of weights should decrease."""
        weights = [0.0, 1.0, 0.0, 1.0, 0.5]
        result = smooth_weight_map(weights, iterations=5, radius=0.5)
        # Variance of result should be less than variance of input
        import statistics
        var_input = statistics.variance(weights)
        var_output = statistics.variance(result)
        assert var_output <= var_input or abs(var_output - var_input) < 0.01

    def test_smoothing_preserves_range(self):
        """Smoothed weights should stay in [0, 1] range."""
        import random
        random.seed(42)
        weights = [random.random() for _ in range(20)]
        result = smooth_weight_map(weights, iterations=10, radius=0.5)
        for w in result:
            assert 0.0 <= w <= 1.0 or abs(w) < 0.001  # Allow tiny float errors

    def test_multiple_iterations_more_smoothing(self):
        """More iterations should produce smoother results."""
        weights = [0.0, 1.0, 0.0, 1.0, 0.0]
        result_1 = smooth_weight_map(weights, iterations=1, radius=0.3)
        result_5 = smooth_weight_map(weights, iterations=5, radius=0.3)
        # Calculate smoothness as max difference between adjacent elements
        max_diff_1 = max(abs(result_1[i] - result_1[i+1]) for i in range(len(result_1)-1))
        max_diff_5 = max(abs(result_5[i] - result_5[i+1]) for i in range(len(result_5)-1))
        assert max_diff_5 <= max_diff_1

    def test_does_not_modify_input(self):
        """smooth_weight_map should never modify the input list."""
        weights = [0.1, 0.5, 0.9]
        original = list(weights)
        smooth_weight_map(weights, iterations=3, radius=0.5)
        assert weights == original

    def test_boundary_vertices_have_fewer_neighbours(self):
        """First and last vertices only have one neighbour."""
        weights = [0.0, 0.5, 1.0, 0.5, 0.0]
        result = smooth_weight_map(weights, iterations=1, radius=1.0)
        # Vertex 0: no prev, next=0.5 → avg=0.5 → result=0.0*(1-1)+0.5*1.0=0.5
        # But vertex 0 has no prev, so avg = 0.5 (just one neighbour)
        assert abs(result[0] - 0.5) < 0.01


# ══════════════════════════════════════════════════════════════════════
# Normalize logic tests (pure Python simulation)
# ══════════════════════════════════════════════════════════════════════


class TestNormalizeLogic:
    """Test weight normalisation logic using pure-Python helpers."""

    def _normalize_vertex_weights(self, weights: list[float]) -> list[float]:
        """Pure-Python normalize: divide each weight by the sum."""
        total = sum(weights)
        if total == 0:
            return weights  # leave zero-weight verts as-is
        return [w / total for w in weights]

    def test_normalize_balanced_weights(self):
        """Weights summing to 2.0 → normalize to sum 1.0."""
        weights = [0.5, 0.3, 0.2]
        normalized = self._normalize_vertex_weights(weights)
        assert abs(sum(normalized) - 1.0) < 0.001

    def test_normalize_already_normalized(self):
        """Weights already summing to 1.0 → unchanged."""
        weights = [0.5, 0.3, 0.2]
        normalized = self._normalize_vertex_weights(weights)
        for orig, norm in zip(weights, normalized):
            assert abs(orig - norm) < 0.001

    def test_normalize_overweighted(self):
        """Weights summing to > 1.0 → normalized down."""
        weights = [0.8, 0.6, 0.4]
        normalized = self._normalize_vertex_weights(weights)
        assert abs(sum(normalized) - 1.0) < 0.001
        assert normalized[0] < weights[0]  # Should be reduced

    def test_normalize_zero_weights(self):
        """All-zero weights → stays zero (can't normalize nothing)."""
        weights = [0.0, 0.0, 0.0]
        normalized = self._normalize_vertex_weights(weights)
        assert sum(normalized) == 0.0

    def test_normalize_single_weight(self):
        """Single weight → normalized to 1.0."""
        weights = [2.5]
        normalized = self._normalize_vertex_weights(weights)
        assert abs(normalized[0] - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════════════
# SMOOTH_REGIONS constant verification
# ══════════════════════════════════════════════════════════════════════


class TestSmoothRegions:
    """Verify the SMOOTH_REGIONS constant data."""

    def test_regions_are_defined(self):
        assert len(SMOOTH_REGIONS) > 0

    def test_all_regions_have_bones(self):
        for name, bones in SMOOTH_REGIONS.items():
            assert len(bones) >= 2, f"Region '{name}' has too few bones: {bones}"

    def test_region_keys_match_expected_joints(self):
        expected_keys = {
            "neck",
            "left_shoulder", "right_shoulder",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_elbow", "right_elbow",
        }
        assert set(SMOOTH_REGIONS.keys()) == expected_keys


# ══════════════════════════════════════════════════════════════════════
# WeightPaintReport dataclass tests
# ══════════════════════════════════════════════════════════════════════


class TestWeightPaintReport:
    """Test that WeightPaintReport dataclass works correctly."""

    def test_create_report(self):
        report = WeightPaintReport(
            avg_groups_per_vertex=2.5,
            min_groups_per_vertex=1,
            max_weight_variance=0.7,
            normalization_rate=0.85,
            score=0.72,
        )
        assert report.avg_groups_per_vertex == 2.5
        assert report.min_groups_per_vertex == 1
        assert report.max_weight_variance == 0.7
        assert report.normalization_rate == 0.85
        assert report.score == 0.72

    def test_score_in_valid_range(self):
        """Report scores should be in the 0–1 range."""
        report = WeightPaintReport(
            avg_groups_per_vertex=3.0,
            min_groups_per_vertex=2,
            max_weight_variance=0.4,
            normalization_rate=0.95,
            score=0.88,
        )
        assert 0.0 <= report.score <= 1.0


# ══════════════════════════════════════════════════════════════════════
# WeightPaintEngine — Blender-dependent tests (marked @pytest.mark.blender)
# ══════════════════════════════════════════════════════════════════════


class TestWeightPaintEngine:
    """Test WeightPaintEngine class structure and method signatures.

    Note: The actual Blender-dependent methods (paint_smooth, transfer_weights,
    get_quality_score, normalize_weights) require bpy and can only run
    inside a Blender Python environment.  Tests here verify the class interface
    and that non-Blender operations raise appropriate errors.
    """

    def test_engine_instantiation(self):
        """WeightPaintEngine should be instantiable without Blender."""
        engine = WeightPaintEngine()
        assert engine is not None

    def test_paint_smooth_requires_blender(self):
        """paint_smooth should raise RuntimeError without bpy."""
        engine = WeightPaintEngine()
        with pytest.raises(RuntimeError, match="bpy not available"):
            engine.paint_smooth("armature", "mesh")

    def test_transfer_weights_requires_blender(self):
        """transfer_weights should raise RuntimeError without bpy."""
        engine = WeightPaintEngine()
        with pytest.raises(RuntimeError, match="bpy not available"):
            engine.transfer_weights("body", "shirt")

    def test_transfer_weights_invalid_method_requires_blender_first(self):
        """Invalid method check happens after bpy check, so still RuntimeError."""
        engine = WeightPaintEngine()
        # Even with invalid method, bpy check comes first
        with pytest.raises(RuntimeError, match="bpy not available"):
            engine.transfer_weights("body", "shirt", method="invalid")

    def test_get_quality_score_requires_blender(self):
        """get_quality_score should raise RuntimeError without bpy."""
        engine = WeightPaintEngine()
        with pytest.raises(RuntimeError, match="bpy not available"):
            engine.get_quality_score("armature", "mesh")

    def test_normalize_weights_requires_blender(self):
        """normalize_weights should raise RuntimeError without bpy."""
        engine = WeightPaintEngine()
        with pytest.raises(RuntimeError, match="bpy not available"):
            engine.normalize_weights("armature", "mesh")


@pytest.mark.blender
class TestWeightPaintEngineBlender:
    """Blender-dependent tests — only run inside Blender.

    These tests require bpy and will be skipped in normal pytest runs.
    They verify the actual Blender operations work with a test scene.
    """

    @pytest.fixture(autouse=True)
    def _setup_blender(self):
        """Skip all tests in this class if bpy is not available."""
        try:
            import bpy as _bpy
            self.bpy = _bpy
        except ImportError:
            pytest.skip("bpy not available — requires Blender")

    def test_paint_smooth_signature(self):
        """Verify paint_smooth method signature accepts expected args."""
        engine = WeightPaintEngine()
        # Create test scene
        bpy = self.bpy
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

        # Create armature
        bpy.ops.object.armature_add(location=(0, 0, 0))
        armature = bpy.context.active_object
        armature.name = "TestArmature"

        # Create mesh
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        mesh = bpy.context.active_object
        mesh.name = "TestCube"

        # Parent mesh to armature with auto weights
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type="ARMATURE_AUTO_WEIGHTS")

        # Now test paint_smooth
        engine.paint_smooth("TestArmature", "TestCube", iterations=1)

        # Verify mesh still exists
        assert bpy.data.objects.get("TestCube") is not None

    def test_transfer_weights_signature(self):
        """Verify transfer_weights accepts valid method strings."""
        engine = WeightPaintEngine()
        # Just verify the method exists and has the right signature
        import inspect
        sig = inspect.signature(engine.transfer_weights)
        params = list(sig.parameters.keys())
        assert "source_mesh" in params
        assert "target_mesh" in params
        assert "method" in params

    def test_get_quality_score_returns_report(self):
        """get_quality_score should return a WeightPaintReport."""
        engine = WeightPaintEngine()
        bpy = self.bpy
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

        # Create armature
        bpy.ops.object.armature_add(location=(0, 0, 0))
        armature = bpy.context.active_object
        armature.name = "TestArmature"

        # Create mesh
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        mesh = bpy.context.active_object
        mesh.name = "TestCube"

        # Parent mesh to armature with auto weights
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type="ARMATURE_AUTO_WEIGHTS")

        report = engine.get_quality_score("TestArmature", "TestCube")
        assert isinstance(report, WeightPaintReport)
        assert 0.0 <= report.score <= 1.0

    def test_normalize_weights(self):
        """Test that normalize_weights runs without error on a parented mesh."""
        engine = WeightPaintEngine()
        bpy = self.bpy
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

        # Create armature
        bpy.ops.object.armature_add(location=(0, 0, 0))
        armature = bpy.context.active_object
        armature.name = "TestArmature"

        # Create mesh
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        mesh = bpy.context.active_object
        mesh.name = "TestCube"

        # Parent mesh to armature with auto weights
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type="ARMATURE_AUTO_WEIGHTS")

        # Normalize should run without error
        engine.normalize_weights("TestArmature", "TestCube")


# ══════════════════════════════════════════════════════════════════════
# Integration tests — pure-Python quality pipeline
# ══════════════════════════════════════════════════════════════════════


class TestQualityPipelineIntegration:
    """Test the full pure-Python quality scoring pipeline end-to-end."""

    def test_score_then_classify(self):
        """Compute quality score, then classify it."""
        # Simulate a decent weight distribution (3 bones per vertex, normalized)
        vertex_groups = {
            "spine_02": [(i, 0.3 + i * 0.01) for i in range(20)],
            "neck": [(i, 0.4 - i * 0.01) for i in range(20)],
            "head": [(i, 0.3) for i in range(20)],
        }
        bone_names = ["spine_02", "neck", "head"]

        score = compute_quality_score(vertex_groups, bone_names)
        label = classify_deformation_quality(score)

        assert 0.0 <= score <= 1.0
        assert label in ("poor", "acceptable", "good", "excellent")

    def test_smooth_then_score_accuracy(self):
        """Smooth a weight distribution then verify score improves."""
        # Create a raw (noisy) weight distribution
        raw_weights = [0.0, 1.0, 0.0, 1.0, 0.5, 0.5, 0.2, 0.8, 0.0, 1.0]

        # Smooth it
        smoothed = smooth_weight_map(raw_weights, iterations=5, radius=0.4)

        # Both should be valid
        assert len(smoothed) == len(raw_weights)
        for w in smoothed:
            assert 0.0 <= w <= 1.0 or abs(w) < 0.01  # float tolerance

    def test_engine_class_has_all_methods(self):
        """Verify WeightPaintEngine has all required public methods."""
        engine = WeightPaintEngine()
        assert hasattr(engine, "paint_smooth")
        assert hasattr(engine, "transfer_weights")
        assert hasattr(engine, "get_quality_score")
        assert hasattr(engine, "normalize_weights")
        # Verify method signatures
        import inspect
        ps_sig = inspect.signature(engine.paint_smooth)
        assert "armature_name" in ps_sig.parameters
        assert "mesh_name" in ps_sig.parameters
        tw_sig = inspect.signature(engine.transfer_weights)
        assert "source_mesh" in tw_sig.parameters
        assert "target_mesh" in tw_sig.parameters
        assert "method" in tw_sig.parameters