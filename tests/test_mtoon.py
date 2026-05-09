"""
Tests for MToon Shader System — Phase 16, Task T1.

Pure-Python tests — no bpy dependency required.
"""

from __future__ import annotations

import pytest

from hamr.materials.mtoon import (
    MToonConfig,
    PRESET_MTOON_CONFIGS,
    validate_mtoon_config,
    mtoon_config_to_vrm_properties,
    mtoon_config_to_glTF_material,
    create_mtoon_preset,
    list_mtoon_presets,
    blend_mtoon_configs,
    VALID_RENDER_MODES,
    VALID_CULL_MODES,
)


# ═══════════════════════════════════════════════════════════════
# MToonConfig defaults
# ═══════════════════════════════════════════════════════════════

class TestMToonConfigDefaults:
    """Default MToonConfig values match the VRM spec."""

    def test_lit_color_default(self):
        cfg = MToonConfig()
        assert cfg.lit_color == (1.0, 1.0, 1.0)

    def test_shade_color_default(self):
        cfg = MToonConfig()
        assert cfg.shade_color == (0.8, 0.8, 0.8)

    def test_lit_shade_shift_default(self):
        cfg = MToonConfig()
        assert cfg.lit_shade_shift == 0.0

    def test_lit_shade_toony_default(self):
        cfg = MToonConfig()
        assert cfg.lit_shade_toony == 0.9

    def test_outline_width_default(self):
        cfg = MToonConfig()
        assert cfg.outline_width == 0.0

    def test_rim_lighting_mix_default(self):
        cfg = MToonConfig()
        assert cfg.rim_lighting_mix == 0.0

    def test_emission_intensity_default(self):
        cfg = MToonConfig()
        assert cfg.emission_intensity == 0.0

    def test_alpha_cutoff_default(self):
        cfg = MToonConfig()
        assert cfg.alpha_cutoff == 0.5

    def test_render_mode_default(self):
        cfg = MToonConfig()
        assert cfg.render_mode == "opaque"

    def test_cull_mode_default(self):
        cfg = MToonConfig()
        assert cfg.cull_mode == "back"

    def test_z_write_default(self):
        cfg = MToonConfig()
        assert cfg.z_write is True

    def test_z_test_default(self):
        cfg = MToonConfig()
        assert cfg.z_test is True

    def test_matcap_texture_default(self):
        cfg = MToonConfig()
        assert cfg.matcap_texture is None


# ═══════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════

class TestValidateMToonConfig:
    """validate_mtoon_config catches issues and accepts valid configs."""

    def test_valid_default_config(self):
        cfg = MToonConfig()
        issues = validate_mtoon_config(cfg)
        assert issues == [], f"Default config should be valid, got: {issues}"

    def test_shade_shift_out_of_range(self):
        cfg = MToonConfig(lit_shade_shift=1.5)
        issues = validate_mtoon_config(cfg)
        assert any("lit_shade_shift" in i for i in issues)

    def test_shade_shift_negative_out_of_range(self):
        cfg = MToonConfig(lit_shade_shift=-1.5)
        issues = validate_mtoon_config(cfg)
        assert any("lit_shade_shift" in i for i in issues)

    def test_toony_out_of_range(self):
        cfg = MToonConfig(lit_shade_toony=1.5)
        issues = validate_mtoon_config(cfg)
        assert any("lit_shade_toony" in i for i in issues)

    def test_toony_negative(self):
        cfg = MToonConfig(lit_shade_toony=-0.1)
        issues = validate_mtoon_config(cfg)
        assert any("lit_shade_toony" in i for i in issues)

    def test_emission_intensity_negative(self):
        cfg = MToonConfig(emission_intensity=-1.0)
        issues = validate_mtoon_config(cfg)
        assert any("emission_intensity" in i for i in issues)

    def test_alpha_cutoff_out_of_range(self):
        cfg = MToonConfig(alpha_cutoff=1.5)
        issues = validate_mtoon_config(cfg)
        assert any("alpha_cutoff" in i for i in issues)

    def test_alpha_cutoff_negative(self):
        cfg = MToonConfig(alpha_cutoff=-0.1)
        issues = validate_mtoon_config(cfg)
        assert any("alpha_cutoff" in i for i in issues)

    def test_render_mode_invalid(self):
        cfg = MToonConfig(render_mode="invalid_mode")
        issues = validate_mtoon_config(cfg)
        assert any("render_mode" in i for i in issues)

    def test_cull_mode_invalid(self):
        cfg = MToonConfig(cull_mode="invalid_mode")
        issues = validate_mtoon_config(cfg)
        assert any("cull_mode" in i for i in issues)

    def test_color_out_of_range(self):
        cfg = MToonConfig(lit_color=(1.5, 0.0, 0.0))
        issues = validate_mtoon_config(cfg)
        assert any("lit_color" in i for i in issues)

    def test_outline_width_negative(self):
        cfg = MToonConfig(outline_width=-0.1)
        issues = validate_mtoon_config(cfg)
        assert any("outline_width" in i for i in issues)

    def test_rim_lighting_mix_out_of_range(self):
        cfg = MToonConfig(rim_lighting_mix=1.5)
        issues = validate_mtoon_config(cfg)
        assert any("rim_lighting_mix" in i for i in issues)

    def test_rim_fresnel_power_negative(self):
        cfg = MToonConfig(rim_fresnel_power=-1.0)
        issues = validate_mtoon_config(cfg)
        assert any("rim_fresnel_power" in i for i in issues)

    def test_transparent_with_z_write_warning(self):
        """Transparent mode with z_write=True should produce a warning."""
        cfg = MToonConfig(render_mode="transparent", z_write=True)
        issues = validate_mtoon_config(cfg)
        assert any("z_write" in i for i in issues)

    def test_cutout_with_zero_alpha_cutoff_warning(self):
        """Cutout mode with alpha_cutoff=0 should produce a warning."""
        cfg = MToonConfig(render_mode="cutout", alpha_cutoff=0.0)
        issues = validate_mtoon_config(cfg)
        assert any("alpha_cutoff" in i for i in issues)

    def test_valid_boundary_values(self):
        """Edge values at exact boundaries should be valid."""
        cfg = MToonConfig(
            lit_shade_shift=-1.0,
            lit_shade_toony=1.0,
            alpha_cutoff=1.0,
            outline_width=0.0,
        )
        issues = validate_mtoon_config(cfg)
        # Only the edge-case semantic warnings — no range errors
        range_issues = [
            i for i in issues
            if "out of range" in i or "must be" in i
        ]
        assert range_issues == []


# ═══════════════════════════════════════════════════════════════
# VRM Properties Conversion
# ═══════════════════════════════════════════════════════════════

class TestMToonToVRMProperties:
    """mtoon_config_to_vrm_properties produces valid VRM extension dicts."""

    def test_produces_dict(self):
        cfg = MToonConfig()
        result = mtoon_config_to_vrm_properties(cfg)
        assert isinstance(result, dict)

    def test_has_spec_version(self):
        cfg = MToonConfig()
        result = mtoon_config_to_vrm_properties(cfg)
        assert "specVersion" in result
        assert result["specVersion"] == 1

    def test_has_color_section(self):
        cfg = MToonConfig()
        result = mtoon_config_to_vrm_properties(cfg)
        assert "color" in result
        assert "lit" in result["color"]
        assert "shade" in result["color"]

    def test_has_lit_shade_blending(self):
        cfg = MToonConfig()
        result = mtoon_config_to_vrm_properties(cfg)
        assert "litAndShadeBlending" in result
        assert result["litAndShadeBlending"]["shift"] == 0.0
        assert result["litAndShadeBlending"]["toony"] == 0.9

    def test_has_outline(self):
        cfg = MToonConfig(outline_width=0.05)
        result = mtoon_config_to_vrm_properties(cfg)
        assert "outline" in result
        assert result["outline"]["width"] == 0.05

    def test_has_rim(self):
        cfg = MToonConfig(rim_lighting_mix=0.2)
        result = mtoon_config_to_vrm_properties(cfg)
        assert "rim" in result
        assert result["rim"]["lightingMix"] == 0.2

    def test_has_emission(self):
        cfg = MToonConfig(emission_intensity=2.0)
        result = mtoon_config_to_vrm_properties(cfg)
        assert "emission" in result
        assert result["emission"]["intensity"] == 2.0

    def test_render_mode_mapping(self):
        for mode, expected in [("opaque", "Opaque"), ("cutout", "Cutout"), ("transparent", "Transparent")]:
            cfg = MToonConfig(render_mode=mode)
            result = mtoon_config_to_vrm_properties(cfg)
            assert result["renderMode"] == expected

    def test_cull_mode_mapping(self):
        for mode, expected in [("off", "Off"), ("front", "Front"), ("back", "Back")]:
            cfg = MToonConfig(cull_mode=mode)
            result = mtoon_config_to_vrm_properties(cfg)
            assert result["cullMode"] == expected

    def test_cutout_includes_alpha_cutoff(self):
        cfg = MToonConfig(render_mode="cutout", alpha_cutoff=0.7)
        result = mtoon_config_to_vrm_properties(cfg)
        assert "alphaCutoff" in result
        assert result["alphaCutoff"] == 0.7

    def test_opaque_no_alpha_cutoff_key(self):
        cfg = MToonConfig(render_mode="opaque")
        result = mtoon_config_to_vrm_properties(cfg)
        assert "alphaCutoff" not in result

    def test_uv_transform_when_non_identity(self):
        cfg = MToonConfig(uv_transform_scale=(2.0, 2.0), uv_transform_offset=(0.1, 0.2))
        result = mtoon_config_to_vrm_properties(cfg)
        assert "uvTransform" in result
        assert result["uvTransform"]["scale"] == [2.0, 2.0]
        assert result["uvTransform"]["offset"] == [0.1, 0.2]

    def test_uv_transform_omitted_when_identity(self):
        cfg = MToonConfig()
        result = mtoon_config_to_vrm_properties(cfg)
        assert "uvTransform" not in result

    def test_matcap_texture_present(self):
        cfg = MToonConfig(matcap_texture="matcap_metal.png")
        result = mtoon_config_to_vrm_properties(cfg)
        assert "matcap" in result
        assert result["matcap"]["texture"] == "matcap_metal.png"

    def test_matcap_texture_omitted_when_none(self):
        cfg = MToonConfig()
        result = mtoon_config_to_vrm_properties(cfg)
        assert "matcap" not in result


# ═══════════════════════════════════════════════════════════════
# glTF Material Conversion
# ═══════════════════════════════════════════════════════════════

class TestMToonToglTFMaterial:
    """mtoon_config_to_glTF_material produces valid glTF material dicts."""

    def test_produces_dict(self):
        cfg = MToonConfig()
        result = mtoon_config_to_glTF_material(cfg)
        assert isinstance(result, dict)

    def test_has_pbr_metallic_roughness(self):
        cfg = MToonConfig()
        result = mtoon_config_to_glTF_material(cfg)
        assert "pbrMetallicRoughness" in result
        pbr = result["pbrMetallicRoughness"]
        # baseColorFactor is lit_color + alpha
        assert pbr["baseColorFactor"][:3] == list(cfg.lit_color)
        assert pbr["baseColorFactor"][3] == 1.0
        # Metallic is 0 for anime
        assert pbr["metallicFactor"] == 0.0

    def test_alpha_mode_opaque(self):
        cfg = MToonConfig(render_mode="opaque")
        result = mtoon_config_to_glTF_material(cfg)
        assert result["alphaMode"] == "OPAQUE"

    def test_alpha_mode_cutout(self):
        cfg = MToonConfig(render_mode="cutout", alpha_cutoff=0.7)
        result = mtoon_config_to_glTF_material(cfg)
        assert result["alphaMode"] == "MASK"
        assert result["alphaCutoff"] == 0.7

    def test_alpha_mode_transparent(self):
        cfg = MToonConfig(render_mode="transparent")
        result = mtoon_config_to_glTF_material(cfg)
        assert result["alphaMode"] == "BLEND"

    def test_double_sided_when_cull_off(self):
        cfg = MToonConfig(cull_mode="off")
        result = mtoon_config_to_glTF_material(cfg)
        assert result["doubleSided"] is True

    def test_not_double_sided_when_cull_back(self):
        cfg = MToonConfig(cull_mode="back")
        result = mtoon_config_to_glTF_material(cfg)
        assert result["doubleSided"] is False

    def test_has_mtoon_extension(self):
        cfg = MToonConfig()
        result = mtoon_config_to_glTF_material(cfg)
        assert "extensions" in result
        assert "VRMC_materials_mtoon" in result["extensions"]

    def test_unlit_extension_for_fully_toony(self):
        """Materials with toony≈1, no rim, no emission, no outline get unlit hint."""
        cfg = MToonConfig(
            lit_shade_toony=1.0,
            rim_lighting_mix=0.0,
            emission_intensity=0.0,
            outline_width=0.0,
        )
        result = mtoon_config_to_glTF_material(cfg)
        assert "KHR_materials_unlit" in result["extensions"]

    def test_no_unlit_extension_with_rim(self):
        """Materials with rim lighting don't get unlit hint."""
        cfg = MToonConfig(
            lit_shade_toony=1.0,
            rim_lighting_mix=0.3,
        )
        result = mtoon_config_to_glTF_material(cfg)
        assert "KHR_materials_unlit" not in result["extensions"]

    def test_no_unlit_extension_with_emission(self):
        cfg = MToonConfig(
            lit_shade_toony=1.0,
            emission_intensity=1.0,
        )
        result = mtoon_config_to_glTF_material(cfg)
        assert "KHR_materials_unlit" not in result["extensions"]

    def test_no_unlit_extension_with_outline(self):
        cfg = MToonConfig(
            lit_shade_toony=1.0,
            outline_width=0.05,
        )
        result = mtoon_config_to_glTF_material(cfg)
        assert "KHR_materials_unlit" not in result["extensions"]


# ═══════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════

class TestPresets:
    """PRESET_MTOON_CONFIGS has all 5 presets."""

    def test_has_five_presets(self):
        assert len(PRESET_MTOON_CONFIGS) == 5

    def test_preset_keys(self):
        expected = {"anime_skin", "anime_hair", "anime_eyes", "anime_outfit", "anime_accessory"}
        assert set(PRESET_MTOON_CONFIGS.keys()) == expected

    def test_all_presets_are_mtoon_config(self):
        for name, cfg in PRESET_MTOON_CONFIGS.items():
            assert isinstance(cfg, MToonConfig), f"'{name}' is not MToonConfig"

    def test_anime_skin_preset_values(self):
        skin = PRESET_MTOON_CONFIGS["anime_skin"]
        assert skin.lit_shade_toony == 0.9
        assert skin.outline_width > 0  # has outline
        assert skin.render_mode == "opaque"

    def test_anime_hair_preset_values(self):
        hair = PRESET_MTOON_CONFIGS["anime_hair"]
        assert hair.lit_shade_toony == 0.7
        assert hair.outline_width > 0  # has outline

    def test_anime_eyes_preset_values(self):
        eyes = PRESET_MTOON_CONFIGS["anime_eyes"]
        assert eyes.lit_shade_toony == 0.95
        assert eyes.outline_width == 0.0  # no outline
        assert eyes.render_mode == "transparent"
        assert eyes.cull_mode == "off"

    def test_anime_outfit_preset_values(self):
        outfit = PRESET_MTOON_CONFIGS["anime_outfit"]
        assert outfit.lit_shade_toony == 0.8
        assert outfit.outline_width > 0  # slight outline

    def test_anime_accessory_preset_values(self):
        acc = PRESET_MTOON_CONFIGS["anime_accessory"]
        assert acc.lit_shade_toony == 0.5
        assert acc.outline_width == 0.0  # no outline


# ═══════════════════════════════════════════════════════════════
# create_mtoon_preset
# ═══════════════════════════════════════════════════════════════

class TestCreateMToonPreset:
    """create_mtoon_preset creates configs from presets with overrides."""

    def test_create_from_existing_preset(self):
        cfg = create_mtoon_preset("anime_skin")
        assert isinstance(cfg, MToonConfig)
        assert cfg.lit_shade_toony == 0.9  # matches preset

    def test_create_with_overrides(self):
        cfg = create_mtoon_preset("anime_skin", lit_shade_toony=0.5, outline_width=0.1)
        assert cfg.lit_shade_toony == 0.5  # overridden
        assert cfg.outline_width == 0.1  # overridden
        assert cfg.lit_color == PRESET_MTOON_CONFIGS["anime_skin"].lit_color  # not overridden

    def test_create_does_not_mutate_preset(self):
        original_toony = PRESET_MTOON_CONFIGS["anime_skin"].lit_shade_toony
        cfg = create_mtoon_preset("anime_skin", lit_shade_toony=0.3)
        assert PRESET_MTOON_CONFIGS["anime_skin"].lit_shade_toony == original_toony

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown MToon preset"):
            create_mtoon_preset("nonexistent")

    def test_invalid_override_field_raises(self):
        with pytest.raises(ValueError, match="Unknown MToonConfig field"):
            create_mtoon_preset("anime_skin", nonexistent_field=42)


# ═══════════════════════════════════════════════════════════════
# list_mtoon_presets
# ═══════════════════════════════════════════════════════════════

class TestListMToonPresets:
    """list_mtoon_presets returns expected names."""

    def test_returns_expected_list(self):
        names = list_mtoon_presets()
        assert isinstance(names, list)
        assert set(names) == {
            "anime_skin", "anime_hair", "anime_eyes",
            "anime_outfit", "anime_accessory",
        }

    def test_returns_sorted_list(self):
        names = list_mtoon_presets()
        assert names == sorted(names)


# ═══════════════════════════════════════════════════════════════
# blend_mtoon_configs
# ═══════════════════════════════════════════════════════════════

class TestBlendMToonConfigs:
    """blend_mtoon_configs interpolates correctly."""

    def test_blend_at_zero_returns_a(self):
        a = MToonConfig(lit_color=(1.0, 0.0, 0.0))
        b = MToonConfig(lit_color=(0.0, 0.0, 1.0))
        result = blend_mtoon_configs(a, b, 0.0)
        assert result.lit_color == pytest.approx((1.0, 0.0, 0.0))

    def test_blend_at_one_returns_b(self):
        a = MToonConfig(lit_color=(1.0, 0.0, 0.0))
        b = MToonConfig(lit_color=(0.0, 0.0, 1.0))
        result = blend_mtoon_configs(a, b, 1.0)
        assert result.lit_color == pytest.approx((0.0, 0.0, 1.0))

    def test_blend_at_half_interpolates(self):
        a = MToonConfig(lit_color=(1.0, 0.0, 0.0))
        b = MToonConfig(lit_color=(0.0, 0.0, 1.0))
        result = blend_mtoon_configs(a, b, 0.5)
        assert result.lit_color == pytest.approx((0.5, 0.0, 0.5))

    def test_blend_scalar_at_half(self):
        a = MToonConfig(lit_shade_toony=0.0)
        b = MToonConfig(lit_shade_toony=1.0)
        result = blend_mtoon_configs(a, b, 0.5)
        assert result.lit_shade_toony == pytest.approx(0.5)

    def test_blend_snap_fields_at_t_049(self):
        """Snap fields should choose a's value when t < 0.5."""
        a = MToonConfig(render_mode="opaque")
        b = MToonConfig(render_mode="transparent")
        result = blend_mtoon_configs(a, b, 0.49)
        assert result.render_mode == "opaque"

    def test_blend_snap_fields_at_t_050(self):
        """Snap fields should choose b's value when t >= 0.5."""
        a = MToonConfig(render_mode="opaque")
        b = MToonConfig(render_mode="transparent")
        result = blend_mtoon_configs(a, b, 0.5)
        assert result.render_mode == "transparent"

    def test_blend_boolean_fields_at_t_049(self):
        a = MToonConfig(z_write=True)
        b = MToonConfig(z_write=False)
        result = blend_mtoon_configs(a, b, 0.4)
        assert result.z_write is True

    def test_blend_boolean_fields_at_t_050(self):
        a = MToonConfig(z_write=True)
        b = MToonConfig(z_write=False)
        result = blend_mtoon_configs(a, b, 0.5)
        assert result.z_write is False

    def test_blend_uv_transform(self):
        a = MToonConfig(uv_transform_scale=(1.0, 1.0), uv_transform_offset=(0.0, 0.0))
        b = MToonConfig(uv_transform_scale=(2.0, 3.0), uv_transform_offset=(0.5, 0.5))
        result = blend_mtoon_configs(a, b, 0.5)
        assert result.uv_transform_scale == pytest.approx((1.5, 2.0))
        assert result.uv_transform_offset == pytest.approx((0.25, 0.25))

    def test_blend_clamps_t_to_zero(self):
        a = MToonConfig(lit_shade_toony=0.5)
        b = MToonConfig(lit_shade_toony=1.0)
        result = blend_mtoon_configs(a, b, -0.5)
        assert result.lit_shade_toony == pytest.approx(0.5)

    def test_blend_clamps_t_to_one(self):
        a = MToonConfig(lit_shade_toony=0.5)
        b = MToonConfig(lit_shade_toony=1.0)
        result = blend_mtoon_configs(a, b, 1.5)
        assert result.lit_shade_toony == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════
# Serialization round-trip
# ═══════════════════════════════════════════════════════════════

class TestSerialization:
    """MToonConfig to_dict/from_dict round-trips correctly."""

    def test_to_dict_and_from_dict(self):
        cfg = MToonConfig(
            lit_color=(0.9, 0.8, 0.7),
            lit_shade_toony=0.85,
            render_mode="cutout",
        )
        d = cfg.to_dict()
        cfg2 = MToonConfig.from_dict(d)
        assert cfg2.lit_color == (0.9, 0.8, 0.7)
        assert cfg2.lit_shade_toony == 0.85
        assert cfg2.render_mode == "cutout"

    def test_from_dict_handles_lists(self):
        """Lists in JSON deserialize back to tuples."""
        d = {
            "lit_color": [0.9, 0.8, 0.7],
            "uv_transform_scale": [2.0, 2.0],
        }
        cfg = MToonConfig.from_dict(d)
        assert cfg.lit_color == (0.9, 0.8, 0.7)
        assert cfg.uv_transform_scale == (2.0, 2.0)

    def test_from_dict_ignores_unknown_keys(self):
        d = {"lit_color": (1.0, 1.0, 1.0), "unknown_key": 42}
        cfg = MToonConfig.from_dict(d)
        assert cfg.lit_color == (1.0, 1.0, 1.0)


# ═══════════════════════════════════════════════════════════════
# Valid enums
# ═══════════════════════════════════════════════════════════════

class TestValidEnums:
    """Known render_mode and cull_mode values pass validation."""

    def test_render_modes(self):
        for mode in VALID_RENDER_MODES:
            cfg = MToonConfig(render_mode=mode)
            # For transparent, make z_write consistent to avoid warning
            if mode == "transparent":
                cfg.z_write = False
            issues = validate_mtoon_config(cfg)
            mode_issues = [i for i in issues if "render_mode" in i]
            assert mode_issues == [], f"render_mode='{mode}' should be valid"

    def test_cull_modes(self):
        for mode in VALID_CULL_MODES:
            cfg = MToonConfig(cull_mode=mode)
            issues = validate_mtoon_config(cfg)
            mode_issues = [i for i in issues if "cull_mode" in i]
            assert mode_issues == [], f"cull_mode='{mode}' should be valid"