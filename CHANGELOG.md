# Changelog

All notable changes to Hamr will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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