"""ROS2 backend skeleton for Ubuntu integration."""

from __future__ import annotations

from threading import Thread
from typing import Any

from PySide6.QtCore import QTimer

from ..config import JOINTS
from ..models import JointState
from ..models import RobotState
from .base import ArmBackend


ROS_JOINT_NAMES = {ui_name: f"joint{index + 1}" for index, ui_name in enumerate(JOINTS)}


class Ros2Backend(ArmBackend):
    name = "ros2"

    def __init__(self, state: RobotState) -> None:
        super().__init__()
        self.state = state
        self.available = False
        self.rclpy = None
        self.node = None
        self.executor = None
        self.executor_thread: Thread | None = None
        self.joint_state_pub = None
        self.preview_positions: list[float] | None = None
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(100)
        self.preview_timer.timeout.connect(self._publish_preview_joint_state)
        self._owns_rclpy = False

    def start(self) -> None:
        try:
            import rclpy
            from rclpy.executors import MultiThreadedExecutor
            from sensor_msgs.msg import JointState as RosJointState
        except ImportError:
            self.available = False
            self.state.set_backend(self.name, False)
            self.state.log("rclpy unavailable; ROS2 backend running in disconnected placeholder mode", "WARN")
            self.state_changed.emit()
            return

        self.rclpy = rclpy
        self.RosJointState = RosJointState
        if not rclpy.ok():
            rclpy.init(args=None)
            self._owns_rclpy = True
        self.node = rclpy.create_node("remibot_console_backend")
        self.joint_state_pub = self.node.create_publisher(RosJointState, "/joint_states", 10)
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor_thread = Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()
        self.available = True
        self.state.set_backend(self.name, True)
        self.state.log("ROS2 backend started; GUI preview publishes /joint_states")
        self.state_changed.emit()

    def stop(self) -> None:
        self.preview_timer.stop()
        if self.executor is not None:
            self.executor.shutdown()
        if self.executor_thread is not None:
            self.executor_thread.join(timeout=1.0)
        if self.node is not None:
            self.node.destroy_node()
        if self.rclpy is not None and self._owns_rclpy and self.rclpy.ok():
            self.rclpy.shutdown()
        self.state.set_backend(self.name, False)
        self.state_changed.emit()

    def set_estop(self, enabled: bool) -> None:
        self._todo(f"publish/request estop={enabled}")

    def request_mode(self, mode: str) -> None:
        self._todo(f"call /mode_request: {mode}")

    def start_homing(self) -> None:
        self._todo("call /homing/start")

    def enter_teaching(self) -> None:
        self.request_mode("Teaching")

    def exit_teaching(self) -> None:
        self.request_mode("Position PID")

    def set_recording(self, enabled: bool) -> None:
        self._todo(f"recording={enabled}")

    def send_joint_target(self, joint: str, target_rad: float) -> None:
        self.preview_joint_targets({joint: target_rad})

    def preview_joint_targets(self, targets_rad: dict[str, float]) -> None:
        with self.state.lock:
            for joint, target in targets_rad.items():
                if joint in self.state.joints:
                    old = self.state.joints[joint]
                    self.state.set_joint(
                        joint,
                        JointState(old.current, target, 0.0, old.temperature, old.voltage, old.fault),
                    )
            ordered_positions = [self.state.joints[joint].position for joint in JOINTS]
            self.preview_positions = [float(value) for value in ordered_positions]

        if not self.available or self.node is None or self.joint_state_pub is None:
            self.state.log("ROS2 preview unavailable; pose stored in console state only", "WARN")
            self.state_changed.emit()
            return

        self._publish_preview_joint_state()
        if not self.preview_timer.isActive():
            self.preview_timer.start()
        self.state.log("Preview joint state streaming to /joint_states")
        self.state_changed.emit()

    def _publish_preview_joint_state(self) -> None:
        if (
            self.preview_positions is None
            or not self.available
            or self.node is None
            or self.joint_state_pub is None
        ):
            return
        msg = self.RosJointState()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.name = [ROS_JOINT_NAMES[joint] for joint in JOINTS]
        msg.position = list(self.preview_positions)
        msg.velocity = [0.0] * len(JOINTS)
        msg.effort = [0.0] * len(JOINTS)
        self.joint_state_pub.publish(msg)

    def write_pid(self, joint: str, kp: float, ki: float, kd: float) -> dict[str, Any]:
        self._todo(f"set PID for {joint}")
        return {"joint": joint, "kp": kp, "ki": ki, "kd": kd}

    def run_step_test(self, joint: str, amplitude: float) -> None:
        self._todo(f"run step test {joint}, amplitude={amplitude:.3f}")

    def identify_tool(self, tool: str) -> None:
        self._todo(f"identify tool {tool}")

    def _todo(self, message: str) -> None:
        self.state.log(f"ROS2 TODO: {message}", "WARN")
        self.state_changed.emit()
