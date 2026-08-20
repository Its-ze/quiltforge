from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..models import Pattern


class PatternCanvas(QWidget):
    pattern_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.pattern: Pattern | None = None
        self.source_path: str = ""
        self.source_pixmap: QPixmap | None = None
        self.view_mode = "Pattern"
        self.show_grid = True
        self.show_labels = True
        self.setMinimumSize(420, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click a shape to move it to the next paint color")

    def set_source(self, path: str) -> None:
        self.source_path = path
        self.source_pixmap = QPixmap(path) if Path(path).exists() else None
        self.update()

    def set_pattern(self, pattern: Pattern | None) -> None:
        self.pattern = pattern
        self.update()

    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        self.update()

    def _art_rect(self) -> QRectF:
        margin = 24
        side = max(10, min(self.width(), self.height()) - margin * 2)
        return QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#E8E2D7"))
        rect = self._art_rect()
        painter.setPen(QPen(QColor("#D2C8B8"), 1))
        painter.setBrush(QColor("#FFFDF8"))
        painter.drawRoundedRect(rect.adjusted(-7, -7, 7, 7), 7, 7)

        if self.view_mode == "Original" and self.source_pixmap and not self.source_pixmap.isNull():
            scaled = self.source_pixmap.scaled(
                int(rect.width()), int(rect.height()), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            crop_x = max(0, (scaled.width() - int(rect.width())) // 2)
            crop_y = max(0, (scaled.height() - int(rect.height())) // 2)
            painter.drawPixmap(rect.toRect(), scaled, QRectF(crop_x, crop_y, rect.width(), rect.height()).toRect())
        elif self.pattern:
            self._paint_pattern(painter, rect)
        else:
            painter.setPen(QColor("#738391"))
            font = painter.font()
            font.setPointSize(13)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Import an image to begin")

        painter.setPen(QPen(QColor("#102A43"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    def _paint_pattern(self, painter: QPainter, rect: QRectF) -> None:
        assert self.pattern is not None
        line_width = 0.75 if self.pattern.grid_size <= 12 else 0.45
        font = QFont("Segoe UI", max(5, min(9, round(55 / self.pattern.grid_size))), QFont.Weight.Bold)
        painter.setFont(font)
        for shape in self.pattern.shapes:
            polygon = QPolygonF([
                QPointF(rect.left() + x * rect.width(), rect.top() + y * rect.height()) for x, y in shape.points
            ])
            color = QColor(self.pattern.palette[shape.color_index])
            painter.setBrush(color)
            painter.setPen(QPen(QColor("#102A43"), line_width) if self.show_grid else Qt.PenStyle.NoPen)
            painter.drawPolygon(polygon)
            if self.show_labels and rect.width() / self.pattern.grid_size >= 24:
                center = polygon.boundingRect().center()
                luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
                painter.setPen(QColor("#102A43") if luminance > 155 else QColor("white"))
                painter.drawText(QRectF(center.x() - 12, center.y() - 9, 24, 18), Qt.AlignmentFlag.AlignCenter, str(shape.color_index + 1))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or not self.pattern or self.view_mode != "Pattern":
            return super().mousePressEvent(event)
        rect = self._art_rect()
        if not rect.contains(event.position()):
            return
        normalized = QPointF(
            (event.position().x() - rect.left()) / rect.width(),
            (event.position().y() - rect.top()) / rect.height(),
        )
        for shape in reversed(self.pattern.shapes):
            polygon = QPolygonF([QPointF(x, y) for x, y in shape.points])
            if polygon.containsPoint(normalized, Qt.FillRule.WindingFill):
                shape.color_index = (shape.color_index + 1) % len(self.pattern.palette)
                self.pattern_changed.emit()
                self.update()
                return

