"""
conftest — Shared pytest fixtures for Hamr Phase 14 e2e integration suite.

Every test that needs a character spec, GPU profile, or performance budget
uses these fixtures so that the same well-populated objects are shared across
all test classes without duplication.

All fixtures produce pure-Python objects — no bpy import required.
"""

from __future__ import annotations

import pytest


# ── Custom markers ──────────────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "blender: marks tests as requiring Blender (skip in CI)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip Blender-dependent tests if Blender is not available."""
    import os
    skip_blender = pytest.mark.skip(
        reason="Blender not available — set RUN_BLENDER=1 to enable"
    )
    run_blender = os.environ.get("RUN_BLENDER", "").strip() in ("1", "true", "yes")
    for item in items:
        if "blender" in item.keywords and not run_blender:
            item.add_marker(skip_blender)

from hamr.core.models import (
    CharacterSpec,
    BodySpec,
    FaceSpec,
    HairSpec,
    HairColorSpec,
    EyeSpec,
    SkinSpec,
    ClothingSpec,
    ExpressionSpec,
    CustomExpressionSpec,
    PhysicsSpec,
    HairPhysicsSpec,
    BreastPhysicsSpec,
    ExportSpec,
)
from hamr.core.perf import PerformanceBudget, DEFAULT_PI5_BUDGET
from hamr.core.gpu_profiles import GPUProfile, GPU_PROFILES


# ── Fully-populated Spec ─────────────────────────────────────────────────────

@pytest.fixture
def sample_spec() -> CharacterSpec:
    """A fully-populated CharacterSpec with all sub-specs filled in.

    Uses a realistic anime character configuration that should pass
    validation and be within the Pi 5 performance budget.
    """
    return CharacterSpec(
        name="Elda_Testrun",
        version="1.0",
        body=BodySpec(
            height_cm=165.0,
            build="athletic-slender",
            skin=SkinSpec(
                base_hex="#E8B87A",
                undertone="warm",
                freckles=False,
                tan_level=0.7,
            ),
            proportions={
                "shoulder_width": 0.4,
                "bust": 0.55,
                "waist": 0.35,
                "hip_width": 0.65,
                "leg_length": 0.55,
            },
        ),
        face=FaceSpec(
            jaw="V-shape",
            cheekbones="high",
            eyes=EyeSpec(
                iris_hex="#B8D4E3",
                shape="cat-tilt",
                size=1.1,
            ),
            nose_size="small",
            nose_bridge="narrow",
            lip_fullness=0.7,
            default_expression="soft-half-smile",
        ),
        hair=HairSpec(
            style="wild-curly",
            length="shoulder-plus",
            volume=0.7,
            curl_tightness=0.75,
            color=HairColorSpec(
                roots="#C4A265",
                mid="#D4B87A",
                tips="#F5E6B8",
            ),
            shell_layers=6,
        ),
        clothing=[
            ClothingSpec(
                name="warrior_armor",
                type="full-outfit",
                primary_hex="#1A1A3E",
                accent_hex="#00D4FF",
                trim_hex="#FFD700",
            ),
        ],
        expressions=ExpressionSpec(
            defaults={
                "blink": "subtle",
                "blush": "always-on",
            },
            custom=[
                CustomExpressionSpec(
                    name="wink",
                    morphs=[{"eye_L_open": 0.0, "eye_R_open": 1.0}],
                ),
            ],
        ),
        physics=PhysicsSpec(
            hair=HairPhysicsSpec(
                stiffness=0.35,
                gravity=0.3,
                drag=0.4,
            ),
            breast=BreastPhysicsSpec(
                stiffness=0.25,
                drag=0.6,
            ),
        ),
        export=ExportSpec(
            format="vrm1",
            title="Elda Testrun",
            author="Hamr Forge",
            version="1.0",
        ),
    )


# ── Bare-minimum Spec ────────────────────────────────────────────────────────

@pytest.fixture
def minimal_spec() -> CharacterSpec:
    """A bare-minimum CharacterSpec using all defaults.

    Should pass validation since CharacterSpec defaults are valid.
    Useful for testing edge cases and budget floor calculations.
    """
    return CharacterSpec(
        name="Minimal_Avatar",
        body=BodySpec(),
        face=FaceSpec(),
        hair=HairSpec(),
        clothing=[],
        expressions=ExpressionSpec(),
        physics=PhysicsSpec(),
        export=ExportSpec(),
    )


# ── GPU Profile for Raspberry Pi 5 ──────────────────────────────────────────

@pytest.fixture
def pi5_profile() -> GPUProfile:
    """The Raspberry Pi 5 GPU profile.

    The constrained target: 20k triangles, 1024px textures, 45s build time,
    no SSS, no anisotropic. The anvil.
    """
    return GPU_PROFILES["pi5"]