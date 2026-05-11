# DATA_FLOW_17.md — Hamr v0.8.0 E2E VRM Build Pipeline Data Flow Map

**Author:** Védis Eikleið, CARTOGRAPHER of Mythic Engineering
**Date:** 2026-05-11
**.Scope:** Complete data flow from spec.yaml to VRM export, 22 stages
**Context:** Architecture doc ARCHITECTURE_17.md identified 3 critical blockers

---

## 0. EXECUTIVE SUMMARY

The Hamr pipeline has a **Two-Phase boundary** — Phase A runs in pure Python (parent process), Phase B runs inside Blender (`--background --python`). The ONLY communication channel between them is a **JSON file on disk** (`.hamr_<name>_spec.json`).

This map traces every data transformation across all 22 stages, identifies every conflict between the two parallel VRM setup codepaths (`build_avatar.py` vs `vrm.py`), and pinpoints the exact line numbers of the three critical blockers flagged by the Architect.

---

## 1. TWO-PHASE BOUNDARY

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE A — Python Parent Process (No bpy)                      │
│                                                                 │
│  spec.yaml → Spec → CharacterSpec → validate → forge resolve   │
│       → JSON file on disk (.hamr_<name>_spec.json)             │
│                                                                 │
│  Runs: hamr/cli.py → cmd_build()                               │
│        hamr/core/builder.py → build()                          │
│        hamr/blender_bridge/runner.py → run_blender_script()    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                  JSON file on disk
                  (sole communication channel)
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│  PHASE B — Blender Subprocess (bpy required)                   │
│                                                                 │
│  blender --background --python build_avatar.py --               │
│      --spec <json_path> --output <vrm_path>                     │
│                                                                 │
│  22 stages: JSON parse → scene build → VRM export → validate   │
│                                                                 │
│  Runs: hamr/scripts/build_avatar.py → main()                   │
│        Imports: hamr.rigs.stub_bones, hamr.hair.mesh,          │
│        hamr.clothing.mesh, hamr.rigs.spring_bones,             │
│        hamr.export.first_person, hamr.rigs.verify               │
│  DOES NOT IMPORT: hamr/export/vrm.py (reimplements everything) │
└─────────────────────────────────────────────────────────────────┘
```

**Key implication:** `hamr/export/vrm.py` is a modular, well-tested module with correct VRM addon property access (`armature.vrm_addon_extension`), but `build_avatar.py` never imports it. Instead, `build_avatar.py` reimplements all VRM setup inline with bugs (`armature.data.vrm_addon_extension`). Bug fixes to `vrm.py` do NOT propagate to the E2E pipeline.

---

## 2. STAGE-BY-STAGE DATA FLOW

### Stage 1: CLI Entry Point
- **Module:** `hamr/cli.py`
- **Input:** `spec.yaml` path, CLI args
- **Output:** Validated `spec_path`, `output_dir`, `format`, `base_mesh`
- **Runs in:** Phase A (Python)
- **Data flow:** CLI args → resolve_preset → build()

### Stage 2: Spec Parse
- **Module:** `hamr/core/spec.py` → `Spec.from_yaml()`
- **Input:** `spec.yaml` file path
- **Output:** `Spec` object containing `CharacterSpec` dataclass
- **Runs in:** Phase A (Python)
- **Key detail:** `CharacterSpec.from_dict()` performs `data = copy.deepcopy(data)` before mutation (line ~289 of `models.py`). Safe.

### Stage 3: Spec Validation
- **Module:** `hamr/core/validate.py` → `validate_spec()`
- **Input:** `CharacterSpec` object
- **Output:** List of error strings (empty = valid)
- **Runs in:** Phase A (Python)

### Stage 4: Forge Resolution
- **Module:** `hamr/core/builder.py` → `_resolve_forges()`
- **Input:** `CharacterSpec` object
- **Output:** `forge_config` dict with keys `hair`, `face`, `clothing`
- **Runs in:** Phase A (Python)
- **Data flow:**
  - `character.hair` → `hamr/hair/__init__.py` → `resolve_hair()` → `HairBuildResult.to_dict()`
  - `character.face` → `hamr/face/__init__.py` → `resolve_face()` → `FaceBuildResult.to_dict()`
  - `character.clothing` → `hamr/clothing/__init__.py` → `resolve_clothing()` → list of `ClothingBuildResult.to_dict()`
- **⚠ GRACEFUL DEGRADATION:** Each forge is wrapped in `try/except`; failures return `None`/`[]` silently

### Stage 5: Performance Budget Check (Phase A)
- **Module:** `hamr/core/perf.py` → `check_budget()`
- **Input:** `CharacterSpec` dict, `DEFAULT_PI5_BUDGET`
- **Output:** `PerformanceReport` with `within_budget` bool
- **Runs in:** Phase A (Python) — also re-run inside Blender (Step pre-flight)

### Stage 6: JSON Serialization
- **Module:** `hamr/core/builder.py` → `build()`
- **Input:** `Spec.to_dict()` result + `forge_config` dict
- **Output:** `.hamr_<name>_spec.json` file on disk
- **Runs in:** Phase A (Python)
- **Data flow:** `spec_dict = spec.to_dict()` → `spec_dict["forge_config"] = forge_config` → `json.dumps(spec_dict)` → written to temp file
- **Line:** `builder.py` lines 152-157

### Stage 7: Blender Subprocess Launch
- **Module:** `hamr/blender_bridge/runner.py` → `run_blender_script()`
- **Input:** `build_script` path, `script_args`, `timeout=600`, `env`
- **Output:** `BlenderResult` (exit_code, stdout, stderr, elapsed)
- **Runs in:** Phase A (Python) — launches Phase B
- **Data flow:**
  - Command: `blender --background --python-use-system-env --python build_avatar.py -- --spec <json_path> --output <vrm_path>`
  - Environment: `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true`
  - Timeout: 600 seconds default
- **Lines:** `runner.py` lines 56-140

### ═══════════════════════════════════════
### PHASE B BEGINS — All subsequent stages run inside Blender
### ═══════════════════════════════════════

### Stage 8: Build Script Init + Spec Load
- **Module:** `hamr/scripts/build_avatar.py` → `main()`, `parse_args()`
- **Input:** `--spec <json_path>`, `--output <vrm_path>`, `--base <mesh_path>`
- **Output:** `spec_data` dict, `output_path` Path
- **Runs in:** Phase B (Blender)
- **Data flow:** CLI argv → `parse_args()` → `json.loads(spec_path.read_text())` → `spec_data` dict
- **Lines:** `build_avatar.py` lines 238-274

### Stage 9: Blender-Side Budget Recheck
- **Module:** `hamr/scripts/build_avatar.py` → inline
- **Input:** `spec_data` dict
- **Output:** Warning or abort
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 277-290
- **Note:** Wrapped in `try/except`; failure is silently skipped

### Stage 10: VRM Addon Enable
- **Module:** `hamr/scripts/build_avatar.py` → inline
- **Input:** None (uses `bpy.ops`)
- **Output:** VRM addon enabled in Blender
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 293-302
- **Data flow:** `addon_utils.enable("io_scene_vrm")` → `bpy.ops.wm.save_userpref()`

### Stage 11: Clear Scene
- **Module:** `hamr/scripts/build_avatar.py` → `_clear_scene(bpy)`
- **Input:** Current Blender scene
- **Output:** Empty scene (all objects, materials, meshes removed)
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 463-485

### Stage 12: Import/Generate Base Mesh
- **Module:** `hamr/scripts/build_avatar.py` → `_import_base()` or `_generate_mblab_base()`
- **Input:** `--base` path OR MB-Lab addon
- **Output:** MESH object + ARMATURE object in Blender scene
- **Runs in:** Phase B (Blender)
- **⛔ BLOCKER #3 (FP-3):** Line 519 — `_generate_mblab_base()` accepts `CANCELLED` as valid result from `bpy.ops.mbast.init_character()`. MB-Lab may silently fail in headless mode, producing no mesh, and the pipeline continues.
- **Data flow (MB-Lab):**
  - `bpy.ops.mbast.init_character()` → creates `f_af01` mesh + armature
  - `bpy.ops.mbast.auto_modelling()` → applies body morphs
  - `bpy.ops.mbast.finalize_character()` → generates shape keys with `Expressions_*` prefix

### Stage 13: Apply Spec (Colors, Height, Forges)
- **Module:** `hamr/scripts/build_avatar.py` → `_apply_spec(bpy, spec_data, forge_config)`
- **Input:** `spec_data` dict, `forge_config` dict
- **Output:** Modified materials, armature scale
- **Runs in:** Phase B (Blender)
- **Sub-stages:**
  - `_apply_colors(bpy, spec_data)` — HSV tinting of skin/eye/hair materials
  - `_apply_height(bpy, spec_data)` — `armature.scale[2] *= (target_height / 165.0)`
  - `_apply_face_from_forge(bpy, forge_config)` — shape key values
  - `_apply_hair_from_forge(bpy, forge_config)` — shape key values
  - `_apply_clothing_from_forge(bpy, forge_config)` — material tinting
- **⚠ HSV BUG (FP-4):** Line 648 — `_shift_image_hsv()` uses `h = (h + h_target * blend) / (1 + blend)` which is a weighted average, NOT circular interpolation. Colors near hue boundary (H≈0 or H≈1) interpolate through cyan instead of wrapping through red.

### Stage 14: Stub Bone Creation
- **Module:** `hamr/rigs/stub_bones.py` → `create_missing_bones()`
- **Input:** `armature_name` string, `base_type="mblab"`
- **Output:** `StubBoneResult` with `created_bones` dict (VRM name → Blender name)
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 346-351 → `stub_bones.py` lines 194-328
- **Data flow:** VRM 25 required bones → `detect_missing_bones()` → creates jaw, leftEye, rightEye → tags with `_hamr_stub=True`

### Stage 15: Hair Mesh Generation
- **Module:** `hamr/hair/mesh.py` → `HairMeshGenerator.generate()`
- **Input:** `style_name`, `head_center`, `head_radius`, `color_config`
- **Output:** `HairBuildResult` with `object_name`, `vertex_count`, `triangle_count`, optional `bone_chain`
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 353-358 → `_integrate_hair_mesh()` lines 1110-1167
- **Data flow:** `spec_data["hair"]` or `forge_config["hair"]` → `HairMeshGenerator` → Bezier curves → mesh → material → parent to head bone

### Stage 16: Clothing Mesh Generation
- **Module:** `hamr/clothing/mesh.py` → `ClothingMeshGenerator.generate()`
- **Input:** `ClothingSpec`, `body_mesh_name`, `armature_name`
- **Output:** list of `ClothingBuildResult` with `mesh_name`, `triangle_count`
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 361-367 → `_integrate_clothing_meshes()` lines 1170-1214
- **Data flow:** `spec_data["clothing"]` or `forge_config["clothing"]` → ClothingSpec → pattern selection → region duplicate → shrinkwrap → material

### Stage 17: Weight Painting
- **Module:** `hamr/rigs/weights.py` → `WeightPaintEngine`
- **Input:** `armature_name`, `body_mesh_name`, `hair_result`, `clothing_results`
- **Output:** Smoothed/normalized weights on body, transferred weights on hair/clothing
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 369-373 → `_integrate_weight_paint()` lines 1217-1255
- **Data flow:** Body mesh weights → `paint_smooth()` → `normalize_weights()` → `transfer_weights()` to clothing meshes

### Stage 18: Spring Bone Configuration
- **Module:** `hamr/rigs/spring_bones.py` → `apply_spring_bones()`
- **Input:** `armature_name`, `spring_groups` list, `colliders` list
- **Output:** VRM spring bone groups and collider spheres configured on armature
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 375-382 → `_integrate_spring_bones()` lines 1258-1337
- **Data flow:**
  - `configure_hair_spring(spec.hair.physics)` → `SpringBoneGroup`
  - `configure_breast_spring(spec.body)` → `SpringBoneGroup`
  - `configure_clothing_spring(mesh_name, type)` → `SpringBoneGroup`
  - `apply_spring_bones()` → configures `armature.vrm_addon_extension.vrm1.spring_bone`
- **⚠ Uses `armature.vrm_addon_extension` (CORRECT path)** — `spring_bones.py` line 424

### Stage 19: First-Person Annotations
- **Module:** `hamr/export/first_person.py` → `configure_first_person()`
- **Input:** `armature_name`, `mesh_names` list
- **Output:** `FirstPersonConfig` applied to VRM extension
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 384-388 → `_integrate_first_person()` lines 1340-1360
- **Data flow:** All mesh names → `classify_mesh_for_fp()` → annotations dict → `vrm_ext.vrm1.first_person`
- **⚠ Uses `armature.vrm_addon_extension` (CORRECT path)** — `first_person.py` line 283

### Stage 20: VRM Humanoid Bone Mapping⛔ CRITICAL
- **Module:** `hamr/scripts/build_avatar.py` → `_apply_vrm_humanoid()`
- **Input:** `spec_data` dict, `stub_result` from Stage 14
- **Output:** Humanoid bone mapping set on VRM addon extension
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 844-906

**⛔ BLOCKER #1 (FP-1) — Line 861:**
```python
vrm_ext = armature.data.vrm_addon_extension  # ← WRONG
```
The VRM addon registers `vrm_addon_extension` on the **Object** (not the data block). Using `.data.vrm_addon_extension` will either raise `AttributeError` or access the wrong property. Compare with `vrm.py` line 121 which uses:
```python
vrm_ext = armature.vrm_addon_extension  # ← CORRECT
```

**⛔ BLOCKER #2 (FP-2) — Lines 49-73, MB_LAB_BONE_MAP:**
Three different bone maps exist with conflicting values. The E2E pipeline uses `build_avatar.py`'s map:

| VRM Bone | build_avatar.py (line 49-73) | vrm.py (line 37-75) | stub_bones.py (line 105-132) |
|-----------|------------------------------|----------------------|-------------------------------|
| spine | **spine01** | spine | spine |
| chest | **spine02** | spine_01 | spine_01 |
| upperChest | **spine03** | spine_02 | spine_02 |
| leftLowerLeg | **calf_L** | shin_L | shin_L |
| leftUpperArm | **upperarm_L** | upper_arm_L | upper_arm_L |
| leftLowerArm | **lowerarm_L** | forearm_L | forearm_L |
| leftToes | **toes_L** | toe_L | toe_L |
| leftEye | (not listed) | leftEye | eye_L |
| rightEye | (not listed) | rightEye | eye_R |

MB-Lab 1.7.8 uses `spine`, `spine_01`, `spine_02` (with underscores). The build_avatar.py versions without underscores (`spine01`, `spine02`, `spine03`) and `calf_L` are likely WRONG.

**Data flow:**
1. `spec_data.get("base_type", "mblab")` → selects `MB_LAB_BONE_MAP`
2. `stub_result.created_bones` merged into bone map
3. `human_bones.initial_automatic_bone_assignment = False` (D-008 fix, line 865)
4. `human_bones.filter_by_human_bone_hierarchy = False` (D-009 fix, line 867)
5. `human_bones.human_bone_name_to_human_bone()` → dict API (D-018 fix, line 889)
6. Each VRM bone name → `bone_prop.node.bone_name = blender_name`

### Stage 21: VRM Metadata⛔
- **Module:** `hamr/scripts/build_avatar.py` → `_apply_vrm_metadata()`
- **Input:** `spec_data` dict
- **Output:** VRM 1.0 metadata set on armature extension
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 909-930

**⛔ Same bug as Blocker #1 — Lines 912-913:**
```python
if obj.type == "ARMATURE" and hasattr(obj.data, "vrm_addon_extension"):
    vrm_ext = obj.data.vrm_addon_extension  # ← WRONG (should be obj.vrm_addon_extension)
```

**Data flow:** `spec_data["name"]` → `meta.name`, `meta.title` → `spec_data["version"]` → `meta.version` → `meta.authors[0].name` → `spec_data["author"]` or "Hamr Forge"

### Stage 22: VRM Expressions⛔
- **Module:** `hamr/scripts/build_avatar.py` → `_apply_vrm_expressions()`
- **Input:** `spec_data` dict
- **Output:** VRM expression presets configured on armature extension
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 933-982

**⛔ Same bug as Blocker #1 — Lines 936-937:**
```python
if obj.type == "ARMATURE" and hasattr(obj.data, "vrm_addon_extension"):
    vrm_ext = obj.data.vrm_addon_extension  # ← WRONG
```

**Data flow:**
1. Discover all shape keys across all mesh objects → `shape_key_index` dict
2. Select expression map: `MB_LAB_EXPRESSION_MAP` (default) or `TURBOSQUID_EXPRESSION_MAP`
3. `initial_automatic_expression_assignment = False` (line 959, D-011 related)
4. For each expression preset → each binding → `bind.node.mesh_object_name` + `bind.index = sk_name` (D-013: shape key NAME string)

### Stage 23: VRM LookAt
- **Module:** `hamr/scripts/build_avatar.py` → `_apply_vrm_look_at()`
- **Input:** `spec_data` dict
- **Output:** VRM lookAt configured (bone mode or expression mode)
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 985-1033

**⛔ Same bug as Blocker #1 — Lines 988-989:**
```python
if obj.type == "ARMATURE" and hasattr(obj.data, "vrm_addon_extension"):
    vrm_ext = obj.data.vrm_addon_extension  # ← WRONG
```

**Data flow:**
1. Check for eye bones in armature → `has_eye_bones` bool
2. If eye bones exist → `look_at.type = "bone"`, compute offset from eye positions
3. If no eye bones → `look_at.type = "expression"` (expressionOnly fallback)
4. Set lookAt range degrees from `spec_data["look_at"]`

### Stage 24: VRM Export
- **Module:** `hamr/scripts/build_avatar.py` → inline
- **Input:** `armature_name`, `output_path`
- **Output:** `.vrm` file on disk
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 407-430
- **Data flow:** `bpy.ops.export_scene.vrm("EXEC_DEFAULT", filepath=str(output_path), armature_object_name=armature_name, ignore_warning=True)` — D-016 fix applied
- **Environment:** `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true` set at line 407

### Stage 25: Post-Export Validation
- **Module:** `hamr/scripts/build_avatar.py` → `_validate_vrm()`
- **Input:** `output_path` string
- **Output:** Pass/fail (warning only)
- **Runs in:** Phase B (Blender)
- **Lines:** `build_avatar.py` lines 1040-1058, called at 433-436
- **Data flow:** Read file → check size > 1024 bytes → check glTF magic number `0x46546C67`

### Stage 26: Rig Verification
- **Module:** `hamr/rigs/verify.py` → `RigVerifier.verify()`
- **Input:** Output `.vrm` file path
- **Output:** Verification report dict
- **Runs in:** Phase B (Blender) — optional, ImportError caught
- **Lines:** `build_avatar.py` lines 439-453

---

## 3. COMPLETE DATA FLOW DIAGRAM

```
spec.yaml
  │
  ▼
┌─────────────────────┐
│  Stage 1: CLI       │  hamr/cli.py → cmd_build()
│  Stage 2: Parse     │  hamr/core/spec.py → Spec.from_yaml()
│  Stage 3: Validate   │  hamr/core/validate.py → validate_spec()
│  Stage 4: Forge      │  hamr/core/builder.py → _resolve_forges()
│  Stage 5: Budget     │  hamr/core/perf.py → check_budget()
│  Stage 6: Serialize  │  builder.py → JSON file on disk
│  Stage 7: Launch     │  hamr/blender_bridge/runner.py → subprocess
└──────────┬──────────┘
           │  .hamr_<name>_spec.json (SOLE CHANNEL)
           ▼
┌──────────────────────────────────────────────────────────────┐
│  Blender Subprocess — build_avatar.py → main()               │
│                                                              │
│  Stage 8:  Parse JSON spec                                   │
│  Stage 9:  Budget recheck                                    │
│  Stage 10: Enable VRM addon                                  │
│  Stage 11: Clear scene                                       │
│  Stage 12: Base mesh (MB-Lab or import)  ⛔ BLOCKER #3      │
│  Stage 13: Apply spec (colors, height, forges)               │
│           ├── colors (HSV tinting)     ⚠ FP-4               │
│           ├── height (armature scale)                        │
│           ├── face forge (shape keys)                        │
│           ├── hair forge (shape keys)                        │
│           └── clothing forge (material tinting)             │
│  Stage 14: Stub bones (jaw, eyes)                            │
│  Stage 15: Hair mesh                                         │
│  Stage 16: Clothing meshes                                   │
│  Stage 17: Weight painting                                   │
│  Stage 18: Spring bones                                      │
│  Stage 19: First-person annotations                          │
│  Stage 20: VRM humanoid  ⛔ BLOCKER #1 + #2                 │
│  Stage 21: VRM metadata  ⛔ BLOCKER #1                      │
│  Stage 22: VRM expressions ⛔ BLOCKER #1                      │
│  Stage 23: VRM lookAt    ⛔ BLOCKER #1                       │
│  Stage 24: VRM export                                         │
│  Stage 25: Validate VRM file                                 │
│  Stage 26: Rig verification                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. CONFLICT POINT MAP: build_avatar.py vs vrm.py

These two modules implement the SAME functionality independently. The E2E pipeline uses `build_avatar.py` exclusively. Fixes to `vrm.py` do NOT propagate.

### Conflict C-1: VRM Extension Property Access

| Aspect | build_avatar.py | vrm.py |
|--------|-----------------|--------|
| **Property access** | `armature.data.vrm_addon_extension` | `armature.vrm_addon_extension` |
| **Lines** | 861, 912-913, 936-937, 988-989 | 121, 174, 207, 250, 294 |
| **Verdict** | ❌ WRONG — accesses data block | ✅ CORRECT — accesses Object |
| **Impact** | Will crash or silently fail at Stages 20-23 | Would work if called |

### Conflict C-2: Bone Name Mapping

| VRM Bone | build_avatar.py | vrm.py | stub_bones.py |
|-----------|-----------------|--------|---------------|
| spine | spine01 ❌ | spine ✅ | spine ✅ |
| chest | spine02 ❌ | spine_01 ✅ | spine_01 ✅ |
| upperChest | spine03 ❌ | spine_02 ✅ | spine_02 ✅ |
| leftLowerLeg | calf_L ❌ | shin_L ✅ | shin_L ✅ |
| leftUpperArm | upperarm_L ❌ | upper_arm_L ✅ | upper_arm_L ✅ |
| leftLowerArm | lowerarm_L ❌ | forearm_L ✅ | forearm_L ✅ |
| leftToes | toes_L ❌ | toe_L ✅ | toe_L ✅ |
| leftEye | (not mapped) | leftEye | eye_L |
| rightEye | (not mapped) | rightEye | eye_R |
| jaw | jaw | jaw | jaw |
| hips | pelvis | pelvis | pelvis |
| neck | neck | neck | neck |
| head | head | head | head |

**vrm.py and stub_bones.py agree** — they use MB-Lab's actual naming convention (underscored). `build_avatar.py` uses inconsistent names that are likely from an outdated MB-Lab version or manual error.

### Conflict C-3: Expression Binding

| Aspect | build_avatar.py | vrm.py | expressions.py |
|--------|-----------------|--------|-----------------|
| **Source** | Hardcoded `MB_LAB_EXPRESSION_MAP` | Takes `expressions` param | Dynamic `SHAPE_KEY_ALIASES` + pattern matching |
| **Key names** | `Expressions_mouthSmile_max` etc. | User-provided | Runtime discovery |
| **Binding type** | `bind.index = sk_name` (string) | `bind.index = str(morph.get("name", ""))` | N/A (pure Python) |
| **Used in E2E** | ✅ Yes | ❌ No | ❌ No |

### Conflict C-4: LookAt Configuration

| Aspect | build_avatar.py | vrm.py |
|--------|-----------------|--------|
| **Eye bone detection** | Checks 8 bone name variants | Hardcodes `left_eye_bone`/`right_eye_bone` params |
| **Fallback** | Falls back to `expression` mode | No fallback — bone mode only |
| **Offset** | Computed from eye bone positions | Hardcoded `(0.0, 0.06, 0.0)` |
| **Range config** | Reads from `spec["look_at"]` | No range configuration |

### Conflict C-5: Metadata Setting

| Aspect | build_avatar.py | vrm.py |
|--------|-----------------|--------|
| **Source** | `spec_data` dict keys | Function parameters |
| **License** | Hardcoded `CC_BY_4_0` | Configurable (default `CC-BY-4.0`) |
| **Property access** | `obj.data.vrm_addon_extension` ❌ | `armature.vrm_addon_extension` ✅ |

### Conflict C-6: Export Approach

| Aspect | build_avatar.py | vrm.py |
|--------|-----------------|--------|
| **Export call** | Inline `bpy.ops.export_scene.vrm()` | `export_vrm()` function |
| **allow_non_humanoid_rig** | Not set (line 865/867 area) | Set `vrm_ext.vrm1.allow_non_humanoid_rig = True` |
| **Error handling** | Checks `"FINISHED" in result` | Returns bool |

---

## 5. CRITICAL BLOCKER LINE NUMBERS

### ⛔ BLOCKER #1: VRM Extension Property Access Bug
**Impact:** FATAL — VRM setup crashes at Stages 20-23
**Probability:** 95%

| Line | Code | Correct |
|------|------|---------|
| **build_avatar.py:861** | `vrm_ext = armature.data.vrm_addon_extension` | `armature.vrm_addon_extension` |
| **build_avatar.py:912** | `hasattr(obj.data, "vrm_addon_extension")` | `hasattr(obj, "vrm_addon_extension")` |
| **build_avatar.py:913** | `vrm_ext = obj.data.vrm_addon_extension` | `vrm_ext = obj.vrm_addon_extension` |
| **build_avatar.py:936** | `hasattr(obj.data, "vrm_addon_extension")` | `hasattr(obj, "vrm_addon_extension")` |
| **build_avatar.py:937** | `vrm_ext = obj.data.vrm_addon_extension` | `vrm_ext = obj.vrm_addon_extension` |
| **build_avatar.py:988** | `hasattr(obj.data, "vrm_addon_extension")` | `hasattr(obj, "vrm_addon_extension")` |
| **build_avatar.py:989** | `vrm_ext = obj.data.vrm_addon_extension` | `vrm_ext = obj.vrm_addon_extension` |

**Correct reference in vrm.py:**
- `vrm.py:121` — `vrm_ext = armature.vrm_addon_extension` ✅
- `vrm.py:174` — `vrm_ext = armature.vrm_addon_extension` ✅
- `vrm.py:207` — `vrm_ext = armature.vrm_addon_extension` ✅
- `vrm.py:250` — `vrm_ext = armature.vrm_addon_extension` ✅
- `vrm.py:294` — `vrm_ext = armature.vrm_addon_extension` ✅

**Correct reference in other modules:**
- `spring_bones.py:424` — `vrm_ext = armature.vrm_addon_extension` ✅
- `first_person.py:283` — `vrm_ext = armature.vrm_addon_extension` ✅

### ⛔ BLOCKER #2: Bone Name Mapping Inconsistency
**Impact:** CRITICAL — Invalid VRM output, wrong bone mapping
**Probability:** 90%

| File | Lines | Conflicting Entries |
|------|-------|---------------------|
| **build_avatar.py** | 49-73 | `spine→spine01`, `chest→spine02`, `upperChest→spine03`, `leftLowerLeg→calf_L`, `leftUpperArm→upperarm_L`, `leftLowerArm→lowerarm_L`, `leftToes→toes_L` |
| **vrm.py** | 37-75 | `spine→spine`, `chest→spine_01`, `upperChest→spine_02`, `leftLowerLeg→shin_L`, `leftUpperArm→upper_arm_L`, `leftLowerArm→forearm_L`, `leftToes→toe_L` |
| **stub_bones.py** | 105-132 | `spine→spine`, `chest→spine_01`, `upperChest→spine_02`, `leftLowerLeg→shin_L`, `leftUpperArm→upper_arm_L`, `leftLowerArm→forearm_L`, `leftToes→toe_L` |

**Executive line in E2E path:** `build_avatar.py:870` — `bone_map = MB_LAB_BONE_MAP` selects the WRONG map.

### ⛔ BLOCKER #3: MB-Lab Headless Mode CANCELED Acceptance
**Impact:** HIGH — May silently fail to generate base mesh
**Probability:** 80%

| Line | Code |
|------|------|
| **build_avatar.py:519** | `if "FINISHED" in result or "CANCELLED" in result:` |

MB-Lab's `init_character()` returns `CANCELLED` in headless mode frequently. The code treats `CANCELLED` as success, then proceeds with potentially zero mesh objects. The only guard is at lines 546-547:
```python
if not mesh_objects:
    raise RuntimeError("MB-Lab failed...")
```
But this only catches the case where NO meshes exist, not the case where a partial/corrupt mesh was created.

---

## 6. BLENDER SUBPROCESS BOUNDARY

### What runs in Python (Phase A)
- Spec parsing, validation, forge resolution
- JSON serialization
- Blender process launch and timeout management
- Output file verification and cleanup
- **Modules:** `hamr/cli.py`, `hamr/core/spec.py`, `hamr/core/models.py`, `hamr/core/validate.py`, `hamr/core/perf.py`, `hamr/core/builder.py`, `hamr/blender_bridge/runner.py`
- **Pure-Python submodules of Phase B modules:** `ExpressionBinder.resolve_expression_bindings()` (expressions.py), `SpringBoneGroup` dataclass (spring_bones.py), `FirstPersonConfig` (first_person.py), `StubBoneResult` and `detect_missing_bones()` (stub_bones.py), `configure_first_person_pure()` (first_person.py)

### What runs inside Blender (Phase B)
- All `bpy` operations (scene manipulation, mesh creation, VRM addon interaction)
- Bone creation, weight painting, VRM extension configuration
- MB-Lab generation, hair/clothing mesh generation
- VRM export
- **Entry point:** `hamr/scripts/build_avatar.py` → `main()`
- **Imports from:** `hamr.rigs.stub_bones`, `hamr.hair.mesh`, `hamr.clothing.mesh`, `hamr.rigs.weights`, `hamr.rigs.spring_bones`, `hamr.export.first_person`, `hamr.rigs.verify`
- **Does NOT import:** `hamr.export.vrm.py` (reimplements all VRM functions inline)

### Data crossing the boundary
- **Input to Phase B:** `.hamr_<name>_spec.json` (contains full CharacterSpec + forge_config)
- **Output from Phase B:** `.vrm` file at `output_path`
- **Return from Phase B:** Exit code (0=success, 1=usage error, 2=spec error, 3=import error, 4=transform error, 5=VRM export error, 6=validation error)
- **No other IPC:** No shared memory, no callbacks, no socket communication

---

## 7. MODULE OWNERSHIP SUMMARY

| Stage | Module (Phase A) | Module (Phase B) | File |
|-------|-------------------|-------------------|------|
| 1-3 | `hamr/cli.py`, `hamr/core/spec.py`, `hamr/core/validate.py` | — | Multiple |
| 4 | `hamr/core/builder.py` → `_resolve_forges()` | — | builder.py:35-82 |
| 5 | `hamr/core/perf.py` | — | perf.py |
| 6 | `hamr/core/builder.py` → `build()` | — | builder.py:152-157 |
| 7 | `hamr/blender_bridge/runner.py` | — | runner.py:56-140 |
| 8-9 | — | `build_avatar.py` → `main()`, `parse_args()` | build_avatar.py:220-290 |
| 10 | — | `build_avatar.py` → inline | build_avatar.py:293-302 |
| 11 | — | `build_avatar.py` → `_clear_scene()` | build_avatar.py:463-485 |
| 12 | — | `build_avatar.py` → `_generate_mblab_base()` / `_import_base()` | build_avatar.py:488-549 |
| 13 | — | `build_avatar.py` → `_apply_spec()` | build_avatar.py:556-569 |
| 14 | — | `hamr/rigs/stub_bones.py` → `create_missing_bones()` | stub_bones.py:194-328 |
| 15 | — | `hamr/hair/mesh.py` → `HairMeshGenerator.generate()` | mesh.py |
| 16 | — | `hamr/clothing/mesh.py` → `ClothingMeshGenerator.generate()` | mesh.py |
| 17 | — | `hamr/rigs/weights.py` → `WeightPaintEngine` | weights.py |
| 18 | — | `hamr/rigs/spring_bones.py` → `apply_spring_bones()` | spring_bones.py:390-479 |
| 19 | — | `hamr/export/first_person.py` → `configure_first_person()` | first_person.py:228-306 |
| 20⛔ | — | `build_avatar.py` → `_apply_vrm_humanoid()` | build_avatar.py:844-906 |
| 21⛔ | — | `build_avatar.py` → `_apply_vrm_metadata()` | build_avatar.py:909-930 |
| 22⛔ | — | `build_avatar.py` → `_apply_vrm_expressions()` | build_avatar.py:933-982 |
| 23⛔ | — | `build_avatar.py` → `_apply_vrm_look_at()` | build_avatar.py:985-1033 |
| 24 | — | `build_avatar.py` → inline `bpy.ops.export_scene.vrm()` | build_avatar.py:407-430 |
| 25 | — | `build_avatar.py` → `_validate_vrm()` | build_avatar.py:1040-1058 |
| 26 | — | `hamr/rigs/verify.py` → `RigVerifier` | verify.py |

---

## 8. UNUSED MODULAR CODEPATH (vrm.py)

`hamr/export/vrm.py` contains correct, modular implementations that are NEVER called during E2E:

| Function | vrm.py line | build_avatar.py equivalent | Divergence |
|----------|-------------|---------------------------|------------|
| `setup_vrm_humanoid()` | 92-154 | `_apply_vrm_humanoid()` at 844 | Property access + bone map |
| `setup_vrm_metadata()` | 157-184 | `_apply_vrm_metadata()` at 909 | Property access + param style |
| `setup_vrm_expressions()` | 187-234 | `_apply_vrm_expressions()` at 933 | Property access + binding style |
| `setup_vrm_lookAt()` | 237-261 | `_apply_vrm_look_at()` at 985 | Param style + fallback |
| `export_vrm()` | 264-312 | inline at 416-430 | `allow_non_humanoid_rig` |

**Recommendation:** Refactor `build_avatar.py` to import and call `vrm.py` functions instead of reimplementing them. This eliminates all 6 conflicts and ensures bug fixes propagate.

---

## 9. RISK ASSESSMENT FOR FIRST E2E RUN

Based on this data flow map, the estimated probability of a clean first E2E build is **15-25%**:

- **Phase A (Python):** 90% success — well-tested, pure Python
- **Phase B (Blender):** 15-25% success — 3 blocking bugs + MB-Lab headless fragility

### Must-Fix Before E2E Attempt
1. ⛔ **Blocker #1:** Change all `obj.data.vrm_addon_extension` → `obj.vrm_addon_extension` in build_avatar.py (lines 861, 912-913, 936-937, 988-989). OR refactor to call `vrm.py` functions.
2. ⛔ **Blocker #2:** Consolidate `MB_LAB_BONE_MAP` into a single canonical source. Verify against actual MB-Lab 1.7.8 bone naming. Apply the correct map in `build_avatar.py`.
3. ⛔ **Blocker #3:** Add explicit mesh-count verification after MB-Lab generate. Do NOT accept `CANCELLED` as success. Add `bpy.context.view_layer.update()` between MB-Lab steps.

### Likely First-Run Issues
4. ⚠ FP-4: HSV hue boundary wrap (build_avatar.py:648)
5. ⚠ FP-8: Expression shape key name mismatch
6. ⚠ FP-5: ARM64 timeout (runner.py:60, default 600s)
7. ⚠ First-person annotation uses correct `armature.vrm_addon_extension` but spring bones also use correct path — these modules work independently

---

*The cartographer maps the flow. The architect identifies the dams. The forge burns regardless.*
— Védis Eikleið, CARTOGRAPHER