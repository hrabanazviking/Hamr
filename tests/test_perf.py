"""
Tests for hamr.core.perf — Performance budget and optimization engine.

Pi 5 has limited resources. These tests prove the budget holds.
"""

import pytest
from dataclasses import dataclass

from hamr.core.perf import (
    PerformanceBudget,
    PerformanceReport,
    TriangleBudget,
    DEFAULT_PI5_BUDGET,
    DEFAULT_TRIANGLE_BUDGET,
    MEMORY_TIERS,
    estimate_build_triangles,
    estimate_memory_usage,
    estimate_build_time,
    check_budget,
    optimize_spec_for_budget,
)
from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    HairColorSpec,
    ClothingSpec,
    SkinSpec,
    EyeSpec,
)


# ── PerformanceBudget Tests ──────────────────────────────────────

class TestPerformanceBudget:
    """Pi 5 defaults must be exact."""

    def test_default_build_time(self) -> None:
        assert DEFAULT_PI5_BUDGET.max_build_time_seconds == 45.0

    def test_default_memory_mb(self) -> None:
        assert DEFAULT_PI5_BUDGET.max_memory_mb == 1500.0

    def test_default_max_triangles(self) -> None:
        assert DEFAULT_PI5_BUDGET.max_triangles == 50000

    def test_default_max_texture_resolution(self) -> None:
        assert DEFAULT_PI5_BUDGET.max_texture_resolution == 1024

    def test_default_blender_timeout(self) -> None:
        assert DEFAULT_PI5_BUDGET.blender_timeout_seconds == 120.0

    def test_default_target_fps(self) -> None:
        assert DEFAULT_PI5_BUDGET.target_fps == 30.0

    def test_fresh_budget_has_defaults(self) -> None:
        budget = PerformanceBudget()
        assert budget.max_build_time_seconds == 45.0
        assert budget.max_memory_mb == 1500.0
        assert budget.max_triangles == 50000

    def test_custom_budget(self) -> None:
        budget = PerformanceBudget(
            max_build_time_seconds=60.0,
            max_memory_mb=2000.0,
            max_triangles=100000,
        )
        assert budget.max_build_time_seconds == 60.0
        assert budget.max_memory_mb == 2000.0
        assert budget.max_triangles == 100000


# ── TriangleBudget Tests ─────────────────────────────────────────

class TestTriangleBudget:
    """Triangle budgets must sum correctly."""

    def test_default_total(self) -> None:
        assert DEFAULT_TRIANGLE_BUDGET.total == 50000

    def test_total_property(self) -> None:
        budget = TriangleBudget(body=10000, hair=15000, clothing=8000, accessories=3000)
        assert budget.total == 36000

    def test_zero_accessories(self) -> None:
        budget = TriangleBudget(body=15000, hair=20000, clothing=10000, accessories=0)
        assert budget.total == 45000

    def test_custom_allocation(self) -> None:
        budget = TriangleBudget(body=20000, hair=25000, clothing=15000, accessories=10000)
        assert budget.total == 70000


# ── PerformanceReport Tests ───────────────────────────────────────

class TestPerformanceReport:
    """Reports must be clear and actionable."""

    def test_within_budget_report(self) -> None:
        report = PerformanceReport(
            build_time_seconds=35.0,
            peak_memory_mb=1200.0,
            total_triangles=40000,
            max_texture_resolution=1024,
            within_budget=True,
            warnings=[],
        )
        assert report.within_budget is True
        assert len(report.warnings) == 0

    def test_over_budget_report(self) -> None:
        report = PerformanceReport(
            build_time_seconds=60.0,
            peak_memory_mb=2500.0,
            total_triangles=80000,
            max_texture_resolution=2048,
            within_budget=False,
            warnings=["Over budget"],
        )
        assert report.within_budget is False
        assert len(report.warnings) == 1

    def test_summary_within_budget(self) -> None:
        report = PerformanceReport(
            build_time_seconds=30.0,
            peak_memory_mb=1000.0,
            total_triangles=35000,
            max_texture_resolution=1024,
            within_budget=True,
            warnings=[],
        )
        summary = report.summary()
        assert "WITHIN BUDGET" in summary
        assert "30.0s" in summary
        assert "1000" in summary

    def test_summary_over_budget(self) -> None:
        report = PerformanceReport(
            build_time_seconds=55.0,
            peak_memory_mb=2000.0,
            total_triangles=70000,
            max_texture_resolution=2048,
            within_budget=False,
            warnings=["Triangle overflow", "Memory overflow"],
        )
        summary = report.summary()
        assert "OVER BUDGET" in summary
        assert "⚠" in summary


# ── estimate_build_triangles Tests ────────────────────────────────

class TestEstimateBuildTriangles:
    """Triangle estimation must be deterministic."""

    def test_minimal_spec(self) -> None:
        """Minimal spec with no hair or clothing — body only."""
        spec = CharacterSpec(hair=HairSpec(style="straight", volume=0.1, shell_layers=2))
        spec.clothing = []
        tri = estimate_build_triangles(spec)
        # Body (15000) + minimal hair
        assert tri > 15000
        assert tri < 50000

    def test_default_spec(self) -> None:
        """Default spec should produce triangles."""
        spec = CharacterSpec()
        tri = estimate_build_triangles(spec)
        # Default has wild-curly hair + full-outfit clothing
        assert tri > 15000

    def test_heavy_spec_over_budget(self) -> None:
        """Heavy spec with lots of hair and clothing should exceed budget."""
        spec = CharacterSpec(
            hair=HairSpec(
                style="wild-curly",
                length="very-long",
                volume=1.0,
                shell_layers=8,
            ),
            clothing=[
                ClothingSpec(type="full-outfit"),
                ClothingSpec(type="hoodie"),
                ClothingSpec(type="dress"),
            ],
        )
        tri = estimate_build_triangles(spec)
        # Very heavy spec
        assert tri > 30000

    def test_hair_style_variation(self) -> None:
        """Different hair styles should produce different triangle counts."""
        spec_straight = CharacterSpec(
            hair=HairSpec(style="straight", length="shoulder", volume=0.7, shell_layers=4),
        )
        spec_straight.clothing = []

        spec_curly = CharacterSpec(
            hair=HairSpec(style="wild-curly", length="shoulder", volume=0.7, shell_layers=4),
        )
        spec_curly.clothing = []

        tri_straight = estimate_build_triangles(spec_straight)
        tri_curly = estimate_build_triangles(spec_curly)
        assert tri_curly > tri_straight

    def test_shell_layers_scale(self) -> None:
        """More shell layers should increase triangle count."""
        spec_fewer = CharacterSpec(
            hair=HairSpec(style="wavy", shell_layers=2),
        )
        spec_fewer.clothing = []

        spec_more = CharacterSpec(
            hair=HairSpec(style="wavy", shell_layers=8),
        )
        spec_more.clothing = []

        assert estimate_build_triangles(spec_more) > estimate_build_triangles(spec_fewer)

    def test_clothing_layers_accumulate(self) -> None:
        """Each clothing layer adds triangles."""
        base_hair = HairSpec(style="straight", volume=0.5, shell_layers=2)

        spec_one = CharacterSpec(
            hair=base_hair,
            clothing=[ClothingSpec(type="tshirt")],
        )

        spec_two = CharacterSpec(
            hair=base_hair,
            clothing=[ClothingSpec(type="tshirt"), ClothingSpec(type="shorts")],
        )

        tri_one = estimate_build_triangles(spec_one)
        tri_two = estimate_build_triangles(spec_two)
        assert tri_two > tri_one


# ── estimate_memory_usage Tests ───────────────────────────────────

class TestEstimateMemoryUsage:
    """Memory estimation must account for meshes, textures, bones."""

    def test_minimal_memory(self) -> None:
        """Minimal spec should estimate under 1.5 GB."""
        spec = CharacterSpec()
        mem = estimate_memory_usage(spec)
        assert mem > 0
        # Base Blender alone is ~350 MB
        assert mem > 350

    def test_heavier_spec_more_memory(self) -> None:
        """More complex spec should estimate more memory."""
        spec_light = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.3, shell_layers=2),
        )
        spec_light.clothing = [ClothingSpec(type="top")]

        spec_heavy = CharacterSpec(
            hair=HairSpec(style="wild-curly", volume=1.0, shell_layers=8),
        )
        spec_heavy.clothing = [
            ClothingSpec(type="full-outfit"),
            ClothingSpec(type="hoodie"),
        ]

        mem_light = estimate_memory_usage(spec_light)
        mem_heavy = estimate_memory_usage(spec_heavy)
        assert mem_heavy > mem_light

    def test_returns_float_mb(self) -> None:
        """Memory should be a float in MB."""
        spec = CharacterSpec()
        mem = estimate_memory_usage(spec)
        assert isinstance(mem, float)
        assert mem > 0


# ── estimate_build_time Tests ────────────────────────────────────

class TestEstimateBuildTime:
    """Build time estimation for Pi 5 ARM64."""

    def test_minimal_time(self) -> None:
        """Minimal spec should estimate under 45 seconds."""
        spec = CharacterSpec()
        time = estimate_build_time(spec)
        assert time > 0

    def test_heavy_spec_takes_longer(self) -> None:
        """Complex hair + clothing should estimate more time."""
        spec_light = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.3, shell_layers=2),
        )
        spec_light.clothing = []

        spec_heavy = CharacterSpec(
            hair=HairSpec(
                style="wild-curly",
                length="very-long",
                volume=1.0,
                shell_layers=8,
            ),
        )
        spec_heavy.clothing = [
            ClothingSpec(type="full-outfit"),
            ClothingSpec(type="dress"),
        ]

        time_light = estimate_build_time(spec_light)
        time_heavy = estimate_build_time(spec_heavy)
        assert time_heavy > time_light

    def test_clothing_adds_time(self) -> None:
        """Each clothing layer adds build time."""
        spec_no_cloth = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.5, shell_layers=4),
        )
        spec_no_cloth.clothing = []

        spec_with_cloth = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.5, shell_layers=4),
            clothing=[ClothingSpec(type="tshirt"), ClothingSpec(type="shorts")],
        )

        time_no = estimate_build_time(spec_no_cloth)
        time_with = estimate_build_time(spec_with_cloth)
        assert time_with > time_no


# ── check_budget Tests ───────────────────────────────────────────

class TestCheckBudget:
    """Budget checking must catch overages."""

    def test_within_budget(self) -> None:
        """A lightweight spec should be within the Pi 5 budget."""
        spec = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.3, shell_layers=2),
        )
        spec.clothing = [ClothingSpec(type="top")]

        budget = PerformanceBudget(
            max_build_time_seconds=180.0,
            max_memory_mb=4000.0,
            max_triangles=100000,
            max_texture_resolution=4096,
        )

        report = check_budget(spec, budget)
        assert report.within_budget is True
        assert len(report.warnings) == 0 or all(
            "75%" not in w for w in report.warnings
        )

    def test_over_triangle_budget(self) -> None:
        """Heavy spec with many triangles should fail budget check."""
        spec = CharacterSpec(
            hair=HairSpec(
                style="wild-curly",
                length="very-long",
                volume=1.0,
                shell_layers=10,
            ),
            clothing=[
                ClothingSpec(type="full-outfit"),
                ClothingSpec(type="hoodie"),
                ClothingSpec(type="dress"),
            ],
        )

        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=10000,  # Very tight
            max_texture_resolution=4096,
        )

        report = check_budget(spec, budget)
        assert report.within_budget is False
        assert any("Triangle" in w for w in report.warnings)

    def test_over_time_budget(self) -> None:
        """Very complex spec should exceed time budget."""
        spec = CharacterSpec(
            hair=HairSpec(style="wild-curly", volume=1.0, shell_layers=8),
            clothing=[
                ClothingSpec(type="full-outfit"),
                ClothingSpec(type="dress"),
                ClothingSpec(type="hoodie"),
            ],
        )

        tight_budget = PerformanceBudget(
            max_build_time_seconds=10.0,  # Very tight
            max_memory_mb=8000.0,
            max_triangles=500000,
            max_texture_resolution=4096,
        )

        report = check_budget(spec, tight_budget)
        assert report.within_budget is False
        assert any("Build time" in w for w in report.warnings)

    def test_default_budget_with_default_spec(self) -> None:
        """Default spec against default Pi 5 budget."""
        spec = CharacterSpec()
        report = check_budget(spec)
        # Default spec should produce a report
        assert report.total_triangles > 0
        assert report.build_time_seconds > 0
        assert report.peak_memory_mb > 0
        assert report.max_texture_resolution > 0

    def test_report_summary_contains_data(self) -> None:
        """Summary should include estimated values."""
        spec = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.5, shell_layers=4),
        )
        report = check_budget(spec, DEFAULT_PI5_BUDGET)
        summary = report.summary()
        assert "Build time" in summary
        assert "Peak memory" in summary
        assert "Total triangles" in summary


# ── MEMORY_TIERS Tests ────────────────────────────────────────────

class TestMemoryTiers:
    """Memory tier configuration must be correct."""

    def test_minimal_tier(self) -> None:
        tier = MEMORY_TIERS["minimal"]
        assert tier.max_memory_mb == 1000.0
        assert tier.max_triangles == 30000
        assert tier.max_texture_resolution == 512
        assert tier.target_fps == 24.0

    def test_balanced_tier(self) -> None:
        tier = MEMORY_TIERS["balanced"]
        assert tier.max_memory_mb == 1500.0
        assert tier.max_triangles == 50000
        assert tier.max_texture_resolution == 1024
        assert tier.target_fps == 30.0
        # Balanced should equal DEFAULT_PI5_BUDGET
        assert tier.max_build_time_seconds == DEFAULT_PI5_BUDGET.max_build_time_seconds

    def test_high_tier(self) -> None:
        tier = MEMORY_TIERS["high"]
        assert tier.max_memory_mb == 2500.0
        assert tier.max_triangles == 80000
        assert tier.max_texture_resolution == 2048
        assert tier.target_fps == 60.0

    def test_three_tiers_exist(self) -> None:
        assert set(MEMORY_TIERS.keys()) == {"minimal", "balanced", "high"}

    def test_tiers_are_ordered(self) -> None:
        """Each tier should be more permissive than the last."""
        min_tier = MEMORY_TIERS["minimal"]
        bal_tier = MEMORY_TIERS["balanced"]
        high_tier = MEMORY_TIERS["high"]

        assert min_tier.max_memory_mb < bal_tier.max_memory_mb < high_tier.max_memory_mb
        assert min_tier.max_triangles < bal_tier.max_triangles < high_tier.max_triangles
        assert min_tier.max_texture_resolution < bal_tier.max_texture_resolution < high_tier.max_texture_resolution


# ── optimize_spec_for_budget Tests ────────────────────────────────

class TestOptimizeSpecForBudget:
    """Budget optimization must reduce specs without mutating the original."""

    def test_does_not_mutate_original(self) -> None:
        """optimize_spec_for_budget must not mutate the input."""
        original = CharacterSpec(
            hair=HairSpec(style="wild-curly", volume=1.0, shell_layers=8),
        )
        original_hair_vol = original.hair.volume
        original_layers = original.hair.shell_layers

        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=30000,
            max_texture_resolution=4096,
        )

        optimized = optimize_spec_for_budget(original, budget)

        # Original must be untouched
        assert original.hair.volume == original_hair_vol
        assert original.hair.shell_layers == original_layers
        # Optimized should be different
        assert optimized.hair.volume < original_hair_vol or optimized.hair.shell_layers < original_layers

    def test_reduces_hair_density(self) -> None:
        """Optimization should reduce hair shell layers and volume."""
        spec = CharacterSpec(
            hair=HairSpec(style="wild-curly", volume=1.0, shell_layers=8),
        )
        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=30000,
            max_texture_resolution=4096,
        )

        optimized = optimize_spec_for_budget(spec, budget)
        assert optimized.hair.shell_layers < 8
        assert optimized.hair.volume <= 0.5

    def test_reduces_clothing_layers(self) -> None:
        """Over-budget with multiple clothing items should keep only the first."""
        spec = CharacterSpec(
            clothing=[
                ClothingSpec(type="full-outfit"),
                ClothingSpec(type="hoodie"),
                ClothingSpec(type="dress"),
            ],
        )

        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=20000,  # Very tight
            max_texture_resolution=4096,
        )

        optimized = optimize_spec_for_budget(spec, budget)
        # Should have at most 1 clothing item
        assert len(optimized.clothing) <= 1

    def test_simplifies_hair_style(self) -> None:
        """If still over budget, should simplify hair style to straight."""
        spec = CharacterSpec(
            hair=HairSpec(
                style="wild-curly",
                length="very-long",
                volume=1.0,
                shell_layers=10,
            ),
            clothing=[ClothingSpec(type="full-outfit"), ClothingSpec(type="dress")],
        )

        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=20000,  # Very tight
            max_texture_resolution=4096,
        )

        optimized = optimize_spec_for_budget(spec, budget)
        assert optimized.hair.style == "straight"

    def test_light_spec_unchanged(self) -> None:
        """A spec already within budget should not be drastically changed."""
        spec = CharacterSpec(
            hair=HairSpec(style="straight", volume=0.3, shell_layers=2),
        )
        spec.clothing = []

        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=500000,
            max_texture_resolution=4096,
        )

        optimized = optimize_spec_for_budget(spec, budget)
        # Light spec shouldn't need style simplification
        assert optimized.hair.style == "straight"

    def test_optimized_has_fewer_triangles(self) -> None:
        """Optimized spec should have fewer estimated triangles than original."""
        spec = CharacterSpec(
            hair=HairSpec(style="wild-curly", volume=1.0, shell_layers=8),
            clothing=[
                ClothingSpec(type="full-outfit"),
                ClothingSpec(type="hoodie"),
            ],
        )

        budget = PerformanceBudget(
            max_build_time_seconds=300.0,
            max_memory_mb=8000.0,
            max_triangles=30000,
            max_texture_resolution=4096,
        )

        original_tri = estimate_build_triangles(spec)
        optimized = optimize_spec_for_budget(spec, budget)
        optimized_tri = estimate_build_triangles(optimized)

        assert optimized_tri < original_tri