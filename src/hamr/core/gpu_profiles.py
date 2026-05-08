"""
GPU Profiles — Hardware-aware build profiles for Pi 5, Desktop, and Cloud.

Each GPU profile describes the hardware capability of a target machine and
maps to concrete build limits (triangles, textures, time, memory) as well
as feature flags (SSS, anisotropic shading, hair styles, clothing layers).

The Pi 5 is the anvil. The cloud is the sky. The desktop stands between.
— Eldra Járnsdóttir
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field

from hamr.core.perf import PerformanceBudget, MEMORY_TIERS


# ── GPUProfile Dataclass ────────────────────────────────────────────────

@dataclass
class GPUProfile:
    """Hardware profile for the build target machine.

    Each profile describes what the hardware can handle: maximum polygon
    counts, texture resolution, build time budgets, memory limits, and
    which advanced shader features are available.

    Attributes:
        name: Machine-readable profile identifier (e.g. "pi5").
        display_name: Human-readable name (e.g. "Raspberry Pi 5").
        max_triangles: Maximum total triangle count across all meshes.
        max_texture_resolution: Maximum texture side length in pixels.
        max_build_time_seconds: Maximum Blender build time in seconds.
        max_memory_mb: Maximum peak memory usage in MB.
        recommended_hair_styles: Hair styles this profile can render well.
        recommended_clothing_layers: Max clothing layers the profile supports.
        supports_sss: Whether skin subsurface scattering is feasible.
        supports_anisotropic: Whether hair anisotropic shading is feasible.
        auto_detect_order: Priority order for auto-detection (lower = checked first).
    """

    name: str
    display_name: str
    max_triangles: int
    max_texture_resolution: int
    max_build_time_seconds: float
    max_memory_mb: int
    recommended_hair_styles: list[str] = field(default_factory=list)
    recommended_clothing_layers: int = 1
    supports_sss: bool = True
    supports_anisotropic: bool = True
    auto_detect_order: int = 0


# ── Pre-defined Profiles ────────────────────────────────────────────────

GPU_PROFILES: dict[str, GPUProfile] = {
    "pi5": GPUProfile(
        name="pi5",
        display_name="Raspberry Pi 5",
        max_triangles=20_000,
        max_texture_resolution=1024,
        max_build_time_seconds=45.0,
        max_memory_mb=1500,
        recommended_hair_styles=["short", "medium_bob"],
        recommended_clothing_layers=1,
        supports_sss=False,
        supports_anisotropic=False,
        auto_detect_order=1,
    ),
    "desktop": GPUProfile(
        name="desktop",
        display_name="Desktop GPU",
        max_triangles=80_000,
        max_texture_resolution=2048,
        max_build_time_seconds=30.0,
        max_memory_mb=4096,
        recommended_hair_styles=["short", "medium_bob", "long", "twin_tails", "ponytail"],
        recommended_clothing_layers=3,
        supports_sss=True,
        supports_anisotropic=True,
        auto_detect_order=2,
    ),
    "cloud": GPUProfile(
        name="cloud",
        display_name="Cloud GPU",
        max_triangles=200_000,
        max_texture_resolution=4096,
        max_build_time_seconds=15.0,
        max_memory_mb=8192,
        recommended_hair_styles=["short", "medium_bob", "long", "twin_tails", "ponytail"],
        recommended_clothing_layers=5,
        supports_sss=True,
        supports_anisotropic=True,
        auto_detect_order=3,
    ),
}


# ── Lookup Functions ────────────────────────────────────────────────────

def get_profile(name: str) -> GPUProfile:
    """Look up a GPU profile by name.

    Args:
        name: Profile identifier — one of "pi5", "desktop", "cloud".

    Returns:
        The matching GPUProfile.

    Raises:
        KeyError: If the name is not a recognised profile.
    """
    if name not in GPU_PROFILES:
        available = ", ".join(sorted(GPU_PROFILES.keys()))
        raise KeyError(
            f"Unknown GPU profile: {name!r}. Available: {available}"
        )
    return GPU_PROFILES[name]


def list_profiles() -> list[GPUProfile]:
    """Return all GPU profiles sorted by auto_detect_order.

    Returns:
        List of GPUProfile objects, lowest auto_detect_order first.
    """
    return sorted(GPU_PROFILES.values(), key=lambda p: p.auto_detect_order)


# ── Auto-detection ──────────────────────────────────────────────────────

def auto_detect_profile() -> str:
    """Detect the best-matching GPU profile for the current hardware.

    Strategy:
      1. If the CPU architecture is ARM/AArch64 → "pi5"
      2. If total system RAM ≥ 64 GB → "cloud"
      3. Otherwise → "desktop"

    Falls back to "desktop" on any detection failure.

    Returns:
        Profile name string ("pi5", "desktop", or "cloud").
    """
    try:
        machine = platform.machine().lower()

        # ARM-based systems are assumed to be Pi 5 class
        if machine.startswith("arm") or machine.startswith("aarch"):
            return "pi5"

        # Check system memory
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            mem_bytes = page_size * phys_pages
            mem_gb = mem_bytes / (1024.0 ** 3)
        except (ValueError, OSError):
            # sysconf not available (Windows, some containers)
            mem_gb = 0.0
            # Try psutil as fallback
            try:
                import psutil  # type: ignore[import-untyped]
                mem_gb = psutil.virtual_memory().total / (1024.0 ** 3)
            except ImportError:
                pass

        if mem_gb >= 64:
            return "cloud"

        return "desktop"
    except Exception:
        # If anything goes wrong, safest fallback is desktop
        return "desktop"


# ── Spec-based Profile Recommendation ───────────────────────────────────

def profile_from_spec(spec: dict) -> str:
    """Recommend a GPU profile based on the complexity of a character spec.

    Analyses the spec's demands (hair, clothing, texture resolution) and
    picks the minimum profile that can satisfy them.

    Args:
        spec: A character specification dict. Recognised keys:
            - "hair": dict with "style", "length", "volume", "shell_layers"
            - "clothing": list of clothing item dicts
            - "textures": dict with optional "resolution"

    Returns:
        Profile name string ("pi5", "desktop", or "cloud").
    """
    # Accumulate minimum requirements
    needs_cloud = False
    needs_desktop = False

    hair = spec.get("hair")
    if isinstance(hair, dict):
        style = hair.get("style", "straight")
        volume = hair.get("volume", 0.7)
        complex_styles = {"wild-curly", "braided"}
        if style in complex_styles or volume > 0.9:
            needs_cloud = True
        elif volume > 0.5 or style not in ("straight", "bun"):
            needs_desktop = True

    clothing = spec.get("clothing")
    if isinstance(clothing, list):
        n_layers = len(clothing)
        if n_layers > 3:
            needs_cloud = True
        elif n_layers > 1:
            needs_desktop = True

    textures = spec.get("textures")
    if isinstance(textures, dict):
        tex_res = textures.get("resolution", 1024)
        if tex_res > 2048:
            needs_cloud = True
        elif tex_res > 1024:
            needs_desktop = True

    # Resolve to highest needed profile
    if needs_cloud:
        return "cloud"
    if needs_desktop:
        return "desktop"
    return "pi5"


# ── Compatibility Validation ────────────────────────────────────────────

def validate_profile_compatibility(profile_name: str, spec: dict) -> list[str]:
    """Check a spec against a GPU profile's limits.

    Returns a list of warning strings — empty if the spec is fully
    compatible with the profile.

    Args:
        profile_name: One of "pi5", "desktop", "cloud".
        spec: Character specification dict.

    Returns:
        List of human-readable warning strings.
    """
    profile = get_profile(profile_name)
    warnings: list[str] = []

    # ── Triangle budget ──────────────────────────────────────────────
    clothing = spec.get("clothing")
    n_clothing = len(clothing) if isinstance(clothing, list) else 0
    if n_clothing > profile.recommended_clothing_layers:
        warnings.append(
            f"Spec has {n_clothing} clothing layers but profile "
            f"'{profile_name}' recommends at most "
            f"{profile.recommended_clothing_layers}"
        )

    # ── Hair style compatibility ─────────────────────────────────────
    hair = spec.get("hair")
    if isinstance(hair, dict):
        style = hair.get("style", "straight")
        # Map perf.py style names to our recommended_hair_styles list
        # The recommended_hair_styles list uses our naming convention
        style_name = style
        if style_name not in profile.recommended_hair_styles and style != "none":
            # Check if it's a known complex style that should be in the list
            if style_name not in ("straight", "bun"):
                warnings.append(
                    f"Hair style '{style_name}' may not render well on "
                    f"profile '{profile_name}' — recommended: "
                    f"{', '.join(profile.recommended_hair_styles)}"
                )

    # ── Texture resolution ───────────────────────────────────────────
    textures = spec.get("textures")
    if isinstance(textures, dict):
        tex_res = textures.get("resolution", 1024)
        if tex_res > profile.max_texture_resolution:
            warnings.append(
                f"Texture resolution {tex_res}px exceeds profile "
                f"'{profile_name}' limit of {profile.max_texture_resolution}px"
            )

    # ── SSS / Anisotropic feature gates ──────────────────────────────
    body = spec.get("body")
    if isinstance(body, dict):
        skin = body.get("skin", {})
        if isinstance(skin, dict):
            if skin.get("sss_enabled") and not profile.supports_sss:
                warnings.append(
                    f"Spec requests SSS but profile '{profile_name}' "
                    f"does not support skin subsurface scattering"
                )
        hair_spec = body.get("hair", {}) if isinstance(body, dict) else {}
        # Also check top-level hair for anisotropic
    if isinstance(hair, dict):
        if hair.get("anisotropic_enabled") and not profile.supports_anisotropic:
            warnings.append(
                f"Spec requests anisotropic shading but profile "
                f"'{profile_name}' does not support hair anisotropic shading"
            )

    # ── Build time (rough estimate, scaled by profile speed) ─────────
    # Base times assume Pi 5–class hardware. Scale by a speed factor
    # derived from the profile's max_build_time_seconds (lower = faster).
    # Pi 5 = 45s budget → factor 1.0, desktop = 30s → factor ~0.67,
    # cloud = 15s → factor ~0.33.
    pi5_reference_time = 45.0
    speed_factor = profile.max_build_time_seconds / pi5_reference_time

    estimated_time = 15.0  # base time (Pi 5 scale)
    if isinstance(hair, dict):
        style = hair.get("style", "straight")
        style_time_map = {
            "wild-curly": 10.0,
            "straight": 5.0,
            "wavy": 7.0,
            "braided": 12.0,
            "bun": 4.0,
            "ponytail": 6.0,
        }
        estimated_time += style_time_map.get(style, 7.0)
    estimated_time += n_clothing * 3.0
    estimated_time *= speed_factor  # Scale by hardware capability
    if estimated_time > profile.max_build_time_seconds:
        warnings.append(
            f"Estimated build time {estimated_time:.1f}s exceeds "
            f"profile '{profile_name}' limit of "
            f"{profile.max_build_time_seconds:.1f}s"
        )

    return warnings


# ── Budget Conversion ───────────────────────────────────────────────────

def profile_to_budget(profile_name: str) -> dict:
    """Convert a GPU profile to a performance budget dict.

    The returned dict is compatible with the budget parameters used in
    ``hamr.core.perf`` (``PerformanceBudget`` fields).

    Args:
        profile_name: One of "pi5", "desktop", "cloud".

    Returns:
        Dict with keys: max_triangles, max_texture_resolution,
        max_build_time_seconds, max_memory_mb, and blender_timeout_seconds
        (set to 2× max_build_time_seconds), target_fps.
    """
    profile = get_profile(profile_name)

    # Determine FPS target based on profile capability
    fps_targets = {
        "pi5": 24.0,
        "desktop": 30.0,
        "cloud": 60.0,
    }
    target_fps = fps_targets.get(profile_name, 30.0)

    return {
        "max_triangles": profile.max_triangles,
        "max_texture_resolution": profile.max_texture_resolution,
        "max_build_time_seconds": profile.max_build_time_seconds,
        "max_memory_mb": float(profile.max_memory_mb),
        "blender_timeout_seconds": profile.max_build_time_seconds * 2.5,
        "target_fps": target_fps,
    }