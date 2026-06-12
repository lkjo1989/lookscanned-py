"""Image processing effects that simulate a flatbed scanner."""

import os
import platform
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def _rotate_image(image: Image.Image, angle: float) -> Image.Image:
    """Rotate around centre, keeping original canvas size. Uncovered areas
    are filled white, mimicking the scanner bed showing through."""
    if angle == 0:
        return image
    return image.rotate(
        angle, expand=False, resample=Image.BICUBIC, fillcolor="white"
    )


def _apply_grayscale(image: Image.Image) -> Image.Image:
    return image.convert("L").convert("RGB")


def _apply_blur(image: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return image
    sigma = amount * 2.0
    return image.filter(ImageFilter.GaussianBlur(radius=sigma))


def _apply_noise(image: Image.Image, intensity: float) -> Image.Image:
    if intensity <= 0:
        return image
    arr = np.array(image, dtype=np.float32)
    noise = np.random.normal(0, intensity * 25, arr.shape)
    arr += noise
    arr = np.clip(arr, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def _apply_yellowish(image: Image.Image, amount: float) -> Image.Image:
    """Blend with a warm paper tone to simulate aged/recycled paper."""
    if amount <= 0:
        return image
    overlay = Image.new("RGB", image.size, (252, 242, 199))
    return Image.blend(image, overlay, amount)


def _apply_border(image: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [(0, 0), (image.width - 1, image.height - 1)],
        outline="black",
        width=1,
    )
    return image


# ---------------------------------------------------------------------------
# Font detection for watermark text
# ---------------------------------------------------------------------------

_FONT_CACHE: ImageFont.ImageFont | ImageFont.FreeTypeFont | None = None
_FONT_PATH: str | None = None


def _find_system_font() -> str | None:
    """Try to find a TrueType font on the system that supports both ASCII
    and common CJK characters."""
    candidates: list[str] = []

    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        candidates = [
            os.path.join(windir, "Fonts", "msyh.ttc"),   # Microsoft YaHei
            os.path.join(windir, "Fonts", "simhei.ttf"),  # SimHei
            os.path.join(windir, "Fonts", "simsun.ttc"),  # SimSun
            os.path.join(windir, "Fonts", "arial.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def _get_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Return a font object at the given *size*.

    Uses the system CJK-compatible font if available, otherwise falls back
    to PIL's built-in default font (which is tiny and won't scale).
    """
    global _FONT_CACHE, _FONT_PATH
    if _FONT_PATH is None:
        _FONT_PATH = _find_system_font()

    if _FONT_PATH:
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except OSError:
            pass

    # Ultimate fallback — PIL default (very small, size ignored)
    return ImageFont.load_default()


def _apply_watermark(
    image: Image.Image,
    text: str,
    *,
    x: float = 0.5,
    y: float = 0.5,
    font_size: int = 36,
    opacity: float = 0.3,
    color: str = "#000000",
) -> Image.Image:
    """Draw semi-transparent watermark text on the image.

    Args:
        image: Source image (modified in place on an overlay, then blended).
        text: Watermark text to draw.
        x: Horizontal anchor as a fraction of image width (0.0–1.0).
        y: Vertical anchor as a fraction of image height (0.0–1.0).
        font_size: Font size in points.
        opacity: Alpha value for the text (0.0 = invisible, 1.0 = opaque).
        color: Hex colour string for the text.
    """
    if not text:
        return image

    font = _get_font(font_size)

    # Render text on a transparent overlay to control opacity
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Get text bounding box for centering the anchor
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    px = int((image.width - text_w) * x) - bbox[0]
    py = int((image.height - text_h) * y) - bbox[1]

    # Parse colour
    r, g, b = _hex_to_rgb(color)
    alpha = int(255 * opacity)

    draw.text((px, py), text, font=font, fill=(r, g, b, alpha))

    # Composite overlay onto base image
    image_rgba = image.convert("RGBA")
    result = Image.alpha_composite(image_rgba, overlay)
    return result.convert("RGB")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex colour string like ``#ff0000`` to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def apply_scan_effects(
    image: Image.Image,
    config,
    page_rotate: float = 0.0,
) -> Image.Image:
    """Apply the full scan-effect pipeline to a single page image.

    Effects are applied in an order that mimics a physical scanner:
    rotation → grayscale → blur → brightness → contrast → aged-paper toning
    → sensor noise → border → watermark.

    Args:
        image: The rendered page as a PIL Image (RGB).
        config: ``ScanConfig`` instance with desired effect parameters.
        page_rotate: Per-page rotation angle (base + random variance).
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    image = _rotate_image(image, page_rotate)

    if config.grayscale:
        image = _apply_grayscale(image)

    image = _apply_blur(image, config.blur)

    if abs(config.brightness - 1.0) > 0.001:
        image = ImageEnhance.Brightness(image).enhance(config.brightness)

    if abs(config.contrast - 1.0) > 0.001:
        image = ImageEnhance.Contrast(image).enhance(config.contrast)

    image = _apply_yellowish(image, config.yellowish)
    image = _apply_noise(image, config.noise)

    if config.border:
        image = _apply_border(image)

    if config.watermark_text:
        image = _apply_watermark(
            image,
            config.watermark_text,
            x=config.watermark_x,
            y=config.watermark_y,
            font_size=config.watermark_font_size,
            opacity=config.watermark_opacity,
            color=config.watermark_color,
        )

    return image
