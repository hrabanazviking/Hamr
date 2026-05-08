"""
Tests for Hamr spec parsing and validation.
"""

import pytest
from pathlib import Path

from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    SkinSpec,
    EyeSpec,
    ExportSpec,
)
from hamr.core.validate import validate_spec
from hamr.core.spec import Spec


class TestCharacterSpecDefaults:
    """Test that default values are sensible."""

    def test_default_spec_validates(self) -> None:
        spec = CharacterSpec()
        errors = validate_spec(spec)
        assert errors == [], f"Default spec should validate: {errors}"

    def test_default_name(self) -> None:
        spec = CharacterSpec()
        assert spec.name == "Unnamed"

    def test_default_body(self) -> None:
        spec = CharacterSpec()
        assert spec.body.build == "athletic-slender"
        assert spec.body.height_cm == 173.0

    def test_default_hair(self) -> None:
        spec = CharacterSpec()
        assert spec.hair.style == "wild-curly"
        assert spec.hair.shell_layers == 6

    def test_default_export(self) -> None:
        spec = CharacterSpec()
        assert spec.export.format == "vrm1"


class TestSpecValidation:
    """Test validation catches invalid specs."""

    def test_empty_name_fails(self) -> None:
        spec = CharacterSpec(name="")
        errors = validate_spec(spec)
        assert any("name" in e for e in errors)

    def test_invalid_build_fails(self) -> None:
        spec = CharacterSpec(body=BodySpec(build="nonexistent"))
        errors = validate_spec(spec)
        assert any("build" in e for e in errors)

    def test_height_out_of_range(self) -> None:
        spec = CharacterSpec(body=BodySpec(height_cm=50.0))
        errors = validate_spec(spec)
        assert any("height" in e for e in errors)

    def test_invalid_hex_color(self) -> None:
        spec = CharacterSpec(body=BodySpec(skin=SkinSpec(base_hex="red")))
        errors = validate_spec(spec)
        assert any("hex" in e.lower() for e in errors)

    def test_valid_hex_accepted(self) -> None:
        spec = CharacterSpec(body=BodySpec(skin=SkinSpec(base_hex="#E8B87A")))
        errors = validate_spec(spec)
        assert not any("skin.base_hex" in e for e in errors)


class TestSpecRoundTrip:
    """Test that specs can be serialized and deserialized."""

    def test_to_dict_from_dict(self) -> None:
        spec = CharacterSpec(name="Test", body=BodySpec(height_cm=170.0))
        data = spec.to_dict()
        restored = CharacterSpec.from_dict(data)
        assert restored.name == "Test"
        assert restored.body.height_cm == 170.0

    def test_yaml_round_trip(self, tmp_path: Path) -> None:
        spec = Spec(CharacterSpec(name="Round Trip Test"))
        yaml_path = tmp_path / "test_spec.yaml"

        # Write
        spec.to_yaml(yaml_path)
        assert yaml_path.exists()

        # Read back
        restored = Spec.from_yaml(yaml_path)
        assert restored.character.name == "Round Trip Test"


class TestSpecFromYaml:
    """Test loading specs from YAML files."""

    def test_load_example_spec(self) -> None:
        example = Path(__file__).parent.parent / "examples" / "spec_runa_gridweaver.yaml"
        if example.exists():
            spec = Spec.from_yaml(example)
            assert spec.character.name == "Runa Gridweaver"
            assert spec.character.body.build == "athletic-slender"
            assert spec.character.hair.style == "wild-curly"