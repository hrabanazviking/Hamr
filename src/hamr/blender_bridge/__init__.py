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
]