"""
Perf Gate — Pre-flight performance budget check for the build pipeline.

Catches builds that would exceed Pi 5 resource limits *before* launching
Blender. Every build passes through this gate first — the anvil checks
the metal before striking.

Phase 12 T7: The forge worker welds the performance gate shut.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from hamr.core.perf import (
    PerformanceBudget,
    PerformanceReport,
    MEMORY_TIERS,
    check_budget,
    estimate_build_triangles,
    estimate_memory_usage,
    estimate_build_time,
)
from hamr.core.presets import CHARACTER_PRESETS, get_preset

logger = logging.getLogger("hamr.core.perf_gate")


# ── PerfGateResult Dataclass ────────────────────────────────────────────────

@dataclass
class PerfGateResult:
    """Result from a performance gate check.

    Attributes:
        allowed: Whether the build is allowed to proceed.
        estimated_triangle_count: Projected total triangles.
        estimated_memory_mb: Projected peak memory in MB.
        estimated_build_time_seconds: Projected build time in seconds.
        budget_tier: Name of the budget tier used ("minimal", "balanced", "high").
        warnings: Non-fatal warnings about resource usage.
        errors: Fatal errors (e.g. invalid input).
        over_budget_reasons: Specific reasons the build is over budget.
    """

    allowed: bool
    estimated_triangle_count: int = 0
    estimated_memory_mb: float = 0.0
    estimated_build_time_seconds: float = 0.0
    budget_tier: str = "balanced"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    over_budget_reasons: list[str] = field(default_factory=list)


# ── Per-Component Resource Estimates ────────────────────────────────────────

ESTIMATE_FACTORS: dict[str, dict[str, float]] = {
    "body": {
        "triangles": 15000,
        "memory_mb": 200,
        "time_s": 10,
    },
    "hair_mesh": {
        "triangles": 8000,
        "memory_mb": 100,
        "time_s": 8,
    },
    "clothing": {
        "triangles": 12000,
        "memory_mb": 80,
        "time_s": 5,
    },
    "stub_bones": {
        "triangles": 0,
        "memory_mb": 10,
        "time_s": 2,
    },
    "weight_paint": {
        "triangles": 0,
        "memory_mb": 20,
        "time_s": 3,
    },
    "spring_bones": {
        "triangles": 0,
        "memory_mb": 5,
        "time_s": 1,
    },
    "first_person": {
        "triangles": 0,
        "memory_mb": 2,
        "time_s": 0.5,
    },
    "collision_meshes": {
        "triangles": 500,
        "memory_mb": 10,
        "time_s": 1,
    },
    "expressions": {
        "triangles": 0,
        "memory_mb": 15,
        "time_s": 2,
    },
    "materials": {
        "triangles": 0,
        "memory_mb": 30,
        "time_s": 3,
    },
}


# ── Helper: dict-style attribute getter ──────────────────────────────────────

def _get_attr(obj, name: str, default=None):
    """Get an attribute from an object or dict, with default."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# ── PerfGate Class ───────────────────────────────────────────────────────────

class PerfGate:
    """Pre-flight performance budget gate.

    Usage::

        gate = PerfGate(tier="balanced")
        result = gate.check_gate(spec=my_spec)
        if not result.allowed:
            print(format_gate_report(result))
    """

    def __init__(
        self,
        budget: PerformanceBudget | None = None,
        tier: str = "balanced",
    ) -> None:
        """Initialize with a budget or select from MEMORY_TIERS.

        Args:
            budget: Explicit budget. If None, *tier* is used to look up
                    MEMORY_TIERS.
            tier: Budget tier name ("minimal", "balanced", "high").
                  Ignored when *budget* is provided.
        """
        if budget is not None:
            self.budget = budget
            # Try to match tier name from MEMORY_TIERS
            self.tier_name = "custom"
            for name, tb in MEMORY_TIERS.items():
                if tb is budget:
                    self.tier_name = name
                    break
        else:
            self.budget = select_budget_tier(tier)
            self.tier_name = tier

    # ── Resource Estimation ──────────────────────────────────────────────

    def estimate_resources(
        self,
        spec: dict | None = None,
        preset_name: str | None = None,
    ) -> dict:
        """Estimate projected resource usage from a spec or preset.

        Sums the per-component ESTIMATE_FACTORS for components that are
        present in the spec, then adds refined estimates from the existing
        perf module for hair styling details and clothing item counts.

        Args:
            spec: A CharacterSpec, dict, or any object with .hair, .body,
                  .clothing attributes. If None, *preset_name* must be given.
            preset_name: Name of a CHARACTER_PRESETS entry to resolve *spec*.

        Returns:
            Dict with keys: triangles (int), memory_mb (float), time_s (float),
            components (list of component names estimated).
        """
        if spec is None and preset_name is not None:
            spec = _resolve_spec(preset_name)
        if spec is None:
            return {
                "triangles": 0,
                "memory_mb": 0.0,
                "time_s": 0.0,
                "components": [],
            }

        triangles = 0
        memory_mb = 0.0
        time_s = 0.0
        components: list[str] = []

        # Body is always present
        triangles += ESTIMATE_FACTORS["body"]["triangles"]
        memory_mb += ESTIMATE_FACTORS["body"]["memory_mb"]
        time_s += ESTIMATE_FACTORS["body"]["time_s"]
        components.append("body")

        # Hair mesh — check if hair is present and not "none"
        hair = _get_attr(spec, "hair")
        if hair is not None:
            hair_style = _get_attr(hair, "style", default="straight")
            if hair_style != "none":
                # Base hair estimate
                triangles += ESTIMATE_FACTORS["hair_mesh"]["triangles"]
                memory_mb += ESTIMATE_FACTORS["hair_mesh"]["memory_mb"]
                time_s += ESTIMATE_FACTORS["hair_mesh"]["time_s"]
                components.append("hair_mesh")

                # Refined triangle estimate from perf module
                hair_tri_delta = estimate_build_triangles(spec) - 15000  # minus body base
                if hair_tri_delta > 0:
                    triangles = triangles - ESTIMATE_FACTORS["hair_mesh"]["triangles"] + hair_tri_delta

        # Clothing — each item adds cost
        clothing = _get_attr(spec, "clothing", default=[])
        if isinstance(spec, dict):
            clothing = spec.get("clothing", [])
        if clothing:
            per_item = len(clothing) if isinstance(clothing, list) else 1
            triangles += ESTIMATE_FACTORS["clothing"]["triangles"] * per_item
            memory_mb += ESTIMATE_FACTORS["clothing"]["memory_mb"] * per_item
            time_s += ESTIMATE_FACTORS["clothing"]["time_s"] * per_item
            components.append("clothing")

            # Refined: use perf module clothing triangle estimates
            clothing_tri_delta = 0
            for item in clothing:
                ctype = _get_attr(item, "type", default="full-outfit")
                from hamr.core.perf import _CLOTHING_TYPE_BASE_TRI
                clothing_tri_delta += _CLOTHING_TYPE_BASE_TRI.get(ctype, 3000)
            if clothing_tri_delta > 0:
                triangles = triangles - ESTIMATE_FACTORS["clothing"]["triangles"] * per_item + clothing_tri_delta

        # Stub bones — always present
        memory_mb += ESTIMATE_FACTORS["stub_bones"]["memory_mb"]
        time_s += ESTIMATE_FACTORS["stub_bones"]["time_s"]
        components.append("stub_bones")

        # Weight paint — present when hair or clothing exists
        has_hair = "hair_mesh" in components
        has_clothing = "clothing" in components
        if has_hair or has_clothing:
            memory_mb += ESTIMATE_FACTORS["weight_paint"]["memory_mb"]
            time_s += ESTIMATE_FACTORS["weight_paint"]["time_s"]
            components.append("weight_paint")
        else:
            # Weight paint the body even without extras
            memory_mb += ESTIMATE_FACTORS["weight_paint"]["memory_mb"]
            time_s += ESTIMATE_FACTORS["weight_paint"]["time_s"]
            components.append("weight_paint")

        # Spring bones — always present
        memory_mb += ESTIMATE_FACTORS["spring_bones"]["memory_mb"]
        time_s += ESTIMATE_FACTORS["spring_bones"]["time_s"]
        components.append("spring_bones")

        # First-person — always present
        memory_mb += ESTIMATE_FACTORS["first_person"]["memory_mb"]
        time_s += ESTIMATE_FACTORS["first_person"]["time_s"]
        components.append("first_person")

        # Collision meshes — present when spring bones exist
        memory_mb += ESTIMATE_FACTORS["collision_meshes"]["memory_mb"]
        time_s += ESTIMATE_FACTORS["collision_meshes"]["time_s"]
        triangles += ESTIMATE_FACTORS["collision_meshes"]["triangles"]
        components.append("collision_meshes")

        # Expressions — check if present in spec
        expressions = _get_attr(spec, "expressions")
        if expressions is not None:
            memory_mb += ESTIMATE_FACTORS["expressions"]["memory_mb"]
            time_s += ESTIMATE_FACTORS["expressions"]["time_s"]
            components.append("expressions")
        elif isinstance(spec, dict) and "expressions" in spec:
            memory_mb += ESTIMATE_FACTORS["expressions"]["memory_mb"]
            time_s += ESTIMATE_FACTORS["expressions"]["time_s"]
            components.append("expressions")

        # Materials — always present
        memory_mb += ESTIMATE_FACTORS["materials"]["memory_mb"]
        time_s += ESTIMATE_FACTORS["materials"]["time_s"]
        components.append("materials")

        # Refine memory with perf module estimates
        try:
            perf_mem = estimate_memory_usage(spec)
            if perf_mem > 0:
                # Use perf module's more detailed memory estimate
                # but keep our component-level tracking
                memory_mb = max(memory_mb, perf_mem)
        except Exception:
            pass  # Fall back to our ESTIMATE_FACTORS-based estimate

        # Refine time with perf module
        try:
            perf_time = estimate_build_time(spec)
            if perf_time > 0:
                time_s = max(time_s, perf_time)
        except Exception:
            pass

        return {
            "triangles": triangles,
            "memory_mb": memory_mb,
            "time_s": time_s,
            "components": components,
        }

    # ── Gate Check ────────────────────────────────────────────────────────

    def check_gate(
        self,
        spec: dict | None = None,
        preset_name: str | None = None,
        force: bool = False,
    ) -> PerfGateResult:
        """Run the full budget check and return pass/fail result.

        Args:
            spec: A CharacterSpec or dict. If None, *preset_name* must be given.
            preset_name: Resolve spec from a preset name.
            force: If True, the build is allowed even if over budget.

        Returns:
            PerfGateResult with allowed flag, estimates, and any warnings/errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Resolve spec
        if spec is None and preset_name is None:
            errors.append("No spec or preset_name provided — nothing to check")
            return PerfGateResult(
                allowed=False,
                errors=errors,
                budget_tier=self.tier_name,
            )

        if spec is None and preset_name is not None:
            try:
                spec = _resolve_spec(preset_name)
            except KeyError as e:
                errors.append(str(e))
                return PerfGateResult(
                    allowed=False,
                    errors=errors,
                    budget_tier=self.tier_name,
                )

        # Estimate resources
        est = self.estimate_resources(spec=spec)

        # Run the perf module's check_budget for detailed warnings
        try:
            perf_report: PerformanceReport = check_budget(spec, self.budget)
        except Exception as exc:
            errors.append(f"Budget check failed: {exc}")
            return PerfGateResult(
                allowed=False,
                estimated_triangle_count=est["triangles"],
                estimated_memory_mb=est["memory_mb"],
                estimated_build_time_seconds=est["time_s"],
                budget_tier=self.tier_name,
                errors=errors,
            )

        # Determine over-budget reasons
        over_budget_reasons: list[str] = []

        if est["triangles"] > self.budget.max_triangles:
            over_pct = ((est["triangles"] / self.budget.max_triangles) - 1) * 100
            over_budget_reasons.append(
                f"Triangles: {est['triangles']} exceeds limit "
                f"{self.budget.max_triangles} by {over_pct:.0f}%"
            )

        if est["memory_mb"] > self.budget.max_memory_mb:
            over_pct = ((est["memory_mb"] / self.budget.max_memory_mb) - 1) * 100
            over_budget_reasons.append(
                f"Memory: {est['memory_mb']:.0f} MB exceeds limit "
                f"{self.budget.max_memory_mb:.0f} MB by {over_pct:.0f}%"
            )

        if est["time_s"] > self.budget.max_build_time_seconds:
            over_pct = ((est["time_s"] / self.budget.max_build_time_seconds) - 1) * 100
            over_budget_reasons.append(
                f"Build time: {est['time_s']:.1f}s exceeds limit "
                f"{self.budget.max_build_time_seconds:.1f}s by {over_pct:.0f}%"
            )

        # Collect warnings from perf report
        if perf_report.warnings:
            warnings.extend(perf_report.warnings)

        # Add near-limit warnings
        tri_pct = est["triangles"] / self.budget.max_triangles
        if 0.8 <= tri_pct < 1.0:
            warnings.append(
                f"Triangles at {tri_pct:.0%} of budget ({est['triangles']}/{self.budget.max_triangles})"
            )

        mem_pct = est["memory_mb"] / self.budget.max_memory_mb
        if 0.8 <= mem_pct < 1.0:
            warnings.append(
                f"Memory at {mem_pct:.0%} of budget ({est['memory_mb']:.0f}/{self.budget.max_memory_mb:.0f} MB)"
            )

        time_pct = est["time_s"] / self.budget.max_build_time_seconds
        if 0.8 <= time_pct < 1.0:
            warnings.append(
                f"Build time at {time_pct:.0%} of budget ({est['time_s']:.1f}/{self.budget.max_build_time_seconds:.1f}s)"
            )

        # Determine if allowed
        over_budget = len(over_budget_reasons) > 0
        allowed = (not over_budget) or force

        return PerfGateResult(
            allowed=allowed,
            estimated_triangle_count=est["triangles"],
            estimated_memory_mb=est["memory_mb"],
            estimated_build_time_seconds=est["time_s"],
            budget_tier=self.tier_name,
            warnings=warnings,
            errors=errors,
            over_budget_reasons=over_budget_reasons,
        )

    # ── Recommendations ───────────────────────────────────────────────────

    def get_recommendations(self, result: PerfGateResult) -> list[str]:
        """Suggest optimizations for over-budget results.

        Args:
            result: A PerfGateResult that is over budget.

        Returns:
            List of human-readable recommendation strings.
        """
        if result.allowed and not result.over_budget_reasons:
            return []  # Within budget — no recommendations needed

        recs: list[str] = []

        budget = self.budget

        # Triangle recommendations
        if result.estimated_triangle_count > budget.max_triangles:
            over_pct = result.estimated_triangle_count / budget.max_triangles
            if over_pct > 1.5:
                recs.append(
                    "⚠ Severely over triangle budget — consider reducing hair "
                    "volume to 0.3 and shell layers to 2, then simplify hair style"
                )
            else:
                recs.append(
                    "Over triangle budget — reduce hair shell layers by 50% "
                    "and volume to ≤0.5"
                )
            recs.append(
                "Remove non-essential clothing items (keep at most 1 outfit)"
            )
            recs.append(
                "Switch to a simpler hair style (straight or bun)"
            )

        # Memory recommendations
        if result.estimated_memory_mb > budget.max_memory_mb:
            recs.append(
                "Over memory budget — reduce texture resolution and "
                "hair shell layers"
            )
            if budget.max_texture_resolution <= 512:
                recs.append(
                    "At minimal tier: skip expressions and collision meshes "
                    "if possible"
                )

        # Build time recommendations
        if result.estimated_build_time_seconds > budget.max_build_time_seconds:
            recs.append(
                "Over time budget — skip clothing items and "
                "reduce hair complexity"
            )
            recs.append(
                "Consider using the 'high' tier for faster builds with "
                "relaxed limits"
            )

        # Tier-specific recommendations
        if self.tier_name == "minimal":
            recs.append(
                "Minimal tier: skip all non-essential components — "
                "hair only, no clothing, reduced expressions"
            )
        elif self.tier_name == "balanced":
            recs.append(
                "Balanced tier: simplify hair (straight/bun) and "
                "limit to 1 clothing item"
            )

        return recs


# ── Utility Functions ─────────────────────────────────────────────────────────

def select_budget_tier(tier_name: str) -> PerformanceBudget:
    """Look up a MEMORY_TIERS budget by name.

    Args:
        tier_name: One of "minimal", "balanced", "high".

    Returns:
        The corresponding PerformanceBudget.

    Raises:
        KeyError: If tier_name is not a known tier.
    """
    if tier_name not in MEMORY_TIERS:
        available = ", ".join(sorted(MEMORY_TIERS.keys()))
        raise KeyError(
            f"Unknown budget tier: {tier_name!r}. Available: {available}"
        )
    return MEMORY_TIERS[tier_name]


def estimate_from_preset(preset_name: str) -> dict:
    """Convenience: estimate resources from a preset name.

    Args:
        preset_name: Name of a CHARACTER_PRESETS entry.

    Returns:
        Dict with triangles, memory_mb, time_s, components.

    Raises:
        KeyError: If preset_name is not a known preset.
    """
    spec = _resolve_spec(preset_name)
    gate = PerfGate(tier="balanced")
    return gate.estimate_resources(spec=spec)


def format_gate_report(result: PerfGateResult) -> str:
    """Format a PerfGateResult as a human-readable report for CLI output.

    Args:
        result: A PerfGateResult to format.

    Returns:
        Multi-line string suitable for printing to the terminal.
    """
    status = "✓ ALLOWED" if result.allowed else "✗ BLOCKED"
    if result.over_budget_reasons and result.allowed:
        status = "⚠ ALLOWED (forced over budget)"

    lines = [
        f"{'=' * 60}",
        f"Performance Gate — {status}",
        f"{'=' * 60}",
        f"  Budget tier:       {result.budget_tier}",
        f"  Estimated tris:    {result.estimated_triangle_count:,}",
        f"  Estimated memory:  {result.estimated_memory_mb:.0f} MB",
        f"  Estimated time:    {result.estimated_build_time_seconds:.1f}s",
    ]

    if result.over_budget_reasons:
        lines.append("")
        lines.append("  Over budget:")
        for reason in result.over_budget_reasons:
            lines.append(f"    ✗ {reason}")

    if result.warnings:
        lines.append("")
        lines.append("  Warnings:")
        for w in result.warnings:
            lines.append(f"    ⚠ {w}")

    if result.errors:
        lines.append("")
        lines.append("  Errors:")
        for e in result.errors:
            lines.append(f"    ✗ {e}")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _resolve_spec(preset_name: str) -> dict:
    """Resolve a preset name to a spec dict.

    Uses CHARACTER_PRESETS if available, falling back to get_preset().

    Args:
        preset_name: Name of a character preset.

    Returns:
        The spec dict from the preset.

    Raises:
        KeyError: If preset_name is unknown.
    """
    if preset_name in CHARACTER_PRESETS:
        return CHARACTER_PRESETS[preset_name]["spec"]
    # Try get_preset which raises a clean error
    return get_preset(preset_name).spec