"""
Texture Forge — Procedural texture generation via Pillow + NumPy.

The Texture Forge is independent. It needs no Blender, no GPU,
no Cycles. It runs on Pi 5 ARM64 with just Pillow and NumPy.

HSV shifts, procedural patterns, gradient maps — all here.
"""

from __future__ import annotations

import colorsys
import logging
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image

from hamr.core.models import SkinSpec, HairColorSpec
from hamr.core.constants import TEXTURE_SIZE, TEXTURE_BLEND_FACTOR

logger = logging.getLogger("hamr.textures")


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color (#RRGGBB) to RGB tuple (0-255)."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def hex_to_hsv(hex_color: str) -> Tuple[float, float, float]:
    """Convert hex color (#RRGGBB) to HSV tuple (0-1 range)."""
    r, g, b = hex_to_rgb(hex_color)
    r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
    return colorsys.rgb_to_hsv(r_f, g_f, b_f)


def hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convert HSV (0-1 range) to hex color (#RRGGBB)."""
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def shift_hsv(
    image: Image.Image,
    hue_shift: float = 0.0,
    sat_shift: float = 0.0,
    val_shift: float = 0.0,
    blend: float = TEXTURE_BLEND_FACTOR,
) -> Image.Image:
    """
    Shift the HSV values of an image.

    Args:
        image: PIL Image to shift (will be converted to RGB).
        hue_shift: Hue rotation in degrees (0-360, wraps around).
        sat_shift: Saturation multiplier (1.0 = no change, >1 = more saturated).
        val_shift: Value/brightness multiplier (1.0 = no change, >1 = brighter).
        blend: Blend factor between original and shifted (0.0 = original, 1.0 = shifted).

    Returns:
        New PIL Image with shifted colors.
    """
    img = image.convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0

    # Convert RGB to HSV
    # Pillow doesn't have HSV, so we use colorsys channel-by-channel
    # But numpy vectorization is faster — compute manually
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Compute max, min, delta
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc

    # Hue
    h = np.zeros_like(maxc)
    mask_r = (maxc == r) & (delta > 0)
    mask_g = (maxc == g) & (delta > 0)
    mask_b = (maxc == b) & (delta > 0)

    h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
    h[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2
    h[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4
    h = h / 6.0  # Normalize to 0-1

    # Saturation
    s = np.where(maxc > 0, delta / maxc, 0.0)

    # Value
    v = maxc

    # Apply shifts (additive for hue since it's circular)
    h_shift_norm = (hue_shift / 360.0) % 1.0
    h_new = (h + h_shift_norm) % 1.0
    s_new = np.clip(s * sat_shift, 0.0, 1.0)
    v_new = np.clip(v * val_shift, 0.0, 1.0)

    # Blend original and shifted
    h_out = h + (h_new - h) * blend
    s_out = s + (s_new - s) * blend
    v_out = v + (v_new - v) * blend

    # Wrap hue
    h_out = h_out % 1.0

    # HSV back to RGB
    # Use numpy vectorized conversion
    i = (h_out * 6.0).astype(np.int32) % 6
    f = (h_out * 6.0) - np.floor(h_out * 6.0)
    p = v_out * (1.0 - s_out)
    q = v_out * (1.0 - s_out * f)
    t = v_out * (1.0 - s_out * (1.0 - f))

    # D-014: HSV→RGB boundary fix — h6 can equal exactly 6.0 when h=1.0
    # This is handled by the % 6 above (i = (h*6) % 6)
    r_out = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                      [v_out, q, p, p, t, v_out], default=v_out)
    g_out = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                      [t, v_out, v_out, q, p, p], default=v_out)
    b_out = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                      [p, p, t, v_out, v_out, q], default=v_out)

    result = np.stack([
        np.clip(r_out * 255, 0, 255).astype(np.uint8),
        np.clip(g_out * 255, 0, 255).astype(np.uint8),
        np.clip(b_out * 255, 0, 255).astype(np.uint8),
    ], axis=2)

    return Image.fromarray(result)


def tint_texture(
    base_image: Image.Image,
    target_hex: str,
    blend: float = TEXTURE_BLEND_FACTOR,
) -> Image.Image:
    """
    Tint a texture image toward a target color using HSV blending.

    This preserves the tonal variation of the original while shifting
    the overall color toward the target. A blend of 0.75 means 75%
    target color, 25% original variation.

    Args:
        base_image: Original texture (e.g., skin, hair base).
        target_hex: Target hex color (#RRGGBB).
        blend: Blend factor (0.0 = original, 1.0 = full tint).

    Returns:
        Tinted PIL Image.
    """
    target_h, target_s, target_v = hex_to_hsv(target_hex)

    # Calculate hue shift from neutral (0.0) to target
    # Since we want to TINT toward the color, we shift hue
    # and boost saturation/value toward the target
    img = base_image.convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc

    # Current HSV
    h = np.zeros_like(maxc)
    mask = delta > 0
    mask_r = mask & (maxc == r)
    mask_g = mask & (maxc == g)
    mask_b = mask & (maxc == b)

    h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
    h[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2
    h[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4
    h = h / 6.0

    s = np.where(maxc > 0, delta / maxc, 0.0)
    v = maxc

    # Blend toward target
    h_out = h + (target_h - h) * blend
    s_out = s + (target_s - s) * blend * 1.2  # Boost saturation slightly
    v_out = v + (target_v - v) * blend * 0.3  # Gentle value shift

    h_out = h_out % 1.0
    s_out = np.clip(s_out, 0.0, 1.0)
    v_out = np.clip(v_out, 0.0, 1.0)

    # HSV to RGB (vectorized)
    i = (h_out * 6.0).astype(np.int32) % 6
    f = (h_out * 6.0) - np.floor(h_out * 6.0)
    p = v_out * (1.0 - s_out)
    q = v_out * (1.0 - s_out * f)
    t = v_out * (1.0 - s_out * (1.0 - f))

    r_out = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                      [v_out, q, p, p, t, v_out], default=v_out)
    g_out = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                      [t, v_out, v_out, q, p, p], default=v_out)
    b_out = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                      [p, p, t, v_out, v_out, q], default=v_out)

    result = np.stack([
        np.clip(r_out * 255, 0, 255).astype(np.uint8),
        np.clip(g_out * 255, 0, 255).astype(np.uint8),
        np.clip(b_out * 255, 0, 255).astype(np.uint8),
    ], axis=2)

    return Image.fromarray(result)


def generate_gradient_texture(
    width: int = TEXTURE_SIZE,
    height: int = TEXTURE_SIZE,
    color_top: str = "#FFFFFF",
    color_bottom: str = "#000000",
    direction: str = "vertical",
) -> Image.Image:
    """
    Generate a gradient texture from two hex colors.

    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.
        color_top: Top (or left) color.
        color_bottom: Bottom (or right) color.
        direction: "vertical" or "horizontal".

    Returns:
        PIL Image with gradient.
    """
    top_rgb = hex_to_rgb(color_top)
    bot_rgb = hex_to_rgb(color_bottom)

    arr = np.zeros((height, width, 3), dtype=np.uint8)

    if direction == "vertical":
        for y in range(height):
            t = y / max(height - 1, 1)
            arr[y, :, 0] = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
            arr[y, :, 1] = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
            arr[y, :, 2] = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)
    else:
        for x in range(width):
            t = x / max(width - 1, 1)
            arr[:, x, 0] = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
            arr[:, x, 1] = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
            arr[:, x, 2] = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)

    return Image.fromarray(arr)


def generate_skin_texture(spec: SkinSpec, size: int = TEXTURE_SIZE) -> Image.Image:
    """
    Generate a procedural skin base texture from a SkinSpec.

    Creates a base skin tone with undertone variation.
    """
    base_rgb = hex_to_rgb(spec.base_hex)
    arr = np.full((size, size, 3), base_rgb, dtype=np.uint8)

    # Add subtle random variation for natural skin
    noise = np.random.randint(-8, 9, (size, size, 3), dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return Image.fromarray(arr)


def generate_hair_texture(spec: HairColorSpec, size: int = TEXTURE_SIZE) -> Image.Image:
    """
    Generate a procedural hair strand texture from root to tip.

    Creates a vertical gradient following the hair's color spec.
    """
    return generate_gradient_texture(
        width=size,
        height=size,
        color_top=spec.tips,     # Tips at top
        color_bottom=spec.roots,  # Roots at bottom
        direction="vertical",
    )