# Release Notes — Hamr v0.7.0-rc1

**Release Date:** 2026-05-08  
**Codename:** Gjallarhorn — *The Resounding Horn*

> Heimdallr blows the Gjallarhorn, and the final assembly is called.
> Every subsystem stands together, ready for the world.

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