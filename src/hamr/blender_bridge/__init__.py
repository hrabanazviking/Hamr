"""
Blender Bridge — Headless Blender subprocess bridge for Hamr.

Run inside Blender via ``--python``, or orchestrate from outside
via runner.py. The bridge never opens a GUI.
"""

from hamr.blender_bridge.runner import (
    BlenderResult,
    run_blender_script,
    run_inline_script,
)
from hamr.blender_bridge.compat import (
    BlenderVersion,
    BlenderCompatResult,
    MINIMUM_BLENDER,
    SUPPORTED_BLENDER_VERSIONS,
    check_blender_available,
    get_blender_version,
    check_blender_compat,
    meets_version,
    get_blender_info,
    format_compat_report,
    verify_addon_compatibility,
)
from hamr.blender_bridge.e2e import (
    E2EBuildResult,
    E2EBuildConfig,
    E2E_TEST_SPECS,
    create_e2e_config,
    validate_e2e_config,
    stage_order,
    simulate_build,
    generate_build_script,
    estimate_build_stats,
    execute_blender_build,
)

__all__ = [
    "BlenderResult",
    "run_blender_script",
    "run_inline_script",
    "BlenderVersion",
    "BlenderCompatResult",
    "MINIMUM_BLENDER",
    "SUPPORTED_BLENDER_VERSIONS",
    "check_blender_available",
    "get_blender_version",
    "check_blender_compat",
    "meets_version",
    "get_blender_info",
    "format_compat_report",
    "verify_addon_compatibility",
    "E2EBuildResult",
    "E2EBuildConfig",
    "E2E_TEST_SPECS",
    "create_e2e_config",
    "validate_e2e_config",
    "stage_order",
    "simulate_build",
    "generate_build_script",
    "estimate_build_stats",
    "execute_blender_build",
]