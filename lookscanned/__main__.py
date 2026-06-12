"""CLI for lookscanned — Make PDF documents look like they were scanned."""

import argparse
import sys
from pathlib import Path

from .scanner import ScanConfig, look_scanned


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Make PDF documents look like they were scanned.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  lookscanned input.pdf
  lookscanned input.pdf output.pdf --rotate 2.5 --blur 0.3 --noise 0.1
  lookscanned input.pdf --grayscale --border --yellowish 0.2
  lookscanned report.pdf -r 3 --blur 0.2 --noise 0.05 -g --border --scale 2
  lookscanned input.pdf --watermark-text "CONFIDENTIAL" --watermark-opacity 0.15
  lookscanned input.pdf --title "My Report" --author "Me" --producer "HP Scan"
        """,
    )
    parser.add_argument(
        "input", type=str, help="Input PDF file path"
    )
    parser.add_argument(
        "output", type=str, nargs="?", default=None,
        help="Output PDF file path (default: <input>_scanned.pdf)",
    )

    grp = parser.add_argument_group("scan effects")
    grp.add_argument(
        "-r", "--rotate", type=float, default=0.0,
        help="Rotation angle in degrees (-10 to 10)",
    )
    grp.add_argument(
        "--rotate-variance", type=float, default=0.0,
        help="Per-page random rotation variance (0 to 5)",
    )
    grp.add_argument(
        "--blur", type=float, default=0.0,
        help="Gaussian blur amount (0 to 1)",
    )
    grp.add_argument(
        "--noise", type=float, default=0.0,
        help="Sensor noise intensity (0 to 1)",
    )
    grp.add_argument(
        "--border", action="store_true",
        help="Add a 1px black border",
    )
    grp.add_argument(
        "-g", "--grayscale", action="store_true",
        help="Convert to grayscale",
    )
    grp.add_argument(
        "--brightness", type=float, default=1.0,
        help="Brightness multiplier (0 to 2, default 1.0)",
    )
    grp.add_argument(
        "--yellowish", type=float, default=0.0,
        help="Aged-paper warm tone (0 to 1)",
    )
    grp.add_argument(
        "--contrast", type=float, default=1.0,
        help="Contrast multiplier (0 to 2, default 1.0)",
    )

    grp2 = parser.add_argument_group("output options")
    grp2.add_argument(
        "--scale", type=float, default=1.0,
        help="Resolution multiplier (default 1.0)",
    )
    grp2.add_argument(
        "--dpi", type=int, default=150,
        help="Base render DPI (default 150)",
    )
    grp2.add_argument(
        "--png", action="store_true",
        help="Use PNG instead of JPEG for embedded images",
    )
    grp2.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible output",
    )

    grp3 = parser.add_argument_group("watermark")
    grp3.add_argument(
        "--watermark-text", type=str, default="",
        help="Watermark text (empty = no watermark)",
    )
    grp3.add_argument(
        "--watermark-x", type=float, default=0.5,
        help="Watermark X position (0.0-1.0 fraction of page width, default 0.5)",
    )
    grp3.add_argument(
        "--watermark-y", type=float, default=0.5,
        help="Watermark Y position (0.0-1.0 fraction of page height, default 0.5)",
    )
    grp3.add_argument(
        "--watermark-font-size", type=int, default=36,
        help="Watermark font size in points (default 36)",
    )
    grp3.add_argument(
        "--watermark-opacity", type=float, default=0.3,
        help="Watermark opacity 0.0-1.0 (default 0.3)",
    )
    grp3.add_argument(
        "--watermark-color", type=str, default="#000000",
        help="Watermark hex colour (default #000000)",
    )

    grp4 = parser.add_argument_group("pdf metadata")
    grp4.add_argument(
        "--title", type=str, default="",
        help="PDF metadata title",
    )
    grp4.add_argument(
        "--author", type=str, default="",
        help="PDF metadata author",
    )
    grp4.add_argument(
        "--subject", type=str, default="",
        help="PDF metadata subject",
    )
    grp4.add_argument(
        "--producer", type=str, default="Adobe PDF Library",
        help="PDF metadata producer (default: 'Adobe PDF Library')",
    )
    grp4.add_argument(
        "--creator", type=str, default="HP Scan",
        help="PDF metadata creator (default: 'HP Scan')",
    )
    grp4.add_argument(
        "--creation-date", type=str, default="",
        help="PDF metadata creation date (ISO 8601)",
    )
    grp4.add_argument(
        "--mod-date", type=str, default="",
        help="PDF metadata modification date (ISO 8601)",
    )

    args = parser.parse_args(argv)

    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    config = ScanConfig(
        rotate=args.rotate,
        rotate_variance=args.rotate_variance,
        blur=args.blur,
        noise=args.noise,
        border=args.border,
        grayscale=args.grayscale,
        brightness=args.brightness,
        yellowish=args.yellowish,
        contrast=args.contrast,
        scale=args.scale,
        dpi=args.dpi,
        output_format="png" if args.png else "jpeg",
        seed=args.seed,
        watermark_text=args.watermark_text,
        watermark_x=args.watermark_x,
        watermark_y=args.watermark_y,
        watermark_font_size=args.watermark_font_size,
        watermark_opacity=args.watermark_opacity,
        watermark_color=args.watermark_color,
        title=args.title,
        author=args.author,
        subject=args.subject,
        producer=args.producer,
        creator=args.creator,
        creation_date=args.creation_date,
        mod_date=args.mod_date,
    )

    def _progress(current: int, total: int) -> None:
        sys.stderr.write(f"\rProcessing page {current}/{total}...")
        sys.stderr.flush()
        if current == total:
            sys.stderr.write("\n")
            sys.stderr.flush()

    try:
        output = look_scanned(args.input, args.output, config=config, on_progress=_progress)
        print(output)
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
