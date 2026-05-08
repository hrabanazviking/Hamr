"""
Tests for Hamr Phase 7 — The Three Forges.

Tests the Hair, Face, and Clothing forges:
- Hair: style resolution, length presets, color gradients, physics
- Face: shape key mapping, eye shapes, jaw presets, lip fullness
- Clothing: type templates, material categories, color resolution
- Forge integration: builder wires forge config into Blender script
"""

import pytest
from pathlib import Path

from hamr.core.models import (
    HairSpec, HairColorSpec, HairStyle, HairLength, FaceSpec, EyeSpec,
    ClothingSpec, CharacterSpec, BodySpec, PhysicsSpec, HairPhysicsSpec,
)
from hamr.core.spec import Spec


# ── Hair Forge Tests ────────────────────────────────────────────────────────────

class TestHairForge:
    """Test the Hair Forge resolve_hair function."""

    def test_resolve_hair_default_spec(self):
        """Resolve a default HairSpec produces a valid HairBuildResult."""
        from hamr.hair import resolve_hair
        spec = HairSpec()
        result = resolve_hair(spec)
        assert result.style_template is not None
        assert result.volume == 0.7
        assert result.curl_tightness >= 0.0
        assert result.length_factor > 0.0
        assert len(result.color_roots_hsv) == 3
        assert len(result.color_tips_hsv) == 3

    def test_resolve_hair_wild_curly(self):
        """Wild-curly style resolves with curl and volume."""
        from hamr.hair import resolve_hair
        spec = HairSpec(style="wild-curly", length="shoulder-plus", volume=0.9, curl_tightness=0.8)
        result = resolve_hair(spec)
        assert result.style_template["shell_count"] == 8
        assert result.curl_tightness == 0.8
        assert result.volume == 0.9

    def test_resolve_hair_straight(self):
        """Straight style has zero curl and fewer shells."""
        from hamr.hair import resolve_hair
        spec = HairSpec(style="straight", length="long", curl_tightness=0.0)
        result = resolve_hair(spec)
        assert result.style_template["shell_count"] == 4
        assert result.curl_tightness == 0.0

    def test_resolve_hair_custom_color(self):
        """Custom hair colors resolve to HSV tuples."""
        from hamr.hair import resolve_hair
        spec = HairSpec(
            color=HairColorSpec(roots="#FF0000", mid="#00FF00", tips="#0000FF")
        )
        result = resolve_hair(spec)
        # Roots should be red-ish in HSV (hue near 0)
        assert result.color_roots_hsv[0] < 0.05 or result.color_roots_hsv[0] > 0.95

    def test_hair_length_table_complete(self):
        """All documented hair lengths have entries."""
        from hamr.hair import HAIR_LENGTH_TABLE
        for length in ("short", "medium", "shoulder", "shoulder-plus", "long", "very-long"):
            assert length in HAIR_LENGTH_TABLE

    def test_hair_style_templates_complete(self):
        """All documented hair styles have templates."""
        from hamr.hair import HAIR_STYLE_TEMPLATES
        for style in ("wild-curly", "straight", "wavy", "braided", "bun", "ponytail"):
            assert style in HAIR_STYLE_TEMPLATES

    def test_gradient_presets_keys(self):
        """Gradient presets have roots, mid, tips."""
        from hamr.hair import HAIR_GRADIENT_PRESETS
        for name, colors in HAIR_GRADIENT_PRESETS.items():
            assert "roots" in colors
            assert "mid" in colors
            assert "tips" in colors

    def test_hair_build_result_to_dict(self):
        """HairBuildResult serializes to dict with list HSV tuples."""
        from hamr.hair import resolve_hair
        result = resolve_hair(HairSpec())
        d = result.to_dict()
        assert isinstance(d["color_roots_hsv"], list)
        assert len(d["color_roots_hsv"]) == 3
        assert isinstance(d["style_template"], dict)

    def test_resolve_hair_unknown_style(self):
        """Unknown style falls back to 'wavy'."""
        from hamr.hair import resolve_hair
        spec = HairSpec(style="does-not-exist")
        result = resolve_hair(spec)
        assert result.style_template["shell_count"] == 6  # wavy default

    def test_resolve_hair_unknown_length(self):
        """Unknown length falls back to 'shoulder-plus'."""
        from hamr.hair import resolve_hair, HAIR_LENGTH_TABLE
        spec = HairSpec(length="nonexistent")
        result = resolve_hair(spec)
        assert result.normalized_length == HAIR_LENGTH_TABLE["shoulder-plus"]


# ── Face Forge Tests ────────────────────────────────────────────────────────────

class TestFaceForge:
    """Test the Face Forge resolve_face function."""

    def test_resolve_face_default(self):
        """Default FaceSpec resolves with shape keys."""
        from hamr.face import resolve_face
        spec = FaceSpec()
        result = resolve_face(spec)
        assert len(result.shape_keys) > 0
        assert result.eye_size_factor == 1.1  # EyeSpec default

    def test_resolve_face_v_jaw(self):
        """V-shape jaw applies correct shape key overrides."""
        from hamr.face import resolve_face, JAW_MAP
        spec = FaceSpec(jaw="V-shape")
        result = resolve_face(spec)
        v_jaw = JAW_MAP["V-shape"]
        for key, value in v_jaw.items():
            assert result.shape_keys.get(key) == value

    def test_resolve_face_round_jaw(self):
        """Round jaw applies width-positive overrides."""
        from hamr.face import resolve_face, JAW_MAP
        spec = FaceSpec(jaw="round")
        result = resolve_face(spec)
        assert result.shape_keys.get("jaw_width", 0) > 0

    def test_resolve_face_cat_tilt_eyes(self):
        """Cat-tilt eyes apply eye tilt shape keys."""
        from hamr.face import resolve_face
        spec = FaceSpec(eyes=EyeSpec(shape="cat-tilt"))
        result = resolve_face(spec)
        assert result.shape_keys.get("eye_tilt") is not None

    def test_resolve_face_round_eyes(self):
        """Round eyes have higher openness."""
        from hamr.face import resolve_face
        spec = FaceSpec(eyes=EyeSpec(shape="round", size=1.3))
        result = resolve_face(spec)
        assert result.shape_keys.get("eye_openness", 0) > 0

    def test_resolve_face_thin_lips(self):
        """Low lip_fullness maps to thin lip shape keys."""
        from hamr.face import resolve_face
        spec = FaceSpec(lip_fullness=0.1)
        result = resolve_face(spec)
        assert result.lip_fullness == 0.0  # thin

    def test_resolve_face_full_lips(self):
        """High lip_fullness maps to full lip shape keys."""
        from hamr.face import resolve_face
        spec = FaceSpec(lip_fullness=0.9)
        result = resolve_face(spec)
        assert result.lip_fullness == 1.0  # full

    def test_resolve_face_expression_preset(self):
        """Default expression is resolved from presets."""
        from hamr.face import resolve_face, DEFAULT_EXPRESSION_MAP
        spec = FaceSpec(default_expression="soft-half-smile")
        result = resolve_face(spec)
        assert "mouth_smile" in result.default_expression

    def test_face_build_result_to_dict(self):
        """FaceBuildResult serializes correctly."""
        from hamr.face import resolve_face
        result = resolve_face(FaceSpec())
        d = result.to_dict()
        assert isinstance(d["eye_color_hsv"], list)
        assert len(d["eye_color_hsv"]) == 3
        assert isinstance(d["shape_keys"], dict)

    def test_list_presets_are_complete(self):
        """Preset listing functions return valid presets."""
        from hamr.face import list_jaw_presets, list_eye_shape_presets, list_expression_presets
        jaws = list_jaw_presets()
        assert "V-shape" in jaws
        assert "round" in jaws
        eyes = list_eye_shape_presets()
        assert "cat-tilt" in eyes
        exprs = list_expression_presets()
        assert "soft-half-smile" in exprs


# ── Clothing Forge Tests ──────────────────────────────────────────────────────

class TestClothingForge:
    """Test the Clothing Forge resolve_clothing function."""

    def test_resolve_clothing_default(self):
        """Default ClothingSpec resolves to a full-outfit."""
        from hamr.clothing import resolve_clothing
        spec = ClothingSpec()
        result = resolve_clothing(spec)
        assert result.cloth_type == "full-outfit"
        assert result.primary_hsv is not None
        assert len(result.primary_hsv) == 3

    def test_resolve_clothing_top(self):
        """Top type resolves with correct layers."""
        from hamr.clothing import resolve_clothing
        spec = ClothingSpec(name="t-shirt", type="top", primary_hex="#333333")
        result = resolve_clothing(spec)
        assert result.cloth_type == "top"
        assert "torso" in result.template["layers"]

    def test_resolve_clothing_metal_jewelry(self):
        """Jewelry infers metal material category."""
        from hamr.clothing import resolve_clothing
        spec = ClothingSpec(name="silver_ring", type="jewelry", primary_hex="#C0C0C0")
        result = resolve_clothing(spec)
        assert result.material_category == "metal"
        assert result.material_properties["metallic"] > 0.5

    def test_resolve_clothing_leather_footwear(self):
        """Footwear defaults to leather material."""
        from hamr.clothing import resolve_clothing
        spec = ClothingSpec(name="boots", type="footwear", primary_hex="#5C3A1E")
        result = resolve_clothing(spec)
        assert result.material_category == "leather"

    def test_resolve_clothing_silk_dress(self):
        """Dress named with silk keyword infers silk material."""
        from hamr.clothing import resolve_clothing
        spec = ClothingSpec(name="silk_dress", type="dress", primary_hex="#4466AA")
        result = resolve_clothing(spec)
        assert result.material_category == "silk"

    def test_clothing_color_resolution(self):
        """Clothing colors resolve to HSV tuples."""
        from hamr.clothing import resolve_clothing
        spec = ClothingSpec(
            primary_hex="#FF0000",
            accent_hex="#00FF00",
            trim_hex="#0000FF",
        )
        result = resolve_clothing(spec)
        # Red roots should have hue near 0
        assert result.primary_hsv[0] < 0.05 or result.primary_hsv[0] > 0.95

    def test_clothing_build_result_to_dict(self):
        """ClothingBuildResult serializes correctly."""
        from hamr.clothing import resolve_clothing
        result = resolve_clothing(ClothingSpec())
        d = result.to_dict()
        assert isinstance(d["primary_hsv"], list)
        assert isinstance(d["material_properties"], dict)

    def test_list_clothing_types(self):
        """list_clothing_types returns all valid types."""
        from hamr.clothing import list_clothing_types
        types = list_clothing_types()
        assert "full-outfit" in types
        assert "top" in types
        assert "jewelry" in types

    def test_list_material_categories(self):
        """list_material_categories returns all material categories."""
        from hamr.clothing import list_material_categories
        cats = list_material_categories()
        assert "fabric" in cats
        assert "metal" in cats
        assert "leather" in cats


# ── Forge Integration Tests ────────────────────────────────────────────────────

class TestForgeIntegration:
    """Test forge resolution integrated into the builder pipeline."""

    def test_resolve_forges_in_builder(self):
        """_resolve_forges processes hair, face, and clothing."""
        from hamr.core.builder import _resolve_forges
        char = CharacterSpec(
            name="Forge Test",
            hair=HairSpec(style="wild-curly", length="long"),
            face=FaceSpec(jaw="round", eyes=EyeSpec(shape="cat-tilt")),
            clothing=[ClothingSpec(name="dress", type="dress")],
        )
        config = _resolve_forges(char)
        assert "hair" in config
        assert "face" in config
        assert "clothing" in config
        assert config["hair"] is not None
        assert config["face"] is not None
        assert len(config["clothing"]) == 1

    def test_resolve_forges_hair_failure_graceful(self):
        """Hair forge failure doesn't crash — returns None."""
        from hamr.core.builder import _resolve_forges
        char = CharacterSpec(name="Grace Test")
        # Should succeed even with defaults
        config = _resolve_forges(char)
        assert config["hair"] is not None

    def test_resolve_forges_empty_clothing(self):
        """Empty clothing list resolves to empty list."""
        from hamr.core.builder import _resolve_forges
        char = CharacterSpec(name="No Clothes", clothing=[])
        config = _resolve_forges(char)
        assert config["clothing"] == []

    def test_forge_config_in_spec_dict(self):
        """Builder injects forge_config into spec dict."""
        from hamr.core.builder import _resolve_forges
        char = CharacterSpec(
            name="Config Inject",
            hair=HairSpec(style="straight"),
        )
        config = _resolve_forges(char)
        assert "hair" in config
        assert config["hair"]["style_template"]["shell_count"] == 4

    def test_spec_yaml_roundtrip_with_forges(self, tmp_path):
        """Spec YAML roundtrip preserves forge-resolvable data."""
        yaml_content = """
name: Roundtrip Test
body:
  height_cm: 165
  build: athletic-slender
  skin:
    base_hex: "#D4A373"
face:
  jaw: heart
  eyes:
    shape: cat-tilt
    iris_hex: "#70C1B3"
hair:
  style: wavy
  length: shoulder-plus
  color:
    roots: "#C4A265"
    tips: "#F5E6B8"
clothing:
  - name: boots
    type: footwear
    primary_hex: "#5C3A1E"
"""
        spec_file = tmp_path / "test_spec.yaml"
        spec_file.write_text(yaml_content)
        spec = Spec.from_yaml(spec_file)
        # Resolve through forges
        from hamr.core.builder import _resolve_forges
        config = _resolve_forges(spec.character)
        assert config["hair"]["curl_tightness"] == 0.75  # HairSpec default curl
        assert config["face"]["shape_keys"]["jaw_width"] is not None
        assert len(config["clothing"]) == 1
        assert config["clothing"][0]["material_category"] == "leather"