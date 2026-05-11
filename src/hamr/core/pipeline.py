"""
Pipeline — The full forge pipeline orchestrator.

Spec → Validate → JSON → Blender → VRM.

The pipeline ties every forge together. It never opens a GUI.
It speaks to Blender through the command line, like a völva speaking to the beyond.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hamr.core.spec import Spec
from hamr.core.models import CharacterSpec, ExportSpec
from hamr.core.validate import validate_spec
from hamr.core.errors import HamrError, SpecValidationError, BuildError, ExportError
from hamr.blender_bridge.runner import run_blender_script, run_inline_script, BlenderResult, check_blender_available, get_blender_version

logger = logging.getLogger("hamr.pipeline")


@dataclass
class PipelineResult:
    """Result from a full pipeline run."""

    success: bool
    spec_path: Path
    output_path: Path | None = None
    elapsed: float = 0.0
    blender_result: BlenderResult | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def output_size_mb(self) -> float | None:
        if self.output_path and self.output_path.exists():
            return self.output_path.stat().st_size / (1024 * 1024)
        return None

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        size = f"{self.output_size_mb:.1f}MB" if self.output_size_mb else "?"
        return f"PipelineResult({status} {size} {self.elapsed:.1f}s)"


class BuildPipeline:
    """
    The full forge pipeline orchestrator.

    Usage:
        pipeline = BuildPipeline()
        result = pipeline.build("character.yaml", output_dir="output/")
        if result.success:
            print(f"Built: {result.output_path}")
    """

    def __init__(
        self,
        blender_path: str | None = None,
        blender_timeout: int = 600,
        blender_args: list[str] | None = None,
        keep_temp: bool = False,
    ) -> None:
        """
        Initialize the build pipeline.

        Args:
            blender_path: Override path to Blender executable.
            blender_timeout: Maximum seconds for Blender subprocess.
            blender_args: Additional Blender CLI arguments.
            keep_temp: Keep temporary files after build (for debugging).
        """
        self.blender_path = blender_path
        self.blender_timeout = blender_timeout
        self.blender_args = blender_args or []
        self.keep_temp = keep_temp

    def build(
        self,
        spec_path: str | Path,
        output_dir: str | Path,
        format: str = "vrm",
        base_mesh: str | Path | None = None,
        validate: bool = True,
        max_tex: int = 0,
        force_over_budget: bool = False,
    ) -> PipelineResult:
        """
        Build a character from a spec file through the full pipeline.

        Steps:
            1. Parse and validate spec
            2. Resolve body preset
            3. Serialize to JSON for Blender
            4. Run Blender build script
            5. Verify output
            6. Clean up

        Args:
            spec_path: Path to the YAML spec file.
            output_dir: Directory for output files.
            format: Export format ("vrm" or "glb").
            base_mesh: Override base mesh path.
            validate: Run validation before building.
            max_tex: Maximum texture resolution (0=unlimited).

        Returns:
            PipelineResult with success status, output path, and timing.
        """
        start = time.time()
        spec_path = Path(spec_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 1: Parse spec ────────────────────────────────────────────
        logger.info(f"📖 Parsing spec: {spec_path}")
        result = PipelineResult(success=False, spec_path=spec_path)
        try:
            spec = Spec.from_yaml(spec_path)
        except Exception as e:
            result.errors.append(f"Spec parse error: {e}")
            result.elapsed = time.time() - start
            return result

        char = spec.character
        safe_name = char.name.replace(" ", "_").lower()

        # ── Step 2: Validate ──────────────────────────────────────────────
        if validate:
            logger.info("🔍 Validating spec...")
            errors = validate_spec(char)
            if errors:
                for err in errors:
                    result.errors.append(str(err))
                    logger.error(f"  ✗ {err}")
                result.elapsed = time.time() - start
                return result
            logger.info("✓ Spec valid")

        # ── Step 3: Serialize to JSON ─────────────────────────────────────
        logger.info(f"🔨 Building: {char.name}")
        logger.info(f"   Body: {char.body.build}, {char.body.height_cm}cm")
        logger.info(f"   Skin: {char.body.skin.base_hex}")
        logger.info(f"   Format: {format}")

        spec_dict = spec.to_dict()

        # Add pipeline metadata
        spec_dict["_pipeline"] = {
            "base_type": "mblab" if not base_mesh else "custom",
            "format": format,
            "max_tex": max_tex,
        }

        spec_json = json.dumps(spec_dict, indent=2)
        spec_temp = output_dir / f".hamr_{safe_name}_spec.json"
        spec_temp.write_text(spec_json)
        logger.debug(f"Spec JSON written to: {spec_temp}")

        # ── Step 4: Run Blender ───────────────────────────────────────────
        build_script = Path(__file__).parent.parent / "scripts" / "build_avatar.py"
        if not build_script.exists():
            # Try alternative location (installed package)
            import hamr
            build_script = Path(hamr.__file__).parent / "scripts" / "build_avatar.py"

        if not build_script.exists():
            result.errors.append(
                f"Build script not found: {build_script}\n"
                "The Blender-side build pipeline is required for VRM output."
            )
            result.elapsed = time.time() - start
            return result

        output_file = output_dir / f"{safe_name}.{format}"
        blender_args = []
        if self.blender_path:
            blender_args.extend(["--blender", self.blender_path])

        logger.info(f"⚡ Launching Blender build script...")

        blender_result = run_blender_script(
            script_path=build_script,
            script_args=[
                "--spec", str(spec_temp),
                "--output", str(output_file),
            ] + (
                ["--base", str(base_mesh)] if base_mesh else []
            ) + (
                ["--max-tex", str(max_tex)] if max_tex > 0 else []
            ) + (
                ["--force-over-budget"] if force_over_budget else []
            ),
            blender_args=self.blender_args or None,
            timeout=self.blender_timeout,
        )

        result.blender_result = blender_result

        # ── Step 5: Verify output ─────────────────────────────────────────
        if not blender_result.success:
            result.errors.append(
                f"Blender build failed (exit {blender_result.exit_code}): "
                f"{blender_result.stderr[:500]}"
            )
            if not self.keep_temp:
                spec_temp.unlink(missing_ok=True)
            result.elapsed = time.time() - start
            return result

        if output_file.exists():
            result.output_path = output_file
            size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Character built: {output_file} ({size_mb:.1f} MB)")
        else:
            result.errors.append(f"Output file not created: {output_file}")
            result.elapsed = time.time() - start
            return result

        # ── Step 6: Clean up ──────────────────────────────────────────────
        if not self.keep_temp:
            spec_temp.unlink(missing_ok=True)
            from hamr.blender_bridge.scene import clean_blend_backups
            clean_blend_backups(str(output_dir))

        result.success = True
        result.elapsed = time.time() - start

        logger.info(f"✓ Pipeline complete in {result.elapsed:.1f}s")
        return result

    def validate_only(self, spec_path: str | Path) -> list[str]:
        """Validate a spec without building. Returns list of error messages."""
        try:
            spec = Spec.from_yaml(spec_path)
        except SpecValidationError as e:
            return [str(e)]
        return validate_spec(spec.character)

    def check_environment(self) -> dict[str, Any]:
        """
        Check the build environment for readiness.

        Returns a dict with status of:
            - blender_available: bool
            - blender_version: str | None
            - vrm_addon: bool | None (None = cannot check without Blender)
            - mblab_addon: bool | None
            - build_script: bool
        """
        result: dict[str, Any] = {}

        # Blender availability
        result["blender_available"] = check_blender_available()
        result["blender_version"] = get_blender_version()

        # Build script exists
        build_script = Path(__file__).parent.parent / "scripts" / "build_avatar.py"
        if not build_script.exists():
            import hamr
            build_script = Path(hamr.__file__).parent / "scripts" / "build_avatar.py"
        result["build_script"] = build_script.exists()

        # Check addons by running a quick Blender script
        if result["blender_available"]:
            result.update(self._check_blender_addons())

        return result

    def _check_blender_addons(self) -> dict[str, bool | None]:
        """Check if VRM and MB-Lab addons are installed in Blender."""
        check_script = '''
import bpy
import addon_utils

results = {}

# Check VRM addon
vrm_found = False
for mod in addon_utils.modules():
    if "io_scene_vrm" in mod.__name__:
        vrm_found = True
        break
results["vrm_addon"] = vrm_found

# Check MB-Lab addon
mblab_found = False
for mod in addon_utils.modules():
    if any(k in mod.__name__.lower() for k in ("mblab", "mb-lab", "mb_lab")):
        mblab_found = True
        break
results["mblab_addon"] = mblab_found

# Print results as JSON for parsing
import json
print("HAMR_ADDON_CHECK:" + json.dumps(results))
'''

        result = run_inline_script(check_script, timeout=30)

        addon_status = {"vrm_addon": None, "mblab_addon": None}

        for line in result.stdout.splitlines():
            if "HAMR_ADDON_CHECK:" in line:
                json_str = line.split("HAMR_ADDON_CHECK:", 1)[1]
                try:
                    addon_status = json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                break

        return addon_status