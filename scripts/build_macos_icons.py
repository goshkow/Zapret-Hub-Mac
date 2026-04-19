from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_SOURCE = PROJECT_ROOT / "H.icon"
BUILD_ROOT = PROJECT_ROOT / "build" / "macos_icon_assets"
ASSET_CATALOG = BUILD_ROOT / "AppAssets.xcassets" / "AppIcon.appiconset"
ICONS_DIR = PROJECT_ROOT / "resources" / "ui_assets" / "icons"


def _qcolor(p3_text: str) -> QColor:
    r, g, b, a = [float(x) for x in p3_text.split(",")]
    return QColor.fromRgbF(r, g, b, a)


def _render_app_icon() -> QImage:
    config = json.loads((ICON_SOURCE / "icon.json").read_text(encoding="utf-8"))
    start = config["fill"]["linear-gradient"][0].split(":", 1)[1]
    stop = config["fill"]["linear-gradient"][1].split(":", 1)[1]
    scale = float(config["groups"][1]["layers"][0]["position"]["scale"])

    size = 1024
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    outer = QRectF(0, 0, size, size)
    radius = 236.0
    clip_path = QPainterPath()
    clip_path.addRoundedRect(outer, radius, radius)
    painter.setClipPath(clip_path)

    gradient = QLinearGradient(QPointF(size * 0.5, 0), QPointF(size * 0.5, size * 0.72))
    gradient.setColorAt(0.0, _qcolor(start))
    gradient.setColorAt(1.0, _qcolor(stop))
    painter.fillPath(clip_path, gradient)

    highlight = QLinearGradient(QPointF(size * 0.5, 0), QPointF(size * 0.5, size * 0.42))
    highlight.setColorAt(0.0, QColor(255, 255, 255, 88))
    highlight.setColorAt(0.45, QColor(255, 255, 255, 24))
    highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.fillPath(clip_path, highlight)

    source = QImage(str(ICON_SOURCE / "Assets" / "H.png")).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    content_w = size * scale
    content_h = size * scale
    x = (size - content_w) / 2.0
    y = (size - content_h) / 2.0
    painter.drawImage(QRectF(x, y, content_w, content_h), source, QRectF(0, 0, source.width(), source.height()))

    painter.setClipping(False)
    painter.setPen(QColor(255, 255, 255, 32))
    painter.drawRoundedRect(outer.adjusted(10, 10, -10, -10), radius - 12, radius - 12)
    painter.setPen(QColor(0, 0, 0, 28))
    painter.drawRoundedRect(outer.adjusted(2, 2, -2, -2), radius - 3, radius - 3)
    painter.end()
    return image


def _render_tray_template() -> QImage:
    source = QImage(str(ICON_SOURCE / "Assets" / "H.png")).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    size = 128
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawImage(QRectF(10, 10, 108, 108), source, QRectF(0, 0, source.width(), source.height()))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(image.rect(), QColor(255, 255, 255, 255))
    painter.end()
    return image


def _write_appiconset(source: QImage) -> None:
    ASSET_CATALOG.mkdir(parents=True, exist_ok=True)
    sizes = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for filename, size in sizes:
        scaled = source.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        scaled.save(str(ASSET_CATALOG / filename))

    contents = {
        "images": [
            {"filename": "icon_16x16.png", "idiom": "mac", "scale": "1x", "size": "16x16"},
            {"filename": "icon_16x16@2x.png", "idiom": "mac", "scale": "2x", "size": "16x16"},
            {"filename": "icon_32x32.png", "idiom": "mac", "scale": "1x", "size": "32x32"},
            {"filename": "icon_32x32@2x.png", "idiom": "mac", "scale": "2x", "size": "32x32"},
            {"filename": "icon_128x128.png", "idiom": "mac", "scale": "1x", "size": "128x128"},
            {"filename": "icon_128x128@2x.png", "idiom": "mac", "scale": "2x", "size": "128x128"},
            {"filename": "icon_256x256.png", "idiom": "mac", "scale": "1x", "size": "256x256"},
            {"filename": "icon_256x256@2x.png", "idiom": "mac", "scale": "2x", "size": "256x256"},
            {"filename": "icon_512x512.png", "idiom": "mac", "scale": "1x", "size": "512x512"},
            {"filename": "icon_512x512@2x.png", "idiom": "mac", "scale": "2x", "size": "512x512"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    (ASSET_CATALOG / "Contents.json").write_text(json.dumps(contents, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    app_icon = _render_app_icon()
    tray_icon = _render_tray_template()

    app_icon.save(str(ICONS_DIR / "app.png"))
    tray_icon.save(str(ICONS_DIR / "tray_h_template.png"))
    _write_appiconset(app_icon)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
