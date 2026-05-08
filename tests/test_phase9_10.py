# =============================================================================
# Hamr Phase 9+10 Tests — The Awakening & The Final Quench
# CLI dry-run, bone mapping, MB-Lab character generation, and E2E VRM validation
# =============================================================================

import subprocess
import json
import struct
import tempfile
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJ = Path(__file__).resolve().parent.parent
EXAMPLES = PROJ / "examples"
MINIMAL_YAML = EXAMPLES / "minimal.yaml"
RUNA_YAML = EXAMPLES / "runa_gridweaver.yaml"

# ── MB-Lab Bone Map ───────────────────────────────────────────────────────────

MB_LAB_BONE_MAP = {
    "hips": "pelvis",
    "spine": "spine01",
    "chest": "spine02",
    "upperChest": "spine03",
    "neck": "neck",
    "head": "head",
    "leftUpperLeg": "thigh_L",
    "leftLowerLeg": "calf_L",
    "leftFoot": "foot_L",
    "leftToes": "toes_L",
    "rightUpperLeg": "thigh_R",
    "rightLowerLeg": "calf_R",
    "rightFoot": "foot_R",
    "rightToes": "toes_R",
    "leftShoulder": "clavicle_L",
    "leftUpperArm": "upperarm_L",
    "leftLowerArm": "lowerarm_L",
    "leftHand": "hand_L",
    "rightShoulder": "clavicle_R",
    "rightUpperArm": "upperarm_R",
    "rightLowerArm": "lowerarm_R",
    "rightHand": "hand_R",
    "jaw": "jaw",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 9 — The Awakening: CLI, Spec, and Bone Mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLIDryRun:
    """CLI --dry-run validates spec without launching Blender."""

    def test_dry_run_minimal_spec(self):
        result = subprocess.run(
            ["python", "-m", "hamr.cli", "build", str(MINIMAL_YAML), "--dry-run"],
            capture_output=True, text=True, cwd=str(PROJ),
        )
        assert result.returncode == 0, f"dry-run failed: {result.stderr}"
        assert "Quick Avatar" in result.stdout or "Quick" in result.stdout

    def test_dry_run_verbose(self):
        result = subprocess.run(
            ["python", "-m", "hamr.cli", "build", str(MINIMAL_YAML), "--dry-run", "--verbose"],
            capture_output=True, text=True, cwd=str(PROJ),
        )
        assert result.returncode == 0
        assert "Hair" in result.stdout or "hair" in result.stdout

    def test_dry_run_nonexistent_spec_fails(self):
        result = subprocess.run(
            ["python", "-m", "hamr.cli", "build", "/nonexistent/spec.yaml", "--dry-run"],
            capture_output=True, text=True, cwd=str(PROJ),
        )
        assert result.returncode != 0

    def test_dry_run_with_format(self):
        result = subprocess.run(
            ["python", "-m", "hamr.cli", "build", str(MINIMAL_YAML), "--dry-run", "--format", "vrm1"],
            capture_output=True, text=True, cwd=str(PROJ),
        )
        assert result.returncode == 0


class TestBoneMapping:
    """MB-Lab bone names map correctly to VRM humanoid bones."""

    def test_mblab_bone_map_has_required_vrm_bones(self):
        """VRM 1.0 requires at least 15 humanoid bones."""
        required = [
            "hips", "spine", "chest", "neck", "head",
            "leftUpperLeg", "leftLowerLeg", "leftFoot",
            "rightUpperLeg", "rightLowerLeg", "rightFoot",
            "leftUpperArm", "leftLowerArm", "leftHand",
            "rightUpperArm", "rightLowerArm", "rightHand",
        ]
        for bone in required:
            assert bone in MB_LAB_BONE_MAP, f"Missing required bone: {bone}"

    def test_mblab_bone_map_values_are_underscore_notation(self):
        """MB-Lab uses underscore notation (thigh_L) not dot notation (thigh.L)."""
        for vrm_name, mblab_name in MB_LAB_BONE_MAP.items():
            assert "." not in mblab_name, (
                f"MB-Lab bone '{mblab_name}' for VRM '{vrm_name}' uses dot notation — should use underscore"
            )

    def test_mblab_bone_map_has_jaw(self):
        """Jaw bone should be in the map even if MB-Lab may not have it."""
        assert "jaw" in MB_LAB_BONE_MAP

    def test_no_eye_bones_in_mblab_map(self):
        """MB-Lab rigs do not have eye bones — they should not be in the bone map."""
        assert "leftEye" not in MB_LAB_BONE_MAP
        assert "rightEye" not in MB_LAB_BONE_MAP


class TestExpressionMaps:
    """Expression maps contain correct MB-Lab shape key names."""

    def test_mblab_expression_map_has_required_presets(self):
        from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
        required = ["happy", "angry", "sad", "relaxed", "surprised", "blink", "aa", "ih", "ou", "ee", "oh"]
        for preset in required:
            assert preset in MB_LAB_EXPRESSION_MAP, f"Missing preset: {preset}"

    def test_mblab_expression_keys_use_prefix(self):
        """MB-Lab expression shape keys use the Expressions_ prefix."""
        from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
        for preset, bindings in MB_LAB_EXPRESSION_MAP.items():
            for binding in bindings:
                sk = binding.get("shape_key", "")
                assert sk.startswith("Expressions_"), (
                    f"Shape key '{sk}' in preset '{preset}' doesn't use Expressions_ prefix"
                )

    def test_mblab_no_hardcoded_mesh_names(self):
        """MB-Lab expression bindings should NOT have hardcoded mesh names."""
        from hamr.scripts.build_avatar import MB_LAB_EXPRESSION_MAP
        for preset, bindings in MB_LAB_EXPRESSION_MAP.items():
            for binding in bindings:
                assert "mesh" not in binding, (
                    f"Binding in preset '{preset}' has hardcoded 'mesh' key: {binding}"
                )

    def test_turbosquid_no_hardcoded_mesh_names(self):
        """TurboSquid expression bindings should NOT have hardcoded mesh names."""
        from hamr.scripts.build_avatar import TURBOSQUID_EXPRESSION_MAP
        for preset, bindings in TURBOSQUID_EXPRESSION_MAP.items():
            for binding in bindings:
                assert "mesh" not in binding, (
                    f"Binding in preset '{preset}' has hardcoded 'mesh' key: {binding}"
                )


class TestExampleSpecs:
    """Example character specs are valid."""

    @pytest.mark.parametrize("spec_file", [
        "minimal.yaml",
        "runa_gridweaver.yaml",
        "warrior_shield_maiden.yaml",
        "mage_volva.yaml",
    ])
    def test_example_spec_loads(self, spec_file):
        from hamr.core.spec import Spec
        path = EXAMPLES / spec_file
        spec = Spec.from_yaml(path)
        assert spec.character.name
        assert spec.character.hair is not None

    def test_runa_spec_has_clothing(self):
        from hamr.core.spec import Spec
        spec = Spec.from_yaml(RUNA_YAML)
        assert len(spec.character.clothing) > 0

    def test_runa_spec_has_jaw(self):
        from hamr.core.spec import Spec
        spec = Spec.from_yaml(RUNA_YAML)
        assert spec.character.face is not None
        if spec.character.face.jaw:
            assert spec.character.face.jaw == "V-shape"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 10 — The Final Quench: VRM File Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestVRMValidation:
    """Validate the structure of a generated VRM file."""

    @pytest.fixture(scope="class")
    def vrm_path(self):
        """Find the most recently built VRM file in output/."""
        output_dir = PROJ / "output"
        if not output_dir.exists():
            pytest.skip("No output directory — run a VRM build first")
        vrm_files = sorted(output_dir.glob("*.vrm1"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not vrm_files:
            pytest.skip("No VRM files found — run a VRM build first")
        return vrm_files[0]

    def test_vrm_file_exists_and_not_small(self, vrm_path):
        """VRM file exists and is not suspiciously small."""
        assert vrm_path.exists()
        size_mb = vrm_path.stat().st_size / (1024 * 1024)
        assert size_mb > 0.1, f"VRM file too small: {size_mb:.2f} MB"

    def test_vrm_gltf_magic(self, vrm_path):
        """VRM file starts with glTF 2.0 magic bytes."""
        with open(vrm_path, "rb") as f:
            header = f.read(12)
        magic = struct.unpack("<I", header[0:4])[0]
        assert magic == 0x46546C67, f"Not a glTF file: magic=0x{magic:08X}"

    def test_vrm_has_vrmc_extension(self, vrm_path):
        """VRM file contains VRMC_vrm extension."""
        gltf = _parse_gltf_json(vrm_path)
        assert gltf is not None, "Could not parse glTF JSON"
        extensions = gltf.get("extensions", {})
        assert "VRMC_vrm" in extensions, "Missing VRMC_vrm extension"

    def test_vrm_has_humanoid_bones(self, vrm_path):
        """VRM file has humanoid bone mappings."""
        gltf = _parse_gltf_json(vrm_path)
        vrm = gltf["extensions"]["VRMC_vrm"]
        bones = vrm.get("humanoid", {}).get("humanBones", {})
        assert len(bones) >= 15, f"Too few humanoid bones: {len(bones)}"

    def test_vrm_has_expressions(self, vrm_path):
        """VRM file has expression presets."""
        gltf = _parse_gltf_json(vrm_path)
        vrm = gltf["extensions"]["VRMC_vrm"]
        expressions = vrm.get("expressions", {})
        preset = expressions.get("preset", {})
        assert len(preset) >= 5, f"Too few expression presets: {len(preset)}"

    def test_vrm_has_lookat(self, vrm_path):
        """VRM file has lookAt configuration."""
        gltf = _parse_gltf_json(vrm_path)
        vrm = gltf["extensions"]["VRMC_vrm"]
        lookat = vrm.get("lookAt", {})
        assert "type" in lookat, "Missing lookAt type"
        assert lookat["type"] in ("bone", "expression"), f"Invalid lookAt type: {lookat['type']}"


# ── Helper ────────────────────────────────────────────────────────────────────

def _parse_gltf_json(vrm_path: Path) -> dict | None:
    """Extract and parse the glTF JSON chunk from a VRM file."""
    import json as _json
    with open(vrm_path, "rb") as f:
        f.read(12)  # skip glTF header
        chunk_len = struct.unpack("<I", f.read(4))[0]
        f.read(4)  # skip chunk_type
        # Check if this is standard glTF binary or Blender-variant
        f.seek(20)
        all_data = f.read(chunk_len + 8)  # generous read
        # Find JSON start
        json_start = all_data.find(b'{"')
        if json_start < 0:
            return None
        # Count braces
        depth = 0
        pos = json_start
        while pos < len(all_data):
            if all_data[pos:pos+1] == b'{':
                depth += 1
            elif all_data[pos:pos+1] == b'}':
                depth -= 1
                if depth == 0:
                    return _json.loads(all_data[json_start:pos+1])
            pos += 1
    return None