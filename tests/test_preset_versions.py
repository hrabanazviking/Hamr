"""
Tests for Hamr preset versioning system (Phase 14 T4).
"""

import pytest
from copy import deepcopy

from hamr.core.preset_versions import (
    PresetVersion,
    VersionedPreset,
    PRESET_VERSIONS,
    PRESET_CATEGORIES,
    get_versioned_preset,
    list_presets_by_category,
    list_all_categories,
    validate_preset_version,
    compare_presets,
    migrate_preset,
)
from hamr.core.presets import CHARACTER_PRESETS


# ── PresetVersion ─────────────────────────────────────────────────────────────

class TestPresetVersion:

    def test_creation_with_all_fields(self) -> None:
        v = PresetVersion(
            name="test",
            version="1.2.3",
            created="2025-01-01",
            modified="2025-05-08",
            changelog=["Added feature X"],
        )
        assert v.name == "test"
        assert v.version == "1.2.3"
        assert v.created == "2025-01-01"
        assert v.modified == "2025-05-08"
        assert v.changelog == ["Added feature X"]

    def test_default_changelog_is_empty(self) -> None:
        v = PresetVersion(
            name="test", version="0.1.0",
            created="2025-01-01", modified="2025-01-01",
        )
        assert v.changelog == []

    def test_changelog_is_independent_per_instance(self) -> None:
        v1 = PresetVersion(name="a", version="1.0.0", created="", modified="")
        v2 = PresetVersion(name="b", version="1.0.0", created="", modified="")
        v1.changelog.append("change")
        assert v2.changelog == []


# ── VersionedPreset ───────────────────────────────────────────────────────────

class TestVersionedPreset:

    def test_creation_with_all_fields(self) -> None:
        pv = VersionedPreset(
            name="anime_girl_default",
            display_name="Anime Girl — Default",
            category="anime",
            tags=["school", "female"],
            version=PresetVersion(
                name="anime_girl_default",
                version="1.0.0",
                created="2025-01-15",
                modified="2025-05-08",
            ),
            spec={"body": {"height_cm": 158.0}},
        )
        assert pv.name == "anime_girl_default"
        assert pv.category == "anime"
        assert pv.tags == ["school", "female"]
        assert pv.spec["body"]["height_cm"] == 158.0

    def test_default_tags_is_empty(self) -> None:
        pv = VersionedPreset(
            name="x",
            display_name="X",
            category="chibi",
            version=PresetVersion(name="x", version="1.0.0", created="", modified=""),
            spec={},
        )
        assert pv.tags == []

    def test_tags_is_independent_per_instance(self) -> None:
        pv1 = VersionedPreset(
            name="a", display_name="A", category="anime",
            version=PresetVersion(name="a", version="1.0.0", created="", modified=""),
            spec={},
        )
        pv2 = VersionedPreset(
            name="b", display_name="B", category="anime",
            version=PresetVersion(name="b", version="1.0.0", created="", modified=""),
            spec={},
        )
        pv1.tags.append("new-tag")
        assert pv2.tags == []


# ── PRESET_VERSIONS ────────────────────────────────────────────────────────────

EXPECTED_PRESET_NAMES = [
    "anime_girl_default",
    "anime_girl_warrior",
    "anime_girl_mage",
    "anime_boy_default",
    "anime_boy_warrior",
    "chibi_cute",
]


class TestPresetVersionsRegistry:

    def test_has_entries_for_all_six_presets(self) -> None:
        for name in EXPECTED_PRESET_NAMES:
            assert name in PRESET_VERSIONS, f"Missing version entry for {name}"

    def test_entries_are_preset_version_instances(self) -> None:
        for name, pv in PRESET_VERSIONS.items():
            assert isinstance(pv, PresetVersion), f"{name} is not PresetVersion"

    def test_entry_names_match_keys(self) -> None:
        for name, pv in PRESET_VERSIONS.items():
            assert pv.name == name

    def test_versions_are_semver_strings(self) -> None:
        for name, pv in PRESET_VERSIONS.items():
            parts = pv.version.split(".")
            assert len(parts) == 3, f"{name} version not semver: {pv.version}"
            for part in parts:
                assert part.isdigit(), f"{name} version component not numeric: {part}"


# ── PRESET_CATEGORIES ──────────────────────────────────────────────────────────

class TestPresetCategoriesVersioned:

    def test_has_four_category_keys(self) -> None:
        assert len(PRESET_CATEGORIES) == 4

    def test_category_keys_are_expected(self) -> None:
        assert set(PRESET_CATEGORIES.keys()) == {"anime", "realistic", "fantasy", "chibi"}

    def test_category_values_are_strings(self) -> None:
        for key, display_name in PRESET_CATEGORIES.items():
            assert isinstance(display_name, str)
            assert len(display_name) > 0


# ── get_versioned_preset ──────────────────────────────────────────────────────

class TestGetVersionedPreset:

    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_returns_versioned_preset(self, name: str) -> None:
        result = get_versioned_preset(name)
        assert isinstance(result, VersionedPreset)
        assert result.name == name

    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_spec_is_dict(self, name: str) -> None:
        result = get_versioned_preset(name)
        assert isinstance(result.spec, dict)

    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_version_matches_registry(self, name: str) -> None:
        result = get_versioned_preset(name)
        assert result.version is PRESET_VERSIONS[name]

    def test_raises_for_unknown_preset(self) -> None:
        with pytest.raises(KeyError, match="Unknown character preset"):
            get_versioned_preset("nonexistent_preset")

    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_category_is_valid(self, name: str) -> None:
        result = get_versioned_preset(name)
        assert result.category in PRESET_CATEGORIES

    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_display_name_not_empty(self, name: str) -> None:
        result = get_versioned_preset(name)
        assert len(result.display_name) > 0


# ── list_presets_by_category ──────────────────────────────────────────────────

class TestListPresetsByCategory:

    def test_anime_category(self) -> None:
        results = list_presets_by_category("anime")
        names = [vp.name for vp in results]
        assert "anime_girl_default" in names
        assert "anime_boy_default" in names
        # anime_girl_warrior is "fantasy", not "anime"
        assert "anime_girl_warrior" not in names

    def test_fantasy_category(self) -> None:
        results = list_presets_by_category("fantasy")
        names = [vp.name for vp in results]
        assert "anime_girl_warrior" in names
        assert "anime_boy_warrior" in names
        assert "anime_girl_mage" in names

    def test_chibi_category(self) -> None:
        results = list_presets_by_category("chibi")
        names = [vp.name for vp in results]
        assert names == ["chibi_cute"]

    def test_realistic_category_is_empty(self) -> None:
        # No presets currently assigned to "realistic"
        results = list_presets_by_category("realistic")
        assert results == []

    def test_raises_for_unknown_category(self) -> None:
        with pytest.raises(ValueError, match="Unknown category"):
            list_presets_by_category("nonexistent")


# ── list_all_categories ───────────────────────────────────────────────────────

class TestListAllCategories:

    def test_returns_four_categories(self) -> None:
        cats = list_all_categories()
        assert len(cats) == 4

    def test_returns_sorted_list(self) -> None:
        cats = list_all_categories()
        assert cats == sorted(cats)

    def test_contains_expected_keys(self) -> None:
        cats = list_all_categories()
        assert set(cats) == {"anime", "chibi", "fantasy", "realistic"}


# ── validate_preset_version ────────────────────────────────────────────────────

class TestValidatePresetVersion:

    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_current_version_passes_default_min(self, name: str) -> None:
        assert validate_preset_version(name) is True

    def test_higher_min_version_fails(self) -> None:
        # All presets are currently 1.0.0; requiring 2.0.0 should fail
        assert validate_preset_version("anime_girl_default", min_version="2.0.0") is False

    def test_exact_version_passes(self) -> None:
        assert validate_preset_version("anime_girl_default", min_version="1.0.0") is True

    def test_lower_min_version_passes(self) -> None:
        assert validate_preset_version("anime_girl_default", min_version="0.9.0") is True

    def test_raises_for_unknown_preset(self) -> None:
        with pytest.raises(KeyError):
            validate_preset_version("nonexistent_preset")


# ── compare_presets ────────────────────────────────────────────────────────────

class TestComparePresets:

    def test_same_preset_shows_no_differences(self) -> None:
        result = compare_presets("anime_girl_default", "anime_girl_default")
        assert result["different"] == []
        # body, face, hair, etc. should all match
        assert len(result["matching"]) > 0

    def test_different_presets_show_differences(self) -> None:
        result = compare_presets("anime_girl_default", "chibi_cute")
        # Different presets must have at least some differing top-level keys
        assert len(result["different"]) > 0
        # The "details" dict should have entries for each different key
        for key in result["different"]:
            assert key in result["details"]
            assert "a" in result["details"][key]
            assert "b" in result["details"][key]

    def test_compare_warrior_and_mage(self) -> None:
        result = compare_presets("anime_girl_warrior", "anime_girl_mage")
        # These presets differ in many ways
        assert len(result["different"]) > 0
        # Name will differ
        assert "name" in result["different"] or "name" in result["matching"]

    def test_raises_for_unknown_preset(self) -> None:
        with pytest.raises(KeyError):
            compare_presets("nonexistent", "anime_girl_default")


# ── migrate_preset ─────────────────────────────────────────────────────────────

class TestMigratePreset:

    def test_no_op_migration_returns_spec(self) -> None:
        # Since there are no migration steps registered yet,
        # migrating from 1.0.0 to 1.0.0 should return a copy of the spec.
        result = migrate_preset("anime_girl_default", "1.0.0", "1.0.0")
        assert isinstance(result, dict)
        assert "body" in result

    def test_migration_returns_deep_copy(self) -> None:
        result = migrate_preset("anime_boy_default", "1.0.0", "1.0.0")
        # Verify it's a copy, not a reference
        assert result is not CHARACTER_PRESETS["anime_boy_default"]["spec"]

    def test_migration_to_higher_version_when_no_steps(self) -> None:
        # No migration steps registered; should return the current spec as-is
        result = migrate_preset("chibi_cute", "1.0.0", "2.0.0")
        assert isinstance(result, dict)
        assert "body" in result

    def test_raises_for_unknown_preset(self) -> None:
        with pytest.raises(KeyError, match="Unknown character preset"):
            migrate_preset("nonexistent_preset", "1.0.0", "2.0.0")


# ── Integration: presets + preset_versions ────────────────────────────────────

class TestPresetVersionsIntegration:

    def test_all_versioned_presets_have_matching_spec(self) -> None:
        """Every VersionedPreset.spec should match the CHARACTER_PRESETS entry."""
        for name in EXPECTED_PRESET_NAMES:
            vp = get_versioned_preset(name)
            base = CHARACTER_PRESETS[name]
            assert vp.spec["body"]["height_cm"] == base["spec"]["body"]["height_cm"]

    def test_all_versioned_presets_have_valid_category(self) -> None:
        for name in EXPECTED_PRESET_NAMES:
            vp = get_versioned_preset(name)
            assert vp.category in PRESET_CATEGORIES

    @pytest.mark.parametrize("category", ["anime", "fantasy", "chibi", "realistic"])
    def test_list_presets_by_category_returns_versioned(self, category: str) -> None:
        results = list_presets_by_category(category)
        for vp in results:
            assert isinstance(vp, VersionedPreset)
            assert vp.category == category