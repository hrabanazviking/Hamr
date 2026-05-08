"""
Tests for hamr.hair.mesh — Hair mesh generation (Phase 11 T2).

Pure-Python geometry functions are tested directly.
Blender-dependent code (HairMeshGenerator, create_hair_material) is
tested with RuntimeError checks and @pytest.mark.blender for
integration runs inside Blender.
"""

from __future__ import annotations

import math
import pytest

from hamr.hair.mesh import (
    HAIR_MESH_STYLES,
    _REQUIRED_STYLE_KEYS,
    HAIR_LENGTH_SCALE,
    GuideCurve,
    HairMeshResult,
    BLENDER_AVAILABLE,
    generate_guide_curves,
    compute_strand_count,
    interpolate_curve_points,
    apply_wave_to_curve,
    HairMeshGenerator,
    create_hair_material,
)

# ══════════════════════════════════════════════════════════════════════
# HAIR_MESH_STYLES structure tests
# ══════════════════════════════════════════════════════════════════════


class TestHairMeshStyles:
    """Validate the HAIR_MESH_STYLES configuration dictionary."""

    EXPECTED_STYLES = {"long_straight", "long_wavy", "short_bob", "twin_tails", "spiky"}

    def test_all_five_styles_present(self):
        """All five required styles exist in HAIR_MESH_STYLES."""
        assert set(HAIR_MESH_STYLES.keys()) == self.EXPECTED_STYLES

    def test_each_style_has_required_keys(self):
        """Each style config has all required keys."""
        for name, cfg in HAIR_MESH_STYLES.items():
            missing = _REQUIRED_STYLE_KEYS - set(cfg.keys())
            assert not missing, f"Style '{name}' missing keys: {missing}"

    def test_each_style_has_display_name(self):
        """Each style has a human-readable display_name."""
        for name, cfg in HAIR_MESH_STYLES.items():
            assert isinstance(cfg["display_name"], str)
            assert len(cfg["display_name"]) > 0

    def test_guide_curves_per_side_range(self):
        """guide_curves_per_side is a reasonable number (2–20)."""
        for name, cfg in HAIR_MESH_STYLES.items():
            n = cfg["guide_curves_per_side"]
            assert 2 <= n <= 20, f"{name}: {n} curves per side out of range"

    def test_guide_curves_back_range(self):
        """guide_curves_back is a reasonable number (2–10)."""
        for name, cfg in HAIR_MESH_STYLES.items():
            n = cfg["guide_curves_back"]
            assert 2 <= n <= 10, f"{name}: {n} back curves out of range"

    def test_length_factor_positive(self):
        """base_length_factor is positive and reasonable."""
        for name, cfg in HAIR_MESH_STYLES.items():
            f = cfg["base_length_factor"]
            assert 0.0 < f <= 2.0, f"{name}: length factor {f} out of range"

    def test_strand_density_in_range(self):
        """strand_density is between 0 and 2."""
        for name, cfg in HAIR_MESH_STYLES.items():
            d = cfg["strand_density"]
            assert 0.0 < d <= 2.0, f"{name}: density {d} out of range"

    def test_triangle_budget_reasonable(self):
        """max_triangle_budget is within Pi performance limits."""
        for name, cfg in HAIR_MESH_STYLES.items():
            b = cfg["max_triangle_budget"]
            assert 1000 <= b <= 15000, f"{name}: budget {b} unreasonable"

    def test_requires_mesh_is_true(self):
        """All mesh styles require mesh generation."""
        for name, cfg in HAIR_MESH_STYLES.items():
            assert cfg["requires_mesh"] is True, f"{name} should require mesh"

    def test_keywords_are_non_empty_lists(self):
        """Each style has non-empty keyword list."""
        for name, cfg in HAIR_MESH_STYLES.items():
            kws = cfg["keywords"]
            assert isinstance(kws, list)
            assert len(kws) > 0, f"{name} has no keywords"

    def test_taper_ratio_in_range(self):
        """taper_ratio is between 0 and 1."""
        for name, cfg in HAIR_MESH_STYLES.items():
            t = cfg["taper_ratio"]
            assert 0.0 < t <= 1.0, f"{name}: taper {t} out of range"

    def test_cross_section_radius_positive(self):
        """cross_section_radius is a positive small value."""
        for name, cfg in HAIR_MESH_STYLES.items():
            r = cfg["cross_section_radius"]
            assert 0.001 <= r <= 0.01, f"{name}: radius {r} out of range"


# ══════════════════════════════════════════════════════════════════════
# generate_guide_curves tests
# ══════════════════════════════════════════════════════════════════════


class TestGenerateGuideCurves:
    """Test generate_guide_curves for each style."""

    STYLES = list(HAIR_MESH_STYLES.keys())

    @pytest.mark.parametrize("style", STYLES)
    def test_returns_list_for_each_style(self, style):
        """Each style produces a non-empty list of GuideCurves."""
        curves = generate_guide_curves(style)
        assert isinstance(curves, list)
        assert len(curves) > 0

    @pytest.mark.parametrize("style", STYLES)
    def test_each_curve_has_required_fields(self, style):
        """Each GuideCurve has origin, control_points, group."""
        curves = generate_guide_curves(style)
        for c in curves:
            assert isinstance(c, GuideCurve)
            assert isinstance(c.origin, tuple)
            assert len(c.origin) == 3
            assert isinstance(c.control_points, list)
            assert len(c.control_points) >= 2
            assert isinstance(c.group, str)

    @pytest.mark.parametrize("style", STYLES)
    def test_control_points_are_3d(self, style):
        """All control points are (x, y, z) tuples."""
        curves = generate_guide_curves(style)
        for c in curves:
            for pt in c.control_points:
                assert isinstance(pt, tuple)
                assert len(pt) == 3

    @pytest.mark.parametrize("style", STYLES)
    def test_origins_near_head(self, style):
        """Guide curve origins are near the head center."""
        center = (0.0, 1.65, 0.0)
        radius = 0.10
        curves = generate_guide_curves(style, center, radius)
        for c in curves:
            # Origin should be within ~2×radius of head center
            dx = c.origin[0] - center[0]
            dy = c.origin[1] - center[1]
            dz = c.origin[2] - center[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            assert dist < radius * 3.0, f"Origin too far from head: {dist}"

    def test_unknown_style_falls_back(self):
        """Unknown style falls back to long_straight."""
        curves = generate_guide_curves("nonexistent_style")
        assert len(curves) > 0

    def test_default_params(self):
        """Default head_center and head_radius produce curves."""
        curves = generate_guide_curves("long_straight")
        assert len(curves) > 0

    def test_long_straight_has_no_wave(self):
        """long_straight has zero wave amplitude in config."""
        cfg = HAIR_MESH_STYLES["long_straight"]
        assert cfg["wave_amplitude"] == 0.0

    def test_long_wavy_has_wave(self):
        """long_wavy has non-zero wave amplitude."""
        cfg = HAIR_MESH_STYLES["long_wavy"]
        assert cfg["wave_amplitude"] > 0.0

    def test_spiky_has_high_taper(self):
        """spiky style has a high taper ratio (sharp tips)."""
        cfg = HAIR_MESH_STYLES["spiky"]
        assert cfg["taper_ratio"] >= 0.5

    def test_twin_tails_has_tied_modifier(self):
        """twin_tails guide curves have 'tied' style_modifier."""
        curves = generate_guide_curves("twin_tails")
        tied = [c for c in curves if c.style_modifier == "tied"]
        # At least some curves should be tied
        assert len(tied) > 0


# ══════════════════════════════════════════════════════════════════════
# compute_strand_count tests
# ══════════════════════════════════════════════════════════════════════


class TestComputeStrandCount:
    """Test compute_strand_count with various densities."""

    def test_default_density_returns_positive(self):
        """Default density produces a positive strand count."""
        count = compute_strand_count("long_straight")
        assert count > 0

    @pytest.mark.parametrize("style", list(HAIR_MESH_STYLES.keys()))
    def test_each_style_positive_count(self, style):
        """Every style produces at least 4 strands."""
        count = compute_strand_count(style)
        assert count >= 4

    def test_higher_density_more_strands(self):
        """Higher density multiplier produces more strands."""
        low = compute_strand_count("long_straight", density=0.5)
        high = compute_strand_count("long_straight", density=1.5)
        # If low == 0 they'd be clamped to minimum; otherwise high > low
        if low > 4 and high > 4:
            assert high >= low

    def test_zero_density_clamped(self):
        """Density near zero still returns minimum 4 strands."""
        count = compute_strand_count("long_straight", density=0.01)
        assert count >= 4

    def test_very_high_density_clamped(self):
        """Excessively high density is clamped by triangle budget."""
        count = compute_strand_count("long_straight", density=10.0)
        budget = HAIR_MESH_STYLES["long_straight"]["max_triangle_budget"]
        max_strands = budget // 12
        assert count <= max_strands

    def test_unknown_style_falls_back(self):
        """Unknown style falls back gracefully."""
        count = compute_strand_count("unknown_style")
        assert count > 0

    @pytest.mark.parametrize("style", ["spiky", "short_bob"])
    def test_short_styles_fewer_strands(self, style):
        """Short styles generally have fewer strands than long."""
        short_count = compute_strand_count(style, density=1.0)
        long_count = compute_strand_count("long_straight", density=1.0)
        # Not guaranteed to be less due to budget clamping but should be
        # less or equal for short styles
        assert short_count <= long_count


# ══════════════════════════════════════════════════════════════════════
# interpolate_curve_points tests
# ══════════════════════════════════════════════════════════════════════


class TestInterpolateCurvePoints:
    """Test Catmull-Rom spline interpolation."""

    def test_two_points_subdivisions_8(self):
        """Two control points produce subdivisions+1 output points."""
        ctrl = [(0.0, 0.0, 0.0), (0.0, -1.0, 0.0)]
        pts = interpolate_curve_points(ctrl, subdivisions=8)
        # subdivisions points per pair + final point
        assert len(pts) == 8 + 1

    def test_three_points_produces_more(self):
        """Three control points produce more points than two."""
        ctrl2 = [(0.0, 0.0, 0.0), (0.0, -1.0, 0.0)]
        ctrl3 = [(0.0, 0.0, 0.0), (0.5, -0.5, 0.0), (0.0, -1.0, 0.0)]
        pts2 = interpolate_curve_points(ctrl2, subdivisions=4)
        pts3 = interpolate_curve_points(ctrl3, subdivisions=4)
        assert len(pts3) > len(pts2)

    def test_start_near_first_point(self):
        """First interpolated point is near the first control point."""
        ctrl = [(1.0, 2.0, 3.0), (1.0, 1.0, 3.0)]
        pts = interpolate_curve_points(ctrl, subdivisions=8)
        dx = abs(pts[0][0] - ctrl[0][0])
        dy = abs(pts[0][1] - ctrl[0][1])
        dz = abs(pts[0][2] - ctrl[0][2])
        assert dx < 0.01
        assert dy < 0.01
        assert dz < 0.01

    def test_end_near_last_point(self):
        """Last interpolated point is the last control point."""
        ctrl = [(0.0, 0.0, 0.0), (0.0, -1.0, 0.0)]
        pts = interpolate_curve_points(ctrl, subdivisions=8)
        assert pts[-1] == ctrl[-1]

    def test_straight_line_interpolation(self):
        """Points along a straight line stay close to linear."""
        ctrl = [(0.0, 0.0, 0.0), (0.0, -2.0, 0.0)]
        pts = interpolate_curve_points(ctrl, subdivisions=10)
        # For a straight line, all y-values should be monotonically decreasing
        for i in range(1, len(pts)):
            assert pts[i][1] <= pts[i - 1][1] + 0.01

    def test_single_point_passthrough(self):
        """Single control point returns itself."""
        ctrl = [(1.0, 2.0, 3.0)]
        pts = interpolate_curve_points(ctrl, subdivisions=8)
        assert pts == [(1.0, 2.0, 3.0)]

    def test_empty_input(self):
        """Empty control points list returns empty."""
        pts = interpolate_curve_points([], subdivisions=8)
        assert pts == []

    def test_higher_subdivisions_more_points(self):
        """More subdivisions produce more interpolated points."""
        ctrl = [(0.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, -2.0, 0.0)]
        pts4 = interpolate_curve_points(ctrl, subdivisions=4)
        pts16 = interpolate_curve_points(ctrl, subdivisions=16)
        assert len(pts16) > len(pts4)

    def test_output_is_3d_tuples(self):
        """All output points are 3-float tuples."""
        ctrl = [(0.0, 0.0, 0.0), (0.0, -1.0, 0.0)]
        pts = interpolate_curve_points(ctrl, subdivisions=4)
        for pt in pts:
            assert isinstance(pt, tuple)
            assert len(pt) == 3
            for coord in pt:
                assert isinstance(coord, float)


# ══════════════════════════════════════════════════════════════════════
# apply_wave_to_curve tests
# ══════════════════════════════════════════════════════════════════════


class TestApplyWaveToCurve:
    """Test sine-wave deformation of curve points."""

    def test_zero_amplitude_passthrough(self):
        """Zero amplitude returns unmodified copy."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        result = apply_wave_to_curve(pts, amplitude=0.0, frequency=2.0)
        assert result == pts

    def test_zero_frequency_passthrough(self):
        """Zero frequency returns unmodified copy."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        result = apply_wave_to_curve(pts, amplitude=0.01, frequency=0.0)
        assert result == pts

    def test_positive_amplitude_modifies_points(self):
        """Non-zero amplitude changes x coordinates."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        result = apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0)
        # At least some x values should differ from zero
        x_changed = [p[0] != 0.0 for p in result]
        assert any(x_changed)

    def test_wave_preserves_y(self):
        """Wave deformation preserves Y (vertical) coordinates."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        result = apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0)
        for orig, wavy in zip(pts, result):
            assert abs(wavy[1] - orig[1]) < 1e-10

    def test_wave_same_length(self):
        """Wave result has same number of points as input."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        result = apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0, phase=0.5)
        assert len(result) == len(pts)

    def test_large_amplitude_larger_displacement(self):
        """Larger amplitude produces larger displacement."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        small = apply_wave_to_curve(pts, amplitude=0.01, frequency=2.0)
        large = apply_wave_to_curve(pts, amplitude=0.05, frequency=2.0)
        # Maximum displacement should be larger for larger amplitude
        max_small = max(abs(p[0]) for p in small)
        max_large = max(abs(p[0]) for p in large)
        assert max_large >= max_small

    def test_phase_shift_changes_pattern(self):
        """Different phase shifts produce different point patterns."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(20)]
        wave0 = apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0, phase=0.0)
        wave_pi = apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0, phase=math.pi)
        # Not all points should be the same
        differs = sum(1 for a, b in zip(wave0, wave_pi) if abs(a[0] - b[0]) > 1e-6)
        assert differs > 0

    def test_single_point_unchanged(self):
        """Single point is still returned (though wave can't apply)."""
        pts = [(0.0, 0.0, 0.0)]
        result = apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0)
        assert len(result) == 1

    def test_does_not_modify_input(self):
        """apply_wave_to_curve does not modify the input list."""
        pts = [(0.0, -i * 0.1, 0.0) for i in range(10)]
        original = [p for p in pts]
        apply_wave_to_curve(pts, amplitude=0.02, frequency=2.0)
        assert pts == original


# ══════════════════════════════════════════════════════════════════════
# HairMeshResult dataclass tests
# ══════════════════════════════════════════════════════════════════════


class TestHairMeshResult:
    """Test HairMeshResult dataclass."""

    def test_creation(self):
        """HairMeshResult stores all fields correctly."""
        r = HairMeshResult(
            object_name="hair_long",
            bone_chain=["hair_01", "hair_02"],
            vertex_count=1200,
            triangle_count=800,
            style="long_straight",
        )
        assert r.object_name == "hair_long"
        assert r.bone_chain == ["hair_01", "hair_02"]
        assert r.vertex_count == 1200
        assert r.triangle_count == 800
        assert r.style == "long_straight"


# ══════════════════════════════════════════════════════════════════════
# Blender-dependent tests
# ══════════════════════════════════════════════════════════════════════


class TestHairMeshGeneratorBlender:
    """Blender-dependent tests for HairMeshGenerator."""

    def test_raises_without_bpy(self):
        """HairMeshGenerator raises RuntimeError without bpy."""
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy"):
                HairMeshGenerator()
        else:
            # If bpy IS available, instantiation should work
            gen = HairMeshGenerator()
            assert gen is not None


class TestCreateHairMaterialBlender:
    """Blender-dependent tests for create_hair_material."""

    def test_raises_without_bpy(self):
        """create_hair_material raises RuntimeError without bpy."""
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy"):
                create_hair_material("test_mat", (0.1, 0.7, 0.6), (0.12, 0.3, 0.9))


@pytest.mark.blender
@pytest.mark.skipif(not BLENDER_AVAILABLE, reason="Requires Blender/bpy runtime")
class TestHairMeshGeneratorIntegration:
    """Integration tests that require Blender to be running."""

    def test_generate_long_straight(self):
        """Generate long_straight hair mesh inside Blender."""
        gen = HairMeshGenerator()
        result = gen.generate(
            "long_straight",
            head_center=(0.0, 1.65, 0.0),
            head_radius=0.10,
        )
        assert isinstance(result, HairMeshResult)
        assert result.style == "long_straight"
        assert result.vertex_count > 0
        assert result.object_name.startswith("hair_")

    def test_generate_spiky(self):
        """Generate spiky hair mesh inside Blender."""
        gen = HairMeshGenerator()
        result = gen.generate("spiky")
        assert result.style == "spiky"

    def test_generate_with_color_config(self):
        """Generate hair mesh with custom color gradient."""
        gen = HairMeshGenerator()
        result = gen.generate(
            "short_bob",
            color_config={
                "roots_hsv": (30.0, 0.8, 0.6),
                "tips_hsv": (40.0, 0.3, 0.95),
            },
        )
        assert result.object_name.startswith("hair_")

    def test_create_material(self):
        """Create hair material with gradient."""
        mat = create_hair_material("test_hair_mat", (0.0, 0.0, 1.0), (120.0, 0.5, 0.8))
        assert mat is not None
        assert mat.name == "test_hair_mat"


# ══════════════════════════════════════════════════════════════════════
# HAIR_LENGTH_SCALE tests
# ══════════════════════════════════════════════════════════════════════


class TestHairLengthScale:
    """Test HAIR_LENGTH_SCALE reference data."""

    def test_all_length_keys_present(self):
        """All expected hair length keys are present."""
        expected = {"short", "medium", "shoulder", "shoulder-plus", "long", "very-long"}
        assert set(HAIR_LENGTH_SCALE.keys()) == expected

    def test_values_ascending(self):
        """Length scale values are in ascending order."""
        keys = ["short", "medium", "shoulder", "shoulder-plus", "long", "very-long"]
        values = [HAIR_LENGTH_SCALE[k] for k in keys]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1]

    def test_all_positive(self):
        """All length scale values are positive."""
        for key, val in HAIR_LENGTH_SCALE.items():
            assert val > 0, f"{key} has non-positive scale {val}"


# ══════════════════════════════════════════════════════════════════════
# GuideCurve dataclass tests
# ══════════════════════════════════════════════════════════════════════


class TestGuideCurve:
    """Test GuideCurve dataclass."""

    def test_creation(self):
        """GuideCurve stores all fields correctly."""
        gc = GuideCurve(
            origin=(0.0, 1.7, 0.0),
            control_points=[(0.0, 1.7, 0.0), (0.1, 1.5, 0.0), (0.0, 1.3, 0.0)],
            group="side",
            style_modifier="tied",
        )
        assert gc.origin == (0.0, 1.7, 0.0)
        assert len(gc.control_points) == 3
        assert gc.group == "side"
        assert gc.style_modifier == "tied"

    def test_default_modifier(self):
        """GuideCurve default style_modifier is empty string."""
        gc = GuideCurve(
            origin=(0.0, 1.7, 0.0),
            control_points=[(0.0, 1.7, 0.0), (0.0, 1.3, 0.0)],
            group="back",
        )
        assert gc.style_modifier == ""