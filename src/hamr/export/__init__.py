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

__all__ = [
    "MB_LAB_BONE_MAP",
    "VRM_REQUIRED_BONES",
    "setup_vrm_humanoid",
    "setup_vrm_metadata",
    "setup_vrm_expressions",
    "setup_vrm_look_at",
    "export_vrm",
    "export_glb",
]