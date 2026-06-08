"""Qt backend interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from PySide6.QtCore import QObject, Signal


class ArmBackend(QObject):
    state_changed = Signal()
    visualization_frame = Signal(object)

    name = "base"

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_estop(self, enabled: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def request_mode(self, mode: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def request_control_authority(self, source: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_homing(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def enter_teaching(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def exit_teaching(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_recording(self, enabled: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_joint_target(self, joint: str, target_rad: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def preview_joint_targets(self, targets_rad: dict[str, float]) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute_joint_targets(self, targets_rad: dict[str, float]) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_pid(self, joint: str, kp: float, ki: float, kd: float) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def run_step_test(self, joint: str, amplitude: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def identify_tool(self, tool: str) -> None:
        raise NotImplementedError
