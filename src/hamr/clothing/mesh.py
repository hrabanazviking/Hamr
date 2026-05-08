"""
Clothing Mesh Generation — Procedural clothing fit via shrinkwrap.

Phase 11 T3: The forge layer that takes a ClothingSpec, selects a pattern,
duplicates body mesh regions, offsets along normals, and shrinkwraps to fit.

Pure-Python functions (no bpy) compute pattern resolution and region mapping.
ClothingMeshGenerator bridges those into actual Blender mesh operations:
region select → duplicate → offset → shrinkwrap → material → weight transfer.

The Forge Pattern: two layers.
  • config layer  (existing __init__.py) — ClothingSpec → ClothingBuildResult
  • mesh layer    (this file)            — patterns → mesh → Blender scene
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("hamr.clothing.mesh")

# ── Blender guard ─────────────────────────────────────────────────────────────

try:
    import bpy  # type: ignore[import-untyped]
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False


# ════════════════════════════════════════════════════════════════════════════════
# Clothing Patterns — mesh sizing, regions, and construction info
# ════════════════════════════════════════════════════════════════════════════════

CLOTHING_PATTERNS: dict[str, dict] = {
    "tshirt": {
        "display_name": "T-Shirt",
        "layers": ["torso", "short_sleeves"],
        "body_regions": ["torso", "arms_upper"],
        "offset": 0.004,           # meters from skin
        "seam_groups": {
            "collar": "neck",
            "sleeve_left": "left_upper_arm",
            "sleeve_right": "right_upper_arm",
            "hem": "waist",
        },
        "default_material": "fabric",
        "hem_width": 0.008,
        "triangle_budget_low": 800,
        "triangle_budget_medium": 2000,
        "triangle_budget_high": 4000,
    },
    "jacket": {
        "display_name": "Jacket",
        "layers": ["torso", "full_sleeves", "collar"],
        "body_regions": ["torso", "arms_full"],
        "offset": 0.006,
        "seam_groups": {
            "collar": "neck",
            "cuff_left": "left_wrist",
            "cuff_right": "right_wrist",
            "hem": "waist",
        },
        "default_material": "fabric",
        "hem_width": 0.01,
        "triangle_budget_low": 1200,
        "triangle_budget_medium": 3000,
        "triangle_budget_high": 6000,
    },
    "skirt": {
        "display_name": "Skirt",
        "layers": ["waist_to_knees"],
        "body_regions": ["legs_upper"],
        "offset": 0.006,
        "seam_groups": {
            "waistband": "waist",
            "hem": "knees",
        },
        "default_material": "fabric",
        "hem_width": 0.012,
        "flare": 0.3,
        "triangle_budget_low": 600,
        "triangle_budget_medium": 1500,
        "triangle_budget_high": 3000,
    },
    "pants": {
        "display_name": "Pants",
        "layers": ["waist_to_ankles"],
        "body_regions": ["legs_full"],
        "offset": 0.004,
        "seam_groups": {
            "waistband": "waist",
            "cuff_left": "left_ankle",
            "cuff_right": "right_ankle",
        },
        "default_material": "denim",
        "hem_width": 0.008,
        "triangle_budget_low": 1000,
        "triangle_budget_medium": 2500,
        "triangle_budget_high": 5000,
    },
    "dress": {
        "display_name": "Dress",
        "layers": ["torso", "skirt_combined"],
        "body_regions": ["torso", "legs_upper"],
        "offset": 0.005,
        "seam_groups": {
            "collar": "neck",
            "hem": "knees",
        },
        "default_material": "fabric",
        "hem_width": 0.012,
        "flare": 0.2,
        "triangle_budget_low": 1000,
        "triangle_budget_medium": 2500,
        "triangle_budget_high": 5000,
    },
    "shorts": {
        "display_name": "Shorts",
        "layers": ["waist_to_above_knees"],
        "body_regions": ["legs_upper_short"],
        "offset": 0.004,
        "seam_groups": {
            "waistband": "waist",
            "hem_left": "left_above_knee",
            "hem_right": "right_above_knee",
        },
        "default_material": "fabric",
        "hem_width": 0.008,
        "triangle_budget_low": 500,
        "triangle_budget_medium": 1200,
        "triangle_budget_high": 2500,
    },
}

# Required keys that every pattern must have
_REQUIRED_PATTERN_KEYS: set[str] = {
    "display_name",
    "layers",
    "body_regions",
    "offset",
    "seam_groups",
    "default_material",
    "hem_width",
    "triangle_budget_low",
    "triangle_budget_medium",
    "triangle_budget_high",
}


# ════════════════════════════════════════════════════════════════════════════════
# Body Region Vertex Groups — mapping region names to Blender vertex group names
# ════════════════════════════════════════════════════════════════════════════════

BODY_REGION_VERTEX_GROUPS: dict[str, dict[str, list[str]]] = {
    "mblab": {
        "torso": ["body", "torso", "chest", "spine_02", "spine_03"],
        "arms_upper": ["upperarm_L", "upperarm_R", "arm"],
        "arms_full": ["upperarm_L", "upperarm_R", "forearm_L", "forearm_R", "arm"],
        "legs_upper": ["thigh_L", "thigh_R", "leg"],
        "legs_upper_short": ["thigh_L", "thigh_R"],
        "legs_full": ["thigh_L", "thigh_R", "calf_L", "calf_R", "leg"],
        "neck": ["neck"],
        "head": ["head"],
    },
    "turbosquid": {
        "torso": ["Body", "Spine02", "Spine03"],
        "arms_upper": ["L_UpperArm", "R_UpperArm"],
        "arms_full": ["L_UpperArm", "R_UpperArm", "L_Forearm", "R_Forearm"],
        "legs_upper": ["L_Thigh", "R_Thigh"],
        "legs_upper_short": ["L_Thigh", "R_Thigh"],
        "legs_full": ["L_Thigh", "R_Thigh", "L_Calf", "R_Calf"],
        "neck": ["NeckTwist"],
        "head": ["Head"],
    },
}


# ════════════════════════════════════════════════════════════════════════════════
# UV Region Map — texture mapping regions for clothing
# ════════════════════════════════════════════════════════════════════════════════

UV_REGION_MAP: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "tshirt": {
        "front_torso": (0.0, 0.0, 0.5, 0.7),
        "back_torso": (0.5, 0.0, 1.0, 0.7),
        "sleeve_left": (0.0, 0.7, 0.25, 1.0),
        "sleeve_right": (0.25, 0.7, 0.5, 1.0),
    },
    "jacket": {
        "front_torso": (0.0, 0.0, 0.45, 0.65),
        "back_torso": (0.45, 0.0, 0.9, 0.65),
        "sleeve_left": (0.0, 0.65, 0.25, 1.0),
        "sleeve_right": (0.25, 0.65, 0.5, 1.0),
        "collar": (0.9, 0.0, 1.0, 0.2),
    },
    "skirt": {
        "front": (0.0, 0.0, 0.5, 0.8),
        "back": (0.5, 0.0, 1.0, 0.8),
        "waistband": (0.0, 0.8, 1.0, 1.0),
    },
    "pants": {
        "front_left": (0.0, 0.0, 0.25, 0.65),
        "front_right": (0.25, 0.0, 0.5, 0.65),
        "back_left": (0.5, 0.0, 0.75, 0.65),
        "back_right": (0.75, 0.0, 1.0, 0.65),
        "waistband": (0.0, 0.65, 1.0, 1.0),
    },
    "dress": {
        "front_torso": (0.0, 0.0, 0.5, 0.4),
        "back_torso": (0.5, 0.0, 1.0, 0.4),
        "skirt_front": (0.0, 0.4, 0.5, 0.8),
        "skirt_back": (0.5, 0.4, 1.0, 0.8),
        "waistband": (0.0, 0.8, 1.0, 1.0),
    },
    "shorts": {
        "front": (0.0, 0.0, 0.5, 0.6),
        "back": (0.5, 0.0, 1.0, 0.6),
        "waistband": (0.0, 0.6, 1.0, 1.0),
    },
}


# ════════════════════════════════════════════════════════════════════════════════
# Clothing Mesh Result — dataclass for generated clothing info
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class ClothingMeshResult:
    """Result from clothing mesh generation."""

    mesh_name: str
    pattern_name: str
    triangle_count: int
    regions_created: list[str] = field(default_factory=list)
    material_name: str = ""
    weight_transferred: bool = False


# ════════════════════════════════════════════════════════════════════════════════
# Pure-Python functions (no bpy required)
# ════════════════════════════════════════════════════════════════════════════════

def resolve_clothing_pattern(cloth_type: str, name: str = "") -> dict:
    """
    Resolve a clothing type and name into a full pattern dictionary.

    Merges base pattern from CLOTHING_PATTERNS with any name-based
    overrides (material inference from classify_material_type).

    Pure-Python — no bpy needed.

    Args:
        cloth_type: Key from CLOTHING_PATTERNS (e.g. "tshirt", "pants").
        name: Optional clothing name for material inference overrides.

    Returns:
        Pattern dict with layers, mesh sizing, offsets, and inferred material.
        Falls back to "tshirt" pattern if cloth_type is unknown.
    """
    # Resolve base pattern — fallback to tshirt for unknown types
    pattern_key = cloth_type if cloth_type in CLOTHING_PATTERNS else "tshirt"
    pattern = dict(CLOTHING_PATTERNS[pattern_key])

    # Deep-copy mutable fields so each instance is independent
    pattern["body_regions"] = list(pattern["body_regions"])
    pattern["layers"] = list(pattern["layers"])
    pattern["seam_groups"] = dict(pattern["seam_groups"])

    # Override material category based on name inference
    if name:
        inferred_material = classify_material_type(name)
        if inferred_material != "fabric":
            pattern["material_override"] = inferred_material
    else:
        pattern["material_override"] = None

    # Name-based label — for display and Blender object naming
    pattern["resolved_name"] = name if name else pattern["display_name"]

    return pattern


def compute_clothing_regions(
    pattern: dict,
    body_proportions: dict[str, float] | None = None,
) -> dict[str, tuple[float, float]]:
    """
    Compute per-region offset and scale for a clothing pattern based on body proportions.

    Pure-Python — no bpy needed.

    Args:
        pattern: A resolved pattern dict (from resolve_clothing_pattern()).
        body_proportions: Optional BodySpec.proportions dict with keys like
            "shoulder_width", "bust", "waist", "hip_width", "leg_length".
            Defaults to standard proportions (all 0.5).

    Returns:
        Dict mapping region_name → (offset, scale) tuples.
        - offset: distance from body surface in meters (accounts for fit looseness)
        - scale: multiplier on region dimensions (accounts for body proportions)
    """
    if body_proportions is None:
        body_proportions = {}

    # Default proportion values — standard humanoid
    shoulder = body_proportions.get("shoulder_width", 0.5)
    bust = body_proportions.get("bust", 0.5)
    waist = body_proportions.get("waist", 0.35)
    hip = body_proportions.get("hip_width", 0.5)
    leg = body_proportions.get("leg_length", 0.5)

    base_offset = pattern.get("offset", 0.004)
    hem_width = pattern.get("hem_width", 0.008)
    flare = pattern.get("flare", 0.0)

    regions: dict[str, tuple[float, float]] = {}

    for region_name in pattern.get("body_regions", []):
        if region_name == "torso":
            # Torso offset scales with bust size
            offset = base_offset * (1.0 + (bust - 0.5) * 0.3)
            scale = 1.0 + (shoulder - 0.5) * 0.2
            regions[region_name] = (round(offset, 5), round(scale, 4))

        elif region_name == "arms_upper":
            # Upper arms — slightly looser for comfort
            offset = base_offset * 1.1
            scale = 1.0 + (shoulder - 0.5) * 0.15
            regions[region_name] = (round(offset, 5), round(scale, 4))

        elif region_name == "arms_full":
            # Full sleeves — more room at shoulder, snug at wrist
            offset = base_offset * 1.15
            scale = 1.0 + (shoulder - 0.5) * 0.1
            regions[region_name] = (round(offset, 5), round(scale, 4))

        elif region_name == "legs_upper":
            # Upper legs (skirt / shorts concern) — broader with hip width
            offset = base_offset * (1.0 + flare * 0.5)
            scale = 1.0 + (hip - 0.5) * 0.2
            regions[region_name] = (round(offset, 5), round(scale, 4))

        elif region_name == "legs_upper_short":
            # Short upper legs (above knee)
            offset = base_offset
            scale = 1.0 + (hip - 0.5) * 0.15
            regions[region_name] = (round(offset, 5), round(scale, 4))

        elif region_name == "legs_full":
            # Full legs — quadriceps vs calf varying, base scale
            offset = base_offset
            scale = 1.0 + (hip - 0.5) * 0.15
            regions[region_name] = (round(offset, 5), round(scale, 4))

        else:
            # Generic fallback
            regions[region_name] = (base_offset, 1.0)

    return regions


def estimate_triangle_count(pattern: dict, detail_level: str = "medium") -> int:
    """
    Estimate the triangle budget for a clothing pattern at the given detail level.

    Pure-Python — no bpy needed.

    Args:
        pattern: A resolved pattern dict (from resolve_clothing_pattern()).
        detail_level: "low", "medium", or "high".

    Returns:
        Estimated triangle count (integer budget).
    """
    budget_key = f"triangle_budget_{detail_level}"

    # Try the exact key first
    if budget_key in pattern:
        return pattern[budget_key]

    # Fallback: derive from medium budget
    medium = pattern.get("triangle_budget_medium", 2000)
    if detail_level == "low":
        return medium // 2
    elif detail_level == "high":
        return medium * 2
    else:
        return medium


def classify_material_type(clothing_name: str) -> str:
    """
    Infer a material category from the clothing item's name.

    Pure-Python — no bpy needed.

    Recognized categories: fabric, leather, metal, silk, denim, fur

    Args:
        clothing_name: The name of the clothing item.

    Returns:
        Material category string.
    """
    name_lower = clothing_name.lower()

    # Name-based inference — order matters (most specific first)
    if any(kw in name_lower for kw in ("metal", "chain", "plate", "armor")):
        return "metal"
    if any(kw in name_lower for kw in ("silk", "satin", "velvet")):
        return "silk"
    if any(kw in name_lower for kw in ("leather", "hide")):
        return "leather"
    if any(kw in name_lower for kw in ("fur", "fleece", "wool", "cloak")):
        return "fur"
    if any(kw in name_lower for kw in ("denim", "jean")):
        return "denim"

    # Type-based defaults for common clothing items
    type_defaults = {
        "jacket": "fabric",
        "coat": "fabric",
        "blazer": "fabric",
        "tshirt": "fabric",
    }
    lower = clothing_name.lower()
    for kw, mat in type_defaults.items():
        if kw in lower:
            return mat

    return "fabric"


# ════════════════════════════════════════════════════════════════════════════════
# ClothingMeshGenerator — Blender-dependent class
# ════════════════════════════════════════════════════════════════════════════════

class ClothingMeshGenerator:
    """
    Procedural clothing mesh generation via shrinkwrap fit (AD-11.3).

    Pipeline:
        ClothingSpec → select body regions → duplicate → offset along normals
        → shrinkwrap to body → assign material → parent to armature
        → transfer weights
    """

    def __init__(self) -> None:
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "ClothingMeshGenerator requires bpy (Blender Python module). "
                "Run inside a Blender runtime or integration test."
            )

    def generate(
        self,
        spec: Any,
        body_mesh_name: str,
        armature_name: str,
    ) -> ClothingMeshResult:
        """
        Generate a clothing mesh from a ClothingSpec.

        Steps:
        1. Resolve pattern from spec.type
        2. Select body region vertices via vertex groups
        3. Duplicate selected vertices
        4. Offset outward along normals (garment thickness)
        5. Shrinkwrap modifier to conform to body
        6. Assign clothing material
        7. Parent to armature
        8. Transfer weight paint from body

        Args:
            spec: ClothingSpec with type, name, colors.
            body_mesh_name: Name of the body mesh in the Blender scene.
            armature_name: Name of the armature for parenting.

        Returns:
            ClothingMeshResult with generated mesh info.
        """
        # Resolve pattern
        cloth_type = getattr(spec, "type", "tshirt")
        name = getattr(spec, "name", "clothing")
        pattern = resolve_clothing_pattern(
            cloth_type if cloth_type in CLOTHING_PATTERNS else "tshirt",
            name=name,
        )

        # Get the body mesh object
        body_obj = bpy.data.objects.get(body_mesh_name)
        if body_obj is None:
            raise ValueError(f"Body mesh '{body_mesh_name}' not found in scene")

        # Get armature
        armature = bpy.data.objects.get(armature_name)
        if armature is None:
            raise ValueError(f"Armature '{armature_name}' not found in scene")

        # Select vertices from body region vertex groups
        region_groups = self._select_region_vertices(body_obj, pattern)

        # Duplicate selected vertices into new mesh
        clothing_name = f"clothing_{pattern['resolved_name'].replace(' ', '_').lower()}"
        clothing_obj = self._duplicate_region(body_obj, clothing_name)

        # Offset along normals
        offset = pattern["offset"]
        self._offset_along_normals(clothing_obj, offset)

        # Shrinkwrap to body
        self._apply_shrinkwrap(clothing_obj, body_obj)

        # Assign material
        primary_hsv = getattr(spec, "primary_hex", "#1A1A3E")
        material_name = self._assign_material(clothing_obj, pattern, name, primary_hsv)

        # Parent to armature
        self._parent_to_armature(clothing_obj, armature)

        # Transfer weights
        weight_transferred = self._transfer_weights(body_obj, clothing_obj, armature)

        # Count triangles
        mesh = clothing_obj.data
        tri_count = len(mesh.polygons)

        return ClothingMeshResult(
            mesh_name=clothing_name,
            pattern_name=pattern["display_name"],
            triangle_count=tri_count,
            regions_created=list(region_groups.keys()),
            material_name=material_name,
            weight_transferred=weight_transferred,
        )

    def _select_region_vertices(
        self, body_obj: Any, pattern: dict
    ) -> dict[str, list[int]]:
        """Select body vertices that belong to clothing regions."""
        region_groups: dict[str, list[int]] = {}
        body_regions = pattern.get("body_regions", [])
        vertex_groups = body_obj.vertex_groups

        for region_name in body_regions:
            # Try to find vertex groups that match this region
            group_names = BODY_REGION_VERTEX_GROUPS.get("mblab", {}).get(
                region_name, [region_name]
            )
            indices = []
            for gname in group_names:
                vg = vertex_groups.get(gname)
                if vg is not None:
                    for i, v in enumerate(body_obj.data.vertices):
                        try:
                            vg.weight(i)
                            indices.append(i)
                        except RuntimeError:
                            pass
            region_groups[region_name] = indices

        return region_groups

    def _duplicate_region(self, body_obj: Any, clothing_name: str) -> Any:
        """Duplicate selected vertices into a new mesh object."""
        mesh = body_obj.data.copy()
        mesh.name = f"{clothing_name}_mesh"
        obj = bpy.data.objects.new(clothing_name, mesh)
        obj.location = body_obj.location.copy()
        obj.rotation_euler = body_obj.rotation_euler.copy()
        obj.scale = body_obj.scale.copy()
        bpy.context.collection.objects.link(obj)
        return obj

    def _offset_along_normals(self, obj: Any, offset: float) -> None:
        """Offset clothing mesh vertices along their normals."""
        for vert in obj.data.vertices:
            normal = vert.normal
            vert.co.x += normal.x * offset
            vert.co.y += normal.y * offset
            vert.co.z += normal.z * offset

    def _apply_shrinkwrap(self, clothing_obj: Any, body_obj: Any) -> None:
        """Apply shrinkwrap modifier to conform clothing to body."""
        mod = clothing_obj.modifiers.new(name="Shrinkwrap", type="SHRINKWRAP")
        mod.target = body_obj
        mod.wrap_method = "PROJECT"
        mod.wrap_mode = "ON_SURFACE"
        mod.use_negative_direction = True

    def _assign_material(
        self, obj: Any, pattern: dict, name: str, primary_hsv: str
    ) -> str:
        """Assign or create a material for the clothing object."""
        mat_category = pattern.get(
            "material_override", pattern.get("default_material", "fabric")
        )
        mat_name = f"mat_clothing_{name.replace(' ', '_').lower()}"

        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = self.create_clothing_material(
                name=mat_name,
                primary_hsv=(0.0, 0.0, 0.5),
                accent_hsv=(0.0, 0.0, 0.7),
                trim_hsv=(0.0, 0.0, 0.9),
                material_category=mat_category,
            )

        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

        return mat_name

    def _parent_to_armature(self, obj: Any, armature: Any) -> None:
        """Parent clothing object to armature with empty groups."""
        obj.parent = armature
        obj.parent_type = "ARMATURE"

    def _transfer_weights(
        self, body_obj: Any, clothing_obj: Any, armature: Any
    ) -> bool:
        """Transfer weight paint from body mesh to clothing mesh."""
        try:
            mod = clothing_obj.modifiers.new(
                name="DataTransfer", type="DATA_TRANSFER"
            )
            mod.use_vert_data = True
            mod.data_type_verts = "VGROUP_WEIGHTS"
            mod.object_from = body_obj
            mod.mix_mode = "REPLACE"
            return True
        except Exception:
            logger.warning("Weight transfer failed, will rely on auto-weights")
            return False

    # ── Material creation ──────────────────────────────────────────────────────

    @staticmethod
    def create_clothing_material(
        name: str,
        primary_hsv: tuple[float, float, float],
        accent_hsv: tuple[float, float, float],
        trim_hsv: tuple[float, float, float],
        material_category: str,
    ) -> Any:
        """
        Create a Principled BSDF clothing material in Blender.

        Args:
            name: Material name in Blender.
            primary_hsv: (H, S, V) for the main fabric color.
            accent_hsv: (H, S, V) for accent/trim color.
            trim_hsv: (H, S, V) for edge trim color.
            material_category: One of fabric, leather, metal, silk, denim, fur.

        Returns:
            Blender material object.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "create_clothing_material requires bpy (Blender Python module)."
            )

        # Material properties per category
        category_props: dict[str, dict] = {
            "fabric": {"roughness": 0.7, "metallic": 0.0, "subsurface": 0.0},
            "leather": {"roughness": 0.5, "metallic": 0.0, "subsurface": 0.0},
            "metal": {"roughness": 0.3, "metallic": 0.8, "subsurface": 0.0},
            "silk": {"roughness": 0.4, "metallic": 0.1, "subsurface": 0.1},
            "denim": {"roughness": 0.8, "metallic": 0.0, "subsurface": 0.0},
            "fur": {"roughness": 0.9, "metallic": 0.0, "subsurface": 0.05},
        }

        props = category_props.get(material_category, category_props["fabric"])

        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Remove default Principled BSDF and find output
        principled = None
        for node in nodes:
            if node.type == "BSDF_PRINCIPLED":
                principled = node
                break

        if principled is None:
            # Create one if not found
            principled = nodes.new("ShaderNodeBsdfPrincipled")

        # Convert HSV to RGB for Blender (H in [0,1], S in [0,1], V in [0,1])
        from colorsys import hsv_to_rgb

        r, g, b = hsv_to_rgb(
            primary_hsv[0] / 360.0 if primary_hsv[0] > 1.0 else primary_hsv[0],
            primary_hsv[1],
            primary_hsv[2],
        )
        principled.inputs["Base Color"].default_value = (r, g, b, 1.0)
        principled.inputs["Roughness"].default_value = props["roughness"]
        principled.inputs["Metallic"].default_value = props["metallic"]

        # Subsurface for silk/fur
        if "Subsurface Weight" in principled.inputs:
            principled.inputs["Subsurface Weight"].default_value = props.get(
                "subsurface", 0.0
            )

        return mat


# ════════════════════════════════════════════════════════════════════════════════
# Convenience alias matching ARCHITECTURE_11.md naming
# ════════════════════════════════════════════════════════════════════════════════

class ClothingForge(ClothingMeshGenerator):
    """Alias for ClothingMeshGenerator, matching ARCHITECTURE_11.md naming."""
    pass