"""Lightweight ROS2 fallback renderer for the operator console.

This node is intentionally simple: it subscribes to /joint_states and publishes
an RGB image stream that the Qt console can display. The rendering is split into
three deployment-friendly views: J1 top view, J2-J4 side view, and J5 tool roll.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState


JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5"]
LINK_LENGTHS = [92, 88, 72, 54, 34]
BG = (31, 41, 55)
PANEL = (45, 55, 72)
GRID = (75, 85, 99)
TEXT = (209, 213, 219)
LINK = (102, 201, 164)
JOINT = (232, 185, 85)
TIP = (122, 178, 240)


@dataclass
class Canvas:
    width: int
    height: int
    background: tuple[int, int, int] = BG
    data: bytearray = field(init=False)

    def __post_init__(self) -> None:
        self.data = bytearray(self.background * (self.width * self.height))

    def pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        i = (y * self.width + x) * 3
        self.data[i : i + 3] = bytes(color)

    def rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        for yy in range(max(0, y), min(self.height, y + h)):
            row = (yy * self.width + max(0, x)) * 3
            for _xx in range(max(0, x), min(self.width, x + w)):
                self.data[row : row + 3] = bytes(color)
                row += 3

    def line(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        radius = max(0, thickness // 2)
        while True:
            self.disc(x0, y0, radius, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    self.pixel(x, y, color)

    def circle(self, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        last = None
        for step in range(97):
            a = 2.0 * math.pi * step / 96.0
            point = (int(cx + radius * math.cos(a)), int(cy + radius * math.sin(a)))
            if last is not None:
                self.line(last[0], last[1], point[0], point[1], color)
            last = point

    def frame(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        self.line(x, y, x + w, y, color)
        self.line(x + w, y, x + w, y + h, color)
        self.line(x + w, y + h, x, y + h, color)
        self.line(x, y + h, x, y, color)


class ConsoleVisualizationRenderer(Node):
    def __init__(self) -> None:
        super().__init__("remibot_visualization_renderer")
        self.declare_parameter("image_topic", "/remibot/visualization/fallback_image")
        self.declare_parameter("joint_topic", "/joint_states")
        self.declare_parameter("width", 960)
        self.declare_parameter("height", 540)
        self.declare_parameter("fps", 15.0)

        self.width = int(self.get_parameter("width").value)
        self.height = int(self.get_parameter("height").value)
        fps = float(self.get_parameter("fps").value)
        image_topic = str(self.get_parameter("image_topic").value)
        joint_topic = str(self.get_parameter("joint_topic").value)

        self.positions = {name: 0.0 for name in JOINT_NAMES}
        self.publisher = self.create_publisher(Image, image_topic, 2)
        self.subscription = self.create_subscription(JointState, joint_topic, self._joint_state_callback, 10)
        self.timer = self.create_timer(1.0 / max(1.0, fps), self._publish_frame)
        self.get_logger().info(f"Publishing console visualization frames on {image_topic}")

    def _joint_state_callback(self, msg: JointState) -> None:
        for name in JOINT_NAMES:
            if name not in msg.name:
                continue
            idx = msg.name.index(name)
            if len(msg.position) > idx:
                self.positions[name] = float(msg.position[idx])

    def _publish_frame(self) -> None:
        canvas = Canvas(self.width, self.height)
        self._draw_layout(canvas)
        self._draw_top_view(canvas)
        self._draw_side_view(canvas)
        self._draw_roll_view(canvas)

        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "remibot_console_view"
        msg.height = canvas.height
        msg.width = canvas.width
        msg.encoding = "rgb8"
        msg.is_bigendian = 0
        msg.step = canvas.width * 3
        msg.data = bytes(canvas.data)
        self.publisher.publish(msg)

    def _panels(self) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
        margin = 18
        gap = 14
        top_h = self.height // 2 - margin - gap // 2
        top_w = self.width // 2 - margin - gap // 2
        roll_x = margin + top_w + gap
        side_y = margin + top_h + gap
        return (
            (margin, margin, top_w, top_h),
            (margin, side_y, self.width - 2 * margin, self.height - side_y - margin),
            (roll_x, margin, self.width - roll_x - margin, top_h),
        )

    def _draw_layout(self, canvas: Canvas) -> None:
        for panel in self._panels():
            x, y, w, h = panel
            canvas.rect(x, y, w, h, PANEL)
            canvas.frame(x, y, w, h, GRID)

    def _draw_top_view(self, canvas: Canvas) -> None:
        q = [self.positions[name] for name in JOINT_NAMES]
        x, y, w, h = self._panels()[0]
        cx = x + w // 2
        cy = y + h // 2
        radius = min(w, h) // 3
        canvas.circle(cx, cy, radius, GRID)
        canvas.line(cx - radius, cy, cx + radius, cy, GRID)
        canvas.line(cx, cy - radius, cx, cy + radius, GRID)
        angle = q[0] - math.pi / 2
        tip_x = int(cx + radius * math.cos(angle))
        tip_y = int(cy + radius * math.sin(angle))
        canvas.line(cx, cy, tip_x, tip_y, LINK, 7)
        canvas.disc(cx, cy, 11, JOINT)
        canvas.disc(tip_x, tip_y, 9, TIP)
        self._draw_value_bar(canvas, x + 22, y + h - 32, w - 44, q[0], -math.pi, math.pi)

    def _draw_side_view(self, canvas: Canvas) -> None:
        q = [self.positions[name] for name in JOINT_NAMES]
        x, y, w, h = self._panels()[1]
        base_x = x + 90
        base_y = y + h - 52
        canvas.line(x + 30, base_y, x + w - 30, base_y, GRID, 2)
        canvas.rect(base_x - 38, base_y - 20, 76, 20, (55, 65, 81))
        points = [(base_x, base_y - 20)]
        angle = -math.pi / 2
        for index, length in enumerate(LINK_LENGTHS[:4]):
            if index:
                angle += q[index] * (1 if index != 3 else -1)
            prev_x, prev_y = points[-1]
            x = int(prev_x + length * math.cos(angle))
            y = int(prev_y + length * math.sin(angle))
            points.append((x, y))

        shadow = (17, 24, 39)
        for start, end in zip(points, points[1:]):
            canvas.line(start[0] + 4, start[1] + 5, end[0] + 4, end[1] + 5, shadow, 9)
        for start, end in zip(points, points[1:]):
            canvas.line(start[0], start[1], end[0], end[1], LINK, 7)
        for x, y in points[:-1]:
            canvas.disc(x, y, 10, JOINT)
            canvas.disc(x, y, 4, BG)
        canvas.disc(points[-1][0], points[-1][1], 9, TIP)

    def _draw_roll_view(self, canvas: Canvas) -> None:
        q5 = self.positions["joint5"]
        x, y, w, h = self._panels()[2]
        cx = x + w // 2
        cy = y + h // 2
        radius = min(w, h) // 4
        canvas.circle(cx, cy, radius, GRID)
        canvas.disc(cx, cy, 8, JOINT)
        for offset in [0.0, math.pi]:
            angle = q5 + offset
            tip_x = int(cx + radius * math.cos(angle))
            tip_y = int(cy + radius * math.sin(angle))
            canvas.line(cx, cy, tip_x, tip_y, TIP, 5)
            canvas.disc(tip_x, tip_y, 5, TIP)
        self._draw_value_bar(canvas, x + 28, y + h - 36, w - 56, q5, -2.0 * math.pi, 2.0 * math.pi)

    def _draw_value_bar(self, canvas: Canvas, x: int, y: int, w: int, value: float, lo: float, hi: float) -> None:
        canvas.rect(x, y, w, 12, (55, 65, 81))
        normalized = (max(lo, min(hi, value)) - lo) / (hi - lo)
        canvas.rect(x, y, int(w * normalized), 12, LINK)
        zero = int(x + w * ((0.0 - lo) / (hi - lo)))
        canvas.rect(zero - 1, y - 3, 2, 18, TEXT)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ConsoleVisualizationRenderer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
