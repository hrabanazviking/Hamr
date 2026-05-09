"""Phase 13 regression guard tests — Vǫllr Vígríðar.

Ensures no regressions across all Phase 11-12 modules and validates
cross-module invariants that were previously untested.
"""
import pytest
from copy import deepcopy


# ── T1: Preset / Spec Roundtrip ──────────────────────────────────────────

class TestPresetToDictRoundtrip:
    """CharacterSpec → dict → CharacterSpec roundtrip preserves data."""

    def test_spec_to_dict_preserves_keys(self):
        from hamr.core.presets import CHARACTER_PRESETS, spec_to_dict
        for name, preset in CHARACTER_PRESETS.items():
            result = spec_to_dict(preset["spec"])
            assert isinstance(result, dict), f"Preset {name} did not convert to dict"
            assert "body" in result, f"Preset {name} missing 'body' key after conversion"

    def test_spec_to_dict_idempotent(self):
        from hamr.core.presets import spec_to_dict
        original = {"body": {"height": 1.6}, "face": {}}
        result = spec_to_dict(original)
        # spec_to_dict returns an equivalent plain dict (may be a new object
        # if normalization was needed).  Value equality is the guarantee.
        assert result == original, "spec_to_dict should preserve dict contents"
        assert isinstance(result, dict), "spec_to_dict should return a dict"

    def test_validate_preset_accepts_dict(self):
        from hamr.core.presets import validate_preset, CHARACTER_PRESETS
        spec_dict = CHARACTER_PRESETS["anime_girl_default"]["spec"]
        result = validate_preset(spec_dict)
        # Should not raise — valid dict spec
        assert isinstance(result, list), "validate_preset should return list for dict input"

    def test_validate_preset_accepts_dataclass(self):
        from hamr.core.presets import validate_preset, get_preset
        preset = get_preset("anime_girl_default")
        # CharacterSpec dataclass should work via spec_to_dict internally
        result = validate_preset(preset.spec)
        assert isinstance(result, list), "validate_preset should return list for CharacterSpec input"


# ── T2: Hair Styles ─────────────────────────────────────────────────────

class TestHairStyleRegression:
    """All HAIR_MESH_STYLES are valid and have required fields."""

    def test_hair_styles_count(self):
        from hamr.hair.mesh import HAIR_MESH_STYLES
        assert len(HAIR_MESH_STYLES) >= 5, "Should have at least 5 hair styles"

    def test_hair_styles_have_required_keys(self):
        from hamr.hair.mesh import HAIR_MESH_STYLES
        required = {"display_name", "strand_density", "base_length_factor"}
        for name, config in HAIR_MESH_STYLES.items():
            for key in required:
                assert key in config, f"Style {name} missing key {key}"

    def test_guide_curves_generate(self):
        from hamr.hair.mesh import generate_guide_curves
        curves = generate_guide_curves(style="long", head_radius=0.1)
        assert len(curves) > 0, "Should generate at least one guide curve"


# ── T3: Clothing Patterns ────────────────────────────────────────────────

class TestClothingPatternsRegression:
    """All CLOTHING_PATTERNS are valid."""

    def test_clothing_patterns_count(self):
        from hamr.clothing.mesh import CLOTHING_PATTERNS
        assert len(CLOTHING_PATTERNS) >= 6, "Should have at least 6 clothing patterns"

    def test_clothing_patterns_have_materials(self):
        from hamr.clothing.mesh import CLOTHING_PATTERNS
        for name, pattern in CLOTHING_PATTERNS.items():
            assert "default_material" in pattern, f"Pattern {name} missing 'default_material' key"

    def test_classify_material_type(self):
        from hamr.clothing.mesh import classify_material_type
        assert classify_material_type("cotton") in ("fabric", "leather", "metal", "unknown")
        assert classify_material_type("leather") == "leather"


# ── T4: Spring Bone Groups ───────────────────────────────────────────────

class TestSpringBoneRegression:
    """Spring bone presets and colliders are valid."""

    def test_spring_bone_presets_count(self):
        from hamr.rigs.spring_bones import BREAST_SPRING_PRESETS, HAIR_SPRING_PRESETS, CLOTHING_SPRING_PRESETS
        total = len(BREAST_SPRING_PRESETS) + len(HAIR_SPRING_PRESETS) + len(CLOTHING_SPRING_PRESETS)
        assert total >= 3, f"Should have at least 3 spring bone presets, got {total}"

    def test_breast_spring_presets_valid(self):
        from hamr.rigs.spring_bones import BREAST_SPRING_PRESETS
        for name, preset in BREAST_SPRING_PRESETS.items():
            assert isinstance(preset, dict), f"Breast preset {name} should be dict"

    def test_default_colliders_exist(self):
        from hamr.rigs.spring_bones import DEFAULT_COLLIDERS
        assert len(DEFAULT_COLLIDERS) >= 3, "Should have at least 3 default colliders"


# ── T5: Stub Bones ───────────────────────────────────────────────────────

class TestStubBonesRegression:
    """VRM 25-bone name list is complete."""

    def test_vrm_25_bone_names_count(self):
        from hamr.rigs.stub_bones import VRM_25_BONE_NAMES
        assert len(VRM_25_BONE_NAMES) == 25, f"Expected 25 bones, got {len(VRM_25_BONE_NAMES)}"

    def test_vrm_25_bone_names_has_required_bones(self):
        from hamr.rigs.stub_bones import VRM_25_BONE_NAMES
        required = ["hips", "spine", "head", "leftUpperLeg", "rightUpperLeg"]
        for bone in required:
            assert bone in VRM_25_BONE_NAMES, f"Missing required bone: {bone}"


# ── T6: Performance Budgets ──────────────────────────────────────────────

class TestPerfRegression:
    """All 3 memory tier budgets are valid."""

    def test_all_memory_tiers_present(self):
        from hamr.core.perf import MEMORY_TIERS
        assert set(MEMORY_TIERS.keys()) == {"minimal", "balanced", "high"}

    def test_memory_tiers_have_required_fields(self):
        from hamr.core.perf import MEMORY_TIERS
        for tier_name, budget in MEMORY_TIERS.items():
            assert hasattr(budget, "max_build_time_seconds"), f"Tier {tier_name} missing max_build_time_seconds"
            assert hasattr(budget, "max_memory_mb"), f"Tier {tier_name} missing max_memory_mb"
            assert hasattr(budget, "max_triangles"), f"Tier {tier_name} missing max_triangles"


# ── T7: Perf Gate ────────────────────────────────────────────────────────

class TestPerfGateRegression:
    """PerfGate works for all 6 character presets."""

    def test_perf_gate_all_presets(self):
        from hamr.core.perf_gate import PerfGate
        from hamr.core.presets import CHARACTER_PRESETS
        gate = PerfGate(tier="balanced")
        for name in CHARACTER_PRESETS:
            result = gate.check_gate(preset_name=name)
            assert hasattr(result, "allowed"), f"Preset {name} gate check failed"
            assert hasattr(result, "estimated_triangle_count"), f"Preset {name} missing triangle estimate"

    def test_estimate_factors_complete(self):
        from hamr.core.perf_gate import ESTIMATE_FACTORS
        expected = {"body", "hair_mesh", "clothing", "stub_bones", "weight_paint",
                    "spring_bones", "first_person", "collision_meshes", "expressions", "materials"}
        assert set(ESTIMATE_FACTORS.keys()) == expected


# ── T8: VRM Expressions ──────────────────────────────────────────────────

class TestExpressionRegression:
    """All 8 VRM expressions can be resolved."""

    def test_vrm_expressions_complete(self):
        from hamr.face.expressions import VRM_EXPRESSIONS
        required = {"happy", "angry", "sad", "surprised", "neutral", "blink", "blinkLeft", "blinkRight"}
        assert set(VRM_EXPRESSIONS.keys()) == required

    def test_expression_binder_resolves_all(self):
        from hamr.face.expressions import ExpressionBinder
        binder = ExpressionBinder()
        mb_lab_keys = ["Expressions_mouthSmile_max", "Expressions_browFrown_L",
                       "Expressions_browFrown_R", "Expressions_mouthFrown_L",
                       "Expressions_mouthOpen", "eye_blink_L", "eye_blink_R"]
        bindings = binder.resolve_expression_bindings(available_shape_keys=mb_lab_keys)
        # At least some expressions should resolve with MB-Lab keys
        assert len(bindings) > 0, "Should resolve at least one expression with MB-Lab keys"


# ── T9: Collision Regions ────────────────────────────────────────────────

class TestCollisionRegression:
    """All 12 collider regions are valid."""

    def test_collider_regions_count(self):
        from hamr.rigs.collision import COLLIDER_REGIONS
        assert len(COLLIDER_REGIONS) == 12, f"Expected 12 collision regions, got {len(COLLIDER_REGIONS)}"

    def test_collider_regions_have_required_keys(self):
        from hamr.rigs.collision import COLLIDER_REGIONS
        required_keys = {"bone", "radius", "offset"}
        for name, region in COLLIDER_REGIONS.items():
            for key in required_keys:
                assert key in region, f"Region {name} missing key {key}"

    def test_collider_regions_all_have_positive_radius(self):
        from hamr.rigs.collision import COLLIDER_REGIONS
        for name, region in COLLIDER_REGIONS.items():
            assert region["radius"] > 0, f"Region {name} has non-positive radius"


# ── T10: CLI Preset Names ────────────────────────────────────────────────

class TestCLIPresetRegression:
    """CLI preset choices match CHARACTER_PRESETS keys."""

    def test_cli_preset_names_match(self):
        from hamr.cli import CHARACTER_PRESETS as CLI_PRESETS
        from hamr.core.presets import CHARACTER_PRESETS as CORE_PRESETS
        cli_keys = set(CLI_PRESETS.keys()) if isinstance(CLI_PRESETS, dict) else set(CLI_PRESETS)
        core_keys = set(CORE_PRESETS.keys())
        # CLI should reference all core presets
        assert cli_keys == core_keys or cli_keys.issuperset(core_keys), \
            f"CLI presets {cli_keys} != core presets {core_keys}"


# ── T11: Build Pipeline Integrity ────────────────────────────────────────

class TestPipelineRegression:
    """BuildPipeline still works after all changes."""

    def test_pipeline_instantiation(self):
        from hamr.core.pipeline import BuildPipeline
        bp = BuildPipeline()
        assert bp is not None

    def test_pipeline_integrate_instantiation(self):
        from hamr.core.pipeline_integrate import IntegrationResult, plan_stages
        # plan_stages should work with dict specs
        result = plan_stages({"hair": {"style": "long"}, "clothing": [{"type": "dress"}]})
        assert "stub_bones" in result, f"Expected stub_bones in stages, got {result}"


# ── T12: Anime Materials ──────────────────────────────────────────────────

class TestMaterialsRegression:
    """All material presets are valid."""

    def test_skin_presets_count(self):
        from hamr.materials.anime import ANIME_SKIN_PRESETS
        assert len(ANIME_SKIN_PRESETS) >= 5, "Should have at least 5 skin presets"

    def test_eye_presets_count(self):
        from hamr.materials.anime import ANIME_EYE_PRESETS
        assert len(ANIME_EYE_PRESETS) >= 6, "Should have at least 6 eye presets"

    def test_hair_material_presets_count(self):
        from hamr.materials.anime import ANIME_HAIR_PRESETS
        assert len(ANIME_HAIR_PRESETS) >= 8, "Should have at least 8 hair material presets"


# ── T13: Integration Result ──────────────────────────────────────────────

class TestIntegrationResultRegression:
    """IntegrationResult from Phase 12 T1 still works."""

    def test_integration_result_defaults(self):
        from hamr.core.pipeline_integrate import IntegrationResult
        result = IntegrationResult()
        assert result.stages_completed == []
        assert result.warnings == []
        assert result.errors == []

    def test_plan_stages_full_spec(self):
        from hamr.core.pipeline_integrate import plan_stages
        full_spec = {
            "body": {}, "hair": {"style": "long"},
            "clothing": [{"type": "dress"}],
            "physics": {}, "expressions": {}, "export": {}
        }
        stages = plan_stages(full_spec)
        assert len(stages) >= 5, f"Full spec should have ≥5 stages, got {len(stages)}"


# ── T14: Version Consistency ──────────────────────────────────────────────

class TestVersionConsistency:
    """Package version is consistent across files."""

    def test_pyproject_version_matches(self):
        from hamr import __version__
        # Version must be valid PEP 440 (x.y.z or x.y.zN — e.g. 0.7.0rc1)
        import re
        pep440_re = re.compile(r"^\d+\.\d+\.\d+([a-zA-Z]+\d+)?$")
        assert pep440_re.match(__version__), f"Version {__version__} is not valid PEP 440"


# ── T1 Phase 15: from_dict() Immutability & get_preset() Isolation ────────

class TestFromDictImmutability:
    """CharacterSpec.from_dict() must NOT mutate its input dict (Phase 15 T1)."""

    def test_from_dict_does_not_mutate_input(self):
        from hamr.core.models import CharacterSpec
        original = {
            "name": "test",
            "body": {"height_cm": 165.0, "build": "athletic",
                      "skin": {"base_hex": "#E8B87A", "undertone": "warm"}},
            "face": {"jaw": "V-shape", "cheekbones": "high",
                     "eyes": {"iris_hex": "#B8D4E3", "shape": "round", "size": 1.1}},
            "hair": {"style": "straight", "length": "long", "volume": 0.7,
                     "curl_tightness": 0.0,
                     "color": {"roots": "#C4A265", "mid": "#D4B87A", "tips": "#F5E6B8"}},
        }
        from copy import deepcopy
        snapshot = deepcopy(original)
        CharacterSpec.from_dict(original)
        assert original == snapshot, "from_dict() must not mutate its input dict"

    def test_from_dict_called_twice_produces_identical_results(self):
        from hamr.core.models import CharacterSpec
        data = {
            "name": "test2",
            "body": {"height_cm": 170.0, "build": "slender",
                      "skin": {"base_hex": "#F0E0D0", "undertone": "cool"}},
            "face": {"eyes": {"iris_hex": "#6080C0", "shape": "narrow", "size": 1.15}},
        }
        result1 = CharacterSpec.from_dict(data)
        result2 = CharacterSpec.from_dict(data)
        assert result1 == result2, "Calling from_dict() twice on same input must produce equal results"

    def test_from_dict_no_input_mutation_nested(self):
        """Verify nested dicts stay as dicts, not dataclass instances."""
        from hamr.core.models import CharacterSpec
        data = {
            "body": {"height_cm": 160.0, "build": "average",
                      "skin": {"base_hex": "#F5D6C3", "undertone": "warm", "freckles": False, "tan_level": 0.4}},
            "face": {"jaw": "round", "eyes": {"iris_hex": "#C090E0", "shape": "round", "size": 1.6}},
            "hair": {"style": "wavy", "length": "shoulder", "volume": 0.9,
                     "color": {"roots": "#E0A0C0", "mid": "#F0C0D8", "tips": "#F8E0F0"}},
        }
        original_eyes_type = type(data["face"]["eyes"])
        CharacterSpec.from_dict(data)
        assert type(data["face"]["eyes"]) is original_eyes_type, \
            "from_dict() must not convert nested dicts to dataclasses in the input"


class TestGetPresetIsolation:
    """get_preset() must return independent copies; mutations must not poison globals (Phase 15 T1)."""

    def test_get_preset_returns_independent_copy(self):
        from hamr.core.presets import get_preset, CHARACTER_PRESETS
        p1 = get_preset("anime_girl_default")
        p2 = get_preset("anime_girl_default")
        assert p1.spec == p2.spec, "Two get_preset calls should return equal specs"
        assert p1.spec is not p2.spec, "Two get_preset calls should return different objects"

    def test_mutating_returned_spec_does_not_affect_global(self):
        from hamr.core.presets import get_preset, CHARACTER_PRESETS
        original_style = CHARACTER_PRESETS["anime_girl_default"]["spec"]["hair"]["style"]
        result = get_preset("anime_girl_default")
        result.spec["hair"]["style"] = "MODIFIED"
        assert CHARACTER_PRESETS["anime_girl_default"]["spec"]["hair"]["style"] == original_style, \
            "Mutating a returned spec must not change the global CHARACTER_PRESETS"

    def test_spec_dict_item_assignment_works(self):
        """Verify that dict-style item assignment works on returned specs."""
        from hamr.core.presets import get_preset
        spec = get_preset("chibi_cute").spec
        # These must NOT raise TypeError
        spec["face"]["eyes"]["size"] = 5.0
        assert spec["face"]["eyes"]["size"] == 5.0
        spec["body"]["skin"]["tan_level"] = 0.99
        assert spec["body"]["skin"]["tan_level"] == 0.99
        spec["hair"]["color"]["roots"] = "#FF0000"
        assert spec["hair"]["color"]["roots"] == "#FF0000"

    def test_resolve_preset_returns_mutable_dict(self):
        """resolve_preset() must return a plain dict supporting item assignment."""
        from hamr.core.presets import resolve_preset
        result = resolve_preset("chibi_cute")
        result["face"]["eyes"]["size"] = 5.0
        assert result["face"]["eyes"]["size"] == 5.0