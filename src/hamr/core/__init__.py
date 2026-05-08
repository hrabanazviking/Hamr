"""
Core — The single source of truth.

Spec parsing, validation, building, and the sacred constants.
These modules never touch Blender directly. They prepare the
data, then hand it to the forges.
"""

from hamr.core.spec import Spec
from hamr.core.models import CharacterSpec, BodySpec, FaceSpec, HairSpec
from hamr.core.errors import HamrError, SpecValidationError, BuildError, ExportError
from hamr.core.builder import build, validate_only, inspect
from hamr.core.perf import (
    PerformanceBudget,
    PerformanceReport,
    TriangleBudget,
    DEFAULT_PI5_BUDGET,
    DEFAULT_TRIANGLE_BUDGET,
    MEMORY_TIERS,
    estimate_build_triangles,
    estimate_memory_usage,
    estimate_build_time,
    check_budget,
    optimize_spec_for_budget,
)
from hamr.core.perf_gate import (
    PerfGateResult,
    PerfGate,
    ESTIMATE_FACTORS,
    select_budget_tier,
    estimate_from_preset,
    format_gate_report,
)

__all__ = [
    "Spec",
    "CharacterSpec",
    "BodySpec",
    "FaceSpec",
    "HairSpec",
    "HamrError",
    "SpecValidationError",
    "BuildError",
    "ExportError",
    "build",
    "validate_only",
    "inspect",
    "PerformanceBudget",
    "PerformanceReport",
    "TriangleBudget",
    "DEFAULT_PI5_BUDGET",
    "DEFAULT_TRIANGLE_BUDGET",
    "MEMORY_TIERS",
    "estimate_build_triangles",
    "estimate_memory_usage",
    "estimate_build_time",
    "check_budget",
    "optimize_spec_for_budget",
    "PerfGateResult",
    "PerfGate",
    "ESTIMATE_FACTORS",
    "select_budget_tier",
    "estimate_from_preset",
    "format_gate_report",
]