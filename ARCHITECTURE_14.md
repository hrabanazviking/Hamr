# Phase 14: Gjallarhorn — Architecture Document

> *Rúnhild Svartdóttir, The Architect*
> *System mapping and domain decomposition*

---

## 1. Module Dependency Map

The data flow through Hamr follows a strict layering: **Spec → Validate → Forge → Pipeline → Blender Bridge → Export**. Below is the complete call graph, with Blender-dependent paths marked with 🎬 and pure-Python paths marked with 🐍.

```
CLI (hamr/cli.py)
 ├── cmd_build()
 │    ├── BuildPipeline.build()                    [core/pipeline.py]
 │    │    ├── Spec.from_yaml()                     [core/spec.py] 🐍
 │    │    ├── validate_spec()                       [core/validate.py] 🐍
 │    │    ├── Spec.to_dict()                        [core/spec.py] 🐍
 │    │    ├── check_budget()                        [core/perf.py] 🐍
 │    │    ├── run_blender_script()                  [blender_bridge/runner.py] 🎬
 │    │    │    └── build_avatar.py::main()          [scripts/build_avatar.py] 🎬
 │    │    │         ├── _clear_scene()              🎬
 │    │    │         ├── _import_base() / _generate_mblab_base() 🎬
 │    │    │         ├── _apply_spec()               🎬
 │    │    │         │    ├── _apply_colors()        🎬
 │    │    │         │    ├── _apply_height()        🎬
 │    │    │         │    ├── _apply_face_from_forge()  🎬
 │    │    │         │    ├── _apply_hair_from_forge()  🎬
 │    │    │         │    └── _apply_clothing_from_forge() 🎬
 │    │    │         ├── _integrate_stub_bones()    🎬  ← rigs/stub_bones.py
 │    │    │         ├── _integrate_hair_mesh()     🎬  ← hair/mesh.py
 │    │    │         ├── _integrate_clothing_meshes() 🎬 ← clothing/mesh.py
 │    │    │         ├── _integrate_weight_paint()   🎬  ← rigs/weights.py
 │    │    │         ├── _integrate_spring_bones()  🎬  ← rigs/spring_bones.py
 │    │    │         ├── _integrate_first_person()  🎬  ← export/first_person.py
 │    │    │         ├── _apply_vrm_humanoid()       🎬
 │    │    │         ├── _apply_vrm_metadata()       🎬
 │    │    │         ├── _apply_vrm_expressions()    🎬
 │    │    │         ├── _apply_vrm_look_at()        🎬
 │    │    │         ├── bpy.ops.export_scene.vrm()  🎬
 │    │    │         └── _validate_vrm()             🎬/🐍
 │    │    └── clean_blend_backups()                [blender_bridge/scene.py] 🎬
 │    ├── _resolve_forges()                         [core/builder.py] 🐍
 │    │    ├── resolve_hair()                       [hair/__init__.py] 🐍
 │    │    ├── resolve_face()                       [face/__init__.py] 🐍
 │    │    └── resolve_clothing()                    [clothing/__init__.py] 🐍
 │    └── PerformanceBudget / check_budget()        [core/perf.py] 🐍
 ├── cmd_validate()
 │    └── BuildPipeline.validate_only()             🐍
 ├── cmd_inspect()
 │    └── inspect()                                 [core/builder.py] 🐍
 ├── cmd_verify_rig()
 │    └── verify_vrm_rig()                          [rigs/verify.py] 🐍
 ├── cmd_check_env()
 │    └── BuildPipeline.check_environment()         🐍/🎬
 ├── cmd_list_presets()
 │    └── CHARACTER_PRESETS                          [core/presets.py] 🐍
 └── cmd_docs()
      └── generate_all()                            [docs/generate.py] 🐍

Pipeline Integration Layer [core/pipeline_integrate.py] 🐍/🎬
 ├── plan_stages()                                 🐍
 ├── estimate_stage_time()                         🐍
 ├── validate_spec_completeness()                  🐍
 └── run_integration_stages()                      🎬  (requires bpy)
      ├── rigs.stub_bones.create_missing_bones()   🎬
      ├── hair.mesh.HairMeshGenerator.generate()  🎬
      ├── clothing.mesh.ClothingMeshGenerator      🎬
      ├── rigs.weights.WeightPaintEngine            🎬
      ├── rigs.spring_bones.apply_spring_bones()   🎬
      └── export.first_person.configure_first_person() 🎬/🐍

Pure-Python Subsystems (no bpy dependency) ────────────────────────
 ├── core/spec.py          Spec, from_yaml, from_dict, to_dict, to_yaml
 ├── core/models.py        CharacterSpec, BodySpec, FaceSpec, HairSpec, etc.
 ├── core/validate.py      validate_spec()
 ├── core/errors.py        HamrError hierarchy
 ├── core/constants.py     BODY_PRESETS, VRM_25_BONE_NAMES, SKIN_PALETTES
 ├── core/perf.py          PerformanceBudget, check_budget(), estimate_*
 ├── core/perf_gate.py     PerfGate, select_budget_tier()
 ├── core/gpu_profiles.py  GPUProfile, auto_detect_profile()
 ├── core/presets.py       CHARACTER_PRESETS, resolve_preset()
 ├── core/textures.py      generate_hair_texture(), hex_to_hsv()
 ├── core/texture_procedural.py  ProceduralTexturePipeline (PIL-based)
 ├── core/a11y.py          CLIOptions, format_output()
 ├── core/builder.py       build(), validate_only(), inspect(), _resolve_forges()
 ├── core/iterate.py       Spec iteration utilities
 ├── core/inspect.py       VRM/GLB inspection
 ├── hair/__init__.py      HairBuildResult, resolve_hair()
 ├── face/__init__.py      FaceBuildResult, resolve_face()
 ├── clothing/__init__.py  ClothingBuildResult, resolve_clothing()
 ├── rigs/verify.py        RigVerifier, check_naming_conventions_pure()
 ├── rigs/stub_bones.py    StubBoneResult, detect_missing_bones() 🐍, create_missing_bones() 🎬
 ├── rigs/collision.py     CollisionMeshGenerator (pure geometry)
 ├── rigs/spring_bones.py  SpringBoneGroup, configure_*_spring() 🐍, apply_spring_bones() 🎬
 ├── export/vrm_validator.py  VRMValidator (pure glTF binary parsing) 🐍
 ├── export/animation_clips.py  AnimationClip, create_clip(), clip_to_gltf_animation() 🐍
 ├── export/first_person.py    FirstPersonConfig, classify_mesh_for_fp() 🐍, configure_first_person() 🎬
 ├── materials/anime.py   AnimeMaterialSpec, AnimeMaterialGenerator 🐍/🎬
 └── docs/generate.py     generate_cli_reference(), generate_architecture_diagram() 🐍
```

### Layer Boundary Summary

| Layer | Module(s) | bpy Dep? | Testable Without Blender? |
|-------|-----------|----------|---------------------------|
| **Spec** | core/spec, core/models, core/errors, core/constants | ✗ No | ✅ Fully |
| **Validation** | core/validate, core/perf, core/perf_gate, core/gpu_profiles | ✗ No | ✅ Fully |
| **Forge (config)** | hair/\_\_init\_\_, face/\_\_init\_\_, clothing/\_\_init\_\_ | ✗ No | ✅ Fully |
| **Forge (mesh)** | hair/mesh, clothing/mesh | ✓ Yes | ⚠️ Partial (pure parts: yes) |
| **Rigs (data)** | rigs/verify, rigs/collision, rigs/stub_bones (detect) | ✗ No | ✅ Fully |
| **Rigs (action)** | rigs/weights, rigs/spring_bones (apply), rigs/stub_bones (create) | ✓ Yes | ❌ Needs Blender |
| **Pipeline** | core/pipeline, core/pipeline_integrate, core/builder | ✗ No | ✅ Partial |
| **Bridge** | blender_bridge/runner, blender_bridge/scene | ✓ Yes | ❌ Needs Blender |
| **Build Script** | scripts/build_avatar | ✓ Yes | ❌ Needs Blender |
| **Export** | export/vrm_validator, export/animation_clips | ✗ No | ✅ Fully |
| **Export (action)** | export/vrm, export/first_person (configure) | ✓ Yes | ❌ Needs Blender |
| **Materials** | materials/anime | ✓ Yes | ⚠️ Partial |
| **CLI** | cli | ✗ No | ✅ Fully (unit) |
| **Docs** | docs/generate | ✗ No | ✅ Fully |

---

## 2. Task Decomposition (T1–T7)

### T1 — End-to-End Integration Suite (14.1)

**Goal:** Comprehensive E2E test harness: spec ingest → procedural texturing → VRM export → validation, one unbroken flow.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T1.1: E2E test harness framework | `tests/test_e2e_suite.py` (NEW) | `class TestE2ESuite`, `def test_full_pipeline_spec_to_vrm()` | No (mock) |
| T1.2: Spec→Forge→JSON serialization round-trip | `tests/test_e2e_suite.py` | `def test_spec_roundtrip()`, `def test_forge_resolution_all_presets()` | No |
| T1.3: Pure-Python pipeline path (validate → budget → plan) | `tests/test_e2e_suite.py` | `def test_validate_budget_plan_chain()` | No |
| T1.4: VRM validator integration | `tests/test_e2e_suite.py` | `def test_validator_on_known_vrm()` | No |
| T1.5: Blender E2E (CI only, skipped locally) | `tests/test_e2e_blender.py` (NEW) | `def test_blender_full_build()`, `def test_blender_mblab_build()` | Yes |
| T1.6: Platform matrix markers | `tests/conftest.py` (MODIFY) | `@pytest.mark.linux`, `@pytest.mark.macos`, `@pytest.mark.windows` | — |
| T1.7: CI workflow matrix config | `.github/workflows/e2e.yml` (NEW/UPDATE) | Matrix: python 3.11/3.12 × OS | — |

**Key Integration Points:**
- `BuildPipeline.build()` → `run_blender_script()` → `build_avatar.py::main()`
- `pipeline_integrate.py::plan_stages()` → `validate_spec_completeness()` → `check_budget()`
- `VRMValidator.validate()` after export for compliance

### T2 — Blender Build Verification (14.2)

**Goal:** CI matrix testing Hamr against Blender 4.2 LTS, 4.3 LTS, 4.4 LTS, and current stable.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T2.1: Blender version detection helper | `src/hamr/blender_bridge/runner.py` (MODIFY) | `get_blender_version()` enhancement, `check_blender_compatibility()` | No (subprocess) |
| T2.2: Version compatibility matrix | `src/hamr/blender_bridge/compat.py` (NEW) | `BLENDER_COMPAT_MATRIX`, `check_version_compat()`, `get_deprecation_warnings()` | No |
| T2.3: Addon registration verification script | `tests/blender_scripts/test_addon_registration.py` (NEW) | `def test_register_all_operators()` | Yes |
| T2.4: Blender version CI matrix | `.github/workflows/blender_matrix.yml` (NEW/UPDATE) | Matrix: blender=4.2,4.3,4.4,latest | — |
| T2.5: Version-specific caveats doc | `docs/BLENDER_COMPAT.md` (NEW) | Markdown table of known issues | — |

### T3 — Performance Regression Benchmarks (14.3)

**Goal:** Automated benchmark suite for key operations, ±5% tolerance, CI-gated.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T3.1: Benchmark framework | `src/hamr/core/benchmark.py` (NEW) | `class Benchmark`, `class BenchmarkResult`, `def run_benchmark()`, `def compare_to_baseline()` | No |
| T3.2: Spec-parse + validate benchmark | `tests/bench/test_bench_spec.py` (NEW) | `def bench_spec_parse()`, `def bench_validate()` | No |
| T3.3: Forge resolution benchmark | `tests/bench/test_bench_forges.py` (NEW) | `def bench_resolve_hair()`, `def bench_resolve_face()`, `def bench_resolve_clothing()` | No |
| T3.4: VRM validator benchmark | `tests/bench/test_bench_validator.py` (NEW) | `def bench_vrm_validate_small()`, `def bench_vrm_validate_large()` | No |
| T3.5: Full-pipeline benchmark (mock Blender) | `tests/bench/test_bench_pipeline.py` (NEW) | `def bench_pipeline_dry_run()` | No |
| T3.6: Baseline file + CI gate | `benchmarks/baselines.json` (NEW), `.github/workflows/benchmark.yml` | Baseline JSON with tolerance, CI diff gate | — |

### T4 — Preset System Rework (14.4)

**Goal:** Versioned, tagged, categorized preset format with browser stub.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T4.1: Versioned preset schema | `src/hamr/core/presets_v2.py` (NEW) | `class PresetManifest`, `class PresetEntry`, `PRESET_SCHEMA_VERSION`, `load_preset_v2()`, `migrate_v1_to_v2()` | No |
| T4.2: Category taxonomy | `src/hamr/core/presets_v2.py` | `PRESET_CATEGORIES_V2` (humanoid_base, creature, accessory, environment), `categorize_preset()` | No |
| T4.3: Preset validation against new schema | `src/hamr/core/presets_v2.py` | `validate_preset_v2()`, `validate_preset_manifest()` | No |
| T4.4: Preset import/export (JSON + YAML) | `src/hamr/core/presets_v2.py` | `export_preset()`, `import_preset()`, `export_manifest()` | No |
| T4.5: Preset browser UI stub | `src/hamr/cli.py` (MODIFY) | `cmd_list_presets()` → add `--category`, `--tag`, `--format=v2` options | No |
| T4.6: Community preset repository stub | `src/hamr/core/preset_repo.py` (NEW) | `class PresetRepository`, `def fetch_community_presets()`, `def validate_remote()` | No |
| T4.7: Migrate existing presets to v2 | `src/hamr/core/presets.py` (MODIFY) | Add `PRESET_VERSION = 2`, backward compat | No |

### T5 — PyPI Packaging & Installer Preparation (14.5)

**Goal:** Core library on PyPI, Blender addon as separate zip, CLI entry points.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T5.1: Core/non-core module split | `pyproject.toml` (MODIFY) | Add `[project.optional-dependencies]` split: `core` vs `blender` | — |
| T5.2: Ensure pure-Python modules have zero bpy imports | Audit of all core/ hair/ face/ clothing/ rigs/ export/vrm_validator.py | — | No |
| T5.3: Blender addon packaging script | `scripts/package_addon.py` (NEW) | `package_blender_addon()`, zip structure | No |
| T5.4: CLI entry points for headless validation | `pyproject.toml` (MODIFY) | `hamr-validate`, `hamr-inspect`, `hamr-verify-rig` as console_scripts | — |
| T5.5: Clean pip install test | `scripts/test_pip_install.sh` (NEW) | Fresh venv → `pip install hamr` → `hamr validate --help` | — |
| T5.6: TestPyPI publish workflow | `.github/workflows/publish.yml` (NEW/UPDATE) | Build wheel, publish to TestPyPI on tag | — |

### T6 — Release Candidate 0.7.0-rc1 (14.6)

**Goal:** Tag, cut, and publish the first release candidate.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T6.1: Version bump | `src/hamr/__init__.py` (MODIFY) | `__version__ = "0.7.0rc1"` | — |
| T6.2: Changelog generation (Phases 7–14) | `CHANGELOG.md` (NEW/MODIFY) | Aggregate from PHASE_*.md commit messages | — |
| T6.3: Migration guide from v0.5.x | `docs/MIGRATION_v0.5_to_v0.7.md` (NEW) | Breaking changes, new API, deprecated items | — |
| T6.4: README update with screenshots | `README.md` (MODIFY) | Add build output screenshots, CLI examples | — |
| T6.5: Git tag + GitHub Release | `scripts/cut_release.sh` (NEW) | `git tag v0.7.0-rc1`, `gh release create` | — |
| T6.6: TestPyPI publish rc1 | `.github/workflows/publish.yml` | Upload `hamr-0.7.0rc1` to TestPyPI | — |

### T7 — Documentation Finalization & Accessibility Audit (14.7)

**Goal:** Complete API docs, a11y audit, reproducible docs build.

| Subtask | File | Functions/Classes | bpy? |
|---------|------|-------------------|------|
| T7.1: API reference from docstrings | `src/hamr/docs/generate.py` (MODIFY) | `generate_api_reference()`, `generate_module_docs()` | No |
| T7.2: Keyboard navigation audit | `src/hamr/core/a11y.py` (MODIFY) | Add `audit_keyboard_navigation()`, verify all CLI paths are keyboard-only | No |
| T7.3: Screen-reader compatibility | `src/hamr/core/a11y.py` (MODIFY) | `audit_screen_reader()`, structured output mode | No |
| T7.4: WCAG 2.1 AA contrast ratio check | `src/hamr/core/a11y.py` (MODIFY) | `check_contrast_ratios()` for ANSI output | No |
| T7.5: Docs backlog from Phase 13 | `docs/*.md` (MODIFY) | Fix outstanding doc issues | — |
| T7.6: Reproducible docs CI build | `.github/workflows/docs.yml` (NEW) | Build docs → publish to GitHub Pages | — |

---

## 3. Integration Test Strategy

### 3.1 Problem: Blender Dependency

The core challenge: `bpy` only exists inside a Blender Python environment. This blocks standard `pytest` runs on CI machines without a Blender install.

### 3.2 Solution: Three-Tier Testing

**Tier 1 — Pure-Python Unit Tests (no bpy, no mocks)**

All modules in the "🐍 Fully testable" column of the layer table above. These run on every PR, every OS, every Python version.

```
tests/test_spec.py          — Spec parsing, round-trip, defaults
tests/test_phase2-5.py       — Model validation, skin maps, body presets
tests/test_phase7.py         — Forge resolution (hair, face, clothing)
tests/test_perf.py           — Budget checks, memory estimation
tests/test_perf_gate.py      — PerfGate, tier selection
tests/test_gpu_profiles.py   — GPU profile detection
tests/test_presets.py        — Preset resolution and validation
tests/test_animation_clips.py — Keyframe creation, clip validation
tests/test_vrm_validator.py  — glTF binary parsing, bone coverage
tests/test_expressions.py    — Expression binding, VRM expression maps
tests/test_first_person.py   — classify_mesh_for_fp() (pure-Python path)
tests/test_stub_bones.py     — detect_missing_bones() (pure-Python path)
tests/test_spring_bones.py   — SpringBoneGroup config (pure part)
tests/test_collision.py      — Collision mesh computation
tests/test_materials.py      — AnimeMaterialSpec, color helpers
tests/test_a11y.py           — CLIOptions, format_output()
tests/test_texture_procedural.py — ProceduralTexturePipeline (needs Pillow)
tests/test_clothing_mesh.py  — resolve_clothing_pattern(), estimate_triangle_count()
tests/test_hair_mesh.py      — generate_guide_curves(), compute_strand_count()
tests/test_cli.py            — CLI argument parsing, command routing
tests/test_docs_generate.py  — Doc generation
```

**Tier 2 — Pipeline Integration Tests (mocked bpy via monkeypatch)**

These test the orchestration and data flow without launching Blender.

```python
# tests/test_e2e_suite.py

class TestE2EPurePython:
    """Tier 2: Full pipeline path that doesn't touch bpy."""

    def test_spec_to_validation_to_forge(self):
        """Spec → Validate → Resolve Forges → Serialize JSON."""
        spec = Spec.from_yaml("tests/fixtures/character.yaml")
        errors = validate_spec(spec.character)
        assert not errors
        forge_config = _resolve_forges(spec.character)
        assert "hair" in forge_config
        # Serialize to JSON (what pipeline sends to Blender)
        spec_dict = spec.to_dict()
        assert "character" in spec_dict

    def test_pipeline_dry_run_mock_builder(self, monkeypatch, tmp_path):
        """BuildPipeline.build() with Blender mocked to succeed."""
        mock_result = BlenderResult(
            success=True, exit_code=0,
            stdout="Build complete.", stderr="",
            elapsed=5.0
        )
        monkeypatch.setattr("hamr.core.pipeline.run_blender_script", lambda **kw: mock_result)
        pipeline = BuildPipeline()
        # Create a minimal spec file
        spec_path = tmp_path / "test.yaml"
        spec_path.write_text(YAML_MINIMAL_SPEC)
        result = pipeline.build(str(spec_path), str(tmp_path))
        assert result.success

    def test_pipeline_integrate_planning(self):
        """plan_stages() returns correct stage order for each spec."""
        stages_default = plan_stages(spec_with_hair_and_clothing)
        assert stages_default == [
            "stub_bones", "hair_mesh", "clothing_mesh",
            "weight_paint", "spring_bones", "first_person"
        ]
        stages_bald = plan_stages(spec_bald)
        assert "hair_mesh" not in stages_bald

    def test_vrm_validator_on_synthetic(self, tmp_path):
        """Create a minimal glTF binary, validate with VRMValidator."""
        synthetic_vrm = create_minimal_vrm_binary()
        vrm_path = tmp_path / "test.vrm"
        vrm_path.write_bytes(synthetic_vrm)
        validator = VRMValidator()
        result = validator.validate(vrm_path)
        # Should detect missing VRM extension
        assert not result.has_vrm_extension

    def test_build_avatar_spec_json_roundtrip(self):
        """JSON serialization preserves all forge config fields."""
        spec = Spec.from_yaml("tests/fixtures/full_spec.yaml")
        spec_dict = spec.to_dict()
        spec_dict["_pipeline"] = {"base_type": "mblab", "format": "vrm"}
        json_str = json.dumps(spec_dict)
        parsed = json.loads(json_str)
        assert parsed["character"]["name"] == spec.character.name
        assert parsed["_pipeline"]["format"] == "vrm"
```

**Tier 3 — Blender Integration Tests (real bpy, CI-only)**

These run with a real Blender executable on CI. They are **skipped** in local `pytest` runs unless `--run-blender` is passed.

```python
# tests/test_e2e_blender.py

import pytest

# Skip entire module if bpy unavailable
pytest.importorskip("bpy", reason="Blender not available — use --run-blender to enable")

@pytest.mark.blender
class TestBlenderIntegration:
    """Tier 3: Tests that require real Blender."""

    def test_register_vrm_addon(self):
        """VRM addon can be enabled in Blender."""
        import addon_utils
        addon_utils.enable("io_scene_vrm")
        # Verify it's in bpy.ops

    def test_full_mblab_build(self, blender_env, tmp_path):
        """Complete build from MB-Lab default to VRM."""
        pipeline = BuildPipeline()
        # Use a minimal spec that doesn't require custom base mesh
        result = pipeline.build(
            spec_path="tests/fixtures/minimal_mblab.yaml",
            output_dir=str(tmp_path)
        )
        assert result.success
        assert result.output_path.suffix == ".vrm"
        # Validate the output
        validator = VRMValidator()
        vrm_result = validator.validate(result.output_path)
        assert vrm_result.valid

    def test_full_custom_base_build(self, blender_env, tmp_path):
        """Build from a custom base mesh."""
        result = pipeline.build(
            spec_path="tests/fixtures/custom_base.yaml",
            output_dir=str(tmp_path),
            base_mesh="tests/fixtures/base_mesh.glb"
        )
        assert result.success
```

### 3.3 CI Markers and Skip Strategy

```python
# tests/conftest.py

import pytest

def pytest_addoption(parser):
    parser.addoption("--run-blender", action="store_true", help="Run Blender integration tests")
    parser.addoption("--run-benchmarks", action="store_true", help="Run benchmark suite")

def pytest_collection_modifyitems(config, items):
    # Skip Blender tests unless --run-blender
    if not config.getoption("--run-blender"):
        skip_blender = pytest.mark.skip(reason="Need --run-blender to run")
        for item in items:
            if "blender" in item.keywords:
                item.add_marker(skip_blender)

    # Skip benchmarks unless --run-benchmarks
    if not config.getoption("--run-benchmarks"):
        skip_bench = pytest.mark.skip(reason="Need --run-benchmarks to run")
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_bench)

# Platform markers
pytest.mark.linux    # Linux-only tests
pytest.mark.macos    # macOS-only tests
pytest.mark.windows  # Windows-only tests
pytest.mark.blender  # Requires bpy
pytest.mark.benchmark  # Benchmark tests
```

### 3.4 Fixture Strategy

```
tests/fixtures/
 ├── minimal_mblab.yaml        — Smallest valid MB-Lab spec
 ├── full_spec.yaml            — Spec with all fields populated
 ├── custom_base.yaml          — Spec referencing a .glb base
 ├── base_mesh.glb             — Minimal GLB for custom base tests
 ├── sample_vrm.vrm           — Known-good VRM for validator tests
 ├── invalid_vrm.vrm          — Deliberately broken VRM for negative tests
 └── over_budget.yaml          — Spec that exceeds minimal tier budget
```

### 3.5 Blender-on-CI Strategy

For GitHub Actions, use the `blender` APT package or download Blender LTS from https://download.blender.org/release/. The CI workflow installs Blender, the VRM addon, and MB-Lab, then runs with `--run-blender`.

---

## 4. Release Readiness Checklist

Every item must be ✅ before v0.7.0-rc1 can be tagged.

### 4.1 Code Quality

- [ ] **All 1569+ existing tests pass** (`pytest tests/ -x`)
- [ ] **No `import bpy` in pure-Python modules** — grep audit confirms core/, hair/__init__, face/__init__, clothing/__init__, rigs/verify, export/vrm_validator have zero bpy imports
- [ ] **All modules have `__init__.py` with `__all__`** — consistent public API surface
- [ ] **Type annotations complete** on all public functions (`mypy src/hamr --ignore-missing-imports` passes)
- [ ] **Ruff lint clean** (`ruff check src/ tests/`)
- [ ] **No `TODO`, `HACK`, or `XXX` comments** remaining in production code
- [ ] **Decision log entries** (D-008 through D-019) documented in code and changelog

### 4.2 Integration

- [ ] **E2E spec→validation→forge→JSON round-trip** passes for all 6 built-in presets
- [ ] **E2E pipeline dry-run** (mocked Blender) completes without errors
- [ ] **E2E Blender build** produces valid VRM for at least 1 preset on each LTS (4.2, 4.3, 4.4)
- [ ] **VRM validator** passes on all generated VRM files
- [ ] **Performance budget check** correctly gates builds (over-budget exit code 3)
- [ ] **CLI all commands work**: `build`, `validate`, `inspect`, `list-presets`, `verify-rig`, `check-env`, `version`, `docs generate`
- [ ] **No regressions**: benchmark suite runs within ±5% of baseline

### 4.3 Packaging

- [ ] **`pip install hamr`** in fresh venv succeeds, brings in core dependencies only (PyYAML, Pillow, numpy, click, pydantic, rich)
- [ ] **`pip install hamr[dev]`** brings in pytest, ruff, mypy
- [ ] **CLI entry points work**: `hamr validate --help`, `hamr verify-rig --help`
- [ ] **Blender addon zip** packages correctly with `scripts/package_addon.py`
- [ ] **Package imports cleanly**: `python -c "import hamr; print(hamr.__version__)"` prints `0.7.0rc1`

### 4.4 Documentation

- [ ] **API reference** auto-generated from docstrings (`hamr docs generate`)
- [ ] **Architecture diagram** renders correctly (Mermaid)
- [ ] **CLI reference** documents all subcommands and flags
- [ ] **README.md** updated with v0.7.0 features, screenshots, installation instructions
- [ ] **CHANGELOG.md** covers Phases 7–14
- [ ] **Migration guide** from v0.5.x to v0.7.0
- [ ] **Blender compatibility matrix** documented
- [ ] **All docstrings use imperative mood**, Google style, and include `Args:` / `Returns:` sections

### 4.5 Accessibility

- [ ] **All CLI output works with `--no-color`** — no info lost when ANSI is stripped
- [ ] **All CLI output works with `--json`** — machine-parseable JSON output for every command
- [ ] **Screen-reader mode**: `--quiet` suppresses progress bars and decorative output
- [ ] **WCAG 2.1 AA contrast ratios** for ANSI color output (4.5:1 minimum)
- [ ] **Keyboard-only operation**: every CLI task achievable without mouse/pointer

### 4.6 Security & Legal

- [ ] **No secrets in code** — `.gitignore` covers `.env`, `*.key`, `*.pem`
- [ ] **LICENSE file** present and correct (MIT)
- [ ] **Third-party attributions** in NOTICE or third-party-licenses
- [ ] **SBOM** generated for PyPI package dependencies

### 4.7 Release Mechanics

- [ ] **Version bump** in `src/hamr/__init__.py`: `__version__ = "0.7.0rc1"`
- [ ] **Git tag**: `v0.7.0-rc1` on `Development` branch
- [ ] **GitHub Release** created with changelog and artifacts
- [ ] **TestPyPI** publish succeeds: `pip install --index-url https://test.pypi.org/simple hamr==0.7.0rc1`
- [ ] **Community announcement** on Discord/GitHub Discussions

---

## Appendix: File Change Map

**New Files (T1–T7):**
```
tests/test_e2e_suite.py                          # T1
tests/test_e2e_blender.py                        # T1
tests/conftest.py                                 # T1 (modify: add markers)
.github/workflows/e2e.yml                         # T1
src/hamr/blender_bridge/compat.py                 # T2
tests/blender_scripts/test_addon_registration.py  # T2
.github/workflows/blender_matrix.yml              # T2
docs/BLENDER_COMPAT.md                            # T2
src/hamr/core/benchmark.py                        # T3
tests/bench/test_bench_spec.py                   # T3
tests/bench/test_bench_forges.py                  # T3
tests/bench/test_bench_validator.py               # T3
tests/bench/test_bench_pipeline.py                # T3
benchmarks/baselines.json                         # T3
.github/workflows/benchmark.yml                   # T3
src/hamr/core/presets_v2.py                        # T4
src/hamr/core/preset_repo.py                       # T4
scripts/package_addon.py                           # T5
scripts/test_pip_install.sh                        # T5
.github/workflows/publish.yml                      # T5+T6
CHANGELOG.md                                       # T6
docs/MIGRATION_v0.5_to_v0.7.md                    # T6
scripts/cut_release.sh                             # T6
.github/workflows/docs.yml                          # T7
```

**Modified Files:**
```
src/hamr/__init__.py              # T6: version bump
src/hamr/blender_bridge/runner.py # T2: version compat checks
src/hamr/core/presets.py          # T4: backward compat + v2 migration
src/hamr/cli.py                   # T4: preset browser stub, T5: new entry points
src/hamr/core/a11y.py             # T7: a11y audit functions
src/hamr/docs/generate.py         # T7: API reference generator
pyproject.toml                    # T5: optional deps, entry points
README.md                         # T6: update
tests/conftest.py                 # T1: markers
```

---

*This architecture stands ready. Every module named, every path traced, every test tier defined. Let the horn resound.* 📯