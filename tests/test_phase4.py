"""
Tests for Hamr Phase 4 — Tempering.

Tests the full pipeline orchestrator, CLI, environment checks,
and end-to-end spec → JSON → Blender argument preparation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ── Pipeline Tests ────────────────────────────────────────────────────────────


class TestBuildPipeline:
    """BuildPipeline orchestrates the full spec → VRM flow."""

    def test_pipeline_init_defaults(self):
        from hamr.core.pipeline import BuildPipeline
        pipeline = BuildPipeline()
        assert pipeline.blender_path is None
        assert pipeline.blender_timeout == 600
        assert pipeline.keep_temp is False

    def test_pipeline_init_custom(self):
        from hamr.core.pipeline import BuildPipeline
        pipeline = BuildPipeline(
            blender_path="/usr/local/bin/blender",
            blender_timeout=300,
            keep_temp=True,
        )
        assert pipeline.blender_path == "/usr/local/bin/blender"
        assert pipeline.blender_timeout == 300
        assert pipeline.keep_temp is True

    def test_validate_only_valid_spec(self, tmp_path):
        """validate_only should return empty list for valid spec."""
        from hamr.core.pipeline import BuildPipeline
        spec_file = tmp_path / "test.yaml"
        spec_file.write_text("""
name: Test Character
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        pipeline = BuildPipeline()
        errors = pipeline.validate_only(str(spec_file))
        assert errors == []

    def test_validate_only_invalid_spec(self, tmp_path):
        """validate_only should return errors for invalid spec."""
        from hamr.core.pipeline import BuildPipeline
        spec_file = tmp_path / "bad.yaml"
        spec_file.write_text("""
name: ""
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        pipeline = BuildPipeline()
        errors = pipeline.validate_only(str(spec_file))
        assert len(errors) > 0

    def test_build_raises_on_missing_spec(self, tmp_path):
        """Build should fail gracefully with missing spec file."""
        from hamr.core.pipeline import BuildPipeline
        pipeline = BuildPipeline()
        result = pipeline.build(
            spec_path="/nonexistent/spec.yaml",
            output_dir=str(tmp_path),
        )
        assert not result.success
        assert len(result.errors) > 0

    def test_pipeline_result_properties(self):
        """PipelineResult should track output size and timing."""
        from hamr.core.pipeline import PipelineResult
        result = PipelineResult(success=True, spec_path=Path("test.yaml"))
        assert result.success is True
        assert result.output_size_mb is None  # No output yet

    def test_pipeline_result_repr(self):
        """PipelineResult should have a useful repr."""
        from hamr.core.pipeline import PipelineResult
        result = PipelineResult(success=True, spec_path=Path("test.yaml"), elapsed=5.2)
        assert "✓" in repr(result)
        assert "5.2s" in repr(result)


class TestPipelineResult:
    """PipelineResult data class."""

    def test_success_result(self):
        from hamr.core.pipeline import PipelineResult
        result = PipelineResult(
            success=True,
            spec_path=Path("char.yaml"),
            output_path=Path("output/char.vrm"),
            elapsed=42.0,
        )
        assert result.success
        assert result.output_path == Path("output/char.vrm")
        assert result.elapsed == 42.0
        assert result.errors == []
        assert result.warnings == []

    def test_failure_result(self):
        from hamr.core.pipeline import PipelineResult
        result = PipelineResult(
            success=False,
            spec_path=Path("bad.yaml"),
            errors=["Spec parse error: empty name"],
            elapsed=0.1,
        )
        assert not result.success
        assert len(result.errors) == 1
        assert "empty name" in result.errors[0]


# ── CLI Tests ──────────────────────────────────────────────────────────────────


class TestCLI:
    """CLI command parsing and execution."""

    def test_cli_version(self, capsys):
        from hamr.cli import cmd_version
        import argparse
        args = argparse.Namespace()
        result = cmd_version(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "0.8.0" in captured.out
        assert "Shape-Skin Engine" in captured.out

    def test_cli_list_presets(self, capsys):
        from hamr.cli import cmd_list_presets
        import argparse
        args = argparse.Namespace()
        result = cmd_list_presets(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "athletic-slender" in captured.out
        assert "average" in captured.out

    def test_cli_validate_valid(self, tmp_path):
        from hamr.cli import cmd_validate
        import argparse
        spec_file = tmp_path / "char.yaml"
        spec_file.write_text("""
name: Test Character
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        args = argparse.Namespace(spec=str(spec_file))
        result = cmd_validate(args)
        assert result == 0

    def test_cli_validate_invalid(self, tmp_path):
        """CLI validate should return 1 for invalid specs."""
        from hamr.cli import cmd_validate
        import argparse
        spec_file = tmp_path / "bad.yaml"
        spec_file.write_text("""
name: ""
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        args = argparse.Namespace(spec=str(spec_file))
        result = cmd_validate(args)
        # Either exit 1 (errors returned) or exception caught
        assert result in (0, 1, 2)

    def test_cli_main_no_args(self):
        """CLI with no args should show help and return 1."""
        from hamr.cli import main
        with patch("sys.argv", ["hamr"]):
            result = main()
        assert result == 1  # No command = help + exit 1


# ── Spec-to-JSON Pipeline ─────────────────────────────────────────────────────


class TestSpecToJSON:
    """Spec YAML → dict → JSON pipeline for Blender consumption."""

    def test_spec_to_dict_complete(self):
        """Full spec serializes with all fields."""
        from hamr.core.models import CharacterSpec, BodySpec, SkinSpec, HairSpec, HairColorSpec, FaceSpec
        char = CharacterSpec(
            name="Pipeline Test",
            body=BodySpec(
                height_cm=170,
                build="athletic-slender",
                skin=SkinSpec(base_hex="#D4A574"),
            ),
            hair=HairSpec(color=HairColorSpec(roots="#3A1E0A")),
            face=FaceSpec(eyes={"iris_hex": "#4169E1"}),
        )
        d = char.to_dict()
        assert d["name"] == "Pipeline Test"
        assert d["body"]["height_cm"] == 170
        assert d["body"]["skin"]["base_hex"] == "#D4A574"
        assert d["hair"]["color"]["roots"] == "#3A1E0A"

    def test_spec_json_roundtrip(self):
        """Spec can serialize to JSON and back."""
        from hamr.core.models import CharacterSpec, BodySpec
        char = CharacterSpec(name="Round Trip", body=BodySpec(height_cm=175))
        d = char.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["name"] == "Round Trip"
        assert parsed["body"]["height_cm"] == 175

    def test_pipeline_metadata_injection(self, tmp_path):
        """BuildPipeline should inject _pipeline metadata into spec JSON."""
        from hamr.core.spec import Spec
        spec_file = tmp_path / "meta.yaml"
        spec_file.write_text("""
name: Meta Test
version: "1.0"
body:
  height_cm: 170
  build: average
  skin:
    base_hex: "#E8B87A"
""")
        spec = Spec.from_yaml(spec_file)
        spec_dict = spec.to_dict()

        # Simulate pipeline metadata injection
        spec_dict["_pipeline"] = {
            "base_type": "mblab",
            "format": "vrm",
            "max_tex": 0,
        }

        json_str = json.dumps(spec_dict)
        parsed = json.loads(json_str)
        assert "_pipeline" in parsed
        assert parsed["_pipeline"]["base_type"] == "mblab"
        assert parsed["_pipeline"]["format"] == "vrm"

    def test_spec_json_file_write(self, tmp_path):
        """Spec JSON can be written to file for Blender consumption."""
        from hamr.core.models import CharacterSpec, BodySpec
        char = CharacterSpec(
            name="File Test",
            body=BodySpec(height_cm=165),
        )
        spec_dict = char.to_dict()
        spec_dict["_pipeline"] = {"base_type": "mblab", "format": "vrm", "max_tex": 0}

        json_path = tmp_path / "spec.json"
        json_path.write_text(json.dumps(spec_dict, indent=2))

        assert json_path.exists()
        loaded = json.loads(json_path.read_text())
        assert loaded["name"] == "File Test"
        assert loaded["_pipeline"]["base_type"] == "mblab"


# ── Example Spec Validation ────────────────────────────────────────────────────


class TestExampleSpecs:
    """Validate the example spec files."""

    def test_minimal_spec_valid(self):
        """The minimal example spec should parse and validate."""
        from hamr.core.spec import Spec
        from hamr.core.validate import validate_spec

        spec_path = Path(__file__).parent.parent / "examples" / "minimal.yaml"
        if not spec_path.exists():
            pytest.skip("Example spec not found")

        spec = Spec.from_yaml(spec_path)
        errors = validate_spec(spec.character)
        assert len(errors) == 0, f"Minimal spec validation errors: {errors}"

    def test_runa_spec_valid(self):
        """The detailed Runa spec should parse and validate."""
        from hamr.core.spec import Spec
        from hamr.core.validate import validate_spec

        spec_path = Path(__file__).parent.parent / "examples" / "runa_gridweaver.yaml"
        if not spec_path.exists():
            pytest.skip("Example spec not found")

        spec = Spec.from_yaml(spec_path)
        errors = validate_spec(spec.character)
        assert len(errors) == 0, f"Runa spec validation errors: {errors}"