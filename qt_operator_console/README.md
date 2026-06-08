# Qt Operator Console

This folder contains a Qt/PySide version of the kitchen arm operator console. It is intended as the long-term architecture for native Qt controls, embedded MuJoCo visualization, richer diagnostics, and a more standard desktop application framework.

The app keeps the functional surface expected from the kitchen arm upper computer:

- joint telemetry and rolling plots
- mode/status/contact monitoring
- manual joint targets and teleop controls
- homing state machine view
- waypoint saving/execution/deletion
- teaching recording save/clear
- PID tuning and step response preview
- tool identification and tool library
- embedded MuJoCo visualization with image-stream fallback
- structured logs

## Run

From the repository root:

```powershell
python -m pip install -r qt_operator_console/requirements.txt
python qt_operator_console/run_qt_console.py
```

If PySide6 installation fails on Windows with a message about `Windows Long Path support`, install it inside a short-path virtual environment instead of the Microsoft Store Python user package directory:

```powershell
cd D:\Arm_Gui
python -m venv C:\tmp\armqt
C:\tmp\armqt\Scripts\python.exe -m pip install --upgrade pip
C:\tmp\armqt\Scripts\python.exe -m pip install -r qt_operator_console\requirements.txt
C:\tmp\armqt\Scripts\python.exe qt_operator_console\run_qt_console.py
```

The short `C:\tmp\armqt` path avoids the very long package path used by the Store Python installation.

Optional:

```powershell
python qt_operator_console/run_qt_console.py --backend mock --data-dir data
```

Optional MuJoCo viewport:

```bash
python -m pip install -r requirements-mujoco.txt
python qt_operator_console/run_qt_console.py --backend mock --mjcf /path/to/remibot.xml
```

On Ubuntu/ROS2:

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
source install/setup.bash
python qt_operator_console/run_qt_console.py --backend ros2
```

## Architecture

- `kitchen_qt/models.py`: thread-safe robot state.
- `kitchen_qt/storage.py`: JSON persistence shared with the existing `data/` directory.
- `kitchen_qt/backend/base.py`: Qt `QObject` backend contract with a `state_changed` signal.
- `kitchen_qt/backend/mock.py`: Qt timer driven mock backend.
- `kitchen_qt/backend/ros2.py`: ROS2 adapter skeleton for Ubuntu.
- `kitchen_qt/ui/main_window.py`: `QMainWindow` with tabbed functional pages.
- `kitchen_qt/ui/widgets/plot.py`: lightweight Qt painter plot widget.

## Visualization Path

Qt is the host for the operator visualization:

- MuJoCo is the preferred embedded 3D viewport and renders from the current joint state.
- RViz remains external for MoveIt planning and debugging.
- RViz capture is an opt-in bridge, not the default display path.
- The 2D/image-stream path remains available as a fallback.
