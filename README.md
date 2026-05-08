---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/f5796b46-87be-49ef-927d-7e7ac3320153.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/f5796b46-87be-49ef-927d-7e7ac3320153.jpg)

---

<div align="center">

# ᚺᚨᛗᚱ Hamr

### *The Shape-Skin Engine*

**Open-source parametric 3D anime character forge**

Linux-native · Headless-first · Agent-orchestrated · VRM 1.0

[![Tests](https://img.shields.io/badge/tests-103%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Blender](https://img.shields.io/badge/blender-3.4%2B-orange)]()
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

## ✨ Features

- **YAML-First Spec** — Define characters in simple YAML files, not GUI clicks
- **8 Body Presets** — Athletic-slender, curvy, petite, tall, muscular, and more
- **Parametric Face** — Eyes, nose, mouth, cheeks, ears, chin — all slider-driven
- **Skin & Hair Textures** — HSV-driven procedural textures, no image assets needed
- **MB-Lab + TurboSquid Bone Maps** — Explicit bone mappings (never auto-map)
- **VRM 1.0 Export** — Spring bones, expressions, look-at, first-person annotations
- **Blender Headless** — Runs entirely in `blender --background`, no GUI required
- **Agent-Orchestrated** — Designed for AI-driven creation pipelines
- **103 Tests** — Every forge tested, every path validated

## 🗡️ Quick Start

```bash
# Install
pip install hamr

# Create a character from a spec
hamr build my_character.yaml --out output/

# Validate a spec without building
hamr validate my_character.yaml

# Check your Blender environment
hamr check-env

# List available body presets
hamr list-presets

# Inspect a VRM file
hamr inspect output/avatar.vrm
```

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

Hamr is organized as **six forges** around a central spec:

```
┌─────────────┐
│  YAML Spec  │ ← Your character definition
└──────┬──────┘
       │
┌──────▼──────┐
│   Builder   │ ← Validates, orchestrates, wires
└──────┬──────┘
       │
  ┌────┼────┬────────┬─────────┐
  │    │    │        │         │
┌▼─┐ ┌▼─┐ ┌▼──┐ ┌───▼───┐ ┌──▼──┐
│Bd│ │Tx│ │Rig│ │Texture│ │Export│
│Fo│ │Fo│ │Fo │ │ Forge │ │Forge│
│rg│ │rg│ │rge│ │       │ │     │
└──┘ └──┘ └───┘ └───────┘ └─────┘
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
| `core/pipeline` | Full `BuildPipeline` with error handling |
| `core/textures` | HSV-driven procedural texture generation |
| `core/constants` | Body presets, skin palettes, bone names |
| `body/` | Body proportions and presets |
| `blender_bridge/` | Headless Blender subprocess runner |
| `export/` | VRM 1.0 export with bone maps and expressions |
| `hair/` | Procedural hair (Phase 7) |
| `face/` | Detailed facial controls (Phase 7) |
| `clothing/` | Parametric outfits (Phase 7) |

---

![https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/e7f18ecb-1916-4b15-be64-a7351fec37ee.jpg](https://raw.githubusercontent.com/hrabanazviking/Hamr/refs/heads/Development/e7f18ecb-1916-4b15-be64-a7351fec37ee.jpg)

---

## 🛡️ Design Lessons (from Seiðr-Smiðja)

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

## 🔧 Development

```bash
# Clone
git clone https://github.com/hrabanazviking/Hamr.git
cd Hamr

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=hamr --cov-report=term-missing

# Lint
ruff check src/hamr/

# Build docs
cd docs/
```

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
