"""
Facial Expression Blend Shape Binding — VRM 1.0 Expressions & MB-Lab Shape Keys.

Binds MB-Lab / TurboSquid shape keys to VRM 1.0 expression blend shapes.
VRM 1.0 requires: happy, angry, sad, surprised, neutral, blink, blinkLeft, blinkRight.

The ExpressionBinder is pure-Python (no bpy dependency). The apply_expression_bindings()
function requires Blender and is guarded accordingly.

Phase 12, Task T5 — The Forge Worker speaks: the face learns its expressions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("hamr.face.expressions")


# ═══════════════════════════════════════════════════════════════════════════════
# VRM 1.0 Expression Definitions
# ═══════════════════════════════════════════════════════════════════════════════

# VRM 1.0 required expressions mapped to common shape key name aliases.
# Each VRM expression maps to a list of shape key names that commonly
# represent that expression. The ExpressionBinder uses these aliases
# to find matching shape keys in an MB-Lab or TurboSquid mesh.
VRM_EXPRESSIONS: dict[str, list[str]] = {
    "happy": ["smile", "happy", "mouth_smile", "grin"],
    "angry": ["angry", "frown", "brow_frown"],
    "sad": ["sad", "frown_sad", "mouth_sad"],
    "surprised": ["surprised", "mouth_open", "brow_surprised"],
    "neutral": ["neutral", "rest"],
    "blink": ["blink", "eye_blink", "wink"],
    "blinkLeft": ["blink_l", "eye_blink_l", "wink_l"],
    "blinkRight": ["blink_r", "eye_blink_r", "wink_r"],
}

# Number of required VRM 1.0 expressions
VRM_EXPRESSION_COUNT = len(VRM_EXPRESSIONS)


# ═══════════════════════════════════════════════════════════════════════════════
# MB-Lab Shape Key Aliases
# ═══════════════════════════════════════════════════════════════════════════════

# Maps MB-Lab and TurboSquid shape key names to canonical VRM expression names.
# MB-Lab prefixes shape keys with 'Expressions_' and uses camelCase with
# _L/_R suffixes for left/right sides and _min/_max for range.
# TurboSquid uses PascalCase names like 'Smile', 'Blink_L'.
SHAPE_KEY_ALIASES: dict[str, str] = {
    # --- Happy / Smile ---
    "Expressions_mouthSmile_max": "happy",
    "Expressions_mouthSmile_min": "sad",
    # --- Angry / Brow ---
    "Expressions_browSqueezeL_max": "angry",
    "Expressions_browSqueezeR_max": "angry",
    "Expressions_browSqueezeL_min": "happy",
    "Expressions_browSqueezeR_min": "happy",
    # --- Surprised / Eyes Vert ---
    "Expressions_eyesVert_max": "surprised",
    "Expressions_eyesVert_min": "sad",
    # --- Mouth Open ---
    "Expressions_mouthOpen_max": "surprised",
    "Expressions_mouthOpenAggr_max": "angry",
    # --- Mouth Horizontal ---
    "Expressions_mouthHoriz_max": "happy",
    # --- Mouth O ---
    "Expressions_mouthOpenO_max": "surprised",
    # --- Blink (both eyes closed) ---
    "Expressions_eyeClosedL_max": "blinkLeft",
    "Expressions_eyeClosedR_max": "blinkRight",
    "Expressions_eyeClosedL_min": "blinkLeft",
    "Expressions_eyeClosedR_min": "blinkRight",
    # --- TurboSquid aliases ---
    "Smile": "happy",
    "Blink_L": "blinkLeft",
    "Blink_R": "blinkRight",
    "EyeSquint_L": "happy",
    "EyeSquint_R": "happy",
    "BrowFurrow_L": "angry",
    "BrowFurrow_R": "angry",
    "Frown_L": "sad",
    "Frown_R": "sad",
    "BrowSad_L": "sad",
    "BrowSad_R": "sad",
    "EyeWide_L": "surprised",
    "EyeWide_R": "surprised",
    "JawOpen": "surprised",
    "MouthWide": "happy",
    "MouthPucker": "surprised",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ExpressionBinding:
    """A binding between a VRM expression and one or more shape keys.

    Attributes:
        expression_name: The VRM 1.0 expression name (e.g. 'happy', 'blink').
        shape_keys: List of (shape_key_name, weight) pairs to activate.
        is_complete: True if at least one shape key was found.
        confidence: 0.0–1.0 rating of binding quality.
            More matches = higher confidence. A single exact match = 0.5.
            Two or more matches = monotonically increasing up to 1.0.
    """

    expression_name: str
    shape_keys: list[tuple[str, float]] = field(default_factory=list)
    is_complete: bool = False
    confidence: float = 0.0

    def __post_init__(self):
        """Derive is_complete and confidence from shape_keys if not explicitly set."""
        if self.shape_keys:
            self.is_complete = True
            # More shape keys = higher confidence
            # 1 key → 0.5, 2+ keys → monotonically increasing up to 1.0
            n = len(self.shape_keys)
            if n == 1:
                self.confidence = max(self.confidence, 0.5)
            else:
                self.confidence = max(self.confidence, min(1.0, 0.5 + 0.25 * (n - 1)))


@dataclass
class ExpressionSet:
    """Complete set of VRM 1.0 expression bindings.

    Each field corresponds to a VRM 1.0 required expression.
    None means no binding was found for that expression.
    """

    happy: Optional[ExpressionBinding] = None
    angry: Optional[ExpressionBinding] = None
    sad: Optional[ExpressionBinding] = None
    surprised: Optional[ExpressionBinding] = None
    neutral: Optional[ExpressionBinding] = None
    blink: Optional[ExpressionBinding] = None
    blink_left: Optional[ExpressionBinding] = None
    blink_right: Optional[ExpressionBinding] = None

    def completion_count(self) -> int:
        """Count how many expressions have bindings (is_complete=True)."""
        count = 0
        for name in ("happy", "angry", "sad", "surprised", "neutral", "blink",
                      "blink_left", "blink_right"):
            binding = getattr(self, name)
            if binding is not None and binding.is_complete:
                count += 1
        return count

    def is_vrm_complete(self) -> bool:
        """Check if all 8 VRM 1.0 required expressions have bindings."""
        return self.completion_count() == VRM_EXPRESSION_COUNT


# ═══════════════════════════════════════════════════════════════════════════════
# ExpressionBinder — Pure-Python (No bpy dependency)
# ═══════════════════════════════════════════════════════════════════════════════


class ExpressionBinder:
    """Bind VRM 1.0 expressions to available mesh shape keys.

    This class is pure-Python — no bpy dependency in the constructor or
    any method except apply_expression_bindings() (which is module-level).

    Usage:
        binder = ExpressionBinder()
        available = ["Expressions_mouthSmile_max", "Expressions_eyeClosedL_max", ...]
        bindings = binder.resolve_expression_bindings(available)
        warnings = binder.validate_bindings(bindings)
    """

    def __init__(self):
        """Initialize the ExpressionBinder. No bpy dependency."""
        pass

    def bind_expression(
        self,
        expression_name: str,
        shape_key_weights: dict[str, float],
    ) -> ExpressionBinding:
        """Create a binding between a VRM expression and shape keys with weights.

        Args:
            expression_name: VRM 1.0 expression name (e.g. 'happy').
            shape_key_weights: Mapping of shape_key_name → weight.

        Returns:
            ExpressionBinding with the shape_keys populated and confidence set.
        """
        if not shape_key_weights:
            return ExpressionBinding(
                expression_name=expression_name,
                shape_keys=[],
                is_complete=False,
                confidence=0.0,
            )

        pairs = [(name, weight) for name, weight in shape_key_weights.items()]
        binding = ExpressionBinding(
            expression_name=expression_name,
            shape_keys=pairs,
        )
        return binding

    def find_matching_shape_keys(
        self,
        expression_name: str,
        available_keys: list[str],
    ) -> list[tuple[str, float]]:
        """Find matching shape keys for a VRM expression name.

        Searches in order:
        1. Direct alias lookup in SHAPE_KEY_ALIASES
        2. VRM_EXPRESSIONS pattern matching (case-insensitive substring)
        3. Fuzzy matching on expression name itself

        Args:
            expression_name: VRM 1.0 expression name.
            available_keys: List of shape key names on the mesh.

        Returns:
            List of (shape_key_name, default_weight) pairs.
            default_weight is 1.0 for primary matches, 0.5 for secondary.
        """
        matches: list[tuple[str, float]] = []
        seen: set[str] = set()
        available_lower = {k.lower(): k for k in available_keys}

        # Strategy 1: Direct alias lookup (MB-Lab / TurboSquid known names)
        for key in available_keys:
            if key in SHAPE_KEY_ALIASES:
                if SHAPE_KEY_ALIASES[key] == expression_name:
                    if key not in seen:
                        matches.append((key, 1.0))
                        seen.add(key)

        # Strategy 2: VRM_EXPRESSIONS pattern matching
        patterns = VRM_EXPRESSIONS.get(expression_name, [])
        for pattern in patterns:
            pattern_lower = pattern.lower()
            # Exact lowercase match
            for lower_key, orig_key in available_lower.items():
                if lower_key == pattern_lower and orig_key not in seen:
                    matches.append((orig_key, 1.0))
                    seen.add(orig_key)
            # Substring match (pattern found within key name)
            for lower_key, orig_key in available_lower.items():
                if pattern_lower in lower_key and orig_key not in seen:
                    matches.append((orig_key, 0.5))
                    seen.add(orig_key)

        # Strategy 3: Expression name itself as substring (case-insensitive)
        expr_lower = expression_name.lower()
        for lower_key, orig_key in available_lower.items():
            if expr_lower in lower_key and orig_key not in seen:
                matches.append((orig_key, 0.3))
                seen.add(orig_key)

        return matches

    def resolve_expression_bindings(
        self,
        available_shape_keys: list[str],
        expression_names: Optional[list[str]] = None,
    ) -> dict[str, ExpressionBinding]:
        """Resolve ALL expressions against available shape keys.

        Args:
            available_shape_keys: List of shape key names on the mesh.
            expression_names: Optional list of expression names to resolve.
                Defaults to all VRM_EXPRESSIONS keys.

        Returns:
            Dict mapping expression_name → ExpressionBinding.
        """
        if expression_names is None:
            expression_names = list(VRM_EXPRESSIONS.keys())

        bindings: dict[str, ExpressionBinding] = {}
        for expr_name in expression_names:
            matches = self.find_matching_shape_keys(expr_name, available_shape_keys)
            if matches:
                shape_key_weights = {name: weight for name, weight in matches}
                bindings[expr_name] = self.bind_expression(expr_name, shape_key_weights)
            else:
                bindings[expr_name] = ExpressionBinding(
                    expression_name=expr_name,
                    shape_keys=[],
                    is_complete=False,
                    confidence=0.0,
                )

        return bindings

    def validate_bindings(
        self, bindings: dict[str, ExpressionBinding]
    ) -> list[str]:
        """Return warnings for expressions with no bound shape keys.

        Args:
            bindings: Dict of expression_name → ExpressionBinding.

        Returns:
            List of warning strings. Empty if all expressions are bound.
        """
        warnings: list[str] = []
        for expr_name, binding in bindings.items():
            if not binding.is_complete:
                warnings.append(
                    f"Expression '{expr_name}' has no bound shape keys — "
                    f"the avatar will lack this expression in VRM."
                )
        return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# Blender-Dependent: Apply Expression Bindings to Armature
# ═══════════════════════════════════════════════════════════════════════════════


def apply_expression_bindings(
    armature_name: str,
    bindings: dict[str, ExpressionBinding],
) -> list[str]:
    """Apply VRM expression blend shape groups to an armature's mesh objects.

    This function requires Blender (bpy) and must run inside a Blender
    Python environment. It creates VRM expression morph bindings on each
    mesh object parented to the armature.

    Args:
        armature_name: Name of the armature object in the Blender scene.
        bindings: Dict mapping VRM expression name → ExpressionBinding.

    Returns:
        List of status messages (one per expression applied).

    Raises:
        RuntimeError: If bpy is not available (not running inside Blender).
    """
    try:
        import bpy  # noqa: F811
    except ImportError:
        raise RuntimeError(
            "apply_expression_bindings requires bpy (Blender Python). "
            "This function must run inside a Blender Python environment."
        )

    messages: list[str] = []

    # Find the armature
    armature = bpy.data.objects.get(armature_name)
    if armature is None:
        messages.append(f"⚠ Armature '{armature_name}' not found — skipping expressions.")
        return messages

    # Find mesh objects parented to this armature
    mesh_objects = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.parent == armature:
            mesh_objects.append(obj)

    if not mesh_objects:
        # Fallback: find any mesh objects in the scene
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                mesh_objects.append(obj)

    for obj in mesh_objects:
        # Ensure the object has shape keys
        if obj.data.shape_keys is None:
            bpy.context.view_layer.objects.active = obj
            obj.shape_key_add(name="Basis", from_mix=False)

        shape_key_names = (
            {sk.name for sk in obj.data.shape_keys.key_blocks}
            if obj.data.shape_keys
            else set()
        )

        for expr_name, binding in bindings.items():
            if not binding.is_complete:
                messages.append(
                    f"⚠ Expression '{expr_name}' incomplete — skipping for {obj.name}."
                )
                continue

            # Apply each shape key in the binding with its weight
            applied_keys = []
            for sk_name, weight in binding.shape_keys:
                if sk_name in shape_key_names:
                    applied_keys.append(f"{sk_name}={weight:.2f}")
                # If the shape key is not found in this mesh, skip silently

            if applied_keys:
                messages.append(
                    f"✓ Expression '{expr_name}' on {obj.name}: "
                    + ", ".join(applied_keys)
                )

            # Set the active shape key to the expression's primary key
            # (VRM add-on handles blend shape groups)
            if binding.shape_keys:
                primary_key = binding.shape_keys[0][0]
                if primary_key in shape_key_names:
                    sk_index = list(shape_key_names).index(primary_key)
                    obj.data.shape_keys.key_blocks[primary_key].value = weight

    return messages


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Build ExpressionSet from resolved bindings
# ═══════════════════════════════════════════════════════════════════════════════


def build_expression_set(
    bindings: dict[str, ExpressionBinding],
) -> ExpressionSet:
    """Build an ExpressionSet from a dict of resolved expression bindings.

    Args:
        bindings: Dict mapping VRM expression name → ExpressionBinding.

    Returns:
        ExpressionSet with all 8 expression slots populated.
    """
    return ExpressionSet(
        happy=bindings.get("happy"),
        angry=bindings.get("angry"),
        sad=bindings.get("sad"),
        surprised=bindings.get("surprised"),
        neutral=bindings.get("neutral"),
        blink=bindings.get("blink"),
        blink_left=bindings.get("blinkLeft"),
        blink_right=bindings.get("blinkRight"),
    )