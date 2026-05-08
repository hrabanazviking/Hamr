"""
Tests for the Anime Materials system — Phase 12, Task T4.

Pure-Python tests run without Blender. Blender-dependent tests are marked
with @pytest.mark.blender and skipped if bpy is unavailable.
"""

from __future__ import annotations

import colorsys
import math
import pytest

# ── Import guard ──
# The pure-Python parts must work without bpy

from hamr.materials.anime import (
    AnimeMaterialSpec,
    ANIME_SKIN_PRESETS,
    ANIME_EYE_PRESETS,
    ANIME_HAIR_PRESETS,
    EMBLEMATIC_COLORS,
    hsv_to_rgb,
    rgb_to_hex,
    hsv_to_hex,
    blend_colors,
    compute_material_summary,
    validate_material_spec,
)


# ═══════════════════════════════════════════════════════════════
# Preset Dict Tests
# ═══════════════════════════════════════════════════════════════

class TestSkinPresets:
    """ANIME_SKIN_PRESETS has required keys and valid HSV values."""

    REQUIRED_KEYS = {"light", "medium", "dark", "tan", "pale"}

    def test_has_all_required_keys(self):
        for key in self.REQUIRED_KEYS:
            assert key in ANIME_SKIN_PRESETS, f"Missing skin preset: '{key}'"

    def test_all_presets_are_skin_type(self):
        for name, spec in ANIME_SKIN_PRESETS.items():
            assert spec.material_type == "skin", (
                f"Skin preset '{name}' has material_type='{spec.material_type}', expected 'skin'"
            )

    def test_skin_presets_have_subsurface(self):
        for name, spec in ANIME_SKIN_PRESETS.items():
            assert spec.subsurface is True, (
                f"Skin preset '{name}' should have subsurface=True"
            )

    def test_primary_hsv_in_range(self):
        for name, spec in ANIME_SKIN_PRESETS.items():
            h, s, v = spec.primary_hsv
            assert 0.0 <= h <= 1.0, f"Skin preset '{name}' hue {h} out of [0,1]"
            assert 0.0 <= s <= 1.0, f"Skin preset '{name}' sat {s} out of [0,1]"
            assert 0.0 <= v <= 1.0, f"Skin preset '{name}' val {v} out of [0,1]"

    def test_skin_roughness_reasonable(self):
        for name, spec in ANIME_SKIN_PRESETS.items():
            assert 0.3 <= spec.roughness <= 0.7, (
                f"Skin preset '{name}' roughness {spec.roughness} outside reasonable range"
            )


class TestEyePresets:
    """ANIME_EYE_PRESETS has required keys and valid HSV values."""

    REQUIRED_KEYS = {"brown", "blue", "green", "red", "violet", "gold"}

    def test_has_all_required_keys(self):
        for key in self.REQUIRED_KEYS:
            assert key in ANIME_EYE_PRESETS, f"Missing eye preset: '{key}'"

    def test_all_presets_are_eye_type(self):
        for name, spec in ANIME_EYE_PRESETS.items():
            assert spec.material_type == "eyes", (
                f"Eye preset '{name}' has material_type='{spec.material_type}'"
            )

    def test_primary_hsv_in_range(self):
        for name, spec in ANIME_EYE_PRESETS.items():
            h, s, v = spec.primary_hsv
            assert 0.0 <= h <= 1.0, f"Eye preset '{name}' hue {h} out of [0,1]"
            assert 0.0 <= s <= 1.0, f"Eye preset '{name}' sat {s} out of [0,1]"
            assert 0.0 <= v <= 1.0, f"Eye preset '{name}' val {v} out of [0,1]"

    def test_red_violet_gold_have_emission(self):
        """Eyes that glow (red, violet, gold) should have emission_hsv."""
        for name in ("red", "violet", "gold"):
            spec = ANIME_EYE_PRESETS[name]
            assert spec.emission_hsv is not None, (
                f"Eye preset '{name}' should have emission_hsv for glow effect"
            )

    def test_eye_roughness_low(self):
        """Eyes should have low roughness for glassy appearance."""
        for name, spec in ANIME_EYE_PRESETS.items():
            assert spec.roughness < 0.25, (
                f"Eye preset '{name}' roughness {spec.roughness} too high for eyes"
            )


class TestHairPresets:
    """ANIME_HAIR_PRESETS has required keys and valid HSV values."""

    REQUIRED_KEYS = {"black", "brown", "blonde", "red", "silver", "blue", "pink", "white"}

    def test_has_all_required_keys(self):
        for key in self.REQUIRED_KEYS:
            assert key in ANIME_HAIR_PRESETS, f"Missing hair preset: '{key}'"

    def test_all_presets_are_hair_type(self):
        for name, spec in ANIME_HAIR_PRESETS.items():
            assert spec.material_type == "hair", (
                f"Hair preset '{name}' has material_type='{spec.material_type}'"
            )

    def test_hair_presets_have_anisotropic(self):
        for name, spec in ANIME_HAIR_PRESETS.items():
            assert spec.anisotropic is True, (
                f"Hair preset '{name}' should have anisotropic=True"
            )

    def test_primary_hsv_in_range(self):
        for name, spec in ANIME_HAIR_PRESETS.items():
            h, s, v = spec.primary_hsv
            assert 0.0 <= h <= 1.0, f"Hair preset '{name}' hue {h} out of [0,1]"
            assert 0.0 <= s <= 1.0, f"Hair preset '{name}' sat {s} out of [0,1]"
            assert 0.0 <= v <= 1.0, f"Hair preset '{name}' val {v} out of [0,1]"


class TestEmblematicColors:
    """EMBLEMATIC_COLORS dict has valid HSV tuples."""

    def test_all_values_are_tuples_of_three(self):
        for name, hsv in EMBLEMATIC_COLORS.items():
            assert isinstance(hsv, tuple), f"Color '{name}' is not a tuple"
            assert len(hsv) == 3, f"Color '{name}' should have 3 values, got {len(hsv)}"

    def test_all_hsv_in_range(self):
        for name, hsv in EMBLEMATIC_COLORS.items():
            h, s, v = hsv
            assert 0.0 <= h <= 1.0, f"Color '{name}' hue {h} out of [0,1]"
            assert 0.0 <= s <= 1.0, f"Color '{name}' sat {s} out of [0,1]"
            assert 0.0 <= v <= 1.0, f"Color '{name}' val {v} out of [0,1]"

    def test_preset_colors_reference_emblematic(self):
        """All preset HSV values should exist in EMBLEMATIC_COLORS."""
        for preset_name, spec in ANIME_SKIN_PRESETS.items():
            assert spec.primary_hsv in EMBLEMATIC_COLORS.values(), (
                f"Skin preset '{preset_name}' primary_hsv not in EMBLEMATIC_COLORS"
            )


# ═══════════════════════════════════════════════════════════════
# AnimeMaterialSpec Dataclass Tests
# ═══════════════════════════════════════════════════════════════

class TestAnimeMaterialSpec:
    """Test AnimeMaterialSpec creation, defaults, and serialization."""

    def test_default_creation(self):
        spec = AnimeMaterialSpec()
        assert spec.material_type == "skin"
        assert spec.primary_hsv == (0.07, 0.35, 0.88)
        assert spec.secondary_hsv == (0.0, 0.0, 0.0)
        assert spec.detail_level == "medium"
        assert spec.subsurface is False
        assert spec.anisotropic is False
        assert spec.metallic == 0.0
        assert spec.roughness == 0.5
        assert spec.alpha == 1.0
        assert spec.emission_hsv is None

    def test_custom_creation(self):
        spec = AnimeMaterialSpec(
            material_type="hair",
            primary_hsv=(0.60, 0.65, 0.75),
            secondary_hsv=(0.62, 0.70, 0.45),
            detail_level="high",
            anisotropic=True,
            roughness=0.40,
        )
        assert spec.material_type == "hair"
        assert spec.anisotropic is True
        assert spec.roughness == 0.40

    def test_to_dict(self):
        spec = AnimeMaterialSpec(material_type="skin", roughness=0.45)
        d = spec.to_dict()
        assert isinstance(d, dict)
        assert d["material_type"] == "skin"
        assert d["roughness"] == 0.45

    def test_from_dict(self):
        data = {
            "material_type": "eyes",
            "primary_hsv": [0.58, 0.65, 0.85],
            "roughness": 0.15,
        }
        spec = AnimeMaterialSpec.from_dict(data)
        assert spec.material_type == "eyes"
        assert spec.primary_hsv == (0.58, 0.65, 0.85)
        assert spec.roughness == 0.15

    def test_from_dict_with_emission(self):
        data = {
            "material_type": "eyes",
            "emission_hsv": [0.98, 0.75, 0.70],
        }
        spec = AnimeMaterialSpec.from_dict(data)
        assert spec.emission_hsv == (0.98, 0.75, 0.70)

    def test_from_dict_ignores_unknown_keys(self):
        data = {
            "material_type": "skin",
            "unknown_key": "should_be_ignored",
        }
        spec = AnimeMaterialSpec.from_dict(data)
        assert spec.material_type == "skin"
        assert not hasattr(spec, "unknown_key")

    def test_roundtrip(self):
        """Serialize → deserialize should produce equivalent spec."""
        original = ANIME_SKIN_PRESETS["medium"]
        d = original.to_dict()
        restored = AnimeMaterialSpec.from_dict(d)
        assert restored.material_type == original.material_type
        assert restored.primary_hsv == original.primary_hsv
        assert restored.secondary_hsv == original.secondary_hsv
        assert restored.roughness == original.roughness
        assert restored.subsurface == original.subsurface


# ═══════════════════════════════════════════════════════════════
# Color Conversion Tests
# ═══════════════════════════════════════════════════════════════

class TestHsvToRgb:
    """Test hsv_to_rgb conversion."""

    def test_black(self):
        r, g, b = hsv_to_rgb(0.0, 0.0, 0.0)
        assert r == 0.0 and g == 0.0 and b == 0.0

    def test_white(self):
        r, g, b = hsv_to_rgb(0.0, 0.0, 1.0)
        assert abs(r - 1.0) < 1e-6
        assert abs(g - 1.0) < 1e-6
        assert abs(b - 1.0) < 1e-6

    def test_pure_red(self):
        r, g, b = hsv_to_rgb(0.0, 1.0, 1.0)
        assert abs(r - 1.0) < 1e-6
        assert abs(g) < 1e-6
        assert abs(b) < 1e-6

    def test_pure_green(self):
        r, g, b = hsv_to_rgb(1/3, 1.0, 1.0)
        assert abs(r) < 1e-6
        assert abs(g - 1.0) < 1e-6
        assert abs(b) < 1e-6

    def test_pure_blue(self):
        r, g, b = hsv_to_rgb(2/3, 1.0, 1.0)
        assert abs(r) < 1e-6
        assert abs(g) < 1e-6
        assert abs(b - 1.0) < 1e-6

    def test_hue_wraps(self):
        """Hue > 1.0 should wrap around correctly."""
        r1, g1, b1 = hsv_to_rgb(0.0, 1.0, 1.0)
        r2, g2, b2 = hsv_to_rgb(1.0, 1.0, 1.0)
        assert abs(r1 - r2) < 1e-6
        assert abs(g1 - g2) < 1e-6
        assert abs(b1 - b2) < 1e-6

    def test_clamps_saturation(self):
        """Saturation > 1 should be clamped."""
        r, g, b = hsv_to_rgb(0.5, 2.0, 1.0)
        # Should not crash; saturation clamped to 1.0
        assert isinstance(r, float)
        assert 0.0 <= r <= 1.0

    def test_clamps_value(self):
        """Value > 1 should be clamped."""
        r, g, b = hsv_to_rgb(0.5, 0.5, 5.0)
        assert isinstance(r, float)

    def test_mid_tone(self):
        """A known mid-tone conversion."""
        # colorsys.hsv_to_rgb(0.07, 0.35, 0.88) should match
        expected = colorsys.hsv_to_rgb(0.07, 0.35, 0.88)
        result = hsv_to_rgb(0.07, 0.35, 0.88)
        assert abs(result[0] - expected[0]) < 1e-6
        assert abs(result[1] - expected[1]) < 1e-6
        assert abs(result[2] - expected[2]) < 1e-6


class TestRgbToHex:
    """Test rgb_to_hex conversion."""

    def test_white(self):
        assert rgb_to_hex(1.0, 1.0, 1.0) == "#ffffff"

    def test_black(self):
        assert rgb_to_hex(0.0, 0.0, 0.0) == "#000000"

    def test_red(self):
        assert rgb_to_hex(1.0, 0.0, 0.0) == "#ff0000"

    def test_green(self):
        assert rgb_to_hex(0.0, 1.0, 0.0) == "#00ff00"

    def test_blue(self):
        assert rgb_to_hex(0.0, 0.0, 1.0) == "#0000ff"

    def test_clamps_out_of_range(self):
        """Values > 1 should be clamped to ff."""
        assert rgb_to_hex(2.0, 1.0, 1.0) == "#ffffff"

    def test_clamps_negative(self):
        """Negative values should be clamped to 00."""
        assert rgb_to_hex(-1.0, 0.0, 0.0) == "#000000"

    def test_known_color(self):
        """Test a specific known color conversion."""
        # (0.91, 0.72, 0.48) should give approximately #e8b87a
        result = rgb_to_hex(0.91, 0.72, 0.48)
        assert result.startswith("#")
        assert len(result) == 7  # #RRGGBB


class TestHsvToHex:
    """Test hsv_to_hex convenience function."""

    def test_black(self):
        assert hsv_to_hex(0.0, 0.0, 0.0) == "#000000"

    def test_white(self):
        assert hsv_to_hex(0.0, 0.0, 1.0) == "#ffffff"

    def test_red(self):
        result = hsv_to_hex(0.0, 1.0, 1.0)
        assert result == "#ff0000"

    def test_matches_hsv_to_rgb_plus_rgb_to_hex(self):
        """Direct hsv_to_hex should match the two-step conversion."""
        h, s, v = 0.07, 0.35, 0.88
        r, g, b = hsv_to_rgb(h, s, v)
        expected = rgb_to_hex(r, g, b)
        actual = hsv_to_hex(h, s, v)
        assert expected == actual


# ═══════════════════════════════════════════════════════════════
# blend_colors Tests
# ═══════════════════════════════════════════════════════════════

class TestBlendColors:
    """Test blend_colors linear interpolation."""

    def test_factor_zero_returns_first(self):
        """Blend factor 0.0 should return the first color."""
        c1 = (0.5, 0.8, 0.9)
        c2 = (0.1, 0.2, 0.3)
        result = blend_colors(c1, c2, 0.0)
        assert abs(result[0] - 0.5) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6
        assert abs(result[2] - 0.9) < 1e-6

    def test_factor_one_returns_second(self):
        """Blend factor 1.0 should return the second color."""
        c1 = (0.5, 0.8, 0.9)
        c2 = (0.1, 0.2, 0.3)
        result = blend_colors(c1, c2, 1.0)
        assert abs(result[0] - 0.1) < 1e-6
        assert abs(result[1] - 0.2) < 1e-6
        assert abs(result[2] - 0.3) < 1e-6

    def test_factor_half_is_midpoint(self):
        """Blend factor 0.5 should produce midpoint."""
        # Use non-zero saturation/value so the midpoint is clear
        c1 = (0.0, 0.2, 0.4)
        c2 = (1.0, 0.8, 0.6)
        result = blend_colors(c1, c2, 0.5)
        # Hue wraps: 0.0 and 1.0 are the same, midpoint stays ~0.0
        # Saturation and value blend linearly
        assert abs(result[1] - 0.5) < 1e-6
        assert abs(result[2] - 0.5) < 1e-6

    def test_hue_wrapping_short_arc_forward(self):
        """Hue should wrap through shortest arc: 0.9 → 0.1 goes through 0.0."""
        c1 = (0.9, 1.0, 1.0)  # near-red
        c2 = (0.1, 1.0, 1.0)  # orange
        result = blend_colors(c1, c2, 0.5)
        # Should go 0.9 → 0.0/1.0 → 0.1, midpoint around 0.0
        assert result[0] < 0.15 or result[0] > 0.85  # Near 0.0/1.0

    def test_hue_wrapping_short_arc_backward(self):
        """Hue should wrap through shortest arc: 0.1 → 0.9 goes through 0.0."""
        c1 = (0.1, 1.0, 1.0)  # orange
        c2 = (0.9, 1.0, 1.0)  # near-red
        result = blend_colors(c1, c2, 0.5)
        # Should go 0.1 → 0.0/1.0 → 0.9, midpoint around 0.0
        assert result[0] < 0.15 or result[0] > 0.85

    def test_saturation_blend(self):
        c1 = (0.5, 0.0, 0.5)
        c2 = (0.5, 1.0, 0.5)
        result = blend_colors(c1, c2, 0.5)
        assert abs(result[1] - 0.5) < 1e-6

    def test_value_blend(self):
        c1 = (0.5, 0.5, 0.0)
        c2 = (0.5, 0.5, 1.0)
        result = blend_colors(c1, c2, 0.5)
        assert abs(result[2] - 0.5) < 1e-6

    def test_clamps_factor_below_zero(self):
        """Factor < 0 should be clamped to 0, returning hsv1."""
        c1 = (0.25, 0.5, 0.8)
        c2 = (0.75, 1.0, 0.3)
        result = blend_colors(c1, c2, -0.5)
        # At factor=0, result should be hsv1
        assert abs(result[0] - 0.25) < 1e-6
        assert abs(result[1] - 0.5) < 1e-6
        assert abs(result[2] - 0.8) < 1e-6

    def test_clamps_factor_above_one(self):
        """Factor > 1 should be clamped to 1."""
        result = blend_colors((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 1.5)
        assert abs(result[1] - 1.0) < 1e-6


# ═══════════════════════════════════════════════════════════════
# compute_material_summary Tests
# ═══════════════════════════════════════════════════════════════

class TestComputeMaterialSummary:
    """Test compute_material_summary returns correct shader parameters."""

    def test_basic_skin_summary(self):
        spec = ANIME_SKIN_PRESETS["medium"]
        s = compute_material_summary(spec)
        assert s["material_type"] == "skin"
        assert s["roughness"] == 0.50
        assert s["metallic"] == 0.0
        assert s["alpha"] == 1.0
        assert s["has_emission"] is False
        assert s["subsurface_enabled"] is True
        assert s["subsurface_weight"] > 0.0
        assert s["anisotropic_enabled"] is False
        assert s["clearcoat"] == 0.0

    def test_eye_with_emission(self):
        spec = ANIME_EYE_PRESETS["red"]
        s = compute_material_summary(spec)
        assert s["material_type"] == "eyes"
        assert s["has_emission"] is True
        assert s["emission_hex"] is not None
        assert s["roughness"] < 0.25

    def test_eye_without_emission(self):
        spec = ANIME_EYE_PRESETS["brown"]
        s = compute_material_summary(spec)
        assert s["has_emission"] is False
        assert s["emission_hex"] is None

    def test_hair_anisotropic_params(self):
        spec = ANIME_HAIR_PRESETS["blonde"]
        s = compute_material_summary(spec)
        assert s["anisotropic_enabled"] is True
        assert s["clearcoat"] > 0.0
        assert s["sheen"] > 0.0

    def test_clothing_no_special_params(self):
        spec = AnimeMaterialSpec(
            material_type="clothing",
            primary_hsv=(0.63, 0.80, 0.25),
            roughness=0.65,
        )
        s = compute_material_summary(spec)
        assert s["material_type"] == "clothing"
        assert s["subsurface_enabled"] is False
        assert s["subsurface_weight"] == 0.0
        assert s["anisotropic_enabled"] is False
        assert s["clearcoat"] == 0.0

    def test_primary_hex_format(self):
        spec = ANIME_SKIN_PRESETS["light"]
        s = compute_material_summary(spec)
        assert s["primary_hex"].startswith("#")
        assert len(s["primary_hex"]) == 7  # #RRGGBB

    def test_detail_level_affects_sss_weight(self):
        spec_minimal = AnimeMaterialSpec(
            material_type="skin", subsurface=True, detail_level="minimal"
        )
        spec_medium = AnimeMaterialSpec(
            material_type="skin", subsurface=True, detail_level="medium"
        )
        spec_high = AnimeMaterialSpec(
            material_type="skin", subsurface=True, detail_level="high"
        )
        s_min = compute_material_summary(spec_minimal)
        s_med = compute_material_summary(spec_medium)
        s_hi = compute_material_summary(spec_high)
        assert s_min["subsurface_weight"] < s_med["subsurface_weight"]
        assert s_med["subsurface_weight"] < s_hi["subsurface_weight"]


# ═══════════════════════════════════════════════════════════════
# validate_material_spec Tests
# ═══════════════════════════════════════════════════════════════

class TestValidateMaterialSpec:
    """Test validate_material_spec catches invalid values."""

    def test_valid_spec_no_warnings(self):
        spec = ANIME_SKIN_PRESETS["medium"]
        warnings = validate_material_spec(spec)
        assert len(warnings) == 0, f"Unexpected warnings: {warnings}"

    def test_invalid_material_type(self):
        spec = AnimeMaterialSpec(material_type="metal")
        warnings = validate_material_spec(spec)
        assert any("material_type" in w for w in warnings)

    def test_invalid_detail_level(self):
        spec = AnimeMaterialSpec(detail_level="ultra")
        warnings = validate_material_spec(spec)
        assert any("detail_level" in w for w in warnings)

    def test_negative_roughness(self):
        spec = AnimeMaterialSpec(roughness=-0.5)
        warnings = validate_material_spec(spec)
        assert any("Roughness" in w and "negative" in w for w in warnings)

    def test_roughness_exceeds_one(self):
        spec = AnimeMaterialSpec(roughness=1.5)
        warnings = validate_material_spec(spec)
        assert any("Roughness" in w and "exceeds" in w for w in warnings)

    def test_negative_metallic(self):
        spec = AnimeMaterialSpec(metallic=-0.5)
        warnings = validate_material_spec(spec)
        assert any("Metallic" in w and "negative" in w for w in warnings)

    def test_metallic_exceeds_one(self):
        spec = AnimeMaterialSpec(metallic=2.0)
        warnings = validate_material_spec(spec)
        assert any("Metallic" in w and "exceeds" in w for w in warnings)

    def test_negative_alpha(self):
        spec = AnimeMaterialSpec(alpha=-0.1)
        warnings = validate_material_spec(spec)
        assert any("Alpha" in w and "negative" in w for w in warnings)

    def test_alpha_exceeds_one(self):
        spec = AnimeMaterialSpec(alpha=1.5)
        warnings = validate_material_spec(spec)
        assert any("Alpha" in w and "exceeds" in w for w in warnings)

    def test_subsurface_on_non_skin_warns(self):
        spec = AnimeMaterialSpec(material_type="clothing", subsurface=True)
        warnings = validate_material_spec(spec)
        assert any("Subsurface" in w and "skin" in w for w in warnings)

    def test_anisotropic_on_non_hair_warns(self):
        spec = AnimeMaterialSpec(material_type="eyes", anisotropic=True)
        warnings = validate_material_spec(spec)
        assert any("Anisotropic" in w and "hair" in w for w in warnings)

    def test_high_metallic_on_skin_warns(self):
        spec = AnimeMaterialSpec(material_type="skin", metallic=0.7)
        warnings = validate_material_spec(spec)
        assert any("Metallic" in w and "skin" in w for w in warnings)

    def test_zero_primary_hsv_warns(self):
        spec = AnimeMaterialSpec(material_type="skin", primary_hsv=(0.0, 0.0, 0.0))
        warnings = validate_material_spec(spec)
        assert any("pure black" in w for w in warnings)

    def test_zero_primary_hsv_hair_not_warned(self):
        spec = AnimeMaterialSpec(material_type="hair", primary_hsv=(0.0, 0.0, 0.0))
        warnings = validate_material_spec(spec)
        assert not any("pure black" in w for w in warnings)

    def test_emission_hsv_out_of_range(self):
        spec = AnimeMaterialSpec(emission_hsv=(1.5, 2.0, -0.1))
        warnings = validate_material_spec(spec)
        assert any("Emission" in w for w in warnings)

    def test_primary_hsv_out_of_range(self):
        spec = AnimeMaterialSpec(primary_hsv=(1.5, -0.5, 2.0))
        warnings = validate_material_spec(spec)
        assert any("Primary" in w for w in warnings)

    def test_secondary_hsv_out_of_range(self):
        spec = AnimeMaterialSpec(secondary_hsv=(1.5, -0.1, 2.0))
        warnings = validate_material_spec(spec)
        assert any("Secondary" in w for w in warnings)


# ═══════════════════════════════════════════════════════════════
# AnimeMaterialGenerator Blender-dependent Tests
# ═══════════════════════════════════════════════════════════════

class TestAnimeMaterialGeneratorNoBpy:
    """Test that AnimeMaterialGenerator raises RuntimeError without bpy."""

    def test_generate_raises_without_bpy(self):
        from hamr.materials.anime import AnimeMaterialGenerator
        gen = AnimeMaterialGenerator()
        spec = ANIME_SKIN_PRESETS["light"]
        with pytest.raises(RuntimeError, match="bpy is not available"):
            gen.generate(spec, "body_mesh")

    def test_create_skin_material_raises_without_bpy(self):
        from hamr.materials.anime import AnimeMaterialGenerator
        gen = AnimeMaterialGenerator()
        spec = ANIME_SKIN_PRESETS["light"]
        with pytest.raises(RuntimeError, match="bpy is not available"):
            gen.create_skin_material(spec, "body_mesh")

    def test_create_eye_material_raises_without_bpy(self):
        from hamr.materials.anime import AnimeMaterialGenerator
        gen = AnimeMaterialGenerator()
        spec = ANIME_EYE_PRESETS["blue"]
        with pytest.raises(RuntimeError, match="bpy is not available"):
            gen.create_eye_material(spec, "eye_mesh")

    def test_create_hair_material_raises_without_bpy(self):
        from hamr.materials.anime import AnimeMaterialGenerator
        gen = AnimeMaterialGenerator()
        spec = ANIME_HAIR_PRESETS["blonde"]
        with pytest.raises(RuntimeError, match="bpy is not available"):
            gen.create_hair_material(spec, "hair_mesh")

    def test_create_clothing_material_raises_without_bpy(self):
        from hamr.materials.anime import AnimeMaterialGenerator
        gen = AnimeMaterialGenerator()
        spec = AnimeMaterialSpec(
            material_type="clothing",
            primary_hsv=(0.63, 0.80, 0.25),
            roughness=0.65,
        )
        with pytest.raises(RuntimeError, match="bpy is not available"):
            gen.create_clothing_material(spec, "shirt_mesh")


# ═══════════════════════════════════════════════════════════════
# Integration: presets → summary → validation
# ═══════════════════════════════════════════════════════════════

class TestPresetIntegration:
    """Integration tests combining presets, summaries, and validation."""

    def test_all_skin_presets_produce_valid_summary(self):
        for name, spec in ANIME_SKIN_PRESETS.items():
            summary = compute_material_summary(spec)
            assert summary["material_type"] == "skin"
            assert summary["primary_hex"].startswith("#")
            assert summary["subsurface_enabled"] is True

    def test_all_eye_presets_produce_valid_summary(self):
        for name, spec in ANIME_EYE_PRESETS.items():
            summary = compute_material_summary(spec)
            assert summary["material_type"] == "eyes"
            assert summary["roughness"] < 0.25

    def test_all_hair_presets_produce_valid_summary(self):
        for name, spec in ANIME_HAIR_PRESETS.items():
            summary = compute_material_summary(spec)
            assert summary["material_type"] == "hair"
            assert summary["anisotropic_enabled"] is True
            assert summary["clearcoat"] > 0.0

    def test_all_presets_validate_clean(self):
        """All built-in presets should validate with no warnings."""
        all_presets = {**ANIME_SKIN_PRESETS, **ANIME_EYE_PRESETS, **ANIME_HAIR_PRESETS}
        for name, spec in all_presets.items():
            warnings = validate_material_spec(spec)
            assert len(warnings) == 0, (
                f"Preset '{name}' has validation warnings: {warnings}"
            )

    def test_summary_hex_colors_are_valid(self):
        """All hex colors in summaries should be well-formed #RRGGBB strings."""
        all_presets = {**ANIME_SKIN_PRESETS, **ANIME_EYE_PRESETS, **ANIME_HAIR_PRESETS}
        for name, spec in all_presets.items():
            summary = compute_material_summary(spec)
            assert summary["primary_hex"].startswith("#")
            assert len(summary["primary_hex"]) == 7
            # secondary_hex may be #000000 for presets without accent
            assert summary["secondary_hex"].startswith("#")
            assert len(summary["secondary_hex"]) == 7