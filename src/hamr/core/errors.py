"""
Hamr Error Types

All errors inherit from HamrError.
The forge does not silently fail.
"""

from __future__ import annotations


class HamrError(Exception):
    """Base error for all Hamr operations."""

    pass


class SpecValidationError(HamrError):
    """Spec failed validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        base = super().__str__()
        if self.errors:
            detail = "\n  - ".join(self.errors)
            return f"{base}\n  - {detail}"
        return base


class BuildError(HamrError):
    """Build pipeline failed."""

    def __init__(
        self, message: str, stage: str | None = None, details: str | None = None
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        if self.stage:
            return f"[{self.stage}] {base}"
        return base


class ExportError(HamrError):
    """VRM/GLB export failed."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.details = details


class AssetNotFoundError(HamrError):
    """Required base mesh or texture not found."""

    def __init__(self, message: str, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path