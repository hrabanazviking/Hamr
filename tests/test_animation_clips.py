"""
Tests for hamr.export.animation_clips — Animation preset clips for VRM avatars.

Phase 13 T4: idle_breathe, idle_shift_weight, idle_look_around, walk_cycle_ref
"""

from __future__ import annotations

import math
import pytest

from hamr.export.animation_clips import (
    AnimationKeyframe,
    AnimationClip,
    PRESET_CLIPS,
    create_clip,
    create_keyframe,
    get_preset_clips,
    keyframes_to_dict,
    validate_clip,
    MB_LAB_TO_VRM,
    _VALID_BONE_NAMES,
)


# ── AnimationKeyframe tests ───────────────────────────────────────


class TestAnimationKeyframe:
    """Test AnimationKeyframe creation and defaults."""

    def test_default_position(self):
        kf = AnimationKeyframe(time=0.0, bone="spine")
        assert kf.position == (0.0, 0.0, 0.0)

    def test_default_rotation(self):
        kf = AnimationKeyframe(time=0.0, bone="spine")
        assert kf.rotation == (0.0, 0.0, 0.0)

    def test_default_scale(self):
        kf = AnimationKeyframe(time=0.0, bone="spine")
        assert kf.scale == (1.0, 1.0, 1.0)

    def test_custom_values(self):
        kf = AnimationKeyframe(
            time=1.5,
            bone="head",
            position=(0.01, 0.02, 0.03),
            rotation=(-2.0, 15.0, 0.0),
            scale=(1.0, 1.02, 1.0),
        )
        assert kf.time == 1.5
        assert kf.bone == "head"
        assert kf.position == (0.01, 0.02, 0.03)
        assert kf.rotation == (-2.0, 15.0, 0.0)
        assert kf.scale == (1.0, 1.02, 1.0)

    def test_defaults_are_immutable_tuples(self):
        kf = AnimationKeyframe(time=0.0, bone="hips")
        assert isinstance(kf.position, tuple)
        assert isinstance(kf.rotation, tuple)
        assert isinstance(kf.scale, tuple)


# ── AnimationClip tests ──────────────────────────────────────────


class TestAnimationClip:
    """Test AnimationClip creation and defaults."""

    def test_default_fps(self):
        clip = AnimationClip(name="test", duration=1.0)
        assert clip.fps == 30

    def test_default_loop(self):
        clip = AnimationClip(name="test", duration=1.0)
        assert clip.loop is True

    def test_default_keyframes(self):
        clip = AnimationClip(name="test", duration=1.0)
        assert clip.keyframes == []

    def test_custom_keyframes(self):
        kfs = [
            AnimationKeyframe(time=0.0, bone="spine"),
            AnimationKeyframe(time=0.5, bone="spine", rotation=(0.0, 15.0, 0.0)),
        ]
        clip = AnimationClip(name="test", duration=1.0, keyframes=kfs)
        assert len(clip.keyframes) == 2
        assert clip.keyframes[0].time == 0.0
        assert clip.keyframes[1].rotation == (0.0, 15.0, 0.0)

    def test_each_clip_gets_distinct_keyframes_list(self):
        clip_a = AnimationClip(name="a", duration=1.0)
        clip_b = AnimationClip(name="b", duration=2.0)
        clip_a.keyframes.append(AnimationKeyframe(time=0.0, bone="hips"))
        assert len(clip_a.keyframes) == 1
        assert len(clip_b.keyframes) == 0


# ── create_keyframe convenience ──────────────────────────────────


class TestCreateKeyframe:
    """Test create_keyframe convenience function."""

    def test_basic_creation(self):
        kf = create_keyframe(time=0.5, bone="head", rotation=(-2.0, 0.0, 0.0))
        assert kf.time == 0.5
        assert kf.bone == "head"
        assert kf.rotation == (-2.0, 0.0, 0.0)
        assert kf.position == (0.0, 0.0, 0.0)
        assert kf.scale == (1.0, 1.0, 1.0)

    def test_rotation_before_position(self):
        """Spec convention: rotation comes before position in args."""
        kf = create_keyframe(
            time=0.0,
            bone="hips",
            rotation=(1.0, 2.0, 3.0),
            position=(0.01, 0.02, 0.03),
        )
        assert kf.rotation == (1.0, 2.0, 3.0)
        assert kf.position == (0.01, 0.02, 0.03)

    def test_all_defaults(self):
        kf = create_keyframe(time=0.0, bone="spine")
        assert kf.position == (0.0, 0.0, 0.0)
        assert kf.rotation == (0.0, 0.0, 0.0)
        assert kf.scale == (1.0, 1.0, 1.0)


# ── create_clip convenience ──────────────────────────────────────


class TestCreateClip:
    """Test create_clip convenience function."""

    def test_defaults(self):
        clip = create_clip(name="test_clip", duration=2.0)
        assert clip.name == "test_clip"
        assert clip.duration == 2.0
        assert clip.fps == 30
        assert clip.loop is True
        assert clip.keyframes == []

    def test_custom_fps_and_loop(self):
        clip = create_clip(name="fast", duration=0.5, fps=60, loop=False)
        assert clip.fps == 60
        assert clip.loop is False


# ── PRESET_CLIPS tests ───────────────────────────────────────────


class TestPresetClips:
    """Test PRESET_CLIPS container has all 4 presets."""

    EXPECTED_NAMES = [
        "idle_breathe",
        "idle_shift_weight",
        "idle_look_around",
        "walk_cycle_ref",
    ]

    def test_preset_clips_has_four_entries(self):
        assert len(PRESET_CLIPS) == 4

    @pytest.mark.parametrize("name", EXPECTED_NAMES)
    def test_preset_exists(self, name):
        assert name in PRESET_CLIPS

    @pytest.mark.parametrize("name", EXPECTED_NAMES)
    def test_preset_name_matches_key(self, name):
        clip = PRESET_CLIPS[name]
        assert clip.name == name

    @pytest.mark.parametrize("name", EXPECTED_NAMES)
    def test_preset_has_keyframes(self, name):
        clip = PRESET_CLIPS[name]
        assert len(clip.keyframes) > 0

    @pytest.mark.parametrize("name", EXPECTED_NAMES)
    def test_preset_keyframe_times_in_range(self, name):
        clip = PRESET_CLIPS[name]
        for kf in clip.keyframes:
            assert kf.time >= 0, f"{name}: time {kf.time} < 0"
            assert kf.time <= clip.duration, (
                f"{name}: time {kf.time} > duration {clip.duration}"
            )

    @pytest.mark.parametrize("name", EXPECTED_NAMES)
    def test_preset_duration_is_positive(self, name):
        clip = PRESET_CLIPS[name]
        assert clip.duration > 0

    @pytest.mark.parametrize("name", EXPECTED_NAMES)
    def test_preset_loop_is_true(self, name):
        clip = PRESET_CLIPS[name]
        assert clip.loop is True


# ── idle_breathe specific tests ───────────────────────────────────


class TestIdleBreathe:
    """Test idle_breathe preset targets correct bones."""

    def test_targets_spine_and_head(self):
        clip = PRESET_CLIPS["idle_breathe"]
        bones = {kf.bone for kf in clip.keyframes}
        assert "spine" in bones
        assert "head" in bones

    def test_duration_2_5(self):
        clip = PRESET_CLIPS["idle_breathe"]
        assert clip.duration == 2.5

    def test_spine_scale_animates(self):
        clip = PRESET_CLIPS["idle_breathe"]
        spine_kfs = [kf for kf in clip.keyframes if kf.bone == "spine"]
        scales = [kf.scale for kf in spine_kfs]
        # At least one non-default scale
        assert any(s != (1.0, 1.0, 1.0) for s in scales)

    def test_head_rotation_animates(self):
        clip = PRESET_CLIPS["idle_breathe"]
        head_kfs = [kf for kf in clip.keyframes if kf.bone == "head"]
        rotations = [kf.rotation for kf in head_kfs]
        # At least one non-zero rotation
        assert any(r != (0.0, 0.0, 0.0) for r in rotations)


# ── idle_shift_weight specific tests ──────────────────────────────


class TestIdleShiftWeight:
    """Test idle_shift_weight preset targets correct bones."""

    def test_targets_hips_and_spine(self):
        clip = PRESET_CLIPS["idle_shift_weight"]
        bones = {kf.bone for kf in clip.keyframes}
        assert "hips" in bones
        assert "spine" in bones

    def test_duration_4(self):
        clip = PRESET_CLIPS["idle_shift_weight"]
        assert clip.duration == 4.0


# ── idle_look_around specific tests ───────────────────────────────


class TestIdleLookAround:
    """Test idle_look_around preset targets correct bones."""

    def test_targets_neck_and_head(self):
        clip = PRESET_CLIPS["idle_look_around"]
        bones = {kf.bone for kf in clip.keyframes}
        assert "neck" in bones
        assert "head" in bones

    def test_duration_6(self):
        clip = PRESET_CLIPS["idle_look_around"]
        assert clip.duration == 6.0

    def test_neck_y_rotation_range(self):
        clip = PRESET_CLIPS["idle_look_around"]
        neck_kfs = [kf for kf in clip.keyframes if kf.bone == "neck"]
        y_rotations = [kf.rotation[1] for kf in neck_kfs]
        # Max Y rotation should be 15° or -15°
        assert max(y_rotations) <= 15.0
        assert min(y_rotations) >= -15.0


# ── walk_cycle_ref specific tests ─────────────────────────────────


class TestWalkCycleRef:
    """Test walk_cycle_ref preset targets correct bones."""

    def test_targets_hips(self):
        clip = PRESET_CLIPS["walk_cycle_ref"]
        bones = {kf.bone for kf in clip.keyframes}
        assert "hips" in bones

    def test_targets_legs(self):
        clip = PRESET_CLIPS["walk_cycle_ref"]
        bones = {kf.bone for kf in clip.keyframes}
        assert "leftUpperLeg" in bones
        assert "rightUpperLeg" in bones
        assert "leftLowerLeg" in bones
        assert "rightLowerLeg" in bones

    def test_targets_arms(self):
        clip = PRESET_CLIPS["walk_cycle_ref"]
        bones = {kf.bone for kf in clip.keyframes}
        assert "leftUpperArm" in bones
        assert "rightUpperArm" in bones

    def test_duration_0_8(self):
        clip = PRESET_CLIPS["walk_cycle_ref"]
        assert clip.duration == 0.8

    def test_hip_has_position_animation(self):
        clip = PRESET_CLIPS["walk_cycle_ref"]
        hip_kfs = [kf for kf in clip.keyframes if kf.bone == "hips"]
        positions = [kf.position for kf in hip_kfs]
        # At least one non-zero position
        assert any(p != (0.0, 0.0, 0.0) for p in positions)

    def test_legs_have_rotation_animation(self):
        clip = PRESET_CLIPS["walk_cycle_ref"]
        leg_kfs = [
            kf for kf in clip.keyframes
            if kf.bone in ("leftUpperLeg", "rightUpperLeg")
        ]
        rotations = [kf.rotation for kf in leg_kfs]
        assert any(r != (0.0, 0.0, 0.0) for r in rotations)


# ── validate_clip tests ──────────────────────────────────────────


class TestValidateClip:
    """Test validate_clip catches errors and passes valid clips."""

    def test_catches_invalid_bone_name(self):
        clip = AnimationClip(
            name="bad_bone",
            duration=1.0,
            keyframes=[
                AnimationKeyframe(time=0.0, bone="totally_fake_bone"),
            ],
        )
        warnings = validate_clip(clip)
        assert len(warnings) > 0
        assert any("unknown bone" in w for w in warnings)

    def test_catches_negative_time(self):
        clip = AnimationClip(
            name="neg_time",
            duration=2.0,
            keyframes=[
                AnimationKeyframe(time=-0.5, bone="spine"),
            ],
        )
        warnings = validate_clip(clip)
        assert any("negative time" in w for w in warnings)

    def test_catches_time_exceeds_duration(self):
        clip = AnimationClip(
            name="over_duration",
            duration=1.0,
            keyframes=[
                AnimationKeyframe(time=2.0, bone="spine"),
            ],
        )
        warnings = validate_clip(clip)
        assert any("exceeds duration" in w for w in warnings)

    def test_catches_zero_duration(self):
        clip = AnimationClip(
            name="zero_dur",
            duration=0.0,
            keyframes=[],
        )
        warnings = validate_clip(clip)
        assert any("non-positive duration" in w for w in warnings)

    def test_catches_negative_duration(self):
        clip = AnimationClip(
            name="neg_dur",
            duration=-1.0,
            keyframes=[],
        )
        warnings = validate_clip(clip)
        assert any("non-positive duration" in w for w in warnings)

    def test_passes_for_valid_clip(self):
        clip = create_clip(name="valid", duration=2.0)
        clip.keyframes = [
            AnimationKeyframe(time=0.0, bone="spine"),
            AnimationKeyframe(time=1.0, bone="spine", rotation=(0.0, 10.0, 0.0)),
            AnimationKeyframe(time=2.0, bone="spine"),
        ]
        warnings = validate_clip(clip)
        assert warnings == []

    def test_passes_for_all_presets(self):
        """All four preset clips should validate cleanly."""
        for name, clip in PRESET_CLIPS.items():
            warnings = validate_clip(clip)
            assert warnings == [], (
                f"Preset '{name}' has validation warnings: {warnings}"
            )

    def test_mb_lab_alias_bones_are_valid(self):
        """MB-Lab bone names should be accepted by validation."""
        clip = AnimationClip(
            name="mblab_test",
            duration=1.0,
            keyframes=[
                AnimationKeyframe(time=0.0, bone="pelvis"),
                AnimationKeyframe(time=0.0, bone="spine_01"),
                AnimationKeyframe(time=0.0, bone="clavicle_L"),
            ],
        )
        warnings = validate_clip(clip)
        assert warnings == []

    def test_time_at_duration_boundary_is_valid(self):
        """Time exactly equal to duration should be valid (loop point)."""
        clip = AnimationClip(
            name="boundary",
            duration=2.0,
            keyframes=[
                AnimationKeyframe(time=0.0, bone="spine"),
                AnimationKeyframe(time=2.0, bone="spine"),
            ],
        )
        warnings = validate_clip(clip)
        assert warnings == []


# ── keyframes_to_dict tests ──────────────────────────────────────


class TestKeyframesToDict:
    """Test keyframes_to_dict produces valid glTF animation structure."""

    def test_produces_name(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        assert result["name"] == "idle_breathe"

    def test_produces_channels(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        assert isinstance(result["channels"], list)
        # Should have at least scale channel for spine and rotation for head
        assert len(result["channels"]) > 0

    def test_produces_samplers(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        assert isinstance(result["samplers"], list)
        assert len(result["samplers"]) == len(result["channels"])

    def test_produces_keyframe_data(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        assert "keyframe_data" in result
        assert "spine" in result["keyframe_data"]
        assert "head" in result["keyframe_data"]

    def test_channel_has_path_property(self):
        clip = AnimationClip(
            name="test_path",
            duration=1.0,
            keyframes=[
                AnimationKeyframe(
                    time=0.0, bone="spine", rotation=(0.0, 0.0, 0.0)
                ),
                AnimationKeyframe(
                    time=1.0, bone="spine", rotation=(10.0, 0.0, 0.0)
                ),
            ],
        )
        result = keyframes_to_dict(clip)
        paths = [ch["target"]["path"] for ch in result["channels"]]
        assert "rotation" in paths

    def test_channel_node_is_bone_name(self):
        clip = AnimationClip(
            name="test_node",
            duration=1.0,
            keyframes=[
                AnimationKeyframe(
                    time=0.0, bone="head", rotation=(5.0, 0.0, 0.0)
                ),
            ],
        )
        result = keyframes_to_dict(clip)
        head_channels = [
            ch for ch in result["channels"]
            if ch["target"]["node"] == "head"
        ]
        assert len(head_channels) >= 1

    def test_sampler_interpolation_is_linear(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        for sampler in result["samplers"]:
            assert sampler["interpolation"] == "LINEAR"

    def test_duration_preserved(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        assert result["duration"] == 2.5

    def test_loop_preserved(self):
        clip = PRESET_CLIPS["idle_breathe"]
        result = keyframes_to_dict(clip)
        assert result["loop"] is True

    def test_empty_clip_produces_empty_channels(self):
        clip = create_clip(name="empty", duration=1.0)
        result = keyframes_to_dict(clip)
        assert result["channels"] == []
        assert result["samplers"] == []

    def test_default_values_not_included(self):
        """Channels with all-default values should be omitted."""
        clip = AnimationClip(
            name="defaults_only",
            duration=1.0,
            keyframes=[
                AnimationKeyframe(
                    time=0.0,
                    bone="hips",
                    position=(0.0, 0.0, 0.0),
                    rotation=(0.0, 0.0, 0.0),
                    scale=(1.0, 1.0, 1.0),
                ),
                AnimationKeyframe(
                    time=1.0,
                    bone="hips",
                    position=(0.0, 0.0, 0.0),
                    rotation=(0.0, 0.0, 0.0),
                    scale=(1.0, 1.0, 1.0),
                ),
            ],
        )
        result = keyframes_to_dict(clip)
        # All channels are defaults — should produce no channels
        assert result["channels"] == []


# ── get_preset_clips tests ───────────────────────────────────────


class TestGetPresetClips:
    """Test get_preset_clips returns dict with all 4 clips."""

    def test_returns_dict(self):
        clips = get_preset_clips()
        assert isinstance(clips, dict)

    def test_has_four_clips(self):
        clips = get_preset_clips()
        assert len(clips) == 4

    def test_keys_match_expected_names(self):
        clips = get_preset_clips()
        expected = {"idle_breathe", "idle_shift_weight", "idle_look_around", "walk_cycle_ref"}
        assert set(clips.keys()) == expected

    def test_returns_shallow_copy(self):
        """get_preset_clips should return a copy, not the original dict."""
        clips = get_preset_clips()
        # Mutating the returned dict shouldn't affect PRESET_CLIPS
        clips["test"] = AnimationClip(name="test", duration=1.0)
        assert "test" not in PRESET_CLIPS

    def test_values_are_animation_clips(self):
        clips = get_preset_clips()
        for name, clip in clips.items():
            assert isinstance(clip, AnimationClip)


# ── MB_LAB_TO_VRM mapping tests ─────────────────────────────────


class TestMBLabToVRM:
    """Test MB-Lab alias mapping."""

    def test_pelvis_maps_to_hips(self):
        assert MB_LAB_TO_VRM["pelvis"] == "hips"

    def test_spine_01_maps_to_chest(self):
        assert MB_LAB_TO_VRM["spine_01"] == "chest"

    def test_all_aliases_in_valid_bones(self):
        """All MB-Lab aliases should be in _VALID_BONE_NAMES."""
        for alias in MB_LAB_TO_VRM:
            assert alias in _VALID_BONE_NAMES, f"Alias '{alias}' not in valid bones"


# ── Blender-dependent tests (skipped in CI without Blender) ─────


@pytest.mark.blender
class TestClipToGltfAnimation:
    """Test clip_to_gltf_animation (requires Blender)."""

    def test_requires_bpy(self):
        """If bpy is not available, should raise RuntimeError."""
        from hamr.export.animation_clips import BLENDER_AVAILABLE

        if BLENDER_AVAILABLE:
            pytest.skip("bpy IS available — test the error path would require mocking")
        else:
            clip = PRESET_CLIPS["idle_breathe"]
            with pytest.raises(RuntimeError, match="bpy not available"):
                from hamr.export.animation_clips import clip_to_gltf_animation
                clip_to_gltf_animation(clip, "Armature")