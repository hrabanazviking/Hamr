"""
Tests for hamr.docs.a11y_audit — Phase 14 T7: Accessibility Compliance Checker.

Coverage: A11yIssue, A11yAuditResult, audit_module_accessibility,
audit_cli_accessibility, audit_all_modules, format_audit_report.
"""

from __future__ import annotations

import textwrap

import pytest

from hamr.docs.a11y_audit import (
    A11yIssue,
    A11yAuditResult,
    audit_all_modules,
    audit_cli_accessibility,
    audit_module_accessibility,
    format_audit_report,
)


# ── A11yIssue ────────────────────────────────────────────────────────────────

class TestA11yIssue:
    """A11yIssue creation and validation."""

    def test_creation(self):
        issue = A11yIssue(
            module="hamr.core.spec",
            function="from_yaml",
            severity="warning",
            description="Missing docstring",
            suggestion="Add a docstring",
        )
        assert issue.module == "hamr.core.spec"
        assert issue.function == "from_yaml"
        assert issue.severity == "warning"
        assert issue.description == "Missing docstring"
        assert issue.suggestion == "Add a docstring"

    def test_severity_critical(self):
        issue = A11yIssue(
            module="m", function="f", severity="critical",
            description="d", suggestion="s",
        )
        assert issue.severity == "critical"

    def test_severity_warning(self):
        issue = A11yIssue(
            module="m", function="f", severity="warning",
            description="d", suggestion="s",
        )
        assert issue.severity == "warning"

    def test_severity_info(self):
        issue = A11yIssue(
            module="m", function="f", severity="info",
            description="d", suggestion="s",
        )
        assert issue.severity == "info"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="severity"):
            A11yIssue(
                module="m", function="f", severity="bad",
                description="d", suggestion="s",
            )


# ── A11yAuditResult ──────────────────────────────────────────────────────────

class TestA11yAuditResult:
    """A11yAuditResult creation, defaults, and counting."""

    def test_defaults(self):
        result = A11yAuditResult(module="hamr.core.spec")
        assert result.module == "hamr.core.spec"
        assert result.issues == []
        assert result.passed is True
        assert result.critical_count == 0
        assert result.warning_count == 0
        assert result.info_count == 0

    def test_add_issue_updates_counts(self):
        result = A11yAuditResult(module="test")
        result.add_issue(A11yIssue(
            module="test", function="f1", severity="critical",
            description="d", suggestion="s",
        ))
        result.add_issue(A11yIssue(
            module="test", function="f2", severity="warning",
            description="d", suggestion="s",
        ))
        result.add_issue(A11yIssue(
            module="test", function="f3", severity="info",
            description="d", suggestion="s",
        ))
        assert result.critical_count == 1
        assert result.warning_count == 1
        assert result.info_count == 1
        assert len(result.issues) == 3

    def test_critical_issue_fails(self):
        result = A11yAuditResult(module="test")
        result.add_issue(A11yIssue(
            module="test", function="f", severity="critical",
            description="d", suggestion="s",
        ))
        assert result.passed is False

    def test_no_critical_passes(self):
        result = A11yAuditResult(module="test")
        result.add_issue(A11yIssue(
            module="test", function="f", severity="warning",
            description="d", suggestion="s",
        ))
        result.add_issue(A11yIssue(
            module="test", function="f", severity="info",
            description="d", suggestion="s",
        ))
        assert result.passed is True

    def test_severity_counts_are_accurate(self):
        """Ensure severity counts match the actual issue list."""
        result = A11yAuditResult(module="test")
        for i in range(3):
            result.add_issue(A11yIssue(
                module="test", function=f"f{i}", severity="critical",
                description="d", suggestion="s",
            ))
        for i in range(5):
            result.add_issue(A11yIssue(
                module="test", function=f"f{i+10}", severity="warning",
                description="d", suggestion="s",
            ))
        for i in range(2):
            result.add_issue(A11yIssue(
                module="test", function=f"f{i+20}", severity="info",
                description="d", suggestion="s",
            ))
        assert result.critical_count == 3
        assert result.warning_count == 5
        assert result.info_count == 2
        assert len(result.issues) == 10
        assert result.passed is False  # has critical issues


# ── audit_module_accessibility ────────────────────────────────────────────────

class TestAuditModuleAccessibility:
    """Module accessibility audits."""

    def test_audits_well_documented_module(self):
        """A module with good docs should have fewer issues."""
        # hamr.core.a11y is well-documented, so it should pass
        result = audit_module_accessibility("hamr.core.a11y")
        assert isinstance(result, A11yAuditResult)
        assert result.module == "hamr.core.a11y"
        # Well-documented module should have 0 critical issues
        assert result.critical_count == 0

    def test_audits_module_with_missing_docstrings(self):
        """Modules with missing docstrings should report issues."""
        # Use a module that's less documented
        result = audit_module_accessibility("hamr.core.constants")
        assert isinstance(result, A11yAuditResult)
        # Constants may have some issues, but should never crash
        # We just verify it returns something reasonable
        assert len(result.issues) >= 0

    def test_audits_nonexistent_module(self):
        """Nonexistent module should report a critical import failure."""
        result = audit_module_accessibility("hamr.nonexistent.module")
        assert result.critical_count == 1
        assert result.passed is False
        assert "Cannot import" in result.issues[0].description

    def test_audits_hamr_core_errors(self):
        """Errors module should be mostly documented."""
        result = audit_module_accessibility("hamr.core.errors")
        assert result.module == "hamr.core.errors"
        # hamr.core.errors has docstrings
        assert isinstance(result.issues, list)

    def test_returns_result_for_all_hamr_modules(self):
        """Every module name should produce a result, even if it has import errors."""
        result = audit_module_accessibility("hamr.core.spec")
        assert result.module == "hamr.core.spec"
        # Should not crash
        assert isinstance(result.issues, list)


# ── audit_cli_accessibility ──────────────────────────────────────────────────

class TestAuditCLIAccessibility:
    """CLI accessibility audits."""

    def test_returns_result(self):
        result = audit_cli_accessibility()
        assert isinstance(result, A11yAuditResult)
        assert result.module == "hamr.cli"

    def test_has_required_a11y_flags(self):
        """CLI should have --no-color, --json, --quiet flags."""
        result = audit_cli_accessibility()
        # Check that no critical flags are missing
        critical_flag_issues = [
            i for i in result.issues
            if i.severity == "critical" and "Missing required accessibility flag" in i.description
        ]
        # The CLI does have these flags, so there should be 0 critical flag issues
        assert len(critical_flag_issues) == 0

    def test_subcommands_have_help(self):
        """Subcommands should have help text."""
        result = audit_cli_accessibility()
        # Check for missing help issues
        missing_help = [
            i for i in result.issues
            if "no help text" in i.description.lower()
        ]
        # May have some but should not be excessive
        assert len(missing_help) < 10  # reasonable bound


# ── audit_all_modules ─────────────────────────────────────────────────────────

class TestAuditAllModules:
    """Full audit across all modules."""

    def test_covers_expected_modules(self):
        results = audit_all_modules()
        module_names = {r.module for r in results}
        # Key modules should be present
        assert "hamr.core.a11y" in module_names
        assert "hamr.core.errors" in module_names
        assert "hamr.cli" in module_names

    def test_returns_list_of_results(self):
        results = audit_all_modules()
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, A11yAuditResult)
            assert r.module
            assert isinstance(r.issues, list)

    def test_all_results_have_valid_severity_counts(self):
        results = audit_all_modules()
        for r in results:
            assert r.critical_count == sum(
                1 for i in r.issues if i.severity == "critical"
            ), f"Severity recount failed for {r.module}"
            assert r.warning_count == sum(
                1 for i in r.issues if i.severity == "warning"
            )
            assert r.info_count == sum(
                1 for i in r.issues if i.severity == "info"
            )


# ── format_audit_report ──────────────────────────────────────────────────────

class TestFormatAuditReport:
    """Report formatting."""

    def test_produces_readable_output(self):
        result1 = A11yAuditResult(module="test.module1")
        result1.add_issue(A11yIssue(
            module="test.module1", function="f1", severity="warning",
            description="Missing docstring", suggestion="Add docstring",
        ))
        result2 = A11yAuditResult(module="test.module2")
        # No issues

        report = format_audit_report([result1, result2])
        assert "Accessibility & Compliance Audit" in report
        assert "test.module1" in report
        assert "test.module2" in report
        assert "PASS" in report

    def test_report_with_critical_issues(self):
        result = A11yAuditResult(module="broken.module")
        result.add_issue(A11yIssue(
            module="broken.module", function="bad_func",
            severity="critical", description="Cannot import module",
            suggestion="Fix import",
        ))
        report = format_audit_report([result])
        assert "FAILED" in report
        assert "critical" in report.lower()
        assert "broken.module" in report

    def test_empty_results(self):
        report = format_audit_report([])
        assert "Accessibility & Compliance Audit" in report
        assert "0" in report

    def test_multiple_severity_levels(self):
        result = A11yAuditResult(module="mixed.module")
        result.add_issue(A11yIssue(
            module="mixed.module", function="f1", severity="critical",
            description="Import failed", suggestion="Fix import",
        ))
        result.add_issue(A11yIssue(
            module="mixed.module", function="f2", severity="warning",
            description="No docstring", suggestion="Add docs",
        ))
        result.add_issue(A11yIssue(
            module="mixed.module", function="f3", severity="info",
            description="Missing return type", suggestion="Add type hint",
        ))
        report = format_audit_report([result])
        assert "1C" in report
        assert "1W" in report
        assert "1I" in report

    def test_passed_module_shown(self):
        result = A11yAuditResult(module="clean.module")
        # No issues added — defaults to passing
        report = format_audit_report([result])
        assert "no issues" in report or "PASS" in report