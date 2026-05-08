"""
ᚺᚨᛗᚱ — The Shape-Skin Engine

Open-source parametric 3D anime character forge.
Linux-native, headless-first, agent-orchestrated, VRM 1.0.

"Every vertex, every slider, every algorithm is yours."
    — Runa Gridweaver Freyjasdottir

Quick start:
    from hamr import build, validate, inspect
    from hamr.core.models import CharacterSpec, BodySpec

    # Build a character from spec
    output = build("spec.yaml", output_dir="output/")

    # Validate without building
    errors = validate("spec.yaml")

    # Inspect a VRM file
    report = inspect("output/character.vrm", targets=["VRCHAT"])
"""

__version__ = "0.2.0"
__author__ = "Runa Gridweaver Freyjasdottir & Volmarr"

# Core — the sacred contracts
from hamr.core import (
    Spec,
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    HamrError,
    SpecValidationError,
    BuildError,
    ExportError,
    build,
    validate_only,
    inspect,
)

# Blender Bridge — the völva's sight
from hamr.blender_bridge import (
    BlenderResult,
    run_blender_script,
    run_inline_script,
    check_blender_available,
    get_blender_version,
)

# Texture Forge — pure Pillow, no Blender needed
from hamr.core.textures import (
    shift_hsv,
    tint_texture,
    generate_gradient_texture,
    generate_skin_texture,
    generate_hair_texture,
)

# Body Forge — parametric bodies
from hamr.body import BodyForge, BODY_PRESETS, BODY_PRESET_ALIASES

# Export Forge — VRM 1.0 & GLB
from hamr.export import (
    MB_LAB_BONE_MAP,
    VRM_REQUIRED_BONES,
    setup_vrm_humanoid,
    setup_vrm_metadata,
    setup_vrm_expressions,
    setup_vrm_look_at,
    export_vrm,
    export_glb,
)

__all__ = [
    # Core
    "Spec", "CharacterSpec", "BodySpec", "FaceSpec", "HairSpec",
    "HamrError", "SpecValidationError", "BuildError", "ExportError",
    "build", "validate_only", "inspect",
    # Blender Bridge
    "BlenderResult", "run_blender_script", "run_inline_script",
    "check_blender_available", "get_blender_version",
    # Textures
    "shift_hsv", "tint_texture", "generate_gradient_texture",
    "generate_skin_texture", "generate_hair_texture",
    # Body
    "BodyForge", "BODY_PRESETS", "BODY_PRESET_ALIASES",
    # Export
    "MB_LAB_BONE_MAP", "VRM_REQUIRED_BONES",
    "setup_vrm_humanoid", "setup_vrm_metadata",
    "setup_vrm_expressions", "setup_vrm_look_at",
    "export_vrm", "export_glb",
]