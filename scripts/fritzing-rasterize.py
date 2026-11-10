#!/usr/bin/env python3
"""Rasterize a native Fritzing SVG with the same Qt5 SVG engine, offscreen."""
import argparse
import os
from pathlib import Path
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide2.QtCore import QRectF
from PySide2.QtGui import QGuiApplication, QImage, QPainter, QColor
from PySide2.QtSvg import QSvgRenderer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    app = QGuiApplication([])
    renderer = QSvgRenderer(str(args.source))
    if not renderer.isValid():
        parser.error("Qt cannot render this SVG")
    dimensions = renderer.defaultSize()
    if dimensions.width() <= 0 or dimensions.height() <= 0:
        parser.error("SVG has no positive dimensions")
    scale = min(2.0, 4096 / max(dimensions.width(), dimensions.height()))
    width, height = max(1, round(dimensions.width() * scale)), max(1, round(dimensions.height() * scale))
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    if not image.save(str(args.output), "PNG"):
        parser.error("Qt failed to write PNG")
    print(f"QtSvg PNG: {width} x {height} pixels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
