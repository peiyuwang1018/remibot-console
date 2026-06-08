# Kitchen Arm Operator Console

This repository now keeps only the Qt/PySide operator console for the kitchen robot arm. The GUI is designed as a professional desktop upper-computer application for monitoring, teleoperation, waypoint capture, homing, tuning, tool identification, and future RViz/MuJoCo integration.

## Run On Windows

If PySide6 is already installed:

```powershell
python kitchen_arm_gui.py
```

Recommended short-path virtual environment, especially for Microsoft Store Python:

```powershell
cd D:\Arm_Gui
python -m venv C:\tmp\armqt
C:\tmp\armqt\Scripts\python.exe -m pip install --upgrade pip
C:\tmp\armqt\Scripts\python.exe -m pip install -r requirements.txt
C:\tmp\armqt\Scripts\python.exe kitchen_arm_gui.py
```

You can also launch the Qt subproject directly:

```powershell
C:\tmp\armqt\Scripts\python.exe qt_operator_console\run_qt_console.py
```

## Run On Ubuntu/ROS2

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
source install/setup.bash
python kitchen_arm_gui.py --backend ros2
```

For UI-only work without ROS2:

```bash
python kitchen_arm_gui.py --backend mock
```

If `rclpy` is not available, `--backend ros2` still opens the console in a disconnected placeholder mode so Ubuntu UI work can continue without a sourced ROS2 workspace.

RViz should be started by the ROS2 bringup layer, not by the GUI process. The intended Ubuntu integration is to install this console as a Python package inside `/home/peiyu/kitchen_arm_ws/src`, then launch MoveIt, RViz, CANdle, joystick nodes, scene loading, and the GUI from one bringup script or ROS2 launch file.

RViz display linkage comes from the ROS2 graph: publish valid `/joint_states`, `robot_description`, TF, markers, and MoveIt planning scene topics, then RViz updates the arm model without the GUI directly controlling the RViz window.

Current workspace integration:

```bash
cd ~/kitchen_arm_ws
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
colcon build --packages-select remibot_console remibot_bringup
source install/setup.bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py
```

The bringup starts a lightweight visualization frame renderer by default. It subscribes `/joint_states`, publishes `/remibot/visualization/image`, and the Qt Workbench displays that stream in the center viewport. You can run it alone with:

```bash
ros2 run remibot_console visualization_renderer
```

Disable it when testing another image source:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py start_renderer:=false
```

For a one-command launch after building:

```bash
~/kitchen_arm_ws/start_remibot_system.sh
```

More details are in `docs/ros2_bringup_integration.md`.

For the product-level state model, Sim/Real/Teaching separation, authority arbitration, and future UI consolidation plan, see `docs/operator_console_product_architecture.md`.

## Current Structure

- `kitchen_arm_gui.py`: repository-level Qt launcher.
- `qt_operator_console/`: Qt/PySide application.
- `qt_operator_console/kitchen_qt/models.py`: thread-safe robot state.
- `qt_operator_console/kitchen_qt/storage.py`: JSON persistence for waypoints, tools, PID history, and teaching trajectories.
- `qt_operator_console/kitchen_qt/backend/base.py`: backend contract.
- `qt_operator_console/kitchen_qt/backend/mock.py`: Windows-friendly simulated backend.
- `qt_operator_console/kitchen_qt/backend/ros2.py`: ROS2 adapter skeleton for Ubuntu.
- `qt_operator_console/kitchen_qt/ui/main_window.py`: main Qt window and functional tabs.
- `qt_operator_console/kitchen_qt/ui/widgets/plot.py`: lightweight telemetry plot widget.
- `data/`: local operator data.

## ROS2 Architecture Review

Your ROS2 diagram is directionally reasonable: perception, planning, control, hardware, GUI, and future learning are separate concerns, and the GUI should mostly monitor state plus send high-level requests. The important improvement is to make command ownership explicit:

- GUI should not publish raw motor commands during normal operation. It should request mode changes, send teleop targets, save waypoints, and ask the control layer to execute.
- `control_mode_manager` should remain the arbitration point for Position PID, impedance/teaching, gravity compensation, homing, and emergency stop.
- Homing should be a state machine with observable step status, not just a UI button.
- Planning should own waypoint/task execution and MoveIt interaction; GUI should send `waypoint_cmd` or action goals, not call MoveIt directly.
- Hardware drivers should publish normalized telemetry and faults. The GUI should consume those as read-only state.
- Contact detection is safety-relevant, so it should feed both planning/task manager and control arbitration.

Suggested ROS2 mapping:

| UI Feature | ROS2 Interface |
| --- | --- |
| Joint monitor | subscribe `/joint_states`, motor diagnostics |
| System status | subscribe `/arm/system_state` |
| Homing view | subscribe `/homing_status`, call `/homing/start` |
| Mode selector | call `/mode_request` |
| Manual teleop | publish `/teleop/cartesian_cmd` or `/teleop/joint_cmd` |
| Waypoint save | local JSON first, later optionally service `/waypoint/save` |
| Waypoint execute | action `/execute_waypoint` or `/execute_sequence` |
| PID tuning | service `/motor_controller/set_pid` |
| Step test | action `/motor_controller/step_test` |
| Tool identification | action `/tool_identification` |
| E-stop | dedicated latched safety topic/service, plus hardware-level stop outside GUI |

## RViz And MuJoCo Integration Strategy

Qt is the right direction if native visualization integration becomes important.

Preferred options:

1. Run RViz or MuJoCo as a separate process during development and use ROS2 as the shared contract.
2. For an embedded-looking viewport, render camera/simulation frames offscreen and display them in the `Visualization` tab.
3. For true RViz embedding, replace the placeholder with an RViz Qt widget on Ubuntu.
4. For MuJoCo, render offscreen to image frames or build a Qt OpenGL widget.
5. Avoid X11 window reparenting except for short experiments; it is brittle and Wayland-hostile.

## Validation

Static syntax check:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('ast ok')"
```
