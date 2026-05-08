"""
Tests for Hamr Phase 3 — The Quench.

Tests the Blender-side build script, VRM bone maps, expression maps,
spec-to-JSON serialization, and the full builder pipeline.
"""

import json
import tempfile
from pathlib import Path

import pytest

# ── Bone Map Tests ────────────────────────────────────────────────────────────


class TestBoneMaps:
    """VRM 1.0 humanoid bone mapping correctness."""

    def test_mblab_bone_map_complete(self):
        """MB-Lab bone map covers all required VRM bones."""
        from hamr.scripts.build_avatar import MB_LAB_BONE_MAP
        required = [
            "hips", "spine", "chest", "neck", "head",
            "leftUpperLeg", "leftLowerLeg", "leftFoot",
            "rightUpperLeg", "rightLowerLeg", "rightFoot",
            "leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand",
            "rightShoulder", "rightUpperArm", "rightLowerArm", "rightHand",
        ]
        for bone in required:
            assert bone in MB_LAB_BONE_MAP, f"Required VRM bone '{bone}' missing from MB-Lab map"

    def test_turbosquid_bone_map_complete(self):
        """TurboSquid bone map covers all required VRM bones."""
        from hamr.scripts.build_avatar import TURBOSQUID_BONE_MAP
        required = [
            "hips", "spine", "chest", "neck", "head",
            "leftUpperLeg", "leftLowerLeg", "leftFoot",
            "rightUpperLeg", "rightLowerLeg", "rightFoot",
            "leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand",
            "rightShoulder", "rightUpperArm", "rightLowerArm", "rightHand",
        ]
        for bone in required:
            assert bone in TURBOSQUID_BONE_MAP, f"Required VRM bone '{bone}' missing from TurboSquid map"

    def test_mblab_values_nonempty(self):
        """MB-Lab bone map values are non-empty strings."""
        from hamr.scripts.build_avatar import MB_LAB_BONE_MAP
        for vrm_name, blender_name in MB_LAB_BONE_MAP.items():
            assert isinstance(blender_name, str) and len(blender_name) > 0, \
                f"Bone '{vrm_name}' has empty Blender name"

    def test_turbosquid_values_nonempty(self):
        """TurboSquid bone map values are non-empty strings."""
        from hamr.scripts.build_avatar import TURBOSQUID_BONE_MAP
        for vrm_name, blender_name in TURBOSQUID_BONE_MAP.items():
            assert isinstance(blender_name, str) and len(blender_name) > 0, \
                f"Bone '{vrm_name}' has empty Blender name"


# ── Expression Map Tests ─────────────────────────────────────────────────────


class TestExpressionMaps:
    """VRM 1.0 expression preset mapping."""

    def test_mblab_expressions_exist(self):
        """MB-Lab expression map has required presets."""
        from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
        required_presets = ["happy", "angry", "sad", "blink", "aa", "oh"]
        for preset in required_presets:
            assert preset in MB_LAB_EXPRESSION_MAP, f"Missing expression preset: {preset}"

    def test_expression_bindings_have_required_fields(self):
        """Each expression binding has shape_key and weight."""
        from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
        for preset_name, bindings in MB_LAB_EXPRESSION_MAP.items():
            assert isinstance(bindings, list), f"{preset_name} bindings should be a list"
            for binding in bindings:
                assert "shape_key" in binding, f"Missing shape_key in {preset_name}"
                assert "weight" in binding, f"Missing weight in {preset_name}"
                assert 0.0 <= binding["weight"] <= 1.0, f"Weight out of range in {preset_name}"

    def test_symmetric_expressions_bind_both_sides(self):
        """D-011: Symmetric expressions bind BOTH L and R shape keys."""
        from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
        for preset_name, bindings in MB_LAB_EXPRESSION_MAP.items():
            if preset_name in ("blinkLeft", "blinkRight", "lookLeft", "lookRight"):
                continue  # Asymmetric by design
            shape_keys = [b["shape_key"] for b in bindings]
            has_L = any("_L" in k for k in shape_keys)
            has_R = any("_R" in k for k in shape_keys)
            if has_L and not has_R:
                pytest.fail(f"D-011 violation: {preset_name} has L but no R shape keys")
            if has_R and not has_L:
                pytest.fail(f"D-011 violation: {preset_name} has R but no L shape keys")


# ── Material Classification ──────────────────────────────────────────────────


class TestMaterialClassification:
    """Material name → category classification."""

    def test_skin_classification(self):
        from hamr.scripts.build_avatar import _classify_material
        for name in ("Body_MAT", "Skin_Base", "Head_Skin", "arm_material", "Leg тек"):
            assert _classify_material(name) == "skin", f"Failed to classify '{name}' as skin"

    def test_eye_classification(self):
        from hamr.scripts.build_avatar import _classify_material
        for name in ("Eye_MAT", "Iris_Color", "Cornea"):
            assert _classify_material(name) == "eye", f"Failed to classify '{name}' as eye"

    def test_hair_classification(self):
        from hamr.scripts.build_avatar import _classify_material
        for name in ("Hair_MAT", "Scalp_Base"):
            assert _classify_material(name) == "hair", f"Failed to classify '{name}' as hair"

    def test_unknown_classification(self):
        from hamr.scripts.build_avatar import _classify_material
        assert _classify_material("Outfit_Boots") is None
        assert _classify_material("Background") is None


# ── Color Conversion ──────────────────────────────────────────────────────────


class TestColorConversion:
    """Hex → HSV color conversion for Blender-side color application."""

    def test_hex_to_hsv_red(self):
        from hamr.scripts.build_avatar import _hex_to_hsv
        h, s, v = _hex_to_hsv("#FF0000")
        assert abs(h - 0.0) < 0.01
        assert abs(s - 1.0) < 0.01
        assert abs(v - 1.0) < 0.01

    def test_hex_to_hsv_skin_tone(self):
        from hamr.scripts.build_avatar import _hex_to_hsv
        h, s, v = _hex_to_hsv("#E8B87A")
        # Golden skin should have warm hue (0.05-0.15), medium saturation
        assert 0.05 < h < 0.15, f"Skin hue {h} should be warm (orange range)"
        assert 0.3 < s < 0.8, f"Skin saturation {s} should be moderate"

    def test_hex_to_hsv_blue_eyes(self):
        from hamr.scripts.build_avatar import _hex_to_hsv
        h, s, v = _hex_to_hsv("#4169E1")
        # Royal blue should be around hue 0.62
        assert 0.58 < h < 0.68, f"Blue hue {h} should be in blue range"


# ── Argument Parsing ──────────────────────────────────────────────────────────


class TestArgParsing:
    """Build script argument parsing."""

    def test_parse_args_full(self):
        from hamr.scripts.build_avatar import parse_args
        args = parse_args(["--spec", "spec.json", "--base", "base.fbx", "--output", "out.vrm", "--max-tex", "1024"])
        assert args["spec"] == "spec.json"
        assert args["base"] == "base.fbx"
        assert args["output"] == "out.vrm"
        assert args["max_tex"] == 1024

    def test_parse_args_minimal(self):
        from hamr.scripts.build_avatar import parse_args
        args = parse_args(["--spec", "spec.json", "--output", "out.vrm"])
        assert args["spec"] == "spec.json"
        assert args["base"] is None
        assert args["output"] == "out.vrm"
        assert args["max_tex"] == 0

    def test_parse_args_empty(self):
        from hamr.scripts.build_avatar import parse_args
        args = parse_args([])
        assert args["spec"] is None
        assert args["base"] is None
        assert args["output"] is None


# ── Spec Serialization ─────────────────────────────────────────────────────────


class TestSpecSerialization:
    """CharacterSpec → JSON → Blender build script pipeline."""

    def test_spec_to_json_roundtrip(self):
        """Spec can be serialized to JSON and parsed by build script."""
        from hamr.core.models import CharacterSpec, BodySpec, SkinSpec, HairSpec, HairColorSpec, FaceSpec, ExportSpec

        spec = CharacterSpec(
            name="Test Avatar",
            body=BodySpec(
                height_cm=165,
                build="athletic-slender",
                skin=SkinSpec(base_hex="#E8B87A"),
            ),
            hair=HairSpec(
                color=HairColorSpec(roots="#C4A265"),
            ),
            face=FaceSpec(eyes={"iris_hex": "#4169E1"}),
            export=ExportSpec(format="vrm"),
        )

        # Serialize
        spec_dict = spec.to_dict()
        json_str = json.dumps(spec_dict)

        # Parse as build script would
        parsed = json.loads(json_str)
        assert parsed["name"] == "Test Avatar"
        assert parsed["body"]["height_cm"] == 165
        assert parsed["body"]["skin"]["base_hex"] == "#E8B87A"
        assert parsed["hair"]["color"]["roots"] == "#C4A265"

    def test_spec_json_to_temp_file(self):
        """Spec JSON can be written to temp file for Blender consumption."""
        from hamr.core.models import CharacterSpec, BodySpec

        spec = CharacterSpec(name="Temp Test", body=BodySpec(height_cm=170))
        spec_dict = spec.to_dict()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(spec_dict, f)
            temp_path = f.name

        assert Path(temp_path).exists()
        loaded = json.loads(Path(temp_path).read_text())
        assert loaded["name"] == "Temp Test"

        Path(temp_path).unlink()  # cleanup


# ── VRM Validation ────────────────────────────────────────────────────────────


class TestVRMValidation:
    """Post-export VRM file validation."""

    def test_validate_missing_file(self):
        from hamr.scripts.build_avatar import _validate_vrm
        with pytest.raises(ValueError, match="not found"):
            _validate_vrm("/nonexistent/path/avatar.vrm")

    def test_validate_too_small(self):
        """A nearly-empty file should fail validation."""
        from hamr.scripts.build_avatar import _validate_vrm
        with tempfile.NamedTemporaryFile(suffix=".vrm", delete=False) as f:
            f.write(b"not a real vrm file at all just junk")
            temp_path = f.name

        # Too small → should raise ValueError
        with pytest.raises(ValueError):
            _validate_vrm(temp_path)

        Path(temp_path).unlink()