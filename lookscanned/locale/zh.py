"""Chinese (Simplified) locale strings for Look Scanned."""

strings: dict[str, str] = {
    # Window / App
    "app.title": "Look Scanned",
    "app.description": (
        "让你的 PDF 看起来就像扫描件一样。所有处理均在本地完成——数据不会离开你的设备。"
    ),

    # File actions
    "file.select_pdf": "选择 PDF",
    "file.no_file": "尚未选择文件",
    "file.pages": "{count} 页",

    # Preview
    "preview.original": "原稿",
    "preview.scanned": "扫描效果",
    "preview.no_pdf": "未加载 PDF",

    # Settings groups
    "settings.settings": "扫描设置",
    "settings.output": "输出选项",

    # Settings: sliders
    "settings.rotate": "旋转角度",
    "settings.rotate_variance": "旋转随机度",
    "settings.blur": "模糊",
    "settings.noise": "噪点",
    "settings.brightness": "亮度",
    "settings.contrast": "对比度",
    "settings.yellowish": "泛黄",
    "settings.scale": "分辨率",

    # Settings: combos / checkboxes
    "settings.dpi": "DPI",
    "settings.format": "格式",
    "settings.grayscale": "灰度",
    "settings.border": "边框",

    # Settings: watermark
    "settings.watermark": "文字水印",
    "settings.watermark_text": "水印文字",
    "settings.watermark_x": "X 位置",
    "settings.watermark_y": "Y 位置",
    "settings.watermark_size": "字号",
    "settings.watermark_opacity": "透明度",
    "settings.watermark_color": "颜色",

    # Settings: metadata
    "settings.metadata": "PDF 元数据",
    "settings.metadata.title": "标题",
    "settings.metadata.author": "作者",
    "settings.metadata.subject": "主题",
    "settings.metadata.producer": "生成器",
    "settings.metadata.creator": "创建者",
    "settings.metadata.creation_date": "创建日期",
    "settings.metadata.mod_date": "修改日期",

    # Buttons
    "button.generate": "生成扫描版 PDF",

    # Status
    "status.ready": "就绪",
    "status.generating": "正在生成...",
    "status.done": "完成",
    "status.error": "错误",
    "status.processing": "正在处理第 {current}/{total} 页...",

    # Error messages
    "error.open_pdf": "无法打开 PDF：\n{error}",
    "error.generate": "生成 PDF 失败：\n{error}",
    "error.output_same": "输出路径不能与输入路径相同。",
    "error.save_dialog": "错误",
    "error.warning": "错误",
}
