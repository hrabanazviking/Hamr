"""
Inspect — VRM/GLB compliance inspection.

Phase 1: Placeholder.
"""

from __future__ import annotations

from pathlib import Path


def inspect(path: str | Path, targets: list[str] | None = None) -> dict:
    """
    Inspect a VRM/GLB file for compliance.

    Phase 1: Placeholder. Full inspection will be implemented.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return {
        "status": "placeholder",
        "path": str(path),
        "targets": targets or ["VRCHAT"],
        "message": "Inspect not yet implemented.",
    }