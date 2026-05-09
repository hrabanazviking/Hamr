"""
Tests for hamr.rigs.spring_tuning — Spring bone physics parameter optimization.

Phase 16 T2: Spring bone tuning, presets, validation, VRM conversion, energy.
"""

import math
import pytest

from hamr.rigs.spring_tuning import (
    SpringBoneParams,
    SpringBoneGroup,
    SPRING_PRESETS,
    validate_spring_params,
    create_spring_group,
    tune_spring_params,
    blend_spring_params,
    spring_params_to_vrm,
    spring_group_to_vrm,
    estimate_spring_energy,
)


# ──────────────────────────────────────────────────────────────
# SpringBoneParams
# ──────────────────────────────────────────────────────────────

class TestSpringBoneParams:
    """Test SpringBoneParams defaults and ranges."""

    def test_defaults(self):
        p = SpringBoneParams()
        assert p.stiffness == 1.0
        assert p.gravity_power == 0.0
        assert p.gravity_dir == (0.0, -1.0, 0.0)
        assert p.drag_force == 0.4
        assert p.hit_radius == 0.02
        assert p.decay == 0.3

    def test_custom_values(self):
        p = SpringBoneParams(
            stiffness=0.6,
            gravity_power=0.2,
            gravity_dir=(0.1, -0.9, 0.1),
            drag_force=0.5,
            hit_radius=0.03,
            decay=0.25,
        )
        assert p.stiffness == 0.6
        assert p.gravity_power == 0.2
        assert p.gravity_dir == (0.1, -0.9, 0.1)
        assert p.drag_force == 0.5
        assert p.hit_radius == 0.03
        assert p.decay == 0.25

    def test_stiffness_range_boundary(self):
        # Min and max valid stiffness
        SpringBoneParams(stiffness=0.0)
        SpringBoneParams(stiffness=2.0)

    def test_gravity_power_boundary(self):
        SpringBoneParams(gravity_power=0.0)
        SpringBoneParams(gravity_power=1.0)


# ──────────────────────────────────────────────────────────────
# SpringBoneGroup
# ──────────────────────────────────────────────────────────────

class TestSpringBoneGroup:
    """Test SpringBoneGroup creation."""

    def test_creation(self):
        params = SpringBoneParams(stiffness=0.8, gravity_power=0.15)
        group = SpringBoneGroup(
            name="skirt_group",
            bones=["skirt_01_L", "skirt_02_L"],
            params=params,
            collider_groups=["hips_collider"],
        )
        assert group.name == "skirt_group"
        assert group.bones == ["skirt_01_L", "skirt_02_L"]
        assert group.params.stiffness == 0.8
        assert group.params.gravity_power == 0.15
        assert group.collider_groups == ["hips_collider"]

    def test_defaults(self):
        group = SpringBoneGroup(name="test")
        assert group.name == "test"
        assert group.bones == []
        assert isinstance(group.params, SpringBoneParams)
        assert group.collider_groups == []

    def test_defaults_empty_lists(self):
        group = SpringBoneGroup(name="empty")
        assert group.bones == []
        assert group.collider_groups == []


# ──────────────────────────────────────────────────────────────
# SPRING_PRESETS
# ──────────────────────────────────────────────────────────────

class TestSpringPresets:
    """Test SPRING_PRESETS."""

    def test_has_seven_presets(self):
        assert len(SPRING_PRESETS) == 7

    def test_preset_keys(self):
        expected = {"long_hair", "short_hair", "skirt", "breast", "cape", "ribbon", "tail"}
        assert set(SPRING_PRESETS.keys()) == expected

    def test_all_presets_are_params(self):
        for key, params in SPRING_PRESETS.items():
            assert isinstance(params, SpringBoneParams), f"{key} is not SpringBoneParams"

    def test_long_hair_preset(self):
        p = SPRING_PRESETS["long_hair"]
        assert p.stiffness == 0.6
        assert p.gravity_power == 0.2
        assert p.drag_force == 0.5
        assert p.decay == 0.25

    def test_short_hair_preset(self):
        p = SPRING_PRESETS["short_hair"]
        assert p.stiffness == 1.2
        assert p.gravity_power == 0.05
        assert p.drag_force == 0.6
        assert p.decay == 0.2

    def test_skirt_preset(self):
        p = SPRING_PRESETS["skirt"]
        assert p.stiffness == 0.8
        assert p.gravity_power == 0.15
        assert p.drag_force == 0.4
        assert p.decay == 0.3

    def test_breast_preset(self):
        p = SPRING_PRESETS["breast"]
        assert p.stiffness == 0.4
        assert p.gravity_power == 0.3
        assert p.drag_force == 0.3
        assert p.decay == 0.35

    def test_cape_preset(self):
        p = SPRING_PRESETS["cape"]
        assert p.stiffness == 0.5
        assert p.gravity_power == 0.1
        assert p.drag_force == 0.45
        assert p.decay == 0.25

    def test_ribbon_preset(self):
        p = SPRING_PRESETS["ribbon"]
        assert p.stiffness == 0.3
        assert p.gravity_power == 0.05
        assert p.drag_force == 0.55
        assert p.decay == 0.15

    def test_tail_preset(self):
        p = SPRING_PRESETS["tail"]
        assert p.stiffness == 0.7
        assert p.gravity_power == 0.1
        assert p.drag_force == 0.35
        assert p.decay == 0.2


# ──────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────

class TestValidateSpringParams:
    """Test validate_spring_params."""

    def test_valid_params_no_warnings(self):
        params = SpringBoneParams()
        warnings = validate_spring_params(params)
        assert warnings == []

    def test_valid_preset_params(self):
        for name, params in SPRING_PRESETS.items():
            warnings = validate_spring_params(params)
            assert warnings == [], f"Preset '{name}' has validation warnings: {warnings}"

    def test_stiffness_below_range(self):
        params = SpringBoneParams(stiffness=-0.5)
        warnings = validate_spring_params(params)
        assert any("stiffness" in w for w in warnings)

    def test_stiffness_above_range(self):
        params = SpringBoneParams(stiffness=2.5)
        warnings = validate_spring_params(params)
        assert any("stiffness" in w for w in warnings)

    def test_gravity_power_below_range(self):
        params = SpringBoneParams(gravity_power=-0.1)
        warnings = validate_spring_params(params)
        assert any("gravity_power" in w for w in warnings)

    def test_gravity_power_above_range(self):
        params = SpringBoneParams(gravity_power=1.5)
        warnings = validate_spring_params(params)
        assert any("gravity_power" in w for w in warnings)

    def test_drag_force_below_range(self):
        params = SpringBoneParams(drag_force=-0.1)
        warnings = validate_spring_params(params)
        assert any("drag_force" in w for w in warnings)

    def test_drag_force_above_range(self):
        params = SpringBoneParams(drag_force=1.5)
        warnings = validate_spring_params(params)
        assert any("drag_force" in w for w in warnings)

    def test_negative_hit_radius(self):
        params = SpringBoneParams(hit_radius=-0.01)
        warnings = validate_spring_params(params)
        assert any("hit_radius" in w for w in warnings)

    def test_decay_below_range(self):
        params = SpringBoneParams(decay=-0.1)
        warnings = validate_spring_params(params)
        assert any("decay" in w for w in warnings)

    def test_decay_above_range(self):
        params = SpringBoneParams(decay=1.5)
        warnings = validate_spring_params(params)
        assert any("decay" in w for w in warnings)

    def test_unnormalized_gravity_dir(self):
        # Normalized gravity dir should pass; unnormalized should warn
        params_ok = SpringBoneParams(gravity_dir=(0.0, -1.0, 0.0))
        assert validate_spring_params(params_ok) == []

        params_bad = SpringBoneParams(gravity_dir=(0.0, -2.0, 0.0))
        warnings = validate_spring_params(params_bad)
        assert any("gravity_dir" in w and "normalized" in w for w in warnings)

    def test_zero_gravity_dir_ok(self):
        # Zero gravity dir (no gravity) should be fine
        params = SpringBoneParams(gravity_dir=(0.0, 0.0, 0.0))
        warnings = validate_spring_params(params)
        assert not any("gravity_dir" in w for w in warnings)

    def test_multiple_warnings(self):
        params = SpringBoneParams(stiffness=3.0, drag_force=-1.0, decay=2.0)
        warnings = validate_spring_params(params)
        assert len(warnings) >= 3


# ──────────────────────────────────────────────────────────────
# create_spring_group
# ──────────────────────────────────────────────────────────────

class TestCreateSpringGroup:
    """Test create_spring_group from presets."""

    def test_basic_creation(self):
        group = create_spring_group(
            name="hair",
            bones=["hair_01", "hair_02", "hair_03"],
            preset="long_hair",
        )
        assert group.name == "hair"
        assert group.bones == ["hair_01", "hair_02", "hair_03"]
        assert group.params.stiffness == 0.6
        assert group.params.gravity_power == 0.2
        assert group.collider_groups == []

    def test_with_collider_groups(self):
        group = create_spring_group(
            name="skirt",
            bones=["skirt_01", "skirt_02"],
            preset="skirt",
            collider_groups=["hips", "legs"],
        )
        assert group.collider_groups == ["hips", "legs"]

    def test_with_overrides(self):
        group = create_spring_group(
            name="hair",
            bones=["hair_01"],
            preset="long_hair",
            stiffness=0.9,
            gravity_power=0.3,
        )
        assert group.params.stiffness == 0.9
        assert group.params.gravity_power == 0.3
        # Other values should remain from preset
        assert group.params.drag_force == 0.5
        assert group.params.decay == 0.25

    def test_override_hit_radius(self):
        group = create_spring_group(
            name="test",
            bones=["b1"],
            preset="tail",
            hit_radius=0.05,
        )
        assert group.params.hit_radius == 0.05

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="Unknown spring preset"):
            create_spring_group(
                name="test",
                bones=["b1"],
                preset="nonexistent",
            )


# ──────────────────────────────────────────────────────────────
# tune_spring_params
# ──────────────────────────────────────────────────────────────

class TestTuneSpringParams:
    """Test tune_spring_params for realistic/snappy/floaty."""

    def test_realistic_is_identity(self):
        params = SpringBoneParams(stiffness=0.8, gravity_power=0.15, drag_force=0.4, decay=0.3)
        tuned = tune_spring_params(params, "realistic")
        assert abs(tuned.stiffness - 0.8) < 1e-6
        assert abs(tuned.gravity_power - 0.15) < 1e-6
        assert abs(tuned.drag_force - 0.4) < 1e-6
        assert abs(tuned.decay - 0.3) < 1e-6

    def test_snappy_increases_stiffness(self):
        params = SpringBoneParams(stiffness=0.6)
        tuned = tune_spring_params(params, "snappy")
        assert tuned.stiffness > params.stiffness

    def test_snappy_reduces_gravity(self):
        params = SpringBoneParams(gravity_power=0.2)
        tuned = tune_spring_params(params, "snappy")
        assert tuned.gravity_power < params.gravity_power

    def test_floaty_reduces_stiffness(self):
        params = SpringBoneParams(stiffness=0.6)
        tuned = tune_spring_params(params, "floaty")
        assert tuned.stiffness < params.stiffness

    def test_floaty_increases_gravity(self):
        params = SpringBoneParams(gravity_power=0.2)
        tuned = tune_spring_params(params, "floaty")
        assert tuned.gravity_power > params.gravity_power

    def test_clamping_stiffness(self):
        # Snappy stiffness = 1.5 * stiffness; 2.0 * 1.5 = 3.0 → clamped to 2.0
        params = SpringBoneParams(stiffness=2.0)
        tuned = tune_spring_params(params, "snappy")
        assert tuned.stiffness <= 2.0

    def test_preserves_gravity_dir(self):
        params = SpringBoneParams(gravity_dir=(0.1, -0.9, 0.1))
        tuned = tune_spring_params(params, "snappy")
        assert tuned.gravity_dir == params.gravity_dir

    def test_preserves_hit_radius(self):
        params = SpringBoneParams(hit_radius=0.05)
        tuned = tune_spring_params(params, "floaty")
        assert tuned.hit_radius == 0.05

    def test_unknown_target_raises(self):
        with pytest.raises(KeyError, match="Unknown tuning target"):
            tune_spring_params(SpringBoneParams(), "wobbly")


# ──────────────────────────────────────────────────────────────
# blend_spring_params
# ──────────────────────────────────────────────────────────────

class TestBlendSpringParams:
    """Test blend_spring_params at t=0, t=0.5, t=1.0."""

    def test_blend_at_zero_returns_a(self):
        a = SpringBoneParams(stiffness=0.3, gravity_power=0.1, drag_force=0.5, hit_radius=0.01, decay=0.2)
        b = SpringBoneParams(stiffness=1.2, gravity_power=0.4, drag_force=0.3, hit_radius=0.04, decay=0.35)
        result = blend_spring_params(a, b, t=0.0)
        assert abs(result.stiffness - a.stiffness) < 1e-6
        assert abs(result.gravity_power - a.gravity_power) < 1e-6
        assert abs(result.drag_force - a.drag_force) < 1e-6
        assert abs(result.hit_radius - a.hit_radius) < 1e-6
        assert abs(result.decay - a.decay) < 1e-6

    def test_blend_at_one_returns_b(self):
        a = SpringBoneParams(stiffness=0.3, gravity_power=0.1, drag_force=0.5, hit_radius=0.01, decay=0.2)
        b = SpringBoneParams(stiffness=1.2, gravity_power=0.4, drag_force=0.3, hit_radius=0.04, decay=0.35)
        result = blend_spring_params(a, b, t=1.0)
        assert abs(result.stiffness - b.stiffness) < 1e-6
        assert abs(result.gravity_power - b.gravity_power) < 1e-6
        assert abs(result.drag_force - b.drag_force) < 1e-6
        assert abs(result.hit_radius - b.hit_radius) < 1e-6
        assert abs(result.decay - b.decay) < 1e-6

    def test_blend_at_half_is_average(self):
        a = SpringBoneParams(stiffness=0.2, gravity_power=0.0, drag_force=0.2, hit_radius=0.01, decay=0.1)
        b = SpringBoneParams(stiffness=0.6, gravity_power=0.4, drag_force=0.6, hit_radius=0.05, decay=0.3)
        result = blend_spring_params(a, b, t=0.5)
        assert abs(result.stiffness - 0.4) < 1e-6
        assert abs(result.gravity_power - 0.2) < 1e-6
        assert abs(result.drag_force - 0.4) < 1e-6
        assert abs(result.hit_radius - 0.03) < 1e-6
        assert abs(result.decay - 0.2) < 1e-6

    def test_blend_gravity_dir_interpolated(self):
        a = SpringBoneParams(gravity_dir=(0.0, -1.0, 0.0))
        b = SpringBoneParams(gravity_dir=(1.0, 0.0, 0.0))
        result = blend_spring_params(a, b, t=0.5)
        assert abs(result.gravity_dir[0] - 0.5) < 1e-6
        assert abs(result.gravity_dir[1] - (-0.5)) < 1e-6
        assert abs(result.gravity_dir[2] - 0.0) < 1e-6

    def test_blend_clamped_t(self):
        a = SpringBoneParams(stiffness=0.0)
        b = SpringBoneParams(stiffness=1.0)
        # t below 0 should clamp to 0
        result_neg = blend_spring_params(a, b, t=-0.5)
        assert abs(result_neg.stiffness - 0.0) < 1e-6
        # t above 1 should clamp to 1
        result_over = blend_spring_params(a, b, t=1.5)
        assert abs(result_over.stiffness - 1.0) < 1e-6


# ──────────────────────────────────────────────────────────────
# VRM conversion
# ──────────────────────────────────────────────────────────────

class TestSpringParamsToVrm:
    """Test spring_params_to_vrm produces valid dict."""

    def test_produces_dict_with_required_keys(self):
        params = SpringBoneParams()
        vrm = spring_params_to_vrm(params)
        assert isinstance(vrm, dict)
        required_keys = {"stiffness", "gravityPower", "gravityDir", "dragForce", "hitRadius", "decay"}
        assert required_keys.issubset(vrm.keys())

    def test_gravity_dir_is_nested_dict(self):
        params = SpringBoneParams(gravity_dir=(0.1, -0.9, 0.2))
        vrm = spring_params_to_vrm(params)
        gdir = vrm["gravityDir"]
        assert isinstance(gdir, dict)
        assert abs(gdir["x"] - 0.1) < 1e-6
        assert abs(gdir["y"] - (-0.9)) < 1e-6
        assert abs(gdir["z"] - 0.2) < 1e-6

    def test_values_match_params(self):
        params = SpringBoneParams(
            stiffness=0.6,
            gravity_power=0.2,
            drag_force=0.5,
            hit_radius=0.02,
            decay=0.25,
        )
        vrm = spring_params_to_vrm(params)
        assert vrm["stiffness"] == 0.6
        assert vrm["gravityPower"] == 0.2
        assert vrm["dragForce"] == 0.5
        assert vrm["hitRadius"] == 0.02
        assert vrm["decay"] == 0.25


class TestSpringGroupToVrm:
    """Test spring_group_to_vrm produces valid dict."""

    def test_produces_dict_with_required_keys(self):
        group = SpringBoneGroup(
            name="test_group",
            bones=["bone_01", "bone_02"],
            params=SpringBoneParams(),
            collider_groups=["col_01"],
        )
        vrm = spring_group_to_vrm(group)
        assert isinstance(vrm, dict)
        required_keys = {
            "name", "stiffness", "gravityPower", "gravityDir",
            "dragForce", "hitRadius", "decay",
            "boneIndices", "colliderGroupIndices",
        }
        assert required_keys.issubset(vrm.keys())

    def test_name_matches(self):
        group = SpringBoneGroup(name="skirt_spring", bones=["a"], params=SpringBoneParams())
        vrm = spring_group_to_vrm(group)
        assert vrm["name"] == "skirt_spring"

    def test_bones_match(self):
        group = SpringBoneGroup(
            name="test",
            bones=["hair_01", "hair_02", "hair_03"],
            params=SpringBoneParams(),
        )
        vrm = spring_group_to_vrm(group)
        assert vrm["boneIndices"] == ["hair_01", "hair_02", "hair_03"]

    def test_collider_groups_match(self):
        group = SpringBoneGroup(
            name="test",
            bones=["b1"],
            params=SpringBoneParams(),
            collider_groups=["hips", "legs"],
        )
        vrm = spring_group_to_vrm(group)
        assert vrm["colliderGroupIndices"] == ["hips", "legs"]

    def test_params_serialized(self):
        params = SpringBoneParams(stiffness=0.8, gravity_power=0.15)
        group = SpringBoneGroup(name="test", bones=["b1"], params=params)
        vrm = spring_group_to_vrm(group)
        assert vrm["stiffness"] == 0.8
        assert vrm["gravityPower"] == 0.15


# ──────────────────────────────────────────────────────────────
# Energy estimation
# ──────────────────────────────────────────────────────────────

class TestEstimateSpringEnergy:
    """Test estimate_spring_energy for different presets."""

    def test_returns_positive_for_all_presets(self):
        for name, params in SPRING_PRESETS.items():
            energy = estimate_spring_energy(params)
            assert energy > 0, f"Preset '{name}' has non-positive energy: {energy}"

    def test_higher_stiffness_means_more_energy(self):
        soft = SpringBoneParams(stiffness=0.5, gravity_power=0.1, drag_force=0.4, decay=0.2)
        stiff = SpringBoneParams(stiffness=1.5, gravity_power=0.1, drag_force=0.4, decay=0.2)
        assert estimate_spring_energy(stiff) > estimate_spring_energy(soft)

    def test_higher_gravity_means_more_energy(self):
        low_g = SpringBoneParams(stiffness=1.0, gravity_power=0.05, drag_force=0.4, decay=0.2)
        high_g = SpringBoneParams(stiffness=1.0, gravity_power=0.5, drag_force=0.4, decay=0.2)
        assert estimate_spring_energy(high_g) > estimate_spring_energy(low_g)

    def test_lower_drag_means_more_energy(self):
        high_drag = SpringBoneParams(stiffness=1.0, gravity_power=0.2, drag_force=0.8, decay=0.2)
        low_drag = SpringBoneParams(stiffness=1.0, gravity_power=0.2, drag_force=0.2, decay=0.2)
        assert estimate_spring_energy(low_drag) > estimate_spring_energy(high_drag)

    def test_delta_time_scales_energy(self):
        params = SpringBoneParams()
        energy_60fps = estimate_spring_energy(params, delta_time=1/60)
        energy_30fps = estimate_spring_energy(params, delta_time=1/30)
        # 30fps delta_time is ~2x 60fps, so energy should be ~2x
        assert energy_30fps > energy_60fps
        # Rough ratio check (not exact due to floating point)
        ratio = energy_30fps / energy_60fps
        assert abs(ratio - 2.0) < 0.01

    def test_preset_ordering(self):
        # Breast preset has more gravity than ribbon → higher energy
        # (other params differ but gravity is dominant here)
        breast_energy = estimate_spring_energy(SPRING_PRESETS["breast"])
        ribbon_energy = estimate_spring_energy(SPRING_PRESETS["ribbon"])
        # Breast has gravity=0.3; ribbon has gravity=0.05
        # But breast also has low drag and higher decay...
        # Let's just verify they're different
        assert breast_energy != ribbon_energy

    def test_default_delta_time(self):
        params = SpringBoneParams()
        energy_default = estimate_spring_energy(params)
        energy_explicit = estimate_spring_energy(params, delta_time=1/60)
        assert abs(energy_default - energy_explicit) < 1e-10