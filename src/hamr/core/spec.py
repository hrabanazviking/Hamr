"""
Spec — The single source of truth.

The CharacterSpec is the soul of Hamr. Every parameter, every default,
every constraint lives here. No module owns parameters that belong to another.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional

from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    ClothingSpec,
    SkinSpec,
    ExpressionSpec,
    PhysicsSpec,
    ExportSpec,
)
from hamr.core.validate import validate_spec


class Spec:
    """
    Parse, validate, and manipulate character specifications.

    The Spec class is the primary interface for both humans and agents.
    Load from YAML, modify programmatically, export back to YAML.
    """

    def __init__(self, character: CharacterSpec) -> None:
        self.character = character
        self._validate()

    @classmethod
    def from_yaml(cls, path: str | Path) -> Spec:
        """Load a character spec from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Spec file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> Spec:
        """Load a character spec from a dictionary."""
        character = CharacterSpec.from_dict(data)
        return cls(character)

    def to_yaml(self, path: str | Path) -> Path:
        """Export the spec to a YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.character.to_dict()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return path

    def to_dict(self) -> dict:
        """Export the spec as a dictionary."""
        return self.character.to_dict()

    def _validate(self) -> None:
        """Validate the spec against all constraints."""
        errors = validate_spec(self.character)
        if errors:
            from hamr.core.errors import SpecValidationError
            raise SpecValidationError(
                f"Spec validation failed with {len(errors)} errors",
                errors=errors,
            )

    def __repr__(self) -> str:
        return f"Spec(name={self.character.name!r})"