# Contributing to Hamr

Thank you for your interest in contributing to the Shape-Skin Engine!

## Development Setup

```bash
git clone https://github.com/hrabanazviking/Hamr.git
cd Hamr
pip install -e ".[dev]"
```

## Code Style

- **Python 3.11+** — use `from __future__ import annotations`
- **Line length**: 100 characters max
- **Linting**: `ruff check src/hamr/`
- **Type checking**: `mypy src/hamr/`
- **Naming**: Norse-mythology inspired variable names are welcome for high-level concepts, but use clear descriptive English names for implementation details

## Running Tests

```bash
# All tests
pytest tests/ -v

# Phase-specific
pytest tests/test_phase1.py -v   # Spec, Models, Validation
pytest tests/test_phase2.py -v   # Textures, Bridge, Export, Body
pytest tests/test_phase3.py -v   # Bone Maps, Expressions, Build Script
pytest tests/test_phase4.py -v   # Pipeline, CLI
pytest tests/test_phase5.py -v   # Blender E2E, Environment

# With coverage
pytest tests/ --cov=hamr --cov-report=term-missing
```

## Branch Strategy

- **Development** — Active development, all PRs merge here first
- **main** — Stable releases only, merged from Development after full test pass

## Commit Messages

Use conventional commit format with emoji:

```
🔥 Phase N — Description
⚔️ Fix: description
✨ Feature: description
📝 Docs: description
🧪 Test: description
```

## Design Principles

1. **YAML-First** — Every parameter controllable via spec files
2. **Headless-First** — No GUI dependency, Blender runs `--background`
3. **Agent-Orchestrated** — Designed for AI-driven creation pipelines
4. **Explicit Over Implicit** — Never auto-map bones (lesson D-008)
5. **Additive-Only Bug Fixes** — Fix by adding correct paths, not removing old ones
6. **Pathlib Over Strings** — Use `Path` objects, not raw string paths

## Adding a New Forge

1. Create `src/hamr/<forge>/__init__.py` with your public API
2. Add models to `src/hamr/core/models.py` if needed
3. Add constants to `src/hamr/core/constants.py` if needed
4. Wire into `src/hamr/core/builder.py` and `src/hamr/core/pipeline.py`
5. Add tests in `tests/test_phase<N+1>.py`
6. Update this README's architecture table

## Questions?

Open an issue or find us in the VRM/open-source 3D community.

*May the Nornir guide your threads.*