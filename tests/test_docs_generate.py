"""
Tests for hamr.docs.generate — Documentation Inscription.

Phase 13 T5: The forge breathes documentation.
Tests that DocSection, CliCommand, generate_cli_reference,
generate_architecture_diagram, generate_preset_guide, and
generate_readme all produce correct output.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from hamr.docs.generate import (
    DocSection,
    CliCommand,
    generate_cli_reference,
    generate_architecture_diagram,
    generate_preset_guide,
    generate_readme,
    generate_all,
)


# ── DocSection Tests ──────────────────────────────────────────────────────────

class TestDocSection:
    """Tests for the DocSection dataclass."""

    def test_creation_with_defaults(self):
        """DocSection uses level=2 by default."""
        section = DocSection(title="Test", content="Hello")
        assert section.title == "Test"
        assert section.content == "Hello"
        assert section.level == 2

    def test_creation_custom_level(self):
        """DocSection can be created with a custom heading level."""
        section = DocSection(title="Sub", content="Detail", level=3)
        assert section.level == 3

    def test_render_level_2(self):
        """DocSection renders as ## heading at level 2."""
        section = DocSection(title="Heading", content="Body text", level=2)
        rendered = section.render()
        assert rendered.startswith("## Heading")
        assert "Body text" in rendered

    def test_render_level_1(self):
        """DocSection renders as # heading at level 1."""
        section = DocSection(title="Top", content="Content", level=1)
        rendered = section.render()
        assert rendered.startswith("# Top")

    def test_render_level_3(self):
        """DocSection renders as ### heading at level 3."""
        section = DocSection(title="Sub", content="Text", level=3)
        rendered = section.render()
        assert rendered.startswith("### Sub")


# ── CliCommand Tests ──────────────────────────────────────────────────────────

class TestCliCommand:
    """Tests for the CliCommand dataclass."""

    def test_creation_with_defaults(self):
        """CliCommand with only required fields has empty arg/opt/example lists."""
        cmd = CliCommand(name="build", description="Build a character")
        assert cmd.name == "build"
        assert cmd.description == "Build a character"
        assert cmd.arguments == []
        assert cmd.options == []
        assert cmd.examples == []

    def test_creation_with_all_fields(self):
        """CliCommand accepts arguments, options, and examples."""
        cmd = CliCommand(
            name="build",
            description="Build a character from spec",
            arguments=[("spec", "Path to YAML spec file")],
            options=[("--out", "Output directory")],
            examples=["hamr build my_character.yaml"],
        )
        assert len(cmd.arguments) == 1
        assert cmd.arguments[0] == ("spec", "Path to YAML spec file")
        assert len(cmd.options) == 1
        assert len(cmd.examples) == 1

    def test_render_with_arguments(self):
        """render() includes arguments section."""
        cmd = CliCommand(
            name="validate",
            description="Validate a spec",
            arguments=[("spec", "Spec file path")],
        )
        rendered = cmd.render()
        assert "### `validate`" in rendered
        assert "**Arguments:**" in rendered
        assert "`spec`" in rendered

    def test_render_with_options(self):
        """render() includes options section."""
        cmd = CliCommand(
            name="build",
            description="Build",
            options=[("--out", "Output dir"), ("--format", "Export format")],
        )
        rendered = cmd.render()
        assert "**Options:**" in rendered
        assert "`--out`" in rendered

    def test_render_with_examples(self):
        """render() includes examples in a code block."""
        cmd = CliCommand(
            name="build",
            description="Build",
            examples=["hamr build spec.yaml", "hamr build --preset anime_girl_default"],
        )
        rendered = cmd.render()
        assert "```bash" in rendered
        assert "hamr build spec.yaml" in rendered


# ── generate_cli_reference Tests ──────────────────────────────────────────────

class TestGenerateCliReference:
    """Tests for the generate_cli_reference function."""

    def test_produces_non_empty_markdown(self):
        """generate_cli_reference() returns a non-empty string."""
        result = generate_cli_reference()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_includes_command_names(self):
        """CLI reference includes known command names."""
        result = generate_cli_reference()
        # The main subcommands
        assert "build" in result
        assert "validate" in result
        assert "inspect" in result
        assert "list-presets" in result or "list_presets" in result
        assert "verify-rig" in result or "verify_rig" in result
        assert "check-env" in result or "check_env" in result

    def test_includes_title(self):
        """CLI reference has a top-level heading."""
        result = generate_cli_reference()
        assert "# Hamr CLI Reference" in result

    def test_includes_global_usage(self):
        """CLI reference includes global usage pattern."""
        result = generate_cli_reference()
        assert "hamr" in result.lower()
        assert "command" in result.lower() or "usage" in result.lower()


# ── generate_architecture_diagram Tests ────────────────────────────────────────

class TestGenerateArchitectureDiagram:
    """Tests for the generate_architecture_diagram function."""

    def test_contains_mermaid(self):
        """Architecture diagram contains mermaid code block."""
        result = generate_architecture_diagram()
        assert "```mermaid" in result

    def test_contains_graph(self):
        """Architecture diagram contains a graph declaration."""
        result = generate_architecture_diagram()
        assert "graph" in result

    def test_lists_core_modules(self):
        """Architecture diagram lists core modules."""
        result = generate_architecture_diagram()
        assert "Spec" in result
        assert "Builder" in result
        assert "Pipeline" in result

    def test_has_data_flow(self):
        """Architecture diagram includes a data flow section."""
        result = generate_architecture_diagram()
        assert "Data Flow" in result or "data flow" in result.lower()

    def test_has_module_table(self):
        """Architecture diagram includes a module reference table."""
        result = generate_architecture_diagram()
        assert "Module" in result
        assert "Purpose" in result


# ── generate_preset_guide Tests ───────────────────────────────────────────────

class TestGeneratePresetGuide:
    """Tests for the generate_preset_guide function."""

    def test_includes_all_six_preset_names(self):
        """Preset guide lists all 6 character presets."""
        result = generate_preset_guide()
        # All 6 built-in presets
        assert "anime_girl_default" in result
        assert "anime_girl_warrior" in result
        assert "anime_girl_mage" in result
        assert "anime_boy_default" in result
        assert "anime_boy_warrior" in result
        assert "chibi_cute" in result

    def test_has_custom_section(self):
        """Preset guide has a section about creating custom presets."""
        result = generate_preset_guide()
        assert "Custom" in result or "custom" in result.lower() or "Creating" in result

    def test_has_validation_rules(self):
        """Preset guide documents validation rules."""
        result = generate_preset_guide()
        assert "Validation" in result or "validation" in result.lower()

    def test_includes_preset_categories(self):
        """Preset guide shows preset categories (female, male, chibi)."""
        result = generate_preset_guide()
        assert "female" in result.lower() or "male" in result.lower() or "chibi" in result.lower()

    def test_mentions_deep_merge(self):
        """Preset guide documents the deep_merge utility."""
        result = generate_preset_guide()
        assert "deep_merge" in result

    def test_includes_resolve_preset(self):
        """Preset guide documents resolve_preset usage."""
        result = generate_preset_guide()
        assert "resolve_preset" in result


# ── generate_readme Tests ─────────────────────────────────────────────────────

class TestGenerateReadme:
    """Tests for the generate_readme function."""

    def test_contains_project_name(self):
        """README contains the project name 'Hamr'."""
        result = generate_readme()
        assert "Hamr" in result

    def test_has_installation_section(self):
        """README has an installation or quick start section."""
        result = generate_readme()
        assert "Install" in result or "install" in result.lower() or "pip install" in result

    def test_has_architecture_section(self):
        """README has an architecture section."""
        result = generate_readme()
        assert "Architecture" in result or "architecture" in result.lower()

    def test_has_license_badge(self):
        """README includes a license badge."""
        result = generate_readme()
        assert "License" in result or "license" in result.lower()

    def test_has_features_list(self):
        """README includes a features section."""
        result = generate_readme()
        assert "Feature" in result or "feature" in result.lower()

    def test_includes_version(self):
        """README includes version info."""
        from hamr import __version__
        result = generate_readme()
        assert __version__ in result

    def test_has_cli_reference(self):
        """README has a CLI reference section."""
        result = generate_readme()
        assert "CLI" in result or "cli" in result.lower()

    def test_has_preset_section(self):
        """README mentions character presets."""
        result = generate_readme()
        assert "preset" in result.lower() or "Preset" in result


# ── generate_all Integration Tests ─────────────────────────────────────────────

class TestGenerateAll:
    """Tests for the generate_all function that writes files to disk."""

    def test_writes_all_files(self, tmp_path):
        """generate_all creates 4 documentation files."""
        generate_all(output_dir=str(tmp_path / "docs"))
        out = tmp_path / "docs"
        assert (out / "cli_reference.md").exists()
        assert (out / "architecture.md").exists()
        assert (out / "preset_guide.md").exists()
        assert (out / "README.md").exists()

    def test_files_are_non_empty(self, tmp_path):
        """All generated files contain content."""
        generate_all(output_dir=str(tmp_path / "docs"))
        out = tmp_path / "docs"
        for filename in ["cli_reference.md", "architecture.md", "preset_guide.md", "README.md"]:
            content = (out / filename).read_text()
            assert len(content) > 50, f"{filename} is too short"

    def test_creates_output_directory(self, tmp_path):
        """generate_all creates the output directory if it doesn't exist."""
        out = tmp_path / "nested" / "docs"
        generate_all(output_dir=str(out))
        assert out.exists()