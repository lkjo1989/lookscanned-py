# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

Python project that makes clean PDFs look like they were physically scanned. Provides CLI, library API, and PySide6 GUI. All processing is local — no data leaves the machine.

### Commands

```sh
# CLI (works without pip install — current dir is on sys.path)
python -m lookscanned input.pdf --rotate 0.1 --blur 0.3 --noise 0.1 --border --yellowish 0.08
python -m lookscanned input.pdf -g --border   # grayscale + border

# GUI (requires PySide6)
python -m lookscanned.gui

# Install for persistent console scripts
pip install -e ".[gui]"
lookscanned input.pdf
lookscanned-gui
```

### Architecture

```
lookscanned/
  __init__.py      # Public API: look_scanned(), ScanConfig, get_lang(), set_lang(), tr()
  scanner.py       # Core pipeline: fitz render → effects → fitz output
  effects.py       # Per-page image transforms (Pillow + numpy)
  __main__.py      # argparse CLI
  locale/
    __init__.py    # Locale detection (en/zh) + tr() translation function
    en.py          # English strings
    zh.py          # Chinese (Simplified) strings
  gui/
    __init__.py    # Exports launch(), MainWindow
    __main__.py    # python -m lookscanned.gui entry
    app.py         # All PySide6 widgets: MainWindow, SettingsPanel, ImageLabel, GenerateWorker
```

### Processing pipeline

```
PDF → pymupdf renders pages at (dpi × scale) DPI
    → apply_scan_effects(img, config, page_rotate)
    → pymupdf assembles with metadata
```

**Effect order matters** for realistic output:
`rotation → grayscale → blur → brightness → contrast → yellowish → noise → border → watermark`

Effects in `effects.py` follow a composable pattern: each `_apply_*` function takes a PIL `Image` and returns one. New effects slot into `apply_scan_effects` by adding the call at the desired pipeline position. All effect parameters live on `ScanConfig`.

### Key design details

- **Per-page rotation variance**: Each page gets `base_rotate + random.uniform(-variance, +variance)`. The GUI stores offsets per page index in `_page_offsets` so a page shows consistent rotation when you navigate back to it. Offsets are cleared when settings change so the preview updates correctly.
- **GUI preview**: uses 96 DPI for speed, 200ms debounce timer on settings changes. Original page image is cached; only effects are reapplied.
- **GUI settings panel**: Slider values are stored as ints (e.g. rotate 0.1° → slider value 1, yellowish 0.08 → slider value 8). `build_config()` converts back to floats.
- **PDF generation** runs in a `GenerateWorker(QThread)` so the UI stays responsive.
- **GUI slider defaults** (different from `ScanConfig` dataclass defaults): rotate=0.1°, rotate_variance=0.3°, blur=0.30, noise=0.10, border=on, yellowish=0.08, grayscale=off. These are set as initial slider positions in `SettingsPanel.__init__`.
- **`_make_slider_row`** returns `(QHBoxLayout, QSlider, QLabel)` — callers must `addLayout(row)` themselves.
- **No caching in scanner.py** — `look_scanned()` renders and processes every page from scratch. The GUI caches only the current page's unprocessed image for preview responsiveness.
- **Random seed**: Set via `ScanConfig.seed`. When set, both CLI and GUI produce deterministic page rotations. GUI does not expose seed currently.
- **Watermark**: Text watermark rendered with PIL's `ImageDraw` + `ImageFont`. Auto-detects system CJK font (Microsoft YaHei on Windows, PingFang on macOS, Noto Sans CJK on Linux). Falls back to PIL default font. Watermark is drawn on a transparent overlay then alpha-composited for opacity control.
- **PDF metadata**: Full metadata support via PyMuPDF (`title`, `author`, `subject`, `producer`, `creator`, `creationDate`, `modDate`). Defaults: producer="Adobe PDF Library", creator="HP Scan". Empty string values are omitted from output.
- **i18n**: GUI auto-detects system language via `locale.getdefaultlocale()` with fallback checks for `LANG`/`LC_ALL` env vars and Windows `GetUserDefaultUILanguage`. Currently supports `en` and `zh`. Override with `LOOKSCANNED_LANG` env var. CLI is English-only.
- **Page size math**: `zoom = dpi * scale / 72.0`. Page dimensions in points = pixel dimensions / zoom. The zoom already has the /72 factor, so do NOT multiply by 72 again when computing output page size.
