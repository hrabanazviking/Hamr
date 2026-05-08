"""
Tests for build_avatar Phase 12 integration — wiring all Phase 11 modules.

Tests cover pure-Python functions from build_avatar.py integration helpers,
plus the pipeline_integrate module's planning, validation, and result tracking.
Blender-dependent tests are marked with @pytest.mark.blender.
"""

import pytest
from dataclasses import dataclass, field, asdict
from unittest.mock import MagicMock, patch

from hamr.core.pipeline_integrate import (
    IntegrationResult,
    STAGE_STUB_BONES,
    STAGE_HAIR_MESH,
    STAGE_CLOTHING_MESH,
    STAGE_WEIGHT_PAINT,
    STAGE_SPRING_BONES,
    STAGE_FIRST_PERSON,
    ALL_STAGES,
    plan_stages,
    estimate_stage_time,
    validate_spec_completeness,
    _get_attr,
)
from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    HairSpec,
    HairColorSpec,
    ClothingSpec,
    PhysicsSpec,
    HairPhysicsSpec,
)
from hamr.rigs.stub_bones import (
    StubBoneResult,
    detect_missing_bones,
    get_stub_bone_map,
    STUB_BONE_DEFS,
)


# ──────────────────────────────────────────────────────────────────────────────
# Test: build_avatar module imports correctly (pure-Python parts)
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildAvatarImport:
    """Test that build_avatar.py can be parsed and its pure-Python parts work."""

    def test_import_module_outside_blender(self):
        """build_avatar should be importable — bpy import is guarded with try/except."""
        # This should NOT raise ImportError even outside Blender
        # The module uses try/except ImportError for bpy
        import importlib
        spec = importlib.util.find_spec("hamr.scripts.build_avatar")
        # The module should be findable
        assert spec is not None

    def test_hex_to_hsv_function(self):
        """_hex_to_hsv is a pure-Python helper used by integration."""
        from hamr.scripts.build_avatar import _hex_to_hsv
        # Basic test
        h, s, v = _hex_to_hsv("#FF0000")
        assert abs(h - 0.0) < 0.01  # Red hue ≈ 0
        assert abs(s - 1.0) < 0.01
        assert abs(v - 1.0) < 0.01

        # Black
        h, s, v = _hex_to_hsv("#000000")
        assert abs(v) < 0.01

        # White
        h, s, v = _hex_to_hsv("#FFFFFF")
        assert abs(s) < 0.01
        assert abs(v - 1.0) < 0.01

    def test_dict_to_clothing_spec(self):
        """_dict_to_clothing_spec converts dicts to ClothingSpec dataclasses."""
        from hamr.scripts.build_avatar import _dict_to_clothing_spec

        # Dict conversion
        result = _dict_to_clothing_spec({"name": "shirt", "type": "tshirt", "primary_hex": "#333"})
        assert isinstance(result, ClothingSpec)
        assert result.name == "shirt"
        assert result.type == "tshirt"
        assert result.primary_hex == "#333"

        # Already a ClothingSpec
        spec = ClothingSpec(name="pants", type="pants")
        result = _dict_to_clothing_spec(spec)
        assert result is spec

        # Default values
        result = _dict_to_clothing_spec({})
        assert isinstance(result, ClothingSpec)
        assert "clothing" in result.name  # default name format "clothing_0"

    def test_dict_to_clothing_spec_index(self):
        """_dict_to_clothing_spec uses index for default names."""
        from hamr.scripts.build_avatar import _dict_to_clothing_spec

        result = _dict_to_clothing_spec({}, index=3)
        assert result.name == "clothing_3"


# ──────────────────────────────────────────────────────────────────────────────
# Test: IntegrationResult from pipeline_integrate
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegrationResult:
    """Test that IntegrationResult dataclass works correctly."""

    def test_default_result(self):
        result = IntegrationResult()
        assert result.stages_completed == []
        assert result.stub_bones_applied is False
        assert result.hair_meshes_created == []
        assert result.clothing_meshes_created == []
        assert result.weight_paint_applied is False
        assert result.spring_bones_configured is False
        assert result.first_person_configured is False
        assert result.warnings == []
        assert result.errors == []
        assert result.elapsed_seconds == 0.0

    def test_success_property(self):
        result = IntegrationResult()
        assert result.success is True

        result.errors.append("something went wrong")
        assert result.success is False

    def test_stage_count(self):
        result = IntegrationResult()
        assert result.stage_count == 0

        result.stages_completed = ["stub_bones", "hair_mesh"]
        assert result.stage_count == 2

    def test_repr(self):
        result = IntegrationResult()
        assert "✓" in repr(result)
        assert "0/6 stages" in repr(result)

        result.errors.append("fail")
        assert "✗" in repr(result)

    def test_full_result(self):
        result = IntegrationResult(
            stages_completed=ALL_STAGES,
            stub_bones_applied=True,
            hair_meshes_created=["hair_mesh"],
            clothing_meshes_created=["shirt_mesh", "skirt_mesh"],
            weight_paint_applied=True,
            spring_bones_configured=True,
            first_person_configured=True,
            elapsed_seconds=14.2,
        )
        assert result.success is True
        assert result.stage_count == 6
        assert "14.2s" in repr(result)


# ──────────────────────────────────────────────────────────────────────────────
# Test: plan_stages produces correct stage lists
# ──────────────────────────────────────────────────────────────────────────────

class TestPlanStages:
    """Test that plan_stages() produces correct stage lists for each preset."""

    def test_full_spec_all_stages(self):
        """A full CharacterSpec should produce all 6 stages."""
        spec = CharacterSpec(
            hair=HairSpec(style="long_straight"),
            clothing=[ClothingSpec(name="shirt", type="tshirt")],
            physics=PhysicsSpec(),
        )
        stages = plan_stages(spec)
        assert STAGE_STUB_BONES in stages
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages
        assert STAGE_WEIGHT_PAINT in stages
        assert STAGE_SPRING_BONES in stages
        assert STAGE_FIRST_PERSON in stages
        assert len(stages) == 6

    def test_no_hair_skips_hair_stage(self):
        """Spec with hair.style='none' should skip hair mesh stage."""
        spec_dict = {
            "hair": {"style": "none"},
        }
        stages = plan_stages(spec_dict)
        assert STAGE_HAIR_MESH not in stages
        assert STAGE_STUB_BONES in stages  # Always runs

    def test_no_clothing_skips_clothing_stage(self):
        """Spec with empty clothing list should skip clothing stage."""
        spec_dict = {
            "hair": {"style": "long_straight"},
            "clothing": [],
        }
        stages = plan_stages(spec_dict)
        assert STAGE_CLOTHING_MESH not in stages
        assert STAGE_HAIR_MESH in stages

    def test_minimal_spec(self):
        """Minimal spec (just body) should still produce core stages."""
        spec_dict = {"body": {"height_cm": 165}}
        stages = plan_stages(spec_dict)
        assert STAGE_STUB_BONES in stages
        assert STAGE_WEIGHT_PAINT in stages
        assert STAGE_SPRING_BONES in stages
        assert STAGE_FIRST_PERSON in stages

    def test_dict_spec_with_all_sections(self):
        """Dict-based spec with all sections produces all stages."""
        spec = {
            "body": {"height_cm": 165},
            "hair": {"style": "twin_tails", "color": {"roots": "#222", "tips": "#F0E0D0"}},
            "clothing": [{"name": "shirt", "type": "tshirt"}, {"name": "skirt", "type": "skirt"}],
            "physics": {"hair": {"stiffness": 0.3, "gravity": 0.4, "drag": 0.5}},
        }
        stages = plan_stages(spec)
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages
        assert len(stages) == 6

    def test_empty_spec_produces_core_stages(self):
        """Empty spec should still produce stub, weight paint, spring, first-person."""
        stages = plan_stages({})
        assert STAGE_STUB_BONES in stages
        assert STAGE_WEIGHT_PAINT in stages
        assert STAGE_SPRING_BONES in stages
        assert STAGE_FIRST_PERSON in stages

    def test_stage_ordering(self):
        """Stages should appear in the correct order."""
        spec = CharacterSpec(
            hair=HairSpec(style="long_wavy"),
            clothing=[ClothingSpec(name="dress", type="dress")],
            physics=PhysicsSpec(),
        )
        stages = plan_stages(spec)
        # Verify ordering
        if STAGE_STUB_BONES in stages and STAGE_HAIR_MESH in stages:
            assert stages.index(STAGE_STUB_BONES) < stages.index(STAGE_HAIR_MESH)
        if STAGE_HAIR_MESH in stages and STAGE_CLOTHING_MESH in stages:
            assert stages.index(STAGE_HAIR_MESH) < stages.index(STAGE_CLOTHING_MESH)
        if STAGE_CLOTHING_MESH in stages and STAGE_WEIGHT_PAINT in stages:
            assert stages.index(STAGE_CLOTHING_MESH) < stages.index(STAGE_WEIGHT_PAINT)
        if STAGE_WEIGHT_PAINT in stages and STAGE_SPRING_BONES in stages:
            assert stages.index(STAGE_WEIGHT_PAINT) < stages.index(STAGE_SPRING_BONES)
        if STAGE_SPRING_BONES in stages and STAGE_FIRST_PERSON in stages:
            assert stages.index(STAGE_SPRING_BONES) < stages.index(STAGE_FIRST_PERSON)


# ──────────────────────────────────────────────────────────────────────────────
# Test: validate_spec_completeness catches missing fields
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateSpecCompleteness:
    """Test that validate_spec_completeness() catches missing fields."""

    def test_complete_spec_no_warnings(self):
        """A fully-specified spec should produce zero warnings."""
        spec = CharacterSpec(
            body=BodySpec(height_cm=165),
            hair=HairSpec(style="long_straight", color=HairColorSpec()),
            clothing=[ClothingSpec()],
            physics=PhysicsSpec(),
        )
        warnings = validate_spec_completeness(spec)
        # May still have warnings for face, export, expressions
        # but NOT for body, hair, clothing, physics
        body_warns = [w for w in warnings if "body" in w.lower()]
        hair_warns = [w for w in warnings if "hair" in w.lower()]
        clothing_warns = [w for w in warnings if "clothing" in w.lower()]
        physics_warns = [w for w in warnings if "physics" in w.lower()]
        assert len(body_warns) == 0
        assert len(hair_warns) == 0
        assert len(clothing_warns) == 0
        assert len(physics_warns) == 0

    def test_missing_body_warns(self):
        """Missing body section should produce a warning."""
        spec = {"hair": {"style": "short"}}
        warnings = validate_spec_completeness(spec)
        assert any("body" in w.lower() for w in warnings)

    def test_missing_face_warns(self):
        """Missing face section should produce a warning."""
        spec = {"body": {"height_cm": 165}}
        warnings = validate_spec_completeness(spec)
        assert any("face" in w.lower() for w in warnings)

    def test_missing_hair_warns(self):
        """Missing hair section should produce a warning."""
        spec = {"body": {"height_cm": 165}}
        warnings = validate_spec_completeness(spec)
        assert any("hair" in w.lower() for w in warnings)

    def test_missing_physics_warns(self):
        """Missing physics section should produce a warning."""
        spec = {"hair": {"style": "short"}}
        warnings = validate_spec_completeness(spec)
        assert any("physics" in w.lower() for w in warnings)

    def test_missing_clothing_none_warns(self):
        """If clothing is None (not empty list), should warn."""
        spec = {"hair": {"style": "short"}}
        warnings = validate_spec_completeness(spec)
        assert any("clothing" in w.lower() or "bare" in w.lower() for w in warnings)

    def test_empty_spec_many_warnings(self):
        """An empty spec should produce many warnings."""
        warnings = validate_spec_completeness({})
        assert len(warnings) >= 4  # body, face, hair, physics at minimum

    def test_dict_spec_with_hair_style(self):
        """Dict spec with hair.style set should not warn about missing style."""
        spec = {
            "hair": {"style": "long_straight", "color": {"roots": "#222", "tips": "#F5E6B8"}},
        }
        warnings = validate_spec_completeness(spec)
        style_warns = [w for w in warnings if "hair.style" in w.lower() or "hair style" in w.lower()]
        assert len(style_warns) == 0

    def test_dict_spec_missing_hair_color(self):
        """Dict spec with hair but no color should warn about default gradient."""
        spec = {"hair": {"style": "short"}}
        warnings = validate_spec_completeness(spec)
        assert any("color" in w.lower() and "hair" in w.lower() for w in warnings)


# ──────────────────────────────────────────────────────────────────────────────
# Test: Stub bone detection (pure-Python, no bpy)
# ──────────────────────────────────────────────────────────────────────────────

class TestStubBonesPure:
    """Test stub bone detection without Blender."""

    def test_detect_missing_bones_mblab(self):
        """MB-Lab rigs (missing jaw/eyes) should detect missing bones."""
        # MB-Lab rig has most bones but NOT jaw, leftEye, rightEye
        mblab_rig = {
            "head", "neck", "spine_02", "spine_03",
            "clavicle_L", "clavicle_R",
            "upper_arm_L", "upper_arm_R",
            "forearm_L", "forearm_R",
            "hand_L", "hand_R",
            "pelvis", "spine",
            "thigh_L", "thigh_R",
            "shin_L", "shin_R",
            "foot_L", "foot_R",
            "toe_L", "toe_R",
        }
        missing = detect_missing_bones(mblab_rig)
        assert "jaw" in missing
        assert "leftEye" in missing
        assert "rightEye" in missing

    def test_detect_no_missing_with_stubs(self):
        """A rig with all 25 bones should detect no missing."""
        # Simulate a fully-rigged armature with stubs already added
        full_rig = {
            "head", "neck", "spine_02", "spine_03",
            "clavicle_L", "clavicle_R",
            "upper_arm_L", "upper_arm_R",
            "forearm_L", "forearm_R",
            "hand_L", "hand_R",
            "pelvis", "spine",
            "thigh_L", "thigh_R",
            "shin_L", "shin_R",
            "foot_L", "foot_R",
            "toe_L", "toe_R",
            "jaw", "leftEye", "rightEye",
        }
        missing = detect_missing_bones(full_rig)
        # jaw, leftEye, rightEye are present, so none of our stubs needed
        assert "jaw" not in missing

    def test_get_stub_bone_map(self):
        """get_stub_bone_map should return a dict mapping VRM names to Blender names."""
        bone_map = get_stub_bone_map()
        assert isinstance(bone_map, dict)
        assert "jaw" in bone_map
        assert "leftEye" in bone_map
        assert "rightEye" in bone_map
        assert bone_map["jaw"] == "jaw"
        assert bone_map["leftEye"] == "leftEye"
        assert bone_map["rightEye"] == "rightEye"

    def test_compute_stub_position(self):
        """Stub positions should be at head bone midpoint + offset."""
        from hamr.rigs.stub_bones import compute_stub_position
        head_head = (0.0, 0.0, 1.55)
        head_tail = (0.0, 0.0, 1.75)

        jaw_pos = compute_stub_position("jaw", head_head, head_tail)
        assert jaw_pos[2] < 1.65  # Below midpoint (7cm below)
        assert abs(jaw_pos[2] - 1.58) < 0.02  # Approx chin position

        left_eye_pos = compute_stub_position("leftEye", head_head, head_tail)
        assert left_eye_pos[0] > 0  # Left of center
        assert left_eye_pos[2] > 1.60  # Eye level


# ──────────────────────────────────────────────────────────────────────────────
# Test: Spring bone configuration (pure-Python)
# ──────────────────────────────────────────────────────────────────────────────

class TestSpringBonesPure:
    """Test spring bone configuration without Blender."""

    def test_configure_hair_spring_defaults(self):
        """configure_hair_spring with no spec should use defaults."""
        from hamr.rigs.spring_bones import configure_hair_spring
        group = configure_hair_spring(None)
        assert group.name == "hair_spring"
        assert group.center == "head"
        assert len(group.bone_chains) > 0

    def test_configure_hair_spring_with_spec(self):
        """configure_hair_spring with HairPhysicsSpec should use spec values."""
        from hamr.rigs.spring_bones import configure_hair_spring
        spec = HairPhysicsSpec(stiffness=0.8, gravity=0.2, drag=0.3)
        group = configure_hair_spring(spec)
        assert group.name == "hair_spring"
        assert group.stiff_force > 1.0  # Mapped from 0.8 stiffness

    def test_configure_breast_spring_defaults(self):
        """configure_breast_spring with no spec should use defaults."""
        from hamr.rigs.spring_bones import configure_breast_spring
        group = configure_breast_spring(None)
        assert group.name == "breast_spring"

    def test_configure_clothing_spring_skirt(self):
        """configure_clothing_spring for skirt type."""
        from hamr.rigs.spring_bones import configure_clothing_spring
        group = configure_clothing_spring("test_skirt_mesh", "skirt")
        assert "skirt" in group.name
        assert len(group.bone_chains) > 0

    def test_spring_bone_group_serialization(self):
        """SpringBoneGroup.to_dict() should produce VRM-compatible output."""
        from hamr.rigs.spring_bones import SpringBoneGroup
        group = SpringBoneGroup(
            name="test_spring",
            stiff_force=1.0,
            gravity_power=0.5,
            bone_chains=[["bone1", "bone2"]],
        )
        d = group.to_dict()
        assert d["name"] == "test_spring"
        assert d["stiff_force"] == 1.0
        assert d["gravity_dir"] == [0.0, -1.0, 0.0]


# ──────────────────────────────────────────────────────────────────────────────
# Test: First-person configuration (pure-Python)
# ──────────────────────────────────────────────────────────────────────────────

class TestFirstPersonPure:
    """Test first-person annotation classification without Blender."""

    def test_classify_mesh_for_fp_head(self):
        """Head-related meshes should be thirdPersonOnly."""
        from hamr.export.first_person import classify_mesh_for_fp, FP_THIRD_PERSON_ONLY
        assert classify_mesh_for_fp("Head") == FP_THIRD_PERSON_ONLY
        assert classify_mesh_for_fp("hair_long") == FP_THIRD_PERSON_ONLY
        assert classify_mesh_for_fp("Eye_L") == FP_THIRD_PERSON_ONLY

    def test_classify_mesh_for_fp_body(self):
        """Body-related meshes should be both."""
        from hamr.export.first_person import classify_mesh_for_fp, FP_BOTH
        assert classify_mesh_for_fp("Body") == FP_BOTH
        assert classify_mesh_for_fp("Hand_L") == FP_BOTH
        assert classify_mesh_for_fp("clothes_shirt") == FP_BOTH

    def test_classify_mesh_for_fp_first_person(self):
        """FP-specific meshes should be firstPersonOnly."""
        from hamr.export.first_person import classify_mesh_for_fp, FP_FIRST_PERSON_ONLY
        assert classify_mesh_for_fp("fp_body") == FP_FIRST_PERSON_ONLY
        assert classify_mesh_for_fp("first_person_body") == FP_FIRST_PERSON_ONLY

    def test_classify_mesh_for_fp_unknown(self):
        """Unknown meshes should return auto."""
        from hamr.export.first_person import classify_mesh_for_fp, FP_AUTO
        assert classify_mesh_for_fp("random_mesh_001") == FP_AUTO

    def test_configure_first_person_pure(self):
        """configure_first_person_pure should classify all given meshes."""
        from hamr.export.first_person import configure_first_person_pure
        config = configure_first_person_pure(
            body_name="Body",
            clothing_names=["shirt_mesh", "skirt_mesh"],
        )
        assert config.first_person_bone == "head"
        assert "Body" in config.mesh_annotations
        assert "shirt_mesh" in config.mesh_annotations
        assert "skirt_mesh" in config.mesh_annotations

    def test_first_person_config_validation(self):
        """FirstPersonConfig.validate() should catch invalid annotations."""
        from hamr.export.first_person import FirstPersonConfig
        config = FirstPersonConfig(
            first_person_bone="head",
            mesh_annotations={"bad_mesh": "invalid_annotation"},
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("invalid" in e.lower() for e in errors)


# ──────────────────────────────────────────────────────────────────────────────
# Test: Hair mesh pure-Python functions
# ──────────────────────────────────────────────────────────────────────────────

class TestHairMeshPure:
    """Test pure-Python hair mesh geometry functions."""

    def test_generate_guide_curves(self):
        """generate_guide_curves should produce GuideCurve objects."""
        from hamr.hair.mesh import generate_guide_curves, HAIR_MESH_STYLES
        curves = generate_guide_curves("long_straight", head_center=(0, 1.65, 0), head_radius=0.10)
        assert len(curves) > 0
        assert all(hasattr(c, "origin") for c in curves)
        assert all(hasattr(c, "control_points") for c in curves)

    def test_generate_guide_curves_unknown_style(self):
        """Unknown style should fall back to long_straight."""
        from hamr.hair.mesh import generate_guide_curves
        curves = generate_guide_curves("unknown_style_xyz")
        assert len(curves) > 0

    def test_compute_strand_count(self):
        """compute_strand_count should return a reasonable integer."""
        from hamr.hair.mesh import compute_strand_count
        count = compute_strand_count("long_straight", density=1.0)
        assert isinstance(count, int)
        assert count > 0
        assert count < 1000  # Reasonable budget

    def test_interpolate_curve_points(self):
        """Catmull-Rom interpolation should produce smooth curves."""
        from hamr.hair.mesh import interpolate_curve_points
        control_points = [(0, 0, 0), (0, 0, 0.1), (0, 0, 0.2), (0, 0, 0.3), (0, 0, 0.4)]
        points = interpolate_curve_points(control_points, subdivisions=4)
        assert len(points) > len(control_points)
        # First point should be near the first control point
        assert abs(points[0][2]) < 0.01

    def test_hair_mesh_styles_complete(self):
        """All HAIR_MESH_STYLES should have required keys."""
        from hamr.hair.mesh import HAIR_MESH_STYLES, _REQUIRED_STYLE_KEYS
        for style_name, cfg in HAIR_MESH_STYLES.items():
            for key in _REQUIRED_STYLE_KEYS:
                assert key in cfg, f"Style '{style_name}' missing key '{key}'"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Clothing mesh pure-Python functions
# ──────────────────────────────────────────────────────────────────────────────

class TestClothingMeshPure:
    """Test pure-Python clothing mesh functions."""

    def test_resolve_clothing_pattern(self):
        """resolve_clothing_pattern should return a valid pattern dict."""
        from hamr.clothing.mesh import resolve_clothing_pattern
        pattern = resolve_clothing_pattern("tshirt")
        assert "layers" in pattern
        assert "body_regions" in pattern
        assert pattern["display_name"] == "T-Shirt"

    def test_resolve_clothing_pattern_unknown(self):
        """Unknown pattern should fall back to tshirt."""
        from hamr.clothing.mesh import resolve_clothing_pattern
        pattern = resolve_clothing_pattern("nonexistent_garment")
        assert pattern["display_name"] == "T-Shirt"  # Falls back

    def test_compute_clothing_regions(self):
        """compute_clothing_regions should return offset/scale pairs."""
        from hamr.clothing.mesh import compute_clothing_regions, resolve_clothing_pattern
        pattern = resolve_clothing_pattern("tshirt")
        regions = compute_clothing_regions(pattern)
        assert "torso" in regions
        offset, scale = regions["torso"]
        assert isinstance(offset, float)
        assert isinstance(scale, float)
        assert offset > 0

    def test_estimate_triangle_count(self):
        """estimate_triangle_count should return reasonable values."""
        from hamr.clothing.mesh import estimate_triangle_count, resolve_clothing_pattern
        pattern = resolve_clothing_pattern("tshirt")
        low = estimate_triangle_count(pattern, "low")
        medium = estimate_triangle_count(pattern, "medium")
        high = estimate_triangle_count(pattern, "high")
        assert low < medium < high
        assert low > 0

    def test_classify_material_type(self):
        """classify_material_type should infer material from name."""
        from hamr.clothing.mesh import classify_material_type
        assert classify_material_type("leather_jacket") == "leather"
        assert classify_material_type("chain_mail") == "metal"
        assert classify_material_type("silk_dress") == "silk"
        assert classify_material_type("denim_pants") == "denim"
        assert classify_material_type("basic_shirt") == "fabric"

    def test_clothing_patterns_all_have_required_keys(self):
        """All clothing patterns should have required keys."""
        from hamr.clothing.mesh import CLOTHING_PATTERNS, _REQUIRED_PATTERN_KEYS
        for name, pattern in CLOTHING_PATTERNS.items():
            for key in _REQUIRED_PATTERN_KEYS:
                assert key in pattern, f"Pattern '{name}' missing key '{key}'"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Weight paint pure-Python functions
# ──────────────────────────────────────────────────────────────────────────────

class TestWeightPaintPure:
    """Test pure-Python weight paint analysis functions."""

    def test_compute_quality_score_empty(self):
        """Empty inputs should return 0.0."""
        from hamr.rigs.weights import compute_quality_score
        assert compute_quality_score({}, []) == 0.0

    def test_compute_quality_score_good(self):
        """Well-distributed weights should score high."""
        from hamr.rigs.weights import compute_quality_score
        # Each vertex has 2 bones with 0.5 weight each (ideal distribution)
        groups = {
            "bone_A": [(0, 0.5), (1, 0.5), (2, 0.5)],
            "bone_B": [(0, 0.5), (1, 0.5), (2, 0.5)],
        }
        score = compute_quality_score(groups, ["bone_A", "bone_B"])
        assert score > 0.5

    def test_smooth_weight_map(self):
        """smooth_weight_map should produce a list of same length."""
        from hamr.rigs.weights import smooth_weight_map
        weights = [0.0, 0.5, 1.0, 0.5, 0.0]
        result = smooth_weight_map(weights, iterations=3, radius=0.3)
        assert len(result) == len(weights)
        # Smoothed values should be more uniform
        assert max(result) < max(weights)

    def test_classify_deformation_quality(self):
        """Quality classification should return expected labels."""
        from hamr.rigs.weights import classify_deformation_quality
        assert classify_deformation_quality(0.3) == "poor"
        assert classify_deformation_quality(0.5) == "acceptable"
        assert classify_deformation_quality(0.7) == "good"
        assert classify_deformation_quality(0.9) == "excellent"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Performance budget check (pure-Python)
# ──────────────────────────────────────────────────────────────────────────────

class TestPerfBudget:
    """Test performance budget checking."""

    def test_check_budget_with_empty_spec(self):
        """Empty spec should still produce a report."""
        from hamr.core.perf import check_budget, DEFAULT_PI5_BUDGET
        report = check_budget({}, DEFAULT_PI5_BUDGET)
        assert hasattr(report, "within_budget")
        assert hasattr(report, "warnings")

    def test_default_pi5_budget_values(self):
        """DEFAULT_PI5_BUDGET should have Pi-appropriate constraints."""
        from hamr.core.perf import DEFAULT_PI5_BUDGET
        assert DEFAULT_PI5_BUDGET.max_build_time_seconds > 0
        assert DEFAULT_PI5_BUDGET.max_memory_mb > 0
        assert DEFAULT_PI5_BUDGET.max_triangles > 0

    def test_performance_report_has_summary(self):
        """PerformanceReport should have a summary method."""
        from hamr.core.perf import PerformanceReport
        report = PerformanceReport()
        assert hasattr(report, "within_budget")
        assert hasattr(report, "warnings")
        assert hasattr(report, "summary")


# ──────────────────────────────────────────────────────────────────────────────
# Test: estimate_stage_time
# ──────────────────────────────────────────────────────────────────────────────

class TestEstimateStageTime:
    """Test stage time estimation."""

    def test_known_stages_have_times(self):
        """All known stages should have positive time estimates."""
        for stage in ALL_STAGES:
            time = estimate_stage_time(stage)
            assert time > 0, f"Stage {stage} should have positive time estimate"

    def test_unknown_stage_returns_default(self):
        """Unknown stage names should return a default time."""
        time = estimate_stage_time("nonexistent_stage")
        assert time > 0

    def test_hair_mesh_is_slowest(self):
        """Hair mesh generation should be the slowest stage."""
        hair_time = estimate_stage_time(STAGE_HAIR_MESH)
        for stage in ALL_STAGES:
            if stage != STAGE_HAIR_MESH:
                assert hair_time >= estimate_stage_time(stage), \
                    f"Hair should be >= {stage}"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Blender-dependent tests (marked with @pytest.mark.blender)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.blender
class TestBuildAvatarBlender:
    """Tests that require Blender (bpy) to run."""

    def test_integrate_stub_bones_callable(self):
        """_integrate_stub_bones should be callable (requires bpy)."""
        from hamr.scripts.build_avatar import _integrate_stub_bones
        # Just verify it's a function that takes bpy + armature_name
        import inspect
        sig = inspect.signature(_integrate_stub_bones)
        assert "bpy" in sig.parameters or len(sig.parameters) >= 2

    def test_integrate_hair_mesh_callable(self):
        """_integrate_hair_mesh should be callable (requires bpy)."""
        from hamr.scripts.build_avatar import _integrate_hair_mesh
        import inspect
        sig = inspect.signature(_integrate_hair_mesh)
        assert len(sig.parameters) >= 4

    def test_integrate_weight_paint_callable(self):
        """_integrate_weight_paint should be callable (requires bpy)."""
        from hamr.scripts.build_avatar import _integrate_weight_paint
        import inspect
        sig = inspect.signature(_integrate_weight_paint)
        assert len(sig.parameters) >= 4