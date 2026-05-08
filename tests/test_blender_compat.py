"""
Tests for Blender compatibility verification (hamr.blender_bridge.compat).

These tests are pure-Python — they mock ``subprocess.run`` and do not
require ``bpy`` or a Blender installation.  Mark any test that *does*
need a real Blender with ``@pytest.mark.blender``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hamr.blender_bridge.compat import (
    MINIMUM_BLENDER,
    SUPPORTED_BLENDER_VERSIONS,
    BlenderCompatResult,
    BlenderVersion,
    check_blender_available,
    check_blender_compat,
    format_compat_report,
    get_blender_info,
    get_blender_version,
    meets_version,
    verify_addon_compatibility,
)


# ──────────────────────────────────────────────────────────────────────────────
# BlenderVersion dataclass
# ──────────────────────────────────────────────────────────────────────────────


class TestBlenderVersion:
    """Tests for BlenderVersion creation and comparison."""

    def test_creation(self) -> None:
        v = BlenderVersion(major=3, minor=4, patch=1, version_string="3.4.1")
        assert v.major == 3
        assert v.minor == 4
        assert v.patch == 1
        assert v.version_string == "3.4.1"

    def test_from_string_full(self) -> None:
        v = BlenderVersion.from_string("3.4.1")
        assert v is not None
        assert v.major == 3
        assert v.minor == 4
        assert v.patch == 1
        assert v.version_string == "3.4.1"

    def test_from_string_two_part(self) -> None:
        v = BlenderVersion.from_string("4.0")
        assert v is not None
        assert v.major == 4
        assert v.minor == 0
        assert v.patch == 0
        assert v.version_string == "4.0.0"

    def test_from_string_garbage(self) -> None:
        assert BlenderVersion.from_string("not-a-version") is None

    def test_from_string_empty(self) -> None:
        assert BlenderVersion.from_string("") is None

    def test_from_string_patch_zero(self) -> None:
        v = BlenderVersion.from_string("3.0.0")
        assert v is not None
        assert v.patch == 0

    def test_ordering(self) -> None:
        v300 = BlenderVersion(3, 0, 0, "3.0.0")
        v341 = BlenderVersion(3, 4, 1, "3.4.1")
        v400 = BlenderVersion(4, 0, 0, "4.0.0")
        assert v300 < v341
        assert v341 < v400
        assert v400 > v300


# ──────────────────────────────────────────────────────────────────────────────
# meets_version
# ──────────────────────────────────────────────────────────────────────────────


class TestMeetsVersion:
    """Tests for version comparison logic."""

    def test_equal_version(self) -> None:
        v = BlenderVersion(3, 0, 0, "3.0.0")
        assert meets_version(MINIMUM_BLENDER, v) is True

    def test_higher_major(self) -> None:
        v = BlenderVersion(4, 0, 0, "4.0.0")
        assert meets_version(MINIMUM_BLENDER, v) is True

    def test_higher_minor(self) -> None:
        v = BlenderVersion(3, 4, 1, "3.4.1")
        assert meets_version(MINIMUM_BLENDER, v) is True

    def test_lower_major(self) -> None:
        v = BlenderVersion(2, 93, 0, "2.93.0")
        assert meets_version(MINIMUM_BLENDER, v) is False

    def test_lower_minor_same_major(self) -> None:
        v = BlenderVersion(3, 0, 0, "3.0.0")
        minimum = BlenderVersion(3, 4, 0, "3.4.0")
        assert meets_version(minimum, v) is False

    def test_same_major_minor_higher_patch(self) -> None:
        minimum = BlenderVersion(3, 4, 0, "3.4.0")
        v = BlenderVersion(3, 4, 1, "3.4.1")
        assert meets_version(minimum, v) is True

    def test_zero_minimum(self) -> None:
        minimum = BlenderVersion(0, 0, 0, "0.0.0")
        v = BlenderVersion(3, 0, 0, "3.0.0")
        assert meets_version(minimum, v) is True


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────


class TestConstants:
    """Tests for module-level constants."""

    def test_minimum_blender_is_3_0_0(self) -> None:
        assert MINIMUM_BLENDER.major == 3
        assert MINIMUM_BLENDER.minor == 0
        assert MINIMUM_BLENDER.patch == 0
        assert MINIMUM_BLENDER.version_string == "3.0.0"

    def test_supported_versions_has_multiple_entries(self) -> None:
        assert len(SUPPORTED_BLENDER_VERSIONS) >= 2

    def test_minimum_is_in_supported(self) -> None:
        assert MINIMUM_BLENDER in SUPPORTED_BLENDER_VERSIONS


# ──────────────────────────────────────────────────────────────────────────────
# check_blender_available
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckBlenderAvailable:
    """Tests for check_blender_available."""

    def test_returns_bool(self) -> None:
        """Result is always a bool (not None, not int)."""
        result = check_blender_available()
        assert isinstance(result, bool)

    def test_unavailable_path(self) -> None:
        """A nonexistent binary path should return False."""
        result = check_blender_available("/nonexistent/path/to/blender_xyz")
        assert result is False

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_mock_available(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Blender 3.4.1\n")
        assert check_blender_available("blender") is True

    @patch("hamr.blender_bridge.compat.shutil.which", return_value=None)
    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_mock_file_not_found(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        assert check_blender_available("blender") is False

    @patch("hamr.blender_bridge.compat.shutil.which", return_value=None)
    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_mock_timeout(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["blender"], timeout=10)
        assert check_blender_available("blender") is False


# ──────────────────────────────────────────────────────────────────────────────
# get_blender_version
# ──────────────────────────────────────────────────────────────────────────────


class TestGetBlenderVersion:
    """Tests for get_blender_version with mocked subprocess."""

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_parse_standard_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Blender 3.4.1\n",
        )
        v = get_blender_version("blender")
        assert v is not None
        assert v.major == 3
        assert v.minor == 4
        assert v.patch == 1
        assert v.version_string == "3.4.1"

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_parse_with_hash(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Blender 4.0.0 (hash abc1234def)\n",
        )
        v = get_blender_version("blender")
        assert v is not None
        assert v.version_string == "4.0.0"

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_nonzero_exit(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        assert get_blender_version("blender") is None

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_file_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        assert get_blender_version("blender") is None

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["blender"], timeout=10)
        assert get_blender_version("blender") is None


# ──────────────────────────────────────────────────────────────────────────────
# check_blender_compat
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckBlenderCompat:
    """Tests for check_blender_compat."""

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_returns_compat_result(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Blender 3.4.1\n", stderr=""
        )
        result = check_blender_compat("blender")
        assert isinstance(result, BlenderCompatResult)
        assert result.blender_available is True
        assert result.version is not None
        assert result.version.version_string == "3.4.1"

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_unavailable_blender(self, mock_run: MagicMock) -> None:
        """When Blender is not found, result should reflect that."""
        mock_run.side_effect = FileNotFoundError()
        result = check_blender_compat("/no/such/blender")
        assert isinstance(result, BlenderCompatResult)
        assert result.blender_available is False
        assert result.version is None
        assert result.meets_minimum_version is False
        assert len(result.errors) > 0

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_meets_minimum(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Blender 3.4.1\n", stderr=""
        )
        result = check_blender_compat("blender")
        assert result.meets_minimum_version is True

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_below_minimum(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Blender 2.93.0\n", stderr=""
        )
        result = check_blender_compat("blender")
        assert result.meets_minimum_version is False

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_unparseable_version(self, mock_run: MagicMock) -> None:
        """If version string cannot be parsed, result should have errors."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Blender CustomBuild Unknown\n",
            stderr="",
        )
        result = check_blender_compat("blender")
        assert result.version is None
        assert len(result.errors) > 0

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_v4_has_features(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Blender 4.0.0\n", stderr=""
        )
        result = check_blender_compat("blender")
        assert result.supports_headless is True
        assert result.supports_python_scripts is True
        assert result.supports_vrm_export is True
        assert result.supports_eevee is True

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_has_warnings_for_vrm(self, mock_run: MagicMock) -> None:
        """VRM export should always emit a warning about addon dependency."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Blender 3.4.1\n", stderr=""
        )
        result = check_blender_compat("blender")
        vrm_warnings = [w for w in result.warnings if "VRM" in w or "io_scene_vrm" in w]
        assert len(vrm_warnings) > 0


# ──────────────────────────────────────────────────────────────────────────────
# get_blender_info
# ──────────────────────────────────────────────────────────────────────────────


class TestGetBlenderInfo:
    """Tests for get_blender_info."""

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_returns_dict_with_version(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Blender 3.4.1\nBlender Foundation\n",
            stderr="",
        )
        info = get_blender_info("blender")
        assert isinstance(info, dict)
        assert "version" in info
        assert info["version"] == "3.4.1"
        assert "blender_available" in info
        assert info["blender_available"] is True

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_unavailable_returns_dict(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        info = get_blender_info("/no/blender")
        assert isinstance(info, dict)
        assert info["blender_available"] is False

    @patch("hamr.blender_bridge.compat.subprocess.run")
    def test_compat_result_included(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Blender 4.0.0\n", stderr=""
        )
        info = get_blender_info("blender")
        assert "compat_result" in info
        assert isinstance(info["compat_result"], BlenderCompatResult)


# ──────────────────────────────────────────────────────────────────────────────
# format_compat_report
# ──────────────────────────────────────────────────────────────────────────────


class TestFormatCompatReport:
    """Tests for format_compat_report."""

    def test_available_report(self) -> None:
        result = BlenderCompatResult(
            blender_available=True,
            version=BlenderVersion(3, 4, 1, "3.4.1"),
            supports_headless=True,
            supports_python_scripts=True,
            supports_vrm_export=True,
            supports_eevee=True,
            meets_minimum_version=True,
        )
        report = format_compat_report(result)
        assert "3.4.1" in report
        assert "Headless" in report
        assert "Python scripts" in report
        assert "VRM export" in report
        assert "Eevee" in report

    def test_unavailable_report(self) -> None:
        result = BlenderCompatResult(
            blender_available=False,
            version=None,
            supports_headless=False,
            supports_python_scripts=False,
            supports_vrm_export=False,
            supports_eevee=False,
            meets_minimum_version=False,
            errors=["Blender not found"],
        )
        report = format_compat_report(result)
        assert "not available" in report
        assert "Blender not found" in report

    def test_warnings_in_report(self) -> None:
        result = BlenderCompatResult(
            blender_available=True,
            version=BlenderVersion(3, 5, 0, "3.5.0"),
            supports_headless=True,
            supports_python_scripts=True,
            supports_vrm_export=True,
            supports_eevee=True,
            meets_minimum_version=True,
            warnings=["Untested version"],
        )
        report = format_compat_report(result)
        assert "Warnings" in report
        assert "Untested version" in report


# ──────────────────────────────────────────────────────────────────────────────
# verify_addon_compatibility (bpy-guarded)
# ──────────────────────────────────────────────────────────────────────────────


class TestVerifyAddonCompatibility:
    """Tests for verify_addon_compatibility — graceful without bpy."""

    def test_returns_dict_without_bpy(self) -> None:
        """When bpy is not available, should return available=False."""
        result = verify_addon_compatibility()
        assert isinstance(result, dict)
        assert "available" in result
        # On CI without Blender, bpy won't be importable — verify graceful fallback
        if not result["available"]:
            assert "errors" in result
            assert len(result["errors"]) > 0

    @pytest.mark.blender
    def test_with_bpy(self) -> None:
        """When run inside Blender, should return full addon info."""
        result = verify_addon_compatibility()
        if result["available"]:
            assert "io_scene_vrm" in result["addons"]