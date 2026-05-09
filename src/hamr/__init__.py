"""
ᚺᚨᛗᚱ — The Shape-Skin Engine

Open-source parametric 3D anime character forge.
Linux-native, headless-first, agent-orchestrated, VRM 1.0.

"Every vertex, every slider, every algorithm is yours."

Modules:
    core        — Spec parser, models, validation, constants, pipeline
    blender_bridge — Headless Blender subprocess bridge
    body        — Body Forge: presets, proportion mapping
    export      — Export Forge: VRM 1.0 and GLB export
    face        — Face Forge: shape keys, expression mapping, eye/nose/lip sliders
    hair        — Hair Forge: procedural hair styles, color gradients, physics
    clothing    — Clothing Forge: outfit layers, materials, tinting
    rigs        — Rig mapping reference
"""

__version__ = "0.8.0"
__author__ = "Volmarr & Runa — hrabanazviking"

from hamr.core.spec import Spec
from hamr.core.models import (
    CharacterSpec, BodySpec, SkinSpec, FaceSpec, HairSpec,
    HairColorSpec, ExportSpec,
)
from hamr.core.errors import (
    HamrError, SpecValidationError, BuildError, ExportError,
)
from hamr.core.pipeline import BuildPipeline, PipelineResult
from hamr.hair import resolve_hair, list_hair_presets, list_gradient_presets
from hamr.face import resolve_face, list_jaw_presets, list_eye_shape_presets
from hamr.clothing import resolve_clothing, list_clothing_types, list_material_categories

def get_version() -> str:
    """Return the current Hamr version string."""
    return __version__

__all__ = [
    # Version
    "__version__", "__author__", "get_version",
    # Core
    "Spec",
    "CharacterSpec", "BodySpec", "SkinSpec", "FaceSpec",
    "HairSpec", "HairColorSpec", "ExportSpec",
    # Errors
    "HamrError", "SpecValidationError", "BuildError", "ExportError",
    # Pipeline
    "BuildPipeline", "PipelineResult",
    # Hair Forge
    "resolve_hair", "list_hair_presets", "list_gradient_presets",
    # Face Forge
    "resolve_face", "list_jaw_presets", "list_eye_shape_presets",
    # Clothing Forge
    "resolve_clothing", "list_clothing_types", "list_material_categories",
]