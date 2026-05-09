# Contributing to Hamr

Thank you for your interest in contributing to **Hamr — The Shape-Skin Engine**.
This document covers everything you need to get started.

---

## Development Setup

### Prerequisites

- Python ≥ 3.10
- Git
- Blender 4.2+ (for full pipeline testing; not required for core library work)

### Clone & Install

```bash
git clone https://github.com/hrabanazviking/Hamr.git
cd Hamr
git checkout Development
pip install -e ".[dev]"
```

### Run Tests

```bash
# Full suite
python3 -m pytest tests/ -q --tb=short

# Without Blender-dependent tests
python3 -m pytest tests/ -q -m "not blender and not e2e"

# Performance regression only
python3 -m pytest tests/ -m perf

# With coverage
python3 -m pytest tests/ --cov=hamr --cov-report=term-missing
```

---

## Code Style

We use **ruff** for linting and formatting.

- **Line length:** 100 characters
- **Target:** Python 3.10+
- **Rules:** E, F, W, I, N, UP, B, A, SIM

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format
ruff format src/ tests/
```

### Type Checking

```bash
mypy src/
```

All public functions should have type annotations. `disallow_untyped_defs` is
enabled in `mypy` configuration.

---

## Commit Message Format

We use **emoji prefixes** to make the commit log scannable:

| Emoji | Prefix | Meaning |
|---|---|---|
| ⚡ | `⚡ feat:` | New feature |
| 🐛 | `🐛 fix:` | Bug fix |
| 📝 | `📝 docs:` | Documentation |
| 🎨 | `🎨 style:` | Code style / formatting (no logic change) |
| ♻️ | `♻️ refactor:` | Refactoring (no feature or fix) |
| ⚙️ | `⚙️ ci:` | CI / build configuration |
| ✅ | `✅ test:` | Test additions or changes |
| 🔒 | `🔒 chore:` | Security or housekeeping |
| 🚀 | `🚀 release:` | Release preparation |

**Examples:**
```
⚡ feat: add procedural iris texture generation
🐛 fix: correct bone hierarchy for TurboSquid rigs
📝 docs: update CLI reference for Phase 14
✅ test: add regression guards for Phase 12 presets
🚀 release: bump version to 0.7.0rc1
```

---

## Branch Workflow

| Branch | Purpose |
|---|---|
| `Main` | Stable releases only. Merged from `Development` at release. |
| `Development` | Active development. All PRs target this branch. |
| `feature/<name>` | Feature branches, branched from `Development`. |

### Workflow

1. Branch from `Development`:
   ```bash
   git checkout Development
   git pull origin Development
   git checkout -b feature/my-feature
   ```

2. Make changes, commit with emoji prefix.

3. Push and open a PR against `Development`:
   ```bash
   git push origin feature/my-feature
   ```

4. After review and approval, merge into `Development`.

5. At release time, `Development` is merged into `Main`.

---

## PR Checklist

Before submitting a pull request, verify:

- [ ] All tests pass: `pytest tests/ -q --tb=short`
- [ ] Lint is clean: `ruff check src/ tests/`
- [ ] Type check passes: `mypy src/`
- [ ] New code has tests
- [ ] Docstrings on all public functions / classes
- [ ] No hardcoded secrets or credentials
- [ ] Commit messages follow emoji prefix format
- [ ] PR targets `Development` (not `Main`)

---

## Reporting Issues

- Use [GitHub Issues](https://github.com/hrabanazviking/Hamr/issues)
- Include: Hamr version (`hamr version`), Python version, OS, Blender version
  (if applicable), minimal reproduction steps

---

## License

By contributing, you agree that your work will be licensed under the MIT License,
as described in the project's `LICENSE` file.