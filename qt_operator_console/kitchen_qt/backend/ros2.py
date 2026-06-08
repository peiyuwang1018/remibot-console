"""ROS2 backend skeleton for Ubuntu integration."""

from __future__ import annotations

from threading import Thread
from typing import Any
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage

from ..config import JOINTS, ROS_JOINT_NAMES, VISUALIZATION_COMPRESSED_IMAGE_TOPICS, VISUALIZATION_IMAGE_TOPICS
from ..models import JointState
from ..models import RobotState
from .base import ArmBackend


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
        self.trajectory_client = None
        self.image_subs = []
        self.compressed_image_subs = []
        self.preview_positions: list[float] | None = None
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(100)
        self.preview_timer.timeout.connect(self._publish_preview_joint_state)
        self._owns_rclpy = False

    def start(self) -> None:
        try:
            import rclpy
            from control_msgs.action import FollowJointTrajectory
            from rclpy.action import ActionClient
            from rclpy.executors import MultiThreadedExecutor
            from rclpy.duration import Duration
            from sensor_msgs.msg import Joy
            from sensor_msgs.msg import CompressedImage
            from sensor_msgs.msg import Image
            from sensor_msgs.msg import JointState as RosJointState
            from trajectory_msgs.msg import JointTrajectoryPoint
        except ImportError:
            self.available = False
            with self.state.lock:
                self.state.world = "SimulationOnly"
                self.state.hardware = "Disconnected"
            self.state.set_backend(self.name, False)
            self.state.log("rclpy unavailable; ROS2 backend running in disconnected placeholder mode", "WARN")
            self.state_changed.emit()
            return

        self.rclpy = rclpy
        self.Duration = Duration
        self.FollowJointTrajectory = FollowJointTrajectory
        self.JointTrajectoryPoint = JointTrajectoryPoint
        self.RosJointState = RosJointState
        self.Image = Image
        self.CompressedImage = CompressedImage
        if not rclpy.ok():
            rclpy.init(args=None)
            self._owns_rclpy = True
        self.node = rclpy.create_node("remibot_console_backend")
        self.joint_state_pub = self.node.create_publisher(RosJointState, "/joint_states", 10)
        self.joy_sub = self.node.create_subscription(Joy, "/joy", self._joy_callback, 10)
        self.joint_state_sub = self.node.create_subscription(RosJointState, "/joint_states", self._joint_state_callback, 10)
        self.image_subs = [
            self.node.create_subscription(Image, topic, self._image_callback, 2)
            for topic in VISUALIZATION_IMAGE_TOPICS
        ]
        self.compressed_image_subs = [
            self.node.create_subscription(CompressedImage, topic, self._compressed_image_callback, 2)
            for topic in VISUALIZATION_COMPRESSED_IMAGE_TOPICS
        ]
        self.trajectory_client = ActionClient(self.node, FollowJointTrajectory, "/arm_controller/follow_joint_trajectory")
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor_thread = Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()
        with self.state.lock:
            self.state.world = "SimulationOnly"
            self.state.hardware = "ROS graph"
        self.available = True
        self.state.set_backend(self.name, True)
        self.state.log("ROS2 backend started; GUI preview publishes /joint_states")
        self.state.log(
            "Visualization image stream listening on: "
            + ", ".join(VISUALIZATION_IMAGE_TOPICS + VISUALIZATION_COMPRESSED_IMAGE_TOPICS)
        )
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

    def request_control_authority(self, source: str) -> None:
        with self.state.lock:
            self.state.control_source = source
            if source == "Joystick":
                self.state.joystick_connected = True
        self.state.log(f"Control authority requested: {source}")
        if source == "Joystick":
            self.state.log("Joystick authority requires joy_arm_control or an arbitration node to be running", "WARN")
        self.state_changed.emit()

    def start_homing(self) -> None:
        self._todo("call /homing/start")

    def enter_teaching(self) -> None:
        with self.state.lock:
            self.state.teaching_active = True
            self.state.mode = "Teaching"
            self.state.status = "TEACHING"
            self.state.control_source = "TeachingDrag"
            self.state.data_source = "real_teaching"
        self.request_mode("Teaching")
        self.state_changed.emit()

    def exit_teaching(self) -> None:
        with self.state.lock:
            self.state.teaching_active = False
            self.state.recording = False
            self.state.mode = "Position PID"
            self.state.status = "READY"
            self.state.control_source = "GUI"
        self.request_mode("Position PID")
        self.state_changed.emit()

    def set_recording(self, enabled: bool) -> None:
        with self.state.lock:
            self.state.recording = enabled
            if enabled:
                self.state.recorded_points.clear()
        self.state.log("Teaching recording started" if enabled else "Teaching recording stopped")
        self.state_changed.emit()

    def send_joint_target(self, joint: str, target_rad: float) -> None:
        self.preview_joint_targets({joint: target_rad})

    def preview_joint_targets(self, targets_rad: dict[str, float]) -> None:
        self._command_joint_targets(targets_rad, duration_s=1.0, action_label="Preview")

    def execute_joint_targets(self, targets_rad: dict[str, float]) -> None:
        self._command_joint_targets(targets_rad, duration_s=2.5, action_label="Plan/execute")

    def _command_joint_targets(self, targets_rad: dict[str, float], duration_s: float, action_label: str) -> None:
        with self.state.lock:
            for joint, target in targets_rad.items():
                if joint in self.state.joints:
                    old = self.state.joints[joint]
                    self.state.set_joint(
                        joint,
                        JointState(old.current, target, 0.0, old.temperature, old.voltage, old.fault),
                    )
            self.state.control_source = "GUI"
            ordered_positions = [self.state.joints[joint].position for joint in JOINTS]
            self.preview_positions = [float(value) for value in ordered_positions]

        if not self.available or self.node is None or self.joint_state_pub is None:
            self.state.log("ROS2 preview unavailable; pose stored in console state only", "WARN")
            self.state_changed.emit()
            return

        if self._send_joint_trajectory(duration_s):
            self.preview_timer.stop()
            self.state.log(f"{action_label} trajectory sent to /arm_controller/follow_joint_trajectory")
            self.state_changed.emit()
            return

        publisher_count = self.node.count_publishers("/joint_states") if self.node is not None else 0
        if publisher_count > 1:
            self.preview_timer.stop()
            self.state.log(
                f"No trajectory controller found and {publisher_count - 1} external /joint_states publisher(s) exist; direct preview blocked to avoid flicker",
                "WARN",
            )
            self.state_changed.emit()
            return
        self._publish_preview_joint_state()
        if not self.preview_timer.isActive():
            self.preview_timer.start()
        self.state.log(f"No trajectory controller found; {action_label.lower()} joint state streaming to /joint_states", "WARN")
        self.state_changed.emit()

    def _send_joint_trajectory(self, duration_s: float) -> bool:
        if self.preview_positions is None or self.trajectory_client is None:
            return False
        if not self.trajectory_client.wait_for_server(timeout_sec=0.1):
            return False
        goal = self.FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = [ROS_JOINT_NAMES[joint] for joint in JOINTS]
        point = self.JointTrajectoryPoint()
        point.positions = list(self.preview_positions)
        point.velocities = [0.0] * len(JOINTS)
        point.time_from_start = self.Duration(seconds=duration_s).to_msg()
        goal.trajectory.points = [point]
        future = self.trajectory_client.send_goal_async(goal)
        future.add_done_callback(self._preview_goal_response)
        return True

    def _preview_goal_response(self, future) -> None:
        try:
            goal_handle = future.result()
        except Exception as exc:  # noqa: BLE001 - keep GUI alive across ROS errors
            self.state.log(f"Preview trajectory failed: {exc}", "WARN")
            self.state_changed.emit()
            return
        if not goal_handle.accepted:
            self.state.log("Preview trajectory rejected by controller", "WARN")
            self.state_changed.emit()

    def _joy_callback(self, msg) -> None:
        active = any(abs(value) > 0.05 for value in msg.axes) or any(bool(value) for value in msg.buttons)
        with self.state.lock:
            self.state.joystick_connected = True
            self.state.joystick_active = active
            if active:
                self.state.control_source = "Joystick"
        self.state_changed.emit()

    def _joint_state_callback(self, msg) -> None:
        updated = False
        with self.state.lock:
            for ui_joint, ros_joint in ROS_JOINT_NAMES.items():
                if ros_joint not in msg.name:
                    continue
                idx = msg.name.index(ros_joint)
                position = msg.position[idx] if len(msg.position) > idx else self.state.joints[ui_joint].position
                velocity = msg.velocity[idx] if len(msg.velocity) > idx else 0.0
                old = self.state.joints[ui_joint]
                self.state.set_joint(
                    ui_joint,
                    JointState(old.current, float(position), float(velocity), old.temperature, old.voltage, old.fault),
                )
                updated = True
            if updated:
                self.state.data_source = "real_teaching" if self.state.teaching_active else "ros_joint_state"
                if self.state.teaching_active and self.state.recording:
                    self.state.recorded_points.append({
                        "time": datetime.now().isoformat(timespec="milliseconds"),
                        "source": self.state.data_source,
                        "q": [self.state.joints[j].position for j in JOINTS],
                        "velocity": [self.state.joints[j].velocity for j in JOINTS],
                    })
        if updated:
            self.state_changed.emit()

    def _image_callback(self, msg) -> None:
        image = self._qimage_from_ros_image(msg)
        if image is not None:
            self.visualization_frame.emit(image)

    def _compressed_image_callback(self, msg) -> None:
        image = QImage()
        if image.loadFromData(bytes(msg.data)):
            self.visualization_frame.emit(image.copy())

    def _qimage_from_ros_image(self, msg) -> QImage | None:
        width = int(msg.width)
        height = int(msg.height)
        if width <= 0 or height <= 0:
            return None
        encoding = msg.encoding.lower()
        data = bytes(msg.data)
        step = int(msg.step)
        if encoding in {"rgb8", "8uc3"}:
            return QImage(data, width, height, step, QImage.Format_RGB888).copy()
        if encoding == "bgr8":
            return QImage(data, width, height, step, QImage.Format_RGB888).rgbSwapped().copy()
        if encoding in {"rgba8", "bgra8"}:
            image = QImage(data, width, height, step, QImage.Format_RGBA8888)
            if encoding == "bgra8":
                image = image.rgbSwapped()
            return image.copy()
        if encoding in {"mono8", "8uc1"}:
            return QImage(data, width, height, step, QImage.Format_Grayscale8).copy()
        self.state.log(f"Unsupported visualization image encoding: {msg.encoding}", "WARN")
        self.state_changed.emit()
        return None

    def _publish_preview_joint_state(self) -> None:
        if (
            self.preview_positions is None
            or not self.available
            or self.node is None
            or self.joint_state_pub is None
        ):
            return
        publisher_count = self.node.count_publishers("/joint_states")
        if publisher_count > 1:
            self.preview_timer.stop()
            self.state.log("Direct preview stopped because another /joint_states publisher is active", "WARN")
            self.state_changed.emit()
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
