"""Small dependency-free plotting widget for telemetry previews."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class MultiLinePlot(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(280)
        self.series: dict[str, list[float]] = {}
        self.colors = ["#5b8bd7", "#66c9a4", "#e8b955", "#d66c75", "#a58de8"]

    def set_series(self, series: dict[str, list[float]]) -> None:
        self.series = series
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(14, 12, -14, -18)
        painter.fillRect(self.rect(), QColor("#121821"))
        painter.setPen(QPen(QColor("#2e3a4d"), 1))
        painter.drawRoundedRect(rect, 7, 7)

        for i in range(1, 5):
            y = rect.top() + rect.height() * i / 5
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        if not self.series:
            painter.setPen(QColor("#8c99ad"))
            painter.drawText(rect, Qt.AlignCenter, "No signal")
            return

        values = [v for line in self.series.values() for v in line]
        lo = min(values) if values else -1.0
        hi = max(values) if values else 1.0
        if abs(hi - lo) < 1e-6:
            lo -= 1.0
            hi += 1.0

        for index, (name, data) in enumerate(self.series.items()):
            if len(data) < 2:
                continue
            painter.setPen(QPen(QColor(self.colors[index % len(self.colors)]), 2))
            points = []
            for i, value in enumerate(data):
                x = rect.left() + rect.width() * i / max(1, len(data) - 1)
                y = rect.bottom() - rect.height() * (value - lo) / (hi - lo)
                points.append((int(x), int(y)))
            for a, b in zip(points, points[1:]):
                painter.drawLine(a[0], a[1], b[0], b[1])
            painter.drawText(rect.left() + 10, rect.top() + 18 + index * 18, name)
