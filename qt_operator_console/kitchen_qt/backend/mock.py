"""Qt timer based mock backend."""

from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Any

from PySide6.QtCore import QTimer

from ..config import DATA_HZ, JOINTS
from ..models import JointState, RobotState
from .base import ArmBackend


class MockBackend(ArmBackend):
    name = "mock"

    def __init__(self, state: RobotState) -> None:
        super().__init__()
        self.state = state
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.t = 0.0
        self.homing_elapsed = 0.0
        self.step_elapsed = 0.0

    def start(self) -> None:
        self.state.set_backend(self.name, True)
        self.state.log("Mock backend connected")
        self.timer.start(int(1000 / DATA_HZ))
        self.state_changed.emit()

    def stop(self) -> None:
        self.timer.stop()
        self.state.set_backend(self.name, False)
        self.state.log("Backend stopped")
        self.state_changed.emit()

    def set_estop(self, enabled: bool) -> None:
        with self.state.lock:
            self.state.estop = enabled
            self.state.status = "ESTOP" if enabled else "READY"
        self.state.log("Emergency stop engaged" if enabled else "Emergency stop released", "WARN")
        self.state_changed.emit()

    def request_mode(self, mode: str) -> None:
        with self.state.lock:
            if self.state.estop:
                self.state.log(f"Mode request ignored during ESTOP: {mode}", "WARN")
                return
            self.state.mode = mode
            self.state.status = "TEACHING" if mode == "Teaching" else "READY"
        self.state.log(f"Control mode requested: {mode}")
        self.state_changed.emit()

    def start_homing(self) -> None:
        with self.state.lock:
            if self.state.estop:
                self.state.log("Homing blocked by ESTOP", "WARN")
                return
            self.state.homing_active = True
            self.state.status = "HOMING"
            self.state.mode = "Homing"
            self.state.homing_steps = {name: "pending" for name in self.state.homing_steps}
        self.homing_elapsed = 0.0
        self.state.log("Homing sequence requested")
        self.state_changed.emit()

    def enter_teaching(self) -> None:
        with self.state.lock:
            self.state.teaching_active = True
            self.state.mode = "Teaching"
            self.state.status = "TEACHING"
        self.state.log("Teaching mode entered")
        self.state_changed.emit()

    def exit_teaching(self) -> None:
        with self.state.lock:
            self.state.teaching_active = False
            self.state.recording = False
            self.state.mode = "Position PID"
            self.state.status = "READY"
        self.state.log("Teaching mode exited")
        self.state_changed.emit()

    def set_recording(self, enabled: bool) -> None:
        with self.state.lock:
            self.state.recording = enabled
            if enabled:
                self.state.recorded_points.clear()
        self.state.log("Teaching recording started" if enabled else "Teaching recording stopped")
        self.state_changed.emit()

    def send_joint_target(self, joint: str, target_rad: float) -> None:
        with self.state.lock:
            current = self.state.joints[joint]
            current.position = target_rad
        self.state.log(f"Joint target sent: {joint} -> {target_rad:.3f} rad")
        self.state_changed.emit()

    def preview_joint_targets(self, targets_rad: dict[str, float]) -> None:
        with self.state.lock:
            for joint, target in targets_rad.items():
                if joint in self.state.joints:
                    self.state.joints[joint].position = target
        self.state.log("Mock preview pose updated from GUI sliders")
        self.state_changed.emit()

    def write_pid(self, joint: str, kp: float, ki: float, kd: float) -> dict[str, Any]:
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "joint": joint,
            "kp": kp,
            "ki": ki,
            "kd": kd,
        }
        with self.state.lock:
            self.state.pid_history.append(entry)
        self.state.log(f"PID updated for {joint}: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}")
        self.state_changed.emit()
        return entry

    def run_step_test(self, joint: str, amplitude: float) -> None:
        with self.state.lock:
            self.state.step_running = True
            self.state.step_results = {}
            for values in self.state.step_history.values():
                values.clear()
        self.step_elapsed = 0.0
        self.state.log(f"Step test started: {joint}, amplitude={amplitude:.3f}")
        self.state_changed.emit()

    def identify_tool(self, tool: str) -> None:
        mass = round(random.uniform(0.15, 0.30), 3)
        com = [round(random.gauss(0.004, 0.004), 4) for _ in range(3)]
        residual = round(random.uniform(0.010, 0.030), 4)
        with self.state.lock:
            self.state.tools[tool] = {
                "mass": mass,
                "com": com,
                "residual": residual,
                "identified": datetime.now().isoformat(timespec="seconds"),
            }
        self.state.log(f"Tool identification finished: {tool}, mass={mass} kg")
        self.state_changed.emit()

    def _tick(self) -> None:
        if self.state.estop:
            self.state_changed.emit()
            return
        dt = 1.0 / DATA_HZ
        self.t += dt
        self._update_joints()
        self._update_pose()
        self._update_contact()
        self._update_teaching_recording()
        self._update_homing(dt)
        self._update_step(dt)
        self.state_changed.emit()

    def _update_joints(self) -> None:
        for index, joint in enumerate(JOINTS):
            current = 0.8 + 0.35 * index + 0.9 * math.sin(self.t * 1.5 + index) + random.gauss(0, 0.035)
            position = 0.45 * math.sin(self.t * 0.34 + index) + index * 0.18
            velocity = 0.18 * math.cos(self.t * 0.34 + index) + random.gauss(0, 0.012)
            temp = 34.0 + index * 1.8 + abs(current) * 2.0 + random.gauss(0, 0.2)
            fault = "WARN" if temp > 48.0 else "OK"
            self.state.set_joint(joint, JointState(current, position, velocity, temp, 24.0 + random.gauss(0, 0.05), fault))

    def _update_pose(self) -> None:
        with self.state.lock:
            self.state.pose.xyz = [
                0.23 + 0.025 * math.sin(self.t * 0.2),
                0.01 + 0.018 * math.cos(self.t * 0.24),
                0.35 + 0.02 * math.sin(self.t * 0.17),
            ]
            self.state.pose.rpy = [0.0, 0.2 * math.sin(self.t * 0.12), 0.1 * math.cos(self.t * 0.14)]

    def _update_contact(self) -> None:
        phase = int(self.t / 5.0) % 4
        with self.state.lock:
            self.state.contact = ["No Contact", "Contact", "Wedged", "No Contact"][phase]

    def _update_teaching_recording(self) -> None:
        with self.state.lock:
            if not (self.state.teaching_active and self.state.recording):
                return
            self.state.recorded_points.append({
                "t": round(self.t, 3),
                "q": [self.state.joints[j].position for j in JOINTS],
                "current": [self.state.joints[j].current for j in JOINTS],
            })

    def _update_homing(self, dt: float) -> None:
        with self.state.lock:
            if not self.state.homing_active:
                return
            self.homing_elapsed += dt
            steps = list(self.state.homing_steps)
            done_count = sum(1 for value in self.state.homing_steps.values() if value == "done")
            in_progress = [name for name, value in self.state.homing_steps.items() if value == "in_progress"]
            if not in_progress and done_count < len(steps):
                self.state.homing_steps[steps[done_count]] = "in_progress"
                self.homing_elapsed = 0.0
                self.state.log(f"Homing step started: {steps[done_count]}")
            elif in_progress and self.homing_elapsed >= 2.0:
                self.state.homing_steps[in_progress[0]] = "done"
                self.homing_elapsed = 0.0
                self.state.log(f"Homing step complete: {in_progress[0]}")
                if all(value == "done" for value in self.state.homing_steps.values()):
                    self.state.homing_active = False
                    self.state.status = "READY"
                    self.state.mode = "Position PID"
                    self.state.log("Homing sequence complete")

    def _update_step(self, dt: float) -> None:
        with self.state.lock:
            if not self.state.step_running:
                return
            self.step_elapsed += dt
            for index, joint in enumerate(JOINTS):
                response = 1.0 - math.exp(-self.step_elapsed * (2.2 + index * 0.1))
                response += 0.06 * math.sin(self.step_elapsed * 18.0) * math.exp(-self.step_elapsed * 1.8)
                self.state.step_history[joint].append(response + random.gauss(0, 0.008))
            if self.step_elapsed >= 3.0:
                self.state.step_running = False
                self.state.step_results = {"rise_time_s": 0.68, "overshoot_pct": 4.5, "settling_time_s": 1.42}
                self.state.log("Step test complete")
