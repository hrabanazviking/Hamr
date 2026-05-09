"""
Tests for hamr.core.release — Release artifact pipeline.

Covers: hash computation, artifact discovery, checksum generation,
release bundles, and manifest formatting.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from hamr.core.release import (
    ArtifactInfo,
    ReleaseBundle,
    compute_file_hash,
    compute_file_hashes,
    create_artifact_info,
    create_release_bundle,
    find_artifacts,
    generate_checksums,
    generate_release_manifest,
    validate_release_bundle,
    write_checksums,
)


# ---------------------------------------------------------------------------
# compute_file_hash
# ---------------------------------------------------------------------------

class TestComputeFileHash:
    """Tests for compute_file_hash."""

    def test_sha256(self, tmp_path: Path) -> None:
        """Compute SHA-256 hash of a temp file."""
        f = tmp_path / "hello.txt"
        content = b"hello world\n"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_file_hash(f) == expected

    def test_md5(self, tmp_path: Path) -> None:
        """Compute MD5 hash of a temp file."""
        f = tmp_path / "hello.txt"
        content = b"hello world\n"
        f.write_bytes(content)
        expected = hashlib.md5(content).hexdigest()
        assert compute_file_hash(f, algorithm="md5") == expected

    def test_missing_file_raises(self) -> None:
        """FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            compute_file_hash(Path("/nonexistent/file.txt"))

    def test_unsupported_algorithm(self, tmp_path: Path) -> None:
        """ValueError for unsupported hash algorithm."""
        f = tmp_path / "data.bin"
        f.write_bytes(b"data")
        with pytest.raises(ValueError):
            compute_file_hash(f, algorithm="rot13")


# ---------------------------------------------------------------------------
# compute_file_hashes
# ---------------------------------------------------------------------------

class TestComputeFileHashes:
    """Tests for compute_file_hashes."""

    def test_returns_both_algorithms(self, tmp_path: Path) -> None:
        """Returns dict with sha256 and md5 keys."""
        f = tmp_path / "data.bin"
        content = b"some test content"
        f.write_bytes(content)
        result = compute_file_hashes(f)
        assert "sha256" in result
        assert "md5" in result
        assert result["sha256"] == hashlib.sha256(content).hexdigest()
        assert result["md5"] == hashlib.md5(content).hexdigest()


# ---------------------------------------------------------------------------
# create_artifact_info
# ---------------------------------------------------------------------------

class TestCreateArtifactInfo:
    """Tests for create_artifact_info."""

    def test_from_wheel_file(self, tmp_path: Path) -> None:
        """Build ArtifactInfo from a .whl file."""
        whl = tmp_path / "hamr-0.7.0-py3-none-any.whl"
        content = b"wheel content here"
        whl.write_bytes(content)
        info = create_artifact_info(whl)
        assert info.filename == "hamr-0.7.0-py3-none-any.whl"
        assert info.path == whl
        assert info.size_bytes == len(content)
        assert info.sha256 == hashlib.sha256(content).hexdigest()
        assert info.md5 == hashlib.md5(content).hexdigest()
        assert info.artifact_type == "wheel"

    def test_from_sdist_file(self, tmp_path: Path) -> None:
        """Build ArtifactInfo from a .tar.gz file."""
        sdist = tmp_path / "hamr-0.7.0.tar.gz"
        content = b"sdist archive data"
        sdist.write_bytes(content)
        info = create_artifact_info(sdist)
        assert info.artifact_type == "sdist"

    def test_from_binary_file(self, tmp_path: Path) -> None:
        """Unknown extension yields 'binary' type."""
        binary = tmp_path / "hamr-addon.bin"
        content = b"addon binary data"
        binary.write_bytes(content)
        info = create_artifact_info(binary)
        assert info.artifact_type == "binary"


# ---------------------------------------------------------------------------
# find_artifacts
# ---------------------------------------------------------------------------

class TestFindArtifacts:
    """Tests for find_artifacts."""

    def test_finds_wheel_and_sdist(self, tmp_path: Path) -> None:
        """Discovers .whl and .tar.gz in a dist directory."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "hamr-0.7.0-py3-none-any.whl").write_bytes(b"w")
        (dist / "hamr-0.7.0.tar.gz").write_bytes(b"s")
        (dist / "notes.txt").write_text("not an artifact")  # should be skipped

        result = find_artifacts(dist)
        assert len(result) == 2
        names = [a.filename for a in result]
        assert "hamr-0.7.0-py3-none-any.whl" in names
        assert "hamr-0.7.0.tar.gz" in names

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Empty dist dir returns empty list."""
        dist = tmp_path / "empty_dist"
        dist.mkdir()
        assert find_artifacts(dist) == []

    def test_nonexistent_dir(self) -> None:
        """Nonexistent directory returns empty list."""
        assert find_artifacts(Path("/nonexistent/dist")) == []

    def test_sorted_output(self, tmp_path: Path) -> None:
        """Artifacts are sorted by filename."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "z-package.tar.gz").write_bytes(b"z")
        (dist / "a-package.whl").write_bytes(b"a")
        result = find_artifacts(dist)
        names = [a.filename for a in result]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# generate_checksums
# ---------------------------------------------------------------------------

class TestGenerateChecksums:
    """Tests for generate_checksums."""

    def test_correct_format(self, tmp_path: Path) -> None:
        """Produces SHA256SUMS-compatible output."""
        f = tmp_path / "test.whl"
        content = b"test wheel"
        f.write_bytes(content)
        info = create_artifact_info(f)
        result = generate_checksums([info])
        sha = hashlib.sha256(content).hexdigest()
        assert result == f"{sha}  test.whl"

    def test_multiple_artifacts(self, tmp_path: Path) -> None:
        """Each artifact gets its own line."""
        f1 = tmp_path / "a.whl"
        f2 = tmp_path / "b.tar.gz"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        info1 = create_artifact_info(f1)
        info2 = create_artifact_info(f2)
        result = generate_checksums([info1, info2])
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0].endswith("a.whl")
        assert lines[1].endswith("b.tar.gz")


# ---------------------------------------------------------------------------
# write_checksums
# ---------------------------------------------------------------------------

class TestWriteChecksums:
    """Tests for write_checksums."""

    def test_creates_sha256_and_md5_files(self, tmp_path: Path) -> None:
        """Writes SHA256SUMS and MD5SUMS files."""
        dist = tmp_path / "dist"
        dist.mkdir()
        whl = dist / "hamr-0.7.0-py3-none-any.whl"
        sdist = dist / "hamr-0.7.0.tar.gz"
        whl_content = b"wheel data"
        sdist_content = b"sdist data"
        whl.write_bytes(whl_content)
        sdist.write_bytes(sdist_content)

        artifacts = find_artifacts(dist)
        output_dir = tmp_path / "output"
        result_path = write_checksums(artifacts, output_dir)

        sha256_file = result_path / "SHA256SUMS"
        md5_file = result_path / "MD5SUMS"
        assert sha256_file.exists()
        assert md5_file.exists()

        sha_text = sha256_file.read_text()
        md5_text = md5_file.read_text()

        # Check SHA-256 format
        sha256_whl = hashlib.sha256(whl_content).hexdigest()
        sha256_sdist = hashlib.sha256(sdist_content).hexdigest()
        assert f"{sha256_whl}  hamr-0.7.0-py3-none-any.whl" in sha_text
        assert f"{sha256_sdist}  hamr-0.7.0.tar.gz" in sha_text

        # Check MD5 format
        md5_whl = hashlib.md5(whl_content).hexdigest()
        md5_sdist = hashlib.md5(sdist_content).hexdigest()
        assert f"{md5_whl}  hamr-0.7.0-py3-none-any.whl" in md5_text
        assert f"{md5_sdist}  hamr-0.7.0.tar.gz" in md5_text


# ---------------------------------------------------------------------------
# create_release_bundle
# ---------------------------------------------------------------------------

class TestCreateReleaseBundle:
    """Tests for create_release_bundle."""

    def test_from_temp_dist(self, tmp_path: Path) -> None:
        """Create a bundle from a temp dist directory."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "hamr-0.7.0-py3-none-any.whl").write_bytes(b"w")
        (dist / "hamr-0.7.0.tar.gz").write_bytes(b"s")

        bundle = create_release_bundle(
            version="0.7.0",
            dist_dir=dist,
            platform="linux-arm64",
            python_version="3.11",
        )
        assert bundle.version == "0.7.0"
        assert len(bundle.artifacts) == 2
        assert bundle.platform == "linux-arm64"
        assert bundle.python_version == "3.11"
        assert bundle.created_at  # ISO timestamp not empty

    def test_empty_dist(self, tmp_path: Path) -> None:
        """Empty dist yields bundle with no artifacts."""
        dist = tmp_path / "dist"
        dist.mkdir()
        bundle = create_release_bundle(version="0.7.0", dist_dir=dist)
        assert bundle.artifacts == []


# ---------------------------------------------------------------------------
# validate_release_bundle
# ---------------------------------------------------------------------------

class TestValidateReleaseBundle:
    """Tests for validate_release_bundle."""

    def _make_valid_bundle(self, tmp_path: Path) -> ReleaseBundle:
        """Helper to create a valid bundle for testing."""
        dist = tmp_path / "dist"
        dist.mkdir()
        whl = dist / "hamr-0.7.0-py3-none-any.whl"
        sdist = dist / "hamr-0.7.0.tar.gz"
        whl.write_bytes(b"wheel content")
        sdist.write_bytes(b"sdist content")
        artifacts = find_artifacts(dist)
        return ReleaseBundle(
            version="0.7.0",
            artifacts=artifacts,
            created_at="2026-05-08T20:00:00+00:00",
            platform="linux-arm64",
            python_version="3.11",
        )

    def test_valid_bundle(self, tmp_path: Path) -> None:
        """Valid bundle returns no issues."""
        bundle = self._make_valid_bundle(tmp_path)
        issues = validate_release_bundle(bundle)
        assert issues == []

    def test_empty_version(self, tmp_path: Path) -> None:
        """Empty version string is flagged."""
        bundle = self._make_valid_bundle(tmp_path)
        bundle.version = "  "
        issues = validate_release_bundle(bundle)
        assert any("Version" in i for i in issues)

    def test_no_artifacts(self) -> None:
        """Bundle with no artifacts is flagged."""
        bundle = ReleaseBundle(
            version="0.7.0",
            artifacts=[],
            created_at="2026-05-08T20:00:00+00:00",
        )
        issues = validate_release_bundle(bundle)
        assert any("no artifacts" in i for i in issues)

    def test_missing_file(self, tmp_path: Path) -> None:
        """Artifact pointing to deleted file is flagged."""
        bundle = self._make_valid_bundle(tmp_path)
        # Delete one artifact's source file
        bundle.artifacts[0].path.unlink()
        issues = validate_release_bundle(bundle)
        assert any("missing" in i.lower() for i in issues)

    def test_invalid_timestamp(self, tmp_path: Path) -> None:
        """Invalid created_at timestamp is flagged."""
        bundle = self._make_valid_bundle(tmp_path)
        bundle.created_at = "not-a-date"
        issues = validate_release_bundle(bundle)
        assert any("timestamp" in i.lower() or "ISO" in i for i in issues)

    def test_missing_wheel_type(self, tmp_path: Path) -> None:
        """Bundle without a wheel is flagged (when artifacts exist)."""
        dist = tmp_path / "dist_only_sdist"
        dist.mkdir()
        sdist = dist / "hamr-0.7.0.tar.gz"
        sdist.write_bytes(b"sdist only")
        artifacts = find_artifacts(dist)
        bundle = ReleaseBundle(
            version="0.7.0",
            artifacts=artifacts,
            created_at="2026-05-08T20:00:00+00:00",
        )
        issues = validate_release_bundle(bundle)
        assert any("wheel" in i.lower() for i in issues)


# ---------------------------------------------------------------------------
# generate_release_manifest
# ---------------------------------------------------------------------------

class TestGenerateReleaseManifest:
    """Tests for generate_release_manifest."""

    def test_produces_readable_output(self, tmp_path: Path) -> None:
        """Manifest contains key sections."""
        dist = tmp_path / "dist"
        dist.mkdir()
        whl = dist / "hamr-0.7.0-py3-none-any.whl"
        sdist = dist / "hamr-0.7.0.tar.gz"
        whl.write_bytes(b"wheel content here")
        sdist.write_bytes(b"sdist content here")

        bundle = create_release_bundle(version="0.7.0", dist_dir=dist)
        manifest = generate_release_manifest(bundle)

        assert "0.7.0" in manifest
        assert "linux-arm64" in manifest
        assert "3.11" in manifest
        assert "wheel" in manifest
        assert "sdist" in manifest
        assert "sha256" in manifest.lower()
        # Valid bundle should show no issues
        assert "validated" in manifest.lower() or "✓" in manifest

    def test_empty_manifest(self) -> None:
        """Manifest for empty bundle includes 'no artifacts'."""
        bundle = ReleaseBundle(
            version="0.7.0",
            artifacts=[],
            created_at="2026-05-08T20:00:00+00:00",
        )
        manifest = generate_release_manifest(bundle)
        assert "0.7.0" in manifest
        assert "Artifacts:  0" in manifest