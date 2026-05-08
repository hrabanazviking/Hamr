"""
Tests for hamr.core.pipeline_integrate — Pipeline integration layer.

Phase 12 T1: The forge worker welds the pipeline shut.
These tests cover pure-Python functions: no bpy required.
"""

import pytest
from dataclasses import dataclass, field, asdict

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
    run_integration_stages,
    _get_attr,
    _extract_character_spec,
    _hex_to_hsv,
)
from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    HairColorSpec,
    EyeSpec,
    ClothingSpec,
    PhysicsSpec,
    HairPhysicsSpec,
    BreastPhysicsSpec,
    ExportSpec,
    ExpressionSpec,
)
from hamr.core.presets import CHARACTER_PRESETS
from hamr.core.perf import PerformanceBudget


# ── IntegrationResult dataclass tests ───────────────────────────────────────

class TestIntegrationResult:
    """IntegrationResult is a dataclass with all the tracking fields."""

    def test_default_values(self) -> None:
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

    def test_success_property_no_errors(self) -> None:
        result = IntegrationResult()
        assert result.success is True

    def test_success_property_with_errors(self) -> None:
        result = IntegrationResult(errors=["hair mesh failed"])
        assert result.success is False

    def test_stage_count(self) -> None:
        result = IntegrationResult(
            stages_completed=[
                STAGE_STUB_BONES,
                STAGE_HAIR_MESH,
                STAGE_WEIGHT_PAINT,
            ]
        )
        assert result.stage_count == 3

    def test_repr_success(self) -> None:
        result = IntegrationResult(
            stages_completed=[STAGE_STUB_BONES],
            elapsed_seconds=2.5,
        )
        r = repr(result)
        assert "✓" in r
        assert "1/6" in r

    def test_repr_with_errors(self) -> None:
        result = IntegrationResult(
            stages_completed=[STAGE_STUB_BONES],
            errors=["boom"],
            elapsed_seconds=1.0,
        )
        r = repr(result)
        assert "✗" in r

    def test_field_mutability(self) -> None:
        result = IntegrationResult()
        result.stages_completed.append(STAGE_STUB_BONES)
        result.errors.append("test error")
        result.stub_bones_applied = True
        assert result.stages_completed == [STAGE_STUB_BONES]
        assert result.errors == ["test error"]
        assert result.stub_bones_applied is True

    def test_with_all_fields_populated(self) -> None:
        result = IntegrationResult(
            stages_completed=ALL_STAGES,
            stub_bones_applied=True,
            hair_meshes_created=["hair_long_straight"],
            clothing_meshes_created=["school_uniform"],
            weight_paint_applied=True,
            spring_bones_configured=True,
            first_person_configured=True,
            warnings=["clothing item 1 failed: no body mesh"],
            errors=[],
            elapsed_seconds=14.3,
        )
        assert result.success is True
        assert result.stage_count == 6
        assert result.stub_bones_applied is True
        assert result.hair_meshes_created == ["hair_long_straight"]
        assert result.clothing_meshes_created == ["school_uniform"]
        assert result.weight_paint_applied is True
        assert result.spring_bones_configured is True
        assert result.first_person_configured is True
        assert len(result.warnings) == 1


# ── plan_stages tests ────────────────────────────────────────────────────────

class TestPlanStages:
    """plan_stages determines which integration stages will run based on spec."""

    def test_full_spec_all_stages(self) -> None:
        """A full CharacterSpec with hair and clothing should run all 6 stages."""
        spec = CharacterSpec(
            name="Full Character",
            hair=HairSpec(style="straight", length="long"),
            clothing=[ClothingSpec(name="school_uniform", type="full-outfit")],
        )
        stages = plan_stages(spec)
        assert STAGE_STUB_BONES in stages
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages
        assert STAGE_WEIGHT_PAINT in stages
        assert STAGE_SPRING_BONES in stages
        assert STAGE_FIRST_PERSON in stages
        assert len(stages) == 6

    def test_minimal_spec_no_hair_no_clothing(self) -> None:
        """A spec with hair style 'none' should skip hair mesh stage."""
        spec = CharacterSpec(
            name="Minimal",
            hair=HairSpec(style="none", length="short"),
        )
        stages = plan_stages(spec)
        assert STAGE_STUB_BONES in stages
        assert STAGE_HAIR_MESH not in stages
        assert STAGE_CLOTHING_MESH not in stages  # no clothing
        assert STAGE_WEIGHT_PAINT in stages  # still weight paint body
        assert STAGE_SPRING_BONES in stages
        assert STAGE_FIRST_PERSON in stages

    def test_spec_with_hair_no_clothing(self) -> None:
        """Spec with hair but no clothing — still runs weight paint."""
        spec = CharacterSpec(
            name="Hair Only",
            hair=HairSpec(style="wavy", length="long"),
            clothing=[],
        )
        stages = plan_stages(spec)
        assert STAGE_STUB_BONES in stages
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH not in stages
        assert STAGE_WEIGHT_PAINT in stages
        assert STAGE_SPRING_BONES in stages
        assert STAGE_FIRST_PERSON in stages

    def test_spec_with_clothing_no_hair_style_none(self) -> None:
        """Spec with clothing but hair style 'none' — skips hair mesh."""
        spec = CharacterSpec(
            name="Clothed, No Hair",
            hair=HairSpec(style="none", length="short"),
            clothing=[ClothingSpec(name="tshirt", type="tshirt")],
        )
        stages = plan_stages(spec)
        assert STAGE_STUB_BONES in stages
        assert STAGE_HAIR_MESH not in stages
        assert STAGE_CLOTHING_MESH in stages
        assert STAGE_WEIGHT_PAINT in stages

    def test_preset_anime_girl_default(self) -> None:
        """anime_girl_default preset should run all stages."""
        preset_data = CHARACTER_PRESETS["anime_girl_default"]
        spec_dict = preset_data["spec"]
        spec = CharacterSpec.from_dict(spec_dict)
        stages = plan_stages(spec)
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages
        assert len(stages) == 6

    def test_preset_anime_boy_default(self) -> None:
        """anime_boy_default has no clothing, so clothing stage is skipped."""
        preset_data = CHARACTER_PRESETS["anime_boy_default"]
        spec_dict = preset_data["spec"]
        spec = CharacterSpec.from_dict(spec_dict)
        stages = plan_stages(spec)
        assert STAGE_HAIR_MESH in stages
        # anime_boy_default has empty clothing list
        assert STAGE_CLOTHING_MESH not in stages

    def test_preset_warrior(self) -> None:
        """anime_girl_warrior has hair + clothing — all stages."""
        preset_data = CHARACTER_PRESETS["anime_girl_warrior"]
        spec_dict = preset_data["spec"]
        spec = CharacterSpec.from_dict(spec_dict)
        stages = plan_stages(spec)
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages
        assert len(stages) == 6

    def test_preset_mage(self) -> None:
        """anime_girl_mage has hair + clothing — all stages."""
        preset_data = CHARACTER_PRESETS["anime_girl_mage"]
        spec_dict = preset_data["spec"]
        spec = CharacterSpec.from_dict(spec_dict)
        stages = plan_stages(spec)
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages

    def test_preset_chibi(self) -> None:
        """chibi_cute has hair + clothing — all stages."""
        preset_data = CHARACTER_PRESETS["chibi_cute"]
        spec_dict = preset_data["spec"]
        spec = CharacterSpec.from_dict(spec_dict)
        stages = plan_stages(spec)
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages

    def test_dict_spec(self) -> None:
        """plan_stages should work with plain dict input."""
        spec_dict = {
            "name": "Dict Character",
            "hair": {"style": "braided", "length": "long"},
            "clothing": [{"name": "dress", "type": "dress"}],
        }
        stages = plan_stages(spec_dict)
        assert STAGE_HAIR_MESH in stages
        assert STAGE_CLOTHING_MESH in stages
        assert STAGE_STUB_BONES in stages

    def test_dict_spec_no_hair(self) -> None:
        """Dict spec with hair style 'none' should skip hair mesh."""
        spec_dict = {
            "name": "Bare",
            "hair": {"style": "none"},
        }
        stages = plan_stages(spec_dict)
        assert STAGE_HAIR_MESH not in stages

    def test_dict_spec_no_clothing_key(self) -> None:
        """Dict spec without clothing key should skip clothing stage."""
        spec_dict = {
            "name": "No Clothing",
            "hair": {"style": "straight"},
        }
        stages = plan_stages(spec_dict)
        assert STAGE_CLOTHING_MESH not in stages

    def test_stages_order(self) -> None:
        """Stages should always be in canonical order."""
        spec = CharacterSpec(
            hair=HairSpec(style="straight", length="long"),
            clothing=[ClothingSpec(name="shirt", type="tshirt")],
        )
        stages = plan_stages(spec)
        # The order should match ALL_STAGES exactly
        assert stages == ALL_STAGES


# ── estimate_stage_time tests ────────────────────────────────────────────────

class TestEstimateStageTime:
    """Pre-flight time estimates for each integration stage."""

    def test_stub_bones_estimate(self) -> None:
        t = estimate_stage_time(STAGE_STUB_BONES)
        assert isinstance(t, float)
        assert t > 0
        assert t < 10  # Stub bones should be fast

    def test_hair_mesh_estimate(self) -> None:
        t = estimate_stage_time(STAGE_HAIR_MESH)
        assert isinstance(t, float)
        assert t > 0
        # Hair is one of the slower stages
        assert t >= estimate_stage_time(STAGE_STUB_BONES)

    def test_clothing_mesh_estimate(self) -> None:
        t = estimate_stage_time(STAGE_CLOTHING_MESH)
        assert isinstance(t, float)
        assert t > 0

    def test_weight_paint_estimate(self) -> None:
        t = estimate_stage_time(STAGE_WEIGHT_PAINT)
        assert isinstance(t, float)
        assert t > 0

    def test_spring_bones_estimate(self) -> None:
        t = estimate_stage_time(STAGE_SPRING_BONES)
        assert isinstance(t, float)
        assert t > 0

    def test_first_person_estimate(self) -> None:
        t = estimate_stage_time(STAGE_FIRST_PERSON)
        assert isinstance(t, float)
        assert t > 0

    def test_unknown_stage_returns_default(self) -> None:
        t = estimate_stage_time("unknown_stage")
        assert t == 1.0

    def test_total_time_estimate_reasonable(self) -> None:
        """Total integration time should be reasonable on Pi 5."""
        total = sum(estimate_stage_time(s) for s in ALL_STAGES)
        assert total > 0
        # Must complete within the Blender timeout (120s)
        assert total < 120


# ── validate_spec_completeness tests ─────────────────────────────────────────

class TestValidateSpecCompleteness:
    """Returns warnings for missing spec fields."""

    def test_complete_spec_no_warnings(self) -> None:
        """A fully specified CharacterSpec should have no warnings."""
        spec = CharacterSpec(
            name="Complete",
            body=BodySpec(height_cm=165.0),
            face=FaceSpec(),
            hair=HairSpec(style="straight", length="long"),
            clothing=[ClothingSpec(name="shirt", type="tshirt")],
            physics=PhysicsSpec(),
            export=ExportSpec(),
            expressions=ExpressionSpec(),
        )
        warnings = validate_spec_completeness(spec)
        assert len(warnings) == 0

    def test_missing_body_warning(self) -> None:
        """Missing body section should generate a warning."""
        spec = CharacterSpec(name="No Body")
        # body has a default factory, so it won't be None
        # but we can test with a dict that omits it
        spec_dict = {"name": "No Body Dict"}
        warnings = validate_spec_completeness(spec_dict)
        # body is missing from dict
        assert any("body" in w.lower() for w in warnings)

    def test_missing_hair_warning(self) -> None:
        """Missing hair section should generate a warning."""
        spec_dict = {"name": "No Hair Dict"}
        warnings = validate_spec_completeness(spec_dict)
        assert any("hair" in w.lower() for w in warnings)

    def test_missing_clothing_warning(self) -> None:
        """Empty or missing clothing should generate a warning."""
        spec_dict = {"name": "No Clothing Dict"}
        warnings = validate_spec_completeness(spec_dict)
        assert any("clothing" in w.lower() for w in warnings)

    def test_missing_physics_warning(self) -> None:
        """Missing physics section should generate a warning."""
        spec_dict = {"name": "No Physics"}
        warnings = validate_spec_completeness(spec_dict)
        assert any("physics" in w.lower() for w in warnings)

    def test_missing_face_warning(self) -> None:
        """Missing face section should generate a warning."""
        spec_dict = {"name": "No Face"}
        warnings = validate_spec_completeness(spec_dict)
        assert any("face" in w.lower() for w in warnings)

    def test_missing_export_warning(self) -> None:
        """Missing export section should generate a warning."""
        spec_dict = {"name": "No Export"}
        warnings = validate_spec_completeness(spec_dict)
        assert any("export" in w.lower() for w in warnings)

    def test_missing_expressions_warning(self) -> None:
        """Missing expressions section should generate a warning."""
        spec_dict = {"name": "No Expressions"}
        warnings = validate_spec_completeness(spec_dict)
        assert any("expressions" in w.lower() for w in warnings)

    def test_default_character_spec_has_all_sections(self) -> None:
        """Default CharacterSpec has all sections via default factories."""
        spec = CharacterSpec(name="Default Everything")
        warnings = validate_spec_completeness(spec)
        # Default spec has all sections, so should have no warnings
        assert len(warnings) == 0

    def test_preset_specs_have_no_warnings(self) -> None:
        """All built-in presets should have no completeness warnings."""
        for preset_name, preset_data in CHARACTER_PRESETS.items():
            spec = CharacterSpec.from_dict(preset_data["spec"])
            warnings = validate_spec_completeness(spec)
            assert len(warnings) == 0, (
                f"Preset '{preset_name}' has warnings: {warnings}"
            )


# ── run_integration_stages tests (requires bpy — should raise) ──────────────

class TestRunIntegrationStages:
    """run_integration_stages requires bpy and should raise when unavailable."""

    def test_raises_runtime_error_without_bpy(self) -> None:
        """Without bpy available, run_integration_stages should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="requires Blender"):
            run_integration_stages(
                armature_name="test_armature",
                mesh_names=["test_mesh"],
                spec=CharacterSpec(name="test"),
            )

    def test_raises_runtime_error_with_budget_without_bpy(self) -> None:
        """Same behavior when a budget is provided."""
        with pytest.raises(RuntimeError, match="requires Blender"):
            run_integration_stages(
                armature_name="test_armature",
                mesh_names=["test_mesh"],
                spec=CharacterSpec(name="test"),
                budget=PerformanceBudget(),
            )


# ── Helper function tests ───────────────────────────────────────────────────

class TestHelperFunctions:
    """Internal helper functions for spec attribute access."""

    def test_get_attr_from_dataclass(self) -> None:
        spec = CharacterSpec(name="Test")
        assert _get_attr(spec, "name") == "Test"

    def test_get_attr_from_dict(self) -> None:
        d = {"name": "DictTest", "hair": {"style": "straight"}}
        assert _get_attr(d, "name") == "DictTest"
        assert _get_attr(d, "hair") == {"style": "straight"}

    def test_get_attr_default(self) -> None:
        d = {"name": "Test"}
        assert _get_attr(d, "nonexistent", "default_val") == "default_val"

    def test_get_attr_default_from_dataclass(self) -> None:
        spec = CharacterSpec(name="Test")
        result = _get_attr(spec, "nonexistent", "default_val")
        assert result == "default_val"

    def test_extract_character_spec_from_dict(self) -> None:
        d = {"character": {"name": "Inner"}}
        result = _extract_character_spec(d)
        assert result == {"name": "Inner"}

    def test_extract_character_spec_from_dict_no_character_key(self) -> None:
        d = {"name": "Outer"}
        result = _extract_character_spec(d)
        assert result == d

    def test_extract_character_spec_from_object(self) -> None:
        spec = CharacterSpec(name="Test")
        result = _extract_character_spec(spec)
        assert result is spec

    def test_hex_to_hsv(self) -> None:
        """Test hex to HSV conversion."""
        h, s, v = _hex_to_hsv("#FF0000")
        assert abs(h - 0.0) < 0.01  # Red hue
        assert abs(s - 1.0) < 0.01
        assert abs(v - 1.0) < 0.01

    def test_hex_to_hsv_white(self) -> None:
        h, s, v = _hex_to_hsv("#FFFFFF")
        assert abs(v - 1.0) < 0.01
        assert abs(s) < 0.01  # White has zero saturation

    def test_hex_to_hsv_black(self) -> None:
        h, s, v = _hex_to_hsv("#000000")
        assert abs(v) < 0.01  # Black has zero value


# ── Stage constant tests ─────────────────────────────────────────────────────

class TestStageConstants:
    """Verify stage constants are well-defined."""

    def test_all_stages_has_six_entries(self) -> None:
        assert len(ALL_STAGES) == 6

    def test_stage_order(self) -> None:
        """Stage order must match the integration sequence."""
        assert ALL_STAGES == [
            STAGE_STUB_BONES,
            STAGE_HAIR_MESH,
            STAGE_CLOTHING_MESH,
            STAGE_WEIGHT_PAINT,
            STAGE_SPRING_BONES,
            STAGE_FIRST_PERSON,
        ]

    def test_stage_names_are_strings(self) -> None:
        for stage in ALL_STAGES:
            assert isinstance(stage, str)
            assert len(stage) > 0

    def test_no_duplicate_stages(self) -> None:
        assert len(set(ALL_STAGES)) == len(ALL_STAGES)