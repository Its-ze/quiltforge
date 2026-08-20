from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Shape:
    """A paintable polygon using coordinates normalized from 0 to 1."""

    points: list[tuple[float, float]]
    color_index: int
    label: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shape":
        return cls(
            points=[(float(x), float(y)) for x, y in data["points"]],
            color_index=int(data["color_index"]),
            label=str(data.get("label", "")),
        )


@dataclass
class Pattern:
    grid_size: int
    style: str
    palette: list[str]
    shapes: list[Shape]
    source_width: int
    source_height: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pattern":
        return cls(
            grid_size=int(data["grid_size"]),
            style=str(data["style"]),
            palette=list(data["palette"]),
            shapes=[Shape.from_dict(item) for item in data["shapes"]],
            source_width=int(data.get("source_width", 0)),
            source_height=int(data.get("source_height", 0)),
        )


@dataclass
class QuiltProject:
    id: str
    name: str
    source_image: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    grid_size: int = 8
    palette_size: int = 6
    style: str = "Triangles"
    color_style: str = "Bold & clean"
    framing: str = "Crop to square"
    board_size: float = 48.0
    units: str = "in"
    show_grid: bool = True
    show_labels: bool = False
    pattern: Pattern | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pattern"] = self.pattern.to_dict() if self.pattern else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuiltProject":
        raw_pattern = data.get("pattern")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            source_image=str(data["source_image"]),
            created_at=str(data.get("created_at", utc_now())),
            updated_at=str(data.get("updated_at", utc_now())),
            grid_size=int(data.get("grid_size", 8)),
            palette_size=int(data.get("palette_size", 6)),
            style=str(data.get("style", "Triangles")),
            color_style=str(data.get("color_style", "Bold & clean")),
            framing=str(data.get("framing", "Crop to square")),
            board_size=float(data.get("board_size", 48.0)),
            units=str(data.get("units", "in")),
            show_grid=bool(data.get("show_grid", True)),
            show_labels=bool(data.get("show_labels", False)),
            pattern=Pattern.from_dict(raw_pattern) if raw_pattern else None,
        )
