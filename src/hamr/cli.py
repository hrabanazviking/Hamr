"""
Hamr CLI — The forge's command-line interface.

Usage:
    hamr build spec.yaml --out output/
    hamr validate spec.yaml
    hamr inspect output/avatar.vrm --targets VRCHAT
    hamr list-presets
    hamr version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hamr.core.constants import BODY_PRESETS
from hamr.core.validate import validate_spec
from hamr.core.errors import HamrError, SpecValidationError


def cmd_build(args: argparse.Namespace) -> int:
    """Build a character from a spec file."""
    from hamr.core.builder import build

    try:
        output = build(
            spec_path=args.spec,
            output_dir=args.out,
            format=args.format,
            validate=not args.no_validate,
        )
        print(f"✓ Character built: {output}")
        return 0
    except SpecValidationError as e:
        print(f"✗ Validation failed: {e}", file=sys.stderr)
        return 2
    except HamrError as e:
        print(f"✗ Build error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a spec without building."""
    from hamr.core.builder import validate_only

    errors = validate_only(args.spec)
    if errors:
        print(f"✗ {len(errors)} validation error(s):")
        for err in errors:
            print(f"  • {err}")
        return 1
    else:
        print("✓ Spec is valid")
        return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect a VRM/GLB file for compliance."""
    from hamr.core.builder import inspect

    try:
        report = inspect(args.path, targets=args.targets)
        print(json.dumps(report, indent=2, default=str))
        return 0
    except HamrError as e:
        print(f"✗ Inspection error: {e}", file=sys.stderr)
        return 1


def cmd_list_presets(args: argparse.Namespace) -> int:
    """List available body presets."""
    print("Available body presets:")
    print("-" * 40)
    for name, proportions in BODY_PRESETS.items():
        desc = ", ".join(f"{k}={v:.1f}" for k, v in proportions.items())
        print(f"  {name:20s}  {desc}")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Print version information."""
    from hamr import __version__, __author__
    print(f"Hamr {__version__} — The Shape-Skin Engine")
    print(f"By {__author__}")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="hamr",
        description="ᚺᚨᛗᚱ — The Shape-Skin Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # build
    build_parser = subparsers.add_parser("build", help="Build a character from spec")
    build_parser.add_argument("spec", help="Path to YAML spec file")
    build_parser.add_argument("--out", "-o", default="output/", help="Output directory")
    build_parser.add_argument("--format", "-f", default="vrm", choices=["vrm", "glb"])
    build_parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    build_parser.set_defaults(func=cmd_build)

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate spec without building")
    validate_parser.add_argument("spec", help="Path to YAML spec file")
    validate_parser.set_defaults(func=cmd_validate)

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect VRM/GLB compliance")
    inspect_parser.add_argument("path", help="Path to VRM/GLB file")
    inspect_parser.add_argument("--targets", "-t", nargs="+", default=["VRCHAT"])
    inspect_parser.set_defaults(func=cmd_inspect)

    # list-presets
    subparsers.add_parser("list-presets", help="List body presets").set_defaults(func=cmd_list_presets)

    # version
    subparsers.add_parser("version", help="Print version").set_defaults(func=cmd_version)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())