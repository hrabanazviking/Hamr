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
]