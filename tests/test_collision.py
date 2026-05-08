"""
Tests for collision mesh generation — VRM 1.0 spring bone colliders.

Every shield a sphere, every sphere a guard against clipping.
Phase 12 (Yggdrasil): The roots drink from geometry.
"""

import pytest
from dataclasses import fields

from hamr.rigs.collision import (
    COLLIDER_REGIONS,
    CollisionMeshResult,
    CollisionMeshGenerator,
    compute_collider_radius,
    compute_collision_mesh_summary,
    generate_collider_list,
    validate_collision_config,
)


# ──────────────────────────────────────────────────────────────
# COLLIDER_REGIONS structure tests
# ──────────────────────────────────────────────────────────────

class TestColliderRegions:
    """Test the COLLIDER_REGIONS registry."""

    def test_regions_count(self):
        """COLLIDER_REGIONS should contain 12+ body regions."""
        assert len(COLLIDER_REGIONS) >= 12

    def test_required_regions_present(self):
        """All specified body regions must be present."""
        required = [
            "head", "neck", "upper_chest", "chest", "spine", "hips",
            "left_shoulder", "right_shoulder",
            "left_upper_arm", "right_upper_arm",
            "left_thigh", "right_thigh",
        ]
        for region in required:
            assert region in COLLIDER_REGIONS, f"Missing region: {region}"

    def test_region_keys_valid(self):
        """Every region must have bone, radius, and offset keys."""
        for region_name, region_data in COLLIDER_REGIONS.items():
            assert "bone" in region_data, f"{region_name} missing 'bone'"
            assert "radius" in region_data, f"{region_name} missing 'radius'"
            assert "offset" in region_data, f"{region_name} missing 'offset'"

    def test_bone_names_are_strings(self):
        """Bone names must be non-empty strings."""
        for region_name, region_data in COLLIDER_REGIONS.items():
            assert isinstance(region_data["bone"], str), (
                f"{region_name}: bone must be str"
            )
            assert len(region_data["bone"]) > 0, (
                f"{region_name}: bone must be non-empty"
            )

    def test_radii_are_positive(self):
        """All radii must be positive floats."""
        for region_name, region_data in COLLIDER_REGIONS.items():
            assert isinstance(region_data["radius"], (int, float)), (
                f"{region_name}: radius must be numeric"
            )
            assert region_data["radius"] > 0, (
                f"{region_name}: radius must be positive, got {region_data['radius']}"
            )

    def test_offsets_are_3_tuples(self):
        """Offset values must be 3-element tuples of numbers."""
        for region_name, region_data in COLLIDER_REGIONS.items():
            assert isinstance(region_data["offset"], tuple), (
                f"{region_name}: offset must be tuple"
            )
            assert len(region_data["offset"]) == 3, (
                f"{region_name}: offset must have 3 elements"
            )
            for i, v in enumerate(region_data["offset"]):
                assert isinstance(v, (int, float)), (
                    f"{region_name}: offset[{i}] must be numeric"
                )


# ──────────────────────────────────────────────────────────────
# CollisionMeshResult dataclass tests
# ──────────────────────────────────────────────────────────────

class TestCollisionMeshResult:
    """Test CollisionMeshResult creation and defaults."""

    def test_create_result(self):
        """CollisionMeshResult can be created with required fields."""
        result = CollisionMeshResult(
            collider_name="head_collider",
            mesh_name="collider_head_sphere",
            bone_name="head",
            radius=0.08,
            position=(0.0, 0.0, 0.0),
        )
        assert result.collider_name == "head_collider"
        assert result.mesh_name == "collider_head_sphere"
        assert result.bone_name == "head"
        assert result.radius == 0.08
        assert result.position == (0.0, 0.0, 0.0)

    def test_default_created_true(self):
        """Default value of 'created' should be True."""
        result = CollisionMeshResult(
            collider_name="test",
            mesh_name="test_mesh",
            bone_name="bone",
            radius=0.1,
            position=(0, 0, 0),
        )
        assert result.created is True

    def test_default_warnings_empty(self):
        """Default value of 'warnings' should be an empty list."""
        result = CollisionMeshResult(
            collider_name="test",
            mesh_name="test_mesh",
            bone_name="bone",
            radius=0.1,
            position=(0, 0, 0),
        )
        assert result.warnings == []

    def test_warnings_independent(self):
        """Each instance should have its own warnings list."""
        r1 = CollisionMeshResult(
            collider_name="a", mesh_name="ma", bone_name="ba",
            radius=0.1, position=(0, 0, 0),
        )
        r2 = CollisionMeshResult(
            collider_name="b", mesh_name="mb", bone_name="bb",
            radius=0.2, position=(0, 0, 0),
        )
        r1.warnings.append("test")
        assert len(r1.warnings) == 1
        assert len(r2.warnings) == 0

    def test_created_can_be_false(self):
        """The 'created' field can be set to False."""
        result = CollisionMeshResult(
            collider_name="test",
            mesh_name="test_mesh",
            bone_name="bone",
            radius=0.1,
            position=(0, 0, 0),
            created=False,
        )
        assert result.created is False

    def test_fields_count(self):
        """CollisionMeshResult should have exactly 7 fields."""
        assert len(fields(CollisionMeshResult)) == 7


# ──────────────────────────────────────────────────────────────
# compute_collider_radius tests
# ──────────────────────────────────────────────────────────────

class TestComputeColliderRadius:
    """Test compute_collider_radius lookups and scaling."""

    def test_known_bone_head(self):
        """'head' bone should return radius 0.08 at scale 1.0."""
        assert compute_collider_radius("head") == pytest.approx(0.08)

    def test_known_bone_spine1(self):
        """'spine1' (chest) should return radius 0.12 at scale 1.0."""
        assert compute_collider_radius("spine1") == pytest.approx(0.12)

    def test_known_bone_hips(self):
        """'hips' should return radius 0.14 at scale 1.0."""
        assert compute_collider_radius("hips") == pytest.approx(0.14)

    def test_scale_factor(self):
        """Radius should scale linearly with body_scale."""
        r_default = compute_collider_radius("head", body_scale=1.0)
        r_scaled = compute_collider_radius("head", body_scale=1.5)
        assert r_scaled == pytest.approx(r_default * 1.5)

    def test_all_known_bones_have_radius(self):
        """Every bone in COLLIDER_REGIONS should have a positive radius."""
        for region_name, region_data in COLLIDER_REGIONS.items():
            radius = compute_collider_radius(region_data["bone"])
            assert radius > 0, f"Zero radius for {region_name}/{region_data['bone']}"

    def test_unknown_bone_returns_fallback(self):
        """Unknown bone names should return the fallback radius 0.05."""
        radius = compute_collider_radius("totally_fake_bone_xyz")
        assert radius == pytest.approx(0.05)

    def test_unknown_bone_scaled(self):
        """Fallback radius should also scale with body_scale."""
        radius = compute_collider_radius("fake_bone", body_scale=2.0)
        assert radius == pytest.approx(0.05 * 2.0)

    def test_left_shoulder(self):
        """leftShoulder bone lookup."""
        assert compute_collider_radius("leftShoulder") == pytest.approx(0.05)

    def test_right_upper_arm(self):
        """rightUpperArm bone lookup."""
        assert compute_collider_radius("rightUpperArm") == pytest.approx(0.04)


# ──────────────────────────────────────────────────────────────
# generate_collider_list tests
# ──────────────────────────────────────────────────────────────

class TestGenerateColliderList:
    """Test collider list generation."""

    def test_default_generates_all_regions(self):
        """Default call generates colliders for all COLLIDER_REGIONS."""
        colliders = generate_collider_list()
        assert len(colliders) == len(COLLIDER_REGIONS)

    def test_collider_names_match_regions(self):
        """Each collider_name should follow the '{region}_collider' convention."""
        colliders = generate_collider_list()
        for c in colliders:
            assert c.collider_name.endswith("_collider"), (
                f"Unexpected collider name: {c.collider_name}"
            )

    def test_mesh_names_follow_convention(self):
        """Each mesh_name should follow 'collider_{region}_sphere'."""
        colliders = generate_collider_list()
        for c in colliders:
            assert c.mesh_name.startswith("collider_"), (
                f"Unexpected mesh name: {c.mesh_name}"
            )
            assert c.mesh_name.endswith("_sphere"), (
                f"Unexpected mesh name: {c.mesh_name}"
            )

    def test_default_created_is_false(self):
        """Without Blender, generated colliders should have created=False."""
        colliders = generate_collider_list()
        for c in colliders:
            assert c.created is False

    def test_body_scale_affects_radius(self):
        """body_scale should scale all radii."""
        default = generate_collider_list(body_scale=1.0)
        scaled = generate_collider_list(body_scale=2.0)
        for d, s in zip(default, scaled):
            assert s.radius == pytest.approx(d.radius * 2.0)

    def test_spec_override_radius(self):
        """Spec can override radius for a region."""
        spec = {"head": {"radius": 0.15}}
        colliders = generate_collider_list(spec=spec)
        head_collider = [c for c in colliders if c.bone_name == "head"][0]
        assert head_collider.radius == pytest.approx(0.15)

    def test_spec_override_bone(self):
        """Spec can override bone for a region."""
        spec = {"head": {"bone": "head_end"}}
        colliders = generate_collider_list(spec=spec)
        head_collider = [c for c in colliders if c.collider_name == "head_collider"][0]
        assert head_collider.bone_name == "head_end"

    def test_spec_override_offset(self):
        """Spec can override offset for a region."""
        spec = {"chest": {"offset": (0.01, 0.02, 0.03)}}
        colliders = generate_collider_list(spec=spec)
        chest = [c for c in colliders if c.collider_name == "chest_collider"][0]
        assert chest.position == (0.01, 0.02, 0.03)

    def test_spec_disable_region(self):
        """Spec with enabled=False should exclude that region."""
        spec = {"hips": {"enabled": False}}
        colliders = generate_collider_list(spec=spec)
        region_names = [c.collider_name for c in colliders]
        assert "hips_collider" not in region_names

    def test_spec_scale_combined(self):
        """Both spec override and body_scale should apply."""
        spec = {"head": {"radius": 0.15}}
        colliders = generate_collider_list(spec=spec, body_scale=2.0)
        head = [c for c in colliders if c.bone_name == "head"][0]
        # Override radius 0.15 * scale 2.0 = 0.30
        assert head.radius == pytest.approx(0.30)

    def test_large_radius_warning(self):
        """Radius > 1.0 should generate a warning."""
        spec = {"head": {"radius": 1.5}}
        colliders = generate_collider_list(spec=spec)
        head = [c for c in colliders if c.bone_name == "head"][0]
        assert any("Large radius" in w for w in head.warnings)

    def test_zero_radius_warning(self):
        """Radius <= 0 should generate a warning."""
        spec = {"head": {"radius": 0.0}}
        colliders = generate_collider_list(spec=spec)
        head = [c for c in colliders if c.bone_name == "head"][0]
        assert any("Non-positive" in w for w in head.warnings)


# ──────────────────────────────────────────────────────────────
# compute_collision_mesh_summary tests
# ──────────────────────────────────────────────────────────────

class TestComputeCollisionMeshSummary:
    """Test collision mesh summary computation."""

    def test_empty_list(self):
        """Empty collider list should produce zero-count summary."""
        summary = compute_collision_mesh_summary([])
        assert summary["count"] == 0
        assert summary["total_radius_avg"] == 0.0
        assert summary["regions"] == {}

    def test_count_matches_list(self):
        """Summary count should match collider list length."""
        colliders = generate_collider_list()
        summary = compute_collision_mesh_summary(colliders)
        assert summary["count"] == len(colliders)

    def test_average_radius(self):
        """Average radius should be the mean of all collider radii."""
        colliders = generate_collider_list(body_scale=1.0)
        summary = compute_collision_mesh_summary(colliders)
        expected_avg = sum(c.radius for c in colliders) / len(colliders)
        assert summary["total_radius_avg"] == pytest.approx(expected_avg)

    def test_regions_keys_match_names(self):
        """Region dict keys should be collider names."""
        colliders = generate_collider_list()
        summary = compute_collision_mesh_summary(colliders)
        for name in [c.collider_name for c in colliders]:
            assert name in summary["regions"]

    def test_regions_contain_bone(self):
        """Each region entry should contain the bone name."""
        colliders = generate_collider_list()
        summary = compute_collision_mesh_summary(colliders)
        for c in colliders:
            assert summary["regions"][c.collider_name]["bone"] == c.bone_name


# ──────────────────────────────────────────────────────────────
# validate_collision_config tests
# ──────────────────────────────────────────────────────────────

class TestValidateCollisionConfig:
    """Test collision configuration validation."""

    def test_valid_empty_spec(self):
        """Empty spec should produce no warnings."""
        warnings = validate_collision_config({})
        assert warnings == []

    def test_valid_override_radius(self):
        """Valid radius override should produce no warnings."""
        warnings = validate_collision_config({"head": {"radius": 0.1}})
        assert warnings == []

    def test_unknown_region(self):
        """Unknown region name should produce a warning."""
        warnings = validate_collision_config({"nonexistent_region": {"radius": 0.1}})
        assert len(warnings) == 1
        assert "Unknown collider region" in warnings[0]

    def test_negative_radius(self):
        """Negative radius should produce a warning."""
        warnings = validate_collision_config({"head": {"radius": -0.5}})
        assert any("positive" in w for w in warnings)

    def test_zero_radius(self):
        """Zero radius should produce a warning."""
        warnings = validate_collision_config({"head": {"radius": 0}})
        assert any("positive" in w for w in warnings)

    def test_excessively_large_radius(self):
        """Radius > 2.0 should produce a warning."""
        warnings = validate_collision_config({"head": {"radius": 3.0}})
        assert any("excessively large" in w for w in warnings)

    def test_invalid_offset_wrong_length(self):
        """Offset with wrong length should produce a warning."""
        warnings = validate_collision_config({"head": {"offset": (1, 2)}})
        assert any("3-element" in w for w in warnings)

    def test_invalid_offset_non_numeric(self):
        """Offset with non-numeric values should produce a warning."""
        warnings = validate_collision_config({"head": {"offset": (1, "x", 3)}})
        assert any("numeric" in w for w in warnings)

    def test_empty_bone_name(self):
        """Empty bone name should produce a warning."""
        warnings = validate_collision_config({"head": {"bone": ""}})
        assert any("non-empty" in w for w in warnings)

    def test_non_string_bone(self):
        """Non-string bone name should produce a warning."""
        warnings = validate_collision_config({"head": {"bone": 42}})
        assert any("non-empty string" in w for w in warnings)

    def test_non_dict_override(self):
        """Non-dict override value should produce a warning."""
        warnings = validate_collision_config({"head": "not_a_dict"})
        assert any("dict" in w for w in warnings)

    def test_non_numeric_radius(self):
        """Non-numeric radius value should produce a warning."""
        warnings = validate_collision_config({"head": {"radius": "big"}})
        assert any("numeric" in w for w in warnings)

    def test_multiple_warnings(self):
        """Multiple issues should all appear."""
        spec = {
            "head": {"radius": -0.1, "bone": ""},
            "fake_region": {"radius": 5.0},
        }
        warnings = validate_collision_config(spec)
        assert len(warnings) >= 3  # negative radius, empty bone, unknown region


# ──────────────────────────────────────────────────────────────
# CollisionMeshGenerator tests (Blender-dependent)
# ──────────────────────────────────────────────────────────────

@pytest.mark.blender
class TestCollisionMeshGenerator:
    """Test CollisionMeshGenerator — requires Blender."""

    def test_generator_requires_bpy(self):
        """CollisionMeshGenerator.generate() should raise RuntimeError without bpy."""
        from hamr.rigs.collision import BLENDER_AVAILABLE
        if BLENDER_AVAILABLE:
            pytest.skip("bpy is available — cannot test RuntimeError path")
        gen = CollisionMeshGenerator()
        with pytest.raises(RuntimeError, match="bpy not available"):
            gen.generate()

    def test_create_collider_sphere_requires_bpy(self):
        """CollisionMeshGenerator.create_collider_sphere() raises without bpy."""
        from hamr.rigs.collision import BLENDER_AVAILABLE
        if BLENDER_AVAILABLE:
            pytest.skip("bpy is available — cannot test RuntimeError path")
        gen = CollisionMeshGenerator()
        with pytest.raises(RuntimeError, match="bpy not available"):
            gen.create_collider_sphere("test", "head", 0.1)


class TestCollisionMeshGeneratorWithoutBpy:
    """Test that CollisionMeshGenerator raises RuntimeError without bpy."""

    def test_generate_raises_without_bpy(self):
        """generate() should raise RuntimeError if bpy is unavailable."""
        # This test works regardless of whether bpy is available
        # by checking the guard directly
        import hamr.rigs.collision as collision_mod
        original_available = collision_mod.BLENDER_AVAILABLE
        try:
            collision_mod.BLENDER_AVAILABLE = False
            gen = CollisionMeshGenerator()
            with pytest.raises(RuntimeError, match="bpy not available"):
                gen.generate(spec=None, armature_name=None)
        finally:
            collision_mod.BLENDER_AVAILABLE = original_available

    def test_create_collider_sphere_raises_without_bpy(self):
        """create_collider_sphere() should raise RuntimeError without bpy."""
        import hamr.rigs.collision as collision_mod
        original_available = collision_mod.BLENDER_AVAILABLE
        try:
            collision_mod.BLENDER_AVAILABLE = False
            gen = CollisionMeshGenerator()
            with pytest.raises(RuntimeError, match="bpy not available"):
                gen.create_collider_sphere("test", "head", 0.1)
        finally:
            collision_mod.BLENDER_AVAILABLE = original_available