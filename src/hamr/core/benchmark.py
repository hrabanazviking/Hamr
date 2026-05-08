"""
Benchmark — Performance regression benchmarking for Hamr Phase 14.

The anvil tests the metal. This module provides pure-Python benchmarking
to detect performance regressions across key pipeline operations. Every
threshold is sacred — exceed it and the forge bellows stop.

— Eldra Járnsdóttir, The Forge Worker
"""

from __future__ import annotations

import json
import math
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


# ── Benchmark Thresholds ───────────────────────────────────────────────

BENCHMARK_THRESHOLD: dict[str, float] = {
    "spec_creation": 0.01,        # 10ms for spec creation
    "preset_resolution": 0.005,   # 5ms for preset lookup
    "bone_mapping": 0.02,         # 20ms for bone mapping
    "hair_config": 0.01,          # 10ms for hair configuration
    "clothing_config": 0.01,      # 10ms for clothing configuration
    "material_setup": 0.01,       # 10ms for material setup
    "spring_bones": 0.02,         # 20ms for spring bone config
    "collision_setup": 0.01,      # 10ms for collision setup
    "expression_config": 0.01,    # 10ms for expression config
    "full_pipeline_spec": 0.05,   # 50ms for full pipeline spec stage
    "vrm_validation": 0.01,       # 10ms for VRM validation
    "gpu_profile_detection": 0.005,  # 5ms for profile detection
}


# ── Dataclasses ────────────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    """Result of a single benchmark run.

    Attributes:
        name: Benchmark identifier (must match a BENCHMARK_THRESHOLD key).
        duration_seconds: Total wall-clock time for all iterations.
        iterations: Number of times the function was executed.
        mean_seconds: Average time per iteration.
        min_seconds: Fastest iteration time.
        max_seconds: Slowest iteration time.
        std_dev: Standard deviation of iteration times.
        memory_peak_mb: Peak memory usage during the benchmark (MB).
        passed: Whether the benchmark met its threshold.
        threshold_seconds: The budget threshold for this benchmark.
        regression: Whether the benchmark exceeded its threshold.
        metadata: Arbitrary additional key-value information.
    """

    name: str
    duration_seconds: float
    iterations: int = 1
    mean_seconds: float = 0.0
    min_seconds: float = 0.0
    max_seconds: float = 0.0
    std_dev: float = 0.0
    memory_peak_mb: float = 0.0
    passed: bool = True
    threshold_seconds: float = 0.0
    regression: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """A collection of benchmark results with environment metadata.

    Attributes:
        name: Suite identifier (e.g. "hamr-phase14-regression").
        results: List of individual benchmark results.
        timestamp: ISO format timestamp of when the suite was run.
        python_version: Python version string.
        platform_info: Platform information string.
    """

    name: str
    results: list[BenchmarkResult] = field(default_factory=list)
    timestamp: str = ""
    python_version: str = ""
    platform_info: str = ""


# ── Core Benchmark Functions ───────────────────────────────────────────

def run_benchmark(
    name: str,
    func: Callable[[], None],
    iterations: int = 100,
    threshold: float | None = None,
) -> BenchmarkResult:
    """Time a function and detect performance regressions.

    Runs *func* for *iterations* iterations, computes timing statistics,
    checks against the threshold from BENCHMARK_THRESHOLD (or the explicit
    *threshold* argument), and returns a BenchmarkResult.

    Args:
        name: Benchmark identifier. Used to look up the default threshold.
        func: Zero-argument callable to benchmark.
        iterations: Number of iterations to run. Default 100.
        threshold: Explicit threshold in seconds. If None, looks up
            BENCHMARK_THRESHOLD[name]. If not found there either, defaults
            to 0.0 (no threshold check).

    Returns:
        BenchmarkResult with timing statistics and regression detection.
    """
    # Resolve threshold
    if threshold is None:
        threshold = BENCHMARK_THRESHOLD.get(name, 0.0)

    # Record baseline memory
    mem_before = get_memory_usage()

    # Collect per-iteration timings
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)

    duration_seconds = sum(times)
    mean_seconds = statistics.mean(times) if times else 0.0
    min_seconds = min(times) if times else 0.0
    max_seconds = max(times) if times else 0.0
    std_dev = statistics.stdev(times) if len(times) >= 2 else 0.0

    # Record peak memory
    mem_after = get_memory_usage()
    memory_peak_mb = max(mem_before, mem_after)

    # Regression check: did mean time exceed the threshold?
    regression = mean_seconds > threshold if threshold > 0 else False
    passed = not regression

    return BenchmarkResult(
        name=name,
        duration_seconds=duration_seconds,
        iterations=iterations,
        mean_seconds=mean_seconds,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
        std_dev=std_dev,
        memory_peak_mb=memory_peak_mb,
        passed=passed,
        threshold_seconds=threshold,
        regression=regression,
        metadata={},
    )


def run_benchmark_suite(
    funcs: dict[str, Callable[[], None]],
    iterations: int = 100,
) -> BenchmarkSuite:
    """Time multiple functions and package results into a suite.

    Args:
        funcs: Mapping of benchmark name → callable.
        iterations: Number of iterations per benchmark.

    Returns:
        BenchmarkSuite with results for each function.
    """
    results: list[BenchmarkResult] = []
    for name, func in funcs.items():
        result = run_benchmark(name=name, func=func, iterations=iterations)
        results.append(result)

    return BenchmarkSuite(
        name="hamr-benchmark-suite",
        results=results,
        timestamp=datetime.now(timezone.utc).isoformat(),
        python_version=platform.python_version(),
        platform_info=platform.platform(),
    )


def check_regression(
    result: BenchmarkResult,
    threshold: float | None = None,
) -> bool:
    """Check if a benchmark result exceeds its threshold.

    Args:
        result: The benchmark result to check.
        threshold: Explicit threshold in seconds. If None, uses
            result.threshold_seconds.

    Returns:
        True if the result represents a regression (exceeds threshold).
    """
    if threshold is None:
        threshold = result.threshold_seconds
    if threshold <= 0:
        return False
    return result.mean_seconds > threshold


# ── Memory Tracking ────────────────────────────────────────────────────

def get_memory_usage() -> float:
    """Return current process memory usage in MB.

    Uses psutil if available, falls back to /proc/self/status on Linux,
    and returns 0.0 if neither is available.

    Returns:
        Memory usage in megabytes.
    """
    try:
        import psutil  # type: ignore[import-untyped]
        process = psutil.Process()
        return process.memory_info().rss / (1024.0 * 1024.0)
    except ImportError:
        pass

    # Fallback: /proc/self/status on Linux
    try:
        status_path = Path("/proc/self/status")
        if status_path.exists():
            content = status_path.read_text()
            for line in content.splitlines():
                if line.startswith("VmRSS:"):
                    # VmRSS is in kB
                    kb = int(line.split()[1])
                    return kb / 1024.0
    except (OSError, ValueError, IndexError):
        pass

    return 0.0


# ── Reporting ──────────────────────────────────────────────────────────

def format_benchmark_report(suite: BenchmarkSuite) -> str:
    """Format a BenchmarkSuite into a human-readable report.

    Each result is shown with a PASS/FAIL/REGRESSION marker alongside
    timing statistics and threshold information.

    Args:
        suite: The benchmark suite to format.

    Returns:
        Multi-line string report.
    """
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append(f"  BENCHMARK REPORT — {suite.name}")
    lines.append(f"  Timestamp : {suite.timestamp or 'N/A'}")
    lines.append(f"  Python     : {suite.python_version or 'N/A'}")
    lines.append(f"  Platform   : {suite.platform_info or 'N/A'}")
    lines.append("=" * 72)
    lines.append("")

    total = len(suite.results)
    passed = sum(1 for r in suite.results if r.passed and not r.regression)
    regressions = sum(1 for r in suite.results if r.regression)

    for r in suite.results:
        if r.regression:
            marker = "✗ REGRESSION"
        elif r.passed:
            marker = "✓ PASS"
        else:
            marker = "✗ FAIL"

        lines.append(
            f"  {marker:14s} {r.name}"
        )
        lines.append(
            f"                "
            f"mean={r.mean_seconds * 1000:.3f}ms  "
            f"min={r.min_seconds * 1000:.3f}ms  "
            f"max={r.max_seconds * 1000:.3f}ms  "
            f"std={r.std_dev * 1000:.3f}ms"
        )
        lines.append(
            f"                "
            f"threshold={r.threshold_seconds * 1000:.1f}ms  "
            f"iterations={r.iterations}  "
            f"memory={r.memory_peak_mb:.1f}MB"
        )
        lines.append("")

    lines.append("-" * 72)
    lines.append(
        f"  Total: {total}   Passed: {passed}   "
        f"Regressions: {regressions}   Failed: {total - passed}"
    )
    lines.append("=" * 72)

    return "\n".join(lines)


# ── Persistence ────────────────────────────────────────────────────────

def save_benchmark_results(suite: BenchmarkSuite, path: Path) -> None:
    """Save benchmark suite results to a JSON file.

    Args:
        suite: The benchmark suite to save.
        path: File path to write JSON to.
    """
    data = {
        "name": suite.name,
        "timestamp": suite.timestamp,
        "python_version": suite.python_version,
        "platform_info": suite.platform_info,
        "results": [asdict(r) for r in suite.results],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_benchmark_results(path: Path) -> BenchmarkSuite:
    """Load benchmark suite results from a JSON file.

    Args:
        path: File path to read JSON from.

    Returns:
        BenchmarkSuite with all results restored.
    """
    path = Path(path)
    data = json.loads(path.read_text())

    results = [
        BenchmarkResult(**r) for r in data.get("results", [])
    ]

    return BenchmarkSuite(
        name=data.get("name", ""),
        results=results,
        timestamp=data.get("timestamp", ""),
        python_version=data.get("python_version", ""),
        platform_info=data.get("platform_info", ""),
    )


# ── Suite Comparison ───────────────────────────────────────────────────

def compare_suites(
    base: BenchmarkSuite,
    current: BenchmarkSuite,
) -> dict[str, dict]:
    """Compare two benchmark suites for regressions and improvements.

    Matches results by name, then computes the percentage change in
    mean_seconds between the base and current suites.

    Args:
        base: The baseline suite (e.g. from a previous CI run).
        current: The current suite to compare against the baseline.

    Returns:
        Dict mapping benchmark name → comparison info dict with keys:
            - base_mean: baseline mean_seconds
            - current_mean: current mean_seconds
            - delta_seconds: current_mean - base_mean
            - delta_pct: percentage change ((current - base) / base * 100)
            - regression: True if current_mean > base_mean * 1.05 (±5%)
            - improvement: True if current_mean < base_mean * 0.95 (±5%)
            - threshold_seconds: threshold from current result
    """
    base_by_name = {r.name: r for r in base.results}
    current_by_name = {r.name: r for r in current.results}

    comparison: dict[str, dict] = {}

    all_names = set(base_by_name.keys()) | set(current_by_name.keys())

    for name in sorted(all_names):
        base_r = base_by_name.get(name)
        current_r = current_by_name.get(name)

        base_mean = base_r.mean_seconds if base_r else 0.0
        current_mean = current_r.mean_seconds if current_r else 0.0
        threshold = current_r.threshold_seconds if current_r else 0.0

        if base_mean > 0:
            delta_seconds = current_mean - base_mean
            delta_pct = (delta_seconds / base_mean) * 100
        else:
            delta_seconds = current_mean
            delta_pct = 0.0 if current_mean == 0.0 else float("inf")

        # Regression: more than 5% slower
        regression = delta_pct > 5.0
        # Improvement: more than 5% faster
        improvement = delta_pct < -5.0

        comparison[name] = {
            "base_mean": base_mean,
            "current_mean": current_mean,
            "delta_seconds": delta_seconds,
            "delta_pct": delta_pct,
            "regression": regression,
            "improvement": improvement,
            "threshold_seconds": threshold,
        }

    return comparison