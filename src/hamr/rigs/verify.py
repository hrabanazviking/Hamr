"""
Rig Verification — Bone count, naming, and hierarchy checks for VRM 1.0 rigs.

Every bone accounted for. Every name true. Every parentage correct.
The forge inspects before it ships.

Phase 11 T5: Rig Verifier — bone count, naming, hierarchy checks.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hamr.core.constants import VRM_25_BONE_NAMES

logger = logging.getLogger("hamr.rigs.verify")

try:
    import bpy  # type: ignore

    BLENDER_AVAILABLE = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    BLENDER_AVAILABLE = False


# ── Canonical VRM 1.0 hierarchy ──────────────────────────────────────────
# Maps each VRM bone to its expected parent bone in the humanoid rig.
# "hips" is the root — no parent.
VRM_BONE_HIERARCHY: dict[str, str | None] = {
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

# VRM bone naming convention: VRM allows camelCase only.
# These are the exact canonical names. Any deviation is a naming issue.
VRM_CANONICAL_NAMES: set[str] = set(VRM_25_BONE_NAMES)

# Common MB-Lab / Blender naming that VRM considers non-standard
MB_LAB_NAMES_TO_VRM: dict[str, str] = {
    "pelvis": "hips",
    "spine_01": "chest",
    "spine_02": "upperChest",
    "spine_03": "upperChest",
    "clavicle_L": "leftShoulder",
    "clavicle_R": "rightShoulder",
    "upper_arm_L": "leftUpperArm",
    "upper_arm_R": "rightUpperArm",
    "forearm_L": "leftLowerArm",
    "forearm_R": "rightLowerArm",
    "hand_L": "leftHand",
    "hand_R": "rightHand",
    "thigh_L": "leftUpperLeg",
    "thigh_R": "rightUpperLeg",
    "shin_L": "leftLowerLeg",
    "shin_R": "rightLowerLeg",
    "foot_L": "leftFoot",
    "foot_R": "rightFoot",
    "toe_L": "leftToes",
    "toe_R": "rightToes",
}


# ── RigReport dataclass ────────────────────────────────────────────────────

@dataclass
class RigReport:
    """Verification report for a rig's VRM 1.0 compliance.

    Every measurement, every deviation, every missing bone — recorded.
    The quality score is a 0–1 float derived from the weights module's
    scoring approach adapted for rig completeness.
    """

    bones_found: int
    bones_missing: list[str] = field(default_factory=list)
    hierarchy_issues: list[str] = field(default_factory=list)
    naming_issues: list[str] = field(default_factory=list)
    quality_score: float = 0.0

    @property
    def is_valid(self) -> bool:
        """A rig is valid if it has all 25 bones and no hierarchy issues."""
        return len(self.bones_missing) == 0 and len(self.hierarchy_issues) == 0

    def summary(self) -> str:
        """Human-readable summary of the rig verification report."""
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("RIG VERIFICATION REPORT")
        lines.append("=" * 60)
        lines.append(f"  Bones found:    {self.bones_found}/25")
        lines.append(f"  Bones missing:  {len(self.bones_missing)}")
        if self.bones_missing:
            for b in self.bones_missing:
                lines.append(f"    - {b}")
        lines.append(f"  Hierarchy issues: {len(self.hierarchy_issues)}")
        if self.hierarchy_issues:
            for issue in self.hierarchy_issues:
                lines.append(f"    - {issue}")
        lines.append(f"  Naming issues:   {len(self.naming_issues)}")
        if self.naming_issues:
            for issue in self.naming_issues:
                lines.append(f"    - {issue}")
        lines.append(f"  Quality score:   {self.quality_score:.2f}")
        lines.append(f"  Valid:           {'YES' if self.is_valid else 'NO'}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ── Pure-Python verification functions (no bpy) ────────────────────────────

def verify_bone_list(bone_names: list[str]) -> RigReport:
    """Check if a list of bone names contains all 25 VRM-required bones.

    Pure-Python function — does not require Blender.

    Cross-references bone names against VRM_25_BONE_NAMES and the
    MB_LAB_NAMES_TO_VRM mapping to detect bones present under
    non-standard (MB-Lab) naming.

    Args:
        bone_names: List of bone names to verify.

    Returns:
        RigReport with bones_found, bones_missing, naming_issues, and score.
    """
    bone_set = set(bone_names)
    vrm_set = set(VRM_25_BONE_NAMES)

    # Which VRM-required bones are directly present
    directly_found = vrm_set & bone_set

    # Which bones are present only via MB-Lab naming
    mb_lab_found: set[str] = set()
    naming_issues: list[str] = []

    for mb_name, vrm_name in MB_LAB_NAMES_TO_VRM.items():
        if mb_name in bone_set and vrm_name not in bone_set:
            mb_lab_found.add(vrm_name)
            naming_issues.append(
                f"Bone '{mb_name}' found but uses non-VRM name; "
                f"expected '{vrm_name}'"
            )

    # All found bones (either directly or via MB-Lab mapping)
    all_found = directly_found | mb_lab_found

    # Missing bones
    bones_missing = sorted(vrm_set - all_found)

    # Bones found count
    bones_found = len(all_found)

    # Quality score: based on how complete the bone list is
    quality_score = _compute_rig_quality_score(
        bones_found=bones_found,
        bones_missing=bones_missing,
        hierarchy_issues=[],
        naming_issues=naming_issues,
    )

    return RigReport(
        bones_found=bones_found,
        bones_missing=bones_missing,
        hierarchy_issues=[],
        naming_issues=naming_issues,
        quality_score=quality_score,
    )


def check_hierarchy_graph(
    bone_names: list[str],
    parent_map: dict[str, str],
) -> list[str]:
    """Verify parent-child relationships in a bone hierarchy.

    Pure-Python function — does not require Blender.

    Checks each bone in bone_names against the VRM_BONE_HIERARCHY
    to verify that the parent is correct. Bones not in the VRM
    hierarchy are skipped (extra bones are not flagged).

    Args:
        bone_names: List of bone names in the armature.
        parent_map: Dict mapping bone name → parent bone name.
                    Use empty string or None for root bones.

    Returns:
        List of human-readable hierarchy issue strings.
    """
    bone_set = set(bone_names)
    issues: list[str] = []

    for vrm_bone, expected_parent in VRM_BONE_HIERARCHY.items():
        if vrm_bone not in bone_set:
            # Bone itself is missing — that's a count issue, not hierarchy
            continue

        actual_parent = parent_map.get(vrm_bone)

        # Normalize None/empty to None
        if actual_parent is not None and actual_parent == "":
            actual_parent = None

        if expected_parent is None:
            # Root bone (hips) should have no parent
            if actual_parent is not None:
                issues.append(
                    f"Bone '{vrm_bone}' has parent '{actual_parent}' "
                    f"but should be root (no parent)"
                )
        else:
            if actual_parent != expected_parent:
                issues.append(
                    f"Bone '{vrm_bone}' has parent '{actual_parent}' "
                    f"but expected '{expected_parent}'"
                )

    return issues


def check_naming_conventions_pure(bone_names: list[str]) -> list[str]:
    """Check bone names against VRM naming conventions.

    Pure-Python function — does not require Blender.

    Flags bones that are present under non-VRM naming conventions
    (e.g., MB-Lab naming like 'pelvis' instead of 'hips').

    Args:
        bone_names: List of bone names to check.

    Returns:
        List of naming issue strings.
    """
    bone_set = set(bone_names)
    vrm_set = set(VRM_25_BONE_NAMES)
    issues: list[str] = []

    # Check for bones present only under MB-Lab names
    for mb_name, vrm_name in MB_LAB_NAMES_TO_VRM.items():
        if mb_name in bone_set and vrm_name not in bone_set:
            issues.append(
                f"Bone '{mb_name}' uses non-standard name; "
                f"VRM expects '{vrm_name}'"
            )

    # Check for bones in the list that aren't in VRM or MB-Lab naming
    known_names = vrm_set | set(MB_LAB_NAMES_TO_VRM.keys())
    # Also add common variants
    known_names |= {"spine", "neck", "head", "jaw"}
    unknown = bone_set - known_names
    # Don't flag extra bones too harshly — just note them
    for name in sorted(unknown):
        issues.append(f"Unknown bone '{name}' not in VRM or MB-Lab naming")

    return issues


def generate_rig_report(
    bones_found: int,
    bones_missing: list[str],
    hierarchy_issues: list[str],
    naming_issues: list[str],
) -> RigReport:
    """Generate a RigReport from individual verification results.

    Pure-Python function — does not require Blender.

    Args:
        bones_found: Number of VRM-required bones found.
        bones_missing: List of missing VRM bone names.
        hierarchy_issues: List of hierarchy problem descriptions.
        naming_issues: List of naming convention problem descriptions.

    Returns:
        RigReport with computed quality_score and is_valid flag.
    """
    quality_score = _compute_rig_quality_score(
        bones_found=bones_found,
        bones_missing=bones_missing,
        hierarchy_issues=hierarchy_issues,
        naming_issues=naming_issues,
    )

    return RigReport(
        bones_found=bones_found,
        bones_missing=bones_missing,
        hierarchy_issues=hierarchy_issues,
        naming_issues=naming_issues,
        quality_score=quality_score,
    )


def _compute_rig_quality_score(
    bones_found: int,
    bones_missing: list[str],
    hierarchy_issues: list[str],
    naming_issues: list[str],
) -> float:
    """Compute a 0–1 quality score for rig completeness.

    Scoring weights:
      - Bone completeness: 0.6 × (bones_found / 25)
      - Hierarchy correctness: 0.3 × (1.0 if no issues, else max(0, 1 - 0.2 * issue_count))
      - Naming conventions: 0.1 × (1.0 if no issues, else max(0, 1 - 0.2 * issue_count))
    """
    if bones_found == 0:
        return 0.0

    # Bone completeness score
    completeness = bones_found / 25.0
    completeness_score = min(completeness, 1.0)

    # Hierarchy score
    if not hierarchy_issues:
        hierarchy_score = 1.0
    else:
        hierarchy_score = max(0.0, 1.0 - 0.2 * len(hierarchy_issues))

    # Naming score
    if not naming_issues:
        naming_score = 1.0
    else:
        naming_score = max(0.0, 1.0 - 0.2 * len(naming_issues))

    return (
        0.6 * completeness_score
        + 0.3 * hierarchy_score
        + 0.1 * naming_score
    )


# ── Blender-dependent verification ─────────────────────────────────────────

class RigVerifier:
    """Verify an armature's VRM 1.0 compliance inside Blender.

    Each method requires bpy and a valid armature in the scene.
    Use the pure-Python functions (verify_bone_list, check_hierarchy_graph,
    etc.) for offline analysis without Blender.
    """

    def verify(self, armature_name: str) -> RigReport:
        """Full verification of an armature: bones, naming, hierarchy.

        Args:
            armature_name: Name of the armature object in Blender.

        Returns:
            RigReport with all findings.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError("bpy not available — verify() must run inside Blender")

        count_report = self.check_bone_count(armature_name)
        naming_issues = self.check_naming_conventions(armature_name)
        hierarchy_issues = self.check_hierarchy(armature_name)

        return generate_rig_report(
            bones_found=count_report.bones_found,
            bones_missing=count_report.bones_missing,
            hierarchy_issues=hierarchy_issues,
            naming_issues=naming_issues,
        )

    def check_bone_count(self, armature_name: str) -> RigReport:
        """Verify that the armature has all 25 VRM-required bones.

        Args:
            armature_name: Name of the armature object in Blender.

        Returns:
            RigReport with bones_found and bones_missing populated.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError("bpy not available — check_bone_count() must run inside Blender")

        armature = bpy.data.objects.get(armature_name)
        if armature is None or armature.type != "ARMATURE":
            logger.error(f"Armature '{armature_name}' not found or not an armature")
            return RigReport(
                bones_found=0,
                bones_missing=list(VRM_25_BONE_NAMES),
                hierarchy_issues=[],
                naming_issues=[],
                quality_score=0.0,
            )

        existing_bones = {b.name for b in armature.data.bones}
        return verify_bone_list(list(existing_bones))

    def check_naming_conventions(self, armature_name: str) -> list[str]:
        """Verify bone names match the VRM 1.0 spec.

        Args:
            armature_name: Name of the armature object in Blender.

        Returns:
            List of naming convention issue strings.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError("bpy not available — check_naming_conventions() must run inside Blender")

        armature = bpy.data.objects.get(armature_name)
        if armature is None or armature.type != "ARMATURE":
            logger.error(f"Armature '{armature_name}' not found or not an armature")
            return [f"Armature '{armature_name}' not found or not an armature"]

        existing_bones = [b.name for b in armature.data.bones]
        return check_naming_conventions_pure(existing_bones)

    def check_hierarchy(self, armature_name: str) -> list[str]:
        """Verify bone parenting matches the VRM 1.0 humanoid hierarchy.

        Args:
            armature_name: Name of the armature object in Blender.

        Returns:
            List of hierarchy issue strings.

        Raises:
            RuntimeError: If bpy is not available.
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError("bpy not available — check_hierarchy() must run inside Blender")

        armature = bpy.data.objects.get(armature_name)
        if armature is None or armature.type != "ARMATURE":
            logger.error(f"Armature '{armature_name}' not found or not an armature")
            return [f"Armature '{armature_name}' not found or not an armature"]

        bone_names: list[str] = []
        parent_map: dict[str, str] = {}

        for bone in armature.data.bones:
            bone_names.append(bone.name)
            parent_bone = bone.parent
            if parent_bone is not None:
                parent_map[bone.name] = parent_bone.name
            else:
                parent_map[bone.name] = None  # type: ignore[assignment]

        return check_hierarchy_graph(bone_names, parent_map)


# ── CLI command support ────────────────────────────────────────────────────

def cmd_verify_rig(spec_path: str) -> RigReport:
    """CLI-friendly verification: load a spec, verify the rig, print report.

    The spec file is a JSON file with an "armature_name" key, or a
    plain text file containing just the armature name on the first line.

    Args:
        spec_path: Path to the spec file (JSON or text).

    Returns:
        RigReport with findings.
    """
    spec_file = Path(spec_path)
    if not spec_file.exists():
        logger.error(f"Spec file not found: {spec_path}")
        print(f"ERROR: Spec file not found: {spec_path}")
        return RigReport(
            bones_found=0,
            bones_missing=list(VRM_25_BONE_NAMES),
            hierarchy_issues=[f"Spec file not found: {spec_path}"],
            naming_issues=[],
            quality_score=0.0,
        )

    armature_name: str | None = None

    # Try JSON format first
    try:
        with open(spec_file, "r") as f:
            data = json.load(f)
            armature_name = data.get("armature_name")
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Fall back to plain text — first line is the armature name
        with open(spec_file, "r") as f:
            armature_name = f.readline().strip()
    except Exception as exc:
        logger.error(f"Failed to read spec file: {exc}")
        print(f"ERROR: Failed to read spec file: {exc}")
        return RigReport(
            bones_found=0,
            bones_missing=list(VRM_25_BONE_NAMES),
            hierarchy_issues=[f"Failed to read spec: {exc}"],
            naming_issues=[],
            quality_score=0.0,
        )

    if not armature_name:
        logger.error("No armature_name found in spec file")
        print("ERROR: No armature_name found in spec file")
        return RigReport(
            bones_found=0,
            bones_missing=list(VRM_25_BONE_NAMES),
            hierarchy_issues=["No armature_name in spec"],
            naming_issues=[],
            quality_score=0.0,
        )

    # If running inside Blender, use the full verifier
    if BLENDER_AVAILABLE:
        verifier = RigVerifier()
        report = verifier.verify(armature_name)
    else:
        # Without Blender, we can only verify a bone list if provided
        # Check if the spec has a bone_names list for offline use
        try:
            with open(spec_file, "r") as f:
                data = json.load(f)
                spec_bones = data.get("bone_names", [])
        except Exception:
            spec_bones = []

        if spec_bones:
            report = verify_bone_list(spec_bones)
        else:
            logger.warning(
                "No Blender context and no bone_names in spec — "
                "returning empty report"
            )
            report = RigReport(
                bones_found=0,
                bones_missing=list(VRM_25_BONE_NAMES),
                hierarchy_issues=["No Blender context and no bone_names in spec"],
                naming_issues=[],
                quality_score=0.0,
            )

    # Print the report
    print(report.summary())
    return report


def verify_vrm_rig(path: str) -> dict:
    """Pure-Python VRM rig verification — reads a GLB/VRM file off disk.

    Extracts bone names from the glTF JSON chunk and runs verify_bone_list
    on them. Does NOT require Blender.

    Args:
        path: Path to a VRM or GLB file.

    Returns:
        Dict with keys:
          - "valid": bool — True if all 25 VRM bones are present with no
            hierarchy issues.
          - "bones_found": int — number of VRM bones found.
          - "bones_missing": list[str] — missing VRM bone names.
          - "naming_issues": list[str] — naming convention problems.
          - "quality_score": float — 0–1 quality score.
          - "report": RigReport — the full report object.
    """
    import struct

    vrm_path = Path(path)
    if not vrm_path.exists():
        raise FileNotFoundError(f"VRM file not found: {path}")

    bone_names: list[str] = _extract_bone_names_from_glb(vrm_path)

    if not bone_names:
        # No bones found — return an invalid report
        report = RigReport(
            bones_found=0,
            bones_missing=list(VRM_25_BONE_NAMES),
            hierarchy_issues=["No bones found in file"],
            naming_issues=[],
            quality_score=0.0,
        )
        return {
            "valid": False,
            "bones_found": 0,
            "bones_missing": list(VRM_25_BONE_NAMES),
            "naming_issues": [],
            "quality_score": 0.0,
            "report": report,
        }

    report = verify_bone_list(bone_names)

    return {
        "valid": report.is_valid,
        "bones_found": report.bones_found,
        "bones_missing": report.bones_missing,
        "naming_issues": report.naming_issues,
        "quality_score": report.quality_score,
        "report": report,
    }


def _extract_bone_names_from_glb(path: Path) -> list[str]:
    """Extract bone (node) names from a GLB/VRM binary file.

    Reads the JSON chunk of the glTF format and finds nodes referenced
    by skin joints — these are the bones.

    Args:
        path: Path to a GLB/VRM file.

    Returns:
        List of bone names found in the file.
    """
    bone_names: list[str] = []

    try:
        with open(path, "rb") as f:
            # Read the GLB header: magic (4) + version (4) + length (4)
            magic = f.read(4)
            if magic != b"glTF":
                return []

            _version = f.read(4)  # version
            _total_length = f.read(4)  # total file length

            # Read chunks until we find JSON
            while True:
                chunk_length_bytes = f.read(4)
                if not chunk_length_bytes:
                    break

                chunk_length = int.from_bytes(chunk_length_bytes, "little")
                chunk_type = f.read(4)

                if chunk_type == b"JSON":
                    json_data = f.read(chunk_length).decode("utf-8", errors="replace")
                    gltf = json.loads(json_data)

                    nodes = gltf.get("nodes", [])
                    skins = gltf.get("skins", [])

                    # Extract bone names from skin joints
                    seen_joints = set()
                    for skin in skins:
                        for joint_idx in skin.get("joints", []):
                            if 0 <= joint_idx < len(nodes) and joint_idx not in seen_joints:
                                name = nodes[joint_idx].get("name", "")
                                if name:
                                    bone_names.append(name)
                                seen_joints.add(joint_idx)

                    # If no skins, try all nodes that look like bones
                    if not bone_names:
                        for node in nodes:
                            name = node.get("name", "")
                            if name and name[0].isupper():
                                bone_names.append(name)

                    break  # We only need the JSON chunk
                else:
                    # Skip binary chunk
                    f.read(chunk_length)

    except Exception:
        pass

    return bone_names