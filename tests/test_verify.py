# =============================================================================
# Hamr Phase 11 T5 Tests — Rig Verification Tool
# =============================================================================

import pytest
from hamr.core.constants import VRM_25_BONE_NAMES
from hamr.rigs.verify import (
    MB_LAB_NAMES_TO_VRM,
    VRM_BONE_HIERARCHY,
    RigReport,
    RigVerifier,
    check_hierarchy_graph,
    check_naming_conventions_pure,
    cmd_verify_rig,
    generate_rig_report,
    verify_bone_list,
)


# ── Test fixtures ──────────────────────────────────────────────────────────

# Full 25 VRM bone names
ALL_VRM_BONES = list(VRM_25_BONE_NAMES)

# MB-Lab bone names (22 bones — missing jaw, leftEye, rightEye)
MB_LAB_BONES = [
    "pelvis",        # hips
    "spine",         # spine
    "spine_01",      # chest
    "spine_02",      # upperChest
    "neck",          # neck
    "head",          # head
    "clavicle_L",    # leftShoulder
    "upper_arm_L",   # leftUpperArm
    "forearm_L",     # leftLowerArm
    "hand_L",        # leftHand
    "clavicle_R",    # rightShoulder
    "upper_arm_R",   # rightUpperArm
    "forearm_R",     # rightLowerArm
    "hand_R",        # rightHand
    "thigh_L",       # leftUpperLeg
    "shin_L",        # leftLowerLeg
    "foot_L",        # leftFoot
    "toe_L",         # leftToes
    "thigh_R",       # rightUpperLeg
    "shin_R",        # rightLowerLeg
    "foot_R",        # rightFoot
    "toe_R",         # rightToes
]

# Count: MB-Lab has 22 naming convention bones
assert len(MB_LAB_BONES) == 22, f"Expected 22 MB-Lab bones, got {len(MB_LAB_BONES)}"

# Correct hierarchy for VRM 1.0 humanoid
CORRECT_VRM_HIERARCHY = {
    "hips": None,
    "spine": "hips",
    "chest": "spine",
    "upperChest": "chest",
    "neck": "upperChest",
    "head": "neck",
    "jaw": "head",
    "leftEye": "head",
    "rightEye": "head",
    "leftShoulder": "upperChest",
    "rightShoulder": "upperChest",
    "leftUpperArm": "leftShoulder",
    "rightUpperArm": "rightShoulder",
    "leftLowerArm": "leftUpperArm",
    "rightLowerArm": "rightUpperArm",
    "leftHand": "leftLowerArm",
    "rightHand": "rightLowerArm",
    "leftUpperLeg": "hips",
    "rightUpperLeg": "hips",
    "leftLowerLeg": "leftUpperLeg",
    "rightLowerLeg": "rightUpperLeg",
    "leftFoot": "leftLowerLeg",
    "rightFoot": "rightLowerLeg",
    "leftToes": "leftFoot",
    "rightToes": "rightFoot",
}


# ═══════════════════════════════════════════════════════════════════════════════
# verify_bone_list tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerifyBoneList:
    """Test pure-Python bone list verification against VRM_25_BONE_NAMES."""

    def test_full_25_bones_passes(self):
        """With all 25 VRM bone names, verification passes (no missing)."""
        report = verify_bone_list(ALL_VRM_BONES)
        assert report.bones_found == 25
        assert report.bones_missing == []
        assert report.is_valid is True

    def test_mb_lab_22_bones_reports_missing_jaw_eyes(self):
        """With 22 MB-Lab bone names, reports missing jaw, leftEye, rightEye."""
        report = verify_bone_list(MB_LAB_BONES)
        # MB-Lab names map to VRM names, but jaw/eyes are not in MB-Lab naming
        assert report.bones_found == 22
        assert "jaw" in report.bones_missing
        assert "leftEye" in report.bones_missing
        assert "rightEye" in report.bones_missing
        assert len(report.bones_missing) == 3

    def test_mb_lab_plus_stubs_passes(self):
        """MB-Lab 22 bones + jaw/eyes stubs = all 25 present."""
        bones = MB_LAB_BONES + ["jaw", "leftEye", "rightEye"]
        report = verify_bone_list(bones)
        assert report.bones_found == 25
        assert report.bones_missing == []
        assert report.is_valid is True

    def test_empty_list_reports_all_missing(self):
        """Empty bone list means all 25 are missing."""
        report = verify_bone_list([])
        assert report.bones_found == 0
        assert len(report.bones_missing) == 25
        assert report.is_valid is False

    def test_partial_bones_reports_missing(self):
        """A few bones present — reports which are missing."""
        report = verify_bone_list(["hips", "spine", "head"])
        assert report.bones_found == 3
        assert len(report.bones_missing) == 22
        assert report.is_valid is False

    def test_naming_issues_for_mb_lab_convention(self):
        """MB-Lab naming convention causes naming issues."""
        report = verify_bone_list(MB_LAB_BONES)
        assert len(report.naming_issues) > 0

    def test_no_naming_issues_for_vrm_convention(self):
        """VRM-convention names produce no naming issues."""
        report = verify_bone_list(ALL_VRM_BONES)
        assert report.naming_issues == []

    def test_quality_score_full_rig(self):
        """Full rig gets quality score near 1.0."""
        report = verify_bone_list(ALL_VRM_BONES)
        assert report.quality_score >= 0.99

    def test_quality_score_incomplete_rig(self):
        """Incomplete rig gets lower quality score."""
        report = verify_bone_list(["hips", "spine"])
        assert report.quality_score < 0.5

    def test_quality_score_empty_rig(self):
        """Empty rig scores 0.0."""
        report = verify_bone_list([])
        assert report.quality_score == 0.0

    def test_mb_lab_names_recognized(self):
        """MB-Lab bone names are recognized (not reported as missing)."""
        # hips → pelvis, chest → spine_01 should be found
        report = verify_bone_list(["pelvis", "spine", "spine_01", "spine_02"])
        # These map to hips, spine, chest, upperChest
        assert "hips" not in report.bones_missing
        assert "spine" not in report.bones_missing
        assert "chest" not in report.bones_missing
        assert "upperChest" not in report.bones_missing

    def test_duplicated_vrm_and_mb_lab_names(self):
        """Having both VRM and MB-Lab names doesn't double-count."""
        bones = ALL_VRM_BONES + MB_LAB_BONES
        report = verify_bone_list(bones)
        # Still found all 25 VRM bones
        assert report.bones_found == 25
        assert report.bones_missing == []


# ═══════════════════════════════════════════════════════════════════════════════
# check_hierarchy_graph tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckHierarchyGraph:
    """Test pure-Python hierarchy verification."""

    def test_correct_hierarchy_no_issues(self):
        """Correct VRM hierarchy produces no issues."""
        issues = check_hierarchy_graph(ALL_VRM_BONES, CORRECT_VRM_HIERARCHY)
        assert issues == []

    def test_wrong_parent_detected(self):
        """A bone with the wrong parent is flagged."""
        # spine parented to head instead of hips
        wrong_hierarchy = dict(CORRECT_VRM_HIERARCHY)
        wrong_hierarchy["spine"] = "head"
        issues = check_hierarchy_graph(ALL_VRM_BONES, wrong_hierarchy)
        assert len(issues) == 1
        assert "spine" in issues[0]
        assert "head" in issues[0]

    def test_head_parented_to_hips_wrong(self):
        """Head directly parented to hips (skipping neck) is flagged."""
        wrong_hierarchy = dict(CORRECT_VRM_HIERARCHY)
        wrong_hierarchy["head"] = "hips"
        issues = check_hierarchy_graph(ALL_VRM_BONES, wrong_hierarchy)
        assert any("head" in i for i in issues)

    def test_jaw_parented_to_hips_wrong(self):
        """Jaw parented to hips instead of head is flagged."""
        wrong_hierarchy = dict(CORRECT_VRM_HIERARCHY)
        wrong_hierarchy["jaw"] = "hips"
        issues = check_hierarchy_graph(ALL_VRM_BONES, wrong_hierarchy)
        assert any("jaw" in i for i in issues)

    def test_hips_with_parent_flagged(self):
        """Hips with a parent (should be root) is flagged."""
        wrong_hierarchy = dict(CORRECT_VRM_HIERARCHY)
        wrong_hierarchy["hips"] = "spine"
        issues = check_hierarchy_graph(ALL_VRM_BONES, wrong_hierarchy)
        assert any("hips" in i and "root" in i for i in issues)

    def test_missing_bone_not_checked(self):
        """Bones not in the bone_names list are skipped."""
        partial_bones = list(ALL_VRM_BONES)
        partial_bones.remove("jaw")
        issues = check_hierarchy_graph(partial_bones, CORRECT_VRM_HIERARCHY)
        # jaw is missing from the list, so it's not checked
        assert not any("jaw" in i for i in issues)

    def test_multiple_issues_detected(self):
        """Multiple hierarchy issues are all detected."""
        wrong_hierarchy = dict(CORRECT_VRM_HIERARCHY)
        wrong_hierarchy["spine"] = "head"  # should be hips
        wrong_hierarchy["jaw"] = "hips"  # should be head
        issues = check_hierarchy_graph(ALL_VRM_BONES, wrong_hierarchy)
        assert len(issues) == 2

    def test_eyes_must_be_parented_to_head(self):
        """Eyes must be parented to head."""
        wrong_hierarchy = dict(CORRECT_VRM_HIERARCHY)
        wrong_hierarchy["leftEye"] = "neck"
        wrong_hierarchy["rightEye"] = "neck"
        issues = check_hierarchy_graph(ALL_VRM_BONES, wrong_hierarchy)
        assert any("leftEye" in i for i in issues)
        assert any("rightEye" in i for i in issues)

    def test_empty_parent_map_no_crashes(self):
        """Empty parent map doesn't crash — all bones flagged as issues."""
        empty_map: dict[str, str] = {}
        issues = check_hierarchy_graph(ALL_VRM_BONES, empty_map)
        # All bones except hips (which should be root) have issues
        # hips: expected parent=None, actual parent=None (not in map → None)
        # So hips is OK, but everything else is wrong
        assert len(issues) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# RigReport dataclass tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRigReport:
    """Test RigReport dataclass and its methods."""

    def test_rig_report_fields(self):
        """RigReport has all required fields."""
        report = RigReport(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=[],
            naming_issues=[],
            quality_score=1.0,
        )
        assert report.bones_found == 25
        assert report.bones_missing == []
        assert report.hierarchy_issues == []
        assert report.naming_issues == []
        assert report.quality_score == 1.0

    def test_rig_report_is_valid_true(self):
        """Valid rig: no missing bones, no hierarchy issues."""
        report = RigReport(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=[],
            naming_issues=[],
            quality_score=1.0,
        )
        assert report.is_valid is True

    def test_rig_report_is_valid_false_missing(self):
        """Invalid rig: missing bones."""
        report = RigReport(
            bones_found=22,
            bones_missing=["jaw", "leftEye", "rightEye"],
            hierarchy_issues=[],
            naming_issues=[],
            quality_score=0.88,
        )
        assert report.is_valid is False

    def test_rig_report_is_valid_false_hierarchy(self):
        """Invalid rig: hierarchy issues."""
        report = RigReport(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=["spine has wrong parent"],
            naming_issues=[],
            quality_score=0.9,
        )
        assert report.is_valid is False

    def test_rig_report_is_valid_false_both(self):
        """Invalid rig: both missing and hierarchy issues."""
        report = RigReport(
            bones_found=22,
            bones_missing=["jaw"],
            hierarchy_issues=["head parent wrong"],
            naming_issues=["pelvis non-standard"],
            quality_score=0.7,
        )
        assert report.is_valid is False

    def test_rig_report_summary(self):
        """summary() produces human-readable output."""
        report = RigReport(
            bones_found=22,
            bones_missing=["jaw", "leftEye", "rightEye"],
            hierarchy_issues=[],
            naming_issues=["pelvis uses non-standard name"],
            quality_score=0.88,
        )
        text = report.summary()
        assert "22/25" in text
        assert "jaw" in text
        assert "0.88" in text
        assert "NO" in text

    def test_rig_report_summary_valid(self):
        """summary() shows YES for valid rig."""
        report = RigReport(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=[],
            naming_issues=[],
            quality_score=1.0,
        )
        text = report.summary()
        assert "YES" in text
        assert "25/25" in text

    def test_rig_report_default_fields(self):
        """RigReport defaults empty lists."""
        report = RigReport(bones_found=0)
        assert report.bones_missing == []
        assert report.hierarchy_issues == []
        assert report.naming_issues == []
        assert report.quality_score == 0.0

    def test_rig_report_naming_issues_in_summary(self):
        """Naming issues appear in summary."""
        report = RigReport(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=[],
            naming_issues=["pelvis uses non-standard name"],
            quality_score=0.92,
        )
        text = report.summary()
        assert "pelvis" in text

    def test_rig_report_hierarchy_issues_in_summary(self):
        """Hierarchy issues appear in summary."""
        report = RigReport(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=["spine has parent 'head' but expected 'hips'"],
            naming_issues=[],
            quality_score=0.92,
        )
        text = report.summary()
        assert "spine" in text


# ═══════════════════════════════════════════════════════════════════════════════
# Naming conventions tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNamingConventions:
    """Test VRM vs MB-Lab naming convention detection."""

    def test_vrm_names_no_issues(self):
        """VRM-standard names produce no naming issues."""
        issues = check_naming_conventions_pure(ALL_VRM_BONES)
        assert issues == []

    def test_mb_lab_names_flagged(self):
        """MB-Lab naming convention bones are flagged as non-standard."""
        issues = check_naming_conventions_pure(MB_LAB_BONES)
        assert len(issues) > 0
        assert any("pelvis" in i for i in issues)

    def test_mixed_names_flagged(self):
        """Mixed VRM and MB-Lab names — MB-Lab names flagged when VRM equivalent is missing."""
        # When "hips" IS present, "pelvis" is an extra/unknown bone, not a naming issue
        # When "hips" is NOT present but "pelvis" IS, it's flagged as non-standard
        mixed = ["spine", "spine_01", "head", "neck"]
        # "spine_01" maps to "chest" which is NOT in the list → flagged
        issues = check_naming_conventions_pure(mixed)
        assert any("spine_01" in i for i in issues)

    def test_mb_lab_flagged_only_when_vrm_missing(self):
        """MB-Lab name is flagged as non-standard only when VRM name is absent."""
        # When VRM "hips" is present, MB-Lab "pelvis" is just an extra bone
        both_present = ["hips", "pelvis", "spine", "head"]
        issues = check_naming_conventions_pure(both_present)
        assert not any("pelvis" in i and "non-standard" in i for i in issues)

        # When VRM "hips" is absent, "pelvis" IS flagged
        only_mblab = ["pelvis", "spine", "head", "neck"]
        issues = check_naming_conventions_pure(only_mblab)
        assert any("pelvis" in i for i in issues)

    def test_thigh_flagged_as_nonstandard(self):
        """MB-Lab 'thigh_L' is flagged as non-standard for 'leftUpperLeg'."""
        issues = check_naming_conventions_pure(["thigh_L"])
        assert any("thigh_L" in i and "leftUpperLeg" in i for i in issues)

    def test_unknown_bones_flagged(self):
        """Unknown bones are flagged."""
        issues = check_naming_conventions_pure(["weird_bone_42"])
        assert any("weird_bone_42" in i for i in issues)

    def test_empty_list_no_crash(self):
        """Empty bone list produces no issues."""
        issues = check_naming_conventions_pure([])
        # No VRM names missing, no MB-Lab names flagged
        assert issues == []


# ═══════════════════════════════════════════════════════════════════════════════
# generate_rig_report tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateRigReport:
    """Test the generate_rig_report factory function."""

    def test_generate_report_full(self):
        """Full report generated correctly."""
        report = generate_rig_report(
            bones_found=25,
            bones_missing=[],
            hierarchy_issues=[],
            naming_issues=[],
        )
        assert report.bones_found == 25
        assert report.bones_missing == []
        assert report.hierarchy_issues == []
        assert report.naming_issues == []
        assert report.is_valid is True
        assert report.quality_score >= 0.99

    def test_generate_report_with_issues(self):
        """Report with issues has correct quality score."""
        report = generate_rig_report(
            bones_found=22,
            bones_missing=["jaw", "leftEye", "rightEye"],
            hierarchy_issues=["spine parent wrong"],
            naming_issues=["pelvis non-standard"],
        )
        assert report.bones_found == 22
        assert len(report.bones_missing) == 3
        assert len(report.hierarchy_issues) == 1
        assert len(report.naming_issues) == 1
        assert report.is_valid is False
        assert 0.0 < report.quality_score < 1.0

    def test_generate_report_quality_score_calculation(self):
        """Quality score reflects completeness and issue count."""
        # 22/25 bones, 1 hierarchy issue, 1 naming issue
        report = generate_rig_report(
            bones_found=22,
            bones_missing=["jaw", "leftEye", "rightEye"],
            hierarchy_issues=["spine parent wrong"],
            naming_issues=["pelvis non-standard"],
        )
        # completeness = 22/25 = 0.88, hierarchy = 0.8, naming = 0.8
        # score = 0.6*0.88 + 0.3*0.8 + 0.1*0.8 = 0.528 + 0.24 + 0.08 = 0.848
        expected = 0.6 * (22 / 25) + 0.3 * 0.8 + 0.1 * 0.8
        assert abs(report.quality_score - expected) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# VRM_BONE_HIERARCHY constant tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestVRMBoneHierarchy:
    """Verify the VRM_BONE_HIERARCHY constant is consistent."""

    def test_hierarchy_has_all_25_bones(self):
        """The hierarchy covers all 25 VRM bones."""
        assert len(VRM_BONE_HIERARCHY) == 25

    def test_hierarchy_matches_vrm_25_names(self):
        """Hierarchy keys match VRM_25_BONE_NAMES exactly."""
        assert set(VRM_BONE_HIERARCHY.keys()) == set(VRM_25_BONE_NAMES)

    def test_hips_is_root(self):
        """Hips has no parent (root bone)."""
        assert VRM_BONE_HIERARCHY["hips"] is None

    def test_head_parent_is_neck(self):
        """Head parent is neck."""
        assert VRM_BONE_HIERARCHY["head"] == "neck"

    def test_jaw_and_eyes_parented_to_head(self):
        """Jaw, leftEye, rightEye are all parented to head."""
        assert VRM_BONE_HIERARCHY["jaw"] == "head"
        assert VRM_BONE_HIERARCHY["leftEye"] == "head"
        assert VRM_BONE_HIERARCHY["rightEye"] == "head"

    def test_spine_chain(self):
        """Spine chain: hips → spine → chest → upperChest."""
        assert VRM_BONE_HIERARCHY["spine"] == "hips"
        assert VRM_BONE_HIERARCHY["chest"] == "spine"
        assert VRM_BONE_HIERARCHY["upperChest"] == "chest"

    def test_leg_chain(self):
        """Left leg chain: hips → leftUpperLeg → leftLowerLeg → leftFoot → leftToes."""
        assert VRM_BONE_HIERARCHY["leftUpperLeg"] == "hips"
        assert VRM_BONE_HIERARCHY["leftLowerLeg"] == "leftUpperLeg"
        assert VRM_BONE_HIERARCHY["leftFoot"] == "leftLowerLeg"
        assert VRM_BONE_HIERARCHY["leftToes"] == "leftFoot"

    def test_arm_chain(self):
        """Left arm chain: upperChest → leftShoulder → leftUpperArm → leftLowerArm → leftHand."""
        assert VRM_BONE_HIERARCHY["leftShoulder"] == "upperChest"
        assert VRM_BONE_HIERARCHY["leftUpperArm"] == "leftShoulder"
        assert VRM_BONE_HIERARCHY["leftLowerArm"] == "leftUpperArm"
        assert VRM_BONE_HIERARCHY["leftHand"] == "leftLowerArm"

    def test_no_self_parenting(self):
        """No bone lists itself as its own parent."""
        for bone, parent in VRM_BONE_HIERARCHY.items():
            if parent is not None:
                assert bone != parent, f"Bone {bone} is its own parent"

    def test_all_parents_are_valid_bones(self):
        """Every parent reference points to a valid VRM bone (or None for hips)."""
        vrm_set = set(VRM_25_BONE_NAMES)
        for bone, parent in VRM_BONE_HIERARCHY.items():
            if parent is not None:
                assert parent in vrm_set, f"Parent '{parent}' of '{bone}' not in VRM_25_BONE_NAMES"


# ═══════════════════════════════════════════════════════════════════════════════
# MB_LAB_NAMES_TO_VRM mapping tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestMBLabNamesToVRM:
    """Test the MB_LAB_NAMES_TO_VRM mapping constant."""

    def test_mapping_has_entries(self):
        """The mapping has entries for MB-Lab bone names."""
        assert len(MB_LAB_NAMES_TO_VRM) > 0

    def test_all_vrm_targets_are_valid(self):
        """Every VRM target in the mapping is a valid VRM bone name."""
        vrm_set = set(VRM_25_BONE_NAMES)
        for mb_name, vrm_name in MB_LAB_NAMES_TO_VRM.items():
            assert vrm_name in vrm_set, f"VRM target '{vrm_name}' for '{mb_name}' not valid"

    def test_pelvis_maps_to_hips(self):
        """pelvis → hips mapping is present."""
        assert MB_LAB_NAMES_TO_VRM["pelvis"] == "hips"

    def test_spine_01_maps_to_chest(self):
        """spine_01 → chest mapping is present."""
        assert MB_LAB_NAMES_TO_VRM["spine_01"] == "chest"


# ═══════════════════════════════════════════════════════════════════════════════
# cmd_verify_rig tests (pure-Python, no Blender)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCmdVerifyRig:
    """Test the CLI command function (pure-Python paths only)."""

    def test_cmd_verify_rig_missing_file(self, tmp_path):
        """cmd_verify_rig returns error report for missing spec file."""
        report = cmd_verify_rig(str(tmp_path / "nonexistent.json"))
        assert report.bones_found == 0
        assert len(report.bones_missing) == 25
        assert not report.is_valid

    def test_cmd_verify_rig_json_spec(self, tmp_path):
        """cmd_verify_rig reads JSON spec with armature_name and bone_names."""
        import json
        spec = {
            "armature_name": "Armature",
            "bone_names": ALL_VRM_BONES,
        }
        spec_path = tmp_path / "rig_spec.json"
        spec_path.write_text(json.dumps(spec))

        report = cmd_verify_rig(str(spec_path))
        assert report.bones_found == 25
        assert report.bones_missing == []

    def test_cmd_verify_rig_partial_bones(self, tmp_path):
        """cmd_verify_rig with partial bone list reports missing."""
        import json
        spec = {
            "armature_name": "Armature",
            "bone_names": MB_LAB_BONES,
        }
        spec_path = tmp_path / "partial_spec.json"
        spec_path.write_text(json.dumps(spec))

        report = cmd_verify_rig(str(spec_path))
        assert report.bones_found == 22
        assert len(report.bones_missing) == 3
        assert "jaw" in report.bones_missing

    def test_cmd_verify_rig_text_format(self, tmp_path):
        """cmd_verify_rig reads plain-text spec (armature name on first line)."""
        # Without bpy, this will produce a report with bone_names from spec
        # or an empty report if no bone_names key
        spec_path = tmp_path / "rig_name.txt"
        spec_path.write_text("Armature\n")

        # Without Blender, this returns an empty/default report since no
        # bone_names are in the spec
        report = cmd_verify_rig(str(spec_path))
        # Should still return a report (even if empty)
        assert isinstance(report, RigReport)


# ═══════════════════════════════════════════════════════════════════════════════
# Blender-dependent tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.blender
class TestRigVerifierBlender:
    """Blender-dependent tests for the RigVerifier class.

    These tests require bpy and a running Blender instance.
    They only run when Blender is available.
    """

    def test_rig_verifier_requires_blender(self):
        """RigVerifier.verify() raises RuntimeError without bpy."""
        verifier = RigVerifier()
        try:
            import bpy
            # If bpy is available, we skip this test
            pytest.skip("bpy available — cannot test RuntimeError path")
        except ImportError:
            with pytest.raises(RuntimeError, match="bpy not available"):
                verifier.verify("Armature")

    def test_check_bone_count_requires_blender(self):
        """RigVerifier.check_bone_count() raises RuntimeError without bpy."""
        verifier = RigVerifier()
        try:
            import bpy
            pytest.skip("bpy available — cannot test RuntimeError path")
        except ImportError:
            with pytest.raises(RuntimeError, match="bpy not available"):
                verifier.check_bone_count("Armature")

    def test_check_naming_conventions_requires_blender(self):
        """RigVerifier.check_naming_conventions() raises RuntimeError without bpy."""
        verifier = RigVerifier()
        try:
            import bpy
            pytest.skip("bpy available — cannot test RuntimeError path")
        except ImportError:
            with pytest.raises(RuntimeError, match="bpy not available"):
                verifier.check_naming_conventions("Armature")

    def test_check_hierarchy_requires_blender(self):
        """RigVerifier.check_hierarchy() raises RuntimeError without bpy."""
        verifier = RigVerifier()
        try:
            import bpy
            pytest.skip("bpy available — cannot test RuntimeError path")
        except ImportError:
            with pytest.raises(RuntimeError, match="bpy not available"):
                verifier.check_hierarchy("Armature")

    def test_rig_verifier_missing_armature(self):
        """RigVerifier returns error report for nonexistent armature."""
        # This test is Blender-dependent
        try:
            import bpy
        except ImportError:
            pytest.skip("bpy not available")
            return

        verifier = RigVerifier()
        report = verifier.verify("NonExistentArmature")
        assert report.bones_found == 0
        assert len(report.bones_missing) == 25