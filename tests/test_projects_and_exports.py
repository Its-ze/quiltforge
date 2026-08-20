import json
from pathlib import Path

from PIL import Image

from quiltforge.engine import generate_pattern
from quiltforge.exports import export_pdf, export_png, export_svg
from quiltforge.project_store import ProjectStore


def test_project_round_trip_and_exports(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    Image.new("RGB", (160, 120), "#2E7D80").save(source)
    store = ProjectStore(tmp_path / "data")
    project = store.create("My Barn Star", source)
    project.pattern = generate_pattern(project.source_image, 4, 3, "Triangles")
    project.show_labels = True
    project_path = store.save(project)

    loaded = store.load(project_path)
    assert loaded.name == "My Barn Star"
    assert loaded.pattern is not None
    assert len(store.recent()) == 1
    assert json.loads(project_path.read_text(encoding="utf-8"))["pattern"]["style"] == "Triangles"

    png = export_png(loaded, tmp_path / "plan.png")
    svg = export_svg(loaded, tmp_path / "plan.svg")
    pdf = export_pdf(loaded, tmp_path / "plan.pdf")
    assert png.stat().st_size > 1_000
    assert "<polygon" in svg.read_text(encoding="utf-8")
    assert pdf.read_bytes().startswith(b"%PDF")

