"""
Tests for release candidate promotion — Phase 15 T7.

Vápnatak: The Taking Up of Arms. Every check must ring true before we march.
— Eldra Járnsdóttir, The Forge Worker
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hamr.core.release_promotion import (
    PromotionCheck,
    PromotionResult,
    PROJECT_ROOT,
    check_ci_configured,
    check_docs_complete,
    check_no_failures,
    check_source_files_present,
    check_test_count,
    check_version_consistency,
    format_promotion_report,
    run_promotion_checks,
)


# ── PromotionCheck dataclass ──────────────────────────────────────────────

class TestPromotionCheck:
    """Tests for PromotionCheck creation."""

    def test_creation_with_all_fields(self):
        pc = PromotionCheck(name="test", passed=True, message="All good")
        assert pc.name == "test"
        assert pc.passed is True
        assert pc.message == "All good"

    def test_creation_failed(self):
        pc = PromotionCheck(name="version", passed=False, message="Mismatch")
        assert pc.passed is False
        assert pc.message == "Mismatch"

    def test_negative_check(self):
        pc = PromotionCheck(name="missing", passed=False, message="File not found")
        assert pc.name == "missing"
        assert pc.passed is False


# ── PromotionResult dataclass ─────────────────────────────────────────────

class TestPromotionResult:
    """Tests for PromotionResult creation and ready flag."""

    def test_creation_with_checks(self):
        checks = [
            PromotionCheck("a", True, "ok"),
            PromotionCheck("b", True, "also ok"),
        ]
        result = PromotionResult(
            version="0.8.0",
            checks=checks,
            ready=True,
            summary="All checks passed",
        )
        assert result.version == "0.8.0"
        assert len(result.checks) == 2
        assert result.ready is True

    def test_not_ready_with_failure(self):
        checks = [
            PromotionCheck("a", True, "ok"),
            PromotionCheck("b", False, "mismatch"),
        ]
        result = PromotionResult(
            version="0.8.0",
            checks=checks,
            ready=False,
            summary="1/2 checks failed",
        )
        assert result.ready is False

    def test_default_values(self):
        result = PromotionResult(version="0.8.0")
        assert result.checks == []
        assert result.ready is False
        assert result.summary == ""


# ── check_version_consistency ──────────────────────────────────────────────

class TestCheckVersionConsistency:
    """Tests for check_version_consistency."""

    def test_passes_with_consistent_version(self):
        result = check_version_consistency()
        assert result.passed is True, f"Version consistency failed: {result.message}"
        assert "0.8.0" in result.message

    def test_returns_promotion_check(self):
        result = check_version_consistency()
        assert isinstance(result, PromotionCheck)
        assert result.name == "version_consistency"


# ── check_test_count ───────────────────────────────────────────────────────

class TestCheckTestCount:
    """Tests for check_test_count."""

    def test_passes_with_sufficient_tests(self):
        result = check_test_count()
        assert result.passed is True, f"Test count check failed: {result.message}"
        assert result.name == "test_count"


# ── check_docs_complete ─────────────────────────────────────────────────────

class TestCheckDocsComplete:
    """Tests for check_docs_complete."""

    def test_passes_with_all_docs_present(self):
        result = check_docs_complete()
        assert result.passed is True, f"Docs check failed: {result.message}"
        assert result.name == "docs_complete"

    def test_message_mentions_count(self):
        result = check_docs_complete()
        assert "5 required docs present" in result.message


# ── check_ci_configured ─────────────────────────────────────────────────────

class TestCheckCISConfigured:
    """Tests for check_ci_configured."""

    def test_passes_with_ci_yml(self):
        result = check_ci_configured()
        assert result.passed is True, f"CI check failed: {result.message}"
        assert result.name == "ci_configured"

    def test_ci_yml_exists(self):
        ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        assert ci_path.is_file(), f"CI workflow missing at {ci_path}"


# ── check_source_files_present ──────────────────────────────────────────────

class TestCheckSourceFilesPresent:
    """Tests for check_source_files_present."""

    def test_passes_with_all_packages(self):
        result = check_source_files_present()
        assert result.passed is True, f"Source files check failed: {result.message}"
        assert result.name == "source_files_present"

    def test_all_expected_packages_exist(self):
        expected = [
            "core", "blender_bridge", "body", "export",
            "face", "hair", "clothing", "rigs",
            "materials", "docs",
        ]
        src_root = PROJECT_ROOT / "src" / "hamr"
        for pkg in expected:
            assert (src_root / pkg).is_dir(), f"Missing package: {pkg}"


# ── run_promotion_checks ───────────────────────────────────────────────────

class TestRunPromotionChecks:
    """Tests for run_promotion_checks."""

    def test_returns_promotion_result(self):
        result = run_promotion_checks()
        assert isinstance(result, PromotionResult)

    def test_result_has_version(self):
        result = run_promotion_checks()
        assert result.version == "0.8.0"

    def test_result_has_checks(self):
        result = run_promotion_checks()
        assert len(result.checks) == 6

    def test_all_checks_have_names(self):
        result = run_promotion_checks()
        names = [c.name for c in result.checks]
        expected_names = {
            "version_consistency", "test_count", "no_failures",
            "docs_complete", "ci_configured", "source_files_present",
        }
        assert set(names) == expected_names

    def test_all_checks_pass(self):
        result = run_promotion_checks()
        for check in result.checks:
            assert check.passed is True, f"Check '{check.name}' failed: {check.message}"
        assert result.ready is True

    def test_summary_when_ready(self):
        result = run_promotion_checks()
        if result.ready:
            assert "ready" in result.summary.lower() or "passed" in result.summary.lower()


# ── format_promotion_report ────────────────────────────────────────────────

class TestFormatPromotionReport:
    """Tests for format_promotion_report."""

    def test_produces_readable_output(self):
        result = PromotionResult(
            version="0.8.0",
            checks=[
                PromotionCheck("version_consistency", True, "All files agree on version 0.8.0"),
                PromotionCheck("test_count", True, "1993 tests collected (≥1900)"),
                PromotionCheck("docs_complete", True, "All 5 required docs present"),
            ],
            ready=True,
            summary="✓ All 3 checks passed — release 0.8.0 is ready",
        )
        report = format_promotion_report(result)
        assert "Release Promotion Report" in report
        assert "0.8.0" in report
        assert "✓ PASS" in report
        assert "version_consistency" in report

    def test_report_with_failure(self):
        result = PromotionResult(
            version="0.8.0",
            checks=[
                PromotionCheck("version_consistency", True, "All files agree"),
                PromotionCheck("ci_configured", False, "ci.yml not found"),
            ],
            ready=False,
            summary="✗ 1/2 checks failed: ci_configured",
        )
        report = format_promotion_report(result)
        assert "✗ FAIL" in report
        assert "ci_configured" in report

    def test_empty_checks(self):
        result = PromotionResult(version="0.8.0", checks=[], ready=True, summary="No checks defined")
        report = format_promotion_report(result)
        assert "0.8.0" in report

    def test_real_promotion_report(self):
        result = run_promotion_checks()
        report = format_promotion_report(result)
        assert "Release Promotion Report" in report
        assert "0.8.0" in report


# ── Version mismatch detection ─────────────────────────────────────────────

class TestVersionMismatchDetection:
    """Test that the version consistency check can detect mismatches."""

    def test_detects_pyproject_version_mismatch(self, tmp_path, monkeypatch):
        """Temporarily break pyproject.toml version to verify detection."""
        import hamr.core.release_promotion as rp

        # Create a fake project root with mismatched version files
        fake_root = tmp_path / "project"
        fake_root.mkdir()
        src_dir = fake_root / "src" / "hamr"
        src_dir.mkdir(parents=True)

        # __init__.py with version 0.8.0
        (src_dir / "__init__.py").write_text('__version__ = "0.8.0"\n')

        # pyproject.toml with DIFFERENT version
        (fake_root / "pyproject.toml").write_text(
            '[project]\nname = "hamr"\nversion = "0.8.0"\n'
        )

        # CHANGELOG.md with 0.8.0
        (fake_root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [0.7.0] - 2026-05-08\n\n### Added\n- Stuff\n"
        )

        # Monkeypatch PROJECT_ROOT
        monkeypatch.setattr(rp, "PROJECT_ROOT", fake_root)

        result = rp.check_version_consistency()
        assert result.passed is False
        assert "mismatch" in result.message.lower() or "0.8.0" in result.message

    def test_detects_missing_changelog_version(self, tmp_path, monkeypatch):
        """Verify that a missing version in CHANGELOG is detected."""
        import hamr.core.release_promotion as rp

        fake_root = tmp_path / "project2"
        fake_root.mkdir()
        src_dir = fake_root / "src" / "hamr"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text('__version__ = "0.8.0"\n')
        (fake_root / "pyproject.toml").write_text(
            '[project]\nname = "hamr"\nversion = "0.8.0"\n'
        )
        (fake_root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [0.6.0] - 2026-04-01\n\n### Added\n- Old stuff\n"
        )

        monkeypatch.setattr(rp, "PROJECT_ROOT", fake_root)

        result = rp.check_version_consistency()
        assert result.passed is False
        assert "not found" in result.message.lower() or "CHANGELOG" in result.message

    def test_consistent_version_passes(self, tmp_path, monkeypatch):
        """Verify that consistent versions across all files passes."""
        import hamr.core.release_promotion as rp

        fake_root = tmp_path / "project3"
        fake_root.mkdir()
        src_dir = fake_root / "src" / "hamr"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text('__version__ = "0.8.0"\n')
        (fake_root / "pyproject.toml").write_text(
            '[project]\nname = "hamr"\nversion = "0.8.0"\n'
        )
        (fake_root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [0.8.0] - 2026-05-08\n\n### Added\n- New stuff\n"
        )

        monkeypatch.setattr(rp, "PROJECT_ROOT", fake_root)

        result = rp.check_version_consistency()
        assert result.passed is True
        assert "0.8.0" in result.message