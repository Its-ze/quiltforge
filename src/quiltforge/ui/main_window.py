from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..engine import SUPPORTED_STYLES, generate_pattern
from ..exports import export_pdf, export_png, export_svg
from ..models import QuiltProject
from ..project_store import ProjectStore
from .widgets import PatternCanvas


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


class MainWindow(QMainWindow):
    def __init__(self, store: ProjectStore, resources: Path) -> None:
        super().__init__()
        self.store = store
        self.resources = resources
        self.project: QuiltProject | None = None
        self._loading_controls = False

        self.setWindowTitle("QuiltForge — Barn Quilt Studio")
        self.setMinimumSize(1120, 720)
        self.resize(1380, 860)
        icon_path = resources / "brand-art.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.regenerate_timer = QTimer(self)
        self.regenerate_timer.setSingleShot(True)
        self.regenerate_timer.timeout.connect(self.regenerate_pattern)

        root = QWidget(objectName="AppRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.home_page = self._build_home_page()
        self.editor_page = self._build_editor_page()
        self.howto_page = self._build_howto_page()
        self.about_page = self._build_about_page()
        for page in (self.home_page, self.editor_page, self.howto_page, self.about_page):
            self.pages.addWidget(page)
        shell.addWidget(self.pages, 1)

        self._build_menu()
        self.statusBar().showMessage("Ready — your projects stay on this computer")
        self.refresh_home()
        self.navigate(0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(objectName="Sidebar")
        sidebar.setFixedWidth(228)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 20)
        layout.setSpacing(8)

        brand_row = QHBoxLayout()
        logo = QLabel()
        pixmap = QPixmap(str(self.resources / "brand-art.png"))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setFixedSize(50, 50)
        brand_text = QVBoxLayout()
        name = QLabel("QuiltForge", objectName="BrandName")
        caption = QLabel("BARN QUILT STUDIO", objectName="BrandCaption")
        brand_text.addWidget(name)
        brand_text.addWidget(caption)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_text)
        layout.addLayout(brand_row)
        layout.addSpacing(24)

        self.nav_buttons: list[QPushButton] = []
        for index, text in enumerate(("Projects", "Designer", "How to use", "About")):
            button = QPushButton(text, objectName="NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self.navigate(page))
            layout.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[1].setEnabled(False)
        layout.addStretch(1)
        privacy = QLabel("OFFLINE BY DESIGN\nYour images stay private.", objectName="BrandCaption")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        return sidebar

    def _page_shell(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 30)
        layout.setSpacing(8)
        layout.addWidget(QLabel(title, objectName="PageTitle"))
        subtitle_label = QLabel(subtitle, objectName="PageSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
        layout.addSpacing(18)
        return page, layout

    def _build_home_page(self) -> QWidget:
        page, layout = self._page_shell(
            "What will you make today?",
            "Open a recent barn quilt or start from a favorite photo.",
        )
        actions = QHBoxLayout()
        new_button = QPushButton("Start a new project", objectName="PrimaryButton")
        new_button.clicked.connect(self.new_project)
        open_button = QPushButton("Open a .qforge project", objectName="SecondaryButton")
        open_button.clicked.connect(self.open_project_dialog)
        actions.addWidget(new_button)
        actions.addWidget(open_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addSpacing(18)
        recent_header = QHBoxLayout()
        recent_header.addWidget(QLabel("Recent projects", objectName="SectionTitle"))
        recent_header.addStretch(1)
        self.recent_count = QLabel("", objectName="Muted")
        recent_header.addWidget(self.recent_count)
        layout.addLayout(recent_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.recent_content = QWidget()
        self.recent_grid = QGridLayout(self.recent_content)
        self.recent_grid.setContentsMargins(0, 6, 6, 6)
        self.recent_grid.setHorizontalSpacing(16)
        self.recent_grid.setVerticalSpacing(16)
        scroll.setWidget(self.recent_content)
        layout.addWidget(scroll, 1)
        return page

    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(14)

        toolbar = QHBoxLayout()
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("Project name")
        self.project_name.setMinimumWidth(280)
        self.project_name.editingFinished.connect(self.rename_project)
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Pattern", "Original"])
        self.view_combo.currentTextChanged.connect(self._set_view_mode)
        save_button = QPushButton("Save", objectName="SecondaryButton")
        save_button.clicked.connect(self.save_project)
        self.export_button = QPushButton("Export", objectName="PrimaryButton")
        self.export_button.clicked.connect(self.show_export_menu)
        toolbar.addWidget(self.project_name)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel("View"))
        toolbar.addWidget(self.view_combo)
        toolbar.addWidget(save_button)
        toolbar.addWidget(self.export_button)
        outer.addLayout(toolbar)

        content = QHBoxLayout()
        content.setSpacing(18)
        canvas_panel = QFrame(objectName="Panel")
        canvas_layout = QVBoxLayout(canvas_panel)
        canvas_layout.setContentsMargins(12, 12, 12, 12)
        self.canvas = PatternCanvas()
        self.canvas.pattern_changed.connect(self._pattern_edited)
        canvas_layout.addWidget(self.canvas, 1)
        hint = QLabel("Tip: click any shape to cycle it through your paint palette.", objectName="Muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvas_layout.addWidget(hint)
        content.addWidget(canvas_panel, 1)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFixedWidth(330)
        settings_container = QWidget()
        settings = QVBoxLayout(settings_container)
        settings.setContentsMargins(4, 2, 4, 12)
        settings.setSpacing(12)
        settings.addWidget(self._settings_card("1  SHAPES", self._shape_settings()))
        settings.addWidget(self._settings_card("2  BOARD", self._board_settings()))
        self.palette_card_layout = QVBoxLayout()
        self.palette_card_layout.setSpacing(8)
        settings.addWidget(self._settings_card("3  PAINT PALETTE", self.palette_card_layout))
        generate_button = QPushButton("Rebuild pattern", objectName="PrimaryButton")
        generate_button.clicked.connect(self.regenerate_pattern)
        settings.addWidget(generate_button)
        settings.addStretch(1)
        settings_scroll.setWidget(settings_container)
        content.addWidget(settings_scroll)
        outer.addLayout(content, 1)
        return page

    def _settings_card(self, title: str, content_layout) -> QWidget:
        card = QFrame(objectName="Panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 15, 16, 16)
        layout.setSpacing(10)
        label = QLabel(title, objectName="SectionTitle")
        layout.addWidget(label)
        layout.addLayout(content_layout)
        return card

    def _shape_settings(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Pattern style", objectName="Muted"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(SUPPORTED_STYLES)
        self.style_combo.setToolTip("Blocks are simplest; Diamonds create the most traditional star geometry")
        self.style_combo.currentTextChanged.connect(self.schedule_regenerate)
        layout.addWidget(self.style_combo)
        layout.addWidget(QLabel("Grid detail", objectName="Muted"))
        self.grid_combo = QComboBox()
        self.grid_combo.addItems([str(value) for value in (4, 6, 8, 10, 12, 16, 20, 24)])
        self.grid_combo.currentTextChanged.connect(self.schedule_regenerate)
        layout.addWidget(self.grid_combo)
        layout.addWidget(QLabel("Number of paint colors", objectName="Muted"))
        self.palette_spin = QSpinBox()
        self.palette_spin.setRange(2, 12)
        self.palette_spin.setValue(6)
        self.palette_spin.valueChanged.connect(self.schedule_regenerate)
        layout.addWidget(self.palette_spin)
        return layout

    def _board_settings(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        row = QHBoxLayout()
        self.board_size = QDoubleSpinBox()
        self.board_size.setRange(6, 192)
        self.board_size.setDecimals(1)
        self.board_size.setValue(48)
        self.board_size.valueChanged.connect(self._save_display_settings)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["in", "cm"])
        self.units_combo.currentTextChanged.connect(self._save_display_settings)
        row.addWidget(self.board_size, 1)
        row.addWidget(self.units_combo)
        layout.addWidget(QLabel("Finished square size", objectName="Muted"))
        layout.addLayout(row)
        self.grid_check = QCheckBox("Show shape outlines")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self._save_display_settings)
        self.labels_check = QCheckBox("Show paint numbers")
        self.labels_check.setChecked(True)
        self.labels_check.toggled.connect(self._save_display_settings)
        layout.addWidget(self.grid_check)
        layout.addWidget(self.labels_check)
        return layout

    def _build_howto_page(self) -> QWidget:
        page, layout = self._page_shell(
            "How to use QuiltForge",
            "From photograph to a board-ready paint plan in five straightforward steps.",
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 12, 12)
        grid.setSpacing(16)
        steps = [
            ("1", "Choose a clear image", "Use a square-ish photo with strong shapes and a small number of important colors. Simple subjects make the boldest barn quilts."),
            ("2", "Pick your geometry", "Blocks are easiest to tape. Triangles add movement. Diamonds create classic star-like quilt structure."),
            ("3", "Balance detail and paint", "Start with an 8 × 8 grid and 5–7 colors. Increase detail only when an important feature is missing."),
            ("4", "Fine-tune the design", "Click a shape on the canvas to move it to the next palette color. Click a palette color to replace it everywhere."),
            ("5", "Export your build guide", "Save a PDF for measurements and numbered paint areas. PNG is ideal for sharing; SVG is best for crisp resizing."),
            ("✓", "Painting order", "Prime the board, draw the grid, tape one color family at a time, and paint light colors before dark colors. Let each layer dry fully."),
        ]
        for index, (number, title, text) in enumerate(steps):
            card = QFrame(objectName="Card")
            card_layout = QVBoxLayout(card)
            badge = QLabel(number)
            badge.setStyleSheet("background:#D6533D;color:white;border-radius:18px;font-size:14pt;font-weight:700;")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(38, 38)
            card_layout.addWidget(badge)
            card_layout.addWidget(QLabel(title, objectName="CardTitle"))
            description = QLabel(text, objectName="Muted")
            description.setWordWrap(True)
            card_layout.addWidget(description)
            card_layout.addStretch(1)
            grid.addWidget(card, index // 2, index % 2)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        return page

    def _build_about_page(self) -> QWidget:
        page, layout = self._page_shell(
            "About QuiltForge",
            "A practical design companion for barn quilt makers.",
        )
        card = QFrame(objectName="Panel")
        card.setMaximumWidth(760)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(26, 26, 26, 26)
        art = QLabel()
        pixmap = QPixmap(str(self.resources / "brand-art.png"))
        if not pixmap.isNull():
            art.setPixmap(pixmap.scaled(190, 190, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        art.setFixedSize(200, 200)
        card_layout.addWidget(art)
        text_layout = QVBoxLayout()
        text_layout.addWidget(QLabel("QuiltForge", objectName="PageTitle"))
        version = QLabel("Barn Quilt Studio • Version 1.0.0", objectName="Muted")
        text_layout.addWidget(version)
        description = QLabel(
            "QuiltForge turns your own images into clear, geometric, paint-by-number barn quilt patterns. "
            "It works entirely on your computer, so your source images remain private."
        )
        description.setWordWrap(True)
        text_layout.addWidget(description)
        text_layout.addSpacing(12)
        credit = QLabel(
            "Made by <b>Zach Skeens</b><br>"
            "In partnership with <b>ITSZ Studios</b><br>"
            "Maintained by <b>ITSolutions.Digital</b>"
        )
        credit.setTextFormat(Qt.TextFormat.RichText)
        text_layout.addWidget(credit)
        text_layout.addStretch(1)
        website = QPushButton("Visit itsolutions.digital", objectName="SecondaryButton")
        website.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://itsolutions.digital")))
        text_layout.addWidget(website, 0, Qt.AlignmentFlag.AlignLeft)
        card_layout.addLayout(text_layout, 1)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        return page

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        new_action = QAction("New project…", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        open_action = QAction("Open project…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project_dialog)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addActions([new_action, open_action, save_action])
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("Help")
        howto_action = QAction("How to use QuiltForge", self)
        howto_action.triggered.connect(lambda: self.navigate(2))
        about_action = QAction("About QuiltForge", self)
        about_action.triggered.connect(lambda: self.navigate(3))
        help_menu.addActions([howto_action, about_action])

    def navigate(self, index: int) -> None:
        if index == 1 and not self.project:
            index = 0
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
        if index == 0:
            self.refresh_home()

    def refresh_home(self) -> None:
        _clear_layout(self.recent_grid)
        recent = self.store.recent()
        self.recent_count.setText(f"{len(recent)} saved" if recent else "No saved projects yet")
        if not recent:
            empty = QFrame(objectName="Panel")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(30, 48, 30, 48)
            title = QLabel("Your first project starts with one image", objectName="CardTitle")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body = QLabel("Choose a photo and QuiltForge will turn it into a paintable geometric plan.", objectName="Muted")
            body.setAlignment(Qt.AlignmentFlag.AlignCenter)
            start = QPushButton("Choose an image", objectName="PrimaryButton")
            start.clicked.connect(self.new_project)
            empty_layout.addWidget(title)
            empty_layout.addWidget(body)
            empty_layout.addSpacing(10)
            empty_layout.addWidget(start, 0, Qt.AlignmentFlag.AlignHCenter)
            self.recent_grid.addWidget(empty, 0, 0, 1, 3)
            return

        for index, (project, path) in enumerate(recent):
            self.recent_grid.addWidget(self._project_card(project, path), index // 3, index % 3)
        self.recent_grid.setRowStretch((len(recent) + 2) // 3, 1)

    def _project_card(self, project: QuiltProject, path: Path) -> QWidget:
        card = QFrame(objectName="Card")
        card.setMinimumWidth(235)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 14)
        preview = QLabel()
        preview.setFixedHeight(145)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(project.source_image)
        if not pixmap.isNull():
            preview.setPixmap(pixmap.scaled(240, 145, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        preview.setStyleSheet("background:#E8E2D7;border-radius:9px;")
        layout.addWidget(preview)
        layout.addWidget(QLabel(project.name, objectName="CardTitle"))
        try:
            updated = datetime.fromisoformat(project.updated_at).astimezone().strftime("Updated %b %d, %Y")
        except ValueError:
            updated = "Saved project"
        details = QLabel(f"{project.style} • {project.grid_size} × {project.grid_size}\n{updated}", objectName="Muted")
        layout.addWidget(details)
        open_button = QPushButton("Open project", objectName="SecondaryButton")
        open_button.clicked.connect(lambda checked=False, target=path: self.open_project(target))
        layout.addWidget(open_button)
        return card

    def new_project(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Choose an image for your barn quilt",
            str(Path.home() / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;All files (*.*)",
        )
        if not source:
            return
        suggested = Path(source).stem.replace("_", " ").replace("-", " ").title()
        name, accepted = QInputDialog.getText(self, "Name your project", "Project name:", text=suggested)
        if not accepted:
            return
        try:
            self.project = self.store.create(name, source)
            self.nav_buttons[1].setEnabled(True)
            self.load_project_controls()
            self.navigate(1)
            self.regenerate_pattern()
        except Exception as exc:
            QMessageBox.critical(self, "Could not create project", str(exc))

    def open_project_dialog(self) -> None:
        target, _ = QFileDialog.getOpenFileName(
            self,
            "Open a QuiltForge project",
            str(self.store.projects_dir),
            "QuiltForge projects (*.qforge)",
        )
        if target:
            self.open_project(Path(target))

    def open_project(self, path: Path) -> None:
        try:
            self.project = self.store.load(path)
            self.nav_buttons[1].setEnabled(True)
            self.load_project_controls()
            self.navigate(1)
            self.statusBar().showMessage(f"Opened {self.project.name}", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Could not open project", str(exc))

    def load_project_controls(self) -> None:
        if not self.project:
            return
        self._loading_controls = True
        self.project_name.setText(self.project.name)
        self.style_combo.setCurrentText(self.project.style)
        self.grid_combo.setCurrentText(str(self.project.grid_size))
        self.palette_spin.setValue(self.project.palette_size)
        self.board_size.setValue(self.project.board_size)
        self.units_combo.setCurrentText(self.project.units)
        self.grid_check.setChecked(self.project.show_grid)
        self.labels_check.setChecked(self.project.show_labels)
        self.canvas.set_source(self.project.source_image)
        self.canvas.set_pattern(self.project.pattern)
        self.canvas.show_grid = self.project.show_grid
        self.canvas.show_labels = self.project.show_labels
        self._loading_controls = False
        self.refresh_palette()

    def rename_project(self) -> None:
        if not self.project:
            return
        name = self.project_name.text().strip()
        if name:
            self.project.name = name
            self.save_project(quiet=True)

    def schedule_regenerate(self, *_args) -> None:
        if not self.project or self._loading_controls:
            return
        self.regenerate_timer.start(350)

    def regenerate_pattern(self) -> None:
        if not self.project:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.statusBar().showMessage("Building your pattern…")
        try:
            self.project.style = self.style_combo.currentText()
            self.project.grid_size = int(self.grid_combo.currentText())
            self.project.palette_size = self.palette_spin.value()
            self.project.pattern = generate_pattern(
                self.project.source_image,
                self.project.grid_size,
                self.project.palette_size,
                self.project.style,
            )
            self.canvas.set_pattern(self.project.pattern)
            self.refresh_palette()
            self.save_project(quiet=True)
            shape_count = len(self.project.pattern.shapes)
            self.statusBar().showMessage(f"Pattern ready — {shape_count} paintable shapes, {len(self.project.pattern.palette)} colors", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Pattern could not be generated", str(exc))
            self.statusBar().showMessage("Pattern generation failed", 4000)
        finally:
            QApplication.restoreOverrideCursor()

    def refresh_palette(self) -> None:
        _clear_layout(self.palette_card_layout)
        if not self.project or not self.project.pattern:
            label = QLabel("Build the pattern to see its colors.", objectName="Muted")
            label.setWordWrap(True)
            self.palette_card_layout.addWidget(label)
            return
        for index, color in enumerate(self.project.pattern.palette):
            row = QHBoxLayout()
            swatch = QPushButton(str(index + 1))
            swatch.setFixedSize(42, 34)
            qcolor = QColor(color)
            text = "#102A43" if (0.299 * qcolor.red() + 0.587 * qcolor.green() + 0.114 * qcolor.blue()) > 155 else "white"
            swatch.setStyleSheet(
                f"QPushButton{{background:{color};color:{text};border:1px solid #9A9184;border-radius:7px;font-weight:700;}}"
            )
            swatch.setToolTip("Replace this paint color everywhere")
            swatch.clicked.connect(lambda checked=False, palette_index=index: self.change_palette_color(palette_index))
            code = QLabel(color)
            code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(swatch)
            row.addWidget(code)
            row.addStretch(1)
            self.palette_card_layout.addLayout(row)

    def change_palette_color(self, index: int) -> None:
        if not self.project or not self.project.pattern:
            return
        current = QColor(self.project.pattern.palette[index])
        selected = QColorDialog.getColor(current, self, f"Choose paint color {index + 1}")
        if selected.isValid():
            self.project.pattern.palette[index] = selected.name().upper()
            self.canvas.update()
            self.refresh_palette()
            self.save_project(quiet=True)

    def _pattern_edited(self) -> None:
        self.save_project(quiet=True)
        self.statusBar().showMessage("Shape color changed — project autosaved", 2500)

    def _set_view_mode(self, mode: str) -> None:
        self.canvas.set_view_mode(mode)

    def _save_display_settings(self, *_args) -> None:
        if not self.project or self._loading_controls:
            return
        self.project.board_size = self.board_size.value()
        self.project.units = self.units_combo.currentText()
        self.project.show_grid = self.grid_check.isChecked()
        self.project.show_labels = self.labels_check.isChecked()
        self.canvas.show_grid = self.project.show_grid
        self.canvas.show_labels = self.project.show_labels
        self.canvas.update()
        self.save_project(quiet=True)

    def save_project(self, _checked=False, quiet: bool = False) -> None:
        if not self.project:
            if not quiet:
                self.statusBar().showMessage("No project is open", 2500)
            return
        try:
            self.store.save(self.project)
            if not quiet:
                self.statusBar().showMessage("Project saved", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Could not save project", str(exc))

    def show_export_menu(self) -> None:
        menu = QMenu(self)
        png = menu.addAction("High-resolution PNG")
        svg = menu.addAction("Scalable SVG")
        pdf = menu.addAction("Printable PDF build guide")
        chosen = menu.exec(self.export_button.mapToGlobal(self.export_button.rect().bottomLeft()))
        if chosen == png:
            self.export_project("png")
        elif chosen == svg:
            self.export_project("svg")
        elif chosen == pdf:
            self.export_project("pdf")

    def export_project(self, kind: str) -> None:
        if not self.project or not self.project.pattern:
            QMessageBox.information(self, "Nothing to export", "Build a pattern first.")
            return
        suggested = f"{self.project.name.replace(' ', '-')}-paint-plan.{kind}"
        filters = {"png": "PNG image (*.png)", "svg": "SVG vector (*.svg)", "pdf": "PDF guide (*.pdf)"}
        target, _ = QFileDialog.getSaveFileName(self, f"Export {kind.upper()}", str(Path.home() / "Downloads" / suggested), filters[kind])
        if not target:
            return
        if not target.lower().endswith(f".{kind}"):
            target += f".{kind}"
        try:
            {"png": export_png, "svg": export_svg, "pdf": export_pdf}[kind](self.project, target)
            self.statusBar().showMessage(f"Exported {Path(target).name}", 5000)
            QMessageBox.information(self, "Export complete", f"Your file is ready:\n{target}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.save_project(quiet=True)
        event.accept()
