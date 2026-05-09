# Migration Guide — Hamr v0.3.0 → v0.7.0

This guide covers all API, configuration, and behavioral changes introduced
between v0.3.0 (Phase 4) and v0.7.0 (Phase 15).

---

## 1. API Changes

### 1.1 Top-Level Spec Import

**Before (v0.3.0):**
```python
from hamr.core.models import CharacterSpec
spec = CharacterSpec(...)
```

**After (v0.7.0-rc1):**
```python
from hamr.core.spec import Spec
spec = Spec.from_yaml("character.yaml")
# CharacterSpec is still a data model, but Spec is the canonical entry point
```

### 1.2 Build Pipeline

**Before (v0.3.0):** Build was an ad-hoc series of function calls in
`build_avatar.py` with no stage numbering, timing, or error recovery.

**After (v0.7.0-rc1):**
```python
from hamr.core.pipeline import BuildPipeline

pipeline = BuildPipeline()
result = pipeline.build(spec)  # Returns PipelineResult
# result.stages — per-stage timing, success/failure
# result.success — overall build status
# result timing, output_size, diagnostics
```

- 14 explicit numbered stages (0–13)
- Per-stage timing and `BuildResult` tracking
- `--skip-stages hair,clothing` for targeted debugging
- `PerfBudget` integration at pipeline start and end

### 1.3 New Modules

The following modules were introduced in Phases 11–14:

| Module | Class / Function | Since |
|---|---|---|
| `hamr.core.pipeline` | `BuildPipeline`, `PipelineResult` | v0.5.0 |
| `hamr.core.perf` | `PerfBudget`, `PerfTracker` | v0.4.0 |
| `hamr.core.presets` | `PresetLoader` | v0.4.0 |
| `hamr.core.validate` | `spec_to_dict()` | v0.6.0 |
| `hamr.core.gpu_profiles` | `GPUProfiler` | v0.6.0 |
| `hamr.core.a11y` | Accessibility & CLI flags | v0.6.0 |
| `hamr.core.texture_procedural` | `TextureForge` | v0.6.0 |
| `hamr.hair.mesh` | `HairForge` | v0.4.0 |
| `hamr.clothing.mesh` | `ClothingForge` | v0.4.0 |
| `hamr.rigs.stub_bones` | `create_missing_bones()` | v0.4.0 |
| `hamr.rigs.weights` | `WeightPaintEngine` | v0.4.0 |
| `hamr.rigs.verify` | `RigVerifier`, `RigReport` | v0.4.0 |
| `hamr.rigs.spring_bones` | `create_spring_bones()` | v0.4.0 |
| `hamr.rigs.colliders` | `CollisionForge` | v0.5.0 |
| `hamr.materials.forge` | `MaterialForge` | v0.5.0 |
| `hamr.face.expressions` | `ExpressionDiscovery` | v0.5.0 |
| `hamr.export.first_person` | `FirstPersonAnnotator` | v0.4.0 |
| `hamr.export.vrm_validator` | `VRMValidator` | v0.6.0 |
| `hamr.export.animation_clips` | `AnimationForge` | v0.6.0 |
| `hamr.docs.generate` | `DocGenerator` | v0.6.0 |
| `hamr.core.regression` | `RegressionThreshold`, `RegressionBaseline` | v0.7.0 |
| `hamr.core.release` | `ArtifactInfo`, `ReleaseManifest` | v0.7.0 |
| `hamr.blender_bridge.e2e` | `E2EBuildConfig`, `E2EBuildResult` | v0.7.0 |
| `hamr.docs.api_reference` | `APIEntry`, `generate_api_reference()` | v0.7.0 |

### 1.3 Renamed / Moved Functions

| Old Path | New Path | Notes |
|---|---|---|
| `hamr.core.spec.Spec` | Same | `Spec` is now the canonical import; `CharacterSpec` is a data model |
| `hamr.core.models.CharacterSpec` | Still exists | Use `Spec` for YAML loading; `CharacterSpec` is the data structure |

---

## 2. Configuration Changes

### 2.1 Character Spec YAML

The `CharacterSpec` YAML format now supports a `pipeline` section:

```yaml
# New in v0.5.0+ — pipeline configuration
pipeline:
  skip_stages: []          # e.g., ["hair", "clothing"]
  perf_budget: standard    # minimal | standard | full
  spring_bones: true
  collision: true

# Existing fields remain unchanged
body:
  height_cm: 165
  build: feminine
  proportions: average
  # ...
```

### 2.2 Preset Format

Presets (in `assets/presets/`) now support:
- **Deep merge** — user specs override preset defaults while preserving nested
  structure
- **Pipeline section** — `pipeline` sub-key with stage configuration
- **Validation** — presets are validated against the `CharacterSpec` schema on load

### 2.3 CLI Flags

| Flag | Since | Description |
|---|---|---|
| `--json` | v0.5.0 | Machine-readable JSON output for all commands |
| `--verbose` | v0.5.0 | Detailed output for `list-presets` etc. |
| `--skip-stages` | v0.5.0 | Skip pipeline stages (comma-separated) |
| `--no-color` | v0.6.0 | Strip ANSI/Rich formatting for piped output |
| `--quiet` | v0.6.0 | Suppress all non-error output |

### 2.4 Exit Codes

| Code | Meaning | Since |
|---|---|---|
| 0 | Success | v0.3.0 |
| 1 | Warning | v0.6.0 |
| 2 | Error | v0.6.0 |
| 3 | Environment missing | v0.6.0 |

---

## 3. Deprecation Notices

- **`hamr.core.spec.Spec.to_dict()` round-trips** — Use `spec_to_dict()` from
  `hamr.core.validate` for guaranteed round-trip-able serialization. The
  `Spec.to_dict()` method remains but does not guarantee all fields survive
  a YAML round-trip.
- **Ad-hoc build scripts** — Direct calls to individual forge functions should
  migrate to `BuildPipeline.build()`. The old functions are not removed, but
  they are not the recommended entry point.
- **Flat JSON presets** — Presets are now YAML-based with deep merge. Flat JSON
  preset files will still load but should be migrated to the new format.

---

## 4. Dependency Changes

- **Python ≥ 3.10** required (unchanged from v0.3.0)
- **New runtime dependencies:** `pydantic>=2.0`, `rich>=13.0`
- **Dev dependencies:** `mypy`, `ruff` added to `[dev]` extras
- **Blender dependency** unchanged — `bpy` is not pip-installable; core library
  works without it
- **pytest markers:** `blender`, `slow`, `benchmark`, `perf`, `e2e` available

### 5.2 CI/CD (v0.7.0)

- **GitHub Actions** — `.github/workflows/ci.yml` runs lint, test, coverage, and benchmark on every push/PR
- **Release workflow** — `.github/workflows/release.yml` builds wheel/sdist and publishes to TestPyPI on tag push
- **Branch protection** — `Development` and `Main` branches require passing CI

### 5.3 API Reference (v0.7.0)

```python
from hamr.docs.api_reference import generate_api_reference

# Generate markdown API reference for all hamr.* modules
md = generate_api_reference()

# Or specify specific modules
md = generate_api_reference(["hamr.core", "hamr.rigs"])
```

---

## 5. Testing Migration

Tests that relied on ad-hoc build calls should migrate to:

```python
from hamr.core.pipeline import BuildPipeline
from hamr.core.spec import Spec

spec = Spec.from_yaml("test_spec.yaml")
result = BuildPipeline().build(spec)
assert result.success
```

For CI environments without Blender, use:
```bash
pytest tests/ -m "not blender" -m "not e2e"
```

For performance regression tests:
```bash
pytest tests/ -m perf
```