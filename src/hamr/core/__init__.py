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
from hamr.core.texture_procedural import (
    ProceduralTexture,
    ProceduralTexturePipeline,
    PILLOW_AVAILABLE,
)
from hamr.core.gpu_profiles import (
    GPUProfile,
    GPU_PROFILES,
    get_profile,
    list_profiles,
    auto_detect_profile,
    profile_from_spec,
    validate_profile_compatibility,
    profile_to_budget,
)
from hamr.core.benchmark import (
    BenchmarkResult,
    BenchmarkSuite,
    BENCHMARK_THRESHOLD,
    run_benchmark,
    run_benchmark_suite,
    check_regression,
    get_memory_usage,
    format_benchmark_report,
    save_benchmark_results,
    load_benchmark_results,
    compare_suites,
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
    "ProceduralTexture",
    "ProceduralTexturePipeline",
    "PILLOW_AVAILABLE",
    "GPUProfile",
    "GPU_PROFILES",
    "get_profile",
    "list_profiles",
    "auto_detect_profile",
    "profile_from_spec",
    "validate_profile_compatibility",
    "profile_to_budget",
    "BenchmarkResult",
    "BenchmarkSuite",
    "BENCHMARK_THRESHOLD",
    "run_benchmark",
    "run_benchmark_suite",
    "check_regression",
    "get_memory_usage",
    "format_benchmark_report",
    "save_benchmark_results",
    "load_benchmark_results",
    "compare_suites",
]