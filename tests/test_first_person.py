"""
Tests for hamr.export.first_person — VRM 1.0 First-Person Annotations.

Pure-Python tests run without Blender.
Blender-dependent tests are marked with @pytest.mark.blender.
"""

from __future__ import annotations

import pytest

from hamr.export.first_person import (
    FirstPersonConfig,
    FP_AUTO,
    FP_BOTH,
    FP_THIRD_PERSON_ONLY,
    FP_FIRST_PERSON_ONLY,
    VALID_FP_ANNOTATIONS,
    THIRD_PERSON_ONLY_PATTERNS,
    BOTH_VIEW_PATTERNS,
    FIRST_PERSON_ONLY_PATTERNS,
    classify_mesh_for_fp,
    configure_first_person_pure,
    configure_first_person,
)


# ══════════════════════════════════════════════════════════════════════
# FirstPersonConfig dataclass tests
# ══════════════════════════════════════════════════════════════════════


class TestFirstPersonConfig:
    """FirstPersonConfig creation, defaults, and validation tests."""

    def test_defaults(self):
        """Default config has head bone, 6cm Y offset, empty annotations."""
        config = FirstPersonConfig()
        assert config.first_person_bone == "head"
        assert config.first_person_bone_offset == (0.0, 0.06, 0.0)
        assert config.mesh_annotations == {}
        assert config.render_body_from_first_person is True

    def test_custom_values(self):
        """Custom FirstPersonConfig fields are preserved."""
        config = FirstPersonConfig(
            first_person_bone="neck",
            first_person_bone_offset=(0.0, 0.08, 0.0),
            mesh_annotations={"head_mesh": FP_THIRD_PERSON_ONLY},
            render_body_from_first_person=False,
        )
        assert config.first_person_bone == "neck"
        assert config.first_person_bone_offset == (0.0, 0.08, 0.0)
        assert config.mesh_annotations["head_mesh"] == FP_THIRD_PERSON_ONLY
        assert config.render_body_from_first_person is False

    def test_to_dict(self):
        """to_dict produces VRM-compatible dict with list-converted offsets."""
        config = FirstPersonConfig(
            first_person_bone_offset=(0.1, 0.2, 0.3),
            mesh_annotations={"body": FP_BOTH},
        )
        d = config.to_dict()
        assert d["first_person_bone"] == "head"
        assert d["first_person_bone_offset"] == [0.1, 0.2, 0.3]
        assert d["mesh_annotations"] == {"body": FP_BOTH}
        assert d["render_body_from_first_person"] is True

    def test_validate_empty_bone_fails(self):
        """Validation fails for empty first_person_bone."""
        config = FirstPersonConfig(first_person_bone="")
        errors = config.validate()
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)

    def test_validate_invalid_annotation_fails(self):
        """Validation fails for invalid annotation values."""
        config = FirstPersonConfig(
            mesh_annotations={"body": "invalid_mode"}
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("invalid" in e.lower() or "Invalid" in e for e in errors)

    def test_validate_valid_config_passes(self):
        """Valid config produces no validation errors."""
        config = FirstPersonConfig(
            mesh_annotations={
                "head_mesh": FP_THIRD_PERSON_ONLY,
                "body_mesh": FP_BOTH,
                "fp_body": FP_FIRST_PERSON_ONLY,
                "accessory": FP_AUTO,
            }
        )
        errors = config.validate()
        assert errors == []

    def test_validate_large_offset_warns(self):
        """Validation warns about suspiciously large offsets."""
        config = FirstPersonConfig(
            first_person_bone_offset=(5.0, 0.06, 0.0)
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("suspiciously large" in e for e in errors)

    def test_validate_all_valid_annotations(self):
        """All four valid annotation strings pass validation."""
        for annotation in VALID_FP_ANNOTATIONS:
            config = FirstPersonConfig(mesh_annotations={"mesh": annotation})
            errors = config.validate()
            assert errors == [], f"Valid annotation '{annotation}' failed validation"


# ══════════════════════════════════════════════════════════════════════
# classify_mesh_for_fp tests
# ══════════════════════════════════════════════════════════════════════


class TestClassifyMeshForFp:
    """Test mesh name classification to first-person annotation modes."""

    # ── Head/face meshes → thirdPersonOnly ──

    def test_head_mesh_is_third_person_only(self):
        """'head' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("head_mesh") == FP_THIRD_PERSON_ONLY

    def test_face_mesh_is_third_person_only(self):
        """'face' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("Face_Body") == FP_THIRD_PERSON_ONLY

    def test_hair_mesh_is_third_person_only(self):
        """'hair' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("hair_long") == FP_THIRD_PERSON_ONLY

    def test_eye_mesh_is_third_person_only(self):
        """'eye' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("eye_L") == FP_THIRD_PERSON_ONLY

    def test_iris_mesh_is_third_person_only(self):
        """'iris' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("iris_R") == FP_THIRD_PERSON_ONLY

    def test_eyebrow_mesh_is_third_person_only(self):
        """'eyebrow' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("eyebrow_01") == FP_THIRD_PERSON_ONLY

    def test_mouth_mesh_is_third_person_only(self):
        """'mouth' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("mouth_mesh") == FP_THIRD_PERSON_ONLY

    def test_teeth_mesh_is_third_person_only(self):
        """'teeth' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("teeth_upper") == FP_THIRD_PERSON_ONLY

    def test_ear_mesh_is_third_person_only(self):
        """'ear' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("ear_L") == FP_THIRD_PERSON_ONLY

    def test_horn_mesh_is_third_person_only(self):
        """'horn' in mesh name → thirdPersonOnly."""
        assert classify_mesh_for_fp("horn_demon") == FP_THIRD_PERSON_ONLY

    # ── Body/clothing meshes → both ──

    def test_body_mesh_is_both(self):
        """'body' in mesh name → both."""
        assert classify_mesh_for_fp("body_base") == FP_BOTH

    def test_torso_mesh_is_both(self):
        """'torso' in mesh name → both."""
        assert classify_mesh_for_fp("Torso_Upper") == FP_BOTH

    def test_hand_mesh_is_both(self):
        """'hand' in mesh name → both."""
        assert classify_mesh_for_fp("hand_L") == FP_BOTH

    def test_clothes_mesh_is_both(self):
        """'clothes' in mesh name → both."""
        assert classify_mesh_for_fp("clothes_casual") == FP_BOTH

    def test_skirt_mesh_is_both(self):
        """'skirt' in mesh name → both."""
        assert classify_mesh_for_fp("skirt_plaid") == FP_BOTH

    def test_dress_mesh_is_both(self):
        """'dress' in mesh name → both."""
        assert classify_mesh_for_fp("Dress_Sunday") == FP_BOTH

    # ── First-person-only meshes ──

    def test_fp_body_mesh(self):
        """'fp_body' mesh name → firstPersonOnly."""
        assert classify_mesh_for_fp("fp_body") == FP_FIRST_PERSON_ONLY

    def test_first_person_body_mesh(self):
        """'first_person_body' mesh name → firstPersonOnly."""
        assert classify_mesh_for_fp("first_person_body") == FP_FIRST_PERSON_ONLY

    def test_body_fp_mesh(self):
        """'body_fp' mesh name → firstPersonOnly."""
        assert classify_mesh_for_fp("body_fp") == FP_FIRST_PERSON_ONLY

    # ── Default / unknown ──

    def test_unknown_mesh_is_auto(self):
        """Unknown mesh patterns → auto."""
        assert classify_mesh_for_fp("something_random") == FP_AUTO

    def test_empty_string_is_auto(self):
        """Empty string mesh name → auto."""
        assert classify_mesh_for_fp("") == FP_AUTO

    # ── Priority: firstPersonOnly checked before patterns ──

    def test_fp_body_takes_priority_over_body(self):
        """'fp_body' should be firstPersonOnly, not 'both' from 'body' match."""
        assert classify_mesh_for_fp("fp_body") == FP_FIRST_PERSON_ONLY

    def test_head_pattern_priority_over_arm(self):
        """'head' pattern takes third-person even though it appears in both checks.
        Note: third-person check runs before both-view check."""
        assert classify_mesh_for_fp("head_arm") == FP_THIRD_PERSON_ONLY


# ══════════════════════════════════════════════════════════════════════
# configure_first_person_pure tests
# ══════════════════════════════════════════════════════════════════════


class TestConfigureFirstPersonPure:
    """Test pure-Python first-person configuration."""

    def test_empty_inputs(self):
        """Empty body name and no clothing produces empty annotations."""
        config = configure_first_person_pure("")
        assert config.mesh_annotations == {}

    def test_body_name_classified(self):
        """Body mesh gets classified properly."""
        config = configure_first_person_pure("body_base")
        assert "body_base" in config.mesh_annotations
        assert config.mesh_annotations["body_base"] == FP_BOTH

    def test_head_mesh_classified(self):
        """Head mesh is classified as thirdPersonOnly."""
        config = configure_first_person_pure("Head_Mesh")
        assert config.mesh_annotations["Head_Mesh"] == FP_THIRD_PERSON_ONLY

    def test_clothing_names_classified(self):
        """Clothing meshes are classified by their names."""
        clothing = ["skirt_short", "hair_ponytail"]
        config = configure_first_person_pure("body", clothing)
        # 'skirt_short' contains 'skirt' → both
        assert config.mesh_annotations["skirt_short"] == FP_BOTH
        # 'hair_ponytail' contains 'hair' → thirdPersonOnly
        assert config.mesh_annotations["hair_ponytail"] == FP_THIRD_PERSON_ONLY

    def test_default_bone_offset(self):
        """Default bone offset is head with 6cm Y offset."""
        config = configure_first_person_pure("body")
        assert config.first_person_bone == "head"
        assert config.first_person_bone_offset == (0.0, 0.06, 0.0)

    def test_render_body_default_true(self):
        """render_body_from_first_person defaults to True."""
        config = configure_first_person_pure("body")
        assert config.render_body_from_first_person is True

    def test_mixed_mesh_classifications(self):
        """Multiple meshes with different classifications."""
        clothing = [
            "skirt_long",        # both (skirt)
            "hair_back",         # thirdPersonOnly (hair)
            "fp_body_simplified", # firstPersonOnly (fp_body)
            "strange_accessory", # auto (unknown)
        ]
        config = configure_first_person_pure("head_mesh", clothing)
        assert config.mesh_annotations["head_mesh"] == FP_THIRD_PERSON_ONLY
        assert config.mesh_annotations["skirt_long"] == FP_BOTH
        assert config.mesh_annotations["hair_back"] == FP_THIRD_PERSON_ONLY
        assert config.mesh_annotations["fp_body_simplified"] == FP_FIRST_PERSON_ONLY
        assert config.mesh_annotations["strange_accessory"] == FP_AUTO

    def test_none_clothing_list(self):
        """None clothing list is handled gracefully."""
        config = configure_first_person_pure("body_base", None)
        assert "body_base" in config.mesh_annotations
        assert len(config.mesh_annotations) == 1


# ══════════════════════════════════════════════════════════════════════
# Blender-dependent tests
# ══════════════════════════════════════════════════════════════════════


class TestConfigureFirstPersonBlender:
    """Blender-dependent tests for configure_first_person."""

    def test_raises_without_bpy(self):
        """configure_first_person raises RuntimeError without bpy."""
        from hamr.export.first_person import BLENDER_AVAILABLE
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy not available"):
                configure_first_person("armature", ["mesh"])


# ══════════════════════════════════════════════════════════════════════
# Constants tests
# ══════════════════════════════════════════════════════════════════════


class TestFirstPersonConstants:
    """Test first-person annotation constant correctness."""

    def test_valid_annotations_include_all_modes(self):
        """VALID_FP_ANNOTATIONS contains all 4 VRM 1.0 modes."""
        assert FP_AUTO in VALID_FP_ANNOTATIONS
        assert FP_BOTH in VALID_FP_ANNOTATIONS
        assert FP_THIRD_PERSON_ONLY in VALID_FP_ANNOTATIONS
        assert FP_FIRST_PERSON_ONLY in VALID_FP_ANNOTATIONS
        assert len(VALID_FP_ANNOTATIONS) == 4

    def test_third_person_patterns_include_head(self):
        """Head pattern is in third-person-only patterns."""
        assert "head" in THIRD_PERSON_ONLY_PATTERNS

    def test_both_view_patterns_include_body(self):
        """Body pattern is in both-view patterns."""
        assert "body" in BOTH_VIEW_PATTERNS

    def test_fp_only_patterns_include_fp_body(self):
        """fp_body pattern is in first-person-only patterns."""
        assert "fp_body" in FIRST_PERSON_ONLY_PATTERNS