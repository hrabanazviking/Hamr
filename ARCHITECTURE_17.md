# ARCHITECTURE_17.md — Hamr v0.8.0 E2E Build Pipeline Analysis

**Author:** Rúnhild Svartdóttir, ARCHITECT of Mythic Engineering  
**Date:** 2026-05-11  
**Scope:** Full E2E build pipeline mapping, dependency analysis, failure point identification  
**Context:** Development branch, v0.8.0, 2,233 tests (2,206 passing, 27 skipped)  
**Status:** Pipeline has NEVER been run E2E — modules tested individually only

---

## 1. PIPELINE ARCHITECTURE

### 1.1 Top-Level Flow

```
spec.yaml
  │
  ├── CLI Entry Point (hamr/cli.py → cmd_build)
  │     │
  │     ├── Preset Resolution (resolve_preset)
  │     ├── Spec Parse (Spec.from_yaml)
  │     ├── Spec Validation (validate_spec)
  │     ├── Performance Budget Check (check_budget)
  │     │
  │     └── BuildPipeline.build() (core/pipeline.py)
  │           │
  │           ├── Forge Resolution (_resolve_forges)
  │           │     ├── Hair Forge (resolve_hair)
  │           │     ├── Face Forge (resolve_face)
  │           │     └── Clothing Forge (resolve_clothing)
  │           │
  │           ├── JSON Serialization (spec_dict + forge_config)
  │           ├── Blender Bridge (run_blender_script)
  │           │     └── blender --background --python build_avatar.py -- ...
  │           │
  │           └── Output Verification + Cleanup
  │
  └── Blender Subprocess (build_avatar.py)
        │
        ├── Step 0: Enable VRM Add-on
        ├── Step 1: Clear Scene
        ├── Step 2: Import/Generate Base Mesh (MB-Lab or file)
        ├── Step 3: Apply Spec (colors, height, forges)
        ├── Step 3a: Create Stub Bones (jaw, leftEye, rightEye)
        ├── Step 3b: Generate Hair Mesh (HairMeshGenerator)
        ├── Step 3c: Generate Clothing Meshes (ClothingMeshGenerator)
        ├── Step 3d: Weight Paint (WeightPaintEngine)
        ├── Step 3e: Configure Spring Bones
        ├── Step 3f: Configure First-Person Annotations
        ├── Step 4: VRM Humanoid Bone Mapping (D-008 explicit)
        ├── Step 5: VRM Metadata
        ├── Step 6: VRM Expressions (D-011, D-013)
        ├── Step 7: VRM LookAt (D-012)
        ├── Step 8: VRM Export (D-016 EXEC_DEFAULT)
        ├── Step 9: Post-Export Validation (glTF header check)
        └── Step 10: Rig Verification
```

### 1.2 Module Dependency Graph

```
hamr/cli.py
  ├── hamr/core/pipeline.py (BuildPipeline)
  │     ├── hamr/core/spec.py (Spec.from_yaml)
  │     ├── hamr/core/validate.py (validate_spec)
  │     ├── hamr/core/perf.py (check_budget)
  │     ├── hamr/core/builder.py (_resolve_forges)
  │     │     ├── hamr/hair/__init__.py (resolve_hair)
  │     │     ├── hamr/face/__init__.py (resolve_face)
  │     │     └── hamr/clothing/__init__.py (resolve_clothing)
  │     └── hamr/blender_bridge/runner.py (run_blender_script)
  │           └── subprocess: blender --background --python build_avatar.py
  │                 ├── hamr/core/perf.py (check_budget — inside Blender)
  │                 ├── hamr/rigs/stub_bones.py (create_missing_bones)
  │                 ├── hamr/hair/mesh.py (HairMeshGenerator)
  │                 ├── hamr/clothing/mesh.py (ClothingMeshGenerator)
  │                 ├── hamr/rigs/weights.py (WeightPaintEngine)
  │                 ├── hamr/rigs/spring_bones.py (apply_spring_bones)
  │                 ├── hamr/export/first_person.py (configure_first_person)
  │                 ├── hamr/export/vrm.py (VRM setup functions)
  │                 └── hamr/rigs/verify.py (RigVerifier)
  ├── hamr/core/presets.py (resolve_preset)
  └── hamr/core/a11y.py (CLI formatting)
```

### 1.3 Two-Phase Architecture

The pipeline has a clear **Two-Phase** boundary:

| Phase | Process |Runs In |Key Concern |
|-------|---------|--------|------------|
| **Phase A** (Outside Blender) | Spec parse, validate, forge resolution, JSON serialize | Python subprocess (parent) | Pure Python, fully tested |
| **Phase B** (Inside Blender) | Scene construction, mesh generation, VRM setup, export | Blender `--background --python` | Requires `bpy`, addons, headless rendering |

The bridge between them is a **JSON file on disk** (`.hamr_<name>_spec.json`), written by Phase A and read by Phase B. This is the ONLY communication channel. There is no shared state, no IPC, no callback.

---

## 2. DEPENDENCY MAP

What must be working before each stage can succeed:

### Stage 1: Spec Parse & Validate
- **Requires:** Valid YAML spec file, `hamr.core.spec.Spec.from_yaml()` working, `CharacterSpec` dataclass field types
- **Depends on:** Nothing external
- **Failure mode:** YAML parse error, missing required field, type mismatch
- **Risk:** LOW — extensively tested (2,206+ tests)

### Stage 2: Forge Resolution
- **Requires:** Valid `CharacterSpec` object, all forge modules importable
- **Hair Forge** → `hamr/hair/__init__.py` → `resolve_hair()`
- **Face Forge** → `hamr/face/__init__.py` → `resolve_face()`
- **Clothing Forge** → `hamr/clothing/__init__.py` → `resolve_clothing()`
- **Current behavior:** Failures in individual forges are **caught and degraded** (returns `None`/empty list).
- **Risk:** MEDIUM — graceful degradation, but `None` values must be handled downstream

### Stage 3: Performance Budget Check
- **Requires:** `CharacterSpec`, `PerformanceBudget` dataclass
- **Checks:** Triangle count, texture resolution, build time estimates
- **Failure mode:** Spec exceeds budget → blocks build unless `--force-over-budget`
- **Risk:** LOW — pure Python estimation, well-tested

### Stage 4: Blender Subprocess Launch
- **Requires:** `blender` binary at `/usr/bin/blender` (or `BLENDER_PATH` env), `--python-use-system-env` flag for ARM64
- **Bridge:** `hamr/blender_bridge/runner.py` → `run_blender_script()`
- **Timeout:** 600 seconds (10 minutes) default
- **Env:** `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true` is set
- **Risk:** HIGH — Blender 3.4.1 on ARM64 (Pi 5) has known compatibility issues
- **Critical sub-dependency:** VRM addon must be present in Blender, MB-Lab must be installed

### Stage 5: MB-Lab Base Mesh Generation
- **Requires:** MB-Lab 1.7.8 addon enabled and functional in headless mode
- **Steps:** `mbast.init_character()` → `mbast.auto_modelling()` → `mbast.finalize_character()`
- **Produces:** Armature + mesh objects (`f_af01` body mesh + armature)
- **Failure mode:** MB-Lab ops return `CANCELLED` or raise exceptions in headless mode
- **Risk:** HIGH — MB-Lab was designed for interactive use; headless mode is fragile
- **CRITICAL:** The code accepts `CANCELLED` as a valid result state at line 519, which is suspicious

### Stage 6: Spec Application (Colors, Height, Forges)
- **Requires:** At least one MESH object and one ARMATURE object in scene
- **Color application:** HSV tinting via `_hex_to_hsv()` + `_tint_texture()` + `_shift_image_hsv()`
- **Height scaling:** `armature.scale[2] *= (target_height / 165.0)`
- **HSV boundary issue (D-014):** `_hex_to_hsv()` converts hex → RGB → HSV. At hue boundary (H≈0.0 or H≈1.0), the interpolation in `_shift_image_hsv()` can wrap incorrectly: `h = (h + h_target * blend) / (1 + blend)` — this is a weighted average that does NOT properly handle the circular hue space. Colors near red (H≈0) will shift incorrectly.
- **Risk:** MEDIUM — color tinting will work but may produce wrong hues near boundary

### Stage 7: Stub Bone Creation
- **Requires:** ARMATURE object in scene, `head` bone existing
- **Creates:** jaw, leftEye, rightEye as micro-bones parented to head
- **Tags:** `_hamr_stub=True` custom property on pose bones
- **Risk:** LOW — pure bone creation, well-defined positions

### Stage 8: Hair Mesh Generation
- **Requires:** ARMATURE with head bone position resolvable
- **Process:** `HairMeshGenerator.generate()` → Bezier curves → mesh → material → parent to head
- **Potential failure:** Head bone position `(0.0, 0.0, 1.65)` fallback uses incorrect Z-up convention
- **Risk:** MEDIUM — procedural generation, no pre-existing mesh to validate against

### Stage 9: Clothing Mesh Generation
- **Requires:** Body mesh in scene (for shrinkwrap target)
- **Process:** `ClothingMeshGenerator.generate()` → pattern selection → region duplicate → offset → shrinkwrap → material
- **Failure:** If body mesh not found (`_find_body_mesh()` returns empty string), returns `[]`
- **Risk:** MEDIUM — depends on MB-Lab mesh naming conventions

### Stage 10: Weight Painting
- **Requires:** ARMATURE, body mesh, hair mesh (optional), clothing meshes (optional)
- **Process:** `WeightPaintEngine` → `paint_smooth()` → `normalize_weights()` → `transfer_weights()`
- **Risk:** MEDIUM — weight transfer quality affects VRM deformation

### Stage 11: Spring Bones
- **Requires:** ARMATURE with VRM extension, bone names matching MB-Lab conventions
- **Creates:** SpringBoneGroups (hair, breast, clothing) + collider spheres
- **Risk:** MEDIUM — collider bone names must exist in armature

### Stage 12: First-Person View
- **Requires:** ARMATURE with VRM extension, list of all mesh names
- **Risk:** LOW — annotation-only, no mesh manipulation

### Stage 13: VRM Humanoid Bone Mapping (D-008 CRITICAL)
- **Requires:** ARMATURE with `vrm_addon_extension`, all VRM 1.0 required bones present or stubbed
- **⛔ BUG: `armature.data.vrm_addon_extension` vs `armature.vrm_addon_extension`**
  - `build_avatar.py` line 861: `armature.data.vrm_addon_extension`
  - `vrm.py` line 121: `armature.vrm_addon_extension`
  - These are DIFFERENT objects. The VRM addon registers `vrm_addon_extension` on the **Object**, not the data block. Using `armature.data.vrm_addon_extension` will likely fail or access the wrong property.
- **⛔ BUG: Bone map inconsistency between `build_avatar.py` and `vrm.py`**
  - `build_avatar.py` MB_LAB_BONE_MAP: `"spine": "spine01"`, `"leftLowerLeg": "calf_L"`
  - `vrm.py` MB_LAB_BONE_MAP: `"spine": "spine"`, `"leftLowerLeg": "shin_L"`
  - MB-Lab uses different bone names depending on version. These MUST match the actual MB-Lab rig.
- **Risk:** CRITICAL — wrong property access + wrong bone names = VRM FAILS

### Stage 14: VRM Metadata
- **Requires:** ARMATURE with `vrm_addon_extension` (same bug as Stage 13)
- **Risk:** HIGH — cannot set metadata if extension access is wrong

### Stage 15: VRM Expressions (D-011, D-013)
- **Requires:** Shape keys on body mesh, expression presets in VRM extension
- **D-013 implementation:** `bind.index = sk_name` — uses shape key NAME string
- **Risk:** MEDIUM — shape key names must match MB-Lab's `Expressions_*` naming convention

### Stage 16: VRM LookAt (D-012)
- **Requires:** Eye bones (leftEye, rightEye) OR fallback to expression mode
- **Logic:** Checks for eye bones; if found → bone mode, else → expression mode
- **Risk:** LOW — has fallback

### Stage 17: VRM Export (D-016 CRITICAL)
- **Requires:** VRM addon enabled, all VRM properties set, `armature_object_name` parameter
- **D-016 fix applied:** Uses `"EXEC_DEFAULT"` with `ignore_warning=True`
- **D-017 applied:** `allow_non_humanoid_rig = True` as safety net
- **Environment variable:** `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true`
- **Risk:** HIGH — VRM addon version compatibility is critical

### Stage 18: Post-Export Validation
- **Requires:** Output `.vrm` file to exist and be valid glTF
- **Checks:** File size > 1024 bytes, glTF magic number `0x46546C67`
- **Risk:** LOW — basic checks only

### Stage 19: Rig Verification
- **Requires:** `hamr.rigs.verify.RigVerifier` importable inside Blender
- **Risk:** LOW — optional, ImportError caught gracefully

---

## 3. FAILURE POINT ANALYSIS — Top 10 Most Likely Failures

### ⛔ FP-1: VRM Extension Property Access Bug (PROBABILITY: 95%, IMPACT: FATAL)

**Problem:** `build_avatar.py` line 861 uses `armature.data.vrm_addon_extension` while `vrm.py` uses `armature.vrm_addon_extension`. The VRM addon registers the extension on the **Object** (not the data block). Accessing it via `.data` will result in `AttributeError` or silently wrong behavior.

**Location:** `build_avatar.py:861`, lines 912-913, 936-937, 988-989

**Mitigation:** Change all `obj.data.vrm_addon_extension` to `obj.vrm_addon_extension` in `build_avatar.py`, OR verify the VRM addon version stores on the data block for Blender 3.4.1.

### ⛔ FP-2: Bone Name Mapping Inconsistency (PROBABILITY: 90%, IMPACT: CRITICAL)

**Problem:** Three different `MB_LAB_BONE_MAP` dictionaries exist with conflicting values:
- `build_avatar.py`: `"spine": "spine01"`, `"chest": "spine02"`, `"upperChest": "spine03"`, `"leftLowerLeg": "calf_L"`
- `vrm.py`: `"spine": "spine"`, `"chest": "spine_01"`, `"upperChest": "spine_02"`, `"leftLowerLeg": "shin_L"`
- `stub_bones.py` (internal mapping): `"spine": "spine"`, `"chest": "spine_01"`, `"upperChest": "spine_02"`, `"leftLowerLeg": "shin_L"`

The `build_avatar.py` `_apply_vrm_humanoid()` function at line 870 uses `MB_LAB_BONE_MAP` from its own module (lines 49-73), while `vrm.py`'s `setup_vrm_humanoid()` uses its own `MB_LAB_BONE_MAP`. If `build_avatar.py` is what runs during E2E (it IS — it's the Blender-side script), the wrong bone names will be used.

**Mitigation:** Consolidate all bone maps into a single canonical source. Verify against actual MB-Lab 1.7.8 bone naming by running `mbast.init_character()` and inspecting bone names.

### ⛔ FP-3: MB-Lab Headless Mode Failure (PROBABILITY: 80%, IMPACT: HIGH)

**Problem:** MB-Lab 1.7.8 was designed for interactive Blender use. The three-step generate sequence (`init_character` → `auto_modelling` → `finalize_character`) may:
1. Fail silently (return `CANCELLED`)
2. Require a viewport/update cycle between steps
3. Depend on GUI-only operators that don't work in `--background` mode

**Evidence:** Line 519 accepts `CANCELLED` as a non-error, which suggests the authors have already seen this behavior. The `CANCELLED` result means the operator was invoked but chose not to execute.

**Mitigation:** Add explicit error checking after each MB-Lab step. If mesh count is 0 after `finalize_character()`, fall back to base mesh import. Consider adding an explicit scene update (`bpy.context.view_layer.update()`) between MB-Lab steps.

### ⛔ FP-4: HSV Color Boundary Wrap (D-014) (PROBABILITY: 70%, IMPACT: MEDIUM)

**Problem:** The hue interpolation in `_shift_image_hsv()` uses `h = (h + h_target * blend) / (1 + blend)` which is a weighted average, NOT circular interpolation. When `h` is near 1.0 (red) and `h_target` is near 0.0 (also red), the result will be near 0.5 (cyan/green) instead of red.

**Location:** `build_avatar.py:648`

**Mitigation:** Replace with circular (angular) hue interpolation:
```python
import math
h = (math.sin(h * 2 * math.pi) * (1-blend) + math.sin(h_target * 2 * math.pi) * blend,
     math.cos(h * 2 * math.pi) * (1-blend) + math.cos(h_target * 2 * math.pi) * blend)
h = (math.atan2(h_sin, h_cos) / (2 * math.pi)) % 1.0
```

### ⛔ FP-5: Blender ARM64 Timeout on Pi 5 (PROBABILITY: 60%, IMPACT: HIGH)

**Problem:** The default timeout for the Blender subprocess is 600 seconds (10 min). On a Raspberry Pi 5 (ARM64), Blender in headless mode will:
- Take 15-30 seconds just to start (loading addons)
- MB-Lab generation takes 30-60+ seconds on ARM
- Hair mesh generation is CPU-intensive (Catmull-Rom interpolation)
- VRM export involves glTF serialization of potentially 50K+ triangles

The 600-second timeout is generous for x86 but may be tight for Pi 5 with complex specs.

**Mitigation:** Increase default timeout to 900s for ARM64. Add progress indicators via stderr parsing.

### ⛔ FP-6: `from_dict()` Global Mutation (PROBABILITY: 40%, IMPACT: MEDIUM)

**Problem:** The context warns about `from_dict()` global mutation. **However**, examining the code at `models.py:289`, the function now does `data = copy.deepcopy(data)` before any mutation, which should prevent the issue. This was likely a bug that has been patched.

**Remaining risk:** The `CharacterSpec.from_dict()` at line 304 does `[spec_cls.from_dict(item) if isinstance(item, dict) else item for item in data[key]]` which works on the deep copy. The `CharacterSpec.to_dict()` uses `asdict(self)` which creates a new dict. So the data flow is: `Spec.from_yaml()` → `CharacterSpec.from_dict(deepcopy)` → `spec.to_dict()` → JSON serialize. This appears safe.

**Mitigation:** Verify that no code path passes presets directly (by reference) to `from_dict()` without deepcopy. The `cli.py` line 154 does `CharacterSpec.from_dict(preset_data)` where `preset_data` comes from `resolve_preset()` which may return a reference to a global. The deepcopy inside `from_dict()` should protect this.

### ⛔ FP-7: VRM Auto-Mapping Overwrite (D-008) (PROBABILITY: 30%, IMPACT: CRITICAL)

**Problem:** The VRM addon's default behavior is to auto-map bones based on name heuristics. If `initial_automatic_bone_assignment` is not set to `False` BEFORE any other VRM property access, the addon will overwrite explicit mappings.

**Current mitigation:** `build_avatar.py` line 865 sets `human_bones.initial_automatic_bone_assignment = False` and line 867 sets `human_bones.filter_by_human_bone_hierarchy = False`. These are the D-008 and D-009 patches respectively.

**Remaining risk:** The VRM addon may trigger auto-mapping during property access (e.g., when iterating `human_bone_name_to_human_bone()`). The order matters: auto-mapping must be disabled BEFORE accessing any bone properties. The current code does this correctly.

**Mitigation:** Already patched. Verify that the VRM addon version matches expectations.

### ⛔ FP-8: Expression Shape Key Name Mismatch (PROBABILITY: 50%, IMPACT: MEDIUM)

**Problem:** The `MB_LAB_EXPRESSION_MAP` in `build_avatar.py` uses shape key names like `Expressions_mouthSmile_max`. However, MB-Lab 1.7.8 may not generate exactly these names. After `finalize_character()`, MB-Lab renames shape keys with `Expressions_` prefix, but the exact naming convention depends on the MB-Lab version and character template.

If shape keys don't match, expressions will be empty/missing in the VRM output, but the build won't crash (line 972: `if not sk_name or not mesh_name: continue`).

**Mitigation:** Add a shape key discovery step that scans `mesh.data.shape_keys.key_blocks` and logs all available names. Build a dynamic mapping instead of hardcoding.

### ⛔ FP-9: Gender-Specific MB-Lab Initialization (PROBABILITY: 35%, IMPACT: MEDIUM)

**Problem:** `bpy.ops.mbast.init_character()` creates the default MB-Lab character (typically `f_af01` — female). The spec file for Runa Gridweaver specifies `build: athletic-slender` but there's no code to configure MB-Lab's gender/body type parameters before calling `init_character()`. The `auto_modelling()` call also takes no parameters from the spec.

This means MB-Lab will generate its default female character regardless of the spec, and the spec's body proportions will only be applied via height scaling (`armature.scale[2] *= scale`).

**Mitigation:** Add MB-Lab parameter setting between `init_character()` and `auto_modelling()`, or pass the spec to MB-Lab's modelling system.

### ⛔ FP-10: ARMature Search Order and Name Conflicts (PROBABILITY: 25%, IMPACT: MEDIUM)

**Problem:** Multiple functions find the armature by iterating `bpy.data.objects` and taking the first ARMATURE type. If MB-Lab or base mesh import creates multiple armatures (some MB-Lab versions create a separate IK armature), the wrong armature may be selected.

**Evidence:** Line 335-338: `for obj in bpy.data.objects: if obj.type == "ARMATURE": armature_name = obj.name; break` — this takes the FIRST armature found, which may not be the deform armature.

**Mitigation:** Search for armature by name convention (e.g., containing "Armature" or "rig'), or prefer the armature that has mesh children.

---

## 4. PRE-FLIGHT CHECKLIST

Before running `hamr build examples/spec_runa_gridweaver.yaml --out output/`:

### Environment Verification
- [ ] **Blender 3.4.1 installed and accessible:** Run `blender --version` and verify output
- [ ] **VRM addon enabled in Blender:** Run `hamr check-env` and verify `VRM Addon: ✓ Installed`
- [ ] **MB-Lab 1.7.8 addon enabled in Blender:** Verify `MB-Lab: ✓ Installed` in `check-env` output
- [ ] **Python environment:** Verify `hamr.__version__` returns `0.8.0`
- [ ] **Pi 5 memory:** Verify at least 4GB free RAM (`free -h`)

### Code Verification
- [ ] **Bone map consistency:** Verify `MB_LAB_BONE_MAP` values match across `build_avatar.py`, `vrm.py`, `stub_bones.py`
- [ ] **VRM extension access:** Verify whether `armature.data.vrm_addon_extension` or `armature.vrm_addon_extension` is correct for the installed VRM addon version
- [ ] **Seiðr-Smiðja patches D-008 through D-020:** Verify all are present in `build_avatar.py` (check docstring at lines 7-25)
- [ ] **HSV interpolation:** Review `_shift_image_hsv()` for circular hue handling

### Spec File Verification
- [ ] **Run `hamr validate examples/spec_runa_gridweaver.yaml`** — should return 0 errors
- [ ] **Run `hamr build ... --dry-run`** — verify forge resolution completes
- [ ] **Check budget:** `--budget minimal` for first run

### Build Script Path Verification
- [ ] **Verify `build_avatar.py` exists at** `hamr/scripts/build_avatar.py` (relative to package). The `BuildPipeline` looks for it at `Path(__file__).parent.parent / "scripts" / "build_avatar.py"` relative to `pipeline.py`, and also at `hamr.__file__` parent.

### VRM Addon Version Verification
- [ ] **Check VRM addon version:** Must be compatible with Blender 3.4.1. VRM addon 2.x for VRM 1.0.
- [ ] **Verify `allow_non_humanoid_rig` property exists:** Some older versions don't have this
- [ ] **Verify `initial_automatic_bone_assignment` property exists:** Required for D-008 patch
- [ ] **Verify `filter_by_human_bone_hierarchy` property exists:** Required for D-009 patch
- [ ] **Verify `human_bone_name_to_human_bone()` method exists on VRM addon's `HumanBonesPropertyGroup`**

---

## 5. RISK ASSESSMENT

### Clean First Build Probability: **15-25%**

The pipeline has NEVER been run E2E. Based on the code analysis, the most likely scenario is:

1. **Phase A** (spec parse → JSON serialize): **90%** chance of success — well-tested, pure Python
2. **Phase B** (Blender subprocess): **15-25%** chance of first-run success due to:

### Critical Blockers (Must Fix Before E2E Attempt)

| # | Issue | Blocker Level | Estimated Fix Time |
|---|-------|---------------|-------------------|
| 1 | `armature.data.vrm_addon_extension` vs `armature.vrm_addon_extension` inconsistency | **FATAL** — VRM setup will crash | 30 min |
| 2 | MB_LAB_BONE_MAP inconsistency across 3 files | **CRITICAL** — Wrong bone mapping = invalid VRM | 1-2 hours |
| 3 | MB-Lab headless mode — `CANCELLED` acceptance | **HIGH** — May silently fail to generate base mesh | 2-4 hours |

### Likely First-Run Issues (Expect to Fix)

| # | Issue | Probability | Fix Complexity |
|---|-------|-------------|----------------|
| 4 | HSV hue wrap in color tinting | 70% | Low |
| 5 | Shape key name mismatch in expressions | 50% | Medium |
| 6 | MB-Lab gender/body type not configurable | 35% | Medium |
| 7 | Wrong armature selected (multiple armatures) | 25% | Low |
| 8 | Pi 5 timeout (long build times) | 60% | Low (increase timeout) |
| 9 | VRM export `CANCELLED` in headless (D-016 variant) | 40% | Low (already patched) |

### Recommended E2E Approach

1. **Pre-flight:** Run `hamr check-env` and resolve all blockers first
2. **Dry run:** `hamr build examples/spec_runa_gridweaver.yaml --out output/ --dry-run`
3. **Fix FP-1 (VRM extension access):** Change `armature.data.vrm_addon_extension` → `armature.vrm_addon_extension` in build_avatar.py
4. **Fix FP-2 (bone names):** Unify MB_LAB_BONE_MAP across all files. Verify against actual MB-Lab output.
5. **First real run:** Use `--timeout 900` on Pi 5
6. **Iterate:** Expect 2-4 iterations to resolve issues

### Test Isolation Risk

The 2,206 passing tests validate individual modules in isolation. The critical E2E path that crosses the Blender subprocess boundary is **UNTESTED**. Key untested paths:
- Spec JSON → Blender script argument passing
- MB-Lab sequence inside Blender `--background`
- VRM addon property configuration via `bpy` in headless mode
- VRM export `EXEC_DEFAULT` context
- Hair/clothing mesh generation inside Blender
- Weight transfer between body and clothing meshes
- Full VRM output validation (not just glTF header check)

### Estimated Time to Clean E2E Build

**Optimistic:** 1-2 days (1-2 blocker fixes, 3-4 iteration cycles)  
**Realistic:** 3-5 days (discover additional VRM addon quirks, MB-Lab headless issues, bone naming surprises)  
**Pessimistic:** 1-2 weeks (VRM addon incompatibility requiring patches, Pi 5 resource limitations)

---

## 6. KEY ARCHITECTURAL FINDINGS

### 6.1 Two Separate VRM Setup Paths

There are **two independent VRM setup implementations** that will conflict if both are called:

1. **`build_avatar.py`** contains its own `_apply_vrm_humanoid()`, `_apply_vrm_metadata()`, `_apply_vrm_expressions()`, `_apply_vrm_look_at()` functions
2. **`hamr/export/vrm.py`** contains `setup_vrm_humanoid()`, `setup_vrm_metadata()`, `setup_vrm_expressions()`, `setup_vrm_lookAt()`, `export_vrm()`

The `build_avatar.py` does NOT import or call `vrm.py`. It reimplements everything inline. This means bug fixes in `vrm.py` may NOT be reflected in `build_avatar.py`.

### 6.2 Bone Map Divergence Is the Single Most Dangerous Bug

Three different `MB_LAB_BONE_MAP` dictionaries exist with conflicting spine and leg bone names. During E2E build, `build_avatar.py`'s map is used (line 870), which has:
- `"spine": "spine01"` — conflict with `vrm.py`'s `"spine": "spine"`
- `"leftLowerLeg": "calf_L"` — conflict with `vrm.py`'s `"leftLowerLeg": "shin_L"`

MB-Lab 1.7.8 uses `spine`, `spine_01`, `spine_02` (with underscores, no number on the base). The build_avatar.py version without underscores is likely wrong.

### 6.3 Error Handling Pattern: Warn, Don't Fail

Most Phase 12 integration steps (hair, clothing, spring bones, first-person) use `try/except` with `logger.warning()` and continue on failure. This means partial builds are possible, but the output VRM may be missing critical features (hair, clothing, expressions) without clear indication.

### 6.4 The `from_dict()` Mutation Risk Has Been Patched

The context warns about `from_dict()` global mutation, but the current implementation at `models.py:289` does `data = copy.deepcopy(data)` before any transformation. This appears to be a pre-existing bug that has been fixed.

### 6.5 Forge Failure is Silent

`_resolve_forges()` wraps each forge in `try/except` and returns `None` on failure. Downstream code checks `if not hair_config: return` / `if not clothing_layers: return []`, so forge failures degrade gracefully. However, there's no logging summary at the CLI level informing the user that forges failed.

---

## 7. APPENDIX: File Cross-Reference

| File | Lines | Role |
|------|-------|------|
| `hamr/cli.py` | 620 | CLI entry point, preset resolution, budget check |
| `hamr/core/builder.py` | 234 | `build()` orchestrator, forge resolution, Blender bridge |
| `hamr/core/pipeline.py` | 314 | `BuildPipeline` class, JSON serialize + subprocess |
| `hamr/blender_bridge/runner.py` | 197 | `run_blender_script()`, timeout, env vars |
| `hamr/scripts/build_avatar.py` | 1386 | **THE BLENDER SCRIPT** — full E2E build inside Blender |
| `hamr/core/models.py` | 314 | Dataclasses: CharacterSpec, BodySpec, etc. |
| `hamr/core/spec.py` | ~80 | `Spec.from_yaml()`, `Spec.from_dict()` |
| `hamr/core/validate.py` | — | Spec validation |
| `hamr/core/perf.py` | 460 | Performance budget checking |
| `hamr/export/vrm.py` | 311 | VRM setup functions (separate from build_avatar.py) |
| `hamr/rigs/stub_bones.py` | 418 | Stub bone creation for jaw/eyes |
| `hamr/hair/mesh.py` | 752 | HairMeshGenerator |
| `hamr/clothing/mesh.py` | 726 | ClothingMeshGenerator |
| `hamr/face/expressions.py` | 447 | ExpressionBinder |
| `hamr/materials/anime.py` | 1084 | Anime materials (Eevee) |
| `hamr/rigs/spring_bones.py` | ~500+ | Spring bone configuration |
| `hamr/rigs/collision.py` | 485 | Collision mesh generation |
| `hamr/export/first_person.py` | ~350 | First-person annotations |
| `hamr/export/animation_clips.py` | 739 | Animation presets |

---

*The blade remembers every wound it took. This architecture maps every scar in the forge.*

— Rúnhild Svartdóttir, ARCHITECT