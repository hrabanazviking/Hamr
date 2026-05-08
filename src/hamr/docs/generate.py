"""
Hamr Documentation Generation — The Runes Inscribed.

Auto-generates structured Markdown documentation from live code:

  - CLI reference from argparse
  - Architecture diagram (Mermaid)
  - Preset creation guide from CHARACTER_PRESETS data
  - Complete README.md

Phase 13 T5: The forge breathes documentation.
"""

from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class DocSection:
    """A named section of documentation with a heading level."""
    title: str
    content: str
    level: int = 2  # markdown heading level (## = 2, ### = 3, etc.)

    def render(self) -> str:
        """Render this section as a Markdown heading + content."""
        prefix = "#" * self.level
        return f"{prefix} {self.title}\n\n{self.content}\n"


@dataclass
class CliCommand:
    """A CLI command with its arguments, options, and examples."""
    name: str
    description: str
    arguments: list[tuple[str, str]] = field(default_factory=list)   # (name, description)
    options: list[tuple[str, str]] = field(default_factory=list)     # (flag, description)
    examples: list[str] = field(default_factory=list)

    def render(self) -> str:
        """Render this command as a Markdown section."""
        lines = [f"### `{self.name}`", ""]
        lines.append(f"{self.description}")
        lines.append("")

        if self.arguments:
            lines.append("**Arguments:**")
            lines.append("")
            for arg_name, arg_desc in self.arguments:
                lines.append(f"- `{arg_name}` — {arg_desc}")
            lines.append("")

        if self.options:
            lines.append("**Options:**")
            lines.append("")
            for flag, desc in self.options:
                lines.append(f"- `{flag}` — {desc}")
            lines.append("")

        if self.examples:
            lines.append("**Examples:**")
            lines.append("")
            lines.append("```bash")
            for ex in self.examples:
                lines.append(ex)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)


# ── CLI Reference Generator ──────────────────────────────────────────────────

def generate_cli_reference() -> str:
    """Generate Markdown CLI reference from the hamr argparse configuration.

    Reads the CLI parser programmatically, extracting all subcommands,
    their arguments and options, and renders them as structured Markdown.

    Returns:
        A complete Markdown string representing the CLI reference.
    """
    from hamr.cli import main as cli_main

    # We need to build the parser ourselves to inspect it
    # (main() calls parse_args which exits)
    parser = _build_parser()

    sections: list[str] = [
        "# Hamr CLI Reference",
        "",
        "> Auto-generated from `hamr.cli` argparse definitions.",
        "",
    ]

    # Top-level usage
    sections.append("## Global Usage")
    sections.append("")
    sections.append("```bash")
    sections.append("hamr <command> [options]")
    sections.append("```")
    sections.append("")

    # Document each subcommand
    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break

    if subparsers_action is not None:
        sections.append("## Commands")
        sections.append("")
        for cmd_name, cmd_parser in sorted(subparsers_action.choices.items()):
            cmd = _extract_command(cmd_name, cmd_parser)
            sections.append(cmd.render())

    # Global options
    global_options = _extract_global_options(parser)
    if global_options:
        sections.append("## Global Options")
        sections.append("")
        for flag, desc in global_options:
            sections.append(f"- `{flag}` — {desc}")
        sections.append("")

    return "\n".join(sections)


def _build_parser() -> argparse.ArgumentParser:
    """Reconstruct the hamr CLI parser for inspection.

    We replicate the parser construction from cli.py to avoid
    calling main() which would trigger sys.exit on --help.
    """
    from hamr.core.presets import CHARACTER_PRESETS

    parser = argparse.ArgumentParser(
        prog="hamr",
        description="ᚺᚨᛗᚱ — The Shape-Skin Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # build
    build_p = subparsers.add_parser("build", help="Build a character from spec or preset")
    build_p.add_argument("spec", nargs="?", default=None,
                         help="Path to YAML spec file (optional if --preset is used)")
    build_p.add_argument("--out", "-o", default="output/", help="Output directory")
    build_p.add_argument("--format", "-f", default="vrm1", choices=["vrm1", "glb", "blend"])
    build_p.add_argument("--base", "-b", default=None, help="Base mesh path (.vrm, .fbx, .glb)")
    build_p.add_argument("--no-validate", action="store_true", help="Skip validation")
    build_p.add_argument("--preset", "-p", default=None,
                        choices=list(CHARACTER_PRESETS.keys()),
                        help="Apply a character preset before building")
    build_p.add_argument("--budget", "-B", default="balanced",
                        choices=["minimal", "balanced", "high"],
                        help="Performance budget tier (default: balanced)")
    build_p.add_argument("--force-over-budget", action="store_true",
                        help="Force build even if spec exceeds performance budget")
    build_p.add_argument("--dry-run", action="store_true",
                        help="Resolve spec and forges without launching Blender")
    build_p.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output with forge details")
    build_p.add_argument("--keep-temp", action="store_true", help="Keep temp files (debug)")
    build_p.add_argument("--max-tex", type=int, default=0,
                        help="Max texture resolution (0=unlimited)")
    build_p.add_argument("--timeout", type=int, default=600,
                        help="Blender timeout in seconds")
    build_p.add_argument("--blender-path", default=None,
                        help="Path to Blender executable")

    # validate
    val_p = subparsers.add_parser("validate", help="Validate spec without building")
    val_p.add_argument("spec", help="Path to YAML spec file")

    # inspect
    insp_p = subparsers.add_parser("inspect", help="Inspect VRM/GLB compliance")
    insp_p.add_argument("path", help="Path to VRM/GLB file")
    insp_p.add_argument("--targets", "-t", nargs="+", default=["VRCHAT"])

    # list-presets
    lp_p = subparsers.add_parser("list-presets", help="List available presets")
    lp_p.add_argument("--what", "-w", choices=["all", "character", "body"],
                      default="all",
                      help="Which presets to list: all, character, or body (default: all)")

    # verify-rig
    vr_p = subparsers.add_parser("verify-rig",
                                 help="Verify VRM rig completeness and bone hierarchy")
    vr_p.add_argument("path", help="Path to VRM file to verify")
    vr_p.add_argument("--strict", action="store_true",
                      help="Treat naming issues as errors")

    # check-env
    subparsers.add_parser("check-env", help="Check build environment")

    # version
    subparsers.add_parser("version", help="Print version")

    # docs generate
    docs_p = subparsers.add_parser("docs", help="Generate documentation")
    docs_sub = docs_p.add_subparsers(dest="docs_command", help="Documentation commands")
    gen_p = docs_sub.add_parser("generate", help="Generate all documentation files")
    gen_p.add_argument("--output", "-o", default="docs",
                       help="Output directory for generated docs")
    audit_p = docs_sub.add_parser("audit", help="Run accessibility and compliance audit")

    return parser


def _extract_command(name: str, parser: argparse.ArgumentParser) -> CliCommand:
    """Extract a CliCommand from an argparse subparser."""
    arguments: list[tuple[str, str]] = []
    options: list[tuple[str, str]] = []
    examples: list[str] = []

    for action in parser._actions:
        if action is parser._actions[0] and isinstance(action, argparse._HelpAction):
            continue
        # Skip dest==None or subparsers
        if isinstance(action, argparse._SubParsersAction):
            continue

        flags = [f for f in action.option_strings if f]
        desc = action.help or ""

        if flags:
            flag_str = ", ".join(flags)
            if action.choices:
                desc += f" (choices: {', '.join(str(c) for c in action.choices)})"
            if action.default is not None and action.default != argparse.SUPPRESS:
                if not isinstance(action.default, (bool,)):
                    desc += f" (default: {action.default})"
            options.append((flag_str, desc))
        else:
            # Positional argument
            arg_name = action.dest
            arguments.append((arg_name, desc))

    # Add examples based on command
    example_map: dict[str, list[str]] = {
        "build": [
            "hamr build my_character.yaml",
            "hamr build --preset anime_girl_default",
            "hamr build --preset anime_girl_warrior --budget minimal",
            "hamr build --spec spec.yaml --budget high --force-over-budget",
            "hamr build --dry-run --preset chibi_cute",
        ],
        "validate": [
            "hamr validate my_character.yaml",
        ],
        "inspect": [
            "hamr inspect output/avatar.vrm --targets VRCHAT",
        ],
        "list-presets": [
            "hamr list-presets",
            "hamr list-presets --what character",
        ],
        "verify-rig": [
            "hamr verify-rig avatar.vrm",
            "hamr verify-rig avatar.vrm --strict",
        ],
        "check-env": [
            "hamr check-env",
        ],
        "version": [
            "hamr version",
        ],
        "docs": [
            "hamr docs generate",
            "hamr docs generate --output docs/",
            "hamr docs audit",
        ],
    }
    examples = example_map.get(name, [])

    return CliCommand(
        name=name,
        description=parser.description or "",
        arguments=arguments,
        options=options,
        examples=examples,
    )


def _extract_global_options(parser: argparse.ArgumentParser) -> list[tuple[str, str]]:
    """Extract top-level options (not subcommand options)."""
    options: list[tuple[str, str]] = []
    for action in parser._actions:
        if isinstance(action, (argparse._SubParsersAction, argparse._HelpAction)):
            continue
        flags = [f for f in action.option_strings if f]
        if flags:
            flag_str = ", ".join(flags)
            desc = action.help or ""
            options.append((flag_str, desc))
    return options


# ── Architecture Diagram Generator ────────────────────────────────────────────

def generate_architecture_diagram() -> str:
    """Generate a Mermaid architecture diagram of the Hamr module structure.

    Shows module dependencies, data flow from spec → pipeline → build → export,
    and core module relationships.

    Returns:
        A Markdown string containing a Mermaid diagram code block.
    """
    lines = [
        "# Hamr Architecture",
        "",
        "> Auto-generated module structure and data flow diagram.",
        "",
        "## Module Structure",
        "",
        "```mermaid",
        "graph TD",
        '    Spec["Spec<br/>YAML → Python dataclasses"]',
        '    Builder["Builder<br/>Validate + orchestrate"]',
        '    Pipeline["Pipeline<br/>Full BuildPipeline"]',
        "    ",
        '    BodyForge["Body Forge<br/>Proportions + presets"]',
        '    TextureForge["Texture Forge<br/>HSV procedural textures"]',
        '    RigForge["Rig Forge<br/>Bone mapping + spring bones"]',
        '    HairForge["Hair Forge<br/>Procedural styles + shells"]',
        '    FaceForge["Face Forge<br/>Shape keys + sliders"]',
        '    ClothingForge["Clothing Forge<br/>Outfit layers + materials"]',
        "    ",
        '    ExportForge["Export Forge<br/>VRM 1.0 + GLB"]',
        '    BlenderBridge["Blender Bridge<br/>Headless subprocess"]',
        "    ",
        '    Presets["Presets<br/>6 character templates"]',
        '    Perf["Perf Gate<br/>Budget tiers + GPU profiles"]',
        '    Constants["Constants<br/>Colors + bones + skin maps"]',
        "    ",
        "    Spec --> Builder",
        "    Presets --> Spec",
        "    Builder --> Pipeline",
        "    Perf --> Pipeline",
        "    Pipeline --> BodyForge",
        "    Pipeline --> TextureForge",
        "    Pipeline --> RigForge",
        "    Pipeline --> HairForge",
        "    Pipeline --> FaceForge",
        "    Pipeline --> ClothingForge",
        "    BodyForge --> Builder",
        "    TextureForge --> Builder",
        "    RigForge --> Builder",
        "    HairForge --> Builder",
        "    FaceForge --> Builder",
        "    ClothingForge --> Builder",
        "    Builder --> BlenderBridge",
        "    BlenderBridge --> ExportForge",
        "    Constants --> BodyForge",
        "    Constants --> TextureForge",
        "    Constants --> RigForge",
        "```",
        "",
        "## Data Flow",
        "",
        "```mermaid",
        "graph LR",
        '    YAML["YAML Spec"] --> Parse["Parse Spec"]',
        '    Preset["Character Preset"] --> Parse',
        '    Parse --> Validate["Validate"]',
        '    Validate --> Budget["Budget Check"]',
        '    Budget -->|within budget| Build["Build Pipeline"]',
        '    Budget -->|over budget| Reject["Reject + Report"]',
        '    Build --> Blender["Blender Headless"]',
        '    Blender --> VRM["VRM 1.0 Export"]',
        '    Blender --> GLB["GLB Export"]',
        '    Blender --> BLEND["Blend Export"]',
        "```",
        "",
        "## Core Modules",
        "",
        "| Module | Purpose |",
        "|--------|---------|",
        "| `core/spec` | YAML spec parsing, validation, serialization |",
        "| `core/models` | CharacterSpec, BodySpec, FaceSpec, HairSpec dataclasses |",
        "| `core/builder` | Pipeline orchestrator (validate → build → export) |",
        "| `core/pipeline` | Full `BuildPipeline` with error handling |",
        "| `core/textures` | HSV-driven procedural texture generation |",
        "| `core/texture_procedural` | Skin detail, fabric normal, eye iris generators |",
        "| `core/presets` | Character presets (6 built-in) + validation |",
        "| `core/perf` | Memory/performance budget tiers |",
        "| `core/perf_gate` | Build budget enforcement |",
        "| `core/gpu_profiles` | GPU profile detection (Pi 5 / Desktop / Cloud) |",
        "| `core/constants` | Body presets, skin palettes, bone names |",
        "| `rigs/verify` | VRM bone hierarchy verification |",
        "| `export/vrm` | VRM 1.0 export with bone maps and expressions |",
        "| `export/vrm_validator` | glTF + VRM compliance checking |",
        "| `export/animation_clips` | Idle + walk cycle clip definitions |",
        "| `export/glb` | GLB export option |",
        "| `export/first_person` | First-person offset annotations |",
        "| `blender_bridge/runner` | Headless Blender subprocess manager |",
        "| `blender_bridge/scene` | Scene setup and object management |",
        "| `hair` | Procedural hair styles, color gradients, physics |",
        "| `face` | Shape keys, expression mapping, sliders |",
        "| `clothing` | Outfit layers, materials, tinting |",
        "| `docs/generate` | Auto-generated documentation |",
        "| `cli` | Command-line interface |",
        "",
    ]
    return "\n".join(lines)


# ── Preset Guide Generator ────────────────────────────────────────────────────

def generate_preset_guide() -> str:
    """Generate a Markdown preset creation guide from CHARACTER_PRESETS data.

    Lists all 6 character presets with their specs, shows how to create
    a custom preset, how to modify preset values, and documents
    preset validation rules.

    Returns:
        A Markdown string with the complete preset guide.
    """
    from hamr.core.presets import (
        CHARACTER_PRESETS,
        PRESET_CATEGORIES,
        validate_preset,
        deep_merge,
    )

    lines = [
        "# Hamr Character Presets",
        "",
        "> Six ready-made character specs covering common anime archetypes.",
        "> Override any parameter or build your own from scratch.",
        "",
    ]

    # ── Built-in Presets ──────────────────────────────────────────
    lines.append("## Built-in Presets")
    lines.append("")

    for name, data in CHARACTER_PRESETS.items():
        spec = data["spec"]
        lines.append(f"### {data['display_name']}")
        lines.append(f"**Internal name:** `{name}`")
        lines.append("")
        lines.append(f"{data['description']}")
        lines.append("")

        # Body
        body = spec.get("body", {})
        lines.append("**Body:**")
        lines.append(f"- Height: {body.get('height_cm', '?')} cm")
        lines.append(f"- Build: {body.get('build', '?')}")
        skin = body.get("skin", {})
        lines.append(f"- Skin: {skin.get('base_hex', '?')} ({skin.get('undertone', '?')} undertone)")
        lines.append("")

        # Face
        face = spec.get("face", {})
        eyes = face.get("eyes", {})
        lines.append("**Face:**")
        lines.append(f"- Jaw: {face.get('jaw', '?')}, Cheekbones: {face.get('cheekbones', '?')}")
        lines.append(f"- Eyes: {eyes.get('iris_hex', '?')} ({eyes.get('shape', '?')}, size {eyes.get('size', '?')})")
        lines.append(f"- Lip fullness: {face.get('lip_fullness', '?')}")
        lines.append("")

        # Hair
        hair = spec.get("hair", {})
        color = hair.get("color", {})
        lines.append("**Hair:**")
        lines.append(f"- Style: {hair.get('style', '?')}, Length: {hair.get('length', '?')}")
        lines.append(f"- Volume: {hair.get('volume', '?')}, Curl: {hair.get('curl_tightness', '?')}")
        lines.append(f"- Colors: {color.get('roots', '?')} → {color.get('mid', '?')} → {color.get('tips', '?')}")
        lines.append("")

    # ── Categories ──────────────────────────────────────────────────
    lines.append("## Preset Categories")
    lines.append("")
    for category, preset_names in PRESET_CATEGORIES.items():
        lines.append(f"- **{category}**: {', '.join(f'`{n}`' for n in preset_names)}")
    lines.append("")

    # ── Creating a Custom Preset ────────────────────────────────────
    lines.append("## Creating a Custom Preset")
    lines.append("")
    lines.append("You can create custom presets by writing a spec dict and using `deep_merge` "
                  "to layer overrides on top of a built-in preset, or by constructing a "
                  "full spec from scratch.")
    lines.append("")
    lines.append("### Method 1: Override a built-in preset")
    lines.append("")
    lines.append("```python")
    lines.append("from hamr.core.presets import resolve_preset")
    lines.append("")
    lines.append("# Start from a built-in preset, override only what you need")
    lines.append("spec = resolve_preset(")
    lines.append("    'anime_girl_default',")
    lines.append("    overrides={")
    lines.append("        'body': {'height_cm': 170.0, 'build': 'athletic'},")
    lines.append("        'hair': {'style': 'ponytail', 'volume': 0.9},")
    lines.append("    },")
    lines.append(")")
    lines.append("```")
    lines.append("")
    lines.append("### Method 2: Build a spec from scratch")
    lines.append("")
    lines.append("```python")
    lines.append("from hamr.core.models import CharacterSpec, BodySpec, FaceSpec, HairSpec")
    lines.append("")
    lines.append("spec = CharacterSpec(")
    lines.append("    name='My Character',")
    lines.append("    body=BodySpec(height_cm=172.0, build='athletic-slender'),")
    lines.append("    face=FaceSpec(jaw='V-shape', cheekbones='high'),")
    lines.append("    hair=HairSpec(style='wavy', length='long', volume=0.7),")
    lines.append(")")
    lines.append("```")
    lines.append("")

    # ── Modifying Preset Values ──────────────────────────────────────
    lines.append("## Modifying Preset Values")
    lines.append("")
    lines.append("Use `deep_merge` to selectively override nested values "
                  "without replacing the entire struct:")
    lines.append("")
    lines.append("```python")
    lines.append("from hamr.core.presets import deep_merge, get_preset")
    lines.append("")
    lines.append("# Get the base preset")
    lines.append("base = get_preset('anime_girl_default').spec")
    lines.append("")
    lines.append("# Override specific nested values")
    lines.append("modified = deep_merge(base, {")
    lines.append("    'body': {'height_cm': 175.0},")
    lines.append("    'face': {'eyes': {'iris_hex': '#FF69B4'}},")
    lines.append("})")
    lines.append("```")
    lines.append("")

    # ── Validation Rules ────────────────────────────────────────────
    lines.append("## Validation Rules")
    lines.append("")
    lines.append("When you call `validate_preset(spec)`, the following checks are performed:")
    lines.append("")
    lines.append("### Required Keys")
    lines.append("- `body`, `face`, `hair` must be present")
    lines.append("")
    lines.append("### Numeric Ranges")
    lines.append("- `body.height_cm`: 100.0 – 220.0")
    lines.append("- `hair.volume`: 0.0 – 1.0")
    lines.append("- `hair.curl_tightness`: 0.0 – 1.0")
    lines.append("- `face.lip_fullness`: 0.0 – 1.0")
    lines.append("- `body.skin.tan_level`: 0.0 – 1.0")
    lines.append("- `face.eyes.size`: 0.5 – 2.0")
    lines.append("- `hair.shell_layers`: 1 – 12")
    lines.append("- `body.proportions.*`: 0.0 – 1.0")
    lines.append("")
    lines.append("### String Enums")
    lines.append("- `body.build`: athletic-slender, athletic, slender, curvy, average, tall, petite, muscular")
    lines.append("- `face.jaw`: V-shape, round, square, heart")
    lines.append("- `face.cheekbones`: high, low, medium")
    lines.append("- `face.eyes.shape`: cat-tilt, round, narrow, droopy")
    lines.append("- `face.nose_size`: small, medium, large")
    lines.append("- `face.nose_bridge`: narrow, wide, medium")
    lines.append("- `hair.style`: wild-curly, straight, wavy, braided, bun, ponytail")
    lines.append("- `hair.length`: short, medium, shoulder, shoulder-plus, long, very-long")
    lines.append("")
    lines.append("### Hex Colors")
    lines.append("- All `*_hex` fields must match `#[0-9a-fA-F]{6}`")
    lines.append("")
    lines.append("```python")
    lines.append("from hamr.core.presets import validate_preset")
    lines.append("")
    lines.append("# Validate a spec (returns list of warnings)")
    lines.append("warnings = validate_preset(spec)")
    lines.append("if warnings:")
    lines.append("    for w in warnings:")
    lines.append("        print(f'⚠ {w}')")
    lines.append("else:")
    lines.append("    print('✓ Spec is valid')")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


# ── README Generator ──────────────────────────────────────────────────────────

def generate_readme() -> str:
    """Generate a complete README.md for the Hamr project.

    Includes project overview with Norse-themed description, installation
    instructions, quick start guide, CLI reference, architecture overview,
    preset guide, and development setup.

    Returns:
        A complete README.md Markdown string.
    """
    from hamr import __version__, __author__

    lines = [
        "<div align=\"center\">",
        "",
        "# ᚺᚨᛗᚱ Hamr",
        "",
        "### *The Shape-Skin Engine*",
        "",
        "**Open-source parametric 3D anime character forge**",
        "",
        "Linux-native · Headless-first · Agent-orchestrated · VRM 1.0",
        "",
        f"[![Version](https://img.shields.io/badge/version-{__version__}-blue)]()",
        "[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()",
        "[![Blender](https://img.shields.io/badge/blender-3.4%2B-orange)]()",
        "[![License: MIT](https://img.shields.io/badge/license-MIT-green)]()",
        "",
        "</div>",
        "",
        "---",
        "",
        f"**Hamr** (Old Norse: *hamr* — the shape-skin, the second body) is the open-source",
        "alternative to VRoid Studio. It creates parametric 3D anime characters headlessly,",
        "driven by YAML specs and agent commands, and exports VRM 1.0 avatars ready for",
        "VRChat, Resonite, and any VRM-compatible platform.",
        "",
        "No GUI. No Windows dependency. No closed-source lock-in.",
        "",
        "*Every vertex, every slider, every algorithm is yours.*",
        "",
        "---",
        "",
        "## ✨ Features",
        "",
        "- **YAML-First Spec** — Define characters in simple YAML files, not GUI clicks",
        "- **6 Character Presets** — Default schoolgirl, warrior, mage (×2 genders) + chibi",
        "- **8 Body Presets** — Athletic-slender, curvy, petite, tall, muscular, and more",
        "- **Parametric Face** — Eyes, nose, mouth, cheeks, ears, chin — all slider-driven",
        "- **Procedural Textures** — Skin detail, fabric normals, iris patterns — no image assets",
        "- **Hair Shell System** — Multi-layer gradient shells with physics",
        "- **VRM 1.0 Export** — Spring bones, expressions, look-at, first-person annotations",
        "- **Animation Clips** — Idle sway and walk cycle presets baked into VRM",
        "- **GPU Profiles** — Pi 5 / Desktop / Cloud adaptive performance",
        "- **Blender Headless** — Runs entirely in `blender --background`, no GUI required",
        "- **Agent-Orchestrated** — Designed for AI-driven creation pipelines",
        "",
        "---",
        "",
        "## 🗡️ Quick Start",
        "",
        "```bash",
        "# Install",
        "pip install hamr",
        "",
        "# Build from a spec",
        "hamr build my_character.yaml --out output/",
        "",
        "# Build from a preset",
        "hamr build --preset anime_girl_default",
        "",
        "# Validate a spec",
        "hamr validate my_character.yaml",
        "",
        "# Inspect a VRM",
        "hamr inspect output/avatar.vrm --targets VRCHAT",
        "",
        "# List presets",
        "hamr list-presets",
        "",
        "# Check environment",
        "hamr check-env",
        "",
        "# Generate docs",
        "hamr docs generate",
        "```",
        "",
        "---",
        "",
    ]

    # Architecture section
    lines.extend(generate_readme_architecture())

    # CLI Reference
    lines.extend(generate_readme_cli_reference())

    # Preset section
    lines.extend(generate_readme_presets())

    # Development section
    lines.extend(generate_readme_dev())

    # License
    lines.extend([
        "---",
        "",
        "## 📜 License",
        "",
        "MIT License — see [LICENSE](LICENSE) for details.",
        "",
        "*Every vertex, every slider, every algorithm is yours.*",
        "",
        "ᚺᚨᛗᚱ — *hamr* — the shape you wear",
        "",
    ])

    return "\n".join(lines)


def generate_readme_architecture() -> list[str]:
    """Generate the architecture section for README."""
    return [
        "## 🏗️ Architecture",
        "",
        "Hamr is organized as **six forges** around a central spec:",
        "",
        "```",
        "┌─────────────┐",
        "│  YAML Spec  │ ← Your character definition",
        "└──────┬──────┘",
        "       │",
        "┌──────▼──────┐",
        "│   Builder   │ ← Validates, orchestrates, wires",
        "└──────┬──────┘",
        "       │",
        "  ┌────┼────┬────────┬─────────┐",
        "  │    │    │        │         │",
        "┌─▼─┐ ┌─▼─┐ ┌▼──┐ ┌──▼───┐ ┌─▼──┐",
        "│Bd │ │Tx │ │Rg│ │Text  │ │Exp │",
        "│Fo │ │Fo │ │Fo│ │Forge │ │Fort│",
        "│rg │ │rg │ │rge│      │ │ge  │",
        "└──┘ └──┘ └───┘ └──────┘ └────┘",
        "       │",
        "  ┌────▼────┐",
        "  │ Blender  │ ← Headless subprocess",
        "  │  Bridge  │",
        "  └────┬─────┘",
        "       │",
        "  ┌────▼────┐",
        "  │ VRM 1.0 │ ← Your avatar file",
        "  └─────────┘",
        "```",
        "",
    ]


def generate_readme_cli_reference() -> list[str]:
    """Generate the CLI reference section for README."""
    from hamr.core.presets import CHARACTER_PRESETS

    preset_names = ", ".join(sorted(CHARACTER_PRESETS.keys()))

    return [
        "## 📋 CLI Reference",
        "",
        "### `hamr build`",
        "",
        "Build a character from a spec file or preset.",
        "",
        "```bash",
        "hamr build [spec.yaml] [options]",
        "```",
        "",
        f"**Presets:** {preset_names}",
        "",
        "| Option | Description |",
        "|--------|-------------|",
        "| `--out`, `-o` | Output directory (default: `output/`) |",
        "| `--format`, `-f` | Export format: vrm1, glb, blend (default: vrm1) |",
        "| `--preset`, `-p` | Character preset name |",
        "| `--budget`, `-B` | Performance tier: minimal, balanced, high |",
        "| `--force-over-budget` | Build even if budget exceeded |",
        "| `--dry-run` | Resolve spec without launching Blender |",
        "| `--verbose`, `-v` | Verbose output |",
        "| `--timeout` | Blender timeout in seconds (default: 600) |",
        "| `--blender-path` | Path to Blender executable |",
        "",
        "### `hamr validate`",
        "",
        "Validate a spec without building.",
        "",
        "```bash",
        "hamr validate spec.yaml",
        "```",
        "",
        "### `hamr inspect`",
        "",
        "Inspect a VRM/GLB file for compliance.",
        "",
        "```bash",
        "hamr inspect avatar.vrm --targets VRCHAT",
        "```",
        "",
        "### `hamr list-presets`",
        "",
        "List available character and body presets.",
        "",
        "```bash",
        "hamr list-presets                    # All presets",
        "hamr list-presets --what character   # Character presets only",
        "hamr list-presets --what body        # Body presets only",
        "```",
        "",
        "### `hamr verify-rig`",
        "",
        "Verify VRM bone hierarchy and naming.",
        "",
        "```bash",
        "hamr verify-rig avatar.vrm",
        "hamr verify-rig avatar.vrm --strict",
        "```",
        "",
        "### `hamr check-env`",
        "",
        "Check your build environment for Blender, add-ons, etc.",
        "",
        "### `hamr version`",
        "",
        "Print version information.",
        "",
        "### `hamr docs generate`",
        "",
        "Generate documentation files (CLI reference, architecture, presets).",
        "",
        "```bash",
        "hamr docs generate --output docs/",
        "```",
        "",
    ]


def generate_readme_presets() -> list[str]:
    """Generate the presets section for README."""
    from hamr.core.presets import CHARACTER_PRESETS, PRESET_CATEGORIES

    lines = [
        "## 🎭 Character Presets",
        "",
    ]

    for name, data in CHARACTER_PRESETS.items():
        spec = data["spec"]
        body = spec.get("body", {})
        hair = spec.get("hair", {})
        lines.append(f"- **{data['display_name']}** (`{name}`) — {data['description']}")

    lines.extend([
        "",
        "Override any preset parameter with `--preset` + custom YAML, "
        "or use Python `resolve_preset()` with overrides dict.",
        "",
    ])
    return lines


def generate_readme_dev() -> list[str]:
    """Generate the development section for README."""
    return [
        "---",
        "",
        "## 🔧 Development",
        "",
        "```bash",
        "# Clone",
        "git clone https://github.com/hrabanazviking/Hamr.git",
        "cd Hamr",
        "",
        "# Install dev dependencies",
        'pip install -e ".[dev]"',
        "",
        "# Run tests",
        "pytest tests/ -v",
        "",
        "# Run with coverage",
        "pytest tests/ --cov=hamr --cov-report=term-missing",
        "",
        "# Lint",
        "ruff check src/hamr/",
        "",
        "# Generate docs",
        "hamr docs generate --output docs/",
        "```",
        "",
    ]


# ── generate_all — Master Generator ───────────────────────────────────────────

def generate_all(output_dir: str = "docs") -> None:
    """Generate all documentation files to the specified output directory.

    Creates:
      - cli_reference.md
      - architecture.md
      - preset_guide.md
      - README.md (in the project root)

    Args:
        output_dir: Directory to write documentation files into.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cli_ref = generate_cli_reference()
    arch_diag = generate_architecture_diagram()
    preset_guide = generate_preset_guide()
    readme = generate_readme()

    (out / "cli_reference.md").write_text(cli_ref, encoding="utf-8")
    (out / "architecture.md").write_text(arch_diag, encoding="utf-8")
    (out / "preset_guide.md").write_text(preset_guide, encoding="utf-8")
    (out / "README.md").write_text(readme, encoding="utf-8")

    print(f"✓ Generated 4 documentation files in {out}/")
    print(f"  - cli_reference.md  ({len(cli_ref):,} chars)")
    print(f"  - architecture.md   ({len(arch_diag):,} chars)")
    print(f"  - preset_guide.md   ({len(preset_guide):,} chars)")
    print(f"  - README.md         ({len(readme):,} chars)")