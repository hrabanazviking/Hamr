# ᚺᚨᛗᚱ — Phase 11 Architecture: Alvíssmál

> *"Every bone shall have a name. Every strand its place. Every fold shall drape true. Every vertex shall move smooth."*

---

## 1. Module Map

### 1.1 New Modules

```
src/hamr/
├── rigs/                          # WAS: empty __init__.py → NOW: full rig module
│   ├── __init__.py                # Public API: create_missing_bones, WeightPaintEngine, RigVerifier
│   ├── stub_bones.py              # G1: Create jaw/leftEye/rightEye stub bones
│   ├── weights.py                 # G4: Weight painting engine (smooth, normalize, quality score)
│   ├── verify.py                  # G5: VRM rig verification (bone count, expressions, spring bones)
│   └── spring_bones.py            # G8: VRM 1.0 spring bone groups
│
├── hair/
│   ├── __init__.py                # UPDATED: add HairForge class + keep resolve_hair()
│   ├── forge.py                   # G2: HairForge v2 — mesh hair generation dispatcher
│   ├── straight.py                # G2: Straight hair mesh generator
│   ├── curly.py                   # G2: Curly/spiral hair mesh generator
│   ├── wavy.py                    # G2: Wavy hair mesh generator
│   ├── bob.py                     # G2: Bob cut mesh generator
│   ├── ponytail.py                # G2: Ponytail mesh generator
│   ├── braided.py                 # G2: Braided hair mesh generator
│   └── utils.py                   # G2: Shared hair utilities (scalp region, curve ops, vertex colors)
│
├── clothing/
│   ├── __init__.py                # UPDATED: add ClothingForge class + keep resolve_clothing()
│   ├── forge.py                   # G3: ClothingForge v1 — mesh clothing generation
│   ├── patterns.py                # G3: Clothing pattern library (tshirt, shorts, skirt, dress, hoodie, uniform)
│   └── fit.py                     # G3: Shrinkwrap fitting + weight paint transfer
│
├── export/
│   ├── __init__.py                # No change
│   ├── vrm.py                     # UPDATED: spring bones, first-person annotations
│   └── glb.py                     # No change
│
└── cli/
    └── verify_rig.py              # G5: `hamr verify-rig` CLI command

assets/
└── presets/                       # G6: Character preset YAML files
    ├── casual_m.yaml
    ├── casual_f.yaml
    ├── student_m.yaml
    ├── student_f.yaml
    ├── fantasy_m.yaml
    └── fantasy_f.yaml
```

### 1.2 Modified Modules

```
src/hamr/
├── core/
│   ├── models.py                  # ADD: SpringBoneSpec, FirstPersonSpec to CharacterSpec
│   ├── constants.py               # ADD: STUB_BONE_DEFS, SCALP_VERTEX_MAP, CLOTHING_REGION_MAP
│   └── pipeline.py                # MOD: stub bone step, hair mesh step, clothing mesh step, spring bone step
│
├── blender_bridge/
│   ├── runner.py                  # MOD: add timeout guard (120s default), cleanup on timeout
│   ├── scene.py                   # MOD: add memory-conscious cleanup helpers
│   └── mesh_ops.py                # ADD: transfer_weights(), parent_to_bone(), separate_region()
│
├── hair/__init__.py               # MOD: export HairForge alongside resolve_hair
├── clothing/__init__.py           # MOD: export ClothingForge alongside resolve_clothing
├── rigs/__init__.py               # MOD: full public API (was just re-exports)
├── scripts/build_avatar.py        # MOD: integrate stub bones, hair mesh, clothing mesh, weight paint, spring bones
└── cli.py                         # MOD: add verify-rig subcommand, --preset flag to build
```

---

## 2. Data Flow Diagrams

### 2.1 G1: Stub Bone Creation Flow

```
CharacterSpec
     │
     ▼
┌─────────────────────┐
│  MB-Lab Generate     │  _generate_mblab_base()
│  (22 bones present)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────┐
│  stub_bones.create_missing_bones()  │
│  ┌─────────────────────────┐ │
│  │ 1. Scan armature for    │ │
│  │    existing bones       │ │
│  │ 2. Compute missing:    │ │
│  │    jaw → chin verts    │ │
│  │    leftEye → L eye     │ │
│  │    rightEye → R eye    │ │
│  │ 3. Create stub bones   │ │
│  │    parented to head    │ │
│  │ 4. Tag _hamr_stub=True │ │
│  │ 5. Return bone_map     │ │
│  └─────────────────────────┘ │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  VRM Humanoid Mapping       │
│  (uses merged MB_LAB_BONE_MAP  │
│   + stub bone map)          │
│  → 25/25 bones              │
└─────────────────────────────┘
```

### 2.2 G2: Hair Mesh Generation Flow

```
HairSpec
     │
     ├── style ──────────► HairForge.generate()
     │                      ┌──────────────────────┐
     │                      │ Style dispatcher:     │
     │                      │  "straight" → straight.py
     │                      │  "wavy"     → wavy.py
     │                      │  "curly"    → curly.py
     │                      │  "braided"  → braided.py
     │                      │  "ponytail" → ponytail.py
     │                      │  "bun"      → bob.py (variant)
     │                      │  "wild-curly"→ curly.py
     │                      └──────────┬───────────┘
     │                                 │
     │                      ┌──────────▼───────────┐
     │                      │ Shared pipeline:       │
     │                      │ 1. Derive scalp region│
     │                      │    (vertex group or   │
     │                      │     UV zone)           │
     │                      │ 2. Generate guide     │
     │                      │    curves on scalp    │
     │                      │ 3. Apply style mod    │
     │                      │    (curl freq, wave   │
     │                      │     amp, braid pattern)│
     │                      │ 4. Sweep curves → mesh│
     │                      │ 5. Apply length param │
     │                      │ 6. Apply volume       │
     │                      │    (array + jitter)   │
     │                      │ 7. Parent to head    │
     │                      │    bone               │
     │                      └──────────┬───────────┘
     │                                 │
     ├── color ───────────────────────┤
     │                      ┌──────────▼───────────┐
     │                      │ HairForge.apply_colors│
     │                      │  roots→mid→tips      │
     │                      │  vertex color gradient│
     │                      │  (or HSV texture)    │
     │                      └──────────────────────┘
     │
     ├── physics ─────────► spring_bones.configure_hair_spring()
     │                      (stiffness, gravity, drag)
     │
     └── length/volume ──► parameters fed into step 5/6 above
```

### 2.3 G3: Clothing Mesh Generation Flow

```
ClothingSpec
     │
     ▼
┌──────────────────────────────┐
│ ClothingForge.generate()      │
│  ┌──────────────────────────┐ │
│  │ 1. Select pattern:       │ │
│  │    tshirt / shorts /     │ │
│  │    skirt / dress /       │ │
│  │    hoodie / school_...   │ │
│  │ 2. Define region masks  │ │
│  │    (vertex groups from   │ │
│  │     body mesh)           │ │
│  │ 3. Duplicate region      │ │
│  │ 4. Offset along normals │ │
│  │    (garment thickness)  │ │
│  │ 5. Shrinkwrap to body   │ │
│  │ 6. Assign clothing mat  │ │
│  │ 7. Copy weight paint    │ │
│  │    from body vertex grps │ │
│  │ 8. Clean up mesh        │ │
│  └──────────────────────────┘ │
└──────────────────────────────┘

patterns.py ──► CLOTHING_PATTERNS dict
                  Each pattern = {
                    "regions": ["torso", "upper_arms"],
                    "offset": 0.005,    # meters from skin
                    "seam_groups": {...},
                    "default_material": "fabric",
                  }
```

### 2.4 G4: Weight Painting Flow

```
Body mesh + Armature
     │
     ▼
┌──────────────────────────────────┐
│ WeightPaintEngine.paint_smooth() │
│  ┌────────────────────────────┐  │
│  │ 1. Run bpy.ops.object      │  │
│  │    .parent_with_auto_weights│  │
│  │    (baseline weights)      │  │
│  │ 2. For each joint region:  │  │
│  │    neck, shoulders, hips,   │  │
│  │    knees, elbows, wrists   │  │
│  │  ┌──────────────────────┐  │  │
│  │  │ 3. Smooth weights   │  │  │
│  │  │    at boundaries     │  │  │
│  │  │ 4. Ensure ≥3 groups │  │  │
│  │  │    per boundary vert │  │  │
│  │  │ 5. Normalize all     │  │  │
│  │  │    vertex groups     │  │  │
│  │  └──────────────────────┘  │  │
│  │ 6. Apply max_influence   │  │
│  │    limit (no rigid 1-bone)│  │
│  └────────────────────────────┘  │
│                                  │
│  apply to hair mesh & clothing   │
│  via transfer_weights()          │
└──────────────────────────────────┘
```

### 2.5 G5: Rig Verification Flow

```
VRM file path
     │
     ▼
┌──────────────────────────────────┐
│ RigVerifier.verify(vrm_path)     │
│  ┌────────────────────────────┐  │
│  │ 1. Parse glTF binary      │  │
│  │ 2. Check VRM extension    │  │
│  │ 3. Count humanoid bones   │  │
│  │    (expect 25 required)   │  │
│  │ 4. List missing bones     │  │
│  │ 5. Check expressions      │  │
│  │ 6. Check lookAt config    │  │
│  │ 7. Check spring bone grps │  │
│  │ 8. Check first-person     │  │
│  │ 9. Estimate weight paint  │  │
│  │    quality score           │  │
│  └────────────────────────────┘  │
│                                  │
│  Returns RigReport dataclass     │
│  ├── humanoid_bone_count: int   │
│  ├── missing_bones: list[str]    │
│  ├── expression_count: int       │
│  ├── look_at_mode: str           │
│  ├── spring_bone_groups: int      │
│  ├── first_person: bool          │
│  ├── weight_paint_score: float   │
│  ├── errors: list[str]           │
│  └── warnings: list[str]         │
│                                  │
│  to_cli() → formatted table      │
│  to_json() → structured dict      │
└──────────────────────────────────┘
```

### 2.6 G7: Performance Optimization Flow

```
BuildPipeline.build()
     │
     ▼
┌──────────────────────────────────┐
│ 1. Spec Parse                     │  ← pure Python, ~10ms
│ 2. Forge Resolution               │  ← pure Python, ~5ms
│ 3. JSON Serialization             │  ← pure Python, ~2ms
│ 4. Blender Subprocess             │
│    ┌──────────────────────────┐   │
│    │ a. Scene setup            │   │
│    │ b. MB-Lab generate        │   │  ← bulk of time
│    │ c. Apply spec             │   │
│    │ d. Create stub bones      │   │  ← NEW, ~50ms
│    │ e. Generate hair mesh     │   │  ← NEW, ~500ms budget
│    │ f. Generate clothing mesh │   │  ← NEW, ~300ms budget
│    │ g. Smooth weight paint    │   │  ← NEW, ~200ms budget
│    │ h. Configure spring bones │   │  ← NEW, ~10ms
│    │ i. Configure first-person │   │  ← NEW, ~5ms
│    │ j. VRM export              │   │
│    └──────────────────────────┘   │
│ 5. Verification                   │  ← zip inspection, ~5ms
│ 6. Cleanup                       │
└──────────────────────────────────┘

Pi 5 Budget: total < 45s, peak RSS < 1.5GB

Optimizations:
- Lazy texture: only generate textures the spec requests
- Blender timeout: 120s hard kill with process cleanup
- Hair: max_triangle budget per style (decimation if exceeded)
- Clothing: decimation after shrinkwrap
- Memory: purge_orphans() between major steps
```

### 2.7 G8: VRM 1.0 Compliance Flow

```
After _apply_spec() in build_avatar.py:
     │
     ├── stub_bones step ──► 25/25 bones
     │
     ├── hair mesh step ─────► mesh object parented to head
     │
     ├── spring_bones step:
     │    spring_bones.configure_spring_groups(armature, hair_obj, physics)
     │    ┌──────────────────────────────────┐
     │    │ VRM1 springBone.springBoneGroups  │
     │    │  ┌─ group "hair_spring"           │
     │    │  │  stiffiness: 0.35              │
     │    │  │  gravityPower: 0.3             │
     │    │  │  dragForce: 0.4                │
     │    │  │  colliderGroups: []            │
     │    │  │  bones: [hair_root→end chain]  │
     │    │  └────────────────────────────── │
     │    └──────────────────────────────────┘
     │
     └── first_person step:
          first_person.configure(armature, mesh_obj)
          ┌──────────────────────────────────┐
          │ VRM1.firstPerson                 │
          │  meshAnnotations:                 │
          │    - head: mesh renderers → THIRD │
          │    - body: mesh renderers → AUTO  │
          └──────────────────────────────────┘
```

---

## 3. Interface Contracts

### 3.1 `hamr/rigs/stub_bones.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class StubBoneResult:
    """Result from stub bone creation."""
    created_bones: dict[str, str]  # VRM bone name → Blender bone name
    existing_bones: list[str]       # Bones that already existed
    armature_name: str

def create_missing_bones(
    armature_name: str,
    base_type: str = "mblab",
) -> StubBoneResult:
    """
    Create stub bones for VRM 1.0 required humanoid bones
    that don't exist in the base mesh armature.

    Must run inside Blender (bpy available).

    Strategy (AD-11.1):
    - jaw: Rooted at average of chin vertices, parented to head,
            0.5cm length, tagged _hamr_stub=True
    - leftEye: Rooted at left eye vertex center, parented to head,
               0.5cm length, tagged _hamr_stub=True
    - rightEye: Rooted at right eye vertex center, parented to head,
                0.5cm length, tagged _hamr_stub=True

    Args:
        armature_name: Name of armature object in Blender scene.
        base_type: "mblab" or "turbosquid" — determines vertex group
                   naming conventions for finding head/eye positions.

    Returns:
        StubBoneResult with created bone mappings and metadata.
    """

def find_vertex_center(
    mesh_obj: Any,
    vertex_group_name: str,
) -> tuple[float, float, float]:
    """
    Find the center position of vertices in a named vertex group.

    Used to position stub bones accurately on the mesh.

    Args:
        mesh_obj: Blender mesh object.
        vertex_group_name: Name of vertex group to find center of.

    Returns:
        (x, y, z) world-space coordinates of the vertex group center.
    """
```

### 3.2 `hamr/rigs/weights.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

# Joint regions that need smooth weight transitions
SMOOTH_REGIONS: dict[str, list[str]] = {
    "neck": ["head", "neck", "spine_02", "spine_03"],
    "left_shoulder": ["clavicle_L", "upper_arm_L", "spine_02"],
    "right_shoulder": ["clavicle_R", "upper_arm_R", "spine_02"],
    "left_hip": ["thigh_L", "pelvis", "spine"],
    "right_hip": ["thigh_R", "pelvis", "spine"],
    "left_knee": ["thigh_L", "calf_L", "shin_L"],
    "right_knee": ["thigh_R", "calf_R", "shin_R"],
    "left_elbow": ["upper_arm_L", "forearm_L", "lowerarm_L"],
    "right_elbow": ["upper_arm_R", "forearm_R", "lowerarm_R"],
}

@dataclass
class WeightPaintReport:
    """Quality report for weight painting."""
    avg_groups_per_vertex: float
    min_groups_per_vertex: int
    max_weight_variance: float
    normalization_rate: float  # fraction of verts summing to 1.0
    score: float              # 0.0–1.0 composite quality score

class WeightPaintEngine:
    """Automatic weight painting for smooth deformations (AD-11.4)."""

    def paint_smooth(
        self,
        obj: Any,
        armature: Any,
        regions: list[str] | None = None,
        iterations: int = 3,
        min_influence_groups: int = 3,
    ) -> None:
        """
        Apply smooth weight painting to specified regions.

        Must run inside Blender.

        Pipeline:
        1. Use Blender's automatic weights as baseline
        2. For each region boundary, smooth weights across joints
        3. Ensure every boundary vertex has ≥ min_influence_groups
        4. Normalize all vertex groups to sum to 1.0
        5. Apply max_influence limits to prevent rigid single-bone areas

        Args:
            obj: Blender mesh object to paint.
            armature: Blender armature object (source of vertex groups).
            regions: Region names from SMOOTH_REGIONS keys. None = all.
            iterations: Number of smooth iterations per region.
            min_influence_groups: Minimum vertex groups per boundary vertex.
        """

    def transfer_weights(
        self,
        source_obj: Any,
        target_obj: Any,
        armature: Any,
    ) -> None:
        """
        Transfer weight paint from body mesh to clothing/hair mesh.

        Uses Blender's data transfer modifier for vertex group mapping.

        Args:
            source_obj: Body mesh with existing vertex groups.
            target_obj: Clothing/hair mesh to receive weights.
            armature: Armature object (for bone name mapping).
        """

    def get_quality_score(self, obj: Any) -> WeightPaintReport:
        """
        Compute weight paint quality score (AD-11.4).

        Score formula:
        - 0.4 * (avg_groups_per_vertex / 4.0), capped at 1.0
        - 0.3 * normalization_rate
        - 0.3 * (1.0 - max_weight_variance)

        A score ≥ 0.7 means PASS.

        Args:
            obj: Blender mesh object to score.

        Returns:
            WeightPaintReport with detailed metrics.
        """
```

### 3.3 `hamr/rigs/verify.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# VRM 1.0 required humanoid bones (the 25 we map)
VRM_REQUIRED_HUMANOID_BONES: list[str] = [
    "hips", "spine", "chest", "upperChest", "neck", "head",
    "leftUpperLeg", "rightUpperLeg",
    "leftLowerLeg", "rightLowerLeg",
    "leftFoot", "rightFoot",
    "leftToes", "rightToes",
    "leftShoulder", "rightShoulder",
    "leftUpperArm", "rightUpperArm",
    "leftLowerArm", "rightLowerArm",
    "leftHand", "rightHand",
    "jaw", "leftEye", "rightEye",
]

@dataclass
class RigReport:
    """Complete rig verification report."""
    vrm_path: Path
    humanoid_bone_count: int
    expected_bone_count: int = 25
    missing_bones: list[str] = field(default_factory=list)
    extra_bones: list[str] = field(default_factory=list)
    expression_count: int = 0
    expression_names: list[str] = field(default_factory=list)
    look_at_mode: str = "unknown"
    spring_bone_group_count: int = 0
    spring_bone_names: list[str] = field(default_factory=list)
    first_person_annotations: bool = False
    weight_paint_score: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        """True if no errors (warnings are OK)."""
        return len(self.errors) == 0

    @property
    def exit_code(self) -> int:
        """0=compliant, 1=warnings, 2=failures."""
        if self.errors:
            return 2
        if self.warnings:
            return 1
        return 0

class RigVerifier:
    """Verify VRM rig compliance (G5)."""

    def verify(self, vrm_path: str | Path) -> RigReport:
        """
        Check a VRM file for rig compliance.

        Parses the glTF binary directly (no Blender needed).
        Extracts VRM 1.0 extension data.

        Args:
            vrm_path: Path to the .vrm file.

        Returns:
            RigReport with full compliance details.
        """

    def to_cli(self, report: RigReport) -> str:
        """
        Format a RigReport for terminal output with colors and symbols.

        Args:
            report: The verification report.

        Returns:
            Formatted string suitable for terminal output.
        """

    def to_json(self, report: RigReport) -> dict[str, Any]:
        """
        Convert a RigReport to a JSON-serializable dict.

        Args:
            report: The verification report.

        Returns:
            Dict suitable for json.dumps().
        """
```

### 3.4 `hamr/rigs/spring_bones.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class SpringBoneConfig:
    """Configuration for a VRM 1.0 spring bone group."""
    group_name: str
    stiffness: float = 0.35
    gravity_power: float = 0.3
    drag_force: float = 0.4
    hit_radius: float = 0.02
    center_bone_name: str = ""    # Optional center bone for local space
    collider_bone_names: list[str] = field(default_factory=list)

def configure_hair_spring(
    armature_name: str,
    hair_object_name: str,
    physics_config: dict[str, float] | None = None,
) -> list[str]:
    """
    Configure VRM 1.0 spring bone groups for hair.

    Creates bone groups from the hair object's vertex-to-bone
    assignment chain, starting from the head bone connection.

    Must run inside Blender.

    Args:
        armature_name: Name of armature with VRM extension.
        hair_object_name: Name of hair mesh object.
        physics_config: Dict with stiffness, gravity, drag, hit_radius.

    Returns:
        List of created spring bone group names.
    """

def configure_breast_spring(
    armature_name: str,
    physics_config: dict[str, float] | None = None,
) -> list[str]:
    """
    Configure VRM 1.0 spring bone for breast physics.

    Args:
        armature_name: Name of armature.
        physics_config: Override physics values.

    Returns:
        List of created spring bone group names.
    """
```

### 3.5 `hamr/hair/forge.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class HairMeshResult:
    """Result from mesh hair generation."""
    object_name: str                   # Blender object name
    bone_chain: list[str]              # Bones in hair chain (for spring bones)
    vertex_count: int
    triangle_count: int
    style: str

class HairForge:
    """
    Procedural mesh hair generation engine (AD-11.2).

    Pipeline: HairSpec → guide_curves() → style_modifier() →
              to_mesh() → vertex_colors() → parent_to_head()
    """

    def generate(
        self,
        spec: HairSpec,
        head_mesh_name: str,
        armature_name: str,
    ) -> HairMeshResult:
        """
        Generate mesh hair from spec parameters.

        Dispatches to style-specific generator:
        - "straight" → straight.generate()
        - "wavy" → wavy.generate()
        - "curly" / "wild-curly" → curly.generate()
        - "braided" → braided.generate()
        - "ponytail" → ponytail.generate()
        - "bun" → bob.generate()  (variant)
        - "bob" → bob.generate()

        Must run inside Blender.

        Args:
            spec: HairSpec with style, length, volume, color, curl.
            head_mesh_name: Name of head mesh for scalp reference.
            armature_name: Name of armature for parenting.

        Returns:
            HairMeshResult with generated hair info.
        """

    def apply_colors(
        self,
        hair_obj_name: str,
        spec: HairSpec,
    ) -> None:
        """
        Apply root→mid→tip gradient via vertex colors.

        Must run inside Blender.

        Args:
            hair_obj_name: Name of hair mesh object.
            spec: HairSpec with color.roots, color.mid, color.tips.
        """
```

### 3.6 `hamr/hair/utils.py`

```python
from __future__ import annotations
from typing import Any

# Scalp vertex group names by base mesh type
SCALP_GROUPS: dict[str, list[str]] = {
    "mblab": ["scalp", "head_mesh"],
    "turbosquid": ["scalp", "Head"],
}

# Hair length scale factors (meters, relative to head height)
HAIR_LENGTH_SCALE: dict[str, float] = {
    "short": 0.05,
    "medium": 0.12,
    "shoulder": 0.18,
    "shoulder-plus": 0.25,
    "long": 0.35,
    "very-long": 0.50,
}

def get_scalp_vertices(
    mesh_obj: Any,
    base_type: str = "mblab",
) -> list[int]:
    """
    Return indices of vertices in the scalp region.

    Tries named vertex groups first, falls back to UV-based
    zone detection (top of head).

    Args:
        mesh_obj: Head mesh Blender object.
        base_type: "mblab" or "turbosquid".

    Returns:
        List of vertex indices in the scalp region.
    """

def generate_guide_curves(
    scalp_indices: list[int],
    mesh_obj: Any,
    density: float = 1.0,
) -> list[dict]:
    """
    Generate guide curve starting positions and directions.

    Each guide curve is a dict with:
        "origin": (x, y, z) start position
        "direction": (x, y, z) growth direction (normal)
        "group_index": int for UV/seam grouping

    Args:
        scalp_indices: Vertex indices on the scalp.
        mesh_obj: Head mesh for position/normal data.
        density: 0.0–1.0, controls how many guides to generate.

    Returns:
        List of guide curve dicts.
    """

def curve_to_mesh(
    curve_obj: Any,
    resolution: int = 4,
) -> Any:
    """
    Convert a Blender Bezier curve to a mesh object.

    Handles: round/bevel profile, UV mapping for gradient colors.

    Args:
        curve_obj: Blender curve object.
        resolution: Bevel resolution (higher = smoother, more triangles).

    Returns:
        Mesh object (new, linked to current collection).
    """

def apply_vertex_gradient(
    mesh_obj: Any,
    roots_hsv: tuple[float, float, float],
    mid_hsv: tuple[float, float, float],
    tips_hsv: tuple[float, float, float],
    root_ratio: float = 0.15,
    tip_ratio: float = 0.25,
) -> None:
    """
    Apply root→mid→tip vertex color gradient based on vertex
    Y-coordinate (height from head).

    Args:
        mesh_obj: Hair mesh object.
        roots_hsv: (h, s, v) for roots.
        mid_hsv: (h, s, v) for mid-shaft.
        tips_hsv: (h, s, v) for tips.
        root_ratio: Fraction of bottom vertices treated as "root".
        tip_ratio: Fraction of top vertices treated as "tip".
    """

def decimate_mesh(
    mesh_obj: Any,
    max_triangles: int,
) -> int:
    """
    Decimate a mesh to stay within triangle budget.

    Uses Blender's decimate modifier. Returns final triangle count.

    Args:
        mesh_obj: Mesh to decimate.
        max_triangles: Maximum allowed triangle count.

    Returns:
        Final triangle count after decimation.
    """
```

### 3.7 `hamr/clothing/forge.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ClothingMeshResult:
    """Result from mesh clothing generation."""
    object_name: str
    pattern_name: str
    triangle_count: int
    vertex_count: int

class ClothingForge:
    """
    Parametric clothing generation (AD-11.3).

    Pipeline: ClothingSpec → region_select(body) → separate →
              offset → shrinkwrap → material_assign → weight_paint_copy
    """

    def generate(
        self,
        spec: ClothingSpec,
        body_mesh_name: str,
        armature_name: str,
    ) -> ClothingMeshResult:
        """
        Generate clothing mesh from spec.

        Must run inside Blender.

        Args:
            spec: ClothingSpec with type, colors, name.
            body_mesh_name: Body mesh to fit clothing to.
            armature_name: Armature for weight paint transfer.

        Returns:
            ClothingMeshResult with generated clothing info.
        """

    def generate_from_pattern(
        self,
        pattern_name: str,
        body_mesh_name: str,
        armature_name: str,
        offset: float = 0.005,
        material_override: dict | None = None,
    ) -> ClothingMeshResult:
        """
        Generate clothing from a named pattern (more control).

        Args:
            pattern_name: Key from CLOTHING_PATTERNS dict.
            body_mesh_name: Body mesh to fit.
            armature_name: Armature for weights.
            offset: Distance from skin surface (meters).
            material_override: Override material properties.

        Returns:
            ClothingMeshResult.
        """
```

### 3.8 `hamr/clothing/patterns.py`

```python
from __future__ import annotations
from typing import Any

# Each pattern defines which body regions to cover,
# offset from skin, and default material properties.
CLOTHING_PATTERNS: dict[str, dict] = {
    "tshirt": {
        "regions": ["torso", "upper_arms"],
        "offset": 0.004,
        "seam_groups": {
            "collar": "neck",
            "sleeve_left": "left_upper_arm",
            "sleeve_right": "right_upper_arm",
            "hem": "waist",
        },
        "default_material": "fabric",
        "hem_width": 0.01,
    },
    "shorts": {
        "regions": ["hips", "upper_legs"],
        "offset": 0.004,
        "seam_groups": {
            "waistband": "waist",
            "hem_left": "left_knee",
            "hem_right": "right_knee",
        },
        "default_material": "fabric",
        "hem_width": 0.01,
    },
    "skirt": {
        "regions": ["hips", "legs"],
        "offset": 0.006,
        "seam_groups": {
            "waistband": "waist",
            "hem": "knees",
        },
        "default_material": "fabric",
        "hem_width": 0.015,
        "flare": 0.3,
    },
    "dress": {
        "regions": ["torso", "hips", "legs"],
        "offset": 0.005,
        "seam_groups": {
            "collar": "neck",
            "hem": "ankles",
        },
        "default_material": "fabric",
        "hem_width": 0.015,
        "flare": 0.2,
    },
    "hoodie": {
        "regions": ["torso", "arms"],
        "offset": 0.006,
        "seam_groups": {
            "collar": "neck",
            "cuff_left": "left_wrist",
            "cuff_right": "right_wrist",
            "hem": "waist",
            "hood": "head",
        },
        "default_material": "fabric",
        "hem_width": 0.01,
    },
    "school_uniform": {
        "regions": ["torso", "arms", "hips", "upper_legs"],
        "offset": 0.004,
        "seam_groups": {
            "collar": "neck",
            "blazer_hem": "waist",
            "skirt_hem": "knees",
        },
        "default_material": "fabric",
        "hem_width": 0.008,
    },
}

# Body vertex group name mapping by base mesh type
BODY_REGION_VERTEX_GROUPS: dict[str, dict[str, list[str]]] = {
    "mblab": {
        "torso": ["body", "torso", "chest"],
        "upper_arms": ["upperarm_L", "upperarm_R", "arm"],
        "hips": ["pelvis", "hips"],
        "upper_legs": ["thigh_L", "thigh_R", "leg"],
        "legs": ["thigh_L", "thigh_R", "calf_L", "calf_R"],
        "neck": ["neck"],
        "head": ["head"],
    },
    "turbosquid": {
        "torso": ["Body", "Spine02", "Spine03"],
        "upper_arms": ["L_UpperArm", "R_UpperArm"],
        "hips": ["Hip", "Spine01"],
        "upper_legs": ["L_Thigh", "R_Thigh"],
        "legs": ["L_Thigh", "R_Thigh", "L_Calf", "R_Calf"],
        "neck": ["NeckTwist"],
        "head": ["Head"],
    },
}
```

### 3.9 `hamr/clothing/fit.py`

```python
from __future__ import annotations
from typing import Any

def shrinkwrap_clothing(
    clothing_obj: Any,
    body_obj: Any,
    offset: float = 0.005,
) -> None:
    """
    Apply shrinkwrap modifier to fit clothing mesh to body.

    Uses Blender's Shrinkwrap modifier to conform the clothing
    mesh to the body surface. Applies and removes the modifier.

    Must run inside Blender.

    Args:
        clothing_obj: The clothing mesh to fit.
        body_obj: The target body mesh to wrap to.
        offset: Distance from body surface in meters.
    """

def transfer_weights_to_clothing(
    clothing_obj: Any,
    body_obj: Any,
    armature_obj: Any,
) -> None:
    """
    Transfer vertex group weights from body to clothing.

    Uses Blender's Data Transfer modifier for nearest-vertex
    weight transfer, then applies.

    Args:
        clothing_obj: Clothing mesh receiving weights.
        body_obj: Body mesh donating weights.
        armature_obj: Armature for bone group naming.
    """

def separate_body_region(
    body_obj: Any,
    region_names: list[str],
    base_type: str = "mblab",
) -> Any:
    """
    Select and separate body vertices corresponding to a clothing region.

    Args:
        body_obj: Body mesh to select from.
        region_names: Region keys from BODY_REGION_VERTEX_GROUPS.
        base_type: Vertex group naming convention.

    Returns:
        New mesh object with selected vertices separated from body.
    """
```

### 3.10 `hamr/export/first_person.py` (new file added to export/)

```python
from __future__ import annotations
from typing import Any

def configure_first_person(
    armature_name: str,
    mesh_names: list[str],
    head_bone_name: str = "head",
) -> None:
    """
    Configure VRM 1.0 first-person mesh annotations.

    Sets mesh visibility for VRChat's first-person camera:
    - Head mesh: THIRD_PERSON_ONLY (invisible in first-person)
    - Body meshes: AUTO (visible based on distance)

    Must run inside Blender.

    Args:
        armature_name: Armature with VRM extension.
        mesh_names: List of mesh object names in the scene.
        head_bone_name: Name of the head bone for head detection.
    """
```

### 3.11 `hamr/cli/verify_rig.py`

```python
"""CLI command: hamr verify-rig"""
from __future__ import annotations
from pathlib import Path

def cmd_verify_rig(args) -> int:
    """
    Verify a VRM file for rig compliance.

    Usage:
        hamr verify-rig avatar.vrm           # Full verification
        hamr verify-rig avatar.vrm --json    # JSON output
        hamr verify-rig avatar.vrm --quiet   # Exit code only (0/1/2)

    Exit codes:
        0 = compliant (no errors)
        1 = warnings (compliant but with issues)
        2 = failures (missing bones, broken rig)
    """
```

---

## 4. Modification List

### 4.1 `src/hamr/core/models.py`

**Changes:**
- Add `SpringBoneGroup` dataclass
- Add `FirstPersonSpec` dataclass
- Add `spring_bones` and `first_person` fields to `CharacterSpec`

```python
@dataclass
class SpringBoneGroupSpec:
    """Configuration for one spring bone group."""
    name: str = "hair_spring"
    stiffness: float = 0.35
    gravity_power: float = 0.3
    drag_force: float = 0.4
    hit_radius: float = 0.02

@dataclass
class FirstPersonSpec:
    """VRM 1.0 first-person annotation configuration."""
    hide_head_mesh: bool = True
    render_type: str = "auto"  # auto, firstPersonOnly, thirdPersonOnly

# Added to CharacterSpec:
# spring_bones: list[SpringBoneGroupSpec] = field(default_factory=list)
# first_person: FirstPersonSpec = field(default_factory=FirstPersonSpec)
```

### 4.2 `src/hamr/core/constants.py`

**Changes:**
- Add `STUB_BONE_DEFS` — dict of VRM bone name → {parent, position_method, length}
- Add `SCALP_VERTEX_MAP` — vertex group names for scalp by base type
- Add `CLOTHING_REGION_MAP` — body region → vertex group names by base type
- Add `HAIR_TRIANGLE_BUDGETS` — max triangle counts per style for Pi performance
- Add `PERFORMANCE_LIMITS` — memory and time budgets

### 4.3 `src/hamr/core/pipeline.py`

**Changes to `BuildPipeline.build()`:**
- After MB-Lab generation and before VRM export, add steps:
  1. Call `stub_bones.create_missing_bones()` → inject stub bones
  2. Call `HairForge.generate()` → create hair mesh
  3. Call `ClothingForge.generate()` → create clothing meshes
  4. Call `WeightPaintEngine.paint_smooth()` → smooth weights
  5. Call `spring_bones.configure_hair_spring()` → VRM spring bones
  6. Call `first_person.configure_first_person()` → VRM FP annotations
- All new steps are Blender-side, called within `build_avatar.py`
- Python-side `resolve_hair()` and `resolve_clothing()` stay config-only — the Blender-side does the mesh generation

**Changes to `BuildPipeline`:**
- Add `blender_timeout` default of 120 (down from 600 for Pi 5; raise via CLI flag)
- Add memory cleanup calls between major Blender operations

### 4.4 `src/hamr/scripts/build_avatar.py`

**Changes to `main()`:**
- After `_apply_spec()`, add new steps before VRM export:
  1. `_create_stub_bones(bpy)` → inject jaw, leftEye, rightEye
  2. `_generate_hair_mesh(bpy, spec_data, forge_config)` → create hair mesh from forge config
  3. `_generate_clothing_mesh(bpy, spec_data, forge_config)` → create clothing meshes
  4. `_smooth_weights(bpy)` → smooth weight painting
  5. `_configure_spring_bones(bpy, spec_data)` → VRM spring bones
  6. `_configure_first_person(bpy, spec_data)` → VRM FP annotations
- Add `--preset` argument support for reading from `assets/presets/`

### 4.5 `src/hamr/hair/__init__.py`

**Changes:**
- Keep existing `resolve_hair()` function (config-only, pure Python)
- Add import of `HairForge` class (for Blender-side mesh generation)

### 4.6 `src/hamr/clothing/__init__.py`

**Changes:**
- Keep existing `resolve_clothing()` function (config-only, pure Python)
- Add import of `ClothingForge` class (for Blender-side mesh generation)

### 4.7 `src/hamr/rigs/__init__.py`

**Changes:**
- Replace bare re-exports with full module API
- Export: `create_missing_bones`, `WeightPaintEngine`, `RigVerifier`, `WeightPaintReport`, `RigReport`, `StubBoneResult`

### 4.8 `src/hamr/blender_bridge/mesh_ops.py`

**Changes:**
- Add `transfer_weights()` function
- Add `parent_to_bone()` function
- Add `separate_region()` function
- Add `decimate_to_budget()` function
- All use `bpy` guarded by `BLENDER_AVAILABLE` check

### 4.9 `src/hamr/blender_bridge/runner.py`

**Changes:**
- Default `timeout` reduced from 600 → 120 for Pi 5
- Add `_cleanup_subprocess()` helper that kills orphan Blender processes
- Add memory warning in `run_blender_script()` result when stderr contains "Memory"

### 4.10 `src/hamr/cli.py`

**Changes:**
- Add `verify-rig` subcommand (calls `cmd_verify_rig` from `hamr.cli.verify_rig`)
- Add `--preset` flag to `build` command (reads from `assets/presets/`)
- Add `--blender-timeout` flag with default 120

### 4.11 `src/hamr/export/vrm.py`

**Changes:**
- Add `setup_spring_bones()` function
- Add `setup_first_person()` function
- The `MB_LAB_BONE_MAP` already includes jaw/leftEye/rightEye — verify and extend if needed

### 4.12 `src/hamr/export/__init__.py`

**Changes:**
- Add import of `first_person` module

### 4.13 New file: `src/hamr/rigs/spring_bones.py`

New module — see Interface Contracts 3.4.

### 4.14 New file: `src/hamr/export/first_person.py`

New module — see Interface Contracts 3.10.

---

## 5. Testing Strategy

### 5.1 Test Organization

```
tests/
├── test_phase11_stubs.py      # G1: Stub bone creation
├── test_phase11_hair.py        # G2: Hair mesh generation
├── test_phase11_clothing.py    # G3: Clothing mesh generation
├── test_phase11_weights.py     # G4: Weight painting
├── test_phase11_verify.py      # G5: Rig verification
├── test_phase11_presets.py     # G6: Preset loading and building
├── test_phase11_perf.py        # G7: Performance budget tests
└── test_phase11_compliance.py  # G8: VRM 1.0 compliance
```

### 5.2 G1: Stub Bones — Test Strategy

**Unit tests (no Blender):**
- `test_stub_bone_defs_complete`: Verify STUB_BONE_DEFS has entries for jaw, leftEye, rightEye
- `test_stub_bone_parent_is_head`: Verify all stubs parent to "head" bone
- `test_stub_bone_tag_property`: Verify _hamr_stub custom property tagging

**Integration tests (Blender required, marks `blender`):**
- `test_create_missing_bones_creates_3_stubs`: After MB-Lab generation, create_missing_bones() adds exactly 3 new bones
- `test_vrm_has_humanoid_bones_25`: Exported VRM has all 25 humanoid bones mapped
- `test_turbosquid_no_regression`: TurboSquid base (which has 25 already) doesn't create duplicate stubs

### 5.3 G2: Hair Mesh — Test Strategy

**Unit tests (no Blender):**
- `test_hair_style_dispatch`: HairForge dispatches to correct style module for each style string
- `test_hair_length_scale`: HAIR_LENGTH_SCALE maps produce valid float values
- `test_hair_gradient_calculation`: apply_vertex_gradient input/output with known vertex positions
- `test_scalp_vertex_detection`: get_scalp_vertices returns valid indices for mock mesh data
- `test_hair_spec_to_forge_config`: resolve_hair() still works (backward compat)

**Integration tests (Blender, marks `blender`):**
- `test_straight_hair_generates_mesh`: Straight style produces a visible mesh with >0 triangles
- `test_curly_hair_generates_mesh`: Curly style produces distinct mesh from straight
- `test_hair_parented_to_head`: Hair mesh object is parented to head bone
- `test_hair_vertex_colors`: Hair mesh has vertex color layer with gradient
- `test_hair_triangle_budget`: Hair mesh respects HAIR_TRIANGLE_BUDGETS limit

### 5.4 G3: Clothing — Test Strategy

**Unit tests (no Blender):**
- `test_patterns_define_all_regions`: Each CLOTHING_PATTERNS entry has valid regions
- `test_region_vertex_groups_mblab`: BODY_REGION_VERTEX_GROUPS has mblab entries for all patterns
- `test_clothing_spec_to_forge_config`: resolve_clothing() still works (backward compat)
- `test_pattern_seam_groups`: Each pattern's seam_groups reference valid regions

**Integration tests (Blender, marks `blender`):**
- `test_tshirt_generates_mesh`: T-shirt pattern produces a mesh covering torso+arms
- `test_clothing_shrinkwrapped_to_body`: Clothing mesh stays within offset tolerance of body
- `test_clothing_weight_painted`: Clothing mesh has vertex groups matching body armature
- `test_clothing_material_assigned`: Clothing mesh has correct material category

### 5.5 G4: Weight Painting — Test Strategy

**Unit tests (no Blender):**
- `test_smooth_regions_defined`: SMOOTH_REGIONS covers all required joint areas
- `test_weight_paint_report_score_formula`: WeightPaintReport.score calculation with known inputs

**Integration tests (Blender):**
- `test_paint_smooth_produces_multi_influence`: After paint_smooth(), boundary vertices have ≥3 vertex groups
- `test_weight_normalization`: All vertex group weights sum to ≈1.0 per vertex
- `test_quality_score_above_threshold`: Generated avatar scores ≥ 0.7
- `test_transfer_weights_to_clothing`: Weight transfer from body to clothing produces valid vertex groups

### 5.6 G5: Rig Verification — Test Strategy

**Unit tests (no Blender):**
- `test_vrm_required_bones_has_25`: VRM_REQUIRED_HUMANOID_BONES is exactly 25 entries
- `test_rig_report_exit_code_0`: RigReport with no errors/warnings → exit_code 0
- `test_rig_report_exit_code_2`: RigReport with errors → exit_code 2
- `test_rig_report_to_json_roundtrip`: to_json() produces valid JSON

**Integration tests (Blender + glTF):**
- `test_verify_compliant_vrm`: Well-formed VRM passes with 0 errors
- `test_verify_missing_bones`: VRM missing jaw/leftEye/rightEye reports errors
- `test_verify_cli_exits_0`: `hamr verify-rig compliant.vrm` exits 0
- `test_verify_cli_exits_2`: `hamr verify-rig broken.vrm` exits 2

### 5.7 G6: Presets — Test Strategy

**Unit tests:**
- `test_preset_yaml_valid`: Each preset YAML parses into valid CharacterSpec
- `test_preset_contains_required_fields`: Each preset has body, face, hair, clothing, export sections
- `test_preset_list_count`: Exactly 6 presets exist
- `test_preset_names_match`: Preset filenames match expected set

**Integration tests (Blender):**
- `test_casual_f_builds`: `hamr build --preset casual_f` produces valid VRM (or fails gracefully)
- `test_preset_build_under_45s`: Each preset builds under 45s on Pi 5 (marked `perf`)

### 5.8 G7: Performance — Test Strategy

**Marked `perf` — only runs on hardware:**
- `test_build_memory_under_1_5gb`: Peak RSS during build stays under 1.5 GB
- `test_build_time_under_45s`: Total pipeline time under 45s
- `test_blender_timeout_works`: Blender subprocess is killed after timeout

**Unit tests:**
- `test_blender_timeout_default`: Default timeout is 120s in pipeline config
- `test_lazy_texture_skip_unused`: Texture slots not in spec are not generated

### 5.9 G8: VRM 1.0 Compliance — Test Strategy

**Unit tests:**
- `test_spring_bone_config_defaults`: SpringBoneGroupSpec has correct defaults
- `test_first_person_spec_defaults`: FirstPersonSpec has correct defaults

**Integration tests (Blender):**
- `test_spring_bones_in_exported_vrm`: VRM contains ≥1 spring bone group
- `test_first_person_annotations_in_vrm`: VRM has first-person mesh annotations
- `test_vrm_meta_populated`: VRM meta has title, author, version, contactInformation

### 5.10 Test Markers

```python
# conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "blender: requires Blender subprocess")
    config.addinivalue_line("markers", "perf: performance test (Pi 5 hardware)")
    config.addinivalue_line("markers", "slow: takes >10 seconds")

# Run fast tests only:
#   pytest tests/ -m "not blender and not perf and not slow"

# Run all including Blender:
#   pytest tests/ -m "not perf"

# Run performance suite:
#   pytest tests/ -m perf
```

---

## 6. Dependency Graph

```
                    ┌──────────────┐
                    │ CharacterSpec │
                    │  (models.py)  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐──────────────┐──────────────┐
              │            │            │              │              │
       ┌──────▼─────┐ ┌───▼────┐ ┌─────▼──────┐ ┌────▼──────┐ ┌────▼────────┐
       │ BodySpec   │ │HairSpec│ │ClothingSpec│ │PhysicsSpec│ │SpringBone  │
       │  presets   │ │        │ │            │ │           │ │  GroupSpec  │
       └──────┬─────┘ └───┬────┘ └─────┬──────┘ └─────┬─────┘ └─────┬──────┘
              │           │            │              │             │
              │    ┌──────▼──────┐ ┌────▼──────┐ ┌─────▼────┐  ┌────▼─────┐
              │    │ HairForge   │ │ClothingForge│ │SpringBones│ │rigs/      │
              │    │ (mesh gen)  │ │ (mesh gen)  │ │configure  │ │verify.py  │
              │    └──────┬──────┘ └────┬───────┘ └─────┬────┘  └────┬─────┘
              │           │            │               │            │
       ┌──────▼──────┐   │            │          ┌────▼────┐  ┌────▼─────┐
       │ BodyForge   │   │            │          │FirstPer-│  │rigs/      │
       │ (presets)   │   │            │          │son Annot.│  │weights.py │
       └──────┬──────┘   │            │          └────┬────┘  └────┬─────┘
              │           │            │               │            │
              └─────►─────┴─────►──────┴──►───────────┴────►───────┘
                                  │
                        ┌────────▼─────────┐
                        │  Blender Bridge   │
                        │  (runner.py)      │
                        │  build_avatar.py  │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   VRM Export      │
                        │   (vrm.py)        │
                        │  + spring bones   │
                        │  + first-person   │
                        │  + 25/25 bones    │
                        └──────────────────┘
```

**Dependency order for implementation:**

1. **`rigs/stub_bones.py`** — standalone, no deps on other new modules
2. **`rigs/weights.py`** — standalone, only needs mesh_ops helpers
3. **`hair/utils.py`** — foundation for hair generators
4. **`hair/forge.py`** + `hair/{straight,wavy,curly,bob,ponytail,braided}.py` — depends on hair/utils
5. **`clothing/patterns.py`** — standalone data, no Blender
6. **`clothing/fit.py`** — needs mesh_ops.shrinkwrap additions
7. **`clothing/forge.py`** — depends on patterns + fit
8. **`rigs/spring_bones.py`** — needs hair mesh result (bone chain data)
9. **`export/first_person.py`** — needs mesh names from hair/clothing
10. **`rigs/verify.py`** — standalone, glTF parsing only
11. **`cli/verify_rig.py`** — depends on rigs/verify
12. **`core/models.py`** updates — SpringBoneGroupSpec, FirstPersonSpec
13. **`scripts/build_avatar.py`** integration — wires all new modules into pipeline
14. **`core/pipeline.py`** updates — preset loading, timeout changes
15. **`cli.py`** updates — verify-rig command, --preset flag
16. **`assets/presets/*.yaml`** — character preset files
17. **Tests** — throughout, but final integration tests last

---

## 7. Key Architecture Decisions

### AD-11.7: Two-Layer Forge Pattern (Config → Mesh)

The existing `resolve_hair()` and `resolve_clothing()` produce **configuration dicts** (Python-side, no Blender). Phase 11 adds **mesh generation** (Blender-side). These are two separate layers:

- **Layer 1 (Config)**: `resolve_hair(HairSpec) → HairBuildResult` — pure Python, runs outside Blender
- **Layer 2 (Mesh)**: `HairForge.generate(HairSpec, head, armature) → HairMeshResult` — runs inside Blender

The config layer stays unchanged for backward compatibility. The mesh layer is new and optional — if `HairForge` isn't available (no Blender), the pipeline falls back to config-only mode.

**Rationale**: This preserves the 156 existing tests and the config-only workflow. The mesh generators are additive.

### AD-11.8: Scalp Detection Strategy

Hair generation requires knowing where the scalp is. Since MB-Lab and TurboSquid meshes have different naming conventions, hair/utils.py tries:

1. **Named vertex groups** ("scalp", "head_mesh", etc.) — fastest, most accurate
2. **UV zone detection** — select vertices with UV coordinates in the top 40% of the Y range
3. **Normal direction** — select vertices whose normals point upward (Y > 0.5 in local space)

The fallback chain ensures hair works even without named vertex groups.

### AD-11.9: Clothing as Separate Mesh, Not Body Deformation

Clothing meshes are **separate Blender objects** parented to the same armature, not shape key deformations on the body mesh. This is the standard approach in game character pipelines because:

- Clothing can be toggled on/off (VRM material variants)
- Weight paint transfers cleanly from body
- No interference with body shape keys
- VRM 1.0 first-person annotations need separate mesh references

### AD-11.10: Performance Budget Architecture

The 45s / 1.5GB budget on Pi 5 dictates:

- **Hair**: Max triangle budget per style (5000 for short, 15000 for very-long). Decimation applied automatically.
- **Clothing**: Decimation after shrinkwrap (max 3000 triangles per item).
- **Textures**: Lazy — only generate textures the spec references. Skip unused slots.
- **Blender timeout**: 120s hard kill. If Blender doesn't finish in 120s, it's broken.
- **Memory**: Explicit `purge_orphans()` call between major steps (after MB-Lab gen, after hair gen, after clothing gen).

### AD-11.11: Rig Verifier is Blender-Independent

`RigVerifier.verify()` parses the glTF binary directly using struct/json — no Blender required. This means it can run on CI, on Pi, anywhere. Only the Blender-specific steps (weight paint scoring) are optional.

---

## 8. Module Boundary Rules

1. **`core/` never imports from `blender_bridge/`, `hair/`, `clothing/`, `rigs/`** — core is pure Python, testable without Blender
2. **`hair/forge.py` and `clothing/forge.py` import `bpy`** — they only run inside Blender. The `resolve_*()` functions in `__init__.py` remain pure Python.
3. **`rigs/stub_bones.py` imports `bpy`** — it modifies armatures inside Blender
4. **`rigs/weights.py` imports `bpy`** — weight painting requires Blender
5. **`rigs/verify.py` does NOT import `bpy`** — pure glTF parsing
6. **`hair/utils.py` imports `bpy`** — runs inside Blender only
7. **`clothing/patterns.py` does NOT import `bpy`** — pure data module
8. **All new Blender-side code checks `BLENDER_AVAILABLE`** — graceful no-op outside Blender

---

*The dwarf who knew every name was turned to stone at dawn. But the names remain — inscribed in bone and mesh and weight. Hamr learns them all.*

*ᚺᚨᛗᚱ — Phase 11: Alvíssmál — Architecture by Rúnhild Svartdóttir*