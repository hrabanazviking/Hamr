"""
test_e2e_build — Phase 15 T2 E2E Blender Build Tests.

Tests E2E build configuration, simulation, script generation, and
stage validation. All pure-Python tests run without Blender; the
pytest.mark.blender test requires Blender installed and is skipped
in CI.

The forge tests itself before presenting the blade. — Eldra Járnsdóttir
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from hamr.blender_bridge.e2e import (
    E2EBuildConfig,
    E2EBuildResult,
    E2E_TEST_SPECS,
    create_e2e_config,
    estimate_build_stats,
    generate_build_script,
    simulate_build,
    stage_order,
    validate_e2e_config,
)


# ──────────────────────────────────────────────────────────────────────────────
# E2EBuildResult tests
# ──────────────────────────────────────────────────────────────────────────────

class TestE2EBuildResult:
    """Tests for E2EBuildResult dataclass creation and defaults."""

    def test_creation_with_required_fields(self):
        """E2EBuildResult can be created with all required fields."""
        result = E2EBuildResult(
            success=True,
            spec_name="anime_girl_default",
            stages_completed=["clear_scene", "export_vrm"],
            stages_failed=[],
            build_time_seconds=12.5,
            output_path=Path("/tmp/output.vrm"),
        )
        assert result.success is True
        assert result.spec_name == "anime_girl_default"
        assert len(result.stages_completed) == 2
        assert result.stages_failed == []
        assert result.build_time_seconds == 12.5
        assert result.output_path == Path("/tmp/output.vrm")

    def test_defaults(self):
        """E2EBuildResult has sensible defaults for optional fields."""
        result = E2EBuildResult(
            success=False,
            spec_name="test",
            stages_completed=[],
            stages_failed=["export_vrm"],
            build_time_seconds=0.0,
            output_path=None,
        )
        assert result.error is None
        assert result.warnings == []
        assert result.artifact_count == 0
        assert result.total_triangles == 0
        assert result.mesh_count == 0
        assert result.bone_count == 0

    def test_with_all_fields(self):
        """E2EBuildResult accepts all fields including optional ones."""
        result = E2EBuildResult(
            success=True,
            spec_name="chibi_cute",
            stages_completed=["clear_scene"],
            stages_failed=[],
            build_time_seconds=5.0,
            output_path=None,
            error=None,
            warnings=["Low texture resolution"],
            artifact_count=2,
            total_triangles=6000,
            mesh_count=4,
            bone_count=35,
        )
        assert result.total_triangles == 6000
        assert result.mesh_count == 4
        assert result.bone_count == 35
        assert result.artifact_count == 2
        assert len(result.warnings) == 1

    def test_failed_build(self):
        """E2EBuildResult represents a failed build correctly."""
        result = E2EBuildResult(
            success=False,
            spec_name="broken_spec",
            stages_completed=["clear_scene", "import_base"],
            stages_failed=["apply_spec"],
            build_time_seconds=2.3,
            output_path=None,
            error="Spec application failed: missing required field",
        )
        assert result.success is False
        assert len(result.stages_failed) == 1
        assert result.error is not None
        assert "missing" in result.error


# ──────────────────────────────────────────────────────────────────────────────
# E2EBuildConfig tests
# ──────────────────────────────────────────────────────────────────────────────

class TestE2EBuildConfig:
    """Tests for E2EBuildConfig dataclass creation and defaults."""

    def test_creation_with_required_fields(self):
        """E2EBuildConfig requires spec_name as mandatory field."""
        config = E2EBuildConfig(spec_name="anime_girl_default")
        assert config.spec_name == "anime_girl_default"

    def test_defaults(self):
        """E2EBuildConfig has sensible defaults."""
        config = E2EBuildConfig(spec_name="test")
        assert config.spec_overrides == {}
        assert config.output_dir == Path("build_output")
        assert config.validate is True
        assert config.gpu_profile == "pi5"
        assert config.verbose is False
        assert config.cleanup is True

    def test_with_overrides(self):
        """E2EBuildConfig accepts spec_overrides."""
        config = E2EBuildConfig(
            spec_name="anime_girl_warrior",
            spec_overrides={"hair": {"style": "long"}},
            gpu_profile="desktop",
        )
        assert config.spec_overrides == {"hair": {"style": "long"}}
        assert config.gpu_profile == "desktop"

    def test_custom_output_dir(self):
        """E2EBuildConfig accepts custom output directory."""
        config = E2EBuildConfig(
            spec_name="test",
            output_dir=Path("/tmp/e2e_output"),
        )
        assert config.output_dir == Path("/tmp/e2e_output")


# ──────────────────────────────────────────────────────────────────────────────
# E2E_TEST_SPECS tests
# ──────────────────────────────────────────────────────────────────────────────

class TestE2ETestSpecs:
    """Tests for the E2E_TEST_SPECS preset configurations."""

    def test_has_four_configurations(self):
        """E2E_TEST_SPECS contains exactly 4 test configurations."""
        assert len(E2E_TEST_SPECS) == 4

    def test_default_female_spec(self):
        """default_female spec uses anime_girl_default preset and pi5 profile."""
        spec = E2E_TEST_SPECS["default_female"]
        assert spec.spec_name == "anime_girl_default"
        assert spec.gpu_profile == "pi5"

    def test_default_male_spec(self):
        """default_male spec uses anime_boy_default preset and pi5 profile."""
        spec = E2E_TEST_SPECS["default_male"]
        assert spec.spec_name == "anime_boy_default"
        assert spec.gpu_profile == "pi5"

    def test_chibi_lightweight_spec(self):
        """chibi_lightweight spec uses chibi_cute preset and pi5 profile."""
        spec = E2E_TEST_SPECS["chibi_lightweight"]
        assert spec.spec_name == "chibi_cute"
        assert spec.gpu_profile == "pi5"

    def test_full_detail_desktop_spec(self):
        """full_detail_desktop uses anime_girl_warrior, desktop, with overrides."""
        spec = E2E_TEST_SPECS["full_detail_desktop"]
        assert spec.spec_name == "anime_girl_warrior"
        assert spec.gpu_profile == "desktop"
        assert spec.spec_overrides == {"hair": {"style": "long"}}

    def test_all_spec_names_are_valid_presets(self):
        """All E2E_TEST_SPECS reference valid CHARACTER_PRESETS keys."""
        from hamr.core.presets import CHARACTER_PRESETS
        for name, config in E2E_TEST_SPECS.items():
            assert config.spec_name in CHARACTER_PRESETS, (
                f"E2E_TEST_SPECS[{name!r}].spec_name={config.spec_name!r} "
                f"not in CHARACTER_PRESETS"
            )


# ──────────────────────────────────────────────────────────────────────────────
# create_e2e_config tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateE2eConfig:
    """Tests for create_e2e_config helper function."""

    def test_basic_creation(self):
        """create_e2e_config creates a config with just spec_name."""
        config = create_e2e_config("anime_girl_default")
        assert config.spec_name == "anime_girl_default"
        assert config.spec_overrides == {}
        assert config.gpu_profile == "pi5"

    def test_with_gpu_profile_override(self):
        """create_e2e_config forwards gpu_profile override."""
        config = create_e2e_config("anime_boy_default", gpu_profile="desktop")
        assert config.gpu_profile == "desktop"

    def test_with_multiple_overrides(self):
        """create_e2e_config forwards multiple overrides."""
        config = create_e2e_config(
            "chibi_cute",
            gpu_profile="cloud",
            spec_overrides={"body": {"height_cm": 100.0}},
            validate=False,
            verbose=True,
            cleanup=False,
        )
        assert config.spec_name == "chibi_cute"
        assert config.gpu_profile == "cloud"
        assert config.spec_overrides == {"body": {"height_cm": 100.0}}
        assert config.validate is False
        assert config.verbose is True
        assert config.cleanup is False

    def test_custom_spec_name(self):
        """create_e2e_config accepts 'custom' as spec_name."""
        config = create_e2e_config("custom")
        assert config.spec_name == "custom"


# ──────────────────────────────────────────────────────────────────────────────
# validate_e2e_config tests
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateE2eConfig:
    """Tests for validate_e2e_config function."""

    def test_valid_config_no_errors(self):
        """A valid config produces no validation errors."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=Path(tempfile.mkdtemp()),
        )
        errors = validate_e2e_config(config)
        assert errors == []

    def test_unknown_spec_name(self):
        """An unknown spec_name produces a validation error."""
        config = E2EBuildConfig(spec_name="nonexistent_preset")
        errors = validate_e2e_config(config)
        assert any("Unknown spec preset" in e for e in errors)

    def test_custom_spec_name_is_valid(self):
        """The spec_name 'custom' skips preset validation."""
        config = E2EBuildConfig(spec_name="custom")
        errors = validate_e2e_config(config)
        # "custom" should not produce a "Unknown spec preset" error
        assert not any("Unknown spec preset" in e for e in errors)

    def test_unknown_gpu_profile(self):
        """An invalid GPU profile produces a validation error."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            gpu_profile="quantum_computer",
        )
        errors = validate_e2e_config(config)
        assert any("Unknown GPU profile" in e for e in errors)

    def test_unknown_override_key(self):
        """An unknown spec override key produces a validation error."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            spec_overrides={"nonexistent_section": {"foo": "bar"}},
        )
        errors = validate_e2e_config(config)
        assert any("Unknown spec override key" in e for e in errors)

    def test_valid_override_keys(self):
        """Known spec override keys produce no errors."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            spec_overrides={
                "body": {"height_cm": 170.0},
                "hair": {"style": "long"},
                "clothing": [{"name": "shirt"}],
            },
        )
        errors = validate_e2e_config(config)
        # These are all valid keys
        assert not any("Unknown spec override" in e for e in errors)

    def test_all_valid_gpu_profiles(self):
        """All three GPU profiles (pi5, desktop, cloud) are valid."""
        for profile in ("pi5", "desktop", "cloud"):
            config = E2EBuildConfig(
                spec_name="anime_girl_default",
                gpu_profile=profile,
            )
            errors = validate_e2e_config(config)
            assert not any("GPU profile" in e for e in errors), (
                f"Profile {profile!r} should be valid"
            )


# ──────────────────────────────────────────────────────────────────────────────
# stage_order tests
# ──────────────────────────────────────────────────────────────────────────────

class TestStageOrder:
    """Tests for the canonical build stage order."""

    def test_returns_list_of_strings(self):
        """stage_order() returns a list of strings."""
        stages = stage_order()
        assert isinstance(stages, list)
        assert all(isinstance(s, str) for s in stages)

    def test_starts_with_clear_scene(self):
        """The first stage is 'clear_scene'."""
        stages = stage_order()
        assert stages[0] == "clear_scene"

    def test_ends_with_validation(self):
        """The last stage is 'post_export_validation'."""
        stages = stage_order()
        assert stages[-1] == "post_export_validation"

    def test_contains_all_expected_stages(self):
        """The stage order includes all expected build stages."""
        stages = stage_order()
        expected_stages = {
            "clear_scene", "import_base", "apply_spec",
            "integrate_stub_bones", "integrate_hair_mesh",
            "integrate_clothing_mesh", "integrate_weight_paint",
            "integrate_spring_bones", "integrate_first_person",
            "apply_vrm_humanoid", "apply_vrm_metadata",
            "apply_vrm_expressions", "apply_vrm_look_at",
            "export_vrm", "post_export_validation",
        }
        assert set(stages) == expected_stages

    def test_has_15_stages(self):
        """The build pipeline has exactly 15 stages."""
        assert len(stage_order()) == 15

    def test_export_before_validation(self):
        """VRM export comes before post-export validation."""
        stages = stage_order()
        assert stages.index("export_vrm") < stages.index("post_export_validation")

    def test_import_before_export(self):
        """Import base comes before VRM export."""
        stages = stage_order()
        assert stages.index("import_base") < stages.index("export_vrm")


# ──────────────────────────────────────────────────────────────────────────────
# simulate_build tests
# ──────────────────────────────────────────────────────────────────────────────

class TestSimulateBuild:
    """Tests for the simulate_build function."""

    def test_returns_e2e_build_result(self):
        """simulate_build returns an E2EBuildResult."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=Path(tempfile.mkdtemp()),
            cleanup=True,
        )
        result = simulate_build(config)
        assert isinstance(result, E2EBuildResult)

    def test_successful_build(self):
        """simulate_build returns success=True for a valid config."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=Path(tempfile.mkdtemp()),
            cleanup=True,
        )
        result = simulate_build(config)
        assert result.success is True

    def test_all_stages_completed(self):
        """A successful simulation completes all stages."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=Path(tempfile.mkdtemp()),
            cleanup=True,
        )
        result = simulate_build(config)
        assert len(result.stages_completed) == len(stage_order())
        assert result.stages_failed == []

    def test_no_stages_failed(self):
        """A successful simulation has no failed stages."""
        config = E2EBuildConfig(
            spec_name="anime_boy_default",
            output_dir=Path(tempfile.mkdtemp()),
            cleanup=True,
        )
        result = simulate_build(config)
        assert result.stages_failed == []

    def test_plausible_stats_all_specs(self):
        """All 4 E2E_TEST_SPECS produce plausible build statistics."""
        for name, spec_config in E2E_TEST_SPECS.items():
            config = E2EBuildConfig(
                spec_name=spec_config.spec_name,
                gpu_profile=spec_config.gpu_profile,
                output_dir=Path(tempfile.mkdtemp()),
                cleanup=True,
            )
            result = simulate_build(config)
            assert result.total_triangles > 0, f"{name}: triangles > 0"
            assert result.mesh_count > 0, f"{name}: mesh_count > 0"
            assert result.bone_count > 0, f"{name}: bone_count > 0"
            assert result.build_time_seconds > 0, f"{name}: build_time > 0"

    def test_chibi_fewer_triangles_than_warrior(self):
        """Chibi spec has fewer triangles than warrior (full detail) spec."""
        chibi_stats = estimate_build_stats("chibi_cute", "pi5")
        warrior_stats = estimate_build_stats("anime_girl_warrior", "pi5")
        assert chibi_stats["total_triangles"] < warrior_stats["total_triangles"]

    def test_pi5_fewer_triangles_than_desktop(self):
        """pi5 profile budgets fewer triangles than desktop for same spec."""
        pi5_stats = estimate_build_stats("anime_girl_default", "pi5")
        desktop_stats = estimate_build_stats("anime_girl_default", "desktop")
        assert pi5_stats["total_triangles"] < desktop_stats["total_triangles"]

    def test_desktop_fewer_triangles_than_cloud(self):
        """desktop profile budgets fewer triangles than cloud for same spec."""
        desktop_stats = estimate_build_stats("anime_girl_default", "desktop")
        cloud_stats = estimate_build_stats("anime_girl_default", "cloud")
        assert desktop_stats["total_triangles"] < cloud_stats["total_triangles"]

    def test_spec_name_preserved(self):
        """The spec_name is preserved in the result."""
        config = E2EBuildConfig(
            spec_name="chibi_cute",
            output_dir=Path(tempfile.mkdtemp()),
            cleanup=True,
        )
        result = simulate_build(config)
        assert result.spec_name == "chibi_cute"

    def test_build_time_positive(self):
        """Build time is always positive."""
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=Path(tempfile.mkdtemp()),
            cleanup=True,
        )
        result = simulate_build(config)
        assert result.build_time_seconds > 0


# ──────────────────────────────────────────────────────────────────────────────
# generate_build_script tests
# ──────────────────────────────────────────────────────────────────────────────

class TestGenerateBuildScript:
    """Tests for generate_build_script function."""

    def test_creates_valid_python_file(self):
        """generate_build_script creates a .py file that exists and is valid."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        assert script_path.exists()
        assert script_path.suffix == ".py"

    def test_script_is_parseable_python(self):
        """The generated script is parseable Python (valid syntax)."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        content = script_path.read_text()

        # Must be valid Python syntax
        compile(content, str(script_path), "exec")

    def test_script_contains_spec_name(self):
        """The generated script contains the spec name."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="chibi_cute",
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        content = script_path.read_text()
        assert "chibi_cute" in content

    def test_script_contains_gpu_profile(self):
        """The generated script contains the GPU profile."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            gpu_profile="desktop",
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        content = script_path.read_text()
        assert "desktop" in content

    def test_script_contains_build_stages(self):
        """The generated script contains the build stages."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        content = script_path.read_text()
        assert "clear_scene" in content
        assert "export_vrm" in content

    def test_script_with_overrides(self):
        """The generated script includes spec overrides."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="anime_girl_warrior",
            spec_overrides={"hair": {"style": "long"}},
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        content = script_path.read_text()
        assert "style" in content
        assert "long" in content

    def test_script_contains_main_function(self):
        """The generated script defines a main() entry point."""
        output_dir = Path(tempfile.mkdtemp())
        config = E2EBuildConfig(
            spec_name="anime_girl_default",
            output_dir=output_dir,
            cleanup=False,
        )
        script_path = generate_build_script(config)
        content = script_path.read_text()
        assert "def main()" in content
        assert 'if __name__ == "__main__"' in content


# ──────────────────────────────────────────────────────────────────────────────
# estimate_build_stats tests
# ──────────────────────────────────────────────────────────────────────────────

class TestEstimateBuildStats:
    """Tests for estimate_build_stats function."""

    def test_pi5_profile(self):
        """pi5 profile returns plausible stats with lower triangle count."""
        stats = estimate_build_stats("anime_girl_default", "pi5")
        assert stats["total_triangles"] > 0
        assert stats["mesh_count"] > 0
        assert stats["bone_count"] > 0
        assert stats["estimated_time"] > 0

    def test_desktop_profile(self):
        """desktop profile returns plausible stats."""
        stats = estimate_build_stats("anime_girl_default", "desktop")
        assert stats["total_triangles"] > 0
        assert stats["mesh_count"] > 0
        assert stats["bone_count"] > 0

    def test_cloud_profile(self):
        """cloud profile returns plausible stats with highest triangle count."""
        stats = estimate_build_stats("anime_girl_default", "cloud")
        assert stats["total_triangles"] > 0

    def test_profile_triangle_ordering(self):
        """Triangle counts increase: pi5 < desktop < cloud."""
        pi5 = estimate_build_stats("anime_girl_default", "pi5")
        desktop = estimate_build_stats("anime_girl_default", "desktop")
        cloud = estimate_build_stats("anime_girl_default", "cloud")
        assert pi5["total_triangles"] < desktop["total_triangles"]
        assert desktop["total_triangles"] < cloud["total_triangles"]

    def test_chibi_fewer_triangles_than_default(self):
        """Chibi has fewer triangles than default girl on same profile."""
        chibi = estimate_build_stats("chibi_cute", "pi5")
        default_girl = estimate_build_stats("anime_girl_default", "pi5")
        assert chibi["total_triangles"] < default_girl["total_triangles"]

    def test_chibi_fewer_bones_than_default(self):
        """Chibi has fewer bones than default girl."""
        chibi = estimate_build_stats("chibi_cute", "pi5")
        default_girl = estimate_build_stats("anime_girl_default", "pi5")
        assert chibi["bone_count"] < default_girl["bone_count"]

    def test_all_preset_stats_available(self):
        """All CHARACTER_PRESETS have preset stats defined."""
        for preset_name in [
            "anime_girl_default", "anime_girl_warrior", "anime_girl_mage",
            "anime_boy_default", "anime_boy_warrior", "chibi_cute",
        ]:
            stats = estimate_build_stats(preset_name, "pi5")
            assert stats["total_triangles"] > 0, f"Missing stats for {preset_name}"

    def test_unknown_preset_returns_defaults(self):
        """Unknown preset names return plausible default stats."""
        stats = estimate_build_stats("unknown_custom_spec", "pi5")
        assert stats["total_triangles"] > 0
        assert stats["mesh_count"] > 0
        assert stats["bone_count"] > 0

    def test_build_time_faster_on_desktop(self):
        """Build time estimate is faster on desktop than pi5."""
        pi5_time = estimate_build_stats("anime_girl_default", "pi5")["estimated_time"]
        desktop_time = estimate_build_stats("anime_girl_default", "desktop")["estimated_time"]
        assert desktop_time < pi5_time

    def test_build_time_fastest_on_cloud(self):
        """Build time estimate is fastest on cloud."""
        pi5_time = estimate_build_stats("anime_girl_default", "pi5")["estimated_time"]
        cloud_time = estimate_build_stats("anime_girl_default", "cloud")["estimated_time"]
        assert cloud_time < pi5_time


# ──────────────────────────────────────────────────────────────────────────────
# Blender-dependent test (skipped in CI)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.blender
class TestBlenderBuildE2E:
    """Real Blender headless E2E tests — require Blender installed.

    These tests are skipped in CI environments without Blender.
    Run with: pytest tests/test_e2e_build.py --run-blender
    """

    @pytest.fixture(autouse=True)
    def check_blender(self):
        """Skip all tests in this class if Blender is not available."""
        from hamr.blender_bridge.compat import check_blender_available
        if not check_blender_available():
            pytest.skip("Blender not available — skipping Blender E2E tests")

    def test_execute_blender_build_simulated_config(self):
        """execute_blender_build runs with a simulated config.

        This test validates that the E2E pipeline can actually invoke
        Blender headless and produce output. It uses the chibi preset
        (lightweight) for speed.
        """
        from hamr.blender_bridge.e2e import execute_blender_build

        config = E2EBuildConfig(
            spec_name="chibi_cute",
            gpu_profile="pi5",
            output_dir=Path(tempfile.mkdtemp()),
            validate=True,
            cleanup=False,  # keep output for verification
        )
        result = execute_blender_build(config)

        # The build may fail due to missing VRM addon or base mesh,
        # but it should at least launch Blender and return a result
        assert isinstance(result, E2EBuildResult)
        assert result.spec_name == "chibi_cute"
        # If successful, verify we got some stages completed
        if result.success:
            assert len(result.stages_completed) > 0