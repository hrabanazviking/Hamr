"""
Body Forge — Parametric body generation from any base mesh.

The forge takes a CharacterSpec and produces a body. It starts
with a base mesh (MB-Lab by default), applies shape keys and
proportions, and returns the result for further processing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from hamr.core.models import CharacterSpec, BodySpec
from hamr.core.constants import BODY_PRESETS

logger = logging.getLogger("hamr.body")


class BodyForge:
    """
    Generate parametric bodies from a spec.

    The forge works with any base mesh that provides shape keys.
    MB-Lab is the default, but any compatible mesh works.
    """

    def __init__(self, base_mesh_path: Path | None = None) -> None:
        self.base_mesh_path = base_mesh_path
        self._armature = None
        self._body_mesh = None

    def forge(self, spec: CharacterSpec) -> dict[str, Any]:
        """
        Forge a body from a spec.

        Returns a dict with:
            armature: Blender armature object
            body_mesh: Blender mesh object
            materials: list of Blender materials
            spec: the CharacterSpec used
        """
        from hamr.blender_bridge.scene import new_scene, set_scene_defaults

        logger.info(f"Forging body: {spec.name} (build: {spec.body.build})")

        # Set up clean scene
        new_scene(f"Hamr_{spec.name.replace(' ', '_')}")
        set_scene_defaults()

        # Resolve preset proportions
        body = self._resolve_body(spec.body)

        # Import base mesh
        self._import_base_mesh()

        # Apply body proportions
        self._apply_proportions(body)

        # Apply skin texture
        self._apply_skin(body.skin)

        # Scale to target height
        self._scale_height(body.height_cm)

        result = {
            "armature": self._armature,
            "body_mesh": self._body_mesh,
            "materials": [],
            "spec": spec,
        }

        logger.info(f"Body forged: {spec.name}")
        return result

    def _resolve_body(self, body_spec: BodySpec) -> BodySpec:
        """Resolve body preset into explicit proportions."""
        if body_spec.build in BODY_PRESETS:
            preset = BODY_PRESETS[body_spec.build]
            # Merge preset with explicit overrides
            merged = BodySpec(
                height_cm=body_spec.height_cm,
                build=body_spec.build,
                skin=body_spec.skin,
                proportions={**preset, **body_spec.proportions},
            )
            logger.debug(f"Resolved body preset '{body_spec.build}' → {merged.proportions}")
            return merged
        return body_spec

    def _import_base_mesh(self) -> None:
        """Import the base mesh into the scene."""
        # This will be implemented per base mesh type
        # MB-Lab uses bpy.ops.mb.lab_generate_human()
        # FBX/OBJ uses bpy.ops.import_scene.fbx/obj
        logger.info(f"Base mesh import not yet implemented (path: {self.base_mesh_path})")

    def _apply_proportions(self, body: BodySpec) -> None:
        """Apply body proportion sliders via shape keys."""
        # Shape key application depends on the base mesh
        # MB-Lab provides morph targets that map to proportion sliders
        logger.info(f"Applying proportions: {body.proportions}")

        if self._body_mesh and hasattr(self._body_mesh, 'data') and self._body_mesh.data.shape_keys:
            for key_name, value in body.proportions.items():
                # Try to find matching shape key
                key_block = self._body_mesh.data.shape_keys.key_blocks.get(key_name)
                if key_block:
                    key_block.value = max(0.0, min(1.0, value))
                    logger.debug(f"  Shape key '{key_name}' = {value:.3f}")
                else:
                    logger.warning(f"  Shape key '{key_name}' not found")

    def _apply_skin(self, skin_spec: Any) -> None:
        """Apply skin color to body materials."""
        from hamr.core.textures import generate_skin_texture, tint_texture

        logger.info(f"Applying skin: {skin_spec.base_hex} ({skin_spec.undertone} undertone)")

        # Generate procedural skin texture
        skin_tex = generate_skin_texture(skin_spec)

        # If we have an existing skin texture, tint it
        if self._body_mesh and hasattr(self._body_mesh, 'material_slots'):
            for slot in self._body_mesh.material_slots:
                if slot.material:
                    skin_tex = tint_texture(skin_tex, skin_spec.base_hex)

    def _scale_height(self, height_cm: float) -> None:
        """Scale the armature to target height in cm."""
        if self._armature:
            from hamr.blender_bridge.mesh_ops import scale_armature
            scale_armature(self._armature, height_cm)
        else:
            logger.warning("No armature to scale")