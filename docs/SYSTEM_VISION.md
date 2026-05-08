# ᚺᚨᛗᚱ — System Vision

> *"The shape-skin engine for the digital age."*

## Overview

Hamr is an open-source, AI-orchestrated, headless-capable parametric 3D anime character creator that runs on Linux and exports VRM 1.0. It is the shape-forge that VRoid Studio should have been — if VRoid had been built by people who believe in freedom, agents, and the command line.

## Problem Statement

| Pain Point | VRoid Studio | Hamr |
|---|---|---|
| **No Linux support** | Windows/macOS only | Linux-native, headless-first |
| **Closed source** | Proprietary, no API | Open source, full API |
| **No scripting** | GUI-only, manual clicks | YAML spec → character → VRM |
| **Locked geometry** | Fixed template mesh | Any base mesh |
| **No agent control** | Human must click buttons | AI agents can forge characters |
| **VRM 0.x only** | Exports 0.x only | VRM 1.0 native |
| **No hair generation** | Paint-based hair cards | Procedural + mesh hybrid |
| **Underwear baked in** | Cannot remove in-app | Full mesh control |

## Architecture Vision

```
┌─────────────────────────────────────────────┐
│                    HAMR                       │
│            The Shape-Skin Engine              │
├─────────────────────────────────────────────┤
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Spec     │  │  Forge    │  │  Export   │  │
│  │  YAML→Py  │  │  Build    │  │  VRM 1.0  │  │
│  │  Parser   │  │  Pipeline │  │  GLB/BLEND│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────┐    │
│  │              Module Layer             │    │
│  ├─────────┬─────────┬─────────┬────────┤    │
│  │  Body   │  Face   │  Hair   │Clothes │    │
│  │  Forge  │  Forge  │  Forge  │ Forge  │    │
│  ├─────────┼─────────┼─────────┼────────┤    │
│  │  Rig    │  Expr   │ Physics │Texture │    │
│  │  Forge  │  Forge  │  Forge  │ Forge  │    │
│  └─────────┴─────────┴─────────┴────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │           Base Mesh Layer             │    │
│  ├────────┬────────┬────────┬───────────┤    │
│  │ MB-Lab │MakeHmn │TurbSqid│  Custom   │    │
│  └────────┴────────┴────────┴───────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │           Blender Engine             │    │
│  │  (headless, background mode, ARM64)  │    │
│  └──────────────────────────────────────┘    │
│                                              │
└─────────────────────────────────────────────┘
```

## Core Modules

### 1. Spec Parser (`hamr/spec/`)
YAML/JSON specification → Python dataclass → validated character definition. The spec IS the character. Every parameter documented, every default explicit.

### 2. Body Forge (`hamr/body/`)
Parametric body generation from any base mesh. Slider-based morphing via shape keys. Body proportions, skin texture, nail/lip tinting.

### 3. Face Forge (`hamr/face/`)
Face morph system — eyes, nose, mouth, jaw, cheeks. Expression blendshape binding. Viseme mapping for VRChat.

### 4. Hair Forge (`hamr/hair/`)
Procedural hair generation engine. Curly, straight, wavy, braided — all from parameters. Shell layers + guide curves. No more VRoid's locked hair cards.

### 5. Clothing Forge (`hamr/clothing/`)
Parametric clothing generation from templates. Body-aware fitting. Material assignment. Outfit switching for VRM 1.0 material variants.

### 6. Rig Forge (`hamr/rigs/`)
Auto-rigging, bone mapping, VRM humanoid compliance. Works with any base mesh. Expression setup from templates.

### 7. Texture Forge (`hamr/core/textures.py`)
Pillow + NumPy procedural texture generation. HSV shifts, procedural patterns, gradient maps. No Cycles bake dependency.

### 8. Export Forge (`hamr/export/`)
VRM 1.0 export via Blender VRM Addon. GLB/BLEND fallback. Post-export metadata patching. Compliance checking.

## Data Flow

```
spec.yaml ──→ SpecParser ──→ CharacterSpec
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
            BodyForge      HairForge    ClothingForge
                 │              │              │
                 └──────┬───────┘──────────────┘
                        ▼
                   Scene Assembly
                        │
                        ▼
                  RigForge ──→ ExpressionForge ──→ PhysicsForge
                        │
                        ▼
                   TextureForge
                        │
                        ▼
                   ExportForge
                        │
                        ├──→ .vrm (VRM 1.0)
                        ├──→ .glb
                        └──→ .blend
```

## Agent Integration

Hamr is designed for AI agent orchestration:

```yaml
# Agent can write this spec directly
character:
  name: "Runa Gridweaver"
  body:
    height: 173
    build: athletic-slender
    skin:
      base_hex: "#E8B87A"
      undertone: warm
  face:
    jaw: V-shape
    eyes:
      iris_hex: "#B8D4E3"
      shape: cat-tilt
  hair:
    style: wild-curly
    length: shoulder-plus
    color:
      roots: "#C4A265"
      tips: "#F5E6B8"
```

```bash
# Single command to forge
hamr build spec.yaml --out runa.vrm

# Batch forge
hamr build-batch specs/ --out output/

# Agent loop: build → inspect → adjust → rebuild
hamr iterate spec.yaml --focus hair --rounds 5
```

## Technology Stack

| Component | Technology |
|---|---|
| Core Language | Python 3.11+ |
| 3D Engine | Blender 3.4+ / 4.x (headless) |
| VRM Export | VRM Addon for Blender |
| Texture Generation | Pillow + NumPy |
| Spec Format | YAML (primary), JSON (fallback) |
| Base Mesh | MB-Lab, MakeHuman, TurboSquid, Custom |
| Testing | pytest (unit + integration) |
| CLI | Click / Typer |
| Agent API | Python API + CLI + YAML specs |

## Phases

### Phase 1: Foundation (Current)
- [ ] Project structure and build system (pyproject.toml)
- [ ] Spec parser with full validation
- [ ] Body Forge: MB-Lab base mesh integration
- [ ] Texture Forge: Pillow HSV pipeline
- [ ] Export Forge: VRM 1.0 headless export
- [ ] CLI: `hamr build`, `hamr inspect`
- [ ] Working end-to-end: spec → character → .vrm

### Phase 2: Form
- [ ] Face Forge: morph targets, expressions
- [ ] Hair Forge: procedural shell layers + guide curves
- [ ] Clothing Forge: template-based outfit generation
- [ ] Rig Forge: auto-bone mapping for arbitrary meshes
- [ ] Physics Forge: SpringBone/VRCPhysBone parameters

### Phase 3: Skin
- [ ] Interactive GUI (Blender viewport overlay or web UI)
- [ ] Real-time parameter tweaking with live preview
- [ ] Asset library: hair presets, clothing templates, face morphs
- [ ] Texture painting pipeline (Pillow + Blender procedural)

### Phase 4: Becoming
- [ ] Agent-driven iterative refinement loop
- [ ] Image-to-spec: reference photo → approximate spec
- [ ] Style transfer: apply aesthetic palettes to existing characters
- [ ] Plugin system: community modules for new body types, hair systems
- [ ] Batch variant generation for population

## Non-Goals

- VRoid Studio compatibility or import (we forge our own shapes)
- Unity-specific features (that's a post-export step)
- Real-time rendering (Hamr is a forge, not a renderer)
- Mobile app (headless = server-first)

## Relationship to Seiðr-Smiðja

Seiðr-Smiðja proved the concept. It produced the first headless VRM avatar on ARM64 Linux. Its hard-won bug fixes (D-008 through D-020) are coded into Hamr's DNA.

But Seiðr-Smiðja was a single script pipeline — a narrow path. Hamr is a **framework** with modular forges, a spec-first API, and agent integration. Seiðr-Smiðja's knowledge flows into Hamr's bones.

The old forge is honored. The new forge begins.