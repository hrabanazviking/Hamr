# ᚺᚨᛗᚱ — Philosophy

> *"The hamr shifts. The shape remembers."*

## What Hamr Is

Hamr is an open-source, AI-orchestrated, headless-capable parametric 3D anime character creator. It forges living forms from parameter and intent — a shape-skin engine for the digital age.

## What Hamr Is Not

Hamr is **not** a VRoid clone. VRoid Studio is a closed, Windows/macOS-only GUI application with locked geometry, no scripting API, and no Linux support. Hamr transcends these limitations by being:

- **Open source** — every vertex, every slider, every algorithm is yours
- **Cross-platform** — Linux-native, headless-first, GUI optional
- **Agent-orchestrated** — any AI can wear Hamr and forge characters
- **Extensible** — plugin architecture for body types, hair systems, clothing generators
- **VRM-native** — exports VRM 1.0 directly, no intermediate format hell

## The Name

In Norse metaphysics, the **hamr** is the shape-layer beneath the physical body — the metaphysical skin that determines form. When a völva shifts shape (hamhleypa, "hamr-runner"), she is changing her hamr. A parametric character creator does not build static models — it shifts between hamr-states. Users morph parameters and the form reshapes.

Hamr is the engine of becoming.

## Design Principles

1. **Parameter is Sovereign** — Every visual property is a named, typed, ranged parameter. No hidden state. No GUI-only settings. The YAML spec IS the character.

2. **Headless First** — If it cannot run without a display, it is broken. Blender in background mode is the default. GUI is a privilege, not a requirement.

3. **Agent as User** — AI agents are first-class users. Hamr's API (YAML spec → character → VRM) is designed for programmatic consumption. Humans get a GUI later. Agents get the forge now.

4. **Forge, Don't Paint** — Where VRoid says "draw this texture," Hamr says "declare this intent." Procedural generation beats manual painting wherever possible. HSV shifts, noise functions, and blend trees replace brush strokes.

5. **Modular Blades** — Each module (body, face, hair, clothing, rig, export) is a self-contained forge. They can be invoked independently, in any order, with any parameters. No monolithic pipeline.

6. **No Sacred Geometry** — VRoid locks you to their template mesh. Hamr allows any base mesh — MB-Lab, MakeHuman, TurboSquid, or custom. The rig is declared, not assumed.

7. **Yggdrasil, Not Bonsai** — The architecture scales. Single character? One command. Batch of 100 variants? Pipeline. Agent-driven iterative refinement? Loop spec → build → inspect → adjust → build. The tree grows as the roots demand.

## Lineage

Hamr is born from Seiðr-Smiðja, the forge that proved VRM creation could be headless and agent-driven. Where Seiðr-Smiðja was a script pipeline, Hamr is a **framework** — modular, extensible, and self-aware of its own architecture.

Seiðr-Smiðja → Hamr. The blade is quenched. The hamr shifts.