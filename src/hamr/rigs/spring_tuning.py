"""
Spring Bone Tuning — VRM 1.0 spring bone physics parameter optimization.

Spring bones drive secondary motion: hair sways, skirts drape, accessories bob.
Tuning means finding physically plausible parameters so movement looks right.
This module provides presets, validation, blending, VRM serialization,
and energy estimation — all pure-Python, no Blender required.

Phase 16 (Mjölnir): The forge tempers every spring. — Eldra Járnsdóttir
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ──────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────

@dataclass
class SpringBoneParams:
    """Physics parameters for a spring bone group.

    These map directly to VRM 1.0 spring bone extension fields.
    Tuning them controls how secondary bones behave at runtime.

    Attributes:
        stiffness: How quickly the bone returns to rest pose.
                   Range 0.0–2.0; higher = snappier return.
        gravity_power: Strength of downward gravity pull.
                       Range 0.0–1.0; 0 = no gravity, 1 = full.
        gravity_dir: Normalized direction vector for gravity.
                     Default (0, -1, 0) = straight down.
        drag_force: Air resistance factor, dampening motion.
                    Range 0.0–1.0; higher = more damping.
        hit_radius: Collision sphere radius in meters.
                    Used for collider interaction.
        decay: Energy loss per frame. Range 0.0–1.0;
               higher = faster energy dissipation.
    """

    stiffness: float = 1.0
    gravity_power: float = 0.0
    gravity_dir: tuple[float, float, float] = (0.0, -1.0, 0.0)
    drag_force: float = 0.4
    hit_radius: float = 0.02
    decay: float = 0.3


@dataclass
class SpringBoneGroup:
    """A named group of spring bones sharing the same physics parameters.

    In VRM 1.0, a spring bone group defines a chain of bones
    (e.g., hair tips, skirt hems) with shared physics and
    optional collider references.

    Attributes:
        name: Group identifier (e.g., "long_hair_group").
        bones: Bone names in chain order (root → tip).
        params: Physics parameters for this group.
        collider_groups: Names of collider groups this spring connects to.
    """

    name: str
    bones: list[str] = field(default_factory=list)
    params: SpringBoneParams = field(default_factory=SpringBoneParams)
    collider_groups: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# Presets — physically plausible defaults for common anime parts
# ──────────────────────────────────────────────────────────────

SPRING_PRESETS: dict[str, SpringBoneParams] = {
    "long_hair": SpringBoneParams(
        stiffness=0.6,
        gravity_power=0.2,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.5,
        hit_radius=0.02,
        decay=0.25,
    ),
    "short_hair": SpringBoneParams(
        stiffness=1.2,
        gravity_power=0.05,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.6,
        hit_radius=0.02,
        decay=0.2,
    ),
    "skirt": SpringBoneParams(
        stiffness=0.8,
        gravity_power=0.15,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.4,
        hit_radius=0.03,
        decay=0.3,
    ),
    "breast": SpringBoneParams(
        stiffness=0.4,
        gravity_power=0.3,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.3,
        hit_radius=0.04,
        decay=0.35,
    ),
    "cape": SpringBoneParams(
        stiffness=0.5,
        gravity_power=0.1,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.45,
        hit_radius=0.02,
        decay=0.25,
    ),
    "ribbon": SpringBoneParams(
        stiffness=0.3,
        gravity_power=0.05,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.55,
        hit_radius=0.01,
        decay=0.15,
    ),
    "tail": SpringBoneParams(
        stiffness=0.7,
        gravity_power=0.1,
        gravity_dir=(0.0, -1.0, 0.0),
        drag_force=0.35,
        hit_radius=0.02,
        decay=0.2,
    ),
}


# ──────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────

def validate_spring_params(params: SpringBoneParams) -> list[str]:
    """Validate spring bone parameters and return a list of warning strings.

    Checks each parameter is within its valid range.
    Returns an empty list if all parameters are valid.

    Args:
        params: SpringBoneParams to validate.

    Returns:
        List of warning/error strings. Empty list means valid.
    """
    warnings: list[str] = []

    if not (0.0 <= params.stiffness <= 2.0):
        warnings.append(
            f"stiffness {params.stiffness} out of range [0.0, 2.0]"
        )

    if not (0.0 <= params.gravity_power <= 1.0):
        warnings.append(
            f"gravity_power {params.gravity_power} out of range [0.0, 1.0]"
        )

    if not (0.0 <= params.drag_force <= 1.0):
        warnings.append(
            f"drag_force {params.drag_force} out of range [0.0, 1.0]"
        )

    if params.hit_radius < 0.0:
        warnings.append(
            f"hit_radius {params.hit_radius} must be non-negative"
        )

    if not (0.0 <= params.decay <= 1.0):
        warnings.append(
            f"decay {params.decay} out of range [0.0, 1.0]"
        )

    # Check gravity_dir is a normalized vector (or zero vector)
    gdir = params.gravity_dir
    mag = math.sqrt(gdir[0] ** 2 + gdir[1] ** 2 + gdir[2] ** 2)
    if mag > 0 and abs(mag - 1.0) > 0.01:
        warnings.append(
            f"gravity_dir {gdir} is not normalized (magnitude={mag:.4f})"
        )

    return warnings


# ──────────────────────────────────────────────────────────────
# Group creation from presets
# ──────────────────────────────────────────────────────────────

def create_spring_group(
    name: str,
    bones: list[str],
    preset: str = "long_hair",
    collider_groups: list[str] | None = None,
    **overrides: float,
) -> SpringBoneGroup:
    """Create a SpringBoneGroup from a preset with optional overrides.

    Looks up the preset by name, then applies any keyword overrides
    to create a tuned spring bone group.

    Args:
        name: Group identifier.
        bones: Bone names in chain order (root to tip).
        preset: Preset name (must be a key in SPRING_PRESETS).
        collider_groups: Collider group names. Defaults to empty list.
        **overrides: Keyword args to override preset params.
                     Supported keys match SpringBoneParams fields:
                     stiffness, gravity_power, gravity_dir, drag_force,
                     hit_radius, decay.

    Returns:
        A SpringBoneGroup with preset + override parameters.

    Raises:
        KeyError: If preset name is not found in SPRING_PRESETS.
    """
    if preset not in SPRING_PRESETS:
        raise KeyError(
            f"Unknown spring preset '{preset}'. "
            f"Available: {sorted(SPRING_PRESETS.keys())}"
        )

    base = SPRING_PRESETS[preset]

    # Build params from preset + overrides
    param_kwargs: dict[str, Any] = {
        "stiffness": base.stiffness,
        "gravity_power": base.gravity_power,
        "gravity_dir": base.gravity_dir,
        "drag_force": base.drag_force,
        "hit_radius": base.hit_radius,
        "decay": base.decay,
    }

    # Apply overrides
    valid_fields = {
        "stiffness", "gravity_power", "gravity_dir",
        "drag_force", "hit_radius", "decay",
    }
    for key, value in overrides.items():
        if key in valid_fields:
            param_kwargs[key] = value

    params = SpringBoneParams(**param_kwargs)

    return SpringBoneGroup(
        name=name,
        bones=list(bones),
        params=params,
        collider_groups=list(collider_groups) if collider_groups else [],
    )


# ──────────────────────────────────────────────────────────────
# Tuning curves
# ──────────────────────────────────────────────────────────────

# Tuning multipliers for each target style
_TUNING_CURVES: dict[str, dict[str, float]] = {
    "realistic": {
        "stiffness_mult": 1.0,
        "gravity_mult": 1.0,
        "drag_mult": 1.0,
        "decay_mult": 1.0,
    },
    "snappy": {
        "stiffness_mult": 1.5,
        "gravity_mult": 0.7,
        "drag_mult": 0.6,
        "decay_mult": 0.7,
    },
    "floaty": {
        "stiffness_mult": 0.5,
        "gravity_mult": 1.4,
        "drag_mult": 1.3,
        "decay_mult": 0.6,
    },
}


def tune_spring_params(
    params: SpringBoneParams,
    target: str = "realistic",
) -> SpringBoneParams:
    """Apply a tuning curve to spring bone parameters.

    Adjusts stiffness, gravity, drag, and decay to match a
    target motion style while keeping all values in valid ranges.

    Args:
        params: Base spring bone parameters.
        target: Tuning target — "realistic", "snappy", or "floaty".

    Returns:
        A new SpringBoneParams with tuned values.

    Raises:
        KeyError: If target is not in _TUNING_CURVES.
    """
    if target not in _TUNING_CURVES:
        raise KeyError(
            f"Unknown tuning target '{target}'. "
            f"Available: {sorted(_TUNING_CURVES.keys())}"
        )

    curve = _TUNING_CURVES[target]

    return SpringBoneParams(
        stiffness=_clamp(params.stiffness * curve["stiffness_mult"], 0.0, 2.0),
        gravity_power=_clamp(params.gravity_power * curve["gravity_mult"], 0.0, 1.0),
        gravity_dir=params.gravity_dir,
        drag_force=_clamp(params.drag_force * curve["drag_mult"], 0.0, 1.0),
        hit_radius=params.hit_radius,
        decay=_clamp(params.decay * curve["decay_mult"], 0.0, 1.0),
    )


# ──────────────────────────────────────────────────────────────
# Blending — lerp between two param sets
# ──────────────────────────────────────────────────────────────

def blend_spring_params(
    a: SpringBoneParams,
    b: SpringBoneParams,
    t: float,
) -> SpringBoneParams:
    """Linearly interpolate between two SpringBoneParams.

    At t=0 returns a copy of *a*; at t=1 returns a copy of *b*.
    Values in between are linearly interpolated.

    Args:
        a: First parameter set (t=0).
        b: Second parameter set (t=1).
        t: Blend factor. Clamped to [0.0, 1.0].

    Returns:
        A new SpringBoneParams blended between a and b.
    """
    t = max(0.0, min(1.0, t))  # clamp to [0, 1]

    return SpringBoneParams(
        stiffness=a.stiffness + (b.stiffness - a.stiffness) * t,
        gravity_power=a.gravity_power + (b.gravity_power - a.gravity_power) * t,
        gravity_dir=_lerp_vec3(a.gravity_dir, b.gravity_dir, t),
        drag_force=a.drag_force + (b.drag_force - a.drag_force) * t,
        hit_radius=a.hit_radius + (b.hit_radius - a.hit_radius) * t,
        decay=a.decay + (b.decay - a.decay) * t,
    )


# ──────────────────────────────────────────────────────────────
# VRM conversion
# ──────────────────────────────────────────────────────────────

def spring_params_to_vrm(params: SpringBoneParams) -> dict[str, Any]:
    """Convert SpringBoneParams to a VRM spring bone extension dict.

    Produces a dict matching the VRMC_springBone spring group
    schema for VRM 1.0 export.

    Args:
        params: Spring bone parameters.

    Returns:
        Dict suitable for VRM extension serialization.
    """
    return {
        "stiffness": params.stiffness,
        "gravityPower": params.gravity_power,
        "gravityDir": {
            "x": params.gravity_dir[0],
            "y": params.gravity_dir[1],
            "z": params.gravity_dir[2],
        },
        "dragForce": params.drag_force,
        "hitRadius": params.hit_radius,
        "decay": params.decay,
    }


def spring_group_to_vrm(group: SpringBoneGroup) -> dict[str, Any]:
    """Convert a full SpringBoneGroup to a VRM spring bone extension dict.

    Produces a dict matching the VRMC_springBone spring schema
    for VRM 1.0 export, including bone list and collider references.

    Args:
        group: Spring bone group.

    Returns:
        Dict suitable for VRM extension serialization.
    """
    return {
        "name": group.name,
        "stiffness": group.params.stiffness,
        "gravityPower": group.params.gravity_power,
        "gravityDir": {
            "x": group.params.gravity_dir[0],
            "y": group.params.gravity_dir[1],
            "z": group.params.gravity_dir[2],
        },
        "dragForce": group.params.drag_force,
        "hitRadius": group.params.hit_radius,
        "decay": group.params.decay,
        "boneIndices": list(group.bones),
        "colliderGroupIndices": list(group.collider_groups),
    }


# ──────────────────────────────────────────────────────────────
# Energy estimation
# ──────────────────────────────────────────────────────────────

def estimate_spring_energy(
    params: SpringBoneParams,
    delta_time: float = 1 / 60,
) -> float:
    """Estimate the per-frame energy of a spring bone for performance budgeting.

    This is a rough heuristic, not a physical simulation. Higher energy
    means more CPU cost per spring bone per frame. Useful for comparing
    presets or checking whether tuning increases computational load.

    The energy model: E ≈ (stiffness² + gravity_power) × drag⁻¹ × (1 + decay)
    scaled by delta_time. Stiffer springs and heavier gravity cost more;
    higher drag dampens and reduces cost; decay adds overhead.

    Args:
        params: Spring bone parameters.
        delta_time: Frame time in seconds (default 1/60 for 60 FPS).

    Returns:
        Estimated energy per frame per bone (arbitrary units).
    """
    stiffness_energy = params.stiffness ** 2
    gravity_energy = params.gravity_power

    # Drag acts as a dampener — less drag means more oscillation = more cost
    drag_factor = 1.0 / max(params.drag_force, 0.01)

    # Decay adds overhead (energy dissipation computation)
    decay_overhead = 1.0 + params.decay

    total = (stiffness_energy + gravity_energy) * drag_factor * decay_overhead

    return total * delta_time


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def _lerp_vec3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    t: float,
) -> tuple[float, float, float]:
    """Linearly interpolate between two 3-tuples."""
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )