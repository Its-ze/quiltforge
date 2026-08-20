from pathlib import Path

from PIL import Image

from quiltforge.engine import (
    COLOR_BOLD,
    FRAMING_FIT,
    STYLE_BLOCKS,
    STYLE_DIAMONDS,
    STYLE_TRIANGLES,
    generate_pattern,
)


def sample_image(path: Path) -> Path:
    image = Image.new("RGB", (120, 80), "#D6533D")
    for x in range(60, 120):
        for y in range(80):
            image.putpixel((x, y), (20, 60, 90) if y < 40 else (242, 184, 75))
    image.save(path)
    return path


def test_generates_each_supported_geometry(tmp_path: Path) -> None:
    source = sample_image(tmp_path / "source.png")
    expected_multiplier = {STYLE_BLOCKS: 1, STYLE_TRIANGLES: 2, STYLE_DIAMONDS: 4}
    for style, multiplier in expected_multiplier.items():
        pattern = generate_pattern(source, grid_size=6, palette_size=3, style=style)
        assert pattern.grid_size == 6
        assert len(pattern.palette) == 3
        assert len(pattern.shapes) == 36 * multiplier
        assert all(0 <= shape.color_index < 3 for shape in pattern.shapes)
        assert all(0 <= coordinate <= 1 for shape in pattern.shapes for point in shape.points for coordinate in point)


def test_rejects_invalid_settings(tmp_path: Path) -> None:
    source = sample_image(tmp_path / "source.png")
    for kwargs in (
        {"grid_size": 1},
        {"grid_size": 33},
        {"palette_size": 1},
        {"palette_size": 17},
        {"style": "Circles"},
        {"color_style": "Muddy"},
        {"framing": "Stretch"},
    ):
        try:
            generate_pattern(source, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")


def test_bold_palette_keeps_source_colors_separate(tmp_path: Path) -> None:
    source = sample_image(tmp_path / "source.png")
    pattern = generate_pattern(
        source,
        grid_size=4,
        palette_size=3,
        style=STYLE_BLOCKS,
        color_style=COLOR_BOLD,
        framing=FRAMING_FIT,
    )
    colors = [tuple(int(color[index : index + 2], 16) for index in (1, 3, 5)) for color in pattern.palette]
    assert any(red > blue * 1.5 for red, _green, blue in colors)
    assert any(blue > red * 1.5 for red, _green, blue in colors)
    assert len(set(shape.color_index for shape in pattern.shapes)) == 3
