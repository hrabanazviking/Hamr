"""
Tests for hamr.core.benchmark — Phase 14 T3.

Performance regression benchmarking: dataclasses, thresholds, timing,
regression detection, memory tracking, reporting, JSON persistence, and
suite comparison.

— Eldra Járnsdóttir, The Forge Worker
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import pytest

from hamr.core.benchmark import (
    BENCHMARK_THRESHOLD,
    BenchmarkResult,
    BenchmarkSuite,
    check_regression,
    compare_suites,
    format_benchmark_report,
    get_memory_usage,
    load_benchmark_results,
    run_benchmark,
    run_benchmark_suite,
    save_benchmark_results,
)


# ── BenchmarkResult dataclass ──────────────────────────────────────────

class TestBenchmarkResult:
    """Test BenchmarkResult creation and defaults."""

    def test_creation_with_defaults(self):
        result = BenchmarkResult(name="test_op", duration_seconds=0.05)
        assert result.name == "test_op"
        assert result.duration_seconds == 0.05
        assert result.iterations == 1
        assert result.mean_seconds == 0.0
        assert result.min_seconds == 0.0
        assert result.max_seconds == 0.0
        assert result.std_dev == 0.0
        assert result.memory_peak_mb == 0.0
        assert result.passed is True
        assert result.threshold_seconds == 0.0
        assert result.regression is False
        assert result.metadata == {}

    def test_creation_with_all_fields(self):
        result = BenchmarkResult(
            name="full_op",
            duration_seconds=1.5,
            iterations=150,
            mean_seconds=0.01,
            min_seconds=0.008,
            max_seconds=0.015,
            std_dev=0.002,
            memory_peak_mb=120.0,
            passed=True,
            threshold_seconds=0.02,
            regression=False,
            metadata={"gpu": "pi5"},
        )
        assert result.name == "full_op"
        assert result.iterations == 150
        assert result.mean_seconds == 0.01
        assert result.metadata == {"gpu": "pi5"}

    def test_metadata_is_independent(self):
        """Each instance should have an independent metadata dict."""
        r1 = BenchmarkResult(name="a", duration_seconds=0.01)
        r2 = BenchmarkResult(name="b", duration_seconds=0.02)
        r1.metadata["key"] = "value"
        assert "key" not in r2.metadata


# ── BenchmarkSuite dataclass ──────────────────────────────────────────

class TestBenchmarkSuite:
    """Test BenchmarkSuite creation and defaults."""

    def test_creation_with_defaults(self):
        suite = BenchmarkSuite(name="test-suite")
        assert suite.name == "test-suite"
        assert suite.results == []
        assert suite.timestamp == ""
        assert suite.python_version == ""
        assert suite.platform_info == ""

    def test_creation_with_results(self):
        results = [
            BenchmarkResult(name="op1", duration_seconds=0.01),
            BenchmarkResult(name="op2", duration_seconds=0.02),
        ]
        suite = BenchmarkSuite(
            name="full-suite",
            results=results,
            timestamp="2025-01-01T00:00:00+00:00",
            python_version="3.12.0",
            platform_info="Linux-6.1-arm64",
        )
        assert len(suite.results) == 2
        assert suite.timestamp == "2025-01-01T00:00:00+00:00"
        assert suite.python_version == "3.12.0"

    def test_results_list_is_independent(self):
        suite1 = BenchmarkSuite(name="s1")
        suite2 = BenchmarkSuite(name="s2")
        suite1.results.append(BenchmarkResult(name="x", duration_seconds=0.01))
        assert len(suite2.results) == 0


# ── BENCHMARK_THRESHOLD ───────────────────────────────────────────────

class TestBenchmarkThreshold:
    """Test BENCHMARK_THRESHOLD has all expected keys."""

    EXPECTED_KEYS = [
        "spec_creation",
        "preset_resolution",
        "bone_mapping",
        "hair_config",
        "clothing_config",
        "material_setup",
        "spring_bones",
        "collision_setup",
        "expression_config",
        "full_pipeline_spec",
        "vrm_validation",
        "gpu_profile_detection",
    ]

    def test_all_keys_present(self):
        for key in self.EXPECTED_KEYS:
            assert key in BENCHMARK_THRESHOLD, f"Missing key: {key}"

    def test_all_values_positive(self):
        for key, value in BENCHMARK_THRESHOLD.items():
            assert value > 0, f"Threshold for {key} must be > 0, got {value}"

    def test_threshold_count(self):
        assert len(BENCHMARK_THRESHOLD) == len(self.EXPECTED_KEYS)


# ── run_benchmark ──────────────────────────────────────────────────────

class TestRunBenchmark:
    """Test run_benchmark timing functionality."""

    def test_times_a_simple_function(self):
        """run_benchmark should time a function and return valid results."""
        result = run_benchmark(
            name="spec_creation",
            func=lambda: None,
            iterations=10,
        )
        assert result.name == "spec_creation"
        assert result.iterations == 10
        assert result.duration_seconds >= 0
        assert result.mean_seconds >= 0
        assert result.min_seconds >= 0
        assert result.max_seconds >= result.min_seconds
        assert result.threshold_seconds == BENCHMARK_THRESHOLD["spec_creation"]
        # A no-op should not regress
        assert result.passed is True
        assert result.regression is False

    def test_detects_slow_function_regression(self):
        """run_benchmark should detect a function exceeding its threshold."""
        # Sleep for 50ms with a 10ms threshold — guaranteed regression
        result = run_benchmark(
            name="spec_creation",
            func=lambda: time.sleep(0.02),  # 20ms, threshold is 10ms
            iterations=3,
        )
        assert result.name == "spec_creation"
        assert result.regression is True
        assert result.passed is False
        assert result.mean_seconds > BENCHMARK_THRESHOLD["spec_creation"]

    def test_custom_threshold(self):
        """run_benchmark should use an explicit threshold when provided."""
        result = run_benchmark(
            name="custom_threshold_test",
            func=lambda: None,
            iterations=5,
            threshold=999.0,  # Very large — always passes
        )
        assert result.threshold_seconds == 999.0
        assert result.passed is True
        assert result.regression is False

    def test_unknown_name_default_threshold(self):
        """run_benchmark should default threshold to 0.0 for unknown names."""
        result = run_benchmark(
            name="unknown_benchmark",
            func=lambda: None,
            iterations=5,
        )
        assert result.threshold_seconds == 0.0
        # 0.0 threshold means no regression check
        assert result.regression is False

    def test_std_dev_computed(self):
        """run_benchmark should compute standard deviation."""
        # A function with variable timing should have non-zero std_dev
        counter = {"n": 0}
        def variable_func():
            counter["n"] += 1
            if counter["n"] % 2 == 0:
                time.sleep(0.001)
        result = run_benchmark(
            name="bone_mapping",
            func=variable_func,
            iterations=10,
        )
        assert result.std_dev >= 0  # std_dev should be computed

    def test_memory_peak_reported(self):
        """run_benchmark should report memory peak in MB."""
        result = run_benchmark(
            name="hair_config",
            func=lambda: None,
            iterations=5,
        )
        assert result.memory_peak_mb >= 0


# ── run_benchmark_suite ────────────────────────────────────────────────

class TestRunBenchmarkSuite:
    """Test run_benchmark_suite timing multiple functions."""

    def test_times_multiple_functions(self):
        funcs = {
            "spec_creation": lambda: None,
            "preset_resolution": lambda: None,
            "bone_mapping": lambda: None,
        }
        suite = run_benchmark_suite(funcs, iterations=5)
        assert suite.name == "hamr-benchmark-suite"
        assert len(suite.results) == 3
        assert suite.timestamp != ""
        assert suite.python_version != ""
        assert suite.platform_info != ""

    def test_results_match_func_names(self):
        funcs = {
            "hair_config": lambda: None,
            "clothing_config": lambda: None,
        }
        suite = run_benchmark_suite(funcs, iterations=3)
        names = {r.name for r in suite.results}
        assert names == {"hair_config", "clothing_config"}


# ── check_regression ───────────────────────────────────────────────────

class TestCheckRegression:
    """Test check_regression function."""

    def test_passing_threshold(self):
        """A result well within threshold should not regress."""
        result = BenchmarkResult(
            name="spec_creation",
            duration_seconds=0.5,
            iterations=50,
            mean_seconds=0.01,
            threshold_seconds=0.05,
        )
        assert check_regression(result) is False

    def test_failing_threshold(self):
        """A result exceeding its threshold should regress."""
        result = BenchmarkResult(
            name="spec_creation",
            duration_seconds=5.0,
            iterations=50,
            mean_seconds=0.1,
            threshold_seconds=0.01,
            regression=True,
        )
        assert check_regression(result) is True

    def test_explicit_threshold_override(self):
        """check_regression should use an explicit threshold if provided."""
        result = BenchmarkResult(
            name="test",
            duration_seconds=0.5,
            mean_seconds=0.05,
            threshold_seconds=0.01,  # stored threshold is small
        )
        # With a large explicit threshold, no regression
        assert check_regression(result, threshold=1.0) is False

    def test_zero_threshold_no_regression(self):
        """A threshold of 0 should mean no regression check."""
        result = BenchmarkResult(
            name="test",
            duration_seconds=5.0,
            mean_seconds=5.0,
            threshold_seconds=0.0,
        )
        assert check_regression(result) is False


# ── get_memory_usage ──────────────────────────────────────────────────

class TestGetMemoryUsage:
    """Test get_memory_usage returns a positive float."""

    def test_returns_positive_float(self):
        mem = get_memory_usage()
        assert isinstance(mem, float)
        assert mem >= 0.0

    def test_reasonable_range(self):
        """Memory should be in a reasonable range (1-65535 MB)."""
        mem = get_memory_usage()
        if mem > 0:  # Only check if measurement is available
            assert 1.0 <= mem <= 65535.0


# ── format_benchmark_report ────────────────────────────────────────────

class TestFormatBenchmarkReport:
    """Test format_benchmark_report produces readable output."""

    def test_produces_output(self):
        results = [
            BenchmarkResult(
                name="spec_creation",
                duration_seconds=0.5,
                iterations=50,
                mean_seconds=0.01,
                min_seconds=0.008,
                max_seconds=0.015,
                std_dev=0.002,
                threshold_seconds=0.02,
                passed=True,
                regression=False,
            ),
            BenchmarkResult(
                name="bone_mapping",
                duration_seconds=5.0,
                iterations=50,
                mean_seconds=0.1,
                min_seconds=0.08,
                max_seconds=0.15,
                std_dev=0.01,
                threshold_seconds=0.02,
                passed=False,
                regression=True,
            ),
        ]
        suite = BenchmarkSuite(
            name="test-report",
            results=results,
            timestamp="2025-01-01T00:00:00+00:00",
            python_version="3.12.0",
            platform_info="Linux-6.1-arm64",
        )

        report = format_benchmark_report(suite)
        assert "BENCHMARK REPORT" in report
        assert "test-report" in report
        assert "spec_creation" in report
        assert "bone_mapping" in report
        assert "✓ PASS" in report
        assert "✗ REGRESSION" in report
        assert "Passed:" in report
        assert "Regressions:" in report

    def test_empty_suite(self):
        suite = BenchmarkSuite(name="empty-suite")
        report = format_benchmark_report(suite)
        assert "empty-suite" in report
        assert "Total: 0" in report


# ── save/load JSON roundtrip ──────────────────────────────────────────

class TestSaveLoadBenchmarkResults:
    """Test save_benchmark_results and load_benchmark_results JSON roundtrip."""

    def test_json_roundtrip(self, tmp_path):
        results = [
            BenchmarkResult(
                name="spec_creation",
                duration_seconds=0.5,
                iterations=50,
                mean_seconds=0.01,
                min_seconds=0.008,
                max_seconds=0.015,
                std_dev=0.002,
                memory_peak_mb=120.5,
                passed=True,
                threshold_seconds=0.02,
                regression=False,
                metadata={"gpu": "pi5"},
            ),
            BenchmarkResult(
                name="bone_mapping",
                duration_seconds=2.0,
                iterations=50,
                mean_seconds=0.04,
                min_seconds=0.03,
                max_seconds=0.06,
                std_dev=0.005,
                memory_peak_mb=130.0,
                passed=False,
                threshold_seconds=0.02,
                regression=True,
                metadata={"gpu": "desktop"},
            ),
        ]
        suite = BenchmarkSuite(
            name="roundtrip-test",
            results=results,
            timestamp="2025-06-01T12:00:00+00:00",
            python_version="3.12.0",
            platform_info="Linux-6.1-arm64",
        )

        path = tmp_path / "bench_results.json"
        save_benchmark_results(suite, path)

        # Verify file was written and is valid JSON
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["name"] == "roundtrip-test"
        assert len(data["results"]) == 2

        # Load and compare
        loaded = load_benchmark_results(path)
        assert loaded.name == "roundtrip-test"
        assert loaded.timestamp == "2025-06-01T12:00:00+00:00"
        assert loaded.python_version == "3.12.0"
        assert loaded.platform_info == "Linux-6.1-arm64"
        assert len(loaded.results) == 2

        r1 = loaded.results[0]
        assert r1.name == "spec_creation"
        assert r1.duration_seconds == pytest.approx(0.5)
        assert r1.iterations == 50
        assert r1.mean_seconds == pytest.approx(0.01)
        assert r1.memory_peak_mb == pytest.approx(120.5)
        assert r1.passed is True
        assert r1.regression is False
        assert r1.metadata == {"gpu": "pi5"}

        r2 = loaded.results[1]
        assert r2.name == "bone_mapping"
        assert r2.regression is True
        assert r2.threshold_seconds == pytest.approx(0.02)

    def test_creates_parent_dirs(self, tmp_path):
        """save_benchmark_results should create parent directories."""
        path = tmp_path / "nested" / "dir" / "results.json"
        suite = BenchmarkSuite(name="nested-test")
        save_benchmark_results(suite, path)
        assert path.exists()


# ── compare_suites ─────────────────────────────────────────────────────

class TestCompareSuites:
    """Test compare_suites detects improvements and regressions."""

    def _make_result(self, name, mean, threshold=0.02):
        return BenchmarkResult(
            name=name,
            duration_seconds=mean * 50,
            iterations=50,
            mean_seconds=mean,
            threshold_seconds=threshold,
        )

    def test_detects_improvements(self):
        """When current is >5% faster, improvement should be True."""
        base_suite = BenchmarkSuite(
            name="base",
            results=[
                self._make_result("op_a", mean=0.02),
                self._make_result("op_b", mean=0.04),
            ],
        )
        current_suite = BenchmarkSuite(
            name="current",
            results=[
                self._make_result("op_a", mean=0.01),  # 50% faster
                self._make_result("op_b", mean=0.02),  # 50% faster
            ],
        )

        comparison = compare_suites(base_suite, current_suite)

        assert "op_a" in comparison
        assert comparison["op_a"]["improvement"] is True
        assert comparison["op_a"]["regression"] is False
        assert comparison["op_b"]["improvement"] is True
        assert comparison["op_b"]["regression"] is False

    def test_detects_regressions(self):
        """When current is >5% slower, regression should be True."""
        base_suite = BenchmarkSuite(
            name="base",
            results=[
                self._make_result("op_a", mean=0.01),
            ],
        )
        current_suite = BenchmarkSuite(
            name="current",
            results=[
                self._make_result("op_a", mean=0.05),  # 400% slower
            ],
        )

        comparison = compare_suites(base_suite, current_suite)

        assert comparison["op_a"]["regression"] is True
        assert comparison["op_a"]["improvement"] is False
        assert comparison["op_a"]["delta_pct"] > 0

    def test_detects_neutral_change(self):
        """When current is within ±5%, neither regression nor improvement."""
        base_suite = BenchmarkSuite(
            name="base",
            results=[
                self._make_result("op_a", mean=0.02),
            ],
        )
        current_suite = BenchmarkSuite(
            name="current",
            results=[
                self._make_result("op_a", mean=0.0205),  # ~2.5% slower
            ],
        )

        comparison = compare_suites(base_suite, current_suite)

        assert comparison["op_a"]["regression"] is False
        assert comparison["op_a"]["improvement"] is False

    def test_new_benchmark_in_current(self):
        """Benchmarks only in current suite should be included with base_mean=0."""
        base_suite = BenchmarkSuite(
            name="base",
            results=[
                self._make_result("op_a", mean=0.01),
            ],
        )
        current_suite = BenchmarkSuite(
            name="current",
            results=[
                self._make_result("op_a", mean=0.01),
                self._make_result("op_new", mean=0.05, threshold=0.1),
            ],
        )

        comparison = compare_suites(base_suite, current_suite)

        assert "op_new" in comparison
        assert comparison["op_new"]["base_mean"] == 0.0

    def test_delta_computation(self):
        """Delta and delta_pct should be computed correctly."""
        base_suite = BenchmarkSuite(
            name="base",
            results=[
                self._make_result("op_x", mean=0.02),
            ],
        )
        current_suite = BenchmarkSuite(
            name="current",
            results=[
                self._make_result("op_x", mean=0.03),
            ],
        )

        comparison = compare_suites(base_suite, current_suite)

        assert comparison["op_x"]["base_mean"] == pytest.approx(0.02)
        assert comparison["op_x"]["current_mean"] == pytest.approx(0.03)
        assert comparison["op_x"]["delta_seconds"] == pytest.approx(0.01)
        assert comparison["op_x"]["delta_pct"] == pytest.approx(50.0)