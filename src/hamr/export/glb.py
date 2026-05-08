"""
GLB Export — Binary glTF export for intermediate format.

GLB is the container format for VRM. Useful for debugging
and for pipelines that don't need VRM metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("hamr.export.glb")

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None
    BLENDER_AVAILABLE = False


def export_glb(
    output_path: str | Path,
    selected: bool = False,
) -> bool:
    """
    Export scene as GLB (binary glTF 2.0).

    Args:
        output_path: Path for the output .glb file.
        selected: Only export selected objects.

    Returns:
        True if export succeeded.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available — must run inside Blender")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        bpy.ops.export_scene.gltf(
            filepath=str(output_path),
            export_format="GLB",
            use_selection=selected,
        )
        logger.info(f"GLB exported: {output_path}")
        return True
    except Exception as e:
        logger.error(f"GLB export failed: {e}")
        return False