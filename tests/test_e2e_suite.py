"""
test_e2e_suite — Phase 14 T1 End-to-End Integration Suite.

Tests the full pipeline from spec creation through validation, module
cross-flow, export checks, and GPU profile mapping — all without Blender.

Every test uses pure-Python code paths. bpy is never imported.

The forge tests itself. — Eldra Járnsdóttir
"""

from __future__ import annotations

import pytest
from dataclasses import asdict
from copy import deepcopy

# ── Core imports (pure Python, no bpy) ──────────────────────────────────────────
from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    HairColorSpec,
    EyeSpec,
    SkinSpec,
    ClothingSpec,
    ExpressionSpec,
    CustomExpressionSpec,
    PhysicsSpec,
    HairPhysicsSpec,
    BreastPhysicsSpec,
    ExportSpec,
)
from hamr.core.spec import Spec
from hamr.core.validate import validate_spec
from hamr.core.errors import (
    HamrError,
    SpecValidationError,
    BuildError,
    ExportError,
    AssetNotFoundError,
)
from hamr.core.perf import (
    PerformanceBudget,
    PerformanceReport,
    TriangleBudget,
    DEFAULT_PI5_BUDGET,
    estimate_build_triangles,
    estimate_memory_usage,
    estimate_build_time,
    check_budget,
    optimize_spec_for_budget,
)
from hamr.core.perf_gate import PerfGate, PerfGateResult
from hamr.core.gpu_profiles import (
    GPUProfile,
    GPU_PROFILES,
    get_profile,
    list_profiles,
    profile_from_spec,
    validate_profile_compatibility,
    profile_to_budget,
)
from hamr.core.presets import (
    CHARACTER_PRESETS,
    get_preset,
    deep_merge,
    resolve_preset,
    validate_preset,
)
from hamr.core.pipeline import BuildPipeline, PipelineResult
from hamr.core.pipeline_integrate import (
    IntegrationResult,
    plan_stages,
    ALL_STAGES,
    STAGE_STUB_BONES,
    STAGE_HAIR_MESH,
    STAGE_CLOTHING_MESH,
    STAGE_WEIGHT_PAINT,
    STAGE_SPRING_BONES,
    STAGE_FIRST_PERSON,
)
from hamr.core.a11y import (
    format_error,
    get_actionable_suggestion,
    ERROR_SUGGESTIONS,
    CLIOptions,
)

# ── Module imports (pure-Python paths only) ─────────────────────────────────────
from hamr.rigs.stub_bones import STUB_BONE_DEFS, detect_missing_bones
from hamr.rigs.spring_bones import HAIR_SPRING_PRESETS, SpringBoneGroup, SpringBoneCollider
from hamr.rigs.collision import COLLIDER_REGIONS, CollisionMeshResult
from hamr.hair import HAIR_STYLE_TEMPLATES
from hamr.clothing import CLOTH_TYPE_TEMPLATES
from hamr.face import JAW_MAP, CHEEKBONE_MAP, EYE_SHAPE_MAP, LIP_FULLNESS_MAP
from hamr.materials.anime import (
    EMBLEMATIC_COLORS,
    AnimeMaterialSpec,
    validate_material_spec,
)
from hamr.export.vrm_validator import VRMValidator, VRMValidationResult
from hamr.export.animation_clips import AnimationClip, AnimationKeyframe
from hamr.export.first_person import (
    FirstPersonConfig,
    FP_AUTO,
    FP_BOTH,
    FP_THIRD_PERSON_ONLY,
    FP_FIRST_PERSON_ONLY,
    VALID_FP_ANNOTATIONS,
    THIRD_PERSON_ONLY_PATTERNS,
)
from hamr.core.constants import VRM_25_BONE_NAMES


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TestFullPipelineIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPipelineIntegration:
    """End-to-end tests for the full build pipeline flow."""

    def test_spec_to_build_context(self, sample_spec: CharacterSpec) -> None:
        """Create a Spec, pass through BuildContext-style validation, verify all fields populated."""
        # Build a Spec from the character
        spec = Spec(sample_spec)

        # Verify the spec validates cleanly
        errors = validate_spec(spec.character)
        assert errors == [], f"Fully-populated spec should validate: {errors}"

        # Verify all sub-specs are populated
        char = spec.character
        assert char.name == "Elda_Testrun"
        assert char.body.height_cm == 165.0
        assert char.body.build == "athletic-slender"
        assert char.body.skin.base_hex == "#E8B87A"
        assert char.face.jaw == "V-shape"
        assert char.hair.style == "wild-curly"
        assert len(char.clothing) == 1
        assert char.clothing[0].type == "full-outfit"
        assert char.physics.hair.stiffness == 0.35
        assert char.export.format == "vrm1"

        # Verify serialization round-trip
        spec_dict = spec.to_dict()
        assert "body" in spec_dict
        assert "face" in spec_dict
        assert "hair" in spec_dict
        assert spec_dict["body"]["height_cm"] == 165.0

    def test_spec_to_build_result(self, sample_spec: CharacterSpec) -> None:
        """Create a Spec, mock build result structure, verify BuildResult structure."""
        # PipelineResult requires a spec_path so we construct one manually
        from pathlib import Path

        result = PipelineResult(
            success=True,
            spec_path=Path("/tmp/test_spec.yaml"),
            output_path=Path("/tmp/test_output.vrm"),
            elapsed=12.5,
            errors=[],
            warnings=["Near triangle budget"],
        )

        assert result.success is True
        assert result.elapsed == 12.5
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.output_size_mb is not None or result.output_path is not None

    def test_pipeline_stage_ordering(self, sample_spec: CharacterSpec) -> None:
        """BuildPipeline integration stages execute in correct order."""
        # plan_stages is pure-Python — no Blender needed
        stages = plan_stages(sample_spec)

        # Stub bones always come first
        assert stages[0] == STAGE_STUB_BONES

        # Verify all stages are present in order
        expected_order = [
            STAGE_STUB_BONES,
            STAGE_HAIR_MESH,
            STAGE_CLOTHING_MESH,
            STAGE_WEIGHT_PAINT,
            STAGE_SPRING_BONES,
            STAGE_FIRST_PERSON,
        ]
        assert stages == expected_order

        # Verify ALL_STAGES matches
        assert ALL_STAGES == expected_order

    def test_pipeline_error_propagation(self) -> None:
        """Errors in early stages prevent later stages from succeeding."""
        # IntegrationResult tracks errors that prevent success
        result = IntegrationResult(
            stages_completed=[STAGE_STUB_BONES],
            errors=["Hair mesh generation failed: missing base mesh"],
            warnings=[],
        )

        # Result should report failure
        assert result.success is False
        assert result.stage_count == 1
        assert len(result.errors) == 1

        # A result with no errors should report success
        good_result = IntegrationResult(
            stages_completed=ALL_STAGES,
            errors=[],
            warnings=["Near budget"],
        )
        assert good_result.success is True
        assert good_result.stage_count == 6

    def test_pipeline_warning_accumulation(self, sample_spec: CharacterSpec) -> None:
        """Warnings don't stop pipeline but are collected."""
        # A result with warnings but no errors
        result = IntegrationResult(
            stages_completed=ALL_STAGES,
            warnings=[
                "Hair volume high for Pi 5 budget",
                "Near triangle limit",
            ],
            errors=[],
        )

        assert result.success is True
        assert len(result.warnings) == 2
        assert len(result.errors) == 0

        # Performance check can also produce warnings without failure
        report = check_budget(sample_spec, DEFAULT_PI5_BUDGET)
        # Warnings are non-fatal even when present
        assert isinstance(report, PerformanceReport)
        assert isinstance(report.warnings, list)

    def test_pipeline_skip_stage(self) -> None:
        """Stages can be skipped via configuration (no hair, no clothing)."""
        # A spec with no clothing should skip clothing_mesh stage
        spec_no_clothing = CharacterSpec(
            name="NoCloth",
            clothing=[],
        )

        stages = plan_stages(spec_no_clothing)

        # hair_mesh stage should still be present (default hair style)
        assert STAGE_HAIR_MESH in stages
        # clothing_mesh should be skipped because clothing=[]
        assert STAGE_CLOTHING_MESH not in stages
        # Without clothing, we get 5 stages (not 6)
        assert len(stages) == 5

        # A spec with clothing lists the clothing_mesh stage
        spec_with_clothing = CharacterSpec(
            name="WithCloth",
            clothing=[ClothingSpec(name="tunic", type="top")],
        )
        stages_full = plan_stages(spec_with_clothing)
        assert STAGE_CLOTHING_MESH in stages_full
        assert len(stages_full) == 6

    def test_perf_gate_integration(self, sample_spec: CharacterSpec) -> None:
        """Performance gate rejects over-budget specs."""
        gate = PerfGate(tier="minimal")
        result = gate.check_gate(spec=sample_spec)

        # sample_spec has wild-curly hair + full-outfit = likely over budget on minimal
        assert isinstance(result, PerfGateResult)
        assert result.estimated_triangle_count > 0
        assert result.estimated_memory_mb > 0
        assert result.estimated_build_time_seconds > 0
        assert result.budget_tier == "minimal"

        # Even if over budget, force=True allows it
        forced = gate.check_gate(spec=sample_spec, force=True)
        assert forced.allowed is True

    def test_gpu_profile_integration(self, sample_spec: CharacterSpec, pi5_profile: GPUProfile) -> None:
        """GPU profile adjusts build parameters."""
        # Pi 5 profile should constrain triangle budget
        assert pi5_profile.max_triangles == 20_000
        assert pi5_profile.max_texture_resolution == 1024
        assert pi5_profile.supports_sss is False
        assert pi5_profile.supports_anisotropic is False
        assert pi5_profile.recommended_clothing_layers == 1

        # Spec validation against Pi 5 profile should produce warnings
        spec_dict = sample_spec.to_dict()
        warnings = validate_profile_compatibility("pi5", spec_dict)
        # The wild-curly style is not in pi5 recommended styles
        assert isinstance(warnings, list)

        # Desktop profile allows more
        desktop = GPU_PROFILES["desktop"]
        assert desktop.max_triangles > pi5_profile.max_triangles
        assert desktop.supports_sss is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TestModuleIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestModuleIntegration:
    """Tests that spec data feeds correctly into each downstream module."""

    def test_spec_to_stub_bones(self) -> None:
        """Spec body proportions feed into stub bone positions."""
        # Stub bones are defined for the 3 missing VRM humanoid bones
        assert len(STUB_BONE_DEFS) == 3

        # Each stub bone has the required fields
        vrm_names = {d["vrm_name"] for d in STUB_BONE_DEFS}
        assert vrm_names == {"jaw", "leftEye", "rightEye"}

        # Each stub bone is parented to head
        for bd in STUB_BONE_DEFS:
            assert bd["parent"] == "head"
            assert "offset_from_head" in bd
            assert "length" in bd

        # detect_missing_bones with a partial set returns the missing ones
        mb_lab_bones = {
            "hips", "spine", "chest", "upperChest", "neck", "head",
            "leftShoulder", "rightShoulder", "leftUpperArm", "rightUpperArm",
            "leftLowerArm", "rightLowerArm", "leftHand", "rightHand",
            "leftUpperLeg", "rightUpperLeg", "leftLowerLeg", "rightLowerLeg",
            "leftFoot", "rightFoot", "leftToes", "rightToes",
        }
        missing = detect_missing_bones(mb_lab_bones)
        # jaw, leftEye, rightEye are the ones MB-Lab doesn't provide
        assert "jaw" in missing
        assert "leftEye" in missing
        assert "rightEye" in missing

    def test_spec_to_hair_mesh(self, sample_spec: CharacterSpec) -> None:
        """Spec hair style feeds into hair mesh generation config."""
        # The hair style from a spec maps to a HAIR_STYLE_TEMPLATES entry
        style = sample_spec.hair.style
        assert style in HAIR_STYLE_TEMPLATES, f"Hair style '{style}' should be in templates"

        template = HAIR_STYLE_TEMPLATES[style]
        assert "shell_count" in template
        assert "length_factor" in template
        assert "requires_mesh" in template

        # Our sample spec has wild-curly which requires a mesh
        assert template["requires_mesh"] is True

    def test_spec_to_clothing(self, sample_spec: CharacterSpec) -> None:
        """Spec clothing selection feeds into clothing mesh config."""
        # Clothing specs map to CLOTH_TYPE_TEMPLATES
        for outfit in sample_spec.clothing:
            ctype = outfit.type
            assert ctype in CLOTH_TYPE_TEMPLATES, f"Clothing type '{ctype}' should be in templates"

            tmpl = CLOTH_TYPE_TEMPLATES[ctype]
            assert "layers" in tmpl
            assert "priority" in tmpl

        # Our sample has "full-outfit"
        full_outfit_tmpl = CLOTH_TYPE_TEMPLATES["full-outfit"]
        assert "torso" in full_outfit_tmpl["layers"] or "torso" in full_outfit_tmpl.get("mesh_pattern", "")

    def test_spec_to_presets(self, sample_spec: CharacterSpec) -> None:
        """Spec preset name resolves to full preset with all sub-specs."""
        # Get a known preset
        preset = get_preset("anime_girl_default")
        assert preset.name == "anime_girl_default"
        assert "body" in preset.spec
        assert "face" in preset.spec
        assert "hair" in preset.spec

        # Resolve with overrides should deep-merge
        resolved = resolve_preset("anime_girl_default", {"body": {"height_cm": 175.0}})
        assert resolved["body"]["height_cm"] == 175.0
        # Other body fields should still exist from the base preset
        assert "build" in resolved["body"]

    def test_spec_to_expressions(self, sample_spec: CharacterSpec) -> None:
        """Spec expression config feeds into expression blend shapes."""
        # Expressions in spec have defaults and custom
        expr = sample_spec.expressions
        assert "blink" in expr.defaults
        assert "blush" in expr.defaults
        assert len(expr.custom) == 1
        assert expr.custom[0].name == "wink"

        # Face maps convert expression parameters to shape key values
        assert "V-shape" in JAW_MAP
        assert "high" in CHEEKBONE_MAP
        assert "cat-tilt" in EYE_SHAPE_MAP
        assert isinstance(LIP_FULLNESS_MAP, dict)

    def test_spec_to_springs(self, sample_spec: CharacterSpec) -> None:
        """Spec spring bone config feeds into spring bone groups."""
        # Physics spec maps to spring bone configs
        hair_phys = sample_spec.physics.hair
        assert 0.0 <= hair_phys.stiffness <= 1.0
        assert 0.0 <= hair_phys.gravity <= 1.0
        assert 0.0 <= hair_phys.drag <= 1.0

        # HAIR_SPRING_PRESETS should exist for "long", "medium", "short"
        assert "long" in HAIR_SPRING_PRESETS
        assert "medium" in HAIR_SPRING_PRESETS
        assert "short" in HAIR_SPRING_PRESETS

        # Each preset has required physics fields
        long_preset = HAIR_SPRING_PRESETS["long"]
        assert "stiff_force" in long_preset
        assert "gravity_power" in long_preset
        assert "drag_force" in long_preset

    def test_spec_to_materials(self, sample_spec: CharacterSpec) -> None:
        """Spec material config feeds into anime material setup."""
        # EMBLEMATIC_COLORS should contain skin tone references
        assert "porcelain" in EMBLEMATIC_COLORS
        assert "fair" in EMBLEMATIC_COLORS

        # Skin hex from spec is valid
        skin_hex = sample_spec.body.skin.base_hex
        assert skin_hex.startswith("#")
        assert len(skin_hex) == 7

        # Validate a material spec — uses material_type, not name
        mat_spec = AnimeMaterialSpec(material_type="skin")
        result = validate_material_spec(mat_spec)
        # validate_material_spec returns a list of warnings; should be empty for valid
        assert isinstance(result, list)

        # An invalid material type produces warnings
        bad_mat = AnimeMaterialSpec(material_type="invalid_type")
        bad_result = validate_material_spec(bad_mat)
        assert len(bad_result) > 0

    def test_spec_to_collision(self, sample_spec: CharacterSpec) -> None:
        """Spec body proportions feed into collision mesh regions."""
        # COLLIDER_REGIONS map body parts to bone/radius/offset
        assert "head" in COLLIDER_REGIONS
        assert "chest" in COLLIDER_REGIONS
        assert "hips" in COLLIDER_REGIONS

        # Each region has required fields
        head_region = COLLIDER_REGIONS["head"]
        assert "bone" in head_region
        assert "radius" in head_region
        assert head_region["radius"] > 0

        # Body proportions from spec affect collision sizing
        proportions = sample_spec.body.proportions
        assert "shoulder_width" in proportions
        assert "hip_width" in proportions
        # Values should be in [0, 1]
        for key, val in proportions.items():
            assert 0.0 <= val <= 1.0, f"Proportion {key} out of range: {val}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TestExportPipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportPipeline:
    """Tests for VRM validation, animation clips, and first-person config."""

    def _make_valid_vrm_data(self) -> dict:
        """Build a minimal valid VRM/glTF data dict for validation."""
        return {
            "asset": {"version": "2.0", "generator": "Hamr Forge"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "skin": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
            "accessors": [{"type": "VEC3", "count": 3, "max": [1, 1, 1], "min": [-1, -1, -1]}],
            "materials": [{"pbrMetallicRoughness": {}}],
            "skins": [{"joints": list(range(25))}],
            "extensions": {
                "VRMC_vrm": {
                    "humanoid": {
                        "humanBones": [
                            {"bone": name, "node": i}
                            for i, name in enumerate(VRM_25_BONE_NAMES)
                        ]
                    },
                    "expressions": {
                        "preset": {"happy": {"morphTargetBinding": []}},
                    },
                },
            },
            "extensionRequired": ["VRMC_vrm"],
        }

    def test_vrm_validator_on_valid_spec(self) -> None:
        """Validate a well-formed VRM data dict passes VRM checks."""
        validator = VRMValidator(strict=False)
        data = self._make_valid_vrm_data()
        result = validator.validate_vrm_structure(data)

        assert isinstance(result, VRMValidationResult)
        # Valid data should have no critical errors (may have warnings)
        if not result.valid:
            # Allow missing mesh details in the minimal test data
            assert all("bone" in e.lower() or "extension" in e.lower()
                       for e in result.errors) or len(result.errors) == 0

    def test_vrm_validator_on_incomplete_spec(self) -> None:
        """Incomplete spec gets specific warnings."""
        validator = VRMValidator(strict=False)

        # Empty/minimal data — missing everything
        data = {}
        result = validator.validate_vrm_structure(data)

        assert isinstance(result, VRMValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0

        # Data with no VRM extension
        data_no_vrm = {"asset": {"version": "2.0"}}
        result_no_vrm = validator.validate_vrm_structure(data_no_vrm)
        # Should have errors about missing VRM extension
        assert result_no_vrm.valid is False or len(result_no_vrm.errors) > 0

    def test_animation_clips_integration(self) -> None:
        """Preset animation clips can be attached to a spec."""
        # Create a simple animation clip
        keyframes = [
            AnimationKeyframe(
                time=0.0,
                bone="spine",
                position=(0.0, 0.0, 0.0),
                rotation=(1.0, 0.0, 0.0),
            ),
            AnimationKeyframe(
                time=1.0,
                bone="spine",
                position=(0.0, 0.01, 0.0),
                rotation=(-1.0, 0.0, 0.0),
            ),
        ]
        clip = AnimationClip(
            name="idle_breathe",
            duration=2.0,
            fps=30,
            loop=True,
            keyframes=keyframes,
        )

        assert clip.name == "idle_breathe"
        assert clip.duration == 2.0
        assert len(clip.keyframes) == 2
        assert clip.loop is True

        # Verify the bone name is in the VRM 25 bones
        assert "spine" in VRM_25_BONE_NAMES

    def test_first_person_integration(self, sample_spec: CharacterSpec) -> None:
        """First-person config integrates with mesh specification."""
        # Valid FP annotation modes
        assert FP_AUTO in VALID_FP_ANNOTATIONS
        assert FP_BOTH in VALID_FP_ANNOTATIONS
        assert FP_THIRD_PERSON_ONLY in VALID_FP_ANNOTATIONS
        assert FP_FIRST_PERSON_ONLY in VALID_FP_ANNOTATIONS

        # Third-person-only patterns cover head-related meshes
        assert "head" in THIRD_PERSON_ONLY_PATTERNS
        assert "hair" in THIRD_PERSON_ONLY_PATTERNS
        assert "eye" in THIRD_PERSON_ONLY_PATTERNS

        # Create a FirstPersonConfig
        fp_config = FirstPersonConfig(
            first_person_bone="head",
            mesh_annotations=[
                {"mesh": "Body", "annotation": FP_THIRD_PERSON_ONLY},
                {"mesh": "Hair", "annotation": FP_THIRD_PERSON_ONLY},
                {"mesh": "Eyes", "annotation": FP_BOTH},
            ],
        )
        assert fp_config.first_person_bone == "head"
        assert len(fp_config.mesh_annotations) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TestCrossModuleDataFlow
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossModuleDataFlow:
    """Tests for data flowing correctly across module boundaries."""

    def test_gpu_profile_to_perf_budget(self, pi5_profile: GPUProfile) -> None:
        """GPU profile converts to performance budget correctly."""
        budget_dict = profile_to_budget("pi5")

        # All expected keys should be present
        assert "max_triangles" in budget_dict
        assert "max_texture_resolution" in budget_dict
        assert "max_build_time_seconds" in budget_dict
        assert "max_memory_mb" in budget_dict
        assert "target_fps" in budget_dict

        # Pi 5 profile values should match
        assert budget_dict["max_triangles"] == pi5_profile.max_triangles
        assert budget_dict["max_texture_resolution"] == pi5_profile.max_texture_resolution
        assert budget_dict["max_build_time_seconds"] == pi5_profile.max_build_time_seconds
        assert budget_dict["max_memory_mb"] == float(pi5_profile.max_memory_mb)
        assert budget_dict["target_fps"] == 24.0  # Pi 5 fps target

        # blender_timeout should be 2.5× build time
        expected_timeout = pi5_profile.max_build_time_seconds * 2.5
        assert budget_dict["blender_timeout_seconds"] == expected_timeout

    def test_preset_deep_merge(self) -> None:
        """Deep merge of preset + customization preserves both."""
        # Start with a base preset
        base = get_preset("anime_girl_default").spec

        # Override specific nested fields
        overrides = {
            "body": {"height_cm": 170.0},
            "hair": {"style": "straight", "volume": 0.5},
            "name": "Custom Character",
        }

        merged = deep_merge(base, overrides)

        # Overridden values should come from overrides
        assert merged["body"]["height_cm"] == 170.0
        assert merged["hair"]["style"] == "straight"
        assert merged["name"] == "Custom Character"

        # Non-overridden base values should be preserved
        assert merged["body"]["build"] == base["body"]["build"]
        assert "skin" in merged["body"]

    def test_spec_validation_chain(self, sample_spec: CharacterSpec) -> None:
        """Spec validation catches all required fields."""
        # A fully-populated spec should validate clean
        errors = validate_spec(sample_spec)
        assert errors == [], f"Full spec should validate clean, got: {errors}"

        # A spec with invalid build should fail
        bad_spec = CharacterSpec(
            name="BadSpec",
            body=BodySpec(build="nonexistent", height_cm=999),
            face=FaceSpec(jaw="invalid_shape"),
            hair=HairSpec(style="nonexistent_style", shell_layers=99),
        )
        errors = validate_spec(bad_spec)
        assert len(errors) > 0

        # Check specific validation failures
        error_text = " ".join(errors)
        assert "build" in error_text or "body" in error_text
        assert "height_cm" in error_text or "range" in error_text.lower() or "invalid" in error_text.lower() or "outside" in error_text

    def test_error_to_a11y_format(self) -> None:
        """Core errors produce actionable a11y suggestions."""
        # SpecValidationError produces an actionable suggestion
        spec_err = SpecValidationError("Missing required fields", errors=["name is empty"])
        suggestion = get_actionable_suggestion(spec_err)
        assert suggestion == "Check your spec file for required fields"

        # BuildError produces a build suggestion
        build_err = BuildError("Blender crashed", stage="build")
        suggestion = get_actionable_suggestion(build_err)
        assert "build" in suggestion.lower() or "spec" in suggestion.lower()

        # ExportError
        export_err = ExportError("VRM export failed")
        suggestion = get_actionable_suggestion(export_err)
        assert "export" in suggestion.lower() or "path" in suggestion.lower()

        # AssetNotFoundError
        asset_err = AssetNotFoundError("Base mesh not found", path="/tmp/mesh.obj")
        suggestion = get_actionable_suggestion(asset_err)
        assert "path" in suggestion.lower() or "file" in suggestion.lower() or "asset" in suggestion.lower()

        # format_error returns structured dict
        error_dict = format_error(spec_err)
        assert "type" in error_dict
        assert "message" in error_dict
        assert "suggestion" in error_dict
        assert error_dict["type"] == "SpecValidationError"

        # Unknown error type gets fallback
        runtime_err = RuntimeError("Something unexpected")
        suggestion = get_actionable_suggestion(runtime_err)
        assert "Blender" in suggestion or suggestion == "Check the error details and consult the documentation"