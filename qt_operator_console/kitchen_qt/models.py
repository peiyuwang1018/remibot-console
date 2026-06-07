"""State models shared by Qt widgets and backend adapters."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any

from .config import HISTORY_LEN, JOINTS


@dataclass
class JointState:
    current: float = 0.0
    position: float = 0.0
    velocity: float = 0.0
    temperature: float = 34.0
    voltage: float = 24.0
    fault: str = "OK"


@dataclass
class PoseState:
    xyz: list[float] = field(default_factory=lambda: [0.23, 0.01, 0.35])
    rpy: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class LogEntry:
    text: str
    level: str = "INFO"


class RobotState:
    def __init__(self) -> None:
        self.lock = RLock()
        self.joints = {name: JointState() for name in JOINTS}
        self.histories = {
            "Current": {name: deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN) for name in JOINTS},
            "Position": {name: deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN) for name in JOINTS},
            "Velocity": {name: deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN) for name in JOINTS},
        }
        self.step_history = {name: deque(maxlen=180) for name in JOINTS}
        self.pose = PoseState()
        self.backend = "mock"
        self.connected = False
        self.world = "SimulationOnly"
        self.hardware = "Disconnected"
        self.homed = False
        self.status = "READY"
        self.mode = "Position PID"
        self.contact = "No Contact"
        self.joystick_connected = False
        self.joystick_active = False
        self.control_source = "GUI"
        self.data_source = "sim"
        self.estop = False
        self.tool = "Spatula"
        self.homing_active = False
        self.homing_steps = {
            "J1 photogate": "pending",
            "Lift axis": "pending",
            "J2-J4 gravity settle": "pending",
            "J5 vision alignment": "pending",
        }
        self.teaching_active = False
        self.recording = False
        self.recorded_points: list[dict[str, Any]] = []
        self.waypoints: dict[str, dict[str, Any]] = {}
        self.tools: dict[str, dict[str, Any]] = {}
        self.pid_history: list[dict[str, Any]] = []
        self.step_running = False
        self.step_results: dict[str, float] = {}
        self.logs: deque[LogEntry] = deque(maxlen=300)
        self.log("Qt operator console initialized")

    def log(self, message: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        with self.lock:
            self.logs.append(LogEntry(f"[{ts}] [{level}] {message}", level))

    def set_backend(self, name: str, connected: bool) -> None:
        with self.lock:
            self.backend = name
            self.connected = connected

    def set_joint(self, name: str, state: JointState) -> None:
        with self.lock:
            self.joints[name] = state
            self.histories["Current"][name].append(state.current)
            self.histories["Position"][name].append(state.position)
            self.histories["Velocity"][name].append(state.velocity)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "joints": {k: JointState(**vars(v)) for k, v in self.joints.items()},
                "histories": {signal: {j: list(values) for j, values in by_joint.items()} for signal, by_joint in self.histories.items()},
                "step_history": {k: list(v) for k, v in self.step_history.items()},
                "pose": PoseState(list(self.pose.xyz), list(self.pose.rpy)),
                "backend": self.backend,
                "connected": self.connected,
                "world": self.world,
                "hardware": self.hardware,
                "homed": self.homed,
                "status": self.status,
                "mode": self.mode,
                "contact": self.contact,
                "joystick_connected": self.joystick_connected,
                "joystick_active": self.joystick_active,
                "control_source": self.control_source,
                "data_source": self.data_source,
                "estop": self.estop,
                "tool": self.tool,
                "homing_active": self.homing_active,
                "homing_steps": dict(self.homing_steps),
                "teaching_active": self.teaching_active,
                "recording": self.recording,
                "recorded_count": len(self.recorded_points),
                "waypoints": dict(self.waypoints),
                "tools": dict(self.tools),
                "pid_history": list(self.pid_history),
                "step_running": self.step_running,
                "step_results": dict(self.step_results),
                "logs": list(self.logs),
            }
