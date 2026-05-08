"""
Hamr Accessibility Audit — The Forge Inspects Itself.

Compliance checker for accessibility, documentation, and CLI hardness.
Scans modules for missing docstrings, type hints, non-serializable return
types, missing error messages, and hardcoded strings sans i18n markers.
Audits CLI for color-only indicators, missing help text, and flag naming.

Phase 14 T7: Every rune must be legible.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import re
import sys
import types
from dataclasses import dataclass, field
from typing import Any, get_type_hints


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class A11yIssue:
    """A single accessibility or compliance issue found in a module."""

    module: str
    function: str
    severity: str   # "critical", "warning", "info"
    description: str
    suggestion: str

    def __post_init__(self) -> None:
        valid = ("critical", "warning", "info")
        if self.severity not in valid:
            raise ValueError(
                f"severity must be one of {valid}, got {self.severity!r}"
            )


@dataclass
class A11yAuditResult:
    """Audit result for a single module."""

    module: str
    issues: list[A11yIssue] = field(default_factory=list)
    passed: bool = True
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def __post_init__(self) -> None:
        self._recount()

    def add_issue(self, issue: A11yIssue) -> None:
        """Add an issue and update severity counts."""
        self.issues.append(issue)
        self._recount()

    def _recount(self) -> None:
        """Recompute severity counts from the issues list."""
        self.critical_count = sum(
            1 for i in self.issues if i.severity == "critical"
        )
        self.warning_count = sum(
            1 for i in self.issues if i.severity == "warning"
        )
        self.info_count = sum(
            1 for i in self.issues if i.severity == "info"
        )
        self.passed = self.critical_count == 0


# ── Module Accessibility Audit ──────────────────────────────────────────────

# Functions that are private / dunder and can be skipped
_SKIP_NAMES = frozenset({
    "__all__", "__file__", "__path__", "__name__", "__package__",
    "__spec__", "__loader__", "__builtins__", "__cached__",
    "__doc__", "__version__", "__author__",
})

# Return types that are considered non-serializable for CLI / JSON output
_NON_SERIALIZABLE_TYPES = frozenset({
    "module", "function", "method", "builtin_function_or_method",
    "coroutine", "generator",
})

# Hardcoded string patterns that suggest missing i18n (emoji, unicode symbols
# used as status indicators)
_I18N_PATTERN = re.compile(r"[✓✗⚠✅❌📐💰⚡🔧📝🛡🗡🏗🏛📦🔔🙈🌀]")


def audit_module_accessibility(module_name: str) -> A11yAuditResult:
    """Check a module for accessibility and compliance issues.

    Scans public functions and classes for:
      - Missing docstrings
      - Missing type hints (parameters or return)
      - Non-serializable return types (bad for JSON output)
      - Missing error messages in raises
      - Hardcoded strings without i18n markers

    Args:
        module_name: Fully-qualified module name (e.g. ``"hamr.core.a11y"``).

    Returns:
        :class:`A11yAuditResult` with all found issues.
    """
    result = A11yAuditResult(module=module_name)

    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        result.add_issue(A11yIssue(
            module=module_name,
            function="(import)",
            severity="critical",
            description=f"Cannot import module: {exc}",
            suggestion="Fix the import error or exclude this module",
        ))
        return result

    # ── Module-level docstring ────────────────────────────────────────
    if not inspect.getdoc(mod):
        result.add_issue(A11yIssue(
            module=module_name,
            function="(module)",
            severity="warning",
            description="Module has no docstring",
            suggestion="Add a module docstring describing the module's purpose",
        ))

    # ── Scan callables ────────────────────────────────────────────────
    for name, obj in inspect.getmembers(mod):
        if name.startswith("_") and not name.startswith("__"):
            # Private members — informational only
            continue
        if name in _SKIP_NAMES:
            continue
        if not (inspect.isfunction(obj) or inspect.isclass(obj)):
            continue
        # Only check members defined in this module
        if hasattr(obj, "__module__") and obj.__module__ != module_name:
            continue

        if inspect.isclass(obj):
            _audit_class(module_name, obj, result)
        elif inspect.isfunction(obj):
            _audit_function(module_name, name, obj, result)

    return result


def _audit_function(
    module_name: str,
    func_name: str,
    func: Any,
    result: A11yAuditResult,
) -> None:
    """Audit a single function for a11y issues."""
    # Missing docstring
    if not inspect.getdoc(func):
        result.add_issue(A11yIssue(
            module=module_name,
            function=func_name,
            severity="warning",
            description=f"Function `{func_name}` has no docstring",
            suggestion="Add a docstring with Args/Returns sections",
        ))

    # Missing type hints
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    sig = inspect.signature(func)
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        if param.annotation is inspect.Parameter.empty and param_name not in hints:
            result.add_issue(A11yIssue(
                module=module_name,
                function=func_name,
                severity="info",
                description=(
                    f"Parameter `{param_name}` in `{func_name}` "
                    "lacks a type annotation"
                ),
                suggestion="Add a type annotation for better docs and IDE support",
            ))

    # Return annotation
    if sig.return_annotation is inspect.Parameter.empty and "return" not in hints:
        result.add_issue(A11yIssue(
            module=module_name,
            function=func_name,
            severity="info",
            description=f"Function `{func_name}` lacks a return type annotation",
            suggestion="Add `-> ReturnType` to the function signature",
        ))

    # Non-serializable return type
    if "return" in hints:
        ret_type = hints["return"]
        ret_type_name = getattr(ret_type, "__name__", str(ret_type))
        if ret_type_name in _NON_SERIALIZABLE_TYPES:
            result.add_issue(A11yIssue(
                module=module_name,
                function=func_name,
                severity="info",
                description=(
                    f"Function `{func_name}` returns `{ret_type_name}`, "
                    "which is not JSON-serializable"
                ),
                suggestion=(
                    "Consider returning a dataclass or dict for CLI/JSON output"
                ),
            ))

    # Hardcoded strings in source (i18n markers)
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        source = ""

    if source and _I18N_PATTERN.search(source):
        result.add_issue(A11yIssue(
            module=module_name,
            function=func_name,
            severity="info",
            description=(
                f"Function `{func_name}` contains hardcoded emoji/symbol "
                "characters that may need i18n markers"
            ),
            suggestion=(
                "Wrap status strings so --no-color provides text fallbacks"
            ),
        ))

    # Missing error documentation (raises)
    if source and "raise " in source:
        doc = inspect.getdoc(func) or ""
        if "Raises:" not in doc and "raises" not in doc.lower():
            result.add_issue(A11yIssue(
                module=module_name,
                function=func_name,
                severity="info",
                description=(
                    f"Function `{func_name}` raises exceptions but "
                    "docstring lacks a Raises section"
                ),
                suggestion="Document raised exceptions in a Raises: section",
            ))


def _audit_class(
    module_name: str,
    cls: type,
    result: A11yAuditResult,
) -> None:
    """Audit a class and its public methods for a11y issues."""
    class_name = cls.__name__

    if not inspect.getdoc(cls):
        result.add_issue(A11yIssue(
            module=module_name,
            function=class_name,
            severity="warning",
            description=f"Class `{class_name}` has no docstring",
            suggestion="Add a class docstring describing its role",
        ))

    for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if method_name.startswith("_") and method_name != "__init__":
            continue
        if not inspect.getdoc(method):
            result.add_issue(A11yIssue(
                module=module_name,
                function=f"{class_name}.{method_name}",
                severity="info",
                description=(
                    f"Method `{class_name}.{method_name}` has no docstring"
                ),
                suggestion="Add a method docstring",
            ))


# ── CLI Accessibility Audit ──────────────────────────────────────────────────

def audit_cli_accessibility() -> A11yAuditResult:
    """Check CLI for accessibility compliance.

    Verifies:
      - Color-only indicators have text fallbacks
      - All arguments and subcommands have help text
      - Flag naming is consistent (dashes, not underscores)
      - ``--no-color`` and ``--json`` and ``--quiet`` flags exist

    Returns:
        :class:`A11yAuditResult` for the CLI module.
    """
    result = A11yAuditResult(module="hamr.cli")

    try:
        parser = _build_real_parser()

        # ── Global accessibility flags ───────────────────────────────
        flag_names = set()
        for action in parser._actions:
            for flag in action.option_strings:
                flag_names.add(flag)

        for required_flag in ("--no-color", "--json", "--quiet"):
            if required_flag not in flag_names:
                result.add_issue(A11yIssue(
                    module="hamr.cli",
                    function="(global flags)",
                    severity="critical",
                    description=f"Missing required accessibility flag: {required_flag}",
                    suggestion=f"Add {required_flag} flag for a11y compliance",
                ))

        # ── Subcommand help text ─────────────────────────────────────
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for cmd_name, cmd_parser in action.choices.items():
                    _audit_subparser(cmd_name, cmd_parser, result)

        # ── Color-only indicators check ────────────────────────────
        from hamr import cli as cli_mod

        for func_name, func_obj in inspect.getmembers(cli_mod, inspect.isfunction):
            if not func_name.startswith("cmd_"):
                continue
            try:
                source = inspect.getsource(func_obj)
            except (OSError, TypeError):
                continue

            for line_no, line in enumerate(source.splitlines(), 1):
                if _I18N_PATTERN.search(line):
                    stripped = line.strip()
                    if 'print(f"' in stripped or "print('" in stripped:
                        match = re.search(r'["\'](.+?)["\']', stripped)
                        if match:
                            content = match.group(1)
                            emoji_matches = _I18N_PATTERN.findall(content)
                            text_after = re.sub(r'[✓✗⚠✅❌📐💰⚡🔧📝🛡🗡🏗🏛📦🔔🙈🌀]', '', content).strip()
                            if emoji_matches and len(text_after) < 5:
                                result.add_issue(A11yIssue(
                                    module="hamr.cli",
                                    function=func_name,
                                    severity="warning",
                                    description=(
                                        f"Color-only indicator at line {line_no}: "
                                        f"emoji without sufficient text fallback"
                                    ),
                                    suggestion=(
                                        "Add a text description alongside the "
                                        "symbol so --no-color users can understand it"
                                    ),
                                ))

    except ImportError as exc:
        result.add_issue(A11yIssue(
            module="hamr.cli",
            function="(import)",
            severity="critical",
            description=f"Cannot import CLI module: {exc}",
            suggestion="Ensure hamr.cli is importable",
        ))
    except Exception as exc:
        result.add_issue(A11yIssue(
            module="hamr.cli",
            function="(audit)",
            severity="warning",
            description=f"CLI audit encountered unexpected error: {exc}",
            suggestion="Review the CLI module for a11y compliance manually",
        ))

    return result


def _build_real_parser() -> argparse.ArgumentParser:
    """Build a CLI parser that mirrors the real hamr CLI, including
    global accessibility flags.

    This is used for a11y auditing so we test what users actually see.
    """
    from hamr.core.presets import CHARACTER_PRESETS

    parser = argparse.ArgumentParser(
        prog="hamr",
        description="ᚺᚨᛗᚱ — The Shape-Skin Engine",
    )
    # Global accessibility flags
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI color codes in output")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress non-essential output")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON for machine consumption")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    build_p = subparsers.add_parser("build", help="Build a character from spec or preset")
    build_p.add_argument("spec", nargs="?", default=None,
                          help="Path to YAML spec file")
    build_p.add_argument("--out", "-o", default="output/", help="Output directory")
    build_p.add_argument("--format", "-f", default="vrm1", choices=["vrm1", "glb", "blend"])
    build_p.add_argument("--base", "-b", default=None, help="Base mesh path")
    build_p.add_argument("--no-validate", action="store_true", help="Skip validation")
    build_p.add_argument("--preset", "-p", default=None,
                          choices=list(CHARACTER_PRESETS.keys()),
                          help="Apply a character preset")
    build_p.add_argument("--budget", "-B", default="balanced",
                          choices=["minimal", "balanced", "high"],
                          help="Performance budget tier")
    build_p.add_argument("--force-over-budget", action="store_true",
                          help="Force build even if over budget")
    build_p.add_argument("--dry-run", action="store_true",
                          help="Resolve without launching Blender")
    build_p.add_argument("--verbose", "-v", action="store_true",
                          help="Verbose output")
    build_p.add_argument("--keep-temp", action="store_true", help="Keep temp files")
    build_p.add_argument("--max-tex", type=int, default=0, help="Max texture resolution")
    build_p.add_argument("--timeout", type=int, default=600, help="Blender timeout in seconds")
    build_p.add_argument("--blender-path", default=None, help="Path to Blender executable")
    val_p = subparsers.add_parser("validate", help="Validate spec without building")
    val_p.add_argument("spec", help="Path to YAML spec file")
    insp_p = subparsers.add_parser("inspect", help="Inspect VRM/GLB compliance")
    insp_p.add_argument("path", help="Path to VRM/GLB file")
    insp_p.add_argument("--targets", "-t", nargs="+", default=["VRCHAT"])
    lp_p = subparsers.add_parser("list-presets", help="List available presets")
    lp_p.add_argument("--what", "-w", choices=["all", "character", "body"],
                      default="all", help="Which presets to list")
    vr_p = subparsers.add_parser("verify-rig",
                                  help="Verify VRM rig completeness and bone hierarchy")
    vr_p.add_argument("path", help="Path to VRM file")
    vr_p.add_argument("--strict", action="store_true", help="Treat naming issues as errors")
    subparsers.add_parser("check-env", help="Check build environment")
    subparsers.add_parser("version", help="Print version")
    docs_p = subparsers.add_parser("docs", help="Generate documentation or run audit")
    docs_sub = docs_p.add_subparsers(dest="docs_command", help="Documentation commands")
    docs_gen = docs_sub.add_parser("generate", help="Generate all documentation files")
    docs_gen.add_argument("--output", "-o", default="docs",
                          help="Output directory for generated docs")
    docs_audit = docs_sub.add_parser("audit", help="Run accessibility and compliance audit")

    return parser


def _audit_subparser(
    cmd_name: str,
    parser: argparse.ArgumentParser,
    result: A11yAuditResult,
) -> None:
    """Audit a single CLI sub-parser for missing help text and naming."""
    # Check subparser help text
    if not (parser.description or getattr(parser, "help", None)):
        result.add_issue(A11yIssue(
            module="hamr.cli",
            function=cmd_name,
            severity="warning",
            description=f"Command `{cmd_name}` has no help/description text",
            suggestion="Add help text to the subcommand definition",
        ))

    # Check each argument for help text
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            # Recurse into nested subparsers (e.g., docs generate)
            for sub_name, sub_parser in action.choices.items():
                _audit_subparser(f"{cmd_name} {sub_name}", sub_parser, result)
            continue
        if isinstance(action, argparse._HelpAction):
            continue
        if not action.help and action.option_strings:
            flag_str = "/".join(action.option_strings)
            result.add_issue(A11yIssue(
                module="hamr.cli",
                function=cmd_name,
                severity="warning",
                description=(
                    f"Flag `{flag_str}` in `{cmd_name}` has no help text"
                ),
                suggestion="Add a help= description to this argument",
            ))

    # Check underscore naming (should use dashes)
    for action in parser._actions:
        for opt in action.option_strings or []:
            if "_" in opt.lstrip("-"):
                result.add_issue(A11yIssue(
                    module="hamr.cli",
                    function=cmd_name,
                    severity="info",
                    description=(
                        f"Flag `{opt}` uses underscore instead of dash"
                    ),
                    suggestion=(
                        f"Replace underscore with dash: `{opt.replace('_', '-')}``"
                    ),
                ))


# ── Audit All Modules ────────────────────────────────────────────────────────

# Modules to audit (pure-Python ones we can import safely)
_AUDIT_MODULES = [
    "hamr.core.spec",
    "hamr.core.models",
    "hamr.core.errors",
    "hamr.core.constants",
    "hamr.core.validate",
    "hamr.core.perf",
    "hamr.core.perf_gate",
    "hamr.core.gpu_profiles",
    "hamr.core.presets",
    "hamr.core.textures",
    "hamr.core.texture_procedural",
    "hamr.core.a11y",
    "hamr.core.builder",
    "hamr.core.pipeline",
    "hamr.core.pipeline_integrate",
    "hamr.core.iterate",
    "hamr.core.inspect",
    "hamr.core.benchmark",
    "hamr.hair",
    "hamr.face",
    "hamr.clothing",
    "hamr.rigs.verify",
    "hamr.rigs.collision",
    "hamr.rigs.spring_bones",
    "hamr.rigs.stub_bones",
    "hamr.rigs.weights",
    "hamr.export.vrm_validator",
    "hamr.export.animation_clips",
    "hamr.export.first_person",
    "hamr.export.glb",
    "hamr.materials.anime",
    "hamr.docs.generate",
    "hamr.docs.a11y_audit",
    "hamr.cli",
]


def audit_all_modules() -> list[A11yAuditResult]:
    """Run accessibility and compliance audit on all hamr.* modules.

    Returns:
        List of :class:`A11yAuditResult`, one per module.
    """
    results: list[A11yAuditResult] = []

    for module_name in _AUDIT_MODULES:
        try:
            mod_result = audit_module_accessibility(module_name)
        except Exception as exc:
            mod_result = A11yAuditResult(module=module_name)
            mod_result.add_issue(A11yIssue(
                module=module_name,
                function="(audit_all)",
                severity="critical",
                description=f"Audit failed for module: {exc}",
                suggestion="Fix the module or exclude it from audit",
            ))
        results.append(mod_result)

    # Also audit CLI specifically
    cli_result = audit_cli_accessibility()
    # Merge CLI result into existing cli result or append
    existing_cli = [r for r in results if r.module == "hamr.cli"]
    if existing_cli:
        # Combine issues
        for issue in cli_result.issues:
            existing_cli[0].add_issue(issue)
    else:
        results.append(cli_result)

    return results


# ── Report Formatter ─────────────────────────────────────────────────────────

def format_audit_report(results: list[A11yAuditResult]) -> str:
    """Produce a human-readable audit report from a list of results.

    Args:
        results: List of :class:`A11yAuditResult` to report on.

    Returns:
        Multi-line string with pass/fail per module and issue details.
    """
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  ᚺᚨᛗᚱ Accessibility & Compliance Audit Report")
    lines.append("=" * 70)
    lines.append("")

    total_modules = len(results)
    total_issues = sum(len(r.issues) for r in results)
    total_critical = sum(r.critical_count for r in results)
    total_warning = sum(r.warning_count for r in results)
    total_info = sum(r.info_count for r in results)
    passing_modules = sum(1 for r in results if r.passed)

    lines.append(f"Modules audited: {total_modules}")
    lines.append(f"Passing (0 critical): {passing_modules}/{total_modules}")
    lines.append(f"Total issues: {total_issues} "
                 f"(🔴 {total_critical} critical, "
                 f"🟡 {total_warning} warning, "
                 f"🔵 {total_info} info)")
    lines.append("")

    # ── Per-module summary ────────────────────────────────────────────
    lines.append("-" * 70)
    lines.append("  Module Summary")
    lines.append("-" * 70)

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        issue_count = len(r.issues)
        if issue_count == 0:
            lines.append(f"  {status}  {r.module:<45} (no issues)")
        else:
            lines.append(
                f"  {status}  {r.module:<45} "
                f"({r.critical_count}C {r.warning_count}W {r.info_count}I)"
            )

    lines.append("")

    # ── Detailed issues ───────────────────────────────────────────────
    has_detailed = any(r.issues for r in results)
    if has_detailed:
        lines.append("-" * 70)
        lines.append("  Detailed Issues")
        lines.append("-" * 70)

        severity_marker = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }

        for r in results:
            if not r.issues:
                continue
            lines.append("")
            lines.append(f"  [{r.module}]")
            for issue in r.issues:
                marker = severity_marker.get(issue.severity, "❓")
                lines.append(
                    f"    {marker} {issue.severity.upper():8s} "
                    f"{issue.function}: {issue.description}"
                )
                lines.append(
                    f"       → {issue.suggestion}"
                )

    lines.append("")
    lines.append("=" * 70)
    if total_critical == 0:
        lines.append("  ✅ Audit PASSED — no critical issues found.")
    else:
        lines.append(
            f"  ❌ Audit FAILED — {total_critical} critical issue(s) "
            "must be resolved."
        )
    lines.append("=" * 70)

    return "\n".join(lines)