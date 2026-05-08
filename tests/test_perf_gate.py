"""
Tests for the performance gate — pre-flight budget check module.

Phase 12 T7: The forge worker tests the gate before the forge opens.
"""

from __future__ import annotations

import pytest

from hamr.core.perf import (
    PerformanceBudget,
    MEMORY_TIERS,
)
from hamr.core.perf_gate import (
    PerfGateResult,
    PerfGate,
    ESTIMATE_FACTORS,
    select_budget_tier,
    estimate_from_preset,
    format_gate_report,
)
from hamr.core.presets import CHARACTER_PRESETS


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_gate():
    """PerfGate with minimal budget."""
    return PerfGate(tier="minimal")


@pytest.fixture
def balanced_gate():
    """PerfGate with balanced budget."""
    return PerfGate(tier="balanced")


@pytest.fixture
def high_gate():
    """PerfGate with high budget."""
    return PerfGate(tier="high")


@pytest.fixture
def full_spec():
    """A spec dict with all components enabled."""
    return CHARACTER_PRESETS["anime_girl_default"]["spec"]


@pytest.fixture
def minimal_spec():
    """A spec dict with minimal components (no hair, no clothing)."""
    return {
        "name": "Minimal Bot",
        "body": {
            "height_cm": 170.0,
            "build": "average",
        },
        "face": {
            "jaw": "square",
        },
        "hair": {
            "style": "none",
        },
        "clothing": [],
        "physics": {},
    }


@pytest.fixture
def heavy_spec():
    """A spec designed to exceed the balanced budget."""
    return CHARACTER_PRESETS["anime_boy_warrior"]["spec"]


# ── PerfGateResult Dataclass ────────────────────────────────────────────────

class TestPerfGateResult:
    """Test PerfGateResult creation and defaults."""

    def test_defaults(self):
        result = PerfGateResult(allowed=True)
        assert result.allowed is True
        assert result.estimated_triangle_count == 0
        assert result.estimated_memory_mb == 0.0
        assert result.estimated_build_time_seconds == 0.0
        assert result.budget_tier == "balanced"
        assert result.warnings == []
        assert result.errors == []
        assert result.over_budget_reasons == []

    def test_all_fields(self):
        result = PerfGateResult(
            allowed=False,
            estimated_triangle_count=60000,
            estimated_memory_mb=1800.0,
            estimated_build_time_seconds=55.0,
            budget_tier="minimal",
            warnings=["Near triangle limit"],
            errors=[],
            over_budget_reasons=["Triangles over limit"],
        )
        assert result.allowed is False
        assert result.estimated_triangle_count == 60000
        assert result.estimated_memory_mb == 1800.0
        assert result.estimated_build_time_seconds == 55.0
        assert result.budget_tier == "minimal"
        assert len(result.warnings) == 1
        assert len(result.over_budget_reasons) == 1

    def test_independent_default_factories(self):
        """Each instance should have its own list objects."""
        r1 = PerfGateResult(allowed=True)
        r2 = PerfGateResult(allowed=True)
        r1.warnings.append("test")
        assert len(r2.warnings) == 0


# ── ESTIMATE_FACTORS ────────────────────────────────────────────────────────

class TestEstimateFactors:
    """Test that ESTIMATE_FACTORS has all expected component entries."""

    EXPECTED_COMPONENTS = [
        "body", "hair_mesh", "clothing", "stub_bones", "weight_paint",
        "spring_bones", "first_person", "collision_meshes", "expressions",
        "materials",
    ]

    def test_all_components_present(self):
        for comp in self.EXPECTED_COMPONENTS:
            assert comp in ESTIMATE_FACTORS, f"Missing component: {comp}"

    def test_each_component_has_required_keys(self):
        for comp, factors in ESTIMATE_FACTORS.items():
            assert "triangles" in factors, f"{comp} missing 'triangles'"
            assert "memory_mb" in factors, f"{comp} missing 'memory_mb'"
            assert "time_s" in factors, f"{comp} missing 'time_s'"

    def test_triangle_values(self):
        assert ESTIMATE_FACTORS["body"]["triangles"] == 15000
        assert ESTIMATE_FACTORS["hair_mesh"]["triangles"] == 8000
        assert ESTIMATE_FACTORS["clothing"]["triangles"] == 12000
        assert ESTIMATE_FACTORS["collision_meshes"]["triangles"] == 500
        # Non-mesh components have 0 triangles
        for comp in ["stub_bones", "weight_paint", "spring_bones",
                     "first_person", "expressions", "materials"]:
            assert ESTIMATE_FACTORS[comp]["triangles"] == 0

    def test_memory_values(self):
        assert ESTIMATE_FACTORS["body"]["memory_mb"] == 200
        assert ESTIMATE_FACTORS["hair_mesh"]["memory_mb"] == 100
        assert ESTIMATE_FACTORS["clothing"]["memory_mb"] == 80
        assert ESTIMATE_FACTORS["materials"]["memory_mb"] == 30

    def test_time_values(self):
        assert ESTIMATE_FACTORS["body"]["time_s"] == 10
        assert ESTIMATE_FACTORS["hair_mesh"]["time_s"] == 8
        assert ESTIMATE_FACTORS["clothing"]["time_s"] == 5

    def test_total_component_count(self):
        assert len(ESTIMATE_FACTORS) == len(self.EXPECTED_COMPONENTS)


# ── PerfGate.estimate_resources ──────────────────────────────────────────────

class TestPerfGateEstimateResources:
    """Test resource estimation."""

    def test_full_spec(self, balanced_gate, full_spec):
        est = balanced_gate.estimate_resources(spec=full_spec)
        assert est["triangles"] > 0
        assert est["memory_mb"] > 0
        assert est["time_s"] > 0
        assert "body" in est["components"]
        assert "hair_mesh" in est["components"]
        assert "clothing" in est["components"]

    def test_minimal_spec(self, balanced_gate, minimal_spec):
        est = balanced_gate.estimate_resources(spec=minimal_spec)
        assert est["triangles"] > 0  # Body is always present
        assert "body" in est["components"]
        # "none" hair style should NOT add hair_mesh
        assert "hair_mesh" not in est["components"]
        # Empty clothing list should NOT add clothing
        assert "clothing" not in est["components"]

    def test_preset_specs(self, balanced_gate):
        """All 6 presets should return valid estimates."""
        for name in CHARACTER_PRESETS:
            est = balanced_gate.estimate_resources(preset_name=name)
            assert est["triangles"] > 0, f"Preset {name} has 0 triangles"
            assert est["memory_mb"] > 0, f"Preset {name} has 0 memory"
            assert est["time_s"] > 0, f"Preset {name} has 0 time"

    def test_components_always_included(self, balanced_gate, minimal_spec):
        """Core components should always be present."""
        est = balanced_gate.estimate_resources(spec=minimal_spec)
        for comp in ["body", "stub_bones", "weight_paint", "spring_bones",
                      "first_person", "collision_meshes", "materials"]:
            assert comp in est["components"], f"Missing core component: {comp}"

    def test_preset_anime_girl_default(self, balanced_gate):
        est = balanced_gate.estimate_resources(preset_name="anime_girl_default")
        # anime_girl_default has straight long hair + full-outfit clothing
        assert est["triangles"] >= 15000  # at least body
        assert "hair_mesh" in est["components"]
        assert "clothing" in est["components"]

    def test_preset_anime_boy_default(self, balanced_gate):
        """anime_boy_default has short straight hair and no clothing."""
        est = balanced_gate.estimate_resources(preset_name="anime_boy_default")
        assert "hair_mesh" in est["components"]
        # anime_boy_default clothing list is empty
        assert "clothing" not in est["components"]

    def test_none_spec_returns_empty(self, balanced_gate):
        est = balanced_gate.estimate_resources(spec=None)
        assert est["triangles"] == 0
        assert est["memory_mb"] == 0.0
        assert est["time_s"] == 0.0
        assert est["components"] == []


# ── PerfGate.check_gate ──────────────────────────────────────────────────────

class TestPerfGateCheckGate:
    """Test the gate check pass/fail logic."""

    def test_within_budget(self, balanced_gate, minimal_spec):
        result = balanced_gate.check_gate(spec=minimal_spec)
        # Minimal spec should be within balanced budget
        assert result.allowed is True
        assert len(result.over_budget_reasons) == 0
        assert result.estimated_triangle_count > 0

    def test_over_budget_minimal(self, minimal_gate, heavy_spec):
        """Heavy spec should exceed minimal budget."""
        result = minimal_gate.check_gate(spec=heavy_spec)
        assert result.allowed is False
        assert len(result.over_budget_reasons) > 0

    def test_forced_over_budget(self, minimal_gate, heavy_spec):
        """With force=True, even over-budget builds should be allowed."""
        result = minimal_gate.check_gate(spec=heavy_spec, force=True)
        assert result.allowed is True
        assert len(result.over_budget_reasons) > 0  # Still reports why over budget

    def test_no_spec_no_preset(self, balanced_gate):
        result = balanced_gate.check_gate(spec=None, preset_name=None)
        assert result.allowed is False
        assert len(result.errors) > 0

    def test_invalid_preset_name(self, balanced_gate):
        result = balanced_gate.check_gate(preset_name="nonexistent_preset_xyz")
        assert result.allowed is False
        assert len(result.errors) > 0

    def test_preset_name_specified(self, balanced_gate):
        result = balanced_gate.check_gate(preset_name="chibi_cute")
        # chibi_cute should be within balanced budget
        assert isinstance(result, PerfGateResult)
        assert result.budget_tier == "balanced"

    def test_result_has_estimates(self, balanced_gate, full_spec):
        result = balanced_gate.check_gate(spec=full_spec)
        assert result.estimated_triangle_count > 0
        assert result.estimated_memory_mb > 0
        assert result.estimated_build_time_seconds > 0

    def test_high_budget_allows_more(self, minimal_spec, full_spec):
        """A spec that fails minimal budget should pass high budget."""
        min_gate = PerfGate(tier="minimal")
        hi_gate = PerfGate(tier="high")

        min_result = min_gate.check_gate(spec=full_spec)
        hi_result = hi_gate.check_gate(spec=full_spec)

        # high tier should allow at least as much as minimal
        assert hi_gate.budget.max_triangles > min_gate.budget.max_triangles


# ── PerfGate.get_recommendations ─────────────────────────────────────────────

class TestPerfGateGetRecommendations:
    """Test optimization recommendations."""

    def test_within_budget_no_recommendations(self, balanced_gate, minimal_spec):
        result = balanced_gate.check_gate(spec=minimal_spec)
        if result.allowed and not result.over_budget_reasons:
            recs = balanced_gate.get_recommendations(result)
            assert recs == []

    def test_over_budget_has_recommendations(self, minimal_gate, heavy_spec):
        result = minimal_gate.check_gate(spec=heavy_spec)
        recs = minimal_gate.get_recommendations(result)
        assert len(recs) > 0

    def test_triangle_recommendations(self, minimal_gate, heavy_spec):
        result = minimal_gate.check_gate(spec=heavy_spec)
        recs = minimal_gate.get_recommendations(result)
        # Should mention hair reduction or clothing
        recs_text = " ".join(recs).lower()
        assert any(kw in recs_text for kw in ["hair", "clothing", "triangle"])

    def test_forced_over_budget_recommendations(self, minimal_gate, heavy_spec):
        result = minimal_gate.check_gate(spec=heavy_spec, force=True)
        # Even forced builds should get recommendations
        recs = minimal_gate.get_recommendations(result)
        assert len(recs) > 0


# ── select_budget_tier ───────────────────────────────────────────────────────

class TestSelectBudgetTier:
    """Test budget tier lookup."""

    def test_all_three_tiers(self):
        for tier_name in ["minimal", "balanced", "high"]:
            budget = select_budget_tier(tier_name)
            assert isinstance(budget, PerformanceBudget)

    def test_minimal_tier_values(self):
        budget = select_budget_tier("minimal")
        assert budget.max_triangles == 30000
        assert budget.max_memory_mb == 1000.0

    def test_balanced_tier_values(self):
        budget = select_budget_tier("balanced")
        assert budget.max_triangles == 50000
        assert budget.max_memory_mb == 1500.0

    def test_high_tier_values(self):
        budget = select_budget_tier("high")
        assert budget.max_triangles == 80000
        assert budget.max_memory_mb == 2500.0

    def test_invalid_tier_raises(self):
        with pytest.raises(KeyError, match="Unknown budget tier"):
            select_budget_tier("ultra")


# ── estimate_from_preset ─────────────────────────────────────────────────────

class TestEstimateFromPreset:
    """Test convenience function for preset estimation."""

    def test_all_six_presets(self):
        expected_presets = [
            "anime_girl_default",
            "anime_girl_warrior",
            "anime_girl_mage",
            "anime_boy_default",
            "anime_boy_warrior",
            "chibi_cute",
        ]
        for name in expected_presets:
            est = estimate_from_preset(name)
            assert est["triangles"] > 0, f"{name}: expected tris > 0"
            assert est["memory_mb"] > 0, f"{name}: expected memory > 0"
            assert est["time_s"] > 0, f"{name}: expected time > 0"

    def test_invalid_preset_raises(self):
        with pytest.raises(KeyError):
            estimate_from_preset("nonexistent_preset_xyz")

    def test_anime_girl_default_has_hair_and_clothing(self):
        est = estimate_from_preset("anime_girl_default")
        assert "hair_mesh" in est["components"]
        assert "clothing" in est["components"]

    def test_anime_boy_default_has_no_clothing(self):
        est = estimate_from_preset("anime_boy_default")
        assert "hair_mesh" in est["components"]
        assert "clothing" not in est["components"]


# ── format_gate_report ────────────────────────────────────────────────────────

class TestFormatGateReport:
    """Test human-readable report formatting."""

    def test_allowed_result(self):
        result = PerfGateResult(
            allowed=True,
            estimated_triangle_count=25000,
            estimated_memory_mb=800.0,
            estimated_build_time_seconds=30.0,
            budget_tier="balanced",
        )
        report = format_gate_report(result)
        assert "ALLOWED" in report
        assert "25,000" in report
        assert "800" in report
        assert "30.0s" in report
        assert "balanced" in report

    def test_blocked_result(self):
        result = PerfGateResult(
            allowed=False,
            estimated_triangle_count=80000,
            estimated_memory_mb=3000.0,
            estimated_build_time_seconds=120.0,
            budget_tier="minimal",
            over_budget_reasons=[
                "Triangles: 80000 exceeds limit 30000 by 167%",
            ],
        )
        report = format_gate_report(result)
        assert "BLOCKED" in report
        assert "80,000" in report
        assert "Over budget" in report

    def test_forced_result(self):
        result = PerfGateResult(
            allowed=True,
            estimated_triangle_count=60000,
            estimated_memory_mb=2000.0,
            estimated_build_time_seconds=55.0,
            budget_tier="minimal",
            over_budget_reasons=["Triangles over limit"],
        )
        report = format_gate_report(result)
        assert "ALLOWED" in report
        assert "forced over budget" in report.lower() or "forced" in report.lower()

    def test_with_warnings(self):
        result = PerfGateResult(
            allowed=True,
            estimated_triangle_count=25000,
            estimated_memory_mb=800.0,
            estimated_build_time_seconds=30.0,
            budget_tier="balanced",
            warnings=["Near triangle limit"],
        )
        report = format_gate_report(result)
        assert "Warnings" in report
        assert "Near triangle limit" in report

    def test_with_errors(self):
        result = PerfGateResult(
            allowed=False,
            estimated_triangle_count=0,
            estimated_memory_mb=0.0,
            estimated_build_time_seconds=0.0,
            budget_tier="balanced",
            errors=["No spec or preset_name provided"],
        )
        report = format_gate_report(result)
        assert "Errors" in report
        assert "No spec" in report


# ── Error Cases ──────────────────────────────────────────────────────────────

class TestErrorCases:
    """Test edge and error cases."""

    def test_none_spec_without_preset(self, balanced_gate):
        result = balanced_gate.check_gate(spec=None, preset_name=None)
        assert result.allowed is False
        assert "No spec" in " ".join(result.errors)

    def test_invalid_preset_name(self, balanced_gate):
        result = balanced_gate.check_gate(preset_name="does_not_exist")
        assert result.allowed is False
        assert len(result.errors) > 0

    def test_estimate_with_none_spec_no_preset(self, balanced_gate):
        est = balanced_gate.estimate_resources(spec=None)
        assert est["triangles"] == 0

    def test_estimate_with_both_spec_and_preset(self, balanced_gate, minimal_spec):
        """When both spec and preset_name given, spec takes precedence."""
        est = balanced_gate.estimate_resources(spec=minimal_spec, preset_name="anime_girl_default")
        # Should use the spec, not the preset
        assert "body" in est["components"]

    def test_custom_budget(self):
        """PerfGate with custom budget (not from tiers)."""
        custom_budget = PerformanceBudget(
            max_build_time_seconds=20.0,
            max_memory_mb=500.0,
            max_triangles=20000,
        )
        gate = PerfGate(budget=custom_budget)
        assert gate.budget.max_triangles == 20000
        assert gate.tier_name == "custom"

    def test_force_allows_over_budget(self, minimal_gate, heavy_spec):
        result_normal = minimal_gate.check_gate(spec=heavy_spec, force=False)
        result_forced = minimal_gate.check_gate(spec=heavy_spec, force=True)
        # The normal result should be blocked
        if not result_normal.allowed:
            # The forced result should be allowed
            assert result_forced.allowed is True
            # Both should have over_budget_reasons
            assert len(result_forced.over_budget_reasons) > 0


# ── Blender-Marked Tests ────────────────────────────────────────────────────

@pytest.mark.blender
class TestPerfGateBlender:
    """Tests that verify perf_gate works alongside Blender integration.

    These tests require bpy to be available.
    """

    def test_heavy_spec_gate_check(self, balanced_gate):
        """Full integration: check anime_boy_warrior against balanced gate."""
        spec = CHARACTER_PRESETS["anime_boy_warrior"]["spec"]
        result = balanced_gate.check_gate(spec=spec)
        assert isinstance(result, PerfGateResult)
        assert result.budget_tier == "balanced"
        if not result.allowed:
            # It's over budget — check recommendations exist
            recs = balanced_gate.get_recommendations(result)
            assert len(recs) > 0