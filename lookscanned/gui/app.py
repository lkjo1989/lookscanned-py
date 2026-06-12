"""GUI for lookscanned using PySide6."""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

import fitz
from PIL import Image

from ..effects import apply_scan_effects
from ..locale import get_lang, set_lang, tr
from ..scanner import ScanConfig, look_scanned

PREVIEW_DPI = 96
DEBOUNCE_MS = 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    if img.mode != "RGB":
        img = img.convert("RGB")
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


def _make_slider_row(
    label: str,
    lo: int,
    hi: int,
    default: int,
    *,
    fmt: "callable" = str,
) -> tuple[QHBoxLayout, QSlider, QLabel]:
    """Create ``[label |====slider====| value]``.

    Returns ``(row_layout, slider, value_label)`` — callers must add the
    layout to their parent themselves.
    """
    row = QHBoxLayout()

    lbl = QLabel(label)
    lbl.setFixedWidth(90)
    row.addWidget(lbl)

    slider = QSlider(Qt.Horizontal)
    slider.setRange(lo, hi)
    slider.setValue(default)
    row.addWidget(slider)

    val = QLabel(fmt(default))
    val.setFixedWidth(48)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(val)

    slider.valueChanged.connect(lambda v: val.setText(fmt(v)))  # type: ignore[attr-defined]

    return row, slider, val


# ---------------------------------------------------------------------------
# ImageLabel — auto-scaling preview pane
# ---------------------------------------------------------------------------

class ImageLabel(QLabel):
    """QLabel that displays a pixmap scaled to fit, keeping aspect ratio."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("preview.no_pdf"), parent)
        self._pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(180, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #f5f5f5; border: 1px solid #d0d0d0; border-radius: 4px;"
        )

    def setPixmap(self, pixmap: QPixmap) -> None:  # type: ignore[override]
        self._pixmap = pixmap
        self._redraw()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._redraw()

    def _redraw(self) -> None:
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            super().setPixmap(scaled)


# ---------------------------------------------------------------------------
# SettingsPanel — right-hand control panel
# ---------------------------------------------------------------------------

class SettingsPanel(QScrollArea):
    config_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # -- scan effects sliders --
        row, self._rotate_slider, self._rotate_label = _make_slider_row(
            tr("settings.rotate"), -100, 100, 1, fmt=lambda v: f"{v / 10:.1f}°"
        )
        layout.addLayout(row)

        row, self._variance_slider, self._variance_label = _make_slider_row(
            tr("settings.rotate_variance"), 0, 50, 3, fmt=lambda v: f"{v / 10:.1f}°"
        )
        layout.addLayout(row)

        row, self._blur_slider, self._blur_label = _make_slider_row(
            tr("settings.blur"), 0, 100, 30, fmt=lambda v: f"{v / 100:.2f}"
        )
        layout.addLayout(row)

        row, self._noise_slider, self._noise_label = _make_slider_row(
            tr("settings.noise"), 0, 100, 10, fmt=lambda v: f"{v / 100:.2f}"
        )
        layout.addLayout(row)

        row, self._brightness_slider, self._brightness_label = _make_slider_row(
            tr("settings.brightness"), 0, 200, 100, fmt=lambda v: f"{v / 100:.2f}"
        )
        layout.addLayout(row)

        row, self._contrast_slider, self._contrast_label = _make_slider_row(
            tr("settings.contrast"), 0, 200, 100, fmt=lambda v: f"{v / 100:.2f}"
        )
        layout.addLayout(row)

        row, self._yellowish_slider, self._yellowish_label = _make_slider_row(
            tr("settings.yellowish"), 0, 100, 8, fmt=lambda v: f"{v / 100:.2f}"
        )
        layout.addLayout(row)

        # -- checkboxes --
        checks = QHBoxLayout()
        self._grayscale_cb = QCheckBox(tr("settings.grayscale"))
        self._border_cb = QCheckBox(tr("settings.border"))
        self._border_cb.setChecked(True)
        checks.addWidget(self._grayscale_cb)
        checks.addWidget(self._border_cb)
        layout.addLayout(checks)

        # -- output options --
        out_grp = QGroupBox(tr("settings.output"))
        out_layout = QVBoxLayout(out_grp)

        row, self._scale_slider, self._scale_label = _make_slider_row(
            tr("settings.scale"), 25, 400, 100, fmt=lambda v: f"{v / 100:.2f}x"
        )
        out_layout.addLayout(row)

        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel(tr("settings.dpi")))
        self._dpi_combo = QComboBox()
        self._dpi_combo.addItems(["72", "96", "150", "200", "300"])
        self._dpi_combo.setCurrentText("150")
        dpi_row.addWidget(self._dpi_combo)
        dpi_row.addStretch()
        out_layout.addLayout(dpi_row)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel(tr("settings.format")))
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["jpeg", "png"])
        fmt_row.addWidget(self._fmt_combo)
        fmt_row.addStretch()
        out_layout.addLayout(fmt_row)

        layout.addWidget(out_grp)

        # -- watermark --
        wm_grp = QGroupBox(tr("settings.watermark"))
        wm_layout = QVBoxLayout(wm_grp)

        wm_text_row = QHBoxLayout()
        wm_text_row.addWidget(QLabel(tr("settings.watermark_text")))
        self._watermark_text = QLineEdit()
        self._watermark_text.setPlaceholderText("CONFIDENTIAL")
        wm_text_row.addWidget(self._watermark_text)
        wm_layout.addLayout(wm_text_row)

        row, self._watermark_x_slider, self._watermark_x_label = _make_slider_row(
            tr("settings.watermark_x"), 0, 100, 50, fmt=lambda v: f"{v / 100:.2f}"
        )
        wm_layout.addLayout(row)

        row, self._watermark_y_slider, self._watermark_y_label = _make_slider_row(
            tr("settings.watermark_y"), 0, 100, 50, fmt=lambda v: f"{v / 100:.2f}"
        )
        wm_layout.addLayout(row)

        row, self._watermark_size_slider, self._watermark_size_label = _make_slider_row(
            tr("settings.watermark_size"), 8, 120, 36, fmt=lambda v: f"{v}pt"
        )
        wm_layout.addLayout(row)

        row, self._watermark_opacity_slider, self._watermark_opacity_label = _make_slider_row(
            tr("settings.watermark_opacity"), 0, 100, 30, fmt=lambda v: f"{v / 100:.2f}"
        )
        wm_layout.addLayout(row)

        wm_color_row = QHBoxLayout()
        wm_color_row.addWidget(QLabel(tr("settings.watermark_color")))
        self._watermark_color = QLineEdit()
        self._watermark_color.setText("#000000")
        self._watermark_color.setFixedWidth(80)
        self._watermark_color.setPlaceholderText("#000000")
        wm_color_row.addWidget(self._watermark_color)
        wm_color_row.addStretch()
        wm_layout.addLayout(wm_color_row)

        layout.addWidget(wm_grp)

        # -- PDF metadata --
        meta_grp = QGroupBox(tr("settings.metadata"))
        meta_layout = QVBoxLayout(meta_grp)

        self._meta_title = self._add_meta_row(meta_layout, tr("settings.metadata.title"))
        self._meta_author = self._add_meta_row(meta_layout, tr("settings.metadata.author"))
        self._meta_subject = self._add_meta_row(meta_layout, tr("settings.metadata.subject"))
        self._meta_producer = self._add_meta_row(
            meta_layout, tr("settings.metadata.producer"), default="Adobe PDF Library"
        )
        self._meta_creator = self._add_meta_row(
            meta_layout, tr("settings.metadata.creator"), default="HP Scan"
        )
        self._meta_creation_date = self._add_meta_row(
            meta_layout, tr("settings.metadata.creation_date"), placeholder="2024-01-01T00:00:00"
        )
        self._meta_mod_date = self._add_meta_row(
            meta_layout, tr("settings.metadata.mod_date"), placeholder="2024-01-01T00:00:00"
        )

        layout.addWidget(meta_grp)
        layout.addStretch()

        self.setWidget(container)

        # wire signals → config_changed (via _notify so widget args
        # don't leak into the config_changed signal)
        for w in (
            self._rotate_slider, self._variance_slider, self._blur_slider,
            self._noise_slider, self._brightness_slider, self._contrast_slider,
            self._yellowish_slider, self._scale_slider,
            self._watermark_x_slider, self._watermark_y_slider,
            self._watermark_size_slider, self._watermark_opacity_slider,
        ):
            w.valueChanged.connect(self._notify_changed)  # type: ignore[attr-defined]
        for w in (self._grayscale_cb, self._border_cb):
            w.stateChanged.connect(self._notify_changed)  # type: ignore[attr-defined]
        for w in (self._dpi_combo, self._fmt_combo):
            w.currentTextChanged.connect(self._notify_changed)  # type: ignore[attr-defined]
        for w in (
            self._watermark_text, self._watermark_color,
            self._meta_title, self._meta_author, self._meta_subject,
            self._meta_producer, self._meta_creator,
            self._meta_creation_date, self._meta_mod_date,
        ):
            w.textChanged.connect(self._notify_changed)  # type: ignore[attr-defined]

    def _notify_changed(self, *_args: object) -> None:
        """Slot that swallows widget-specific arguments and emits config_changed."""
        self.config_changed.emit()

    @staticmethod
    def _add_meta_row(
        parent: QVBoxLayout,
        label: str,
        *,
        default: str = "",
        placeholder: str = "",
    ) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        edit.setText(default)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        row.addWidget(edit)
        parent.addLayout(row)
        return edit

    # -- config builder -------------------------------------------------------

    def build_config(self) -> ScanConfig:
        return ScanConfig(
            rotate=self._rotate_slider.value() / 10.0,
            rotate_variance=self._variance_slider.value() / 10.0,
            blur=self._blur_slider.value() / 100.0,
            noise=self._noise_slider.value() / 100.0,
            border=self._border_cb.isChecked(),
            grayscale=self._grayscale_cb.isChecked(),
            brightness=self._brightness_slider.value() / 100.0,
            yellowish=self._yellowish_slider.value() / 100.0,
            contrast=self._contrast_slider.value() / 100.0,
            scale=self._scale_slider.value() / 100.0,
            dpi=int(self._dpi_combo.currentText()),
            output_format=self._fmt_combo.currentText(),
            watermark_text=self._watermark_text.text(),
            watermark_x=self._watermark_x_slider.value() / 100.0,
            watermark_y=self._watermark_y_slider.value() / 100.0,
            watermark_font_size=self._watermark_size_slider.value(),
            watermark_opacity=self._watermark_opacity_slider.value() / 100.0,
            watermark_color=self._watermark_color.text() or "#000000",
            title=self._meta_title.text(),
            author=self._meta_author.text(),
            subject=self._meta_subject.text(),
            producer=self._meta_producer.text() or "Adobe PDF Library",
            creator=self._meta_creator.text() or "HP Scan",
            creation_date=self._meta_creation_date.text(),
            mod_date=self._meta_mod_date.text(),
        )


# ---------------------------------------------------------------------------
# GenerateWorker — background PDF generation
# ---------------------------------------------------------------------------

class GenerateWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        input_path: str,
        output_path: str,
        config: ScanConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._input = input_path
        self._output = output_path
        self._config = config

    def run(self) -> None:
        try:
            path = look_scanned(
                self._input,
                self._output,
                config=self._config,
                on_progress=lambda cur, tot: self.progress.emit(cur, tot),
            )
            self.finished.emit(path)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(960, 640)
        self.setAcceptDrops(True)

        self._pdf_doc: fitz.Document | None = None
        self._pdf_path: str = ""
        self._current_page: int = 0
        self._total_pages: int = 0
        self._original_image: Image.Image | None = None
        self._worker: GenerateWorker | None = None
        self._page_offsets: dict[int, float] = {}  # per-page random rotation

        # debounce timer for preview updates
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._update_preview)

        self._build_ui()
        self._update_ui_state()

    # -- UI construction ------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # top bar
        top = QHBoxLayout()
        self._select_btn = QPushButton(tr("file.select_pdf"))
        self._select_btn.clicked.connect(self._on_select_pdf)
        top.addWidget(self._select_btn)

        self._file_label = QLabel(tr("file.no_file"))
        self._file_label.setStyleSheet("color: #888;")
        top.addWidget(self._file_label)
        top.addStretch()
        root.addLayout(top)

        # middle: preview | settings
        splitter = QSplitter(Qt.Horizontal)

        # -- preview area --
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # page navigation
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedWidth(36)
        self._prev_btn.clicked.connect(lambda: self._navigate(-1))
        nav.addWidget(self._prev_btn)

        self._page_label = QLabel("1 / 1")
        self._page_label.setAlignment(Qt.AlignCenter)
        nav.addWidget(self._page_label)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedWidth(36)
        self._next_btn.clicked.connect(lambda: self._navigate(1))
        nav.addWidget(self._next_btn)
        preview_layout.addLayout(nav)

        # side-by-side preview
        side = QHBoxLayout()

        orig_col = QVBoxLayout()
        orig_col.addWidget(QLabel(tr("preview.original"), alignment=Qt.AlignCenter))
        self._orig_preview = ImageLabel()
        orig_col.addWidget(self._orig_preview)
        side.addLayout(orig_col)

        scan_col = QVBoxLayout()
        scan_col.addWidget(QLabel(tr("preview.scanned"), alignment=Qt.AlignCenter))
        self._scan_preview = ImageLabel()
        scan_col.addWidget(self._scan_preview)
        side.addLayout(scan_col)

        preview_layout.addLayout(side)
        splitter.addWidget(preview_widget)

        # -- settings panel --
        self._settings = SettingsPanel()
        self._settings.config_changed.connect(self._on_config_changed)
        splitter.addWidget(self._settings)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([620, 300])
        root.addWidget(splitter, 1)

        # bottom bar
        bottom = QHBoxLayout()
        self._status_label = QLabel(tr("status.ready"))
        bottom.addWidget(self._status_label)
        bottom.addStretch()

        self._progress = QProgressBar()
        self._progress.setFixedWidth(180)
        self._progress.setVisible(False)
        bottom.addWidget(self._progress)

        self._generate_btn = QPushButton(tr("button.generate"))
        self._generate_btn.setMinimumHeight(32)
        self._generate_btn.clicked.connect(self._on_generate)
        bottom.addWidget(self._generate_btn)
        root.addLayout(bottom)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    # -- PDF loading ----------------------------------------------------------

    def _on_select_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("file.select_pdf"), "", "PDF Files (*.pdf);;All Files (*)"
        )
        if path:
            self._load_pdf(path)

    def _load_pdf(self, path: str) -> None:
        try:
            doc = fitz.open(path)
        except Exception as exc:
            QMessageBox.warning(self, tr("error.warning"), tr("error.open_pdf", error=str(exc)))
            return

        if self._pdf_doc:
            self._pdf_doc.close()

        self._pdf_doc = doc
        self._pdf_path = path
        self._total_pages = doc.page_count
        self._current_page = 0
        self._original_image = None
        self._page_offsets.clear()

        self._file_label.setText(f"{Path(path).name}  ({tr('file.pages', count=doc.page_count)})")
        self._file_label.setStyleSheet("")
        self._render_current_page()
        self._update_preview()
        self._update_ui_state()

    def _render_current_page(self) -> None:
        if self._pdf_doc is None:
            return
        zoom = PREVIEW_DPI / 72.0
        page = self._pdf_doc[self._current_page]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        self._original_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self._orig_preview.setPixmap(_pil_to_qpixmap(self._original_image))

    # -- preview updates ------------------------------------------------------

    def _on_config_changed(self) -> None:
        # Settings changed — offsets may need regeneration (e.g. variance changed).
        self._page_offsets.pop(self._current_page, None)
        self._preview_timer.start()

    def _update_preview(self) -> None:
        if self._original_image is None:
            return
        config = self._settings.build_config()

        # per-page random rotation offset (stable per page until settings change)
        if config.rotate_variance > 0 and self._current_page not in self._page_offsets:
            self._page_offsets[self._current_page] = random.uniform(
                -config.rotate_variance, config.rotate_variance
            )
        page_rotate = config.rotate + self._page_offsets.get(self._current_page, 0.0)

        processed = apply_scan_effects(self._original_image.copy(), config, page_rotate)
        self._scan_preview.setPixmap(_pil_to_qpixmap(processed))

    # -- page navigation ------------------------------------------------------

    def _navigate(self, delta: int) -> None:
        if self._pdf_doc is None:
            return
        new_page = self._current_page + delta
        if 0 <= new_page < self._total_pages:
            self._current_page = new_page
            self._page_label.setText(f"{self._current_page + 1} / {self._total_pages}")
            self._render_current_page()
            self._update_preview()
            self._update_ui_state()

    # -- PDF generation -------------------------------------------------------

    def _on_generate(self) -> None:
        if self._pdf_doc is None:
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, tr("button.generate"),
            str(Path(self._pdf_path).with_name(
                Path(self._pdf_path).stem + "_scanned.pdf"
            )),
            "PDF Files (*.pdf)",
        )
        if not out_path:
            return

        if Path(self._pdf_path).resolve() == Path(out_path).resolve():
            QMessageBox.warning(self, tr("error.warning"), tr("error.output_same"))
            return

        config = self._settings.build_config()
        self._worker = GenerateWorker(self._pdf_path, out_path, config)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self._generate_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, self._total_pages)
        self._status_label.setText(tr("status.generating"))
        self._worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        self._progress.setValue(current)
        self._status_label.setText(tr("status.processing", current=current, total=total))

    def _on_finished(self, out_path: str) -> None:
        self._generate_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText(tr("status.done"))
        self._status_bar.showMessage(f"Saved: {out_path}", 8000)
        self._worker = None

    def _on_error(self, msg: str) -> None:
        self._generate_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText(tr("status.error"))
        QMessageBox.critical(self, tr("error.warning"), tr("error.generate", error=msg))
        self._worker = None

    # -- helpers --------------------------------------------------------------

    def _update_ui_state(self) -> None:
        has_pdf = self._pdf_doc is not None
        self._prev_btn.setEnabled(has_pdf and self._current_page > 0)
        self._next_btn.setEnabled(has_pdf and self._current_page < self._total_pages - 1)
        self._page_label.setText(
            f"{self._current_page + 1} / {self._total_pages}" if has_pdf else "1 / 1"
        )
        self._generate_btn.setEnabled(has_pdf)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self._load_pdf(path)
                break

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._pdf_doc:
            self._pdf_doc.close()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def launch() -> None:
    """Launch the Look Scanned GUI application."""
    # Auto-detect system language before building UI
    set_lang(get_lang())

    app = QApplication(sys.argv)
    app.setApplicationName("Look Scanned")
    app.setOrganizationName("lookscanned")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
