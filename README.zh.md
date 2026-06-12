# Look Scanned — Python

[English](README.md)

让 PDF 看起来像扫描件一样。灵感来源于 [lookscanned.io](https://lookscanned.io)，可作为 CLI 工具和 Python 库使用。

所有处理均在本地完成——数据不会离开你的设备。

## 安装

```sh
# 仅 CLI
pip install -r requirements.txt

# CLI + GUI
pip install -r requirements-gui.txt
```

或者作为包安装：

```sh
pip install -e .          # 仅 CLI
pip install -e ".[gui]"   # CLI + GUI
```

## 免安装使用

直接从源码运行（仍需先装依赖）：

```sh
# 先装依赖
pip install -r requirements.txt

# CLI
python -m lookscanned input.pdf --rotate 0.1 --blur 0.3 --noise 0.1 --border --yellowish 0.08

# GUI（需要 PySide6）
pip install -r requirements-gui.txt
python -m lookscanned.gui
```

## CLI 使用

```sh
# 最简单的情况 — 输出为 input_scanned.pdf
lookscanned input.pdf

# 完整的扫描模拟
lookscanned input.pdf output.pdf  --rotate 0.3 --rotate-variance 0.3  --blur 0.3 --noise 0.1  --grayscale --border --yellowish 0.08

# 彩色
lookscanned input.pdf output.pdf  --rotate 0.1 --rotate-variance 0.3  --blur 0.3 --noise 0.1 --border --yellowish 0.08

# 高分辨率输出
lookscanned input.pdf --scale 2 --dpi 300

# 添加水印
lookscanned input.pdf --watermark-text "绝密" --watermark-opacity 0.15

# 设置 PDF 元数据
lookscanned input.pdf --title "季度报告" --author "张三" --producer "HP Scan"
```

### 选项

| 参数 | 范围 | 效果 |
|---|---|---|
| `-r`, `--rotate` | -10 到 10 | 旋转角度（模拟倾斜摆放） |
| `--rotate-variance` | 0 到 5 | 每页随机旋转偏差 |
| `--blur` | 0 到 1 | 高斯模糊 |
| `--noise` | 0 到 1 | 传感器噪点 |
| `--border` | 标志 | 1px 黑色边框 |
| `-g`, `--grayscale` | 标志 | 黑白输出 |
| `--brightness` | 0 到 2 | 亮度（1.0 = 不变） |
| `--yellowish` | 0 到 1 | 纸张泛黄效果 |
| `--contrast` | 0 到 2 | 对比度（1.0 = 不变） |
| `--scale` | 浮点数 | 分辨率倍率 |
| `--dpi` | 整数 | 基础渲染 DPI（默认 150） |
| `--png` | 标志 | 使用 PNG 替代 JPEG |
| `--seed` | 整数 | 可复现的随机输出 |
| `--watermark-text` | 字符串 | 水印文字（空 = 无水印） |
| `--title` | 字符串 | PDF 元数据标题 |
| `--author` | 字符串 | PDF 元数据作者 |

完整选项列表请运行 `lookscanned --help`。

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

# 带进度回调
def progress(current, total):
    print(f"第 {current}/{total} 页")

look_scanned("input.pdf", "output.pdf", config=config, on_progress=progress)
```

### `ScanConfig`

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `rotate` | `float` | `0.0` | 旋转角度 (-10 到 10) |
| `rotate_variance` | `float` | `0.0` | 每页随机偏差 (0 到 5) |
| `blur` | `float` | `0.0` | 模糊量 (0 到 1) |
| `noise` | `float` | `0.0` | 噪点强度 (0 到 1) |
| `border` | `bool` | `False` | 添加 1px 黑色边框 |
| `grayscale` | `bool` | `False` | 转为灰度 |
| `brightness` | `float` | `1.0` | 亮度倍率 |
| `yellowish` | `float` | `0.0` | 纸张泛黄 (0 到 1) |
| `contrast` | `float` | `1.0` | 对比度倍率 |
| `scale` | `float` | `1.0` | 分辨率倍率 |
| `dpi` | `int` | `150` | 基础渲染 DPI |
| `output_format` | `str` | `"jpeg"` | `"jpeg"` 或 `"png"` |
| `seed` | `int \| None` | `None` | 随机种子，用于可复现输出 |
| `watermark_text` | `str` | `""` | 水印文字（空 = 无水印） |
| `watermark_x` | `float` | `0.5` | 水印 X 位置（页面宽度比例 0–1） |
| `watermark_y` | `float` | `0.5` | 水印 Y 位置（页面高度比例 0–1） |
| `watermark_font_size` | `int` | `36` | 水印字号（磅） |
| `watermark_opacity` | `float` | `0.3` | 水印不透明度 (0–1) |
| `watermark_color` | `str` | `"#000000"` | 水印颜色（十六进制） |
| `title` | `str` | `""` | PDF 元数据标题 |
| `author` | `str` | `""` | PDF 元数据作者 |
| `subject` | `str` | `""` | PDF 元数据主题 |
| `producer` | `str` | `"Adobe PDF Library"` | PDF 元数据生成器 |
| `creator` | `str` | `"HP Scan"` | PDF 元数据创建者 |
| `creation_date` | `str` | `""` | PDF 元数据创建日期 (ISO 8601) |
| `mod_date` | `str` | `""` | PDF 元数据修改日期 (ISO 8601) |

## 处理流程

```
PDF → pymupdf 渲染页面为图像
    → Pillow/numpy 应用效果（旋转、模糊、噪点、色调、边框等）
    → pymupdf 组装输出 PDF
```

效果按以下顺序应用：旋转 → 灰度 → 模糊 → 亮度 → 对比度 → 泛黄 → 噪点 → 边框 → 水印。

灵感来源于 [lookscanned.io](https://lookscanned.io)。

## GUI

基于 PySide6 的桌面 GUI，支持实时并排预览。

```sh
pip install -r requirements-gui.txt
python -m lookscanned.gui
```

Windows 上可直接双击 `run-gui.bat`。

GUI 功能：

- **并排预览** — 拖动滑块时，原始效果和扫描效果实时更新
- **完整扫描设置** — 旋转、模糊、噪点、边框、灰度、亮度、对比度、泛黄、水印
- **页面导航** — 翻阅多页 PDF
- **后台处理** — PDF 生成在工作线程中运行，保持 UI 响应
- **中英文界面** — 根据系统语言自动切换

## 许可

MIT
