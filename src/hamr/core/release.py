"""
Release artifact management — wheels, checksums, manifest generation.

Pure-Python module for computing release artifact hashes, building
release bundles, and generating SHA256SUMS/MD5SUMS files for distribution.
No Blender (bpy) imports.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ArtifactInfo:
    """Metadata for a single release artifact (wheel, sdist, or binary)."""

    filename: str
    path: Path
    size_bytes: int
    sha256: str
    md5: str
    artifact_type: str  # "wheel", "sdist", "binary"


@dataclass
class ReleaseBundle:
    """A full release bundle containing all artifacts for a version."""

    version: str
    artifacts: list[ArtifactInfo]
    created_at: str  # ISO format
    platform: str = "linux-arm64"
    python_version: str = "3.11"


# ---------------------------------------------------------------------------
# Hash utilities
# ---------------------------------------------------------------------------

def compute_file_hash(path: Path, algorithm: str = "sha256") -> str:
    """Compute a cryptographic hash of a file's contents.

    Args:
        path: Path to the file to hash.
        algorithm: Hash algorithm name (e.g. "sha256", "md5").

    Returns:
        Hex-encoded digest string.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If *algorithm* is not supported.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    hasher = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65_536)  # 64 KiB chunks
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_file_hashes(path: Path) -> dict[str, str]:
    """Compute SHA-256 and MD5 hashes of a file.

    Args:
        path: Path to the file to hash.

    Returns:
        Dictionary with ``"sha256"`` and ``"md5"`` keys.
    """
    return {
        "sha256": compute_file_hash(path, "sha256"),
        "md5": compute_file_hash(path, "md5"),
    }


# ---------------------------------------------------------------------------
# Artifact discovery
# ---------------------------------------------------------------------------

def _classify_artifact(filename: str) -> str:
    """Determine the artifact type from its filename extension."""
    if filename.endswith(".whl"):
        return "wheel"
    elif filename.endswith(".tar.gz") or filename.endswith(".zip"):
        return "sdist"
    else:
        return "binary"


def create_artifact_info(path: Path) -> ArtifactInfo:
    """Build an :class:`ArtifactInfo` from a file on disk.

    Args:
        path: Path to the artifact file.

    Returns:
        Fully populated :class:`ArtifactInfo`.
    """
    hashes = compute_file_hashes(path)
    return ArtifactInfo(
        filename=path.name,
        path=path,
        size_bytes=path.stat().st_size,
        sha256=hashes["sha256"],
        md5=hashes["md5"],
        artifact_type=_classify_artifact(path.name),
    )


def find_artifacts(dist_dir: Path = Path("dist")) -> list[ArtifactInfo]:
    """Scan a dist directory for built artifacts (.whl and .tar.gz).

    Args:
        dist_dir: Directory containing build outputs.

    Returns:
        List of :class:`ArtifactInfo` for each discovered artifact, sorted
        by filename.
    """
    dist_dir = Path(dist_dir)
    if not dist_dir.is_dir():
        return []

    extensions = (".whl", ".tar.gz", ".zip")
    artifacts: list[ArtifactInfo] = []
    for child in sorted(dist_dir.iterdir()):
        if child.is_file() and any(child.name.endswith(ext) for ext in extensions):
            artifacts.append(create_artifact_info(child))
    return artifacts


# ---------------------------------------------------------------------------
# Checksum generation
# ---------------------------------------------------------------------------

def generate_checksums(artifacts: list[ArtifactInfo]) -> str:
    """Generate a SHA256SUMS-format string from a list of artifacts.

    Each line contains the hex-encoded SHA-256 digest followed by two
    spaces and the filename, matching the format used by ``sha256sum``.

    Args:
        artifacts: List of :class:`ArtifactInfo` objects.

    Returns:
        Multiline string in SHA256SUMS format.
    """
    lines: list[str] = []
    for art in artifacts:
        lines.append(f"{art.sha256}  {art.filename}")
    return "\n".join(lines)


def write_checksums(artifacts: list[ArtifactInfo], output_dir: Path) -> Path:
    """Write SHA256SUMS and MD5SUMS files to *output_dir*.

    Args:
        artifacts: List of :class:`ArtifactInfo` objects.
        output_dir: Directory to write checksum files into.

    Returns:
        The *output_dir* path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # SHA256SUMS
    sha_lines = [f"{art.sha256}  {art.filename}" for art in artifacts]
    (output_dir / "SHA256SUMS").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    # MD5SUMS
    md5_lines = [f"{art.md5}  {art.filename}" for art in artifacts]
    (output_dir / "MD5SUMS").write_text("\n".join(md5_lines) + "\n", encoding="utf-8")

    return output_dir


# ---------------------------------------------------------------------------
# Release bundle
# ---------------------------------------------------------------------------

def create_release_bundle(
    version: str,
    dist_dir: Path = Path("dist"),
    platform: str = "linux-arm64",
    python_version: str = "3.11",
) -> ReleaseBundle:
    """Create a :class:`ReleaseBundle` from artifacts in a dist directory.

    Args:
        version: Version string (e.g. ``"0.7.0"``).
        dist_dir: Directory containing build outputs.
        platform: Target platform identifier.
        python_version: Python version string.

    Returns:
        Fully populated :class:`ReleaseBundle`.
    """
    artifacts = find_artifacts(dist_dir)
    return ReleaseBundle(
        version=version,
        artifacts=artifacts,
        created_at=datetime.now(timezone.utc).isoformat(),
        platform=platform,
        python_version=python_version,
    )


def validate_release_bundle(bundle: ReleaseBundle) -> list[str]:
    """Validate a :class:`ReleaseBundle` for completeness and consistency.

    Args:
        bundle: The bundle to validate.

    Returns:
        List of issue descriptions. An empty list means the bundle is valid.
    """
    issues: list[str] = []

    # Version must be non-empty
    if not bundle.version.strip():
        issues.append("Version string is empty")

    # Must have at least one artifact
    if not bundle.artifacts:
        issues.append("Release bundle contains no artifacts")

    # Each artifact must have a real file
    for art in bundle.artifacts:
        if not art.path.exists():
            issues.append(f"Artifact file missing: {art.filename} at {art.path}")

        # Verify hashes match the file contents
        if art.path.exists():
            actual_sha = compute_file_hash(art.path, "sha256")
            if actual_sha != art.sha256:
                issues.append(
                    f"SHA-256 mismatch for {art.filename}: "
                    f"expected {art.sha256}, got {actual_sha}"
                )
            actual_md5 = compute_file_hash(art.path, "md5")
            if actual_md5 != art.md5:
                issues.append(
                    f"MD5 mismatch for {art.filename}: "
                    f"expected {art.md5}, got {actual_md5}"
                )

        # Size must be positive
        if art.size_bytes <= 0:
            issues.append(f"Artifact {art.filename} has invalid size: {art.size_bytes}")

    # Artifact types should include at least one wheel and one sdist
    types = {art.artifact_type for art in bundle.artifacts}
    if "wheel" not in types and bundle.artifacts:
        issues.append("Release bundle is missing a wheel artifact")
    if "sdist" not in types and bundle.artifacts:
        issues.append("Release bundle is missing an sdist artifact")

    # created_at must parse as ISO format
    try:
        datetime.fromisoformat(bundle.created_at)
    except (ValueError, TypeError):
        issues.append(f"Invalid ISO timestamp: {bundle.created_at!r}")

    return issues


def generate_release_manifest(bundle: ReleaseBundle) -> str:
    """Generate a human-readable release manifest.

    Args:
        bundle: The release bundle to describe.

    Returns:
        Formatted manifest text suitable for printing or saving.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"Hamr Release Manifest — v{bundle.version}")
    lines.append("=" * 60)
    lines.append(f"Created:    {bundle.created_at}")
    lines.append(f"Platform:   {bundle.platform}")
    lines.append(f"Python:     {bundle.python_version}")
    lines.append(f"Artifacts:  {len(bundle.artifacts)}")
    lines.append("-" * 60)

    total_size = 0
    for art in bundle.artifacts:
        size_kb = art.size_bytes / 1024
        total_size += art.size_bytes
        lines.append(
            f"  [{art.artifact_type:>6s}] {art.filename}  "
            f"({size_kb:.1f} KB)  sha256:{art.sha256[:16]}…"
        )

    lines.append("-" * 60)
    total_kb = total_size / 1024
    lines.append(f"Total size: {total_kb:.1f} KB")

    # Validation status
    issues = validate_release_bundle(bundle)
    if issues:
        lines.append("")
        lines.append("⚠  Issues detected:")
        for issue in issues:
            lines.append(f"  - {issue}")
    else:
        lines.append("✓  Bundle validated — no issues detected")

    lines.append("=" * 60)
    return "\n".join(lines)