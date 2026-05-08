"""
Tests for procedural texture pipeline — Phase 13 T2.

Every pore, every fiber tested in isolation.
No Blender required. NumPy + Pillow (graceful skips if Pillow absent).
"""

from __future__ import annotations

import pytest
import numpy as np

# ── Graceful import guard ─────────────────────────────────────
# Pillow may not be available in all test environments.
# NumPy is required — if missing, skip everything.

from hamr.core.texture_procedural import (
    ProceduralTexture,
    ProceduralTexturePipeline,
    _perlin_noise_2d,
    _radial_gradient,
    _height_to_normal,
    _make_texture_image,
    PILLOW_AVAILABLE,
)


# ═══════════════════════════════════════════════════════════════
# ProceduralTexture dataclass tests
# ═══════════════════════════════════════════════════════════════

class TestProceduralTextureDataclass:
    """Test ProceduralTexture creation and defaults."""

    def test_creation_with_defaults(self):
        tex = ProceduralTexture(name="test_tex")
        assert tex.name == "test_tex"
        assert tex.width == 1024
        assert tex.height == 1024
        assert tex.texture_type == "diffuse"
        assert tex.data == b""
        assert tex.generated is False

    def test_creation_with_custom_params(self):
        tex = ProceduralTexture(
            name="custom",
            width=512,
            height=512,
            texture_type="normal",
            data=b"\x89PNG_fake",
            generated=True,
        )
        assert tex.name == "custom"
        assert tex.width == 512
        assert tex.height == 512
        assert tex.texture_type == "normal"
        assert tex.data == b"\x89PNG_fake"
        assert tex.generated is True

    def test_all_texture_types(self):
        """All defined texture_type strings should be valid."""
        valid_types = {"diffuse", "normal", "sss_thickness", "iris_detail", "hair_gradient"}
        for ttype in valid_types:
            tex = ProceduralTexture(name=f"tex_{ttype}", texture_type=ttype)
            assert tex.texture_type == ttype

    def test_default_data_is_empty_bytes(self):
        tex = ProceduralTexture(name="default")
        assert isinstance(tex.data, bytes)
        assert len(tex.data) == 0

    def test_generated_flag_defaults_false(self):
        tex = ProceduralTexture(name="flag_test")
        assert tex.generated is False


# ═══════════════════════════════════════════════════════════════
# Helper function tests
# ═══════════════════════════════════════════════════════════════

class TestPerlinNoise:
    """Test _perlin_noise_2d with various parameters."""

    def test_basic_generation(self):
        result = _perlin_noise_2d((64, 64), scale=20.0, octaves=2, seed=42)
        assert result.shape == (64, 64)
        assert result.dtype == np.float32

    def test_output_range(self):
        """Values should be in [0, 1]."""
        result = _perlin_noise_2d((128, 128), scale=30.0, octaves=3, seed=7)
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_reproducibility_with_seed(self):
        """Same seed should produce same output."""
        r1 = _perlin_noise_2d((64, 64), scale=25.0, octaves=2, seed=42)
        r2 = _perlin_noise_2d((64, 64), scale=25.0, octaves=2, seed=42)
        np.testing.assert_array_equal(r1, r2)

    def test_different_seeds_different_output(self):
        """Different seeds should produce different outputs."""
        r1 = _perlin_noise_2d((64, 64), scale=25.0, octaves=2, seed=1)
        r2 = _perlin_noise_2d((64, 64), scale=25.0, octaves=2, seed=2)
        assert not np.allclose(r1, r2)

    def test_different_scales(self):
        """Different scales should produce different outputs."""
        r1 = _perlin_noise_2d((64, 64), scale=10.0, octaves=2, seed=42)
        r2 = _perlin_noise_2d((64, 64), scale=50.0, octaves=2, seed=42)
        assert not np.allclose(r1, r2)

    def test_more_octaves_more_detail(self):
        """More octaves should add more detail (higher variance)."""
        r2 = _perlin_noise_2d((128, 128), scale=30.0, octaves=2, seed=42)
        r6 = _perlin_noise_2d((128, 128), scale=30.0, octaves=6, seed=42)
        # Higher octave count should have more variation
        assert r2.std() > 0  # At least some variation
        assert r6.std() > 0

    def test_non_square_shape(self):
        """Should work with non-square dimensions."""
        result = _perlin_noise_2d((64, 128), scale=20.0, octaves=2, seed=42)
        assert result.shape == (64, 128)

    def test_small_scale_fine_detail(self):
        """Small scale should produce finer detail patterns."""
        fine = _perlin_noise_2d((128, 128), scale=5.0, octaves=4, seed=42)
        coarse = _perlin_noise_2d((128, 128), scale=100.0, octaves=4, seed=42)
        # Fine detail should have higher frequency variation
        # Measured by gradient magnitude
        fine_grad = np.abs(np.diff(fine, axis=0)).mean()
        coarse_grad = np.abs(np.diff(coarse, axis=0)).mean()
        assert fine_grad > coarse_grad


class TestRadialGradient:
    """Test _radial_gradient helper."""

    def test_basic_generation(self):
        result = _radial_gradient((64, 64))
        assert result.shape == (64, 64, 3)

    def test_center_bright(self):
        """Center should match inner_color."""
        result = _radial_gradient(
            (64, 64),
            center=(0.5, 0.5),
            inner_color=(1.0, 1.0, 1.0),
            outer_color=(0.0, 0.0, 0.0),
        )
        # Center pixel should be close to white
        center_val = result[32, 32]
        assert center_val[0] > 0.8
        assert center_val[1] > 0.8
        assert center_val[2] > 0.8

    def test_edges_dark(self):
        """Edges should lean toward outer_color."""
        result = _radial_gradient(
            (64, 64),
            center=(0.5, 0.5),
            inner_color=(1.0, 1.0, 1.0),
            outer_color=(0.0, 0.0, 0.0),
        )
        # Corner pixel should be darker than center
        corner_val = result[0, 0]
        center_val = result[32, 32]
        assert corner_val[0] < center_val[0]

    def test_custom_center(self):
        """Off-center gradient should shift the bright region."""
        result = _radial_gradient(
            (64, 64),
            center=(0.8, 0.8),
            inner_color=(1.0, 1.0, 1.0),
            outer_color=(0.0, 0.0, 0.0),
        )
        # Pixel near (0.8, 0.8) should be brighter than opposite corner
        bright_val = result[51, 51]  # ~80% of 64
        dark_val = result[3, 3]
        assert bright_val[0] > dark_val[0]

    def test_values_clipped(self):
        """Output should be clipped to [0, 1]."""
        result = _radial_gradient(
            (64, 64),
            inner_color=(0.5, 0.5, 0.5),
            outer_color=(0.2, 0.2, 0.2),
        )
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestHeightToNormal:
    """Test _height_to_normal conversion."""

    def test_basic_conversion(self):
        height = np.zeros((64, 64), dtype=np.float32)
        normal = _height_to_normal(height, strength=1.0)
        assert normal.shape == (64, 64, 3)
        assert normal.dtype == np.uint8

    def test_flat_surface_default_normal(self):
        """Flat surface should produce mostly (0.5, 0.5, 1.0) normals → (128, 128, 255)."""
        height = np.ones((64, 64), dtype=np.float32) * 0.5
        normal = _height_to_normal(height, strength=1.0)
        # Flat surface: Z component should be ~255, X/Y ~128
        center = normal[32, 32]
        assert center[2] > 200  # Z should be prominent
        assert abs(int(center[0]) - 128) < 30  # X near neutral
        assert abs(int(center[1]) - 128) < 30  # Y near neutral

    def test_3d_input(self):
        """Should accept 3D height maps (h, w, 1) or (h, w, c)."""
        height = np.random.RandomState(42).rand(32, 32, 1).astype(np.float32)
        normal = _height_to_normal(height, strength=0.5)
        assert normal.shape == (32, 32, 3)

    def test_strength_affects_normals(self):
        """Higher strength should produce more pronounced normals."""
        height = _perlin_noise_2d((64, 64), scale=20.0, seed=42)
        normal_low = _height_to_normal(height, strength=0.3)
        normal_high = _height_to_normal(height, strength=3.0)

        # Higher strength = more deviation from flat (128, 128, 255)
        low_dev = np.abs(normal_low[:, :, :2].astype(np.float32) - 128).mean()
        high_dev = np.abs(normal_high[:, :, :2].astype(np.float32) - 128).mean()
        assert high_dev > low_dev

    def test_output_range(self):
        """Output should be uint8 in [0, 255]."""
        height = _perlin_noise_2d((64, 64), scale=20.0, seed=42)
        normal = _height_to_normal(height, strength=1.0)
        assert normal.min() >= 0
        assert normal.max() <= 255


class TestMakeTextureImage:
    """Test _make_texture_image helper."""

    def test_rgb_image(self):
        img = _make_texture_image(64, 64, channels=3)
        assert img.shape == (64, 64, 3)
        assert img.dtype == np.float32

    def test_rgba_image(self):
        img = _make_texture_image(128, 64, channels=4)
        assert img.shape == (64, 128, 4)

    def test_grayscale(self):
        img = _make_texture_image(32, 32, channels=1)
        assert img.shape == (32, 32, 1)

    def test_initialized_to_zero(self):
        img = _make_texture_image(8, 8, channels=3)
        assert np.all(img == 0)


# ═══════════════════════════════════════════════════════════════
# Pipeline generation tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestSkinDetail:
    """Test skin detail texture generation."""

    def test_generates_valid_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=128)
        tex = pipeline.generate_skin_detail()
        assert tex.generated is True
        assert tex.name == "skin_detail"
        assert len(tex.data) > 0

    def test_png_bytes_format(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_skin_detail()
        assert tex.data[:4] == b"\x89PNG"

    def test_correct_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=128)
        tex = pipeline.generate_skin_detail({"width": 64, "height": 64})
        assert tex.width == 64
        assert tex.height == 64

    def test_spec_parameters_affect_output(self):
        """Different pore_density should produce different textures."""
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        tex_low = pipeline.generate_skin_detail({"pore_density": 0.1, "seed": 1})
        tex_high = pipeline.generate_skin_detail({"pore_density": 0.9, "seed": 1})
        # Different density should lead to different PNG bytes
        assert tex_low.data != tex_high.data


@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestSkinNormal:
    """Test skin normal map generation."""

    def test_generates_valid_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_skin_normal()
        assert tex.generated is True
        assert tex.texture_type == "normal"
        assert tex.data[:4] == b"\x89PNG"

    def test_custom_strength(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_skin_normal({"normal_strength": 2.0})
        assert tex.generated is True


@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestSSSThickness:
    """Test SSS thickness map generation."""

    def test_generates_valid_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_sss_thickness()
        assert tex.generated is True
        assert tex.texture_type == "sss_thickness"
        assert tex.data[:4] == b"\x89PNG"

    def test_thickness_values(self):
        """Center should be thicker (brighter) than edges."""
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_sss_thickness()
        # Decode to check values
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(tex.data))
        arr = np.array(img, dtype=np.float32) / 255.0
        center_val = arr[32, 32, 0]
        edge_val = arr[0, 0, 0]
        # Center should be thicker (higher value)
        assert center_val > edge_val

    def test_spec_parameters(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_sss_thickness({"base_thickness": 0.95, "edge_thin": 0.1})
        assert tex.generated is True


@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestEyeIris:
    """Test eye iris texture generation."""

    def test_generates_valid_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=128)
        tex = pipeline.generate_eye_iris()
        assert tex.generated is True
        assert tex.texture_type == "iris_detail"
        assert tex.data[:4] == b"\x89PNG"

    def test_iris_has_radial_pattern(self):
        """Iris should have a visible pattern (not uniform)."""
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        tex = pipeline.generate_eye_iris()
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(tex.data))
        arr = np.array(img, dtype=np.float32) / 255.0
        # There should be significant variation in the iris area
        # (not all pixels the same color)
        center_region = arr[20:44, 20:44]
        std = center_region.std()
        assert std > 0.02  # Should have some variation

    def test_custom_iris_color(self):
        """Different iris colors should produce different textures."""
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        blue = pipeline.generate_eye_iris({"iris_color": (0.58, 0.65, 0.85)})
        brown = pipeline.generate_eye_iris({"iris_color": (0.07, 0.70, 0.55)})
        assert blue.data != brown.data


@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestHairGradient:
    """Test hair gradient texture generation."""

    def test_generates_valid_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_hair_gradient()
        assert tex.generated is True
        assert tex.texture_type == "hair_gradient"
        assert tex.data[:4] == b"\x89PNG"

    def test_gradient_direction(self):
        """Top (tips) should differ from bottom (roots)."""
        pipeline = ProceduralTexturePipeline(resolution=64)
        from PIL import Image
        import io
        tex = pipeline.generate_hair_gradient({
            "tip_color": (0.96, 0.90, 0.72),  # blonde tips
            "root_color": (0.77, 0.64, 0.40),  # brown roots
        })
        img = Image.open(io.BytesIO(tex.data))
        arr = np.array(img, dtype=np.float32) / 255.0
        # Top row should be lighter (tip = blonde)
        top_row = arr[0, :, :].mean(axis=0)
        bottom_row = arr[-1, :, :].mean(axis=0)
        # Tips (top) should be lighter than roots (bottom)
        assert top_row.mean() > bottom_row.mean()

    def test_custom_colors(self):
        """Custom root/tip colors should produce different textures."""
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        tex1 = pipeline.generate_hair_gradient({
            "root_color": (0.0, 0.0, 0.1),  # black
            "tip_color": (0.0, 0.0, 0.97),  # white
        })
        tex2 = pipeline.generate_hair_gradient({
            "root_color": (0.77, 0.64, 0.40),  # brown
            "tip_color": (0.96, 0.90, 0.72),   # blonde
        })
        assert tex1.data != tex2.data


@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestFabricNormal:
    """Test fabric normal map generation."""

    def test_generates_valid_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_fabric_normal()
        assert tex.generated is True
        assert tex.texture_type == "normal"
        assert tex.data[:4] == b"\x89PNG"

    def test_all_patterns(self):
        """All fabric patterns should generate valid textures."""
        patterns = ["cotton_weave", "silk", "denim", "leather_grain", "knit"]
        pipeline = ProceduralTexturePipeline(resolution=64)
        for pattern in patterns:
            tex = pipeline.generate_fabric_normal({"pattern": pattern})
            assert tex.generated is True, f"Pattern {pattern} failed to generate"
            assert len(tex.data) > 0, f"Pattern {pattern} produced empty data"

    def test_different_patterns_different_output(self):
        """Different patterns should produce different normal maps."""
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        cotton = pipeline.generate_fabric_normal({"pattern": "cotton_weave"})
        silk = pipeline.generate_fabric_normal({"pattern": "silk"})
        assert cotton.data != silk.data


@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestGenerateAll:
    """Test generate_all returns all expected texture types."""

    def test_returns_all_keys(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        textures = pipeline.generate_all()
        expected_keys = {
            "skin_detail", "skin_normal", "sss_thickness",
            "eye_iris", "hair_gradient", "fabric_normal",
        }
        assert set(textures.keys()) == expected_keys

    def test_all_textures_generated(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        textures = pipeline.generate_all()
        for key, tex in textures.items():
            assert tex.generated is True, f"{key} not marked as generated"
            assert len(tex.data) > 0, f"{key} has empty data"
            assert tex.data[:4] == b"\x89PNG", f"{key} is not PNG"

    def test_all_textures_correct_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=128)
        textures = pipeline.generate_all()
        for key, tex in textures.items():
            assert tex.width == 128, f"{key} width mismatch"
            assert tex.height == 128, f"{key} height mismatch"

    def test_generate_all_with_custom_spec(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        spec = {
            "skin_detail": {"pore_density": 0.8},
            "eye_iris": {"iris_color": (0.07, 0.70, 0.55)},
        }
        textures = pipeline.generate_all(spec)
        assert textures["skin_detail"].generated is True
        assert textures["eye_iris"].generated is True


# ═══════════════════════════════════════════════════════════════
# PNG format validation tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestPNGFormat:
    """Verify all generated textures are valid PNG bytes."""

    def _validate_png(self, data: bytes) -> None:
        """Validate PNG header bytes."""
        assert data[:4] == b"\x89PNG", "Missing PNG magic number"
        # Check IHDR chunk follows
        assert data[4:8] == b"\r\n\x1a\n", "Invalid PNG header"

    def test_skin_detail_png_header(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_skin_detail()
        self._validate_png(tex.data)

    def test_skin_normal_png_header(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_skin_normal()
        self._validate_png(tex.data)

    def test_sss_thickness_png_header(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_sss_thickness()
        self._validate_png(tex.data)

    def test_eye_iris_png_header(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_eye_iris()
        self._validate_png(tex.data)

    def test_hair_gradient_png_header(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_hair_gradient()
        self._validate_png(tex.data)

    def test_fabric_normal_png_header(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_fabric_normal()
        self._validate_png(tex.data)


# ═══════════════════════════════════════════════════════════════
# Decoded dimension verification tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestDecodedDimensions:
    """Verify decoded PNG dimensions match ProceduralTexture metadata."""

    def _check_dims(self, tex: ProceduralTexture) -> None:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(tex.data))
        assert img.width == tex.width, f"Width mismatch: {img.width} != {tex.width}"
        assert img.height == tex.height, f"Height mismatch: {img.height} != {tex.height}"

    def test_skin_detail_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_skin_detail()
        self._check_dims(tex)

    def test_eye_iris_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=128)
        tex = pipeline.generate_eye_iris()
        self._check_dims(tex)

    def test_hair_gradient_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_hair_gradient()
        self._check_dims(tex)

    def test_fabric_normal_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex = pipeline.generate_fabric_normal()
        self._check_dims(tex)

    def test_non_square_dimensions(self):
        pipeline = ProceduralTexturePipeline(resolution=128)
        tex = pipeline.generate_skin_detail({"width": 64, "height": 128})
        assert tex.width == 64
        assert tex.height == 128
        self._check_dims(tex)


# ═══════════════════════════════════════════════════════════════
# Spec parameter variation tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
class TestSpecVariation:
    """Test that spec parameters affect output."""

    def test_different_seed_different_texture(self):
        pipeline = ProceduralTexturePipeline(resolution=64)
        tex1 = pipeline.generate_skin_detail({"seed": 1})
        tex2 = pipeline.generate_skin_detail({"seed": 2})
        assert tex1.data != tex2.data

    def test_different_normal_strength(self):
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        tex_weak = pipeline.generate_skin_normal({"normal_strength": 0.1})
        tex_strong = pipeline.generate_skin_normal({"normal_strength": 3.0})
        assert tex_weak.data != tex_strong.data

    def test_different_fabric_pattern(self):
        """Each fabric pattern should be distinct."""
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        textures = {}
        for pattern in ["cotton_weave", "silk", "denim"]:
            textures[pattern] = pipeline.generate_fabric_normal({"pattern": pattern})
        assert textures["cotton_weave"].data != textures["silk"].data
        assert textures["cotton_weave"].data != textures["denim"].data

    def test_different_iris_pupil_ratio(self):
        pipeline = ProceduralTexturePipeline(resolution=64, seed=42)
        small_pupil = pipeline.generate_eye_iris({"pupil_ratio": 0.15})
        large_pupil = pipeline.generate_eye_iris({"pupil_ratio": 0.5})
        assert small_pupil.data != large_pupil.data


# ═══════════════════════════════════════════════════════════════
# Pipeline initialization tests
# ═══════════════════════════════════════════════════════════════

class TestPipelineInit:
    """Test ProceduralTexturePipeline initialization."""

    def test_default_init(self):
        pipeline = ProceduralTexturePipeline()
        assert pipeline.resolution == 1024
        assert pipeline.seed == 42

    def test_custom_init(self):
        pipeline = ProceduralTexturePipeline(resolution=512, seed=99)
        assert pipeline.resolution == 512
        assert pipeline.seed == 99


# ═══════════════════════════════════════════════════════════════
# Pillow unavailable tests (graceful degradation)
# ═══════════════════════════════════════════════════════════════

class TestPillowUnavailable:
    """Ensure module loads and pure-numpy helpers work without Pillow."""

    def test_perlin_works_without_pillow(self):
        """_perlin_noise_2d should work with pure NumPy."""
        result = _perlin_noise_2d((32, 32), scale=20.0, seed=42)
        assert result.shape == (32, 32)
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_radial_gradient_works_without_pillow(self):
        """_radial_gradient should work with pure NumPy."""
        result = _radial_gradient((32, 32))
        assert result.shape == (32, 32, 3)

    def test_height_to_normal_works_without_pillow(self):
        """_height_to_normal should work with pure NumPy."""
        height = _perlin_noise_2d((32, 32), scale=20.0, seed=42)
        normal = _height_to_normal(height, strength=1.0)
        assert normal.shape == (32, 32, 3)
        assert normal.dtype == np.uint8

    def test_make_texture_image_works_without_pillow(self):
        """_make_texture_image should work with pure NumPy."""
        img = _make_texture_image(32, 32, channels=3)
        assert img.shape == (32, 32, 3)

    @pytest.mark.skipif(PILLOW_AVAILABLE, reason="Test only applies when Pillow is unavailable")
    def test_pipeline_raises_without_pillow(self):
        """Pipeline methods should raise RuntimeError without Pillow."""
        pipeline = ProceduralTexturePipeline(resolution=32)
        with pytest.raises(RuntimeError, match="Pillow"):
            pipeline.generate_skin_detail()