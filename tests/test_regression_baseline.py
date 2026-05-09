"""
Tests for Performance Regression Baselines — Phase 15 T4.

Mímir's Measure. Every threshold is tested. The anvil remembers.
— Eldra Járnsdóttir, The Forge Worker
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hamr.core.regression import (
    BASELINE_THRESHOLDS,
    RegressionResult,
    RegressionThreshold,
    check_regression,
    compare_baselines,
    generate_baseline_report,
    load_baselines,
    load_saved_baselines,
    run_regression_check,
    save_baselines,
)


# ── RegressionThreshold ────────────────────────────────────────────────

class TestRegressionThreshold:
    """Tests for RegressionThreshold dataclass creation and defaults."""

    def test_creation_with_all_fields(self):
        t = RegressionThreshold(
            module="spec_validation",
            metric="time_seconds",
            baseline=0.001,
            tolerance=0.50,
            gpu_profile="pi5",
        )
        assert t.module == "spec_validation"
        assert t.metric == "time_seconds"
        assert t.baseline == 0.001
        assert t.tolerance == 0.50
        assert t.gpu_profile == "pi5"

    def test_default_gpu_profile(self):
        t = RegressionThreshold(
            module="mesh_generation",
            metric="time_seconds",
            baseline=0.100,
            tolerance=0.30,
        )
        assert t.gpu_profile == "pi5"

    def test_desktop_profile(self):
        t = RegressionThreshold(
            module="mesh_generation",
            metric="time_seconds",
            baseline=0.025,
            tolerance=0.30,
            gpu_profile="desktop",
        )
        assert t.gpu_profile == "desktop"

    def test_different_metrics(self):
        for metric in ("time_seconds", "memory_mb", "triangles", "bone_count"):
            t = RegressionThreshold(
                module="test", metric=metric, baseline=1.0, tolerance=0.1,
            )
            assert t.metric == metric


# ── RegressionResult ───────────────────────────────────────────────────

class TestRegressionResult:
    """Tests for RegressionResult dataclass creation and severity."""

    def test_creation_with_all_fields(self):
        r = RegressionResult(
            module="spec_validation",
            metric="time_seconds",
            baseline=0.001,
            actual=0.0012,
            delta_pct=20.0,
            regressed=False,
            severity="ok",
        )
        assert r.module == "spec_validation"
        assert r.baseline == 0.001
        assert r.actual == 0.0012
        assert r.delta_pct == 20.0
        assert r.regressed is False
        assert r.severity == "ok"

    def test_default_severity_empty(self):
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=1.1,
            delta_pct=10.0,
            regressed=True,
        )
        assert r.severity == ""

    def test_compute_severity_ok(self):
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=0.9,
            delta_pct=-10.0,
            regressed=False,
        )
        assert r.compute_severity() == "ok"

    def test_compute_severity_warning(self):
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=1.2,
            delta_pct=20.0,
            regressed=True,
        )
        assert r.compute_severity() == "warning"

    def test_compute_severity_critical(self):
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=2.0,
            delta_pct=100.0,
            regressed=True,
        )
        assert r.compute_severity() == "critical"

    def test_compute_severity_boundary_warning(self):
        """Slightly positive delta is warning, not critical."""
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=1.05,
            delta_pct=5.0,
            regressed=True,
        )
        assert r.compute_severity() == "warning"

    def test_compute_severity_boundary_critical(self):
        """Exactly 50% is critical (>= is not used, but > 50 is critical)."""
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=1.6,
            delta_pct=60.0,
            regressed=True,
        )
        assert r.compute_severity() == "critical"

    def test_compute_severity_zero_delta(self):
        """Zero delta (actual == baseline) is ok."""
        r = RegressionResult(
            module="test",
            metric="time_seconds",
            baseline=1.0,
            actual=1.0,
            delta_pct=0.0,
            regressed=False,
        )
        assert r.compute_severity() == "ok"


# ── BASELINE_THRESHOLDS Coverage ───────────────────────────────────────

class TestBaselineThresholds:
    """Tests for the BASELINE_THRESHOLDS dictionary."""

    EXPECTED_MODULES = [
        "spec_validation",
        "preset_loading",
        "pipeline_init",
        "mesh_generation",
        "bone_rigging",
        "material_setup",
        "export_vrm",
        "full_build_pi5",
        "full_build_desktop",
    ]

    def test_has_all_key_operations(self):
        for module in self.EXPECTED_MODULES:
            assert module in BASELINE_THRESHOLDS, (
                f"Missing module: {module}"
            )

    def test_has_time_seconds_key(self):
        for module, values in BASELINE_THRESHOLDS.items():
            assert "time_seconds" in values, (
                f"Module {module} missing 'time_seconds'"
            )

    def test_has_tolerance_key(self):
        for module, values in BASELINE_THRESHOLDS.items():
            assert "tolerance" in values, (
                f"Module {module} missing 'tolerance'"
            )

    def test_baselines_are_positive(self):
        for module, values in BASELINE_THRESHOLDS.items():
            assert values["time_seconds"] > 0, (
                f"Module {module} has non-positive baseline"
            )

    def test_tolerances_are_positive(self):
        for module, values in BASELINE_THRESHOLDS.items():
            assert 0 < values["tolerance"] <= 1.0, (
                f"Module {module} has invalid tolerance: {values['tolerance']}"
            )

    def test_pi5_baseline_slower_than_desktop(self):
        pi5_time = BASELINE_THRESHOLDS["full_build_pi5"]["time_seconds"]
        desk_time = BASELINE_THRESHOLDS["full_build_desktop"]["time_seconds"]
        assert pi5_time > desk_time, (
            "Pi5 baseline should be slower (higher) than desktop"
        )


# ── load_baselines ─────────────────────────────────────────────────────

class TestLoadBaselines:
    """Tests for load_baselines function."""

    def test_pi5_profile_default(self):
        thresholds = load_baselines()
        assert len(thresholds) == len(BASELINE_THRESHOLDS)
        for t in thresholds:
            assert t.gpu_profile == "pi5"
            assert t.metric == "time_seconds"

    def test_pi5_profile_explicit(self):
        thresholds = load_baselines("pi5")
        assert len(thresholds) == len(BASELINE_THRESHOLDS)
        # Pi5 baselines match the canonical values
        for t in thresholds:
            canonical = BASELINE_THRESHOLDS[t.module]
            assert t.baseline == round(canonical["time_seconds"] * 1.0, 6)

    def test_desktop_profile_scaled(self):
        thresholds = load_baselines("desktop")
        assert len(thresholds) == len(BASELINE_THRESHOLDS)
        for t in thresholds:
            assert t.gpu_profile == "desktop"
            # Desktop should be ~0.25x of pi5 baselines
            canonical = BASELINE_THRESHOLDS[t.module]
            expected = round(canonical["time_seconds"] * 0.25, 6)
            assert t.baseline == expected

    def test_cloud_profile_scaled(self):
        thresholds = load_baselines("cloud")
        assert len(thresholds) == len(BASELINE_THRESHOLDS)
        for t in thresholds:
            assert t.gpu_profile == "cloud"
            canonical = BASELINE_THRESHOLDS[t.module]
            expected = round(canonical["time_seconds"] * 0.10, 6)
            assert t.baseline == expected

    def test_unknown_profile_uses_default_scale(self):
        """Unknown profile falls back to scale factor 1.0."""
        thresholds = load_baselines("unknown_device")
        assert len(thresholds) == len(BASELINE_THRESHOLDS)
        for t in thresholds:
            assert t.gpu_profile == "unknown_device"

    def test_modules_match_canonical(self):
        thresholds = load_baselines("pi5")
        threshold_modules = {t.module for t in thresholds}
        canonical_modules = set(BASELINE_THRESHOLDS.keys())
        assert threshold_modules == canonical_modules


# ── check_regression ────────────────────────────────────────────────────

class TestCheckRegression:
    """Tests for check_regression function."""

    def test_passing_within_tolerance(self):
        """Value within tolerance should not be regressed."""
        result = check_regression("spec_validation", 0.0012)
        # baseline=0.001, tolerance=0.50, so ceiling = 0.0015
        assert result.regressed is False
        assert result.severity == "ok"

    def test_passing_exactly_at_baseline(self):
        """Value exactly at baseline is ok."""
        result = check_regression("spec_validation", 0.001)
        assert result.regressed is False
        assert result.severity == "ok"

    def test_failing_above_tolerance(self):
        """Value above tolerance ceiling should regress."""
        # spec_validation baseline=0.001, tolerance=0.50
        # ceiling = 0.001 * 1.5 = 0.0015
        result = check_regression("spec_validation", 0.002)
        assert result.regressed is True
        assert result.severity == "critical"

    def test_failing_slightly_above_tolerance(self):
        """Value just above tolerance ceiling is a regression."""
        # spec_validation baseline=0.001, tolerance=0.50
        # ceiling = 0.0015
        result = check_regression("spec_validation", 0.0016)
        assert result.regressed is True

    def test_improvement_negative_delta(self):
        """Value below baseline is an improvement."""
        result = check_regression("spec_validation", 0.0005)
        assert result.regressed is False
        assert result.delta_pct < 0
        assert result.severity == "ok"

    def test_desktop_profile(self):
        """Desktop profile uses scaled baselines."""
        # full_build_desktop has a separate canonical entry
        result = check_regression("full_build_desktop", 0.6, profile="pi5")
        # baseline = 0.5, tolerance = 0.25, ceiling = 0.625
        assert result.regressed is False

    def test_desktop_profile_regression(self):
        result = check_regression("full_build_desktop", 0.7, profile="pi5")
        # baseline = 0.5, tolerance = 0.25, ceiling = 0.625
        # 0.7 > 0.625 → regressed
        assert result.regressed is True

    def test_unknown_module(self):
        """Unknown module gets a zero-baseline result, not regressed."""
        result = check_regression("unknown_module_xyz", 0.5)
        assert result.regressed is False
        assert result.baseline == 0.0
        assert result.severity == "ok"

    def test_mesh_generation_regression(self):
        # mesh_generation baseline=0.100, tolerance=0.30
        # ceiling = 0.100 * 1.3 = 0.130
        result = check_regression("mesh_generation", 0.200)
        assert result.regressed is True
        assert result.severity == "critical"

    def test_mesh_generation_ok(self):
        result = check_regression("mesh_generation", 0.120)
        assert result.regressed is False

    def test_delta_pct_calculation(self):
        result = check_regression("spec_validation", 0.0015)
        # delta_pct = (0.0015 - 0.001) / 0.001 * 100 = 50.0
        assert result.delta_pct == 50.0


# ── run_regression_check ────────────────────────────────────────────────

class TestRunRegressionCheck:
    """Tests for run_regression_check function."""

    def test_mixed_results(self):
        results = {
            "spec_validation": 0.001,       # exactly baseline → ok
            "mesh_generation": 0.200,        # above tolerance → regressed
            "preset_loading": 0.003,         # below baseline → ok
        }
        checks = run_regression_check(results, profile="pi5")
        assert len(checks) == 3

        by_module = {c.module: c for c in checks}
        assert by_module["spec_validation"].regressed is False
        assert by_module["mesh_generation"].regressed is True
        assert by_module["preset_loading"].regressed is False

    def test_all_passing(self):
        results = {
            "spec_validation": 0.0005,
            "preset_loading": 0.003,
            "pipeline_init": 0.008,
        }
        checks = run_regression_check(results, profile="pi5")
        assert all(not c.regressed for c in checks)

    def test_all_failing(self):
        results = {
            "spec_validation": 0.010,
            "preset_loading": 0.050,
            "pipeline_init": 0.100,
        }
        checks = run_regression_check(results, profile="pi5")
        assert all(c.regressed for c in checks)

    def test_empty_results(self):
        checks = run_regression_check({}, profile="pi5")
        assert checks == []

    def test_desktop_profile_check(self):
        """Desktop baselines are scaled down by 0.25."""
        # pipeline_init pi5 baseline = 0.010
        # desktop baseline = 0.010 * 0.25 = 0.0025
        # ceiling = 0.0025 * 1.5 = 0.00375
        results = {"pipeline_init": 0.003}
        checks = run_regression_check(results, profile="desktop")
        assert len(checks) == 1
        assert checks[0].regressed is False


# ── generate_baseline_report ───────────────────────────────────────────

class TestGenerateBaselineReport:
    """Tests for generate_baseline_report function."""

    def test_produces_readable_output(self):
        results = [
            RegressionResult(
                module="spec_validation",
                metric="time_seconds",
                baseline=0.001,
                actual=0.001,
                delta_pct=0.0,
                regressed=False,
                severity="ok",
            ),
            RegressionResult(
                module="mesh_generation",
                metric="time_seconds",
                baseline=0.100,
                actual=0.200,
                delta_pct=100.0,
                regressed=True,
                severity="critical",
            ),
        ]
        report = generate_baseline_report(results)
        assert "REGRESSION BASELINE REPORT" in report
        assert "spec_validation" in report
        assert "mesh_generation" in report
        assert "✓ OK" in report
        assert "✗ CRITICAL" in report

    def test_empty_results(self):
        report = generate_baseline_report([])
        assert "REGRESSION BASELINE REPORT" in report
        assert "no results" in report

    def test_summary_counts(self):
        results = [
            RegressionResult("a", "time_seconds", 1.0, 1.5, 50.0, True, "critical"),
            RegressionResult("b", "time_seconds", 1.0, 1.1, 10.0, True, "warning"),
            RegressionResult("c", "time_seconds", 1.0, 0.9, -10.0, False, "ok"),
        ]
        report = generate_baseline_report(results)
        assert "Critical: 1" in report
        assert "Warning: 1" in report
        assert "OK: 1" in report

    def test_all_clear_message(self):
        results = [
            RegressionResult("a", "time_seconds", 1.0, 0.9, -10.0, False, "ok"),
        ]
        report = generate_baseline_report(results)
        assert "ALL CLEAR" in report

    def test_warning_message(self):
        results = [
            RegressionResult("a", "time_seconds", 1.0, 1.2, 20.0, True, "warning"),
        ]
        report = generate_baseline_report(results)
        assert "REGRESSIONS DETECTED" in report

    def test_critical_message(self):
        results = [
            RegressionResult("a", "time_seconds", 1.0, 2.0, 100.0, True, "critical"),
        ]
        report = generate_baseline_report(results)
        assert "investigate critical" in report


# ── save_baselines / load_saved_baselines round-trip ───────────────────

class TestBaselinePersistence:
    """Tests for save_baselines and load_saved_baselines round-trip."""

    def test_round_trip(self, tmp_path):
        data = {
            "spec_validation": 0.001,
            "mesh_generation": 0.100,
            "full_build_pi5": 2.0,
        }
        path = tmp_path / "baselines.json"
        save_baselines(path, data, profile="pi5")

        loaded = load_saved_baselines(path)
        assert loaded == data

    def test_file_created(self, tmp_path):
        data = {"spec_validation": 0.001}
        path = tmp_path / "subdir" / "baselines.json"
        save_baselines(path, data, profile="desktop")
        assert path.exists()

    def test_file_content_is_valid_json(self, tmp_path):
        data = {"preset_loading": 0.005}
        path = tmp_path / "baselines.json"
        save_baselines(path, data)

        raw = json.loads(path.read_text())
        assert raw["profile"] == "pi5"
        assert raw["baselines"] == data

    def test_load_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_saved_baselines(path)

    def test_desktop_profile_saved(self, tmp_path):
        data = {"pipeline_init": 0.0025}
        path = tmp_path / "desktop_baselines.json"
        save_baselines(path, data, profile="desktop")

        raw = json.loads(path.read_text())
        assert raw["profile"] == "desktop"

    def test_numeric_precision(self, tmp_path):
        """Floating-point values survive round-trip."""
        data = {"mesh_generation": 0.1000001}
        path = tmp_path / "baselines.json"
        save_baselines(path, data)

        loaded = load_saved_baselines(path)
        assert loaded["mesh_generation"] == data["mesh_generation"]


# ── compare_baselines ───────────────────────────────────────────────────

class TestCompareBaselines:
    """Tests for compare_baselines function."""

    def test_detects_regression(self):
        old = {"spec_validation": 0.001, "mesh_generation": 0.100}
        new = {"spec_validation": 0.002, "mesh_generation": 0.200}
        results = compare_baselines(old, new, tolerance=0.10)
        assert len(results) == 2
        assert all(r.regressed for r in results)

    def test_detects_improvement(self):
        old = {"spec_validation": 0.001}
        new = {"spec_validation": 0.0005}
        results = compare_baselines(old, new, tolerance=0.10)
        assert len(results) == 1
        assert results[0].regressed is False
        assert results[0].delta_pct < 0
        assert results[0].severity == "ok"

    def test_within_tolerance(self):
        old = {"spec_validation": 0.001}
        new = {"spec_validation": 0.00105}  # 5% increase, within 10%
        results = compare_baselines(old, new, tolerance=0.10)
        assert len(results) == 1
        assert results[0].regressed is False

    def test_skips_modules_not_in_both(self):
        old = {"spec_validation": 0.001, "only_in_old": 0.010}
        new = {"spec_validation": 0.001, "only_in_new": 0.020}
        results = compare_baselines(old, new, tolerance=0.10)
        assert len(results) == 1
        assert results[0].module == "spec_validation"

    def test_custom_tolerance(self):
        old = {"mesh_generation": 0.100}
        new = {"mesh_generation": 0.115}  # 15% increase
        # With 10% tolerance → regression
        strict = compare_baselines(old, new, tolerance=0.10)
        assert strict[0].regressed is True

        # With 20% tolerance → ok
        lenient = compare_baselines(old, new, tolerance=0.20)
        assert lenient[0].regressed is False

    def test_zero_baseline(self):
        old = {"test_module": 0.0}
        new = {"test_module": 0.01}
        results = compare_baselines(old, new, tolerance=0.10)
        # 0 baseline with non-zero actual → inf delta
        assert results[0].delta_pct == float("inf")

    def test_both_zero(self):
        old = {"test_module": 0.0}
        new = {"test_module": 0.0}
        results = compare_baselines(old, new, tolerance=0.10)
        assert results[0].delta_pct == 0.0
        assert results[0].regressed is False

    def test_severity_levels(self):
        """Verify severity classification in compare_baselines."""
        old = {
            "ok_module": 1.0,
            "warning_module": 1.0,
            "critical_module": 1.0,
        }
        new = {
            "ok_module": 0.9,        # -10% → ok
            "warning_module": 1.2,    # +20% → warning
            "critical_module": 2.0,   # +100% → critical
        }
        results = compare_baselines(old, new, tolerance=0.10)
        by_module = {r.module: r for r in results}
        assert by_module["ok_module"].severity == "ok"
        assert by_module["warning_module"].severity == "warning"
        assert by_module["critical_module"].severity == "critical"

    def test_empty_dicts(self):
        results = compare_baselines({}, {}, tolerance=0.10)
        assert results == []

    def test_sorted_output(self):
        old = {"z_module": 1.0, "a_module": 1.0, "m_module": 1.0}
        new = {"z_module": 1.0, "a_module": 1.0, "m_module": 1.0}
        results = compare_baselines(old, new, tolerance=0.10)
        modules = [r.module for r in results]
        assert modules == sorted(modules)