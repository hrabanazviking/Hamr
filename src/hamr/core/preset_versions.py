"""
Preset Versioning System — Hamr Phase 14 (T4).

Versioned, tagged, and categorized preset metadata with migration support.
Each preset carries a PresetVersion record so consumers can check compatibility
and migrate between schema versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from typing import Optional

from hamr.core.presets import CHARACTER_PRESETS, get_preset


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PresetVersion:
    """Version metadata for a single preset."""

    name: str
    version: str  # semver "1.0.0"
    created: str  # ISO date, e.g. "2025-05-08"
    modified: str  # ISO date
    changelog: list[str] = field(default_factory=list)


@dataclass
class VersionedPreset:
    """A preset bundled with its version metadata and category tag."""

    name: str
    display_name: str
    category: str  # "anime", "realistic", "fantasy", "chibi"
    version: PresetVersion
    spec: dict  # the actual preset data
    tags: list[str] = field(default_factory=list)


# ── Category Taxonomy ────────────────────────────────────────────────────────

PRESET_CATEGORIES: dict[str, str] = {
    "anime": "Anime Style",
    "realistic": "Realistic",
    "fantasy": "Fantasy",
    "chibi": "Chibi / SD",
}


# ── Per-preset category mapping ──────────────────────────────────────────────

_PRESET_CATEGORY_MAP: dict[str, str] = {
    "anime_girl_default": "anime",
    "anime_girl_warrior": "fantasy",
    "anime_girl_mage": "fantasy",
    "anime_boy_default": "anime",
    "anime_boy_warrior": "fantasy",
    "chibi_cute": "chibi",
}


# ── Per-preset tag mapping ───────────────────────────────────────────────────

_PRESET_TAG_MAP: dict[str, list[str]] = {
    "anime_girl_default": ["school", "female", "slice-of-life"],
    "anime_girl_warrior": ["battle", "female", "strong"],
    "anime_girl_mage": ["magic", "female", "mystical"],
    "anime_boy_default": ["school", "male", "slice-of-life"],
    "anime_boy_warrior": ["battle", "male", "strong"],
    "chibi_cute": ["cute", "super-deformed", "mascot"],
}


# ── Preset Version Registry ──────────────────────────────────────────────────

PRESET_VERSIONS: dict[str, PresetVersion] = {
    "anime_girl_default": PresetVersion(
        name="anime_girl_default",
        version="1.0.0",
        created="2025-01-15",
        modified="2025-05-08",
        changelog=["Initial preset definition."],
    ),
    "anime_girl_warrior": PresetVersion(
        name="anime_girl_warrior",
        version="1.0.0",
        created="2025-01-15",
        modified="2025-05-08",
        changelog=["Initial preset definition."],
    ),
    "anime_girl_mage": PresetVersion(
        name="anime_girl_mage",
        version="1.0.0",
        created="2025-01-15",
        modified="2025-05-08",
        changelog=["Initial preset definition."],
    ),
    "anime_boy_default": PresetVersion(
        name="anime_boy_default",
        version="1.0.0",
        created="2025-01-15",
        modified="2025-05-08",
        changelog=["Initial preset definition."],
    ),
    "anime_boy_warrior": PresetVersion(
        name="anime_boy_warrior",
        version="1.0.0",
        created="2025-01-15",
        modified="2025-05-08",
        changelog=["Initial preset definition."],
    ),
    "chibi_cute": PresetVersion(
        name="chibi_cute",
        version="1.0.0",
        created="2025-01-15",
        modified="2025-05-08",
        changelog=["Initial preset definition."],
    ),
}


# ── Migration Registry ──────────────────────────────────────────────────────

# Each entry maps (from_version, to_version) → list of transform callables.
# Transforms receive the spec dict and return the transformed spec dict.

_MIGRATION_STEPS: dict[tuple[str, str], list] = {
    # Placeholder for future migrations; currently all presets are 1.0.0.
}


# ── Public Functions ─────────────────────────────────────────────────────────

def get_versioned_preset(name: str) -> VersionedPreset:
    """Look up a preset by name and return its VersionedPreset bundle.

    Args:
        name: The internal preset key (e.g. ``"anime_girl_default"``).

    Returns:
        A :class:`VersionedPreset` with version, category, tags, and spec.

    Raises:
        KeyError: If *name* is not a known preset.
    """
    if name not in CHARACTER_PRESETS:
        raise KeyError(
            f"Unknown character preset: {name!r}. "
            f"Available: {', '.join(sorted(CHARACTER_PRESETS))}"
        )

    preset = get_preset(name)
    version = PRESET_VERSIONS[name]
    category = _PRESET_CATEGORY_MAP.get(name, "anime")
    tags = _PRESET_TAG_MAP.get(name, [])

    return VersionedPreset(
        name=preset.name,
        display_name=preset.display_name,
        category=category,
        tags=list(tags),
        version=version,
        spec=preset.spec,
    )


def list_presets_by_category(category: str) -> list[VersionedPreset]:
    """Return all presets that belong to *category*.

    Args:
        category: One of the keys in :data:`PRESET_CATEGORIES`
            (``"anime"``, ``"realistic"``, ``"fantasy"``, ``"chibi"``).

    Returns:
        A list of :class:`VersionedPreset` objects in the given category.

    Raises:
        ValueError: If *category* is not a recognised category key.
    """
    if category not in PRESET_CATEGORIES:
        raise ValueError(
            f"Unknown category: {category!r}. "
            f"Available: {', '.join(sorted(PRESET_CATEGORIES))}"
        )

    names = [
        name for name, cat in _PRESET_CATEGORY_MAP.items() if cat == category
    ]
    return [get_versioned_preset(name) for name in names]


def list_all_categories() -> list[str]:
    """Return the list of all available category keys.

    Returns:
        ``["anime", "chibi", "fantasy", "realistic"]`` (sorted).
    """
    return sorted(PRESET_CATEGORIES.keys())


def validate_preset_version(name: str, min_version: str = "1.0.0") -> bool:
    """Check that a preset's version satisfies a minimum semver constraint.

    Simple major.minor.patch comparison — does **not** support pre-release
    identifiers.  Comparison is component-wise numeric.

    Args:
        name: The internal preset key.
        min_version: Minimum acceptable version string (default ``"1.0.0"``).

    Returns:
        ``True`` if the preset version >= *min_version*, ``False`` otherwise.

    Raises:
        KeyError: If *name* is not a known preset.
    """
    if name not in PRESET_VERSIONS:
        raise KeyError(f"Unknown character preset: {name!r}")

    preset_ver = PRESET_VERSIONS[name].version
    return _semver_gte(preset_ver, min_version)


def compare_presets(name_a: str, name_b: str) -> dict:
    """Compare two presets by their spec fields and report differences.

    Args:
        name_a: First preset key.
        name_b: Second preset key.

    Returns:
        A dict with:
        - ``"matching"`` — list of top-level spec keys that are identical.
        - ``"different"`` — list of top-level spec keys that differ.
        - ``"details"`` — per-key breakdown of what changed.

    Raises:
        KeyError: If either name is not a known preset.
    """
    spec_a = get_preset(name_a).spec
    spec_b = get_preset(name_b).spec

    matching: list[str] = []
    different: list[str] = []
    details: dict[str, dict] = {}

    all_keys = sorted(set(list(spec_a.keys()) + list(spec_b.keys())))
    for key in all_keys:
        val_a = spec_a.get(key)
        val_b = spec_b.get(key)
        if val_a == val_b:
            matching.append(key)
        else:
            different.append(key)
            details[key] = {"a": val_a, "b": val_b}

    return {
        "matching": matching,
        "different": different,
        "details": details,
    }


def migrate_preset(name: str, from_version: str, to_version: str) -> dict:
    """Apply migration transforms to bring a preset from one version to another.

    The migration walks through the chain of registered migration steps
    between *from_version* and *to_version*, applying each transform
    sequentially.  If there is no registered migration for a given step,
    the spec is passed through unchanged.

    Currently all presets are at version ``1.0.0``, so this is a no-op
    placeholder that returns a deep copy of the preset spec.

    Args:
        name: The internal preset key.
        from_version: Source semver string (e.g. ``"1.0.0"``).
        to_version: Target semver string (e.g. ``"2.0.0"``).

    Returns:
        A migrated spec dict (deep copy).

    Raises:
        KeyError: If *name* is not a known preset.
    """
    if name not in CHARACTER_PRESETS:
        raise KeyError(
            f"Unknown character preset: {name!r}. "
            f"Available: {', '.join(sorted(CHARACTER_PRESETS))}"
        )

    spec = deepcopy(get_preset(name).spec)

    # Walk the migration chain
    current = from_version
    while current != to_version:
        step_key = (current, to_version)
        # Check for a direct step
        if step_key in _MIGRATION_STEPS:
            for transform in _MIGRATION_STEPS[step_key]:
                spec = transform(spec)
            return spec
        # No migration step registered — return as-is (no-op)
        break

    return spec


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _semver_gte(version: str, minimum: str) -> bool:
    """Return True if *version* >= *minimum* (simple component comparison).

    Only handles major.minor.patch with numeric components.
    """
    v_parts = [int(p) for p in version.split(".")]
    m_parts = [int(p) for p in minimum.split(".")]

    # Pad to length 3 in case of short version strings
    while len(v_parts) < 3:
        v_parts.append(0)
    while len(m_parts) < 3:
        m_parts.append(0)

    for v, m in zip(v_parts, m_parts):
        if v > m:
            return True
        if v < m:
            return False
    return True  # exactly equal