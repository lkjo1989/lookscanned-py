"""PDF scan simulator — main processing pipeline."""

import io
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import fitz
from PIL import Image

from .effects import apply_scan_effects


@dataclass
class ScanConfig:
    """Configuration for the scan simulation effect.

    Attributes:
        rotate: Base rotation angle in degrees, simulating crooked placement
                on the scanner bed. Range: -10 to 10.
        rotate_variance: Random additional rotation per page, simulating
                         inconsistent manual placement. Range: 0 to 5.
        blur: Gaussian blur simulating scanner optics softness. Range: 0 to 1.
        noise: Sensor noise intensity. Range: 0 to 1.
        border: Draw a 1px black border around the page, like a scan frame.
        grayscale: Convert to black and white (scanner default).
        brightness: Brightness adjustment. 1.0 = unchanged, <1 darker, >1 brighter.
        yellowish: Warm/sepia toning for an aged-paper look. Range: 0 to 1.
        contrast: Contrast adjustment. 1.0 = unchanged, <1 flatter, >1 punchier.
        scale: Resolution multiplier (e.g. 2.0 doubles the effective DPI).
        dpi: Base render DPI used when rasterising PDF pages.
        output_format: Image format embedded in the output PDF ("jpeg" or "png").
        seed: Random seed for reproducible page variance. None means random.
        watermark_text: Text to draw as a watermark. Empty string = no watermark.
        watermark_x: Horizontal watermark anchor (0.0–1.0 fraction of page width).
        watermark_y: Vertical watermark anchor (0.0–1.0 fraction of page height).
        watermark_font_size: Font size in points for the watermark text.
        watermark_opacity: Watermark opacity (0.0 = invisible, 1.0 = opaque).
        watermark_color: Hex colour for the watermark text (e.g. "#000000").
        title: PDF metadata title.
        author: PDF metadata author.
        subject: PDF metadata subject.
        producer: PDF metadata producer.
        creator: PDF metadata creator.
        creation_date: PDF metadata creation date (ISO 8601 string).
        mod_date: PDF metadata modification date (ISO 8601 string).
    """

    rotate: float = 0.0
    rotate_variance: float = 0.0
    blur: float = 0.0
    noise: float = 0.0
    border: bool = False
    grayscale: bool = False
    brightness: float = 1.0
    yellowish: float = 0.0
    contrast: float = 1.0
    scale: float = 1.0
    dpi: int = 150
    output_format: str = "jpeg"
    seed: int | None = None

    # Watermark
    watermark_text: str = ""
    watermark_x: float = 0.5
    watermark_y: float = 0.5
    watermark_font_size: int = 36
    watermark_opacity: float = 0.3
    watermark_color: str = "#000000"

    # PDF metadata
    title: str = ""
    author: str = ""
    subject: str = ""
    producer: str = "Adobe PDF Library"
    creator: str = "HP Scan"
    creation_date: str = ""
    mod_date: str = ""


def look_scanned(
    input_path: str,
    output_path: str | None = None,
    *,
    config: ScanConfig | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> str:
    """Make a PDF document look like it was scanned.

    All processing happens locally — no data is ever sent anywhere.

    Args:
        input_path: Path to the input PDF file.
        output_path: Path for the output PDF. Defaults to ``<input>_scanned.pdf``.
        config: Scan effect configuration. Uses defaults when omitted.
        on_progress: Optional callback ``(current_page, total_pages)`` called
                     after each page finishes processing.

    Returns:
        The resolved output file path.
    """
    if config is None:
        config = ScanConfig()

    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / f"{p.stem}_scanned{p.suffix}")

    if config.seed is not None:
        random.seed(config.seed)

    src = fitz.open(input_path)
    total = src.page_count

    zoom = config.dpi * config.scale / 72.0
    processed: list[tuple[int, int, bytes]] = []

    for i in range(total):
        if on_progress:
            on_progress(i + 1, total)

        page_rotate = config.rotate
        if config.rotate_variance > 0:
            page_rotate += random.uniform(-config.rotate_variance, config.rotate_variance)

        page = src[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        img = apply_scan_effects(img, config, page_rotate)

        buf = io.BytesIO()
        fmt = "JPEG" if config.output_format == "jpeg" else "PNG"
        save_kwargs: dict = {"quality": 92} if fmt == "JPEG" else {}
        img.save(buf, format=fmt, **save_kwargs)
        processed.append((img.width, img.height, buf.getvalue()))

    src.close()

    dst = fitz.open()
    for width_px, height_px, img_bytes in processed:
        width_pt = width_px / zoom
        height_pt = height_px / zoom
        page = dst.new_page(width=width_pt, height=height_pt)
        page.insert_image(page.rect, stream=img_bytes)

    meta: dict[str, str] = {}
    if config.title:
        meta["title"] = config.title
    if config.author:
        meta["author"] = config.author
    if config.subject:
        meta["subject"] = config.subject
    if config.producer:
        meta["producer"] = config.producer
    if config.creator:
        meta["creator"] = config.creator
    if config.creation_date:
        meta["creationDate"] = config.creation_date
    if config.mod_date:
        meta["modDate"] = config.mod_date

    dst.set_metadata(meta)
    dst.save(output_path)
    dst.close()

    if on_progress:
        on_progress(total, total)

    return output_path
