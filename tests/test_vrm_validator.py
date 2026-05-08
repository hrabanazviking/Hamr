"""
Tests for VRM 1.0 Compliance Validator.

Every assertion is a hammer strike. The forge tests its own blades.

Phase 13 T3: VRM 1.0 validator — glTF compliance, bone coverage,
expression checks, binary parsing.
"""

from __future__ import annotations

import json
import struct

import pytest

from hamr.core.constants import VRM_25_BONE_NAMES
from hamr.export.vrm_validator import (
    VRMValidationResult,
    VRMValidator,
    extract_json_chunk,
    is_valid_vrm_binary,
    parse_vrm_bytes,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_minimal_valid_gltf() -> dict:
    """Create a minimal valid glTF 2.0 dict with VRM 1.0 extension."""
    bones_list = [
        {"bone": name, "node": i}
        for i, name in enumerate(VRM_25_BONE_NAMES)
    ]
    return {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": f"node_{i}"} for i in range(25)],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 0,
                            "NORMAL": 1,
                            "TEXCOORD_0": 2,
                        }
                    }
                ]
            }
        ],
        "materials": [
            {
                "name": "test_material",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                },
            }
        ],
        "textures": [{"source": 0, "sampler": 0}],
        "extensions": {
            "VRMC_vrm": {
                "humanoid": {
                    "humanBones": {name: {"node": i} for i, name in enumerate(VRM_25_BONE_NAMES)},
                },
                "expressions": {
                    "preset": {
                        "happy": {"morphTargetBinds": []},
                        "sad": {"morphTargetBinds": []},
                        "angry": {"morphTargetBinds": []},
                        "surprised": {"morphTargetBinds": []},
                        "neutral": {"morphTargetBinds": []},
                    }
                },
                "meta": {
                    "name": "test",
                    "version": "1.0",
                },
            }
        },
    }


def _make_gltf_no_vrm() -> dict:
    """Create a minimal glTF dict WITHOUT VRM extension."""
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "root"}],
    }


def _make_gltf_vrm0x() -> dict:
    """Create a minimal glTF dict with VRM 0.x extension."""
    bones_list = [
        {"bone": name, "node": i}
        for i, name in enumerate(VRM_25_BONE_NAMES)
    ]
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": f"node_{i}"} for i in range(25)],
        "extensions": {
            "VRM": {
                "humanoid": {
                    "humanBones": bones_list,
                },
                "blendShapeMaster": {
                    "blendShapeGroups": [
                        {"name": "happy"},
                        {"name": "sad"},
                        {"name": "angry"},
                        {"name": "surprised"},
                        {"name": "neutral"},
                    ]
                },
            }
        },
    }


def _make_gltf_binary(json_data: dict) -> bytes:
    """Create a minimal valid glTF binary (.glb) from a JSON dict.

    This constructs the binary on-the-fly — no file I/O needed.
    """
    json_str = json.dumps(json_data, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")

    # Pad JSON to 4-byte boundary
    pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * pad

    # BIN chunk (empty for testing)
    bin_data = b""
    # Pad BIN to 4-byte boundary
    bin_pad = (4 - (len(bin_data) % 4)) % 4
    bin_data += b"\x00" * bin_pad

    # Build chunks
    json_chunk = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    bin_chunk = struct.pack("<II", len(bin_data), 0x004E4942) + bin_data

    total_length = 12 + len(json_chunk) + len(bin_chunk)
    header = struct.pack("<III", 0x46546C67, 2, total_length)

    return header + json_chunk + bin_chunk


# ── VRMValidationResult dataclass tests ─────────────────────────────────────

class TestVRMValidationResult:
    """Test VRMValidationResult dataclass creation and defaults."""

    def test_creation_with_defaults(self):
        result = VRMValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.bone_coverage == 0.0
        assert result.material_count == 0
        assert result.mesh_count == 0
        assert result.texture_count == 0
        assert result.has_vrm_extension is False
        assert result.has_humanoid_bones is False
        assert result.has_expressions is False

    def test_creation_with_values(self):
        result = VRMValidationResult(
            valid=False,
            errors=["bone missing"],
            warnings=["no expressions"],
            bone_coverage=52.0,
            material_count=3,
            mesh_count=2,
            texture_count=5,
            has_vrm_extension=True,
            has_humanoid_bones=True,
            has_expressions=True,
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.bone_coverage == 52.0
        assert result.material_count == 3

    def test_default_factory_independence(self):
        r1 = VRMValidationResult(valid=True)
        r2 = VRMValidationResult(valid=True)
        r1.errors.append("test")
        assert r2.errors == [], "Default factory should produce independent lists"


# ── VRMValidator instantiation tests ─────────────────────────────────────────

class TestVRMValidatorInstantiation:
    """Test VRMValidator instantiation in strict and lenient modes."""

    def test_lenient_mode(self):
        v = VRMValidator(strict=False)
        assert v.strict is False

    def test_strict_mode(self):
        v = VRMValidator(strict=True)
        assert v.strict is True

    def test_default_is_lenient(self):
        v = VRMValidator()
        assert v.strict is False


# ── validate_vrm_structure tests ────────────────────────────────────────────

class TestValidateVRMStructure:
    """Test validate_vrm_structure with various data inputs."""

    def test_minimal_valid_data(self):
        data = _make_minimal_valid_gltf()
        v = VRMValidator(strict=False)
        result = v.validate_vrm_structure(data)
        # Should pass with valid glTF + VRM extension + all 25 bones
        assert result.valid is True
        assert result.errors == []
        assert result.bone_coverage == 100.0
        assert result.has_vrm_extension is True
        assert result.has_humanoid_bones is True
        assert result.has_expressions is True
        assert result.mesh_count == 1
        assert result.material_count == 1
        assert result.texture_count == 1

    def test_missing_gltf_fields(self):
        data = {}  # completely empty dict
        v = VRMValidator(strict=False)
        result = v.validate_vrm_structure(data)
        assert result.valid is False
        assert len(result.errors) > 0
        assert result.bone_coverage == 0.0

    def test_valid_vrm_extension_data(self):
        data = _make_minimal_valid_gltf()
        v = VRMValidator(strict=False)
        result = v.validate_vrm_structure(data)
        assert result.has_vrm_extension is True

    def test_no_vrm_extension_data(self):
        data = _make_gltf_no_vrm()
        v = VRMValidator(strict=False)
        result = v.validate_vrm_structure(data)
        assert result.valid is False
        assert result.has_vrm_extension is False


# ── check_gltf2_compliance tests ───────────────────────────────────────────

class TestCheckGlTF2Compliance:
    """Test glTF 2.0 required field checks."""

    def test_valid_gltf2(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"name": "root"}],
        })
        assert errors == []

    def test_missing_asset(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({"nodes": [{"name": "root"}]})
        assert any("asset" in e for e in errors)

    def test_missing_asset_version(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({"asset": {}})
        assert any("version" in e for e in errors)

    def test_wrong_gltf_version(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({"asset": {"version": "1.0"}})
        assert any("version" in e.lower() for e in errors)

    def test_missing_scene(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({
            "asset": {"version": "2.0"},
            "nodes": [{"name": "root"}],
        })
        assert any("scene" in e for e in errors)

    def test_missing_scenes(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({
            "asset": {"version": "2.0"},
            "scene": 0,
            "nodes": [{"name": "root"}],
        })
        assert any("scenes" in e for e in errors)

    def test_missing_nodes(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
        })
        assert any("nodes" in e for e in errors)

    def test_asset_wrong_type(self):
        v = VRMValidator()
        errors = v.check_gltf2_compliance({"asset": "not a dict"})
        assert any("asset" in e for e in errors)


# ── check_vrm_extension tests ──────────────────────────────────────────────

class TestCheckVRMExtension:
    """Test VRM 0.x and 1.0 extension detection and validation."""

    def test_vrm_1x_extension(self):
        v = VRMValidator()
        errors = v.check_vrm_extension({
            "extensions": {
                "VRMC_vrm": {
                    "humanoid": {"humanBones": {}},
                    "meta": {"name": "test"},
                }
            }
        })
        # Should have no errors about missing extension
        assert not any("extension" in e.lower() and "missing" in e.lower() for e in errors)

    def test_vrm_0x_extension(self):
        v = VRMValidator()
        errors = v.check_vrm_extension({
            "extensions": {
                "VRM": {
                    "humanoid": {"humanBones": []},
                }
            }
        })
        # VRM 0.x extension should be recognized
        assert not any("Neither" in e and "extension found" in e for e in errors)

    def test_no_extensions(self):
        v = VRMValidator()
        errors = v.check_vrm_extension({})
        assert any("extension" in e.lower() for e in errors)

    def test_wrong_extensions(self):
        v = VRMValidator()
        errors = v.check_vrm_extension({
            "extensions": {
                "KHR_materials_unlit": {},
            }
        })
        assert any("Neither" in e for e in errors)

    def test_vrm_1x_missing_humanoid(self):
        v = VRMValidator()
        errors = v.check_vrm_extension({
            "extensions": {
                "VRMC_vrm": {
                    "meta": {"name": "test"},
                }
            }
        })
        assert any("humanoid" in e for e in errors)


# ── check_humanoid_bones tests ──────────────────────────────────────────────

class TestCheckHumanoidBones:
    """Test humanoid bone verification for complete and partial maps."""

    def test_complete_bone_map(self):
        data = _make_minimal_valid_gltf()
        v = VRMValidator()
        errors = v.check_humanoid_bones(data)
        assert errors == [], f"Expected no errors for all 25 bones, got: {errors}"

    def test_partial_bone_map(self):
        """Only some bones mapped — should report missing bones."""
        partial_bones = {
            "hips": {"node": 0},
            "spine": {"node": 1},
            "head": {"node": 2},
        }
        data = {
            "extensions": {
                "VRMC_vrm": {
                    "humanoid": {
                        "humanBones": partial_bones,
                    }
                }
            }
        }
        v = VRMValidator()
        errors = v.check_humanoid_bones(data)
        assert len(errors) > 0
        # Should report 22 missing bones (25 - 3 found)
        assert len(errors) == 22

    def test_no_vrm_extension(self):
        data = {}
        v = VRMValidator()
        errors = v.check_humanoid_bones(data)
        assert len(errors) > 0
        assert any("humanoid" in e.lower() for e in errors)

    def test_vrm_0x_bone_list(self):
        """VRM 0.x uses a list of bone dicts."""
        bones_list = [
            {"bone": name, "node": i}
            for i, name in enumerate(VRM_25_BONE_NAMES)
        ]
        data = {
            "extensions": {
                "VRM": {
                    "humanoid": {
                        "humanBones": bones_list,
                    }
                }
            }
        }
        v = VRMValidator()
        errors = v.check_humanoid_bones(data)
        assert errors == []

    def test_vrm_0x_human_bone_name_key(self):
        """VRM 0.x sometimes uses 'humanBoneName' key."""
        bones_list = [
            {"humanBoneName": name, "node": i}
            for i, name in enumerate(VRM_25_BONE_NAMES)
        ]
        data = {
            "extensions": {
                "VRM": {
                    "humanoid": {
                        "humanBones": bones_list,
                    }
                }
            }
        }
        v = VRMValidator()
        errors = v.check_humanoid_bones(data)
        assert errors == []


# ── compute_bone_coverage tests ──────────────────────────────────────────────

class TestComputeBoneCoverage:
    """Test bone coverage percentage calculation."""

    def test_full_coverage(self):
        data = _make_minimal_valid_gltf()
        v = VRMValidator()
        coverage = v.compute_bone_coverage(data)
        assert coverage == 100.0

    def test_zero_coverage(self):
        """No VRM extension → 0% bone coverage."""
        data = {}
        v = VRMValidator()
        coverage = v.compute_bone_coverage(data)
        assert coverage == 0.0

    def test_partial_coverage_52_percent(self):
        """13 out of 25 bones mapped = 52%">
        (13/25 = 0.52, but 52.0 when expressed as percentage)
        """
        partial_bones = {
            name: {"node": i}
            for i, name in enumerate(VRM_25_BONE_NAMES[:13])
        }
        data = {
            "extensions": {
                "VRMC_vrm": {
                    "humanoid": {
                        "humanBones": partial_bones,
                    }
                }
            }
        }
        v = VRMValidator()
        coverage = v.compute_bone_coverage(data)
        # 13/25 * 100 = 52.0
        assert coverage == pytest.approx(52.0, abs=0.1)

    def test_exact_half_coverage(self):
        """12 out of 24... wait, 25 bones. Let's use 12/25."""
        partial_bones = {
            name: {"node": i}
            for i, name in enumerate(VRM_25_BONE_NAMES[:12])
        }
        data = {
            "extensions": {
                "VRMC_vrm": {
                    "humanoid": {
                        "humanBones": partial_bones,
                    }
                }
            }
        }
        v = VRMValidator()
        coverage = v.compute_bone_coverage(data)
        expected = (12 / 25) * 100.0  # 48.0
        assert coverage == pytest.approx(expected, abs=0.1)


# ── check_meshes tests ──────────────────────────────────────────────────────

class TestCheckMeshes:
    """Test mesh validation for valid and missing mesh data."""

    def test_valid_meshes(self):
        data = {
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": 0,
                                "NORMAL": 1,
                                "TEXCOORD_0": 2,
                            }
                        }
                    ]
                }
            ]
        }
        v = VRMValidator()
        warnings = v.check_meshes(data)
        assert warnings == []

    def test_no_meshes(self):
        data = {}
        v = VRMValidator()
        warnings = v.check_meshes(data)
        assert any("No meshes" in w for w in warnings)

    def test_empty_primitives(self):
        data = {
            "meshes": [
                {"primitives": []}
            ]
        }
        v = VRMValidator()
        warnings = v.check_meshes(data)
        assert any("no primitives" in w for w in warnings)

    def test_missing_position_attribute(self):
        data = {
            "meshes": [
                {
                    "primitives": [
                        {"attributes": {"NORMAL": 1}}
                    ]
                }
            ]
        }
        v = VRMValidator()
        warnings = v.check_meshes(data)
        assert any("POSITION" in w for w in warnings)

    def test_empty_attributes(self):
        data = {
            "meshes": [
                {
                    "primitives": [
                        {"attributes": {}}
                    ]
                }
            ]
        }
        v = VRMValidator()
        warnings = v.check_meshes(data)
        assert any("no attributes" in w for w in warnings)


# ── check_materials tests ───────────────────────────────────────────────────

class TestCheckMaterials:
    """Test material validation for valid material data."""

    def test_valid_materials(self):
        data = {
            "materials": [
                {
                    "name": "skin",
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    },
                }
            ]
        }
        v = VRMValidator()
        warnings = v.check_materials(data)
        assert warnings == []

    def test_no_materials(self):
        data = {}
        v = VRMValidator()
        warnings = v.check_materials(data)
        assert any("No materials" in w for w in warnings)

    def test_material_without_name(self):
        data = {
            "materials": [
                {"pbrMetallicRoughness": {"baseColorFactor": [1.0, 1.0, 1.0, 1.0]}}
            ]
        }
        v = VRMValidator()
        warnings = v.check_materials(data)
        assert any("name" in w for w in warnings)

    def test_material_without_pbr_or_extensions(self):
        data = {
            "materials": [
                {"name": "bare"}
            ]
        }
        v = VRMValidator()
        warnings = v.check_materials(data)
        assert any("pbrMetallicRoughness" in w or "extensions" in w for w in warnings)


# ── format_report tests ──────────────────────────────────────────────────────

class TestFormatReport:
    """Test format_report produces readable output."""

    def test_passing_report(self):
        result = VRMValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            bone_coverage=100.0,
            material_count=2,
            mesh_count=1,
            texture_count=3,
            has_vrm_extension=True,
            has_humanoid_bones=True,
            has_expressions=True,
        )
        v = VRMValidator(strict=False)
        report = v.format_report(result)
        assert "PASS" in report
        assert "100.0%" in report
        assert "No issues found" in report

    def test_failing_report(self):
        result = VRMValidationResult(
            valid=False,
            errors=["Missing bone: jaw"],
            warnings=["No expressions found"],
            bone_coverage=96.0,
            material_count=1,
            mesh_count=1,
            texture_count=0,
            has_vrm_extension=True,
            has_humanoid_bones=True,
            has_expressions=False,
        )
        v = VRMValidator(strict=False)
        report = v.format_report(result)
        assert "FAIL" in report
        assert "Missing bone" in report
        assert "No expressions" in report

    def test_strict_mode_in_report(self):
        v = VRMValidator(strict=True)
        result = VRMValidationResult(valid=True, errors=[], warnings=[])
        report = v.format_report(result)
        assert "STRICT" in report

    def test_lenient_mode_in_report(self):
        v = VRMValidator(strict=False)
        result = VRMValidationResult(valid=True, errors=[], warnings=[])
        report = v.format_report(result)
        assert "LENIENT" in report


# ── Binary parsing tests ────────────────────────────────────────────────────

class TestParseVRMBytes:
    """Test parse_vrm_bytes with valid VRM binary header."""

    def test_valid_binary(self):
        gltf_data = _make_minimal_valid_gltf()
        binary = _make_gltf_binary(gltf_data)
        result = parse_vrm_bytes(binary)
        assert isinstance(result, dict)
        assert "asset" in result
        assert result["asset"]["version"] == "2.0"

    def test_invalid_binary_raises(self):
        with pytest.raises(ValueError, match="Invalid VRM/glTF binary"):
            parse_vrm_bytes(b"not a vrm file")

    def test_too_short_binary_raises(self):
        with pytest.raises(ValueError):
            parse_vrm_bytes(b"glTF" + b"\x00" * 4)


class TestExtractJsonChunk:
    """Test extract_json_chunk with embedded JSON data."""

    def test_valid_binary(self):
        gltf_data = {"asset": {"version": "2.0"}, "scene": 0}
        binary = _make_gltf_binary(gltf_data)
        result = extract_json_chunk(binary)
        assert result["asset"]["version"] == "2.0"

    def test_invalid_magic(self):
        bad_data = b"XXXX" + struct.pack("<I", 2) + struct.pack("<I", 100) + b"\x00" * 88
        with pytest.raises(ValueError, match="Invalid glTF magic"):
            extract_json_chunk(bad_data)

    def test_wrong_version(self):
        # glTF version 1 instead of 2
        header = struct.pack("<III", 0x46546C67, 1, 12 + 8)
        json_bytes = b'{"asset":{"version":"1.0"}}'
        pad = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b" " * pad
        chunk = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
        binary = header + chunk
        with pytest.raises(ValueError, match="Unsupported glTF version"):
            extract_json_chunk(binary)

    def test_empty_dict_roundtrip(self):
        gltf_data = {"asset": {"version": "2.0"}}
        binary = _make_gltf_binary(gltf_data)
        result = extract_json_chunk(binary)
        assert result["asset"]["version"] == "2.0"


class TestIsValidVRMBinary:
    """Test is_valid_vrm_binary with valid and invalid data."""

    def test_valid_binary(self):
        gltf_data = {"asset": {"version": "2.0"}}
        binary = _make_gltf_binary(gltf_data)
        assert is_valid_vrm_binary(binary) is True

    def test_empty_data(self):
        assert is_valid_vrm_binary(b"") is False

    def test_none_data(self):
        assert is_valid_vrm_binary(None) is False

    def test_random_bytes(self):
        assert is_valid_vrm_binary(b"random data that is not glTF") is False

    def test_valid_magic_wrong_version(self):
        # Magic is glTF but version is 1
        header = struct.pack("<III", 0x46546C67, 1, 100)
        data = header + b"\x00" * 88
        assert is_valid_vrm_binary(data) is False

    def test_short_data(self):
        # Too short for even the header
        assert is_valid_vrm_binary(b"glT") is False

    def test_valid_magic_valid_version(self):
        header = struct.pack("<III", 0x46546C67, 2, 100)
        data = header + b"\x00" * 88
        assert is_valid_vrm_binary(data) is True


# ── Strict mode tests ────────────────────────────────────────────────────────

class TestStrictMode:
    """Test that strict mode converts warnings to errors."""

    def test_warnings_cause_failure_in_strict(self):
        """In strict mode, even warnings should make result invalid."""
        data = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"name": "root"}],
            "meshes": [],  # empty meshes → warning
            "materials": [],  # empty materials → warning
            "extensions": {
                "VRMC_vrm": {
                    "humanoid": {
                        "humanBones": {name: {"node": i} for i, name in enumerate(VRM_25_BONE_NAMES)},
                    },
                }
            },
        }
        v_strict = VRMValidator(strict=True)
        result = v_strict.validate_vrm_structure(data)
        # In strict mode, warnings should cause failure
        assert result.valid is False

    def test_warnings_ok_in_lenient(self):
        """In lenient mode, only errors should make result invalid."""
        data = _make_minimal_valid_gltf()
        v_lenient = VRMValidator(strict=False)
        result = v_lenient.validate_vrm_structure(data)
        # In lenient mode, warnings should NOT cause failure
        assert result.valid is True

    def test_strict_mode_flag_in_report(self):
        v = VRMValidator(strict=True)
        result = VRMValidationResult(valid=True)
        report = v.format_report(result)
        assert "STRICT" in report


# ── VRM 0.x extension compatibility tests ─────────────────────────────────────

class TestVRM0xCompatibility:
    """Test that the validator handles VRM 0.x format correctly."""

    def test_vrm0x_full_structure(self):
        data = _make_gltf_vrm0x()
        v = VRMValidator(strict=False)
        result = v.validate_vrm_structure(data)
        assert result.has_vrm_extension is True
        assert result.bone_coverage == 100.0
        assert result.has_expressions is True

    def test_vrm0x_bone_coverage(self):
        data = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"name": "root"}],
            "extensions": {
                "VRM": {
                    "humanoid": {
                        "humanBones": [
                            {"bone": "hips", "node": 0},
                            {"bone": "head", "node": 1},
                        ],
                    },
                }
            },
        }
        v = VRMValidator()
        coverage = v.compute_bone_coverage(data)
        # 2 / 25 * 100 = 8.0
        assert coverage == pytest.approx(8.0, abs=0.1)