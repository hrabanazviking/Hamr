"""
Hamr Build Script — Runs INSIDE Blender via ``--python``.

This is the Blender-side forge. It receives a Hamr CharacterSpec
as JSON, applies all modifications, and exports a VRM 1.0 file.

Embodies every hard-won lesson from Seiðr-Smiðja:
- D-008: Never auto-map bones. Always be explicit.
- D-009: filter_by_human_bone_hierarchy=False for non-standard rigs
- D-011: Symmetric expressions bind BOTH L and R shape keys
- D-012: VRM lookAt uses bone rotation, not morph targets
- D-013: Expression binds use shape key NAME string, not index
- D-016: Use EXEC_DEFAULT for VRM export in headless mode
- D-017: Allow non-humanoid rig as safety net
- D-018: Use human_bone_name_to_human_bone() canonical API
- D-019: VRM 1.0 enum identifiers are lowercase ('bone', 'expression')

Exit codes:
    0 = success
    1 = usage/argument error
    2 = spec read/parse error
    3 = import error (base mesh)
    4 = transformation error
    5 = VRM export error
    6 = post-export validation error
"""

from __future__ import annotations

import colorsys
import json
import logging
import os
import struct
import sys
from pathlib import Path

logger = logging.getLogger("hamr_build")
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.DEBUG)


# ──────────────────────────────────────────────────────────────────────────────
# Bone Maps — MB-Lab & TurboSquid
# ──────────────────────────────────────────────────────────────────────────────

# FP-2: Canonical MB-Lab bone map consolidated in hamr.core.constants
from hamr.core.constants import MB_LAB_BONE_MAP

# MB-Lab expression presets → shape key bindings (using actual MB-Lab expression names)
# After finalize_character, shape keys use the "Expressions_" prefix
MB_LAB_EXPRESSION_MAP: dict[str, list[dict]] = {
    "happy": [
        {"shape_key": "Expressions_mouthSmile_max", "weight": 1.0},
        {"shape_key": "Expressions_eyeClosedL_max", "weight": 0.3},
        {"shape_key": "Expressions_eyeClosedR_max", "weight": 0.3},
    ],
    "angry": [
        {"shape_key": "Expressions_browSqueezeL_max", "weight": 1.0},
        {"shape_key": "Expressions_browSqueezeR_max", "weight": 1.0},
        {"shape_key": "Expressions_mouthOpenAggr_max", "weight": 0.7},
    ],
    "sad": [
        {"shape_key": "Expressions_mouthSmile_min", "weight": 0.8},
        {"shape_key": "Expressions_eyeClosedL_max", "weight": 0.3},
        {"shape_key": "Expressions_eyeClosedR_max", "weight": 0.3},
    ],
    "relaxed": [
        {"shape_key": "Expressions_mouthSmile_max", "weight": 0.2},
    ],
    "surprised": [
        {"shape_key": "Expressions_eyesVert_max", "weight": 1.0},
        {"shape_key": "Expressions_mouthOpen_max", "weight": 0.7},
    ],
    "blink": [
        {"shape_key": "Expressions_eyeClosedL_max", "weight": 1.0},
        {"shape_key": "Expressions_eyeClosedR_max", "weight": 1.0},
    ],
    "blinkLeft": [
        {"shape_key": "Expressions_eyeClosedL_max", "weight": 1.0},
    ],
    "blinkRight": [
        {"shape_key": "Expressions_eyeClosedR_max", "weight": 1.0},
    ],
    "aa": [
        {"shape_key": "Expressions_mouthOpen_max", "weight": 1.0},
    ],
    "ih": [
        {"shape_key": "Expressions_mouthHoriz_max", "weight": 0.6},
    ],
    "ou": [
        {"shape_key": "Expressions_mouthOpenO_max", "weight": 1.0},
    ],
    "ee": [
        {"shape_key": "Expressions_mouthSmile_max", "weight": 0.5},
        {"shape_key": "Expressions_mouthHoriz_max", "weight": 0.3},
    ],
    "oh": [
        {"shape_key": "Expressions_mouthOpenO_max", "weight": 0.7},
    ],
}

TURBOSQUID_BONE_MAP: dict[str, str] = {
    "hips": "Hip",
    "spine": "Spine01",
    "chest": "Spine02",
    "upperChest": "Spine03",
    "neck": "NeckTwist02",
    "head": "Head",
    "leftUpperLeg": "L_Thigh",
    "leftLowerLeg": "L_Calf",
    "leftFoot": "L_Foot",
    "leftToes": "L_Toe",
    "rightUpperLeg": "R_Thigh",
    "rightLowerLeg": "R_Calf",
    "rightFoot": "R_Foot",
    "rightToes": "R_Toe",
    "leftShoulder": "L_Shoulder",
    "leftUpperArm": "L_UpperArm",
    "leftLowerArm": "L_Forearm",
    "leftHand": "L_Hand",
    "rightShoulder": "R_Shoulder",
    "rightUpperArm": "R_UpperArm",
    "rightLowerArm": "R_Forearm",
    "rightHand": "R_Hand",
    "leftEye": "L_Eye",
    "rightEye": "R_Eye",
    "jaw": "UpperJaw",
}

# Material keyword categories
SKIN_KEYWORDS = ("skin", "body", "head", "arm", "leg", "face")
EYE_KEYWORDS = ("eye", "iris", "cornea")
HAIR_KEYWORDS = ("hair", "hairs", "scalp")
NAIL_KEYWORDS = ("nail", "nails")
LIP_KEYWORDS = ("lip", "lips", "mouth_inner")

# TurboSquid expression map — standard humanoid rig shape keys
# mesh name resolved dynamically at runtime via _find_body_mesh()
TURBOSQUID_EXPRESSION_MAP: dict[str, list[dict]] = {
    "happy": [
        {"shape_key": "Smile", "weight": 1.0},
        {"shape_key": "EyeSquint_L", "weight": 0.4},
        {"shape_key": "EyeSquint_R", "weight": 0.4},
    ],
    "angry": [
        {"shape_key": "BrowFurrow_L", "weight": 1.0},
        {"shape_key": "BrowFurrow_R", "weight": 1.0},
        {"shape_key": "Frown_L", "weight": 0.5},
        {"shape_key": "Frown_R", "weight": 0.5},
    ],
    "sad": [
        {"shape_key": "Frown_L", "weight": 1.0},
        {"shape_key": "Frown_R", "weight": 1.0},
        {"shape_key": "BrowSad_L", "weight": 0.6},
        {"shape_key": "BrowSad_R", "weight": 0.6},
    ],
    "relaxed": [
        {"shape_key": "Smile", "weight": 0.3},
    ],
    "surprised": [
        {"shape_key": "EyeWide_L", "weight": 1.0},
        {"shape_key": "EyeWide_R", "weight": 1.0},
        {"shape_key": "JawOpen", "weight": 0.5},
    ],
    "blink": [
        {"shape_key": "Blink_L", "weight": 1.0},
        {"shape_key": "Blink_R", "weight": 1.0},
    ],
    "blinkLeft": [
        {"shape_key": "Blink_L", "weight": 1.0},
    ],
    "blinkRight": [
        {"shape_key": "Blink_R", "weight": 1.0},
    ],
    "aa": [
        {"shape_key": "JawOpen", "weight": 1.0},
    ],
    "ih": [
        {"shape_key": "MouthWide", "weight": 0.6},
    ],
    "ou": [
        {"shape_key": "MouthPucker", "weight": 1.0},
    ],
    "ee": [
        {"shape_key": "Smile", "weight": 0.5},
        {"shape_key": "MouthWide", "weight": 0.5},
    ],
    "oh": [
        {"shape_key": "JawOpen", "weight": 0.7},
    ],
}


def parse_args(argv: list[str]) -> dict:
    """Parse command-line arguments."""
    args = {"spec": None, "base": None, "output": None, "max_tex": 0, "force_over_budget": False}
    i = 0
    while i < len(argv):
        if argv[i] == "--spec" and i + 1 < len(argv):
            args["spec"] = argv[i + 1]; i += 2
        elif argv[i] == "--base" and i + 1 < len(argv):
            args["base"] = argv[i + 1]; i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            args["output"] = argv[i + 1]; i += 2
        elif argv[i] == "--max-tex" and i + 1 < len(argv):
            args["max_tex"] = int(argv[i + 1]); i += 2
        elif argv[i] == "--force-over-budget":
            args["force_over_budget"] = True; i += 1
        else:
            i += 1
    return args


def main() -> int:
    """Main build pipeline — runs inside Blender."""
    try:
        import bpy  # type: ignore
    except ImportError:
        logger.error("This script must run inside Blender (bpy not available)")
        return 1

    argv = sys.argv
    if "--" in argv:
        args = parse_args(argv[argv.index("--") + 1:])
    else:
        logger.error("No arguments passed (expected -- separator)")
        return 1

    if not args["spec"]:
        logger.error("--spec argument required")
        return 1
    if not args["output"]:
        logger.error("--output argument required")
        return 1

    # Load spec
    spec_path = Path(args["spec"])
    if not spec_path.exists():
        logger.error(f"Spec file not found: {spec_path}")
        return 2

    try:
        spec_data = json.loads(spec_path.read_text())
        logger.info(f"Loaded spec: {spec_data.get('name', 'unknown')}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON spec: {e}")
        return 2

    output_path = Path(args["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Pre-flight: Performance budget check ──────────────────────────────
    try:
        from hamr.core.perf import check_budget, DEFAULT_PI5_BUDGET
        char_spec = spec_data.get("character", spec_data)
        perf_report = check_budget(char_spec, DEFAULT_PI5_BUDGET)
        if not perf_report.within_budget:
            logger.warning(f"⚠ Spec over budget: {perf_report.summary()}")
            if not args.get("force_over_budget"):
                logger.error("Aborting: spec exceeds performance budget. Use --force-over-budget to override.")
                return 2
        elif perf_report.warnings:
            for w in perf_report.warnings:
                logger.warning(f"Budget warning: {w}")
    except Exception as exc:
        logger.debug(f"Performance budget check skipped: {exc}")

    # ── Step 0: Enable VRM Add-on ────────────────────────────────────────
    try:
        import addon_utils  # type: ignore
        addon_utils.enable("io_scene_vrm", default_set=True)
        try:
            bpy.ops.wm.save_userpref()
        except Exception:
            pass
        logger.info("VRM Add-on enabled")
    except Exception as exc:
        logger.warning(f"Could not enable VRM add-on: {exc}")

    # ── Step 1: Clear scene ──────────────────────────────────────────────
    _clear_scene(bpy)

    # ── Step 2: Import base mesh ─────────────────────────────────────────
    base_path = args.get("base")
    if base_path:
        try:
            _import_base(bpy, base_path)
        except Exception as exc:
            logger.error(f"Base mesh import failed: {exc}")
            return 3
    else:
        # Try to use MB-Lab to generate a base mesh
        try:
            _generate_mblab_base(bpy)
        except Exception as exc:
            logger.error(f"MB-Lab base generation failed: {exc}")
            return 3

    # ── Step 3: Apply spec transformations ────────────────────────────────
    forge_config = spec_data.pop("forge_config", None)
    try:
        _apply_spec(bpy, spec_data, forge_config=forge_config)
    except Exception as exc:
        logger.error(f"Spec application failed: {exc}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 4

    # ── Find armature (used by integration steps) ───────────────────────
    armature_name = ""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature_name = obj.name
            break

    # ══════════════════════════════════════════════════════════════════════
    # ── Phase 12 integration steps ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    stub_result = None  # Carried forward for VRM bone mapping

    # ── Step 3a: Create stub bones ────────────────────────────────────────
    if armature_name:
        try:
            stub_result = _integrate_stub_bones(bpy, armature_name)
        except Exception as exc:
            logger.warning(f"Stub bone integration failed: {exc}")

    # ── Step 3b: Generate hair mesh ───────────────────────────────────────
    hair_result = None
    try:
        hair_result = _integrate_hair_mesh(bpy, spec_data, forge_config, armature_name)
    except Exception as exc:
        logger.warning(f"Hair mesh integration failed: {exc}")

    # ── Step 3c: Generate clothing meshes ─────────────────────────────────
    clothing_results = []
    try:
        clothing_results = _integrate_clothing_meshes(
            bpy, spec_data, forge_config, armature_name
        )
    except Exception as exc:
        logger.warning(f"Clothing mesh integration failed: {exc}")

    # ── Step 3d: Weight paint all meshes ─────────────────────────────────
    try:
        _integrate_weight_paint(bpy, armature_name, hair_result, clothing_results)
    except Exception as exc:
        logger.warning(f"Weight paint integration failed: {exc}")

    # ── Step 3e: Configure spring bones ───────────────────────────────────
    try:
        _integrate_spring_bones(
            bpy, armature_name, spec_data, forge_config,
            hair_result, clothing_results,
        )
    except Exception as exc:
        logger.warning(f"Spring bone integration failed: {exc}")

    # ── Step 3f: Configure first-person annotations ──────────────────────
    try:
        _integrate_first_person(bpy, armature_name, hair_result, clothing_results)
    except Exception as exc:
        logger.warning(f"First-person integration failed: {exc}")

    # ══════════════════════════════════════════════════════════════════════
    # ── End Phase 12 integration ────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    # ── Step 4: VRM humanoid bone mapping (with stub merge) ──────────────
    _apply_vrm_humanoid(bpy, spec_data, stub_result=stub_result)

    # ── Step 5: VRM metadata ─────────────────────────────────────────────
    _apply_vrm_metadata(bpy, spec_data)

    # ── Step 6: VRM expressions ──────────────────────────────────────────
    _apply_vrm_expressions(bpy, spec_data)

    # ── Step 7: VRM lookAt ───────────────────────────────────────────────
    _apply_vrm_look_at(bpy, spec_data)

    # ── Step 8: Export VRM ───────────────────────────────────────────────
    os.environ["BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION"] = "true"

    if not armature_name:
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                armature_name = obj.name
                break

    try:
        result = bpy.ops.export_scene.vrm(
            "EXEC_DEFAULT",
            filepath=str(output_path),
            armature_object_name=armature_name,
            ignore_warning=True,
        )
        if "FINISHED" not in result:
            logger.error(f"VRM export returned {result}")
            return 5
        logger.info(f"VRM exported: {output_path}")
    except Exception as exc:
        logger.error(f"VRM export failed: {exc}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 5

    # ── Step 9: Post-export validation ────────────────────────────────────
    try:
        _validate_vrm(str(output_path))
    except Exception as exc:
        logger.warning(f"Post-export validation warning: {exc}")

    # ── Step 10: Rig verification ─────────────────────────────────────────
    try:
        from hamr.rigs.verify import RigVerifier
        verifier = RigVerifier()
        report = verifier.verify(str(output_path))
        if report.get("warnings"):
            for w in report["warnings"]:
                logger.warning(f"Rig warning: {w}")
        if report.get("missing"):
            logger.warning(f"Missing bones: {report['missing']}")
        else:
            logger.info("Rig verification passed")
    except ImportError:
        logger.debug("Rig verification module not available outside Blender")
    except Exception as exc:
        logger.warning(f"Rig verification skipped: {exc}")

    logger.info("Build complete.")
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# Scene Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _clear_scene(bpy) -> None:
    """Remove all objects and orphan data."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=True)

    for block_type in ("meshes", "materials", "textures", "images",
                       "armatures", "actions", "cameras", "lights",
                       "curves", "metaballs", "lattices",
                       "shape_keys", "particle_settings", "node_groups"):
        try:
            collection = getattr(bpy.data, block_type)
        except AttributeError:
            continue
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)

    try:
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, recursive=True)
    except Exception:
        pass

    logger.info("Scene cleared")


def _import_base(bpy, base_path: str) -> None:
    """Import a base mesh file."""
    ext = Path(base_path).suffix.lower()
    if ext == ".vrm":
        result = bpy.ops.import_scene.vrm(filepath=base_path)
    elif ext == ".fbx":
        result = bpy.ops.import_scene.fbx(filepath=base_path)
    elif ext == ".glb":
        result = bpy.ops.import_scene.gltf(filepath=base_path)
    elif ext == ".obj":
        result = bpy.ops.wm.obj_import(filepath=base_path)
    else:
        raise ValueError(f"Unsupported format: {ext}")

    if "FINISHED" not in result:
        raise RuntimeError(f"Import returned {result} for {base_path}")
    logger.info(f"Imported base mesh: {base_path}")


def _generate_mblab_base(bpy) -> None:
    """Generate a base mesh using MB-Lab: init → auto_model → finalize."""
    # Ensure MB-Lab addon is enabled
    try:
        bpy.ops.preferences.addon_enable(module="mb-lab")
        logger.info("MB-Lab addon enabled")
    except Exception:
        pass  # May already be enabled

    # FP-3: CANCELLED result from MB-Lab often indicates a silent failure.
    # Log a warning, retry once, and raise BuildError if still CANCELLED.
    # Step 1: Initialize character (creates base mesh f_af01 + armature)
    try:
        result = bpy.ops.mbast.init_character()
        if "CANCELLED" in result:
            logger.warning(f"MB-Lab init_character returned CANCELLED — retrying once")
            result = bpy.ops.mbast.init_character()
            if "CANCELLED" in result:
                from hamr.core.errors import BuildError
                raise BuildError(
                    "MB-Lab init_character returned CANCELLED after retry",
                    stage="mblab_init",
                    details=f"Result: {result}",
                )
        if "FINISHED" in result:
            mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
            if mesh_objects:
                logger.info(f"MB-Lab character initialized: {mesh_objects[0].name}")
        else:
            logger.warning(f"init_character returned {result}")
    except (AttributeError, TypeError) as e:
        logger.warning(f"mbast.init_character failed: {e}")

    # Step 2: Auto-model (apply morphs/body proportions)
    try:
        result = bpy.ops.mbast.auto_modelling()
        logger.info(f"MB-Lab auto_modelling: {result}")
    except (AttributeError, TypeError) as e:
        logger.warning(f"auto_modelling failed: {e}")

    # Step 3: Finalize (applies shape keys as expressions)
    try:
        result = bpy.ops.mbast.finalize_character()
        logger.info(f"MB-Lab finalize: {result}")
    except (AttributeError, TypeError) as e:
        logger.warning(f"finalize_character failed: {e}")

    # Verify we have a mesh and armature
    mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
    armature_objects = [o for o in bpy.data.objects if o.type == "ARMATURE"]

    if not mesh_objects:
        raise RuntimeError("MB-Lab failed to create any mesh objects — provide --base path")

    logger.info(f"MB-Lab base generated: mesh={mesh_objects[0].name}, armatures={len(armature_objects)}")


# ──────────────────────────────────────────────────────────────────────────────
# Spec Application
# ──────────────────────────────────────────────────────────────────────────────

def _apply_spec(bpy, spec: dict, forge_config: dict | None = None) -> None:
    """Apply the Hamr CharacterSpec to the current Blender scene.

    Only applies visual/transform properties. VRM mapping and Phase 12
    integration steps are handled separately in main().
    """
    _apply_colors(bpy, spec)
    _apply_height(bpy, spec)

    # Apply forge-resolved parameters (hair, face, clothing)
    if forge_config:
        _apply_face_from_forge(bpy, forge_config)
        _apply_hair_from_forge(bpy, forge_config)
        _apply_clothing_from_forge(bpy, forge_config)


def _classify_material(mat_name: str) -> str | None:
    """Classify a material name into a category."""
    name_lower = mat_name.lower()
    if any(kw in name_lower for kw in SKIN_KEYWORDS):
        return "skin"
    if any(kw in name_lower for kw in EYE_KEYWORDS):
        return "eye"
    if any(kw in name_lower for kw in HAIR_KEYWORDS):
        return "hair"
    if any(kw in name_lower for kw in NAIL_KEYWORDS):
        return "nail"
    if any(kw in name_lower for kw in LIP_KEYWORDS):
        return "lip"
    return None


def _hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color to HSV (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[:2], 16) / 255, int(hex_color[2:4], 16) / 255, int(hex_color[4:], 16) / 255
    return colorsys.rgb_to_hsv(r, g, b)


def _tint_texture(bpy, mat_name: str, target_hsv: tuple, blend: float = 0.6) -> bool:
    """Tint a material's base color texture towards target HSV."""
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        return False

    # Try Principled BSDF
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            base_color = node.inputs.get("Base Color")
            if base_color and base_color.is_linked:
                # Has texture — shift the linked image
                link = base_color.links[0]
                if link.from_node.type == "TEX_IMAGE":
                    # Shift the image pixels
                    return _shift_image_hsv(bpy, link.from_node.image, target_hsv, blend)
            elif base_color:
                # Direct color — blend towards target
                current = list(base_color.default_value)
                h, s, v = target_hsv
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                new_color = [
                    current[0] * (1 - blend) + r * blend,
                    current[1] * (1 - blend) + g * blend,
                    current[2] * (1 - blend) + b * blend,
                    1.0,
                ]
                base_color.default_value = new_color
                return True
    return False


def _shift_image_hsv(bpy, image, target_hsv: tuple, blend: float) -> bool:
    """Shift an image's pixels towards target HSV color."""
    if image is None or not image.pixels:
        return False

    h_target, s_target, v_target = target_hsv
    pixels = list(image.pixels)
    width, height = image.size

    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            r, g, b, a = pixels[i], pixels[i+1], pixels[i+2], pixels[i+3]

            # Skip transparent or very dark pixels
            if a < 0.01 or (r + g + b) < 0.03:
                continue

            h, s, v = colorsys.rgb_to_hsv(r, g, b)

            # Shift hue and saturation, preserve value (brightness)
            h = (h + h_target * blend) / (1 + blend) if blend > 0 else h
            s = s * (1 - blend) + s_target * blend
            v_keep = v  # preserve original brightness

            r_new, g_new, b_new = colorsys.hsv_to_rgb(h % 1.0, min(s, 1.0), v_keep)

            pixels[i] = r_new
            pixels[i+1] = g_new
            pixels[i+2] = b_new
            # Alpha preserved

    image.pixels = pixels
    image.update()
    return True


def _apply_colors(bpy, spec: dict) -> None:
    """Apply skin, eye, hair, nail colors from spec."""
    body = spec.get("body", {})
    skin_spec = body.get("skin", {})
    hair_spec = spec.get("hair", {})
    face_spec = spec.get("face", {})

    # Skin color
    skin_hex = skin_spec.get("base_hex", "#E8B87A")
    skin_hsv = _hex_to_hsv(skin_hex)
    blend = 0.6

    for mat in bpy.data.materials:
        cat = _classify_material(mat.name)
        if cat == "skin":
            if _tint_texture(bpy, mat.name, skin_hsv, blend):
                logger.info(f"Skin tinted: {mat.name}")

    # Eye color
    eyes = face_spec.get("eyes", {})
    if isinstance(eyes, dict):
        iris_hex = eyes.get("iris_hex", "#4169E1")
        iris_hsv = _hex_to_hsv(iris_hex)
        for mat in bpy.data.materials:
            if _classify_material(mat.name) == "eye":
                if _tint_texture(bpy, mat.name, iris_hsv, 0.7):
                    logger.info(f"Eye tinted: {mat.name}")

    # Hair color
    hair_color = hair_spec.get("color", {})
    if isinstance(hair_color, dict):
        roots_hex = hair_color.get("roots", "#C4A265")
        roots_hsv = _hex_to_hsv(roots_hex)
        for mat in bpy.data.materials:
            if _classify_material(mat.name) == "hair":
                if _tint_texture(bpy, mat.name, roots_hsv, 0.6):
                    logger.info(f"Hair tinted: {mat.name}")


def _apply_face_from_forge(bpy, forge_config: dict) -> None:
    """Apply face shape keys from the Face Forge resolution."""
    face_config = forge_config.get("face")
    if not face_config:
        return

    shape_keys = face_config.get("shape_keys", {})
    if not shape_keys:
        return

    applied = 0
    for mesh_obj in bpy.data.objects:
        if mesh_obj.type != "MESH" or not mesh_obj.data.shape_keys:
            continue
        key_blocks = mesh_obj.data.shape_keys.key_blocks
        for sk_name, weight in shape_keys.items():
            if sk_name in key_blocks:
                key_blocks[sk_name].value = float(weight)
                applied += 1

    if applied > 0:
        logger.info(f"Face forge: applied {applied} shape key values")

    # Eye size — scale eye bones
    eye_size = face_config.get("eye_size_factor", 1.0)
    if abs(eye_size - 1.0) > 0.01:
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                for bone in obj.data.bones:
                    if bone.name in ("eye.L", "L_Eye", "Eye_L", "LeftEye",
                                     "eye.R", "R_Eye", "Eye_R", "RightEye"):
                        bone_obj = obj.pose.bones.get(bone.name)
                        if bone_obj:
                            bone_obj.scale = (eye_size, eye_size, eye_size)
                break

    # Lip fullness — set lip shape keys if present
    lip_fullness = face_config.get("lip_fullness", 0.5)
    for mesh_obj in bpy.data.objects:
        if mesh_obj.type != "MESH" or not mesh_obj.data.shape_keys:
            continue
        key_blocks = mesh_obj.data.shape_keys.key_blocks
        for key_name in ("lip_full", "lips_full", "lip_thick"):
            if key_name in key_blocks:
                key_blocks[key_name].value = lip_fullness
                logger.info(f"Lip fullness set: {lip_fullness:.2f}")


def _apply_clothing_from_forge(bpy, forge_config: dict) -> None:
    """Apply clothing material adjustments from the Clothing Forge resolution."""
    clothing_layers = forge_config.get("clothing", [])
    if not clothing_layers:
        return

    applied = 0
    for layer in clothing_layers:
        mesh_pattern = layer.get("mesh_pattern", "")
        mat_category = layer.get("material_category", "fabric")
        mat_props = layer.get("material_properties", {})
        primary_hsv = layer.get("primary_hsv")
        accent_hsv = layer.get("accent_hsv")

        if not mesh_pattern:
            continue

        # Match materials by pattern
        import re
        pattern = re.compile("|".join(mesh_pattern.split("|")), re.IGNORECASE)

        for mat in bpy.data.materials:
            if pattern.search(mat.name):
                # Apply material properties
                if mat.use_nodes and mat.node_tree:
                    for node in mat.node_tree.nodes:
                        if node.type == "BSDF_PRINCIPLED":
                            if "Roughness" in node.inputs:
                                roughness = mat_props.get("roughness", 0.7)
                                node.inputs["Roughness"].default_value = roughness
                            if "Metallic" in node.inputs:
                                metallic = mat_props.get("metallic", 0.0)
                                node.inputs["Metallic"].default_value = metallic

                # Apply primary color tinting
                if primary_hsv and len(primary_hsv) >= 3:
                    hsv_tuple = tuple(primary_hsv[:3])
                    if _tint_texture(bpy, mat.name, hsv_tuple, 0.5):
                        applied += 1

    if applied > 0:
        logger.info(f"Clothing forge: tinted {applied} materials")


def _apply_hair_from_forge(bpy, forge_config: dict) -> None:
    """Apply hair parameters from the Hair Forge resolution."""
    hair_config = forge_config.get("hair")
    if not hair_config:
        return

    style_template = hair_config.get("style_template", {})
    curl = hair_config.get("curl_tightness", 0.0)
    volume = hair_config.get("volume", 0.7)
    physics = hair_config.get("physics_config", {})

    # Apply curl tightness and volume to shape keys
    applied = 0
    for mesh_obj in bpy.data.objects:
        if mesh_obj.type != "MESH" or not mesh_obj.data.shape_keys:
            continue
        key_blocks = mesh_obj.data.shape_keys.key_blocks
        if any(kw in mesh_obj.name.lower() for kw in ("hair", "strand")):
            # Curl keys
            for key_name in ("curl", "curl_tight", "Curl", "Curly"):
                if key_name in key_blocks:
                    key_blocks[key_name].value = curl
                    applied += 1
            # Volume keys
            for key_name in ("volume", "hair_volume", "Volume", "Fullness"):
                if key_name in key_blocks:
                    key_blocks[key_name].value = volume
                    applied += 1

    if applied > 0:
        logger.info(f"Hair forge: applied {applied} shape key values")


def _apply_height(bpy, spec: dict) -> None:
    """Apply height scaling to the armature."""
    body = spec.get("body", {})
    target_height = body.get("height_cm", 170)
    # Standard MB-Lab/TurboSquid height ~165cm
    reference_height = 165.0
    scale = target_height / reference_height

    if abs(scale - 1.0) > 0.001:
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                obj.scale[2] *= scale
                logger.info(f"Height scale {scale:.3f}x applied to {obj.name}")
                break


def _apply_vrm_humanoid(bpy, spec: dict, stub_result=None) -> None:
    """Configure VRM 1.0 humanoid bone mapping. D-008, D-009, D-017, D-018.
    
    If stub_result is provided (from Phase 12 _integrate_stub_bones),
    the stub bone map is merged into the active bone map so that
    newly created stub bones are included in VRM mapping.
    """
    armature = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if armature is None:
        logger.warning("No armature found for VRM mapping")
        return

    vrm_ext = armature.vrm_addon_extension
    # Compatibility fix for VRM addon API changes (vrm1 vs direct attributes)
    if hasattr(vrm_ext, 'vrm1'):
        humanoid = vrm_ext.vrm1.humanoid
        human_bones = humanoid.human_bones
    elif hasattr(vrm_ext, 'humanoid'):
        human_bones = vrm_ext.humanoid.human_bones
    else:
        logger.warning("VRM addon extension not available or unknown structure. Available attrs: {}".format(dir(vrm_ext)))
        return

    # D-008: NEVER auto-map bones
    human_bones.initial_automatic_bone_assignment = False
    # D-009: Allow non-standard hierarchy
    human_bones.filter_by_human_bone_hierarchy = False

    # Select bone map based on base mesh type
    bone_map = MB_LAB_BONE_MAP  # Default
    base_type = spec.get("base_type", "mblab")
    if base_type == "turbosquid":
        bone_map = TURBOSQUID_BONE_MAP

    # Allow spec overrides
    spec_bones = spec.get("bones", {})
    if spec_bones:
        bone_map = {**bone_map, **spec_bones}

    # Phase 12: Merge stub bone map for newly-created bones (jaw, eyes)
    if stub_result is not None and hasattr(stub_result, "created_bones") and stub_result.created_bones:
        from hamr.rigs.stub_bones import get_stub_bone_map
        stub_map = get_stub_bone_map()
        bone_map.update(stub_map)
        logger.info(f"Merged {len(stub_map)} stub bone entries into VRM bone map")

    # D-018: Use canonical API
    bone_names_in_armature = set(b.name for b in armature.data.bones)
    human_bone_dict = human_bones.human_bone_name_to_human_bone()
    vrm_name_to_prop = {name.value: prop for name, prop in human_bone_dict.items()}

    mapped = 0
    for vrm_name, target in bone_map.items():
        bone_prop = vrm_name_to_prop.get(vrm_name)
        if bone_prop and target in bone_names_in_armature:
            bone_prop.node.bone_name = target
            mapped += 1

    logger.info(f"VRM bone mapping: {mapped}/{len(bone_map)} bones mapped")

    # Fixup
    try:
        from io_scene_vrm.editor.vrm1.property_group import Vrm1HumanBonesPropertyGroup
        Vrm1HumanBonesPropertyGroup.fixup_human_bones(armature)
    except (ImportError, AttributeError, Exception):
        pass


def _apply_vrm_metadata(bpy, spec: dict) -> None:
    """Set VRM 1.0 metadata."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and hasattr(obj, "vrm_addon_extension"):
            vrm_ext = obj.vrm_addon_extension
            if hasattr(vrm_ext, "vrm1"):
                meta = vrm_ext.vrm1.meta
            else:
                logger.warning("VRM addon vrm1 not available for metadata")
                break

            meta.name = spec.get("name", "Hamr Character")
            meta.title = spec.get("name", "Hamr Character")
            meta.version = spec.get("version", "1.0")

            meta.authors.add()
            meta.authors[0].name = spec.get("author", "Hamr Forge")

            meta.license_type = "CC_BY_4_0"
            meta.allow_excessive_violence = False
            meta.allow_excessive_sexual_usage = True
            meta.allow_political_usage = False
            meta.allow_religious_usage = True

            logger.info(f"VRM metadata set: {meta.name} by {meta.authors[0].name}")
            break


def _apply_vrm_expressions(bpy, spec: dict) -> None:
    """Configure VRM 1.0 expressions. D-011, D-013."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and hasattr(obj, "vrm_addon_extension"):
            vrm_ext = obj.vrm_addon_extension

            # Discover shape keys
            shape_key_index = {}  # shape_key_name → mesh_name
            for mesh_obj in bpy.data.objects:
                if mesh_obj.type == "MESH" and mesh_obj.data.shape_keys:
                    for kb in mesh_obj.data.shape_keys.key_blocks:
                        shape_key_index[kb.name] = mesh_obj.name

            # Select expression map
            expr_map = MB_LAB_EXPRESSION_MAP
            base_type = spec.get("base_type", "mblab")
            if base_type == "turbosquid":
                from hamr.scripts.build_avatar import TURBOSQUID_EXPRESSION_MAP
                expr_map = TURBOSQUID_EXPRESSION_MAP

            # Allow spec overrides
            spec_expr = spec.get("expression_map", {})
            if spec_expr:
                expr_map = {**expr_map, **spec_expr}

            # Compatibility for VRM addon versions
            if hasattr(vrm_ext, 'vrm1'):
                vrm1 = vrm_ext.vrm1
            elif hasattr(vrm_ext, 'expressions'):
                vrm1 = vrm_ext
            else:
                logger.warning("Could not locate VRM expressions property group")
                break

            preset = vrm1.expressions.preset
            vrm1.expressions.initial_automatic_expression_assignment = False

            mapped = 0
            for preset_name, bindings in expr_map.items():
                preset_expr = getattr(preset, preset_name, None)
                if preset_expr is None:
                    continue

                for binding in bindings:
                    sk_name = binding.get("shape_key", binding.get("name", ""))
                    weight = float(binding.get("weight", 1.0))
                    mesh_name = binding.get("mesh", shape_key_index.get(sk_name))

                    if not sk_name or not mesh_name:
                        continue

                    bind = preset_expr.morph_target_binds.add()
                    bind.node.mesh_object_name = mesh_name
                    bind.index = sk_name  # D-013: shape key NAME, not number
                    bind.weight = weight
                    mapped += 1

            logger.info(f"VRM expressions: {mapped} bindings configured")
            break


def _apply_vrm_look_at(bpy, spec: dict) -> None:
    """Configure VRM 1.0 lookAt. MB-Lab has no eye bones → use expressionOnly."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and hasattr(obj, "vrm_addon_extension"):
            vrm_ext = obj.vrm_addon_extension
            look_at = vrm_ext.vrm1.look_at

            # Check for eye bones — MB-Lab rigs lack them, so use expressionOnly
            has_eye_bones = any(
                bone.name in ("eye.L", "L_Eye", "Eye_L", "LeftEye",
                              "eye.R", "R_Eye", "Eye_R", "RightEye")
                for bone in obj.data.bones
            )

            if has_eye_bones:
                # D-012: bone rotation mode when eye bones exist
                look_at.type = "bone"

                left_eye_pos = right_eye_pos = None
                for bone in obj.data.bones:
                    if bone.name in ("eye.L", "L_Eye", "Eye_L", "LeftEye"):
                        left_eye_pos = bone.head_local
                    elif bone.name in ("eye.R", "R_Eye", "Eye_R", "RightEye"):
                        right_eye_pos = bone.head_local

                if left_eye_pos and right_eye_pos:
                    center = (left_eye_pos + right_eye_pos) / 2
                    look_at.offset_from_head_bone = (
                        center[0],
                        center[1] - left_eye_pos[1],
                        center[2] - 0.06,
                    )
                else:
                    look_at.offset_from_head_bone = (0.0, 0.0, 0.06)

                logger.info("VRM lookAt configured: bone mode")

            else:
                # No eye bones → expressionOnly mode (VRM 1.0 spec)
                look_at.type = "expression"
                logger.info("VRM lookAt configured: expression mode (no eye bones)")

            # Range configuration
            look_config = spec.get("look_at", {})
            look_at.horizontal_inner = float(look_config.get("horizontal_inner_degrees", 15.0))
            look_at.horizontal_outer = float(look_config.get("horizontal_outer_degrees", 15.0))
            look_at.vertical_down = float(look_config.get("vertical_down_degrees", 10.0))
            look_at.vertical_up = float(look_config.get("vertical_up_degrees", 10.0))
            break


# ──────────────────────────────────────────────────────────────────────────────
# Post-Export Validation
# ──────────────────────────────────────────────────────────────────────────────

def _validate_vrm(output_path: str) -> None:
    """Validate exported VRM file for basic correctness."""
    path = Path(output_path)
    if not path.exists():
        raise ValueError(f"VRM file not found: {output_path}")
    if path.stat().st_size < 1024:
        raise ValueError(f"VRM file suspiciously small: {path.stat().st_size} bytes")

    with open(output_path, "rb") as f:
        header = f.read(20)
        if len(header) < 20:
            raise ValueError("VRM file too short for glTF header")

        magic = struct.unpack("<I", header[0:4])[0]
        if magic != 0x46546C67:
            raise ValueError(f"Not a valid glTF file: magic=0x{magic:08X}")

    size_mb = path.stat().st_size / (1024 * 1024)
    logger.info(f"VRM validation passed — {size_mb:.1f} MB")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 12 Integration Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def _find_armature(bpy) -> str:
    """Find the armature object in the current Blender scene.

    Returns the name of the first ARMATURE object, or empty string.
    """
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj.name
    return ""


def _find_body_mesh(bpy) -> str:
    """Find the main body mesh (first non-hair, non-clothing mesh).

    Returns the name of the first MESH object, or empty string.
    """
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            name_lower = obj.name.lower()
            # Skip hair and clothing meshes — we want the body
            if "hair" not in name_lower and "cloth" not in name_lower:
                return obj.name
    # Fallback: return any mesh
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            return obj.name
    return ""


def _integrate_stub_bones(bpy, armature_name: str):
    """Step 3a: Create stub bones for missing VRM 1.0 humanoid bones.

    Creates micro-stub bones (jaw, leftEye, rightEye) that MB-Lab
    rigs lack, positioning them correctly relative to the head bone.
    """
    from hamr.rigs.stub_bones import create_missing_bones

    result = create_missing_bones(armature_name, base_type="mblab")
    if result.created_bones:
        logger.info(f"Stub bones created: {list(result.created_bones.keys())}")
    else:
        logger.info("All VRM bones already present — no stubs needed")
    return result


def _integrate_hair_mesh(bpy, spec_data: dict, forge_config, armature_name: str):
    """Step 3b: Generate procedural hair mesh from spec.

    Uses HairMeshGenerator to create hair geometry, materials, and
    bone chains for spring physics.
    """
    from hamr.hair.mesh import HairMeshGenerator

    hair_spec = spec_data.get("hair") if isinstance(spec_data, dict) else None
    if not hair_spec:
        # Try forge_config
        if forge_config and isinstance(forge_config, dict):
            hair_spec = forge_config.get("hair")
        if not hair_spec:
            return None

    hair_style = (
        hair_spec.get("style", hair_spec.get("length", "long_straight"))
        if isinstance(hair_spec, dict)
        else "long_straight"
    )
    if hair_style == "none":
        return None

    # Determine head position from armature
    head_pos = (0.0, 0.0, 1.65)
    head_radius = 0.10
    if armature_name:
        armature = bpy.data.objects.get(armature_name)
        if armature and hasattr(armature, "data") and armature.data:
            head_bone = armature.data.bones.get("head")
            if head_bone:
                head_pos = tuple(armature.matrix_world @ head_bone.head_local)
                head_radius = 0.10

    # Build color config from hair spec
    color_config = None
    hair_color = hair_spec.get("color") if isinstance(hair_spec, dict) else None
    if hair_color and isinstance(hair_color, dict):
        roots_hex = hair_color.get("roots", "#C4A265")
        tips_hex = hair_color.get("tips", "#F5E6B8")
        color_config = {
            "roots_hsv": _hex_to_hsv(roots_hex),
            "tips_hsv": _hex_to_hsv(tips_hex),
        }

    gen = HairMeshGenerator()
    result = gen.generate(
        style_name=hair_style,
        head_center=head_pos,
        head_radius=head_radius,
        color_config=color_config,
    )
    logger.info(
        f"Hair mesh: {result.object_name}, "
        f"{result.vertex_count} verts, {result.triangle_count} tris"
    )
    return result


def _integrate_clothing_meshes(bpy, spec_data: dict, forge_config, armature_name: str):
    """Step 3c: Generate procedural clothing meshes from spec.

    Iterates over clothing spec items, generating each one via
    ClothingMeshGenerator with shrinkwrap and weight transfer.
    """
    from hamr.clothing.mesh import ClothingMeshGenerator
    from hamr.core.models import ClothingSpec

    clothing_specs = (
        spec_data.get("clothing", []) if isinstance(spec_data, dict) else []
    )

    # Also check forge_config for clothing
    if not clothing_specs and forge_config and isinstance(forge_config, dict):
        clothing_specs = forge_config.get("clothing", [])

    if not clothing_specs:
        return []

    body_mesh_name = _find_body_mesh(bpy)
    if not body_mesh_name:
        logger.warning("No body mesh found for clothing shrinkwrap")
        return []

    gen = ClothingMeshGenerator()
    results = []

    for i, cloth_spec in enumerate(clothing_specs):
        try:
            cloth_obj = _dict_to_clothing_spec(cloth_spec, index=i)
            result = gen.generate(
                spec=cloth_obj,
                body_mesh_name=body_mesh_name,
                armature_name=armature_name,
            )
            results.append(result)
            logger.info(
                f"Clothing mesh {i}: {result.mesh_name}, "
                f"{result.triangle_count} tris"
            )
        except Exception as exc:
            logger.warning(f"Clothing mesh {i} failed: {exc}")

    return results


def _integrate_weight_paint(bpy, armature_name: str, hair_result, clothing_results: list):
    """Step 3d: Apply weight painting to all generated meshes.

    Smooths body mesh weights, transfers to clothing meshes,
    and normalizes hair mesh weights.
    """
    from hamr.rigs.weights import WeightPaintEngine

    engine = WeightPaintEngine()

    # Smooth weights on body mesh
    body_mesh_name = _find_body_mesh(bpy)
    if body_mesh_name:
        engine.paint_smooth(
            armature_name=armature_name,
            mesh_name=body_mesh_name,
            influence_radius=0.3,
            iterations=3,
        )
        engine.normalize_weights(armature_name, body_mesh_name)

    # Transfer weights from body to clothing
    for cloth_result in (clothing_results or []):
        if hasattr(cloth_result, "mesh_name") and body_mesh_name:
            try:
                engine.transfer_weights(
                    source_mesh=body_mesh_name,
                    target_mesh=cloth_result.mesh_name,
                )
                engine.normalize_weights(armature_name, cloth_result.mesh_name)
            except Exception as exc:
                logger.warning(f"Weight transfer to {cloth_result.mesh_name} failed: {exc}")

    # Normalize hair mesh weights
    if hair_result and hasattr(hair_result, "object_name") and hair_result.object_name:
        try:
            engine.normalize_weights(armature_name, hair_result.object_name)
        except Exception as exc:
            logger.warning(f"Hair weight normalization failed: {exc}")


def _integrate_spring_bones(bpy, armature_name: str, spec_data: dict,
                              forge_config, hair_result, clothing_results: list):
    """Step 3e: Configure VRM 1.0 spring bones for dynamic secondary motion.

    Sets up hair spring, breast spring, and clothing spring groups
    with appropriate collider spheres.
    """
    from hamr.rigs.spring_bones import (
        configure_hair_spring,
        configure_breast_spring,
        configure_clothing_spring,
        apply_spring_bones,
        SpringBoneCollider,
    )

    # Build collider list from defaults (convert dicts to SpringBoneCollider objects)
    default_colliders = [
        {"name": "head_collider", "bone": "head", "offset": (0.0, 0.0, 0.0), "radius": 0.08},
        {"name": "upper_body_collider", "bone": "upperChest", "offset": (0.0, 0.0, 0.0), "radius": 0.12},
        {"name": "lower_body_collider", "bone": "spine", "offset": (0.0, 0.0, 0.0), "radius": 0.1},
        {"name": "left_shoulder_collider", "bone": "clavicle_L", "offset": (0.0, 0.0, 0.0), "radius": 0.05},
        {"name": "right_shoulder_collider", "bone": "clavicle_R", "offset": (0.0, 0.0, 0.0), "radius": 0.05},
    ]
    colliders = [
        SpringBoneCollider(
            name=c["name"],
            bone=c["bone"],
            offset=c["offset"],
            radius=c["radius"],
        )
        for c in default_colliders
    ]

    spring_groups = []

    # Hair spring bones
    physics_spec = None
    hair_spec = spec_data.get("hair") if isinstance(spec_data, dict) else None
    if hair_spec and isinstance(hair_spec, dict):
        hair_phys = hair_spec.get("physics") or hair_spec.get("hair_physics")
        if hair_phys and isinstance(hair_phys, dict):
            try:
                from hamr.core.models import HairPhysicsSpec
                physics_spec = HairPhysicsSpec(**hair_phys)
            except Exception:
                physics_spec = None

    hair_spring = configure_hair_spring(physics_spec)

    # Attach bone chains from hair mesh if available
    if hair_result and hasattr(hair_result, "bone_chain") and hair_result.bone_chain:
        hair_spring.bone_chains = [hair_result.bone_chain]

    spring_groups.append(hair_spring)

    # Breast spring bones
    body_spec = spec_data.get("body", {}) if isinstance(spec_data, dict) else {}
    breast_spring = configure_breast_spring(body_spec)
    spring_groups.append(breast_spring)

    # Clothing spring bones
    for cloth_result in (clothing_results or []):
        if hasattr(cloth_result, "mesh_name") and cloth_result.mesh_name:
            cloth_type = "skirt"  # default
            cloth_spring = configure_clothing_spring(
                clothing_name=cloth_result.mesh_name,
                cloth_type=cloth_type,
            )
            spring_groups.append(cloth_spring)

    result = apply_spring_bones(
        armature_name=armature_name,
        spring_groups=spring_groups,
        colliders=colliders,
    )
    logger.info(
        f"Spring bones applied: "
        f"{len(result.get('spring_groups', []))} groups, "
        f"{len(result.get('colliders', []))} colliders"
    )


def _integrate_first_person(bpy, armature_name: str, hair_result, clothing_results: list):
    """Step 3f: Configure VRM 1.0 first-person view annotations.

    Classifies all meshes as thirdPersonOnly, both, or firstPersonOnly
    for correct VR first-person rendering.
    """
    from hamr.export.first_person import configure_first_person

    # Collect all mesh names in the scene
    all_mesh_names = [
        obj.name for obj in bpy.data.objects if obj.type == "MESH"
    ]

    config = configure_first_person(
        armature_name=armature_name,
        mesh_names=all_mesh_names,
    )
    logger.info(
        f"First-person annotations: {len(config.mesh_annotations)} meshes, "
        f"bone={config.first_person_bone}"
    )


def _dict_to_clothing_spec(cloth_spec, index: int = 0):
    """Convert a clothing spec dict into a ClothingSpec dataclass.

    If the spec is already a ClothingSpec, return it as-is.
    """
    from hamr.core.models import ClothingSpec

    if isinstance(cloth_spec, ClothingSpec):
        return cloth_spec
    if isinstance(cloth_spec, dict):
        name = cloth_spec.get("name", f"clothing_{index}")
        cloth_type = cloth_spec.get("type", "tshirt")
        return ClothingSpec(
            name=name,
            type=cloth_type,
            primary_hex=cloth_spec.get("primary_hex", "#1A1A2E"),
            accent_hex=cloth_spec.get("accent_hex", "#FFFFFF"),
            trim_hex=cloth_spec.get("trim_hex", "#FFD700"),
        )
    return cloth_spec


if __name__ == "__main__":
    sys.exit(main())