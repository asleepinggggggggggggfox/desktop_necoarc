from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class CharacterWidget(QWidget):
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.pixmaps: dict[str, QPixmap] = {}
        self.expression = "normal"
        self.set_expression_images({"normal": image_path})
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_expression_images(self, image_paths: dict[str, Path]) -> None:
        self.pixmaps = {
            name: self._load_pixmap(path)
            for name, path in image_paths.items()
            if path.exists()
        }
        if self.expression not in self.pixmaps:
            self.expression = "normal"
        self.update()

    def set_expression(self, expression: str) -> None:
        next_expression = expression if expression in self.pixmaps else "normal"
        if next_expression == self.expression:
            return
        self.expression = next_expression
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pixmap = self.pixmaps.get(self.expression) or self.pixmaps.get("normal") or QPixmap()
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = self.height() - scaled.height()
            painter.drawPixmap(x, y, scaled)
            return

        cx = self.width() // 2
        h = self.height()
        scale = max(0.45, min(1.0, self.width() / 170))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 28))
        painter.drawEllipse(cx - int(58 * scale), h - int(18 * scale), int(116 * scale), int(14 * scale))

        painter.setPen(QPen(QColor(35, 35, 35), max(2, int(3 * scale))))
        painter.setBrush(QColor(255, 238, 202, 245))
        head = QRect(cx - int(48 * scale), int(22 * scale), int(96 * scale), int(78 * scale))
        painter.drawEllipse(head)

        hair = QPainterPath()
        hair.moveTo(cx - int(50 * scale), int(54 * scale))
        hair.cubicTo(cx - int(55 * scale), int(16 * scale), cx + int(46 * scale), int(8 * scale), cx + int(50 * scale), int(54 * scale))
        hair.cubicTo(cx + int(28 * scale), int(42 * scale), cx, int(50 * scale), cx - int(50 * scale), int(54 * scale))
        painter.setBrush(QColor(246, 207, 143, 245))
        painter.drawPath(hair)

        painter.setBrush(QColor(252, 252, 252, 245))
        body = QRect(cx - int(52 * scale), int(102 * scale), int(104 * scale), int(112 * scale))
        painter.drawRoundedRect(body, int(20 * scale), int(20 * scale))

        painter.setBrush(QColor(39, 47, 70, 245))
        skirt = QRect(cx - int(62 * scale), int(188 * scale), int(124 * scale), int(38 * scale))
        painter.drawRoundedRect(skirt, int(10 * scale), int(10 * scale))

        painter.setBrush(QColor(30, 31, 38, 245))
        painter.drawRoundedRect(cx - int(42 * scale), int(220 * scale), int(34 * scale), int(70 * scale), int(10 * scale), int(10 * scale))
        painter.drawRoundedRect(cx + int(8 * scale), int(220 * scale), int(34 * scale), int(70 * scale), int(10 * scale), int(10 * scale))

        painter.setPen(QPen(QColor(174, 24, 36), max(4, int(5 * scale))))
        painter.drawPoint(cx - int(18 * scale), int(60 * scale))
        painter.drawPoint(cx + int(18 * scale), int(60 * scale))
        painter.setPen(QPen(QColor(44, 44, 44), max(2, int(2 * scale))))
        painter.drawArc(cx - int(17 * scale), int(72 * scale), int(34 * scale), int(16 * scale), 0, -180 * 16)

    def _load_pixmap(self, image_path: Path) -> QPixmap:
        return QPixmap(str(image_path))
