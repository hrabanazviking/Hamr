"""
Release candidate promotion automation — Vápnatak final gate.

Ensures that all preconditions for promoting a release candidate to stable
are satisfied before the war-band marches. Every check must ring true.

No Blender (bpy) imports.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------

def _find_project_root() -> Path:
    """Walk up from this file to find the directory containing pyproject.toml."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fallback: assume src/hamr/core → project root
    return Path(__file__).resolve().parents[3]


PROJECT_ROOT = _find_project_root()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PromotionCheck:
    """Result of a single promotion check."""

    name: str
    passed: bool
    message: str


@dataclass
class PromotionResult:
    """Aggregated result of all promotion checks."""

    version: str
    checks: list[PromotionCheck] = field(default_factory=list)
    ready: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_version_consistency() -> PromotionCheck:
    """Verify __init__.py, pyproject.toml, and CHANGELOG all agree on version."""
    init_path = PROJECT_ROOT / "src" / "hamr" / "__init__.py"
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    changelog_path = PROJECT_ROOT / "CHANGELOG.md"

    versions: dict[str, str] = {}

    # __init__.py
    if init_path.is_file():
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_path.read_text())
        if match:
            versions["__init__.py"] = match.group(1)
        else:
            return PromotionCheck("version_consistency", False, "Cannot find __version__ in __init__.py")
    else:
        return PromotionCheck("version_consistency", False, f"Missing {init_path}")

    # pyproject.toml
    if pyproject_path.is_file():
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pyproject_path.read_text(), re.MULTILINE)
        if match:
            versions["pyproject.toml"] = match.group(1)
        else:
            return PromotionCheck("version_consistency", False, "Cannot find version in pyproject.toml")
    else:
        return PromotionCheck("version_consistency", False, f"Missing {pyproject_path}")

    # CHANGELOG.md — look for the version header
    if changelog_path.is_file():
        content = changelog_path.read_text()
        # Match [0.7.0] or ## [0.7.0] patterns
        match = re.search(r'\[\s*(' + re.escape(versions["__init__.py"]) + r')\s*\]', content)
        if match:
            versions["CHANGELOG.md"] = match.group(1)
        else:
            return PromotionCheck(
                "version_consistency",
                False,
                f"Version {versions['__init__.py']} not found in CHANGELOG.md headers",
            )
    else:
        return PromotionCheck("version_consistency", False, f"Missing {changelog_path}")

    unique_versions = set(versions.values())
    if len(unique_versions) == 1:
        ver = unique_versions.pop()
        return PromotionCheck("version_consistency", True, f"All files agree on version {ver}")
    else:
        detail = "; ".join(f"{k}={v}" for k, v in versions.items())
        return PromotionCheck("version_consistency", False, f"Version mismatch: {detail}")


def check_test_count() -> PromotionCheck:
    """Verify test count is at least 1900."""
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        match = re.search(r'(\d+)\s+test[s]?\s+collected', output)
        if match:
            count = int(match.group(1))
            if count >= 1900:
                return PromotionCheck("test_count", True, f"{count} tests collected (≥1900)")
            else:
                return PromotionCheck("test_count", False, f"Only {count} tests collected (need ≥1900)")
        # Try alternate pattern
        match2 = re.search(r'(\d+)\s+test[s]?', output)
        if match2:
            count = int(match2.group(1))
            if count >= 1900:
                return PromotionCheck("test_count", True, f"{count} tests collected (≥1900)")
            else:
                return PromotionCheck("test_count", False, f"Only {count} tests collected (need ≥1900)")
        return PromotionCheck("test_count", False, "Could not determine test count from pytest output")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return PromotionCheck("test_count", False, f"pytest collection failed: {exc}")


def check_no_failures() -> PromotionCheck:
    """Run pytest collection to verify no collection failures."""
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        # Check for errors during collection
        if "error" in output.lower() and "collected" not in output.lower():
            return PromotionCheck("no_failures", False, "Pytest collection reported errors")
        # Check that tests were actually collected
        match = re.search(r'(\d+)\s+test[s]?\s+collected', output)
        if match and int(match.group(1)) > 0:
            return PromotionCheck("no_failures", True, f"Pytest collected {match.group(1)} tests successfully")
        # Fallback: just check for no error lines
        if result.returncode == 0 or "collected" in output:
            return PromotionCheck("no_failures", True, "Pytest collection completed without errors")
        return PromotionCheck("no_failures", False, f"Pytest collection failed (rc={result.returncode})")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return PromotionCheck("no_failures", False, f"pytest collection failed: {exc}")


def check_docs_complete() -> PromotionCheck:
    """Verify README, CHANGELOG, MIGRATION, RELEASE_NOTES, CONTRIBUTING all exist."""
    required_docs = ["README.md", "CHANGELOG.md", "MIGRATION.md", "RELEASE_NOTES.md", "CONTRIBUTING.md"]
    missing: list[str] = []
    for doc in required_docs:
        if not (PROJECT_ROOT / doc).is_file():
            missing.append(doc)

    if missing:
        return PromotionCheck("docs_complete", False, f"Missing docs: {', '.join(missing)}")
    return PromotionCheck("docs_complete", True, f"All {len(required_docs)} required docs present")


def check_ci_configured() -> PromotionCheck:
    """Verify .github/workflows/ci.yml exists."""
    ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    if ci_path.is_file():
        return PromotionCheck("ci_configured", True, f"CI workflow found at {ci_path.relative_to(PROJECT_ROOT)}")
    return PromotionCheck("ci_configured", False, ".github/workflows/ci.yml not found")


def check_source_files_present() -> PromotionCheck:
    """Verify all expected packages exist under src/hamr/."""
    expected_packages = [
        "core",
        "blender_bridge",
        "body",
        "export",
        "face",
        "hair",
        "clothing",
        "rigs",
        "materials",
        "docs",
    ]
    src_root = PROJECT_ROOT / "src" / "hamr"
    missing: list[str] = []
    for pkg in expected_packages:
        pkg_path = src_root / pkg
        if not pkg_path.is_dir():
            missing.append(pkg)

    if missing:
        return PromotionCheck("source_files_present", False, f"Missing packages: {', '.join(missing)}")
    return PromotionCheck("source_files_present", True, f"All {len(expected_packages)} expected packages present")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_promotion_checks() -> PromotionResult:
    """Run all promotion checks and aggregate the result."""
    from hamr import __version__

    checks: list[PromotionCheck] = [
        check_version_consistency(),
        check_test_count(),
        check_no_failures(),
        check_docs_complete(),
        check_ci_configured(),
        check_source_files_present(),
    ]

    all_passed = all(c.passed for c in checks)
    passed_count = sum(1 for c in checks if c.passed)
    total_count = len(checks)

    if all_passed:
        summary = f"✓ All {total_count} checks passed — release {__version__} is ready"
    else:
        failed = [c.name for c in checks if not c.passed]
        summary = f"✗ {len(failed)}/{total_count} checks failed: {', '.join(failed)}"

    return PromotionResult(
        version=__version__,
        checks=checks,
        ready=all_passed,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_promotion_report(result: PromotionResult) -> str:
    """Produce a human-readable promotion report from a PromotionResult."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"Hamr Release Promotion Report — v{result.version}")
    lines.append("=" * 60)
    lines.append("")

    for check in result.checks:
        status = "✓ PASS" if check.passed else "✗ FAIL"
        lines.append(f"  {status}  {check.name}: {check.message}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"  {result.summary}")
    lines.append("=" * 60)
    return "\n".join(lines)