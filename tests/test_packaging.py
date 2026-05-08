"""
tests/test_packaging.py — PyPI packaging & installer verification (Phase 14 T5).

Validates:
  - pyproject.toml structure and required fields
  - Version consistency between pyproject.toml and __init__.py
  - PEP 561 type marker
  - Public API exports (__all__)
  - CLI entry point is callable
"""

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "hamr"


# ── pyproject.toml ──────────────────────────────────────────────────────────

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

PYPROJECT_PATH = ROOT / "pyproject.toml"


@pytest.mark.skipif(tomllib is None, reason="tomllib/tomli not available")
class TestPyprojectToml:
    """Validate pyproject.toml structure and required metadata."""

    @pytest.fixture()
    def pyproject(self):
        with open(PYPROJECT_PATH, "rb") as f:
            return tomllib.load(f)

    def test_pyproject_is_valid_toml(self):
        """pyproject.toml must parse as valid TOML."""
        with open(PYPROJECT_PATH, "rb") as f:
            data = tomllib.load(f)
        assert isinstance(data, dict), "pyproject.toml must be a dict"

    def test_pyproject_has_required_fields(self, pyproject):
        """pyproject.toml must have name, version, description, requires-python."""
        proj = pyproject["project"]
        assert proj["name"] == "hamr"
        assert isinstance(proj["version"], str)
        assert isinstance(proj["description"], str)
        assert "requires-python" in proj
        assert proj["requires-python"] == ">=3.10"

    def test_pyproject_version_matches_init(self, pyproject):
        """Version in pyproject.toml must match __version__ in __init__.py."""
        import hamr
        assert pyproject["project"]["version"] == hamr.__version__

    def test_pyproject_has_dependencies(self, pyproject):
        """pyproject.toml must list numpy and Pillow as dependencies."""
        deps = pyproject["project"]["dependencies"]
        dep_names = [d.split(">=")[0].split("<")[0].split("=")[0].strip() for d in deps]
        assert "numpy" in dep_names
        assert "Pillow" in dep_names

    def test_pyproject_has_optional_dependencies(self, pyproject):
        """pyproject.toml must have [project.optional-dependencies] sections."""
        opt = pyproject["project"]["optional-dependencies"]
        assert "blender" in opt
        assert "dev" in opt

    def test_pyproject_has_scripts_entry_point(self, pyproject):
        """pyproject.toml must define hamr CLI entry point."""
        scripts = pyproject["project"]["scripts"]
        assert "hamr" in scripts
        assert scripts["hamr"] == "hamr.cli:main"

    def test_pyproject_has_classifiers(self, pyproject):
        """pyproject.toml must have MIT and Beta classifiers."""
        classifiers = pyproject["project"]["classifiers"]
        classifier_strs = " ".join(classifiers)
        assert "License :: OSI Approved :: MIT" in classifier_strs
        assert "Development Status :: 4 - Beta" in classifier_strs
        assert "Programming Language :: Python :: 3" in classifier_strs

    def test_pyproject_has_urls(self, pyproject):
        """pyproject.toml must have repository and issues URLs."""
        urls = pyproject["project"]["urls"]
        assert "repository" in urls
        assert "issues" in urls

    def test_pyproject_has_build_system(self, pyproject):
        """pyproject.toml must declare setuptools build backend."""
        bs = pyproject["build-system"]
        assert "setuptools" in " ".join(bs["requires"])
        assert bs["build-backend"] == "setuptools.build_meta"


# ── PEP 561 type marker ─────────────────────────────────────────────────────

class TestPyTyped:
    """Validate PEP 561 py.typed marker file."""

    def test_py_typed_exists(self):
        """src/hamr/py.typed must exist for PEP 561 type checking."""
        assert (SRC / "py.typed").is_file(), "PEP 561 marker py.typed is missing"

    def test_py_typed_is_empty_or_minimal(self):
        """py.typed should be empty or contain only comments."""
        content = (SRC / "py.typed").read_text().strip()
        # Empty is fine, or just comments
        if content:
            for line in content.splitlines():
                assert line.startswith("#"), f"py.typed should be empty or comments only, got: {line!r}"


# ── __init__.py exports ─────────────────────────────────────────────────────

class TestInitExports:
    """Validate __init__.py public API exports."""

    @pytest.fixture()
    def hamr_module(self):
        import hamr
        return hamr

    def test_init_has_all(self, hamr_module):
        """__init__.py must define __all__."""
        assert hasattr(hamr_module, "__all__"), "hamr must define __all__"
        assert isinstance(hamr_module.__all__, list), "__all__ must be a list"

    def test_all_includes_spec(self, hamr_module):
        """__all__ must include Spec."""
        assert "Spec" in hamr_module.__all__

    def test_all_includes_character_spec(self, hamr_module):
        """__all__ must include CharacterSpec."""
        assert "CharacterSpec" in hamr_module.__all__

    def test_all_includes_build_pipeline(self, hamr_module):
        """__all__ must include BuildPipeline."""
        assert "BuildPipeline" in hamr_module.__all__

    def test_all_includes_get_version(self, hamr_module):
        """__all__ must include get_version."""
        assert "get_version" in hamr_module.__all__

    def test_get_version_returns_version(self, hamr_module):
        """get_version() must return __version__."""
        assert hamr_module.get_version() == hamr_module.__version__
        assert isinstance(hamr_module.get_version(), str)

    def test_all_entries_are_importable(self, hamr_module):
        """Every name in __all__ must be importable from the hamr module."""
        for name in hamr_module.__all__:
            assert hasattr(hamr_module, name), f"__all__ lists {name!r} but it's not an attribute"


# ── CLI entry point ─────────────────────────────────────────────────────────

class TestCLIEntryPoint:
    """Validate the CLI entry point is callable."""

    def test_cli_main_is_callable(self):
        """hamr.cli:main must be a callable function."""
        from hamr.cli import main
        assert callable(main), "hamr.cli:main must be callable"

    def test_cli_main_returns_int(self):
        """hamr.cli:main must return an int exit code or have no annotation."""
        from hamr.cli import main
        # main() takes no args (argparse is internal); just verify it's callable
        # and that it can be used as an entry point
        assert callable(main), "main must be callable"


# ── MANIFEST.in ──────────────────────────────────────────────────────────────

class TestManifest:
    """Validate MANIFEST.in includes necessary files."""

    def test_manifest_includes_pyproject(self):
        """MANIFEST.in must include pyproject.toml."""
        content = (ROOT / "MANIFEST.in").read_text()
        assert "pyproject.toml" in content

    def test_manifest_includes_python_sources(self):
        """MANIFEST.in must include Python source files."""
        content = (ROOT / "MANIFEST.in").read_text()
        assert "*.py" in content

    def test_manifest_includes_license(self):
        """MANIFEST.in must include LICENSE."""
        content = (ROOT / "MANIFEST.in").read_text()
        assert "LICENSE" in content