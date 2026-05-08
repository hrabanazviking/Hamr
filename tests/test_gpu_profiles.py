"""
Tests for hamr.core.gpu_profiles — GPU profile tiers.

Elda Járnsdóttir strikes the anvil: every profile must prove its steel.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from hamr.core.gpu_profiles import (
    GPUProfile,
    GPU_PROFILES,
    get_profile,
    list_profiles,
    auto_detect_profile,
    profile_from_spec,
    validate_profile_compatibility,
    profile_to_budget,
)


# ── GPUProfile Dataclass ────────────────────────────────────────────────

class TestGPUProfileDataclass:
    """Test GPUProfile creation and default values."""

    def test_basic_creation(self):
        """GPUProfile can be created with required fields."""
        p = GPUProfile(
            name="test",
            display_name="Test Device",
            max_triangles=50000,
            max_texture_resolution=1024,
            max_build_time_seconds=30.0,
            max_memory_mb=2000,
        )
        assert p.name == "test"
        assert p.display_name == "Test Device"
        assert p.max_triangles == 50_000
        assert p.max_texture_resolution == 1024
        assert p.max_build_time_seconds == 30.0
        assert p.max_memory_mb == 2000

    def test_defaults(self):
        """GPUProfile default values are correct."""
        p = GPUProfile(
            name="test",
            display_name="Test Device",
            max_triangles=50000,
            max_texture_resolution=1024,
            max_build_time_seconds=30.0,
            max_memory_mb=2000,
        )
        # Defaults from dataclass definition
        assert p.recommended_hair_styles == []
        assert p.recommended_clothing_layers == 1
        assert p.supports_sss is True
        assert p.supports_anisotropic is True
        assert p.auto_detect_order == 0

    def test_custom_optional_fields(self):
        """GPUProfile can override default fields."""
        p = GPUProfile(
            name="custom",
            display_name="Custom Device",
            max_triangles=100_000,
            max_texture_resolution=2048,
            max_build_time_seconds=20.0,
            max_memory_mb=4000,
            recommended_hair_styles=["short", "long"],
            recommended_clothing_layers=4,
            supports_sss=False,
            supports_anisotropic=False,
            auto_detect_order=5,
        )
        assert p.recommended_hair_styles == ["short", "long"]
        assert p.recommended_clothing_layers == 4
        assert p.supports_sss is False
        assert p.supports_anisotropic is False
        assert p.auto_detect_order == 5

    def test_hair_styles_is_independent_per_instance(self):
        """Each GPUProfile gets its own list instance (no mutable default sharing)."""
        p1 = GPUProfile(name="a", display_name="A", max_triangles=1000,
                         max_texture_resolution=512, max_build_time_seconds=10.0,
                         max_memory_mb=500)
        p2 = GPUProfile(name="b", display_name="B", max_triangles=2000,
                         max_texture_resolution=512, max_build_time_seconds=10.0,
                         max_memory_mb=500)
        p1.recommended_hair_styles.append("mohawk")
        assert p2.recommended_hair_styles == []  # must not be affected


# ── GPU_PROFILES Dict ───────────────────────────────────────────────────

class TestGPUProfilesDict:
    """Test the pre-defined GPU_PROFILES mapping."""

    def test_has_three_profiles(self):
        """GPU_PROFILES must contain exactly 3 entries."""
        assert len(GPU_PROFILES) == 3

    def test_profile_names(self):
        """GPU_PROFILES must contain pi5, desktop, cloud."""
        assert set(GPU_PROFILES.keys()) == {"pi5", "desktop", "cloud"}

    def test_pi5_has_low_limits(self):
        """Pi 5 profile should have the lowest limits of the three."""
        pi5 = GPU_PROFILES["pi5"]
        desktop = GPU_PROFILES["desktop"]
        cloud = GPU_PROFILES["cloud"]

        assert pi5.max_triangles < desktop.max_triangles
        assert pi5.max_texture_resolution < desktop.max_texture_resolution
        assert pi5.max_build_time_seconds > desktop.max_build_time_seconds  # slower
        assert pi5.max_memory_mb < desktop.max_memory_mb

    def test_desktop_has_medium_limits(self):
        """Desktop profile should sit between pi5 and cloud."""
        pi5 = GPU_PROFILES["pi5"]
        desktop = GPU_PROFILES["desktop"]
        cloud = GPU_PROFILES["cloud"]

        assert desktop.max_triangles > pi5.max_triangles
        assert desktop.max_triangles < cloud.max_triangles

    def test_cloud_has_highest_limits(self):
        """Cloud profile should have the highest limits."""
        cloud = GPU_PROFILES["cloud"]
        desktop = GPU_PROFILES["desktop"]

        assert cloud.max_triangles > desktop.max_triangles
        assert cloud.max_texture_resolution > desktop.max_texture_resolution
        assert cloud.max_build_time_seconds < desktop.max_build_time_seconds  # faster
        assert cloud.max_memory_mb > desktop.max_memory_mb

    def test_pi5_specific_values(self):
        """Pi 5 profile has exact values per spec."""
        pi5 = GPU_PROFILES["pi5"]
        assert pi5.max_triangles == 20_000
        assert pi5.max_texture_resolution == 1024
        assert pi5.max_build_time_seconds == 45.0
        assert pi5.max_memory_mb == 1500
        assert pi5.recommended_hair_styles == ["short", "medium_bob"]
        assert pi5.recommended_clothing_layers == 1
        assert pi5.supports_sss is False
        assert pi5.supports_anisotropic is False
        assert pi5.auto_detect_order == 1

    def test_pi5_no_sss_no_anisotropic(self):
        """Pi 5 cannot do SSS or anisotropic shading."""
        pi5 = GPU_PROFILES["pi5"]
        assert pi5.supports_sss is False
        assert pi5.supports_anisotropic is False

    def test_pi5_limited_hair_styles(self):
        """Pi 5 only supports short and medium_bob hair."""
        pi5 = GPU_PROFILES["pi5"]
        assert "short" in pi5.recommended_hair_styles
        assert "medium_bob" in pi5.recommended_hair_styles
        assert len(pi5.recommended_hair_styles) == 2

    def test_desktop_wider_hair(self):
        """Desktop supports more hair styles than Pi 5."""
        pi5 = GPU_PROFILES["pi5"]
        desktop = GPU_PROFILES["desktop"]
        assert len(desktop.recommended_hair_styles) > len(pi5.recommended_hair_styles)
        assert "long" in desktop.recommended_hair_styles
        assert "ponytail" in desktop.recommended_hair_styles

    def test_cloud_highest_clothing_layers(self):
        """Cloud supports 5 clothing layers."""
        cloud = GPU_PROFILES["cloud"]
        assert cloud.recommended_clothing_layers == 5

    def test_auto_detect_order_correct(self):
        """Auto-detect orders are 1 (pi5), 2 (desktop), 3 (cloud)."""
        assert GPU_PROFILES["pi5"].auto_detect_order == 1
        assert GPU_PROFILES["desktop"].auto_detect_order == 2
        assert GPU_PROFILES["cloud"].auto_detect_order == 3


# ── get_profile ─────────────────────────────────────────────────────────

class TestGetProfile:
    """Test the get_profile lookup function."""

    def test_get_pi5(self):
        p = get_profile("pi5")
        assert p.name == "pi5"
        assert p.display_name == "Raspberry Pi 5"

    def test_get_desktop(self):
        p = get_profile("desktop")
        assert p.name == "desktop"
        assert p.display_name == "Desktop GPU"

    def test_get_cloud(self):
        p = get_profile("cloud")
        assert p.name == "cloud"
        assert p.display_name == "Cloud GPU"

    def test_unknown_profile_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown GPU profile"):
            get_profile("unknown_profile")

    def test_unknown_profile_lists_available(self):
        """Error message should list available profiles."""
        with pytest.raises(KeyError, match="pi5"):
            get_profile("nonexistent")
        with pytest.raises(KeyError, match="desktop"):
            get_profile("nonexistent")
        with pytest.raises(KeyError, match="cloud"):
            get_profile("nonexistent")


# ── list_profiles ───────────────────────────────────────────────────────

class TestListProfiles:
    """Test list_profiles returns sorted profiles."""

    def test_returns_three_profiles(self):
        profiles = list_profiles()
        assert len(profiles) == 3

    def test_sorted_by_auto_detect_order(self):
        profiles = list_profiles()
        orders = [p.auto_detect_order for p in profiles]
        assert orders == sorted(orders)

    def test_order_is_pi5_desktop_cloud(self):
        profiles = list_profiles()
        names = [p.name for p in profiles]
        assert names == ["pi5", "desktop", "cloud"]


# ── auto_detect_profile ─────────────────────────────────────────────────

class TestAutoDetectProfile:
    """Test auto_detect_profile returns valid profile names."""

    def test_returns_valid_profile_name(self):
        """auto_detect_profile must return one of the three known names."""
        result = auto_detect_profile()
        assert result in ("pi5", "desktop", "cloud")

    def test_arm_machine_gives_pi5(self):
        """ARM machines should auto-detect as pi5."""
        with patch("hamr.core.gpu_profiles.platform") as mock_platform:
            mock_platform.machine.return_value = "aarch64"
            with patch("hamr.core.gpu_profiles.os") as mock_os:
                result = auto_detect_profile()
                assert result == "pi5"

    def test_armv7l_machine_gives_pi5(self):
        """ARMv7l machines should auto-detect as pi5."""
        with patch("hamr.core.gpu_profiles.platform") as mock_platform:
            mock_platform.machine.return_value = "armv7l"
            result = auto_detect_profile()
            assert result == "pi5"

    def test_x86_64_low_memory_gives_desktop(self):
        """x86_64 with < 64GB RAM should auto-detect as desktop."""
        with patch("hamr.core.gpu_profiles.platform") as mock_platform:
            mock_platform.machine.return_value = "x86_64"
            with patch("hamr.core.gpu_profiles.os") as mock_os:
                mock_os.sysconf.side_effect = lambda k: {
                    "SC_PAGE_SIZE": 4096,
                    "SC_PHYS_PAGES": 4000000,  # ~16GB
                }[k]
                result = auto_detect_profile()
                assert result == "desktop"

    def test_x86_64_high_memory_gives_cloud(self):
        """x86_64 with ≥ 64GB RAM should auto-detect as cloud."""
        with patch("hamr.core.gpu_profiles.platform") as mock_platform:
            mock_platform.machine.return_value = "x86_64"
            with patch("hamr.core.gpu_profiles.os") as mock_os:
                mock_os.sysconf.side_effect = lambda k: {
                    "SC_PAGE_SIZE": 4096,
                    "SC_PHYS_PAGES": 20_000_000,  # ~80GB > 64GB threshold
                }[k]
                result = auto_detect_profile()
                assert result == "cloud"


# ── profile_from_spec ───────────────────────────────────────────────────

class TestProfileFromSpec:
    """Test spec-based profile recommendation."""

    def test_simple_spec_returns_pi5_or_desktop(self):
        """A minimal spec should recommend pi5 or desktop."""
        spec = {"hair": {"style": "straight", "volume": 0.3}, "clothing": []}
        result = profile_from_spec(spec)
        assert result in ("pi5", "desktop")

    def test_complex_spec_returns_desktop_or_cloud(self):
        """A complex spec should recommend desktop or cloud."""
        spec = {
            "hair": {"style": "wild-curly", "volume": 1.0},
            "clothing": [
                {"type": "full-outfit"},
                {"type": "dress"},
                {"type": "tshirt"},
                {"type": "hoodie"},
            ],
        }
        result = profile_from_spec(spec)
        assert result in ("desktop", "cloud")

    def test_empty_spec_returns_pi5(self):
        """An empty spec (minimal demands) should recommend pi5."""
        result = profile_from_spec({})
        assert result == "pi5"

    def test_high_texture_returns_desktop_or_cloud(self):
        """Spec requesting high-res textures needs at least desktop."""
        spec = {"textures": {"resolution": 2048}}
        result = profile_from_spec(spec)
        assert result in ("desktop", "cloud")

    def test_very_high_texture_returns_cloud(self):
        """Spec requesting 4K textures needs cloud."""
        spec = {"textures": {"resolution": 4096}}
        result = profile_from_spec(spec)
        assert result == "cloud"

    def test_many_clothing_layers_returns_cloud(self):
        """More than 3 clothing layers needs cloud."""
        spec = {
            "clothing": [
                {"type": "full-outfit"},
                {"type": "tshirt"},
                {"type": "shorts"},
                {"type": "hoodie"},
            ],
        }
        result = profile_from_spec(spec)
        assert result == "cloud"


# ── validate_profile_compatibility ──────────────────────────────────────

class TestValidateProfileCompatibility:
    """Test spec vs. profile compatibility validation."""

    def test_pi5_vs_heavy_spec_produces_warnings(self):
        """Heavy spec on pi5 should produce multiple warnings."""
        spec = {
            "hair": {"style": "wild-curly", "volume": 0.9, "anisotropic_enabled": True},
            "clothing": [
                {"type": "full-outfit"},
                {"type": "dress"},
                {"type": "tshirt"},
            ],
            "textures": {"resolution": 2048},
            "body": {"skin": {"sss_enabled": True}},
        }
        warnings = validate_profile_compatibility("pi5", spec)
        assert len(warnings) > 0
        # At minimum: too many clothing layers, texture exceeds limit
        warning_text = " ".join(warnings)
        assert "clothing" in warning_text.lower() or "layer" in warning_text.lower()

    def test_cloud_vs_light_spec_produces_no_warnings(self):
        """Light spec on cloud should produce zero warnings."""
        spec = {
            "hair": {"style": "straight"},
            "clothing": [],
            "textures": {"resolution": 512},
        }
        warnings = validate_profile_compatibility("cloud", spec)
        assert warnings == []

    def test_desktop_vs_moderate_spec_may_warn(self):
        """A spec that matches desktop limits should produce few or no warnings."""
        spec = {
            "hair": {"style": "straight"},
            "clothing": [{"type": "top"}],
            "textures": {"resolution": 1024},
        }
        warnings = validate_profile_compatibility("desktop", spec)
        # Should have zero or very few warnings (well within budget)
        # Some minor warnings possible from time estimate
        assert len(warnings) <= 1

    def test_sss_on_pi5_warns(self):
        """SSS request on pi5 should produce a warning."""
        spec = {"body": {"skin": {"sss_enabled": True}}}
        warnings = validate_profile_compatibility("pi5", spec)
        sss_warnings = [w for w in warnings if "SSS" in w or "subsurface" in w.lower()]
        assert len(sss_warnings) > 0

    def test_anisotropic_on_pi5_warns(self):
        """Anisotropic shading on pi5 should produce a warning."""
        spec = {"hair": {"anisotropic_enabled": True}}
        warnings = validate_profile_compatibility("pi5", spec)
        aniso_warnings = [w for w in warnings if "anisotropic" in w.lower()]
        assert len(aniso_warnings) > 0

    def test_unknown_profile_raises(self):
        """Passing an unknown profile name should raise KeyError."""
        with pytest.raises(KeyError):
            validate_profile_compatibility("nonexistent", {})

    def test_texture_exceeds_limit_warns(self):
        """Texture resolution exceeding profile limit should warn."""
        spec = {"textures": {"resolution": 4096}}
        warnings = validate_profile_compatibility("pi5", spec)
        tex_warnings = [w for w in warnings if "texture" in w.lower()]
        assert len(tex_warnings) > 0

    def test_too_many_clothing_layers_warns(self):
        """More clothing layers than profile allows should warn."""
        spec = {"clothing": [{"type": "t"}, {"type": "b"}, {"type": "f"}]}
        warnings = validate_profile_compatibility("pi5", spec)
        clothing_warnings = [w for w in warnings if "clothing" in w.lower() or "layer" in w.lower()]
        assert len(clothing_warnings) > 0


# ── profile_to_budget ───────────────────────────────────────────────────

class TestProfileToBudget:
    """Test conversion from GPU profile to performance budget dict."""

    def test_produces_dict_with_required_keys(self):
        """profile_to_budget must return a dict with all budget keys."""
        budget = profile_to_budget("pi5")
        required_keys = {
            "max_triangles",
            "max_texture_resolution",
            "max_build_time_seconds",
            "max_memory_mb",
            "blender_timeout_seconds",
            "target_fps",
        }
        assert required_keys.issubset(set(budget.keys()))

    def test_pi5_budget_matches_profile(self):
        """Pi5 budget values should match the GPUProfile definition."""
        budget = profile_to_budget("pi5")
        pi5 = GPU_PROFILES["pi5"]
        assert budget["max_triangles"] == pi5.max_triangles
        assert budget["max_texture_resolution"] == pi5.max_texture_resolution
        assert budget["max_build_time_seconds"] == pi5.max_build_time_seconds
        assert budget["max_memory_mb"] == float(pi5.max_memory_mb)

    def test_pi5_budget_fps_is_24(self):
        """Pi5 budget should target 24 FPS."""
        budget = profile_to_budget("pi5")
        assert budget["target_fps"] == 24.0

    def test_desktop_budget_fps_is_30(self):
        """Desktop budget should target 30 FPS."""
        budget = profile_to_budget("desktop")
        assert budget["target_fps"] == 30.0

    def test_cloud_budget_fps_is_60(self):
        """Cloud budget should target 60 FPS."""
        budget = profile_to_budget("cloud")
        assert budget["target_fps"] == 60.0

    def test_desktop_budget_matches_profile(self):
        """Desktop budget values match the GPUProfile definition."""
        budget = profile_to_budget("desktop")
        desktop = GPU_PROFILES["desktop"]
        assert budget["max_triangles"] == desktop.max_triangles
        assert budget["max_texture_resolution"] == desktop.max_texture_resolution
        assert budget["max_build_time_seconds"] == desktop.max_build_time_seconds
        assert budget["max_memory_mb"] == float(desktop.max_memory_mb)

    def test_cloud_budget_matches_profile(self):
        """Cloud budget values match the GPUProfile definition."""
        budget = profile_to_budget("cloud")
        cloud = GPU_PROFILES["cloud"]
        assert budget["max_triangles"] == cloud.max_triangles
        assert budget["max_texture_resolution"] == cloud.max_texture_resolution
        assert budget["max_build_time_seconds"] == cloud.max_build_time_seconds
        assert budget["max_memory_mb"] == float(cloud.max_memory_mb)

    def test_blender_timeout_reasonable(self):
        """Blender timeout should be > build time budget."""
        for name in ("pi5", "desktop", "cloud"):
            budget = profile_to_budget(name)
            assert budget["blender_timeout_seconds"] > budget["max_build_time_seconds"]

    def test_unknown_profile_raises_keyerror(self):
        """profile_to_budget with unknown name should raise KeyError."""
        with pytest.raises(KeyError):
            profile_to_budget("nonexistent")