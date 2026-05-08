"""
Rig Forge — Bone mapping and rigging.

The skeleton beneath the skin. Every bone named, every joint placed.
"""

from hamr.rigs.stub_bones import (
    StubBoneResult,
    STUB_BONE_DEFS,
    compute_stub_position,
    create_missing_bones,
    detect_missing_bones,
    get_stub_bone_map,
)
from hamr.export.vrm import MB_LAB_BONE_MAP, VRM_REQUIRED_BONES
from hamr.core.constants import VRM_25_BONE_NAMES

__all__ = [
    "MB_LAB_BONE_MAP",
    "VRM_REQUIRED_BONES",
    "VRM_25_BONE_NAMES",
    "STUB_BONE_DEFS",
    "StubBoneResult",
    "create_missing_bones",
    "detect_missing_bones",
    "compute_stub_position",
    "get_stub_bone_map",
]