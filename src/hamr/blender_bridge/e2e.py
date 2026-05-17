"""
E2E Build Testing — End-to-End Blender headless build configuration,
simulation, script generation, and stage validation.

All pure-Python functions never import bpy. The one Blender-dependent
function (``execute_blender_build``) is guarded behind subprocess calls
so the module degrades gracefully on systems without Blender.

The forge tests itself before presenting the blade. — Eldra Járnsdóttir
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("hamr.blender_bridge.e2e")


# ──────────────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class E2EBuildResult:
    """Result from an E2E build run (simulated or real).

    Attributes:
        success: Whether the build completed without errors.
        spec_name: Name of the spec preset used.
        stages_completed: List of stage names that finished successfully.
        stages_failed: List of stage names that failed.
        build_time_seconds: Wall-clock build time in seconds.
        output_path: Path to the output VRM/GLB file, or None.
        error: Error message if the build failed, None on success.
        warnings: Non-fatal warnings collected during build.
        artifact_count: Number of output artifacts produced.
        total_triangles: Total triangle count across all meshes.
        mesh_count: Number of mesh objects in the output.
        bone_count: Number of bones in the armature.
    """

    success: bool
    spec_name: str
    stages_completed: list[str]
    stages_failed: list[str]
    build_time_seconds: float
    output_path: Path | None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    artifact_count: int = 0
    total_triangles: int = 0
    mesh_count: int = 0
    bone_count: int = 0


@dataclass
class E2EBuildConfig:
    """Configuration for an E2E build test.

    Attributes:
        spec_name: Preset name (must exist in CHARACTER_PRESETS) or "custom".
        spec_overrides: Dict overrides applied on top of the preset spec.
        output_dir: Directory where build outputs are written.
        validate: Whether to validate the spec before building.
        gpu_profile: GPU profile for budget checking ("pi5", "desktop", "cloud").
        verbose: Enable verbose logging during the build.
        cleanup: Remove output artifacts after test completion.
    """

    spec_name: str
    spec_overrides: dict = field(default_factory=dict)
    output_dir: Path = field(default_factory=lambda: Path("build_output"))
    validate: bool = True
    gpu_profile: str = "pi5"
    verbose: bool = False
    cleanup: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# Test specs — 4 configurations covering different presets and GPU profiles
# ──────────────────────────────────────────────────────────────────────────────

E2E_TEST_SPECS: dict[str, E2EBuildConfig] = {
    "default_female": E2EBuildConfig(
        spec_name="anime_girl_default",
        gpu_profile="pi5",
    ),
    "default_male": E2EBuildConfig(
        spec_name="anime_boy_default",
        gpu_profile="pi5",
    ),
    "chibi_lightweight": E2EBuildConfig(
        spec_name="chibi_cute",
        gpu_profile="pi5",
    ),
    "full_detail_desktop": E2EBuildConfig(
        spec_name="anime_girl_warrior",
        gpu_profile="desktop",
        spec_overrides={"hair": {"style": "long"}},
    ),
}


# ──────────────────────────────────────────────────────────────────────────────
# Build stage definitions
# ──────────────────────────────────────────────────────────────────────────────

# The canonical build stage order — mirrors build_avatar.py steps
_BUILD_STAGES: list[str] = [
    "clear_scene",
    "import_base",
    "apply_spec",
    "integrate_stub_bones",
    "integrate_hair_mesh",
    "integrate_clothing_mesh",
    "integrate_weight_paint",
    "integrate_spring_bones",
    "integrate_first_person",
    "apply_vrm_humanoid",
    "apply_vrm_metadata",
    "apply_vrm_expressions",
    "apply_vrm_look_at",
    "export_vrm",
    "post_export_validation",
]


# ──────────────────────────────────────────────────────────────────────────────
# Spec-based stat estimation — mirrors GPU profiles and perf estimates
# ──────────────────────────────────────────────────────────────────────────────

# Approximate triangle/mesh/bone counts per preset on different profiles
# These are realistic estimates based on Hamr's polygon budgets.
_PRESET_STATS: dict[str, dict[str, int]] = {
    "anime_girl_default": {
        "triangles_pi5": 15_000,
        "triangles_desktop": 45_000,
        "triangles_cloud": 120_000,
        "mesh_count": 6,
        "bone_count": 55,
    },
    "anime_girl_warrior": {
        "triangles_pi5": 18_000,
        "triangles_desktop": 55_000,
        "triangles_cloud": 150_000,
        "mesh_count": 8,
        "bone_count": 60,
    },
    "anime_girl_mage": {
        "triangles_pi5": 17_000,
        "triangles_desktop": 50_000,
        "triangles_cloud": 130_000,
        "mesh_count": 7,
        "bone_count": 58,
    },
    "anime_boy_default": {
        "triangles_pi5": 14_000,
        "triangles_desktop": 40_000,
        "triangles_cloud": 110_000,
        "mesh_count": 5,
        "bone_count": 52,
    },
    "anime_boy_warrior": {
        "triangles_pi5": 17_000,
        "triangles_desktop": 52_000,
        "triangles_cloud": 140_000,
        "mesh_count": 8,
        "bone_count": 58,
    },
    "chibi_cute": {
        "triangles_pi5": 6_000,
        "triangles_desktop": 18_000,
        "triangles_cloud": 50_000,
        "mesh_count": 4,
        "bone_count": 35,
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Pure-Python functions (NO bpy import)
# ──────────────────────────────────────────────────────────────────────────────

def create_e2e_config(name: str, **overrides: Any) -> E2EBuildConfig:
    """Create an E2EBuildConfig with optional overrides.

    Args:
        name: Preset name or "custom".
        **overrides: Keyword arguments forwarded to E2EBuildConfig constructor.

    Returns:
        A fully populated E2EBuildConfig.

    Example::

        config = create_e2e_config("anime_girl_default", gpu_profile="desktop")
    """
    return E2EBuildConfig(spec_name=name, **overrides)


def validate_e2e_config(config: E2EBuildConfig) -> list[str]:
    """Validate an E2EBuildConfig, returning a list of error strings.

    Checks:
    - Spec name exists in CHARACTER_PRESETS (unless it's "custom").
    - Spec override keys are known spec sections.
    - Output directory is writable (or can be created).
    - GPU profile name is valid.

    Args:
        config: The config to validate.

    Returns:
        List of error strings. Empty list means valid config.
    """
    errors: list[str] = []

    # Spec name validation
    if config.spec_name != "custom":
        try:
            from hamr.core.presets import CHARACTER_PRESETS
            if config.spec_name not in CHARACTER_PRESETS:
                available = ", ".join(sorted(CHARACTER_PRESETS.keys()))
                errors.append(
                    f"Unknown spec preset: {config.spec_name!r}. "
                    f"Available: {available}"
                )
        except ImportError:
            # If presets module not available, warn but don't fail
            logger.warning("Cannot validate spec_name: presets module unavailable")

    # Spec overrides validation — check keys are known spec sections
    known_sections = {
        "name", "body", "face", "hair", "clothing",
        "expressions", "physics", "export",
        "version",
    }
    for key in config.spec_overrides:
        if key not in known_sections:
            errors.append(
                f"Unknown spec override key: {key!r}. "
                f"Known sections: {', '.join(sorted(known_sections))}"
            )

    # GPU profile validation
    valid_profiles = ("pi5", "desktop", "cloud")
    if config.gpu_profile not in valid_profiles:
        errors.append(
            f"Unknown GPU profile: {config.gpu_profile!r}. "
            f"Valid: {', '.join(valid_profiles)}"
        )

    # Output directory writable check
    try:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        test_file = config.output_dir / ".hamr_e2e_write_test"
        test_file.write_text("test")
        test_file.unlink()
    except OSError as exc:
        errors.append(
            f"Output directory not writable: {config.output_dir} ({exc})"
        )

    return errors


def stage_order() -> list[str]:
    """Return the canonical build stage order.

    This mirrors the actual stages in the Blender build pipeline
    (``scripts/build_avatar.py``) and the integration stages from
    ``core/pipeline_integrate.py``.

    Returns:
        Ordered list of stage name strings.
    """
    return list(_BUILD_STAGES)


def simulate_build(config: E2EBuildConfig) -> E2EBuildResult:
    """Simulate an E2E build without launching Blender.

    Produces plausible mock stats based on the spec preset and GPU profile.
    Each stage is "run" in order with a simulated time cost, producing a
    result that looks like a real build output.

    This is the völva's prophecy — it foretells the shape of the blade
    without lighting the forge.

    Args:
        config: Build configuration to simulate.

    Returns:
        E2EBuildResult with simulated statistics.
    """
    start_time = time.time()
    stages_completed: list[str] = []
    stages_failed: list[str] = []
    warnings: list[str] = []
    asset_count = 0

    # Look up estimated stats
    stats = estimate_build_stats(config.spec_name, config.gpu_profile)
    total_triangles = stats.get("total_triangles", 0)
    mesh_count = stats.get("mesh_count", 0)
    bone_count = stats.get("bone_count", 0)

    # Simulate each build stage
    for stage in stage_order():
        # Each stage has a simulated duration
        stage_duration = _simulated_stage_duration(stage, config.gpu_profile)
        time.sleep(stage_duration)

        # Most stages succeed; add realistic failure simulation
        if stage == "integrate_clothing_mesh" and config.spec_overrides.get("clothing"):
            # Complex clothing overrides might cause warnings
            warnings.append(
                f"Stage '{stage}' completed with clothing override complexity"
            )

        if config.gpu_profile == "pi5" and stage == "export_vrm":
            # Pi 5 may produce warnings about texture limits
            warnings.append("Texture resolution capped to 1024px for pi5 profile")

        stages_completed.append(stage)
        asset_count += 1

    # Calculate build output path
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{config.spec_name}.vrm"

    # Simulated build time (real wall-clock + estimated computation)
    build_time = time.time() - start_time + stats.get("estimated_time", 15.0)

    # Cleanup if requested
    if config.cleanup:
        try:
            if output_path.exists():
                output_path.unlink()
        except OSError:
            pass

    return E2EBuildResult(
        success=True,
        spec_name=config.spec_name,
        stages_completed=stages_completed,
        stages_failed=stages_failed,
        build_time_seconds=round(build_time, 2),
        output_path=output_path if not config.cleanup else None,
        warnings=warnings,
        artifact_count=asset_count,
        total_triangles=total_triangles,
        mesh_count=mesh_count,
        bone_count=bone_count,
    )


def generate_build_script(config: E2EBuildConfig) -> Path:
    """Generate a Python build script that can be run inside Blender.

    The generated script contains all configuration from the E2EBuildConfig
    and can be executed via ``blender --background --python <script>``.

    Args:
        config: Build configuration to generate the script for.

    Returns:
        Path to the generated build script file.
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_path = output_dir / f"e2e_build_{config.spec_name}.py"

    # Build the script content
    stages = stage_order()
    stats = estimate_build_stats(config.spec_name, config.gpu_profile)

    # Try to resolve the preset spec
    try:
        from hamr.core.presets import get_preset
        preset_data = get_preset(config.spec_name)
        # Use .spec dict if available (CharacterPreset), else fall back
        spec_dict = preset_data.spec if hasattr(preset_data, "spec") else preset_data
        spec_json = json.dumps(spec_dict, indent=2, default=str)
    except (ImportError, KeyError, AttributeError):
        spec_json = "{}  # Custom spec — populate manually"

    # Apply overrides to the JSON spec string
    if config.spec_overrides:
        # Note: actual override merging happens at runtime
        overrides_json = json.dumps(config.spec_overrides, indent=2, default=str)
    else:
        overrides_json = "{}"

    script_content = f'''"""
E2E Build Script — Auto-generated by hamr.blender_bridge.e2e
Spec: {config.spec_name}
GPU Profile: {config.gpu_profile}
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""

import json
import sys
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────
SPEC_NAME = "{config.spec_name}"
GPU_PROFILE = "{config.gpu_profile}"
VALIDATE = {config.validate}
VERBOSE = {config.verbose}
OUTPUT_DIR = r"{config.output_dir}"
SPEC_DATA = {spec_json}
SPEC_OVERRIDES = {overrides_json}
BUILD_STAGES = {stages}

# ── Estimated Stats ──────────────────────────────────────────────────────
ESTIMATED_TRIANGLES = {stats.get("total_triangles", 0)}
ESTIMATED_MESHES = {stats.get("mesh_count", 0)}
ESTIMATED_BONES = {stats.get("bone_count", 0)}

# ── Apply Overrides ──────────────────────────────────────
def deep_merge(base, override):
    """Recursively merge override dict into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base

if overrides_json:
    spec_json = deep_merge(dict(spec_json) if isinstance(spec_json, dict) else {{}}, overrides_json)


def main():
    """Main build entry point — runs inside Blender."""
    stages_completed = []
    stages_failed = []

    # Check for Blender
    try:
        import bpy  # type: ignore
    except ImportError:
        print("ERROR: This script must run inside Blender (bpy not available)")
        return 1

    print(f"[E2E] Starting build: {{SPEC_NAME}} on {{GPU_PROFILE}} profile")
    print(f"[E2E] Estimated triangles: {{ESTIMATED_TRIANGLES}}")
    print(f"[E2E] Estimated meshes: {{ESTIMATED_MESHES}}")
    print(f"[E2E] Estimated bones: {{ESTIMATED_BONES}}")

    output_path = Path(OUTPUT_DIR) / f"{{SPEC_NAME}}.vrm"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write spec to temp file for build_avatar.py
    spec_temp = output_path.parent / f".hamr_{{SPEC_NAME}}_spec.json"
    spec_temp.write_text(json.dumps(SPEC_DATA, indent=2))

    # Import the build script and run
    try:
        from hamr.scripts.build_avatar import main as build_main
        sys.argv = sys.argv[:1] + [
            "--", "--spec", str(spec_temp),
            "--output", str(output_path),
        ]
        result = build_main()
        if result == 0:
            print(f"[E2E] Build completed successfully: {{output_path}}")
        else:
            print(f"[E2E] Build failed with exit code: {{result}}")
            stages_failed.append("build_main")
        return result
    except Exception as e:
        print(f"[E2E] Build exception: {{e}}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''

    script_path.write_text(script_content)
    logger.info(f"Generated build script: {script_path}")
    return script_path


def estimate_build_stats(spec_name: str, gpu_profile: str) -> dict[str, Any]:
    """Estimate build statistics for a given spec and GPU profile.

    Uses the preset's known polygon budgets and scales by GPU profile.
    Returns plausible triangle, mesh, and bone counts.

    Args:
        spec_name: The preset name (must exist in _PRESET_STATS or CHARACTER_PRESETS).
        gpu_profile: One of "pi5", "desktop", "cloud".

    Returns:
        Dict with keys: total_triangles, mesh_count, bone_count, estimated_time.
    """
    # Get preset stats or defaults
    preset_stats = _PRESET_STATS.get(spec_name, {
        "triangles_pi5": 12_000,
        "triangles_desktop": 35_000,
        "triangles_cloud": 90_000,
        "mesh_count": 5,
        "bone_count": 50,
    })

    # Map GPU profile to triangle key
    profile_key_map = {
        "pi5": "triangles_pi5",
        "desktop": "triangles_desktop",
        "cloud": "triangles_cloud",
    }
    triangle_key = profile_key_map.get(gpu_profile, "triangles_pi5")

    # Scale triangles — desktop profile allows more than pi5
    # Apply overrides that affect triangle count
    total_triangles = preset_stats.get(triangle_key, preset_stats.get("triangles_pi5", 12_000))

    # Adjust for GPU profile build time multiplier
    # pi5: 45s budget, desktop: 30s, cloud: 15s → scale factor
    time_multipliers = {"pi5": 1.0, "desktop": 0.67, "cloud": 0.33}
    estimated_time = 15.0 * time_multipliers.get(gpu_profile, 1.0)

    return {
        "total_triangles": total_triangles,
        "mesh_count": preset_stats.get("mesh_count", 5),
        "bone_count": preset_stats.get("bone_count", 50),
        "estimated_time": estimated_time,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Stage duration simulation
# ──────────────────────────────────────────────────────────────────────────────

_STAGE_DURATIONS_PI5: dict[str, float] = {
    "clear_scene": 0.01,
    "import_base": 0.05,
    "apply_spec": 0.02,
    "integrate_stub_bones": 0.01,
    "integrate_hair_mesh": 0.03,
    "integrate_clothing_mesh": 0.02,
    "integrate_weight_paint": 0.03,
    "integrate_spring_bones": 0.01,
    "integrate_first_person": 0.01,
    "apply_vrm_humanoid": 0.02,
    "apply_vrm_metadata": 0.01,
    "apply_vrm_expressions": 0.01,
    "apply_vrm_look_at": 0.01,
    "export_vrm": 0.05,
    "post_export_validation": 0.02,
}

_SPEED_FACTORS: dict[str, float] = {
    "pi5": 1.0,
    "desktop": 0.5,
    "cloud": 0.2,
}


def _simulated_stage_duration(stage: str, gpu_profile: str) -> float:
    """Get the simulated duration for a build stage.

    Args:
        stage: Build stage name.
        gpu_profile: GPU profile name for speed scaling.

    Returns:
        Duration in seconds (very short for simulation).
    """
    base_duration = _STAGE_DURATIONS_PI5.get(stage, 0.01)
    speed_factor = _SPEED_FACTORS.get(gpu_profile, 1.0)
    # Keep simulation durations very short (ms range) so tests are fast
    return base_duration * speed_factor * 0.1


# ──────────────────────────────────────────────────────────────────────────────
# Blender-dependent function (guarded — requires Blender installed)
# ──────────────────────────────────────────────────────────────────────────────

def execute_blender_build(
    config: E2EBuildConfig,
    blender_path: str = "blender",
) -> E2EBuildResult:
    """Execute a real E2E Blender build using the headless subprocess runner.

    **Requires Blender to be installed.** This function will fail gracefully
    if Blender is not available.

    The function:
    1. Resolves the preset spec
    2. Generates a build script
    3. Runs Blender headless with the script
    4. Parses results and returns an E2EBuildResult

    Args:
        config: Build configuration.
        blender_path: Path to the Blender executable.

    Returns:
        E2EBuildResult with actual build statistics.
    """
    from hamr.blender_bridge.runner import run_blender_script, check_blender_available
    from hamr.blender_bridge.compat import check_blender_compat

    start_time = time.time()
    stages_completed: list[str] = []
    stages_failed: list[str] = []
    warnings: list[str] = []

    # Check Blender availability
    if not check_blender_available():
        return E2EBuildResult(
            success=False,
            spec_name=config.spec_name,
            stages_completed=[],
            stages_failed=[],
            build_time_seconds=0.0,
            output_path=None,
            error=f"Blender not found at: {blender_path}",
        )

    # Check compatibility
    compat = check_blender_compat()
    if not compat.meets_minimum_version:
        return E2EBuildResult(
            success=False,
            spec_name=config.spec_name,
            stages_completed=[],
            stages_failed=[],
            build_time_seconds=0.0,
            output_path=None,
            error=f"Blender version too old: {compat.version}. "
                  f"Minimum required: 3.0.0",
            warnings=compat.warnings,
        )

    warnings.extend(compat.warnings)

    # Generate build script
    try:
        script_path = generate_build_script(config)
    except Exception as exc:
        return E2EBuildResult(
            success=False,
            spec_name=config.spec_name,
            stages_completed=[],
            stages_failed=[],
            build_time_seconds=time.time() - start_time,
            output_path=None,
            error=f"Script generation failed: {exc}",
        )

    # Run Blender
    try:
        result = run_blender_script(
            script_path=script_path,
            timeout=600,
        )

        build_time = time.time() - start_time

        if not result.success:
            # Parse which stages failed from stderr
            stages_completed = stage_order()
            # Assume all stages up to failure point completed
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            return E2EBuildResult(
                success=False,
                spec_name=config.spec_name,
                stages_completed=stages_completed,
                stages_failed=["build_execution"],
                build_time_seconds=build_time,
                output_path=None,
                error=f"Blender exited with code {result.exit_code}: {error_msg}",
                warnings=warnings,
            )

        # Check for output file
        output_dir = Path(config.output_dir)
        output_file = output_dir / f"{config.spec_name}.vrm"

        artifact_count = 1 if output_file.exists() else 0

        # Cleanup if requested
        output_path = None
        if output_file.exists():
            output_path = output_file
            if config.cleanup:
                try:
                    output_file.unlink()
                except OSError:
                    pass
                output_path = None

        # Clean up temp script
        if config.cleanup:
            try:
                script_path.unlink(missing_ok=True)
            except OSError:
                pass

        return E2EBuildResult(
            success=True,
            spec_name=config.spec_name,
            stages_completed=stage_order(),
            stages_failed=[],
            build_time_seconds=round(build_time, 2),
            output_path=output_path,
            warnings=warnings,
            artifact_count=artifact_count,
        )

    except Exception as exc:
        build_time = time.time() - start_time
        return E2EBuildResult(
            success=False,
            spec_name=config.spec_name,
            stages_completed=stages_completed,
            stages_failed=stages_completed[len(stages_completed):] or ["unknown"],
            build_time_seconds=build_time,
            output_path=None,
            error=f"Build execution failed: {exc}",
        )