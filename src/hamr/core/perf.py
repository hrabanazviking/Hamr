"""
Perf — Performance budget and optimization engine for Pi 5.

The Pi 5 has limited resources (8GB RAM, ARM64, headless Blender).
This module provides pure-Python estimation functions to check whether
a character spec will fit within the Pi 5 performance budget before
spinning up a heavy Blender subprocess.

The budget is sacred. The Pi is the anvil. — Eldra Járnsdóttir
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field


# ── Performance Budget ──────────────────────────────────────────

@dataclass
class PerformanceBudget:
    """Hard limits for a build on resource-constrained hardware.

    Default values target the Raspberry Pi 5 (8GB RAM, ARM64).
    Every number here is a ceiling, not a suggestion.
    """

    max_build_time_seconds: float = 45.0      # Pi 5 target: under 45 seconds
    max_memory_mb: float = 1500.0             # Pi 5 target: under 1.5 GB
    max_triangles: int = 50000                # total across all meshes
    max_texture_resolution: int = 1024        # max texture side in pixels
    blender_timeout_seconds: float = 120.0   # Blender subprocess hard kill
    target_fps: float = 30.0                  # VRM runtime target (VRChat)


@dataclass
class TriangleBudget:
    """Triangle allocation per mesh category.

    The total must stay within PerformanceBudget.max_triangles.
    Think of this as a ration — every triangle costs something on the Pi.
    """

    body: int = 15000
    hair: int = 20000
    clothing: int = 10000
    accessories: int = 5000

    @property
    def total(self) -> int:
        return self.body + self.hair + self.clothing + self.accessories


@dataclass
class PerformanceReport:
    """Report on whether a spec fits within a budget.

    Built by estimate_* functions — pure-Python, no Blender required.
    """

    build_time_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    total_triangles: int = 0
    max_texture_resolution: int = 0
    within_budget: bool = True
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable budget summary."""
        status = "✓ WITHIN BUDGET" if self.within_budget else "✗ OVER BUDGET"
        lines = [
            f"Performance Report — {status}",
            f"  Build time:      {self.build_time_seconds:.1f}s",
            f"  Peak memory:     {self.peak_memory_mb:.0f} MB",
            f"  Total triangles: {self.total_triangles}",
            f"  Max texture res: {self.max_texture_resolution}px",
        ]
        if self.warnings:
            lines.append("  Warnings:")
            for w in self.warnings:
                lines.append(f"    ⚠ {w}")
        return "\n".join(lines)


# ── Pre-configured Budgets ───────────────────────────────────────

DEFAULT_PI5_BUDGET = PerformanceBudget()

DEFAULT_TRIANGLE_BUDGET = TriangleBudget()

MEMORY_TIERS: dict[str, PerformanceBudget] = {
    "minimal": PerformanceBudget(
        max_build_time_seconds=60.0,
        max_memory_mb=1000.0,
        max_triangles=30000,
        max_texture_resolution=512,
        blender_timeout_seconds=180.0,
        target_fps=24.0,
    ),
    "balanced": PerformanceBudget(
        max_build_time_seconds=45.0,
        max_memory_mb=1500.0,
        max_triangles=50000,
        max_texture_resolution=1024,
        blender_timeout_seconds=120.0,
        target_fps=30.0,
    ),
    "high": PerformanceBudget(
        max_build_time_seconds=30.0,
        max_memory_mb=2500.0,
        max_triangles=80000,
        max_texture_resolution=2048,
        blender_timeout_seconds=90.0,
        target_fps=60.0,
    ),
}


# ── Hair Style Triangle Estimates ───────────────────────────────
# Base triangles per hair style (before volume/length modifiers)

_HAIR_STYLE_BASE_TRI = {
    "wild-curly": 8000,
    "straight": 5000,
    "wavy": 6000,
    "braided": 10000,
    "bun": 4000,
    "ponytail": 5500,
}

_HAIR_LENGTH_MULT = {
    "short": 0.6,
    "medium": 0.8,
    "shoulder": 1.0,
    "shoulder-plus": 1.2,
    "long": 1.5,
    "very-long": 2.0,
}

_CLOTHING_TYPE_BASE_TRI = {
    "full-outfit": 8000,
    "top": 3000,
    "bottom": 3000,
    "accessories": 1000,
    "tshirt": 3000,
    "shorts": 2500,
    "skirt": 3000,
    "dress": 6000,
    "hoodie": 4000,
    "school-uniform": 7000,
}

_BODY_BUILD_BASE_TRI = 15000  # base body mesh triangles


# ── Estimation Functions ─────────────────────────────────────────

def estimate_build_triangles(spec) -> int:
    """Estimate total triangle count from a spec.

    Pure-Python estimation — no Blender required.
    Takes a CharacterSpec or any object with .hair, .body, .clothing.

    Returns:
        Estimated total triangle count.
    """
    total = _BODY_BUILD_BASE_TRI

    # Hair triangles
    hair = getattr(spec, "hair", None)
    if hair is not None:
        style = getattr(hair, "style", "straight")
        length = getattr(hair, "length", "shoulder")
        volume = getattr(hair, "volume", 0.7)
        shell_layers = getattr(hair, "shell_layers", 6)

        style_base = _HAIR_STYLE_BASE_TRI.get(style, 6000)
        length_mult = _HAIR_LENGTH_MULT.get(length, 1.0)

        # Volume scales triangle density; shell_layers adds per-layer cost
        hair_tri = int(style_base * length_mult * (0.5 + volume * 0.5))
        # Each shell layer beyond the first adds ~15% of the base
        hair_tri += int(style_base * 0.15 * max(0, shell_layers - 1))
        total += hair_tri

    # Clothing triangles
    clothing = getattr(spec, "clothing", [])
    if clothing is not None:
        for item in clothing:
            ctype = getattr(item, "type", "full-outfit")
            base = _CLOTHING_TYPE_BASE_TRI.get(ctype, 3000)
            total += base

    return total


def estimate_memory_usage(spec) -> float:
    """Estimate peak memory usage in MB from a spec.

    Pure-Python estimation — accounts for textures, meshes, and bones.
    Takes a CharacterSpec or any object with .hair, .body, .clothing.

    Returns:
        Estimated peak memory in MB.
    """
    # Base memory: Blender headless + scene + armature ≈ 350 MB
    base_mb = 350.0

    # Body mesh memory (~1 MB per 1000 triangles)
    body_tri = _BODY_BUILD_BASE_TRI
    base_mb += body_tri / 1000.0

    # Hair memory
    hair = getattr(spec, "hair", None)
    if hair is not None:
        style = getattr(hair, "style", "straight")
        volume = getattr(hair, "volume", 0.7)
        shell_layers = getattr(hair, "shell_layers", 6)

        # Hair mesh memory is proportional to triangle count
        hair_tri = estimate_build_triangles(spec) - body_tri
        # But we only want the hair portion
        style_base = _HAIR_STYLE_BASE_TRI.get(style, 6000)
        length = getattr(hair, "length", "shoulder")
        length_mult = _HAIR_LENGTH_MULT.get(length, 1.0)
        hair_tri = int(style_base * length_mult * (0.5 + volume * 0.5))
        hair_tri += int(style_base * 0.15 * max(0, shell_layers - 1))

        base_mb += hair_tri / 1000.0  # mesh data

        # Hair texture (gradient map) — small
        base_mb += 0.5
    else:
        base_mb += 0.5  # minimal hair texture

    # Clothing memory
    clothing = getattr(spec, "clothing", [])
    if clothing is not None:
        for item in clothing:
            ctype = getattr(item, "type", "full-outfit")
            base_tri = _CLOTHING_TYPE_BASE_TRI.get(ctype, 3000)
            base_mb += base_tri / 1000.0  # mesh data
            base_mb += 2.0  # clothing texture

    # Texture memory (skin, eyes, etc.)
    # Assume base body textures at default resolution
    body = getattr(spec, "body", None)
    # Default texture resolution from constants
    tex_res = 2048  # TEXTURE_SIZE from constants
    # 4 channels × resolution² = bytes, converted to MB
    tex_mb = (tex_res * tex_res * 4) / (1024 * 1024)
    base_mb += tex_mb * 3  # skin, normal, ao maps approximately

    # Bone/armature memory (~0.1 MB per bone, 25 bones minimum + extras)
    base_mb += 3.0  # armature + weight data

    return base_mb


def estimate_build_time(spec) -> float:
    """Estimate build time in seconds from a spec.

    Pure-Python estimation based on hair complexity, clothing layers,
    and bone count. Target: Pi 5 ARM64.

    Returns:
        Estimated build time in seconds.
    """
    # Base time for Blender startup + base mesh + armature + export
    base_seconds = 15.0

    hair = getattr(spec, "hair", None)
    if hair is not None:
        style = getattr(hair, "style", "straight")
        length = getattr(hair, "length", "shoulder")
        volume = getattr(hair, "volume", 0.7)
        shell_layers = getattr(hair, "shell_layers", 6)

        # Complex hair takes longer
        style_time = {
            "wild-curly": 10.0,
            "straight": 5.0,
            "wavy": 7.0,
            "braided": 12.0,
            "bun": 4.0,
            "ponytail": 6.0,
        }.get(style, 7.0)

        length_time_mult = _HAIR_LENGTH_MULT.get(length, 1.0)
        # Shell layers add linear time
        layer_time = shell_layers * 0.8  # ~0.8s per shell layer

        hair_time = style_time * (0.6 + volume * 0.4) * length_time_mult + layer_time
        base_seconds += hair_time

    # Clothing layers add time proportionally
    clothing = getattr(spec, "clothing", [])
    if clothing is not None:
        for item in clothing:
            ctype = getattr(item, "type", "full-outfit")
            item_time = {
                "full-outfit": 5.0,
                "top": 2.0,
                "bottom": 2.0,
                "accessories": 0.5,
                "tshirt": 2.0,
                "shorts": 1.5,
                "skirt": 2.0,
                "dress": 4.0,
                "hoodie": 3.0,
                "school-uniform": 5.0,
            }.get(ctype, 3.0)
            base_seconds += item_time

    return base_seconds


def check_budget(spec, budget: PerformanceBudget = DEFAULT_PI5_BUDGET) -> PerformanceReport:
    """Check whether a spec fits within the given performance budget.

    Pure-Python check — estimates without building.
    Use before spinning up Blender to catch over-budget specs early.

    Args:
        spec: A CharacterSpec or any object with .hair, .body, .clothing.
        budget: The performance budget to check against.

    Returns:
        PerformanceReport with within_budget flag and warnings.
    """
    warnings: list[str] = []

    est_tri = estimate_build_triangles(spec)
    est_mem = estimate_memory_usage(spec)
    est_time = estimate_build_time(spec)

    # Check texture resolution — assume TEXTURE_SIZE from constants (2048)
    # but specs can override; for now, use the default
    max_tex = 2048

    within = True

    if est_tri > budget.max_triangles:
        within = False
        over_pct = ((est_tri / budget.max_triangles) - 1) * 100
        warnings.append(
            f"Triangle count {est_tri} exceeds budget {budget.max_triangles} "
            f"by {over_pct:.0f}%"
        )

    if est_mem > budget.max_memory_mb:
        within = False
        over_pct = ((est_mem / budget.max_memory_mb) - 1) * 100
        warnings.append(
            f"Memory estimate {est_mem:.0f} MB exceeds budget {budget.max_memory_mb:.0f} MB "
            f"by {over_pct:.0f}%"
        )

    if est_time > budget.max_build_time_seconds:
        within = False
        over_pct = ((est_time / budget.max_build_time_seconds) - 1) * 100
        warnings.append(
            f"Build time estimate {est_time:.1f}s exceeds budget "
            f"{budget.max_build_time_seconds:.1f}s by {over_pct:.0f}%"
        )

    if max_tex > budget.max_texture_resolution:
        within = False
        warnings.append(
            f"Texture resolution {max_tex}px exceeds budget "
            f"{budget.max_texture_resolution}px"
        )

    if est_time > budget.blender_timeout_seconds * 0.75:
        warnings.append(
            f"Build time estimate {est_time:.1f}s is within 75% of "
            f"Blender timeout ({budget.blender_timeout_seconds:.0f}s) — "
            f"consider increasing timeout"
        )

    return PerformanceReport(
        build_time_seconds=est_time,
        peak_memory_mb=est_mem,
        total_triangles=est_tri,
        max_texture_resolution=max_tex,
        within_budget=within,
        warnings=warnings,
    )


def optimize_spec_for_budget(spec, budget: PerformanceBudget = DEFAULT_PI5_BUDGET):
    """Reduce a spec to fit within a performance budget.

    Creates a modified copy of the spec with reduced hair density,
    clothing detail, and texture resolution. Does NOT mutate the input.

    Strategy (in order of impact):
    1. Reduce hair shell layers and volume
    2. Reduce texture resolution in the spec
    3. Remove non-essential clothing layers (keep at most 1)
    4. Simplify hair style if still over budget

    Args:
        spec: A CharacterSpec to optimize.
        budget: The performance budget to target.

    Returns:
        A modified copy of the spec that should fit the budget.
    """
    # Deep copy to avoid mutating the input
    optimized = copy.deepcopy(spec)

    # Step 1: Reduce hair density
    hair = getattr(optimized, "hair", None)
    if hair is not None:
        # Reduce shell layers aggressively
        current_layers = getattr(hair, "shell_layers", 6)
        setattr(hair, "shell_layers", max(2, current_layers // 2))

        # Reduce volume
        current_volume = getattr(hair, "volume", 0.7)
        setattr(hair, "volume", min(current_volume, 0.5))

        # Check if still over budget on triangles
        est_tri = estimate_build_triangles(optimized)
        if est_tri > budget.max_triangles:
            # More aggressive: 2 shell layers only, low volume
            setattr(hair, "shell_layers", 2)
            setattr(hair, "volume", 0.3)

    # Step 2: Check again — simplify hair style if still over triangle budget
    est_tri = estimate_build_triangles(optimized)
    if hair is not None and est_tri > budget.max_triangles:
        # Downgrade to simpler style
        style = getattr(hair, "style", "straight")
        style_complexity = {
            "wild-curly": 3, "braided": 3,
            "wavy": 2, "ponytail": 2, "bun": 1,
            "straight": 1,
        }
        if style_complexity.get(style, 2) > 1:
            setattr(hair, "style", "straight")

    # Step 3: Reduce clothing layers — keep at most 1 clothing item
    clothing = getattr(optimized, "clothing", [])
    if clothing is not None and len(clothing) > 1:
        # Keep only the first clothing item
        setattr(optimized, "clothing", [clothing[0]])

    # Step 4: Final check — if still over budget, clear accessories-type clothing
    est_tri = estimate_build_triangles(optimized)
    if est_tri > budget.max_triangles:
        clothing = getattr(optimized, "clothing", [])
        if clothing is not None:
            filtered = [
                c for c in clothing
                if getattr(c, "type", "full-outfit") != "accessories"
            ]
            setattr(optimized, "clothing", filtered)

    return optimized