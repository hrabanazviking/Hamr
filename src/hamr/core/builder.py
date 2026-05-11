"""
Builder — The forge pipeline. Spec → Resolve → Character → VRM.

The builder orchestrates every forge in sequence:
1. Parse & validate spec
2. Resolve through forges (hair, face, clothing)
3. Set up Blender scene
4. Import base mesh
5. Apply body proportions
6. Apply textures & colors
7. Apply hair, face, clothing
8. Set up VRM metadata & bone mapping
9. Export VRM

It never opens a GUI. It speaks to Blender through
the command line, like a völva speaking to the beyond.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from hamr.core.spec import Spec
from hamr.core.models import CharacterSpec
from hamr.core.validate import validate_spec
from hamr.core.errors import HamrError, SpecValidationError, BuildError, ExportError

logger = logging.getLogger("hamr.builder")


def _resolve_forges(char: CharacterSpec) -> dict[str, Any]:
    """
    Run all three forges and produce a resolved build config.

    The forges transform declarative specs into concrete parameters
    that the Blender build script can apply directly.

    Returns:
        Dict with keys 'hair', 'face', 'clothing', each containing
        the forge's resolved build result as a plain dict.
    """
    from hamr.hair import resolve_hair
    from hamr.face import resolve_face
    from hamr.clothing import resolve_clothing

    config: dict[str, Any] = {}

    # Hair Forge
    try:
        hair_result = resolve_hair(char.hair)
        config["hair"] = hair_result.to_dict()
        logger.info(f"💇 Hair resolved: style={char.hair.style}, length={char.hair.length}")
    except Exception as e:
        logger.warning(f"Hair forge failed, using defaults: {e}")
        config["hair"] = None

    # Face Forge
    try:
        face_result = resolve_face(char.face)
        config["face"] = face_result.to_dict()
        logger.info(f"👁 Face resolved: jaw={char.face.jaw}, eyes={char.face.eyes.shape}")
    except Exception as e:
        logger.warning(f"Face forge failed, using defaults: {e}")
        config["face"] = None

    # Clothing Forge — resolve each clothing layer
    try:
        clothing_results = []
        for clothing_spec in char.clothing:
            clothing_result = resolve_clothing(clothing_spec)
            clothing_results.append(clothing_result.to_dict())
        config["clothing"] = clothing_results
        logger.info(f"👕 Clothing resolved: {len(clothing_results)} layers")
    except Exception as e:
        logger.warning(f"Clothing forge failed: {e}")
        config["clothing"] = []

    return config


def build(
    spec_path: str | Path,
    output_dir: str | Path,
    format: str = "vrm",
    base_mesh: str | Path | None = None,
    validate: bool = True,
) -> Path:
    """
    Build a character from a spec file.

    This is the primary entry point. Give it a YAML spec and
    an output directory, and it forges a character.

    Args:
        spec_path: Path to the YAML spec file.
        output_dir: Directory for output files.
        format: Export format ("vrm" or "glb").
        base_mesh: Override base mesh path.
        validate: Run validation before building.

    Returns:
        Path to the exported file.

    Raises:
        SpecValidationError: If the spec fails validation.
        BuildError: If the build pipeline fails.
        ExportError: If the export fails.
    """
    spec_path = Path(spec_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse spec
    logger.info(f"📖 Parsing spec: {spec_path}")
    spec = Spec.from_yaml(spec_path)

    # 2. Validate spec
    if validate:
        logger.info("🔍 Validating spec...")
        errors = validate_spec(spec.character)
        if errors:
            for err in errors:
                logger.error(f"  ✗ {err}")
            raise SpecValidationError(
                f"Spec validation failed with {len(errors)} errors: "
                + "; ".join(str(e) for e in errors[:5])
            )
        logger.info("✓ Spec valid")

    # 3. Resolve output path
    char = spec.character
    safe_name = char.name.replace(" ", "_").lower()
    output_file = output_dir / f"{safe_name}.{format}"

    logger.info(f"🔨 Building: {char.name}")
    logger.info(f"   Body: {char.body.build}, {char.body.height_cm}cm")
    logger.info(f"   Skin: {char.body.skin.base_hex}")
    logger.info(f"   Output: {output_file}")

    # 4. Resolve through forges
    logger.info("🔥 Resolving through forges...")
    forge_config = _resolve_forges(char)

    # 5. Build via Blender bridge
    from hamr.blender_bridge.runner import run_blender_script

    # Prepare spec as JSON for the Blender script
    spec_dict = spec.to_dict()
    # Inject forge-resolved config so Blender script has concrete parameters
    spec_dict["forge_config"] = forge_config
    spec_json = json.dumps(spec_dict)
    spec_temp = output_dir / f".hamr_{safe_name}_spec.json"
    spec_temp.write_text(spec_json)

    # Find the build script
    build_script = Path(__file__).parent / "scripts" / "build_avatar.py"

    if not build_script.exists():
        raise BuildError(
            f"Build script not found: {build_script}\n"
            "The Blender-side build pipeline is not yet implemented. "
            "Phase 2 delivers the Python orchestration; Phase 3 will "
            "implement the Blender-side build script."
        )

    # Run Blender
    result = run_blender_script(
        script_path=build_script,
        script_args=[
            "--spec", str(spec_temp),
            "--output", str(output_file),
        ] + (["--base", str(base_mesh)] if base_mesh else [])
          + (["--force-over-budget"] if force_over_budget else []),
        env={"HAMR_SPEC_PATH": str(spec_temp)},
    )

    if not result.success:
        raise BuildError(
            f"Blender build failed (exit {result.exit_code}): {result.stderr[:500]}"
        )

    # 5. Verify output
    if not output_file.exists():
        raise ExportError(f"Output file not created: {output_file}")

    # 6. Clean up temp files
    spec_temp.unlink(missing_ok=True)
    from hamr.blender_bridge.scene import clean_blend_backups
    clean_blend_backups(str(output_dir))

    logger.info(f"✓ Character built: {output_file}")
    return output_file


def validate_only(spec_path: str | Path) -> list[str]:
    """
    Validate a spec without building.

    Returns a list of error messages (empty if valid).
    """
    spec = Spec.from_yaml(spec_path)
    return validate_spec(spec.character)


def inspect(path: str | Path, targets: list[str] | None = None) -> dict[str, Any]:
    """
    Inspect a VRM/GLB file for compliance.

    Args:
        path: Path to the VRM/GLB file.
        targets: Compliance targets (e.g., ["VRCHAT"]).

    Returns:
        Dict with compliance info.
    """
    path = Path(path)
    if not path.exists():
        raise HamrError(f"File not found: {path}")

    # Basic file info
    result: dict[str, Any] = {
        "path": str(path),
        "size_mb": path.stat().st_size / (1024 * 1024),
        "exists": True,
        "targets": targets or [],
        "checks": [],
    }

    # Extended inspection requires the gate module (Phase 3)
    logger.info(f"Inspection for {path}: {result['size_mb']:.1f} MB")
    return result