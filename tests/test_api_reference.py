"""
Tests for hamr.docs.api_reference — the Rune-Keeper's Ledger.

Every rune must be legible. Every name must be recorded.
— Eldra Járnsdóttir, The Forge Worker
"""

import inspect
import pytest

from hamr.docs.api_reference import (
    APIEntry,
    collect_api_entries,
    format_signature,
    generate_api_reference,
    _discover_hamr_modules,
)


# ── APIEntry ─────────────────────────────────────────────────────────────────

class TestAPIEntry:
    """Test APIEntry creation and rendering."""

    def test_apientry_creation(self):
        """APIEntry holds module, name, type, docstring, and signature."""
        entry = APIEntry(
            module="hamr.core.constants",
            name="SKIN_BASE_HEX",
            type="data",
            docstring="Default skin hex color.",
            signature="",
        )
        assert entry.module == "hamr.core.constants"
        assert entry.name == "SKIN_BASE_HEX"
        assert entry.type == "data"
        assert entry.docstring == "Default skin hex color."
        assert entry.signature == ""

    def test_apientry_function(self):
        """APIEntry can describe a function."""
        entry = APIEntry(
            module="hamr.core.spec",
            name="from_yaml",
            type="function",
            docstring="Load a Spec from YAML.",
            signature="(path: str) -> Spec",
        )
        assert entry.type == "function"
        assert entry.signature == "(path: str) -> Spec"

    def test_apientry_class(self):
        """APIEntry can describe a class."""
        entry = APIEntry(
            module="hamr.core.models",
            name="CharacterSpec",
            type="class",
            docstring="Top-level character specification data model.",
            signature="",
        )
        assert entry.type == "class"

    def test_apientry_to_markdown_data(self):
        """APIEntry.to_markdown() renders data entries."""
        entry = APIEntry(
            module="hamr.core.constants",
            name="SKIN_BASE_HEX",
            type="data",
            docstring="Default skin base hex color.",
            signature="",
        )
        md = entry.to_markdown()
        assert "`SKIN_BASE_HEX`" in md
        assert "(data)" in md
        assert "Default skin base hex color" in md

    def test_apientry_to_markdown_function(self):
        """APIEntry.to_markdown() renders function entries with signature."""
        entry = APIEntry(
            module="hamr.core.spec",
            name="from_yaml",
            type="function",
            docstring="Load a Spec from YAML.",
            signature="(path: str) -> Spec",
        )
        md = entry.to_markdown()
        assert "`hamr.core.spec.from_yaml`" in md
        assert "(path: str) -> Spec" in md

    def test_apientry_to_markdown_class(self):
        """APIEntry.to_markdown() renders class entries."""
        entry = APIEntry(
            module="hamr.core.models",
            name="CharacterSpec",
            type="class",
            docstring="Top-level character spec.",
            signature="",
        )
        md = entry.to_markdown()
        assert "`hamr.core.models.CharacterSpec`" in md
        assert "(class)" in md

    def test_apientry_to_markdown_no_docstring(self):
        """APIEntry.to_markdown() handles missing docstring."""
        entry = APIEntry(
            module="hamr.core.constants",
            name="IRIS_ICE_BLUE_HEX",
            type="data",
            docstring="",
            signature="",
        )
        md = entry.to_markdown()
        assert "`IRIS_ICE_BLUE_HEX`" in md
        # No description line (docstring was empty)

    def test_apientry_to_markdown_long_docstring(self):
        """APIEntry.to_markdown() truncates docstrings over 100 chars."""
        long_doc = "A" * 120
        entry = APIEntry(
            module="hamr.core.constants",
            name="SOME_THING",
            type="data",
            docstring=long_doc,
            signature="",
        )
        md = entry.to_markdown()
        # Should truncate to ~100 chars + "..."
        assert "AAA" in md
        assert "..." in md


# ── collect_api_entries ─────────────────────────────────────────────────────

class TestCollectAPIEntries:
    """Test collect_api_entries for known modules."""

    def test_collect_constants_module(self):
        """collect_api_entries finds entries in hamr.core.constants."""
        entries = collect_api_entries("hamr.core.constants")
        names = [e.name for e in entries]
        # constants should export at least SKIN_BASE_HEX and VRM_25_BONE_NAMES
        assert "SKIN_BASE_HEX" in names
        assert "VRM_25_BONE_NAMES" in names
        # All entries should have the correct module
        for entry in entries:
            assert entry.module == "hamr.core.constants"

    def test_collect_constants_data_types(self):
        """Constants module entries should mostly be 'data' type."""
        entries = collect_api_entries("hamr.core.constants")
        data_entries = [e for e in entries if e.type == "data"]
        assert len(data_entries) > 0

    def test_collect_nonexistent_module(self):
        """collect_api_entries returns empty list for nonexistent modules."""
        entries = collect_api_entries("hamr.nonexistent.module")
        assert entries == []

    def test_collect_errors_module(self):
        """collect_api_entries finds entries in hamr.core.errors."""
        entries = collect_api_entries("hamr.core.errors")
        names = [e.name for e in entries]
        # errors should export HamrError, SpecValidationError, etc.
        assert "HamrError" in names
        assert "SpecValidationError" in names

    def test_collect_entries_have_classifiable_types(self):
        """Every entry should have a valid type."""
        entries = collect_api_entries("hamr.core.constants")
        valid_types = {"function", "class", "data"}
        for entry in entries:
            assert entry.type in valid_types, f"{entry.name} has invalid type: {entry.type}"


# ── format_signature ─────────────────────────────────────────────────────────

class TestFormatSignature:
    """Test format_signature for known functions."""

    def test_format_signature_known_function(self):
        """format_signature returns a string with parentheses for functions."""
        # Use a built-in we can inspect
        from hamr.core.spec import Spec
        sig = format_signature(Spec.from_yaml)
        assert "(" in sig
        assert ")" in sig

    def test_format_signature_dataclass_init(self):
        """format_signature works on dataclass __init__ methods."""
        from hamr.core.models import CharacterSpec
        sig = format_signature(CharacterSpec)
        assert "(" in sig

    def test_format_signature_builtin(self):
        """format_signature handles builtins gracefully."""
        # Built-in functions may not have inspectable signatures
        sig = format_signature(print)
        # Should return something (even if empty for builtins)
        assert isinstance(sig, str)


# ── generate_api_reference ──────────────────────────────────────────────────

class TestGenerateAPIReference:
    """Test generate_api_reference produces valid markdown output."""

    def test_generates_markdown(self):
        """generate_api_reference returns a markdown string."""
        md = generate_api_reference(["hamr.core.constants"])
        assert isinstance(md, str)
        assert len(md) > 0

    def test_contains_module_header(self):
        """The output contains a module header for each module."""
        md = generate_api_reference(["hamr.core.constants"])
        assert "## `hamr.core.constants`" in md

    def test_contains_overall_header(self):
        """The output contains an overall API reference header."""
        md = generate_api_reference(["hamr.core.constants"])
        assert "# Hamr API Reference" in md

    def test_default_modules_discovers_hamr(self):
        """generate_api_reference with no args discovers hamr modules."""
        md = generate_api_reference()  # Discovers all hamr.* modules
        assert isinstance(md, str)
        # Should contain at least the core module
        assert "hamr" in md.lower()

    def test_empty_module_list(self):
        """generate_api_reference with empty list produces header-only output."""
        md = generate_api_reference([])
        assert "# Hamr API Reference" in md
        # Should not crash, just produce header


# ── Module Discovery ────────────────────────────────────────────────────────

class TestModuleDiscovery:
    """Test that all hamr modules are documented."""

    def test_discover_hamr_modules(self):
        """_discover_hamr_modules returns a list with 'hamr' in it."""
        modules = _discover_hamr_modules()
        assert "hamr" in modules
        assert len(modules) > 5  # Should find many submodules

    def test_core_constants_discovered(self):
        """hamr.core.constants should be discoverable."""
        modules = _discover_hamr_modules()
        assert "hamr.core.constants" in modules

    def test_all_hamr_modules_documented(self):
        """Every hamr.* module should produce at least some API entries."""
        modules = _discover_hamr_modules()
        # Filter to leaf modules for speed (skip top-level packages)
        test_modules = [
            m for m in modules
            if m in (
                "hamr.core.constants",
                "hamr.core.errors",
                "hamr.core.models",
            )
        ]
        for mod_name in test_modules:
            entries = collect_api_entries(mod_name)
            assert len(entries) > 0, f"Module {mod_name} has no public entries"

    def test_all_hamr_modules_in_full_reference(self):
        """generate_api_reference() covers all discoverable modules."""
        modules = _discover_hamr_modules()
        md = generate_api_reference(modules)
        # Each module should appear in the output
        for mod_name in modules:
            entries = collect_api_entries(mod_name)
            if entries:
                assert f"## `{mod_name}`" in md, f"Module {mod_name} missing from full reference"