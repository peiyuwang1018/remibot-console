"""Capture the RViz window and republish it as a ROS image stream."""

from __future__ import annotations

import re
import subprocess

import rclpy
from PySide6.QtGui import QGuiApplication, QImage
from rclpy.node import Node
from sensor_msgs.msg import Image


class RvizCaptureRenderer(Node):
    def __init__(self) -> None:
        super().__init__("remibot_rviz_capture_renderer")
        self.declare_parameter("image_topic", "/remibot/visualization/image")
        self.declare_parameter("fps", 10.0)
        self.declare_parameter("window_title_regex", "RViz|rviz")
        self.declare_parameter("exclude_title_regex", "rviz_capture_renderer|visualization_renderer|Terminal|terminal")
        self.declare_parameter("window_id", "")
        self.declare_parameter("screen_fallback", False)

        image_topic = str(self.get_parameter("image_topic").value)
        fps = float(self.get_parameter("fps").value)
        self.window_title_regex = re.compile(str(self.get_parameter("window_title_regex").value))
        self.exclude_title_regex = re.compile(str(self.get_parameter("exclude_title_regex").value))
        self.window_id = self._parse_window_id(str(self.get_parameter("window_id").value))
        self.screen_fallback = bool(self.get_parameter("screen_fallback").value)
        self.publisher = self.create_publisher(Image, image_topic, 2)
        self.timer = self.create_timer(1.0 / max(1.0, fps), self._publish_capture)
        self.warn_count = 0
        self.last_found_window_id = 0
        self.get_logger().info(f"Publishing RViz capture frames on {image_topic}")

    def _parse_window_id(self, value: str) -> int:
        if not value:
            return 0
        try:
            return int(value, 0)
        except ValueError:
            self.get_logger().warning(f"Invalid window_id parameter: {value}")
            return 0

    def _find_rviz_window(self) -> int:
        try:
            result = subprocess.run(
                ["xwininfo", "-root", "-tree"],
                check=False,
                capture_output=True,
                text=True,
                timeout=0.5,
            )
        except Exception as exc:  # noqa: BLE001 - capture must not crash launch
            self._throttled_warn(f"xwininfo unavailable: {exc}")
            return 0
        if result.returncode != 0:
            self._throttled_warn("xwininfo could not inspect the X11 window tree")
            return 0
        for line in result.stdout.splitlines():
            if not self.window_title_regex.search(line):
                continue
            if self.exclude_title_regex.search(line):
                continue
            match = re.search(r"(0x[0-9a-fA-F]+)", line)
            if match:
                window_id = int(match.group(1), 16)
                if window_id != self.last_found_window_id:
                    self.get_logger().info(f"Captured window candidate: {line.strip()}")
                    self.last_found_window_id = window_id
                return window_id
        return 0

    def _publish_capture(self) -> None:
        app = QGuiApplication.instance()
        if app is None:
            self._throttled_warn("QGuiApplication is not available")
            return
        screen = app.primaryScreen()
        if screen is None:
            self._throttled_warn("No primary screen available for RViz capture")
            return

        window_id = self.window_id or self._find_rviz_window()
        if not window_id and not self.screen_fallback:
            self._throttled_warn("RViz window not found; set window_id or enable screen_fallback")
            return

        pixmap = screen.grabWindow(window_id)
        image = pixmap.toImage()
        if image.isNull():
            self._throttled_warn("RViz capture produced an empty image")
            return
        image = image.convertToFormat(QImage.Format_RGB888)
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "rviz_capture"
        msg.height = image.height()
        msg.width = image.width()
        msg.encoding = "rgb8"
        msg.is_bigendian = 0
        msg.step = image.bytesPerLine()
        msg.data = bytes(image.bits().tobytes())
        self.publisher.publish(msg)

    def _throttled_warn(self, message: str) -> None:
        self.warn_count += 1
        if self.warn_count == 1 or self.warn_count % 50 == 0:
            self.get_logger().warning(message)


def main(args: list[str] | None = None) -> None:
    qt_app = QGuiApplication.instance() or QGuiApplication([])
    rclpy.init(args=args)
    node = RvizCaptureRenderer()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            qt_app.processEvents()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
