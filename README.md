---
![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/f5796b46-87be-49ef-927d-7e7ac3320153.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/f5796b46-87be-49ef-927d-7e7ac3320153.jpg)
---

<div align="center">

# ᚺᚨᛗᚱ Hamr

### *The Shape-Skin Engine*

**Open-source parametric 3D anime character forge**

Linux-native · Headless-first · Agent-orchestrated · VRM 1.0

[![CI](https://github.com/hrabanazviking/Hamr/actions/workflows/ci.yml/badge.svg?branch=Development)](https://github.com/hrabanazviking/Hamr/actions)
[![Version](https://img.shields.io/badge/version-0.8.0-blue)]()
[![Tests](https://img.shields.io/badge/tests-2065%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)]()

</div>

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/24224709-e889-4556-ac86-41352b917c35.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/24224709-e889-4556-ac86-41352b917c35.jpg)

---

**Hamr** (Old Norse: *hamr* — the shape-skin, the second body) is the open-source
alternative to VRoid Studio. It creates parametric 3D anime characters headlessly,
driven by YAML specs and agent commands, and exports VRM 1.0 avatars ready for
VRChat, Resonite, and any VRM-compatible platform.

No GUI. No Windows dependency. No closed-source lock-in.

*Every vertex, every slider, every algorithm is yours.*

---

## ✨ Key Features

- **🎨 MToon Anime Shaders** — Two-tone cel-shading, rim lighting, outline rendering, emission — full VRM MToon spec in pure Python
- **🌿 Spring Bone Physics** — Hair sway, skirt drape, accessory bob — physics presets, parameter blending, and energy estimation
- **🤸 Pose Library** — Pre-defined T-pose, A-pose, hand poses, and facial presets with blending and VRM export
- **📦 VRM 1.0 Export** — Spring bones, expressions, look-at, first-person annotations — full VRM 1.0 compliance out of the box
- **🔧 YAML-First Spec** — Define characters in simple YAML files, not GUI clicks
- **🖥️ Headless Blender** — Runs entirely in `blender --background`, no GUI required
- **🍓 Pi 5 Ready** — GPU-adaptive quality profiles for Raspberry Pi 5, desktop, and cloud
- **♿ Accessibility-First** — `--no-color`, `--json`, `--quiet` on every command
- **✅ 2,233 Tests** (2,206 pass, 27 skip, 0 fail) — Every forge tested, every path validated

---

## 🗡️ Quick Start

```bash
# Install
pip install hamr

# Build a character from a preset
hamr build --preset anime_girl_default

# Build from a spec file
hamr build my_character.yaml --out output/

# Validate a spec without building
hamr validate my_character.yaml

# Inspect a VRM file
hamr inspect output/avatar.vrm

# Verify a VRM rig
hamr verify-rig output/avatar.vrm

# Check your build environment
hamr check-env

# List available presets
hamr list-presets

# Print version
hamr version

# Generate documentation
hamr docs generate

# Run accessibility audit
hamr docs audit
```

See [CLI Reference](#-cli-reference) below for all 9 commands and flags.

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/8da3a599-f9da-4728-8545-eaa74b4e302a.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/8da3a599-f9da-4728-8545-eaa74b4e302a.jpg)

---

## 📝 Character Spec

The simplest character spec:

```yaml
name: Quick Avatar
version: "1.0"

body:
  height_cm: 165
  build: average
  skin:
    base_hex: "#E8B87A"

hair:
  style: wavy
  color:
    roots: "#4A2E14"

export:
  format: vrm1
  title: Quick Avatar
  author: Hamr Forge
```

Full spec with every option:

```yaml
name: Runa Gridweaver
version: "1.0"

body:
  height_cm: 172
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
    undertone: warm
    sss: true
  proportions:
    shoulder_width: 0.40
    bust: 0.45
    waist: 0.32
    hip_width: 0.52
    leg_length: 0.52

hair:
  style: wavy
  length: very-long
  volume: 0.7
  color:
    roots: "#C4A265"
    mid: "#D4B47A"
    tips: "#E8D0A0"
    highlight: "#F0E0B8"

face:
  eyes:
    iris_hex: "#4169E1"
    pupil_hex: "#1A1A2E"
    sclera_hex: "#F8F8F0"
    shape: round
    size: 1.1
  eyebrows:
    color_hex: "#B8944A"
    thickness: 0.07
    shape: arched
  nose:
    bridge_width: 0.35
    tip_width: 0.30
    bridge_height: 0.50
    definition: 0.55
    nostril_width: 0.30
  mouth:
    lip_hex: "#C47070"
    width: 0.38
    fullness: 0.55
    upper_curve: 0.40
    lower_fullness: 0.50
    smile_width: 0.60
  cheeks:
    blush_hex: "#E0A0A0"
    bone_width: 0.60
    fat: 0.30
  ears:
    size: 0.40
    protrusion: 0.20
    elf_factor: 0.0
  chin:
    width: 0.30
    protrusion: 0.40
    jaw_width: 0.40

export:
  format: vrm1
  title: Runa Gridweaver
  author: Volmarr & Runa
  version: "1.0"
  license: CC-BY-4.0
```

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/88043fbd-55ab-4b1d-8b08-cbffd127d5f3.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/88043fbd-55ab-4b1d-8b08-cbffd127d5f3.jpg)

---

## 🏗️ Architecture

Hamr is organized as **seven forges** around a central spec:

```
┌─────────────┐
│  YAML Spec  │ ← Your character definition
└──────┬──────┘
       │
┌──────▼──────┐
│   Builder   │ ← Validates, orchestrates, wires
└──────┬──────┘
       │
  ┌────┼────┬────────┬─────────┬───────┐
  │    │    │        │         │       │
┌▼─┐ ┌▼─┐ ┌▼──┐ ┌───▼───┐ ┌──▼──┐ ┌▼────┐
│Bd│ │Tx│ │Rig│ │Texture│ │MToo│ │Expt│
│Fo│ │Fo│ │Fo │ │ Forge │ │ Fo  │ │Forge│
│rg│ │rg│ │rge│ │       │ │ rge │ │     │
└──┘ └──┘ └───┘ └───────┘ └─────┘ └─────┘
       │
  ┌────▼────┐
  │ Blender  │ ← Headless subprocess
  │  Bridge  │
  └────┬─────┘
       │
  ┌────▼────┐
  │ VRM 1.0 │ ← Your avatar file
  └─────────┘
```

| Module | Purpose |
|--------|---------|
| `core/spec` | YAML spec parsing, validation, serialization |
| `core/builder` | Pipeline orchestrator (validate → build → export) |
| `core/pipeline` | Full `BuildPipeline` with 14 numbered stages |
| `core/textures` | HSV-driven procedural texture generation |
| `core/texture_procedural` | Skin detail, iris, hair gradients, fabric normals |
| `core/perf` | Performance budgets and GPU-adaptive quality |
| `core/constants` | Body presets, skin palettes, bone names |
| `core/gpu_profiles` | Pi 5 / Desktop / Cloud hardware detection |
| `core/a11y` | Accessibility flags, CLI hardening, error hints |
| `core/regression` | Performance regression baselines |
| `hair/` | Procedural hair styles, color gradients, physics |
| `face/` | Shape keys, expression mapping, sliders |
| `clothing/` | Outfit layers, materials, tinting |
| `materials/mtoon` | MToon anime shader configuration, presets, VRM export |
| `materials/anime` | Eevee-optimized anime shaders (skin, eye, hair, clothing) |
| `rigs/spring_bones` | VRM 1.0 spring bone groups and collider setup |
| `rigs/spring_tuning` | Spring bone parameter presets, blending, energy estimation |
| `rigs/poses` | Pose library — T-pose, A-pose, hand poses, facial presets |
| `rigs/stub_bones` | Missing bone creation for 25/25 humanoid mapping |
| `rigs/weights` | Weight paint engine with smoothing and quality scoring |
| `rigs/verify` | VRM rig compliance checker |
| `rigs/collision` | Deterministic head and body colliders |
| `blender_bridge/` | Headless Blender subprocess runner |
| `blender_bridge/e2e` | End-to-end Blender build testing |
| `export/` | VRM 1.0 export with bone maps and expressions |
| `export/vrm_validator` | Binary glTF parsing, bone coverage, compliance |
| `export/animation_clips` | Idle, weight shift, look-around, walk cycle clips |
| `export/first_person` | First-person mesh annotations per render subset |
| `docs/` | Auto-generated documentation & a11y audit |
| `cli` | Command-line interface |

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/e7f18ecb-1916-4b15-be64-a7351fec37ee.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/e7f18ecb-1916-4b15-be64-a7351fec37ee.jpg)

---

## 📖 CLI Reference

Hamr's CLI provides 9 commands:

| Command | Description |
|---------|-------------|
| `hamr build` | Build a character from spec or preset |
| `hamr validate` | Validate a spec without building |
| `hamr inspect` | Inspect VRM/GLB file compliance |
| `hamr list-presets` | List available character presets |
| `hamr verify-rig` | Verify VRM rig completeness |
| `hamr check-env` | Check build environment (Blender, VRM addon, GPU) |
| `hamr version` | Print Hamr version |
| `hamr docs generate` | Generate documentation files |
| `hamr docs audit` | Run accessibility & compliance audit |

All commands support `--no-color`, `--quiet`, and `--json` flags for accessibility.
`build` also supports `--preset`, `--spec`, `--skip-stages`, `--dry-run`, and `--budget`.

See `hamr <command> --help` for detailed options.

---

## 🛡️ GPU Profiles

Hamr adapts build quality to your hardware. Three profiles — from anvil to sky:

| Profile | Device | Max Triangles | Texture Res | Build Time | Memory | SSS | Hair Styles |
|---------|--------|--------------|-------------|-------------|--------|-----|-------------|
| **Pi 5** | Raspberry Pi 5 | 20K | 1024px | ≤45s | 1.5 GB | ✗ | limited |
| **Desktop** | Discrete GPU | 80K | 2048px | ≤30s | 4 GB | ✓ | all |
| **Cloud** | Cloud GPU | 200K | 4096px | ≤15s | 8 GB | ✓ | all |

Auto-detection probes `/sys`, `lspci`, and `glxinfo`. Override with `--budget minimal|standard|full`.

---

## 🗡️ Design Lessons (from Seiðr-Smiðja)

Hamr incorporates hard-won lessons from building Seiðr-Smiðja:

| Lesson | Code | Rule |
|--------|------|------|
| Never auto-map bones | D-008 | Always use explicit bone mapping dicts |
| Filter by humanbone | D-009 | `filter_by_human_bone_hierarchy = False` |
| Symmetric expressions | D-011 | Bind BOTH L and R shape keys |
| Bone rotation lookAt | D-012 | Use bone rotation, not morph targets |
| Name-based expression binds | D-013 | Use shape key NAME strings, not indexes |
| `EXEC_DEFAULT` export | D-016 | Required for headless VRM export |
| Allow non-humanoid | D-017 | Safety net for non-standard rigs |
| Canonical bone API | D-018 | Use `human_bone_name_to_human_bone()` |
| Lowercase enums | D-019 | `"bone"` not `"BONE"` in VRM dict |

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/c429f4e8-63a9-4bc1-b2d4-b80a4f4acbfb.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/c429f4e8-63a9-4bc1-b2d4-b80a4f4acbfb.jpg)

---

## 🔧 Installation

```bash
# Install from PyPI
pip install hamr

# Or install from source
git clone https://github.com/hrabanazviking/Hamr.git
cd Hamr
pip install -e ".[dev]"
```

### Requirements

- **Python 3.10+**
- **Blender 3.4+** (for full build pipeline — headless mode)
- **PyYAML**, **Pillow**, **numpy** (auto-installed with pip)

---

## 🧪 Development

```bash
# Clone
git clone https://github.com/hrabanazviking/Hamr.git
cd Hamr

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python3 -m pytest tests/ -q --tb=short

# Without Blender-dependent tests
python3 -m pytest tests/ -q -m "not blender and not e2e"

# With coverage
python3 -m pytest tests/ --cov=hamr --cov-report=term-missing

# Performance regression
python3 -m pytest tests/ -m perf

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines, code style, and PR checklist.

---

## 🆕 What's New in v0.7.0

- **MToon Anime Shaders** — Full VRM MToon cel-shading spec: two-tone lighting, rim, outline, emission, transparency
- **Spring Bone Tuning** — Physics parameter presets, blending, validation, and energy estimation
- **Pose Library** — Pre-defined T-pose, A-pose, hand and facial poses with blending and VRM export
- **14-Stage Build Pipeline** — Explicit numbered stages with timing, skip-stages, and dry-run
- **6 Character Presets** — Built-in presets with deep merge
- **Procedural Hair & Clothing** — 5 hair styles, 6 clothing patterns, weight paint transfer
- **Face Expressions** — Auto-discovery of shape keys, VRM 1.0 expression presets (6+)
- **VRM 1.0 Validator** — Binary glTF parsing, bone coverage, spring bone validation
- **GPU-Adaptive Quality** — Pi 5 / Desktop / Cloud profiles with memory budget enforcement
- **2,233 Tests (2,206 pass, 27 skip, 0 fail)** — Every forge tested, every path validated

See [RELEASE_NOTES.md](./RELEASE_NOTES.md) for the full changelog and [MIGRATION.md](./MIGRATION.md) for upgrade instructions.

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/25a43eff-a420-4c0b-9d54-5289d957b2ab.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/25a43eff-a420-4c0b-9d54-5289d957b2ab.jpg)

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

*Every vertex, every slider, every algorithm is yours.*

## 🙏 Acknowledgments

- **Seiðr-Smiðja** — The predecessor forge that taught us what not to do
- **MB-Lab** — Open-source character base mesh
- **VRM Consortium** — VRM 1.0 specification
- **Blender Foundation** — For making the greatest 3D tool open source
- **The Nornir** — For weaving the threads that brought us here

---

<div align="center">

*Forged in fire, quenched in ice, sharpened on the grindstone of experience.*

ᚺᚨᛗᚱ — *hamr* — the shape you wear

</div>

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/image-23-RuneForgeAI.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/image-23-RuneForgeAI.jpg)

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/IMG_0407.jpeg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/IMG_0407.jpeg)

---