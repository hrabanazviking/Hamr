# ᚺᚨᛗᚱ — Phase 11: Alvíssmál

> *"Þat kann ek it þretaánda, ef ek á þau scal sæta, / unga manna í åldom scýfa — That I know as thirteenth, if I shall a young warrior / wed, the maid I shall win with skill."*
> — Alvíssmál, St. 35

## Phase Number

**Phase 11** — Version target: `0.4.0`

## Norse Naming Rationale

**Alvíssmál** — "The Song of All-Wise" — is the Eddic poem where the dwarf Alvíss comes to Thor claiming the right to wed Thor's daughter. Thor challenges him to prove his wisdom by naming every thing in every domain of the Nine Worlds. Alvíss answers flawlessly, naming each thing in the tongue of the Æsir, the Vanir, the giants, the elves, the dead, and the gods — until dawn turns him to stone.

This phase is **Alvíssmál** because Hamr must now answer for every gap in its form:

- **Every bone** shall have a name — the 25/25 humanoid bones, including the jaw and eyes MB-Lab lacks
- **Every strand** shall have its place — procedural mesh hair, not just shell configs
- **Every fold** shall drape true — clothing meshes on the body
- **Every vertex** shall move smooth — weight painting that deforms like living skin

If Phase 10 was the Final Quench — the blade cooled, solid, functional — then Phase 11 is the moment the blade earns its name. The quenched sword is steel; the named sword is a weapon. The avatar with 22/25 bones is functional; the avatar with 25/25, hair, clothing, and smooth deformation is *real*.

Alvíss knew the name of everything. By the end of this phase, Hamr will know the name, place, and weight of every bone, strand, and fold.

---

## Goals (Specific, Measurable)

### G1: Complete Bone Mapping — 25/25 Humanoid Bones
- [ ] Work around MB-Lab missing bones (jaw, leftEye, rightEye) by **creating stub bones** in the Blender build script
- [ ] Stub jaw bone: parented to head, positioned at chin vertex average
- [ ] Stub eye bones (L/R): parented to head, positioned at eye vertex centers
- [ ] VRM 1.0 export validates with all 25 required humanoid bones mapped
- [ ] TurboSquid bone map already has all 25 — verify in automated test
- [ ] **Metric**: `test_vrm_has_humanoid_bones` passes with 25/25

### G2: Procedural Mesh Hair System
- [ ] `HairForge` generates procedural mesh hair from spec parameters
- [ ] Support styles: straight, wavy, curly, braided, twin-tails, ponytail, bob, spiky
- [ ] Hair mesh is a separate object parented to the head bone
- [ ] Hair color applies HSV tint from spec (roots → mid → tips gradient)
- [ ] Hair mesh weight-painted to head and upper spine/neck for physics
- [ ] Length parameter: ear, chin, shoulder, mid-back, waist, very-long
- [ ] Volume parameter: thin to thick (0.1–1.0)
- [ ] **Metric**: Generated VRM loads in VRChat with visible hair that follows head movement

### G3: Clothing Mesh Generation
- [ ] `ClothingForge` generates parametric clothing meshes from spec
- [ ] Initial outfits: t-shirt, shorts/skirt, dress, hoodie, school uniform
- [ ] Clothing meshes are separate objects with proper weight painting to body bones
- [ ] Clothing uses body mesh as shrinkwrap target for automatic fitting
- [ ] VRM 1.0 material variants for outfit switching
- [ ] **Metric**: Generated VRM includes at least 1 clothing item with correct deformation

### G4: Weight Painting Improvements
- [ ] Smooth deformations at neck, shoulders, hips, knees, elbows
- [ ] Blender-side weight painting script with automatic vertex group assignment
- [ ] Heat map visualization in build log (weights per vertex group statistics)
- [ ] Minimum 3 vertex groups per joint influence (no 1-bone rigid sections)
- [ ] **Metric**: Test avatar has no	mesh tearing visible at joint extremes

### G5: Auto-Rig Verification Tool
- [ ] `hamr verify-rig <vrm>` CLI command inspects a VRM for rig compliance
- [ ] Checks: humanoid bone count, expression count, lookAt config, spring bones
- [ ] Reports: missing bones, unmapped bones, weight paint quality score
- [ ] Exit code: 0 = compliant, 1 = warnings, 2 = failures
- [ ] **Metric**: `hamr verify-rig` correctly identifies all issues in a test VRM

### G6: UI Presets (VRoid-Style Quick Character Templates)
- [ ] 6 character presets: casual_m, casual_f, student_m, student_f, fantasy_m, fantasy_f
- [ ] Each preset: complete spec with body, face, hair, clothing parameters
- [ ] `hamr build --preset casual_f` generates a character from preset
- [ ] Presets live in `assets/presets/` as YAML files
- [ ] **Metric**: `hamr build --preset casual_f --out avatar.vrm` produces valid VRM in <60s

### G7: Performance Optimizations for Pi
- [ ] Peak memory usage < 1.5 GB during full build on Pi 5
- [ ] Full build (spec → VRM) completes in < 45 seconds on Pi 5
- [ ] Texture generation uses lazy resolution (skip unused texture slots)
- [ ] Blender subprocess timeout guard (120s max, clean exit on timeout)
- [ ] **Metric**: `pytest tests/ -m perf` suite passes on Pi 5 hardware

### G8: VRM 1.0 Spec Compliance Improvements
- [ ] Spring bone groups: at least 1 group for hair
- [ ] First-person annotations: mesh visibility flags per render subset
- [ ] Expression override: blink interval + crossfade timing
- [ ] VRM meta: version, author, contactInformation, referenceInformation
- [ ] **Metric**: Generated VRM passes VRM 1.0 validator with 0 errors

---

## New Modules / Features

### `hamr/rigs/stub_bones.py` — Bone Completion Engine
```python
def create_missing_bones(armature: bpy.types.Object, base_type: str = "mblab") -> dict:
    """
    Create stub bones for VRM 1.0 required humanoid bones that don't
    exist in the base mesh armature (MB-Lab lacks jaw, leftEye, rightEye).

    Strategy:
    - jaw: Create at chin position, parented to head, 0-influence by default
    - leftEye / rightEye: Create at eye center, parented to head, 0.5cm bones
    - All stubs get a '_hamr_stub' custom property so we can identify them

    Returns: dict of {vrm_bone_name: blender_bone_name} for the created stubs
    """
```

### `hamr/hair/forge.py` — HairForge v2 (Mesh Hair)
```python
class HairForge:
    """Procedural mesh hair generation engine."""

    def generate(self, spec: HairSpec, head_mesh: bpy.types.Object,
                 armature: bpy.types.Object) -> bpy.types.Object:
        """Generate mesh hair from spec parameters.

        Style dispatch:
        - straight → straight.generate()
        - wavy → wavy.generate()
        - curly → curly.generate()
        - braided → braided.generate()
        - ponytail → ponytail.generate()
        - twin_tails → twin_tails.generate()
        - bob → bob.generate()
        - spiky → spiky.generate()
        """

    def apply_colors(self, hair_obj: bpy.types.Object, spec: HairSpec) -> None:
        """Apply root→mid→tip gradient via vertex colors or HSV texture."""
```

### `hamr/hair/straight.py` — Straight Hair Generator
- Extrude curves from scalp region
- Convert to mesh with `to_mesh()`
- Apply length/volume parameters

### `hamr/hair/curly.py` — Curly Hair Generator
- Spiral curve generation with curl frequency parameter
- Volume via array + random offset

### `hamr/hair/braided.py` — Braided Hair Generator
- 3-strand braid algorithm on Bezier curves
- Ornament slots for hair accessories

### `hamr/clothing/forge.py` — ClothingForge v1
```python
class ClothingForge:
    """Parametric clothing generation."""

    def generate(self, spec: ClothingSpec, body_mesh: bpy.types.Object,
                 armature: bpy.types.Object) -> bpy.types.Object:
        """Generate clothing mesh from spec.

        Strategy:
        1. Duplicate body mesh regions for clothing coverage
        2. Offset along normals (garment thickness)
        3. Shrinkwrap to body for fitting
        4. Assign clothing material
        5. Weight paint to armature body vertex groups
        """
```

### `hamr/clothing/patterns.py` — Clothing Pattern Library
- tshirt: torso coverage, short sleeves, crew neck
- shorts: waist-to-knee coverage, elastic waistband
- skirt: waist-to-knee a-line, waist seam
- dress: full-length torso + skirt, multiple neckline options
- hoodie: torso + long sleeves + hood
- school_uniform: blazer + skirt/pants + shirt collars

### `hamr/rigs/weights.py` — Weight Painting Engine
```python
class WeightPaintEngine:
    """Automatic weight painting for smooth deformations."""

    def paint_smooth(self, obj: bpy.types.Object, armature: bpy.types.Object,
                     regions: list[str] = None) -> None:
        """Apply smooth weight painting to specified regions.

        Uses Blender's automatic weights as base, then:
        1. Smooth weights at joint boundaries
        2. Ensure 3+ vertex groups influence each boundary vertex
        3. Normalize all vertex groups to sum to 1.0
        4. Apply max_influence limits to prevent single-bone rigidity
        """

    def get_quality_score(self, obj: bpy.types.Object) -> float:
        """Score weight paint quality (0.0–1.0) based on:
        - Minimum vertex group count per vertex
        - Smoothness at joint boundaries
        - Normalization compliance
        """
```

### `hamr/rigs/verify.py` — Rig Verification Tool
```python
class RigVerifier:
    """Verify VRM rig compliance."""

    def verify(self, vrm_path: Path) -> RigReport:
        """Check a VRM file for rig compliance.

        Returns RigReport with:
        - humanoid_bone_count: expected 25
        - missing_bones: list of missing VRM bone names
        - expression_count: number of VRM expressions
        - lookAt_config: bone rotation or morph target
        - spring_bone_groups: count and names
        - first_person_annotations: present/absent
        - weight_paint_score: 0.0-1.0 quality estimate
        """

    def to_cli(self, report: RigReport) -> str:
        """Format report for terminal output with colors and symbols."""
```

### `hamr/cli/verify_rig.py` — CLI Command
```bash
hamr verify-rig avatar.vrm           # Full rig verification
hamr verify-rig avatar.vrm --json    # JSON output for agents
hamr verify-rig avatar.vrm --quiet   # Exit code only (0/1/2)
```

### `assets/presets/` — Quick Character Presets
```yaml
# assets/presets/casual_f.yaml
name: Casual Female
version: "1.0"
body:
  height_cm: 163
  build: average
  skin:
    base_hex: "#F5D0B0"
face:
  eyes:
    iris_hex: "#4169E1"
    shape: round
    size: 1.0
hair:
  style: wavy
  length: shoulder
  volume: 0.6
  color:
    roots: "#8B6914"
    tips: "#D4A940"
clothing:
  - type: tshirt
    color_hex: "#FFFFFF"
  - type: shorts
    color_hex: "#4A6A8A"
export:
  format: vrm1
  title: Casual Female
  author: Hamr Forge
```

---

## Architecture Decisions

### AD-11.1: Stub Bone Strategy for MB-Lab Completion
**Decision**: Create micro-stub bones in Blender at runtime rather than modifying MB-Lab's armature directly.

**Rationale**: MB-Lab's armature is generated by its internal code and should not be patched. Instead, we inject stub bones into the armature after MB-Lab generates the character. Stubs are:
- 0.5cm length, parented to `head`
- Tagged with `["_hamr_stub"] = True` custom property
- Zero influence on mesh by default (manual weight painting assigns influence only where needed)
- Visible in VRM as valid humanoid bones

This keeps MB-Lab's rig intact while achieving VRM 1.0 compliance.

### AD-11.2: Curve-to-Mesh Hair Pipeline
**Decision**: Generate hair as Bezier curves first, then convert to mesh. Do not use particle systems.

**Rationale**: Particle systems are GPU-dependent, slow on headless, and hard to control procedurally. Bezier curves give us:
- Deterministic results (same spec → same hair, every time)
- Easy length/volume parameters
- Clean vertex color gradient for root→tip coloring
- Fast conversion to mesh for VRM export
- Pi-compatible (no GPU required)

The pipeline: `HairSpec → guide_curves() → style_modifier() → to_mesh() → vertex_colors() → parent_to_head()`

### AD-11.3: Shrinkwrap Clothing Fit
**Decision**: Generate clothing by duplicating body mesh regions and offsetting along normals, then shrinkwrapping to body.

**Rationale**: This is how VRoid and most game character pipelines work. The shrinkwrap modifier:
- Automatically conforms clothing to body shape
- Handles different body builds without manual per-vertex adjustment
- Is computed by Blender's modifier stack (fast, deterministic)
- Can be applied (baked) before export for clean VRM output

The pipeline: `ClothingSpec → region_select(body) → separate → offset → shrinkwrap → material_assign → weight_paint_copy`

### AD-11.4: Weight Paint Quality Score
**Decision**: Weight paint quality is scored 0.0–1.0 and must exceed 0.7 for a passing build.

**Rationale**: VRChat and Resonite expect smooth deformations. Rigid regions (1-bone influence) cause mesh tearing. The score checks:
- `avg_groups_per_vertex >= 2.0` (no rigid single influences at joints)
- `max_weight_variance < 0.3` (smooth transitions)
- `normalization_rate >= 0.95` (95% of vertices sum to 1.0)

### AD-11.5: Preset-Driven Development
**Decision**: Every feature must be demonstrable via a preset. No feature ships without a YAML preset that exercises it.

**Rationale**: Presets are our integration tests. If `hamr build --preset casual_f` doesn't produce a valid VRM, the feature isn't done. This enforces end-to-end discipline and gives agents a clear API.

### AD-11.6: Pi Performance Budget
**Decision**: Hard performance budget — full build under 45s, peak memory under 1.5 GB on Pi 5.

**Rationale**: If Hamr can't run on a Pi 5, it can't run headlessly on small servers. The budget forces:
- Lazy texture generation (only create textures the spec requests)
- Blender subprocess timeout guard
- Mesh decimation options for hair density
- No Cycles rendering — everything is viewport/Eevee or Pillow-based

---

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| SC-1 | **25/25 humanoid bones mapped** | `hamr verify-rig` reports 25/25 humanoid bones, 0 missing |
| SC-2 | **Mesh hair generates from spec** | `HairForge.generate()` produces a mesh visible in VRM export |
| SC-3 | **At least 4 hair styles** | straight, wavy, curly, bob generate distinct meshes |
| SC-4 | **Clothing mesh fits body** | 1 clothing item (t-shirt) generates and deforms with armature |
| SC-5 | **Weight paint score ≥ 0.7** | `WeightPaintEngine.get_quality_score()` returns ≥ 0.7 on generated avatar |
| SC-6 | **Rig verification CLI works** | `hamr verify-rig <vrm>` exits 0 on compliant VRM, 1 on warnings, 2 on failures |
| SC-7 | **6 presets build to valid VRM** | All 6 presets produce VRM that loads in VRChat |
| SC-8 | **Pi 5 build under 45s** | `time hamr build --preset casual_f` < 45s on Pi 5 |
| SC-9 | **Pi 5 memory under 1.5 GB** | Peak RSS < 1.5 GB during build |
| SC-10 | **Test count ≥ 200** | `pytest tests/` reports ≥ 200 passing tests |
| SC-11 | **VRM 1.0 validator 0 errors** | Generated VRM passes VRM 1.0 validator |
| SC-12 | **Spring bones for hair** | VRM contains ≥ 1 spring bone group affecting hair mesh |

---

## Phase Lineage

| Phase | Name | Version | What It Forged |
|-------|------|---------|---------------|
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
| **11** | **Alvíssmál** | **0.4.0** | **25/25 bones, mesh hair, clothing, weight paint, presets, Pi performance** |

---

## Task Breakdown (Priority Order)

### T1: Stub Bone Creation (AD-11.1, G1, SC-1)
- [ ] Implement `hamr/rigs/stub_bones.py` with `create_missing_bones()`
- [ ] Update `MB_LAB_BONE_MAP` to include jaw, leftEye, rightEye
- [ ] Integration test: VRM export with 25/25 humanoid bones
- [ ] Edge case: TurboSquid map already has all 25 — verify no regression

### T2: Hair Curve Engine (AD-11.2, G2, SC-2/3)
- [ ] Implement `HairForge.generate()` dispatch router
- [ ] Implement `straight.py` — straight hair from scalp curves
- [ ] Implement `wavy.py` — wavy hair with sine wave displacement
- [ ] Implement `curly.py` — curly hair with spiral curve generation
- [ ] Implement `bob.py` — bob cut variant
- [ ] Root-to-tip vertex color gradient
- [ ] Parent hair mesh to head bone
- [ ] Hair length and volume parameters

### T3: Clothing Mesh Generation (AD-11.3, G3, SC-4)
- [ ] Implement `ClothingForge.generate()` with shrinkwrap strategy
- [ ] Implement t-shirt pattern
- [ ] Implement shorts pattern
- [ ] Weight paint copy from body to clothing
- [ ] Clothing material assignment

### T4: Weight Paint Engine (AD-11.4, G4, SC-5)
- [ ] Implement `WeightPaintEngine.paint_smooth()`
- [ ] Implement `WeightPaintEngine.get_quality_score()`
- [ ] Boundary smoothing at neck, shoulders, hips, knees, elbows
- [ ] Normalize all vertex groups

### T5: Rig Verification Tool (G5, SC-6)
- [ ] Implement `RigVerifier.verify()` for VRM files
- [ ] CLI: `hamr verify-rig` command
- [ ] JSON output mode for agent consumption
- [ ] Exit codes: 0=compliant, 1=warnings, 2=failures

### T6: Character Presets (AD-11.5, G6, SC-7)
- [ ] casual_m.yaml
- [ ] casual_f.yaml
- [ ] student_m.yaml
- [ ] student_f.yaml
- [ ] fantasy_m.yaml
- [ ] fantasy_f.yaml
- [ ] CLI: `hamr build --preset <name>` integration
- [ ] End-to-end test: each preset builds to valid VRM

### T7: Pi Performance (AD-11.6, G7, SC-8/9)
- [ ] Profile full build pipeline on Pi 5
- [ ] Lazy texture generation (skip unused slots)
- [ ] Blender subprocess timeout guard (120s)
- [ ] Hair mesh decimation options
- [ ] Memory profiling and optimization
- [ ] Performance test suite (`pytest tests/ -m perf`)

### T8: VRM 1.0 Compliance (G8, SC-11/12)
- [ ] Spring bone groups for hair
- [ ] First-person mesh annotations
- [ ] Expression blink timing
- [ ] VRM meta population
- [ ] Validator pass with 0 errors

---

*The dwarf who knew all names was turned to stone by dawn. But the names remain — every bone, every strand, every fold. Hamr learns them all.*

ᚺᚨᛗᚱ — Phase 11: Alvíssmál — *All-Wise, All-Formed*