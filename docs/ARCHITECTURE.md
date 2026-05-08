# ᚺᚨᛗᚱ — Architecture

> *"A strong system is not one that can do everything. It is one that knows exactly what belongs where."*
> — Rúnhild Svartdóttir, Architect

## Layer 1: Vision → [SYSTEM_VISION.md](SYSTEM_VISION.md), [PHILOSOPHY.md](PHILOSOPHY.md)

## Layer 2: Domain Map

```
┌─────────────────────────────────────────────────────────────────┐
│                          HAMR CORE                              │
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │   Spec    │  │   Forge   │  │  Export   │  │    CLI    │  │
│  │  Domain   │  │  Domain   │  │  Domain   │  │  Domain   │  │
│  │           │  │           │  │           │  │           │  │
│  │ spec.py   │  │ forge.py  │  │ vrm.py    │  │ cli.py    │  │
│  │ models.py │  │ builder.py│  │ glb.py    │  │ commands/ │  │
│  │ validate  │  │ pipeline  │  │ inspect   │  │           │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │              │          │
│  ┌─────┴──────────────┴──────────────┴──────────────┴──────┐  │
│  │                    MODULE LAYER                           │  │
│  │  body/ face/ hair/ clothing/ rigs/ textures/ expressions │  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────────────┐  │
│  │                  BLENDER BRIDGE LAYER                    │  │
│  │  blender_runner.py  │  scene_manager.py  │  mesh_ops.py │  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────────────┐  │
│  │                   ASSET HOARD LAYER                      │  │
│  │  base_meshes/  │  textures/  │  rigs/  │  templates/   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Domain Boundaries

| Domain | Owns | Depends On | Never Reaches Into |
|---|---|---|---|
| **Spec** | CharacterSpec, ParameterDefaults, Validation | Nothing (leaf domain) | Blender, meshes, materials |
| **Body** | Base mesh loading, shape key morphing, proportion sliders | Spec, Blender Bridge | Hair, Clothing, Export |
| **Face** | Expression morphs, viseme mapping, eye config | Spec, Body (for face region) | Hair, Clothing |
| **Hair** | Procedural generation, shell layers, guide curves | Spec, Blender Bridge, Body (for head bound) | Face internals, Clothing |
| **Clothing** | Template fitting, material assignment, outfit switching | Spec, Body (for body mesh) | Hair, Face internals |
| **Rigs** | Bone mapping, VRM humanoid, auto-rig | Spec, Body | Hair generation, Textures |
| **Textures** | HSV shifts, procedural patterns, PBR maps | Spec, Pillow/NumPy | Blender (runs standalone) |
| **Export** | VRM 1.0 output, GLB, .blend, metadata patching | All modules, Blender Bridge | Parameter defaults |
| **CLI** | Command parsing, pipeline orchestration | All modules | Internal module logic |

## Data Contracts

### Spec → Forge (YAML)
```python
@dataclass
class CharacterSpec:
    name: str
    version: str = "1.0"
    body: BodySpec
    face: FaceSpec
    hair: HairSpec
    clothing: list[ClothingSpec]
    expressions: ExpressionSpec
    physics: PhysicsSpec
    export: ExportSpec

@dataclass
class BodySpec:
    height_cm: float = 173.0
    build: str = "athletic-slender"  # slug → preset
    skin: SkinSpec
    proportions: dict[str, float]  # named sliders

@dataclass
class SkinSpec:
    base_hex: str = "#E8B87A"
    undertone: str = "warm"
    freckles: bool = False
    tan_level: float = 0.7  # 0-1
```

### Forge → Export (Blender Scene)
```python
@dataclass
class BuildResult:
    armature: bpy.types.Object
    meshes: list[bpy.types.Object]
    materials: list[bpy.types.Material]
    textures: dict[str, Path]  # name → PNG path
    spec: CharacterSpec  # the spec that created this
```

### Export → File (VRM 1.0)
```python
@dataclass  
class ExportResult:
    vrm_path: Path
    glb_path: Path | None
    blend_path: Path | None
    compliance_report: ComplianceReport
    build_time_seconds: float
    poly_count: int
    bone_count: int
    expression_count: int
```

## File Structure

```
Hamr/
├── src/
│   └── hamr/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── spec.py          # CharacterSpec dataclasses
│       │   ├── models.py        # All spec models (body, face, hair, etc.)
│       │   ├── validate.py      # Spec validation
│       │   ├── textures.py      # Pillow/NumPy texture pipeline
│       │   └── constants.py     # Color defaults, bone maps, etc.
│       ├── body/
│       │   ├── __init__.py
│       │   ├── forge.py         # BodyForge class
│       │   └── presets.py       # Build presets (athletic, curvy, etc.)
│       ├── face/
│       │   ├── __init__.py
│       │   ├── forge.py         # FaceForge class
│       │   └── expressions.py   # Expression/viseme mapping
│       ├── hair/
│       │   ├── __init__.py
│       │   ├── forge.py         # HairForge class
│       │   ├── curly.py         # Curly hair generator
│       │   ├── straight.py      # Straight hair generator
│       │   └── braided.py       # Braided hair generator
│       ├── clothing/
│       │   ├── __init__.py
│       │   ├── forge.py         # ClothingForge class
│       │   └── templates.py     # Clothing template definitions
│       ├── rigs/
│       │   ├── __init__.py
│       │   ├── forge.py         # RigForge class
│       │   ├── humanoid.py      # VRM humanoid bone mapping
│       │   └── expressions.py   # VRM expression setup
│       ├── export/
│       │   ├── __init__.py
│       │   ├── forge.py         # ExportForge class
│       │   ├── vrm.py           # VRM 1.0 export
│       │   ├── glb.py           # GLB export
│       │   └── metadata.py      # Post-export GLB patching
│       └── blender_bridge/
│           ├── __init__.py
│           ├── runner.py        # Headless Blender subprocess
│           ├── scene.py         # Scene setup/teardown
│           └── mesh_ops.py      # Common mesh operations
├── docs/
│   ├── PHILOSOPHY.md
│   ├── SYSTEM_VISION.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_MAP.md
│   └── INTERFACE.md
├── examples/
│   ├── spec_runa_gridweaver.yaml
│   ├── spec_minimal.yaml
│   └── spec_batch_variant.yaml
├── assets/
│   ├── base_meshes/
│   ├── textures/
│   └── rigs/
├── tests/
│   ├── test_spec.py
│   ├── test_body_forge.py
│   └── test_export.py
├── pyproject.toml
└── README.md
```

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Spec format | YAML (primary) | Human-readable, commentable, agent-writable |
| Base mesh | Pluggable (MB-Lab default) | No lock-in; any mesh works |
| Texture pipeline | Pillow + NumPy (not Cycles) | Pi 5 ARM64 compatible, no GPU required |
| Blender API | Background mode subprocess | Headless-first, no GUI dependency |
| VRM export | VRM Addon for Blender | Proven, maintained, spec-compliant |
| Bone mapping | Explicit declaration (not auto) | D-008/D-018 lesson: auto-mapping overwrites correct mappings |
| Hair generation | Shell layers + guide curves | Proven in v5, avoids VRoid lock-in |
| Clothing | Template + fit system | Parametric, not hand-painted |
| Agent API | CLI + Python API + YAML spec | Three interfaces for three use patterns |