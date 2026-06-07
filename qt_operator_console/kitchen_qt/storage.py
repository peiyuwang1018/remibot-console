"""JSON persistence for the Qt operator console."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import TRAJECTORY_DIR
from .models import RobotState


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / TRAJECTORY_DIR).mkdir(exist_ok=True)

    def load_all(self, state: RobotState) -> None:
        state.waypoints = self._load("waypoints.json", self._default_waypoints())
        state.tools = self._load("tools.json", self._default_tools())
        state.pid_history = self._load("pid_history.json", [])

    def save_waypoints(self, state: RobotState) -> None:
        self._save("waypoints.json", state.waypoints)

    def save_tools(self, state: RobotState) -> None:
        self._save("tools.json", state.tools)

    def save_pid_history(self, state: RobotState) -> None:
        self._save("pid_history.json", state.pid_history[-80:])

    def save_teaching(self, points: list[dict[str, Any]]) -> Path:
        name = datetime.now().strftime("trajectory_%Y%m%d_%H%M%S.json")
        path = self.data_dir / TRAJECTORY_DIR / name
        path.write_text(json.dumps(points, indent=2), encoding="utf-8")
        return path

    def _load(self, file_name: str, default: Any) -> Any:
        path = self.data_dir / file_name
        if not path.exists():
            self._save(file_name, default)
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._save(file_name, default)
            return default

    def _save(self, file_name: str, value: Any) -> None:
        (self.data_dir / file_name).write_text(json.dumps(value, indent=2), encoding="utf-8")

    @staticmethod
    def _default_waypoints() -> dict[str, dict[str, Any]]:
        return {
            "home": {"q": [0, 0, 0, 0, 0], "desc": "Neutral folded pose", "tags": ["system"]},
            "above_pan": {"q": [0.2, 1.1, 0.8, -0.3, 0.0], "desc": "Ready above pan", "tags": ["cooking"]},
        }

    @staticmethod
    def _default_tools() -> dict[str, dict[str, Any]]:
        return {
            "Spatula": {"mass": 0.231, "com": [0.008, -0.002, 0.076], "residual": 0.018},
            "Stirrer": {"mass": 0.156, "com": [0.002, 0.001, 0.092], "residual": 0.021},
            "Empty": {"mass": 0.0, "com": [0.0, 0.0, 0.0], "residual": 0.0},
        }
