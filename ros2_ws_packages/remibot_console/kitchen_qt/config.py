"""Runtime constants for the Qt operator console."""

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency for lightweight mock installs
    yaml = None

JOINTS = ["J1", "J2", "J3", "J4", "J5"]
ROS_JOINT_NAMES = {ui_name: f"joint{index + 1}" for index, ui_name in enumerate(JOINTS)}
JOINT_LIMITS_RAD = {
    "J1": (-3.1416, 3.1416),
    "J2": (0.0, 2.6180),
    "J3": (0.0, 2.1817),
    "J4": (-1.8326, 1.2217),
    "J5": (-6.2832, 6.2832),
}
HISTORY_LEN = 240
DATA_HZ = 30
UI_HZ = 20

CONTROL_MODES = ["Position PID", "Impedance PD", "Velocity PID", "Teaching", "Homing"]
TOOLS = ["Spatula", "Stirrer", "Empty"]
SPEED_LEVELS = {"Slow": 0.25, "Medium": 0.60, "Fast": 1.00}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
TRAJECTORY_DIR = "teaching_data"
CONFIG_FILE = "config.yaml"
VISUALIZATION_IMAGE_TOPICS = [
    "/remibot/visualization/image",
    "/rviz/rendered_image",
    "/camera/image_raw",
]
VISUALIZATION_COMPRESSED_IMAGE_TOPICS = [
    "/remibot/visualization/image/compressed",
    "/rviz/rendered_image/compressed",
]


def load_data_config(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, Any]:
    config_path = data_dir / CONFIG_FILE
    if not config_path.exists() or yaml is None:
        return {}
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def find_mjcf(cli_arg: str | Path | None = None, data_dir: Path = DEFAULT_DATA_DIR) -> str | None:
    if cli_arg:
        return str(Path(cli_arg).expanduser())

    import os

    env_value = os.environ.get("REMIBOT_MJCF")
    if env_value:
        return str(Path(env_value).expanduser())

    config = load_data_config(data_dir)
    configured = config.get("mjcf_path")
    if configured:
        return str(Path(str(configured)).expanduser())
    return None
