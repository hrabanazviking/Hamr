"""
Hamr Build Script — Runs INSIDE Blender via --python.

This script is executed by the Blender Bridge runner inside a
headless Blender process. It receives a spec JSON file path,
applies all modifications to the base mesh, and exports the
result as VRM 1.0.

Arguments (passed via argv after --):
    --spec <path>       Path to the spec JSON file
    --base <path>       Path to the base mesh file (.vrm, .fbx, .obj, .glb)
    --output <path>     Path where the output .vrm should be written
    --max-tex <int>     Maximum texture resolution (e.g. 1024). 0=unlimited.

Exit codes:
    0 = success
    1 = usage/argument error
    2 = spec read/parse error
    3 = import error (base mesh)
    4 = transformation error
    5 = VRM export error
    6 = post-export validation error
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Configure logging for Blender output
logger = logging.getLogger("hamr_build")
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.DEBUG)


def parse_args(argv: list[str]) -> dict:
    """Parse command-line arguments."""
    args = {
        "spec": None,
        "base": None,
        "output": None,
        "max_tex": 0,
    }

    i = 0
    while i < len(argv):
        if argv[i] == "--spec" and i + 1 < len(argv):
            args["spec"] = argv[i + 1]
            i += 2
        elif argv[i] == "--base" and i + 1 < len(argv):
            args["base"] = argv[i + 1]
            i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            args["output"] = argv[i + 1]
            i += 2
        elif argv[i] == "--max-tex" and i + 1 < len(argv):
            args["max_tex"] = int(argv[i + 1])
            i += 2
        else:
            i += 1

    return args


def main() -> int:
    """Main build pipeline — runs inside Blender."""
    try:
        import bpy  # type: ignore
    except ImportError:
        logger.error("This script must run inside Blender (bpy not available)")
        return 1

    # Parse arguments from sys.argv (after the -- separator)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        logger.error("No arguments passed (expected -- separator)")
        return 1

    args = parse_args(argv)

    if not args["spec"]:
        logger.error("--spec argument required")
        return 1
    if not args["output"]:
        logger.error("--output argument required")
        return 1

    # Load spec
    spec_path = Path(args["spec"])
    if not spec_path.exists():
        logger.error(f"Spec file not found: {spec_path}")
        return 2

    try:
        spec_data = json.loads(spec_path.read_text())
        logger.info(f"Loaded spec: {spec_data.get('name', 'unknown')}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON spec: {e}")
        return 2

    output_path = Path(args["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Import base mesh
    base_path = args["base"]
    if base_path:
        base_path = Path(base_path)
        suffix = base_path.suffix.lower()

        if suffix == ".vrm":
            # VRM import via VRM Add-on
            bpy.ops.import_scene.vrm(filepath=str(base_path))
        elif suffix == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(base_path))
        elif suffix == ".glb":
            bpy.ops.import_scene.gltf(filepath=str(base_path))
        elif suffix == ".obj":
            bpy.ops.wm.obj_import(filepath=str(base_path))
        else:
            logger.error(f"Unsupported base mesh format: {suffix}")
            return 3

        logger.info(f"Imported base mesh: {base_path}")
    else:
        logger.info("No base mesh specified — using current scene")

    # Find armature
    armature = None
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if armature is None:
        logger.error("No armature found in scene")
        return 4

    logger.info(f"Using armature: {armature.name}")

    # Apply VRM bone mapping
    try:
        from hamr.export.vrm import (
            setup_vrm_humanoid,
            setup_vrm_metadata,
        )

        setup_vrm_humanoid(
            armature_name=armature.name,
            bone_map=None,  # Use MB_LAB_BONE_MAP default
        )

        setup_vrm_metadata(
            armature_name=armature.name,
            title=spec_data.get("name", "Hamr Character"),
            author=spec_data.get("author", "Hamr Forge"),
            version=spec_data.get("version", "1.0"),
        )
    except Exception as e:
        logger.error(f"VRM setup failed: {e}")
        return 4

    # Export VRM
    try:
        from hamr.export.vrm import export_vrm

        success = export_vrm(
            armature_name=armature.name,
            output_path=str(output_path),
        )

        if not success:
            logger.error("VRM export returned False")
            return 5

        logger.info(f"Exported: {output_path}")
        return 0

    except Exception as e:
        logger.error(f"VRM export failed: {e}")
        return 5


if __name__ == "__main__":
    sys.exit(main())