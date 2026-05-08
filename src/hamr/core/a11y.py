"""
Hamr Accessibility & CLI Hardening — Phase 13 T6.

Pure-Python output formatting with color, JSON, quiet mode,
and actionable error suggestions. No bpy dependency.

The forge speaks clearly, or not at all.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ── CLIOptions ────────────────────────────────────────────────────────────

@dataclass
class CLIOptions:
    """Consolidated CLI output preferences.

    Passed through all command handlers so every print()
    can respect the user's output wishes.
    """

    no_color: bool = False
    quiet: bool = False
    json_output: bool = False
    verbose: bool = False


# ── ANSI Color Map ────────────────────────────────────────────────────────

CLI_COLOR_MAP: dict[str, str] = {
    "success": "\033[92m",   # green
    "warning": "\033[93m",   # yellow
    "error":   "\033[91m",   # red
    "info":    "\033[94m",   # blue
    "reset":   "\033[0m",
}


# ── Error Suggestions ─────────────────────────────────────────────────────

ERROR_SUGGESTIONS: dict[str, str] = {
    "FileNotFoundError":     "Check that the file path is correct and the file exists",
    "ImportError":           "Install the missing dependency with pip",
    "ModuleNotFoundError":   "Install the missing module with pip install",
    "RuntimeError":          "Ensure Blender 3.4+ is installed and accessible",
    "ValidationError":        "Check your spec file for required fields",
    "SpecValidationError":   "Check your spec file for required fields",
    "BuildError":            "Review the build error details and check your spec",
    "ExportError":           "Verify export settings and output path permissions",
    "AssetNotFoundError":    "Check that referenced assets exist at the specified paths",
    "HamrError":             "Review the error message for Hamr-specific details",
    "PermissionError":       "Check file and directory permissions",
    "TimeoutError":          "Increase timeout with --timeout or reduce complexity",
    "KeyError":              "Check that all required keys are present in your spec",
    "ValueError":            "Verify that all values in your spec are within valid ranges",
    "TypeError":             "Check that spec field types match expected formats",
    "OSError":               "Check system resources, disk space, and file access",
}

# Fallback suggestion when no specific match is found
_FALLBACK_SUGGESTION = "Check the error details and consult the documentation"


# ── Pure-Python Formatting Functions ───────────────────────────────────────

def format_output(
    message: str,
    severity: str = "info",
    options: CLIOptions | None = None,
) -> str:
    """Format a message with ANSI color codes based on severity.

    Strips all color codes if ``--no-color`` or ``--json`` is set.
    Returns the plain message when color is disabled.

    Args:
        message:  The text to format.
        severity: One of "success", "warning", "error", "info".
        options:  CLI options; ``None`` defaults to color-enabled.

    Returns:
        Formatted string (with or without ANSI escapes).
    """
    opts = options or CLIOptions()

    # JSON mode: return plain message (no decoration)
    if opts.json_output or opts.no_color:
        return _strip_ansi(message)

    color = CLI_COLOR_MAP.get(severity, CLI_COLOR_MAP["info"])
    reset = CLI_COLOR_MAP["reset"]
    return f"{color}{message}{reset}"


def format_json_output(
    data: dict | list,
    options: CLIOptions | None = None,
) -> str:
    """Serialize data to a JSON string.

    Uses pretty-printed (indented) JSON unless ``--quiet`` is set,
    in which case compact single-line JSON is produced.

    Args:
        data:    Dict or list to serialize.
        options: CLI options; ``None`` defaults to pretty-print.

    Returns:
        JSON string.
    """
    opts = options or CLIOptions()

    if opts.quiet:
        return json.dumps(data, separators=(",", ":"))
    return json.dumps(data, indent=2, default=str)


def format_error(
    error: Exception,
    options: CLIOptions | None = None,
) -> dict:
    """Produce a structured error dict with type, message, and suggestion.

    Args:
        error:   The exception to format.
        options: CLI options (reserved for future use).

    Returns:
        Dict with keys ``type``, ``message``, ``suggestion``.
    """
    error_type = type(error).__name__
    message = str(error)

    suggestion = ERROR_SUGGESTIONS.get(error_type, _FALLBACK_SUGGESTION)

    # Walk the MRO for a more specific match if the exact class
    # name isn't in the suggestions dict.
    if error_type not in ERROR_SUGGESTIONS:
        for parent in type(error).__mro__:
            if parent.__name__ in ERROR_SUGGESTIONS:
                suggestion = ERROR_SUGGESTIONS[parent.__name__]
                break

    return {
        "type": error_type,
        "message": message,
        "suggestion": suggestion,
    }


def format_table(
    headers: list[str],
    rows: list[list[str]],
    options: CLIOptions | None = None,
) -> str:
    """Produce a simple aligned text table.

    Columns are padded to the width of the longest cell in that column.
    Header row is underlined with dashes.

    Args:
        headers: Column header labels.
        rows:    List of rows, each row a list of cell strings.
        options: CLI options; ``--no-color`` strips ANSI from cells.

    Returns:
        Multi-line string with aligned columns.
    """
    opts = options or CLIOptions()

    # Strip ANSI from all cells for width calculation
    clean_headers = [_strip_ansi(h) for h in headers]
    clean_rows = [[_strip_ansi(c) for c in row] for row in rows]

    # Calculate column widths
    ncols = len(headers)
    col_widths = [
        max(
            len(clean_headers[i]),
            max((len(row[i]) if i < len(row) else 0 for row in clean_rows), default=0),
        )
        for i in range(ncols)
    ]

    # Build format string
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)

    # Build output lines
    lines: list[str] = []

    # Header row
    header_line = fmt.format(*headers)
    lines.append(header_line)

    # Underline row
    underline = fmt.format(*["─" * w for w in col_widths])
    lines.append(underline)

    # Data rows
    for row in rows:
        # Pad row if shorter than headers
        padded_row = list(row) + [""] * max(0, ncols - len(row))
        line = fmt.format(*padded_row[:ncols])
        lines.append(line)

    output = "\n".join(lines)

    if opts.no_color:
        return _strip_ansi(output)

    return output


def should_suppress_output(options: CLIOptions | None = None) -> bool:
    """Return ``True`` if ``--quiet`` is set, meaning most output should be silenced.

    Args:
        options: CLI options; ``None`` defaults to not suppressing.

    Returns:
        Whether to suppress non-essential output.
    """
    opts = options or CLIOptions()
    return opts.quiet


def get_actionable_suggestion(error: Exception) -> str:
    """Map an exception to a user-friendly, actionable suggestion.

    Walks the exception's MRO to find the most specific match
    in :data:`ERROR_SUGGESTIONS`.

    Args:
        error: The exception to look up.

    Returns:
        Human-readable suggestion string.
    """
    error_type = type(error).__name__

    # Direct match
    if error_type in ERROR_SUGGESTIONS:
        return ERROR_SUGGESTIONS[error_type]

    # Walk MRO for parent class match
    for parent in type(error).__mro__:
        if parent.__name__ in ERROR_SUGGESTIONS:
            return ERROR_SUGGESTIONS[parent.__name__]

    return _FALLBACK_SUGGESTION


# ── Helpers ───────────────────────────────────────────────────────────────

# ANSI escape sequence pattern (matches CSI sequences)
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from *text*."""
    return _ANSI_RE.sub("", text)