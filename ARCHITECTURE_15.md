# Phase 15: Vápnatak — Architecture Document

> *Rúnhild Svartdóttir, The Architect*
> *System mapping and domain decomposition*

---

## 0. State of the Blade at Phase 15 Entry

**v0.7.0rc1** — 1814 tests collected, **5 fail** on full-suite run (all pass in isolation).
Root cause: `CharacterSpec.from_dict()` mutates its input dict in-place, converting
nested plain dicts stored in `CHARACTER_PRESETS` into dataclass instances (`EyeSpec`,
`SkinSpec`, etc.). When `test_pipeline_integrate.py` runs first, it poisons the global
preset store; subsequent `deepcopy()` calls inherit dataclass sub-objects that don't
support `dict` item-assignment. The fix is a defensive `deepcopy` inside `from_dict()`
and a separate immutability guard in `get_preset()`.

**54 source files** across **14 packages**. The forge is forged. Now we prove it whole.

---

## 1. Module Dependency Map — Final State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLI (hamr/cli.py)                                                         │
│  ├── cmd_build → BuildPipeline.build()                                    │
│  ├── cmd_validate → BuildPipeline.validate_only()                         │
│  ├── cmd_inspect → inspect()                                              │
│  ├── cmd_verify_rig → verify_vrm_rig()                                    │
│  ├── cmd_check_env → BuildPipeline.check_environment()                    │
│  ├── cmd_list_presets → CHARACTER_PRESETS / resolve_preset()             │
│  └── cmd_docs → generate_all()                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Core Pipeline Layer (🐍 pure Python)                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ core/spec.py      │  │ core/models.py    │  │ core/validate.py      │  │
│  │ Spec.from_yaml()  │→→│ CharacterSpec     │→→│ validate_spec()       │  │
│  │ Spec.from_dict()  │  │ BodySpec,FaceSpec │  │                       │  │
│  │ Spec.to_dict()    │  │ HairSpec,EyeSpec  │  │                       │  │
│  └──────────────────┘  └──────┬───────────┘  └───────────────────────┘  │
│                               │                                           │
│  ┌──────────────────┐  ┌──────┴──────────┐  ┌───────────────────────┐  │
│  │ core/errors.py    │  │ core/presets.py  │  │ core/builder.py       │  │
│  │ HamrError tree    │  │ CHARACTER_PRESETS │  │ build(), inspect()   │  │
│  │ SpecValidationError│  │ get_preset()      │  │ _resolve_forges()    │  │
│  │ BuildError        │  │ resolve_preset()  │  │                       │  │
│  │ ExportError       │  │ deep_merge()      │  │                       │  │
│  └──────────────────┘  │ validate_preset() │  └───────────────────────┘  │
│                         │ spec_to_dict()    │                            │
│                         │ sanitize_preset()  │                            │
│                         └──────┬───────────┘                            │
│                                │                                        │
│  ┌──────────────────┐  ┌──────┴──────────┐  ┌───────────────────────┐  │
│  │ core/constants.py │  │ core/pipeline.py  │  │ core/perf.py          │  │
│  │ BODY_PRESETS      │  │ BuildPipeline     │  │ PerformanceBudget     │  │
│  │ VRM_25_BONE_NAMES │  │ PipelineResult    │  │ check_budget()        │  │
│  │ SKIN_PALETTES     │  │                    │  │ estimate_*()          │  │
│  └──────────────────┘  └──────────────────┘  └──────────┬────────────┘  │
│                                                          │              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┴────────────┐  │
│  │ core/perf_gate.py│  │ core/gpu_profiles │  │ core/pipeline_integ. │  │
│  │ PerfGate         │  │ GPUProfile        │  │ plan_stages()        │  │
│  │ select_budget() │  │ auto_detect()     │  │ validate_completeness│  │
│  └──────────────────┘  └──────────────────┘  │ run_integration_stages│  │
│                                               └───────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ core/textures.py  │  │ core/texture_proc │  │ core/iterate.py       │  │
│  │ generate_hair_tex │  │ ProceduralTexture│  │ Spec iteration utils  │  │
│  │ hex_to_hsv()     │  │ Pipeline (PIL)    │  │                       │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ core/a11y.py      │  │ core/benchmark.py│  │ core/inspect.py       │  │
│  │ CLIOptions       │  │ Benchmark         │  │ VRM/GLB inspection    │  │
│  │ format_output()  │  │ BenchmarkResult   │  │                       │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────────┘  │
│  ┌────────────────────────┐                                              │
│  │ core/preset_versions.py │                                              │
│  │ PresetManifest, migrate │                                              │
│  │ compare_preset_versions│                                              │
│  └────────────────────────┘                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Forge Layer (🐍 pure-Python config, 🎬 Blender-dependent execution)       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐      │
│  │ hair/__init__.py │  │ face/__init__.py│  │ clothing/__init__.py  │      │
│  │ resolve_hair()   │  │ resolve_face()  │  │ resolve_clothing()   │      │
│  │ HairBuildResult  │  │ FaceBuildResult │  │ ClothingBuildResult  │      │
│  └───────┬─────────┘  └───────┬─────────┘  └──────────┬───────────┘      │
│           │                    │                        │                  │
│  ┌────────┴─────────┐  ┌──────┴──────────┐  ┌────────┴────────────┐      │
│  │ hair/mesh.py 🎬   │  │ face/expressions │  │ clothing/mesh.py 🎬  │      │
│  │ HairMeshGenerator │  │ ExpressionBinding │  │ ClothingMeshGenerator│      │
│  │ generate_guide_*  │  │ VRM expressions  │  │ estimate_tri_count  │      │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘      │
│  ┌──────────────────────────┐                                           │
│  │ body/__init__.py, forge.py│  (temporal — merging into core)           │
│  │ body/presets.py           │                                           │
│  └──────────────────────────┘                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Rigs Layer (🐍 data + 🎬 action)                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐        │
│  │ rigs/verify.py 🐍│  │ rigs/stub_bones │  │ rigs/weights.py 🎬  │        │
│  │ RigVerifier      │  │ detect_missing 🐍│  │ WeightPaintEngine   │        │
│  │ check_naming*()  │  │ create_missing 🎬│  │ paint_*()           │        │
│  └─────────────────┘  └─────────────────┘  └────────────────────┘        │
│  ┌─────────────────┐  ┌─────────────────┐                                 │
│  │ rigs/collision 🐍│ │ rigs/spring_bones│                                 │
│  │ CollisionMeshGen│ │ configure_* 🐍    │                                 │
│  │                 │  │ apply_* 🎬       │                                 │
│  └─────────────────┘  └─────────────────┘                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Blender Bridge (🎬 requires bpy)                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐        │
│  │ bridge/runner.py│  │ bridge/compat.py │  │ bridge/scene.py     │        │
│  │ run_blender_*() │  │ BLENDER_COMPAT_* │  │ clean_blend_*()     │        │
│  │ check_available │  │ check_version()  │  │ scene utilities     │        │
│  └─────────────────┘  └─────────────────┘  └────────────────────┘        │
│  ┌─────────────────┐  ┌─────────────────┐                                 │
│  │ bridge/mesh_ops │  │ scripts/         │                                 │
│  │ Mesh operations  │  │ build_avatar.py │                                 │
│  └─────────────────┘  └─────────────────┘                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Export Layer (🐍 pure-Python validation + 🎬 Blender export)               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐        │
│  │ export/vrm.py 🎬│  │ export/vrm_valid │  │ export/first_person│        │
│  │ VRM export ops  │  │ VRMValidator 🐍  │  │ FirstPersonConfig   │        │
│  │                 │  │ validate() 🐍    │  │ classify_mesh 🐍    │        │
│  └─────────────────┘  └─────────────────┘  │ configure 🎬         │        │
│  ┌─────────────────┐  ┌─────────────────┐  └────────────────────┘        │
│  │ export/glb.py 🎬│  │ export/anim_clip │                                 │
│  │ GLB export      │  │ AnimationClip 🐍 │                                 │
│  │                 │  │ create_clip()    │                                 │
│  └─────────────────┘  └─────────────────┘                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Materials & Docs (🐍 pure Python)                                         │
│  ┌──────────────────┐  ┌───────────────────────────────────────┐         │
│  │ materials/anime.py│  │ docs/generate.py, docs/a11y_audit.py   │         │
│  │ AnimeMaterialSpec │  │ generate_cli_reference()               │         │
│  │ AnimeMatGenerator│  │ generate_api_reference()               │         │
│  └──────────────────┘  │ generate_architecture_diagram()        │         │
│                         └───────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dependency Arrow Summary (what imports what)

```
cli → core/pipeline → {core/spec, core/validate, core/builder, core/errors,
                        core/perf, core/perf_gate, core/pipeline_integrate,
                        blender_bridge/runner}
core/builder → {hair, face, clothing, core/perf}
core/pipeline_integrate → {rigs/*, hair/mesh, clothing/mesh, export/first_person,
                            core/models, core/perf}
core/presets → {core/models}
core/validate → {core/constants, core/models}
blender_bridge/runner → {blender_bridge/compat}
scripts/build_avatar → {all forge modules, rigs/*, export/*}
export/vrm_validator → {pure glTF binary parsing, zero bpy}
```

### Layer Boundary Table

| Layer | Module(s) | bpy Dep? | Testable Without Blender? |
|-------|-----------|----------|--------------------------|
| **Spec** | core/spec, core/models, core/errors, core/constants | ✗ No | ✅ Fully |
| **Presets** | core/presets, core/preset_versions | ✗ No | ✅ Fully (after bugfix) |
| **Validation** | core/validate, core/perf, core/perf_gate, core/gpu_profiles | ✗ No | ✅ Fully |
| **Forge (config)** | hair/\_\_init\_\_, face/\_\_init\_\_, clothing/\_\_init\_\_ | ✗ No | ✅ Fully |
| **Forge (mesh)** | hair/mesh, clothing/mesh | ✓ Yes | ⚠️ Partial |
| **Body** | body/forge, body/presets | ✗ No | ✅ Fully |
| **Rigs (data)** | rigs/verify, rigs/collision, rigs/stub_bones (detect) | ✗ No | ✅ Fully |
| **Rigs (action)** | rigs/weights, rigs/spring_bones (apply), rigs/stub_bones (create) | ✓ Yes | ❌ Needs Blender |
| **Materials** | materials/anime | ✓ Yes | ⚠️ Partial |
| **Pipeline** | core/pipeline, core/pipeline_integrate, core/builder | ✗ No | ✅ Partial |
| **Bridge** | blender_bridge/* | ✓ Yes | ❌ Needs Blender |
| **Build Script** | scripts/build_avatar | ✓ Yes | ❌ Needs Blender |
| **Export (data)** | export/vrm_validator, export/animation_clips, export/first_person (classify) | ✗ No | ✅ Fully |
| **Export (action)** | export/vrm, export/glb, export/first_person (configure) | ✓ Yes | ❌ Needs Blender |
| **CLI** | cli | ✗ No | ✅ Fully (unit) |
| **Docs** | docs/* | ✗ No | ✅ Fully |

---

## 2. Task Decomposition (T1–T7)

### T1 — The Five Nicks: Preset Validation Bugfix (15.4)

**Root cause:** `CharacterSpec.from_dict()` mutates the input dict by converting nested
dicts to dataclass instances in-place. After `test_pipeline_integrate.py` calls
`CharacterSpec.from_dict(CHARACTER_PRESETS["chibi_cute"]["spec"])`, the global preset's
nested `"eyes"` sub-dict becomes an `EyeSpec` dataclass. Subsequent `deepcopy()` copies
the dataclass, and `spec["face"]["eyes"]["size"] = 5.0` raises `TypeError` because
dataclasses don't support item assignment.

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T1.1 | `src/hamr/core/models.py` | `CharacterSpec.from_dict()` — wrap input in `deepcopy()` before mutation | No |
| T1.2 | `src/hamr/core/presets.py` | `get_preset()` — ensure `deepcopy(entry["spec"])` produces a plain dict, not nested dataclasses; add `_freeze_preset()` guard | No |
| T1.3 | `src/hamr/core/presets.py` | `resolve_preset()` — call `spec_to_dict()` on result before returning to ensure callers always get plain dicts | No |
| T1.4 | `tests/test_presets.py` | Add regression test: `test_deepcopy_after_pipeline_integrate_unchanged` — verify CHARACTER_PRESETS not mutated after CharacterSpec.from_dict | No |
| T1.5 | `tests/test_pipeline_integrate.py` | Add `test_from_dict_does_not_mutate_input` — prove `CharacterSpec.from_dict()` is pure | No |
| T1.6 | `src/hamr/core/presets.py` | `deep_merge()` — add `isinstance(value, dict)` guard to handle dataclass objects that are not Mapping | No |
| T1.7 | Run full suite: `pytest tests/ -x` — confirm 5 failures are now 0 | No |

**Verification:** `pytest tests/ -x` → 1814 passed, 0 failed, 12 skipped.

---

### T2 — Eitri's Anvil: E2E Blender Headless Builds (15.1)

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T2.1 | `tests/test_e2e_blender.py` (NEW) | `class TestBlenderE2E`; `test_full_pipeline_anime_girl_default()`, `test_full_pipeline_anime_boy_warrior()`, `test_full_pipeline_chibi_cute()` | Yes |
| T2.2 | `tests/test_e2e_blender.py` | `test_all_presets_produce_vrm()` — iterate CHARACTER_PRESETS, build each, validate with VRMValidator | Yes |
| T2.3 | `tests/test_e2e_blender.py` | `test_weight_transfer_preserves_bone_count()`, `test_spring_bones_attached()` | Yes |
| T2.4 | `tests/test_e2e_suite.py` (MODIFY) | Add `test_spec_to_vrm_roundtrip_mocked()` — mocked full pipeline Tier 2 test | No |
| T2.5 | `tests/conftest.py` (MODIFY) | Add `@pytest.mark.blender_e2e` marker; register in `pytest_collection_modifyitems` | — |
| T2.6 | `tests/conftest.py` | Add `blender_env` fixture that checks for Blender binary and skips if absent | — |
| T2.7 | `src/hamr/blender_bridge/runner.py` (MODIFY) | `run_blender_script()` — add `--headless` flag passthrough, timeout guard, structured JSON output parsing | No (subprocess) |

---

### T3 — Heimdall's Watch: GitHub Actions CI/CD Pipeline (15.2)

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T3.1 | `.github/workflows/ci.yml` (NEW) | **Lint → Unit → Integration** matrix: `{python: [3.10, 3.11, 3.12]} × {os: [ubuntu-latest, macos-latest]}` | — |
| T3.2 | `.github/workflows/ci.yml` | **E2E Blender stage**: `ubuntu-latest` with Blender 4.2 LTS install, `--run-blender` flag | — |
| T3.3 | `.github/workflows/ci.yml` | **ARM64 cross-build**: QEMU + `aarch64` emulation for Pi compatibility; `pip install hamr[core]` smoke test | — |
| T3.4 | `.github/workflows/ci.yml` | **Benchmark gate**: `--run-benchmarks` job; compare against `benchmarks/baselines.json`; fail on >5% regression | — |
| T3.5 | `.github/workflows/ci.yml` | Branch protection: `main` and `release/*` branches require all status checks green; no direct push | — |
| T3.6 | `.github/workflows/ci.yml` | Artifact uploads: test results XML, benchmark JSON, coverage HTML on success | — |
| T3.7 | `scripts/install_blender_ci.sh` (NEW) | Download + install Blender 4.2 LTS on CI, add VRM addon | — |

---

### T4 — Mímir's Measure: Performance Regression Baselines (15.3)

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T4.1 | `src/hamr/core/benchmark.py` (MODIFY) | `class Benchmark` — add `compare_to_baseline()`, `threshold_pct` param, `regression_detected()` | No |
| T4.2 | `tests/bench/test_bench_spec.py` (MODIFY) | `bench_spec_parse()`, `bench_validate()` — capture timing for all 6 presets | No |
| T4.3 | `tests/bench/test_bench_forges.py` (MODIFY) | `bench_resolve_hair()`, `bench_resolve_face()`, `bench_resolve_clothing()` — add regression assertions | No |
| T4.4 | `tests/bench/test_bench_validator.py` (MODIFY) | `bench_vrm_validate_small()`, `bench_vrm_validate_large()` | No |
| T4.5 | `tests/bench/test_bench_pipeline.py` (MODIFY) | `bench_pipeline_dry_run()` — full spec→json dry run timing | No |
| T4.6 | `benchmarks/baselines_v070.json` (NEW) | Baseline timing JSON: `{"spec_parse": 0.002, ...}` for Pi ARM64 and x86_64 | — |
| T4.7 | `benchmarks/baselines.json` (MODIFY) | Add `platform` and `timestamp` fields; separate ARM64 vs x86_64 entries | — |

**Baseline Capture Strategy:**
- Run on Pi 5 ARM64 (this machine) and capture reference timings
- Run on GitHub Actions `ubuntu-latest` (x86_64) for cross-platform baseline
- Threshold: **±10% on ARM64**, ±5% on x86_64 (Pi has more variance)

---

### T5 — Bifröst Bridge: Release Artifact Pipeline (15.5)

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T5.1 | `pyproject.toml` (MODIFY) | Add `[tool.hatch.build.targets.wheel]` config; ensure `hamr[core]` and `hamr[dev]` optional deps are clean | — |
| T5.2 | `.github/workflows/publish.yml` (NEW/UPDATE) | On tag push `v*`: build wheel + sdist, `twine check`, upload artifact, publish to TestPyPI | — |
| T5.3 | `.github/workflows/publish.yml` | ARM64 wheel build via QEMU + `cibuildwheel`; ensure `numpy` and `Pillow` wheels exist for aarch64 | — |
| T5.4 | `scripts/package_addon.py` (NEW) | `package_blender_addon()` — zip Hamr's blender_bridge + scripts for Blender addon install | No |
| T5.5 | `scripts/checksum_manifest.py` (NEW) | `generate_checksums()` — SHA-256 for every release artifact; write to `dist/checksums.txt` | No |
| T5.6 | `.github/workflows/publish.yml` | GPG signing of checksum manifest; `cosign` signing for container images if any | — |
| T5.7 | `scripts/test_pip_install.sh` (MODIFY) | Test both `pip install hamr` (x86_64) and ARM64 cross-install | — |

---

### T6 — Rúnakefli: Documentation Hardening & Changelog (15.6)

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T6.1 | `CHANGELOG.md` (NEW/MODIFY) | Aggregate Phase 7–15 entries; follow Keep a Changelog format; include migration notes | — |
| T6.2 | `docs/MIGRATION_v0.5_to_v0.7.md` (MODIFY) | Update for final v0.7.0 API surface; add note about `CharacterSpec.from_dict()` immutability fix | — |
| T6.3 | `README.md` (MODIFY) | Add: build output screenshots, CLI usage examples, Pi install section, badge row (CI, version, license) | — |
| T6.4 | `docs/API_REFERENCE.md` (MODIFY) | Auto-generate from docstrings via `hamr docs generate`; verify all public symbols | — |
| T6.5 | `src/hamr/core/models.py` (MODIFY) | Audit all docstrings for imperative mood, Google style, `Args:`/`Returns:` sections | No |
| T6.6 | `src/hamr/core/presets.py` (MODIFY) | Audit docstrings; add `Note:` to `from_dict()` about immutability guarantee | No |
| T6.7 | `docs/BLENDER_COMPAT.md` (NEW) | Blender 4.2/4.3/4.4 compatibility matrix, known issues, VRM addon versions | — |

---

### T7 — Vápnatak Review: Full-Pipeline Validation & Release Candidate Promotion (15.7)

| Subtask | File | Function/Class | bpy? |
|---------|------|-----------------|------|
| T7.1 | `src/hamr/__init__.py` (MODIFY) | `__version__ = "0.7.0"` (drop rc1 suffix) | — |
| T7.2 | `scripts/cut_release.sh` (MODIFY) | `git tag v0.7.0` on `main`; `gh release create v0.7.0` with changelog and artifacts | — |
| T7.3 | Run full CI green: `pytest tests/ --tb=short` → 0 failures | — |
| T7.4 | Run benchmark regression gate: `pytest tests/bench/ --run-benchmarks` → all within tolerance | — |
| T7.5 | Run `pip install -e . && hamr validate --help` → non-zero exit only on real errors | — |
| T7.6 | Tag and push: `git tag v0.7.0 && git push origin main --tags` | — |
| T7.7 | Post-release verification: `pip install hamr==0.7.0 && python -c "import hamr; print(hamr.__version__)"` → `0.7.0` | — |

---

## 3. CI/CD Strategy

### 3.1 GitHub Actions Workflow: `.github/workflows/ci.yml`

```yaml
name: Hamr CI — Vápnatak

on:
  push:
    branches: [main, develop, 'release/**']
  pull_request:
    branches: [main]

jobs:
  # ── Stage 1: Lint ────────────────────────────────────────────────────
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff mypy
      - run: ruff check src/ tests/
      - run: mypy src/hamr --ignore-missing-imports --no-error-on-untyped

  # ── Stage 2: Unit + Integration Tests ────────────────────────────────
  test:
    needs: lint
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -x --tb=short -q --junitxml=test-results.xml
      - uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.os }}-py${{ matrix.python-version }}
          path: test-results.xml

  # ── Stage 2b: ARM64 Cross-Build (Raspberry Pi Compatibility) ─────────
  test-arm64:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
        with: { platforms: linux/arm64 }
      - uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/arm64
          build-args: |
            PYTHON_VERSION=3.11
          file: Dockerfile.ci-arm64
          push: false
          load: true
          tags: hamr-arm64-test
      # Run tests inside the ARM64 container
      - run: |
          docker run --rm hamr-arm64-test \
            pip install -e ".[dev]" && \
            pytest tests/ -x --tb=short -q --ignore=tests/test_e2e_blender.py

  # ── Stage 3: E2E Blender Tests (Headless) ───────────────────────────
  blender-e2e:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install Blender 4.2 LTS
        run: bash scripts/install_blender_ci.sh
      - run: pip install -e ".[dev]"
      - run: pytest tests/test_e2e_blender.py --run-blender --tb=short
      - uses: actions/upload-artifact@v4
        with:
          name: blender-e2e-results
          path: test-results-blender.xml

  # ── Stage 4: Benchmark Regression Gate ───────────────────────────────
  benchmark:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/bench/ --run-benchmarks --benchmark-compare=benchmarks/baselines_v070.json
      - uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: benchmarks/

  # ── Stage 5: Coverage Report ────────────────────────────────────────
  coverage:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]" pytest-cov
      - run: pytest tests/ --cov=hamr --cov-report=html --cov-report=term-missing
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/
```

### 3.2 ARM64 Dockerfile for CI

```dockerfile
# Dockerfile.ci-arm64
FROM python:3.11-slim-bookworm AS arm64-test
WORKDIR /hamr
COPY . .
RUN pip install -e ".[dev]"
CMD ["pytest", "tests/", "-x", "--tb=short", "-q"]
```

### 3.3 Branch Protection Rules

- `main`: Require 2 approving reviews, all status checks must pass (lint, test, blender-e2e, benchmark)
- `release/*`: Same as `main` + tag protection
- No direct pushes to `main`; all changes via PR

---

## 4. Release Readiness Audit Checklist

Every item must be ✅ before v0.7.0 can be tagged.

### 4.1 Code Quality — The Blade Must Be Whole

- [ ] **All 1819 tests pass** (`pytest tests/ -x`) — 0 failures, 0 errors
- [ ] **No test order-dependency bugs** — full suite produces same results as individual files
- [ ] **`CharacterSpec.from_dict()` immutability fix landed** — input dicts never mutated
- [ ] **`deep_merge()` handles mixed dict/dataclass inputs** — no `TypeError` on item assignment
- [ ] **No `import bpy` in pure-Python modules** — grep audit confirms core/, hair/\_\_init\_\_, face/\_\_init\_\_, clothing/\_\_init\_\_, rigs/verify, export/vrm_validator have zero bpy imports
- [ ] **All modules have `__init__.py` with `__all__`** — consistent public API surface
- [ ] **Type annotations complete** on all public functions (`mypy src/hamr --ignore-missing-imports` passes)
- [ ] **Ruff lint clean** (`ruff check src/ tests/`)
- [ ] **No `TODO`, `HACK`, or `XXX` comments** remaining in production code
- [ ] **Decision log entries** (D-020 through D-026 for Phase 15) documented

### 4.2 Integration — The Blade Must Cut True

- [ ] **E2E spec→validation→forge→JSON round-trip** passes for all 6 built-in presets
- [ ] **E2E pipeline dry-run** (mocked Blender) completes without errors
- [ ] **E2E Blender build** produces valid VRM for at least 1 preset on Blender 4.2 LTS
- [ ] **VRM validator** passes on all generated VRM files
- [ ] **Performance budget check** gates builds correctly (over-budget → exit code 3)
- [ ] **CLI all commands work**: `build`, `validate`, `inspect`, `list-presets`, `verify-rig`, `check-env`, `version`, `docs generate`
- [ ] **No benchmark regressions**: all metrics within ±10% on ARM64, ±5% on x86_64

### 4.3 CI/CD — The Watch Must Never Sleep

- [ ] **GitHub Actions CI workflow** runs green on all matrix combinations
- [ ] **ARM64 cross-build** passes in QEMU emulation
- [ ] **E2E Blender stage** runs and passes on GitHub Actions
- [ ] **Benchmark gate** runs and passes within tolerance
- [ ] **Branch protection** enabled on `main` requiring all checks
- [ ] **Artifact uploads** working: test results, coverage, benchmark JSON

### 4.4 Packaging — The Blade Must Leave the Forge

- [ ] **`pip install hamr`** in fresh venv succeeds, brings in core dependencies only
- [ ] **`pip install hamr[dev]`** brings in pytest, ruff, mypy
- [ ] **CLI entry points work**: `hamr validate --help`, `hamr verify-rig --help`
- [ ] **Blender addon zip** packages correctly with `scripts/package_addon.py`
- [ ] **Package imports cleanly**: `python -c "import hamr; print(hamr.__version__)"` → `0.7.0`
- [ ] **ARM64 wheel** builds and installs on Pi 5 / aarch64
- [ ] **Checksum manifest** generated for all release artifacts

### 4.5 Documentation — The Rune Must Be Readable

- [ ] **API reference** auto-generated from docstrings (`hamr docs generate`)
- [ ] **Architecture diagram** renders correctly (Mermaid in this file)
- [ ] **CLI reference** documents all subcommands and flags
- [ ] **README.md** updated with v0.7.0 features, screenshots, Pi install section
- [ ] **CHANGELOG.md** covers Phases 7–15
- [ ] **Migration guide** from v0.5.x to v0.7.0
- [ ] **Blender compatibility matrix** documented (BLENDER_COMPAT.md)
- [ ] **All docstrings use imperative mood**, Google style, with `Args:`/`Returns:`

### 4.6 Accessibility — The Blade Must Be Wielded by All

- [ ] **All CLI output works with `--no-color`** — no info lost when ANSI is stripped
- [ ] **All CLI output works with `--json`** — machine-parseable JSON for every command
- [ ] **Screen-reader mode**: `--quiet` suppresses progress bars and decorative output
- [ ] **WCAG 2.1 AA contrast ratios** for ANSI color output (4.5:1 minimum)
- [ ] **Keyboard-only operation**: every CLI task achievable without mouse/pointer

### 4.7 Security & Legal — The Blade Must Be Clean

- [ ] **No secrets in code** — `.gitignore` covers `.env`, `*.key`, `*.pem`
- [ ] **LICENSE file** present and correct (MIT)
- [ ] **Third-party attributions** in NOTICE or third-party-licenses
- [ ] **SBOM** generated for PyPI package dependencies

### 4.8 Release Mechanics — The Blade Is Declared Ready

- [ ] **Version bump** in `src/hamr/__init__.py`: `__version__ = "0.7.0"`
- [ ] **Git tag**: `v0.7.0` on `main` branch
- [ ] **GitHub Release** created with changelog and artifacts
- [ ] **TestPyPI** publish succeeds: `pip install --index-url https://test.pypi.org/simple hamr==0.7.0`
- [ ] **PyPI** publish succeeds: `pip install hamr==0.7.0`
- [ ] **Community announcement** on Discord/GitHub Discussions

---

## Appendix A: The Five Nicks — Failure Root-Cause Analysis

```
Test: test_eye_size_out_of_range
Test: test_invalid_hex_color
Test: test_hair_color_invalid_hex
Test: test_tan_level_out_of_range
Test: test_preset_override_hair_style

Symptom: TypeError: 'EyeSpec' object does not support item assignment
Trigger: test_pipeline_integrate.py → CharacterSpec.from_dict(preset_spec_dict)
Root Cause: CharacterSpec.from_dict() mutates input dict by replacing nested
            plain dicts with dataclass instances (EyeSpec, SkinSpec, etc.)
 cascade: After mutation, CHARACTER_PRESETS["chibi_cute"]["spec"]["face"]["eyes"]
          becomes an EyeSpec dataclass instead of a plain dict.
Resolution: deep_copy the input in from_dict() before any mutation.
            Guard get_preset() to always return plain-dict specs.
            Ensure resolve_preset() unwraps any dataclass leakage.
```

## Appendix B: File Change Map

**New Files (T1–T7):**
```
.github/workflows/ci.yml                          # T3
.github/workflows/publish.yml                     # T5
scripts/install_blender_ci.sh                     # T3
scripts/package_addon.py                          # T5
scripts/checksum_manifest.py                      # T5
scripts/cut_release.sh                            # T7
Dockerfile.ci-arm64                                # T3
benchmarks/baselines_v070.json                     # T4
tests/test_e2e_blender.py                         # T2
docs/BLENDER_COMPAT.md                            # T6
CHANGELOG.md                                       # T6
```

**Modified Files (T1–T7):**
```
src/hamr/__init__.py                               # T7: version bump 0.7.0rc1 → 0.7.0
src/hamr/core/models.py                            # T1: from_dict() immutability fix
src/hamr/core/presets.py                           # T1: deep_merge guard, get_preset, resolve_preset
src/hamr/blender_bridge/runner.py                  # T2: headless flag, timeout, JSON output
src/hamr/core/benchmark.py                         # T4: compare_to_baseline(), threshold_pct
tests/test_presets.py                              # T1: regression test for mutation bug
tests/test_pipeline_integrate.py                   # T1: from_dict immutability test
tests/test_e2e_suite.py                            # T2: additional mock roundtrip test
tests/conftest.py                                  # T2: blender_e2e marker, blender_env fixture
tests/bench/test_bench_spec.py                     # T4: regression assertions
tests/bench/test_bench_forges.py                   # T4: regression assertions
tests/bench/test_bench_validator.py                # T4: update
tests/bench/test_bench_pipeline.py                 # T4: update
pyproject.toml                                     # T5: wheel config, optional deps
README.md                                          # T6: screenshots, Pi section, badges
docs/MIGRATION_v0.5_to_v0.7.md                     # T6: from_dict note
docs/API_REFERENCE.md                              # T6: regenerate
```

---

*This architecture is the whetstone. Every edge drawn across it, proved. Every guard tested. The host takes up its arms and knows them sound. Vápnatak — the blade is declared whole.* ⚔️