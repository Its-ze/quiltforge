from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .models import Pattern, Shape


STYLE_BLOCKS = "Blocks"
STYLE_TRIANGLES = "Triangles"
STYLE_DIAMONDS = "Diamonds"
SUPPORTED_STYLES = (STYLE_BLOCKS, STYLE_TRIANGLES, STYLE_DIAMONDS)


def _hex(rgb: tuple[int, int, int] | np.ndarray) -> str:
    r, g, b = (int(v) for v in rgb[:3])
    return f"#{r:02X}{g:02X}{b:02X}"


def _rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def _nearest_color(sample: np.ndarray, palette: list[np.ndarray]) -> int:
    # Weighted distance tracks human brightness perception better than raw RGB.
    weights = np.array([0.30, 0.59, 0.11], dtype=np.float32)
    distances = [float(np.sum(weights * np.square(sample - color))) for color in palette]
    return int(np.argmin(distances))


def _extract_palette(image: Image.Image, count: int) -> list[str]:
    preview = image.resize((256, 256), Image.Resampling.LANCZOS)
    quantized = preview.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    raw_palette = quantized.getpalette() or []
    usage = Counter(quantized.getdata())
    colors: list[tuple[int, tuple[int, int, int]]] = []
    for index, frequency in usage.most_common(count):
        start = index * 3
        rgb = tuple(raw_palette[start : start + 3])
        if len(rgb) == 3:
            colors.append((frequency, rgb))
    # Stable frequency order keeps the most important paint colors first.
    return [_hex(rgb) for _, rgb in colors]


def _average(region: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    pixels = region.reshape(-1, 3) if mask is None else region[mask]
    if pixels.size == 0:
        pixels = region.reshape(-1, 3)
    return pixels.astype(np.float32).mean(axis=0)


def _shape(points: list[tuple[float, float]], color: int, label: str) -> Shape:
    return Shape(points=points, color_index=color, label=label)


def generate_pattern(
    image_path: str | Path,
    grid_size: int = 8,
    palette_size: int = 6,
    style: str = STYLE_TRIANGLES,
) -> Pattern:
    """Convert an image into grid-snapped, paintable geometric polygons."""
    if grid_size < 2 or grid_size > 32:
        raise ValueError("Grid size must be between 2 and 32")
    if palette_size < 2 or palette_size > 16:
        raise ValueError("Palette size must be between 2 and 16")
    if style not in SUPPORTED_STYLES:
        raise ValueError(f"Unsupported style: {style}")

    with Image.open(image_path) as opened:
        original_size = opened.size
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image = ImageOps.fit(image, (768, 768), method=Image.Resampling.LANCZOS)

    palette_hex = _extract_palette(image, palette_size)
    palette_rgb = [_rgb(color) for color in palette_hex]
    pixels = np.asarray(image)
    cell = pixels.shape[0] / grid_size
    shapes: list[Shape] = []
    label_number = 1

    for row in range(grid_size):
        for col in range(grid_size):
            y0 = round(row * cell)
            y1 = round((row + 1) * cell)
            x0 = round(col * cell)
            x1 = round((col + 1) * cell)
            region = pixels[y0:y1, x0:x1]
            h, w, _ = region.shape
            yy, xx = np.mgrid[0:h, 0:w]
            left, top = col / grid_size, row / grid_size
            right, bottom = (col + 1) / grid_size, (row + 1) / grid_size
            center = ((left + right) / 2, (top + bottom) / 2)

            def add(points: list[tuple[float, float]], mask: np.ndarray | None = None) -> None:
                nonlocal label_number
                index = _nearest_color(_average(region, mask), palette_rgb)
                shapes.append(_shape(points, index, str(label_number)))
                label_number += 1

            if style == STYLE_BLOCKS:
                add([(left, top), (right, top), (right, bottom), (left, bottom)])
            elif style == STYLE_TRIANGLES:
                if (row + col) % 2 == 0:
                    add([(left, top), (right, top), (right, bottom)], yy <= (h / max(w, 1)) * xx)
                    add([(left, top), (right, bottom), (left, bottom)], yy >= (h / max(w, 1)) * xx)
                else:
                    add([(left, top), (right, top), (left, bottom)], yy <= h - (h / max(w, 1)) * xx)
                    add([(right, top), (right, bottom), (left, bottom)], yy >= h - (h / max(w, 1)) * xx)
            else:
                # Four triangles per cell create the classic diamond/star vocabulary.
                add([(left, top), (right, top), center], yy <= h / 2 - np.abs(xx - w / 2) * h / max(w, 1))
                add([(right, top), (right, bottom), center], xx >= w / 2 + np.abs(yy - h / 2) * w / max(h, 1))
                add([(right, bottom), (left, bottom), center], yy >= h / 2 + np.abs(xx - w / 2) * h / max(w, 1))
                add([(left, bottom), (left, top), center], xx <= w / 2 - np.abs(yy - h / 2) * w / max(h, 1))

    return Pattern(
        grid_size=grid_size,
        style=style,
        palette=palette_hex,
        shapes=shapes,
        source_width=original_size[0],
        source_height=original_size[1],
    )


def color_usage(pattern: Pattern) -> list[tuple[int, str, int]]:
    counts = Counter(shape.color_index for shape in pattern.shapes)
    return [(index + 1, color, counts[index]) for index, color in enumerate(pattern.palette)]

