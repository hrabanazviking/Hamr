"""
Models — All spec dataclasses.

Every parameter, every default, every range lives here.
The spec IS the character.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class HairStyle(str, Enum):
    """Available hair style presets."""
    WILD_CURLY = "wild-curly"
    STRAIGHT = "straight"
    WAVY = "wavy"
    BRAIDED = "braided"
    BUN = "bun"
    PONYTAIL = "ponytail"


class HairLength(str, Enum):
    """Available hair length presets."""
    SHORT = "short"
    MEDIUM = "medium"
    SHOULDER = "shoulder"
    SHOULDER_PLUS = "shoulder-plus"
    LONG = "long"
    VERY_LONG = "very-long"


class ExportFormat(str, Enum):
    """Available export formats."""
    VRM1 = "vrm1"
    GLB = "glb"
    BLEND = "blend"


@dataclass
class SkinSpec:
    base_hex: str = "#E8B87A"
    undertone: str = "warm"  # warm, cool, neutral
    freckles: bool = False
    tan_level: float = 0.7  # 0.0 (pale) to 1.0 (deep tan)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SkinSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BodySpec:
    height_cm: float = 173.0
    build: str = "athletic-slender"  # slug → preset
    skin: SkinSpec = field(default_factory=SkinSpec)
    proportions: dict[str, float] = field(default_factory=lambda: {
        "shoulder_width": 0.4,
        "bust": 0.55,
        "waist": 0.35,
        "hip_width": 0.65,
        "leg_length": 0.55,
    })

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> BodySpec:
        data = copy.deepcopy(data)
        if "skin" in data and isinstance(data["skin"], dict):
            data["skin"] = SkinSpec.from_dict(data["skin"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EyeSpec:
    iris_hex: str = "#B8D4E3"
    shape: str = "cat-tilt"  # cat-tilt, round, narrow, droopy
    size: float = 1.1  # multiplier, 1.0 = naturalistic

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> EyeSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FaceSpec:
    jaw: str = "V-shape"  # V-shape, round, square, heart
    cheekbones: str = "high"
    eyes: EyeSpec = field(default_factory=EyeSpec)
    nose_size: str = "small"
    nose_bridge: str = "narrow"
    lip_fullness: float = 0.7  # 0.0 (thin) to 1.0 (full)
    default_expression: str = "soft-half-smile"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> FaceSpec:
        data = copy.deepcopy(data)
        if "eyes" in data and isinstance(data["eyes"], dict):
            data["eyes"] = EyeSpec.from_dict(data["eyes"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HairColorSpec:
    roots: str = "#C4A265"
    mid: str = "#D4B87A"
    tips: str = "#F5E6B8"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> HairColorSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HairSpec:
    style: str = "wild-curly"  # wild-curly, straight, wavy, braided, bun, ponytail
    length: str = "shoulder-plus"  # short, medium, shoulder-plus, long, very-long
    volume: float = 0.7  # 0.0 (flat) to 1.0 (maximum volume)
    curl_tightness: float = 0.75  # 0.0 (straight) to 1.0 (tight curls)
    color: HairColorSpec = field(default_factory=HairColorSpec)
    shell_layers: int = 6  # number of mesh shell layers for volume

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> HairSpec:
        data = copy.deepcopy(data)
        if "color" in data and isinstance(data["color"], dict):
            data["color"] = HairColorSpec.from_dict(data["color"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ClothingSpec:
    name: str = "default"
    type: str = "full-outfit"  # full-outfit, top, bottom, accessories
    primary_hex: str = "#1A1A3E"
    accent_hex: str = "#00D4FF"
    trim_hex: str = "#FFD700"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ClothingSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MorphWeight:
    name: str = ""
    weight: float = 0.5  # 0.0 to 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomExpressionSpec:
    name: str = ""
    morphs: list[dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CustomExpressionSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExpressionSpec:
    defaults: dict[str, str] = field(default_factory=lambda: {
        "blink": "subtle",
        "blush": "always-on",
    })
    custom: list[CustomExpressionSpec] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ExpressionSpec:
        data = copy.deepcopy(data)
        if "custom" in data and isinstance(data["custom"], list):
            data["custom"] = [
                CustomExpressionSpec.from_dict(e) if isinstance(e, dict) else e
                for e in data["custom"]
            ]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HairPhysicsSpec:
    stiffness: float = 0.35
    gravity: float = 0.3
    drag: float = 0.4


@dataclass
class BreastPhysicsSpec:
    stiffness: float = 0.25
    drag: float = 0.6


@dataclass
class PhysicsSpec:
    hair: HairPhysicsSpec = field(default_factory=HairPhysicsSpec)
    breast: BreastPhysicsSpec = field(default_factory=BreastPhysicsSpec)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PhysicsSpec:
        data = copy.deepcopy(data)
        if "hair" in data and isinstance(data["hair"], dict):
            data["hair"] = HairPhysicsSpec(**data["hair"])
        if "breast" in data and isinstance(data["breast"], dict):
            data["breast"] = BreastPhysicsSpec(**data["breast"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExportSpec:
    format: str = "vrm1"  # vrm1, glb, blend
    title: str = "Hamr Character"
    author: str = "Hamr Forge"
    version: str = "1.0"
    license: str = "CC-BY-4.0"
    contact_url: str = "https://github.com/hrabanazviking/Hamr"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ExportSpec:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CharacterSpec:
    """The complete character specification — the single source of truth."""

    name: str = "Unnamed"
    version: str = "1.0"
    body: BodySpec = field(default_factory=BodySpec)
    face: FaceSpec = field(default_factory=FaceSpec)
    hair: HairSpec = field(default_factory=HairSpec)
    clothing: list[ClothingSpec] = field(default_factory=list)
    expressions: ExpressionSpec = field(default_factory=ExpressionSpec)
    physics: PhysicsSpec = field(default_factory=PhysicsSpec)
    export: ExportSpec = field(default_factory=ExportSpec)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> CharacterSpec:
        """Parse a CharacterSpec from a raw dictionary (e.g., from YAML).

        The input dict is **never** mutated — a deep copy is made before
        any in-place transformation, so callers can safely pass a reference
        to a shared global (e.g. CHARACTER_PRESETS entries).
        """
        data = copy.deepcopy(data)
        fields = {}
        field_map = {
            "body": (BodySpec, {}),
            "face": (FaceSpec, {}),
            "hair": (HairSpec, {}),
            "clothing": (ClothingSpec, []),
            "expressions": (ExpressionSpec, {}),
            "physics": (PhysicsSpec, {}),
            "export": (ExportSpec, {}),
        }

        for key, (spec_cls, default) in field_map.items():
            if key in data and isinstance(data[key], (dict, list)):
                if isinstance(default, list):
                    fields[key] = [spec_cls.from_dict(item) if isinstance(item, dict) else item for item in data[key]]
                else:
                    fields[key] = spec_cls.from_dict(data[key])
            elif key in data:
                fields[key] = data[key]

        # Simple string fields
        for key in ("name", "version"):
            if key in data:
                fields[key] = data[key]

        return cls(**{k: v for k, v in fields.items() if k in cls.__dataclass_fields__})