# ᚺᚨᛗᚱ — Interface Contract

> *"If it matters, it deserves a form that can endure."*
> — Eirwyn Rúnblóm, Scribe

## Public API — Python

### `hamr.build(spec_path, output_dir, format="vrm")`
The primary entry point. Takes a YAML spec, forges a character, exports VRM.

```python
from hamr import build

result = build(
    spec_path="examples/spec_runa_gridweaver.yaml",
    output_dir="output/",
    format="vrm",  # or "glb", "blend"
)
print(result.vrm_path)       # Path to .vrm file
print(result.poly_count)     # Total polygons
print(result.build_time)     # Seconds
```

### `hamr.inspect(path, targets=None)`
Inspect a VRM/GLB file for compliance.

```python
from hamr import inspect

report = inspect("output/runa.vrm", targets=["VRCHAT", "VROID"])
for violation in report.violations:
    print(f"[{violation.severity}] {violation.rule_id}: {violation.message}")
```

### `hamr.iterate(spec_path, focus, rounds=5)`
Agent-driven refinement loop. Build, evaluate, adjust spec, rebuild.

```python
from hamr import iterate

result = iterate(
    spec_path="spec.yaml",
    focus="hair",  # focus refinement on hair module
    rounds=5,
)
```

### `hamr.Spec.from_yaml(path)` / `hamr.Spec.from_dict(data)`
Parse and validate a spec without building.

```python
from hamr import Spec

spec = Spec.from_yaml("spec.yaml")
# Modify spec programmatically
spec.body.skin.base_hex = "#C4A265"
spec.hair.style = "straight"

# Re-export modified spec
spec.to_yaml("spec_modified.yaml")
```

## Public API — CLI

```bash
# Build a character from spec
hamr build spec.yaml --out output/ --format vrm

# Build batch of specs
hamr build-batch specs/ --out output/

# Inspect a VRM file
hamr inspect output/avatar.vrm --targets VRCHAT

# List available presets and assets
hamr list-presets
hamr list-assets

# Validate a spec without building
hamr validate spec.yaml

# Bootstrap seed assets (download MB-Lab, textures, etc.)
hamr bootstrap

# Show version
hamr version
```

## Public API — YAML Spec

The YAML spec is the **primary interface** for both humans and agents:

```yaml
# The spec IS the character.
name: "Runa Gridweaver"
version: "1.0"

body:
  height_cm: 173
  build: athletic-slender
  skin:
    base_hex: "#E8B87A"
    undertone: warm
    freckles: false
    tan_level: 0.7
  proportions:
    shoulder_width: 0.4
    bust: 0.55
    waist: 0.35
    hip_width: 0.65
    leg_length: 0.55

face:
  jaw: V-shape
  cheekbones: high
  eyes:
    iris_hex: "#B8D4E3"
    shape: cat-tilt
    size: 1.1  # slightly larger than naturalistic
  nose:
    size: small
    bridge: narrow
  lips:
    fullness: 0.7
    default_expression: soft-half-smile

hair:
  style: wild-curly
  length: shoulder-plus
  volume: 0.7
  curl_tightness: 0.75
  color:
    roots: "#C4A265"
    mid: "#D4B87A"
    tips: "#F5E6B8"
  shell_layers: 6

clothing:
  - name: cyber-viking
    type: full-outfit
    primary_hex: "#1A1A3E"
    accent_hex: "#00D4FF"
    trim_hex: "#FFD700"

expressions:
  defaults:
    blink: subtle
    blush: always-on
  custom:
    - name: flirty
      morphs:
        mouth_smile_l: 0.6
        eye_squint_l: 0.3
    - name: ahegao
      morphs:
        mouth_open: 0.9
        eye_roll: 0.8

physics:
  hair:
    stiffness: 0.35
    gravity: 0.3
    drag: 0.4
  breast:
    stiffness: 0.25
    drag: 0.6

export:
  format: vrm1
  title: "Runa Gridweaver"
  author: "Hamr Forge"
  version: "1.0"
  license: "CC-BY-4.0"
  contact_url: "https://github.com/hrabanazviking/Hamr"
```

## Error Contract

All errors inherit from `HamrError`:

```python
class HamrError(Exception):
    """Base error for all Hamr operations."""

class SpecValidationError(HamrError):
    """Spec failed validation. .errors contains list of violations."""

class BuildError(HamrError):
    """Build pipeline failed. .stage indicates which forge failed."""

class ExportError(HamrError):
    """VRM/GLB export failed. .details contains Blender output."""

class AssetNotFoundError(HamrError):
    """Required base mesh or texture not found."""
```

## Version Contract

- Spec format version: `"1.0"` (in spec file)
- Hamr version: follows semver (`0.1.0` → `0.2.0` → `1.0.0`)
- VRM output: VRM 1.0 spec
- Backward compatibility: specs from version N must be buildable by version N+1