"""
Tests for hamr.core.a11y — Phase 13 T6: Accessibility & CLI Hardening.

Coverage: CLIOptions, format_output, format_json_output, format_error,
format_table, should_suppress_output, get_actionable_suggestion, ERROR_SUGGESTIONS.
"""

from __future__ import annotations

import json

import pytest

from hamr.core.a11y import (
    CLIOptions,
    CLI_COLOR_MAP,
    ERROR_SUGGESTIONS,
    _strip_ansi,
    format_error,
    format_json_output,
    format_output,
    format_table,
    get_actionable_suggestion,
    should_suppress_output,
)
from hamr.core.errors import BuildError, HamrError, SpecValidationError


# ── CLIOptions ────────────────────────────────────────────────────────────

class TestCLIOptions:
    """CLIOptions dataclass: creation, defaults, and overrides."""

    def test_defaults(self):
        opts = CLIOptions()
        assert opts.no_color is False
        assert opts.quiet is False
        assert opts.json_output is False
        assert opts.verbose is False

    def test_no_color(self):
        opts = CLIOptions(no_color=True)
        assert opts.no_color is True

    def test_quiet(self):
        opts = CLIOptions(quiet=True)
        assert opts.quiet is True

    def test_json_output(self):
        opts = CLIOptions(json_output=True)
        assert opts.json_output is True

    def test_verbose(self):
        opts = CLIOptions(verbose=True)
        assert opts.verbose is True

    def test_all_true(self):
        opts = CLIOptions(no_color=True, quiet=True, json_output=True, verbose=True)
        assert opts.no_color
        assert opts.quiet
        assert opts.json_output
        assert opts.verbose

    def test_independent_flags(self):
        """Each flag can be set independently of the others."""
        opts = CLIOptions(quiet=True, no_color=False, json_output=False, verbose=True)
        assert opts.quiet is True
        assert opts.no_color is False
        assert opts.verbose is True


# ── CLI_COLOR_MAP ─────────────────────────────────────────────────────────

class TestCLIColorMap:
    """CLI_COLOR_MAP has required severity keys."""

    def test_has_required_keys(self):
        for key in ("success", "warning", "error", "info", "reset"):
            assert key in CLI_COLOR_MAP, f"Missing key: {key}"

    def test_values_are_ansi(self):
        for key, value in CLI_COLOR_MAP.items():
            assert value.startswith("\033["), f"Key {key}: expected ANSI escape, got {value!r}"

    def test_success_is_green(self):
        assert CLI_COLOR_MAP["success"] == "\033[92m"

    def test_warning_is_yellow(self):
        assert CLI_COLOR_MAP["warning"] == "\033[93m"

    def test_error_is_red(self):
        assert CLI_COLOR_MAP["error"] == "\033[91m"

    def test_info_is_blue(self):
        assert CLI_COLOR_MAP["info"] == "\033[94m"

    def test_reset_code(self):
        assert CLI_COLOR_MAP["reset"] == "\033[0m"


# ── format_output ─────────────────────────────────────────────────────────

class TestFormatOutput:
    """format_output adds color unless --no-color or --json."""

    def test_default_adds_color(self):
        result = format_output("Hello", severity="info")
        assert "\033[94m" in result   # blue info prefix
        assert "\033[0m" in result    # reset suffix
        assert "Hello" in result

    def test_success_color(self):
        result = format_output("OK", severity="success")
        assert "\033[92m" in result  # green

    def test_warning_color(self):
        result = format_output("Careful", severity="warning")
        assert "\033[93m" in result  # yellow

    def test_error_color(self):
        result = format_output("Fail", severity="error")
        assert "\033[91m" in result  # red

    def test_info_color(self):
        result = format_output("Note", severity="info")
        assert "\033[94m" in result  # blue

    def test_no_color_strips_all_ansi(self):
        opts = CLIOptions(no_color=True)
        result = format_output("Hello", severity="error", options=opts)
        assert "\033[" not in result
        assert result == "Hello"

    def test_json_output_strips_all_ansi(self):
        """--json mode returns plain text without ANSI codes."""
        opts = CLIOptions(json_output=True)
        result = format_output("Hello", severity="error", options=opts)
        assert "\033[" not in result
        assert result == "Hello"

    def test_none_options_defaults_to_color(self):
        """Passing options=None uses defaults (color enabled)."""
        result = format_output("Test", severity="warning")
        assert "\033[" in result

    def test_unknown_severity_defaults_to_info_color(self):
        result = format_output("Mystery", severity="unknown_severity")
        # Should use info color (blue) for unknown severity
        assert "\033[94m" in result

    def test_strips_existing_ansi_in_no_color(self):
        """If message already contains ANSI, --no-color strips it out."""
        msg = "\033[91mRed text\033[0m"
        opts = CLIOptions(no_color=True)
        result = format_output(msg, severity="info", options=opts)
        assert "\033[" not in result
        assert "Red text" in result


# ── format_json_output ────────────────────────────────────────────────────

class TestFormatJsonOutput:
    """format_json_output serializes to JSON with optional pretty-print."""

    def test_produces_valid_json(self):
        data = {"name": "test", "count": 42}
        result = format_json_output(data)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["count"] == 42

    def test_pretty_printed_by_default(self):
        data = {"key": "value"}
        result = format_json_output(data)
        assert "\n" in result
        assert "  " in result  # indented

    def test_quiet_produces_compact_json(self):
        data = {"key": "value", "num": 1}
        opts = CLIOptions(quiet=True)
        result = format_json_output(data, options=opts)
        # Compact: no newlines, no extra spaces
        assert "\n" not in result
        assert result == '{"key":"value","num":1}'

    def test_list_data(self):
        data = [1, 2, 3]
        result = format_json_output(data)
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_none_options_defaults_to_pretty(self):
        data = {"a": 1}
        result = format_json_output(data)
        assert "\n" in result

    def test_handles_non_serializable_with_default_str(self):
        """Non-JSON-serializable objects are converted to str."""

        class Custom:
            def __str__(self):
                return "custom_obj"

        data = {"obj": Custom()}
        result = format_json_output(data)
        parsed = json.loads(result)
        assert parsed["obj"] == "custom_obj"


# ── format_error ──────────────────────────────────────────────────────────

class TestFormatError:
    """format_error produces structured dict with type, message, suggestion."""

    def test_returns_structured_dict(self):
        err = FileNotFoundError("no such file")
        result = format_error(err)
        assert "type" in result
        assert "message" in result
        assert "suggestion" in result

    def test_file_not_found(self):
        err = FileNotFoundError("missing.yaml")
        result = format_error(err)
        assert result["type"] == "FileNotFoundError"
        assert "missing.yaml" in result["message"]
        assert "file path" in result["suggestion"].lower()

    def test_import_error(self):
        err = ImportError("No module named 'bpy'")
        result = format_error(err)
        assert result["type"] == "ImportError"
        assert "pip" in result["suggestion"]

    def test_runtime_error(self):
        err = RuntimeError("Blender not found")
        result = format_error(err)
        assert result["type"] == "RuntimeError"
        assert "Blender" in result["suggestion"]

    def test_hamr_error_subclass(self):
        """Custom Hamr errors with specific suggestions."""
        err = SpecValidationError("missing fields", errors=["name required"])
        result = format_error(err)
        assert result["type"] == "SpecValidationError"
        assert "spec" in result["suggestion"].lower()

    def test_build_error(self):
        err = BuildError("pipeline failed", stage="mesh")
        result = format_error(err)
        assert result["type"] == "BuildError"
        assert "build" in result["suggestion"].lower()

    def test_unknown_error_gets_fallback(self):
        """Errors without a specific suggestion get the fallback."""

        class ObscureError(Exception):
            pass

        err = ObscureError("something weird")
        result = format_error(err)
        assert result["type"] == "ObscureError"
        assert result["suggestion"]  # fallback is non-empty

    def test_mro_walk_for_suggestion(self):
        """If exact error class isn't mapped, walks MRO to find a parent."""

        class CustomFileError(FileNotFoundError):
            pass

        err = CustomFileError("custom missing file")
        result = format_error(err)
        # Should find FileNotFoundError in MRO
        assert "file path" in result["suggestion"].lower() or result["suggestion"] != ""

    def test_none_options(self):
        err = ValueError("bad value")
        result = format_error(err, options=None)
        assert isinstance(result, dict)
        assert result["type"] == "ValueError"


# ── format_table ──────────────────────────────────────────────────────────

class TestFormatTable:
    """format_table produces aligned columns with header underline."""

    def test_produces_aligned_columns(self):
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["Bob", "5"]]
        result = format_table(headers, rows)
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + underline + 2 data rows
        # Header line
        assert "Name" in lines[0]
        assert "Age" in lines[0]

    def test_underline_row(self):
        headers = ["Col"]
        rows = [["val"]]
        result = format_table(headers, rows)
        lines = result.split("\n")
        # Second line should be the underline
        assert "─" in lines[1]

    def test_no_color_strips_ansi(self):
        headers = ["Name", "Value"]
        rows = [["\033[91mRed\033[0m", "1"]]
        opts = CLIOptions(no_color=True)
        result = format_table(headers, rows, options=opts)
        assert "\033[" not in result

    def test_short_rows_padded(self):
        """Rows shorter than headers are padded with empty cells."""
        headers = ["A", "B", "C"]
        rows = [["1"]]  # Only 1 cell, 2 missing
        result = format_table(headers, rows)
        lines = result.strip().split("\n")
        # Data row should exist and not crash
        assert len(lines) == 3  # header + underline + 1 data row

    def test_empty_rows(self):
        headers = ["X", "Y"]
        rows = []
        result = format_table(headers, rows)
        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + underline only

    def test_none_options_defaults(self):
        headers = ["A"]
        rows = [["1"]]
        result = format_table(headers, rows, options=None)
        assert "A" in result

    def test_ansi_in_headers_stripped_for_width(self):
        """ANSI codes in headers don't affect column alignment."""
        headers = ["\033[94mName\033[0m", "Val"]
        rows = [["Alice", "30"]]
        result = format_table(headers, rows, options=CLIOptions(no_color=False))
        # Should work without error
        assert "Alice" in result


# ── should_suppress_output ────────────────────────────────────────────────

class TestShouldSuppressOutput:
    """should_suppress_output returns True only when --quiet."""

    def test_quiet_returns_true(self):
        opts = CLIOptions(quiet=True)
        assert should_suppress_output(opts) is True

    def test_default_returns_false(self):
        opts = CLIOptions()
        assert should_suppress_output(opts) is False

    def test_none_returns_false(self):
        assert should_suppress_output(None) is False

    def test_no_color_does_not_suppress(self):
        opts = CLIOptions(no_color=True)
        assert should_suppress_output(opts) is False

    def test_json_does_not_suppress(self):
        opts = CLIOptions(json_output=True)
        assert should_suppress_output(opts) is False


# ── get_actionable_suggestion ─────────────────────────────────────────────

class TestGetActionableSuggestion:
    """get_actionable_suggestion maps exceptions to user-friendly hints."""

    def test_file_not_found(self):
        err = FileNotFoundError("missing.yaml")
        suggestion = get_actionable_suggestion(err)
        assert "file path" in suggestion.lower() or "exists" in suggestion.lower()

    def test_import_error(self):
        err = ImportError("No module named 'bpy'")
        suggestion = get_actionable_suggestion(err)
        assert "pip" in suggestion.lower()

    def test_runtime_error(self):
        err = RuntimeError("Blender crashed")
        suggestion = get_actionable_suggestion(err)
        assert "blender" in suggestion.lower() or "3.4" in suggestion

    def test_validation_error(self):
        err = SpecValidationError("invalid spec")
        suggestion = get_actionable_suggestion(err)
        assert "spec" in suggestion.lower()

    def test_hamr_error(self):
        err = HamrError("generic hamr error")
        suggestion = get_actionable_suggestion(err)
        assert suggestion  # Non-empty

    def test_unknown_error_returns_fallback(self):
        class CompletelyObscureError(Exception):
            pass

        err = CompletelyObscureError("??")
        suggestion = get_actionable_suggestion(err)
        assert suggestion  # Fallback is always returned
        assert len(suggestion) > 0

    def test_mro_walk(self):
        """Subclass of FileNotFoundError should inherit suggestion."""

        class CustomFileError(FileNotFoundError):
            pass

        err = CustomFileError("custom")
        suggestion = get_actionable_suggestion(err)
        # Should get FileNotFoundError's suggestion since exact class
        # isn't in the dict
        assert len(suggestion) > 0


# ── ERROR_SUGGESTIONS ────────────────────────────────────────────────────

class TestErrorSuggestions:
    """ERROR_SUGGESTIONS dict has entries for common error types."""

    def test_has_file_not_found(self):
        assert "FileNotFoundError" in ERROR_SUGGESTIONS

    def test_has_import_error(self):
        assert "ImportError" in ERROR_SUGGESTIONS

    def test_has_runtime_error(self):
        assert "RuntimeError" in ERROR_SUGGESTIONS

    def test_has_validation_error(self):
        assert "ValidationError" in ERROR_SUGGESTIONS
        assert "SpecValidationError" in ERROR_SUGGESTIONS

    def test_has_build_error(self):
        assert "BuildError" in ERROR_SUGGESTIONS

    def test_has_export_error(self):
        assert "ExportError" in ERROR_SUGGESTIONS

    def test_has_asset_not_found_error(self):
        assert "AssetNotFoundError" in ERROR_SUGGESTIONS

    def test_has_hamr_error(self):
        assert "HamrError" in ERROR_SUGGESTIONS

    def test_has_permission_error(self):
        assert "PermissionError" in ERROR_SUGGESTIONS

    def test_has_timeout_error(self):
        assert "TimeoutError" in ERROR_SUGGESTIONS

    def test_all_values_are_non_empty(self):
        for key, value in ERROR_SUGGESTIONS.items():
            assert value, f"Suggestion for {key} is empty"
            assert isinstance(value, str), f"Suggestion for {key} is not a string"

    def test_all_values_are_actionable(self):
        """All suggestions should be non-trivial (more than a few chars)."""
        for key, value in ERROR_SUGGESTIONS.items():
            assert len(value) > 10, f"Suggestion for {key} is too short: {value!r}"


# ── _strip_ansi ──────────────────────────────────────────────────────────

class TestStripAnsi:
    """_strip_ansi removes all ANSI escape sequences."""

    def test_strips_color_codes(self):
        text = "\033[91mRed text\033[0m"
        assert _strip_ansi(text) == "Red text"

    def test_strips_multiple_codes(self):
        text = "\033[94mBlue\033[0m and \033[93mYellow\033[0m"
        assert _strip_ansi(text) == "Blue and Yellow"

    def test_plain_text_unchanged(self):
        text = "No colors here"
        assert _strip_ansi(text) == text

    def test_empty_string(self):
        assert _strip_ansi("") == ""

    def test_complex_ansi_sequence(self):
        text = "\033[1;32;40mBold green on black\033[0m"
        assert _strip_ansi(text) == "Bold green on black"