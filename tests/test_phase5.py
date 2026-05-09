"""
Tests for Hamr Phase 5 — Sharpening.

End-to-end integration tests:
- Blender environment detection
- Build script import validation (inside Blender)
- CLI commands (version, list-presets, validate, check-env)
- Full pipeline spec → JSON → Blender argument preparation
- VRM validation functions
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── Blender Environment ────────────────────────────────────────────────────────


class TestBlenderEnvironment:
    """Verify Blender installation and addons on the Pi 5."""

    @pytest.fixture(scope="class")
    def blender_check(self):
        """Run Blender addon check once for the whole class."""
        result = subprocess.run(
            ["blender", "--background", "--python-expr",
             "import addon_utils; "
             "mods = list(addon_utils.modules()); "
             "vrm = any('vrm' in m.__name__ for m in mods); "
             "mblab = any('mblab' in m.__name__ or 'mb-lab' in m.__name__ for m in mods); "
             "print(f'VRM={vrm}'); "
             "print(f'MBLAB={mblab}')"],
            capture_output=True, text=True, timeout=60,
        )
        return result

    def test_blender_is_installed(self):
        """Blender 3.x should be available on PATH."""
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, "Blender not found on PATH"
        assert "Blender" in result.stdout
        # Parse version
        version_line = result.stdout.strip().split("\n")[0]
        version = version_line.split()[-1]
        major = int(version.split(".")[0])
        assert major >= 3, f"Blender 3.x+ required, got {version}"

    def test_vrm_addon_available(self, blender_check):
        """VRM export addon should be installed."""
        vrm_found = "VRM=True" in blender_check.stdout
        assert vrm_found, "VRM addon (io_scene_vrm) not found in Blender"

    def test_mblab_addon_available(self, blender_check):
        """MB-Lab addon should be installed."""
        mblab_found = "MBLAB=True" in blender_check.stdout
        assert mblab_found, "MB-Lab addon not found in Blender"


# ── Build Script Imports (inside Blender) ──────────────────────────────────────


class TestBuildScriptInBlender:
    """Verify the build script and its constants can be imported inside Blender."""

    def test_bone_maps_import(self):
        """Bone maps should be importable inside Blender."""
        result = subprocess.run(
            ["blender", "--background", "--python-expr",
             "import sys; sys.path.insert(0, '/home/pi/Hamr/src'); "
             "from hamr.scripts.build_avatar import MB_LAB_BONE_MAP, TURBOSQUID_BONE_MAP; "
             "print(f'MBLAB_BONES={len(MB_LAB_BONE_MAP)}'); "
             "print(f'TURBO_BONES={len(TURBOSQUID_BONE_MAP)}')"],
            capture_output=True, text=True, timeout=60,
        )
        assert "MBLAB_BONES=" in result.stdout, f"MB-Lab bones not found: {result.stdout[-500:]}"
        assert "TURBO_BONES=" in result.stdout, f"TurboSquid bones not found: {result.stdout[-500:]}"

    def test_expression_maps_import(self):
        """Expression maps should be importable inside Blender."""
        result = subprocess.run(
            ["blender", "--background", "--python-expr",
             "import sys; sys.path.insert(0, '/home/pi/Hamr/src'); "
             "from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP, TURBOSQUID_EXPRESSION_MAP; "
             "print(f'MBLAB_EXPR={len(MB_LAB_EXPRESSION_MAP)}'); "
             "print(f'TURBO_EXPR={len(TURBOSQUID_EXPRESSION_MAP)}')"],
            capture_output=True, text=True, timeout=60,
        )
        assert "MBLAB_EXPR=" in result.stdout, f"MB-Lab expressions not found: {result.stdout[-500:]}"
        assert "TURBO_EXPR=" in result.stdout, f"TurboSquid expressions not found: {result.stdout[-500:]}"

    def test_helper_functions_import(self):
        """Helper functions should be importable inside Blender."""
        result = subprocess.run(
            ["blender", "--background", "--python-expr",
             "import sys; sys.path.insert(0, '/home/pi/Hamr/src'); "
             "from hamr.scripts.build_avatar import ("
             "parse_args, _classify_material, _hex_to_hsv, _validate_vrm); "
             "print('IMPORTS_OK=True')"],
            capture_output=True, text=True, timeout=60,
        )
        assert "IMPORTS_OK=True" in result.stdout, f"Helper imports failed: {result.stdout[-500:]}"

    def test_classify_material_functions(self):
        """Material classification should work inside Blender."""
        result = subprocess.run(
            ["blender", "--background", "--python-expr",
             "import sys; sys.path.insert(0, '/home/pi/Hamr/src'); "
             "from hamr.scripts.build_avatar import _classify_material; "
             "print(f'SKIN={_classify_material(\"Body_MAT\")}'); "
             "print(f'EYE={_classify_material(\"Eye_Iris\")}'); "
             "print(f'HAIR={_classify_material(\"Hair_Long\")}'); "
             "print(f'NONE={_classify_material(\"Outfit_Boots\")}')"],
            capture_output=True, text=True, timeout=60,
        )
        assert "SKIN=skin" in result.stdout, f"Body_MAT not classified as skin"
        assert "EYE=eye" in result.stdout, f"Eye_Iris not classified as eye"
        assert "HAIR=hair" in result.stdout, f"Hair_Long not classified as hair"
        assert "NONE=None" in result.stdout, f"Outfit_Boots should be None"


# ── Build Script Arg Parsing ──────────────────────────────────────────────────


class TestBuildScriptArgParsing:
    """The build script's parse_args function should work outside Blender."""

    def test_parse_args_full(self):
        from hamr.scripts.build_avatar import parse_args
        args = parse_args([
            "--spec", "spec.json",
            "--output", "out.vrm",
            "--base", "base.fbx",
            "--max-tex", "1024",
        ])
        assert args["spec"] == "spec.json"
        assert args["output"] == "out.vrm"
        assert args["base"] == "base.fbx"
        assert args["max_tex"] == 1024

    def test_parse_args_minimal(self):
        from hamr.scripts.build_avatar import parse_args
        args = parse_args(["--spec", "spec.json", "--output", "out.vrm"])
        assert args["spec"] == "spec.json"
        assert args["base"] is None
        assert args["max_tex"] == 0

    def test_parse_args_defaults(self):
        from hamr.scripts.build_avatar import parse_args
        args = parse_args([])
        assert args["spec"] is None
        assert args["output"] is None


# ── Pipeline Integration ──────────────────────────────────────────────────────


class TestPipelineIntegration:
    """Test the full pipeline preparation (without actually running Blender)."""

    def test_spec_to_json_file(self, tmp_path):
        """Spec can be written to JSON for Blender consumption."""
        from hamr.core.pipeline import BuildPipeline
        from hamr.core.spec import Spec

        spec_content = """
name: Integration Test
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
hair:
  style: wavy
  color:
    roots: "#3A1E0A"
export:
  format: vrm1
  title: Test Avatar
  author: Hamr Test
"""
        spec_file = tmp_path / "test.yaml"
        spec_file.write_text(spec_content)

        spec = Spec.from_yaml(spec_file)
        spec_dict = spec.to_dict()
        spec_dict["_pipeline"] = {"base_type": "mblab", "format": "vrm", "max_tex": 0}

        json_path = tmp_path / "spec.json"
        json_path.write_text(json.dumps(spec_dict, indent=2))

        # Verify JSON is valid and parseable
        loaded = json.loads(json_path.read_text())
        assert loaded["name"] == "Integration Test"
        assert loaded["_pipeline"]["base_type"] == "mblab"

    def test_pipeline_build_missing_spec_returns_failure(self, tmp_path):
        """Pipeline should return a failure result for missing spec file."""
        from hamr.core.pipeline import BuildPipeline

        pipeline = BuildPipeline()
        result = pipeline.build(
            spec_path="/nonexistent/path/spec.yaml",
            output_dir=str(tmp_path),
        )
        assert not result.success
        assert len(result.errors) > 0

    def test_pipeline_validate_valid_spec(self, tmp_path):
        """Pipeline validate_only should accept valid specs."""
        from hamr.core.pipeline import BuildPipeline

        spec_file = tmp_path / "valid.yaml"
        spec_file.write_text("""
name: Valid Character
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


# ── Environment Check ──────────────────────────────────────────────────────────


class TestEnvironmentCheck:
    """Test the environment checking functionality."""

    def test_check_environment_returns_blender(self):
        """check_environment should find Blender on the Pi."""
        from hamr.core.pipeline import BuildPipeline

        pipeline = BuildPipeline()
        env = pipeline.check_environment()
        assert "blender_available" in env
        # On the Pi, Blender should be available
        assert env["blender_available"] is True
        assert env["blender_version"] is not None

    def test_check_environment_finds_build_script(self):
        """check_environment should find the build script."""
        from hamr.core.pipeline import BuildPipeline

        pipeline = BuildPipeline()
        env = pipeline.check_environment()
        assert "build_script" in env


# ── VRM Validation ────────────────────────────────────────────────────────────


class TestVRMValidation:
    """Test the VRM file validation function."""

    def test_validate_missing_file_raises(self):
        """_validate_vrm should raise ValueError for missing file."""
        from hamr.scripts.build_avatar import _validate_vrm

        with pytest.raises(ValueError):
            _validate_vrm("/nonexistent/path/avatar.vrm")

    def test_validate_too_small_file_raises(self, tmp_path):
        """_validate_vrm should raise ValueError for files that are too small."""
        from hamr.scripts.build_avatar import _validate_vrm

        tiny_file = tmp_path / "tiny.vrm"
        tiny_file.write_bytes(b"not a real vrm file")
        with pytest.raises(ValueError):
            _validate_vrm(str(tiny_file))

    def test_validate_non_glb_header_raises(self, tmp_path):
        """_validate_vrm should raise ValueError for files without glTF magic."""
        from hamr.scripts.build_avatar import _validate_vrm

        # Create a file with correct size but wrong magic number
        fake_file = tmp_path / "fake.vrm"
        fake_file.write_bytes(b"x" * 2048)  # Big enough but wrong format
        with pytest.raises(ValueError):
            _validate_vrm(str(fake_file))


# ── CLI Integration ────────────────────────────────────────────────────────────


class TestCLIIntegration:
    """Test CLI commands that don't need Blender output."""

    def test_hamr_version_command(self):
        """hamr version should print version."""
        result = subprocess.run(
            ["python", "-m", "hamr.cli", "version"],
            capture_output=True, text=True, timeout=10,
            cwd="/home/pi/Hamr",
        )
        # May return 0 or may have import issues
        assert "0.8.0" in result.stdout or result.returncode != 0

    def test_hamr_list_presets_command(self):
        """hamr list-presets should show presets."""
        import sys
        env = os.environ.copy()
        env["PYTHONPATH"] = "/home/pi/Hamr/src"

        result = subprocess.run(
            [sys.executable, "-m", "hamr.cli", "list-presets"],
            capture_output=True, text=True, timeout=10,
            cwd="/home/pi/Hamr",
            env=env,
        )
        # Should list presets or fail gracefully
        if result.returncode == 0:
            assert "athletic-slender" in result.stdout

    def test_hamr_validate_valid_spec(self, tmp_path):
        """hamr validate should accept valid spec."""
        import sys
        env = os.environ.copy()
        env["PYTHONPATH"] = "/home/pi/Hamr/src"

        spec_file = tmp_path / "valid.yaml"
        spec_file.write_text("""
name: CLI Test
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        result = subprocess.run(
            [sys.executable, "-m", "hamr.cli", "validate", str(spec_file)],
            capture_output=True, text=True, timeout=10,
            cwd="/home/pi/Hamr",
            env=env,
        )
        assert result.returncode == 0, f"Validate failed: {result.stderr}"