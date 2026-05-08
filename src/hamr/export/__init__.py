"""
Export Forge — VRM 1.0 and GLB headless export.

The final quench. The blade leaves the forge and enters the world.
"""

from hamr.export.vrm import (
    MB_LAB_BONE_MAP,
    VRM_REQUIRED_BONES,
    setup_vrm_humanoid,
    setup_vrm_metadata,
    setup_vrm_expressions,
    setup_vrm_look_at,
    export_vrm,
)
from hamr.export.glb import export_glb
from hamr.export.first_person import (
    FirstPersonConfig,
    FP_AUTO,
    FP_BOTH,
    FP_THIRD_PERSON_ONLY,
    FP_FIRST_PERSON_ONLY,
    VALID_FP_ANNOTATIONS,
    classify_mesh_for_fp,
    configure_first_person_pure,
    configure_first_person,
)
from hamr.export.vrm_validator import (
    VRMValidationResult,
    VRMValidator,
    parse_vrm_bytes,
    extract_json_chunk,
    is_valid_vrm_binary,
)
from hamr.export.animation_clips import (
    AnimationKeyframe,
    AnimationClip,
    PRESET_CLIPS,
    create_keyframe,
    create_clip,
    validate_clip,
    keyframes_to_dict,
    get_preset_clips,
    clip_to_gltf_animation,
    MB_LAB_TO_VRM,
)

__all__ = [
    # VRM export
    "MB_LAB_BONE_MAP",
    "VRM_REQUIRED_BONES",
    "setup_vrm_humanoid",
    "setup_vrm_metadata",
    "setup_vrm_expressions",
    "setup_vrm_look_at",
    "export_vrm",
    # GLB export
    "export_glb",
    # First-person annotations
    "FirstPersonConfig",
    "FP_AUTO",
    "FP_BOTH",
    "FP_THIRD_PERSON_ONLY",
    "FP_FIRST_PERSON_ONLY",
    "VALID_FP_ANNOTATIONS",
    "classify_mesh_for_fp",
    "configure_first_person_pure",
    "configure_first_person",
    # VRM validator
    "VRMValidationResult",
    "VRMValidator",
    "parse_vrm_bytes",
    "extract_json_chunk",
    "is_valid_vrm_binary",
    # Animation clips
    "AnimationKeyframe",
    "AnimationClip",
    "PRESET_CLIPS",
    "create_keyframe",
    "create_clip",
    "validate_clip",
    "keyframes_to_dict",
    "get_preset_clips",
    "clip_to_gltf_animation",
    "MB_LAB_TO_VRM",
]