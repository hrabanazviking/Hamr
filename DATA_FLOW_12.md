# ᚺᚨᛗᚱ — Phase 12 Data Flow Map: Yggdrasil

> *The roots draw from specs and presets. The trunk channels the pipeline. The branches bear VRM output. Every leaf is a test.*

**Author:** Védis Eikleið, THE CARTOGRAPHER  
**Version:** v0.5.0 (Phase 12)  
**Date:** 2026-05-08

---

## 1. Current vs Proposed Pipeline Comparison

### 1.1 Current Pipeline (v0.4.0) — `build_avatar.py`

The current `build_avatar.py` (945 lines) is a monolithic script with **5 steps** that import **zero** Phase 11 modules:

```
┌─────────────────────────────────────────────────────────────┐
│ CURRENT build_avatar.py (v0.4.0) — 5 STEPS                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 0: Enable VRM add-on                                  │
│  Step 1: Clear scene                                         │
│  Step 2: Import base mesh (MB-Lab or file)                  │
│  Step 3: Apply spec transformations:                         │
│          ├── _apply_colors()       → skin/eye/hair tint    │
│          ├── _apply_height()       → armature scale         │
│          ├── _apply_face_from_forge()  → shape keys         │
│          ├── _apply_hair_from_forge()  → curl/volume keys   │
│          ├── _apply_clothing_from_forge() → material tints  │
│          ├── _apply_vrm_humanoid()  → bone mapping          │
│          ├── _apply_vrm_metadata() → title/author/license   │
│          ├── _apply_vrm_expressions() → shape key bindings  │
│          └── _apply_vrm_look_at()   → eye tracking config   │
│  Step 4: Export VRM                                         │
│  Step 5: Post-export validation (_validate_vrm)             │
│                                                             │
│  ❌ No stub bones                                           │
│  ❌ No hair mesh generation                                 │
│  ❌ No clothing mesh generation                             │
│  ❌ No weight paint smoothing                               │
│  ❌ No spring bones                                        │
│  ❌ No first-person annotations                             │
│  ❌ No performance budget check                             │
│  ❌ No preset merging                                       │
│  ❌ No rig verification                                     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Proposed Pipeline (v0.5.0) — Yggdrasil

The proposed pipeline restructures into **14 explicit stages** with Phase 11 module calls at every branch:

```
┌─────────────────────────────────────────────────────────────┐
│ PROPOSED build_avatar.py (v0.5.0) — 14 STAGES              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Stage 0:  Enable VRM add-on                                 │
│  Stage 1:  Clear scene                                       │
│  Stage 2:  Import base mesh                                  │
│  Stage 3:  Apply body spec transformations                   │
│                                                             │
│  ── PHASE 12 NEW INTEGRATION ──────────────────────────    │
│  Stage 3a: _integrate_stub_bones()                           │
│             → hamr.rigs.stub_bones.create_missing_bones()   │
│  Stage 3b: _integrate_hair_mesh()                            │
│             → hamr.hair.mesh.HairMeshGenerator.generate()   │
│  Stage 3c: _integrate_clothing_meshes()                      │
│             → hamr.clothing.mesh.ClothingMeshGenerator()    │
│             .generate() for each spec.clothing item          │
│  Stage 3d: _integrate_weight_paint()                         │
│             → hamr.rigs.weights.WeightPaintEngine             │
│             .paint_smooth() / .transfer_weights() /          │
│             .normalize_weights() / .get_quality_score()      │
│  Stage 3e: _integrate_spring_bones()                         │
│             → hamr.rigs.spring_bones.apply_spring_bones()    │
│             → configure_hair_spring()                        │
│             → configure_breast_spring()                      │
│             → configure_clothing_spring()                    │
│  Stage 3f: _integrate_first_person()                         │
│             → hamr.export.first_person                        │
│             .configure_first_person()                        │
│  ── END PHASE 12 INTEGRATION ───────────────────────      │
│                                                             │
│  Stage 4:  VRM humanoid bone mapping + stub merge            │
│  Stage 5:  VRM metadata                                      │
│  Stage 6:  VRM expressions (existing)                        │
│  Stage 7:  VRM lookAt (existing)                            │
│  Stage 8:  Export VRM                                        │
│  Stage 9:  Post-export validation                            │
│  Stage 10: Rig verification (NEW)                           │
│             → hamr.rigs.verify.RigVerifier.verify()          │
│                                                             │
│  ── PRE-FLIGHT (in pipeline.py, before Blender) ─────      │
│  ★ Perf budget check → hamr.core.perf.check_budget()       │
│  ★ Preset merge       → hamr.core.presets.deep_merge()     │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Key Differences Summary

| Aspect | Current (v0.4.0) | Proposed (v0.5.0) |
|--------|-------------------|---------------------|
| Steps/Stages | 5 (Step 0–4 + validation) | 14 (Stage 0–10 + 3a–3f) |
| Phase 11 calls | 0 | 10 |
| Stub bones | ❌ Not called | ✅ `create_missing_bones()` at Stage 3a |
| Hair mesh | ❌ Not called | ✅ `HairMeshGenerator.generate()` at Stage 3b |
| Clothing mesh | ❌ Not called | ✅ `ClothingMeshGenerator.generate()` at Stage 3c |
| Weight paint | ❌ Not called | ✅ `WeightPaintEngine.*` at Stage 3d |
| Spring bones | ❌ Not called | ✅ `apply_spring_springs()` at Stage 3e |
| First-person | ❌ Not called | ✅ `configure_first_person()` at Stage 3f |
| Rig verification | ❌ Not called | ✅ `RigVerifier.verify()` at Stage 10 |
| Preset merge | ❌ Not in pipeline.py | ✅ `deep_merge_preset()` before Blender |
| Perf budget | ❌ Not checked | ✅ `check_budget()` as pre-flight gate |
| VRM bone mapping | `_apply_vrm_humanoid()` | Same + stub bone map merge |
| Error handling | Per-step try/catch | Per-stage try/catch with timing report |
| Material system | Tint-only (existing) | Tint + `MaterialForge` (Phase 12 new) |
| Collision meshes | ❌ None | ✅ `CollisionForge` (Phase 12 new) |
| Expression binding | Hardcoded maps | Discovery + fallback (Phase 12 new) |

---

## 2. Integration Gap Table

All Phase 11 modules and their current call status from `build_avatar.py`:

| # | Module | File | Lines | Export Symbol | Called from `build_avatar.py`? | Called from `pipeline.py`? | Call Site in v0.5.0 |
|---|--------|------|-------|---------------|-------------------------------|---------------------------|---------------------|
| 1 | Stub Bones | `rigs/stub_bones.py` | 418 | `create_missing_bones()` | ❌ No | ❌ No | Stage 3a in `build_avatar.py` |
| 2 | Hair Mesh | `hair/mesh.py` | 752 | `HairMeshGenerator.generate()` | ❌ No | ❌ No | Stage 3b in `build_avatar.py` |
| 3 | Clothing Mesh | `clothing/mesh.py` | 726 | `ClothingMeshGenerator.generate()` | ❌ No | ❌ No | Stage 3c in `build_avatar.py` |
| 4 | Weight Paint | `rigs/weights.py` | 652 | `WeightPaintEngine.paint_smooth()` | ❌ No | ❌ No | Stage 3d in `build_avatar.py` |
| 5 | Weight Paint (score) | `rigs/weights.py` | — | `WeightPaintEngine.get_quality_score()` | ❌ No | ❌ No | Stage 3d in `build_avatar.py` |
| 6 | Weight Paint (transfer) | `rigs/weights.py` | — | `WeightPaintEngine.transfer_weights()` | ❌ No | ❌ No | Stage 3d in `build_avatar.py` |
| 7 | Rig Verify | `rigs/verify.py` | 574 | `RigVerifier.verify()` | ❌ No | ❌ No | Stage 10 in `build_avatar.py` |
| 8 | Spring Bones | `rigs/spring_bones.py` | 478 | `apply_spring_bones()` | ❌ No | ❌ No | Stage 3e in `build_avatar.py` |
| 9 | Spring Bones (hair) | `rigs/spring_bones.py` | — | `configure_hair_spring()` | ❌ No | ❌ No | Stage 3e in `build_avatar.py` |
| 10 | Spring Bones (breast) | `rigs/spring_bones.py` | — | `configure_breast_spring()` | ❌ No | ❌ No | Stage 3e in `build_avatar.py` |
| 11 | Spring Bones (clothing) | `rigs/spring_bones.py` | — | `configure_clothing_spring()` | ❌ No | ❌ No | Stage 3e in `build_avatar.py` |
| 12 | First-Person | `export/first_person.py` | 305 | `configure_first_person()` | ❌ No | ❌ No | Stage 3f in `build_avatar.py` |
| 13 | First-Person (classify) | `export/first_person.py` | — | `classify_mesh_for_fp()` | ❌ No | ❌ No | Stage 3f in `build_avatar.py` |
| 14 | Perf Budget | `core/perf.py` | 460 | `check_budget()` | ❌ No | ❌ No | Pre-flight in `pipeline.py` |
| 15 | Perf Budget (score) | `core/perf.py` | — | `PerformanceBudget` | ❌ No | ❌ No | Pre-flight in `pipeline.py` |
| 16 | Presets | `core/presets.py` | 722 | `CHARACTER_PRESETS` | ❌ No | ❌ No | Pre-flight in `pipeline.py` + `cli.py` |

**Gap count: 16 out of 16 calls are MISSING in v0.4.0.**

---

## 3. Full Yggdrasil Pipeline Data Flow

### 3.1 End-to-End Data Flow: Preset → VRM → Verify

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          YGGDRASIL FULL DATA FLOW                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                    │
│  │  YAML Spec   │     │ Character    │     │  Validate    │                    │
│  │  OR Preset   │────▶│ Preset Merge │────▶│  Spec Check  │                    │
│  │  --preset X  │     │ deep_merge() │     │ validate()   │                    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘                    │
│                                                     │                           │
│                                                     ▼                           │
│                                             ┌──────────────┐                    │
│           ┌───────────────────────────────── │ Perf Budget  │                   │
│           │                                 │ check_budget()│──❌ FAIL → EXIT   │
│           │                                 └──────┬───────┘                    │
│           │                                        │ ✅ PASS                    │
│           │                                        ▼                            │
│           │                                 ┌──────────────┐                    │
│           │                                 │  Resolve     │                    │
│           │                                 │  Forges      │                    │
│           │                                 │ _resolve_    │                    │
│           │                                 │  forges()    │                    │
│           │                                 └──────┬───────┘                    │
│           │                                        │                            │
│           │                                        ▼                            │
│           │                                 ┌──────────────┐     ┌───────────┐  │
│           │                                 │ Serialize    │────▶│ JSON Spec │  │
│           │                                 │ spec + forge │     │  File      │  │
│           │                                 └──────┬───────┘     └─────┬─────┘  │
│           │                                        │                  │        │
│  ┌────────▼────────────────────────────────────────▼──────────────────▼────┐   │
│  │                    BLENDER SUBPROCESS                                   │   │
│  │                                                                         │   │
│  │  Stage 0:  Enable VRM add-on ──────────────────────────────── python     │   │
│  │  Stage 1:  Clear scene ───────────────────────────────────── bpy.ops   │   │
│  │  Stage 2:  Import base mesh ────────────────────────────── mblab/file  │   │
│  │  Stage 3:  Apply body spec ───────────────────────────── _apply_spec() │   │
│  │            ├── colors, height, face, hair_color, clothing_tint         │   │
│  │                                                                         │   │
│  │  Stage 3a: STUB BONES ────────── hamr.rigs.stub_bones                 │   │
│  │            data_in:  armature_name, base_type="mblab"                   │   │
│  │            data_out: StubBoneResult{created_bones, stub_map}           │   │
│  │                       └──▶ feeds into VRM bone mapping (Stage 4)      │   │
│  │                                                                         │   │
│  │  Stage 3b: HAIR MESH ─────────── hamr.hair.mesh                       │   │
│  │            data_in:  style_name, head_center, head_radius,              │   │
│  │                      color_config{roots_hsv, tips_hsv}                 │   │
│  │            data_out: HairMeshResult{object_name, vertex_count,         │   │
│  │                      triangle_count, bone_chain}                        │   │
│  │                       ├──▶ feeds into weight paint (Stage 3d)          │   │
│  │                       └──▶ feeds into spring bones (Stage 3e)          │   │
│  │                                                                         │   │
│  │  Stage 3c: CLOTHING MESHES ───── hamr.clothing.mesh                   │   │
│  │            data_in:  clothing_spec{}, body_mesh_name,                   │   │
│  │                      armature_name                                     │   │
│  │            data_out: [ClothingMeshResult{mesh_name, triangle_count,    │   │
│  │                      weight_transferred}, ...]                          │   │
│  │                       ├──▶ feeds into weight paint (Stage 3d)          │   │
│  │                       └──▶ feeds into spring bones (Stage 3e)          │   │
│  │                                                                         │   │
│  │  Stage 3d: WEIGHT PAINT ───────── hamr.rigs.weights                     │   │
│  │            data_in:  armature_name, body_mesh_name,                    │   │
│  │                      hair_result, clothing_results                      │   │
│  │            calls:   .paint_smooth() on body                            │   │
│  │                     .transfer_weights() body→clothing                   │   │
│  │                     .normalize_weights() on all meshes                  │   │
│  │                     .get_quality_score() → report for logging            │   │
│  │            data_out: weight paint quality score (logged)               │   │
│  │                                                                         │   │
│  │  Stage 3e: SPRING BONES ───────── hamr.rigs.spring_bones               │   │
│  │            data_in:  armature_name, hair_result.bone_chain,             │   │
│  │                      clothing_results, body_spec,                      │   │
│  │                      DEFAULT_COLLIDERS                                  │   │
│  │            calls:   configure_hair_spring(physics_spec)                │   │
│  │                     configure_breast_spring(body_spec)                  │   │
│  │                     configure_clothing_spring(cloth_name, type)          │   │
│  │                     apply_spring_bones(armature, groups, colliders)     │   │
│  │            data_out: spring bone groups + colliders written to VRM ext │   │
│  │                                                                         │   │
│  │  Stage 3f: FIRST-PERSON ───────── hamr.export.first_person            │   │
│  │            data_in:  armature_name, all mesh_names[]                   │   │
│  │            calls:   classify_mesh_for_fp() per mesh                    │   │
│  │                     configure_first_person(armature, meshes)            │   │
│  │            data_out: mesh annotations on VRM extension                │   │
│  │                                                                         │   │
│  │  Stage 4:  VRM humanoid mapping + stub bone merge ──── _apply_vrm_    │   │
│  │            humanoid() now merges stub_map into bone_map                │   │
│  │                                                                         │   │
│  │  Stage 5:  VRM metadata ───────────────── _apply_vrm_metadata()        │   │
│  │  Stage 6:  VRM expressions ────────────── _apply_vrm_expressions()     │   │
│  │  Stage 7:  VRM lookAt ─────────────────── _apply_vrm_look_at()        │   │
│  │  Stage 8:  Export VRM ──────────────────── bpy.ops.export_scene.vrm   │   │
│  │  Stage 9:  Post-export validation ───────── _validate_vrm()            │   │
│  │  Stage 10: Rig verification ────────────── RigVerifier.verify()         │   │
│  │                                                                         │   │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  POST-BLENDER (Python orchestration)                                    │   │
│  │                                                                         │   │
│  │  Step 8:  Verify output file exists and is valid glTF                   │   │
│  │  Step 9:  Clean up temp spec JSON                                       │   │
│  │  Step 10: Return PipelineResult(success, output_path, timing)           │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Dependencies Between Stages

The pipeline has strict ordering dependencies. Each stage's output flows into subsequent stages:

```
Stage 3a (stub_bones)
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
Stage 3b (hair_mesh)           Stage 4 (VRM bone mapping)
    │                          receives stub_map
    ▼
Stage 3c (clothing_meshes)
    │
    ▼
Stage 3d (weight_paint)
    │ ← needs: body_mesh, hair_result, clothing_results
    ▼
Stage 3e (spring_bones)
    │ ← needs: hair_result.bone_chain, clothing_results, body_spec
    ▼
Stage 3f (first_person)
    │ ← needs: armature_name, all mesh_names
    ▼
Stage 4 (VRM bone mapping)
    │ ← needs: stub_result (merged into bone_map)
    ▼
Stages 5-7 (metadata, expressions, lookAt)
    │
    ▼
Stage 8 (VRM export)
    │
    ▼
Stage 9 (post-export validation)
    │
    ▼
Stage 10 (rig verification)
```

### 3.3 Pre-Flight Data Flow (Outside Blender)

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ CLI args  │────▶│ pipeline.py  │────▶│ Spec.from_   │────▶│ validate_    │
│ --preset  │     │ .build()     │     │ yaml()       │     │ spec()       │
│ --spec    │     │              │     │              │     │              │
│ --budget  │     │              │     │              │     │              │
│ --force   │     │              │     │              │     │              │
└──────────┘     └──────┬───────┘     └──────────────┘     └──────┬───────┘
                        │                                           │
                        │                                           ▼
                        │                                    ┌──────────────┐
                        │                                    │ Perf Budget  │
                        │                                    │ check_       │
                        │                                    │ budget()     │
                        │                                    └──────┬───────┘
                        │                                           │
                        │              FAIL ◀──────────────────── ❌ Budget
                        │                                           │ ✅ PASS
                        │                                           ▼
                        │                                    ┌──────────────┐
                        │                                    │ Preset Merge │
                        │                                    │ deep_merge_  │
                        │                                    │ preset()     │
                        │                                    └──────┬───────┘
                        │                                           │
                        │                                           ▼
                        │                                    ┌──────────────┐
                        │                                    │ Forge        │
                        │                                    │ Resolution   │
                        │                                    │ _resolve_    │
                        │                                    │ forges()     │
                        │                                    └──────┬───────┘
                        │                                           │
                        │                                           ▼
                        │                                    ┌──────────────┐
                        │                                    │ Serialize    │
                        │                                    │ → JSON file  │
                        │                                    └──────┬───────┘
                        │                                           │
                        └──────────────────────────────────────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ Blender Subproc   │
                                  │ build_avatar.py   │
                                  └──────────────────┘
```

---

## 4. CLI Command Data Flows

### 4.1 `hamr build --preset <name> --out output/`

```
hamr build --preset casual_f --out output/
    │
    ▼
cli.py::cmd_build()
    │
    ├── BuildPipeline(blender_path, timeout, keep_temp)
    │
    ├── pipeline.py::BuildPipeline.build()
    │   │
    │   ├── 1. Spec.from_yaml(spec_path)
    │   │      └── If --preset: CHARACTER_PRESETS[name] deep-merged into spec
    │   │
    │   ├── 2. validate_spec(spec.character)
    │   │      └── Returns list of validation errors (empty = valid)
    │   │
    │   ├── 3. check_budget(spec.character, PerformanceBudget(tier))
    │   │      └── If --force-over-budget: skip rejection
    │   │      └── If over budget without --force: return PipelineResult(errors)
    │   │
    │   ├── 4. _resolve_forges(spec.character)
    │   │      └── Returns: {hair: {...}, face: {...}, clothing: [{...}]}
    │   │
    │   ├── 5. Serialize spec + forge_config → JSON temp file
    │   │
    │   ├── 6. run_blender_script(build_avatar.py, args)
    │   │      └── Blender subprocess runs Stages 0-10
    │   │
    │   └── 7. Verify output, clean up, return PipelineResult
    │
    └── Print result to stdout
```

### 4.2 `hamr build --spec <file> --out output/`

Same as 4.1 but without preset merge. The `--spec` path is the only spec source.

### 4.3 `hamr verify-rig <vrm> --json`

```
hamr verify-rig output/avatar.vrm --json
    │
    ▼
cli.py::cmd_verify_rig()
    │
    ├── rigs/verify.py::verify_vrm_rig(path)
    │      │
    │      ├── Read VRM/GLB binary (struct module, no Blender)
    │      ├── Parse glTF JSON chunk
    │      ├── Extract node names from glTF scenes
    │      ├── Check 25/25 VRM humanoid bones present
    │      ├── Check bone hierarchy
    │      └── Return: {valid: bool, bones_present: [...], missing: [...], warnings: [...]}
    │
    └── Print report (human or JSON format)
```

### 4.4 `hamr check-env --verbose`

```
hamr check-env --verbose
    │
    ▼
cli.py::cmd_check_env()
    │
    ├── BuildPipeline.check_environment()
    │      │
    │      ├── check_blender_available()
    │      ├── get_blender_version()
    │      ├── Check VRM addon (via Blender subprocess)
    │      ├── Check MB-Lab addon (via Blender subprocess)
    │      ├── Check build script exists
    │      │
    │      └── NEW Phase 12 checks:
    │          ├── hamr.rigs.stub_bones importable?
    │          ├── hamr.hair.mesh importable?
    │          ├── hamr.clothing.mesh importable?
    │          ├── hamr.rigs.weights importable?
    │          ├── hamr.rigs.spring_bones importable?
    │          ├── hamr.rigs.verify importable?
    │          ├── hamr.export.first_person importable?
    │          ├── hamr.core.perf importable?
    │          └── hamr.core.presets importable?
    │
    └── Print status report
```

### 4.5 `hamr list-presets --what character`

```
hamr list-presets --what character
    │
    ▼
cli.py::cmd_list_presets()
    │
    └── Print CHARACTER_PRESETS dict
        ├── anime_girl_default
        ├── anime_girl_casual
        ├── anime_boy_default
        ├── anime_boy_casual
        ├── fantasy_warrior
        └── sci_fi_pilot
```

### 4.6 Data Flow: New CLI Arguments

| Argument | Added To | Data Path | Consumed By |
|----------|----------|-----------|-------------|
| `--preset` / `-p` | `build_parser` | `args.preset` → `pipeline.build(preset=)` | `pipeline.py` deep-merge |
| `--budget` / `-B` | `build_parser` | `args.budget` → `pipeline.build(budget=)` | `pipeline.py` perf check |
| `--force-over-budget` | `build_parser` | `args.force_over_budget` → `pipeline.build(force=)` | `pipeline.py` perf gate override |
| `--strict` | `verify_rig_parser` | `args.strict` → `cmd_verify_rig()` | `verify.py` warnings-as-errors |
| `--what` | `list_presets_parser` | `args.what` → `cmd_list_presets()` | Print body/character/both |
| `--json` | (global) | `args.json` → output format | All commands |

---

## 5. Files That Need Modification

### 5.1 Modified Files

| # | File | Change Type | Description |
|---|------|-------------|-------------|
| 1 | `src/hamr/scripts/build_avatar.py` | **Major rewrite** | Add 7 integration functions (`_integrate_stub_bones`, `_integrate_hair_mesh`, `_integrate_clothing_meshes`, `_integrate_weight_paint`, `_integrate_spring_bones`, `_integrate_first_person`, `_verify_rig_post_export`). Add 3 helper functions (`_find_body_mesh`, `_find_armature`, `_dict_to_clothing_spec`). Modify `_apply_vrm_humanoid()` to merge `stub_map`. Restructure `main()` into numbered stages with timing. Add `--preset`, `--budget`, `--perf-check` args to `parse_args()`. Update exit codes to cover new failure modes. |
| 2 | `src/hamr/core/pipeline.py` | **Enhancement** | Add `preset` parameter to `build()`. Add `budget` parameter with tier selection. Add `force_over_budget` parameter. Insert `check_budget()` call after `validate_spec()` (pre-flight gate). Insert `deep_merge_preset()` call when `preset` is specified. Pass `verify=True/False` flag to Blender script via args. |
| 3 | `src/hamr/cli.py` | **Enhancement** | Add `--preset`/`-p` with `choices=list(CHARACTER_PRESETS.keys())`. Add `--budget`/`-B` with `choices=["minimal","balanced","high"]`. Add `--force-over-budget` flag. Add `verify-rig` subcommand with `path` positional and `--strict` flag. Add `cmd_verify_rig()` function calling `verify_vrm_rig()`. Add `--what` choice to `list-presets`. Add `--json` flag for machine output. Enhance `cmd_check_env()` to detect Phase 11 modules. |
| 4 | `src/hamr/__init__.py` | **Bump + export** | Change version to `0.5.0`. Add Phase 12 module imports. |
| 5 | `src/hamr/rigs/verify.py` | **Add function** | Add `verify_vrm_rig(path: str) -> dict` — pure-Python VRM binary reader that checks bone presence without Blender. |
| 6 | `src/hamr/core/presets.py` | **Add function** | Add `deep_merge_preset(preset_data: dict, spec_dict: dict) -> dict`. Deep-merges a `CHARACTER_PRESETS[name]["spec"]` into a user spec dict, with user values taking precedence. |
| 7 | `src/hamr/core/__init__.py` | **Add export** | Export `prepare_integration_config` from `pipeline_integrate`. |

### 5.2 New Files

| # | File | Description |
|---|------|-------------|
| 1 | `src/hamr/core/pipeline_integrate.py` | Integration helpers: `prepare_integration_config()` assembles full config dict for Blender; `classify_all_meshes_for_fp()` pure-Python FP annotation; `validate_rig_pure()` pure-Python bone verification. No `bpy` imports. |
| 2 | `tests/test_integration_12.py` | T1 pure-Python + T2 mock integration tests. Tests all Phase 12 call sites without Blender. |
| 3 | `tests/test_e2e_blender.py` | T3 full Blender E2E tests. Marked `@pytest.mark.blender`. Skipped on CI. |
| 4 | `specs/test_integration.yaml` | Minimal E2E test spec. |
| 5 | `specs/test_over_budget.yaml` | Intentionally over-budget spec for testing perf gate. |
| 6 | `specs/anime_girl_default.yaml` | Full preset spec for E2E. |
| 7 | `src/hamr/materials/__init__.py` | New package for material system (Phase 12 G3). |
| 8 | `src/hamr/materials/forge.py` | `MaterialForge` class (Phase 12 G3). |
| 9 | `src/hamr/face/expressions.py` | `ExpressionDiscovery` class (Phase 12 G4). |
| 10 | `src/hamr/rigs/colliders.py` | `CollisionForge` class (Phase 12 G5). |

### 5.3 Change Matrix — What Every Modified File Touches

#### `build_avatar.py` — Stage-by-Stage Changes

```
┌─────────────────────────────────────────────────────────────────────┐
│  build_avatar.py MODIFICATION MAP                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  parse_args()     ←  ADD: --preset, --budget, --perf-check args    │
│                                                                     │
│  main()           ←  RESTRUCTURE: 5 steps → 14 numbered stages     │
│                       Each stage: try/except + timing + logging     │
│                                                                     │
│  NEW: _find_armature(bpy) → str                                     │
│       Finds armature name, used by all integration functions        │
│                                                                     │
│  NEW: _find_body_mesh(bpy) → str                                    │
│       Finds body mesh name, used by clothing & weight paint        │
│                                                                     │
│  NEW: _integrate_stub_bones(bpy, armature_name)                     │
│       → hamr.rigs.stub_bones.create_missing_bones()                 │
│       → Returns: StubBoneResult (created_bones, stub_map)          │
│       → Imports: from hamr.rigs.stub_bones import (               │
│                    create_missing_bones, get_stub_bone_map)         │
│                                                                     │
│  NEW: _integrate_hair_mesh(bpy, spec_data, forge_config,           │
│                            armature_name)                           │
│       → hamr.hair.mesh.HairMeshGenerator().generate()              │
│       → Returns: HairMeshResult | None                              │
│       → Imports: from hamr.hair.mesh import HairMeshGenerator      │
│                                                                     │
│  NEW: _integrate_clothing_meshes(bpy, spec_data, forge_config,      │
│                                   armature_name)                    │
│       → hamr.clothing.mesh.ClothingMeshGenerator().generate()      │
│       → Returns: list[ClothingMeshResult]                           │
│       → Imports: from hamr.clothing.mesh import                   │
│                    ClothingMeshGenerator                            │
│                                                                     │
│  NEW: _integrate_weight_paint(bpy, armature_name, hair_result,     │
│                                clothing_results)                    │
│       → WeightPaintEngine.paint_smooth()                            │
│       → WeightPaintEngine.transfer_weights()                        │
│       → WeightPaintEngine.normalize_weights()                       │
│       → WeightPaintEngine.get_quality_score()                       │
│       → Returns: None (logs quality score)                          │
│       → Imports: from hamr.rigs.weights import WeightPaintEngine  │
│                                                                     │
│  NEW: _integrate_spring_bones(bpy, armature_name, spec_data,       │
│                                forge_config, hair_result,            │
│                                clothing_results)                    │
│       → configure_hair_spring()                                     │
│       → configure_breast_spring()                                   │
│       → configure_clothing_spring()                                 │
│       → apply_spring_bones()                                        │
│       → Returns: None (writes to VRM extension)                    │
│       → Imports: from hamr.rigs.spring_bones import (             │
│                    configure_hair_spring, configure_breast_spring,  │
│                    configure_clothing_spring, apply_spring_bones,    │
│                    SpringBoneCollider, DEFAULT_COLLIDERS)           │
│                                                                     │
│  NEW: _integrate_first_person(bpy, armature_name,                  │
│                                 hair_result, clothing_results)       │
│       → configure_first_person(armature_name, mesh_names)           │
│       → Returns: None (writes mesh annotations to VRM ext)         │
│       → Imports: from hamr.export.first_person import (           │
│                    configure_first_person)                           │
│                                                                     │
│  NEW: _verify_rig_post_export(bpy, armature_name)                  │
│       → hamr.rigs.verify.RigVerifier.verify()                       │
│       → Returns: verification dict (logged, not fatal)             │
│       → Imports: from hamr.rigs.verify import RigVerifier          │
│                                                                     │
│  NEW: _dict_to_clothing_spec(cloth_dict, index)                    │
│       → Converts dict→ClothingSpec for ClothingMeshGenerator       │
│       → Returns: ClothingSpec compatible object                     │
│                                                                     │
│  MOD: _apply_vrm_humanoid(bpy, spec, stub_result=None)             │
│       → If stub_result provided, merge stub_map into bone_map     │
│       → Imports: from hamr.rigs.stub_bones import get_stub_bone_map│
│                                                                     │
│  MOD: _apply_vrm_expressions(bpy, spec)                             │
│       → Scope for ExpressionDiscovery integration (Phase 12 G4)   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### `pipeline.py` — Modification Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  pipeline.py MODIFICATION MAP                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  build()           ←  ADD PARAMETERS:                               │
│                       preset: str | None = None                     │
│                       budget: str = "balanced"                       │
│                       force_over_budget: bool = False               │
│                                                                     │
│                    ADD AFTER validate_spec():                        │
│                       perf_budget = PerformanceBudget(tier=budget)  │
│                       perf_report = check_budget(char, perf_budget) │
│                       if not perf_report.within_budget and           │
│                          not force_over_budget:                       │
│                           return PipelineResult(errors=[...])        │
│                                                                     │
│                    ADD AFTER preset check:                           │
│                       if preset:                                     │
│                           preset_data = CHARACTER_PRESETS[preset]   │
│                           spec_dict = deep_merge_preset(            │
│                               preset_data["spec"], spec_dict)        │
│                                                                     │
│                    ADD TO run_blender_script args:                   │
│                       --preset <name> if specified                    │
│                       --budget <tier>                                │
│                                                                     │
│  check_environment()  ←  ADD Phase 11 module detection:            │
│                       Check importability of Phase 11 modules       │
│                       Report which stages will be available         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### `cli.py` — Modification Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  cli.py MODIFICATION MAP                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  build_parser      ←  ADD ARGUMENTS:                                │
│                       --preset / -p  (choices from CHARACTER_PRESETS)│
│                       --budget / -B  (choices: minimal/balanced/high)│
│                       --force-over-budget (store_true)               │
│                                                                     │
│  cmd_build()       ←  PASS new args to pipeline.build():          │
│                       preset=args.preset,                            │
│                       budget=args.budget,                            │
│                       force_over_budget=args.force_over_budget       │
│                                                                     │
│  NEW: verify_rig_parser (subparser)                                │
│                       positional: path                               │
│                       --strict (store_true)                          │
│                                                                     │
│  NEW: cmd_verify_rig(args)                                          │
│                       → verify_vrm_rig(args.path)                   │
│                       → JSON or human output                         │
│                                                                     │
│  list-presets      ←  ADD: --what choice (all/character/body)      │
│                       Also show CHARACTER_PRESETS when what=character│
│                       or all                                        │
│                                                                     │
│  cmd_check_env()   ←  ADD: Phase 11 module detection              │
│                       Check: stub_bones, hair.mesh, clothing.mesh,  │
│                             weights, spring_bones, verify,          │
│                             first_person, perf, presets              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Test Strategy for Integration

### 6.1 Three-Tier Test Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER T1: Pure-Python Unit Tests (No Blender)                       │
│  Ran by: pytest tests/ -m "not blender"                             │
│  CI: Always runs                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  test_integration_12.py::TestStubBonesPure                          │
│    ├── test_detect_missing_bones_mblab()                            │
│    ├── test_compute_stub_position()                                 │
│    └── test_get_stub_bone_map()                                     │
│                                                                     │
│  test_integration_12.py::TestHairMeshPure                           │
│    ├── test_generate_guide_curves()                                  │
│    └── test_compute_strand_count()                                  │
│                                                                     │
│  test_integration_12.py::TestClothingMeshPure                       │
│    ├── test_resolve_clothing_pattern()                               │
│    └── test_classify_material_type()                                 │
│                                                                     │
│  test_integration_12.py::TestPerfBudget                             │
│    ├── test_check_budget_within()                                    │
│    └── test_check_budget_over()                                      │
│                                                                     │
│  test_integration_12.py::TestFirstPersonPure                        │
│    ├── test_classify_mesh_for_fp()                                   │
│    └── test_configure_first_person_pure()                            │
│                                                                     │
│  test_integration_12.py::TestSpringBonesPure                       │
│    ├── test_configure_hair_spring()                                  │
│    └── test_configure_clothing_spring()                              │
│                                                                     │
│  test_integration_12.py::TestWeightPaintPure                        │
│    ├── test_compute_quality_score()                                  │
│    └── test_classify_deformation_quality()                           │
│                                                                     │
│  test_integration_12.py::TestPresetMerge                            │
│    ├── test_deep_merge_preset_override()                              │
│    └── test_deep_merge_preset_defaults()                              │
│                                                                     │
│  test_integration_12.py::TestPipelineIntegrate                      │
│    ├── test_prepare_integration_config()                              │
│    ├── test_classify_all_meshes_for_fp()                             │
│    └── test_validate_rig_pure()                                       │
│                                                                     │
│  test_integration_12.py::TestVerifyVrmRig                           │
│    └── test_verify_vrm_rig_reads_glb()                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  TIER T2: Integration Mock Tests (No Blender)                       │
│  Ran by: pytest tests/ -m "not blender"                             │
│  CI: Always runs                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  test_integration_12.py::TestPipelineIntegration                    │
│    ├── test_build_with_preset()     — Preset merge logic           │
│    ├── test_perf_budget_gate()      — Over-budget rejection         │
│    ├── test_forge_resolution()      — All 3 forges resolve          │
│    └── test_pipeline_result_type()   — PipelineResult fields        │
│                                                                     │
│  test_integration_12.py::TestCLIParsing                              │
│    ├── test_build_parser_preset()    — --preset arg parsing         │
│    ├── test_build_parser_budget()    — --budget arg parsing         │
│    ├── test_verify_rig_parser()      — verify-rig subcommand       │
│    └── test_list_presets_what()      — --what arg parsing           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  TIER T3: Full Blender E2E (Pi 5 Only)                               │
│  Ran by: pytest tests/ -m blender --on-pi5                          │
│  CI: SKIPPED (no Blender)                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  test_e2e_blender.py::TestE2EBlender                               │
│    ├── test_build_from_preset_anime_girl()                          │
│    ├── test_build_with_hair_clothing()                              │
│    ├── test_build_over_budget_rejected()                            │
│    ├── test_vrm_has_25_bones()                                      │
│    ├── test_vrm_has_hair_mesh()                                      │
│    ├── test_vrm_has_clothing()                                       │
│    ├── test_vrm_has_spring_bones()                                   │
│    ├── test_vrm_has_first_person()                                   │
│    ├── test_weight_paint_quality()                                   │
│    ├── test_perf_budget_under_45s()                                  │
│    └── test_perf_memory_under_1_5gb()                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Test Execution Commands

```bash
# T1 + T2: Pure Python + Integration Mock (CI-safe)
cd /home/pi/Hamr && python3 -m pytest tests/test_integration_12.py -v -m "not blender"

# T3: Full Blender E2E (Pi 5 only)
cd /home/pi/Hamr && python3 -m pytest tests/test_e2e_blender.py -v -m blender

# All tests (regression check)
cd /home/pi/Hamr && python3 -m pytest tests/ -q --tb=short

# Quick integration sanity
cd /home/pi/Hamr && python3 -m pytest tests/test_integration_12.py -q --tb=short
```

### 6.3 Critical Path Tests

These tests MUST pass before Phase 12 is considered complete:

| # | Test | What It Verifies | Tier |
|---|------|------------------|------|
| 1 | `test_detect_missing_bones_mblab` | Stub bone detection works | T1 |
| 2 | `test_compute_stub_position` | Stub bone placement math | T1 |
| 3 | `test_classify_mesh_for_fp` | First-person mesh classification | T1 |
| 4 | `test_check_budget_within` | Perf budget accepts valid specs | T1 |
| 5 | `test_check_budget_over` | Perf budget rejects over-budget specs | T1 |
| 6 | `test_configure_hair_spring` | Spring bone config generation | T1 |
| 7 | `test_compute_quality_score` | Weight paint scoring | T1 |
| 8 | `test_deep_merge_preset_override` | Preset merge logic | T1 |
| 9 | `test_build_with_preset` | Full preset → pipeline flow | T2 |
| 10 | `test_perf_budget_gate` | Budget gate blocks over-budget | T2 |
| 11 | `test_build_from_preset_anime_girl` | Full E2E: preset → VRM | T3 |
| 12 | `test_vrm_has_25_bones` | E2E: VRM bone completeness | T3 |
| 13 | `test_vrm_has_spring_bones` | E2E: Spring bones in VRM | T3 |

### 6.4 Conftest Marker Setup

```python
# tests/conftest.py (addition)
import pytest

def pytest_collection_modifyitems(config, items):
    skip_blender = pytest.mark.skip(reason="Blender not available on CI")
    for item in items:
        if "blender" in item.keywords:
            item.add_marker(skip_blender)
```

### 6.5 Regression Safety

- All 556 existing tests must continue to pass
- New integration tests must not modify existing test files
- T1/T2 tests run in CI; T3 tests are `@pytest.mark.blender`
- `--tb=short` for quick failure diagnosis

---

## Appendix A: Module Import Map (What build_avatar.py Will Import)

| Import Statement | Used In | Phase |
|------------------|---------|-------|
| `from hamr.rigs.stub_bones import create_missing_bones, get_stub_bone_map` | Stage 3a, Stage 4 | 11 |
| `from hamr.hair.mesh import HairMeshGenerator` | Stage 3b | 11 |
| `from hamr.clothing.mesh import ClothingMeshGenerator` | Stage 3c | 11 |
| `from hamr.rigs.weights import WeightPaintEngine` | Stage 3d | 11 |
| `from hamr.rigs.weights import classify_deformation_quality` | Stage 3d | 11 |
| `from hamr.rigs.spring_bones import (configure_hair_spring, configure_breast_spring, configure_clothing_spring, apply_spring_bones, SpringBoneCollider, DEFAULT_COLLIDERS)` | Stage 3e | 11 |
| `from hamr.export.first_person import configure_first_person` | Stage 3f | 11 |
| `from hamr.rigs.verify import RigVerifier` | Stage 10 | 11 |
| `from hamr.core.perf import check_budget, PerformanceBudget` | `pipeline.py` pre-flight | 11 |
| `from hamr.core.presets import CHARACTER_PRESETS, deep_merge_preset` | `pipeline.py` + `cli.py` | 11 |
| `from hamr.core.models import HairPhysicsSpec` | Stage 3e | 11 |

## Appendix B: Data Shapes — Key Result Types

```
StubBoneResult:
    created_bones: dict[str, tuple]  # bone_name → (head_pos, tail_pos)
    stub_map: dict[str, str]         # VRM_bone_name → blender_bone_name
                                      # e.g. {"leftEye": "leftEye", "rightEye": "rightEye", "jaw": "jaw"}

HairMeshResult:
    object_name: str                  # Blender object name
    vertex_count: int
    triangle_count: int
    bone_chain: list[str]             # Bone names for spring bones

ClothingMeshResult:
    mesh_name: str
    triangle_count: int
    weight_transferred: bool           # Whether body→clothing transfer succeeded

WeightPaintReport:
    score: float                      # 0.0–1.0
    classification: str               # "excellent"/"good"/"fair"/"poor"

PipelineResult:
    success: bool
    spec_path: Path
    output_path: Path | None
    elapsed: float
    blender_result: BlenderResult | None
    errors: list[str]
    warnings: list[str]
```

## Appendix C: Pipeline Stage Error Handling Strategy

| Stage | Failure Mode | Action | Exit Code |
|-------|-------------|--------|-----------|
| 0 | VRM add-on unavailable | Log warning, continue | — |
| 1 | Scene clear fails | Hard fail | 4 |
| 2 | Base mesh import fails | Hard fail | 3 |
| 3 | Spec apply fails | Hard fail | 4 |
| 3a | Stub bones fail | Log warning, continue without stubs | — |
| 3b | Hair mesh fails | Log warning, continue without hair | — |
| 3c | Clothing mesh fails | Log warning, skip individual items | — |
| 3d | Weight paint fails | Log warning, continue with raw weights | — |
| 3e | Spring bones fail | Log warning, continue without springs | — |
| 3f | First-person fails | Log warning, continue without FP annotations | — |
| 4 | VRM bone mapping fails | Hard fail | 4 |
| 5 | VRM metadata fails | Log warning, continue | — |
| 6 | VRM expressions fail | Log warning, continue without expressions | — |
| 7 | VRM lookAt fails | Log warning, continue without lookAt | — |
| 8 | VRM export fails | Hard fail | 5 |
| 9 | Post-export validation fails | Log warning | — |
| 10 | Rig verification fails | Log warning, non-fatal | — |
| Pre-flight | Spec parse fails | Hard fail | 2 |
| Pre-flight | Validation fails | Hard fail | 2 |
| Pre-flight | Over budget (no --force) | Hard fail | 1 |

**Philosophy:** The trunk (core pipeline) must stand. Individual branches (hair, clothing, springs) may break, and the tree continues. But the roots (spec, validation, export) must hold or the tree falls.

---

*Védis Eikleið has drawn the map. The roots know where they drink. The branches know where they reach. Every data drop flows through Yggdrasil's trunk.*