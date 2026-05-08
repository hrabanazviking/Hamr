"""
Blender Bridge — Headless Blender subprocess bridge for Hamr.

Run inside Blender via ``--python``, or orchestrate from outside
via runner.py. The bridge never opens a GUI.
"""

from hamr.blender_bridge.runner import (
    BlenderResult,
    run_blender_script,
    run_inline_script,
    check_blender_available,
    get_blender_version,
)

__all__ = [
    "BlenderResult",
    "run_blender_script",
    "run_inline_script",
    "check_blender_available",
    "get_blender_version",
]