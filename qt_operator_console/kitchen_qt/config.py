"""Runtime constants for the Qt operator console."""

from pathlib import Path

JOINTS = ["J1", "J2", "J3", "J4", "J5"]
HISTORY_LEN = 240
DATA_HZ = 30
UI_HZ = 20

CONTROL_MODES = ["Position PID", "Impedance PD", "Velocity PID", "Teaching", "Homing"]
TOOLS = ["Spatula", "Stirrer", "Empty"]
SPEED_LEVELS = {"Slow": 0.25, "Medium": 0.60, "Fast": 1.00}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
TRAJECTORY_DIR = "teaching_data"
