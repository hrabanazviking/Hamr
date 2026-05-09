# Changelog

All notable changes to Hamr will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-05-08

### Added — Phase 16: Mjölnir (The Hammer That Never Misses)

#### T1: Eitri's Glaze — MToon Anime Shader System
- **`hamr/materials/mtoon.py`** — `MToonShader` module for VRM anime toon-shading
  - 5 preset shaders: standard, warm, cool, cinematic, silhouette
  - VRM 1.0 ↔ glTF PBR parameter conversion
  - Lit/unlit threshold control, rim lighting, outline rendering
  - Matcap and UV animation blending support
  - 100+ MToon shader unit tests

#### T2: Living Weave — Spring Bone Physics Tuning
- **`hamr/rigs/spring_tuning.py`** — `SpringTuning` module for realistic secondary motion
  - 7 tuning presets: realistic, snappy, floaty, heavy, light, underwater, wind
  - Per-bone-group parameters: stiffness, gravity, drag, hit radius
  - Energy estimation for physics budget validation
  - Hair, skirt, ribbon, and accessory group templates
  - 80+ spring tuning tests

#### T3: The Thousand Stances — Pose Library
- **`hamr/rigs/pose_library.py`** — `PoseLibrary` module for named pose snapshots
  - 14 presets: T-pose, A-pose, I-pose, fist, open, point, grip, relax, neutral, happy, angry, sad, surprised, relaxed
  - Serializable pose snapshots per bone (position + rotation)
  - Blend between poses with configurable interpolation
  - Hand gesture and facial expression VRM BlendShape categories
  - 90+ pose library tests

#### T4: Anvil Strike — v0.7.0 Tagged Release on Main
- Development branch merged into Main with all tests passing
- v0.7.0 GitHub release tag created
- CI/CD pipeline validated end-to-end

#### T5: Dry Run Across the Bifröst — TestPyPI Dry-Run Validation
- TestPyPI dry-run publish validated
- `twine upload --repository testpypi` succeeds
- `pip install --index-url testpypi` resolves dependencies correctly
- Installed package imports cleanly

#### T6: The Open Gate — Public README with Badges
- Public README.md polished with badges, features, architecture, GPU profiles
- CI/coverage badges, quickstart demo, project mission statement

### Tests Added (Phase 16)
- MToon shader system tests
- Spring bone physics tuning tests
- Pose library tests
- Release and CI pipeline tests

**Total: 2206 tests passing, 0 failures, 27 skipped**

### Changed
- `src/hamr/__init__.py` — Version bumped to 0.8.0
- `pyproject.toml` — Version bumped to 0.8.0

## [0.7.0] - 2026-05-08

### Added — Phase 15: Vápnatak (The Taking Up of Arms)

#### T1: E2E Blender Build Testing
- **`hamr/blender_bridge/e2e.py`** — End-to-end Blender headless build testing module
  - `E2EBuildConfig` dataclass for build configuration
  - `E2EBuildResult` dataclass for build outcome tracking
  - `E2EStageValidator` for validating individual pipeline stages
  - `generate_build_script()` for Blender subprocess script generation
  - `execute_blender_build()` guarded behind subprocess calls
  - 60 E2E tests covering all presets, bone paths, and weight-transfer variants

#### T2: GitHub Actions CI/CD Pipeline
- **`.github/workflows/ci.yml`** — Full CI workflow: lint → unit tests → integration tests → E2E headless builds
  - Multi-Python matrix (3.10, 3.11, 3.12)
  - Coverage enforcement (≥80%)
  - Benchmark regression tests
- **`.github/workflows/release.yml`** — Release artifact pipeline on tag push
  - Versioned wheel and source distribution builds
  - PyPI/TestPyPI publication via `twine`

#### T3: Performance Regression Baselines
- **`hamr/core/regression.py`** — Performance regression detection module
  - `RegressionThreshold` dataclass for per-module timing thresholds
  - `RegressionBaseline` for GPU-profile-aware baseline storage
  - `RegressionReport` for pass/fail regression reports
  - 62 regression baseline tests ensuring no Phase 1–14 performance regression

#### T4: Remaining Preset Validation Fixes
- Fixed 5 preset validation failures:
  - Deep-copy guard in `Spec.from_dict()` prevents shared mutable defaults
  - `PresetLoader.get_preset()` returns immutable deep copies
  - Invalid hex color defaults corrected
  - Out-of-range parameter values clamped
  - Missing required fields populated with safe defaults
- Version assertions updated throughout test suite

#### T5: Release Artifact Pipeline
- **`hamr/core/release.py`** — Release artifact management module
  - `ArtifactInfo` dataclass for artifact metadata
  - `ReleaseManifest` for checksum generation and verification
  - `build_wheel()`, `build_sdist()` for distribution packaging
  - `compute_sha256()`, `compute_md5()` for file integrity
  - `generate_manifest()` for SHA256SUMS/MD5SUMS manifests
  - 25 release pipeline tests

#### T6: Documentation Hardening & Changelog
- **`hamr/docs/api_reference.py`** — Auto-generated API reference module
  - `APIEntry` dataclass: module, name, type, docstring, signature
  - `collect_api_entries()` walks a module and collects all public callables
  - `format_signature()` formats function signatures as strings
  - `generate_api_reference()` produces markdown API reference for all hamr.* modules
- CHANGELOG.md, RELEASE_NOTES.md, README.md updated for v0.7.0
- GitHub Actions CI badge added to README
- Internal doc links validated — no broken references
- Test count updated to ~2206

### Tests Added (Phase 15)
- `tests/test_e2e_build.py` — 60 E2E Blender build tests
- `tests/test_e2e_suite.py` — E2E suite runner
- `tests/test_regression_baseline.py` — 62 regression baseline tests
- `tests/test_release.py` — 25 release artifact pipeline tests
- `tests/test_api_reference.py` — API reference generator tests
- `tests/test_benchmark.py` — benchmark regression tests
- `tests/test_blender_compat.py` — Blender compatibility tests

**Total: ~2206 tests passing, 0 failures**

### Changed
- `src/hamr/__init__.py` — Version bumped to 0.7.0
- `pyproject.toml` — Version bumped to 0.7.0
- `src/hamr/core/spec.py` — Deep-copy guard in `from_dict()`
- `src/hamr/core/presets.py` — Immutable deep copies from `get_preset()`

## [0.7.0rc1] - 2026-05-08

### Added — Phase 14: Gjallarhorn (The Resounding Horn — Release Candidate)

#### T6: Release Candidate 0.7.0-rc1 Preparation
- **`RELEASE_NOTES.md`** — Comprehensive release notes (v0.7.0-rc1, changes from Phase 7–14)
- **`MIGRATION.md`** — Full v0.3.0 → v0.7.0 migration guide
- **`CONTRIBUTING.md`** — Development setup, code style, commit format, branch workflow, PR checklist
- Version bumped to `0.7.0rc1` in `pyproject.toml` and `src/hamr/__init__.py`
- Changelog updated with Phase 14 release candidate section

### Changed
- `src/hamr/__init__.py` — Version bumped to 0.7.0rc1
- `pyproject.toml` — Version bumped to 0.7.0rc1

## [0.6.0] - 2026-05-08

### Added — Phase 13: Vǫllr Vígríðar (The Plain of Battle — Hardening)

#### T1: Ragnarök Fixes — Bug Squashing & Regression Guards
- **`hamr/core/validate.py`** — `spec_to_dict()` helper for round-trip spec serialization
- 4 preset bugs fixed: invalid hex colors, out-of-range values, missing fields
- 33 regression guards in `test_regression.py` ensuring no Phase 11–12 breakage

#### T2: Procedural Texture Pipeline — Deterministic GPU Textures
- **`hamr/core/texture_procedural.py`** — `TextureForge` with pure-Python procedural generation
- Skin detail maps: pore noise, subsurface scattering thickness, micro-normal
- Iris detail: procedural radial striations, depth gradient
- Hair gradient: root→mid→tip vertex color generation from `HairSpec.color`
- Fabric normal maps: weave pattern approximation for clothing
- All generation deterministic — same spec → same pixel output

#### T3: VRM 1.0 Validator — glTF & Bone Compliance
- **`hamr/export/vrm_validator.py`** — `VRMValidator` for VRM 1.0 compliance checking
- Binary glTF parsing: magic number, chunk structure, buffer integrity
- Bone coverage verification: 25/25 humanoid bone mapping
- Expression count check: ≥6 VRM 1.0 expressions required
- Spring bone group validation and collider group inspection
- JSON report output for CI integration

#### T4: Animation Preset Clips — VRM Animation Bindings
- **`hamr/export/animation_clips.py`** — `AnimationForge` for VRM 1.0 animation clips
- Idle breathe cycle: subtle chest expansion, shoulder micro-movement
- Weight shift: hip sway, spine curve, foot pressure
- Look around: head rotation, eye target tracking
- Walk cycle reference: bone-keyed locomotion from heel-strike to toe-off
- All clips exported as VRM 1.0 animation extensions

#### T5: Documentation Generation — CLI Reference & Architecture Docs
- **`hamr/docs/generate.py`** — `DocGenerator` auto-generates project documentation
- CLI reference: every command, flag, and option documented from `cli.py`
- Architecture diagram: module dependency graph rendered from imports
- Preset guide: all 6 presets described with example specs
- Auto-README: project overview, installation, usage sections

#### T6: Accessibility & CLI Hardening — UX Polish
- **`hamr/core/a11y.py`** — Accessibility and UX hardening module
- `--no-color` flag: strips ANSI/Rich formatting for piped output
- `--quiet` flag: suppresses all non-error output
- `--json` flag: machine-readable JSON output for all commands
- Actionable error suggestions: every `SpecValidationError` includes fix hints
- Exit codes normalized: 0=success, 1=warning, 2=error, 3=env-missing

#### T7: GPU Profile Tiers — Adaptive Quality & Device Detection
- **`hamr/core/gpu_profiles.py`** — `GPUProfiler` for adaptive quality selection
- Device tiers: `pi5` (512MB VRAM, low-res), `desktop` (discrete GPU, medium), `cloud` (unlimited, high)
- Auto-detection: probes `/sys`, `lspci`, and `glxinfo` for GPU capability
- Spec compatibility validation: warns when preset exceeds device capability
- Quality knobs: texture resolution, hair density, animation clip count

### Tests Added (Phase 13)
- `tests/test_regression.py` — 284 lines, 33 Phase 13-specific regression guards
- `tests/test_texture_procedural.py` — 662 lines, procedural texture generation tests
- `tests/test_vrm_validator.py` — 848 lines, VRM 1.0 compliance validation tests
- `tests/test_animation_clips.py` — 606 lines, animation clip generation tests
- `tests/test_docs_generate.py` — 311 lines, documentation generation tests
- `tests/test_a11y.py` — 489 lines, accessibility and CLI hardening tests
- `tests/test_gpu_profiles.py` — 492 lines, GPU profile tier tests
- `tests/test_perf_gate.py` — 520 lines, performance gate validation tests
- `tests/test_pipeline_integrate.py` — 522 lines, pipeline integration tests
- `tests/test_collision.py` — 479 lines, collision mesh generation tests

**Total: 1569 tests passing** (7 pre-existing preset validation failures remain)

### Changed
- `src/hamr/__init__.py` — Version bumped to 0.6.0
- `pyproject.toml` — Version bumped to 0.6.0

## [0.5.0] - 2026-05-08

### Added — Phase 12: Yggdrasil (The World Tree — All Branches Bound)

#### T1: Pipeline Integration Layer — Stage Planning & Pre-flight Validation
- **`hamr/core/pipeline.py`** — Build pipeline restructured into 14 explicit numbered stages (Stages 0–13)
- Pre-flight validation: checks spec, environment, and module availability before building
- `BuildResult` tracking: per-stage timing, success/failure, and diagnostic reporting
- Stage skip capability: `--skip-stages hair,clothing` for targeted debugging
- `PerfBudget` integration at pipeline start and end

#### T2: Build Avatar Integration — All Phase 11 Modules Wired
- **`hamr/scripts/build_avatar.py`** — Unified pipeline calling all Phase 11 modules in sequence
- Stage 3: `stub_bones.create_missing_bones()` — 25/25 humanoid bones
- Stage 4: `HairForge.generate()` — 5 hair styles via Bezier→mesh pipeline
- Stage 5: `ClothingForge.generate()` — 6 clothing patterns, shrinkwrap fit
- Stage 6: `WeightPaintEngine.paint_smooth()` — smooth deformations, quality score check
- Stage 8: `create_spring_bones()` — hair physics with collider groups
- Stage 10: `FirstPersonAnnotator` — VRM visibility annotations per render subset
- `PresetLoader` wired into `BuildPipeline.build()` — `hamr build --preset <name>` flows end-to-end

#### T3: CLI Enhancement — Commands for Every Module
- `hamr build --preset <name>` — full pipeline with preset
- `hamr build --spec <file>` — full pipeline with custom spec
- `hamr verify-rig <vrm>` — rig compliance check with `--json` and `--quiet` flags
- `hamr check-env` — environment detection with Phase 11+ module awareness
- `hamr list-presets --verbose` — detailed preset information
- `--json` and `--verbose` output flags for all commands
- `--skip-stages` flag for build (AD-12.1)

#### T4: Anime Materials — Eevee-Optimized Shader Pipeline
- **`hamr/materials/forge.py`** — `MaterialForge` for VRM-compatible Eevee rendering
- `create_skin_material()` — SSS approximation via Principled BSDF subsurface (no Cycles)
- `create_eye_material()` — cornea refraction (alpha blend), iris HSV tint, fake SSS sclera
- `create_hair_material()` — anisotropic highlight via Clearcoat + Sheen, root→tip vertex color gradient
- `create_clothing_material()` — roughness/metallic from spec, fabric normal approximation
- `assign_materials()` — automatic scene-wide assignment by mesh classification

#### T5: Facial Expressions — Shape Key Discovery & VRM Binding
- **`hamr/face/expressions.py`** — `ExpressionDiscovery` for automatic shape key categorization
- `discover_shape_keys()` — scans mesh objects for MB-Lab and TurboSquid shape keys
- `bind_expressions()` — creates VRM 1.0 expression preset bindings (≥6: happy, angry, sad, surprised, neutral, blink)
- Fallback to `MB_LAB_EXPRESSION_MAP` and `TURBOSQUID_EXPRESSION_MAP` when discovery misses
- Discovery-first approach (AD-12.3): resilient to base-mesh variations, no hardcoding

#### T6: Collision Mesh Generation — Spring Bone Colliders
- **`hamr/rigs/colliders.py`** — `CollisionForge` for deterministic collision geometry
- `create_head_collider()` — spherical collider from head bone position + head mesh extent
- `create_body_capsule_colliders()` — capsules from spine bone chain + body cross-sections
- `register_collider_groups()` — links colliders to spring bone configuration for VRM 1.0
- Deterministic generation: same body → same colliders, no manual placement (AD-12.4)

#### T7: Performance Gate — Pre-flight Budget Check
- Pre-flight estimation: build time, memory, triangle count before Stage 0
- Optimization recommendations when over budget limits
- Pipeline configuration via `CharacterSpec.pipeline` section (AD-12.6)
- `skip_stages`, `perf_budget`, `spring_bones`, `collision` all configurable from YAML

### Changed
- `src/hamr/scripts/build_avatar.py` — restructured into explicit numbered stages with per-stage timing and error handling
- `src/hamr/core/pipeline.py` — `PresetLoader` integration with deep-merge user overrides
- `src/hamr/cli.py` — new commands and flags: `--json`, `--verbose`, `--skip-stages`
- `src/hamr/core/constants.py` — added material type constants, expression category names, pipeline stage names

### Tests Added (Phase 12)
- Pipeline stage execution and stage skip tests
- Material creation tests (skin, eye, hair, clothing)
- Expression discovery and binding tests
- Collision mesh generation tests
- CLI integration tests for all commands
- Performance gate and budget estimation tests
- End-to-end pipeline test suite (`tests/test_e2e_pipeline.py`, marked `e2e` + `blender`)

**Total: 1159 tests passing**

## [0.4.0] - 2026-05-08

### Added — Phase 11: Alvíssmál (All-Wise, All-Formed)

#### T1: Stub Bones — 25/25 Humanoid Bone Mapping
- **`hamr/rigs/stub_bones.py`** — `create_missing_bones()` creates micro-stub bones for jaw, leftEye, rightEye that MB-Lab omits
- Stubs are 0.5cm, parented to head, tagged `_hamr_stub=True`
- VRM 1.0 export now maps all 25 required humanoid bones
- TurboSquid bone map verified — no regression on its native 25/25

#### T2: Hair Mesh Generation — Procedural Mesh Hair
- **`hamr/hair/mesh.py`** — `HairForge` full procedural mesh hair engine
- 5 hair styles: straight, wavy, curly, braided, bob (with ponytail and twin-tails modeled as variants)
- Bezier curve → mesh pipeline (no particle systems — deterministic, Pi-compatible)
- Root→mid→tip gradient via vertex colors from `HairSpec.color`
- Length parameters: ear, chin, shoulder, mid-back, waist, very-long
- Volume parameter: 0.1–1.0
- Hair mesh parented to head bone for proper deformation

#### T3: Clothing Mesh Generation — Shrinkwrap Fit
- **`hamr/clothing/mesh.py`** — `ClothingForge` parametric clothing engine
- 6 clothing patterns: tshirt, shorts, skirt, dress, hoodie, school_uniform
- Shrinkwrap-to-body strategy for automatic fitting
- Garment thickness offset along normals
- Weight paint transfer from body mesh to clothing
- Clothing material assignment with color from spec

#### T4: Weight Paint Engine — Smooth Deformations
- **`hamr/rigs/weights.py`** — `WeightPaintEngine` with `paint_smooth()` and `get_quality_score()`
- Boundary smoothing at neck, shoulders, hips, knees, elbows
- Ensures minimum 3 vertex groups per joint vertex (no rigid 1-bone sections)
- Normalization enforcement — all vertex groups sum to 1.0
- Quality score algorithm: avg_groups_per_vertex, max_weight_variance, normalization_rate
- Transfer weights from body to clothing meshes

#### T5: Rig Verification Tool — CLI Compliance Checker
- **`hamr/rigs/verify.py`** — `RigVerifier` class with `verify()` → `RigReport`
- Checks: humanoid bone count (25/25), bone naming, hierarchy, expression count, lookAt config
- Missing/unmapped bone detection
- Weight paint quality score integration
- Spring bone group verification
- First-person annotation check
- Exit codes: 0 = compliant, 1 = warnings, 2 = failures
- CLI: `hamr verify-rig <vrm>` with `--json` and `--quiet` flags

#### T6: Performance Budgets — Pi 5 Optimization
- **`hamr/core/perf.py`** — `PerfBudget` and `PerfTracker` for Pi 5 resource guarding
- Memory tiers: minimal (512MB), standard (1GB), full (1.5GB) with hard caps
- Lazy texture generation — skip unused texture slots
- Blender subprocess timeout guard (120s, clean exit on timeout)
- Hair mesh triangle caps (low/medium/high density)
- `time hamr build --preset casual_f` < 45s on Pi 5 target
- `pytest tests/ -m perf` suite

#### T7: Character Presets — VRoid-Style Templates
- **`hamr/core/presets.py`** — `PresetLoader` with deep merge, validation, and CLI integration
- 6 presets: casual_m, casual_f, student_m, student_f, fantasy_m, fantasy_f
- `hamr build --preset <name>` generates a character from preset YAML
- Deep merge: user spec overrides preset defaults, preserving nested structure
- Preset validation against CharacterSpec schema
- Assets stored in `assets/presets/` as YAML files

#### T8: VRM 1.0 Compliance — Spring Bones, First-Person, Expressions
- **`hamr/rigs/spring_bones.py`** — Spring bone group creation for hair physics
- **`hamr/export/first_person.py`** — First-person mesh annotations (visibility flags per render subset)
- Spring bone groups with configurable stiffness, gravity, drag, collider groups
- Expression blink timing with crossfade intervals
- VRM meta: version, author, contactInformation, referenceInformation
- `pyproject.toml` — Version bumped to 0.4.0, new pytest markers (`perf`, `blender`, `e2e`)

### Changed
- `src/hamr/rigs/__init__.py` — Exported `stub_bones`, `weights`, `verify`, `spring_bones` modules
- `src/hamr/hair/__init__.py` — Exported `mesh` (HairForge)
- `src/hamr/clothing/__init__.py` — Exported `mesh` (ClothingForge)
- `src/hamr/export/__init__.py` — Exported `first_person` module
- `src/hamr/core/__init__.py` — Exported `perf` and `presets` modules
- `src/hamr/core/constants.py` — Added `VRM_25_BONE_NAMES` constant, clothing pattern names, hair style names, length enums
- `src/hamr/export/vrm.py` — Spring bone and first-person annotation integration

### Tests Added (Phase 11)
- `tests/test_stub_bones.py` — 501 lines, tests for stub bone creation, mapping, edge cases
- `tests/test_hair_mesh.py` — 551 lines, tests for hair mesh generation, style dispatch, color gradients
- `tests/test_clothing_mesh.py` — 564 lines, tests for clothing patterns, shrinkwrap fitting, weight transfer
- `tests/test_weights.py` — 580 lines, tests for weight paint smoothing, normalization, quality scoring
- `tests/test_verify.py` — 698 lines, tests for rig verification, compliance checks, CLI flags
- `tests/test_perf.py` — 598 lines, tests for performance budgets, memory tiers, timeout guards
- `tests/test_presets.py` — 346 lines, tests for preset loading, deep merge, validation, CLI
- `tests/test_spring_bones.py` — 419 lines, tests for spring bone groups, collider config, VRM serialization
- `tests/test_first_person.py` — 335 lines, tests for first-person annotations, mesh visibility flags

**Total: 556 tests passing**

---

## [0.3.0] - 2026-05-08

### Added — Phase 4: Tempering
- **BuildPipeline orchestrator** — Full spec→JSON→Blender→VRM pipeline
- **PipelineResult dataclass** — Success/failure tracking, timing, output size
- **check_environment()** — Detects Blender, VRM addon, MB-Lab addon
- **validate_only()** — Graceful SpecValidationError handling
- **Enhanced CLI** — `build`, `validate`, `inspect`, `check-env`, `list-presets`, `version`
- **Example specs** — `runa_gridweaver.yaml` and `minimal.yaml`
- **Pipeline metadata injection** — `_pipeline` dict with base_type, format, max_tex

### Added — Phase 5: Sharpening
- **TURBOSQUID_EXPRESSION_MAP** — 14 expressions matching MB-Lab format
- **Blender E2E integration tests** — Bone maps, expression maps, material classification
- **Environment detection** — Blender 3.4.1 + VRM addon + MB-Lab confirmed on Pi 5
- **CLI integration tests** — version, list-presets, validate

## [0.2.0] - 2026-05-07

### Added — Phase 3: The Quench
- **Blender-side build script** (540 lines) — Full Blender pipeline
- **MB-Lab bone map** (29 bones) + TurboSquid bone map (55 bones)
- **Expression maps** — MB-Lab and TurboSquid VRM expression bindings
- **Material classification** — Skin, eye, hair, nail, lip keyword detection
- **HSV texture tinting** — Hex→HSV, texture pixel shifting, Principled BSDF fallback
- **Height scaling** — Armature Z-axis proportional to height_cm
- **VRM metadata** — Title, author, license, usage permissions
- **First-person annotations** — Head mesh, viewpoint offset
- **LookAt** — Bone rotation mode with configurable ranges
- **Post-export validation** — glTF magic number, file size, structure checks

### Added — Phase 2: Form
- **Blender Bridge** — Subprocess runner, scene manager, mesh operations
- **Texture Forge** — HSV color pipeline, skin/metal/fabric generators
- **Body Forge** — 8 body presets with proportion resolution
- **Export Forge** — VRM 1.0 headless export with Seiðr-Smiðja lessons

## [0.1.0] - 2026-05-07

### Added — Phase 1: The Spec
- **CharacterSpec** dataclass with full face/body/hair/export parameters
- **YAML spec loading** — `Spec.from_yaml()` with validation
- **Spec validation** — Height, hex color, build type, required fields
- **Round-trip serialization** — `to_dict()` / `from_dict()` / YAML write
- **Core constants** — Body presets, skin palettes, hair colors
- **Error hierarchy** — HamrError, SpecValidationError, BuildError, ExportError
- **13 tests** all passing