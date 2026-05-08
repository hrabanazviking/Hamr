"""
Hamr CLI — The forge's command-line interface.

Usage:
    hamr build spec.yaml --out output/
    hamr inspect output/avatar.vrm --targets VRCHAT
    hamr validate spec.yaml
    hamr version
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.console import Console

from hamr.core.spec import Spec
from hamr.core.validate import validate_spec
from hamr.core.models import CharacterSpec

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="hamr")
def main() -> None:
    """ᚺᚨᛗᚱ — The Shape-Skin Engine"""
    pass


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--out", "-o", "output_dir", default="output", help="Output directory")
@click.option("--format", "-f", "export_format", default="vrm1",
              type=click.Choice(["vrm1", "glb", "blend"]),
              help="Export format")
@click.option("--json-output", is_flag=True, help="Output results as JSON")
def build(spec_path: str, output_dir: str, export_format: str, json_output: bool) -> None:
    """Forge a character from a spec file."""
    console.print("[bold cyan]ᚺᚨᛗᚱ[/] — The Shape-Skin Engine")
    console.print(f"[dim]Forging from: {spec_path}[/]")

    start_time = time.time()

    try:
        spec = Spec.from_yaml(spec_path)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)
    except Exception as e:
        from hamr.core.errors import SpecValidationError
        if isinstance(e, SpecValidationError):
            console.print(f"[red]Spec validation failed:[/]")
            for err in e.errors:
                console.print(f"  [red]✗[/] {err}")
            sys.exit(1)
        raise

    console.print(f"[green]✓[/] Spec validated: [bold]{spec.character.name}[/]")
    console.print(f"[dim]  Body: {spec.character.body.build} / {spec.character.body.height_cm}cm[/]")
    console.print(f"[dim]  Hair: {spec.character.hair.style} / {spec.character.hair.length}[/]")
    console.print(f"[dim]  Export: {export_format}[/]")

    # Build pipeline — Phase 1 placeholder
    console.print("\n[yellow]⚠ Build pipeline not yet implemented.[/]")
    console.print("[dim]Phase 1 foundation is laid. The forge will be built.[/]")

    elapsed = time.time() - start_time
    console.print(f"\n[dim]Elapsed: {elapsed:.1f}s[/]")


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--targets", "-t", default="VRCHAT",
              help="Compliance targets (comma-separated)")
def inspect(path: str, targets: str) -> None:
    """Inspect a VRM/GLB file for compliance."""
    console.print("[bold cyan]ᚺᚨᛗᚱ[/] — Inspect")
    console.print(f"[dim]Inspecting: {path}[/]")
    console.print(f"[dim]Targets: {targets}[/]")
    console.print("\n[yellow]⚠ Inspect not yet implemented.[/]")


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
def validate(spec_path: str) -> None:
    """Validate a spec file without building."""
    try:
        spec = Spec.from_yaml(spec_path)
    except Exception as e:
        console.print(f"[red]Parse error:[/] {e}")
        sys.exit(1)

    errors = validate_spec(spec.character)

    if errors:
        console.print(f"[red]✗ {len(errors)} validation errors:[/]")
        for err in errors:
            console.print(f"  [red]✗[/] {err}")
        sys.exit(1)
    else:
        console.print(f"[green]✓[/] Spec valid: [bold]{spec.character.name}[/]")


@main.command()
def list_presets() -> None:
    """List available body presets."""
    from hamr.core.constants import BODY_PRESETS

    console.print("[bold cyan]ᚺᚨᛗᚱ[/] — Body Presets\n")
    for name, values in BODY_PRESETS.items():
        console.print(f"  [bold]{name}[/]")
        for key, value in values.items():
            console.print(f"    {key}: {value}")
        console.print()


if __name__ == "__main__":
    main()