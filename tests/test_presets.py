"""
Tests for Hamr character presets (Phase 11 T7).
"""

import pytest
from copy import deepcopy

from hamr.core.presets import (
    CHARACTER_PRESETS,
    PRESET_CATEGORIES,
    CharacterPreset,
    get_preset,
    list_presets,
    resolve_preset,
    deep_merge,
    sanitize_preset,
    validate_preset,
    spec_to_dict,
)


# ── Preset existence and structure ─────────────────────────────────────────────

EXPECTED_PRESET_NAMES = [
    "anime_girl_default",
    "anime_girl_warrior",
    "anime_girl_mage",
    "anime_boy_default",
    "anime_boy_warrior",
    "chibi_cute",
]

REQUIRED_KEYS = {"name", "display_name", "description", "spec"}

REQUIRED_SPEC_SUBKEYS = {"body", "face", "hair"}


class TestCharacterPresetsStructure:
    """All CHARACTER_PRESETS entries must have the required structure."""

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_preset_exists(self, preset_name: str) -> None:
        assert preset_name in CHARACTER_PRESETS

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_preset_has_required_keys(self, preset_name: str) -> None:
        entry = CHARACTER_PRESETS[preset_name]
        for key in REQUIRED_KEYS:
            assert key in entry, f"{preset_name} missing key: {key}"

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_preset_spec_has_body_face_hair(self, preset_name: str) -> None:
        spec = CHARACTER_PRESETS[preset_name]["spec"]
        for key in REQUIRED_SPEC_SUBKEYS:
            assert key in spec, f"{preset_name} spec missing key: {key}"

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_preset_name_matches_key(self, preset_name: str) -> None:
        entry = CHARACTER_PRESETS[preset_name]
        assert entry["name"] == preset_name

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_preset_display_name_is_string(self, preset_name: str) -> None:
        entry = CHARACTER_PRESETS[preset_name]
        assert isinstance(entry["display_name"], str)
        assert len(entry["display_name"]) > 0

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_preset_description_is_string(self, preset_name: str) -> None:
        entry = CHARACTER_PRESETS[preset_name]
        assert isinstance(entry["description"], str)
        assert len(entry["description"]) > 0

    def test_exactly_six_presets(self) -> None:
        assert len(CHARACTER_PRESETS) == 6


# ── get_preset ─────────────────────────────────────────────────────────────────

class TestGetPreset:

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_returns_character_preset(self, preset_name: str) -> None:
        result = get_preset(preset_name)
        assert isinstance(result, CharacterPreset)
        assert result.name == preset_name

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESET_NAMES)
    def test_spec_is_dict(self, preset_name: str) -> None:
        result = get_preset(preset_name)
        assert isinstance(result.spec, dict)

    def test_unknown_preset_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown character preset"):
            get_preset("nonexistent_preset")

    def test_returns_deep_copy(self) -> None:
        """Modifying the returned spec must not affect the original preset."""
        result = get_preset("anime_girl_default")
        original_hair_style = CHARACTER_PRESETS["anime_girl_default"]["spec"]["hair"]["style"]
        result.spec["hair"]["style"] = "MODIFIED"
        assert CHARACTER_PRESETS["anime_girl_default"]["spec"]["hair"]["style"] == original_hair_style


# ── list_presets ───────────────────────────────────────────────────────────────

class TestListPresets:

    def test_returns_all_six(self) -> None:
        presets = list_presets()
        assert len(presets) == 6

    def test_all_are_character_preset_instances(self) -> None:
        presets = list_presets()
        assert all(isinstance(p, CharacterPreset) for p in presets)

    def test_contains_each_expected_name(self) -> None:
        presets = list_presets()
        names = {p.name for p in presets}
        assert names == set(EXPECTED_PRESET_NAMES)


# ── deep_merge ─────────────────────────────────────────────────────────────────

class TestDeepMerge:

    def test_flat_override(self) -> None:
        base = {"a": 1, "b": 2}
        result = deep_merge(base, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self) -> None:
        base = {"body": {"height_cm": 158.0, "build": "average"}}
        override = {"body": {"height_cm": 170.0}}
        result = deep_merge(base, override)
        assert result == {"body": {"height_cm": 170.0, "build": "average"}}

    def test_deeply_nested_merge(self) -> None:
        base = {"body": {"skin": {"base_hex": "#E8B87A", "undertone": "warm"}}}
        override = {"body": {"skin": {"base_hex": "#FF0000"}}}
        result = deep_merge(base, override)
        assert result == {"body": {"skin": {"base_hex": "#FF0000", "undertone": "warm"}}}

    def test_new_key_added(self) -> None:
        base = {"a": 1}
        result = deep_merge(base, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self) -> None:
        base = {"body": {"height_cm": 158.0}}
        original_base = deepcopy(base)
        deep_merge(base, {"body": {"height_cm": 180.0}})
        assert base == original_base

    def test_list_replaced_not_merged(self) -> None:
        base = {"clothing": [{"name": "old"}]}
        override = {"clothing": [{"name": "new"}]}
        result = deep_merge(base, override)
        assert result == {"clothing": [{"name": "new"}]}

    def test_empty_override_returns_copy(self) -> None:
        base = {"a": 1, "b": {"c": 2}}
        result = deep_merge(base, {})
        assert result == base
        assert result is not base
        assert result["b"] is not base["b"]


# ── resolve_preset ─────────────────────────────────────────────────────────────

class TestResolvePreset:

    def test_no_overrides_returns_base_spec(self) -> None:
        result = resolve_preset("anime_girl_default")
        expected = get_preset("anime_girl_default").spec
        assert result == expected

    def test_overrides_merge_correctly(self) -> None:
        result = resolve_preset("anime_girl_default", {"body": {"height_cm": 180.0}})
        assert result["body"]["height_cm"] == 180.0
        # Other body fields preserved
        assert result["body"]["build"] == "average"

    def test_nested_override_preserves_siblings(self) -> None:
        result = resolve_preset("anime_boy_warrior", {
            "hair": {"style": "ponytail"},
        })
        assert result["hair"]["style"] == "ponytail"
        # Other hair fields should remain from base
        assert result["hair"]["length"] == "short"
        assert result["hair"]["volume"] == 0.9

    def test_none_overrides_returns_base(self) -> None:
        result = resolve_preset("chibi_cute", None)
        expected = get_preset("chibi_cute").spec
        assert result == expected

    def test_empty_dict_overrides_returns_base(self) -> None:
        result = resolve_preset("chibi_cute", {})
        expected = get_preset("chibi_cute").spec
        assert result == expected

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(KeyError):
            resolve_preset("no_such_preset")


# ── sanitize_preset ───────────────────────────────────────────────────────────

class TestSanitizePreset:

    def test_string_name_returns_spec(self) -> None:
        result = sanitize_preset("anime_girl_mage")
        assert isinstance(result, dict)
        assert "body" in result
        assert "face" in result
        assert "hair" in result

    def test_dict_returns_deep_copy(self) -> None:
        raw = {"body": {"height_cm": 160.0}, "face": {"jaw": "round"}}
        result = sanitize_preset(raw)
        assert result == raw
        assert result is not raw
        assert result["body"] is not raw["body"]

    def test_invalid_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="str or dict"):
            sanitize_preset(42)

    def test_unknown_name_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            sanitize_preset("totally_bogus_preset")


# ── validate_preset ────────────────────────────────────────────────────────────

class TestValidatePreset:

    def test_valid_presets_have_no_warnings(self) -> None:
        for name in EXPECTED_PRESET_NAMES:
            spec = get_preset(name).spec
            warnings = validate_preset(spec)
            assert warnings == [], f"Preset {name} has warnings: {warnings}"

    def test_missing_required_key(self) -> None:
        warnings = validate_preset({})
        assert any("Missing required key: body" in w for w in warnings)
        assert any("Missing required key: face" in w for w in warnings)
        assert any("Missing required key: hair" in w for w in warnings)

    def test_height_out_of_range(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_girl_default"]["spec"])
        spec["body"]["height_cm"] = 50.0
        warnings = validate_preset(spec)
        assert any("height_cm out of range" in w for w in warnings)

    def test_volume_out_of_range(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_girl_default"]["spec"])
        spec["hair"]["volume"] = 2.5
        warnings = validate_preset(spec)
        assert any("volume out of range" in w for w in warnings)

    def test_invalid_build_string(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_boy_default"]["spec"])
        spec["body"]["build"] = "super-muscular-nope"
        warnings = validate_preset(spec)
        assert any("body.build unknown" in w for w in warnings)

    def test_invalid_hair_style(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_girl_warrior"]["spec"])
        spec["hair"]["style"] = "mohawk-faux"
        warnings = validate_preset(spec)
        assert any("hair.style unknown" in w for w in warnings)

    def test_invalid_jaw(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["chibi_cute"]["spec"])
        spec["face"]["jaw"] = "hexagonal"
        warnings = validate_preset(spec)
        assert any("face.jaw unknown" in w for w in warnings)

    def test_eye_size_out_of_range(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["chibi_cute"]["spec"])
        spec["face"]["eyes"]["size"] = 5.0
        warnings = validate_preset(spec)
        assert any("eyes.size out of range" in w for w in warnings)

    def test_invalid_hex_color(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_girl_mage"]["spec"])
        spec["face"]["eyes"]["iris_hex"] = "not-a-hex"
        warnings = validate_preset(spec)
        assert any("iris_hex invalid hex" in w for w in warnings)

    def test_proportion_out_of_range(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_boy_default"]["spec"])
        spec["body"]["proportions"]["shoulder_width"] = 2.0
        warnings = validate_preset(spec)
        assert any("shoulder_width out of range" in w for w in warnings)

    def test_shell_layers_out_of_range(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_boy_warrior"]["spec"])
        spec["hair"]["shell_layers"] = 50
        warnings = validate_preset(spec)
        assert any("shell_layers out of range" in w for w in warnings)

    def test_hair_color_invalid_hex(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_girl_default"]["spec"])
        spec["hair"]["color"]["roots"] = "ZZZZZZ"
        warnings = validate_preset(spec)
        assert any("hair.color.roots invalid hex" in w for w in warnings)

    def test_tan_level_out_of_range(self) -> None:
        spec = deepcopy(CHARACTER_PRESETS["anime_girl_default"]["spec"])
        spec["body"]["skin"]["tan_level"] = 5.0
        warnings = validate_preset(spec)
        assert any("tan_level out of range" in w for w in warnings)


# ── PRESET_CATEGORIES ──────────────────────────────────────────────────────────

class TestPresetCategories:

    def test_categories_have_correct_keys(self) -> None:
        assert set(PRESET_CATEGORIES.keys()) == {"female", "male", "chibi"}

    def test_female_category(self) -> None:
        assert PRESET_CATEGORIES["female"] == [
            "anime_girl_default", "anime_girl_warrior", "anime_girl_mage"
        ]

    def test_male_category(self) -> None:
        assert PRESET_CATEGORIES["male"] == [
            "anime_boy_default", "anime_boy_warrior"
        ]

    def test_chibi_category(self) -> None:
        assert PRESET_CATEGORIES["chibi"] == ["chibi_cute"]

    def test_all_presets_accounted_for(self) -> None:
        all_in_categories = set()
        for names in PRESET_CATEGORIES.values():
            all_in_categories.update(names)
        assert all_in_categories == set(EXPECTED_PRESET_NAMES)

    def test_category_names_reference_valid_presets(self) -> None:
        for category, names in PRESET_CATEGORIES.items():
            for name in names:
                assert name in CHARACTER_PRESETS, f"{category} references unknown preset {name}"


# ── Bug-fix regression tests (Phase 14 T4) ───────────────────────────────────

class TestPresetOverrideBodyProportions:
    """Verify that resolve_preset correctly overrides body proportions
    while preserving other body fields (Phase 13/14 regression)."""

    def test_preset_override_body_proportions(self) -> None:
        result = resolve_preset("anime_girl_default", {
            "body": {
                "proportions": {
                    "shoulder_width": 0.25,
                    "bust": 0.40,
                },
            },
        })
        # Overridden proportion fields
        assert result["body"]["proportions"]["shoulder_width"] == 0.25
        assert result["body"]["proportions"]["bust"] == 0.40
        # Preserved proportion fields from the base preset
        assert result["body"]["proportions"]["waist"] == 0.30
        assert result["body"]["proportions"]["hip_width"] == 0.60
        assert result["body"]["proportions"]["leg_length"] == 0.55
        # Other body fields preserved
        assert result["body"]["height_cm"] == 158.0
        assert result["body"]["build"] == "average"


class TestPresetOverrideHairStyle:
    """Verify that resolve_preset correctly overrides hair style
    while preserving other hair fields (Phase 13/14 regression)."""

    def test_preset_override_hair_style(self) -> None:
        result = resolve_preset("anime_girl_mage", {
            "hair": {"style": "braided"},
        })
        # Overridden field
        assert result["hair"]["style"] == "braided"
        # Preserved fields from base preset
        assert result["hair"]["length"] == "very-long"
        assert result["hair"]["volume"] == 0.85
        assert result["hair"]["curl_tightness"] == 0.4
        # Color sub-dict preserved entirely
        assert result["hair"]["color"]["roots"] == "#8A8A9A"
        assert result["hair"]["color"]["mid"] == "#B0B0C0"
        assert result["hair"]["color"]["tips"] == "#D8D8E8"


class TestInvalidHeightCreatesDefaultSpec:
    """Verify that invalid height values are caught by validation and that
    resolving a preset with an invalid height override still produces a
    structurally valid spec (Phase 13/14 regression)."""

    def test_invalid_height_creates_default_spec(self) -> None:
        # Resolve with an out-of-range height override
        spec = resolve_preset("chibi_cute", {
            "body": {"height_cm": 50.0},
        })
        # The spec should still have all required fields
        assert "body" in spec
        assert "face" in spec
        assert "hair" in spec
        # The overridden height value is present (even though invalid)
        assert spec["body"]["height_cm"] == 50.0
        # Other body fields remain from the base preset
        assert spec["body"]["build"] == "petite"
        # Validation should flag the out-of-range height
        warnings = validate_preset(spec)
        assert any("height_cm out of range" in w for w in warnings)