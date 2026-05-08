"""
VRM 1.0 Compliance Validator — glTF schema + VRM extension checks.

A standalone, pure-Python validator that checks VRM files for spec compliance.
No bpy dependency — reads glTF JSON directly from VRM binary chunks.

Every bone accounted for. Every extension checked. Every mesh inspected.
The forge inspects before it ships.

Phase 13 T3: VRM 1.0 validator — glTF compliance, bone coverage,
expression checks, binary parsing.
"""

from __future__ import annotations

import json
import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hamr.core.constants import VRM_25_BONE_NAMES

logger = logging.getLogger("hamr.export.vrm_validator")

# ── glTF 2.0 constants ──────────────────────────────────────────────────────
GLTF_MAGIC = b"glTF"       # First 4 bytes of a valid glTF binary
GLTF_VERSION_2 = 2          # glTF 2.0 spec version

# VRM extension names
VRM_0X_EXTENSION = "VRM"
VRM_1X_EXTENSION = "VRMC_vrm"

# ── VRMValidationResult dataclass ────────────────────────────────────────────

@dataclass
class VRMValidationResult:
    """Structured result of a VRM 1.0 compliance check.

    Every measurement, every deviation, every missing bone — recorded.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bone_coverage: float = 0.0   # percentage of 25 required bones found
    material_count: int = 0
    mesh_count: int = 0
    texture_count: int = 0
    has_vrm_extension: bool = False
    has_humanoid_bones: bool = False
    has_expressions: bool = False


# ── VRMValidator class (pure-Python, no bpy) ────────────────────────────────

class VRMValidator:
    """Validate a parsed VRM/glTF dict for VRM 1.0 compliance.

    Checks glTF 2.0 structure, VRM extension presence, humanoid bone
    mappings, mesh primitives, material properties, and expressions.

    Args:
        strict: If True, treat warnings as errors (valid=False if any warnings).
    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict

    def validate_vrm_structure(self, data: dict) -> VRMValidationResult:
        """Validate a parsed VRM/glTF dict and return a structured result.

        Args:
            data: Parsed glTF/VRM JSON dict (from extract_json_chunk or direct load).

        Returns:
            VRMValidationResult with all findings populated.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. glTF 2.0 compliance
        gltf_errors = self.check_gltf2_compliance(data)
        errors.extend(gltf_errors)

        # 2. VRM extension
        vrm_errors = self.check_vrm_extension(data)
        errors.extend(vrm_errors)

        # 3. Humanoid bones
        bone_errors = self.check_humanoid_bones(data)
        errors.extend(bone_errors)

        # 4. Meshes
        mesh_warnings = self.check_meshes(data)
        warnings.extend(mesh_warnings)

        # 5. Materials
        material_warnings = self.check_materials(data)
        warnings.extend(material_warnings)

        # 6. Expressions
        expr_warnings = self.check_expressions(data)
        warnings.extend(expr_warnings)

        # Compute bone coverage
        bone_coverage = self.compute_bone_coverage(data)

        # Gather stats
        mesh_count = len(data.get("meshes", []))
        material_count = len(data.get("materials", []))
        texture_count = len(data.get("textures", []))

        # Detect VRM extension presence
        has_vrm_extension = bool(
            data.get("extensions", {}).get(VRM_1X_EXTENSION)
            or data.get("extensions", {}).get(VRM_0X_EXTENSION)
        )

        # Detect humanoid bones
        has_humanoid_bones = bone_coverage > 0

        # Detect expressions
        has_expressions = bool(_get_expressions(data))

        # Compute validity
        valid = len(errors) == 0
        if self.strict and len(warnings) > 0:
            valid = False

        return VRMValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            bone_coverage=bone_coverage,
            material_count=material_count,
            mesh_count=mesh_count,
            texture_count=texture_count,
            has_vrm_extension=has_vrm_extension,
            has_humanoid_bones=has_humanoid_bones,
            has_expressions=has_expressions,
        )

    def check_gltf2_compliance(self, data: dict) -> list[str]:
        """Check glTF 2.0 required fields.

        glTF 2.0 spec requires: asset (with version), and at least nodes.
        Scene is strongly recommended but not strictly required.

        Returns:
            List of error strings for missing/invalid fields.
        """
        errors: list[str] = []

        # asset field is required
        asset = data.get("asset")
        if asset is None:
            errors.append("Missing required 'asset' field")
        elif not isinstance(asset, dict):
            errors.append("'asset' field must be a dict")
        elif "version" not in asset:
            errors.append("Missing required 'asset.version' field")
        elif not asset["version"].startswith("2."):
            errors.append(
                f"Unsupported glTF version: {asset['version']} (expected 2.x)"
            )

        # nodes field should exist for a meaningful VRM
        nodes = data.get("nodes")
        if not nodes:
            errors.append("Missing 'nodes' field — no skinning data")
        elif not isinstance(nodes, list):
            errors.append("'nodes' field must be a list")

        # scene field — recommended for VRM
        if "scene" not in data:
            # This is a warning in practice, but we keep it as error for VRM
            errors.append("Missing 'scene' field — no default scene defined")

        # scenes field — strongly recommended
        scenes = data.get("scenes")
        if not scenes:
            errors.append("Missing 'scenes' field — no scene graph")
        elif not isinstance(scenes, list):
            errors.append("'scenes' field must be a list")

        return errors

    def check_vrm_extension(self, data: dict) -> list[str]:
        """Check VRM 0.x and 1.0 extension presence and structure.

        VRM files embed their data in glTF extensions:
        - VRM 0.x uses the "VRM" extension key
        - VRM 1.0 uses the "VRMC_vrm" extension key

        Returns:
            List of error strings for missing/invalid extension data.
        """
        errors: list[str] = []

        extensions = data.get("extensions")
        if not extensions:
            errors.append("No 'extensions' field — VRM extension missing")
            return errors

        if not isinstance(extensions, dict):
            errors.append("'extensions' field must be a dict")
            return errors

        # Check for VRM 1.0 extension
        vrm1 = extensions.get(VRM_1X_EXTENSION)
        vrm0 = extensions.get(VRM_0X_EXTENSION)

        if not vrm1 and not vrm0:
            errors.append(
                f"Neither '{VRM_1X_EXTENSION}' nor '{VRM_0X_EXTENSION}' "
                f"extension found"
            )
            return errors

        # Validate VRM 1.0 extension structure
        if vrm1:
            if not isinstance(vrm1, dict):
                errors.append(f"'{VRM_1X_EXTENSION}' extension must be a dict")
                return errors

            # VRM 1.0 requires a humanoid field
            if "humanoid" not in vrm1:
                errors.append(
                    f"'{VRM_1X_EXTENSION}' extension missing 'humanoid' field"
                )

            # Meta is recommended
            if "meta" not in vrm1:
                errors.append(
                    f"Warning: '{VRM_1X_EXTENSION}' extension missing 'meta' field"
                )

        # Validate VRM 0.x extension structure (legacy)
        if vrm0:
            if not isinstance(vrm0, dict):
                errors.append(f"'{VRM_0X_EXTENSION}' extension must be a dict")
                return errors

            if "humanoid" not in vrm0:
                errors.append(
                    f"'{VRM_0X_EXTENSION}' extension missing 'humanoid' field"
                )

        return errors

    def check_humanoid_bones(self, data: dict) -> list[str]:
        """Verify 25 required VRM humanoid bone mappings.

        VRM 1.0 requires all 25 humanoid bones properly mapped to nodes.
        VRM 0.x uses a similar bone list under humanoid.humanBones.

        Returns:
            List of error strings for missing bones.
        """
        errors: list[str] = []
        vrm_bones = _get_humanoid_bones(data)

        if vrm_bones is None:
            errors.append("No humanoid bone mapping found in VRM data")
            return errors

        # Check each required bone
        found_bones = set()
        if isinstance(vrm_bones, list):
            # VRM 0.x format: list of {bone, node} dicts
            found_bones = {
                b.get("bone", b.get("humanBoneName", ""))
                for b in vrm_bones
                if isinstance(b, dict)
            }
        elif isinstance(vrm_bones, dict):
            # VRM 1.0 format: dict of bone_name → node reference
            found_bones = set(vrm_bones.keys())

        required = set(VRM_25_BONE_NAMES)
        missing = required - found_bones

        if missing:
            for bone in sorted(missing):
                errors.append(f"Missing required humanoid bone: {bone}")

        return errors

    def check_meshes(self, data: dict) -> list[str]:
        """Validate mesh primitives exist and have required attributes.

        VRM mesh primitives should have POSITION attribute at minimum.
        Normal and TEXCOORD_0 are recommended.

        Returns:
            List of warning strings (meshes issues are usually warnings).
        """
        warnings: list[str] = []

        meshes = data.get("meshes", [])
        if not meshes:
            warnings.append("No meshes defined")
            return warnings

        for i, mesh in enumerate(meshes):
            if not isinstance(mesh, dict):
                warnings.append(f"Mesh {i}: invalid mesh definition")
                continue

            primitives = mesh.get("primitives", [])
            if not primitives:
                warnings.append(f"Mesh {i}: no primitives defined")
                continue

            for j, prim in enumerate(primitives):
                if not isinstance(prim, dict):
                    warnings.append(f"Mesh {i} primitive {j}: invalid definition")
                    continue

                attributes = prim.get("attributes", {})
                if not attributes:
                    warnings.append(
                        f"Mesh {i} primitive {j}: no attributes defined"
                    )
                    continue

                if "POSITION" not in attributes:
                    warnings.append(
                        f"Mesh {i} primitive {j}: missing POSITION attribute"
                    )

        return warnings

    def check_materials(self, data: dict) -> list[str]:
        """Validate material properties for VRM compatibility.

        VRM materials should have at least a name and pbrMetallicRoughness
        or a VRM-specific shader extension.

        Returns:
            List of warning strings (material issues are usually warnings).
        """
        warnings: list[str] = []

        materials = data.get("materials", [])
        if not materials:
            warnings.append("No materials defined")
            return warnings

        for i, mat in enumerate(materials):
            if not isinstance(mat, dict):
                warnings.append(f"Material {i}: invalid material definition")
                continue

            # Name is recommended
            if "name" not in mat:
                warnings.append(f"Material {i}: missing 'name' field")

            # Check for a VRM-compatible shader setup
            has_pbr = "pbrMetallicRoughness" in mat
            has_extensions = "extensions" in mat

            if not has_pbr and not has_extensions:
                warnings.append(
                    f"Material {i}: no pbrMetallicRoughness or extensions"
                )

        return warnings

    def check_expressions(self, data: dict) -> list[str]:
        """Check VRM expression/blend shape groups for completeness.

        VRM 1.0 uses 'expressions' under VRMC_vrm extension.
        VRM 0.x uses 'blendShapeMaster' with 'blendShapeGroups'.

        Standard expression presets: happy, sad, angry, surprised, neutral.

        Returns:
            List of warning strings for missing or sparse expressions.
        """
        warnings: list[str] = []

        expressions = _get_expressions(data)
        if expressions is None:
            warnings.append("No expressions/blendShapeGroups found")
            return warnings

        if isinstance(expressions, list):
            # VRM 0.x blendShapeGroups is a list
            if len(expressions) == 0:
                warnings.append("Expressions list is empty")
                return warnings

            expression_names = set()
            for expr in expressions:
                if isinstance(expr, dict):
                    name = expr.get("name", "")
                    if name:
                        expression_names.add(name)

            # Check for standard presets
            standard = {"happy", "sad", "angry", "surprised", "neutral"}
            # VRM 0.x uses Japanese/Kebab-case variants
            standard_vrm0x = {"happy", "sad", "angry", "surprised", "neutral",
                              "Happy", "Sad", "Angry", "Surprised", "Neutral"}
            overlap = expression_names & standard_vrm0x

            if len(overlap) < 3:
                warnings.append(
                    f"Only {len(overlap)} standard expressions found; "
                    f"recommend at least happy, sad, angry, surprised, neutral"
                )

        elif isinstance(expressions, dict):
            # VRM 1.0 expressions is a dict with preset and custom keys
            preset = expressions.get("preset", {})
            if not preset:
                # Could be structured differently
                if len(expressions) == 0:
                    warnings.append("Expressions dict is empty")
                    return warnings

        return warnings

    def compute_bone_coverage(self, data: dict) -> float:
        """Compute percentage of 25 required humanoid bones mapped.

        Returns:
            Float 0.0–100.0 indicating what percentage of the 25
            required VRM humanoid bones are present.
        """
        vrm_bones = _get_humanoid_bones(data)
        if vrm_bones is None:
            return 0.0

        found_bones = set()
        if isinstance(vrm_bones, list):
            found_bones = {
                b.get("bone", b.get("humanBoneName", ""))
                for b in vrm_bones
                if isinstance(b, dict)
            }
        elif isinstance(vrm_bones, dict):
            found_bones = set(vrm_bones.keys())

        required = set(VRM_25_BONE_NAMES)
        return (len(found_bones & required) / len(required)) * 100.0

    def format_report(self, result: VRMValidationResult) -> str:
        """Format a VRMValidationResult into a human-readable report string.

        Args:
            result: The validation result to format.

        Returns:
            Multi-line string with a structured validation report.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("VRM 1.0 COMPLIANCE VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Validity
        status = "PASS" if result.valid else "FAIL"
        lines.append(f"  Status:          {status}")
        if self.strict:
            lines.append("  Mode:            STRICT (warnings as errors)")
        else:
            lines.append("  Mode:            LENIENT")
        lines.append("")

        # Counts
        lines.append(f"  Bone coverage:   {result.bone_coverage:.1f}%")
        lines.append(f"  Meshes:          {result.mesh_count}")
        lines.append(f"  Materials:       {result.material_count}")
        lines.append(f"  Textures:        {result.texture_count}")
        lines.append("")

        # Feature flags
        lines.append(f"  VRM extension:   {'Yes' if result.has_vrm_extension else 'No'}")
        lines.append(f"  Humanoid bones:  {'Yes' if result.has_humanoid_bones else 'No'}")
        lines.append(f"  Expressions:     {'Yes' if result.has_expressions else 'No'}")
        lines.append("")

        # Errors
        if result.errors:
            lines.append(f"  Errors ({len(result.errors)}):")
            for err in result.errors:
                lines.append(f"    ✗ {err}")
            lines.append("")

        # Warnings
        if result.warnings:
            lines.append(f"  Warnings ({len(result.warnings)}):")
            for warn in result.warnings:
                lines.append(f"    ⚠ {warn}")
            lines.append("")

        if not result.errors and not result.warnings:
            lines.append("  No issues found.")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


# ── Pure-Python helper functions ─────────────────────────────────────────────

def parse_vrm_bytes(vrm_data: bytes) -> dict:
    """Parse a VRM binary file and return the glTF JSON dict.

    VRM files are glTF 2.0 binary (.glb) files. This function extracts
    the JSON chunk from the binary format.

    Args:
        vrm_data: Raw bytes of a .vrm file.

    Returns:
        Parsed glTF JSON dict.

    Raises:
        ValueError: If the binary is not a valid glTF/VRM file.
    """
    if not is_valid_vrm_binary(vrm_data):
        raise ValueError("Invalid VRM/glTF binary: bad magic bytes")

    return extract_json_chunk(vrm_data)


def extract_json_chunk(binary: bytes) -> dict:
    """Extract the JSON chunk from a glTF binary (.glb / .vrm).

    glTF binary format:
      - Bytes 0–3:  magic "glTF" (0x46546C67)
      - Bytes 4–7:  version (uint32, LE) — must be 2
      - Bytes 8–15: total file length (uint64, LE)
      - Chunk 0:
        - 0–3: chunk length (uint32, LE)
        - 4–7: chunk type — 0x4E4F534A = "JSON"
        - 8+:  chunk data (JSON)
      - Chunk 1:
        - 0–3: chunk length (uint32, LE)
        - 4–7: chunk type — 0x004E4942 = "BIN"
        - 8+:  binary buffer data

    Args:
        binary: Raw bytes of a .vrm/.glb file.

    Returns:
        Parsed JSON dict from the first chunk.

    Raises:
        ValueError: If the binary format is invalid.
    """
    if len(binary) < 20:
        raise ValueError("Binary data too short for glTF header")

    # Validate magic
    magic = binary[0:4]
    if magic != GLTF_MAGIC:
        raise ValueError(
            f"Invalid glTF magic: {magic!r} (expected {GLTF_MAGIC!r})"
        )

    # Read version
    version = struct.unpack_from("<I", binary, 4)[0]
    if version != GLTF_VERSION_2:
        raise ValueError(f"Unsupported glTF version: {version} (expected 2)")

    # Read total length
    total_length = struct.unpack_from("<I", binary, 8)[0]
    if total_length > len(binary):
        raise ValueError(
            f"glTF file length mismatch: header says {total_length}, "
            f"but got {len(binary)} bytes"
        )

    # Read first chunk (should be JSON)
    chunk_offset = 12
    if chunk_offset + 8 > len(binary):
        raise ValueError("No chunk data found")

    chunk0_length = struct.unpack_from("<I", binary, chunk_offset)[0]
    chunk0_type = struct.unpack_from("<I", binary, chunk_offset + 4)[0]

    # JSON chunk type = 0x4E4F534A
    JSON_CHUNK_TYPE = 0x4E4F534A
    if chunk0_type != JSON_CHUNK_TYPE:
        raise ValueError(
            f"First chunk is not JSON (type: 0x{chunk0_type:08X})"
        )

    json_start = chunk_offset + 8
    json_end = json_start + chunk0_length

    if json_end > len(binary):
        raise ValueError(
            f"JSON chunk extends beyond file: offset {json_start} + "
            f"length {chunk0_length} > file size {len(binary)}"
        )

    json_bytes = binary[json_start:json_end]

    try:
        return json.loads(json_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Failed to parse glTF JSON: {exc}") from exc


def is_valid_vrm_binary(data: bytes) -> bool:
    """Quick format check for VRM/glTF binary data.

    Checks that the data starts with the glTF magic bytes and
    the version field indicates glTF 2.0.

    Args:
        data: Raw bytes to check.

    Returns:
        True if data starts with valid glTF 2.0 header, False otherwise.
    """
    if not data or len(data) < 12:
        return False

    magic = data[0:4]
    if magic != GLTF_MAGIC:
        return False

    try:
        version = struct.unpack_from("<I", data, 4)[0]
    except struct.error:
        return False

    return version == GLTF_VERSION_2


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_humanoid_bones(data: dict) -> list | dict | None:
    """Extract humanoid bone list from VRM extension data.

    Handles both VRM 0.x and VRM 1.0 formats.

    Returns:
        Bone list (VRM 0.x), bone dict (VRM 1.0), or None if not found.
    """
    extensions = data.get("extensions", {})
    if not isinstance(extensions, dict):
        return None

    # VRM 1.0 format
    vrm1 = extensions.get(VRM_1X_EXTENSION)
    if isinstance(vrm1, dict):
        humanoid = vrm1.get("humanoid")
        if isinstance(humanoid, dict):
            bones = humanoid.get("humanBones")
            if bones is not None:
                return bones
            # Older VRM 1.0 draft used "boneMapping"
            bones = humanoid.get("boneMapping")
            if bones is not None:
                return bones
            # Some implementations nest under "bones"
            bones = humanoid.get("bones")
            if bones is not None:
                return bones

    # VRM 0.x format
    vrm0 = extensions.get(VRM_0X_EXTENSION)
    if isinstance(vrm0, dict):
        humanoid = vrm0.get("humanoid")
        if isinstance(humanoid, dict):
            bones = humanoid.get("humanBones")
            if bones is not None:
                return bones
            # Some VRM 0.x files use "boneMapping"
            bones = humanoid.get("boneMapping")
            if bones is not None:
                return bones

    return None


def _get_expressions(data: dict) -> list | dict | None:
    """Extract expressions/blendShapeGroups from VRM extension data.

    Handles both VRM 0.x and VRM 1.0 formats.

    Returns:
        Expression list/dict, or None if not found.
    """
    extensions = data.get("extensions", {})
    if not isinstance(extensions, dict):
        return None

    # VRM 1.0 format
    vrm1 = extensions.get(VRM_1X_EXTENSION)
    if isinstance(vrm1, dict):
        expressions = vrm1.get("expressions")
        if expressions is not None:
            return expressions

    # VRM 0.x format
    vrm0 = extensions.get(VRM_0X_EXTENSION)
    if isinstance(vrm0, dict):
        bsm = vrm0.get("blendShapeMaster")
        if isinstance(bsm, dict):
            groups = bsm.get("blendShapeGroups")
            if groups is not None:
                return groups

    return None