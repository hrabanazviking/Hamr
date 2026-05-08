"""
Blender Compatibility Verification for Hamr.

Pure-Python checks that run without ``bpy`` — they shell out to
``blender --version`` and inspect the output.  The one bpy-dependent
function (``verify_addon_compatibility``) is guarded behind an
``ImportError`` so it degrades gracefully on systems without Blender.

Emulates the völva's sight: know the lay of the land before you forge.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("hamr.blender_bridge.compat")


# ──────────────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, order=True)
class BlenderVersion:
    """Parsed Blender version (semantic versioning)."""

    major: int
    minor: int
    patch: int
    version_string: str  # e.g. "3.4.1"

    @classmethod
    def from_string(cls, version_string: str) -> BlenderVersion | None:
        """Parse a version string like ``"3.4.1"`` or ``"4.0"``.

        Returns ``None`` if the string cannot be parsed.
        """
        match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version_string.strip())
        if not match:
            return None
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3) or 0)
        return cls(
            major=major,
            minor=minor,
            patch=patch,
            version_string=f"{major}.{minor}.{patch}",
        )


@dataclass
class BlenderCompatResult:
    """Result of a Blender compatibility check."""

    blender_available: bool
    version: BlenderVersion | None
    supports_headless: bool
    supports_python_scripts: bool
    supports_vrm_export: bool
    supports_eevee: bool
    meets_minimum_version: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Version constants
# ──────────────────────────────────────────────────────────────────────────────

MINIMUM_BLENDER = BlenderVersion(major=3, minor=0, patch=0, version_string="3.0.0")

SUPPORTED_BLENDER_VERSIONS: list[BlenderVersion] = [
    BlenderVersion(major=3, minor=0, patch=0, version_string="3.0.0"),
    BlenderVersion(major=3, minor=4, patch=0, version_string="3.4.0"),
    BlenderVersion(major=4, minor=0, patch=0, version_string="4.0.0"),
]

# Known-good feature matrices per major version
# headless: --background flag exists since 2.5x
# python_scripts: --python flag exists since 2.5x
# vrm_export: requires io_scene_vrm addon >= 2.0
# eevee: available since 2.8
_FEATURE_MATRIX: dict[tuple[int, int], dict[str, bool]] = {
    (3, 0): {"headless": True, "python_scripts": True, "vrm_export": True, "eevee": True},
    (3, 4): {"headless": True, "python_scripts": True, "vrm_export": True, "eevee": True},
    (4, 0): {"headless": True, "python_scripts": True, "vrm_export": True, "eevee": True},
}


# ──────────────────────────────────────────────────────────────────────────────
# Pure-Python compatibility functions (NO bpy import)
# ──────────────────────────────────────────────────────────────────────────────

def check_blender_available(blender_path: str | Path = "blender") -> bool:
    """Check if the Blender binary exists and is executable.

    Args:
        blender_path: Path or name of the Blender executable.

    Returns:
        ``True`` if Blender is available, ``False`` otherwise.
    """
    # First try shutil.which (works for names in PATH)
    resolved = shutil.which(str(blender_path))
    if resolved is not None:
        return True

    # Fall back to trying ``--version`` — catches absolute paths too
    try:
        result = subprocess.run(
            [str(blender_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def get_blender_version(blender_path: str | Path = "blender") -> BlenderVersion | None:
    """Parse the Blender version from ``blender --version`` output.

    Args:
        blender_path: Path or name of the Blender executable.

    Returns:
        A ``BlenderVersion`` on success, or ``None`` if Blender is
        unavailable or the version string cannot be parsed.
    """
    try:
        result = subprocess.run(
            [str(blender_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        # Blender version output typically looks like:
        #   "Blender 3.4.1"  or  "Blender 4.0.0"
        # Sometimes: "Blender 3.4.1 (hash abc1234)"
        first_line = result.stdout.strip().split("\n")[0]
        # Extract version number — the last version-like token on the line
        version_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", first_line)
        if version_match:
            return BlenderVersion.from_string(version_match.group(1))
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def meets_version(minimum: BlenderVersion, actual: BlenderVersion) -> bool:
    """Compare two ``BlenderVersion`` instances.

    Args:
        minimum: The minimum required version.
        actual: The version to check.

    Returns:
        ``True`` if *actual* >= *minimum*, ``False`` otherwise.
    """
    # dataclass is ordered, so direct comparison works because of @dataclass(frozen=True, order=True)
    # and the field ordering: major, minor, patch, version_string
    # However, version_string would mess with ordering, so compare tuples.
    actual_tuple = (actual.major, actual.minor, actual.patch)
    minimum_tuple = (minimum.major, minimum.minor, minimum.patch)
    return actual_tuple >= minimum_tuple


def check_blender_compat(blender_path: str | Path = "blender") -> BlenderCompatResult:
    """Perform a full Blender compatibility check.

    Args:
        blender_path: Path or name of the Blender executable.

    Returns:
        A ``BlenderCompatResult`` detailing whether the installed Blender
        meets Hamr's requirements.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Is Blender available at all?
    available = check_blender_available(blender_path)
    if not available:
        errors.append(f"Blender not found at path: {blender_path}")
        return BlenderCompatResult(
            blender_available=False,
            version=None,
            supports_headless=False,
            supports_python_scripts=False,
            supports_vrm_export=False,
            supports_eevee=False,
            meets_minimum_version=False,
            errors=errors,
            warnings=warnings,
        )

    # 2. Parse version
    version = get_blender_version(blender_path)
    if version is None:
        errors.append("Could not parse Blender version")
        return BlenderCompatResult(
            blender_available=True,
            version=None,
            supports_headless=False,
            supports_python_scripts=False,
            supports_vrm_export=False,
            supports_eevee=False,
            meets_minimum_version=False,
            errors=errors,
            warnings=warnings,
        )

    # 3. Minimum version check
    meets_min = meets_version(MINIMUM_BLENDER, version)
    if not meets_min:
        errors.append(
            f"Blender {version.version_string} is below minimum "
            f"required version {MINIMUM_BLENDER.version_string}"
        )

    # 4. Look up feature matrix
    feature_key = (version.major, version.minor)
    features = _FEATURE_MATRIX.get(feature_key)

    # For versions not in the matrix, infer from major version
    if features is None:
        if version.major >= 4:
            features = {"headless": True, "python_scripts": True, "vrm_export": True, "eevee": True}
            warnings.append(
                f"Blender {version.version_string} is not in the tested "
                f"compatibility matrix — assuming full feature support"
            )
        elif version.major >= 3:
            features = {"headless": True, "python_scripts": True, "vrm_export": True, "eevee": True}
            warnings.append(
                f"Blender {version.version_string} is not in the tested "
                f"compatibility matrix — assuming feature parity with 3.x"
            )
        else:
            features = {"headless": False, "python_scripts": False, "vrm_export": False, "eevee": False}
            errors.append(
                f"Blender {version.version_string} is too old — unsupported"
            )

    # 5. Check if version is in the explicit supported list
    supported_versions_strings = [v.version_string for v in SUPPORTED_BLENDER_VERSIONS]
    if version.version_string not in supported_versions_strings:
        # Check if it's at least a supported minor release family
        is_in_family = any(
            version.major == sv.major and version.minor == sv.minor
            for sv in SUPPORTED_BLENDER_VERSIONS
        )
        if is_in_family:
            warnings.append(
                f"Blender {version.version_string} is a patch release of a "
                f"supported version — likely compatible"
            )
        else:
            warnings.append(
                f"Blender {version.version_string} has not been explicitly "
                f"tested — compatibility is not guaranteed"
            )

    # 6. VRM addon check — we can't verify without bpy, so warn if version is known-good
    supports_vrm = features.get("vrm_export", False)
    if supports_vrm:
        warnings.append(
            "VRM export capability depends on io_scene_vrm addon — "
            "verify addon installation separately"
        )

    return BlenderCompatResult(
        blender_available=available,
        version=version,
        supports_headless=features.get("headless", False),
        supports_python_scripts=features.get("python_scripts", False),
        supports_vrm_export=supports_vrm,
        supports_eevee=features.get("eevee", False),
        meets_minimum_version=meets_min,
        errors=errors,
        warnings=warnings,
    )


def get_blender_info(blender_path: str | Path = "blender") -> dict[str, Any]:
    """Gather comprehensive Blender system information.

    Returns a dict with keys: ``blender_available``, ``version``,
    ``build_info``, and ``compat_result``.

    Args:
        blender_path: Path or name of the Blender executable.

    Returns:
        Dictionary with Blender system information.
    """
    info: dict[str, Any] = {
        "blender_available": False,
        "version": None,
        "build_info": "",
        "compat_result": None,
    }

    try:
        result = subprocess.run(
            [str(blender_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            info["blender_available"] = True
            info["build_info"] = result.stdout.strip()
            version = get_blender_version(blender_path)
            info["version"] = version.version_string if version else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        info["build_info"] = f"Error running blender: {exc}"

    info["compat_result"] = check_blender_compat(blender_path)
    return info


def format_compat_report(result: BlenderCompatResult) -> str:
    """Render a human-readable compatibility report.

    Args:
        result: The ``BlenderCompatResult`` to format.

    Returns:
        Multi-line string suitable for terminal output.
    """
    lines: list[str] = []
    lines.append("═══ Blender Compatibility Report ═══")

    if not result.blender_available:
        lines.append("✗ Blender not available")
        for err in result.errors:
            lines.append(f"  ✗ {err}")
        return "\n".join(lines)

    lines.append(f"✓ Blender available")
    if result.version:
        lines.append(f"  Version: {result.version.version_string}")
    else:
        lines.append("  Version: unknown")

    lines.append("")

    # Version check
    if result.meets_minimum_version:
        lines.append(f"✓ Meets minimum version ({MINIMUM_BLENDER.version_string})")
    else:
        lines.append(f"✗ Below minimum version ({MINIMUM_BLENDER.version_string})")

    # Features
    lines.append("")
    lines.append("── Features ──")
    lines.append(f"  Headless mode:      {'✓' if result.supports_headless else '✗'}")
    lines.append(f"  Python scripts:     {'✓' if result.supports_python_scripts else '✗'}")
    lines.append(f"  VRM export:         {'✓' if result.supports_vrm_export else '✗'}")
    lines.append(f"  Eevee rendering:    {'✓' if result.supports_eevee else '✗'}")

    # Warnings
    if result.warnings:
        lines.append("")
        lines.append("── Warnings ──")
        for w in result.warnings:
            lines.append(f"  ⚠ {w}")

    # Errors
    if result.errors:
        lines.append("")
        lines.append("── Errors ──")
        for e in result.errors:
            lines.append(f"  ✗ {e}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Blender-dependent function (guarded)
# ──────────────────────────────────────────────────────────────────────────────

def verify_addon_compatibility() -> dict[str, Any]:
    """Check installed Blender addons for compatibility.

    **Must run inside a Blender Python environment** (requires ``bpy``).
    If ``bpy`` is not available, returns a dict with ``available=False``.

    Returns:
        Dictionary with addon compatibility information.
    """
    result: dict[str, Any] = {
        "available": False,
        "addons": {},
        "errors": [],
    }

    try:
        import bpy  # type: ignore
        import addon_utils  # type: ignore
    except ImportError:
        result["errors"].append("bpy not available — run inside Blender to check addons")
        return result

    result["available"] = True

    # Check for VRM addon
    try:
        addon_utils.enable("io_scene_vrm", default_set=True)
        result["addons"]["io_scene_vrm"] = {
            "installed": True,
            "compatible": True,
        }
    except Exception as exc:
        result["addons"]["io_scene_vrm"] = {
            "installed": False,
            "compatible": False,
            "error": str(exc),
        }

    # Check for MB-Lab
    try:
        addon_utils.enable("mblab", default_set=True)
        result["addons"]["mblab"] = {
            "installed": True,
            "compatible": True,
        }
    except Exception as exc:
        result["addons"]["mblab"] = {
            "installed": False,
            "compatible": False,
            "error": str(exc),
        }

    # Blender version from bpy
    try:
        result["blender_version"] = (
            f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}"
        )
    except Exception as exc:
        result["errors"].append(f"Could not read bpy.app.version: {exc}")

    return result