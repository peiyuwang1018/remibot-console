"""Runtime constants for the Qt operator console."""

from pathlib import Path

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
VISUALIZATION_IMAGE_TOPICS = [
    "/remibot/visualization/image",
    "/rviz/rendered_image",
    "/camera/image_raw",
]
VISUALIZATION_COMPRESSED_IMAGE_TOPICS = [
    "/remibot/visualization/image/compressed",
    "/rviz/rendered_image/compressed",
]
