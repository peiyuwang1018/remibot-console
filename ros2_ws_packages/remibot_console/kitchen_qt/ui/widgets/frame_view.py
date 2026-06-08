"""Qt widget for streamed visualization frames."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FrameView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setMaximumHeight(340)
        self.placeholder = "Waiting for visualization image stream"
        self.image_label = QLabel(self.placeholder)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setWordWrap(True)
        self.image_label.setObjectName("VisualizationFrame")
        self.pixmap: QPixmap | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label, 1)

    def set_placeholder(self, text: str) -> None:
        self.placeholder = text
        if self.pixmap is None:
            self.image_label.setText(text)

    def set_frame(self, image: QImage) -> None:
        if image.isNull():
            return
        self.pixmap = QPixmap.fromImage(image)
        self._update_scaled_pixmap()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self.pixmap is None:
            self.image_label.setText(self.placeholder)
            return
        scaled = self.pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
