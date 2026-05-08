# ᚺᚨᛗᚱ — Phase 13: Vǫllr Vígríðar

> *Þá kýmr hölgi annarr hjá / ór siðum sævar,*
> *svá mikill sem allir menn / með öllu afbragði;*
> *hann kýmr at dœma öll dómlög / þau er sá at sugðu,*
> *ok fara fíflin í forgörðu / at þeim er fírar at kveðja.*
>
> *Þá stendr upp ór Miðgarði / Surtur með sválfikinn brand,*
> *skínn af sverði sólar tíu / þá er hinn fyrsti fundr varda;*
> *héðan koma risar / ok ríða á vellu vígríðar,*
> *en manna níu laða / ár ok ævi — tár er at græti komið.*
>
> *En Heimdallr blióstr / ok Höðr hálfan frá;*
> *hjá stendr fögrgr ok fagrbúin / Vindlöð at vápnheimi.*
> *Þá er Míms synir vita / er vænta at vefildar kappi,*
> *ok Loki lýðsins / leiðtökur konungs, —*
> *aldrei skal þeim á Funeral-Plain / fegraldr at rjóða.*

*Thus the Tested one rises — from the sea's edge with all marks of worth,*
*to judge every law the deceiver spoke, and cast the fools into the fire*
*who would not heed the lesser call.*
*Then Surtur stands with the searing blade, the sun glints off tenfold steel,*
*and the Giants ride onto Vígríðr's Field — the Plain of Battle —*
*nine worlds at the borders, and the Watchman blows.*
*But before the world shakes, every seam is tested, every weld is struck,*
*every shield is bent to prove it holds, and every river of fire*
*is mapped so that when the iron meets the iron, the shield-wall stands.*

---

## Phase Number

**Phase 13** — Version target: `0.6.0`

---

## Norse Naming Rationale

**Vǫllr Vígríðar** — The Plain of Battle, the战场 where gods and the tested meet.

Vígríðr is the immense plain — a hundred leagues in every direction — where the final battle of Ragnarök is fought. It is not a place of destruction for destruction's sake. It is **the proving ground**. Odin has prepared for it. Heimdallr sounds the horn. The gods array themselves — each flaw exposed, each weld tested, each gap filled before the shield-wall closes.

This is Phase 13 because the World Tree stands (Phase 12 Yggdrasil) but trees that stand untested fall in the first storm. The 4 preset validation failures are the cracks in the bark. The missing VRM validator is the gap in the shield-wall. The undocumented pipeline is the commander whose orders no one can read. The texture pipeline is the blade that was forged but never sharpened.

**Vǫllr Vígríðar is the hardening.** It is not new knowledge — it is proving that every piece of knowledge already earned still holds under pressure. It is the phase where:

- **Bugs are slain** — the 4 preset failures are not acceptable cracks in the shield
- **Regression walls are raised** — every fix gets a guard that never sleeps
- **VRM validation is forged** — external truth-telling, not self-attestation
- **Textures travel the pipeline** — not just colors, but real material maps
- **Documentation is inscribed** — the runes that let others read and rebuild
- **The system is hardened** — so that when the world shakes, our tree stands

*Ragnarök comes for every system. Those who survive are those who tested every seam before the fire.*

---

## Vision Statement

Phase 12 gave us Yggdrasil — a tree where every branch is grafted, every root draws from its well, every leaf drinks from the same stream. The tree stands at **1159 tests passing, all modules integrated, the full pipeline flowing from spec to VRM.**

But the tree has **4 cracks** — preset validation failures that prove the roots need strengthening. And the tree has **gaps** — no external validator confirms our VRM output is truly spec-compliant, textures exist only as color values and not as pipeline-processed maps, and no one outside this forge can read the runes without explanation.

**Vǫllr Vígríðar** is where every branch is stress-tested, every crack is filled, and every surface is hardened against the battles to come. This is the proving ground. We do not add new modules — we prove the modules we have are iron-true.

---

## Task List

### T1: Ragnarök Bug Fixes — Slain the Four Cracks

The 4 preset validation failures in `test_presets.py` are cracks in the shield-wall. Find them. Fix them. Prove they stay fixed.

- [ ] Identify and classify all 4 preset validation failures (invalid hex colors, tan level range violations)
- [ ] Fix invalid hex color definitions in preset YAML files
- [ ] Fix tan level range validation (ensure values fall within acceptable bounds)
- [ ] Fix any additional validation edge cases discovered during investigation
- [ ] Write targeted regression tests for each fix — every slain bug stays dead
- [ ] Run full test suite: `pytest tests/` — all 1174 collected, 0 failures
- [ ] **Metric**: `pytest tests/test_presets.py` passes with 0 failures

### T2: Regression Guard Fortress — Walls That Never Sleep

Every bug slain in T1 gets a permanent guard. Every existing integration point gets a regression test. The fortress stands because every gate is watched.

- [ ] Create `tests/test_regression.py` — regression test suite for all bug fixes
- [ ] For each T1 bug fix: one regression test that would catch the exact failure mode
- [ ] Add regression tests for pipeline stage transitions (stage N output → stage N+1 input)
- [ ] Add regression tests for VRM export: bone count, expression count, spring bones, first-person flags
- [ ] Add regression tests for material assignment: skin vs. eye vs. hair material boundary conditions
- [ ] Smoke test: `pytest tests/ -m regression` — all pass within 60 seconds
- [ ] **Metric**: ≥ 20 new regression tests, all passing

### T3: VRM Validator Integration — External Truth-Telling

`hamr verify-rig` attests to its own output. We need an **external** VRM 1.0 validator that confirms our VRM files are truly spec-compliant — glTF schema validation, VRM extension checks, mesh integrity.

- [ ] Integrate `pyvrm` or equivalent VRM 1.0 validator as an external check
- [ ] `hamr validate-vrm <file>` command: runs glTF schema validation + VRM extension validation
- [ ] Validate: required glTF nodes (scene, nodes, meshes, accessors)
- [ ] Validate: VRM 1.0 extensions (VRMC_vrm, VRMC_materials_mtoon, VRMC_springBone)
- [ ] Validate: mesh integrity (no zero-area faces, no degenerate normals, vertex count within limits)
- [ ] Validate: texture references are resolved (no dangling image URIs)
- [ ] Output: JSON report with `{valid: bool, errors: [], warnings: []}`
- [ ] Exit codes: 0 = valid, 1 = warnings, 2 = invalid
- [ ] CI integration: `hamr validate-vrm` runs on every generated VRM artifact
- [ ] **Metric**: `hamr validate-vrm output/casual_f.vrm` exits 0 on a Phase 12-generated VRM

### T4: Texture Pipeline — From Color to Surface

Materials are more than hex colors. Real materials have normal maps, roughness variation, subsurface scattering textures. The texture pipeline bakes procedural maps into the VRM.

- [ ] Create `src/hamr/textures/` package with `__init__.py` and `pipeline.py`
- [ ] `TexturePipeline.generate_material_maps(spec)` — generates material texture set from spec
- [ ] Skin: generate SSS thickness map from body regions (face/thinner, torso/thicker)
- [ ] Eyes: generate iris detail map from iris color + pattern type
- [ ] Hair: generate root→tip gradient texture from hair color spec
- [ ] Clothing: generate fabric normal map from pattern type (twill, knit, silk, denim)
- [ ] All textures: Pillow-based procedural generation (no Cycles bake, Pi-compatible)
- [ ] Integrate into `MaterialForge.assign_materials()` — bake textures before material assignment
- [ ] Textures embedded in VRM export (glTF texture array)
- [ ] `TexturePipeline` respects `perf_budget` — skips texture generation for `minimal` tier
- [ ] **Metric**: Generated VRM contains ≥ 4 distinct texture maps viewable in VRM viewer

### T5: Documentation Inscription — Runes for Others

The runes must be legible. Every module, every command, every preset, every architecture decision — written so that the next person who enters this forge can read and rebuild.

- [ ] Auto-generated CLI reference: `hamr docs cli` → markdown from Click decorators
- [ ] Architecture diagram: `docs/architecture.md` — module dependency graph, data flow, pipeline stages
- [ ] Preset creation guide: `docs/presets.md` — how to write a new YAML preset, every field explained
- [ ] VRM spec compliance guide: `docs/vrm-compliance.md` — what Hamr guarantees, what it doesn't
- [ ] API reference: `docs/api.md` — every public class and method with signatures and examples
- [ ] CONTRIBUTING.md update: development setup, test running, PR checklist
- [ ] README.md update: badge counts, Phase 13 features, quickstart examples
- [ ] All docs written for both human and agent consumption
- [ ] **Metric**: `hamr docs cli` generates complete CLI reference; every module has a `module.md` or equivalent

### T6: Accessibility and Hardening — Shield Reforms

The shield has gaps. CLI output is not screen-reader friendly. Error messages assume context. JSON output is inconsistent. The shield reforms when each gap is filled.

- [ ] CLI color codes: add `--no-color` flag; respect `NO_COLOR` and `TERM=dumb` environment variables
- [ ] JSON output consistency: all commands emit valid JSON with `--json`; no mixed output
- [ ] Error message audit: every `raise` and `sys.exit` produces a human-readable message with remediation hint
- [ ] Validation error messages: include field name, expected range, actual value, and example fix
- [ ] Pipeline stage errors: include stage number, module name, elapsed time, and which input failed
- [ ] `hamr check-env --json` returns machine-parseable environment status
- [ ] Add `--quiet` flag to all CLI commands (suppress all output except errors)
- [ ] **Metric**: `hamr build --preset casual_f --no-color --json` produces valid JSON with no ANSI escapes; `hamr build --preset invalid_hex_color` produces an actionable error message

### T7: GPU Profile Tiers — Battle Formation by Hardware

Not every warrior carries the same shield. Pi 5 fights with 8GB. A desktop fights with 32GB. The cloud fights with unlimited RAM. The battle formation adapts to the hardware.

- [ ] Define GPU profile tiers in `src/hamr/core/profiles.py`:
  - `minimal`: Pi 5 (8GB RAM, no GPU) — skip textures, reduce hair density, limit clothing
  - `standard`: Desktop (16GB RAM, discrete GPU) — full textures, medium hair
  - `full`: Cloud/workstation (32GB+ RAM, powerful GPU) — maximum quality everything
- [ ] `PerfBudget` respects profile tier — automatically selects from hardware detection
- [ ] `TexturePipeline.generate_material_maps()` skips or downscales based on tier
- [ ] `HairForge` adjusts hair strand count per tier (minimal: 500, standard: 2000, full: 5000)
- [ ] `ClothingForge` adjusts mesh density per tier
- [ ] CLI: `hamr build --profile minimal|standard|full` overrides auto-detection
- [ ] CLI: `hamr check-env` reports detected profile tier
- [ ] Tests: `pytest tests/ -m perf` validates each tier produces valid output
- [ ] **Metric**: `hamr build --preset casual_f --profile minimal` completes on Pi 5 in < 45s with valid VRM output

---

## Architecture Decisions

### AD-13.1: Bug-First, Feature-Second

**Decision**: Phase 13 fixes bugs before adding features. No T4–T7 work begins until T1 passes with 0 failures and T2 regression guards are in place.

**Rationale**: A hardened system is a system where existing features work flawlessly. The 4 preset failures are proof that our integration has cracks. Every regression test is a rune that prevents the crack from reopening. New features on cracked foundations are walls built on sand.

### AD-13.2: External Validation, Not Self-Attestation

**Decision**: VRM validation uses an external validator (`pyvrm` or equivalent), not `verify-rig` which is part of Hamr itself.

**Rationale**: `verify-rig` checks what Hamr *intended* to generate. An external validator checks what was *actually* generated. The gap between intent and reality is where bugs hide. External validation is the impartial judge at Vígríðr — it owes nothing to the combatant.

### AD-13.3: Procedural Textures via Pillow

**Decision**: All texture generation uses Pillow (PIL) for procedural creation. No Cycles bake, no GPU dependency.

**Rationale**: Hamr runs on a Pi 5 in headless mode. Cycles baking is not available. Pillow is fast, deterministic, and produces consistent results. Normal maps, SSS thickness maps, and gradient textures can all be generated from mathematical functions applied to image arrays. This is the same approach used by game engine texture generators.

### AD-13.4: GPU Profile Tiers Are Suggestions, Not Requirements

**Decision**: Profile tiers suggest quality levels but do not prevent builds. `--profile minimal` may produce lower-quality output, but it still produces valid VRM.

**Rationale**: The purpose of tiers is to ensure Pi 5 viability, not to gate features. A user on a Pi 5 can still run `--profile full` — it will just be slower. The tier system provides sensible defaults, not hard walls. This preserves user agency while giving the system escape hatches for constrained hardware.

---

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| SC-1 | **All preset validations pass** | `pytest tests/test_presets.py` — 0 failures |
| SC-2 | **Full test suite passes** | `pytest tests/` — 1174+ collected, 0 failures |
| SC-3 | **Regression test suite established** | ≥ 20 regression tests, all passing |
| SC-4 | **VRM validator integrated** | `hamr validate-vrm <file>` exits 0 on Phase 12-generated VRM |
| SC-5 | **VRM validator catches errors** | Deliberately broken VRM produces non-zero exit code with error details |
| SC-6 | **Texture pipeline functional** | Generated VRM contains ≥ 4 distinct procedural texture maps |
| SC-7 | **Documentation complete** | CLI reference auto-generated; architecture, presets, API docs all present |
| SC-8 | **CLI accessibility hardened** | `--no-color`, `--json`, `--quiet` all functional; error messages actionable |
| SC-9 | **GPU profile tiers operational** | `hamr build --profile minimal|standard|full` adjusts quality; Pi 5 completes in < 45s on minimal |
| SC-10 | **No regressions from Phase 12** | All Phase 12 tests still pass; 1159+ tests passing |
| SC-11 | **E2E pipeline test suite passes** | `pytest tests/ -m e2e` — full pipeline test suite passes |
| SC-12 | **Test count grows** | Total test count ≥ 1220 (including regression + validation + texture tests) |

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
| 11 | Alvíssmál | 0.4.0 | 25/25 bones, mesh hair, clothing, weight paint, presets, Pi performance |
| 12 | Yggdrasil | 0.5.0 | Integration of all modules, materials, expressions, collisions, performance gates |
| **13** | **Vǫllr Vígríðar** | **0.6.0** | **Bug fixes, regression guards, VRM validation, texture pipeline, documentation, hardening** |

---

## What Comes After — Phase 14 Hints

The plain of testing is crossed. The shield-wall holds. But the battle reveals new terrain:

*Phase 14: **Ginnungagap** — The Void Between Worlds*

The great void before creation, where fire and ice first met. After hardening, we expand. Phase 14 will likely tackle:

1. **Animation Presets** — Idle animation clips baked into VRM for stand-alone preview
2. **Multi-Avatar Assembly** — Build scenes with multiple avatars (POSE → animation → scene composition)
3. **External Base Mesh Support** — Import custom FBX/glTF meshes as alternative bases beyond MB-Lab
4. **VRChat-Specific Validation** — Upload test, performance rating check, quest compatibility
5. **Plugin Architecture** — Allow third-party modules to hook into the pipeline stages
6. **Web UI Foundation** — Browser-based preset editor and avatar preview (the first bridge between forge and user)

*From the void, new worlds are born. But first, the existing world must be proven iron-true.*

---

*Þá stendr upp ór í norðrlǫndum / sá er áðr vállar byggði,*
*ok kǿmr sá or himni ofan / at dónum dauðra dróttin —*
*en hann trír ok trúir / at sá er fætt ok föður hefir,*
*ok sitr á haugi ok skýtr hráum;*
*þat er mikit undr, at hon svá ofan er.*
— Vǫluspá, St. 62*

*Then comes the mighty one, down from the heavens,*
*who rules all and ordains the fates —*
*and from beneath the earth rises the Tested One,*
*who stood on the plain and held the shield-wall true.*

ᚺᚨᛗᚱ — Phase 13: Vǫllr Vígríðar — *The Plain of Battle, the Proving Ground*