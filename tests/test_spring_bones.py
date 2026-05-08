"""
Tests for hamr.rigs.spring_bones — VRM 1.0 Spring Bone Configuration.

Pure-Python tests run without Blender.
Blender-dependent tests are marked with @pytest.mark.blender.
"""

from __future__ import annotations

import pytest

from hamr.rigs.spring_bones import (
    SpringBoneGroup,
    SpringBoneCollider,
    HAIR_SPRING_PRESETS,
    BREAST_SPRING_PRESETS,
    CLOTHING_SPRING_PRESETS,
    DEFAULT_COLLIDERS,
    configure_hair_spring,
    configure_breast_spring,
    configure_clothing_spring,
    apply_spring_bones,
)
from hamr.core.models import HairPhysicsSpec, BreastPhysicsSpec


# ══════════════════════════════════════════════════════════════════════
# SpringBoneGroup dataclass tests
# ══════════════════════════════════════════════════════════════════════


class TestSpringBoneGroup:
    """SpringBoneGroup creation and serialization tests."""

    def test_default_values(self):
        """Default SpringBoneGroup has sensible VRM values."""
        group = SpringBoneGroup(name="test")
        assert group.name == "test"
        assert group.comment == ""
        assert group.stiff_force == 1.0
        assert group.gravity_power == 0.0
        assert group.gravity_dir == (0.0, -1.0, 0.0)
        assert group.drag_force == 0.4
        assert group.center is None
        assert group.collider_groups == []
        assert group.bone_chains == []

    def test_custom_values(self):
        """SpringBoneGroup accepts all custom parameters."""
        group = SpringBoneGroup(
            name="hair_long",
            comment="Long hair sway",
            stiff_force=0.5,
            gravity_power=0.6,
            gravity_dir=(0.0, -0.8, -0.2),
            drag_force=0.5,
            center="head",
            collider_groups=["head_collider"],
            bone_chains=[["hair_01", "hair_02", "hair_03"]],
        )
        assert group.stiff_force == 0.5
        assert group.gravity_power == 0.6
        assert group.gravity_dir == (0.0, -0.8, -0.2)
        assert group.drag_force == 0.5
        assert group.center == "head"
        assert len(group.collider_groups) == 1
        assert len(group.bone_chains) == 1

    def test_to_dict(self):
        """to_dict serialization produces VRM-compatible dict."""
        group = SpringBoneGroup(
            name="skirt",
            stiff_force=0.3,
            gravity_power=0.5,
            bone_chains=[["skirt_01", "skirt_02"]],
        )
        d = group.to_dict()
        assert d["name"] == "skirt"
        assert d["stiff_force"] == 0.3
        assert d["gravity_power"] == 0.5
        assert isinstance(d["gravity_dir"], list)
        assert isinstance(d["collider_groups"], list)
        assert isinstance(d["bone_chains"], list)
        assert d["bone_chains"] == [["skirt_01", "skirt_02"]]

    def test_to_dict_converts_tuples(self):
        """to_dict converts tuple fields to lists for JSON serialization."""
        group = SpringBoneGroup(
            name="test",
            gravity_dir=(1.0, 2.0, 3.0),
        )
        d = group.to_dict()
        assert isinstance(d["gravity_dir"], list)
        assert d["gravity_dir"] == [1.0, 2.0, 3.0]


class TestSpringBoneCollider:
    """SpringBoneCollider creation and serialization tests."""

    def test_default_values(self):
        """Default collider has a bone, zero offset, and small radius."""
        collider = SpringBoneCollider(name="head_coll", bone="head")
        assert collider.name == "head_coll"
        assert collider.bone == "head"
        assert collider.offset == (0.0, 0.0, 0.0)
        assert collider.radius == 0.01

    def test_custom_values(self):
        """Collider accepts custom offset and radius."""
        collider = SpringBoneCollider(
            name="chest_coll",
            bone="spine_02",
            offset=(0.0, 0.05, 0.0),
            radius=0.12,
        )
        assert collider.offset == (0.0, 0.05, 0.0)
        assert collider.radius == 0.12

    def test_to_dict(self):
        """to_dict produces VRM-compatible dict."""
        collider = SpringBoneCollider(
            name="body_col",
            bone="spine",
            offset=(0.1, 0.2, 0.3),
            radius=0.08,
        )
        d = collider.to_dict()
        assert d["name"] == "body_col"
        assert d["bone"] == "spine"
        assert d["offset"] == [0.1, 0.2, 0.3]
        assert d["radius"] == 0.08


# ══════════════════════════════════════════════════════════════════════
# Preset tests
# ══════════════════════════════════════════════════════════════════════


class TestHairSpringPresets:
    """Hair spring preset structure and value tests."""

    def test_all_hair_presets_exist(self):
        """All expected hair presets are present."""
        expected = {"long", "medium", "short", "twin_tails"}
        assert set(HAIR_SPRING_PRESETS.keys()) == expected

    def test_hair_presets_have_required_keys(self):
        """Each hair preset has all required configuration keys."""
        required_keys = {"stiff_force", "gravity_power", "gravity_dir", "drag_force", "bone_chains"}
        for name, preset in HAIR_SPRING_PRESETS.items():
            assert required_keys.issubset(set(preset.keys())), f"Missing keys in {name}"

    def test_hair_presets_stiff_force_range(self):
        """Hair stiff_force values are within VRM 1.0 range (0–10)."""
        for name, preset in HAIR_SPRING_PRESETS.items():
            assert 0 <= preset["stiff_force"] <= 10, f"{name} stiff_force out of range"

    def test_hair_presets_gravity_direction_down(self):
        """Hair gravity should generally point down (negative Y)."""
        for name, preset in HAIR_SPRING_PRESETS.items():
            assert preset["gravity_dir"][1] < 0, f"{name} gravity not pointing down"

    def test_hair_long_has_multiple_chains(self):
        """Long hair preset has multiple bone chains (left, right, back)."""
        preset = HAIR_SPRING_PRESETS["long"]
        assert len(preset["bone_chains"]) >= 3

    def test_hair_short_has_fewer_chains(self):
        """Short hair preset has fewer chains than long hair."""
        short_chains = len(HAIR_SPRING_PRESETS["short"]["bone_chains"])
        long_chains = len(HAIR_SPRING_PRESETS["long"]["bone_chains"])
        assert short_chains < long_chains


class TestBreastSpringPresets:
    """Breast spring preset structure and value tests."""

    def test_all_breast_presets_exist(self):
        """All expected breast presets are present."""
        expected = {"small", "medium", "large"}
        assert set(BREAST_SPRING_PRESETS.keys()) == expected

    def test_breast_presets_have_bone_chains(self):
        """Each breast preset has L/R bone chains."""
        for name, preset in BREAST_SPRING_PRESETS.items():
            chains = preset["bone_chains"]
            assert len(chains) >= 2, f"{name} needs L/R chains"

    def test_breast_stiffness_inversely_proportional(self):
        """Larger bust sizes have lower stiffness (more bounce)."""
        stiff_small = BREAST_SPRING_PRESETS["small"]["stiff_force"]
        stiff_medium = BREAST_SPRING_PRESETS["medium"]["stiff_force"]
        stiff_large = BREAST_SPRING_PRESETS["large"]["stiff_force"]
        assert stiff_small > stiff_medium > stiff_large

    def test_breast_gravity_increases_with_size(self):
        """Larger bust sizes have stronger gravity influence."""
        grav_small = BREAST_SPRING_PRESETS["small"]["gravity_power"]
        grav_large = BREAST_SPRING_PRESETS["large"]["gravity_power"]
        assert grav_large > grav_small


class TestClothingSpringPresets:
    """Clothing spring preset structure and value tests."""

    def test_all_clothing_presets_exist(self):
        """All expected clothing presets are present."""
        expected = {"skirt", "cape", "ribbon"}
        assert set(CLOTHING_SPRING_PRESETS.keys()) == expected

    def test_cape_has_more_chains_than_ribbon(self):
        """Cape has more bone chains (dramatic drape) than ribbon (light flutter)."""
        cape_chains = len(CLOTHING_SPRING_PRESETS["cape"]["bone_chains"])
        ribbon_chains = len(CLOTHING_SPRING_PRESETS["ribbon"]["bone_chains"])
        assert cape_chains >= ribbon_chains

    def test_skirt_has_center_bone(self):
        """Skirt preset specifies a center bone for stability."""
        assert CLOTHING_SPRING_PRESETS["skirt"].get("center") is not None

    def test_clothing_stiff_force_within_range(self):
        """Clothing stiff_force values stay within VRM range."""
        for name, preset in CLOTHING_SPRING_PRESETS.items():
            assert 0 <= preset["stiff_force"] <= 10, f"{name} out of range"


class TestDefaultColliders:
    """Default collider list structure tests."""

    def test_default_colliders_exist(self):
        """The default collider list is non-empty."""
        assert len(DEFAULT_COLLIDERS) > 0

    def test_default_colliders_have_required_fields(self):
        """Each default collider dict has name, bone, offset, radius."""
        for collider in DEFAULT_COLLIDERS:
            assert "name" in collider
            assert "bone" in collider
            assert "offset" in collider
            assert "radius" in collider

    def test_head_collider_in_defaults(self):
        """Head collider is in the defaults (head is critical for hair)."""
        names = [c["name"] for c in DEFAULT_COLLIDERS]
        assert "head_collider" in names


# ══════════════════════════════════════════════════════════════════════
# configure_hair_spring tests
# ══════════════════════════════════════════════════════════════════════


class TestConfigureHairSpring:
    """Test configure_hair_spring with various HairPhysicsSpec values."""

    def test_default_spec(self):
        """Default HairPhysicsSpec produces valid spring config."""
        group = configure_hair_spring()
        assert group.name == "hair_spring"
        assert group.center == "head"
        assert len(group.bone_chains) > 0

    def test_with_custom_spec(self):
        """Custom HairPhysicsSpec maps to spring parameters."""
        spec = HairPhysicsSpec(stiffness=0.8, gravity=0.5, drag=0.3)
        group = configure_hair_spring(spec)
        # stiffness 0.8 → stiff_force = 0.1 + 0.8*4.9 = 4.02
        assert abs(group.stiff_force - 4.02) < 0.01
        # gravity 0.5 → gravity_power = 0.5 * 1.5 = 0.75
        assert abs(group.gravity_power - 0.75) < 0.01
        # drag 0.3 → drag_force = 0.2 + 0.3*0.6 = 0.38
        assert abs(group.drag_force - 0.38) < 0.01

    def test_stiffness_zero(self):
        """Zero stiffness produces minimum stiff_force."""
        spec = HairPhysicsSpec(stiffness=0.0, gravity=0.0, drag=0.0)
        group = configure_hair_spring(spec)
        assert group.stiff_force >= 0.1  # minimum floor

    def test_stiffness_maps_to_long_hair(self):
        """Low stiffness (≤0.6) selects long hair chain preset."""
        spec = HairPhysicsSpec(stiffness=0.3, gravity=0.3, drag=0.4)
        group = configure_hair_spring(spec)
        long_chains = HAIR_SPRING_PRESETS["long"]["bone_chains"]
        assert group.bone_chains == long_chains

    def test_stiffness_maps_to_medium_hair(self):
        """Medium stiffness (0.6–1.2) selects medium hair preset."""
        spec = HairPhysicsSpec(stiffness=0.8, gravity=0.3, drag=0.4)
        group = configure_hair_spring(spec)
        medium_chains = HAIR_SPRING_PRESETS["medium"]["bone_chains"]
        assert group.bone_chains == medium_chains

    def test_stiffness_maps_to_short_hair(self):
        """High stiffness (≥1.2) selects short hair preset."""
        spec = HairPhysicsSpec(stiffness=1.5, gravity=0.3, drag=0.4)
        group = configure_hair_spring(spec)
        short_chains = HAIR_SPRING_PRESETS["short"]["bone_chains"]
        assert group.bone_chains == short_chains

    def test_gravity_maps_to_power(self):
        """Gravity spec maps to gravity_power."""
        spec = HairPhysicsSpec(stiffness=0.5, gravity=0.7, drag=0.4)
        group = configure_hair_spring(spec)
        expected = 0.7 * 1.5  # 1.05
        assert abs(group.gravity_power - expected) < 0.01

    def test_has_head_collider_group(self):
        """Hair spring always references head and body colliders."""
        group = configure_hair_spring()
        assert "head_collider" in group.collider_groups
        assert "upper_body_collider" in group.collider_groups


# ══════════════════════════════════════════════════════════════════════
# configure_breast_spring tests
# ══════════════════════════════════════════════════════════════════════


class TestConfigureBreastSpring:
    """Test configure_breast_spring with various inputs."""

    def test_default_none(self):
        """Default (None) produces medium breast preset."""
        group = configure_breast_spring(None)
        assert group.name == "breast_spring"
        assert group.center == "spine_01"
        assert len(group.bone_chains) >= 2

    def test_with_BreastPhysicsSpec(self):
        """BreastPhysicsSpec maps to spring parameters."""
        spec = BreastPhysicsSpec(stiffness=0.4, drag=0.5)
        group = configure_breast_spring(spec)
        # stiff_force = 0.1 + 0.4 * 4.9 = 2.06
        assert abs(group.stiff_force - 2.06) < 0.01
        # drag_force = 0.2 + 0.5 * 0.6 = 0.5
        assert abs(group.drag_force - 0.5) < 0.01

    def test_dict_small_bust(self):
        """Dict with small bust selects small preset."""
        body = {"bust": 0.3}
        group = configure_breast_spring(body)
        assert group.bone_chains == BREAST_SPRING_PRESETS["small"]["bone_chains"]

    def test_dict_medium_bust(self):
        """Dict with medium bust selects medium preset."""
        body = {"bust": 0.55}
        group = configure_breast_spring(body)
        assert group.bone_chains == BREAST_SPRING_PRESETS["medium"]["bone_chains"]

    def test_dict_large_bust(self):
        """Dict with large bust selects large preset."""
        body = {"bust": 0.8}
        group = configure_breast_spring(body)
        assert group.bone_chains == BREAST_SPRING_PRESETS["large"]["bone_chains"]

    def test_has_upper_body_collider(self):
        """Breast spring references upper body collider."""
        group = configure_breast_spring(None)
        assert "upper_body_collider" in group.collider_groups


# ══════════════════════════════════════════════════════════════════════
# configure_clothing_spring tests
# ══════════════════════════════════════════════════════════════════════


class TestConfigureClothingSpring:
    """Test configure_clothing_spring for various clothing types."""

    def test_skirt_type(self):
        """Skirt type looks up the skirt preset."""
        group = configure_clothing_spring("school_skirt", "skirt")
        assert group.name == "school_skirt_spring"
        assert group.bone_chains == CLOTHING_SPRING_PRESETS["skirt"]["bone_chains"]

    def test_cape_type(self):
        """Cape type looks up the cape preset."""
        group = configure_clothing_spring("hero_cape", "cape")
        assert group.name == "hero_cape_spring"
        assert group.stiff_force == CLOTHING_SPRING_PRESETS["cape"]["stiff_force"]

    def test_ribbon_type(self):
        """Ribbon type looks up the ribbon preset."""
        group = configure_clothing_spring("hair_ribbon", "ribbon")
        assert group.name == "hair_ribbon_spring"
        assert group.stiff_force == CLOTHING_SPRING_PRESETS["ribbon"]["stiff_force"]

    def test_unknown_type_defaults_to_skirt(self):
        """Unknown cloth type defaults to skirt."""
        group = configure_clothing_spring("mystery_cloth", "unknown_type")
        assert group.stiff_force == CLOTHING_SPRING_PRESETS["skirt"]["stiff_force"]

    def test_clothing_name_in_group_name(self):
        """Group name includes the clothing identifier."""
        group = configure_clothing_spring("maid_apron", "skirt")
        assert "maid_apron" in group.name

    def test_skirt_has_center_bone(self):
        """Skirt spring group specifies a center bone."""
        group = configure_clothing_spring("test_skirt", "skirt")
        assert group.center is not None


# ══════════════════════════════════════════════════════════════════════
# Blender-dependent tests (marked @pytest.mark.blender)
# ══════════════════════════════════════════════════════════════════════


class TestApplySpringBonesBlender:
    """Blender-dependent tests for apply_spring_bones."""

    def test_raises_without_bpy(self):
        """apply_spring_bones raises RuntimeError without bpy."""
        # This test only passes outside Blender
        from hamr.rigs.spring_bones import BLENDER_AVAILABLE
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy not available"):
                apply_spring_bones("armature", [], [])