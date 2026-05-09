"""
Tests for hamr.rigs.poses — Pose Library for Phase 16, Task T3.

Tests cover BonePose, PosePreset, POSE_PRESETS, validation,
blending, category queries, lookups, and VRM conversion.
"""

from __future__ import annotations

import math
import pytest

from hamr.rigs.poses import (
    BonePose,
    PosePreset,
    POSE_PRESETS,
    VALID_BONE_NAMES,
    VALID_BLEND_SHAPES,
    validate_pose,
    create_pose,
    blend_poses,
    get_poses_by_category,
    get_pose,
    list_pose_names,
    list_categories,
    pose_to_vrm,
)


# ═══════════════════════════════════════════════════════════════════════════════
# BonePose dataclass tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBonePose:
    """Test BonePose creation and defaults."""

    def test_defaults(self):
        """BonePose defaults: position=(0,0,0), rotation=(0,0,0), scale=(1,1,1)."""
        bp = BonePose(bone_name="head")
        assert bp.bone_name == "head"
        assert bp.position == (0.0, 0.0, 0.0)
        assert bp.rotation == (0.0, 0.0, 0.0)
        assert bp.scale == (1.0, 1.0, 1.0)

    def test_custom_transforms(self):
        """BonePose with custom position, rotation, scale."""
        bp = BonePose(
            bone_name="leftUpperArm",
            position=(0.1, 0.2, 0.3),
            rotation=(10.0, 20.0, 30.0),
            scale=(1.0, 1.0, 1.0),
        )
        assert bp.bone_name == "leftUpperArm"
        assert bp.position == (0.1, 0.2, 0.3)
        assert bp.rotation == (10.0, 20.0, 30.0)
        assert bp.scale == (1.0, 1.0, 1.0)

    def test_asymmetric_scale(self):
        """BonePose with non-uniform scale."""
        bp = BonePose(bone_name="spine", scale=(0.5, 1.2, 1.0))
        assert bp.scale == (0.5, 1.2, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# PosePreset dataclass tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPosePreset:
    """Test PosePreset creation and defaults."""

    def test_defaults(self):
        """PosePreset defaults: empty bones list, empty blend_shapes dict."""
        pp = PosePreset(name="test", category="body")
        assert pp.name == "test"
        assert pp.category == "body"
        assert pp.description == ""
        assert pp.bones == []
        assert pp.blend_shapes == {}

    def test_with_bones_and_blend_shapes(self):
        """PosePreset with bones and blend shapes."""
        pp = PosePreset(
            name="smile",
            category="face",
            description="A smile",
            bones=[BonePose(bone_name="jaw")],
            blend_shapes={"happy": 0.5},
        )
        assert pp.name == "smile"
        assert pp.category == "face"
        assert len(pp.bones) == 1
        assert pp.blend_shapes["happy"] == 0.5

    def test_blend_shapes_default_factory(self):
        """Each PosePreset gets its own blend_shapes dict."""
        pp1 = PosePreset(name="a", category="face")
        pp2 = PosePreset(name="b", category="face")
        pp1.blend_shapes["happy"] = 0.5
        assert "happy" not in pp2.blend_shapes


# ═══════════════════════════════════════════════════════════════════════════════
# POSE_PRESETS structure tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPosePresets:
    """Test POSE_PRESETS dict has entries in all 5 categories."""

    def test_presets_exist(self):
        """POSE_PRESETS dict is non-empty."""
        assert len(POSE_PRESETS) > 0

    def test_rest_category(self):
        """POSE_PRESETS has entries in 'rest' category."""
        rest_poses = get_poses_by_category("rest")
        assert len(rest_poses) >= 2  # t_pose, a_pose
        names = {p.name for p in rest_poses}
        assert "t_pose" in names
        assert "a_pose" in names

    def test_hand_category(self):
        """POSE_PRESETS has entries in 'hand' category."""
        hand_poses = get_poses_by_category("hand")
        assert len(hand_poses) >= 6  # all 6 hand poses
        names = {p.name for p in hand_poses}
        assert "hand_open" in names
        assert "hand_fist" in names
        assert "hand_point" in names
        assert "hand_peace" in names
        assert "hand_grip" in names
        assert "hand_relax" in names

    def test_face_category(self):
        """POSE_PRESETS has entries in 'face' category."""
        face_poses = get_poses_by_category("face")
        assert len(face_poses) >= 6  # all 6 face presets
        names = {p.name for p in face_poses}
        assert "face_neutral" in names
        assert "face_smile" in names
        assert "face_blink" in names
        assert "face_mouth_open" in names
        assert "face_angry" in names
        assert "face_surprise" in names

    def test_all_five_categories_present(self):
        """At least 'rest', 'hand', 'face' categories are present."""
        cats = list_categories()
        # We currently only populate rest, hand, face
        # body and action are valid but may be empty
        assert "rest" in cats
        assert "hand" in cats
        assert "face" in cats

    def test_t_pose_has_arm_rotations(self):
        """T-pose has left arm at +90° and right arm at -90°."""
        t_pose = POSE_PRESETS["t_pose"]
        bones = {b.bone_name: b for b in t_pose.bones}
        assert abs(bones["leftUpperArm"].rotation[2] - 90.0) < 0.01
        assert abs(bones["rightUpperArm"].rotation[2] - (-90.0)) < 0.01

    def test_a_pose_has_arm_rotations(self):
        """A-pose has left arm at +60° and right arm at -60°."""
        a_pose = POSE_PRESETS["a_pose"]
        bones = {b.bone_name: b for b in a_pose.bones}
        assert abs(bones["leftUpperArm"].rotation[2] - 60.0) < 0.01
        assert abs(bones["rightUpperArm"].rotation[2] - (-60.0)) < 0.01

    def test_face_smile_blend_shapes(self):
        """face_smile has happy=0.3 and eyeSquint=0.1."""
        smile = POSE_PRESETS["face_smile"]
        assert smile.blend_shapes.get("happy") == pytest.approx(0.3)
        assert smile.blend_shapes.get("eyeSquint") == pytest.approx(0.1)

    def test_face_blink_blend_shapes(self):
        """face_blink has eyeClose=1.0."""
        blink = POSE_PRESETS["face_blink"]
        assert blink.blend_shapes.get("eyeClose") == pytest.approx(1.0)

    def test_face_neutral_no_blend_shapes(self):
        """face_neutral has empty blend shapes."""
        neutral = POSE_PRESETS["face_neutral"]
        assert neutral.blend_shapes == {}


# ═══════════════════════════════════════════════════════════════════════════════
# validate_pose tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidatePose:
    """Test validate_pose function."""

    def test_valid_pose_no_errors(self):
        """A valid pose returns an empty error list."""
        pose = PosePreset(
            name="valid_test",
            category="body",
            bones=[BonePose(bone_name="head")],
        )
        errors = validate_pose(pose)
        assert errors == []

    def test_invalid_bone_name(self):
        """Invalid bone name produces an error."""
        pose = PosePreset(
            name="bad_bone",
            category="body",
            bones=[BonePose(bone_name="not_a_real_bone")],
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("not_a_real_bone" in e for e in errors)

    def test_out_of_range_rotation(self):
        """Rotation exceeding ±360° produces an error."""
        pose = PosePreset(
            name="extreme_rotation",
            category="body",
            bones=[BonePose(bone_name="head", rotation=(0.0, 0.0, 500.0))],
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("rotation" in e.lower() or "range" in e.lower() for e in errors)

    def test_negative_scale(self):
        """Negative scale values produce an error."""
        pose = PosePreset(
            name="neg_scale",
            category="body",
            bones=[BonePose(bone_name="head", scale=(-1.0, 1.0, 1.0))],
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("scale" in e.lower() or "positive" in e.lower() for e in errors)

    def test_invalid_blend_shape_name(self):
        """Invalid blend shape name produces an error."""
        pose = PosePreset(
            name="bad_blend",
            category="face",
            bones=[],
            blend_shapes={"nonexistent_shape": 0.5},
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("nonexistent_shape" in e for e in errors)

    def test_blend_shape_weight_out_of_range(self):
        """Blend shape weight > 1.0 produces an error."""
        pose = PosePreset(
            name="high_weight",
            category="face",
            bones=[],
            blend_shapes={"happy": 1.5},
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("weight" in e.lower() or "range" in e.lower() for e in errors)

    def test_blend_shape_weight_negative(self):
        """Negative blend shape weight produces an error."""
        pose = PosePreset(
            name="neg_weight",
            category="face",
            bones=[],
            blend_shapes={"happy": -0.5},
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("weight" in e.lower() for e in errors)

    def test_invalid_category(self):
        """Invalid category produces an error."""
        pose = PosePreset(
            name="bad_cat",
            category="invalid",
            bones=[],
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("invalid" in e.lower() or "category" in e.lower() for e in errors)

    def test_all_presets_are_valid(self):
        """All built-in POSE_PRESETS pass validation."""
        for name, preset in POSE_PRESETS.items():
            errors = validate_pose(preset)
            assert errors == [], f"Pose '{name}' has validation errors: {errors}"

    def test_duplicate_bone_name(self):
        """Duplicate bone name produces an error."""
        pose = PosePreset(
            name="dup_bone",
            category="body",
            bones=[
                BonePose(bone_name="head"),
                BonePose(bone_name="head"),
            ],
        )
        errors = validate_pose(pose)
        assert len(errors) >= 1
        assert any("duplicate" in e.lower() for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# create_pose tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreatePose:
    """Test create_pose function."""

    def test_basic_creation(self):
        """create_pose with bones and blend shapes."""
        pose = create_pose(
            name="custom",
            category="body",
            bones=[BonePose(bone_name="head", rotation=(5.0, 0.0, 0.0))],
            blend_shapes={"happy": 0.2},
        )
        assert pose.name == "custom"
        assert pose.category == "body"
        assert len(pose.bones) == 1
        assert pose.blend_shapes == {"happy": 0.2}

    def test_creation_without_blend_shapes(self):
        """create_pose with None blend_shapes defaults to empty dict."""
        pose = create_pose(
            name="just_bones",
            category="action",
            bones=[BonePose(bone_name="hips")],
        )
        assert pose.blend_shapes == {}

    def test_creation_with_description(self):
        """create_pose with description."""
        pose = create_pose(
            name="described_pose",
            category="rest",
            bones=[],
            description="A very descriptive description",
        )
        assert pose.description == "A very descriptive description"

    def test_blend_shapes_is_independent_copy(self):
        """blend_shapes dict is copied, not shared with caller."""
        original = {"happy": 0.3}
        pose = create_pose(
            name="independent",
            category="face",
            bones=[],
            blend_shapes=original,
        )
        original["happy"] = 0.9
        assert pose.blend_shapes["happy"] == pytest.approx(0.3)


# ═══════════════════════════════════════════════════════════════════════════════
# blend_poses tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBlendPoses:
    """Test blend_poses function (lerp between poses)."""

    def _make_pose_a(self):
        return PosePreset(
            name="pose_a",
            category="hand",
            bones=[
                BonePose(bone_name="leftIndexProximal", rotation=(-90.0, 0.0, 0.0)),
                BonePose(bone_name="leftIndexDistal", rotation=(-70.0, 0.0, 0.0)),
            ],
            blend_shapes={"happy": 0.0},
        )

    def _make_pose_b(self):
        return PosePreset(
            name="pose_b",
            category="face",
            bones=[
                BonePose(bone_name="leftIndexProximal", rotation=(0.0, 0.0, 0.0)),
                BonePose(bone_name="leftIndexDistal", rotation=(-5.0, 0.0, 0.0)),
            ],
            blend_shapes={"happy": 1.0},
        )

    def test_blend_at_t0(self):
        """At t=0, blended pose equals pose a."""
        a = self._make_pose_a()
        b = self._make_pose_b()
        result = blend_poses(a, b, t=0.0)
        # Rotation should equal a's rotation
        bones = {bp.bone_name: bp for bp in result.bones}
        assert bones["leftIndexProximal"].rotation[0] == pytest.approx(-90.0)
        assert bones["leftIndexDistal"].rotation[0] == pytest.approx(-70.0)
        # Blend shape at t=0 → 0.0
        assert result.blend_shapes["happy"] == pytest.approx(0.0)

    def test_blend_at_t1(self):
        """At t=1, blended pose equals pose b."""
        a = self._make_pose_a()
        b = self._make_pose_b()
        result = blend_poses(a, b, t=1.0)
        bones = {bp.bone_name: bp for bp in result.bones}
        assert bones["leftIndexProximal"].rotation[0] == pytest.approx(0.0)
        assert bones["leftIndexDistal"].rotation[0] == pytest.approx(-5.0)
        assert result.blend_shapes["happy"] == pytest.approx(1.0)

    def test_blend_at_t_half(self):
        """At t=0.5, blended pose is midpoint between a and b."""
        a = self._make_pose_a()
        b = self._make_pose_b()
        result = blend_poses(a, b, t=0.5)
        bones = {bp.bone_name: bp for bp in result.bones}
        assert bones["leftIndexProximal"].rotation[0] == pytest.approx(-45.0)
        assert bones["leftIndexDistal"].rotation[0] == pytest.approx(-37.5)
        assert result.blend_shapes["happy"] == pytest.approx(0.5)

    def test_blend_mismatched_bones_raises(self):
        """Blending poses with different bone sets raises ValueError."""
        a = PosePreset(
            name="a",
            category="rest",
            bones=[BonePose(bone_name="head")],
        )
        b = PosePreset(
            name="b",
            category="rest",
            bones=[BonePose(bone_name="hips")],
        )
        with pytest.raises(ValueError, match="not found"):
            blend_poses(a, b, t=0.5)

    def test_blend_clamps_t(self):
        """blend_poses clamps t to [0, 1]."""
        a = self._make_pose_a()
        b = self._make_pose_b()
        result_low = blend_poses(a, b, t=-0.5)
        bones_low = {bp.bone_name: bp for bp in result_low.bones}
        assert bones_low["leftIndexProximal"].rotation[0] == pytest.approx(-90.0)

        result_high = blend_poses(a, b, t=1.5)
        bones_high = {bp.bone_name: bp for bp in result_high.bones}
        assert bones_high["leftIndexProximal"].rotation[0] == pytest.approx(0.0)

    def test_blend_preserves_scale(self):
        """blend_poses lerps scale correctly."""
        a = PosePreset(
            name="a",
            category="body",
            bones=[BonePose(bone_name="head", scale=(1.0, 1.0, 1.0))],
        )
        b = PosePreset(
            name="b",
            category="body",
            bones=[BonePose(bone_name="head", scale=(2.0, 2.0, 2.0))],
        )
        result = blend_poses(a, b, t=0.5)
        bones = {bp.bone_name: bp for bp in result.bones}
        for i in range(3):
            assert bones["head"].scale[i] == pytest.approx(1.5)

    def test_blend_blend_shape_in_a_only(self):
        """Blend shape present in a but not b uses 0 for b."""
        a = PosePreset(
            name="a", category="face",
            bones=[BonePose(bone_name="head")],
            blend_shapes={"happy": 0.4},
        )
        b = PosePreset(
            name="b", category="face",
            bones=[BonePose(bone_name="head")],
            blend_shapes={},
        )
        result = blend_poses(a, b, t=0.5)
        assert result.blend_shapes["happy"] == pytest.approx(0.2)


# ═══════════════════════════════════════════════════════════════════════════════
# get_poses_by_category tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetPosesByCategory:
    """Test get_poses_by_category function."""

    def test_rest_category(self):
        """get_poses_by_category('rest') returns t_pose and a_pose."""
        poses = get_poses_by_category("rest")
        assert len(poses) >= 2
        names = {p.name for p in poses}
        assert "t_pose" in names
        assert "a_pose" in names

    def test_hand_category(self):
        """get_poses_by_category('hand') returns hand poses."""
        poses = get_poses_by_category("hand")
        assert len(poses) >= 6

    def test_face_category(self):
        """get_poses_by_category('face') returns face poses."""
        poses = get_poses_by_category("face")
        assert len(poses) >= 6

    def test_empty_category(self):
        """get_poses_by_category('action') returns empty list if not populated."""
        poses = get_poses_by_category("action")
        assert isinstance(poses, list)
        # May be empty or populated depending on presets

    def test_invalid_category(self):
        """get_poses_by_category with unknown category returns empty list."""
        poses = get_poses_by_category("nonexistent")
        assert poses == []


# ═══════════════════════════════════════════════════════════════════════════════
# get_pose tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetPose:
    """Test get_pose lookup function."""

    def test_get_t_pose(self):
        """get_pose('t_pose') returns the T-pose preset."""
        pose = get_pose("t_pose")
        assert pose.name == "t_pose"
        assert pose.category == "rest"

    def test_get_hand_fist(self):
        """get_pose('hand_fist') returns the fist preset."""
        pose = get_pose("hand_fist")
        assert pose.name == "hand_fist"
        assert pose.category == "hand"

    def test_get_face_smile(self):
        """get_pose('face_smile') returns the smile preset."""
        pose = get_pose("face_smile")
        assert pose.name == "face_smile"
        assert pose.category == "face"
        assert "happy" in pose.blend_shapes

    def test_get_nonexistent_raises(self):
        """get_pose with unknown name raises KeyError."""
        with pytest.raises(KeyError, match="nonexistent_pose"):
            get_pose("nonexistent_pose")


# ═══════════════════════════════════════════════════════════════════════════════
# list_pose_names tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestListPoseNames:
    """Test list_pose_names function."""

    def test_returns_sorted_list(self):
        """list_pose_names returns a sorted list of names."""
        names = list_pose_names()
        assert names == sorted(names)

    def test_contains_expected_count(self):
        """list_pose_names returns at least 14 names (2 rest + 6 hand + 6 face)."""
        names = list_pose_names()
        assert len(names) >= 14

    def test_contains_key_poses(self):
        """list_pose_names contains all expected pose names."""
        names = list_pose_names()
        expected = {
            "t_pose", "a_pose",
            "hand_open", "hand_fist", "hand_point", "hand_peace",
            "hand_grip", "hand_relax",
            "face_neutral", "face_smile", "face_blink",
            "face_mouth_open", "face_angry", "face_surprise",
        }
        assert expected.issubset(set(names))


# ═══════════════════════════════════════════════════════════════════════════════
# list_categories tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestListCategories:
    """Test list_categories function."""

    def test_returns_sorted_unique(self):
        """list_categories returns sorted list of unique categories."""
        cats = list_categories()
        assert cats == sorted(cats)
        assert len(cats) == len(set(cats))

    def test_contains_core_categories(self):
        """list_categories includes rest, hand, face."""
        cats = list_categories()
        assert "rest" in cats
        assert "hand" in cats
        assert "face" in cats


# ═══════════════════════════════════════════════════════════════════════════════
# pose_to_vrm tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPoseToVrm:
    """Test pose_to_vrm conversion function."""

    def test_produces_dict(self):
        """pose_to_vrm returns a dict."""
        pose = POSE_PRESETS["t_pose"]
        result = pose_to_vrm(pose)
        assert isinstance(result, dict)

    def test_has_extensions_key(self):
        """VRM dict has 'extensions' key."""
        pose = POSE_PRESETS["t_pose"]
        result = pose_to_vrm(pose)
        assert "extensions" in result

    def test_has_vrmc_vrm_key(self):
        """VRM dict has VRMC_vrm nested key."""
        pose = POSE_PRESETS["t_pose"]
        result = pose_to_vrm(pose)
        assert "VRMC_vrm" in result["extensions"]

    def test_has_humanoid_key(self):
        """VRM dict has humanoid key."""
        pose = POSE_PRESETS["t_pose"]
        result = pose_to_vrm(pose)
        assert "humanoid" in result["extensions"]["VRMC_vrm"]

    def test_has_restpose_key(self):
        """VRM dict has restPose mapping."""
        pose = POSE_PRESETS["t_pose"]
        result = pose_to_vrm(pose)
        rest_pose = result["extensions"]["VRMC_vrm"]["humanoid"]["restPose"]
        assert isinstance(rest_pose, dict)
        assert len(rest_pose) > 0

    def test_bone_rotation_format(self):
        """Each bone in restPose has x, y, z rotation keys."""
        pose = POSE_PRESETS["a_pose"]
        result = pose_to_vrm(pose)
        rest_pose = result["extensions"]["VRMC_vrm"]["humanoid"]["restPose"]

        # Check a specific bone
        left_arm = rest_pose.get("leftUpperArm")
        assert left_arm is not None
        assert "x" in left_arm
        assert "y" in left_arm
        assert "z" in left_arm
        assert left_arm["z"] == pytest.approx(60.0)

    def test_blend_shapes_in_vrm(self):
        """Face poses with blend shapes include expression data in VRM dict."""
        pose = POSE_PRESETS["face_smile"]
        result = pose_to_vrm(pose)
        # face_smile has "happy" which is a VRM preset expression
        vrmc = result["extensions"]["VRMC_vrm"]
        assert "expressions" in vrmc
        assert "preset" in vrmc["expressions"]
        assert "happy" in vrmc["expressions"]["preset"]
        assert vrmc["expressions"]["preset"]["happy"]["weight"] == pytest.approx(0.3)

    def test_face_neutral_no_expressions(self):
        """face_neutral has no blend shapes, so no expressions key."""
        pose = POSE_PRESETS["face_neutral"]
        result = pose_to_vrm(pose)
        vrmc = result["extensions"]["VRMC_vrm"]
        # No blend shapes → no expressions key
        assert "expressions" not in vrmc