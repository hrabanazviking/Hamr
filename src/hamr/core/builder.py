"""
Builder — The forge pipeline. Spec → Character → VRM.

Phase 1: Placeholder. The forge will be built.
"""

from __future__ import annotations

from pathlib import Path
from hamr.core.spec import Spec


def build(
    spec_path: str | Path,
    output_dir: str | Path = "output",
    format: str = "vrm1",
) -> dict:
    """
    Build a character from a spec file.

    Phase 1: Spec parsing and validation only.
    The forge pipeline will be implemented module by module.
    """
    spec = Spec.from_yaml(spec_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "status": "validated",
        "name": spec.character.name,
        "spec_path": str(spec_path),
        "output_dir": str(output_dir),
        "format": format,
        "message": "Forge pipeline not yet implemented. Spec validated successfully.",
    }