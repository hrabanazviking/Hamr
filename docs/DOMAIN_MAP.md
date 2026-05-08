# ᚺᚨᛗᚱ — Domain Map

> *"Most confusion begins when people stop seeing the whole map."*
> — Védis Eikleið, Cartographer

## Domain Ownership

```
                    ┌─────────────┐
                    │    Spec     │
                    │  (Source of  │
                    │   Truth)    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌──┴───┐ ┌──────┴─────┐
        │   Body    │ │ Face │ │    Hair    │
        │   Forge   │ │Forge │ │   Forge    │
        └─────┬─────┘ └──┬───┘ └──────┬─────┘
              │            │            │
              └────────┬──┴──┬─────────┘
                       │     │
              ┌────────┴─────┴────────┐
              │      Rig Forge         │
              │  (owns bone hierarchy) │
              └────────┬───────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
  │ Clothing  │ │   Expr    │ │  Physics  │
  │  Forge    │ │  Forge    │ │  Forge    │
  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
        │              │              │
        └──────────────┼─────────────┘
                       │
              ┌────────┴────────┐
              │  Texture Forge  │
              │ (headless,      │
              │  Pillow+NumPy)   │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │  Export Forge   │
              │  (VRM/GLB/BLEND)│
              └─────────────────┘
```

## Dependency Rules

1. **Spec is the single source of truth.** Every module reads from CharacterSpec. No module owns parameters that belong to another domain.
2. **Dependencies flow downward.** Body → Rig → Export. Never upward.
3. **Texture Forge is independent.** Pure Pillow + NumPy. No Blender dependency. Can run standalone.
4. **Blender Bridge is infrastructure.** Modules call Blender through the bridge, never directly.
5. **Export is a leaf.** It reads from all modules but owns nothing that other modules depend on.

## Cross-Domain Contracts

| From | To | Contract | Format |
|---|---|---|---|
| Spec | All | CharacterSpec dataclass | Python object |
| Body | Rig | Armature + skinned meshes | Blender scene |
| Body | Hair | Head bounding box | (min_x, min_y, min_z, max_x, max_y, max_z) |
| Body | Clothing | Body mesh + measurements | Blender mesh + dict |
| Rig | Expression | Bone names + armature | Blender armature |
| Texture | Export | PNG file paths | dict[name, Path] |
| All | Export | BuildResult | Python dataclass |