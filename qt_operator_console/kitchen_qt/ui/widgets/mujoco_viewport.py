"""MuJoCo-backed Qt viewport for the operator console."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QStackedLayout, QVBoxLayout, QWidget

from ...config import JOINTS, ROS_JOINT_NAMES
from ...models import JointState
from .frame_view import FrameView


class MujocoViewport(QWidget):
    """Render an MJCF model directly in Qt, with image-stream fallback."""

    def __init__(self, mjcf_path: str | None, width: int = 960, height: int = 540) -> None:
        super().__init__()
        self.mjcf_path = str(Path(mjcf_path).expanduser()) if mjcf_path else None
        self.render_width = width
        self.render_height = height
        self.mujoco: Any | None = None
        self.model: Any | None = None
        self.data: Any | None = None
        self.renderer: Any | None = None
        self.status = ""
        self.joints = {joint: 0.0 for joint in JOINTS}
        self.joint_qpos_addr: dict[str, int] = {}

        self.image_label = QLabel()
        self.image_label.setObjectName("VisualizationFrame")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(320, 240)
        self.image_label.setScaledContents(False)

        self.status_label = QLabel()
        self.status_label.setObjectName("Pill")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)

        self.fallback_frame = FrameView()
        self.fallback_frame.set_placeholder(
            "MuJoCo viewport inactive\n"
            "Configure --mjcf, REMIBOT_MJCF, or data/config.yaml\n"
            "Fallback image stream can still be displayed here."
        )

        self.stack = QStackedLayout()
        render_page = QWidget()
        render_layout = QVBoxLayout(render_page)
        render_layout.setContentsMargins(0, 0, 0, 0)
        render_layout.addWidget(self.image_label, 1)
        render_layout.addWidget(self.status_label, 0)
        self.stack.addWidget(render_page)
        self.stack.addWidget(self.fallback_frame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.stack)

        self._load_model()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._render)
        if self.is_active:
            self.stack.setCurrentIndex(0)
            self.timer.start()
        else:
            self.stack.setCurrentIndex(1)

    @property
    def is_active(self) -> bool:
        return self.renderer is not None and self.model is not None and self.data is not None

    def set_joint_states(self, joints: dict[str, JointState]) -> None:
        for joint in JOINTS:
            if joint in joints:
                self.joints[joint] = float(joints[joint].position)

    def set_fallback_frame(self, image: QImage) -> None:
        if not self.is_active:
            self.fallback_frame.set_frame(image)

    def _load_model(self) -> None:
        if not self.mjcf_path:
            self.status = "MuJoCo MJCF is not configured."
            return
        if not Path(self.mjcf_path).exists():
            self.status = f"MuJoCo MJCF not found: {self.mjcf_path}"
            return
        try:
            import mujoco
        except ImportError:
            self.status = "Python package 'mujoco' is not installed; using fallback visualization."
            return
        try:
            self.mujoco = mujoco
            self.model = mujoco.MjModel.from_xml_path(self.mjcf_path)
            self.data = mujoco.MjData(self.model)
            self.renderer = mujoco.Renderer(self.model, height=self.render_height, width=self.render_width)
            self._map_joints()
            mapped = ", ".join(sorted(self.joint_qpos_addr)) or "no matching joints"
            self.status = f"MuJoCo active: {Path(self.mjcf_path).name}; mapped {mapped}"
        except Exception as exc:  # noqa: BLE001 - keep the console usable if MJCF fails
            self.model = None
            self.data = None
            self.renderer = None
            self.status = f"MuJoCo model load failed: {exc}"

    def _map_joints(self) -> None:
        if self.mujoco is None or self.model is None:
            return
        for ui_joint, ros_joint in ROS_JOINT_NAMES.items():
            joint_id = self.mujoco.mj_name2id(self.model, self.mujoco.mjtObj.mjOBJ_JOINT, ros_joint)
            if joint_id >= 0:
                self.joint_qpos_addr[ui_joint] = int(self.model.jnt_qposadr[joint_id])

    def _render(self) -> None:
        if not self.is_active or self.mujoco is None:
            return
        for joint, addr in self.joint_qpos_addr.items():
            if 0 <= addr < len(self.data.qpos):
                self.data.qpos[addr] = self.joints[joint]
        try:
            self.mujoco.mj_forward(self.model, self.data)
            self.renderer.update_scene(self.data)
            pixels = self.renderer.render()
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"MuJoCo render failed: {exc}")
            return

        height, width = int(pixels.shape[0]), int(pixels.shape[1])
        bytes_per_line = int(pixels.strides[0])
        image = QImage(pixels.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)
        self.status_label.setText(self.status)
