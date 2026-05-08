"""
ᚺᚨᛗᚱ — The Shape-Skin Engine

Open-source parametric 3D anime character forge.
Linux-native, headless-first, agent-orchestrated, VRM 1.0.

"Every vertex, every slider, every algorithm is yours."
"""

__version__ = "0.1.0"
__author__ = "Runa Gridweaver Freyjasdottir & Volmarr"

from hamr.core.spec import Spec, CharacterSpec
from hamr.core.models import (
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

# Public API
from hamr.core.builder import build
from hamr.core.inspect import inspect
from hamr.core.iterate import iterate

__all__ = [
    # Version
    "__version__",
    # Core API
    "build",
    "inspect",
    "iterate",
    "validate_spec",
    # Spec models
    "Spec",
    "CharacterSpec",
    "BodySpec",
    "FaceSpec",
    "HairSpec",
    "ClothingSpec",
    "SkinSpec",
    "ExpressionSpec",
    "PhysicsSpec",
    "ExportSpec",
]