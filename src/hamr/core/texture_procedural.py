"""
Procedural Texture Pipeline — Pure-Python texture generation via NumPy + Pillow.

Every pore, every fiber, every iris pattern — generated from math alone.
No Blender, no GPU, no external assets. Just NumPy and Pillow on Pi 5 ARM64.

Phase 13 T2: skin detail, SSS thickness, iris detail, hair gradient, fabric normal maps.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional

import numpy as np

logger = logging.getLogger("hamr.texture_procedural")

# ──────────────────────────────────────────────────────────────
# Pillow availability guard
# ──────────────────────────────────────────────────────────────
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore
    PILLOW_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# ProceduralTexture dataclass
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProceduralTexture:
    """A procedurally generated texture, stored as PNG bytes.

    Attributes:
        name: Human-readable texture name (e.g., "skin_detail_light").
        width: Texture width in pixels.
        height: Texture height in pixels.
        texture_type: One of "diffuse", "normal", "sss_thickness",
                      "iris_detail", "hair_gradient".
        data: PNG-encoded bytes once generated (empty before generation).
        generated: Whether the texture has been generated.
    """

    name: str
    width: int = 1024
    height: int = 1024
    texture_type: str = "diffuse"
    data: bytes = b""
    generated: bool = False


# ═══════════════════════════════════════════════════════════════
# Helper functions — pure NumPy, no images yet
# ═══════════════════════════════════════════════════════════════

def _fade(t: np.ndarray) -> np.ndarray:
    """Smooth-step fade function: 6t⁵ - 15t⁴ + 10t³."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _perlin_noise_2d(
    shape: tuple[int, int],
    scale: float = 50.0,
    octaves: int = 4,
    seed: int = 42,
) -> np.ndarray:
    """Generate 2D Perlin-like noise using gradient interpolation.

    Args:
        shape: (height, width) output dimensions.
        scale: Frequency scale — lower = smoother, higher = more detail.
        octaves: Number of noise octaves to layer.
        seed: Random seed for reproducibility.

    Returns:
        np.ndarray of shape (h, w) with values in [0, 1].
    """
    rng = np.random.RandomState(seed)
    h, w = shape
    result = np.zeros((h, w), dtype=np.float64)
    amplitude = 1.0
    frequency = 1.0
    max_amplitude = 0.0

    for _ in range(octaves):
        cur_scale = scale / frequency
        # Gradient grid dimensions
        grid_w = max(int(np.ceil(w / cur_scale)) + 2, 2)
        grid_h = max(int(np.ceil(h / cur_scale)) + 2, 2)

        # Random gradient vectors at each grid point
        angles = rng.uniform(0, 2 * np.pi, (grid_h, grid_w))
        grad_x = np.cos(angles)
        grad_y = np.sin(angles)

        # Coordinate arrays
        ys = np.arange(h, dtype=np.float64) / cur_scale
        xs = np.arange(w, dtype=np.float64) / cur_scale

        # Integer grid coordinates
        yi = np.floor(ys).astype(np.int32)
        xi = np.floor(xs).astype(np.int32)

        # Fractional parts for interpolation
        yf = ys - yi
        xf = xs - xi

        # Smooth interpolation weights
        yf_smooth = _fade(yf)
        xf_smooth = _fade(xf)

        # Clamp grid indices
        yi_c = np.clip(yi, 0, grid_h - 2)
        xi_c = np.clip(xi, 0, grid_w - 2)

        # Dot products at four corners
        # For each pixel, look up gradients at the four surrounding grid points
        # and compute dot products with distance vectors
        oct_result = np.zeros((h, w), dtype=np.float64)

        for gy_offset in range(2):
            for gx_offset in range(2):
                # Grid indices for this corner
                gy = np.clip(yi_c + gy_offset, 0, grid_h - 1)
                gx = np.clip(xi_c + gx_offset, 0, grid_w - 1)

                # Distance vectors
                dy = yf - gy_offset
                dx = xf - gx_offset

                # Gradient lookups
                gx_vals = grad_x[gy[:, np.newaxis], gx[np.newaxis, :]]
                gy_vals = grad_y[gy[:, np.newaxis], gx[np.newaxis, :]]

                # Dot products
                # dy is (h,), dx is (w,), need outer product style
                dy_col = dy[:, np.newaxis]  # (h, 1)
                dx_row = dx[np.newaxis, :]   # (1, w)

                dots = gy_vals * dy_col + gx_vals * dx_row

                # Bilinear interpolation
                if gy_offset == 0:
                    y_weight = 1.0 - yf_smooth
                else:
                    y_weight = yf_smooth
                if gx_offset == 0:
                    x_weight = 1.0 - xf_smooth
                else:
                    x_weight = xf_smooth

                oct_result += dots * (y_weight[:, np.newaxis] * x_weight[np.newaxis, :])

        result += oct_result * amplitude
        max_amplitude += amplitude
        amplitude *= 0.5
        frequency *= 2.0

    # Normalize to [0, 1]
    if max_amplitude > 0:
        result = result / max_amplitude

    # Shift from [-1, 1] range to [0, 1]
    result = (result + 1.0) * 0.5
    result = np.clip(result, 0.0, 1.0)

    return result.astype(np.float32)


def _radial_gradient(
    shape: tuple[int, int],
    center: tuple[float, float] = (0.5, 0.5),
    inner_color: tuple[float, ...] = (1.0, 1.0, 1.0),
    outer_color: tuple[float, ...] = (0.0, 0.0, 0.0),
) -> np.ndarray:
    """Generate a radial gradient image.

    Args:
        shape: (height, width) output dimensions.
        center: (y_frac, x_frac) center of the gradient in [0,1] range.
        inner_color: RGB tuple at center, values in [0,1].
        outer_color: RGB tuple at edges, values in [0,1].

    Returns:
        np.ndarray of shape (h, w, 3) with float32 values in [0,1].
    """
    h, w = shape
    cy, cx = center

    # Distance from center, normalized to [0, 1]
    y_coords = np.linspace(0, 1, h, dtype=np.float32)
    x_coords = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

    # Aspect-corrected distance
    aspect = w / h
    dx = (xx - cx)
    dy = (yy - cy) * aspect
    dist = np.sqrt(dx * dx + dy * dy)
    dist = np.clip(dist / dist.max(), 0.0, 1.0) if dist.max() > 0 else dist

    # Interpolate colors
    inner = np.array(inner_color, dtype=np.float32)
    outer = np.array(outer_color, dtype=np.float32)

    result = np.zeros((h, w, len(inner_color)), dtype=np.float32)
    for c in range(len(inner_color)):
        result[:, :, c] = inner[c] + (outer[c] - inner[c]) * dist

    return np.clip(result, 0.0, 1.0)


def _height_to_normal(
    height_map: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray:
    """Convert a grayscale height map to a normal map via Sobel-like derivatives.

    Args:
        height_map: 2D array (h, w) with values in [0, 1].
        strength: Normal map strength multiplier (0.1–5.0 typical).

    Returns:
        np.ndarray of shape (h, w, 3) with values in [0, 255] as uint8.
        Normal map in OpenGL convention (Y-up): R=X, G=Y, B=Z.
    """
    if height_map.ndim == 3:
        gray = height_map[:, :, 0].astype(np.float64)
    else:
        gray = height_map.astype(np.float64)

    h, w = gray.shape

    # Sobel-like derivative kernels
    # X gradient (left minus right)
    dx = np.zeros_like(gray)
    dx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) * 0.5
    dx[:, 0] = gray[:, 1] - gray[:, 0]
    dx[:, -1] = gray[:, -1] - gray[:, -2]

    # Y gradient (bottom minus top)
    dy = np.zeros_like(gray)
    dy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) * 0.5
    dy[0, :] = gray[1, :] - gray[0, :]
    dy[-1, :] = gray[-1, :] - gray[-2, :]

    # Normal components: (dx, dy, 1/strength)
    inv_strength = 1.0 / max(strength, 0.001)
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(gray)

    # Normalize
    mag = np.sqrt(nx * nx + ny * ny + nz * nz)
    mag = np.where(mag == 0, 1.0, mag)
    nx /= mag
    ny /= mag
    nz /= mag

    # Map from [-1, 1] to [0, 255]
    normal = np.stack([
        np.clip((nx * 0.5 + 0.5) * 255, 0, 255),
        np.clip((ny * 0.5 + 0.5) * 255, 0, 255),
        np.clip((nz * 0.5 + 0.5) * 255, 0, 255),
    ], axis=2).astype(np.uint8)

    return normal


def _make_texture_image(
    width: int,
    height: int,
    channels: int = 3,
) -> np.ndarray:
    """Create a blank texture image array.

    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.
        channels: Number of color channels (3 for RGB, 4 for RGBA).

    Returns:
        np.ndarray of shape (height, width, channels) with zeros (black).
    """
    return np.zeros((height, width, channels), dtype=np.float32)


def _array_to_png(arr: np.ndarray) -> bytes:
    """Convert a NumPy array to PNG bytes.

    Args:
        arr: Array of shape (h, w) or (h, w, c) with dtype uint8 or float [0,1].

    Returns:
        PNG-encoded bytes.

    Raises:
        RuntimeError: If Pillow is not available.
    """
    if not PILLOW_AVAILABLE:
        raise RuntimeError(
            "Pillow is required for PNG encoding. "
            "Install with: pip install Pillow"
        )

    if arr.dtype != np.uint8:
        arr = np.clip(arr * 255, 0, 255).astype(np.uint8)

    if arr.ndim == 2:
        mode = "L"
        img = Image.fromarray(arr, mode=mode)
    elif arr.shape[2] == 3:
        img = Image.fromarray(arr, mode="RGB")
    elif arr.shape[2] == 4:
        img = Image.fromarray(arr, mode="RGBA")
    else:
        img = Image.fromarray(arr)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════
# ProceduralTexturePipeline
# ═══════════════════════════════════════════════════════════════

class ProceduralTexturePipeline:
    """Orchestrate procedural texture generation for all avatar channels.

    Pure-Python. No bpy dependency. NumPy + Pillow only.
    Every vertex, every pixel generated from math.
    """

    def __init__(self, resolution: int = 1024, seed: int = 42) -> None:
        """Initialize the pipeline.

        Args:
            resolution: Default texture resolution (width and height).
            seed: Random seed for reproducible textures.
        """
        self.resolution = resolution
        self.seed = seed

    # ── Skin Detail ─────────────────────────────────────────────

    def generate_skin_detail(self, spec: Optional[dict] = None) -> ProceduralTexture:
        """Generate a skin pore/detail texture map.

        Uses Perlin-like noise for micro-skin pore patterns overlaid
        with subtle variation for natural skin appearance.

        Args:
            spec: Optional dict with keys:
                - pore_density: float 0.0–1.0 (default 0.5)
                - pore_depth: float 0.0–1.0 (default 0.3)
                - include_freckles: bool (default False)
                - include_veins: bool (default False)
                - seed: int (default from pipeline)

        Returns:
            ProceduralTexture with PNG bytes, texture_type="diffuse".
        """
        if spec is None:
            spec = {}

        pore_density = spec.get("pore_density", 0.5)
        pore_depth = spec.get("pore_depth", 0.3)
        include_freckles = spec.get("include_freckles", False)
        include_veins = spec.get("include_veins", False)
        s = spec.get("seed", self.seed)
        w = spec.get("width", self.resolution)
        h = spec.get("height", self.resolution)

        # Pore noise — fine-scale detail
        # Lower scale = finer pores; density controls the scale
        scale = 15.0 + (1.0 - pore_density) * 50.0
        pore_noise = _perlin_noise_2d((h, w), scale=scale, octaves=5, seed=s)

        # Medium-scale skin variation
        skin_var = _perlin_noise_2d((h, w), scale=80.0, octaves=3, seed=s + 100)

        # Combine: pores are darker (indented), skin variation is gentle
        detail = 1.0 - pore_noise * pore_depth * 0.4
        detail = detail * (0.85 + skin_var * 0.15)

        if include_freckles:
            freckle_noise = _perlin_noise_2d((h, w), scale=25.0, octaves=2, seed=s + 200)
            # Freckles appear where noise is above threshold
            freckle_mask = (freckle_noise > 0.6).astype(np.float32)
            detail -= freckle_mask * 0.15

        if include_veins:
            vein_noise = _perlin_noise_2d((h, w), scale=120.0, octaves=4, seed=s + 300)
            # Veins are subtle blue-ish tint
            detail = detail[..., np.newaxis] if detail.ndim == 2 else detail
            if detail.ndim == 2:
                result = np.stack([detail, detail, detail], axis=2)
                # Add slight reddish vein tint
                vein_strength = np.clip((vein_noise - 0.55) * 3.0, 0, 1) * 0.08
                result[:, :, 0] += vein_strength * 0.3  # slight red
                result[:, :, 2] += vein_strength * 0.2  # slight blue
                detail = np.clip(result, 0, 1)

        detail = np.clip(detail, 0.0, 1.0)

        # Convert to 3-channel grayscale
        if detail.ndim == 2:
            detail = np.stack([detail, detail, detail], axis=2)

        name = spec.get("name", "skin_detail")
        tex = ProceduralTexture(
            name=name,
            width=w,
            height=h,
            texture_type="diffuse",
        )
        tex.data = _array_to_png((detail * 255).astype(np.uint8))
        tex.generated = True
        return tex

    # ── Skin Normal ─────────────────────────────────────────────

    def generate_skin_normal(self, spec: Optional[dict] = None) -> ProceduralTexture:
        """Generate a skin normal map from pore detail.

        Uses Perlin noise as height, then converts via Sobel derivative.

        Args:
            spec: Optional dict with keys:
                - normal_strength: float (default 0.5)
                - scale: float (default 40.0)
                - seed: int (default from pipeline)
                - width, height: texture dimensions

        Returns:
            ProceduralTexture with PNG bytes, texture_type="normal".
        """
        if spec is None:
            spec = {}

        strength = spec.get("normal_strength", 0.5)
        scale = spec.get("scale", 40.0)
        s = spec.get("seed", self.seed)
        w = spec.get("width", self.resolution)
        h = spec.get("height", self.resolution)

        height_map = _perlin_noise_2d((h, w), scale=scale, octaves=4, seed=s)
        normal_map = _height_to_normal(height_map, strength=strength)

        name = spec.get("name", "skin_normal")
        tex = ProceduralTexture(
            name=name,
            width=w,
            height=h,
            texture_type="normal",
        )
        tex.data = _array_to_png(normal_map)
        tex.generated = True
        return tex

    # ── SSS Thickness ──────────────────────────────────────────

    def generate_sss_thickness(self, spec: Optional[dict] = None) -> ProceduralTexture:
        """Generate a subsurface scattering thickness map.

        Thinner at extremities (ears, nose, fingers) — represented by
        lower values at edges. Thicker at torso center — higher values.

        Args:
            spec: Optional dict with keys:
                - base_thickness: float 0.0–1.0 (default 0.8)
                - edge_thin: float 0.0–1.0 (default 0.3)
                - seed: int (default from pipeline)
                - width, height: texture dimensions

        Returns:
            ProceduralTexture with PNG bytes, texture_type="sss_thickness".
        """
        if spec is None:
            spec = {}

        base = spec.get("base_thickness", 0.8)
        edge_thin = spec.get("edge_thin", 0.3)
        s = spec.get("seed", self.seed)
        w = spec.get("width", self.resolution)
        h = spec.get("height", self.resolution)

        # Radial falloff: thick at center, thin at edges
        shape = (h, w)
        center_y, center_x = 0.45, 0.5  # Slightly above center (torso)
        radial = _radial_gradient(
            shape,
            center=(center_y, center_x),
            inner_color=(base,),
            outer_color=(edge_thin,),
        )

        # Add organic noise for natural variation
        noise = _perlin_noise_2d(shape, scale=60.0, octaves=3, seed=s)
        variation = noise * 0.1 - 0.05  # ±0.05 variation

        thickness = np.clip(radial[:, :, 0] + variation, 0.0, 1.0)

        # Add slight variation for ears/nose zones (top-center thinning)
        top_noise = _perlin_noise_2d(shape, scale=30.0, octaves=2, seed=s + 500)
        # Thin at top 20% of texture (simulating ears/nose)
        y_gradient = np.linspace(1.0, 0.0, h, dtype=np.float32)
        top_mask = np.clip(1.0 - y_gradient[:, np.newaxis] * 2.5, 0.0, 1.0)
        thickness -= top_mask * top_noise * 0.1

        thickness = np.clip(thickness, 0.0, 1.0)

        # Convert to 3-channel grayscale
        result = np.stack([thickness, thickness, thickness], axis=2)

        name = spec.get("name", "sss_thickness")
        tex = ProceduralTexture(
            name=name,
            width=w,
            height=h,
            texture_type="sss_thickness",
        )
        tex.data = _array_to_png((result * 255).astype(np.uint8))
        tex.generated = True
        return tex

    # ── Eye Iris ────────────────────────────────────────────────

    def generate_eye_iris(self, spec: Optional[dict] = None) -> ProceduralTexture:
        """Generate a procedural iris texture with radial fibers.

        Creates a circular iris pattern with:
        - Radial fiber pattern (Perlin-based)
        - Limbal ring (darker outer ring)
        - Pupil (dark center)
        - Color variation from iris_color

        Args:
            spec: Optional dict with keys:
                - iris_color: (h, s, v) tuple in 0-1 range (default blue)
                - pupil_ratio: float (default 0.3, fraction of iris radius)
                - limbal_width: float (default 0.08, fraction of iris radius)
                - fiber_intensity: float (default 0.4)
                - seed: int (default from pipeline)
                - width, height: texture dimensions

        Returns:
            ProceduralTexture with PNG bytes, texture_type="iris_detail".
        """
        import colorsys

        if spec is None:
            spec = {}

        iris_hsv = spec.get("iris_color", (0.58, 0.65, 0.85))
        pupil_ratio = spec.get("pupil_ratio", 0.3)
        limbal_width = spec.get("limbal_width", 0.08)
        fiber_intensity = spec.get("fiber_intensity", 0.4)
        s = spec.get("seed", self.seed)
        w = spec.get("width", self.resolution)
        h = spec.get("height", self.resolution)

        # Base iris color in RGB [0,1]
        iris_r, iris_g, iris_b = colorsys.hsv_to_rgb(*iris_hsv)

        # Create coordinate grids
        y_coords = np.linspace(-1.0, 1.0, h, dtype=np.float32)
        x_coords = np.linspace(-1.0, 1.0, w, dtype=np.float32)
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

        # Distance from center and angle
        dist = np.sqrt(xx * xx + yy * yy)
        angle = np.arctan2(yy, xx)  # [-π, π]

        # Iris is in the unit circle, pupil_radius < iris_radius
        iris_radius = 0.85
        pupil_radius = pupil_ratio * iris_radius

        # Radial fiber pattern using angle-based noise
        # Scale angle to create fiber-like variation
        fiber_noise = _perlin_noise_2d(
            (h, w), scale=20.0, octaves=3, seed=s
        )

        # Modulate fibers along angular direction
        # Create thin radial streaks by combining angle and noise
        angular_mod = np.sin(angle * 12.0 + fiber_noise * 6.0) * 0.5 + 0.5
        radial_fibers = angular_mod * fiber_intensity

        # Blend with noise for organic feel
        detail_noise = _perlin_noise_2d(
            (h, w), scale=35.0, octaves=4, seed=s + 77
        )
        fiber_pattern = radial_fibers * 0.6 + detail_noise * 0.4

        # Iris color modulated by fibers
        iris_img = np.zeros((h, w, 3), dtype=np.float32)
        iris_img[:, :, 0] = iris_r + fiber_pattern * 0.15
        iris_img[:, :, 1] = iris_g + fiber_pattern * 0.10
        iris_img[:, :, 2] = iris_b + fiber_pattern * 0.08

        # Limbal ring: dark ring at outer edge of iris
        limbal_start = iris_radius - limbal_width
        limbal_mask = np.clip((dist - limbal_start) / limbal_width, 0.0, 1.0)
        limbal_mask = limbal_mask * np.clip((iris_radius - dist) / limbal_width, 0.0, 1.0)
        limbal_dark = 1.0 - limbal_mask * 0.6  # Darken by 60% in limbal zone

        # Also darken outside the iris
        outside_iris = (dist > iris_radius).astype(np.float32)
        # Black background outside iris

        # Pupil: dark center
        pupil_mask = np.clip((pupil_radius - dist) / 0.05, 0.0, 1.0)

        # Apply limbal ring
        iris_img[:, :, 0] *= limbal_dark
        iris_img[:, :, 1] *= limbal_dark
        iris_img[:, :, 2] *= limbal_dark

        # Apply pupil
        for c in range(3):
            iris_img[:, :, c] = iris_img[:, :, c] * (1.0 - pupil_mask) + 0.05 * pupil_mask

        # Sclera (white of eye) outside iris
        sclera_color = np.array([0.96, 0.96, 0.94], dtype=np.float32)
        for c in range(3):
            iris_img[:, :, c] = iris_img[:, :, c] * (1.0 - outside_iris) + sclera_color[c] * outside_iris

        iris_img = np.clip(iris_img, 0.0, 1.0)

        name = spec.get("name", "eye_iris")
        tex = ProceduralTexture(
            name=name,
            width=w,
            height=h,
            texture_type="iris_detail",
        )
        tex.data = _array_to_png((iris_img * 255).astype(np.uint8))
        tex.generated = True
        return tex

    # ── Hair Gradient ───────────────────────────────────────────

    def generate_hair_gradient(self, spec: Optional[dict] = None) -> ProceduralTexture:
        """Generate a hair strand tip-to-root gradient texture.

        Creates a vertical gradient from tips (top) to roots (bottom),
        with Perlin noise variation for natural strand differentiation.

        Args:
            spec: Optional dict with keys:
                - root_color: (r, g, b) tuple 0-1 range (default warm brown)
                - tip_color: (r, g, b) tuple 0-1 range (default blonde)
                - variation: float 0.0-1.0 noise amount (default 0.1)
                - seed: int (default from pipeline)
                - width, height: texture dimensions

        Returns:
            ProceduralTexture with PNG bytes, texture_type="hair_gradient".
        """
        if spec is None:
            spec = {}

        root_color = spec.get("root_color", (0.77, 0.64, 0.40))
        tip_color = spec.get("tip_color", (0.96, 0.90, 0.72))
        variation = spec.get("variation", 0.1)
        s = spec.get("seed", self.seed)
        w = spec.get("width", self.resolution)
        h = spec.get("height", self.resolution)

        # Vertical gradient: tips at top (y=0), roots at bottom (y=h)
        t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, np.newaxis]
        t = np.broadcast_to(t, (h, w))

        root_rgb = np.array(root_color, dtype=np.float32)
        tip_rgb = np.array(tip_color, dtype=np.float32)

        # Linear interpolation tip→root
        result = np.zeros((h, w, 3), dtype=np.float32)
        for c in range(3):
            result[:, :, c] = tip_rgb[c] + (root_rgb[c] - tip_rgb[c]) * t

        # Add Perlin noise for natural strand variation
        noise = _perlin_noise_2d((h, w), scale=15.0, octaves=4, seed=s)
        # Horizontal strand variation (fine noise)
        strand_noise = _perlin_noise_2d((h, w), scale=8.0, octaves=3, seed=s + 100)

        noise_3d = noise[:, :, np.newaxis]
        strand_3d = strand_noise[:, :, np.newaxis]

        result += (noise_3d * 2.0 - 1.0) * variation * 0.5
        result += (strand_3d * 2.0 - 1.0) * variation * 0.3

        result = np.clip(result, 0.0, 1.0)

        name = spec.get("name", "hair_gradient")
        tex = ProceduralTexture(
            name=name,
            width=w,
            height=h,
            texture_type="hair_gradient",
        )
        tex.data = _array_to_png((result * 255).astype(np.uint8))
        tex.generated = True
        return tex

    # ── Fabric Normal ───────────────────────────────────────────

    def generate_fabric_normal(self, spec: Optional[dict] = None) -> ProceduralTexture:
        """Generate a fabric weave normal map for clothing.

        Creates procedural normal maps for various fabric types:
        - cotton_weave: crosshatch weave pattern
        - silk: smooth with subtle sheen ripples
        - denim: diagonal twill weave
        - leather_grain: organic pebble grain
        - knit: V-shaped rib pattern

        Args:
            spec: Optional dict with keys:
                - pattern: str (default "cotton_weave")
                - strength: float (default 0.3)
                - seed: int (default from pipeline)
                - width, height: texture dimensions

        Returns:
            ProceduralTexture with PNG bytes, texture_type="normal".
        """
        if spec is None:
            spec = {}

        pattern = spec.get("pattern", "cotton_weave")
        strength = spec.get("strength", 0.3)
        s = spec.get("seed", self.seed)
        w = spec.get("width", self.resolution)
        h = spec.get("height", self.resolution)

        if pattern == "cotton_weave":
            height_map = self._fabric_cotton_weave(h, w, s)
        elif pattern == "silk":
            height_map = self._fabric_silk(h, w, s)
        elif pattern == "denim":
            height_map = self._fabric_denim(h, w, s)
        elif pattern == "leather_grain":
            height_map = self._fabric_leather(h, w, s)
        elif pattern == "knit":
            height_map = self._fabric_knit(h, w, s)
        else:
            # Default to cotton_weave for unknown patterns
            height_map = self._fabric_cotton_weave(h, w, s)

        normal_map = _height_to_normal(height_map, strength=strength)

        name = spec.get("name", f"fabric_normal_{pattern}")
        tex = ProceduralTexture(
            name=name,
            width=w,
            height=h,
            texture_type="normal",
        )
        tex.data = _array_to_png(normal_map)
        tex.generated = True
        return tex

    # ── Fabric pattern generators ───────────────────────────────

    def _fabric_cotton_weave(self, h: int, w: int, seed: int) -> np.ndarray:
        """Crosshatch weave pattern for cotton fabric."""
        x = np.linspace(0, 40, w, dtype=np.float32)
        y = np.linspace(0, 40, h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # Horizontal threads
        h_thread = np.abs(np.sin(yy * np.pi))
        # Vertical threads
        v_thread = np.abs(np.sin(xx * np.pi))

        # Weave: horizontal over, then vertical over
        weave = np.maximum(h_thread, v_thread) * 0.5 + 0.5

        # Add subtle noise
        noise = _perlin_noise_2d((h, w), scale=20.0, octaves=2, seed=seed)
        height = weave * 0.8 + noise * 0.2
        return np.clip(height, 0.0, 1.0)

    def _fabric_silk(self, h: int, w: int, seed: int) -> np.ndarray:
        """Smooth sheen with subtle ripples for silk."""
        noise1 = _perlin_noise_2d((h, w), scale=80.0, octaves=2, seed=seed)
        noise2 = _perlin_noise_2d((h, w), scale=120.0, octaves=1, seed=seed + 50)

        # Very subtle undulation
        height = 0.5 + noise1 * 0.15 + noise2 * 0.1
        return np.clip(height, 0.0, 1.0)

    def _fabric_denim(self, h: int, w: int, seed: int) -> np.ndarray:
        """Diagonal twill weave for denim."""
        x = np.linspace(0, 40, w, dtype=np.float32)
        y = np.linspace(0, 40, h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # Diagonal lines (twill)
        diagonal = np.sin((xx + yy) * np.pi * 0.5) * 0.5 + 0.5

        # Add noise for organic feel
        noise = _perlin_noise_2d((h, w), scale=25.0, octaves=2, seed=seed)
        height = diagonal * 0.7 + noise * 0.3
        return np.clip(height, 0.0, 1.0)

    def _fabric_leather(self, h: int, w: int, seed: int) -> np.ndarray:
        """Organic pebble grain for leather."""
        # Multi-scale noise for pebble grain
        fine = _perlin_noise_2d((h, w), scale=15.0, octaves=4, seed=seed)
        medium = _perlin_noise_2d((h, w), scale=40.0, octaves=3, seed=seed + 100)
        broad = _perlin_noise_2d((h, w), scale=100.0, octaves=2, seed=seed + 200)

        height = fine * 0.5 + medium * 0.3 + broad * 0.2
        return np.clip(height, 0.0, 1.0)

    def _fabric_knit(self, h: int, w: int, seed: int) -> np.ndarray:
        """V-shaped rib pattern for knit fabric."""
        x = np.linspace(0, 30, w, dtype=np.float32)
        y = np.linspace(0, 30, h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # V-rib pattern
        rib1 = np.abs(np.sin(yy * np.pi)) * 0.5
        # Staggered columns
        offset = (np.floor(xx / 2.0) % 2) * 0.5
        rib2 = np.abs(np.sin((yy + offset) * np.pi)) * 0.5

        height = np.maximum(rib1, rib2)

        # Add slight noise
        noise = _perlin_noise_2d((h, w), scale=30.0, octaves=2, seed=seed)
        height = height * 0.8 + noise * 0.2
        return np.clip(height, 0.0, 1.0)

    # ── Generate All ────────────────────────────────────────────

    def generate_all(self, spec: Optional[dict] = None) -> dict[str, ProceduralTexture]:
        """Generate the complete texture set for a character spec.

        Args:
            spec: Optional dict with custom parameters for each texture.
                  Keys should match generate method names:
                  - skin_detail, skin_normal, sss_thickness
                  - eye_iris, hair_gradient, fabric_normal

        Returns:
            Dictionary mapping texture names to ProceduralTexture objects.
            Keys: "skin_detail", "skin_normal", "sss_thickness",
                  "eye_iris", "hair_gradient", "fabric_normal"
        """
        if spec is None:
            spec = {}

        textures: dict[str, ProceduralTexture] = {}

        textures["skin_detail"] = self.generate_skin_detail(
            spec.get("skin_detail")
        )
        textures["skin_normal"] = self.generate_skin_normal(
            spec.get("skin_normal")
        )
        textures["sss_thickness"] = self.generate_sss_thickness(
            spec.get("sss_thickness")
        )
        textures["eye_iris"] = self.generate_eye_iris(
            spec.get("eye_iris")
        )
        textures["hair_gradient"] = self.generate_hair_gradient(
            spec.get("hair_gradient")
        )
        textures["fabric_normal"] = self.generate_fabric_normal(
            spec.get("fabric_normal")
        )

        return textures