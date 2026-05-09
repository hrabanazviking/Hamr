# Release Notes — Hamr v0.8.0

**Release Date:** 2026-05-08  
**Codename:** Mjölnir — *The Hammer That Never Misses*

> Mjölnir has flown. The dwarven hammer passed through every test, struck the
> anvil of release, and returned — unerring — to the open hand. New capabilities
> ride its arc: toon-shading for anime skins, spring-physics for living hair and
> cloth, pose-libraries for a thousand stances. The world receives what was forged
> in secret; the Nine Realms hear the thunder.

---

## v0.8.0 — Phase 16: Mjölnir

### Highlights

- **MToon Anime Shader System** — 5 preset shaders (standard, warm, cool, cinematic, silhouette) with VRM/glTF PBR conversion, rim lighting, outline rendering, and matcap blending
- **Spring Bone Physics Tuning** — 7 tuning presets (realistic, snappy, floaty, heavy, light, underwater, wind) with per-bone-group parameters and energy estimation
- **Pose Library** — 14 named presets (T-pose, A-pose, I-pose, 6 hand gestures, 6 facial expressions) with serializable snapshots and pose blending
- **v0.7.0 Tagged Release on Main** — Development merged into Main, GitHub release tag created, CI/CD pipeline validated end-to-end
- **TestPyPI Dry-Run Validation** — `twine upload` to TestPyPI succeeds, dependency resolution verified, clean import confirmed
- **Public README Polish** — Badges, features, architecture diagram, GPU profiles, quickstart demo, project mission statement
- **2,206 Tests, 0 Failures, 27 Skipped** — Full pipeline verified

### New Modules

| Module | Purpose |
|--------|---------|
| `hamr/materials/mtoon.py` | MToon anime shader system with 5 presets and VRM/glTF conversion |
| `hamr/rigs/spring_tuning.py` | Spring bone physics tuning with 7 presets and energy estimation |
| `hamr/rigs/pose_library.py` | Pose library with 14 presets, blending, and VRM BlendShape categories |

### MToon Shader Presets

- **Standard** — Default anime toon with balanced rim and shade
- **Warm** — Warm-toned shading for skin and soft materials
- **Cool** — Cool-toned shading for metallic and cold environments
- **Cinematic** — High-contrast dramatic lighting
- **Silhouette** — Flat-shaded silhouette mode for stylized renders

### Spring Tuning Presets

- **Realistic** — Natural, gravity-driven secondary motion
- **Snappy** — Quick response, minimal overshoot
- **Floaty** — Gentle, airy movement with high drag
- **Heavy** — Sluggish, weighty cloth and hair
- **Light** — Quick and delicate motion
- **Underwater** — Slow, buoyant movement
- **Wind** — Strong directional force with turbulence

### Pose Library Presets

- **Rest Poses**: T-pose, A-pose, I-pose
- **Hand Gestures**: fist, open, point, grip, relax, spread
- **Facial Expressions**: neutral, happy, angry, sad, surprised, relaxed

---

## v0.7.0 — Phase 15: Vápnatak

### Highlights

- **E2E Blender Build Testing** — 60 end-to-end headless build tests proving the pipeline end-to-end
- **GitHub Actions CI/CD** — Full lint → test → E2E pipeline on every push and PR
- **Performance Regression Baselines** — 62 thresholds ensuring no performance degradation
- **5 Preset Validation Fixes** — All preset failures ground smooth; deepcopy guards prevent shared mutability
- **Release Artifact Pipeline** — Versioned wheels, sdist, SHA256SUMS/MD5SUMS on every tag push
- **API Reference Generator** — Auto-generated markdown API docs from live code
- **~2,206 Tests, 0 Failures** — Full pipeline verified

### New Modules

| Module | Purpose |
|--------|---------|
| `hamr/blender_bridge/e2e.py` | End-to-end Blender headless build configuration and execution |
| `hamr/core/regression.py` | Performance regression detection with GPU-profile baselines |
| `hamr/core/release.py` | Release artifact management: wheels, checksums, manifests |
| `hamr/docs/api_reference.py` | Auto-generated API reference from live module introspection |

### Bug Fixes

- **5 preset validation failures resolved** — deepcopy guard in `Spec.from_dict()`, immutable `get_preset()`, corrected hex colors, clamped out-of-range values, populated missing required fields
- **Version assertions updated** throughout the test suite for v0.7.0
- All previous 7 known preset warnings have been eliminated — **0 remaining**

### CI/CD

- `.github/workflows/ci.yml` — lint (ruff) → test (3.10/3.11/3.12) → coverage (≥80%) → benchmark
- `.github/workflows/release.yml` — build wheel/sdist → check → publish to TestPyPI on tag push

---

## v0.7.0-rc1 — Phase 14: Gjallarhorn

---

## Summary

Hamr 0.7.0-rc1 is the first release candidate, culminating eight phases of
development (Phases 7–14). It integrates a complete VRM 1.0 character-creation
pipeline — spec parsing, procedural hair/clothing, weight painting, animation
clips, material shaders, GPU-adaptive quality, accessibility hardening, VRM
validation, and documentation generation — all runnable headless on Linux
(including Raspberry Pi 5).

This release candidate is intended for community smoke-testing before the
stable v0.7.0 release.

---

## Breaking Changes

- **`BuildPipeline` stage numbers** — The pipeline was restructured from ad-hoc
  calls into 14 explicit numbered stages (0–13). Any code that relied on the
  old `build_avatar.py` call sequence must be updated.
- **`CharacterSpec` → `Spec`** — The top-level spec class is now imported as
  `Spec` (via `hamr.core.spec.Spec`). The old `CharacterSpec` name still exists
  as a data model, but the canonical entry point is `Spec.from_yaml()`.
- **Preset schema v2** — Presets now support a `pipeline` sub-section for stage
  configuration. Existing preset YAML files without this section will still
  work (deep-merged with defaults), but the schema has been extended.
- **Exit codes** — CLI exit codes are now normalized: `0` = success, `1` =
  warning, `2` = error, `3` = environment-missing. Scripts that relied on
  simpler exit semantics should update.

---

## New Features

### Core (`hamr/core/`)
- **`pipeline.py`** — `BuildPipeline` with 14 explicit numbered stages,
  per-stage timing, `BuildResult` tracking, and `--skip-stages` support
- **`validate.py`** — `spec_to_dict()` for round-trip spec serialization,
  4 preset bug fixes, 33 regression guards
- **`perf.py`** — `PerfBudget` and `PerfTracker` for Pi 5 memory tiers and
  hard caps
- **`presets.py`** — `PresetLoader` with deep merge, validation, and CLI
  integration; 6 built-in presets
- **`gpu_profiles.py`** — `GPUProfiler` with auto-detection and adaptive
  quality tiers (`pi5`, `desktop`, `cloud`)
- **`a11y.py`** — `--no-color`, `--quiet`, `--json` flags; actionable error
  suggestions; normalized exit codes
- **`constants.py`** — `VRM_25_BONE_NAMES`, material type constants,
  expression categories, pipeline stage names

### Hair (`hamr/hair/`)
- **`mesh.py`** — `HairForge` procedural mesh hair: 5 styles (straight, wavy,
  curly, braided, bob), Bezier→mesh pipeline, root→tip vertex color gradients

### Clothing (`hamr/clothing/`)
- **`mesh.py`** — `ClothingForge` parametric clothing: 6 patterns, shrinkwrap
  fitting, weight paint transfer from body to garments

### Face (`hamr/face/`)
- **`expressions.py`** — `ExpressionDiscovery` for automatic shape key
  categorization; `bind_expressions()` for VRM 1.0 expression presets (≥6)

### Rigs (`hamr/rigs/`)
- **`stub_bones.py`** — `create_missing_bones()` for 25/25 humanoid bone mapping
- **`weights.py`** — `WeightPaintEngine` with `paint_smooth()` and quality scoring
- **`spring_bones.py`** — Spring bone group creation with collider configuration
- **`colliders.py`** — `CollisionForge` for deterministic head and body colliders
- **`verify.py`** — `RigVerifier` / `RigReport` with CLI compliance checking

### Materials (`hamr/materials/`)
- **`forge.py`** — `MaterialForge` for Eevee-optimized anime shaders
  (skin, eye, hair, clothing) with SSS, anisotropic highlights, vertex color
  gradients

### Export (`hamr/export/`)
- **`first_person.py`** — First-person mesh annotations per render subset
- **`vrm_validator.py`** — `VRMValidator` for VRM 1.0 compliance (binary
  glTF parsing, bone coverage, expression count, spring bone groups)
- **`animation_clips.py`** — `AnimationForge` for VRM 1.0 animation clips
  (idle breathe, weight shift, look around, walk cycle)

### Procedural Textures (`hamr/core/`)
- **`texture_procedural.py`** — `TextureForge` for deterministic GPU-quality
  textures: skin detail (pore noise, SSS thickness, micro-normal), iris detail,
  hair gradients, fabric normal maps

### Documentation (`hamr/docs/`)
- **`generate.py`** — `DocGenerator` for auto-generated CLI reference,
  architecture diagrams, preset guides, and README sections

### CLI (`hamr/cli.py`)
- `hamr build --preset <name>` / `--spec <file>` — full pipeline
- `hamr verify-rig <vrm>` — rig compliance with `--json` / `--quiet`
- `hamr check-env` — environment detection
- `hamr list-presets --verbose` — detailed preset info
- `--json`, `--verbose`, `--skip-stages`, `--no-color`, `--quiet` flags

---

## Bug Fixes

- 4 preset validation bugs fixed (invalid hex colors, out-of-range values,
  missing required fields)
- `SpecValidationError` now includes actionable fix hints
- 33 regression guards to prevent Phase 11–12 breakage
- Weight paint normalization enforcement — all vertex groups sum to 1.0
- Bone hierarchy verification catches missing parent relationships

---

## Known Issues

- **7 preset validation failures** remain from pre-Phase-13 data — these are
  cosmetic/schema warnings and do not block the build pipeline.
- **Blender dependency** — `bpy` is not pip-installable; the core library runs
  without it, but full pipeline builds require Blender with the VRM addon.
- **Windows/macOS E2E** — End-to-end Blender tests are only verified on Linux.
  Windows and macOS parity is a release goal for v0.7.0 stable.
- **Animation clips** — Walk cycle clip is a reference implementation; joint
  keyframes may need per-avatar tuning.
- **Procedural textures** — Fabric normal map uses an approximation weave
  pattern; organic weave textures require external baking.

---

## Migration Guide (v0.5.x → v0.7.0-rc1)

See [MIGRATION.md](./MIGRATION.md) for the full guide.

### Quick API Changes

| Old API | New API |
|---|---|
| `from hamr.core.spec import CharacterSpec` | `from hamr.core.spec import Spec` |
| `spec.to_dict()` round-trips | Use `spec_to_dict()` from `hamr.core.validate` |
| Ad-hoc build script | `BuildPipeline.build()` with stage numbering |
| No pipeline config | `CharacterSpec.pipeline` section in YAML |

---

## Contributors

- **Volmarr** — Architecture, core modules, rig systems, pipeline
- **Runa** — Face systems, materials, procedural textures, documentation

---

*Let the horn resound. All realms shall hear it.*

*For detailed changes per phase, see [CHANGELOG.md](./CHANGELOG.md).*