"""
Hamr CLI — The forge's command-line interface.

Usage:
    hamr build --spec spec.yaml                     # Build from spec file
    hamr build --preset anime_girl_default           # Build from preset
    hamr build --preset anime_girl_warrior --budget minimal
    hamr build --spec spec.yaml --budget high --force-over-budget
    hamr validate spec.yaml
    hamr inspect output/avatar.vrm --targets VRCHAT
    hamr list-presets [--what character|body|all]
    hamr verify-rig avatar.vrm [--strict]
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
from hamr.core.presets import CHARACTER_PRESETS


def cmd_build(args: argparse.Namespace) -> int:
    """Build a character from a spec file or preset."""
    from hamr.core.pipeline import BuildPipeline
    from hamr.core.spec import Spec
    from hamr.core.builder import _resolve_forges
    from hamr.core.perf import MEMORY_TIERS, check_budget
    from hamr.core.presets import CHARACTER_PRESETS, resolve_preset

    # ── Resolve spec source: either --preset or spec file ──────────
    if args.preset:
        # Build from a named preset
        if args.preset not in CHARACTER_PRESETS:
            print(f"✗ Unknown preset: {args.preset!r}", file=sys.stderr)
            print(f"  Available: {', '.join(sorted(CHARACTER_PRESETS.keys()))}",
                  file=sys.stderr)
            return 2

        preset_data = resolve_preset(args.preset)
        preset_info = CHARACTER_PRESETS[args.preset]
        print(f"📐 Preset: {preset_info['display_name']}")
        print(f"   {preset_info['description']}")

    # ── Dry-run mode: resolve spec and forges, no Blender ───────────
    if args.dry_run:
        spec_path = getattr(args, "spec", None)
        if spec_path:
            try:
                spec = Spec.from_yaml(args.spec)
                print(f"✓ Spec parsed: {spec.character.name}")
            except SpecValidationError as e:
                print(f"✗ Validation failed: {e}", file=sys.stderr)
                return 2
            except Exception as e:
                print(f"✗ Spec parse error: {e}", file=sys.stderr)
                return 2
        elif args.preset:
            spec_name = CHARACTER_PRESETS[args.preset]["spec"].get("name", args.preset)
            print(f"✓ Preset resolved: {args.preset}")
        else:
            print("✗ Specify --spec or --preset", file=sys.stderr)
            return 2

        # Show forge resolution
        if spec_path:
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

        # Show budget summary in dry-run
        budget = MEMORY_TIERS.get(args.budget, MEMORY_TIERS["balanced"])
        print(f"\n💰 Budget tier: {args.budget}")
        print(f"   Max triangles: {budget.max_triangles}")
        print(f"   Max memory: {budget.max_memory_mb:.0f} MB")
        print(f"   Max build time: {budget.max_build_time_seconds:.0f}s")
        if args.force_over_budget:
            print("   ⚠  Force-over-budget: budget check skipped")

        print("\n⚡ Dry run complete — no Blender launched.")
        return 0

    # ── Full build mode ─────────────────────────────────────────────
    spec_path = getattr(args, "spec", None)

    pipeline = BuildPipeline(
        blender_path=args.blender_path,
        blender_timeout=args.timeout,
        keep_temp=args.keep_temp,
    )

    # Determine performance budget tier
    budget = MEMORY_TIERS.get(args.budget, MEMORY_TIERS["balanced"])

    # If a preset is specified, resolve it and write a temp spec
    if args.preset:
        preset_data = resolve_preset(args.preset)
        preset_info = CHARACTER_PRESETS[args.preset]
        print(f"📐 Preset: {preset_info['display_name']}")
        print(f"   {preset_info['description']}")

        # We need a spec file path for the pipeline — if no spec is
        # provided, write the preset data to a temp file
        if not spec_path:
            import tempfile
            from hamr.core.models import CharacterSpec

            # Build a CharacterSpec from the preset dict
            char_spec = CharacterSpec.from_dict(preset_data)
            safe_name = char_spec.name.replace(" ", "_").lower()

            # Write preset to a temp YAML file
            output_dir = Path(args.out)
            output_dir.mkdir(parents=True, exist_ok=True)
            spec_path = str(output_dir / f".hamr_{safe_name}_preset.yaml")

            # Write as YAML
            try:
                from hamr.core.spec import Spec
                temp_spec = Spec(character=char_spec)
                temp_spec.to_yaml(spec_path)
            except Exception:
                # Fallback: write as JSON which Spec.from_yaml can also parse
                import yaml
                # Build minimal YAML structure
                yaml_data = {"character": preset_data}
                with open(spec_path, "w") as f:
                    yaml.dump(yaml_data, f, default_flow_style=False)

    # Parse the spec and run budget check before launching Blender
    if spec_path:
        try:
            spec_obj = Spec.from_yaml(spec_path)
        except SpecValidationError as e:
            print(f"✗ Validation failed: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"✗ Spec parse error: {e}", file=sys.stderr)
            return 2

        # ── Performance budget pre-flight check ─────────────────────
        perf_report = check_budget(spec_obj.character, budget)
        if not perf_report.within_budget and not args.force_over_budget:
            print(f"\n{'=' * 60}", file=sys.stderr)
            print("⚠  PERFORMANCE BUDGET CHECK FAILED", file=sys.stderr)
            print(f"{'=' * 60}", file=sys.stderr)
            print(perf_report.summary(), file=sys.stderr)
            print(f"\n✗ Build exceeds {args.budget} budget tier. "
                  "Use --force-over-budget to override.", file=sys.stderr)
            return 3  # Exit code 3 = budget exceeded
        elif not perf_report.within_budget and args.force_over_budget:
            print("⚠  Performance budget exceeded — continuing due to --force-over-budget",
                  file=sys.stderr)
            print(perf_report.summary(), file=sys.stderr)
        elif perf_report.warnings:
            print("⚠  Performance budget warnings:")
            for w in perf_report.warnings:
                print(f"   {w}")

    try:
        result = pipeline.build(
            spec_path=spec_path or "",
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
    """List available presets (body + character)."""
    from hamr.core.presets import CHARACTER_PRESETS

    what = getattr(args, "what", "all")

    if what in ("all", "character"):
        print("Character presets:")
        print("-" * 60)
        for name, preset in CHARACTER_PRESETS.items():
            print(f"  {name:30s}  {preset['display_name']}")
            print(f"  {'':30s}  {preset['description']}")

    if what in ("all", "body"):
        if what == "all":
            print()
        print("Body presets:")
        print("-" * 60)
        for name, proportions in BODY_PRESETS.items():
            desc = ", ".join(f"{k}={v:.2f}" for k, v in proportions.items())
            print(f"  {name:20s}  {desc}")

    return 0


def cmd_verify_rig(args: argparse.Namespace) -> int:
    """Verify a VRM file's rig structure."""
    from hamr.rigs.verify import verify_vrm_rig

    vrm_path = args.path
    try:
        result = verify_vrm_rig(vrm_path)
    except FileNotFoundError:
        print(f"✗ File not found: {vrm_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error reading file: {e}", file=sys.stderr)
        return 1

    report = result["report"]
    print(report.summary())

    valid = result["valid"]

    if args.strict and result["naming_issues"]:
        print("\n⚠  Strict mode: treating naming issues as errors")
        valid = False

    return 0 if valid else 1


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
    build_parser = subparsers.add_parser("build", help="Build a character from spec or preset")
    build_parser.add_argument(
        "spec", nargs="?", default=None,
        help="Path to YAML spec file (optional if --preset is used)",
    )
    build_parser.add_argument("--out", "-o", default="output/", help="Output directory")
    build_parser.add_argument("--format", "-f", default="vrm1", choices=["vrm1", "glb", "blend"])
    build_parser.add_argument("--base", "-b", default=None, help="Base mesh path (.vrm, .fbx, .glb)")
    build_parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    build_parser.add_argument(
        "--preset", "-p", default=None,
        choices=list(CHARACTER_PRESETS.keys()),
        help="Apply a character preset before building",
    )
    build_parser.add_argument(
        "--budget", "-B", default="balanced",
        choices=["minimal", "balanced", "high"],
        help="Performance budget tier (default: balanced)",
    )
    build_parser.add_argument(
        "--force-over-budget",
        action="store_true",
        help="Force build even if spec exceeds performance budget",
    )
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
    list_presets_parser = subparsers.add_parser("list-presets", help="List available presets")
    list_presets_parser.add_argument(
        "--what", "-w",
        choices=["all", "character", "body"],
        default="all",
        help="Which presets to list: all, character, or body (default: all)",
    )
    list_presets_parser.set_defaults(func=cmd_list_presets)

    # verify-rig
    verify_rig_parser = subparsers.add_parser(
        "verify-rig",
        help="Verify VRM rig completeness and bone hierarchy",
    )
    verify_rig_parser.add_argument("path", help="Path to VRM file to verify")
    verify_rig_parser.add_argument(
        "--strict", action="store_true",
        help="Treat naming issues as errors",
    )
    verify_rig_parser.set_defaults(func=cmd_verify_rig)

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