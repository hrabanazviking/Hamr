"""
Hair Mesh Generation — Procedural VRoid-quality anime hair from guide curves.

Phase 11 T2: The curve-to-mesh pipeline that breathes hair onto a bare skull.

Pure-Python geometry functions (no bpy) compute guide curves and strand
positions.  HairMeshGenerator bridges those curves into actual Blender
Bezier curve objects, converts them to mesh, and auto-parents the result
to the head bone.  Material creation uses vertex-color gradients anchored
by root-tip HSV pairs.

The Forge Pattern: two layers.
  • config layer  (existing __init__.py) — HairSpec → HairBuildResult
  • mesh layer    (this file)            — guide curves → mesh → Blender scene
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("hamr.hair.mesh")

# ── Blender guard ─────────────────────────────────────────────────────────────

try:
    import bpy  # type: ignore[import-untyped]
    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False

# ── Style configurations ──────────────────────────────────────────────────────

HAIR_MESH_STYLES: dict[str, dict] = {
    "long_straight": {
        "display_name": "Long Straight",
        "guide_curves_per_side": 10,
        "guide_curves_back": 6,
        "base_length_factor": 1.0,
        "strand_density": 1.0,
        "wave_amplitude": 0.0,
        "wave_frequency": 0.0,
        "wave_phase": 0.0,
        "curl_tightness": 0.0,
        "cross_section_radius": 0.003,
        "taper_ratio": 0.3,
        "scalp_coverage": 0.85,
        "requires_mesh": True,
        "keywords": ["straight", "long", "flowing", "sleek"],
        "max_triangle_budget": 8000,
    },
    "long_wavy": {
        "display_name": "Long Wavy",
        "guide_curves_per_side": 10,
        "guide_curves_back": 6,
        "base_length_factor": 1.0,
        "strand_density": 1.0,
        "wave_amplitude": 0.025,
        "wave_frequency": 3.0,
        "wave_phase": 0.0,
        "curl_tightness": 0.2,
        "cross_section_radius": 0.003,
        "taper_ratio": 0.35,
        "scalp_coverage": 0.85,
        "requires_mesh": True,
        "keywords": ["wavy", "flowing", "beach", "romantic"],
        "max_triangle_budget": 9000,
    },
    "short_bob": {
        "display_name": "Short Bob",
        "guide_curves_per_side": 8,
        "guide_curves_back": 4,
        "base_length_factor": 0.35,
        "strand_density": 1.0,
        "wave_amplitude": 0.008,
        "wave_frequency": 1.5,
        "wave_phase": 0.0,
        "curl_tightness": 0.1,
        "cross_section_radius": 0.0025,
        "taper_ratio": 0.25,
        "scalp_coverage": 0.9,
        "requires_mesh": True,
        "keywords": ["bob", "chin-length", "short", "cute"],
        "max_triangle_budget": 5000,
    },
    "twin_tails": {
        "display_name": "Twin Tails",
        "guide_curves_per_side": 6,
        "guide_curves_back": 2,
        "base_length_factor": 0.85,
        "strand_density": 0.9,
        "wave_amplitude": 0.01,
        "wave_frequency": 2.0,
        "wave_phase": 0.0,
        "curl_tightness": 0.0,
        "cross_section_radius": 0.003,
        "taper_ratio": 0.3,
        "scalp_coverage": 0.7,
        "requires_mesh": True,
        "keywords": ["twin_tails", "twintails", "symmetrical", "anime"],
        "max_triangle_budget": 6000,
        "tied_spread": 0.04,
    },
    "spiky": {
        "display_name": "Spiky",
        "guide_curves_per_side": 8,
        "guide_curves_back": 4,
        "base_length_factor": 0.25,
        "strand_density": 0.7,
        "wave_amplitude": 0.0,
        "wave_frequency": 0.0,
        "wave_phase": 0.0,
        "curl_tightness": 0.0,
        "cross_section_radius": 0.002,
        "taper_ratio": 0.6,
        "scalp_coverage": 0.8,
        "requires_mesh": True,
        "keywords": ["spiky", "shonen", "short", "wild"],
        "max_triangle_budget": 4000,
        "spike_spread": 0.06,
    },
}

# Required keys every style config must have
_REQUIRED_STYLE_KEYS = {
    "display_name",
    "guide_curves_per_side",
    "guide_curves_back",
    "base_length_factor",
    "strand_density",
    "wave_amplitude",
    "wave_frequency",
    "wave_phase",
    "curl_tightness",
    "cross_section_radius",
    "taper_ratio",
    "scalp_coverage",
    "requires_mesh",
    "keywords",
    "max_triangle_budget",
}

# ── Hair length scale (meters, referenced from HAIR_LENGTH_TABLE) ────────────

HAIR_LENGTH_SCALE: dict[str, float] = {
    "short": 0.05,
    "medium": 0.12,
    "shoulder": 0.18,
    "shoulder-plus": 0.25,
    "long": 0.35,
    "very-long": 0.50,
}

# ── Dataclasses ────────────────────────────────────────────────────────────────


@dataclass
class GuideCurve:
    """A single hair guide curve definition."""

    origin: tuple[float, float, float]
    control_points: list[tuple[float, float, float]]
    group: str  # "left", "right", "back", "top"
    style_modifier: str = ""  # e.g. "tied" for twin_tails


@dataclass
class HairMeshResult:
    """Result from HairMeshGenerator.generate()."""

    object_name: str
    bone_chain: list[str]
    vertex_count: int
    triangle_count: int
    style: str


# ══════════════════════════════════════════════════════════════════════════════
# Pure-Python hair geometry functions (no bpy required)
# ══════════════════════════════════════════════════════════════════════════════

# ── Scalp region helper ───────────────────────────────────────────────────────

def _scalp_angles(n_side: int, n_back: int, coverage: float = 0.85):
    """Return (theta, phi) pairs for guide curve root placement on the scalp.

    Theta is the azimuthal angle (around the head, 0 = front), phi is the
    elevation from the top of the head (0 = north pole, pi/2 = equator).

    Side guides are placed symmetrically at ±theta on both sides.
    Back guides occupy theta ∈ (π*coverage, π) (the back of the head).
    """
    angles: list[tuple[float, str]] = []

    # Side guides — evenly spaced on each side of the face
    side_start = math.pi * (1.0 - coverage) * 0.5  # small band from front
    side_end = math.pi * 0.45
    for i in range(n_side):
        t = i / max(n_side - 1, 1)
        theta = side_start + t * (side_end - side_start)
        angles.append((theta, "side"))

    # Back guides — fill the back hemisphere
    back_start = math.pi * 0.45
    back_end = math.pi * 0.95
    for i in range(n_back):
        t = i / max(n_back - 1, 1)
        theta = back_start + t * (back_end - back_start)
        angles.append((theta, "back"))

    return angles


def generate_guide_curves(
    style: str,
    head_center: tuple[float, float, float] = (0.0, 1.65, 0.0),
    head_radius: float = 0.10,
) -> list[GuideCurve]:
    """Generate guide curves for a given hair style on a spherical head.

    This is the core pure-Python geometry function.  It produces guide curve
    origins and control points relative to the head sphere.  The rest of
    the pipeline (HairMeshGenerator) uses these to build Blender curves.

    Args:
        style: Key from HAIR_MESH_STYLES.
        head_center: (x, y, z) world position of head center.
        head_radius: Head sphere radius in meters.

    Returns:
        List of GuideCurve objects with origins and control points.
    """
    if style not in HAIR_MESH_STYLES:
        logger.warning("Unknown hair style '%s', falling back to 'long_straight'", style)
        style = "long_straight"

    cfg = HAIR_MESH_STYLES[style]
    n_side = cfg["guide_curves_per_side"]
    n_back = cfg["guide_curves_back"]
    length_factor = cfg["base_length_factor"]
    coverage = cfg["scalp_coverage"]
    wave_amp = cfg["wave_amplitude"]
    wave_freq = cfg["wave_frequency"]
    wave_phase = cfg["wave_phase"]

    cx, cy, cz = head_center
    hair_length = head_radius * 3.5 * length_factor  # hair extends below head
    curves: list[GuideCurve] = []

    # Phi angles: where on the dome the roots sit (0 = top, ~pi/3 = sides)
    phi_for_group = {
        "side": math.pi / 3.2,
        "back": math.pi / 3.0,
        "top": 0.05,
    }

    def _make_curve(theta: float, group: str, side_sign: float = 1.0) -> GuideCurve:
        """Build one guide curve at (theta, phi) on the scalp dome."""
        phi = phi_for_group.get(group, math.pi / 3.0)

        # Origin on head sphere (head-center + spherical offset)
        ox = cx + head_radius * math.sin(phi) * math.cos(theta) * side_sign
        oy = cy + head_radius * math.cos(phi)
        oz = cz + head_radius * math.sin(phi) * math.sin(theta)

        # Growth direction: roughly (outward from head + downward)
        dx = math.sin(phi) * math.cos(theta) * side_sign
        dy = -0.5  # strong downward bias for gravity
        dz = math.sin(phi) * math.sin(theta)
        mag = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / mag, dy / mag, dz / mag

        # Control points along the strand
        cp: list[tuple[float, float, float]] = []
        n_points = 5  # origin + 4 more control points
        for k in range(n_points):
            t = k / (n_points - 1)
            # Base position: origin + t * length * direction
            px = ox + t * hair_length * dx * 0.7
            py = oy + t * hair_length * dy
            pz = oz + t * hair_length * dz * 0.7

            # Style-specific deformations
            if style == "long_wavy" and wave_amp > 0:
                # Apply sine wave
                px += wave_amp * math.sin(wave_freq * t * math.pi + wave_phase) * side_sign
                pz += wave_amp * 0.5 * math.cos(wave_freq * t * math.pi + wave_phase)

            elif style == "twin_tails":
                tied = cfg.get("tied_spread", 0.04)
                if t > 0.2:
                    # Converge strands toward the tie point
                    spread_factor = t * tied
                    if side_sign > 0:
                        px += spread_factor
                    else:
                        px -= spread_factor

            elif style == "spiky":
                spike_spread = cfg.get("spike_spread", 0.06)
                if t < 0.3:
                    # Spike tip: slight outward flare then inward convergence
                    flare = spike_spread * math.sin(t / 0.3 * math.pi)
                    px += flare * dx
                    pz += flare * dz

            # Taper: reduce cross-section toward tip (reflected in control points
            # by pulling toward center line)
            taper = cfg.get("taper_ratio", 0.3)
            if t > 0.6:
                taper_factor = 1.0 - (t - 0.6) / 0.4 * taper
                px = ox + (px - ox) * max(taper_factor, 0.3)
                pz = oz + (pz - oz) * max(taper_factor, 0.3)

            cp.append((px, py, pz))

        origin = (ox, oy, oz)
        modifier = ""
        if style == "twin_tails":
            modifier = "tied"

        return GuideCurve(origin=origin, control_points=cp, group=group, style_modifier=modifier)

    # ── Build curves by group ──────────────────────────────────────────────

    # Top spike (for anime "ahoge" / spiky styles)
    if style in ("spiky", "long_straight", "long_wavy"):
        curves.append(_make_curve(0.0, "top", side_sign=0.0))

    # Left side curves
    side_angles = _scalp_angles(n_side, n_back, coverage)
    idx = 0
    for theta_raw, group in side_angles:
        idx += 1
        if group == "side":
            # Left side
            curves.append(_make_curve(theta_raw, "side", side_sign=-1.0))
            # Right side (mirror)
            curves.append(_make_curve(theta_raw, "side", side_sign=1.0))
        elif group == "back":
            curves.append(_make_curve(theta_raw, "back", side_sign=0.0))

    return curves


def compute_strand_count(style: str, density: float = 1.0) -> int:
    """Compute how many hair strands to generate for a style and density.

    Each guide curve is an anchor; the strand count determines how many
    interpolated curves fan out around each guide.  Higher density =
    more strands = richer hair but heavier mesh.

    Args:
        style: Key from HAIR_MESH_STYLES.
        density: 0.0–2.0 multiplier (1.0 = standard, 0.5 = half, etc.)

    Returns:
        Integer strand count (clamped to reasonable bounds).
    """
    if style not in HAIR_MESH_STYLES:
        style = "long_straight"

    cfg = HAIR_MESH_STYLES[style]
    base_density = cfg["strand_density"]
    n_side = cfg["guide_curves_per_side"]
    n_back = cfg["guide_curves_back"]

    # Sub-strands per guide curve (base × density multiplier)
    sub_strands = max(1, round(3.0 * base_density * density))
    # Total guide curves: top spike + side guides (×2 for L/R) + back guides
    total_guides = 1 + (n_side * 2) + n_back
    count = total_guides * sub_strands

    # Clamp to triangle budget
    budget = cfg["max_triangle_budget"]
    # Each strand ≈ 8-16 faces (cross-section segments × subdivisions)
    faces_per_strand = 12
    max_strands = max(4, budget // faces_per_strand)
    return min(count, max_strands)


def interpolate_curve_points(
    control_points: list[tuple[float, float, float]],
    subdivisions: int = 8,
) -> list[tuple[float, float, float]]:
    """Interpolate smooth curve points from control points using Catmull-Rom.

    Given a set of control points defining a hair strand, produces a denser
    set of points along a smooth curve.  Uses Catmull-Rom interpolation
    which is tangent-continuous at every control point.

    Args:
        control_points: 3D anchor points along the strand.
        subdivisions: Number of sub-divisions between each pair of anchors.

    Returns:
        List of (x, y, z) points along the smooth curve.
    """
    if len(control_points) < 2:
        return list(control_points)

    points: list[tuple[float, float, float]] = []

    n = len(control_points)
    for i in range(n - 1):
        # Catmull-Rom uses p0=p[i-1], p1=p[i], p2=p[i+1], p3=p[i+2]
        # Pad the ends by duplicating the first / last point
        p0 = control_points[max(i - 1, 0)]
        p1 = control_points[i]
        p2 = control_points[min(i + 1, n - 1)]
        p3 = control_points[min(i + 2, n - 1)]

        for s in range(subdivisions):
            t = s / subdivisions
            t2 = t * t
            t3 = t2 * t

            # Catmull-Rom coefficients
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            z = 0.5 * (
                (2 * p1[2])
                + (-p0[2] + p2[2]) * t
                + (2 * p0[2] - 5 * p1[2] + 4 * p2[2] - p3[2]) * t2
                + (-p0[2] + 3 * p1[2] - 3 * p2[2] + p3[2]) * t3
            )

            points.append((x, y, z))

    # Append the final point
    points.append(control_points[-1])
    return points


def apply_wave_to_curve(
    curve_points: list[tuple[float, float, float]],
    amplitude: float,
    frequency: float,
    phase: float = 0.0,
) -> list[tuple[float, float, float]]:
    """Apply a sine-wave deformation to curve points (lateral sway).

    This modifies the x and z coordinates of each point based on its
    parametric position along the curve.  It creates a sinusoidal
    displacement perpendicular to the primary curve direction, producing
    wave-like flowing hair.

    Args:
        curve_points: Input curve points (from interpolate_curve_points).
        amplitude: Peak displacement in meters.
        frequency: Number of full sine waves along the strand length.
        phase: Phase offset in radians.

    Returns:
        Modified curve points with wave applied.
    """
    if amplitude <= 0.0 or frequency <= 0.0:
        return list(curve_points)

    n = len(curve_points)
    if n < 2:
        return list(curve_points)

    result: list[tuple[float, float, float]] = []
    for i, (x, y, z) in enumerate(curve_points):
        t = i / (n - 1)  # 0..1 along strand
        displacement = amplitude * math.sin(frequency * t * 2.0 * math.pi + phase)
        result.append((x + displacement, y, z + displacement * 0.3))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Blender-dependent hair mesh generation
# ══════════════════════════════════════════════════════════════════════════════


class HairMeshGenerator:
    """Procedural hair mesh generation using Blender Bezier curves.

    Pipeline: guide_curves → style_modifier → Bezier curve objects →
              convert to mesh → assign material → parent to head bone →
              shape keys from curl_tightness.
    """

    def __init__(self) -> None:
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "HairMeshGenerator requires bpy (Blender). "
                "Run inside Blender or use the pure-Python geometry functions."
            )

    def generate(
        self,
        style_name: str,
        head_center: tuple[float, float, float] = (0.0, 1.65, 0.0),
        head_radius: float = 0.10,
        color_config: dict | None = None,
    ) -> HairMeshResult:
        """Generate a procedural hair mesh for the given style.

        Args:
            style_name: Key from HAIR_MESH_STYLES.
            head_center: World-space center of the head sphere.
            head_radius: Head radius in meters.
            color_config: Dict with 'roots_hsv' and 'tips_hsv' tuples.

        Returns:
            HairMeshResult with Blender object info.
        """
        if style_name not in HAIR_MESH_STYLES:
            logger.warning("Unknown style '%s', defaulting to 'long_straight'", style_name)
            style_name = "long_straight"

        cfg = HAIR_MESH_STYLES[style_name]
        guide_curves = generate_guide_curves(style_name, head_center, head_radius)
        strand_count = compute_strand_count(style_name, cfg["strand_density"])
        bevel_radius = cfg["cross_section_radius"]

        # Collect all interpolated curve data
        all_curve_points: list[list[tuple[float, float, float]]] = []
        for guide in guide_curves:
            pts = interpolate_curve_points(guide.control_points, subdivisions=8)
            # Apply wave if the style calls for it
            if cfg["wave_amplitude"] > 0:
                pts = apply_wave_to_curve(
                    pts, cfg["wave_amplitude"], cfg["wave_frequency"], cfg["wave_phase"]
                )
            all_curve_points.append(pts)

        # Build Blender curve objects
        collection = self._ensure_collection("Hamr_Hair")
        curve_name = f"hair_{style_name}"

        curve_data = bpy.data.curves.new(name=curve_name, type="CURVE")
        curve_data.dimensions = "3D"
        curve_data.bevel_depth = bevel_radius
        curve_data.bevel_resolution = 2  # octagonal cross-section
        curve_data.fill_mode = "FULL"

        spline_idx = 0
        for pts in all_curve_points:
            if len(pts) < 2:
                continue
            spline = curve_data.splines.new("BEZIER")
            spline.bezier_points.add(count=len(pts) - 1)
            for j, (px, py, pz) in enumerate(pts):
                bp = spline.bezier_points[j]
                bp.co = (px, py, pz)
                bp.handle_left_type = "AUTO"
                bp.handle_right_type = "AUTO"
            spline_idx += 1

        curve_obj = bpy.data.objects.new(curve_name, curve_data)
        collection.objects.link(curve_obj)

        # Convert to mesh
        bpy.context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        bpy.ops.object.convert(target="MESH")
        mesh_obj = bpy.context.active_object  # now a mesh

        # Apply material
        if color_config is None:
            color_config = {
                "roots_hsv": (0.1, 0.7, 0.6),
                "tips_hsv": (0.12, 0.3, 0.9),
            }
        mat = create_hair_material(
            f"mat_{curve_name}",
            color_config.get("roots_hsv", (0.1, 0.7, 0.6)),
            color_config.get("tips_hsv", (0.12, 0.3, 0.9)),
        )
        if mesh_obj.data.materials:
            mesh_obj.data.materials[0] = mat
        else:
            mesh_obj.data.materials.append(mat)

        # Parent to head bone
        self._parent_to_head(mesh_obj)

        # Apply shape key for curl (if curl_tightness > 0)
        curl = cfg.get("curl_tightness", 0.0)
        if curl > 0:
            self._apply_curl_shapekey(mesh_obj, curl)

        # Read back stats
        vert_count = len(mesh_obj.data.vertices)
        tri_count = len(mesh_obj.data.polygons)
        bone_chain = self._extract_bone_chain(mesh_obj)

        logger.info(
            "Hair mesh generated: %s, %d verts, %d tris",
            style_name, vert_count, tri_count,
        )

        return HairMeshResult(
            object_name=mesh_obj.name,
            bone_chain=bone_chain,
            vertex_count=vert_count,
            triangle_count=tri_count,
            style=style_name,
        )

    def _ensure_collection(self, name: str) -> Any:
        """Get or create a Blender collection by name."""
        if name in bpy.data.collections:
            return bpy.data.collections[name]
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
        return col

    def _parent_to_head(self, obj: Any) -> None:
        """Parent the hair mesh to the head bone."""
        for armature in bpy.context.scene.objects:
            if armature.type == "ARMATURE":
                obj.parent = armature
                obj.parent_type = "BONE"
                # Find head bone
                for bone in armature.data.bones:
                    if "head" in bone.name.lower():
                        obj.parent_bone = bone.name
                        break
                break

    def _apply_curl_shapekey(self, obj: Any, curl: float) -> None:
        """Add a shape key that curls the hair tips inward."""
        if not obj.data.shape_keys:
            bpy.ops.object.shape_key_add(from_mix=False)
        bpy.ops.object.shape_key_add(from_mix=False)
        if len(obj.data.shape_keys.key_blocks) < 2:
            return
        sk = obj.data.shape_keys.key_blocks[1]
        sk.name = "curl"
        sk.value = curl
        # Offset tip vertices toward center (curl inward)
        for i, v in enumerate(sk.data):
            t = i / max(len(sk.data) - 1, 1)
            if t > 0.6:
                curl_amount = curl * 0.02 * (t - 0.6) / 0.4
                v.co.x += curl_amount
                v.co.z -= curl_amount * 0.5

    def _extract_bone_chain(self, obj: Any) -> list[str]:
        """Extract vertex group names that look like bones (for spring bones)."""
        chains: list[str] = []
        for vg in obj.vertex_groups:
            if vg.name.startswith("hair_"):
                chains.append(vg.name)
        return chains


# ── Material creation ──────────────────────────────────────────────────────────

def create_hair_material(
    name: str,
    roots_hsv: tuple[float, float, float],
    tips_hsv: tuple[float, float, float],
) -> Any:
    """Create a Blender hair material with root-to-tip gradient.

    Uses a color ramp node to blend from roots_hsv at the base to
    tips_hsv at the tips, driven by the Z coordinate (height).

    Args:
        name: Material name.
        roots_hsv: (H, S, V) at the roots.
        tips_hsv: (H, S, V) at the tips.

    Returns:
        Blender Material object.

    Raises:
        RuntimeError: If bpy is not available.
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("create_hair_material requires bpy (Blender)")

    import colorsys

    # Convert HSV to RGB (colorsys uses H in 0-1 range)
    roots_rgb = colorsys.hsv_to_rgb(roots_hsv[0] / 360.0, roots_hsv[1], roots_hsv[2])
    tips_rgb = colorsys.hsv_to_rgb(tips_hsv[0] / 360.0, tips_hsv[1], tips_hsv[2])

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clean default nodes
    for node in nodes:
        nodes.remove(node)

    # Principled BSDF
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Specular IOR Level"].default_value = 0.3

    # Color ramp for gradient
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 0)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*roots_rgb, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*tips_rgb, 1.0)
    # Add a mid-point for smooth transition
    mid_elem = ramp.color_ramp.elements.new(0.5)
    mid_color = tuple(
        (r1 + r2) / 2 for r1, r2 in zip(roots_rgb, tips_rgb)
    )
    mid_elem.color = (*mid_color, 1.0)

    # Separate Z for height-based gradient
    sep = nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-700, 0)

    # Object info for position
    pos = nodes.new("ShaderNodeNewObject")
    pos.location = (-900, 0)
    pos.outputs[0].name  # position output

    # Map range to normalize Z
    map_range = nodes.new("ShaderNodeMapRange")
    map_range.location = (-550, 0)
    map_range.inputs["From Min"].default_value = 0.0
    map_range.inputs["From Max"].default_value = 2.0

    # Output
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)

    # Links
    links.new(pos.outputs[0], sep.inputs[0])
    links.new(sep.outputs[2], map_range.inputs["Value"])
    links.new(map_range.outputs[0], ramp.inputs[0])
    links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs[0], output.inputs[0])

    return mat