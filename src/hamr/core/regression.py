"""
Regression — Performance regression detection for Hamr Phase 15.

Mímir's Measure. The anvil remembers every strike. This module provides
threshold-based regression detection across key pipeline operations,
comparing actual timings against per-GPU-profile baselines.

Every threshold is a promise. Exceed it, and the forge bells ring.

— Eldra Járnsdóttir, The Forge Worker
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ── Dataclasses ────────────────────────────────────────────────────────

@dataclass
class RegressionThreshold:
    """Threshold definition for a single module/metric pair.

    Attributes:
        module: Pipeline operation name (e.g. "spec_validation").
        metric: Metric type — one of "time_seconds", "memory_mb",
            "triangles", "bone_count".
        baseline: Reference value that defines acceptable performance.
        tolerance: Acceptable deviation as a fraction
            (e.g. 0.10 = ±10%, 0.50 = ±50%).
        gpu_profile: Target hardware profile (e.g. "pi5", "desktop").
    """

    module: str
    metric: str
    baseline: float
    tolerance: float
    gpu_profile: str = "pi5"


@dataclass
class RegressionResult:
    """Outcome of comparing an actual value against a baseline threshold.

    Attributes:
        module: Pipeline operation name.
        metric: Metric type.
        baseline: Reference value from the threshold.
        actual: Measured value.
        delta_pct: Percentage change from baseline
            ((actual - baseline) / baseline * 100).
        regressed: True when actual exceeds baseline × (1 + tolerance).
        severity: One of "critical" (>50% regression), "warning"
            (>tolerance regression), or "ok" (within tolerance).
    """

    module: str
    metric: str
    baseline: float
    actual: float
    delta_pct: float
    regressed: bool
    severity: str = ""

    def compute_severity(self, tolerance_pct: float = 0.0) -> str:
        """Compute severity from delta_pct and regression status.

        Severity levels:
            - "critical": delta_pct > 50 (massive regression)
            - "warning": regressed but delta_pct ≤ 50 (above tolerance)
            - "ok": within tolerance or an improvement

        Args:
            tolerance_pct: Tolerance as percentage (e.g. 10.0 for ±10%).
                Unused when the result already carries ``regressed`` —
                severity is inferred from ``regressed`` and ``delta_pct``.

        Returns:
            Severity string: "critical", "warning", or "ok".
        """
        if self.delta_pct > 50.0:
            return "critical"
        if self.regressed:
            return "warning"
        return "ok"


# ── Baseline Thresholds ───────────────────────────────────────────────

BASELINE_THRESHOLDS: dict[str, dict[str, float]] = {
    "spec_validation": {
        "time_seconds": 0.001,
        "tolerance": 0.50,
    },
    "preset_loading": {
        "time_seconds": 0.005,
        "tolerance": 0.50,
    },
    "pipeline_init": {
        "time_seconds": 0.010,
        "tolerance": 0.50,
    },
    "mesh_generation": {
        "time_seconds": 0.100,
        "tolerance": 0.30,
    },
    "bone_rigging": {
        "time_seconds": 0.050,
        "tolerance": 0.30,
    },
    "material_setup": {
        "time_seconds": 0.020,
        "tolerance": 0.30,
    },
    "export_vrm": {
        "time_seconds": 0.200,
        "tolerance": 0.40,
    },
    "full_build_pi5": {
        "time_seconds": 2.0,
        "tolerance": 0.30,
    },
    "full_build_desktop": {
        "time_seconds": 0.5,
        "tolerance": 0.25,
    },
}

# Profile-specific baseline scaling.
# Pi5 is 1.0x (reference), desktop is ~4x faster for CPU-bound ops,
# cloud is ~10x faster.
_PROFILE_SCALE: dict[str, float] = {
    "pi5": 1.0,
    "desktop": 0.25,
    "cloud": 0.10,
}


# ── Core Functions ─────────────────────────────────────────────────────

def load_baselines(profile: str = "pi5") -> list[RegressionThreshold]:
    """Load baseline thresholds for a given GPU profile.

    Scales the canonical baselines by the profile's speed factor so
    that desktop and cloud profiles get proportionally lower baselines.

    Args:
        profile: GPU profile name — "pi5", "desktop", or "cloud".

    Returns:
        List of RegressionThreshold dataclasses for the profile.
    """
    scale = _PROFILE_SCALE.get(profile, 1.0)
    thresholds: list[RegressionThreshold] = []

    for module, values in BASELINE_THRESHOLDS.items():
        baseline = values["time_seconds"] * scale
        tolerance = values["tolerance"]
        thresholds.append(RegressionThreshold(
            module=module,
            metric="time_seconds",
            baseline=round(baseline, 6),
            tolerance=tolerance,
            gpu_profile=profile,
        ))

    return thresholds


def check_regression(
    module: str,
    actual: float,
    profile: str = "pi5",
) -> RegressionResult:
    """Check a single metric against its baseline threshold.

    Args:
        module: Pipeline operation name (must match a BASELINE_THRESHOLDS key).
        actual: Measured value to compare.
        profile: GPU profile for threshold selection.

    Returns:
        RegressionResult with comparison details and severity.
    """
    thresholds = load_baselines(profile)
    threshold = next(
        (t for t in thresholds if t.module == module),
        None,
    )

    if threshold is None:
        # Unknown module — report with zero baseline, no regression flag
        return RegressionResult(
            module=module,
            metric="time_seconds",
            baseline=0.0,
            actual=actual,
            delta_pct=0.0,
            regressed=False,
            severity="ok",
        )

    baseline = threshold.baseline
    tolerance = threshold.tolerance

    if baseline > 0:
        delta_pct = ((actual - baseline) / baseline) * 100.0
    else:
        delta_pct = 0.0 if actual == 0.0 else float("inf")

    regressed = actual > baseline * (1.0 + tolerance)

    result = RegressionResult(
        module=module,
        metric=threshold.metric,
        baseline=baseline,
        actual=actual,
        delta_pct=round(delta_pct, 2),
        regressed=regressed,
        severity="",
    )
    result.severity = result.compute_severity()
    return result


def run_regression_check(
    results: dict[str, float],
    profile: str = "pi5",
) -> list[RegressionResult]:
    """Check multiple module timings against their baselines.

    Args:
        results: Mapping of module name → measured value (seconds).
        profile: GPU profile for threshold selection.

    Returns:
        List of RegressionResult, one per entry in *results*.
    """
    return [
        check_regression(module, actual, profile)
        for module, actual in results.items()
    ]


def generate_baseline_report(results: list[RegressionResult]) -> str:
    """Produce a human-readable text report from regression results.

    Args:
        results: List of RegressionResult to summarise.

    Returns:
        Multi-line string report with status markers and summary.
    """
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("  REGRESSION BASELINE REPORT — Mímir's Measure")
    lines.append("=" * 72)
    lines.append("")

    if not results:
        lines.append("  (no results)")
        lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)

    total = len(results)
    critical_count = 0
    warning_count = 0
    ok_count = 0

    for r in results:
        if r.severity == "critical":
            marker = "✗ CRITICAL"
            critical_count += 1
        elif r.severity == "warning" or r.regressed:
            marker = "⚠ WARNING"
            warning_count += 1
        else:
            marker = "✓ OK"
            ok_count += 1

        lines.append(f"  {marker:14s} {r.module}")
        lines.append(
            f"                "
            f"baseline={r.baseline:.6f}s  "
            f"actual={r.actual:.6f}s  "
            f"delta={r.delta_pct:+.1f}%"
        )
        lines.append(f"                metric={r.metric}")
        lines.append("")

    lines.append("-" * 72)
    lines.append(
        f"  Total: {total}   "
        f"Critical: {critical_count}   "
        f"Warning: {warning_count}   "
        f"OK: {ok_count}"
    )

    if critical_count > 0:
        lines.append("  REGRESSIONS DETECTED — investigate critical failures")
    elif warning_count > 0:
        lines.append("  REGRESSIONS DETECTED — review warnings")
    else:
        lines.append("  ALL CLEAR — no regressions detected")

    lines.append("=" * 72)

    return "\n".join(lines)


# ── Persistence ────────────────────────────────────────────────────────

def save_baselines(
    path: Path,
    results: dict[str, float],
    profile: str = "pi5",
) -> None:
    """Save baseline values to a JSON file.

    The file includes the profile name and all measured values so that
    future runs can compare against a stored reference.

    Args:
        path: File path to write the JSON baseline file.
        results: Mapping of module name → actual value (seconds).
        profile: GPU profile name stored as metadata.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "profile": profile,
        "baselines": results,
    }
    path.write_text(json.dumps(data, indent=2))


def load_saved_baselines(path: Path) -> dict[str, float]:
    """Load baseline values from a JSON file.

    Args:
        path: File path to read the JSON baseline file from.

    Returns:
        Mapping of module name → baseline value (seconds).

    Raises:
        FileNotFoundError: If *path* does not exist.
        json.JSONDecodeError: If *path* contains invalid JSON.
    """
    path = Path(path)
    data = json.loads(path.read_text())
    return data.get("baselines", data)


def compare_baselines(
    old: dict[str, float],
    new: dict[str, float],
    tolerance: float = 0.10,
) -> list[RegressionResult]:
    """Compare two sets of baseline measurements for regressions.

    Modules present in *old* but absent in *new* (or vice-versa) are
    skipped — only modules appearing in both dicts are compared.

    Args:
        old: Previous baseline mapping (module → value in seconds).
        new: Current baseline mapping (module → value in seconds).
        tolerance: Acceptable deviation fraction (default 0.10 = ±10%).

    Returns:
        List of RegressionResult for every module common to both dicts.
    """
    results: list[RegressionResult] = []
    common_keys = set(old.keys()) & set(new.keys())

    for module in sorted(common_keys):
        baseline = old[module]
        actual = new[module]

        if baseline > 0:
            delta_pct = ((actual - baseline) / baseline) * 100.0
        else:
            delta_pct = 0.0 if actual == 0.0 else float("inf")

        regressed = actual > baseline * (1.0 + tolerance)

        result = RegressionResult(
            module=module,
            metric="time_seconds",
            baseline=baseline,
            actual=actual,
            delta_pct=round(delta_pct, 2),
            regressed=regressed,
            severity="",
        )
        result.severity = result.compute_severity()
        results.append(result)

    return results