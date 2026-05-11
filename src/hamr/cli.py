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

from hamr.core.a11y import CLIOptions, format_output, format_json_output, format_error, should_suppress_output, get_actionable_suggestion
from hamr.core.constants import BODY_PRESETS
from hamr.core.errors import HamrError, SpecValidationError
from hamr.core.presets import CHARACTER_PRESETS


def _a11y_from_args(args: argparse.Namespace) -> CLIOptions:
    """Build CLIOptions from parsed argparse Namespace."""
    return CLIOptions(
        no_color=getattr(args, "no_color", False),
        quiet=getattr(args, "quiet", False),
        json_output=getattr(args, "json", False),
        verbose=getattr(args, "verbose", False),
    )


def cmd_build(args: argparse.Namespace) -> int:
    """Build a character from a spec file or preset."""
    from hamr.core.pipeline import BuildPipeline
    from hamr.core.spec import Spec
    from hamr.core.builder import _resolve_forges
    from hamr.core.perf import MEMORY_TIERS, check_budget
    from hamr.core.presets import CHARACTER_PRESETS, resolve_preset

    opts = _a11y_from_args(args)

    # ── Resolve spec source: either --preset or spec file ──────────
    if args.preset:
        # Build from a named preset
        if args.preset not in CHARACTER_PRESETS:
            if opts.json_output:
                print(format_json_output(format_error(
                    FileNotFoundError(f"Unknown preset: {args.preset!r}"), opts
                ), opts), file=sys.stderr)
            else:
                print(format_output(f"✗ Unknown preset: {args.preset!r}", severity="error", options=opts), file=sys.stderr)
                print(format_output(f"  Available: {', '.join(sorted(CHARACTER_PRESETS.keys()))}", severity="info", options=opts),
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
            force_over_budget=args.force_over_budget,
        )
    except SpecValidationError as e:
        if opts.json_output:
            print(format_json_output(format_error(e, opts), opts), file=sys.stderr)
        else:
            print(format_output(f"✗ Validation failed: {e}", severity="error", options=opts), file=sys.stderr)
            print(format_output(f"  Suggestion: {get_actionable_suggestion(e)}", severity="info", options=opts), file=sys.stderr)
        return 2
    except HamrError as e:
        if opts.json_output:
            print(format_json_output(format_error(e, opts), opts), file=sys.stderr)
        else:
            print(format_output(f"✗ Build error: {e}", severity="error", options=opts), file=sys.stderr)
            print(format_output(f"  Suggestion: {get_actionable_suggestion(e)}", severity="info", options=opts), file=sys.stderr)
        return 1

    if result.success:
        if opts.json_output:
            result_data = {
                "success": True,
                "output_path": str(result.output_path) if result.output_path else None,
                "output_size_mb": result.output_size_mb,
                "elapsed_seconds": result.elapsed,
            }
            print(format_json_output(result_data, opts))
        elif not should_suppress_output(opts):
            print(format_output(f"✓ Character built: {result.output_path}", severity="success", options=opts))
            if result.output_size_mb:
                print(f"  Size: {result.output_size_mb:.1f} MB")
            print(f"  Time: {result.elapsed:.1f}s")
            if args.verbose and result.blender_result:
                print(f"  Blender stdout: {result.blender_result.stdout[-500:]!r}")
        return 0
    else:
        if opts.json_output:
            print(format_json_output({
                "success": False,
                "errors": [str(e) for e in result.errors],
            }, opts), file=sys.stderr)
        else:
            print(format_output("✗ Build failed:", severity="error", options=opts), file=sys.stderr)
            for err in result.errors:
                print(format_output(f"  • {err}", severity="error", options=opts), file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a spec without building."""
    from hamr.core.pipeline import BuildPipeline

    opts = _a11y_from_args(args)
    pipeline = BuildPipeline()
    errors = pipeline.validate_only(args.spec)

    if should_suppress_output(opts) and not opts.json_output:
        return 1 if errors else 0

    if errors:
        if opts.json_output:
            error_data = [format_error(e, opts) if isinstance(e, Exception) else {"message": str(e)} for e in errors]
            print(format_json_output({"valid": False, "errors": error_data}, opts))
        else:
            print(format_output(f"✗ {len(errors)} validation error(s):", severity="error", options=opts))
            for err in errors:
                print(format_output(f"  • {err}", severity="error", options=opts))
        return 1
    else:
        if opts.json_output:
            print(format_json_output({"valid": True}, opts))
        else:
            print(format_output("✓ Spec is valid", severity="success", options=opts))
        return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect a VRM/GLB file for compliance."""
    from hamr.core.builder import inspect

    opts = _a11y_from_args(args)

    try:
        report = inspect(args.path, targets=args.targets)
        if opts.json_output:
            print(format_json_output(report, opts))
        else:
            print(json.dumps(report, indent=2, default=str))
        return 0
    except HamrError as e:
        if opts.json_output:
            print(format_json_output(format_error(e, opts), opts))
        else:
            print(format_output(f"✗ Inspection error: {e}", severity="error", options=opts), file=sys.stderr)
        return 1


def cmd_list_presets(args: argparse.Namespace) -> int:
    """List available presets (body + character)."""
    from hamr.core.presets import CHARACTER_PRESETS

    opts = _a11y_from_args(args)
    what = getattr(args, "what", "all")

    if opts.json_output:
        data = {}
        if what in ("all", "character"):
            data["character"] = {
                name: {"display_name": p["display_name"], "description": p["description"]}
                for name, p in CHARACTER_PRESETS.items()
            }
        if what in ("all", "body"):
            data["body"] = {
                name: {k: v for k, v in proportions.items()}
                for name, proportions in BODY_PRESETS.items()
            }
        print(format_json_output(data, opts))
        return 0

    if should_suppress_output(opts):
        return 0

    if what in ("all", "character"):
        print(format_output("Character presets:", severity="info", options=opts))
        print("-" * 60)
        for name, preset in CHARACTER_PRESETS.items():
            print(f"  {name:30s}  {preset['display_name']}")
            print(f"  {'':30s}  {preset['description']}")

    if what in ("all", "body"):
        if what == "all":
            print()
        print(format_output("Body presets:", severity="info", options=opts))
        print("-" * 60)
        for name, proportions in BODY_PRESETS.items():
            desc = ", ".join(f"{k}={v:.2f}" for k, v in proportions.items())
            print(f"  {name:20s}  {desc}")

    return 0


def cmd_verify_rig(args: argparse.Namespace) -> int:
    """Verify a VRM file's rig structure."""
    from hamr.rigs.verify import verify_vrm_rig

    opts = _a11y_from_args(args)

    vrm_path = args.path
    try:
        result = verify_vrm_rig(vrm_path)
    except FileNotFoundError:
        if opts.json_output:
            print(format_json_output(format_error(FileNotFoundError(vrm_path), opts), opts), file=sys.stderr)
        else:
            print(format_output(f"✗ File not found: {vrm_path}", severity="error", options=opts), file=sys.stderr)
        return 1
    except Exception as e:
        if opts.json_output:
            print(format_json_output(format_error(e, opts), opts), file=sys.stderr)
        else:
            print(format_output(f"✗ Error reading file: {e}", severity="error", options=opts), file=sys.stderr)
        return 1

    report = result["report"]

    if opts.json_output:
        print(format_json_output({
            "valid": result["valid"],
            "naming_issues": result.get("naming_issues", []),
            "summary": report.summary(),
        }, opts))
        return 0 if result["valid"] else 1

    if should_suppress_output(opts):
        return 0 if result["valid"] else 1

    print(report.summary())

    valid = result["valid"]

    if args.strict and result["naming_issues"]:
        print(format_output("\n⚠  Strict mode: treating naming issues as errors", severity="warning", options=opts))
        valid = False

    return 0 if valid else 1


def cmd_check_env(args: argparse.Namespace) -> int:
    """Check the build environment for readiness."""
    from hamr.core.pipeline import BuildPipeline

    opts = _a11y_from_args(args)
    pipeline = BuildPipeline()
    env = pipeline.check_environment()

    blender_ok = env.get("blender_available", False)

    if opts.json_output:
        print(format_json_output(env, opts))
        return 0 if blender_ok else 1

    if should_suppress_output(opts):
        return 0 if blender_ok else 1

    print(format_output("Hamr Build Environment Check", severity="info", options=opts))
    print("=" * 40)

    print(f"  Blender:     {'✓ ' + str(env.get('blender_version', '')) if blender_ok else '✗ Not found'}")
    print(f"  VRM Addon:   {'✓ Installed' if env.get('vrm_addon') else '✗ Not found' if env.get('vrm_addon') is not None else '? Unknown'}")
    print(f"  MB-Lab:      {'✓ Installed' if env.get('mblab_addon') else '✗ Not found' if env.get('mblab_addon') is not None else '? Unknown'}")
    print(f"  Build Script:{'✓ Found' if env.get('build_script') else '✗ Not found'}")

    if blender_ok:
        return 0
    else:
        print(format_output("\n⚠  Blender not found. Install Blender and add it to PATH.", severity="warning", options=opts))
        print(format_output("   Or specify path with --blender-path.", severity="info", options=opts))
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """Print version information."""
    from hamr import __version__, __author__

    opts = _a11y_from_args(args)

    if opts.json_output:
        print(format_json_output({"version": __version__, "author": __author__}, opts))
        return 0

    if should_suppress_output(opts):
        return 0

    print(format_output(f"Hamr {__version__} — The Shape-Skin Engine", severity="info", options=opts))
    print(format_output(f"By {__author__}", severity="info", options=opts))
    return 0


def cmd_docs(args: argparse.Namespace) -> int:
    """Generate documentation files."""
    from hamr.docs.generate import generate_all

    opts = _a11y_from_args(args)
    output_dir = getattr(args, "output", "docs")
    try:
        generate_all(output_dir=output_dir)
    except Exception as e:
        if opts.json_output:
            print(format_json_output(format_error(e, opts), opts), file=sys.stderr)
        else:
            print(format_output(f"✗ Documentation generation failed: {e}", severity="error", options=opts), file=sys.stderr)
        return 1

    if not should_suppress_output(opts) and not opts.json_output:
        print(format_output(f"✓ Documentation generated in {output_dir}/", severity="success", options=opts))
    return 0


def cmd_docs_audit(args: argparse.Namespace) -> int:
    """Run accessibility and compliance audit on all hamr modules."""
    from hamr.docs.a11y_audit import audit_all_modules, format_audit_report

    opts = _a11y_from_args(args)
    results = audit_all_modules()

    if opts.json_output:
        data = []
        for r in results:
            data.append({
                "module": r.module,
                "passed": r.passed,
                "critical_count": r.critical_count,
                "warning_count": r.warning_count,
                "info_count": r.info_count,
                "issues": [
                    {
                        "function": i.function,
                        "severity": i.severity,
                        "description": i.description,
                        "suggestion": i.suggestion,
                    }
                    for i in r.issues
                ],
            })
        print(format_json_output(data, opts))
    else:
        report = format_audit_report(results)
        print(report)

    # Exit 1 if any critical issues, 0 otherwise
    total_critical = sum(r.critical_count for r in results)
    return 1 if total_critical > 0 else 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="hamr",
        description="ᚺᚨᛗᚱ — The Shape-Skin Engine",
    )

    # ── Global accessibility flags ───────────────────────────────────
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color codes in output",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress non-essential output; produce compact JSON when --json is set",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON for machine consumption",
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

    # docs generate
    docs_parser = subparsers.add_parser("docs", help="Generate documentation")
    docs_sub = docs_parser.add_subparsers(dest="docs_command", help="Documentation commands")
    docs_gen = docs_sub.add_parser("generate", help="Generate all documentation files")
    docs_gen.add_argument("--output", "-o", default="docs", help="Output directory for generated docs")
    docs_gen.set_defaults(func=cmd_docs)

    # docs audit
    docs_audit = docs_sub.add_parser("audit", help="Run accessibility and compliance audit")
    docs_audit.set_defaults(func=cmd_docs_audit)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())