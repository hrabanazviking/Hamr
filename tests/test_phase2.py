"""
Tests for Hamr Phase 2 modules:
- Blender Bridge (runner, scene, mesh_ops)
- Texture Forge (HSV shifts, tinting, gradients)
- Body Forge (presets, resolution)
- Export (bone maps, metadata)
- Builder (orchestration)
"""

import pytest
import json
import math
from pathlib import Path

from hamr.core.models import (
    CharacterSpec, BodySpec, FaceSpec, HairSpec,
    HairColorSpec, SkinSpec, ClothingSpec, PhysicsSpec, ExportSpec,
)
from hamr.core.spec import Spec
from hamr.core.validate import validate_spec
from hamr.core.constants import (
    BODY_PRESETS, TEXTURE_SIZE, TEXTURE_BLEND_FACTOR,
    SKIN_BASE_HEX, HAIR_ROOTS_HEX,
)
from hamr.core.errors import HamrError, SpecValidationError, BuildError, ExportError
from hamr.export.vrm import MB_LAB_BONE_MAP, VRM_REQUIRED_BONES


# ──────────────────────────────────────────────
# Texture Forge Tests
# ──────────────────────────────────────────────

class TestTextures:
    """Tests for the Texture Forge (Pillow + NumPy)."""

    def test_hex_to_rgb(self):
        from hamr.core.textures import hex_to_rgb
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)
        assert hex_to_rgb("#E8B87A") == (232, 184, 122)

    def test_hex_to_hsv(self):
        from hamr.core.textures import hex_to_hsv
        h, s, v = hex_to_hsv("#FF0000")
        assert abs(h - 0.0) < 0.01
        assert abs(s - 1.0) < 0.01
        assert abs(v - 1.0) < 0.01

    def test_hsv_to_hex_roundtrip(self):
        from hamr.core.textures import hex_to_hsv, hsv_to_hex
        original = "#E8B87A"
        h, s, v = hex_to_hsv(original)
        result = hsv_to_hex(h, s, v)
        # Allow 1 unit of error per channel
        r1, g1, b1 = int(original[1:3], 16), int(original[3:5], 16), int(original[5:7], 16)
        r2, g2, b2 = int(result[1:3], 16), int(result[3:5], 16), int(result[5:7], 16)
        assert abs(r1 - r2) <= 1
        assert abs(g1 - g2) <= 1
        assert abs(b1 - b2) <= 1

    def test_shift_hsv_no_shift(self):
        """Shifting with zero values returns the original image."""
        from hamr.core.textures import shift_hsv
        from PIL import Image
        import numpy as np
        img = Image.fromarray(np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8))
        result = shift_hsv(img, hue_shift=0, sat_shift=1.0, val_shift=1.0, blend=1.0)
        result_arr = np.array(result)
        orig_arr = np.array(img.convert("RGB"))
        # Should be very close (some floating point rounding)
        assert np.allclose(result_arr, orig_arr, atol=2)

    def test_shift_hsv_with_hue(self):
        """Hue shift should change colors."""
        from hamr.core.textures import shift_hsv
        from PIL import Image
        import numpy as np
        # Red image
        red = Image.fromarray(np.full((64, 64, 3), [255, 0, 0], dtype=np.uint8))
        result = shift_hsv(red, hue_shift=120, sat_shift=1.0, val_shift=1.0, blend=1.0)
        # After 120° hue shift, red should become green-ish
        result_arr = np.array(result)
        assert result_arr[0, 0, 1] > 100  # Green channel should be significant

    def test_tint_texture(self):
        """Tinting should shift color toward target."""
        from hamr.core.textures import tint_texture, hex_to_rgb
        from PIL import Image
        import numpy as np
        # White base image
        white = Image.fromarray(np.full((64, 64, 3), 255, dtype=np.uint8))
        result = tint_texture(white, "#FF0000", blend=0.5)
        result_arr = np.array(result)
        # Should have shifted toward red
        assert result_arr[0, 0, 0] > 200  # Red channel high
        assert result_arr[0, 0, 1] < 200  # Green channel lower

    def test_generate_gradient_texture(self):
        """Gradient should produce smooth color transition."""
        from hamr.core.textures import generate_gradient_texture
        import numpy as np
        grad = generate_gradient_texture(64, 64, "#000000", "#FFFFFF", "vertical")
        arr = np.array(grad)
        # Top should be dark, bottom should be bright
        assert arr[0, 0].mean() < arr[-1, 0].mean()

    def test_generate_skin_texture(self):
        """Skin texture generation should produce a valid image."""
        from hamr.core.textures import generate_skin_texture
        import numpy as np
        skin = SkinSpec(base_hex="#E8B87A", undertone="warm")
        result = generate_skin_texture(skin, size=128)
        assert result.size == (128, 128)
        arr = np.array(result)
        # Should be roughly around the base color
        assert arr.mean() > 100  # Not too dark
        assert arr.mean() < 250  # Not pure white

    def test_generate_hair_texture(self):
        """Hair texture should produce a gradient from roots to tips."""
        from hamr.core.textures import generate_hair_texture
        import numpy as np
        hair = HairColorSpec(roots="#3A1E0A", tips="#8B6D2F")
        result = generate_hair_texture(hair, size=128)
        assert result.size == (128, 128)
        arr = np.array(result)
        # Tips (top) should be lighter than roots (bottom)
        top_row_mean = arr[0, :, :].mean()
        bottom_row_mean = arr[-1, :, :].mean()
        assert top_row_mean > bottom_row_mean


# ──────────────────────────────────────────────
# Blender Bridge Tests (no Blender needed)
# ──────────────────────────────────────────────

class TestBlenderBridge:
    """Tests for Blender Bridge module (no Blender required)."""

    def test_runner_imports(self):
        """Runner module should be importable without Blender."""
        from hamr.blender_bridge.runner import (
            BlenderResult,
            run_blender_script,
            run_inline_script,
            check_blender_available,
            get_blender_version,
        )
        assert BlenderResult is not None

    def test_blender_result(self):
        """BlenderResult should store exit code and timing."""
        from hamr.blender_bridge.runner import BlenderResult
        result = BlenderResult(exit_code=0, stdout="ok", stderr="", elapsed=5.2)
        assert result.success is True
        assert result.elapsed == 5.2

    def test_blender_result_failure(self):
        """BlenderResult with non-zero exit code should report failure."""
        from hamr.blender_bridge.runner import BlenderResult
        result = BlenderResult(exit_code=1, stdout="", stderr="error", elapsed=1.0)
        assert result.success is False

    def test_scene_module_imports(self):
        """Scene module should be importable (bpy guarded)."""
        from hamr.blender_bridge.scene import BLENDER_AVAILABLE
        # On Pi without Blender running, should be False
        assert isinstance(BLENDER_AVAILABLE, bool)

    def test_mesh_ops_module_imports(self):
        """mesh_ops module should be importable (bpy guarded)."""
        from hamr.blender_bridge.mesh_ops import BLENDER_AVAILABLE
        assert isinstance(BLENDER_AVAILABLE, bool)


# ──────────────────────────────────────────────
# Export Forge Tests
# ──────────────────────────────────────────────

class TestExport:
    """Tests for VRM/GLB export module."""

    def test_bone_map_completeness(self):
        """MB-Lab bone map should cover all required VRM bones."""
        # At minimum, all required bones must be mapped
        for bone in VRM_REQUIRED_BONES:
            assert bone in MB_LAB_BONE_MAP, f"Required bone '{bone}' not in MB-Lab bone map"

    def test_bone_map_values(self):
        """Bone map values should be non-empty strings."""
        for vrm_name, blender_name in MB_LAB_BONE_MAP.items():
            assert isinstance(blender_name, str)
            assert len(blender_name) > 0

    def test_vrm_required_bones_count(self):
        """VRM 1.0 requires at least 15 humanoid bones."""
        assert len(VRM_REQUIRED_BONES) >= 15


# ──────────────────────────────────────────────
# Body Forge Tests
# ──────────────────────────────────────────────

class TestBodyForge:
    """Tests for Body Forge module."""

    def test_body_presets_exist(self):
        """All canonical body presets should be defined."""
        expected = ["athletic-slender", "athletic", "curvy", "slender",
                    "average", "tall", "petite", "muscular"]
        for preset in expected:
            assert preset in BODY_PRESETS, f"Missing preset: {preset}"

    def test_preset_proportions(self):
        """Each preset should have proportion values between 0 and 1."""
        for name, proportions in BODY_PRESETS.items():
            for key, value in proportions.items():
                assert 0 <= value <= 1, f"Preset '{name}' key '{key}' has value {value} outside [0, 1]"

    def test_body_forge_imports(self):
        """BodyForge class should be importable."""
        from hamr.body.forge import BodyForge
        forge = BodyForge()
        assert forge is not None

    def test_resolve_body_preset(self):
        """Resolving a preset should merge with spec overrides."""
        from hamr.body.forge import BodyForge
        forge = BodyForge()
        spec = CharacterSpec(
            name="Test",
            body=BodySpec(
                height_cm=170,
                build="athletic-slender",
                skin=SkinSpec(base_hex="#E8B87A"),
                proportions={"shoulders": 0.8},  # Override
            ),
        )
        resolved = forge._resolve_body(spec.body)
        # Should have preset values plus the override
        assert resolved.proportions["shoulders"] == 0.8  # Override preserved
        assert "waist" in resolved.proportions  # Preset value present


# ──────────────────────────────────────────────
# Builder Tests
# ──────────────────────────────────────────────

class TestBuilder:
    """Tests for the build pipeline."""

    def test_validate_only_valid_spec(self, tmp_path):
        """Validating a valid spec should return no errors."""
        spec_file = tmp_path / "test_spec.yaml"
        spec_file.write_text("""
name: Test Character
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        from hamr.core.builder import validate_only
        errors = validate_only(str(spec_file))
        assert len(errors) == 0

    def test_validate_invalid_height(self, tmp_path):
        """Invalid height should fail validation."""
        spec_file = tmp_path / "bad_spec.yaml"
        spec_file.write_text("""
name: Bad Character
version: "1.0"
body:
  height_cm: -50
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        from hamr.core.builder import validate_only
        from hamr.core.errors import SpecValidationError
        with pytest.raises(SpecValidationError, match="height_cm"):
            validate_only(str(spec_file))

    def test_build_raises_without_blender(self, tmp_path):
        """Building without Blender script should raise BuildError."""
        spec_file = tmp_path / "test_spec.yaml"
        spec_file.write_text("""
name: Test Character
version: "1.0"
body:
  height_cm: 170
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
""")
        from hamr.core.builder import build
        with pytest.raises(BuildError, match="Build script not found"):
            build(str(spec_file), str(tmp_path / "output"))


# ──────────────────────────────────────────────
# Spec Round-Trip Tests (from Phase 1, extended)
# ──────────────────────────────────────────────

class TestSpecExtended:
    """Extended spec tests for Phase 2 features."""

    def test_skin_spec_defaults(self):
        """SkinSpec should have sensible defaults."""
        skin = SkinSpec()
        assert skin.base_hex == "#E8B87A"
        assert skin.undertone == "warm"
        # sss_enabled removed from SkinSpec in Phase 2

    def test_hair_color_spec(self):
        """HairColorSpec should store roots and tips."""
        hair_color = HairColorSpec(roots="#3A1E0A", tips="#8B6D2F")
        assert hair_color.roots == "#3A1E0A"
        assert hair_color.tips == "#8B6D2F"

    def test_full_character_with_hair(self):
        """Character should accept all Phase 2 fields."""
        char = CharacterSpec(
            name="Full Test",
            body=BodySpec(
                height_cm=173,
                build="athletic-slender",
                skin=SkinSpec(base_hex="#E8B87A", undertone="warm"),
            ),
            hair=HairSpec(
                style="long_straight",
                color=HairColorSpec(roots="#3A1E0A", tips="#8B6D2F"),
            ),
            face=FaceSpec(eyes={"iris_hex": "#4169E1"}),
            export=ExportSpec(format="vrm"),
        )
        assert char.hair.color.roots == "#3A1E0A"
        assert char.face.eyes.get("iris_hex") == "#4169E1"
        assert char.export.format == "vrm"

    def test_spec_json_export(self, tmp_path):
        """Spec should export to JSON for Blender build script."""
        spec = Spec(character=CharacterSpec(
            name="JSON Test",
            body=BodySpec(height_cm=170, build="athletic-slender", skin=SkinSpec()),
        ))
        json_str = json.dumps(spec.to_dict())
        data = json.loads(json_str)
        assert data["name"] == "JSON Test"
        assert data["body"]["height_cm"] == 170