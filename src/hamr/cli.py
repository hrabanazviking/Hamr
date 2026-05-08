"""
Hamr CLI — The forge's command-line interface.

Usage:
    hamr build spec.yaml --out output/
    hamr validate spec.yaml
    hamr inspect output/avatar.vrm --targets VRCHAT
    hamr list-presets
    hamr check-env
    hamr version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hamr.core.constants import BODY_PRESETS
from hamr.core.errors import HamrError, SpecValidationError


def cmd_build(args: argparse.Namespace) -> int:
    """Build a character from a spec file."""
    from hamr.core.pipeline import BuildPipeline
    from hamr.core.spec import Spec
    from hamr.core.builder import _resolve_forges

    # ── Dry-run mode: resolve spec and forges, no Blender ───────────
    if args.dry_run:
        try:
            spec = Spec.from_yaml(args.spec)
            print(f"✓ Spec parsed: {spec.character.name}")
        except SpecValidationError as e:
            print(f"✗ Validation failed: {e}", file=sys.stderr)
            return 2

        forge_config = _resolve_forges(spec.character)
        print("✓ Forges resolved:")
        if forge_config.get("hair"):
            h = forge_config["hair"]
            print(f"  Hair: curl={h.get('curl_tightness', 0.0):.2f}, "
                  f"volume={h.get('volume', 0.0):.2f}, "
                  f"gradient={h.get('gradient_preset', '?')}, "
                  f"shells={h.get('style_template', {}).get('shell_count', '?') if isinstance(h.get('style_template'), dict) else '?'}")
        if forge_config.get("face"):
            f = forge_config["face"]
            n_keys = len(f.get("shape_keys", {}))
            elf_factor = f.get("ear_elf_factor", "?")
            lip_full = f.get("lip_fullness", "?")
            print(f"  Face: {n_keys} shape keys, "
                  f"elf_factor={elf_factor}, "
                  f"lip_fullness={lip_full}")
        if forge_config.get("clothing"):
            c = forge_config["clothing"]
            print(f"  Clothing: {len(c)} items")
            for item in c:
                name = item.get("name", "?") if isinstance(item, dict) else getattr(item, "name", "?")
                ctype = item.get("cloth_type", "?") if isinstance(item, dict) else getattr(item, "cloth_type", "?")
                mat = item.get("material_category", "?") if isinstance(item, dict) else getattr(item, "material_category", "?")
                print(f"    - {name}: {ctype} ({mat})")

        if args.verbose:
            print("\nVerbose forge config:")
            for forge_name, config in forge_config.items():
                print(f"  [{forge_name}]")
                if hasattr(config, "to_dict"):
                    for k, v in config.to_dict().items():
                        print(f"    {k}: {v}")
                elif isinstance(config, list):
                    for i, item in enumerate(config):
                        if hasattr(item, "to_dict"):
                            print(f"    [{i}] {item.to_dict()}")
                        else:
                            print(f"    [{i}] {item}")
        print("\n⚡ Dry run complete — no Blender launched.")
        return 0

    # ── Full build mode ─────────────────────────────────────────────
    pipeline = BuildPipeline(
        blender_path=args.blender_path,
        blender_timeout=args.timeout,
        keep_temp=args.keep_temp,
    )

    try:
        result = pipeline.build(
            spec_path=args.spec,
            output_dir=args.out,
            format=args.format,
            base_mesh=args.base,
            validate=not args.no_validate,
            max_tex=args.max_tex,
        )
    except SpecValidationError as e:
        print(f"✗ Validation failed: {e}", file=sys.stderr)
        return 2
    except HamrError as e:
        print(f"✗ Build error: {e}", file=sys.stderr)
        return 1

    if result.success:
        print(f"✓ Character built: {result.output_path}")
        if result.output_size_mb:
            print(f"  Size: {result.output_size_mb:.1f} MB")
        print(f"  Time: {result.elapsed:.1f}s")
        if args.verbose and result.blender_result:
            print(f"  Blender stdout: {result.blender_result.stdout[-500:]!r}")
        return 0
    else:
        print(f"✗ Build failed:", file=sys.stderr)
        for err in result.errors:
            print(f"  • {err}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a spec without building."""
    from hamr.core.pipeline import BuildPipeline

    pipeline = BuildPipeline()
    errors = pipeline.validate_only(args.spec)
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
        desc = ", ".join(f"{k}={v:.2f}" for k, v in proportions.items())
        print(f"  {name:20s}  {desc}")
    return 0


def cmd_check_env(args: argparse.Namespace) -> int:
    """Check the build environment for readiness."""
    from hamr.core.pipeline import BuildPipeline

    pipeline = BuildPipeline()
    env = pipeline.check_environment()

    print("Hamr Build Environment Check")
    print("=" * 40)

    blender_ok = env.get("blender_available", False)
    print(f"  Blender:     {'✓ ' + str(env.get('blender_version', '')) if blender_ok else '✗ Not found'}")
    print(f"  VRM Addon:   {'✓ Installed' if env.get('vrm_addon') else '✗ Not found' if env.get('vrm_addon') is not None else '? Unknown'}")
    print(f"  MB-Lab:      {'✓ Installed' if env.get('mblab_addon') else '✗ Not found' if env.get('mblab_addon') is not None else '? Unknown'}")
    print(f"  Build Script:{'✓ Found' if env.get('build_script') else '✗ Not found'}")

    if blender_ok:
        return 0
    else:
        print("\n⚠  Blender not found. Install Blender and add it to PATH.")
        print("   Or specify path with --blender-path.")
        return 1


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
    build_parser.add_argument("--format", "-f", default="vrm1", choices=["vrm1", "glb", "blend"])
    build_parser.add_argument("--base", "-b", default=None, help="Base mesh path (.vrm, .fbx, .glb)")
    build_parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    build_parser.add_argument("--dry-run", action="store_true", help="Resolve spec and forges without launching Blender")
    build_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output with forge details")
    build_parser.add_argument("--keep-temp", action="store_true", help="Keep temp files (debug)")
    build_parser.add_argument("--max-tex", type=int, default=0, help="Max texture resolution (0=unlimited)")
    build_parser.add_argument("--timeout", type=int, default=600, help="Blender timeout in seconds")
    build_parser.add_argument("--blender-path", default=None, help="Path to Blender executable")
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

    # check-env
    subparsers.add_parser("check-env", help="Check build environment").set_defaults(func=cmd_check_env)

    # version
    subparsers.add_parser("version", help="Print version").set_defaults(func=cmd_version)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())