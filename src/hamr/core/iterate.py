"""
Iterate — Agent-driven refinement loop.

Phase 1: Placeholder.
"""

from __future__ import annotations

from pathlib import Path
from hamr.core.spec import Spec


def iterate(
    spec_path: str | Path,
    focus: str | None = None,
    rounds: int = 5,
) -> dict:
    """
    Agent-driven refinement: build, evaluate, adjust spec, rebuild.

    Phase 1: Placeholder. Iteration loop will be implemented.
    """
    spec = Spec.from_yaml(spec_path)

    return {
        "status": "placeholder",
        "name": spec.character.name,
        "focus": focus,
        "rounds": rounds,
        "message": "Iterate not yet implemented.",
    }