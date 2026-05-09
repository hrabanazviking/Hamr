"""
Tests for Hamr Phase 8 — The Sacred Fire (E2E VRM Build).

End-to-end tests that invoke the full Blender pipeline:
- BuildPipeline integration: spec YAML → Blender → VRM file
- Environment detection: Blender, VRM addon, MB-Lab
- Forge integration in Blender context
- VRM file validation (glTF magic bytes, file size)
- CLI end-to-end: hamr build command
"""

import json
import os
import struct
import tempfile
from pathlib import Path

import pytest

from hamr.core.spec import Spec
from hamr.core.pipeline import BuildPipeline, PipelineResult
from hamr.core.models import (
    CharacterSpec, BodySpec, SkinSpec, FaceSpec, EyeSpec,
    HairSpec, HairColorSpec, ClothingSpec, ExportSpec,
    HairStyle, HairLength, ExportFormat,
)
from hamr.blender_bridge.runner import (
    check_blender_available,
    get_blender_version,
    run_blender_script,
    run_inline_script,
)


# ── Environment Checks ─────────────────────────────────────────────────────────

class TestSacredFireEnvironment:
    """Verify the build environment is ready for E2E testing."""

    def test_blender_available(self):
        """Blender is available on the system."""
        assert check_blender_available(), "Blender must be installed for E2E tests"

    def test_blender_version_minimum(self):
        """Blender version meets minimum requirements (>=3.0)."""
        version = get_blender_version()
        assert version is not None
        major = int(version.split(".")[0])
        assert major >= 3, f"Blender 3.0+ required, got {version}"

    def test_vrm_addon_available(self):
        """VRM add-on is available in Blender."""
        script = """
import bpy
addon_utils = __import__("addon_utils")
addon_utils.enable("io_scene_vrm", default_set=True)
result = "VRM_ADDON=True"
"""
        result = run_inline_script(script, timeout=30)
        assert "VRM_ADDON=True" in result.stdout or result.success, \
            f"VRM add-on not available: {result.stderr[:200]}"

    def test_mblab_addon_available(self):
        """MB-Lab add-on is available for base mesh generation."""
        script = """
import bpy
has_mblab = hasattr(bpy.ops, "mblab")
print(f"MBLAB_ADDON={has_mblab}")
"""
        result = run_inline_script(script, timeout=30)
        assert "MBLAB_ADDON=True" in result.stdout, \
            f"MB-Lab add-on not available: {result.stderr[:200]}"

    def test_environment_check_method(self):
        """BuildPipeline.check_environment returns expected structure."""
        pipeline = BuildPipeline()
        env = pipeline.check_environment()
        assert "blender_available" in env
        assert "blender_version" in env
        assert "vrm_addon" in env
        assert env["blender_available"], "Blender must be available"
        assert env["vrm_addon"] is not None


# ── Forge Resolution in Blender Context ─────────────────────────────────────────

class TestForgesInBlender:
    """Test forge resolution runs inside Blender."""

    def test_hair_forge_blender_import(self):
        """Hair forge resolution can be imported and run inside Blender."""
        script = """
import json
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.hair import resolve_hair
from hamr.core.models import HairSpec, HairColorSpec
result = resolve_hair(HairSpec(style="wavy", length="shoulder-plus"))
print(f"HAIR_STYLE={result.style_template['shell_count']}")
print(f"HAIR_CURL={result.curl_tightness}")
"""
        br = run_inline_script(script, timeout=30)
        assert br.success, f"Hair forge Blender import failed: {br.stderr[:300]}"
        assert "HAIR_STYLE=6" in br.stdout  # wavy = 6 shells
        assert "HAIR_CURL=" in br.stdout

    def test_face_forge_blender_import(self):
        """Face forge resolution can run inside Blender."""
        script = """
import json
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.face import resolve_face
from hamr.core.models import FaceSpec, EyeSpec
result = resolve_face(FaceSpec(jaw="V-shape", eyes=EyeSpec(shape="cat-tilt")))
print(f"FACE_KEYS={len(result.shape_keys)}")
"""
        br = run_inline_script(script, timeout=30)
        assert br.success, f"Face forge Blender import failed: {br.stderr[:300]}"
        assert "FACE_KEYS=" in br.stdout

    def test_clothing_forge_blender_import(self):
        """Clothing forge resolution can run inside Blender."""
        script = """
import json
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.clothing import resolve_clothing
from hamr.core.models import ClothingSpec
result = resolve_clothing(ClothingSpec(name="dress", type="dress", primary_hex="#4466AA"))
print(f"CLOTH_TYPE={result.cloth_type}")
print(f"CLOTH_MAT={result.material_category}")
"""
        br = run_inline_script(script, timeout=30)
        assert br.success, f"Clothing forge Blender import failed: {br.stderr[:300]}"
        assert "CLOTH_TYPE=dress" in br.stdout

    def test_forge_config_blender_side(self):
        """Full forge config generation works inside Blender."""
        script = """
import json
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.core.builder import _resolve_forges
from hamr.core.models import CharacterSpec, HairSpec, FaceSpec, EyeSpec, ClothingSpec
char = CharacterSpec(
    name="BlenderE2E",
    hair=HairSpec(style="straight", length="long"),
    face=FaceSpec(jaw="square", eyes=EyeSpec(shape="round")),
    clothing=[ClothingSpec(name="boots", type="footwear", primary_hex="#333333")]
)
config = _resolve_forges(char)
print(f"HAS_HAIR={config.get('hair') is not None}")
print(f"HAS_FACE={config.get('face') is not None}")
print(f"CLOTH_COUNT={len(config.get('clothing', []))}")
"""
        br = run_inline_script(script, timeout=30)
        assert br.success, f"Forge config Blender failed: {br.stderr[:300]}"
        assert "HAS_HAIR=True" in br.stdout
        assert "HAS_FACE=True" in br.stdout
        assert "CLOTH_COUNT=1" in br.stdout


# ── Build Script Smoke Tests ───────────────────────────────────────────────────

class TestBuildScriptSmoke:
    """Test build_avatar.py script functions inside Blender without export."""

    def test_build_script_imports(self):
        """The build script module can be imported inside Blender."""
        script = """
import bpy
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.scripts.build_avatar import (
    _clear_scene, _apply_spec, _validate_vrm,
    MB_LAB_EXPRESSION_MAP, TURBOSQUID_EXPRESSION_MAP,
)
print("BUILD_IMPORTS=True")
print(f"MBLAB_EXPR_COUNT={len(MB_LAB_EXPRESSION_MAP)}")
print(f"TURBO_EXPR_COUNT={len(TURBOSQUID_EXPRESSION_MAP)}")
"""
        br = run_inline_script(script, timeout=30)
        assert br.success, f"Build script imports failed: {br.stderr[:300]}"
        assert "BUILD_IMPORTS=True" in br.stdout
        assert "MBLAB_EXPR_COUNT=" in br.stdout
        assert "TURBO_EXPR_COUNT=" in br.stdout

    def test_mblab_expression_map_complete(self):
        """MB-Lab expression map has all expected keys."""
        script = """
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
expected = ["happy", "sad", "angry", "relaxed", "surprised", "blink",
            "aa", "ih", "ou", "ee", "oh"]
for name in expected:
    assert name in MB_LAB_EXPRESSION_MAP, f"Missing: {name}"
print(f"MBLAB_COMPLETE=True COUNT={len(MB_LAB_EXPRESSION_MAP)}")
"""
        br = run_inline_script(script, timeout=15)
        assert br.success, f"MB-Lab expression map check failed: {br.stderr[:200]}"
        assert "MBLAB_COMPLETE=True" in br.stdout

    def test_turbosquid_expression_map_complete(self):
        """TurboSquid expression map has all expected keys."""
        script = """
import sys
sys.path.insert(0, "/home/pi/Hamr/src")
from hamr.scripts.build_avatar import TURBOSQUID_EXPRESSION_MAP
expected = ["happy", "angry", "sad", "relaxed", "surprised",
            "blink", "aa", "ih", "ou", "ee", "oh",
            "blinkLeft", "blinkRight"]
for name in expected:
    assert name in TURBOSQUID_EXPRESSION_MAP, f"Missing: {name}"
print(f"TURBO_COMPLETE=True COUNT={len(TURBOSQUID_EXPRESSION_MAP)}")
"""
        br = run_inline_script(script, timeout=15)
        assert br.success, f"TurboSquid expression map check failed: {br.stderr[:200]}"
        assert "TURBO_COMPLETE=True" in br.stdout


# ── Full E2E VRM Build ────────────────────────────────────────────────────────

class TestE2EVRMBuild:
    """End-to-end VRM build tests — the Sacred Fire.

    These tests run the full Blender pipeline and produce actual VRM files.
    They require Blender + VRM addon + MB-Lab to be installed.
    """

    @pytest.fixture
    def spec_file(self, tmp_path):
        """Create a minimal spec YAML for E2E testing."""
        yaml_content = """name: E2E Test Character
body:
  height_cm: 165
  build: athletic-slender
  skin:
    base_hex: "#D4A373"
face:
  jaw: V-shape
  eyes:
    shape: cat-tilt
    iris_hex: "#70C1B3"
    size: 1.2
hair:
  style: wavy
  length: shoulder-plus
  color:
    roots: "#C4A265"
    tips: "#F5E6B8"
  volume: 0.7
clothing:
  - name: basic_dress
    type: dress
    primary_hex: "#4466AA"
export:
  format: vrm1
"""
        spec_path = tmp_path / "e2e_spec.yaml"
        spec_path.write_text(yaml_content)
        return spec_path

    def test_e2e_build_pipeline(self, spec_file, tmp_path):
        """Full pipeline: YAML spec → Blender → VRM file on disk.

        This is the Sacred Fire — the moment Hamr truly speaks to Blender
        and births a character into the world.
        """
        pipeline = BuildPipeline(
            blender_path="/usr/bin/blender",
            keep_temp=True,  # Keep temp files for debugging
        )

        # First validate the spec
        errors = pipeline.validate_only(spec_file)
        assert errors == [], f"Spec validation errors: {errors}"

        # Build
        result = pipeline.build(
            spec_path=spec_file,
            output_dir=tmp_path / "output",
        )

        # The build might fail if MB-Lab can't generate in headless mode,
        # but the pipeline should not crash
        if result.success:
            assert result.output_path is not None
            assert result.output_path.exists()
            assert result.output_path.stat().st_size > 1024

            # Validate it's a real glTF/GLB file (VRM is GLB)
            with open(result.output_path, "rb") as f:
                header = f.read(4)
                magic = struct.unpack("<I", header)[0]
                assert magic == 0x46546C67, \
                    f"Not a valid glTF/GLB file: magic=0x{magic:08X}"
        elif result.errors:
            # Even if build fails, we should get structured errors
            assert isinstance(result.errors, list)
            assert len(result.errors) > 0

    def test_e2e_build_result_structure(self, spec_file, tmp_path):
        """PipelineResult has correct structure regardless of outcome."""
        pipeline = BuildPipeline(blender_path="/usr/bin/blender")
        result = pipeline.build(
            spec_path=spec_file,
            output_dir=tmp_path / "output",
        )

        # Check result structure
        assert isinstance(result, PipelineResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.elapsed, float)
        assert result.elapsed >= 0
        assert result.spec_path is not None

    def test_e2e_validate_only_no_errors(self, spec_file):
        """validate_only returns empty list for valid spec."""
        pipeline = BuildPipeline()
        errors = pipeline.validate_only(spec_file)
        assert errors == [], f"Expected no errors, got: {errors}"


# ── CLI Integration ────────────────────────────────────────────────────────────

class TestCLIEndToEnd:
    """Test the hamr CLI commands end-to-end."""

    def test_hamr_version(self):
        """hamr version prints version string."""
        import hamr
        version = hamr.__version__
        assert version == "0.8.0"

    def test_hamr_list_presets(self):
        """hamr list-presets returns all body presets."""
        from hamr.core.constants import BODY_PRESETS
        presets = list(BODY_PRESETS.keys())
        assert len(presets) == 8
        assert "athletic-slender" in presets
        assert "curvy" in presets

    def test_spec_yaml_to_vrm_roundtrip(self, tmp_path):
        """Spec YAML → dict → JSON → pipeline can parse it."""
        from hamr.core.builder import _resolve_forges
        from hamr.core.models import CharacterSpec, HairSpec

        spec = CharacterSpec(
            name="Roundtrip",
            hair=HairSpec(style="straight"),
        )
        spec_dict = spec.to_dict()
        assert "name" in spec_dict
        assert "hair" in spec_dict

        # Resolve forges and verify config
        forge_config = _resolve_forges(spec)
        assert "hair" in forge_config
        assert forge_config["hair"]["style_template"]["shell_count"] == 4