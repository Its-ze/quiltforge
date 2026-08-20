from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from .models import Pattern, Shape


STYLE_BLOCKS = "Blocks"
STYLE_TRIANGLES = "Triangles"
STYLE_DIAMONDS = "Diamonds"
SUPPORTED_STYLES = (STYLE_BLOCKS, STYLE_TRIANGLES, STYLE_DIAMONDS)

COLOR_BOLD = "Bold & clean"
COLOR_BALANCED = "Balanced"
COLOR_NATURAL = "Natural"
SUPPORTED_COLOR_STYLES = (COLOR_BOLD, COLOR_BALANCED, COLOR_NATURAL)

FRAMING_CROP = "Crop to square"
FRAMING_FIT = "Fit full image"
SUPPORTED_FRAMING = (FRAMING_CROP, FRAMING_FIT)


def _hex(rgb: tuple[int, int, int] | np.ndarray) -> str:
    r, g, b = (int(v) for v in rgb[:3])
    return f"#{r:02X}{g:02X}{b:02X}"


def _rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def _oklab(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB values to OKLab for perceptually useful color distances."""
    values = np.asarray(rgb, dtype=np.float32) / 255.0
    linear = np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)
    r, g, b = np.moveaxis(linear, -1, 0)
    l = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return np.stack(
        (
            0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
        ),
        axis=-1,
    )


def _extract_palette(image: Image.Image, count: int) -> list[str]:
    preview = image.resize((256, 256), Image.Resampling.LANCZOS)
    # Start with extra candidates, then pick colors that are both common and
    # clearly separated. This avoids a palette full of similar muddy midtones.
    quantized = preview.quantize(
        colors=min(64, max(count * 8, 24)),
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    )
    raw_palette = quantized.getpalette() or []
    usage = Counter(quantized.getdata())
    candidates: list[tuple[int, tuple[int, int, int]]] = []
    for index, frequency in usage.most_common():
        start = index * 3
        rgb = tuple(raw_palette[start : start + 3])
        if len(rgb) == 3:
            candidates.append((frequency, rgb))
    if not candidates:
        return ["#000000"] * count

    selected = [candidates[0]]
    maximum_frequency = candidates[0][0]
    while len(selected) < count and len(selected) < len(candidates):
        remaining = [candidate for candidate in candidates if candidate not in selected]

        def score(candidate: tuple[int, tuple[int, int, int]]) -> float:
            frequency, rgb = candidate
            color = _oklab(np.asarray(rgb))
            separation = min(float(np.linalg.norm(color - _oklab(np.asarray(chosen)))) for _, chosen in selected)
            return (frequency / maximum_frequency) ** 0.35 * separation

        selected.append(max(remaining, key=score))
    return [_hex(rgb) for _, rgb in selected]


def _dominant_color(region: np.ndarray, palette: list[np.ndarray], mask: np.ndarray | None = None) -> int:
    pixels = region.reshape(-1, 3) if mask is None else region[mask]
    if pixels.size == 0:
        pixels = region.reshape(-1, 3)
    # Majority voting creates solid, intentional paint areas instead of muddy
    # averages at photographic edges.
    sample = pixels[:: max(1, len(pixels) // 4096)]
    sample_lab = _oklab(sample)
    palette_lab = _oklab(np.asarray(palette))
    distances = np.sum(np.square(sample_lab[:, None, :] - palette_lab[None, :, :]), axis=2)
    nearest = np.argmin(distances, axis=1)
    return int(np.bincount(nearest, minlength=len(palette)).argmax())


def _prepare_image(image: Image.Image, color_style: str, framing: str) -> Image.Image:
    if framing == FRAMING_FIT:
        fitted = ImageOps.contain(image, (768, 768), method=Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (768, 768), "#FFF9ED")
        canvas.paste(fitted, ((768 - fitted.width) // 2, (768 - fitted.height) // 2))
        image = canvas
    else:
        image = ImageOps.fit(image, (768, 768), method=Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image, cutoff=1)
    saturation = {COLOR_NATURAL: 1.0, COLOR_BALANCED: 1.22, COLOR_BOLD: 1.45}[color_style]
    return ImageEnhance.Color(image).enhance(saturation)


def _shape(points: list[tuple[float, float]], color: int, label: str) -> Shape:
    return Shape(points=points, color_index=color, label=label)


def generate_pattern(
    image_path: str | Path,
    grid_size: int = 8,
    palette_size: int = 6,
    style: str = STYLE_TRIANGLES,
    color_style: str = COLOR_BOLD,
    framing: str = FRAMING_CROP,
) -> Pattern:
    """Convert an image into grid-snapped, paintable geometric polygons."""
    if grid_size < 2 or grid_size > 32:
        raise ValueError("Grid size must be between 2 and 32")
    if palette_size < 2 or palette_size > 16:
        raise ValueError("Palette size must be between 2 and 16")
    if style not in SUPPORTED_STYLES:
        raise ValueError(f"Unsupported style: {style}")
    if color_style not in SUPPORTED_COLOR_STYLES:
        raise ValueError(f"Unsupported color style: {color_style}")
    if framing not in SUPPORTED_FRAMING:
        raise ValueError(f"Unsupported framing: {framing}")

    with Image.open(image_path) as opened:
        original_size = opened.size
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image = _prepare_image(image, color_style, framing)

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
                index = _dominant_color(region, palette_rgb, mask)
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
