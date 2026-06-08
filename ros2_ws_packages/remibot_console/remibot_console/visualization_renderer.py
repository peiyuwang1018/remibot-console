"""Lightweight ROS2 image renderer for the operator console.

This node is intentionally simple: it subscribes to /joint_states and publishes
an RGB image stream that the Qt console can display. It is a proving step for
the frame-stream architecture before introducing RViz/offscreen rendering.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState


JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5"]
LINK_LENGTHS = [92, 88, 72, 54, 34]


@dataclass
class Canvas:
    width: int
    height: int
    background: tuple[int, int, int] = (31, 41, 55)
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


class ConsoleVisualizationRenderer(Node):
    def __init__(self) -> None:
        super().__init__("remibot_visualization_renderer")
        self.declare_parameter("image_topic", "/remibot/visualization/image")
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
        self._draw_grid(canvas)
        self._draw_workspace(canvas)
        self._draw_joint_bars(canvas)
        self._draw_arm(canvas)

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

    def _draw_grid(self, canvas: Canvas) -> None:
        grid = (75, 85, 99)
        for x in range(0, canvas.width, 60):
            canvas.line(x, 0, x, canvas.height, grid)
        for y in range(0, canvas.height, 60):
            canvas.line(0, y, canvas.width, y, grid)

    def _draw_workspace(self, canvas: Canvas) -> None:
        canvas.rect(0, canvas.height - 86, canvas.width, 86, (45, 55, 72))
        canvas.line(0, canvas.height - 86, canvas.width, canvas.height - 86, (148, 163, 184), 2)
        canvas.rect(canvas.width // 2 - 90, canvas.height - 72, 180, 28, (55, 65, 81))

    def _draw_joint_bars(self, canvas: Canvas) -> None:
        x = 24
        y = 28
        for index, name in enumerate(JOINT_NAMES):
            value = self.positions[name]
            bar_y = y + index * 28
            canvas.rect(x, bar_y, 132, 10, (55, 65, 81))
            normalized = max(-1.0, min(1.0, value / math.pi))
            fill = int((normalized + 1.0) * 66)
            canvas.rect(x, bar_y, fill, 10, (102, 201, 164))
            canvas.rect(x + 66, bar_y - 3, 2, 16, (209, 213, 219))

    def _draw_arm(self, canvas: Canvas) -> None:
        q = [self.positions[name] for name in JOINT_NAMES]
        base_x = canvas.width // 2
        base_y = canvas.height - 88
        yaw_offset = 55 * math.sin(q[0])
        points = [(base_x + int(yaw_offset), base_y)]
        angle = -math.pi / 2
        for index, length in enumerate(LINK_LENGTHS):
            if index > 0:
                angle += q[index] * (1 if index != 3 else -1)
            prev_x, prev_y = points[-1]
            x = int(prev_x + length * math.cos(angle))
            y = int(prev_y + length * math.sin(angle))
            points.append((x, y))

        shadow = (17, 24, 39)
        link = (102, 201, 164)
        joint = (232, 185, 85)
        tip = (122, 178, 240)
        for start, end in zip(points, points[1:]):
            canvas.line(start[0] + 4, start[1] + 5, end[0] + 4, end[1] + 5, shadow, 9)
        for start, end in zip(points, points[1:]):
            canvas.line(start[0], start[1], end[0], end[1], link, 7)
        for x, y in points[:-1]:
            canvas.disc(x, y, 10, joint)
            canvas.disc(x, y, 4, (31, 41, 55))
        canvas.disc(points[-1][0], points[-1][1], 9, tip)


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
