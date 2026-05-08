# Phase 14: Gjallarhorn

> *"Þá blæss Heimdallr, horni alt, ok rístar knefill frá."*
> Then Heimdallr blows the Gjallarhorn, the all-resounding horn,
> and the final assembly is called.

---

## Name & Meaning

**Gjallarhorn** — *"The Resounding Horn"*

The Gjallarhorn is the great horn of Heimdallr, guardian of the Bifröst bridge. When blown, its sound echoes across all the Nine Realms, gathering every force into a single assembly before Ragnarök. It is the clarion call that says: *all things are now one thing — the moment of truth has come.* This phase is that horn: the unification of every disparate thread, subsystem, and artifact into a single integrated whole, standing ready for release.

---

## Evocative Description

The shape-skin engine has been forged in fire, hardened in the proving ground of Vígríðar, and tested against every edge case the Valkyries could devise. Now Heimdallr raises the horn to his lips. Gjallarhorn is the phase where every subsystem — procedural textures, VRM validation, animation rigs, GPU profiles, documentation, presets — is drawn together into a single resonant build. The horn's blast is the end-to-end integration test, the Blender build verification, the PyPI package that installs cleanly, the release candidate that says: *this is the shape the world will receive.*

---

## Task List

### 14.1 — End-to-End Integration Suite
Build a comprehensive end-to-end test harness that exercises the full pipeline: asset ingestion → procedural texturing → VRM export → validation — as one unbroken flow. Integration tests must pass on all target platforms (Windows, macOS, Linux). Existing unit/e2e tests remain; this is the *unified* run that gates the release candidate.

### 14.2 — Blender Build Verification
Create a CI matrix that tests Hamr against the three latest Blender LTS releases (4.2, 4.3, 4.4) plus current stable. Verify that the addon installs, registers all operators, and can execute the full pipeline without errors. Document any version-specific caveats or deprecation warnings.

### 14.3 — Performance Regression Benchmarks
Establish baseline performance metrics for key operations: mesh generation, texture baking, VRM export, and UI responsiveness. Implement an automated benchmark suite that runs on every PR and flags regressions beyond tolerance thresholds (±5%). Publish benchmark results to the repo wiki.

### 14.4 — Preset System Rework
Overhaul the preset architecture: migrate from flat JSON files to a versioned, tagged preset format with categories (humanoid base, creature, accessory, environment). Add a preset browser UI panel, import/export, and a community preset repository stub. Ensure all built-in presets pass validation with the new schema.

### 14.5 — PyPI Packaging & Installer Preparation
Configure `pyproject.toml` / `setup.cfg` for PyPI distribution of the core library (non-Blender-dependent modules). Create a separate Blender addon zip packaging script. Add CLI entry points for headless VRM validation and mesh generation. Verify `pip install` works cleanly in a fresh venv.

### 14.6 — Release Candidate 0.7.0-rc1
Tag and cut the first release candidate from the `Development` branch. Bundle complete changelog (Phases 7–14), migration guide from v0.5.x, and updated README with screenshots. Publish rc1 to GitHub Releases and TestPyPI. Announce to the community for smoke testing.

### 14.7 — Documentation Finalization & Accessibility Audit
Complete API reference auto-generation from docstrings. Run a full accessibility audit (keyboard navigation, screen-reader compatibility, WCAG 2.1 AA contrast ratios) on all UI panels. Fix outstanding docs issues from Phase 13 backlog. Ensure the documentation site builds reproducibly via CI.

---

## What Comes After — Phase 15 Vision

**Ragnarök** — *"The Twilight of the Gods"*

If Gjallarhorn is the call to assembly, Ragnarök is the transformation that follows. Phase 15 is the release itself: v0.7.0 stable ships, the old `Development` branch merges to `Main`, and Hamr steps out of the forge and into the world. Bug reports from rc1 are triaged and fixed. Community feedback from the wild is incorporated. The addon lands on the Blender Market, the library hits PyPI, and the shape-skin engine becomes a living tool in the hands of creators. After Ragnarök comes the new world — and V0.8 will turn towardnext-generation features: MToon shader parity, pose-space deformation, and the long-promised multiplayer scene-sync.

---

*Let the horn resound. All realms shall hear it.*