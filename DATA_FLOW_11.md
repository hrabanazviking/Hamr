# ᚺᚨᛗᚱ — Data Flow Map: Phase 11 (Alvíssmál)

> *"Every bone shall have a name. Every strand its place. Every fold shall drape true. Every vertex shall move smooth."*

---

## 1. Complete Current File Map

Every `.py` file in `src/hamr/`, its role, and its status heading into Phase 11.

### 1.1 Core Package (`src/hamr/core/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | Re-exports: `Spec`, `CharacterSpec`, `BodySpec`, `FaceSpec`, `HairSpec`, `HamrError`, `SpecValidationError`, `BuildError`, `ExportError`, `build`, `validate_only`, `inspect` | No change |
| `spec.py` | YAML spec parser — `Spec.from_yaml()` → `CharacterSpec`. Loads from file, validates, returns structured spec. | No change |
| `models.py` | All dataclass models: `CharacterSpec`, `BodySpec`, `SkinSpec`, `FaceSpec`, `EyeSpec`, `HairSpec`, `HairColorSpec`, `HairStyle` (enum), `HairLength` (enum), `HairPhysicsSpec`, `ClothingSpec`, `ExportSpec`, `PhysicsSpec` | **MODIFY**: Add `SpringBoneGroupSpec`, `FirstPersonSpec` fields to `CharacterSpec` |
| `constants.py` | Default values: skin colors, VRM bone list (`VRM_REQUIRED_BONES`), `MB_LAB_BONE_MAP`, `TURBOSQUID_BONE_MAP`, lilToon shader defaults, physics defaults, body presets (`BODY_PRESETS`), texture pipeline constants (`TEXTURE_SIZE`, `TEXTURE_BLEND_FACTOR`) | **MODIFY**: Add `STUB_BONE_DEFS`, `SCALP_VERTEX_MAP`, `CLOTHING_REGION_MAP`, `HAIR_TRIANGLE_BUDGETS`, `PERFORMANCE_LIMITS` |
| `validate.py` | Validates `CharacterSpec`: builds, jaw shapes, eye shapes, hair styles/lengths, hex colors, export formats, physics ranges. Returns list of error strings. | No change (may extend for new fields) |
| `pipeline.py` | Full forge pipeline orchestrator. `BuildPipeline.build()` → Spec parse → Validate → JSON serialize → Blender subprocess → Verify output → Cleanup. `PipelineResult` dataclass. Also `validate_only()`, `check_environment()`. | **MODIFY**: Add stub bone, hair mesh, clothing mesh, weight paint, spring bone, first-person steps in Blender-side pipeline. Reduce `blender_timeout` default from 600→120. Add memory cleanup calls. Add `--preset` flag support. |
| `builder.py` | Alternative entry: `build()` → Spec parse → Validate → Resolve forges → JSON serialize → Blender bridge → Verify. `_resolve_forges()` calls `resolve_hair()`, `resolve_face()`, `resolve_clothing()`. | Reference only (pipeline.py is primary path) |
| `textures.py` | Texture Forge — procedural texture generation via Pillow + NumPy. Functions: `hex_to_rgb()`, `generate_skin_texture()`, `tint_texture()`, HSV utilities. Pure Python, no Blender. | No change |
| `errors.py` | Error hierarchy: `HamrError` → `SpecValidationError`, `BuildError`, `ExportError`, `AssetNotFoundError`. | No change |
| `iterate.py` | Agent-driven refinement loop — **placeholder**, not yet implemented. | No change |
| `inspect.py` | VRM/GLB compliance inspection — **placeholder**, not yet implemented. | No change (superceded by `rigs/verify.py`) |

### 1.2 Body Package (`src/hamr/body/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | Re-exports: `BodyForge`, `BODY_PRESETS`, `BODY_PRESET_ALIASES` | No change |
| `forge.py` | `BodyForge` class — resolves body preset, imports base mesh, applies shape key proportions, applies skin texture, scales to target height. Currently has stub `_import_base_mesh()`. Imports `blender_bridge.scene` and `core.textures` lazily. | No change |
| `presets.py` | Re-exports `BODY_PRESETS` from `core.constants`. Defines `BODY_PRESET_ALIASES` (slim→athletic-slender, etc.). | No change |

### 1.3 Hair Package (`src/hamr/hair/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | `resolve_hair(HairSpec)` → `HairBuildResult` (config-only, pure Python). Also: `list_hair_presets()`, `list_gradient_presets()`. Style templates: wild-curly, straight, wavy, braided, bun, ponytail. Length presets. Gradient presets. HSV color utilities. | **MODIFY**: Add `HairForge` import alongside `resolve_hair` |
| — | — | — |
| `forge.py` | **NEW**: `HairForge` class — mesh hair generation engine. Dispatches to style modules. `generate(spec, head_mesh, armature) → HairMeshResult`. `apply_colors(hair_obj, spec)`. | **NEW** |
| `straight.py` | **NEW**: Straight hair mesh generator — extrude curves from scalp, convert to mesh | **NEW** |
| `wavy.py` | **NEW**: Wavy hair mesh generator — sine wave displacement on guide curves | **NEW** |
| `curly.py` | **NEW**: Curly/spiral hair mesh generator — spiral curve generation | **NEW** |
| `bob.py` | **NEW**: Bob cut mesh generator (also covers "bun" style variant) | **NEW** |
| `ponytail.py` | **NEW**: Ponytail mesh generator | **NEW** |
| `braided.py` | **NEW**: Braided hair mesh generator — 3-strand braid algorithm | **NEW** |
| `utils.py` | **NEW**: Shared hair utilities — `get_scalp_vertices()`, `generate_guide_curves()`, `curve_to_mesh()`, `apply_vertex_gradient()`, `decimate_mesh()`, `SCALP_GROUPS`, `HAIR_LENGTH_SCALE` | **NEW** |

### 1.4 Clothing Package (`src/hamr/clothing/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | `resolve_clothing(ClothingSpec)` → `ClothingBuildResult` (config-only, pure Python). Also: `list_clothing_types()`, `list_material_categories()`. Cloth type templates, material categories. | **MODIFY**: Add `ClothingForge` import alongside `resolve_clothing` |
| — | — | — |
| `forge.py` | **NEW**: `ClothingForge` class — mesh clothing generation. `generate(spec, body_mesh, armature) → ClothingMeshResult`. `generate_from_pattern(pattern_name, body_mesh, armature)`. Shrinkwrap strategy. | **NEW** |
| `patterns.py` | **NEW**: `CLOTHING_PATTERNS` dict, `BODY_REGION_VERTEX_GROUPS` dict. Pattern definitions for tshirt, shorts, skirt, dress, hoodie, school_uniform. Pure data, no bpy import. | **NEW** |
| `fit.py` | **NEW**: `shrinkwrap_clothing()`, `transfer_weights_to_clothing()`, `separate_body_region()`. Shrinkwrap + weight transfer. Requires bpy. | **NEW** |

### 1.5 Face Package (`src/hamr/face/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | `resolve_face(FaceSpec)` → `FaceBuildResult` (config-only, pure Python). Shape key maps for jaw, cheekbones, nose, eyes. Expression presets. | No change |

### 1.6 Rigs Package (`src/hamr/rigs/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | Currently just re-exports `MB_LAB_BONE_MAP` and `VRM_REQUIRED_BONES` from `export.vrm`. | **MODIFY**: Replace with full public API: `create_missing_bones`, `WeightPaintEngine`, `RigVerifier`, `WeightPaintReport`, `RigReport`, `StubBoneResult` |
| — | — | — |
| `stub_bones.py` | **NEW**: `create_missing_bones(armature_name, base_type) → StubBoneResult`. Finds chin/eye vertex centers, creates jaw/leftEye/rightEye stub bones parented to head. Tags `_hamr_stub=True`. | **NEW** |
| `weights.py` | **NEW**: `WeightPaintEngine` class with `paint_smooth()`, `transfer_weights()`, `get_quality_score() → WeightPaintReport`. `SMOOTH_REGIONS` dict for joint boundaries. Requires bpy. | **NEW** |
| `verify.py` | **NEW**: `RigVerifier` class with `verify(vrm_path) → RigReport`. Pure glTF parsing, no Blender. `to_cli()`, `to_json()` formatters. | **NEW** |
| `spring_bones.py` | **NEW**: `SpringBoneConfig` dataclass, `configure_hair_spring()`, `configure_breast_spring()`. VRM 1.0 spring bone group setup. Requires bpy. | **NEW** |

### 1.7 Export Package (`src/hamr/export/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | Re-exports from `vrm.py`: `export_vrm`, `MB_LAB_BONE_MAP`, `VRM_REQUIRED_BONES`, `TURBOSQUID_BONE_MAP`. Re-exports `export_glb` from `glb.py`. | **MODIFY**: Add `first_person` module import |
| `vrm.py` | VRM 1.0 export. Explicit bone mapping (D-008: NEVER auto-map). `human_bone_name_to_human_bone` dict API (D-018). `EXEC_DEFAULT` with `ignore_warning=True` (D-016). `allow_non_humanoid_rig` safety net (D-017). Cache check for migration (D-018b). Viseme/expression/look-at setup. | **MODIFY**: Add `setup_spring_bones()`, `setup_first_person()` functions. Verify `MB_LAB_BONE_MAP` includes jaw/leftEye/rightEye. |
| `glb.py` | GLB (binary glTF 2.0) export. Simple bpy export, no VRM metadata. | No change |
| — | — | — |
| `first_person.py` | **NEW**: `configure_first_person(armature_name, mesh_names, head_bone_name)`. Sets VRM first-person mesh annotations: head → THIRD_PERSON_ONLY, body → AUTO. Requires bpy. | **NEW** |

### 1.8 Blender Bridge Package (`src/hamr/blender_bridge/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | Re-exports from `runner.py`: `BlenderResult`, `run_blender_script`, `run_inline_script`, `check_blender_available`, `get_blender_version`. | No change |
| `runner.py` | Headless Blender subprocess runner. `run_blender_script()`, `run_inline_script()`, `check_blender_available()`, `get_blender_version()`. Uses `subprocess.Popen`, `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true`. | **MODIFY**: Default timeout 600→120. Add `_cleanup_subprocess()` for killing orphan Blender processes. Add memory warning in result when stderr contains "Memory". |
| `mesh_ops.py` | Blender mesh operations: `apply_shape_key()`, `scale_armature()`, `get_all_materials()`, `find_material_by_name()`, `duplicate_object()`, `join_objects()`. All guarded by `BLENDER_AVAILABLE` check. | **MODIFY**: Add `transfer_weights()`, `parent_to_bone()`, `separate_region()`, `decimate_to_budget()`. |
| `scene.py` | Scene management: `new_scene()`, `clean_scene()`, `_purge_orphans()`, `get_armature()`, `get_mesh_objects()`, `set_scene_defaults()`, `clean_blend_backups()`. | **MODIFY**: Add memory-conscious cleanup helpers. |

### 1.9 Scripts (`src/hamr/scripts/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `build_avatar.py` | Main Blender-side build script. Runs inside Blender subprocess. Reads JSON spec → generates character via MB-Lab → applies spec (face, hair config, clothing config, textures) → sets up VRM bone mapping → exports VRM 1.0. ~500 lines. | **MODIFY**: Add 6 new steps after `_apply_spec()`: `_create_stub_bones()`, `_generate_hair_mesh()`, `_generate_clothing_mesh()`, `_smooth_weights()`, `_configure_spring_bones()`, `_configure_first_person()`. Add `--preset` arg support. |

### 1.10 CLI Package (`src/hamr/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `cli.py` | CLI with subcommands: `build`, `validate`, `inspect`, `list-presets`, `check-env`, `version`. Supports `--dry-run` and `--verbose`. | **MODIFY**: Add `verify-rig` subcommand. Add `--preset` flag to `build`. Add `--blender-timeout` flag (default 120). |
| — | — | — |
| `cli/verify_rig.py` | **NEW**: `cmd_verify_rig(args) → int`. CLI handler for `hamr verify-rig`. Supports `--json` and `--quiet` flags. Exit codes: 0=compliant, 1=warnings, 2=failures. | **NEW** |

### 1.11 Top-Level Package (`src/hamr/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `__init__.py` | Package init. `__version__ = "0.3.0"`. Re-exports: `Spec`, all `*Spec` models, `*Error` classes, `BuildPipeline`, `PipelineResult`, forge functions (`resolve_hair`, etc.). | **MODIFY**: Bump version to `0.4.0`. Add `HairForge`, `ClothingForge`, `WeightPaintEngine`, `RigVerifier` to `__all__`. |

### 1.12 Presets (`assets/presets/`)

| File | Role | Phase 11 Status |
|------|------|-----------------|
| `casual_m.yaml` | **NEW**: Default male casual character spec | **NEW** |
| `casual_f.yaml` | **NEW**: Default female casual character spec | **NEW** |
| `student_m.yaml` | **NEW**: Male student character spec | **NEW** |
| `student_f.yaml` | **NEW**: Female student character spec | **NEW** |
| `fantasy_m.yaml` | **NEW**: Male fantasy character spec | **NEW** |
| `fantasy_f.yaml` | **NEW**: Female fantasy character spec | **NEW** |

---

## 2. Complete Data Flow: YAML Spec → VRM on Disk

### 2.1 Full Pipeline Trace

```
character.yaml
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  1. SPEC PARSE (Pure Python)                            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Spec.from_yaml(path)                                │ │
│  │   → yaml.safe_load()                                │ │
│  │   → CharacterSpec dataclass construction            │ │
│  │   → BodySpec, SkinSpec, FaceSpec, HairSpec,          │ │
│  │     HairColorSpec, ClothingSpec[], ExportSpec,       │ │
│  │     PhysicsSpec                                      │ │
│  │   → validate_spec(char) — validate fields            │ │
│  │   → resolve_hair(HairSpec) → HairBuildResult (dict)  │ │
│  │   → resolve_face(FaceSpec) → FaceBuildResult (dict)  │ │
│  │   → resolve_clothing(ClothingSpec) → list[dict]      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  Output: CharacterSpec + forge_config dict               │
│                                                          │
│  Modules: spec.py, models.py, validate.py,               │
│           hair/__init__.py, face/__init__.py,             │
│           clothing/__init__.py, constants.py              │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│  2. JSON SERIALIZATION (Pure Python)                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ spec.to_dict() → JSON dict                           │ │
│  │ inject forge_config into dict                        │ │
│  │ inject _pipeline metadata (base_type, format, etc.)  │ │
│  │ json.dumps() → write to .hamr_{name}_spec.json       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  Modules: spec.py, pipeline.py/builder.py                │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│  3. BLENDER SUBPROCESS LAUNCH (Pure Python)             │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ run_blender_script(                                  │ │
│  │     script_path=build_avatar.py,                      │ │
│  │     script_args=[                                     │ │
│  │         "--spec", spec_json_path,                      │ │
│  │         "--output", output_vrm_path,                  │ │
│  │     ],                                                │ │
│  │     timeout=120,                                      │ │
│  │ )                                                     │ │
│  │                                                       │ │
│  │ subprocess.Popen([                                    │ │
│  │     blender_path,                                     │ │
│  │     "--background",                                   │ │
│  │     "--python-use-system-env",                        │ │
│  │     "--python", build_avatar.py,                       │ │
│  │     "--",                                             │ │
│  │     "--spec", spec_json_path,                         │ │
│  │     "--output", output_vrm_path,                      │ │
│  │ ], env={BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION}) │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  Modules: blender_bridge/runner.py                       │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. BLENDER-SIDE BUILD (Inside Blender Subprocess)            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ build_avatar.py main() execution                         │ │
│  │                                                           │ │
│  │  4a. Parse --spec / --output arguments                    │ │
│  │      → json.loads() → spec_data dict                      │ │
│  │                                                           │ │
│  │  4b. Scene setup                                          │ │
│  │      → new_scene(), set_scene_defaults()                  │ │
│  │      Modules: blender_bridge/scene.py                     │ │
│  │                                                           │ │
│  │  4c. MB-Lab character generation                          │ │
│  │      → _generate_mblab_base()                              │ │
│  │      → Creates armature (22 bones) + body mesh            │ │
│  │      → Applies body shape keys from body preset           │ │
│  │                                                           │ │
│  │  4d. Apply spec (body proportions, textures)              │ │
│  │      → _apply_spec(spec_data, forge_config)               │ │
│  │      → BodyForge._resolve_body() → shape key values        │ │
│  │      → BodyForge._apply_proportions()                     │ │
│  │      → BodyForge._apply_skin() → textures.py               │ │
│  │      → BodyForge._scale_height() → mesh_ops.scale_armature│ │
│  │      Modules: body/forge.py, core/textures.py,             │ │
│  │               blender_bridge/mesh_ops.py                   │ │
│  │                                                           │ │
│  │  4e. [PHASE 11 NEW] Create stub bones ──────────────────  │ │
│  │      → create_missing_bones(armature_name, base_type)      │ │
│  │      → jaw, leftEye, rightEye stubs parented to head       │ │
│  │      → Tagged _hamr_stub=True                              │ │
│  │      Module: rigs/stub_bones.py                            │ │
│  │                                                           │ │
│  │  4f. [PHASE 11 NEW] Generate hair mesh ───────────────   │ │
│  │      → HairForge.generate(hair_spec, head_mesh, armature)  │ │
│  │      → Style dispatch (straight/wavy/curly/bob/etc.)       │ │
│  │      → HairForge.apply_colors(hair_obj, spec)              │ │
│  │      → Parent to head bone                                 │ │
│  │      Module: hair/forge.py, hair/straight.py, etc.         │ │
│  │      Utility: hair/utils.py                                │ │
│  │                                                           │ │
│  │  4g. [PHASE 11 NEW] Generate clothing mesh ────────────   │ │
│  │      → ClothingForge.generate(clothing_spec, body, arm)    │ │
│  │      → Region select → separate → offset → shrinkwrap      │ │
│  │      → Material assign → weight paint transfer             │ │
│  │      Module: clothing/forge.py, clothing/patterns.py,      │ │
│  │               clothing/fit.py                               │ │
│  │                                                           │ │
│  │  4h. [PHASE 11 NEW] Smooth weight painting ────────────   │ │
│  │      → WeightPaintEngine.paint_smooth(obj, armature)       │ │
│  │      → WeightPaintEngine.transfer_weights(body, hair, arm) │ │
│  │      → WeightPaintEngine.transfer_weights(body, cloth, arm) │ │
│  │      → WeightPaintEngine.get_quality_score(obj)             │ │
│  │      Module: rigs/weights.py                               │ │
│  │                                                           │ │
│  │  4i. [PHASE 11 NEW] Configure spring bones ────────────   │ │
│  │      → configure_hair_spring(armature, hair_obj, physics)   │ │
│  │      → VRM1 springBone.springBoneGroups                    │ │
│  │      Module: rigs/spring_bones.py                           │ │
│  │                                                           │ │
│  │  4j. [PHASE 11 NEW] Configure first-person ────────────   │ │
│  │      → configure_first_person(armature, mesh_names)         │ │
│  │      → head mesh → THIRD_PERSON_ONLY, body → AUTO          │ │
│  │      Module: export/first_person.py                         │ │
│  │                                                           │ │
│  │  4k. VRM 1.0 Export                                       │ │
│  │      → export_vrm(output_path, armature)                   │ │
│  │      → Explicit bone mapping (D-008: NEVER auto-map)       │ │
│  │      → human_bone_name_to_human_bone map → 25/25 bones     │ │
│  │      → Viseme setup (aa, ih, oh, ee, ou)                  │ │
│  │      → Expression overrides                               │ │
│  │      → Look-at config (bone rotation, from eyes)           │ │
│  │      → Meta: title, author, version                       │ │
│  │      Module: export/vrm.py                                 │ │
│  │                                                           │ │
│  │  4l. Cleanup                                               │ │
│  │      → clean_blend_backups(output_dir)                     │ │
│  │      Module: blender_bridge/scene.py                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                │
│  Returns: BlenderResult (success, exit_code, stdout, stderr)   │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│  5. OUTPUT VERIFICATION (Pure Python)                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Check BlenderResult.success                           │ │
│  │ Verify output_path.exists()                           │ │
│  │ Report size_mb                                         │ │
│  │ Clean up temp spec JSON                               │ │
│  │ Clean up .blend1 backup files                         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  Modules: pipeline.py, blender_bridge/scene.py           │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
     ✅ avatar.vrm on disk
```

### 2.2 Data Format at Each Boundary

| Boundary | Format | Source Module | Sink Module |
|----------|--------|---------------|-------------|
| YAML file → Spec.parse() | YAML string | `spec.py` | `spec.py` |
| Spec → Validate | `CharacterSpec` dataclass | `spec.py` | `validate.py` |
| Validate → Forges | `CharacterSpec` | `validate.py` | `hair/__init__.py`, `face/__init__.py`, `clothing/__init__.py` |
| Forges → JSON | `dict` (via `.to_dict()`) | `builder.py` | `json.dumps()` |
| JSON → Blender | `.json` temp file on disk | `pipeline.py` | `build_avatar.py` via `--spec` argument |
| Blender → Output | `.vrm` file on disk | `export/vrm.py` | Filesystem |
| Blender → Python | `BlenderResult` (exit code, stdout, stderr) | `runner.py` | `pipeline.py` |
| Python → User | `PipelineResult` (success, path, size, timing) | `pipeline.py` | CLI / caller |

---

## 3. New Phase 11 Data Flows

### 3.1 Stub Bone Creation Flow (G1)

```
CharacterSpec.body.build → "mblab" | "turbosquid"
     │
     ▼
MB-Lab / Base Mesh Generation
     │ → armature with 22/25 humanoid bones
     ▼
create_missing_bones(armature_name, base_type)
     │
     ├── 1. Import bpy
     ├── 2. Get armature object by name
     ├── 3. Scan for jaw, leftEye, rightEye in existing bones
     ├── 4. For each missing bone:
     │      ├── jaw: find_vertex_center(mesh, "jaw"/"chin") → position
     │      ├── leftEye: find_vertex_center(mesh, "eye_L"/"leftEye") → position
     │      └── rightEye: find_vertex_center(mesh, "eye_R"/"rightEye") → position
     ├── 5. Create EditBone, set head/tail, parent to "head"
     ├── 6. Tag bone["_hamr_stub"] = True
     └── 7. Return StubBoneResult(created_bones={...}, existing_bones=[...])
     │
     ▼
MB_LAB_BONE_MAP (updated with 3 stub entries)
     │
     ▼
export_vrm() → 25/25 humanoid bones mapped
```

**Data entities:**
- `STUB_BONE_DEFS` (new in `constants.py`): `{ "jaw": {parent: "head", position_method: "chin_vertices", length: 0.05}, "leftEye": {...}, "rightEye": {...} }`
- `StubBoneResult` (new dataclass in `rigs/stub_bones.py`)
- `MB_LAB_BONE_MAP` (expanding from 22→25 entries in `export/vrm.py`)

### 3.2 Hair Mesh Generation Flow (G2)

```
HairSpec (style, length, volume, color, curl, physics)
     │
     ├── [Config Layer] resolve_hair(HairSpec) → HairBuildResult
     │   Pure Python, runs outside Blender
     │   (Existing, unchanged)
     │
     └── [Mesh Layer] HairForge.generate(HairSpec, head_mesh, armature)
         │   Runs inside Blender only
         │
         ├── 1. Style dispatch
         │      "straight"  → straight.generate()
         │      "wavy"      → wavy.generate()
         │      "curly"     → curly.generate()
         │      "wild-curly" → curly.generate()
         │      "braided"   → braided.generate()
         │      "ponytail"  → ponytail.generate()
         │      "bun"       → bob.generate() (variant)
         │      "bob"       → bob.generate()
         │
         ├── 2. Shared pipeline (inside style module)
         │      a. get_scalp_vertices(mesh, base_type) → scalp vertex indices
         │      b. generate_guide_curves(scalp_indices, mesh, density) → guide curve dicts
         │      c. Apply style modifier (curl frequency, wave amplitude, braid pattern)
         │      d. Create Bezier curves in Blender scene
         │      e. curve_to_mesh(curve_obj, resolution) → mesh object
         │      f. Apply length parameter (scale hair height)
         │      g. Apply volume (array modifier + random offset)
         │      h. decimate_mesh(mesh, HAIR_TRIANGLE_BUDGETS[style])
         │      i. Parent hair object to head bone
         │
         ├── 3. HairForge.apply_colors(hair_obj_name, spec)
         │      a. Convert spec.color.roots/tips HSV → RGB
         │      b. apply_vertex_gradient(mesh_obj, roots_hsv, mid_hsv, tips_hsv)
         │         → root→mid→tip vertex color gradient via Y-coordinate
         │
         └── 4. Return HairMeshResult
                (object_name, bone_chain, vertex_count, triangle_count, style)
```

**Data entities:**
- `HairMeshResult` (new dataclass): `object_name`, `bone_chain`, `vertex_count`, `triangle_count`, `style`
- `HAIR_TRIANGLE_BUDGETS` (new in constants): `{ "short": 5000, "shoulder": 8000, "long": 12000, "very-long": 15000 }`
- `HAIR_LENGTH_SCALE` (new in hair/utils.py): `{ "short": 0.05, "medium": 0.12, ... }`
- `SCALP_GROUPS` (new in hair/utils.py): MB-Lab / TurboSquid scalp vertex group names

### 3.3 Clothing Mesh Generation Flow (G3)

```
ClothingSpec (type, color_hex, material_category, name)
     │
     ├── [Config Layer] resolve_clothing(ClothingSpec) → ClothingBuildResult
     │   Pure Python, runs outside Blender
     │   (Existing, unchanged)
     │
     └── [Mesh Layer] ClothingForge.generate(ClothingSpec, body_mesh, armature)
         │   Runs inside Blender only
         │
         ├── 1. Select pattern from CLOTHING_PATTERNS[spec.type]
         │      → regions, offset, seam_groups, default_material, hem_width
         │
         ├── 2. Region selection
         │      a. Look up BODY_REGION_VERTEX_GROUPS[base_type][region]
         │      b. Select vertices in those vertex groups on body mesh
         │
         ├── 3. Duplicate & separate
         │      a. separate_body_region(body_obj, region_names, base_type)
         │      b. Creates new mesh object with selected vertices
         │
         ├── 4. Offset along normals
         │      a. Push vertices outward by `offset` meters (0.004–0.006)
         │
         ├── 5. Shrinkwrap to body
         │      a. shrinkwrap_clothing(clothing_obj, body_obj, offset)
         │      b. Apply Blender Shrinkwrap modifier, then apply modifier
         │
         ├── 6. Material assignment
         │      a. Create lilToon material with clothing color
         │      b. Assign to clothing mesh faces
         │
         ├── 7. Weight paint transfer
         │      a. transfer_weights_to_clothing(clothing_obj, body_obj, armature)
         │      b. Blender Data Transfer modifier → nearest vertex weight mapping
         │
         ├── 8. Clean up
         │      a. Remove interior faces (where clothing meets body)
         │      b. decimate_to_budget(clothing_obj, 3000) max triangles
         │
         └── 9. Return ClothingMeshResult
                (object_name, pattern_name, triangle_count, vertex_count)
```

**Data entities:**
- `ClothingMeshResult` (new dataclass): `object_name`, `pattern_name`, `triangle_count`, `vertex_count`
- `CLOTHING_PATTERNS` (new in `clothing/patterns.py`): Dict of pattern definitions
- `BODY_REGION_VERTEX_GROUPS` (new in `clothing/patterns.py`): MB-Lab / TurboSquid region → vertex group mappings

### 3.4 Weight Painting Flow (G4)

```
Body mesh + Armature (after MB-Lab generation + stub bones + hair + clothing)
     │
     ▼
WeightPaintEngine.paint_smooth(obj, armature, regions=None, iterations=3, min_influence_groups=3)
     │
     ├── 1. Run bpy.ops.object.parent_with_auto_weights — baseline
     │
     ├── 2. For each region in SMOOTH_REGIONS (or all):
     │      neck:         [head, neck, spine_02, spine_03]
     │      left_shoulder: [clavicle_L, upper_arm_L, spine_02]
     │      right_shoulder:[clavicle_R, upper_arm_R, spine_02]
     │      left_hip:      [thigh_L, pelvis, spine]
     │      right_hip:     [thigh_R, pelvis, spine]
     │      left_knee:     [thigh_L, calf_L, shin_L]
     │      right_knee:    [thigh_R, calf_R, shin_R]
     │      left_elbow:    [upper_arm_L, forearm_L, lowerarm_L]
     │      right_elbow:   [upper_arm_R, forearm_R, lowerarm_R]
     │
     ├── 3. For each boundary vertex:
     │      a. Smooth weights across joint (3 iterations default)
     │      b. Ensure ≥ min_influence_groups vertex groups per vertex
     │      c. Normalize all vertex groups to sum to 1.0
     │
     ├── 4. Apply max_influence limits (no rigid 1-bone areas at joints)
     │
     └── 5. For hair and clothing meshes:
            auto-invoke transfer_weights(source=body, target=target, armature)
```

**Data entities:**
- `WeightPaintReport` (new dataclass): `avg_groups_per_vertex`, `min_groups_per_vertex`, `max_weight_variance`, `normalization_rate`, `score`
- `SMOOTH_REGIONS` (new in `rigs/weights.py`): Joint → bone names mapping
- Quality score formula: `0.4 × (avg_groups/4.0) + 0.3 × normalization_rate + 0.3 × (1.0 - max_variance)`

### 3.5 Rig Verification Flow (G5)

```
VRM file path (on disk, post-export)
     │
     ▼
RigVerifier.verify(vrm_path)
     │
     ├── 1. Open VRM binary (glTF container)
     │      → Parse JSON chunk (glTF JSON format)
     │      → No Blender needed — pure struct/json parsing
     │
     ├── 2. Check VRM extension data
     │      → VRMC_vrm_extensions present?
     │
     ├── 3. Count humanoid bones
     │      → VRM_REQUIRED_HUMANOID_BONES (25 total)
     │      → List missing bones
     │      → List extra bones
     │
     ├── 4. Check expression count
     │      → VRMC_vrm.expressions presence
     │      → List expression names (happy, sad, angry, surprised, etc.)
     │
     ├── 5. Check lookAt configuration
     │      → bone rotation mode? morph target mode?
     │
     ├── 6. Check spring bone groups
     │      → Count springBoneGroups
     │      → List group names
     │
     ├── 7. Check first-person annotations
     │      → VRMC_vrm.firstPerson.meshAnnotations present?
     │
     ├── 8. Estimate weight paint quality (if data available)
     │      → Parse mesh data, count vertex groups per vertex
     │
     └── 9. Return RigReport
            (humanoid_bone_count, missing_bones, expression_count,
             look_at_mode, spring_bone_group_count, first_person_annotations,
             weight_paint_score, errors, warnings)
            → to_cli() → formatted terminal output
            → to_json() → structured dict for agents
```

**Data entities:**
- `RigReport` (new dataclass): Full verification report
- `VRM_REQUIRED_HUMANOID_BONES` (in `rigs/verify.py`): List of 25 required bone names
- Exit codes: 0=compliant, 1=warnings, 2=failures

### 3.6 Spring Bone Configuration Flow (G8)

```
HairSpec.physics (HairPhysicsSpec: bounce, stiffness, gravity)
     │
     ▼
configure_hair_spring(armature_name, hair_object_name, physics_config)
     │
     ├── 1. Get armature object in Blender scene
     ├── 2. Find hair bone chain from hair mesh vertex groups
     │      → Identify root bone (connected to head)
      │      → Trace chain: root → end bone
     ├── 3. Create VRM1 springBone spring group
     │      group_name: "hair_spring"
     │      stiffness: physics_config.stiffness || 0.35
     │      gravityPower: physics_config.gravity || 0.3
     │      dragForce: physics_config.drag || 0.4
     │      hitRadius: 0.02
     │      colliderGroups: []
     │      bones: [hair_root → hair_end chain]
     │
     └── 4. Return list of created spring bone group names
```

### 3.7 First-Person Configuration Flow (G8)

```
Mesh names (body, hair, clothing) + Armature name
     │
     ▼
configure_first_person(armature_name, mesh_names, head_bone_name="head")
     │
     ├── 1. Get armature object
     ├── 2. For each mesh:
     │      Identify if mesh is head-related (weighted to head bone)
     │      Head meshes → THIRD_PERSON_ONLY annotation
     │      Body/clothing meshes → AUTO annotation
     ├── 3. Write VRM firstPerson.meshAnnotations
     │
     └── 4. (No return value — modifies VRM extension data directly)
```

---

## 4. Module Dependency Graph

### 4.1 Current Dependencies (Phase 10 and earlier)

```
                    ┌──────────┐
                    │  cli.py  │ ← Entry point
                    └────┬─────┘
                         │ imports
          ┌──────────────┼──────────────────┐
          ▼              ▼                   ▼
   ┌──────────┐   ┌──────────┐      ┌─────────────┐
   │ core/    │   │ core/    │      │ core/       │
   │ pipeline │   │ builder  │      │ constants   │
   └────┬─────┘   └────┬─────┘      └─────────────┘
        │              │
        │              ├─► core/spec.py ─► core/models.py
        │              ├─► core/validate.py ─► core/models.py
        │              ├─► core/errors.py
        │              └─► hair/__init__.py ─► core/models.py, core/textures.py
        │                 face/__init__.py ─► core/models.py
        │                 clothing/__init__.py ─► core/models.py
        │
        ├─► blender_bridge/runner.py (subprocess launcher)
        │      blender_bridge/mesh_ops.py (bpy-dependent)
        │      blender_bridge/scene.py (bpy-dependent)
        │
        ├─► body/forge.py ─► core/models.py, core/constants.py, blender_bridge/*
        │
        ├─► export/vrm.py (bpy-dependent) ← rigs/__init__.py re-exports from here
        │   export/glb.py (bpy-dependent)
        │
        └─► scripts/build_avatar.py (bpy-dependent, runs inside Blender)
               imports: core/spec.py, core/models.py (as needed),
                        blender_bridge/scene.py, blender_bridge/mesh_ops.py,
                        export/vrm.py, face/__init__.py

   Layer: core/       → Pure Python (no bpy)
   Layer: body/        → Imports core/ + bpy (lazy)
   Layer: hair/        → Imports core/ (pure Python config functions)
   Layer: face/        → Imports core/ (pure Python config functions)
   Layer: clothing/    → Imports core/ (pure Python config functions)
   Layer: rigs/        → Re-exports from export/vrm.py (no own modules yet)
   Layer: blender_bridge/ → bpy-dependent helpers
   Layer: export/      → bpy-dependent (VRM/GLB export)
   Layer: scripts/     → bpy-dependent (main build script)
```

### 4.2 Phase 11 New Dependencies

```
NEW MODULES ADDED:

hair/forge.py        ─► hair/utils.py, core/models.py, bpy
hair/straight.py     ─► hair/utils.py, bpy
hair/wavy.py         ─► hair/utils.py, bpy
hair/curly.py        ─► hair/utils.py, bpy
hair/bob.py          ─► hair/utils.py, bpy
hair/ponytail.py     ─► hair/utils.py, bpy
hair/braided.py      ─► hair/utils.py, bpy

clothing/forge.py    ─► clothing/patterns.py, clothing/fit.py, core/models.py, bpy
clothing/patterns.py ─► (pure data, no imports beyond typing)
clothing/fit.py      ─► blender_bridge/mesh_ops.py, bpy

rigs/stub_bones.py   ─► core/constants.py (STUB_BONE_DEFS), bpy
rigs/weights.py      ─► core/constants.py, bpy
rigs/verify.py       ─► (pure glTF parsing, no bpy)
rigs/spring_bones.py ─► core/models.py (SpringBoneGroupSpec), bpy

export/first_person.py ─► bpy

cli/verify_rig.py    ─► rigs/verify.py (RigVerifier, RigReport)
```

### 4.3 Updated rigs/__init__.py Dependency

```
BEFORE:
  rigs/__init__.py → from hamr.export.vrm import MB_LAB_BONE_MAP, VRM_REQUIRED_BONES

AFTER:
  rigs/__init__.py → from hamr.rigs.stub_bones import create_missing_bones, StubBoneResult
                    from hamr.rigs.weights import WeightPaintEngine, WeightPaintReport
                    from hamr.rigs.verify import RigVerifier, RigReport
                    from hamr.rigs.spring_bones import configure_hair_spring, SpringBoneConfig
                    (also still re-exports MB_LAB_BONE_MAP, VRM_REQUIRED_BONES from export/vrm)
```

### 4.4 Updated scripts/build_avatar.py Dependency

```
BEFORE:
  build_avatar.py → blender_bridge/scene, blender_bridge/mesh_ops,
                    export/vrm, face/__init__ (for shape key maps)

AFTER (Phase 11 additions):
  build_avatar.py → + rigs.stub_bones (create_missing_bones)
                    + hair.forge (HairForge)
                    + clothing.forge (ClothingForge)
                    + rigs.weights (WeightPaintEngine)
                    + rigs.spring_bones (configure_hair_spring)
                    + export.first_person (configure_first_person)
```

---

## 5. Blender-Side vs Python-Side Boundary

### 5.1 Strict Boundary Rule

The architecture enforces a strict boundary between pure Python code (testable without Blender) and Blender-dependent code (requires `bpy`, must run in Blender subprocess). This boundary is defined by the `BLENDER_AVAILABLE` flag pattern:

```python
try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None
    BLENDER_AVAILABLE = False
```

### 5.2 Pure Python Side (No bpy)

These modules run **outside** Blender. They handle configuration, validation, texture generation, spec parsing, and pipeline orchestration. All can be unit-tested without Blender.

| Module | Function |
|--------|----------|
| `core/spec.py` | YAML parsing → CharacterSpec |
| `core/models.py` | Dataclass definitions (CharacterSpec, BodySpec, etc.) |
| `core/constants.py` | Default values, bone maps, presets |
| `core/validate.py` | Spec field validation |
| `core/errors.py` | Error types |
| `core/textures.py` | Pillow + NumPy procedural texture generation |
| `core/pipeline.py` | Orchestrator — launches Blender subprocess |
| `core/builder.py` | Alternative entry — also launches Blender subprocess |
| `core/iterate.py` | Placeholder for agent refinement |
| `core/inspect.py` | Placeholder for VRM inspection (superseded by rigs/verify.py) |
| `hair/__init__.py` | `resolve_hair()` — config-only pure Python |
| `face/__init__.py` | `resolve_face()` — config-only pure Python |
| `clothing/__init__.py` | `resolve_clothing()` — config-only pure Python |
| `body/presets.py` | Preset name mappings |
| **NEW** `clothing/patterns.py` | CLOTHING_PATTERNS, BODY_REGION_VERTEX_GROUPS — pure data |
| **NEW** `rigs/verify.py` | RigVerifier — glTF binary parsing, no Blender |
| **NEW** `cli/verify_rig.py` | CLI handler — calls RigVerifier |

### 5.3 Blender Side (Requires bpy)

These modules run **inside** the Blender subprocess. They manipulate the 3D scene, armature, meshes, and export VRM. All require `BLENDER_AVAILABLE = True`.

| Module | Function |
|--------|----------|
| `blender_bridge/runner.py` | **Exception**: Launches Blender but doesn't import bpy. |
| `blender_bridge/scene.py` | Scene creation, cleanup, armature/mesh finding |
| `blender_bridge/mesh_ops.py` | Shape keys, scaling, material ops, object duplication |
| `scripts/build_avatar.py` | **Main Blender-side entry point** — orchestrates entire build |
| `body/forge.py` | Body generation (lazy bpy import) |
| `export/vrm.py` | VRM 1.0 export (lazy bpy import) |
| `export/glb.py` | GLB export (lazy bpy import) |
| **NEW** `hair/forge.py` | HairForge mesh generation |
| **NEW** `hair/straight.py` | Straight hair mesh generation |
| **NEW** `hair/wavy.py` | Wavy hair mesh generation |
| **NEW** `hair/curly.py` | Curly hair mesh generation |
| **NEW** `hair/bob.py` | Bob cut mesh generation |
| **NEW** `hair/ponytail.py` | Ponytail mesh generation |
| **NEW** `hair/braided.py` | Braided hair mesh generation |
| **NEW** `hair/utils.py` | Scalp detection, guide curves, curve-to-mesh, vertex gradients |
| **NEW** `clothing/forge.py` | ClothingForge mesh generation |
| **NEW** `clothing/fit.py` | Shrinkwrap, weight transfer, body region separation |
| **NEW** `rigs/stub_bones.py` | Create missing bones ( jaw, leftEye, rightEye) |
| **NEW** `rigs/weights.py` | WeightPaintEngine — Blender weight paint ops |
| **NEW** `rigs/spring_bones.py` | VRM 1.0 spring bone group configuration |
| **NEW** `export/first_person.py` | VRM 1.0 first-person annotation configuration |

### 5.4 Bridge Mechanism

The two sides communicate exclusively through:

1. **JSON spec file on disk** — Python side serializes CharacterSpec + forge_config to `.hamr_{name}_spec.json`, passes path via `--spec` argument
2. **Blender subprocess** — `runner.py` launches `blender --background --python build_avatar.py` with `--spec` and `--output` arguments
3. **VRM file on disk** — Blender side writes the `.vrm` output file
4. **Process exit code + stdout/stderr** — Python side checks `BlenderResult.success` and parses stdout

There is **no direct Python ↔ Blender API call**. All Blender operations happen inside the subprocess. The Python side is purely orchestration and configuration.

### 5.5 Two-Layer Forge Pattern (AD-11.7)

Each forge has **two layers**:

| Layer | Runs | Input | Output | Blender? |
|-------|------|-------|--------|----------|
| Config | Pure Python | `HairSpec` / `ClothingSpec` | `HairBuildResult` / `ClothingBuildResult` (dict) | No |
| Mesh | Blender subprocess | `HairSpec` + head mesh + armature | `HairMeshResult` / `ClothingMeshResult` (Blender objects) | Yes |

The config layer (`resolve_hair()`, `resolve_clothing()`) remains unchanged. The mesh layer (`HairForge.generate()`, `ClothingForge.generate()`) is additive and runs only inside Blender.

---

## 6. Gaps and Inconsistencies Between PHASE_11.md Goals and ARCHITECTURE_11.md Design

### 6.1 Gaps Found

| # | Gap | PHASE_11.md | ARCHITECTURE_11.md | Resolution |
|---|-----|-------------|---------------------|------------|
| G-1 | **twin-tails style not in arch** | PHASE_11 G2: "Support styles: ... twin-tails" | ARCHITECTURE_11 §1.1: Lists straight, wavy, curly, braided, ponytail, bob, spiky — **no twin-tails, no spiky generator module** | Either add `hair/twin_tails.py` and `hair/spiky.py`, or map twin-tails → braided variant and spiky → straight variant. Verify with task T2. |
| G-2 | **"bun" style ambiguity** | PHASE_11 G2: lists "bun" as a supported style, ARCHITECTURE_11 shows "bun" dispatching to `bob.py` | ARCHITECTURE_11 §3.5: `"bun" → bob.generate() (variant)` | Placeholder matching is fine, but the templates in `hair/__init__.py` current code already include "bun" as a `HAIR_STYLES` key. Confirm `bob.py` handles both. |
| G-3 | **FirstPersonSpec not in data flow** | PHASE_11 G8: "First-person annotations: mesh visibility flags per render subset" | ARCHITECTURE_11 §3.10: `configure_first_person()` takes mesh_names and head_bone_name | `FirstPersonSpec` is defined in §4.1 (models.py changes) but no data flow shows how `CharacterSpec.first_person` gets from YAML spec → JSON → `configure_first_person()`. The YAML spec format needs to specify `first_person.hide_head_mesh: true`. |
| G-4 | **No `spiky` module** | PHASE_11 G2: "Support styles: ... spiky" | ARCHITECTURE_11 module list has no `hair/spiky.py` | Add `spiky.py` or dispatch "spiky" as a short variant of "straight". |
| G-5 | **`HairPhysicsSpec` → spring bones gap** | PHASE_11 G8: "Spring bone groups: at least 1 group for hair" | ARCHITECTURE_11 §3.4: `configure_hair_spring()` takes `physics_config` dict | The current `HairPhysicsSpec` dataclass has `bounce`, `stiffness`, `gravity`, `damping`. The `SpringBoneConfig` uses `stiffness`, `gravity_power`, `drag_force`, `hit_radius`. The field mapping (bounce→drag?, damping→?) needs explicit documentation. |
| G-6 | **spring_bones.py uses armature_name (string)** | Architecture §3.4: `configure_hair_spring(armature_name: str, ...)` | vrm.py also uses string-based armature names | Consistent pattern, but verify all Blender-side modules use string names (not bpy object refs) for cross-module consistency. |
| G-7 | **RigVerifier weight_paint_score requires glTF mesh data** | PHASE_11 G5: "weight paint quality score" | ARCHITECTURE_11 §3.3: `RigVerifier.verify()` parses glTF binary | Weight paint scoring from glTF requires parsing accessor data for vertex group weights. This is non-trivial and may need to fall back to "heuristic" scoring if glTF accessor parsing is incomplete. The architecture says "pure glTF parsing" but doesn't detail how vertex group weights are extracted from binary. |
| G-8 | **Preset loading mechanism undefined** | PHASE_11 G6: "`hamr build --preset casual_f`" | ARCHITECTURE_11 §4.10: "Add --preset flag to build command" | How does `--preset` resolve? Does it read YAML from `assets/presets/` and merge with CLI overrides? The pipeline.py changes say "preset loading" but don't define the lookup mechanism. Need: `preset_path = ASSETS_DIR / "presets" / f"{name}.yaml"`. |
| G-9 | **`--blender-timeout` vs `blender_timeout` constructor parameter** | ARCHITECTURE_11 §4.10: `--blender-timeout` CLI flag with default 120 | Current `pipeline.py`: `BuildPipeline.__init__(blender_timeout=600)` | The pipeline constructor defaults to 600 but Phase 11 says "reduce from 600→120". Both the constructor default AND the CLI flag must change to 120. |
| G-10 | **Missing `HairStyle` enum values** | PHASE_11 G2: twin-tails, spiky as styles | Current `models.py` `HairStyle` enum may not include all new styles | Need to add `TWIN_TAILS`, `SPIKY` to the `HairStyle` enum and update `validate.py` to accept them. |
| G-11 | **`ClothingSpec.type` → pattern mapping** | PHASE_11 G3: "t-shirt, shorts/skirt, dress, hoodie, school uniform" | ARCHITECTURE_11 §3.8: patterns.py defines tshirt, shorts, skirt, dress, hoodie, school_uniform | Current `ClothingSpec` may have a `type` field with different naming (e.g., "full-outfit", "top"). Need to map spec type names to pattern keys, or update `ClothingSpec.type` values. |
| G-12 | **No `--dry-run` for mesh generation** | `--dry-run` flag exists in CLI for config-only resolution | Phase 11 adds mesh generation that requires Blender | Need to clarify: does `--dry-run` skip Blender entirely (config-only) or just skip mesh generation? The two-layer forge pattern implies dry-run = config layer only. |

### 6.2 Inconsistencies Found

| # | Inconsistency | Details |
|---|---------------|---------|
| I-1 | **`build_avatar.py` step numbering** | Current `build_avatar.py` has steps: 4d (_apply_spec), then new steps 4e-4j. But the architecture shows different ordering: stub bones BEFORE hair (correct), hair BEFORE clothing (correct), but weight painting comes AFTER both hair and clothing (correct). The build_avatar.py modification list in §4.4 matches this ordering. Verify the actual script implementation matches. |
| I-2 | **`rigs/__init__.py` circular import risk** | Currently `rigs/__init__.py` imports from `export/vrm.py`. With Phase 11, `rigs/` gets its own modules. But `spring_bones.py` needs VRM extension data, which is also set in `export/vrm.py`. Need to ensure `spring_bones.py` doesn't import from `export/vrm.py` and cause a circular dependency. Recommended: `spring_bones.py` writes to the same VRM extension object that `export_vrm` reads later. |
| I-3 | **`runner.py` timeout vs `pipeline.py` timeout** | `runner.py` has its own timeout (currently 600s). `pipeline.py` passes `blender_timeout` to `run_blender_script`. These must be consistent. ARCHITECTURE_11 says reduce both to 120s. |
| I-4 | **`ClothingSpec` in models.py vs pattern keys** | Current `ClothingSpec` type field uses values like "full-outfit", "top", "bottom". `CLOTHING_PATTERNS` uses "tshirt", "shorts", "skirt". Need a mapping function or spec type enum update. |
| I-5 | **SpringBoneGroupSpec vs configure_hair_spring parameters** | `SpringBoneGroupSpec` defines `stiffness`, `gravity_power`, `drag_force`, `hit_radius`. `configure_hair_spring()` takes `physics_config: dict[str, float]`. The architecture needs to clarify how `HairPhysicsSpec` (in current code) maps to `SpringBoneGroupSpec` (new), and whether `configure_hair_spring` receives `SpringBoneGroupSpec` or a raw dict. |

### 6.3 Architecture Decisions That Need Explicit Acknowledgment

| # | Decision | Location | Notes |
|---|----------|----------|-------|
| D-11.1 | Stub bones tagged `_hamr_stub=True` | §AD-11.1 | Must be stripped or handled during VRM export if VRM validator rejects custom properties on bones |
| D-11.2 | Hair as Bezier curves → mesh (no particles) | §AD-11.2 | Correct for headless/Pi. Verify `to_mesh()` conversion handles UV mapping for vertex colors |
| D-11.3 | Shrinkwrap clothing fit | §AD-11.3 | Requires body mesh to have correct normals. MB-Lab output must have outward-facing normals. |
| D-11.4 | Weight paint score ≥ 0.7 = pass | §AD-11.4 | Score formula: `0.4×(avg_groups/4) + 0.3×norm_rate + 0.3×(1-variance)`. Need validation testing. |
| D-11.5 | Every feature needs a preset | §AD-11.5 | 6 presets must exercise: stub bones, hair, clothing, weight paint, spring bones, first-person |
| D-11.6 | 45s / 1.5GB budget on Pi 5 | §AD-11.6 | Hair 500ms, clothing 300ms, weight paint 200ms budget. Needs profiling on actual hardware. |
| D-11.7 | Two-layer forge pattern | §AD-11.7 | Critical: mesh layer is additive, config layer unchanged. Backward compat is preserved. |
| D-11.8 | Scalp detection fallback chain | §AD-11.8 | vertex groups → UV zone → normal direction. Must test on both MB-Lab and TurboSquid meshes. |
| D-11.9 | Clothing as separate objects | §AD-11.9 | Standard for VRM. Enables material variant switching. |
| D-11.10 | Performance budget architecture | §AD-11.10 | Lazy textures, triangle budgets, explicit `purge_orphans()` between steps, 120s Blender timeout. |
| D-11.11 | RigVerifier is Blender-independent | §AD-11.11 | Pure glTF parsing. Weight paint scoring may be limited to heuristic from glTF accessor data. |

---

## 7. Summary: Module Count by Status

| Status | Count | Modules |
|--------|-------|---------|
| **Unchanged** | 13 | `core/spec.py`, `core/models.py` (minor additions), `core/validate.py`, `core/textures.py`, `core/errors.py`, `core/iterate.py`, `core/inspect.py`, `core/pipeline.py` (modified), `core/builder.py`, `face/__init__.py`, `export/glb.py`, `blender_bridge/__init__.py`, `body/presets.py` |
| **Modified** | 12 | `core/models.py` (add dataclasses), `core/constants.py` (add constants), `core/pipeline.py` (add steps, timeout), `hair/__init__.py` (add HairForge import), `clothing/__init__.py` (add ClothingForge import), `rigs/__init__.py` (full API), `export/vrm.py` (spring bones, FP), `export/__init__.py` (add first_person), `blender_bridge/runner.py` (timeout, cleanup), `blender_bridge/mesh_ops.py` (add functions), `blender_bridge/scene.py` (memory cleanup), `scripts/build_avatar.py` (6 new steps), `cli.py` (verify-rig, --preset), `__init__.py` (version bump, new exports) |
| **New** | 15 | `hair/forge.py`, `hair/straight.py`, `hair/wavy.py`, `hair/curly.py`, `hair/bob.py`, `hair/ponytail.py`, `hair/braided.py`, `hair/utils.py`, `clothing/forge.py`, `clothing/patterns.py`, `clothing/fit.py`, `rigs/stub_bones.py`, `rigs/weights.py`, `rigs/verify.py`, `rigs/spring_bones.py`, `export/first_person.py`, `cli/verify_rig.py`, 6× `assets/presets/*.yaml` |
| **Total .py files (Phase 10)** | 28 | |
| **Total .py files (Phase 11)** | ~43 | 28 existing + ~15 new |

---

*The Cartographer has mapped every trail. Every module, every data path, every boundary. The map is the territory.* ᚺᚨᛗᚱ