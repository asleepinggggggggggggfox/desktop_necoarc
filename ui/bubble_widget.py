from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class BubbleWidget(QWidget):
    def __init__(self, side: str, tone: str, text: str = "", parent=None):
        super().__init__(parent)
        self.side = side
        self.tone = tone
        self._text = text
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def preferred_size(self, max_width: int, max_height: int) -> tuple[int, int]:
        scale = max(0.45, min(1.0, max_width / 220))
        font = self._font(scale)
        metrics = QFontMetrics(font)
        text = self._text.strip() or " "
        min_width = max(92, int(110 * scale))
        min_height = max(48, int(64 * scale))
        tail_h = int(24 * scale)
        pad_x = int(36 * scale)
        pad_y = int(34 * scale)

        for width in range(min_width, max_width + 1, 8):
            text_rect = QRect(0, 0, max(20, width - pad_x), max_height)
            text_bounds = metrics.boundingRect(text_rect, Qt.TextWordWrap, text)
            needed_height = text_bounds.height() + pad_y + tail_h
            if needed_height <= max_height:
                return width, max(min_height, needed_height)

        text_rect = QRect(0, 0, max(20, max_width - pad_x), max_height)
        text_bounds = metrics.boundingRect(text_rect, Qt.TextWordWrap, text)
        return max_width, min(max_height, max(min_height, text_bounds.height() + pad_y + tail_h))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = 5
        scale = max(0.45, min(1.0, self.width() / 220))
        tail_w = int(30 * scale)
        tail_h = int(18 * scale)
        body = QRect(margin, margin, self.width() - margin * 2, self.height() - tail_h - margin)
        radius = int(14 * scale)

        path = QPainterPath()
        path.addRoundedRect(body, radius, radius)
        if self.side == "left":
            base_x = body.right() - int(44 * scale)
            path.moveTo(base_x, body.bottom() - 1)
            path.cubicTo(
                base_x + int(8 * scale),
                body.bottom() + int(7 * scale),
                base_x + tail_w,
                body.bottom() + tail_h,
                base_x + tail_w,
                body.bottom() + tail_h,
            )
            path.cubicTo(
                base_x + int(14 * scale),
                body.bottom() + int(7 * scale),
                base_x + int(4 * scale),
                body.bottom(),
                base_x + int(24 * scale),
                body.bottom() - 1,
            )
        else:
            base_x = body.left() + int(52 * scale)
            path.moveTo(base_x, body.bottom() - 1)
            path.cubicTo(
                base_x - int(8 * scale),
                body.bottom() + int(7 * scale),
                base_x - tail_w,
                body.bottom() + tail_h,
                base_x - tail_w,
                body.bottom() + tail_h,
            )
            path.cubicTo(
                base_x - int(14 * scale),
                body.bottom() + int(7 * scale),
                base_x - int(4 * scale),
                body.bottom(),
                base_x - int(24 * scale),
                body.bottom() - 1,
            )

        shadow = QPainterPath(path)
        painter.translate(0, int(3 * scale))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 20))
        painter.drawPath(shadow)
        painter.translate(0, -int(3 * scale))

        if self.tone == "input":
            border = QColor(210, 82, 90, 82)
            fill = QColor(255, 247, 248, 218)
            text_color = QColor(178, 44, 52)
        else:
            border = QColor(66, 168, 110, 82)
            fill = QColor(247, 255, 250, 218)
            text_color = QColor(28, 132, 78)

        painter.setPen(QPen(border, max(1, int(1.35 * scale))))
        painter.setBrush(fill)
        painter.drawPath(path)

        pad_x = int(18 * scale)
        pad_y = int(14 * scale)
        text_rect = body.adjusted(pad_x, pad_y, -pad_x, -int(14 * scale))
        font = self._font(scale)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(
            text_rect,
            Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap,
            self._fit_text(painter, text_rect),
        )

    def _fit_text(self, painter: QPainter, rect: QRect) -> str:
        words = self._text.strip() or " "
        base_font = painter.font()
        for point_size in range(base_font.pointSize(), 6, -1):
            trial_font = QFont(base_font)
            trial_font.setPointSize(point_size)
            painter.setFont(trial_font)
            metrics = painter.fontMetrics()
            if metrics.boundingRect(rect, Qt.TextWordWrap, words).height() <= rect.height():
                return words

        metrics = painter.fontMetrics()
        compact = words
        while compact and metrics.boundingRect(rect, Qt.TextWordWrap, compact + "...").height() > rect.height():
            compact = compact[:-1]
        return compact.rstrip() + "..."

    def _font(self, scale: float) -> QFont:
        font = QFont("Microsoft YaHei UI", max(8, int(15 * scale)))
        font.setWeight(QFont.Medium)
        return font
