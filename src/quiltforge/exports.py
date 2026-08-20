from __future__ import annotations

import html
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .engine import color_usage
from .models import Pattern, QuiltProject


NAVY = "#102A43"
CREAM = "#FFF9ED"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _text_color(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    r, g, b = [int(value[i : i + 2], 16) for i in (0, 2, 4)]
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#102A43" if luminance > 155 else "#FFFFFF"


def render_pattern(
    pattern: Pattern,
    size: int = 2400,
    show_grid: bool = True,
    show_labels: bool = True,
) -> Image.Image:
    image = Image.new("RGB", (size, size), CREAM)
    draw = ImageDraw.Draw(image)
    line_width = max(1, size // 800)
    font = _font(max(10, int(size / max(pattern.grid_size, 4) * 0.19)))

    for shape in pattern.shapes:
        points = [(round(x * size), round(y * size)) for x, y in shape.points]
        fill = pattern.palette[shape.color_index]
        draw.polygon(points, fill=fill)
        if show_grid:
            draw.line(points + [points[0]], fill=NAVY, width=line_width, joint="curve")
        if show_labels:
            cx = sum(x for x, _ in points) / len(points)
            cy = sum(y for _, y in points) / len(points)
            label = str(shape.color_index + 1)
            box = draw.textbbox((0, 0), label, font=font)
            draw.text(
                (cx - (box[2] - box[0]) / 2, cy - (box[3] - box[1]) / 2),
                label,
                fill=_text_color(fill),
                font=font,
                stroke_width=max(0, line_width // 2),
                stroke_fill=fill,
            )
    draw.rectangle((0, 0, size - 1, size - 1), outline=NAVY, width=max(3, size // 300))
    return image


def export_png(project: QuiltProject, target: str | Path) -> Path:
    if not project.pattern:
        raise ValueError("Generate a pattern before exporting")
    target = Path(target)
    render_pattern(project.pattern, 3000, project.show_grid, project.show_labels).save(target, "PNG")
    return target


def export_svg(project: QuiltProject, target: str | Path) -> Path:
    if not project.pattern:
        raise ValueError("Generate a pattern before exporting")
    pattern = project.pattern
    target = Path(target)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200">',
        f'<title>{html.escape(project.name)}</title>',
        f'<rect width="1200" height="1200" fill="{CREAM}"/>',
    ]
    for shape in pattern.shapes:
        points = " ".join(f"{x * 1200:.2f},{y * 1200:.2f}" for x, y in shape.points)
        stroke = NAVY if project.show_grid else "none"
        lines.append(
            f'<polygon points="{points}" fill="{pattern.palette[shape.color_index]}" '
            f'stroke="{stroke}" stroke-width="1.5" stroke-linejoin="round"/>'
        )
        if project.show_labels:
            cx = sum(point[0] for point in shape.points) / len(shape.points) * 1200
            cy = sum(point[1] for point in shape.points) / len(shape.points) * 1200
            fill = _text_color(pattern.palette[shape.color_index])
            lines.append(
                f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" dominant-baseline="central" '
                f'font-family="Segoe UI, sans-serif" font-size="14" font-weight="700" fill="{fill}">'
                f'{shape.color_index + 1}</text>'
            )
    lines.append(f'<rect x="2" y="2" width="1196" height="1196" fill="none" stroke="{NAVY}" stroke-width="4"/>')
    lines.append("</svg>")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _register_pdf_fonts() -> tuple[str, str]:
    regular, bold = "Helvetica", "Helvetica-Bold"
    segoe = Path("C:/Windows/Fonts/segoeui.ttf")
    segoe_bold = Path("C:/Windows/Fonts/seguisb.ttf")
    try:
        if segoe.exists():
            pdfmetrics.registerFont(TTFont("SegoeUI", str(segoe)))
            regular = "SegoeUI"
        if segoe_bold.exists():
            pdfmetrics.registerFont(TTFont("SegoeUISemibold", str(segoe_bold)))
            bold = "SegoeUISemibold"
    except Exception:
        pass
    return regular, bold


def export_pdf(project: QuiltProject, target: str | Path) -> Path:
    if not project.pattern:
        raise ValueError("Generate a pattern before exporting")
    target = Path(target)
    regular, bold = _register_pdf_fonts()
    c = canvas.Canvas(str(target), pagesize=letter, pageCompression=1)
    width, height = letter
    navy = colors.HexColor(NAVY)
    cream = colors.HexColor(CREAM)
    terracotta = colors.HexColor("#D6533D")

    # Page 1: complete paint-by-number plan.
    c.setFillColor(cream)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(navy)
    c.setFont(bold, 22)
    c.drawString(0.55 * inch, height - 0.62 * inch, project.name)
    c.setFont(regular, 10)
    c.setFillColor(colors.HexColor("#52677A"))
    cell_measurement = project.board_size / project.grid_size
    c.drawString(
        0.55 * inch,
        height - 0.88 * inch,
        f"{project.board_size:g} {project.units} board • {project.pattern.grid_size} × {project.pattern.grid_size} grid • "
        f"{cell_measurement:.2f} {project.units} per grid square • {project.pattern.style}",
    )
    art_size = 6.7 * inch
    art_x = (width - art_size) / 2
    art_y = height - 1.25 * inch - art_size
    _draw_pdf_pattern(c, project, art_x, art_y, art_size)
    c.setFillColor(navy)
    c.setFont(bold, 11)
    c.drawString(0.55 * inch, 0.48 * inch, "QuiltForge Paint Plan")
    c.setFont(regular, 8)
    c.setFillColor(colors.HexColor("#6B7D8C"))
    c.drawRightString(width - 0.55 * inch, 0.48 * inch, "Measure twice • Tape carefully • Paint light colors first")
    c.showPage()

    # Page 2: palette and measuring guide.
    c.setFillColor(cream)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(navy)
    c.setFont(bold, 22)
    c.drawString(0.6 * inch, height - 0.7 * inch, "Paint & measuring guide")
    c.setFont(regular, 10)
    c.setFillColor(colors.HexColor("#52677A"))
    c.drawString(0.6 * inch, height - 0.94 * inch, "Match each number on the plan to its paint color below.")

    y = height - 1.35 * inch
    for number, hex_color, shape_count in color_usage(project.pattern):
        c.setFillColor(colors.HexColor(hex_color))
        c.roundRect(0.65 * inch, y - 0.18 * inch, 0.42 * inch, 0.42 * inch, 5, fill=1, stroke=0)
        c.setFillColor(navy)
        c.setFont(bold, 11)
        c.drawString(1.22 * inch, y, f"Paint {number}")
        c.setFont(regular, 10)
        c.drawString(2.15 * inch, y, hex_color)
        c.setFillColor(colors.HexColor("#6B7D8C"))
        c.drawRightString(width - 0.7 * inch, y, f"{shape_count} shapes")
        y -= 0.55 * inch

    y -= 0.12 * inch
    c.setStrokeColor(colors.HexColor("#D9E1E7"))
    c.line(0.65 * inch, y, width - 0.65 * inch, y)
    y -= 0.35 * inch
    c.setFillColor(navy)
    c.setFont(bold, 13)
    c.drawString(0.65 * inch, y, "Layout marks")
    c.setFont(regular, 10)
    c.setFillColor(colors.HexColor("#52677A"))
    y -= 0.28 * inch
    c.drawString(0.65 * inch, y, f"Board: {project.board_size:g} {project.units} square")
    y -= 0.22 * inch
    c.drawString(0.65 * inch, y, f"Grid spacing: {cell_measurement:.3f} {project.units}")
    y -= 0.22 * inch
    c.drawString(0.65 * inch, y, "Mark the same spacing from every edge, then connect opposite marks with a straightedge.")
    y -= 0.38 * inch
    marks = [cell_measurement * index for index in range(1, project.grid_size)]
    chunks = [marks[index : index + 8] for index in range(0, len(marks), 8)]
    c.setFont(bold, 9)
    c.setFillColor(terracotta)
    c.drawString(0.65 * inch, y, "Measure from the left and top edges:")
    c.setFont(regular, 9)
    c.setFillColor(navy)
    for chunk in chunks:
        y -= 0.2 * inch
        c.drawString(0.82 * inch, y, "  •  ".join(f"{mark:.3f}".rstrip("0").rstrip(".") for mark in chunk) + f" {project.units}")

    c.setFont(regular, 8)
    c.setFillColor(colors.HexColor("#6B7D8C"))
    c.drawString(0.65 * inch, 0.48 * inch, "Screen colors vary. Test real paint on scrap material before painting the board.")
    c.save()
    return target


def _draw_pdf_pattern(c: canvas.Canvas, project: QuiltProject, x: float, y: float, size: float) -> None:
    pattern = project.pattern
    assert pattern is not None
    for shape in pattern.shapes:
        path = c.beginPath()
        first_x, first_y = shape.points[0]
        path.moveTo(x + first_x * size, y + (1 - first_y) * size)
        for px, py in shape.points[1:]:
            path.lineTo(x + px * size, y + (1 - py) * size)
        path.close()
        c.setFillColor(colors.HexColor(pattern.palette[shape.color_index]))
        c.setStrokeColor(colors.HexColor(NAVY) if project.show_grid else colors.transparent)
        c.setLineWidth(0.35)
        c.drawPath(path, fill=1, stroke=int(project.show_grid))
        if project.show_labels:
            cx = x + sum(px for px, _ in shape.points) / len(shape.points) * size
            cy = y + (1 - sum(py for _, py in shape.points) / len(shape.points)) * size
            c.setFillColor(colors.HexColor(_text_color(pattern.palette[shape.color_index])))
            c.setFont("Helvetica-Bold", max(4, min(8, 42 / pattern.grid_size)))
            c.drawCentredString(cx, cy - 2, str(shape.color_index + 1))
    c.setStrokeColor(colors.HexColor(NAVY))
    c.setLineWidth(2)
    c.rect(x, y, size, size, fill=0, stroke=1)

