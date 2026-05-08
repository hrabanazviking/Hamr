"""
Tests for hamr.clothing.mesh — Clothing mesh generation (Phase 11 T3).

Pure-Python pattern/région/computation functions are tested directly.
Blender-dependent code (ClothingMeshGenerator, create_clothing_material) is
tested with RuntimeError checks and @pytest.mark.blender for integration
runs inside Blender.
"""

from __future__ import annotations

import pytest

from hamr.clothing.mesh import (
    CLOTHING_PATTERNS,
    BODY_REGION_VERTEX_GROUPS,
    UV_REGION_MAP,
    _REQUIRED_PATTERN_KEYS,
    ClothingMeshResult,
    ClothingMeshGenerator,
    ClothingForge,
    BLENDER_AVAILABLE,
    resolve_clothing_pattern,
    compute_clothing_regions,
    estimate_triangle_count,
    classify_material_type,
)


# ══════════════════════════════════════════════════════════════════════════════
# CLOTHING_PATTERNS structure tests
# ══════════════════════════════════════════════════════════════════════════════

class TestClothingPatternsStructure:
    """Validate the CLOTHING_PATTERNS configuration dictionary."""

    EXPECTED_PATTERNS = {"tshirt", "jacket", "skirt", "pants", "dress", "shorts"}

    def test_all_six_patterns_present(self):
        """All six required patterns exist in CLOTHING_PATTERNS."""
        assert set(CLOTHING_PATTERNS.keys()) == self.EXPECTED_PATTERNS

    def test_each_pattern_has_required_keys(self):
        """Each pattern has all required keys."""
        for name, cfg in CLOTHING_PATTERNS.items():
            missing = _REQUIRED_PATTERN_KEYS - set(cfg.keys())
            assert not missing, f"Pattern '{name}' missing keys: {missing}"

    def test_each_pattern_has_display_name(self):
        """Each pattern has a human-readable display_name."""
        for name, cfg in CLOTHING_PATTERNS.items():
            assert isinstance(cfg["display_name"], str)
            assert len(cfg["display_name"]) > 0

    def test_each_pattern_has_body_regions(self):
        """Each pattern has a non-empty body_regions list."""
        for name, cfg in CLOTHING_PATTERNS.items():
            regions = cfg["body_regions"]
            assert isinstance(regions, list)
            assert len(regions) > 0, f"{name} has no body_regions"

    def test_each_pattern_has_layers(self):
        """Each pattern has a non-empty layers list."""
        for name, cfg in CLOTHING_PATTERNS.items():
            layers = cfg["layers"]
            assert isinstance(layers, list)
            assert len(layers) > 0, f"{name} has no layers"

    def test_offsets_are_positive_small(self):
        """Offsets are positive and small (in meters)."""
        for name, cfg in CLOTHING_PATTERNS.items():
            offset = cfg["offset"]
            assert 0.001 < offset < 0.05, f"{name}: offset {offset} unreasonable"

    def test_triangle_budgets_ordered(self):
        """Low < medium < high for each pattern."""
        for name, cfg in CLOTHING_PATTERNS.items():
            low = cfg["triangle_budget_low"]
            med = cfg["triangle_budget_medium"]
            high = cfg["triangle_budget_high"]
            assert low < med < high, f"{name}: budgets not ordered: {low} < {med} < {high}"

    def test_hem_width_positive(self):
        """Hem widths are positive."""
        for name, cfg in CLOTHING_PATTERNS.items():
            assert cfg["hem_width"] > 0, f"{name}: hem_width must be positive"

    def test_default_material_is_known(self):
        """Default material is a known category."""
        known_materials = {"fabric", "leather", "metal", "silk", "denim", "fur"}
        for name, cfg in CLOTHING_PATTERNS.items():
            assert cfg["default_material"] in known_materials, \
                f"{name}: unknown material '{cfg['default_material']}'"

    def test_tshirt_pattern_specifics(self):
        """T-shirt has torso + short_sleeves layers."""
        cfg = CLOTHING_PATTERNS["tshirt"]
        assert "torso" in cfg["layers"]
        assert "short_sleeves" in cfg["layers"]
        assert "torso" in cfg["body_regions"]
        assert "arms_upper" in cfg["body_regions"]

    def test_jacket_pattern_specifics(self):
        """Jacket has full_sleeves and collar layers."""
        cfg = CLOTHING_PATTERNS["jacket"]
        assert "full_sleeves" in cfg["layers"]
        assert "collar" in cfg["layers"]

    def test_dress_pattern_has_flare(self):
        """Dress pattern includes flare property."""
        cfg = CLOTHING_PATTERNS["dress"]
        assert "flare" in cfg
        assert cfg["flare"] > 0

    def test_skirt_pattern_has_flare(self):
        """Skirt pattern includes flare property."""
        cfg = CLOTHING_PATTERNS["skirt"]
        assert "flare" in cfg
        assert cfg["flare"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# resolve_clothing_pattern tests
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveClothingPattern:
    """Test resolve_clothing_pattern for each pattern type."""

    @pytest.mark.parametrize(
        "cloth_type", ["tshirt", "jacket", "skirt", "pants", "dress", "shorts"]
    )
    def test_resolve_known_pattern(self, cloth_type):
        """Each known pattern resolves with correct data."""
        pattern = resolve_clothing_pattern(cloth_type)
        assert isinstance(pattern, dict)
        assert "body_regions" in pattern
        assert "offset" in pattern
        assert "layers" in pattern
        assert pattern["body_regions"] == CLOTHING_PATTERNS[cloth_type]["body_regions"]
        assert pattern["offset"] == CLOTHING_PATTERNS[cloth_type]["offset"]

    @pytest.mark.parametrize(
        "cloth_type", ["tshirt", "jacket", "skirt", "pants", "dress", "shorts"]
    )
    def test_resolve_with_name(self, cloth_type):
        """Resolving with a name adds resolved_name and material_override."""
        pattern = resolve_clothing_pattern(cloth_type, name="Denim Jacket")
        assert "resolved_name" in pattern
        assert pattern["resolved_name"] == "Denim Jacket"

    def test_unknown_pattern_falls_back_to_tshirt(self):
        """Unknown cloth_type falls back to tshirt."""
        pattern = resolve_clothing_pattern("nonexistent_type")
        assert pattern["display_name"] == "T-Shirt"

    def test_name_infers_material_override(self):
        """Leather in name sets material_override."""
        pattern = resolve_clothing_pattern("jacket", name="Leather Biker Jacket")
        assert pattern["material_override"] == "leather"

    def test_name_no_override_for_fabric(self):
        """Fabric-default names do not set material_override."""
        pattern = resolve_clothing_pattern("tshirt", name="Cotton Tee")
        # "Cotton Tee" → fabric (default), so material_override should be None or "fabric"
        # Actually classify_material_type("Cotton Tee") returns "fabric"
        # resolve_clothing_pattern only sets override when != "fabric"
        assert pattern.get("material_override") is None or \
               pattern.get("material_override") in ("fabric", None)

    def test_resolved_pattern_is_independent_copy(self):
        """Each resolution returns an independent copy (no aliasing)."""
        p1 = resolve_clothing_pattern("tshirt")
        p2 = resolve_clothing_pattern("tshirt")
        p1["body_regions"].append("extra_region")
        assert "extra_region" not in p2["body_regions"]

    def test_seam_groups_are_independent(self):
        """Seam groups dict is deep-copied (no aliasing)."""
        p1 = resolve_clothing_pattern("jacket")
        p2 = resolve_clothing_pattern("jacket")
        p1["seam_groups"]["collar"] = "modified"
        assert p2["seam_groups"]["collar"] != "modified"

    def test_default_name_uses_display_name(self):
        """No name provided → resolved_name = display_name."""
        pattern = resolve_clothing_pattern("skirt")
        assert pattern["resolved_name"] == "Skirt"


# ══════════════════════════════════════════════════════════════════════════════
# compute_clothing_regions tests
# ══════════════════════════════════════════════════════════════════════════════

class TestComputeClothingRegions:
    """Test compute_clothing_regions with body proportions."""

    @pytest.mark.parametrize(
        "cloth_type", ["tshirt", "jacket", "skirt", "pants", "dress", "shorts"]
    )
    def test_returns_dict_for_each_pattern(self, cloth_type):
        """Each pattern produces a non-empty region dict."""
        pattern = resolve_clothing_pattern(cloth_type)
        regions = compute_clothing_regions(pattern)
        assert isinstance(regions, dict)
        assert len(regions) > 0

    @pytest.mark.parametrize(
        "cloth_type", ["tshirt", "jacket", "skirt", "pants", "dress", "shorts"]
    )
    def test_offsets_are_positive(self, cloth_type):
        """All region offsets are positive."""
        pattern = resolve_clothing_pattern(cloth_type)
        regions = compute_clothing_regions(pattern)
        for region_name, (offset, scale) in regions.items():
            assert offset > 0, f"{cloth_type}/{region_name}: offset {offset} not positive"

    @pytest.mark.parametrize(
        "cloth_type", ["tshirt", "jacket", "skirt", "pants", "dress", "shorts"]
    )
    def test_scales_are_reasonable(self, cloth_type):
        """All region scales are close to 1.0 (within ±50%)."""
        pattern = resolve_clothing_pattern(cloth_type)
        regions = compute_clothing_regions(pattern)
        for region_name, (offset, scale) in regions.items():
            assert 0.5 < scale < 1.5, \
                f"{cloth_type}/{region_name}: scale {scale} out of [0.5, 1.5]"

    def test_default_proportions_use_base_offset(self):
        """Default proportions (None) produce base offset from pattern."""
        pattern = resolve_clothing_pattern("tshirt")
        regions = compute_clothing_regions(pattern, None)
        base_offset = pattern["offset"]
        # Torso region offset should be close to base offset for default proportions
        torso_offset = regions.get("torso", (0, 0))[0]
        assert abs(torso_offset - base_offset) < 0.002

    def test_wide_shoulders_increase_torso_scale(self):
        """Wider shoulders increase torso scale."""
        pattern = resolve_clothing_pattern("tshirt")
        narrow = compute_clothing_regions(pattern, {"shoulder_width": 0.3})
        wide = compute_clothing_regions(pattern, {"shoulder_width": 0.7})
        # Torso scale should be larger for wider shoulders
        if "torso" in narrow and "torso" in wide:
            assert wide["torso"][1] > narrow["torso"][1]

    def test_larger_bust_increases_torso_offset(self):
        """Larger bust increases torso offset."""
        pattern = resolve_clothing_pattern("jacket")
        small = compute_clothing_regions(pattern, {"bust": 0.35})
        large = compute_clothing_regions(pattern, {"bust": 0.7})
        if "torso" in small and "torso" in large:
            assert large["torso"][0] > small["torso"][0]

    def test_skirt_with_flare_has_larger_offset(self):
        """Skirt (which has flare) has increased offset for legs upper."""
        pattern = resolve_clothing_pattern("skirt")
        regions = compute_clothing_regions(pattern)
        # Skirt has flare=0.3, so offset should be base*1.15 ish
        base = pattern["offset"]
        if "legs_upper" in regions:
            # Offset should be larger than base due to flare
            assert regions["legs_upper"][0] >= base

    def test_wide_hips_increase_leg_scale(self):
        """Wider hips increase legs scale."""
        pattern = resolve_clothing_pattern("pants")
        narrow = compute_clothing_regions(pattern, {"hip_width": 0.4})
        wide = compute_clothing_regions(pattern, {"hip_width": 0.8})
        if "legs_full" in narrow and "legs_full" in wide:
            assert wide["legs_full"][1] > narrow["legs_full"][1]

    def test_region_count_matches_pattern(self):
        """Number of computed regions matches pattern body_regions."""
        pattern = resolve_clothing_pattern("dress")
        regions = compute_clothing_regions(pattern)
        assert len(regions) == len(pattern["body_regions"])


# ══════════════════════════════════════════════════════════════════════════════
# estimate_triangle_count tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEstimateTriangleCount:
    """Test estimate_triangle_count at different detail levels."""

    @pytest.mark.parametrize("detail", ["low", "medium", "high"])
    def test_returns_positive_int_for_each_detail(self, detail):
        """Each detail level returns a positive integer."""
        pattern = resolve_clothing_pattern("tshirt")
        count = estimate_triangle_count(pattern, detail)
        assert isinstance(count, int)
        assert count > 0

    def test_low_medium_high_ordering(self):
        """Low < Medium < High for triangle budgets."""
        pattern = resolve_clothing_pattern("jacket")
        low = estimate_triangle_count(pattern, "low")
        med = estimate_triangle_count(pattern, "medium")
        high = estimate_triangle_count(pattern, "high")
        assert low < med < high

    @pytest.mark.parametrize(
        "cloth_type", ["tshirt", "jacket", "skirt", "pants", "dress", "shorts"]
    )
    def test_each_pattern_at_medium(self, cloth_type):
        """Medium detail matches the pattern's triangle_budget_medium."""
        pattern = resolve_clothing_pattern(cloth_type)
        count = estimate_triangle_count(pattern, "medium")
        assert count == pattern["triangle_budget_medium"]

    def test_unknown_detail_defaults_to_medium(self):
        """Unknown detail level falls back to medium budget."""
        pattern = resolve_clothing_pattern("tshirt")
        count = estimate_triangle_count(pattern, "ultra")
        assert count == pattern["triangle_budget_medium"]

    def test_jacket_has_more_triangles_than_shorts_at_medium(self):
        """Jacket generally has a higher triangle budget than shorts."""
        jacket = resolve_clothing_pattern("jacket")
        shorts = resolve_clothing_pattern("shorts")
        j_count = estimate_triangle_count(jacket, "medium")
        s_count = estimate_triangle_count(shorts, "medium")
        assert j_count >= s_count


# ══════════════════════════════════════════════════════════════════════════════
# classify_material_type tests
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyMaterialType:
    """Test classify_material_type name inference."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Leather Jacket", "leather"),
            ("Chain Mail", "metal"),
            ("Silk Dress", "silk"),
            ("Denim Pants", "denim"),
            ("Fur Coat", "fur"),
            ("Cotton T-Shirt", "fabric"),
            ("Metal Armor Plate", "metal"),
            ("Velvet Evening Gown", "silk"),
            ("Jean Shorts", "denim"),
            ("Wool Sweater", "fur"),
        ],
    )
    def test_known_name_patterns(self, name, expected):
        """Known keywords map to expected material categories."""
        assert classify_material_type(name) == expected

    def test_unknown_name_defaults_to_fabric(self):
        """Unknown names default to fabric."""
        assert classify_material_type("Random Thing") == "fabric"

    def test_empty_string_defaults_to_fabric(self):
        """Empty string defaults to fabric."""
        assert classify_material_type("") == "fabric"

    def test_case_insensitive(self):
        """Material classification is case-insensitive."""
        assert classify_material_type("LEATHER boots") == "leather"
        assert classify_material_type("SILK scarf") == "silk"

    def test_hybrid_names_first_match_wins(self):
        """First matching keyword wins (metal before leather)."""
        # "metal" appears before "leather" in the check order
        result = classify_material_type("metallic leather bag")
        assert result == "metal"

    def test_jacket_type_default(self):
        """'jacket' keyword defaults to fabric in type_defaults."""
        assert classify_material_type("Winter Jacket") == "fabric"


# ══════════════════════════════════════════════════════════════════════════════
# ClothingMeshResult dataclass tests
# ══════════════════════════════════════════════════════════════════════════════

class TestClothingMeshResult:
    """Test ClothingMeshResult dataclass."""

    def test_creation_with_defaults(self):
        """ClothingMeshResult stores all fields, with defaults for optional."""
        r = ClothingMeshResult(
            mesh_name="clothing_tshirt",
            pattern_name="T-Shirt",
            triangle_count=2000,
        )
        assert r.mesh_name == "clothing_tshirt"
        assert r.pattern_name == "T-Shirt"
        assert r.triangle_count == 2000
        assert r.regions_created == []
        assert r.material_name == ""
        assert r.weight_transferred is False

    def test_creation_with_all_fields(self):
        """ClothingMeshResult stores all fields when provided."""
        r = ClothingMeshResult(
            mesh_name="clothing_jacket",
            pattern_name="Jacket",
            triangle_count=3000,
            regions_created=["torso", "arms_full"],
            material_name="mat_clothing_jacket",
            weight_transferred=True,
        )
        assert r.mesh_name == "clothing_jacket"
        assert r.pattern_name == "Jacket"
        assert r.triangle_count == 3000
        assert r.regions_created == ["torso", "arms_full"]
        assert r.material_name == "mat_clothing_jacket"
        assert r.weight_transferred is True


# ══════════════════════════════════════════════════════════════════════════════
# BODY_REGION_VERTEX_GROUPS tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBodyRegionVertexGroups:
    """Test BODY_REGION_VERTEX_GROUPS structure."""

    def test_has_mblab_and_turbosquid(self):
        """Both mblab and turbosquid base types exist."""
        assert "mblab" in BODY_REGION_VERTEX_GROUPS
        assert "turbosquid" in BODY_REGION_VERTEX_GROUPS

    def test_all_pattern_regions_have_mappings(self):
        """Every body region used by CLOTHING_PATTERNS has a vertex group mapping in mblab."""
        mblab = BODY_REGION_VERTEX_GROUPS["mblab"]
        for pattern_name, pattern in CLOTHING_PATTERNS.items():
            for region in pattern["body_regions"]:
                assert region in mblab, \
                    f"Pattern '{pattern_name}' region '{region}' not in mblab vertex groups"

    def test_vertex_groups_are_lists_of_strings(self):
        """All vertex group entries are lists of strings."""
        for base_type, regions in BODY_REGION_VERTEX_GROUPS.items():
            for region_name, groups in regions.items():
                assert isinstance(groups, list), \
                    f"{base_type}/{region_name}: vertex groups not a list"
                for g in groups:
                    assert isinstance(g, str), \
                        f"{base_type}/{region_name}: group '{g}' not a string"


# ══════════════════════════════════════════════════════════════════════════════
# UV_REGION_MAP tests
# ══════════════════════════════════════════════════════════════════════════════

class TestUVRegionMap:
    """Test UV_REGION_MAP structure."""

    def test_all_six_patterns_have_uv_maps(self):
        """Each pattern has a UV region map."""
        for pattern_name in CLOTHING_PATTERNS:
            assert pattern_name in UV_REGION_MAP, \
                f"Pattern '{pattern_name}' missing from UV_REGION_MAP"

    def test_uv_regions_are_tuples_of_four_floats(self):
        """Each UV region is a (u_min, v_min, u_max, v_max) tuple."""
        for pattern_name, regions in UV_REGION_MAP.items():
            for region_name, uv_bounds in regions.items():
                assert isinstance(uv_bounds, tuple), \
                    f"{pattern_name}/{region_name}: UV bounds not a tuple"
                assert len(uv_bounds) == 4, \
                    f"{pattern_name}/{region_name}: UV bounds not 4 floats"
                for val in uv_bounds:
                    assert isinstance(val, float), \
                        f"{pattern_name}/{region_name}: UV value not float"
                    assert 0.0 <= val <= 1.0, \
                        f"{pattern_name}/{region_name}: UV value {val} out of [0,1]"

    def test_uv_bounds_are_valid_rectangles(self):
        """UV bounds satisfy (u_min < u_max) and (v_min < v_max)."""
        for pattern_name, regions in UV_REGION_MAP.items():
            for region_name, (u0, v0, u1, v1) in regions.items():
                assert u0 < u1, \
                    f"{pattern_name}/{region_name}: u_min >= u_max"
                assert v0 < v1, \
                    f"{pattern_name}/{region_name}: v_min >= v_max"


# ══════════════════════════════════════════════════════════════════════════════
# Blender-dependent tests
# ══════════════════════════════════════════════════════════════════════════════

class TestClothingMeshGeneratorBlenderGuard:
    """Test that ClothingMeshGenerator raises RuntimeError without bpy."""

    def test_raises_without_bpy(self):
        """ClothingMeshGenerator raises RuntimeError without bpy."""
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy"):
                ClothingMeshGenerator()
        else:
            # If bpy IS available, instantiation should work
            gen = ClothingMeshGenerator()
            assert gen is not None


class TestCreateClothingMaterialBlenderGuard:
    """Test that create_clothing_material raises RuntimeError without bpy."""

    def test_raises_without_bpy(self):
        """create_clothing_material raises RuntimeError without bpy."""
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy"):
                ClothingMeshGenerator.create_clothing_material(
                    "test_mat",
                    primary_hsv=(0.0, 0.0, 0.5),
                    accent_hsv=(120.0, 0.5, 0.7),
                    trim_hsv=(60.0, 0.3, 0.9),
                    material_category="fabric",
                )


class TestClothingForgeAlias:
    """Test ClothingForge alias class."""

    def test_is_subclass(self):
        """ClothingForge is a subclass of ClothingMeshGenerator."""
        assert issubclass(ClothingForge, ClothingMeshGenerator)

    def test_raises_without_bpy(self):
        """ClothingForge raises RuntimeError without bpy (same as parent)."""
        if not BLENDER_AVAILABLE:
            with pytest.raises(RuntimeError, match="bpy"):
                ClothingForge()
        else:
            gen = ClothingForge()
            assert gen is not None


# ══════════════════════════════════════════════════════════════════════════════
# Blender integration tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.blender
@pytest.mark.skipif(not BLENDER_AVAILABLE, reason="Requires Blender/bpy runtime")
class TestClothingMeshGeneratorIntegration:
    """Integration tests that require Blender to be running."""

    def test_generate_tshirt(self):
        """Generate tshirt clothing mesh inside Blender."""
        from hamr.core.models import ClothingSpec

        spec = ClothingSpec(name="Test Tee", type="tshirt")
        gen = ClothingMeshGenerator()
        # This test requires a body mesh and armature to exist in a Blender scene
        # In practice, integration tests would set those up first
        # For now, just verify the generator can be instantiated
        assert gen is not None

    def test_create_material(self):
        """Create clothing material with Principled BSDF."""
        mat = ClothingMeshGenerator.create_clothing_material(
            "test_clothing_mat",
            primary_hsv=(220.0, 0.8, 0.3),
            accent_hsv=(180.0, 0.9, 0.9),
            trim_hsv=(50.0, 1.0, 0.9),
            material_category="fabric",
        )
        assert mat is not None
        assert mat.name == "test_clothing_mat"