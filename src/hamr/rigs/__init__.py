"""
Rig Forge — Bone mapping, rigging, and weight painting.

The skeleton beneath the skin. Every bone named, every joint placed.
Every vertex shall move smooth, every weight gradient true.
"""

from hamr.rigs.stub_bones import (
    StubBoneResult,
    STUB_BONE_DEFS,
    compute_stub_position,
    create_missing_bones,
    detect_missing_bones,
    get_stub_bone_map,
)
from hamr.rigs.weights import (
    SMOOTH_REGIONS,
    WeightPaintEngine,
    WeightPaintReport,
    classify_deformation_quality,
    compute_quality_score,
    smooth_weight_map,
)
from hamr.rigs.verify import (
    MB_LAB_NAMES_TO_VRM,
    VRM_BONE_HIERARCHY,
    RigReport,
    RigVerifier,
    check_hierarchy_graph,
    check_naming_conventions_pure,
    cmd_verify_rig,
    generate_rig_report,
    verify_bone_list,
)
from hamr.rigs.spring_bones import (
    SpringBoneGroup,
    SpringBoneCollider,
    HAIR_SPRING_PRESETS,
    BREAST_SPRING_PRESETS,
    CLOTHING_SPRING_PRESETS,
    DEFAULT_COLLIDERS,
    configure_hair_spring,
    configure_breast_spring,
    configure_clothing_spring,
    apply_spring_bones,
)
from hamr.export.vrm import MB_LAB_BONE_MAP, VRM_REQUIRED_BONES
from hamr.core.constants import VRM_25_BONE_NAMES

__all__ = [
    # Stub bones
    "MB_LAB_BONE_MAP",
    "VRM_REQUIRED_BONES",
    "VRM_25_BONE_NAMES",
    "STUB_BONE_DEFS",
    "StubBoneResult",
    "create_missing_bones",
    "detect_missing_bones",
    "compute_stub_position",
    "get_stub_bone_map",
    # Weight paint engine
    "SMOOTH_REGIONS",
    "WeightPaintEngine",
    "WeightPaintReport",
    "compute_quality_score",
    "classify_deformation_quality",
    "smooth_weight_map",
    # Rig verification
    "MB_LAB_NAMES_TO_VRM",
    "VRM_BONE_HIERARCHY",
    "RigReport",
    "RigVerifier",
    "verify_bone_list",
    "check_hierarchy_graph",
    "check_naming_conventions_pure",
    "generate_rig_report",
    "cmd_verify_rig",
    # Spring bones
    "SpringBoneGroup",
    "SpringBoneCollider",
    "HAIR_SPRING_PRESETS",
    "BREAST_SPRING_PRESETS",
    "CLOTHING_SPRING_PRESETS",
    "DEFAULT_COLLIDERS",
    "configure_hair_spring",
    "configure_breast_spring",
    "configure_clothing_spring",
    "apply_spring_bones",
]