# AUDIT_17.md — HAMREISA Pre-Flight Audit

**Auditor:** Sólrún Hvítmynd (manual completion after sub-agent timeout)
**Date:** 2026-05-11
**Ritual:** HAMREISA — The Raising of the Shape

## Environment Check ✓

| Component | Status | Version |
|-----------|--------|---------|
| Blender | ✓ | 3.4.1 |
| VRM Addon | ✓ | Installed |
| MB-Lab | ✓ | 1.7.8 |
| Build Script | ✓ | Found |
| Disk Space | ✓ | 324GB free |
| RAM | ✓ | 11GB available |
| Test Suite | ✓ | 2206 passed, 27 skipped |

## Critical Blocker Verification

### FP-1: vrm_addon_extension Pattern ✅ FIXED
- **Before:** `build_avatar.py` used `armature.data.vrm_addon_extension` (Armature data block) — lines 861, 912-913, 936-937, 988-989
- **After:** All changed to `armature.vrm_addon_extension` (Object) — matching vrm.py, spring_bones.py, first_person.py
- **Also fixed:** 3 `hasattr(obj.data, "vrm_addon_extension")` → `hasattr(obj, "vrm_addon_extension")`

### FP-2: Conflicting MB_LAB_BONE_MAP ✅ FIXED
- **Before:** Three different inline bone maps in build_avatar.py (25 entries), vrm.py (39 entries), stub_bones.py (28-line internal dict)
- **After:** Single canonical `MB_LAB_BONE_MAP` in `hamr/core/constants.py` (25 bones), all three files import from it
- **MB-Lab 1.7.8 naming confirmed:** underscore suffix convention (`thigh_L`, `calf_L`, `upperarm_L`)
- **Note:** `animation_clips.py` and `verify.py` still have reverse maps (`MB_LAB_TO_VRM`) — separate concern, not blocking

### FP-3: MB-Lab CANCELLED Handling ✅ FIXED
- **Before:** Line 519 treated CANCELLED as valid result → silent empty mesh generation
- **After:** Logs warning → retries once → raises BuildError(stage="mblab_init") if still CANCELLED
- **FINISHED result:** Proceeds normally as before

## Risk Assessment

- **Pre-fix probability of clean first build:** 15-25% (per Architect)
- **Post-fix probability:** 50-70% (blockers FP-1, FP-2, FP-3 resolved)
- **Remaining risks:** Blender headless quirks, VRM addon export edge cases, MB-Lab mesh generation variations on ARM64

## remaining_conflicts.py (Noted, Not Fixed)

- `animation_clips.py`: reverse bone map uses old naming
- `verify.py`: reverse bone map uses old naming
- `weights.py`, `spring_bones.py`, `clothing/mesh.py`: mixed bone name region definitions
- These are NOT blocking for E2E build but should be addressed in Phase 18

---

*The anvil is struck. The shape stirs. Hail the Norns.*