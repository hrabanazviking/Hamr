"""
API Reference Generator — The Rune-Keeper's Ledger.

Auto-generates markdown API reference documentation by introspecting
all public hamr.* modules. Every callable, every class, every constant
— carved into clear runes for those who follow.

— Eldra Járnsdóttir, The Forge Worker
"""

from __future__ import annotations

import inspect
import importlib
import pkgutil
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class APIEntry:
    """A single public API entry from a hamr module.

    Attributes:
        module: Fully-qualified module name (e.g. 'hamr.core.constants').
        name: Public symbol name (e.g. 'SKIN_BASE_HEX').
        type: One of 'function', 'class', 'data'.
        docstring: The symbol's docstring (may be empty).
        signature: Formatted function/method signature string (empty for data).
    """
    module: str
    name: str
    type: str  # "function" | "class" | "data"
    docstring: str = ""
    signature: str = ""

    def to_markdown(self) -> str:
        """Render this entry as a markdown line item."""
        anchor = f"`{self.module}.{self.name}`"
        if self.type == "function":
            sig = self.signature or "()"
            line = f"- **{anchor}** {sig}"
        elif self.type == "class":
            sig = self.signature or ""
            line = f"- **{anchor}** (class){sig}"
        else:
            line = f"- `{self.name}` ({self.type})"

        if self.docstring:
            # First line only, truncated
            first_line = self.docstring.strip().split("\n")[0]
            if len(first_line) > 100:
                first_line = first_line[:97] + "..."
            line += f"  \n  {first_line}"

        return line


# ── Public API ────────────────────────────────────────────────────────────────

def format_signature(func: Callable) -> str:
    """Format a function or class signature as a string.

    Args:
        func: A callable (function, method, or class) to inspect.

    Returns:
        A string representation of the signature, e.g.
        '(spec: Spec, preset: str = "casual_f") -> BuildResult'.
        Returns an empty string if the signature cannot be determined.
    """
    try:
        sig = inspect.signature(func)
        return str(sig)
    except (ValueError, TypeError):
        return ""


def collect_api_entries(module_name: str) -> list[APIEntry]:
    """Walk a module and collect all public callables, classes, and data.

    Public symbols are those that do not start with underscore ('_')
    and are defined in or re-exported from the given module.

    Args:
        module_name: Fully-qualified module name (e.g. 'hamr.core.constants').

    Returns:
        A list of APIEntry objects for every public symbol found.
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return []

    entries: list[APIEntry] = []

    # Walk the module's public __all__ if available, otherwise dir()
    if hasattr(module, "__all__"):
        public_names = list(module.__all__)
    else:
        public_names = [
            name for name in dir(module)
            if not name.startswith("_")
        ]

    for name in sorted(public_names):
        obj = getattr(module, name, None)
        if obj is None:
            continue

        # Determine type
        if inspect.isclass(obj):
            entry_type = "class"
        elif inspect.isfunction(obj) or inspect.ismethod(obj) or callable(obj):
            # Distinguish dataclasses-as-classes from plain functions
            if inspect.isclass(obj):
                entry_type = "class"
            else:
                entry_type = "function"
        else:
            entry_type = "data"

        # More precise classification
        if inspect.isclass(obj):
            entry_type = "class"
        elif callable(obj) and not inspect.isclass(obj):
            entry_type = "function"
        else:
            entry_type = "data"

        # Docstring
        docstring = inspect.getdoc(obj) or ""

        # Signature (for functions and classes)
        sig = ""
        if entry_type in ("function", "class"):
            sig = format_signature(obj)

        entries.append(APIEntry(
            module=module_name,
            name=name,
            type=entry_type,
            docstring=docstring,
            signature=sig,
        ))

    return entries


def _discover_hamr_modules() -> list[str]:
    """Discover all hamr.* subpackages by walking the package tree.

    Returns:
        A sorted list of fully-qualified module names,
        e.g. ['hamr', 'hamr.cli', 'hamr.core', 'hamr.core.constants', ...].
    """
    modules: list[str] = ["hamr"]

    try:
        hamr_pkg = importlib.import_module("hamr")
    except ImportError:
        return modules

    # Walk subpackages
    if hasattr(hamr_pkg, "__path__"):
        for _importer, modname, ispkg in pkgutil.walk_packages(
            hamr_pkg.__path__, prefix="hamr."
        ):
            modules.append(modname)

    return sorted(modules)


def generate_api_reference(module_names: list[str] | None = None) -> str:
    """Generate a markdown API reference for all hamr.* modules.

    Args:
        module_names: Optional list of fully-qualified module names to document.
            If None, discovers and documents all hamr.* packages automatically.

    Returns:
        A markdown string containing the full API reference.
    """
    if module_names is None:
        module_names = _discover_hamr_modules()

    lines: list[str] = [
        "# Hamr API Reference",
        "",
        f"Auto-generated documentation for all public `hamr.*` modules.",
        f"Generated by `hamr.docs.api_reference.generate_api_reference()`.",
        "",
    ]

    for mod_name in module_names:
        entries = collect_api_entries(mod_name)
        if not entries:
            continue

        lines.append(f"## `{mod_name}`")
        lines.append("")

        # Group by type
        functions = [e for e in entries if e.type == "function"]
        classes = [e for e in entries if e.type == "class"]
        data = [e for e in entries if e.type == "data"]

        if classes:
            lines.append("### Classes")
            lines.append("")
            for entry in classes:
                lines.append(entry.to_markdown())
            lines.append("")

        if functions:
            lines.append("### Functions")
            lines.append("")
            for entry in functions:
                lines.append(entry.to_markdown())
            lines.append("")

        if data:
            lines.append("### Constants & Data")
            lines.append("")
            for entry in data:
                lines.append(entry.to_markdown())
            lines.append("")

    return "\n".join(lines)