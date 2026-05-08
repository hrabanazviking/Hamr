"""
Pipeline Integration Layer — Bridge between Phase 11 modules and the build pipeline.

The CRITICAL GAP: build_avatar.py doesn't call ANY Phase 11 modules.
This module provides the integration stages that build_avatar.py will later call,
plus pure-Python planning, validation, and result tracking that can be tested
without Blender.

Run order for run_integration_stages():
  1. Stub bones    — hamr.rigs.stub_bones.create_missing_bones()
  2. Hair mesh     — hamr.hair.mesh.HairMeshGenerator.generate()
  3. Clothing mesh — hamr.clothing.mesh.ClothingMeshGenerator.generate()
  4. Weight paint  — hamr.rigs.weights.WeightPaintEngine.paint_smooth()
  5. Spring bones   — hamr.rigs.spring_bones.apply_spring_bones()
  6. First-person   — hamr.export.first_person.configure_first_person()

Each stage is try/except wrapped — failures are logged in errors, NOT raised.
Stage completions are appended to stages_completed.

Phase 12 T1: The forge worker welds the pipeline shut.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from hamr.core.perf import (
    PerformanceBudget,
    PerformanceReport,
    DEFAULT_PI5_BUDGET,
    check_budget,
    estimate_build_time,
)

logger = logging.getLogger("hamr.core.pipeline_integrate")


# ── Integration Result ──────────────────────────────────────────────────────

@dataclass
class IntegrationResult:
    """Complete report from running integration stages.

    Every field is populated by run_integration_stages().
    Failures are logged in ``errors``, NOT raised — the pipeline keeps running.
    """

    stages_completed: list[str] = field(default_factory=list)
    stub_bones_applied: bool = False
    hair_meshes_created: list[str] = field(default_factory=list)
    clothing_meshes_created: list[str] = field(default_factory=list)
    weight_paint_applied: bool = False
    spring_bones_configured: bool = False
    first_person_configured: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def success(self) -> bool:
        """True if no errors were recorded."""
        return len(self.errors) == 0

    @property
    def stage_count(self) -> int:
        """Number of completed stages."""
        return len(self.stages_completed)

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return (
            f"IntegrationResult({status} {self.stage_count}/6 stages "
            f"{self.elapsed_seconds:.1f}s "
            f"errs={len(self.errors)} warns={len(self.warnings)})"
        )


# ── Stage Names ─────────────────────────────────────────────────────────────

STAGE_STUB_BONES = "stub_bones"
STAGE_HAIR_MESH = "hair_mesh"
STAGE_CLOTHING_MESH = "clothing_mesh"
STAGE_WEIGHT_PAINT = "weight_paint"
STAGE_SPRING_BONES = "spring_bones"
STAGE_FIRST_PERSON = "first_person"

ALL_STAGES: list[str] = [
    STAGE_STUB_BONES,
    STAGE_HAIR_MESH,
    STAGE_CLOTHING_MESH,
    STAGE_WEIGHT_PAINT,
    STAGE_SPRING_BONES,
    STAGE_FIRST_PERSON,
]

# ── Stage Time Estimates (seconds on Pi 5) ─────────────────────────────────

_STAGE_TIME_ESTIMATES: dict[str, float] = {
    STAGE_STUB_BONES: 0.5,
    STAGE_HAIR_MESH: 5.0,
    STAGE_CLOTHING_MESH: 3.0,
    STAGE_WEIGHT_PAINT: 4.0,
    STAGE_SPRING_BONES: 1.0,
    STAGE_FIRST_PERSON: 0.5,
}


# ── Pure-Python Functions (no bpy) ─────────────────────────────────────────

def plan_stages(spec: Any) -> list[str]:
    """Return the ordered list of stages that *will* run for a given spec.

    Stages are skipped when their spec section is missing or explicitly
    disabled.  Pure-Python — no Blender required.

    Args:
        spec: A CharacterSpec or any object with .hair, .clothing, .physics,
              and .export attributes.  Also accepts a plain dict (from JSON).

    Returns:
        Ordered list of stage name strings.
    """
    stages: list[str] = []

    # Stub bones: always run — every VRM needs the 25 humanoid bones
    stages.append(STAGE_STUB_BONES)

    # Hair mesh: skip if hair.style == "none" or hair is None
    hair = _get_attr(spec, "hair")
    if hair is not None:
        hair_style = _get_attr(hair, "style", default="straight")
        if hair_style != "none":
            stages.append(STAGE_HAIR_MESH)
    elif isinstance(spec, dict):
        hair_dict = spec.get("hair")
        if hair_dict is not None:
            hair_style = hair_dict.get("style", "straight")
            if hair_style != "none":
                stages.append(STAGE_HAIR_MESH)

    # Clothing mesh: skip if clothing list is empty
    clothing = _get_attr(spec, "clothing", default=None)
    if isinstance(spec, dict):
        clothing = spec.get("clothing", [])
    if clothing:
        stages.append(STAGE_CLOTHING_MESH)

    # Weight paint: always run if we have body + any additional meshes
    # (hair or clothing) — but conservatively always include if hair or
    # clothing stages are present
    has_hair = STAGE_HAIR_MESH in stages
    has_clothing = STAGE_CLOTHING_MESH in stages
    if has_hair or has_clothing:
        stages.append(STAGE_WEIGHT_PAINT)
    else:
        # Still weight paint the body mesh even without extras
        stages.append(STAGE_WEIGHT_PAINT)

    # Spring bones: always run — hair physics + breast physics configured
    stages.append(STAGE_SPRING_BONES)

    # First-person: always run — every VRM needs mesh annotations
    stages.append(STAGE_FIRST_PERSON)

    return stages


def estimate_stage_time(stage_name: str) -> float:
    """Pre-flight time estimate in seconds for a single integration stage.

    Pure-Python — no Blender required.

    Args:
        stage_name: One of the STAGE_* constants.

    Returns:
        Estimated time in seconds on Pi 5 hardware.
    """
    return _STAGE_TIME_ESTIMATES.get(stage_name, 1.0)


def validate_spec_completeness(spec: Any) -> list[str]:
    """Return a list of warnings for missing or incomplete spec fields.

    Pure-Python — no Blender required.  Does not raise; only collects
    warnings for fields that should be present for a complete build.

    Args:
        spec: A CharacterSpec, dict, or any object with spec attributes.

    Returns:
        List of warning strings.  Empty list means the spec is fully specified.
    """
    warnings: list[str] = []

    # Body
    body = _get_attr(spec, "body")
    if body is None:
        warnings.append("Missing 'body' section — default proportions will be used")
    else:
        height = _get_attr(body, "height_cm")
        if height is None:
            warnings.append("body.height_cm not set — default (173cm) will be used")

    # Face
    face = _get_attr(spec, "face")
    if face is None:
        warnings.append("Missing 'face' section — default face will be generated")

    # Hair
    hair = _get_attr(spec, "hair")
    if hair is None:
        warnings.append("Missing 'hair' section — no hair mesh will be generated")
    else:
        hair_style = _get_attr(hair, "style")
        if hair_style is None:
            warnings.append("hair.style not set — default ('wild-curly') will be used")
        hair_color = _get_attr(hair, "color")
        if hair_color is None:
            warnings.append("hair.color not set — default gradient will be applied")

    # Clothing: warn only if the key is missing entirely (None).
    # An empty list [] is a valid explicit choice — no clothes.
    clothing = _get_attr(spec, "clothing")
    if clothing is None:
        warnings.append("No clothing spec — avatar will be bare")

    # Physics
    physics = _get_attr(spec, "physics")
    if physics is None:
        warnings.append("Missing 'physics' section — default spring bone physics will be used")
    else:
        hair_phys = _get_attr(physics, "hair")
        if hair_phys is None:
            warnings.append("physics.hair not set — default hair spring bone stiffness applied")

    # Export
    export = _get_attr(spec, "export")
    if export is None:
        warnings.append("Missing 'export' section — VRM 1.0 defaults will be used")

    # Expressions
    expressions = _get_attr(spec, "expressions")
    if expressions is None:
        warnings.append("Missing 'expressions' section — default expressions will be generated")

    return warnings


# ── Integration Runner (requires Blender) ────────────────────────────────────

def run_integration_stages(
    armature_name: str,
    mesh_names: list[str],
    spec: Any,
    budget: PerformanceBudget | None = None,
) -> IntegrationResult:
    """Run all Phase 11 integration stages inside Blender.

    Each stage is try/except wrapped. Failures are recorded in
    ``result.errors`` and the pipeline continues to the next stage.
    This means a hair mesh failure won't block weight painting, etc.

    Args:
        armature_name: Name of the armature object in the Blender scene.
        mesh_names: List of mesh object names currently in the scene.
        spec: CharacterSpec (or dict) describing the character.
        budget: Optional PerformanceBudget for triangle/time checks.
                If provided, the run is aborted early if the budget is exceeded.

    Returns:
        IntegrationResult with full report of what succeeded and what failed.

    Raises:
        RuntimeError: If bpy is not available (not running inside Blender).
    """
    try:
        import bpy  # type: ignore
    except ImportError:
        raise RuntimeError(
            "run_integration_stages() requires Blender (bpy). "
            "Use plan_stages(), estimate_stage_time(), or validate_spec_completeness() "
            "for pure-Python operations."
        )

    result = IntegrationResult()
    start = time.time()

    # ── Pre-flight budget check ──────────────────────────────────────
    if budget is not None:
        # Extract character spec for budget estimation
        char_spec = _extract_character_spec(spec)
        perf_report = check_budget(char_spec, budget)
        if not perf_report.within_budget:
            result.errors.append(
                f"Spec exceeds performance budget: "
                + "; ".join(perf_report.warnings)
            )
            result.elapsed_seconds = time.time() - start
            return result
        if perf_report.warnings:
            result.warnings.extend(perf_report.warnings)

    # ── Stage 1: Stub Bones ──────────────────────────────────────────
    try:
        from hamr.rigs.stub_bones import create_missing_bones
        stub_result = create_missing_bones(armature_name, base_type="mblab")
        result.stub_bones_applied = True
        result.stages_completed.append(STAGE_STUB_BONES)
        if stub_result and hasattr(stub_result, "created_bones"):
            logger.info(
                f"Stub bones created: {list(stub_result.created_bones.keys())}"
            )
    except Exception as exc:
        result.errors.append(f"Stub bones failed: {exc}")
        logger.error(f"Stage {STAGE_STUB_BONES} failed: {exc}")

    # ── Stage 2: Hair Mesh ──────────────────────────────────────────
    hair_spec = _get_attr(spec, "hair")
    if hair_spec is not None:
        hair_style = _get_attr(hair_spec, "style", default="straight")
    elif isinstance(spec, dict):
        hair_dict = spec.get("hair", {})
        hair_style = hair_dict.get("style", "straight")
    else:
        hair_style = "none"

    if hair_style != "none":
        try:
            from hamr.hair.mesh import HairMeshGenerator
            head_pos, head_radius = _get_head_position(bpy, armature_name)
            color_config = _get_hair_color_config(spec)
            gen = HairMeshGenerator()
            hair_result = gen.generate(
                style_name=hair_style,
                head_center=head_pos,
                head_radius=head_radius,
                color_config=color_config,
            )
            result.hair_meshes_created.append(hair_result.object_name)
            result.stages_completed.append(STAGE_HAIR_MESH)
            logger.info(
                f"Hair mesh generated: {hair_result.object_name}, "
                f"{hair_result.vertex_count} verts, {hair_result.triangle_count} tris"
            )
        except Exception as exc:
            result.errors.append(f"Hair mesh failed: {exc}")
            logger.error(f"Stage {STAGE_HAIR_MESH} failed: {exc}")

    # ── Stage 3: Clothing Mesh ───────────────────────────────────────
    clothing_spec = _get_attr(spec, "clothing")
    if isinstance(spec, dict):
        clothing_spec = spec.get("clothing", [])
    if clothing_spec:
        try:
            from hamr.clothing.mesh import ClothingMeshGenerator
            body_mesh_name = _find_body_mesh(bpy)
            gen = ClothingMeshGenerator()
            cloth_items = _iter_clothing_spec(clothing_spec)
            for i, cloth_obj in enumerate(cloth_items):
                try:
                    cloth_result = gen.generate(
                        spec=cloth_obj,
                        body_mesh_name=body_mesh_name or "",
                        armature_name=armature_name,
                    )
                    result.clothing_meshes_created.append(cloth_result.mesh_name)
                    logger.info(
                        f"Clothing mesh {i}: {cloth_result.mesh_name}, "
                        f"{cloth_result.triangle_count} tris"
                    )
                except Exception as inner_exc:
                    result.warnings.append(
                        f"Clothing item {i} failed: {inner_exc}"
                    )
                    logger.warning(f"Clothing item {i} failed: {inner_exc}")
            result.stages_completed.append(STAGE_CLOTHING_MESH)
        except Exception as exc:
            result.errors.append(f"Clothing mesh stage failed: {exc}")
            logger.error(f"Stage {STAGE_CLOTHING_MESH} failed: {exc}")

    # ── Stage 4: Weight Paint ───────────────────────────────────────
    try:
        from hamr.rigs.weights import WeightPaintEngine
        engine = WeightPaintEngine()
        body_mesh_name = _find_body_mesh(bpy)
        if body_mesh_name:
            engine.paint_smooth(
                armature_name=armature_name,
                mesh_name=body_mesh_name,
                influence_radius=0.3,
                iterations=3,
            )
            engine.normalize_weights(armature_name, body_mesh_name)

        for cloth_name in result.clothing_meshes_created:
            if body_mesh_name:
                try:
                    engine.transfer_weights(
                        source_mesh=body_mesh_name,
                        target_mesh=cloth_name,
                    )
                    engine.normalize_weights(armature_name, cloth_name)
                except Exception as inner_exc:
                    result.warnings.append(
                        f"Weight transfer to {cloth_name} failed: {inner_exc}"
                    )

        for hair_name in result.hair_meshes_created:
            try:
                engine.normalize_weights(armature_name, hair_name)
            except Exception as inner_exc:
                result.warnings.append(
                    f"Weight normalization for {hair_name} failed: {inner_exc}"
                )

        result.weight_paint_applied = True
        result.stages_completed.append(STAGE_WEIGHT_PAINT)
    except Exception as exc:
        result.errors.append(f"Weight paint failed: {exc}")
        logger.error(f"Stage {STAGE_WEIGHT_PAINT} failed: {exc}")

    # ── Stage 5: Spring Bones ───────────────────────────────────────
    try:
        from hamr.rigs.spring_bones import (
            configure_hair_spring,
            configure_breast_spring,
            configure_clothing_spring,
            apply_spring_bones,
            DEFAULT_COLLIDERS,
        )
        from hamr.core.models import HairPhysicsSpec, PhysicsSpec

        spring_groups = []

        # Hair spring bones
        hair_physics = None
        physics_obj = _get_attr(spec, "physics")
        if physics_obj is not None:
            hair_physics_raw = _get_attr(physics_obj, "hair")
            if hair_physics_raw is not None:
                if isinstance(hair_physics_raw, HairPhysicsSpec):
                    hair_physics = hair_physics_raw
                elif isinstance(hair_physics_raw, dict):
                    hair_physics = HairPhysicsSpec(**hair_physics_raw)

        hair_spring = configure_hair_spring(hair_physics)

        # If hair mesh was created, try to set bone chains
        if result.hair_meshes_created:
            # Hair mesh generator would have created bone chains;
            # we reference them by convention
            try:
                from hamr.hair.mesh import HairMeshGenerator
                # Bone chains come from the hair mesh result
                # For now, use standard naming convention
                pass
            except Exception:
                pass
        spring_groups.append(hair_spring)

        # Breast spring bones
        body_spec = _get_attr(spec, "body")
        breast_spring = configure_breast_spring(body_spec if body_spec else {})
        spring_groups.append(breast_spring)

        # Clothing spring bones
        for cloth_name in result.clothing_meshes_created:
            cloth_type = "skirt"  # default
            cloth_spring = configure_clothing_spring(
                clothing_name=cloth_name,
                cloth_type=cloth_type,
            )
            spring_groups.append(cloth_spring)

        spring_result = apply_spring_bones(
            armature_name=armature_name,
            spring_groups=spring_groups,
            colliders=DEFAULT_COLLIDERS,
        )
        result.spring_bones_configured = True
        result.stages_completed.append(STAGE_SPRING_BONES)
        logger.info(
            f"Spring bones configured: "
            f"{len(spring_result.get('spring_groups', []))} groups, "
            f"{len(spring_result.get('colliders', []))} colliders"
        )
    except Exception as exc:
        result.errors.append(f"Spring bones failed: {exc}")
        logger.error(f"Stage {STAGE_SPRING_BONES} failed: {exc}")

    # ── Stage 6: First-Person Annotations ────────────────────────────
    try:
        from hamr.export.first_person import configure_first_person

        # Collect all mesh names in the scene
        all_mesh_names = [
            obj.name for obj in bpy.data.objects if obj.type == "MESH"
        ]
        fp_config = configure_first_person(
            armature_name=armature_name,
            mesh_names=all_mesh_names,
        )
        result.first_person_configured = True
        result.stages_completed.append(STAGE_FIRST_PERSON)
        logger.info(
            f"First-person configured: {len(fp_config.mesh_annotations)} meshes, "
            f"bone={fp_config.first_person_bone}"
        )
    except Exception as exc:
        result.errors.append(f"First-person configuration failed: {exc}")
        logger.error(f"Stage {STAGE_FIRST_PERSON} failed: {exc}")

    result.elapsed_seconds = time.time() - start
    logger.info(
        f"Integration complete: {result.stage_count}/6 stages in "
        f"{result.elapsed_seconds:.1f}s "
        f"(errors={len(result.errors)}, warnings={len(result.warnings)})"
    )
    return result


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Get an attribute from an object, dict, or return default.

    Works with dataclasses (via getattr) and plain dicts (via .get()).
    """
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_character_spec(spec: Any):
    """Extract a CharacterSpec-compatible object from spec or dict.

    If spec is already a CharacterSpec, return it.
    If it's a dict with a 'character' key, return the inner object.
    Otherwise return the spec as-is (still works with perf check functions).
    """
    if isinstance(spec, dict):
        if "character" in spec:
            return spec["character"]
        return spec
    return spec


def _get_head_position(bpy, armature_name: str):
    """Get head bone position from the armature in the Blender scene.

    Returns:
        Tuple of (head_pos, head_radius).
    """
    armature = bpy.data.objects.get(armature_name)
    if armature and hasattr(armature, "data") and armature.data:
        head_bone = armature.data.bones.get("head")
        if head_bone:
            head_pos = tuple(armature.matrix_world @ head_bone.head_local)
            head_radius = 0.10  # Standard head radius in meters
            return head_pos, head_radius
    # Default fallback: standard anime character head position
    return (0.0, 0.0, 1.65), 0.10


def _find_body_mesh(bpy) -> str | None:
    """Find the body mesh in the current Blender scene.

    Returns the name of the first mesh with 'body' in the name,
    or the first mesh object if no body-named mesh exists.
    """
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if not mesh_objects:
        return None
    # Prefer mesh with 'body' in name
    for obj in mesh_objects:
        if "body" in obj.name.lower():
            return obj.name
    # Fall back to first mesh
    return mesh_objects[0].name


def _get_hair_color_config(spec: Any) -> dict | None:
    """Extract hair color configuration from spec for HairMeshGenerator."""
    hair = _get_attr(spec, "hair")
    if hair is None and isinstance(spec, dict):
        hair = spec.get("hair")

    if hair is None:
        return None

    color = _get_attr(hair, "color")
    if color is None:
        return None

    # Build color config dict with roots/tips HSV
    from hamr.core.models import HairColorSpec

    if isinstance(color, HairColorSpec):
        return {
            "roots_hsv": _hex_to_hsv(color.roots),
            "tips_hsv": _hex_to_hsv(color.tips),
        }
    elif isinstance(color, dict):
        return {
            "roots_hsv": _hex_to_hsv(color.get("roots", "#C4A265")),
            "tips_hsv": _hex_to_hsv(color.get("tips", "#F5E6B8")),
        }

    return None


def _hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color string to HSV tuple (0-1 range)."""
    import colorsys

    hex_color = hex_color.lstrip("#")
    r = int(hex_color[:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return colorsys.rgb_to_hsv(r, g, b)


def _iter_clothing_spec(clothing_spec):
    """Iterate over clothing spec items, yielding spec objects.

    Handles both list-of-dicts and list-of-ClothingSpec.
    """
    from hamr.core.models import ClothingSpec

    if not clothing_spec:
        return

    for item in clothing_spec:
        if isinstance(item, ClothingSpec):
            yield item
        elif isinstance(item, dict):
            yield ClothingSpec.from_dict(item)