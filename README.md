# Look Scanned — Python

[中文版](README.zh.md)

Make PDF documents look like they were scanned. A Python port of the [lookscanned.io](https://lookscanned.io) scan simulator, usable as both a CLI tool and a library.

All processing happens locally — no data ever leaves your machine.

## Installation

```sh
# CLI only
pip install -r requirements.txt

# CLI + GUI
pip install -r requirements-gui.txt
```

Or install as a package:

```sh
pip install -e .          # CLI only
pip install -e ".[gui]"   # CLI + GUI
```

## Use without installing

Run directly from source (dependencies still required):

```sh
# Install deps first
pip install -r requirements.txt

# CLI
python -m lookscanned input.pdf --rotate 0.1 --blur 0.3 --noise 0.1 --border --yellowish 0.08

# GUI (needs PySide6)
pip install -r requirements-gui.txt
python -m lookscanned.gui
```

## CLI Usage

```sh
# Simplest case — outputs input_scanned.pdf
lookscanned input.pdf

# Full scan simulation
lookscanned input.pdf output.pdf  --rotate 0.3 --rotate-variance 0.3  --blur 0.3 --noise 0.1  --grayscale --border --yellowish 0.08
# Colorful
lookscanned input.pdf output.pdf  --rotate 0.1 --rotate-variance 0.3  --blur 0.3 --noise 0.1 --border --yellowish 0.08

# High-resolution output
lookscanned input.pdf --scale 2 --dpi 300
```

### Options

| Flag | Range | Effect |
|---|---|---|
| `-r`, `--rotate` | -10 to 10 | Rotation angle (crooked placement) |
| `--rotate-variance` | 0 to 5 | Random per-page rotation jitter |
| `--blur` | 0 to 1 | Gaussian blur |
| `--noise` | 0 to 1 | Sensor noise |
| `--border` | flag | 1px black frame |
| `-g`, `--grayscale` | flag | Black and white output |
| `--brightness` | 0 to 2 | Brightness (1.0 = unchanged) |
| `--yellowish` | 0 to 1 | Aged-paper warm tone |
| `--contrast` | 0 to 2 | Contrast (1.0 = unchanged) |
| `--scale` | float | Resolution multiplier |
| `--dpi` | int | Base render DPI (default 150) |
| `--png` | flag | Embed PNG instead of JPEG |
| `--seed` | int | Reproducible random output |

## Python API

```python
from lookscanned import look_scanned, ScanConfig

config = ScanConfig(
    rotate=2.5,
    rotate_variance=0.5,
    blur=0.3,
    noise=0.1,
    border=True,
    grayscale=True,
    yellowish=0.15,
)

# With progress callback
def progress(current, total):
    print(f"Page {current}/{total}")

look_scanned("input.pdf", "output.pdf", config=config, on_progress=progress)
```

### `ScanConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `rotate` | `float` | `0.0` | Rotation angle (-10 to 10) |
| `rotate_variance` | `float` | `0.0` | Per-page random variance (0 to 5) |
| `blur` | `float` | `0.0` | Blur amount (0 to 1) |
| `noise` | `float` | `0.0` | Noise intensity (0 to 1) |
| `border` | `bool` | `False` | Add 1px black border |
| `grayscale` | `bool` | `False` | Convert to grayscale |
| `brightness` | `float` | `1.0` | Brightness multiplier |
| `yellowish` | `float` | `0.0` | Aged-paper warm tone (0 to 1) |
| `contrast` | `float` | `1.0` | Contrast multiplier |
| `scale` | `float` | `1.0` | Resolution multiplier |
| `dpi` | `int` | `150` | Base render DPI |
| `output_format` | `str` | `"jpeg"` | `"jpeg"` or `"png"` |
| `seed` | `int \| None` | `None` | Random seed for reproducibility |

## Processing pipeline

```
PDF → pymupdf renders pages to images
    → Pillow/numpy applies effects (rotate, blur, noise, tone, border)
    → pymupdf assembles into output PDF
```

Effects are applied in order: rotation → grayscale → blur → brightness → contrast → yellowish → noise → border → watermark.

Inspired by [lookscanned.io](https://lookscanned.io).

## GUI

A PySide6-based desktop GUI with live side-by-side preview.

```sh
pip install -r requirements-gui.txt
python -m lookscanned.gui
```

Or double-click `run-gui.bat` on Windows.

The GUI provides:

- **Side-by-side preview** — original and scanned view update in real time as you drag sliders
- **All scan settings** — rotate, blur, noise, border, grayscale, brightness, contrast, yellowish
- **Page navigation** — flip through multi-page PDFs
- **Background processing** — PDF generation runs in a worker thread so the UI stays responsive

## License

MIT
