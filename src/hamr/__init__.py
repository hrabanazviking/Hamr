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
    face        — Face Forge: expression mapping (Phase 3)
    hair        — Hair Forge: procedural hair (Phase 3)
    clothing    — Clothing Forge: outfits (Phase 3)
    rigs        — Rig mapping reference
"""

__version__ = "0.3.0"
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

__all__ = [
    # Core
    "Spec",
    "CharacterSpec", "BodySpec", "SkinSpec", "FaceSpec",
    "HairSpec", "HairColorSpec", "ExportSpec",
    # Errors
    "HamrError", "SpecValidationError", "BuildError", "ExportError",
    # Pipeline
    "BuildPipeline", "PipelineResult",
]