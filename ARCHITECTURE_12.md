# ᚺᚨᛗᚱ — Architecture Phase 12: Integration & Testing

**Phase Name:** Heimdallr — The Gatekeeper Sees All  
**Version:** v0.5.0 (post-Phase 11, v0.4.0 → v0.5.0)  
**Status:** Design  
**Author:** Rúnhild Svartdóttir, THE ARCHITECT  

---

## 0. Problem Statement

Phase 11 built six powerful standalone modules (stub bones, hair mesh, clothing mesh, weight paint, spring bones, first-person, presets, perf budgets). **None of them are wired into the build pipeline.** The Blender script (`build_avatar.py`) stops at Step 3: _apply spec → export VRM_. It never calls:

- ❌ `hamr.rigs.stub_bones.create_missing_bones()`  
- ❌ `hamr.hair.mesh.HairMeshGenerator.generate()`  
- ❌ `hamr.clothing.mesh.ClothingMeshGenerator.generate()`  
- ❌ `hamr.rigs.weights.WeightPaintEngine.paint_smooth()` / `.transfer_weights()`  
- ❌ `hamr.rigs.spring_bones.apply_spring_bones()`  
- ❌ `hamr.export.first_person.configure_first_person()`  
- ❌ `hamr.core.perf.check_budget()`  

The CLI has no `hamr build --preset <name>` command. There is no end-to-end test. Performance budgets exist but are never consulted.

**Phase 12's mission: Connect everything. Ship an avatar.**

---

## 1. Module Integration Map

The diagram below shows **which existing module calls which Phase 11 module**, and in **what order**. Arrows indicate call direction (caller → callee).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE ORCHESTRATOR                           │
│                        (core/pipeline.py)                              │
│                                                                        │
│  Spec.parse() → validate() → perf.check_budget() ──→ [FAIL if over]   │
│       │                                                                │
│       ▼                                                                │
│  _resolve_forges() ─── hair.resolve_hair()                            │
│       │              face.resolve_face()                               │
│       │              clothing.resolve_clothing()                        │
│       ▼                                                                │
│  blender_bridge.runner.run_blender_script(build_avatar.py ── args)    │
│                                                                        │
└─────────────────────────────────────────────┬───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  build_avatar.py (RUNS INSIDE BLENDER)                  │
│                                                                        │
│  Step 0  Enable VRM add-on                                             │
│  Step 1  Clear scene                                                   │
│  Step 2  Import base mesh (MB-Lab or file)                             │
│  Step 3  Apply body presets + proportions                              │
│  ──────── PHASE 12 NEW INTEGRATION BELOW ──────────                    │
│  Step 3a Stub Bones ── hamr.rigs.stub_bones.create_missing_bones()     │
│  Step 3b Hair Mesh  ── hamr.hair.mesh.HairMeshGenerator.generate()     │
│  Step 3c Clothing    ── hamr.clothing.mesh.ClothingMeshGenerator       │
│                       .generate() for each spec.clothing item           │
│  Step 3d Weight Paint ─ hamr.rigs.weights.WeightPaintEngine            │
│           .paint_smooth() on each mesh (body + hair + clothing)        │
│           .transfer_weights() from body → clothing                      │
│           .normalize_weights() on each mesh                             │
│  Step 3e Spring Bones ─ hamr.rigs.spring_bones.apply_spring_bones()   │
│  Step 3f First-Person ─ hamr.export.first_person.configure_first_      │
│           person() for all meshes                                      │
│  ──────── EXISTING STEPS (MODIFIED) ─────────────────                    │
│  Step 4  Apply VRM humanoid bone mapping                                │
│  Step 5  Apply VRM metadata                                             │
│  Step 6  Apply VRM expressions                                          │
│  Step 7  Apply VRM lookAt                                               │
│  Step 8  Export VRM                                                     │
│  Step 9  Post-export validation                                         │
│  ──────── PHASE 12 NEW POST-EXPORT ─────────────────                    │
│  Step 10 Rig verification ─ hamr.rigs.verify.verify_rig()              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Call Order Summary

| Step | Module Path | Function | Caller | New/Modified |
|------|------------|----------|--------|-------------|
| 0 | `blender_bridge/runner.py` | `run_blender_script()` | `core/pipeline.py` | Modified (add perf + preset args) |
| 1 | `scripts/build_avatar.py` | `main()` | Blender subprocess | **Major rewrite** |
| 3a | `rigs/stub_bones.py` | `create_missing_bones()` | `build_avatar.py` | **New call site** |
| 3b | `hair/mesh.py` | `HairMeshGenerator.generate()` | `build_avatar.py` | **New call site** |
| 3c | `clothing/mesh.py` | `ClothingMeshGenerator.generate()` | `build_avatar.py` | **New call site** |
| 3d | `rigs/weights.py` | `WeightPaintEngine.*` | `build_avatar.py` | **New call site** |
| 3e | `rigs/spring_bones.py` | `apply_spring_bones()` | `build_avatar.py` | **New call site** |
| 3f | `export/first_person.py` | `configure_first_person()` | `build_avatar.py` | **New call site** |
| — | `core/perf.py` | `check_budget()` | `core/pipeline.py` | **New call site** |
| — | `core/presets.py` | `CHARACTER_PRESETS` | `core/pipeline.py`, `cli.py` | **New call site** |
| — | `rigs/verify.py` | `verify_rig()` | `build_avatar.py` (post-export) | **New call site** |

---

## 2. build_avatar.py Integration — Full Sequence

### 2.1 Current State (v0.4.0)

The script has 5 steps:
```
Step 0: Enable VRM add-on
Step 1: Clear scene
Step 2: Import base mesh
Step 3: Apply spec transformations (colors, height, forge config, VRM mapping, expressions, lookAt)
Step 4: Export VRM
Step 5: Validate VRM file
```

### 2.2 New Build Sequence (v0.5.0)

```python
def main() -> int:
    # ── Step 0: Parse args & enable VRM add-on (UNCHANGED) ──────────────
    # ── Step 1: Clear scene (UNCHANGED) ─────────────────────────────────
    # ── Step 2: Import base mesh (UNCHANGED) ────────────────────────────

    # ── Step 3: Apply body spec transformations (UNCHANGED) ──────────────
    _apply_spec(bpy, spec_data, forge_config=forge_config)

    # ═══════════════════════════════════════════════════════════════════
    # ── Step 3a: Create stub bones (NEW) ────────────────────────────────
    armature_name = _find_armature(bpy)
    stub_result = _integrate_stub_bones(bpy, armature_name)

    # ── Step 3b: Generate hair mesh (NEW) ────────────────────────────────
    hair_result = _integrate_hair_mesh(bpy, spec_data, forge_config, armature_name)

    # ── Step 3c: Generate clothing meshes (NEW) ─────────────────────────
    clothing_results = _integrate_clothing_meshes(bpy, spec_data, forge_config,
                                                   armature_name)

    # ── Step 3d: Weight paint all meshes (NEW) ───────────────────────────
    _integrate_weight_paint(bpy, armature_name, hair_result, clothing_results)

    # ── Step 3e: Configure spring bones (NEW) ────────────────────────────
    _integrate_spring_bones(bpy, armature_name, spec_data, forge_config,
                            hair_result, clothing_results)

    # ── Step 3f: Configure first-person annotations (NEW) ────────────────
    _integrate_first_person(bpy, armature_name, hair_result, clothing_results)
    # ═══════════════════════════════════════════════════════════════════

    # ── Step 4: Apply VRM humanoid bone mapping (UNCHANGED) ─────────────
    _apply_vrm_humanoid(bpy, spec_data, stub_result)
    # ── Step 5: Apply VRM metadata (UNCHANGED) ──────────────────────────
    # ── Step 6: Apply VRM expressions (UNCHANGED) ───────────────────────
    # ── Step 7: Apply VRM lookAt (UNCHANGED) ────────────────────────────

    # ── Step 8: Export VRM (UNCHANGED) ───────────────────────────────────
    # ── Step 9: Post-export validation (UNCHANGED) ───────────────────────

    # ── Step 10: Rig verification (NEW) ──────────────────────────────────
    _verify_rig_post_export(bpy, armature_name)
```

### 2.3 New Integration Functions

#### `_integrate_stub_bones(bpy, armature_name) → StubBoneResult`

```python
def _integrate_stub_bones(bpy, armature_name: str):
    """Create stub bones for missing VRM 1.0 humanoid bones."""
    from hamr.rigs.stub_bones import create_missing_bones
    result = create_missing_bones(armature_name, base_type="mblab")
    if result.created_bones:
        logger.info(f"Stub bones created: {list(result.created_bones.keys())}")
    return result
```

**Modification to `_apply_vrm_humanoid`**: Merge stub bone map into the bone map before VRM mapping. The existing `stub_bones.get_stub_bone_map()` returns `{"leftEye": "leftEye", "rightEye": "rightEye", "jaw": "jaw"}`. These must be **added** to whichever bone map is active (MB-Lab or TurboSquid).

```python
# In _apply_vrm_humanoid():
from hamr.rigs.stub_bones import get_stub_bone_map
stub_map = get_stub_bone_map()
bone_map.update(stub_map)  # Merge stub bones into VRM mapping
```

#### `_integrate_hair_mesh(bpy, spec_data, forge_config, armature_name) → HairMeshResult | None`

```python
def _integrate_hair_mesh(bpy, spec_data, forge_config, armature_name):
    """Generate procedural hair mesh from spec."""
    from hamr.hair.mesh import HairMeshGenerator

    hair_spec = spec_data.get("hair", {})
    if not hair_spec or hair_spec.get("style") == "none":
        return None

    style = hair_spec.get("style", "long_straight")
    # Determine head position from armature
    armature = bpy.data.objects.get(armature_name)
    head_bone = armature.data.bones.get("head")
    if head_bone:
        head_pos = tuple(armature.matrix_world @ head_bone.head_local)
        head_radius = 0.10  # Standard head radius in meters
    else:
        head_pos = (0.0, 1.65, 0.0)
        head_radius = 0.10

    # Build color config from hair spec
    color_config = None
    if forge_config and forge_config.get("hair"):
        hair_fc = forge_config["hair"]
        color_config = {
            "roots_hsv": hair_fc.get("roots_hsv", (30, 0.7, 0.6)),
            "tips_hsv": hair_fc.get("tips_hsv", (35, 0.3, 0.9)),
        }

    gen = HairMeshGenerator()
    result = gen.generate(
        style_name=style,
        head_center=head_pos,
        head_radius=head_radius,
        color_config=color_config,
    )
    logger.info(
        f"Hair mesh: {result.object_name}, "
        f"{result.vertex_count} verts, {result.triangle_count} tris"
    )
    return result
```

#### `_integrate_clothing_meshes(bpy, spec_data, forge_config, armature_name) → list[ClothingMeshResult]`

```python
def _integrate_clothing_meshes(bpy, spec_data, forge_config, armature_name):
    """Generate procedural clothing meshes from spec."""
    from hamr.clothing.mesh import ClothingMeshGenerator

    clothing_specs = spec_data.get("clothing", [])
    if not clothing_specs:
        return []

    # Find body mesh (first mesh with "body" in name or the largest mesh)
    body_mesh_name = _find_body_mesh(bpy)
    if not body_mesh_name:
        logger.warning("No body mesh found for clothing shrinkwrap")
        return []

    gen = ClothingMeshGenerator()
    results = []

    for i, cloth_spec in enumerate(clothing_specs):
        # Create a simple spec object from dict for ClothingMeshGenerator
        cloth_obj = _dict_to_clothing_spec(cloth_spec, index=i)

        try:
            result = gen.generate(
                spec=cloth_obj,
                body_mesh_name=body_mesh_name,
                armature_name=armature_name,
            )
            results.append(result)
            logger.info(
                f"Clothing mesh {i}: {result.mesh_name}, "
                f"{result.triangle_count} tris, "
                f"weight_transferred={result.weight_transferred}"
            )
        except Exception as exc:
            logger.warning(f"Clothing mesh {i} failed: {exc}")
            continue

    return results
```

#### `_integrate_weight_paint(bpy, armature_name, hair_result, clothing_results)`

```python
def _integrate_weight_paint(bpy, armature_name, hair_result, clothing_results):
    """Apply weight painting to all generated meshes."""
    from hamr.rigs.weights import WeightPaintEngine

    engine = WeightPaintEngine()

    # Smooth weights on body mesh
    body_mesh_name = _find_body_mesh(bpy)
    if body_mesh_name:
        engine.paint_smooth(
            armature_name=armature_name,
            mesh_name=body_mesh_name,
            influence_radius=0.3,
            iterations=3,
        )
        engine.normalize_weights(armature_name, body_mesh_name)

    # Transfer weights from body to clothing
    for cloth_result in (clothing_results or []):
        if cloth_result.mesh_name and body_mesh_name:
            engine.transfer_weights(
                source_mesh=body_mesh_name,
                target_mesh=cloth_result.mesh_name,
            )
            engine.normalize_weights(armature_name, cloth_result.mesh_name)

    # Normalize hair mesh weights
    if hair_result and hair_result.object_name:
        engine.normalize_weights(armature_name, hair_result.object_name)

    # Score quality on body mesh
    if body_mesh_name:
        report = engine.get_quality_score(armature_name, body_mesh_name)
        logger.info(
            f"Weight paint quality: {report.score:.3f} "
            f"({classify_deformation_quality(report.score)})"
        )
```

#### `_integrate_spring_bones(bpy, armature_name, spec_data, forge_config, hair_result, clothing_results)`

```python
def _integrate_spring_bones(bpy, armature_name, spec_data, forge_config,
                              hair_result, clothing_results):
    """Configure VRM 1.0 spring bones for dynamic secondary motion."""
    from hamr.rigs.spring_bones import (
        configure_hair_spring,
        configure_breast_spring,
        configure_clothing_spring,
        apply_spring_bones,
        SpringBoneCollider,
        DEFAULT_COLLIDERS,
    )
    from hamr.core.models import HairPhysicsSpec

    spring_groups = []

    # Hair spring bones
    hair_spec = spec_data.get("hair", {})
    physics_spec = None
    if hair_spec.get("physics"):
        physics_spec = HairPhysicsSpec(**hair_spec["physics"])
    hair_spring = configure_hair_spring(physics_spec)
    if hair_result and hair_result.bone_chain:
        hair_spring.bone_chains = [hair_result.bone_chain]
    spring_groups.append(hair_spring)

    # Breast spring bones (from body proportions)
    body_spec = spec_data.get("body", {})
    breast_spring = configure_breast_spring(body_spec)
    spring_groups.append(breast_spring)

    # Clothing spring bones
    for cloth_result in (clothing_results or []):
        cloth_type = "skirt"  # default
        cloth_spring = configure_clothing_spring(
            clothing_name=cloth_result.mesh_name,
            cloth_type=cloth_type,
        )
        spring_groups.append(cloth_spring)

    # Apply all spring bones to armature
    result = apply_spring_bones(
        armature_name=armature_name,
        spring_groups=spring_groups,
        colliders=DEFAULT_COLLIDERS,
    )
    logger.info(
        f"Spring bones applied: {len(result.get('spring_groups', []))} groups, "
        f"{len(result.get('colliders', []))} colliders"
    )
```

#### `_integrate_first_person(bpy, armature_name, hair_result, clothing_results)`

```python
def _integrate_first_person(bpy, armature_name, hair_result, clothing_results):
    """Configure VRM 1.0 first-person view annotations."""
    from hamr.export.first_person import configure_first_person

    # Collect all mesh names to annotate
    mesh_names = []
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            mesh_names.append(obj.name)

    config = configure_first_person(
        armature_name=armature_name,
        mesh_names=mesh_names,
    )
    logger.info(
        f"First-person annotations: {len(config.mesh_annotations)} meshes, "
        f"bone={config.first_person_bone}"
    )
```

### 2.4 Perf Budget Check — Pre-Blender Gate

The `core/pipeline.py::BuildPipeline.build()` method must check performance budgets **before** launching Blender. This is a pre-flight gate:

```python
# In core/pipeline.py, BuildPipeline.build(), after Step 2 (validate):
from hamr.core.perf import check_budget, PerformanceBudget

# Step 2b: Check performance budget
budget = PerformanceBudget()  # Pi 5 defaults
perf_report = check_budget(spec.character, budget)
if not perf_report.within_budget:
    logger.warning(f"⚠ Spec over budget: {perf_report.summary()}")
    if not args.get("force_over_budget", False):
        result.errors.append(
            f"Spec exceeds Pi 5 performance budget:\n"
            + "\n".join(f"  • {w}" for w in perf_report.warnings)
        )
        result.elapsed = time.time() - start
        return result
```

The pipeline also receives the budget tier from the CLI:
```
hamr build --budget balanced spec.yaml
```

Valid budget tiers: `minimal`, `balanced` (default), `high`.

### 2.5 Preset-Driven Build Path

When `--preset <name>` is used, the pipeline loads a preset, deep-merges it with the spec, and proceeds:

```python
# In core/pipeline.py, BuildPipeline.build():
from hamr.core.presets import CHARACTER_PRESETS, deep_merge_preset

if preset_name:
    if preset_name not in CHARACTER_PRESETS:
        result.errors.append(f"Unknown preset: {preset_name}")
        return result
    preset_data = CHARACTER_PRESETS[preset_name]
    spec_dict = deep_merge_preset(preset_data["spec"], spec_dict)
    logger.info(f"Applied preset: {preset_name} ({preset_data['display_name']})")
```

---

## 3. CLI Enhancement

### 3.1 New Commands

#### `hamr build --preset <name>`

```python
# Add to build_parser in cli.py
build_parser.add_argument(
    "--preset", "-p",
    default=None,
    choices=list(CHARACTER_PRESETS.keys()),
    help="Apply a character preset before building"
)
build_parser.add_argument(
    "--budget", "-b",
    default="balanced",
    choices=["minimal", "balanced", "high"],
    help="Performance budget tier (default: balanced for Pi 5)"
)
build_parser.add_argument(
    "--force-over-budget",
    action="store_true",
    help="Force build even if spec exceeds performance budget"
)
```

The `cmd_build()` function passes these through to `BuildPipeline.build()`.

#### `hamr verify-rig <vrm>`

```python
# New subparser
verify_rig_parser = subparsers.add_parser(
    "verify-rig",
    help="Verify VRM rig completeness and bone hierarchy"
)
verify_rig_parser.add_argument("path", help="Path to VRM file")
verify_rig_parser.add_argument(
    "--strict", action="store_true",
    help="Treat warnings as errors"
)
verify_rig_parser.set_defaults(func=cmd_verify_rig)

def cmd_verify_rig(args: argparse.Namespace) -> int:
    """Verify a VRM file's rig structure."""
    from hamr.rigs.verify import verify_vrm_rig
    try:
        report = verify_vrm_rig(args.path)
        # ... format and print report ...
        return 0 if report["valid"] else 1
    except HamrError as e:
        print(f"✗ Verification error: {e}", file=sys.stderr)
        return 1
```

Note: `verify_vrm_rig()` is a **new pure-Python function** in `rigs/verify.py` that reads a VRM/GLB file off disk (using `struct` to parse glTF binary) and checks bone presence without Blender.

#### `hamr list-presets` (Enhanced)

The existing `cmd_list_presets()` only shows body presets. It should also list character presets:

```python
def cmd_list_presets(args: argparse.Namespace) -> int:
    """List available presets (body + character)."""
    what = getattr(args, "what", "all")

    if what in ("all", "character"):
        print("Character presets:")
        print("-" * 40)
        for name, preset in CHARACTER_PRESETS.items():
            print(f"  {name:30s}  {preset['display_name']}")

    if what in ("all", "body"):
        print("\nBody presets:")
        print("-" * 40)
        for name, proportions in BODY_PRESETS.items():
            desc = ", ".join(f"{k}={v:.2f}" for k, v in proportions.items())
            print(f"  {name:20s}  {desc}")

    return 0
```

### 3.2 Argument Signature Summary

| Command | Argument | Type | Default | Description |
|---------|----------|------|---------|-------------|
| `build` | `--preset` / `-p` | `str` | `None` | Apply character preset |
| `build` | `--budget` / `-B` | `str` | `balanced` | Perf budget tier |
| `build` | `--force-over-budget` | flag | `False` | Build even if over budget |
| `verify-rig` | `path` | positional | — | VRM file to verify |
| `verify-rig` | `--strict` | flag | `False` | Warnings as errors |
| `list-presets` | `--what` | `str` | `all` | `all`, `character`, or `body` |

---

## 4. Pipeline Order — Exact Execution Sequence

This is the canonical execution order for a full Hamr build:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ PHASE 12 FULL BUILD PIPELINE                                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─ PYTHON (outside Blender) ─────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  1.  Spec.from_yaml(spec_path)                                      │   │
│  │  2.  validate_spec(spec.character)                                  │   │
│  │  3.  perf.check_budget(spec.character, budget)   ← PRE-FLIGHT GATE│   │
│  │  4.  presets.deep_merge_preset(preset_data, spec_dict)  ← OPTIONAL│   │
│  │  5.  _resolve_forges(spec.character)                                │   │
│  │  6.  Serialize spec_dict + forge_config → JSON                     │   │
│  │  7.  blender_bridge.runner.run_blender_script(build_avatar.py)     │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─ BLENDER (inside subprocess) ──────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Step 0:  Enable VRM add-on                                        │   │
│  │  Step 1:  Clear scene                                               │   │
│  │  Step 2:  Import base mesh (MB-Lab or file)                        │   │
│  │  Step 3:  Apply body spec (colors, height, face, hair_color,       │   │
│  │           clothing_tint)                                            │   │
│  │  Step 3a: Create stub bones  ← hamr.rigs.stub_bones                │   │
│  │  Step 3b: Generate hair mesh  ← hamr.hair.mesh                      │   │
│  │  Step 3c: Generate clothing   ← hamr.clothing.mesh                 │   │
│  │  Step 3d: Weight paint all    ← hamr.rigs.weights                   │   │
│  │  Step 3e: Spring bones       ← hamr.rigs.spring_bones               │   │
│  │  Step 3f: First-person ann.  ← hamr.export.first_person             │   │
│  │  Step 4:  VRM humanoid bone mapping (with stub bone merge)         │   │
│  │  Step 5:  VRM metadata                                              │   │
│  │  Step 6:  VRM expressions                                           │   │
│  │  Step 7:  VRM lookAt                                               │   │
│  │  Step 8:  Export VRM                                                │   │
│  │  Step 9:  Post-export validation (_validate_vrm)                     │   │
│  │  Step 10: Rig verification ← hamr.rigs.verify (optional)           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─ PYTHON (outside Blender) ─────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  8.  Verify output file exists and is valid glTF                    │   │
│  │  9.  Clean up temp files                                           │   │
│  │  10. Return PipelineResult                                         │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Why This Order?

1. **Stub bones before bone mapping** — The 3 missing VRM bones (jaw, leftEye, rightEye) must exist before `_apply_vrm_humanoid()` tries to map them.  
2. **Hair/clothing before weight paint** — Generated meshes need weights transferred from the body before spring bones reference them.  
3. **Weight paint before spring bones** — Spring bone chains reference vertex groups that must exist first.  
4. **Spring bones before VRM mapping** — The VRM addon reads spring bone configuration from the armature extension.  
5. **First-person before export** — Mesh annotations are written to the VRM extension before the export call.  
6. **Perf budget check is pre-flight** — No point launching Blender if the spec is over budget.  

---

## 5. E2E Test Architecture

### 5.1 The Problem

Blender is not available on CI (GitHub Actions, etc.). The Pi 5 is the primary build machine. We need E2E tests that cover the full pipeline **without requiring a Blender subprocess**.

### 5.2 Strategy: Three Test Tiers

| Tier | Name | Needs Blender? | Runs On | What It Tests |
|------|------|----------------|---------|---------------|
| **T1** | Pure-Python Unit | No | CI + Pi | Each module's pure-Python functions |
| **T2** | Integration Mock | No | CI + Pi | Pipeline orchestration with mocked Blender |
| **T3** | Full Blender E2E | Yes | Pi only | Complete preset → VRM build |

### 5.3 Tier T1: Pure-Python Unit Tests (No Blender)

Each Phase 11 module has pure-Python functions. These are tested normally:

```python
# tests/test_integration_12.py

class TestStubBonesPure:
    """T1: Pure-Python stub bone detection — no Blender needed."""

    def test_detect_missing_bones_mblab(self):
        from hamr.rigs.stub_bones import detect_missing_bones
        existing = {"pelvis", "spine", "head", "neck", ...}
        missing = detect_missing_bones(existing)
        assert "jaw" in missing
        assert "leftEye" in missing
        assert "rightEye" in missing

    def test_compute_stub_position(self):
        from hamr.rigs.stub_bones import compute_stub_position
        pos = compute_stub_position("jaw", (0, 0, 1.7), (0, 0, 1.85))
        assert pos[2] < 1.7  # Jaw should be below head center


class TestHairMeshPure:
    """T1: Pure-Python hair geometry — no Blender needed."""

    def test_generate_guide_curves(self):
        from hamr.hair.mesh import generate_guide_curves
        curves = generate_guide_curves("long_straight")
        assert len(curves) > 0
        assert all(len(c.control_points) >= 2 for c in curves)

    def test_compute_strand_count(self):
        from hamr.hair.mesh import compute_strand_count
        count = compute_strand_count("long_straight", density=1.0)
        assert 50 < count < 8000


class TestClothingMeshPure:
    """T1: Pure-Python clothing pattern resolution."""

    def test_resolve_clothing_pattern(self):
        from hamr.clothing.mesh import resolve_clothing_pattern
        pattern = resolve_clothing_pattern("tshirt")
        assert pattern["display_name"] == "T-Shirt"
        assert "torso" in pattern["body_regions"]

    def test_classify_material_type(self):
        from hamr.clothing.mesh import classify_material_type
        assert classify_material_type("leather jacket") == "leather"
        assert classify_material_type("cotton tshirt") == "fabric"


class TestPerfBudget:
    """T1: Performance budget checks — pure Python."""

    def test_check_budget_within(self):
        from hamr.core.perf import check_budget, PerformanceBudget
        from hamr.core.presets import CHARACTER_PRESETS
        from hamr.core.models import CharacterSpec
        # Build a minimal spec
        spec = CharacterSpec(name="test")
        budget = PerformanceBudget(max_triangles=80000)
        report = check_budget(spec, budget)
        assert report.within_budget

    def test_check_budget_over(self):
        from hamr.core.perf import check_budget, PerformanceBudget
        from hamr.core.models import CharacterSpec
        spec = CharacterSpec(name="test")
        budget = PerformanceBudget(max_triangles=100)  # Way too low
        report = check_budget(spec, budget)
        assert not report.within_budget
        assert len(report.warnings) > 0


class TestFirstPersonPure:
    """T1: First-person mesh classification — no Blender."""

    def test_classify_mesh_for_fp(self):
        from hamr.export.first_person import classify_mesh_for_fp
        assert classify_mesh_for_fp("hair_long") == "thirdPersonOnly"
        assert classify_mesh_for_fp("body_base") == "both"
        assert classify_mesh_for_fp("fp_body_simplified") == "firstPersonOnly"

    def test_configure_first_person_pure(self):
        from hamr.export.first_person import configure_first_person_pure
        config = configure_first_person_pure("body_base", ["skirt_mesh"])
        assert config.mesh_annotations["body_base"] == "both"
        assert config.mesh_annotations["skirt_mesh"] == "both"


class TestSpringBonesPure:
    """T1: Spring bone configuration — no Blender."""

    def test_configure_hair_spring(self):
        from hamr.rigs.spring_bones import configure_hair_spring
        from hamr.core.models import HairPhysicsSpec
        spec = HairPhysicsSpec()
        group = configure_hair_spring(spec)
        assert group.name == "hair_spring"
        assert group.stiff_force > 0

    def test_configure_clothing_spring(self):
        from hamr.rigs.spring_bones import configure_clothing_spring
        group = configure_clothing_spring("test_skirt", "skirt")
        assert "skirt" in group.name.lower() or "spring" in group.name


class TestWeightPaintPure:
    """T1: Weight paint analysis — no Blender."""

    def test_compute_quality_score(self):
        from hamr.rigs.weights import compute_quality_score
        vertex_groups = {
            "spine": [(0, 1.0), (1, 0.5)],
            "chest": [(1, 0.5)],
        }
        score = compute_quality_score(vertex_groups, ["spine", "chest"])
        assert 0.0 <= score <= 1.0

    def test_classify_deformation_quality(self):
        from hamr.rigs.weights import classify_deformation_quality
        assert classify_deformation_quality(0.9) == "excellent"
        assert classify_deformation_quality(0.3) == "poor"
```

### 5.4 Tier T2: Integration Mock Tests (No Blender)

These test the pipeline orchestration with mocked `run_blender_script`:

```python
class TestPipelineIntegration:
    """T2: Pipeline orchestration with mocked Blender."""

    def test_build_with_preset(self, tmp_path):
        """Test that preset merging works before Blender is called."""
        from hamr.core.pipeline import BuildPipeline
        from hamr.core.presets import CHARACTER_PRESETS

        preset = CHARACTER_PRESETS["anime_girl_default"]
        spec_dict = preset["spec"]
        # Verify preset can be parsed
        from hamr.core.models import CharacterSpec
        spec = CharacterSpec.from_dict(spec_dict["spec"] if "spec" in spec_dict else spec_dict)
        assert spec.name  # Preset name exists

    def test_perf_budget_gate(self):
        """Test that over-budget specs are rejected before Blender."""
        from hamr.core.pipeline import BuildPipeline
        from hamr.core.perf import PerformanceBudget
        # This should fail at the budget check, not at Blender launch
        pipeline = BuildPipeline()
        # We can't fully test this without a spec file, but we can
        # verify the budget check logic

    def test_forge_resolution(self):
        """Test that all three forges resolve correctly."""
        from hamr.core.builder import _resolve_forges
        from hamr.core.models import CharacterSpec, HairSpec, FaceSpec, ClothingSpec
        spec = CharacterSpec(
            name="test",
            hair=HairSpec(style="straight", length="long"),
            face=FaceSpec(),
            clothing=[ClothingSpec(type="tshirt", name="school_shirt")],
        )
        config = _resolve_forges(spec)
        assert "hair" in config
        assert "face" in config
        assert "clothing" in config
```

### 5.5 Tier T3: Full Blender E2E (Pi Only)

```python
@pytest.mark.blender
class TestE2EBlender:
    """T3: Full build pipeline end-to-end, requires Blender."""

    def test_build_from_preset_anime_girl(self, tmp_path):
        """Full build: anime_girl_default preset → VRM file."""
        from hamr.core.pipeline import BuildPipeline
        pipeline = BuildPipeline()
        result = pipeline.build(
            spec_path="specs/anime_girl_default.yaml",
            output_dir=str(tmp_path),
        )
        assert result.success
        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 1024

    def test_build_with_hair_clothing(self, tmp_path):
        """Full build with hair mesh and clothing generation."""
        result = pipeline.build(
            spec_path="specs/test_hair_clothing.yaml",
            output_dir=str(tmp_path),
        )
        assert result.success

    def test_build_over_budget_rejected(self, tmp_path):
        """Over-budget spec should be rejected before Blender."""
        from hamr.core.perf import PerformanceBudget
        pipeline = BuildPipeline()
        # Use an intentionally over-complex spec
        result = pipeline.build(
            spec_path="specs/over_budget.yaml",
            output_dir=str(tmp_path),
        )
        # Should fail at budget check, not at Blender
        assert not result.success
        assert any("budget" in e.lower() for e in result.errors)
```

The `@pytest.mark.blender` marker allows CI to skip T3 tests:
```python
# conftest.py
import pytest

def pytest_collection_modifyitems(config, items):
    skip_blender = pytest.mark.skip(reason="Blender not available on CI")
    for item in items:
        if "blender" in item.keywords:
            item.add_marker(skip_blender)
```

### 5.6 E2E Spec File

A minimal YAML spec for E2E testing:

```yaml
# specs/test_integration.yaml
name: Integration Test Character
body:
  height_cm: 158
  build: average
  skin:
    base_hex: "#F5D6C3"
hair:
  style: long_straight
  length: shoulder
  color:
    roots: "#C4A265"
    tips: "#F5E6B8"
face:
  jaw: V-shape
  eyes:
    iris_hex: "#4169E1"
clothing:
  - type: tshirt
    name: school_shirt
    primary_hsv: "#FFFFFF"
export:
  format: vrm1
```

---

## 6. New Module Boundaries

### 6.1 New File: `core/pipeline_integrate.py`

A **new module** that contains the integration helpers called from both the CLI and the Blender script. This avoids putting integration logic in either place:

```python
"""
Pipeline Integration Helpers — The bridge between Phase 11 modules and the build pipeline.

Pure-Python functions that prepare forge configs for Blender consumption.
No bpy imports — these run in the orchestration process, not inside Blender.
"""

def prepare_integration_config(spec, forge_config, preset_name=None):
    """
    Assemble the full integration config that build_avatar.py receives as JSON.
    
    Merges:
    - Forge config (hair, face, clothing)
    - Preset overrides (if any)
    - Spring bone config (hair, breast, clothing)
    - First-person mesh classification
    - Performance budget check result
    
    Returns:
        dict with keys: hair, face, clothing, spring_bones, first_person, perf
    """
    ...

def classify_all_meshes_for_fp(mesh_names):
    """
    Pure-Python mesh → first-person annotation classification.
    Used both by the Blender script and by tests.
    """
    ...

def validate_rig_pure(bone_names):
    """
    Pure-Python rig validation from bone name lists.
    No Blender needed.
    """
    ...
```

### 6.2 New File: `tests/test_integration_12.py`

All T1 and T2 tests for Phase 12 integration.

### 6.3 New File: `specs/` directory

Contains YAML spec files for E2E testing:
- `specs/test_integration.yaml` — minimal spec for E2E
- `specs/test_over_budget.yaml` — intentionally over-budget spec
- `specs/anime_girl_default.yaml` — full preset spec

### 6.4 No New Modules in Subpackages

Phase 12 **does not** create new subpackages. It integrates existing Phase 11 modules by:

1. Adding call sites in `scripts/build_avatar.py` (Blender-side)
2. Adding call sites in `core/pipeline.py` (orchestrator-side)
3. Adding call sites in `cli.py` (user-facing)
4. Adding a thin `core/pipeline_integrate.py` helper module

---

## 7. Modification List — Every Existing File That Changes

| File | Change Type | Description |
|------|------------|-------------|
| `src/hamr/scripts/build_avatar.py` | **Major rewrite** | Add Steps 3a–3f, 10. Add `_integrate_stub_bones()`, `_integrate_hair_mesh()`, `_integrate_clothing_meshes()`, `_integrate_weight_paint()`, `_integrate_spring_bones()`, `_integrate_first_person()`, `_verify_rig_post_export()`, `_find_body_mesh()`, `_find_armature()`, `_dict_to_clothing_spec()`. Modify `_apply_vrm_humanoid()` to merge stub bone map. Add `--preset`, `--budget`, `--perf-check` args to `parse_args()`. |
| `src/hamr/core/pipeline.py` | **Add perf gate** | Add `check_budget()` call after `validate_spec()`. Add `--preset` merge logic. Add `--budget` tier selection. Add `--force-over-budget` flag. |
| `src/hamr/cli.py` | **Add commands** | Add `--preset`, `--budget`, `--force-over-budget` args to build_parser. Add `verify-rig` subcommand. Enhance `list-presets` with `--what` arg. |
| `src/hamr/core/__init__.py` | **Add exports** | Export `prepare_integration_config` from `pipeline_integrate`. |
| `src/hamr/__init__.py` | **Bump version** | `__version__ = "0.5.0"`. Add Phase 12 module imports. |
| `src/hamr/rigs/verify.py` | **Add function** | Add `verify_vrm_rig(path: str) -> dict` pure-Python function that reads a VRM/GLB binary and checks bone presence without Blender. |
| `src/hamr/export/vrm.py` | **Minor** | Ensure stub bone names (jaw, leftEye, rightEye) are included in VRM_REQUIRED_BONES (already done via constants module). No code change needed if `VRM_25_BONE_NAMES` from `constants.py` is used. |
| `src/hamr/core/presets.py` | **Add function** | Add `deep_merge_preset(preset_data, spec_dict) -> dict` that deep-merges a CHARACTER_PRESETS entry into a spec dict. |

### New Files

| File | Description |
|------|-------------|
| `src/hamr/core/pipeline_integrate.py` | Integration helpers: config assembly, mesh classification, pure-Python rig validation |
| `tests/test_integration_12.py` | T1 + T2 integration tests (all 556 existing tests still pass) |
| `tests/test_e2e_blender.py` | T3 Blender E2E tests (marked `@pytest.mark.blender`, skipped on CI) |
| `specs/test_integration.yaml` | Minimal E2E test spec |
| `specs/test_over_budget.yaml` | Over-budget test spec |
| `specs/anime_girl_default.yaml` | Full preset spec for E2E |
| `ARCHITECTURE_12.md` | This document |

---

## 8. Dependency Graph

```
core/perf.py ←──── core/pipeline.py ←── cli.py
                     ↑
core/presets.py ──── →  │
                     │
core/pipeline_integrate.py ←── NEW
                     │
                     ├──→ scripts/build_avatar.py
                     │       ├── rigs/stub_bones.py
                     │       ├── hair/mesh.py
                     │       ├── clothing/mesh.py
                     │       ├── rigs/weights.py
                     │       ├── rigs/spring_bones.py
                     │       ├── export/first_person.py
                     │       └── rigs/verify.py
                     │
                     └──→ blender_bridge/runner.py
```

**Key insight**: All Phase 11 modules are **called from inside Blender** (within `build_avatar.py`), except `core/perf.py` which is called **before** Blender launches, in `core/pipeline.py`.

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Blender subprocess hangs during weight paint | `blender_timeout_seconds` hard kill; power-wash scene between attempts |
| Hair mesh generation fails for unknown styles | Fallback to `long_straight`; catch and continue |
| Clothing shrinkwrap fails (no body mesh) | Skip clothing step, log warning, continue |
| Spring bone addon extension not found | Graceful fallback: store config as JSON, apply post-export |
| First-person addon API differs between Blender versions | Try/except with version-specific paths |
| Over-budget spec crashes Blender OOM | Pre-flight budget check prevents Blender launch |
| CI can't run Blender E2E tests | T3 tests marked `@pytest.mark.blender`, skipped on CI |

---

## 10. Success Criteria

Phase 12 is complete when:

- [ ] `hamr build --preset anime_girl_default spec.yaml` produces a valid VRM with stub bones, hair, clothing, weights, spring bones, and first-person annotations
- [ ] `hamr verify-rig output.vrm` reports 25/25 VRM bones mapped
- [ ] `hamr list-presets --what character` shows all 6 character presets
- [ ] `hamr build --budget minimal spec.yaml` rejects an over-budget spec before Blender
- [ ] All 556 existing tests still pass
- [ ] At least 20 new T1/T2 integration tests pass on CI
- [ ] At least 3 T3 E2E Blender tests pass on Pi
- [ ] Performance budget check runs in < 10ms (pure Python, no Blender)
- [ ] Full build from preset → VRM completes in < 45s on Pi 5

---

*The gatekeeper sees all. Every module connected. Every bone accounted for. Every weight smooth. Every spring wound. The forge ships avatars.*

— Rúnhild Svartdóttir, THE ARCHITECT