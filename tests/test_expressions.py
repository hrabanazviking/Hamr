"""
Tests for hamr.face.expressions — VRM 1.0 Expression Blend Shape Binding.

Phase 12, Task T5 — The Forge Worker tests the face.
"""

from __future__ import annotations

import pytest

from hamr.face.expressions import (
    VRM_EXPRESSIONS,
    VRM_EXPRESSION_COUNT,
    SHAPE_KEY_ALIASES,
    ExpressionBinding,
    ExpressionSet,
    ExpressionBinder,
    build_expression_set,
)


# ═══════════════════════════════════════════════════════════════════════════════
# VRM_EXPRESSIONS structure tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestVRMExpressions:
    """Test VRM_EXPRESSIONS dict structure and completeness."""

    def test_has_eight_expressions(self):
        """VRM_EXPRESSIONS contains exactly the 8 required VRM 1.0 expressions."""
        assert len(VRM_EXPRESSIONS) == 8

    def test_required_expression_names(self):
        """All required VRM 1.0 expression names are present."""
        required = {"happy", "angry", "sad", "surprised", "neutral", "blink",
                     "blinkLeft", "blinkRight"}
        assert set(VRM_EXPRESSIONS.keys()) == required

    def test_each_expression_has_aliases(self):
        """Each expression maps to a list of at least 2 shape key aliases."""
        for name, aliases in VRM_EXPRESSIONS.items():
            assert isinstance(aliases, list), f"{name} aliases must be a list"
            assert len(aliases) >= 2, f"{name} must have ≥2 aliases, got {len(aliases)}"

    def test_happy_aliases(self):
        """happy maps to smile, happy, mouth_smile, grin."""
        assert "smile" in VRM_EXPRESSIONS["happy"]
        assert "happy" in VRM_EXPRESSIONS["happy"]

    def test_angry_aliases(self):
        """angry maps to angry, frown, brow_frown."""
        assert "angry" in VRM_EXPRESSIONS["angry"]
        assert "frown" in VRM_EXPRESSIONS["angry"]
        assert "brow_frown" in VRM_EXPRESSIONS["angry"]

    def test_sad_aliases(self):
        """sad maps to sad, frown_sad, mouth_sad."""
        assert "sad" in VRM_EXPRESSIONS["sad"]
        assert "frown_sad" in VRM_EXPRESSIONS["sad"]

    def test_surprised_aliases(self):
        """surprised maps to surprised, mouth_open, brow_surprised."""
        assert "surprised" in VRM_EXPRESSIONS["surprised"]
        assert "mouth_open" in VRM_EXPRESSIONS["surprised"]

    def test_neutral_aliases(self):
        """neutral maps to neutral, rest."""
        assert "neutral" in VRM_EXPRESSIONS["neutral"]
        assert "rest" in VRM_EXPRESSIONS["neutral"]

    def test_blink_aliases(self):
        """blink maps to blink, eye_blink, wink."""
        assert "blink" in VRM_EXPRESSIONS["blink"]
        assert "eye_blink" in VRM_EXPRESSIONS["blink"]

    def test_blink_left_aliases(self):
        """blinkLeft maps to blink_l, eye_blink_l, wink_l."""
        assert "blink_l" in VRM_EXPRESSIONS["blinkLeft"]
        assert "eye_blink_l" in VRM_EXPRESSIONS["blinkLeft"]

    def test_blink_right_aliases(self):
        """blinkRight maps to blink_r, eye_blink_r, wink_r."""
        assert "blink_r" in VRM_EXPRESSIONS["blinkRight"]
        assert "eye_blink_r" in VRM_EXPRESSIONS["blinkRight"]

    def test_vrm_expression_count(self):
        """VRM_EXPRESSION_COUNT constant equals 8."""
        assert VRM_EXPRESSION_COUNT == 8


# ═══════════════════════════════════════════════════════════════════════════════
# SHAPE_KEY_ALIASES mapping tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestShapeKeyAliases:
    """Test SHAPE_KEY_ALIASES dict mapping MB-Lab names to VRM expressions."""

    def test_aliases_is_non_empty(self):
        """SHAPE_KEY_ALIASES is a non-empty dict."""
        assert isinstance(SHAPE_KEY_ALIASES, dict)
        assert len(SHAPE_KEY_ALIASES) > 0

    def test_mblab_smile_maps_to_happy(self):
        """MB-Lab mouthSmile_max maps to 'happy'."""
        assert SHAPE_KEY_ALIASES["Expressions_mouthSmile_max"] == "happy"

    def test_mblab_smile_min_maps_to_sad(self):
        """MB-Lab mouthSmile_min maps to 'sad'."""
        assert SHAPE_KEY_ALIASES["Expressions_mouthSmile_min"] == "sad"

    def test_mblab_brow_squeeze_maps_to_angry(self):
        """MB-Lab browSqueezeL/R_max maps to 'angry'."""
        assert SHAPE_KEY_ALIASES["Expressions_browSqueezeL_max"] == "angry"
        assert SHAPE_KEY_ALIASES["Expressions_browSqueezeR_max"] == "angry"

    def test_mblab_eyes_vert_maps_to_surprised(self):
        """MB-Lab eyesVert_max maps to 'surprised'."""
        assert SHAPE_KEY_ALIASES["Expressions_eyesVert_max"] == "surprised"

    def test_mblab_eye_closed_l_maps_to_blink_left(self):
        """MB-Lab eyeClosedL_max maps to 'blinkLeft'."""
        assert SHAPE_KEY_ALIASES["Expressions_eyeClosedL_max"] == "blinkLeft"

    def test_mblab_eye_closed_r_maps_to_blink_right(self):
        """MB-Lab eyeClosedR_max maps to 'blinkRight'."""
        assert SHAPE_KEY_ALIASES["Expressions_eyeClosedR_max"] == "blinkRight"

    def test_turbosquid_aliases(self):
        """TurboSquid shape key names map correctly."""
        assert SHAPE_KEY_ALIASES["Smile"] == "happy"
        assert SHAPE_KEY_ALIASES["Blink_L"] == "blinkLeft"
        assert SHAPE_KEY_ALIASES["Blink_R"] == "blinkRight"
        assert SHAPE_KEY_ALIASES["BrowFurrow_L"] == "angry"
        assert SHAPE_KEY_ALIASES["Frown_L"] == "sad"

    def test_all_aliases_point_to_valid_vrm_expressions(self):
        """Every value in SHAPE_KEY_ALIASES must be a valid VRM expression name."""
        for mblab_key, vrm_expr in SHAPE_KEY_ALIASES.items():
            assert vrm_expr in VRM_EXPRESSIONS, (
                f"Alias {mblab_key!r} maps to {vrm_expr!r}, "
                f"which is not a VRM expression"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# ExpressionBinding dataclass tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestExpressionBinding:
    """Test ExpressionBinding dataclass creation and properties."""

    def test_empty_binding(self):
        """Empty binding has is_complete=False and confidence=0.0."""
        binding = ExpressionBinding(expression_name="happy")
        assert binding.expression_name == "happy"
        assert binding.shape_keys == []
        assert binding.is_complete is False
        assert binding.confidence == 0.0

    def test_binding_with_one_shape_key(self):
        """Binding with one shape key: is_complete=True, confidence=0.5."""
        binding = ExpressionBinding(
            expression_name="happy",
            shape_keys=[("smile", 1.0)],
        )
        assert binding.is_complete is True
        assert binding.confidence == 0.5

    def test_binding_with_multiple_shape_keys(self):
        """Binding with 3 shape keys: confidence increases."""
        binding = ExpressionBinding(
            expression_name="happy",
            shape_keys=[
                ("smile", 1.0),
                ("eye_squint_l", 0.4),
                ("eye_squint_r", 0.4),
            ],
        )
        assert binding.is_complete is True
        assert binding.confidence >= 0.5
        assert binding.confidence <= 1.0

    def test_binding_two_keys_confidence(self):
        """Binding with exactly 2 shape keys: confidence=0.75."""
        binding = ExpressionBinding(
            expression_name="blink",
            shape_keys=[("blink_l", 1.0), ("blink_r", 1.0)],
        )
        assert binding.confidence == 0.75

    def test_binding_preserves_shape_key_names(self):
        """Shape key names and weights are preserved exactly."""
        binding = ExpressionBinding(
            expression_name="angry",
            shape_keys=[
                ("brow_frown_l", 0.7),
                ("brow_frown_r", 0.7),
                ("mouth_frown", 0.5),
            ],
        )
        assert binding.shape_keys[0] == ("brow_frown_l", 0.7)
        assert binding.shape_keys[2] == ("mouth_frown", 0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# ExpressionSet dataclass tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestExpressionSet:
    """Test ExpressionSet dataclass creation and methods."""

    def test_all_none_by_default(self):
        """Default ExpressionSet has all bindings as None."""
        eset = ExpressionSet()
        assert eset.happy is None
        assert eset.angry is None
        assert eset.sad is None
        assert eset.surprised is None
        assert eset.neutral is None
        assert eset.blink is None
        assert eset.blink_left is None
        assert eset.blink_right is None

    def test_completion_count_empty(self):
        """Empty ExpressionSet has completion_count = 0."""
        eset = ExpressionSet()
        assert eset.completion_count() == 0

    def test_completion_count_partial(self):
        """ExpressionSet with 3 bound expressions has completion_count = 3."""
        happy = ExpressionBinding("happy", [("smile", 1.0)])
        blink = ExpressionBinding("blink", [("blink_l", 1.0)])
        sad = ExpressionBinding("sad", [("frown_sad", 0.8)])
        eset = ExpressionSet(happy=happy, blink=blink, sad=sad)
        assert eset.completion_count() == 3

    def test_is_vrm_complete(self):
        """Only fully bound ExpressionSet returns True for is_vrm_complete."""
        # Create bindings for all 8 expressions
        bindings = {
            "happy": ExpressionBinding("happy", [("smile", 1.0)]),
            "angry": ExpressionBinding("angry", [("frown", 1.0)]),
            "sad": ExpressionBinding("sad", [("frown_sad", 0.8)]),
            "surprised": ExpressionBinding("surprised", [("mouth_open", 1.0)]),
            "neutral": ExpressionBinding("neutral", [("rest", 1.0)]),
            "blink": ExpressionBinding("blink", [("blink_l", 1.0)]),
            "blinkLeft": ExpressionBinding("blinkLeft", [("blink_l", 1.0)]),
            "blinkRight": ExpressionBinding("blinkRight", [("blink_r", 1.0)]),
        }
        eset = build_expression_set(bindings)
        assert eset.is_vrm_complete()

    def test_is_vrm_complete_fails_if_missing(self):
        """ExpressionSet missing one expression returns False."""
        bindings = {
            "happy": ExpressionBinding("happy", [("smile", 1.0)]),
            "angry": ExpressionBinding("angry", [("frown", 1.0)]),
            # sad is missing
            "surprised": ExpressionBinding("surprised", [("mouth_open", 1.0)]),
            "neutral": ExpressionBinding("neutral", [("rest", 1.0)]),
            "blink": ExpressionBinding("blink", [("blink", 1.0)]),
            "blinkLeft": ExpressionBinding("blinkLeft", [("blink_l", 1.0)]),
            "blinkRight": ExpressionBinding("blinkRight", [("blink_r", 1.0)]),
        }
        eset = build_expression_set(bindings)
        assert not eset.is_vrm_complete()


# ═══════════════════════════════════════════════════════════════════════════════
# ExpressionBinder tests — Pure Python
# ═══════════════════════════════════════════════════════════════════════════════


class TestExpressionBinderInit:
    """Test ExpressionBinder construction — no bpy dependency."""

    def test_init_no_bpy_needed(self):
        """ExpressionBinder can be created without bpy."""
        binder = ExpressionBinder()
        assert binder is not None

    def test_init_no_arguments(self):
        """ExpressionBinder takes no arguments."""
        binder = ExpressionBinder()
        # No attributes expected
        assert isinstance(binder, ExpressionBinder)


class TestBindExpression:
    """Test ExpressionBinder.bind_expression."""

    def setup_method(self):
        self.binder = ExpressionBinder()

    def test_bind_with_single_key(self):
        """bind_expression with one shape key."""
        binding = self.binder.bind_expression("happy", {"smile": 1.0})
        assert binding.expression_name == "happy"
        assert binding.shape_keys == [("smile", 1.0)]
        assert binding.is_complete is True

    def test_bind_with_multiple_keys(self):
        """bind_expression with multiple shape keys."""
        binding = self.binder.bind_expression("blink", {
            "blink_l": 1.0,
            "blink_r": 1.0,
        })
        assert len(binding.shape_keys) == 2
        assert binding.is_complete is True

    def test_bind_with_empty_keys(self):
        """bind_expression with empty dict returns incomplete binding."""
        binding = self.binder.bind_expression("happy", {})
        assert binding.is_complete is False
        assert binding.confidence == 0.0


class TestFindMatchingShapeKeys:
    """Test ExpressionBinder.find_matching_shape_keys."""

    def setup_method(self):
        self.binder = ExpressionBinder()

    def test_mblab_keys_match_happy(self):
        """MB-Lab 'Expressions_mouthSmile_max' matches 'happy'."""
        available = [
            "Expressions_mouthSmile_max",
            "Expressions_eyeClosedL_max",
            "Expressions_eyeClosedR_max",
        ]
        matches = self.binder.find_matching_shape_keys("happy", available)
        names = [name for name, _ in matches]
        assert "Expressions_mouthSmile_max" in names

    def test_mblab_keys_match_blink_left(self):
        """MB-Lab 'Expressions_eyeClosedL_max' matches 'blinkLeft'."""
        available = [
            "Expressions_mouthSmile_max",
            "Expressions_eyeClosedL_max",
            "Expressions_eyeClosedR_max",
        ]
        matches = self.binder.find_matching_shape_keys("blinkLeft", available)
        names = [name for name, _ in matches]
        assert "Expressions_eyeClosedL_max" in names

    def test_mblab_keys_match_blink_right(self):
        """MB-Lab 'Expressions_eyeClosedR_max' matches 'blinkRight'."""
        available = [
            "Expressions_mouthSmile_max",
            "Expressions_eyeClosedL_max",
            "Expressions_eyeClosedR_max",
        ]
        matches = self.binder.find_matching_shape_keys("blinkRight", available)
        names = [name for name, _ in matches]
        assert "Expressions_eyeClosedR_max" in names

    def test_mblab_keys_match_angry(self):
        """MB-Lab brow squeeze keys match 'angry'."""
        available = [
            "Expressions_browSqueezeL_max",
            "Expressions_browSqueezeR_max",
            "Expressions_mouthOpenAggr_max",
        ]
        matches = self.binder.find_matching_shape_keys("angry", available)
        names = [name for name, _ in matches]
        assert "Expressions_browSqueezeL_max" in names
        assert "Expressions_browSqueezeR_max" in names
        assert "Expressions_mouthOpenAggr_max" in names

    def test_generic_keys_match(self):
        """Generic shape key names like 'smile' match 'happy'."""
        available = ["smile", "frown", "blink_l", "blink_r"]
        matches = self.binder.find_matching_shape_keys("happy", available)
        names = [name for name, _ in matches]
        assert "smile" in names

    def test_no_matches_returns_empty(self):
        """No matching shape keys returns empty list."""
        available = ["teeth_upper", "teeth_lower", "tongue"]
        matches = self.binder.find_matching_shape_keys("happy", available)
        assert matches == []

    def test_turbosquid_keys_match(self):
        """TurboSquid-style keys like 'Smile', 'Blink_L' match."""
        available = ["Smile", "Blink_L", "Blink_R", "Frown_L", "JawOpen"]
        matches_happy = self.binder.find_matching_shape_keys("happy", available)
        names = [n for n, _ in matches_happy]
        assert "Smile" in names

        matches_blink_left = self.binder.find_matching_shape_keys("blinkLeft", available)
        names = [n for n, _ in matches_blink_left]
        assert "Blink_L" in names

    def test_primary_match_has_weight_1(self):
        """Direct alias matches have weight 1.0."""
        available = ["Expressions_mouthSmile_max"]
        matches = self.binder.find_matching_shape_keys("happy", available)
        assert len(matches) == 1
        assert matches[0] == ("Expressions_mouthSmile_max", 1.0)

    def test_substring_matches_have_lower_weight(self):
        """Substring matches have weight 0.5 or 0.3."""
        available = ["mouth_smile_wide"]
        matches = self.binder.find_matching_shape_keys("happy", available)
        # "smile" (from VRM_EXPRESSIONS["happy"]) is substring of "mouth_smile_wide"
        assert len(matches) >= 1
        # Should be 0.5 for pattern substring match
        weights = [w for _, w in matches]
        assert any(w <= 0.5 for w in weights)

    def test_deduplication_no_duplicate_keys(self):
        """No shape key appears twice in match results."""
        available = ["Expressions_mouthSmile_max", "mouth_smile"]
        matches = self.binder.find_matching_shape_keys("happy", available)
        names = [n for n, _ in matches]
        assert len(names) == len(set(names)), f"Duplicate keys found: {names}"


class TestResolveExpressionBindings:
    """Test ExpressionBinder.resolve_expression_bindings."""

    def setup_method(self):
        self.binder = ExpressionBinder()

    def test_resolve_all_with_mblab_keys(self):
        """Resolve all 8 VRM expressions against MB-Lab-like shape keys."""
        available = [
            "Expressions_mouthSmile_max",
            "Expressions_mouthSmile_min",
            "Expressions_browSqueezeL_max",
            "Expressions_browSqueezeR_max",
            "Expressions_eyesVert_max",
            "Expressions_mouthOpen_max",
            "Expressions_mouthOpenAggr_max",
            "Expressions_eyeClosedL_max",
            "Expressions_eyeClosedR_max",
            "Expressions_mouthHoriz_max",
        ]
        bindings = self.binder.resolve_expression_bindings(available)

        # happy should be bound
        assert bindings["happy"].is_complete
        # angry should be bound
        assert bindings["angry"].is_complete
        # blinkLeft should be bound
        assert bindings["blinkLeft"].is_complete
        # blinkRight should be bound
        assert bindings["blinkRight"].is_complete
        # surprised should be bound
        assert bindings["surprised"].is_complete

    def test_resolve_with_empty_keys(self):
        """Empty available keys results in all incomplete bindings."""
        bindings = self.binder.resolve_expression_bindings([])
        for name, binding in bindings.items():
            assert not binding.is_complete

    def test_resolve_specific_expressions(self):
        """Resolve only a subset of expressions."""
        available = ["Blink_L", "Blink_R", "Smile"]
        bindings = self.binder.resolve_expression_bindings(
            available, expression_names=["happy", "blinkLeft", "blinkRight"]
        )
        assert len(bindings) == 3
        assert "happy" in bindings
        assert "blinkLeft" in bindings
        assert "blinkRight" in bindings

    def test_resolve_returns_all_8_by_default(self):
        """Default resolve returns all 8 VRM expression bindings."""
        bindings = self.binder.resolve_expression_bindings(["smile"])
        assert len(bindings) == VRM_EXPRESSION_COUNT


class TestValidateBindings:
    """Test ExpressionBinder.validate_bindings."""

    def setup_method(self):
        self.binder = ExpressionBinder()

    def test_warnings_for_missing_bindings(self):
        """validate_bindings returns warnings for incomplete expressions."""
        bindings = {
            "happy": ExpressionBinding("happy", [("smile", 1.0)]),
            "angry": ExpressionBinding("angry", [], is_complete=False, confidence=0.0),
        }
        warnings = self.binder.validate_bindings(bindings)
        assert len(warnings) == 1
        assert "angry" in warnings[0]

    def test_no_warnings_when_all_complete(self):
        """No warnings when all expressions are bound."""
        bindings = {
            "happy": ExpressionBinding("happy", [("smile", 1.0)]),
            "angry": ExpressionBinding("angry", [("frown", 1.0)]),
        }
        warnings = self.binder.validate_bindings(bindings)
        assert len(warnings) == 0

    def test_all_missing_warnings(self):
        """All expressions missing → 8 warnings."""
        bindings = {}
        for name in VRM_EXPRESSIONS:
            bindings[name] = ExpressionBinding(name)
        warnings = self.binder.validate_bindings(bindings)
        assert len(warnings) == VRM_EXPRESSION_COUNT


class TestBuildExpressionSet:
    """Test build_expression_set helper function."""

    def test_build_expression_set_from_bindings(self):
        """Build ExpressionSet from a dict of bindings."""
        bindings = {
            "happy": ExpressionBinding("happy", [("smile", 1.0)]),
            "angry": ExpressionBinding("angry", [("frown", 1.0)]),
        }
        eset = build_expression_set(bindings)
        assert eset.happy is not None
        assert eset.happy.expression_name == "happy"
        assert eset.angry is not None
        assert eset.angry.expression_name == "angry"
        # Unbound expressions are None
        assert eset.sad is None
        assert eset.surprised is None
        assert eset.neutral is None
        assert eset.blink is None
        assert eset.blink_left is None
        assert eset.blink_right is None

    def test_build_expression_set_key_mapping(self):
        """blinkLeft → blink_left, blinkRight → blink_right in ExpressionSet."""
        bindings = {
            "blinkLeft": ExpressionBinding("blinkLeft", [("blink_l", 1.0)]),
            "blinkRight": ExpressionBinding("blinkRight", [("blink_r", 1.0)]),
        }
        eset = build_expression_set(bindings)
        assert eset.blink_left is not None
        assert eset.blink_left.expression_name == "blinkLeft"
        assert eset.blink_right is not None
        assert eset.blink_right.expression_name == "blinkRight"


# ═══════════════════════════════════════════════════════════════════════════════
# Blender-dependent tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestApplyExpressionBindingsBlender:
    """Test apply_expression_bindings — requires bpy (Blender)."""

    def test_raises_runtime_error_without_bpy(self):
        """apply_expression_bindings raises RuntimeError if bpy is unavailable."""
        from hamr.face.expressions import apply_expression_bindings
        bindings = {
            "happy": ExpressionBinding("happy", [("smile", 1.0)]),
        }
        # This will raise RuntimeError because we're not in Blender
        with pytest.raises(RuntimeError, match="bpy"):
            apply_expression_bindings("Armature", bindings)


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Full resolve → bind → validate → build_expression_set
# ═══════════════════════════════════════════════════════════════════════════════


class TestExpressionIntegration:
    """Integration test: resolve → bind → validate → build expression set."""

    def test_full_pipeline_mblab(self):
        """Full pipeline with MB-Lab shape keys."""
        available_keys = [
            "Expressions_mouthSmile_max",
            "Expressions_browSqueezeL_max",
            "Expressions_browSqueezeR_max",
            "Expressions_mouthOpenAggr_max",
            "Expressions_mouthSmile_min",
            "Expressions_eyeClosedL_max",
            "Expressions_eyeClosedL_min",
            "Expressions_eyeClosedR_max",
            "Expressions_eyeClosedR_min",
            "Expressions_eyesVert_max",
            "Expressions_mouthOpen_max",
            "Expressions_mouthHoriz_max",
        ]

        binder = ExpressionBinder()
        bindings = binder.resolve_expression_bindings(available_keys)
        warnings = binder.validate_bindings(bindings)
        eset = build_expression_set(bindings)

        # happy should be bound (mouthSmile_max)
        assert eset.happy is not None
        assert eset.happy.is_complete

        # blinkLeft should be bound (eyeClosedL)
        assert eset.blink_left is not None
        assert eset.blink_left.is_complete

        # Validate that some warnings might exist (no neutral key in list)
        # but key expressions should be bound
        assert eset.completion_count() >= 4, (
            f"Expected ≥4 expressions bound, got {eset.completion_count()}"
        )

    def test_full_pipeline_turbosquid(self):
        """Full pipeline with TurboSquid-style shape keys."""
        available_keys = [
            "Smile",
            "Blink_L",
            "Blink_R",
            "BrowFurrow_L",
            "BrowFurrow_R",
            "EyeWide_L",
            "EyeWide_R",
            "JawOpen",
            "MouthPucker",
        ]

        binder = ExpressionBinder()
        bindings = binder.resolve_expression_bindings(available_keys)
        eset = build_expression_set(bindings)

        assert eset.happy is not None
        assert eset.happy.is_complete
        assert eset.blink_left is not None
        assert eset.blink_left.is_complete
        assert eset.blink_right is not None
        assert eset.blink_right.is_complete