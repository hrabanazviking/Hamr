# ᚺᚨᛗᚱ — Phase 13 Architecture: Ragnarök Testing (Hardening)

> **Author:** Rúnhild Svartdóttir, THE ARCHITECT  
> **Phase:** 13 — Ragnarök Testing (Hardening)  
> **Base:** v0.5.0, 984 tests, 43 Python files, 13,608 lines  
> **Objective:** Fix 4 preset validation failures; add texture pipeline, VRM validator, animation presets, GPU tiers, E2E test, and docs generation.

---

## Module Map (Phase 13 Additions)

```
src/hamr/
├── core/
│   ├── presets.py          ← PATCH (T1: fix 4 failures + regression guards)
│   ├── perf.py             ← PATCH (T5: split GPU tiers from memory tiers)
│   ├── perf_gate.py         ← PATCH (T5: accept GPUProfileTier)
│   ├── textures.py          ← EXISTS → EXTEND (T2: procedural texture pipeline)
│   ├── texture_procedural.py ← NEW (T2: skin detail / fabric normal / eye iris generators)
│   ├── gpu_profiles.py      ← NEW (T5: GPU profile tier definitions)
│   └── models.py            ← PATCH (T2: add texture-related spec fields)
├── export/
│   ├── vrm.py              ← EXISTS → EXTEND (T4: animation clip references)
│   ├── vrm_validator.py    ← NEW (T3: glTF + VRM extension compliance checker)
│   └── animation_clips.py  ← NEW (T4: idle + walk cycle clip definitions)
├── rigs/
│   └── verify.py           ← EXISTS (T3 references its VRM_BONE_HIERARCHY)
├── cli.py                  ← PATCH (T5: --gpu-tier, T7: docs commands)
└── docs/
    └── generate.py         ← NEW (T7: auto-generate CLI reference + architecture mermaid)
```

---

## T1 — Fix 4 Preset Validation Failures + Regression Guards

### Problem

Four tests in `TestValidatePreset` fail because `get_preset().spec` returns a `CharacterSpec` dataclass (with `SkinSpec`, `EyeSpec`, `HairColorSpec` sub-objects), but the tests attempt dict-style item assignment (`spec["body"]["skin"]["tan_level"] = 5.0`). Dataclass objects don't support `__setitem__`.

The root cause: `get_preset()` does `CharacterSpec.from_dict(entry["spec"])` which converts nested dicts into typed dataclass objects. But `validate_preset()` in `presets.py` expects a plain dict. There is a type mismatch between what `get_preset()` returns and what `validate_preset()` and the tests expect.

### Architecture Decision

**`validate_preset()` shall accept both `dict` and `CharacterSpec` inputs**, normalizing internally. The `CHARACTER_PRESETS` dict stores raw dicts. `get_preset()` converts to `CharacterSpec`. The tests use `get_preset().spec` which returns a `CharacterSpec` — but then try to mutate it with `spec["face"]["eyes"]["iris_hex"] = ...`.

**Fix strategy:**  
1. Add a `_to_spec_dict(spec)` helper that converts `CharacterSpec` → plain dict via `asdict()` or `.to_dict()`.  
2. Make `validate_preset()` call `_to_spec_dict()` at the top so it always works on dicts internally.  
3. Fix the 4 failing tests by ensuring they work with the returned type — OR convert the test mutations to work via the dict stored in `CHARACTER_PRESETS[name]["spec"]` directly (which IS a plain dict).

**Recommended:** Fix the tests AND the function. The tests should use `CHARACTER_PRESETS[name]["spec"]` (raw dict) for mutation tests since those ARE mutable dicts. Add a note to `validate_preset` docstring that it accepts both dict and CharacterSpec.

### Module Path  
`hamr.core.presets`

### Key Changes

| File | Change |
|------|--------|
| `src/hamr/core/presets.py` | Add `_to_spec_dict(spec: dict | CharacterSpec) -> dict` helper. Update `validate_preset()` to normalize input. |
| `tests/test_presets.py` | Change 4 failing tests to use `CHARACTER_PRESETS[name]["spec"]` (raw dict) instead of `get_preset(name).spec` (CharacterSpec). Add regression test class. |

### Key Functions

```python
def _to_spec_dict(spec: dict | CharacterSpec) -> dict:
    """Normalize spec input to a plain dict for validation."""
    if isinstance(spec, dict):
        return spec
    if hasattr(spec, "to_dict"):
        return spec.to_dict()
    # Fallback: dataclass → asdict
    from dataclasses import asdict
    return asdict(spec)
```

### Regression Guards

Add `TestPresetRegressionGuard13` test class:

```python
class TestPresetRegressionGuard13:
    """Phase 13 regression: all preset specs must validate clean."""
    
    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_preset_spec_validates_clean(self, name):
        """Every built-in preset must pass validation with zero warnings."""
        spec = CHARACTER_PRESETS[name]["spec"]  # raw dict
        warnings = validate_preset(spec)
        assert warnings == [], f"{name}: {warnings}"
    
    @pytest.mark.parametrize("name", EXPECTED_PRESET_NAMES)
    def test_preset_roundtrip_character_spec(self, name):
        """get_preset() → CharacterSpec → to_dict() → validate_preset() must pass."""
        preset = get_preset(name)
        spec_dict = _to_spec_dict(preset.spec)
        warnings = validate_preset(spec_dict)
        assert warnings == [], f"{name} roundtrip: {warnings}"
    
    def test_validate_accepts_character_spec(self):
        """validate_preset must accept CharacterSpec objects, not just dicts."""
        preset = get_preset("anime_girl_default")
        # Should NOT raise TypeError
        warnings = validate_preset(preset.spec)
        assert isinstance(warnings, list)
    
    def test_validate_accepts_dict(self):
        """validate_preset must accept raw dicts."""
        spec = CHARACTER_PRESETS["anime_girl_default"]["spec"]
        warnings = validate_preset(spec)
        assert isinstance(warnings, list)
```

### Test Strategy

- **Unit:** 4 existing failing tests fixed (use raw dict).  
- **Regression:** `TestPresetRegressionGuard13` class with 14 tests (6 presets × 2 roundtrip + 2 acceptance).  
- **Total:** ~18 new + 4 fixed = 22 regression-guard tests.  
- **CI gate:** `python -m pytest tests/test_presets.py -v` must show 0 failures.

---

## T2 — Procedural Texture Pipeline (Skin Detail, Fabric Normal, Eye Iris)

### Problem

Current `hamr.core.textures` has `generate_skin_texture()` (flat base color + noise) and `generate_hair_texture()` (gradient). No skin detail maps (pores/freckles/veins), no fabric normal maps, no eye iris textures. VRM exports require these for quality avatars.

### Architecture Decision

Create a **ProceduralTexturePipeline** that generates textures in stages:

1. **Base texture** → existing functions  
2. **Detail overlay** → skin pores/freckles/veins (Perlin noise)  
3. **Normal map** → from grayscale detail map or fabric weave pattern  
4. **Eye iris** → procedural radial iris with limbal ring and pupil  

All generators are pure-Python (Pillow + NumPy). No Blender, no GPU, no Cycles.

### Module Path  
`hamr.core.texture_procedural` (new module)  
`hamr.core.textures` (extend existing)  
`hamr.core.models` (add spec fields)

### Key Classes / Functions

**New file: `src/hamr/core/texture_procedural.py`**

```python
class ProceduralTexturePipeline:
    """Orchestrate texture generation for all avatar channels."""
    
    def __init__(self, spec: CharacterSpec, resolution: int = TEXTURE_SIZE):
        self.spec = spec
        self.resolution = resolution
        self._cache: dict[str, Image.Image] = {}
    
    def generate_all(self) -> dict[str, Image.Image]:
        """Generate full texture set: skin_base, skin_detail, skin_normal, 
        eye_iris, hair_gradient, fabric_normal per clothing item."""
        ...
    
    def generate_skin_detail(self) -> Image.Image:
        """Pores + optional freckles + veins, blended over base."""
        ...
    
    def generate_skin_normal(self) -> Image.Image:
        """Normal map from skin detail (Sobel derivative)."""
        ...
    
    def generate_eye_iris(self) -> Image.Image:
        """Procedural iris with radial fibers, limbal ring, pupil."""
        ...
    
    def generate_fabric_normal(self, fabric_type: str) -> Image.Image:
        """Weave/knit pattern normal maps for clothing."""
        ...


def generate_pore_map(size: int, density: float, seed: int = 42) -> Image.Image:
    """Perlin-like pore pattern. density: 0.0–1.0."""

def generate_freckle_map(
    size: int, 
    density: float, 
    seed: int = 42,
    radius_range: tuple = (2, 6),
) -> Image.Image:
    """Scattered dot freckle pattern."""

def generate_vein_map(size: int, intensity: float, seed: int = 42) -> Image.Image:
    """Subtle vein network overlay."""

def generate_iris_pattern(
    size: int,
    iris_hex: str,
    pupil_ratio: float = 0.3,
    limbal_width: float = 0.08,
    fiber_count: int = 180,
    seed: int = 42,
) -> Image.Image:
    """Radial iris with fibers, limbal ring, and pupil."""

def generate_fabric_normal_map(
    size: int,
    pattern: str = "cotton_weave",
    strength: float = 0.3,
) -> Image.Image:
    """Normal map from procedural fabric pattern. 
    Patterns: cotton_weave, silk, denim, leather_grain, knit."""

def grayscale_to_normal(gray: Image.Image, strength: float = 1.0) -> Image.Image:
    """Convert grayscale height map to normal map via Sobel."""
```

### Model Additions (`models.py`)

```python
@dataclass
class TextureSpec:
    skin_detail_density: float = 0.5      # pore density 0–1
    skin_detail_freckles: bool = False    # from SkinSpec.freckles
    skin_detail_veins: bool = False
    iris_detail: bool = True
    fabric_normal_strength: float = 0.3

@dataclass
class EyeSpec:  # extend existing
    # ... existing fields ...
    iris_detail_level: float = 1.0  # 0=flat, 1=full procedural
    pupil_ratio: float = 0.3
    limbal_ring_width: float = 0.08
```

### Test Strategy

- **Unit:** `tests/test_texture_procedural.py` — test each generator in isolation.  
  - `test_generate_pore_map_shape` — output is `(size, size)` grayscale  
  - `test_generate_iris_pattern_color_range` — iris RGB values near spec hex  
  - `test_generate_fabric_normal_map_patterns` — all 5 patterns produce valid normal map  
  - `test_grayscale_to_normal` — Sobel conversion is invertible-ish  
- **Integration:** `test_procedural_pipeline_generate_all` — full pipeline produces 5+ textures  
- **Regression:** assert all output images are correct size, mode (RGB/RGBA/L)  
- **Target:** 10–15 new tests

---

## T3 — VRM 1.0 Compliance Validator (glTF Schema + VRM Extension Checks)

### Problem

Currently `hamr.rigs.verify.py` checks bone count/naming/hierarchy, and `hamr.export.vrm.py` sets up VRM metadata + bone mapping. But there is **no standalone validator** that checks a `.vrm` (glTF binary) file for VRM 1.0 compliance: required glTF nodes, VRM extension fields, mesh validation, material structure, etc. The `hamr cli inspect` command exists but lacks depth.

### Architecture Decision

Create a **VRM 1.0 Compliance Validator** that checks glTF binary structure WITHOUT Blender. It reads the `.vrm` file directly (glTF uses JSON + binary chunks accessible via struct parsing). This is a **pure-Python** validator.

### Module Path  
`hamr.export.vrm_validator` (new module)

### Key Classes / Functions

```python
@dataclass
class VRMValidationReport:
    """Structured compliance check result."""
    path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)  # glTF stats
    
    # Populated fields:
    gltf_version: str = ""
    vrm_version: str = ""
    mesh_count: int = 0
    material_count: int = 0
    texture_count: int = 0
    bone_count: int = 0
    has_vrm_extension: bool = False
    has_humanoid: bool = False
    has_expressions: bool = False
    has_spring_bones: bool = False
    
    def summary(self) -> str: ...


class VRMValidator:
    """Validate a VRM 1.0 file for glTF + VRM extension compliance.
    
    Checks:
    1. glTF structure valid (JSON chunk accessible)
    2. Required glTF 2.0 fields present
    3. VRM extension node exists on scene root
    4. VRM humanoid bone map present with 25 required bones
    5. Expressions present (at least happy, sad, angry, surprised, neutral)
    6. Spring bones configured (if hair physics present)
    7. Materials use MToon_unlit or VRM_unlit_texture
    8. Mesh primitives have proper POSITION, NORMAL, TEXCOORD_0
    9. First-person offsets set
    10. Meta fields (title, author, version) non-empty
    """
    
    def __init__(self, strict: bool = False):
        self.strict = strict
    
    def validate(self, path: str | Path) -> VRMValidationReport:
        """Full validation of a VRM file."""
        ...
    
    def _parse_gltf_json(self, data: bytes) -> dict:
        """Extract the JSON chunk from a glTF binary."""
        ...
    
    def _check_gltf_structure(self, gltf: dict) -> list[str]:
        """Check required glTF 2.0 fields."""
        ...
    
    def _check_vrm_extension(self, gltf: dict) -> list[str]:
        """Check VRM 1.0 extension structure."""
        ...
    
    def _check_humanoid_bones(self, gltf: dict) -> list[str]:
        """Verify 25 VRM-required bones are mapped."""
        ...
    
    def _check_meshes(self, gltf: dict) -> list[str]:
        """Verify mesh primitives have required attributes."""
        ...
    
    def _check_materials(self, gltf: dict) -> list[str]:
        """Verify VRM-compatible materials."""
        ...


# Convenience function
def validate_vrm(path: str | Path, strict: bool = False) -> VRMValidationReport:
    """Validate a VRM file and return structured report."""
    return VRMValidator(strict=strict).validate(path)
```

### File Changes

| File | Change |
|------|--------|
| `src/hamr/export/vrm_validator.py` | **NEW** — VRM compliance validator |
| `src/hamr/cli.py` | **PATCH** — add `vrm-validate` subcommand |
| `tests/test_vrm_validator.py` | **NEW** — unit tests for validator |

### CLI Integration

```python
# In cli.py, add subparser:
vrm_validate_parser = subparsers.add_parser(
    "vrm-validate",
    help="Validate VRM 1.0 file for glTF + extension compliance",
)
vrm_validate_parser.add_argument("path", help="Path to VRM file")
vrm_validate_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
vrm_validate_parser.add_argument("--json", action="store_true", help="Output JSON report")
vrm_validate_parser.set_defaults(func=cmd_vrm_validate)
```

### Test Strategy

- **Unit:** Test glTF JSON parsing, VRM extension detection, bone mapping checks.  
- **Fixtures:** Create minimal valid/invalid `.vrm` test fixtures as binary blobs in `tests/fixtures/`.  
- **Regression:** Test every preset + perf gate combination produces a valid VRM (requires Blender — skip in CI without Blender).  
- **Target:** 15–20 new tests.

---

## T4 — Animation Preset Clips (Idle, Walk Cycle References Baked into VRM)

### Problem

VRM 1.0 supports animation via glTF animation channels and VRM expressions, but Hamr currently has **no animation presets**. Users need common animation clips (idle sway, walk cycle references) baked into the VRM export.

### Architecture Decision

Animation clips in VRM are stored as **glTF Animation** nodes with channels targeting bone properties. We define clip templates as Python dataclasses that map to glTF animation channels. These are NOT baked mesh animations — they are bone rotation references that VRChat-compatible systems can layer.

The clips are lightweight: a small number of keyframes per bone for idle sway and walk cycle reference poses.

### Module Path  
`hamr.export.animation_clips` (new module)

### Key Classes / Functions

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class AnimationKeyframe:
    """A single keyframe: frame index + bone + property + value."""
    frame: int
    bone: str           # VRM humanoid bone name
    property: str        # "rotation_quat" or "rotation_euler"
    value: tuple[float, ...]  # Quaternion (4,) or Euler (3,)

@dataclass
class AnimationClip:
    """A named animation clip with keyframes."""
    name: str
    fps: float = 30.0
    loop: bool = True
    keyframes: list[AnimationKeyframe] = field(default_factory=list)
    
    @property
    def duration_frames(self) -> int: ...
    
    @property
    def duration_seconds(self) -> float: ...


# ── Preset Clips ──────────────────────────────────────────────────

IDLE_CLIP: AnimationClip = AnimationClip(
    name="idle",
    fps=30.0,
    loop=True,
    keyframes=[
        # Subtle breathing + hip sway cycle (2 seconds @ 30fps)
        # Frame 0: rest pose
        AnimationKeyframe(0, "spine", "rotation_euler", (0.0, 0.0, 0.0)),
        AnimationKeyframe(0, "hips", "rotation_euler", (0.0, 0.0, 0.0)),
        # Frame 30: subtle exhale + sway
        AnimationKeyframe(30, "spine", "rotation_euler", (-0.02, 0.0, 0.01)),
        AnimationKeyframe(30, "hips", "rotation_euler", (0.01, 0.0, -0.005)),
        # Frame 60: return to rest
        AnimationKeyframe(60, "spine", "rotation_euler", (0.0, 0.0, 0.0)),
        AnimationKeyframe(60, "hips", "rotation_euler", (0.0, 0.0, 0.0)),
    ],
)

WALK_CLIP: AnimationClip = AnimationClip(
    name="walk",
    fps=30.0,
    loop=True,
    keyframes=[
        # Basic walk cycle (1 second, 8 key poses)
        # Left leg forward, right leg back
        AnimationKeyframe(0, "leftUpperLeg", "rotation_euler", (0.3, 0.0, 0.0)),
        AnimationKeyframe(0, "rightUpperLeg", "rotation_euler", (-0.2, 0.0, 0.0)),
        AnimationKeyframe(0, "hips", "rotation_euler", (0.0, 0.02, 0.0)),
        # ... 7 more keyframes ...
        AnimationKeyframe(15, "leftUpperLeg", "rotation_euler", (-0.1, 0.0, 0.0)),
        AnimationKeyframe(15, "rightUpperLeg", "rotation_euler", (0.3, 0.0, 0.0)),
        AnimationKeyframe(15, "hips", "rotation_euler", (0.0, -0.02, 0.0)),
        AnimationKeyframe(30, "leftUpperLeg", "rotation_euler", (0.3, 0.0, 0.0)),
        AnimationKeyframe(30, "rightUpperLeg", "rotation_euler", (-0.2, 0.0, 0.0)),
        AnimationKeyframe(30, "hips", "rotation_euler", (0.0, 0.02, 0.0)),
    ],
)


PRESET_CLIPS: dict[str, AnimationClip] = {
    "idle": IDLE_CLIP,
    "walk": WALK_CLIP,
}


def get_clip(name: str) -> AnimationClip:
    """Look up a preset clip by name."""
    if name not in PRESET_CLIPS:
        raise KeyError(f"Unknown animation clip: {name!r}. Available: {', '.join(PRESET_CLIPS)}")
    return PRESET_CLIPS[name]


def clip_to_gltf_animation(clip: AnimationClip, sampler_mode: str = "LINEAR") -> dict:
    """Convert an AnimationClip to a glTF 2.0 Animation node dict.
    
    This produces the JSON structure for a glTF animation that can be
    inserted into a VRM file's glTF data.
    """
    ...
```

### File Changes

| File | Change |
|------|--------|
| `src/hamr/export/animation_clips.py` | **NEW** — clip definitions + glTF converter |
| `src/hamr/export/vrm.py` | **PATCH** — add `setup_vrm_animations()` function |
| `tests/test_animation_clips.py` | **NEW** — clip structure + glTF output tests |

### VRM Integration

Add to `export/vrm.py`:

```python
def setup_vrm_animations(
    armature_name: str,
    clip_names: list[str] | None = None,
) -> bool:
    """Insert preset animation clips into VRM.
    
    Args:
        armature_name: Target armature in Blender scene.
        clip_names: List of clip names from PRESET_CLIPS. Default: ["idle"].
    """
    if not BLENDER_AVAILABLE:
        raise RuntimeError("bpy not available")
    ...
```

### Test Strategy

- **Unit:** `test_animation_clips.py` — clip structure validation, keyframe count, duration calculation, glTF output format.  
- **Integration:** Test `clip_to_gltf_animation()` produces valid glTF animation dict.  
- **Blender-dependent:** Test `setup_vrm_animations()` (skip in CI).  
- **Target:** 8–10 new tests.

---

## T5 — GPU Profile Tiers (Pi 5, Desktop, Cloud — Split from Current Memory Tiers)

### Problem

Current `perf.py` has `MEMORY_TIERS` with names "minimal", "balanced", "high" that conflate memory budget, build time, triangle budget, and texture resolution into a single tier. These don't map to actual hardware profiles. A Pi 5 (8GB ARM64) has different constraints than a desktop (32GB x86_64) or cloud GPU (A100 80GB).

### Architecture Decision

**Split** performance budgets into two orthogonal axes:
1. **Memory tier** (existing: minimal/balanced/high) — RAM + texture limits  
2. **GPU profile** (new: pi5/desktop/cloud) — compute capacity for Blender subprocess

GPU profiles determine:
- Whether Blender can run with GPU compositing  
- Expected Blender startup time  
- Whether texture baking uses Cycles or Eevee  
- Max concurrent texture generator threads  

Memory tiers remain as-is but are now selected **by** GPU profile (Pi 5 → minimal, desktop → balanced, cloud → high) unless overridden.

### Module Path  
`hamr.core.gpu_profiles` (new module)  
`hamr.core.perf` (patch)  
`hamr.core.perf_gate` (patch)  
`hamr.cli` (patch)

### Key Classes / Functions

**New file: `src/hamr/core/gpu_profiles.py`**

```python
from dataclasses import dataclass
from hamr.core.perf import PerformanceBudget, MEMORY_TIERS


@dataclass
class GPUProfile:
    """Hardware profile for build target machine."""
    name: str
    display_name: str
    description: str
    default_memory_tier: str      # maps to MEMORY_TIERS key
    supports_gpu_compositing: bool
    blender_startup_seconds: float
    max_concurrent_textures: int
    cycles_available: bool


GPU_PROFILES: dict[str, GPUProfile] = {
    "pi5": GPUProfile(
        name="pi5",
        display_name="Raspberry Pi 5 (8GB ARM64)",
        description="Headless Blender on ARM64. No GPU compositing. Eevee only.",
        default_memory_tier="minimal",
        supports_gpu_compositing=False,
        blender_startup_seconds=12.0,
        max_concurrent_textures=1,
        cycles_available=False,
    ),
    "desktop": GPUProfile(
        name="desktop",
        display_name="Desktop Workstation (32GB x86_64)",
        description="Standard desktop with GPU. Eevee + limited Cycles.",
        default_memory_tier="balanced",
        supports_gpu_compositing=True,
        blender_startup_seconds=5.0,
        max_concurrent_textures=2,
        cycles_available=True,
    ),
    "cloud": GPUProfile(
        name="cloud",
        display_name="Cloud GPU (A100 80GB)",
        description="Full Cycles rendering. Unlimited concurrency.",
        default_memory_tier="high",
        supports_gpu_compositing=True,
        blender_startup_seconds=3.0,
        max_concurrent_textures=4,
        cycles_available=True,
    ),
}


def get_gpu_profile(name: str) -> GPUProfile:
    """Look up a GPU profile by name."""
    if name not in GPU_PROFILES:
        available = ", ".join(sorted(GPU_PROFILES.keys()))
        raise KeyError(f"Unknown GPU profile: {name!r}. Available: {available}")
    return GPU_PROFILES[name]


def profile_to_budget(profile: GPUProfile) -> PerformanceBudget:
    """Get the default memory budget for a GPU profile."""
    return MEMORY_TIERS[profile.default_memory_tier]


def get_profile_for_device() -> str:
    """Auto-detect GPU profile from runtime environment.
    
    Checks /proc/cpuinfo and system memory to classify.
    Returns 'pi5', 'desktop', or 'cloud'.
    """
    import platform
    import os
    
    machine = platform.machine().lower()
    mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    mem_gb = mem_bytes / (1024. ** 3)
    
    if machine.startswith('arm') or machine.startswith('aarch'):
        return "pi5"
    elif mem_gb >= 64:
        return "cloud"
    else:
        return "desktop"
```

### File Changes

| File | Change |
|------|--------|
| `src/hamr/core/gpu_profiles.py` | **NEW** — GPU profile definitions + auto-detect |
| `src/hamr/core/perf.py` | **PATCH** — add docstring noting relationship to GPU profiles |
| `src/hamr/core/perf_gate.py` | **PATCH** — `PerfGate.__init__` accepts `gpu_profile` param; auto-selects budget tier |
| `src/hamr/cli.py` | **PATCH** — add `--gpu-profile` flag (choices: pi5/desktop/cloud), auto-detect if not specified |
| `tests/test_gpu_profiles.py` | **NEW** — profile lookup, budget mapping, auto-detect mocking |

### CLI Change

```python
build_parser.add_argument(
    "--gpu-profile", "-G", default=None,
    choices=["pi5", "desktop", "cloud"],
    help="GPU profile (auto-detected if not specified)",
)
# When --gpu-profile is set, it overrides --budget's default
# --budget still works as explicit override
```

### Test Strategy

- **Unit:** Test profile lookup, budget mapping, boundary conditions.  
- **Auto-detect mock:** Patch `platform.machine()` and `os.sysconf` to test Pi 5 / desktop / cloud detection.  
- **Integration:** Test that `PerfGate(gpu_profile="pi5")` selects "minimal" budget by default.  
- **Regression:** All existing `PerfGate` tests still pass (backward compatible: `tier=` param unchanged).  
- **Target:** 10–12 new tests.

---

## T6 — End-to-End Integration Test (Mock Blender Build Pipeline)

### Problem

No E2E test exists. The pipeline (`BuildPipeline.build()`) launches a real Blender subprocess, which is unavailable in CI. We need a test that exercises the full spec → validate → serialize → "build" → verify path with a **mock Blender** that doesn't require the actual binary.

### Architecture Decision

Create a `MockBlenderRunner` that replaces `run_blender_script()` in tests. It simulates:
- Successful Blender invocation (writes a small dummy `.vrm` file)  
- Blender timeout  
- Blender validation failure  
- Blender not found  

The E2E test exercises `BuildPipeline.build()` end-to-end with this mock, verifying:
1. Spec parsing and validation  
2. JSON serialization  
3. Temp file management  
4. Output file creation  
5. Error path handling  
6. PipelineResult fields  

### Module Path  
`tests/test_e2e_build.py` (new test file)  
`tests/conftest.py` (extend with mock fixtures)

### Key Classes / Functions

```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from hamr.blender_bridge.runner import BlenderResult


@pytest.fixture
def mock_blender_success(tmp_path):
    """Mock run_blender_script that simulates successful build."""
    def mock_run(*args, **kwargs):
        # Create a dummy output file
        output_path = kwargs.get("output", None)
        # Find output arg from script_args
        if not output_path and "script_args" in kwargs:
            for i, arg in enumerate(kwargs["script_args"]):
                if arg == "--output" and i+1 < len(kwargs["script_args"]):
                    output_path = Path(kwargs["script_args"][i+1])
                    break
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"MOCK_VRM_DATA" * 100)  # ~1.4 KB
        
        return BlenderResult(
            success=True,
            exit_code=0,
            stdout="HAMR_BUILD_OK",
            stderr="",
        )
    return mock_run


@pytest.fixture
def mock_blender_timeout():
    """Mock that simulates Blender timeout."""
    def mock_run(*args, **kwargs):
        return BlenderResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="Blender subprocess timed out",
        )
    return mock_run


@pytest.fixture
def mock_blender_validation_failure():
    """Mock that simulates Blender validation error."""
    def mock_run(*args, **kwargs):
        return BlenderResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="AssertionError: Bone 'hips' not found in armature",
        )
    return mock_run
```

```python
# tests/test_e2e_build.py
class TestE2EBuildPipeline:
    """End-to-end tests for the full build pipeline with mock Blender."""
    
    def test_full_build_success(self, tmp_path, mock_blender_success):
        """Spec → validate → serialize → build → verify output."""
        from hamr.core.pipeline import BuildPipeline
        from hamr.core.presets import get_preset
        from hamr.core.spec import Spec
        from hamr.core.models import CharacterSpec
        
        # Create a spec YAML from preset
        spec = Spec(character=CharacterSpec.from_dict(
            get_preset("anime_girl_default").spec
        ))
        spec_path = tmp_path / "test_spec.yaml"
        spec.to_yaml(str(spec_path))
        
        with patch("hamr.core.pipeline.run_blender_script", mock_blender_success):
            with patch("hamr.core.pipeline.check_blender_available", return_value=True):
                with patch("hamr.core.pipeline.get_blender_version", return_value="4.2.0"):
                    pipeline = BuildPipeline(keep_temp=True)
                    result = pipeline.build(
                        spec_path=str(spec_path),
                        output_dir=str(tmp_path / "output"),
                    )
        
        assert result.success
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.elapsed > 0
    
    def test_validation_failure(self, tmp_path):
        """Invalid spec should fail before Blender is called."""
        ...
    
    def test_blender_timeout(self, tmp_path, mock_blender_timeout):
        """Blender timeout should produce error in result."""
        ...
    
    def test_build_from_preset(self, tmp_path, mock_blender_success):
        """Build pipeline from preset name."""
        ...
    
    def test_perf_gate_blocks_build(self, tmp_path):
        """Over-budget spec should be blocked by perf gate."""
        ...
    
    def test_temp_file_cleanup(self, tmp_path, mock_blender_success):
        """Temp files should be cleaned up after successful build."""
        ...
    
    def test_validate_only_mode(self, tmp_path):
        """validate_only should never call Blender."""
        ...


class TestE2EEnvironmentCheck:
    """Test pipeline environment check."""
    
    def test_check_env_without_blender(self):
        """check_environment should handle missing Blender gracefully."""
        ...
```

### Test Strategy

- **Integration:** 6–8 E2E scenarios with mock Blender runner.  
- **Error paths:** timeout, validation failure, missing Blender.  
- **Coverage:** spec path, preset path, perf gate integration.  
- **CI-friendly:** No actual Blender required. All Blender calls mocked.  
- **Target:** 8–12 new tests.

---

## T7 — Documentation Generation (CLI Reference, Architecture Diagram, Preset Guide)

### Problem

No auto-generated documentation exists. The CLI has subcommands across `build`, `validate`, `inspect`, `list-presets`, `verify-rig`, `check-env`, `version`. Preset data and constants are scattered. No architecture diagram.

### Architecture Decision

Create a `docs/generate.py` module that:
1. **CLI Reference** — Extract argparse help text into a structured Markdown reference.  
2. **Architecture Diagram** — Generate a Mermaid diagram from module imports/structure.  
3. **Preset Guide** — Render CHARACTER_PRESETS data into a human-readable Markdown table.  

This is a **build-time tool**, not a runtime dependency. It runs via `hamr docs generate`.

### Module Path  
`hamr.docs.generate` (new module)  
`hamr.cli` (patch — add `docs` subcommand)

### Key Classes / Functions

```python
# src/hamr/docs/generate.py

def generate_cli_reference() -> str:
    """Generate CLI reference Markdown from argparse."""
    from hamr.cli import main
    import io
    import sys
    
    # Capture help output
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        main(["--help"])
    except SystemExit:
        pass
    finally:
        sys.stdout = old_stdout
    
    help_text = buffer.getvalue()
    # Format as Markdown
    ...


def generate_architecture_diagram() -> str:
    """Generate Mermaid diagram of Hamr module structure."""
    modules = {
        "core": ["pipeline", "presets", "perf", "perf_gate", "validate", 
                 "models", "spec", "textures", "texture_procedural", "gpu_profiles"],
        "body": ["forge", "presets"],
        "hair": ["mesh"],
        "face": ["expressions"],
        "clothing": ["mesh"],
        "materials": ["anime"],
        "rigs": ["spring_bones", "stub_bones", "collision", "weights", "verify"],
        "export": ["vrm", "glb", "first_person", "vrm_validator", "animation_clips"],
        "blender_bridge": ["runner", "scene", "mesh_ops"],
        "cli": [],
    }
    # Generate Mermaid graph
    ...


def generate_preset_guide() -> str:
    """Generate preset guide Markdown from CHARACTER_PRESETS data."""
    from hamr.core.presets import CHARACTER_PRESETS, PRESET_CATEGORIES, get_preset
    
    lines = ["# Hamr Character Presets\n"]
    for name, data in CHARACTER_PRESETS.items():
        spec = data["spec"]
        lines.append(f"## {data['display_name']}")
        lines.append(f"**{data['description']}**\n")
        body = spec.get("body", {})
        lines.append(f"- Height: {body.get('height_cm', '?')} cm")
        lines.append(f"- Build: {body.get('build', '?')}")
        hair = spec.get("hair", {})
        lines.append(f"- Hair: {hair.get('style', '?')}, {hair.get('length', '?')}")
        lines.append("")
    return "\n".join(lines)


def generate_all(output_dir: str = "docs") -> None:
    """Generate all documentation to output directory."""
    from pathlib import Path
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    (out / "cli_reference.md").write_text(generate_cli_reference())
    (out / "architecture.md").write_text(generate_architecture_diagram())
    (out / "preset_guide.md").write_text(generate_preset_guide())
    
    print(f"✓ Documentation generated in {out}/")
```

### CLI Integration

```python
# In cli.py, add subparser:
docs_parser = subparsers.add_parser("docs", help="Generate documentation")
docs_parser.add_argument("--output", "-o", default="docs", help="Output directory")
docs_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
docs_parser.set_defaults(func=cmd_docs)


def cmd_docs(args):
    from hamr.docs.generate import generate_all
    generate_all(output_dir=args.out)
    return 0
```

### File Changes

| File | Change |
|------|--------|
| `src/hamr/docs/__init__.py` | **NEW** — empty init |
| `src/hamr/docs/generate.py` | **NEW** — doc generators |
| `src/hamr/cli.py` | **PATCH** — `docs` subcommand |
| `tests/test_docs_generate.py` | **NEW** — test each generator |

### Test Strategy

- **Unit:** Test `generate_cli_reference()` returns non-empty string with known patterns (e.g., "build", "validate").  
- **Unit:** Test `generate_architecture_diagram()` returns valid Mermaid syntax (contains `graph TD`).  
- **Unit:** Test `generate_preset_guide()` contains all 6 preset names.  
- **Integration:** Test `generate_all()` writes 3 files to temp directory.  
- **Target:** 6–8 new tests.

---

## Dependency Graph

```
T1 (preset fix) ─────────────→ no dependencies, unblocks T6
T2 (texture pipeline) ───────→ T5 (GPU profiles determine texture concurrency)
T3 (VRM validator) ──────────→ T4 (animation clips need validator checks)
T4 (animation clips) ────────→ T3 (clips validated against VRM spec)
T5 (GPU profiles) ───────────→ T6 (perf gate uses GPU profiles)
T6 (E2E test) ───────────────→ T1, T5 (must test fixed presets + new GPU tiers)
T7 (docs) ───────────────────→ T1, T2, T3, T4, T5 (docs reflect all changes)
```

**Recommended build order:** T1 → T5 → T2 → T3 → T4 → T6 → T7

---

## Test Count Projection

| Task | New Tests | Fixed Tests | Total |
|------|-----------|-------------|-------|
| T1 — Preset fix + regression | 14 | 4 | 18 |
| T2 — Texture pipeline | 12 | 0 | 12 |
| T3 — VRM validator | 18 | 0 | 18 |
| T4 — Animation clips | 10 | 0 | 10 |
| T5 — GPU profiles | 12 | 0 | 12 |
| T6 — E2E integration | 10 | 0 | 10 |
| T7 — Docs generation | 8 | 0 | 8 |
| **Total** | **84** | **4** | **88** |

**Projected total after Phase 13: 984 + 88 = 1,072 tests**

---

## File Manifest

### New Files (9)
```
src/hamr/core/gpu_profiles.py
src/hamr/core/texture_procedural.py
src/hamr/export/vrm_validator.py
src/hamr/export/animation_clips.py
src/hamr/docs/__init__.py
src/hamr/docs/generate.py
tests/test_gpu_profiles.py
tests/test_texture_procedural.py
tests/test_vrm_validator.py
tests/test_animation_clips.py
tests/test_e2e_build.py
tests/test_docs_generate.py
```

### Modified Files (6)
```
src/hamr/core/presets.py       — _to_spec_dict helper, validate_preset normalization
src/hamr/core/perf.py           — docstring noting GPU profile relationship
src/hamr/core/perf_gate.py      — PerfGate accepts gpu_profile param
src/hamr/core/models.py         — add TextureSpec, extend EyeSpec
src/hamr/core/textures.py       — reference ProceduralTexturePipeline
src/hamr/export/vrm.py          — setup_vrm_animations function
src/hamr/cli.py                  — --gpu-profile flag, vrm-validate cmd, docs cmd
tests/test_presets.py            — fix 4 failing tests, add regression guards
tests/conftest.py                — mock Blender fixtures
```

---

*The forge burns hot. The anvil rings true. Rúnhild Svartdóttir signs off Phase 13.* ᚱ