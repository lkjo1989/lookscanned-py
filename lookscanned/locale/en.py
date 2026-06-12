"""English locale strings for Look Scanned."""

strings: dict[str, str] = {
    # Window / App
    "app.title": "Look Scanned",
    "app.description": (
        "Make your PDFs look like they were scanned. "
        "All processing is local — no data ever leaves your machine."
    ),

    # File actions
    "file.select_pdf": "Select PDF",
    "file.no_file": "No file selected",
    "file.pages": "{count} pages",

    # Preview
    "preview.original": "Original",
    "preview.scanned": "Scanned",
    "preview.no_pdf": "No PDF loaded",

    # Settings groups
    "settings.settings": "Scan Settings",
    "settings.output": "Output",

    # Settings: sliders
    "settings.rotate": "Rotate",
    "settings.rotate_variance": "Rotate Variance",
    "settings.blur": "Blur",
    "settings.noise": "Noise",
    "settings.brightness": "Brightness",
    "settings.contrast": "Contrast",
    "settings.yellowish": "Yellowish",
    "settings.scale": "Scale",

    # Settings: combos / checkboxes
    "settings.dpi": "DPI",
    "settings.format": "Format",
    "settings.grayscale": "Grayscale",
    "settings.border": "Border",

    # Settings: watermark
    "settings.watermark": "Watermark",
    "settings.watermark_text": "Text",
    "settings.watermark_x": "X Position",
    "settings.watermark_y": "Y Position",
    "settings.watermark_size": "Font Size",
    "settings.watermark_opacity": "Opacity",
    "settings.watermark_color": "Color",

    # Settings: metadata
    "settings.metadata": "PDF Metadata",
    "settings.metadata.title": "Title",
    "settings.metadata.author": "Author",
    "settings.metadata.subject": "Subject",
    "settings.metadata.producer": "Producer",
    "settings.metadata.creator": "Creator",
    "settings.metadata.creation_date": "Creation Date",
    "settings.metadata.mod_date": "Mod Date",

    # Buttons
    "button.generate": "Generate Scanned PDF",

    # Status
    "status.ready": "Ready",
    "status.generating": "Generating...",
    "status.done": "Done",
    "status.error": "Error",
    "status.processing": "Processing page {current}/{total}...",

    # Error messages
    "error.open_pdf": "Could not open PDF:\n{error}",
    "error.generate": "Failed to generate PDF:\n{error}",
    "error.output_same": "Output path must differ from input.",
    "error.save_dialog": "Error",
    "error.warning": "Error",
}
