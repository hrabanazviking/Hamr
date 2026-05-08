# ᚺᚨᛗᚱ — Phase 12: Yggdrasil

> *"Þrjár rœtrir standa á þrím vegum undan aski Yggdrasils; / Hel býr í einni, annarri hrímþursa, / þriðju manni menn moldar."
> — Three roots stand on three ways under Yggdrasil's ash; / Hel lives under one, frost-giants under another, / under the third, the humans of the earth.*
> — Gylfaginning, St. 15

## Phase Number

**Phase 12** — Version target: `0.5.0`

## Norse Naming Rationale

**Yggdrasil** — The World Tree, the axis that binds all Nine Worlds into one living system.

Yggdrasil is not a forge. It is not a weapon. It is the **binding** — the structure through which every realm, every root, every branch draws from the same source and bears the weight of the whole. Its three roots drink from three wells (Urðr, Mímir, Hvergelmir). Its canopy shelters the hawk Veðrfölnir. The squirrel Ratatoskr carries messages between root and crown. The Norns water it daily. Remove Yggdrasil, and the Nine Worlds drift apart into chaos.

**This is Phase 12.**

Phases 7–11 forged the pieces in separate fires — bones in one hearth, hair in another, clothing in a third, weight paint in a fourth. Each forge produced working metal. But a sword is not made of separate blades. A body is not made of separate organs floating in void. **They must be bound to one trunk.**

The **trunk** is `build_avatar.py` — the Blender-side script that must now call every module we forged: stub bones, hair mesh, clothing mesh, weight paint, spring bones, first-person, performance budgets, presets. Today, `build_avatar.py` is 945 lines of metal that imports nothing from Phase 11. It clears the scene, loads MB-Lab, applies colors and bone maps, and exports. It does not grow hair. It does not dress the body. It does not smooth the joints. It does not verify its own bone count. It is a trunk without branches.

Phase 11 was **Alvíssmál** — the dwarf who knew every name. He named every bone, every strand, every fold. Phase 12 is **Yggdrasil** — the tree where every name dissolves into one living system. The roots draw from specs and presets. The trunk channels the pipeline. The branches bear VRM output. Every leaf is a test. And like the Norns who tend the tree daily, our integration test suite must run every day on the Pi 5 that tends this garden.

*Þat er Yggdrasils askr, er er öllum meiri ok miklu. Þar er askrinn, er er öllum öðrum trjám mestr. Þar ráða þing öll ogthing Motors — wait. Wrong continent. They say the tree will shake at Ragnarök. But first, the branches must be grafted.*

---

## The Integration Gap (Diagnosis)

Examination of `src/hamr/scripts/build_avatar.py` (945 lines) reveals it does **not** call any Phase 11 module:

| Phase 11 Module | File | Lines | Called in build_avatar.py? |
|-----------------|------|-------|---------------------------|
| `stub_bones.create_missing_bones()` | `rigs/stub_bones.py` | 418 | ❌ No |
| `HairForge.generate()` | `hair/mesh.py` | 752 | ❌ No |
| `ClothingForge.generate()` | `clothing/mesh.py` | 726 | ❌ No |
| `WeightPaintEngine.paint_smooth()` | `rigs/weights.py` | 652 | ❌ No |
| `WeightPaintEngine.get_quality_score()` | `rigs/weights.py` | — | ❌ No |
| `RigVerifier.verify()` | `rigs/verify.py` | 574 | ❌ No |
| `create_spring_bones()` | `rigs/spring_bones.py` | 478 | ❌ No |
| `FirstPersonAnnotator` | `export/first_person.py` | 305 | ❌ No |
| `PerfBudget` / `PerfTracker` | `core/perf.py` | 460 | ❌ No |
| `PresetLoader` | `core/presets.py` | 722 | ❌ No |

The `builder.py` (233 lines) resolves forges from Phase 7 code and sends a JSON blob to Blender. But the Blender script only applies colors, height, expressions, bone maps, and lookAt. **No hair grows. No clothing drapes. No weight paint smooths. No spring bone bounces.**

Yggdrasil's roots are deep but its trunk is hollow. This phase grafts every branch.

---

## Goals (Specific, Measurable)

### G1: Unified Build Pipeline — The Trunk at Full Sap
- [ ] `build_avatar.py` calls all Phase 11 modules in the correct order
- [ ] Build pipeline order: scene clear → MB-Lab → stub bones → hair mesh → clothing mesh → weight paint → spring bones → first-person annotations → VRM export → verification
- [ ] `PresetLoader` integrates into `builder.py` so `hamr build --preset <name>` flows through the entire pipeline
- [ ] `PerfBudget` checks run at the start and end of the build pipeline
- [ ] **Metric**: `hamr build --preset casual_f --output output/test.vrm` completes successfully on Pi 5

### G2: End-to-End VRM Integration Test — The Root Drinks
- [ ] Integration test: YAML preset → `BuildPipeline.build()` → VRM file → `RigVerifier.verify()`
- [ ] Test covers: stub bones (25/25), hair mesh generation, clothing mesh generation, weight paint quality, spring bone groups, first-person annotations
- [ ] Pi 5 timing test: full build completes in < 45 seconds
- [ ] Pi 5 memory test: peak RSS < 1.5 GB during build
- [ ] **Metric**: `pytest tests/ -m e2e` passes with a generated VRM that loads in a VRM validator

### G3: Material System — Skin, Eyes, Hair
- [ ] `MaterialForge` creates Principled BSDF materials with SSS approximation for skin
- [ ] Eye materials with refraction/fake SSS iris shader
- [ ] Hair materials with anisotropic highlight approximation (no Cycles — Eevee-compatible)
- [ ] Material assignment integrates into `build_avatar.py` after mesh generation
- [ ] **Metric**: Generated VRM has distinct skin, eye, and hair materials in VRM viewer

### G4: Facial Expression Blend Shapes — MB-Lab → VRM Binding
- [ ] Discover MB-Lab shape keys from the generated mesh
- [ ] Bind 6 VRM expression presets (happy, angry, sad, surprised, neutral, blink) to shape keys
- [ ] Blend weights respect the existing `MB_LAB_EXPRESSION_MAP` in `build_avatar.py`
- [ ] Expression discovery is automatic — no manual shape key names in config
- [ ] **Metric**: `hamr verify-rig` reports ≥ 6 expressions on generated VRM

### G5: Collision Mesh Generation — Spring Bone Colliders
- [ ] `CollisionForge` generates simplified collision meshes from body mesh regions
- [ ] Head collision sphere for hair spring bones
- [ ] Body collision capsule for clothing spring bones
- [ ] Collision groups integrate with `create_spring_bones()` for VRM 1.0 collider groups
- [ ] **Metric**: Generated VRM contains ≥ 1 spring bone collider group with reference to body mesh

### G6: CLI Exposure — Commands for Every Module
- [ ] `hamr build --preset <name>` — full pipeline with preset
- [ ] `hamr build --spec <file>` — full pipeline with custom spec
- [ ] `hamr verify-rig <vrm>` — rig compliance check (existing, verify it works end-to-end)
- [ ] `hamr check-env` — environment check with Phase 11 module detection
- [ ] `--verbose` / `--json` output flags for all commands
- [ ] **Metric**: All CLI commands have `--help` text and integration test coverage

---

## New Modules / Integrations

### T1: Unified Build Pipeline Rewrite (G1, G2) — **CRITICAL PATH**

This is the core integration task. The build script must become the trunk of Yggdrasil.

**`src/hamr/scripts/build_avatar.py`** — Rewritten pipeline stages:

```python
def main() -> int:
    """Main build pipeline — runs inside Blender. The trunk of Yggdrasil."""
    # Stage 0: Enable VRM add-on
    # Stage 1: Clear scene
    # Stage 2: Import base mesh (MB-Lab or custom)
    # Stage 3: Create stub bones (Phase 11 — NEW)
    # Stage 4: Generate hair mesh (Phase 11 — NEW)
    # Stage 5: Generate clothing mesh (Phase 11 — NEW)
    # Stage 6: Apply weight paint smoothing (Phase 11 — NEW)
    # Stage 7: Assign materials (Phase 12 — NEW)
    # Stage 8: Create spring bone groups (Phase 11 — NEW)
    # Stage 9: Create collision groups (Phase 12 — NEW)
    # Stage 10: First-person annotations (Phase 11 — NEW)
    # Stage 11: VRM bone mapping + expressions + lookAt
    # Stage 12: VRM export
    # Stage 13: Post-export verification
```

Each stage logs its entry/exit and accumulated timing. If any stage fails, the pipeline reports which module failed and continues (or halts for critical stages).

**`src/hamr/core/pipeline.py`** — Updated to inject preset data:

```python
# New: PresetLoader integration
from hamr.core.presets import PresetLoader

def build(self, spec_path, output_dir, format="vrm", base_mesh=None, validate=True, max_tex=0, preset=None):
    # If preset requested, deep-merge preset spec with user spec
    if preset:
        loader = PresetLoader()
        spec = loader.load(preset)
        # Deep merge user overrides on top of preset
```

### T2: Material Forge (G3)

**`src/hamr/materials/forge.py`** — New module:

```python
class MaterialForge:
    """Generate and assign materials for VRM export."""

    def create_skin_material(self, spec: SkinSpec) -> bpy.types.Material:
        """Create skin material with SSS approximation (Eevee-compatible).
        Uses Principled BSDF with:
        - Subsurface scattering radius for skin tones
        - Subsurface weight/tint from spec
        - Roughness 0.4-0.6 for realistic skin
        """

    def create_eye_material(self, spec: EyeSpec) -> bpy.types.Material:
        """Create eye material with refraction/fake SSS.
        - Cornea: slightly transparent, IOR 1.38
        - Iris: HSV-tinted, anisotropic highlight
        - Sclera: off-white, subtle subsurface
        """

    def create_hair_material(self, spec: HairSpec) -> bpy.types.Material:
        """Create hair material with anisotropic highlight.
        - Separated specular layer (Eevee-compatible)
        - Root-to-tip gradient via vertex colors
        - No Cycles — all Eevee/viewport rendering
        """

    def create_clothing_material(self, spec: ClothingSpec) -> bpy.types.Material:
        """Create clothing material from spec properties.
        - Roughness/metallic from spec
        - HSV tint from spec color
        - Fabric normal map approximation
        """

    def assign_materials(self, body_obj, hair_obj, clothing_objs, spec) -> None:
        """Assign materials to all meshes in the scene based on mesh classification."""
```

### T3: Expression Discovery Engine (G4)

**`src/hamr/face/expressions.py`** — New module:

```python
class ExpressionDiscovery:
    """Automatically discover and bind shape keys to VRM expressions."""

    def discover_shape_keys(self, mesh_obj: bpy.types.Object) -> dict[str, list[str]]:
        """Find all shape keys and categorize them by expression type.
        Searches for MB-Lab expressions (Expressions_ prefix)
        and TurboSquid expressions (standard names).
        Returns: {expression_type: [shape_key_names]}
        """

    def bind_expressions(self, armature, mesh_objects, spec_expr_map=None) -> int:
        """Bind discovered shape keys to VRM 1.0 expression presets.
        Uses the existing MB_LAB_EXPRESSION_MAP and TURBOSQUID_EXPRESSION_MAP
        as fallback maps, but discovers actual available shape keys first.
        Returns count of bindings created.
        """

    def validate_expressions(self, vrm_path: Path) -> dict:
        """Verify expression count and names in exported VRM."""
```

### T4: Collision Mesh Generation (G5)

**`src/hamr/rigs/colliders.py`** — New module:

```python
class CollisionForge:
    """Generate collision meshes and collider groups for spring bones."""

    def create_head_collider(self, head_mesh: bpy.types.Object) -> dict:
        """Create a spherical collider from head bounding geometry.
        Uses head bone + mesh extent to define collision sphere.
        Returns collider config dict for spring bone reference.
        """

    def create_body_capsule_colliders(self, body_mesh: bpy.types.Object,
                                       armature: bpy.types.Object) -> list[dict]:
        """Create capsule colliders along the spine and limbs.
        One capsule per major body region: chest, waist, hips.
        Returns list of collider configs.
        """

    def register_collider_groups(self, spring_config: dict,
                                  colliders: list[dict]) -> dict:
        """Register collider groups with spring bone configuration.
        Links colliders to the spring bone groups they affect.
        """
```

### T5: CLI Enhancement (G6)

**`src/hamr/cli.py`** — Updated commands:

```bash
# Build with preset (full pipeline)
hamr build --preset casual_f --output output/avatar.vrm

# Build with custom spec (full pipeline)
hamr build --spec character.yaml --output output/avatar.vrm

# Verify rig compliance
hamr verify-rig output/avatar.vrm --json

# Check environment (with Phase 11 module detection)
hamr check-env --verbose

# List available presets
hamr list-presets --verbose

# Version info
hamr version
```

All commands support `--json` output for machine parsing and `--verbose` for human-readable progress.

### T6: Integration Test Suite (G2)

**`tests/test_e2e_pipeline.py`** — New integration test file:

```python
class TestEndToEndPipeline:
    """Full pipeline tests: preset → VRM → verification."""

    def test_casual_f_builds_to_vrm(self):
        """casual_f preset produces a valid VRM file."""

    def test_casual_m_builds_to_vrm(self):
        """casual_m preset produces a valid VRM file."""

    def test_all_presets_build(self):
        """All 6 presets build to valid VRM."""

    def test_vrm_has_25_bones(self):
        """Generated VRM maps all 25 humanoid bones."""

    def test_vrm_has_hair_mesh(self):
        """Generated VRM contains a hair mesh object."""

    def test_vrm_has_clothing(self):
        """Generated VRM contains at least 1 clothing mesh."""

    def test_vrm_has_spring_bones(self):
        """Generated VRM has ≥ 1 spring bone group."""

    def test_vrm_has_expressions(self):
        """Generated VRM has ≥ 6 expression presets."""

    def test_vrm_has_first_person(self):
        """Generated VRM has first-person annotations."""

    def test_weight_paint_quality(self):
        """Weight paint quality score ≥ 0.7 on generated avatar."""

    def test_perf_budget_under_45s(self):
        """Full build completes in < 45s on Pi 5."""

    def test_perf_memory_under_1_5gb(self):
        """Peak RSS < 1.5 GB during build."""
```

These tests require Blender and are marked with `@pytest.mark.blender` and `@pytest.mark.e2e`.

---

## Architecture Decisions

### AD-12.1: Build Pipeline as Sequential Stages (The Trunk)

**Decision**: `build_avatar.py` is the single trunk of Yggdrasil. Every module is a branch grafted onto this trunk in a fixed sequence.

**Rationale**: The current `build_avatar.py` is a monolithic function with helper functions. Phase 11 modules exist but are not called. Rather than adding ad-hoc calls, we restructure the pipeline into **explicit numbered stages** with consistent error handling and timing:

1. **Stage 0**: Enable add-ons (VRM, MB-Lab)
2. **Stage 1**: Clear scene
3. **Stage 2**: Import/generate base mesh
4. **Stage 3**: Create stub bones (rigs/stub_bones)
5. **Stage 4**: Generate hair mesh (hair/mesh)
6. **Stage 5**: Generate clothing mesh (clothing/mesh)
7. **Stage 6**: Smooth weight paint (rigs/weights)
8. **Stage 7**: Assign materials (materials/forge) — NEW
9. **Stage 8**: Create spring bone groups (rigs/spring_bones)
10. **Stage 9**: Create collision groups (rigs/colliders) — NEW
11. **Stage 10**: First-person annotations (export/first_person)
12. **Stage 11**: VRM mapping + expressions + lookAt
13. **Stage 12**: Export VRM
14. **Stage 13**: Post-export verification

Each stage logs its entry, catches its own exceptions, and reports timing. The trunk accumulates a stage-by-stage timing report.

This makes it possible to:
- Skip stages for testing (`--skip-stages hair,clothing`)
- Profile individual stages on Pi 5
- Diagnose which module fails when a build breaks
- Run stages over CLI for debugging

### AD-12.2: Material System via Principled BSDF (Eevee-Only)

**Decision**: All materials use Principled BSDF with Eevee-compatible features only. No Cycles nodes, no ray-traced SSS.

**Rationale**: Hamr runs on a Pi 5 with Blender in headless mode. Cycles rendering is not available. Eevee subsurface scattering (via the Subsurface value on Principled BSDF) provides a visually acceptable SSS approximation for anime-style avatars. The formula:

- **Skin**: Subsurface Weight 0.15–0.3, Subsurface Scale 0.1–0.5, Subsurface Radius derived from skin tone
- **Eyes**: Cornea transparency via alpha blend, iris via HSV tint, fake reflection via specular map
- **Hair**: Anisotropic highlight via tangent map approximation (Eevee's "Clearcoat" + "Sheen" inputs), root-to-tip gradient via vertex colors

This gives 80% of the visual quality at 5% of the computational cost.

### AD-12.3: Expression Discovery, Not Hardcoding

**Decision**: Expression bindings are discovered at build time from the actual shape keys in the mesh, not hardcoded from a map.

**Rationale**: The existing `MB_LAB_EXPRESSION_MAP` and `TURBOSQUID_EXPRESSION_MAP` are hardcoded maps that assume shape keys exist. But MB-Lab shape keys depend on morph targets that may or may not be finalized, and different base meshes have different shape key names. Phase 12 introduces `ExpressionDiscovery` which:

1. Scans all mesh objects for shape keys
2. Matches them against known patterns (Expressions_ prefix, common names)
3. Falls back to the hardcoded maps for missing bindings
4. Reports what was found vs. what was expected

This makes the pipeline **resilient** to base-mesh variations. The discovery engine is the Norn who reads the roots.

### AD-12.4: Collision Meshes from Body Geometry

**Decision**: Collision meshes are generated from the body mesh's bounding geometry, not from manual configuration.

**Rationale**: Spring bone colliders need collision geometry. For hair, a sphere around the head. For skirts/capes, capsules along the body. Generating these from the body mesh's bounding box is:
- Deterministic (same body → same colliders)
- Automatic (no manual collider placement)
- Pi-compatible (bounding box math, no simulation)

The `CollisionForge` creates:
- Head collider: sphere from head bone position + head mesh extent
- Body colliders: capsules from spine bone chain + body mesh cross-sections
- Links collision groups to spring bone configuration

### AD-12.5: Integration Tests as the Roots

**Decision**: End-to-end integration tests are the roots of Yggdrasil. No module ships without an integration test that exercises it through the full pipeline.

**Rationale**: Phase 11 has 556 unit tests but zero end-to-end pipeline tests that exercise `build_avatar.py` with all modules. This means we have proof that each leaf is green but no proof that the tree stands. Phase 12 adds `tests/test_e2e_pipeline.py` with tests that:
- Use actual presets (casual_f, etc.)
- Run through `BuildPipeline.build()`
- Verify the output VRM with `RigVerifier`
- Measure Pi 5 timing and memory

These are marked `@pytest.mark.e2e` and `@pytest.mark.blender` and can be skipped in CI that lacks Blender.

### AD-12.6: Stage Configuration via Spec (Branches Grow from the Same Root)

**Decision**: Pipeline stages are configurable through the CharacterSpec, not hardcoded flags.

**Rationale**: The same spec that defines hair color and body height should also define whether spring bones are enabled, what collision resolution to use, and which stages to execute. This means the CharacterSpec grows a `pipeline` section:

```yaml
pipeline:
  skip_stages: []       # List of stages to skip
  perf_budget: standard # minimal, standard, full
  spring_bones: true    # Enable spring bone generation
  collision: true       # Enable collision mesh generation
```

Default values preserve current behavior: all stages run, standard perf budget, spring bones enabled.

---

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| SC-1 | **All Phase 11 modules called in build pipeline** | `build_avatar.py` imports and calls `stub_bones`, `HairForge`, `ClothingForge`, `WeightPaintEngine`, spring bones, first-person, `PerfBudget` |
| SC-2 | **Full preset build produces valid VRM** | `hamr build --preset casual_f --output output/casual_f.vrm` succeeds |
| SC-3 | **All 6 presets build to VRM** | All 6 presets produce VRM that loads in VRM viewer |
| SC-4 | **25/25 humanoid bones in generated VRM** | `hamr verify-rig` reports 25/25 on generated VRM |
| SC-5 | **Hair mesh present in VRM** | Generated VRM contains ≥ 1 hair mesh object |
| SC-6 | **Clothing mesh present in VRM** | Generated VRM contains ≥ 1 clothing mesh object |
| SC-7 | **Weight paint quality ≥ 0.7** | `WeightPaintEngine.get_quality_score()` returns ≥ 0.7 |
| SC-8 | **≥ 6 VRM expression presets** | VRM contains happy, angry, sad, surprised, neutral, blink expressions |
| SC-9 | **≥ 1 spring bone collider group** | VRM contains spring bone groups with collision references |
| SC-10 | **Pi 5 build under 45s** | `time hamr build --preset casual_f` < 45s on Pi 5 |
| SC-11 | **Pi 5 memory under 1.5 GB** | Peak RSS < 1.5 GB during build |
| SC-12 | **Materials assigned correctly** | Skin, eye, hair materials have distinct Principled BSDF settings |
| SC-13 | **Integration test suite passes** | `pytest tests/ -m e2e` — full pipeline test suite passes |
| SC-14 | **550+ unit tests still passing** | `pytest tests/` — no regressions |
| SC-15 | **CLI commands work end-to-end** | `hamr build`, `hamr verify-rig`, `hamr check-env` all functional |

---

## Task Breakdown (Priority Order)

### T1: Build Pipeline Integration — The Trunk (G1, G2) — **CRITICAL PATH**
- [ ] Rewrite `build_avatar.py` main flow as explicit numbered stages (AD-12.1)
- [ ] Stage 3: Integrate `stub_bones.create_missing_bones()`
- [ ] Stage 4: Integrate `HairForge.generate()` with spec-driven parameters
- [ ] Stage 5: Integrate `ClothingForge.generate()` with spec-driven parameters
- [ ] Stage 6: Integrate `WeightPaintEngine.paint_smooth()` and `get_quality_score()`
- [ ] Stage 8: Integrate spring bone creation from `rigs/spring_bones.py`
- [ ] Stage 10: Integrate first-person annotations from `export/first_person.py`
- [ ] Add `PerfBudget` tracking at pipeline start and end
- [ ] Wire `PresetLoader` into `pipeline.py` `build()` method
- [ ] Test: `hamr build --preset casual_f` produces VRM with hair, clothing, stub bones, spring bones, first-person

### T2: Expression Discovery Engine (G4)
- [ ] Create `src/hamr/face/expressions.py` with `ExpressionDiscovery`
- [ ] Shape key scanner: discover all shape keys in mesh objects
- [ ] Pattern matcher: categorize shape keys into expression types
- [ ] VRM binder: create expression preset bindings from discovered keys
- [ ] Fallback: use existing `MB_LAB_EXPRESSION_MAP` and `TURBOSQUID_EXPRESSION_MAP`
- [ ] Integration: call in build pipeline Stage 11 (expressions)
- [ ] Verify: `hamr verify-rig` reports ≥ 6 expressions

### T3: Material Forge (G3)
- [ ] Create `src/hamr/materials/` package with `__init__.py` and `forge.py`
- [ ] Implement `MaterialForge.create_skin_material()` with SSS approximation
- [ ] Implement `MaterialForge.create_eye_material()` with refraction
- [ ] Implement `MaterialForge.create_hair_material()` with anisotropic highlight
- [ ] Implement `MaterialForge.create_clothing_material()` from spec
- [ ] Implement `MaterialForge.assign_materials()` for scene-wide assignment
- [ ] Integration: call in build pipeline Stage 7 (materials)
- [ ] Verify: distinct materials in VRM viewer

### T4: Collision Mesh Generation (G5)
- [ ] Create `src/hamr/rigs/colliders.py` with `CollisionForge`
- [ ] Implement `CollisionForge.create_head_collider()` from head mesh bounds
- [ ] Implement `CollisionForge.create_body_capsule_colliders()` from spine chain
- [ ] Implement `CollisionForge.register_collider_groups()` linking to spring bones
- [ ] Integration: call in build pipeline Stage 9 (collisions)
- [ ] Verify: spring bone collider groups in generated VRM

### T5: CLI Enhancement (G6)
- [ ] `hamr build --preset <name>` — full pipeline with preset
- [ ] `hamr build --spec <file>` — full pipeline with custom spec
- [ ] `hamr verify-rig <vrm>` — verify end-to-end integration
- [ ] `hamr check-env` — detect Phase 11 modules
- [ ] `--json` and `--verbose` flags for all commands
- [ ] `--skip-stages` flag for build (AD-12.1)

### T6: Integration Test Suite (G2)
- [ ] Create `tests/test_e2e_pipeline.py` with full pipeline tests
- [ ] Test: all 6 presets build to valid VRM
- [ ] Test: 25/25 bones in generated VRM
- [ ] Test: hair mesh present
- [ ] Test: clothing mesh present
- [ ] Test: spring bone groups present
- [ ] Test: expressions present (≥ 6)
- [ ] Test: weight paint quality ≥ 0.7
- [ ] Test: first-person annotations present
- [ ] Test: Pi 5 timing < 45s
- [ ] Test: Pi 5 memory < 1.5 GB
- [ ] Mark all with `@pytest.mark.e2e` and `@pytest.mark.blender`

### T7: Pipeline Stage Configuration (AD-12.6)
- [ ] Extend `CharacterSpec` with `pipeline` section
- [ ] Allow `skip_stages`, `perf_budget`, `spring_bones`, `collision` config
- [ ] Wire pipeline configuration into `build_avatar.py` stage dispatch
- [ ] Default values preserve current behavior
- [ ] Verify: `--skip-stages hair,clothing` skips stages 4 and 5

---

## Phase Lineage

| Phase | Name | Version | What It Forged |
|-------|------|---------|----------------|
| 1 | The Spec | 0.1.0 | CharacterSpec, YAML, 13 tests |
| 2 | Form | 0.1.0 | Blender Bridge, Texture Forge, Body Forge, Export Forge |
| 3 | The Quench | 0.2.0 | Full Blender pipeline, MB-Lab bone maps, expressions, VRM export |
| 4 | Tempering | 0.3.0 | BuildPipeline, CLI, presets, metadata |
| 5 | Sharpening | 0.3.0 | E2E integration, Blender validation, environment checks |
| 6 | Polishing | 0.3.0 | README, LICENSE, CONTRIBUTING, CHANGELOG |
| 7 | Three Forges | 0.3.0 | Hair, Face, Clothing module stubs |
| 8 | Sacred Fire | 0.3.0 | E2E VRM build pipeline |
| 9 | The Awakening | 0.3.0 | VRM generation integration tests |
| 10 | The Final Quench | 0.3.0 | 156 tests, 22/25 bones, 13 expressions |
| 11 | Alvíssmál | 0.4.0 | 25/25 bones, mesh hair, clothing, weight paint, presets, Pi performance |
| **12** | **Yggdrasil** | **0.5.0** | **Unified pipeline, material forge, expressions, colliders, E2E integration** |

---

## Module Map — New Files

| Module | File | Purpose |
|--------|------|---------|
| Material Forge | `src/hamr/materials/forge.py` | Skin SSS, eye refraction, hair anisotropic, clothing materials |
| Material Init | `src/hamr/materials/__init__.py` | Package exports |
| Expression Discovery | `src/hamr/face/expressions.py` | Auto-discover shape keys → VRM expression bindings |
| Collision Forge | `src/hamr/rigs/colliders.py` | Spring bone collision meshes from body geometry |
| E2E Tests | `tests/test_e2e_pipeline.py` | Full pipeline integration tests |

**Updated**: `src/hamr/scripts/build_avatar.py` — Rewritten with explicit stage pipeline (AD-12.1)
**Updated**: `src/hamr/core/pipeline.py` — PresetLoader integration, stage configuration
**Updated**: `src/hamr/core/models.py` — Pipeline configuration in CharacterSpec
**Updated**: `src/hamr/cli.py` — New commands and flags

---

*Three roots drink from three wells. Nine worlds hang from branches. One trunk channels them all. The Norns tend Yggdrasil every day — and so shall our tests tend this pipeline, every run.*

*Phase 11 gave every piece its name. Phase 12 gives every name its place in the tree.*

*ᚺᚨᛗᚱ — Phase 12: Yggdrasil — The Binding of Worlds*