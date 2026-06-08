# Remibot Console

Remibot Console is a Qt/PySide operator console for a 5-DOF kitchen robot arm. It is intended for simulation, RViz/MoveIt debugging, waypoint management, teaching capture, controller tuning, and later hardware bringup.

The console is an upper-computer interface, not the final safety authority. Safety-critical arbitration, motor enable/disable, emergency stop behavior, and hardware command ownership must live in the robot control layer and hardware stop path.

## Current Capabilities

- Unified Workbench for day-to-day operation:
  - joint command sliders with URDF-derived joint limits
  - live joint state table from `/joint_states`
  - waypoint save, preview, plan/execute, and delete
  - teaching drag state and recording controls
  - homing status summary and homing trigger
  - tool selection and tool identification trigger
  - active control-source indicators for GUI and joystick
- ROS2 backend:
  - subscribes `/joint_states`
  - subscribes `/joy` for joystick connection/activity status
  - sends joint targets through `/arm_controller/follow_joint_trajectory` when available
  - does not publish preview `/joint_states` directly, to avoid state-source contention
- Visualization:
  - Qt viewport subscribes image streams such as `/remibot/visualization/image`
  - `rviz_capture_renderer` captures the RViz window and republishes it into the Qt viewport
  - `visualization_renderer` provides a separate 2D fallback stream on `/remibot/visualization/fallback_image`
- Local persistence:
  - waypoints
  - tool identification results
  - PID history
  - teaching recordings
- Mock backend for UI development without ROS2.

## Repository Layout

```text
kitchen_arm_gui.py                 # repository-level launcher
qt_operator_console/               # Qt/PySide application
ros2_ws_packages/remibot_console   # ROS2 Python package template
ros2_ws_packages/remibot_bringup   # ROS2 launch package template
ros2_ws_packages/start_remibot_system.sh
data/                              # local operator data
docs/                              # architecture and bringup notes
```

The ROS2 package templates are intended to be copied into a ROS2 workspace, for example:

```text
~/kitchen_arm_ws/src/remibot_console
~/kitchen_arm_ws/src/remibot_bringup
```

## Running Without ROS2

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the mock console:

```bash
python kitchen_arm_gui.py --backend mock
```

Mock mode provides synthetic telemetry and a synthetic visualization frame. It is useful for UI work on Windows or on Ubuntu without a sourced ROS2 workspace.

## Running In A ROS2 Workspace

Build the packages:

```bash
cd ~/kitchen_arm_ws
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
colcon build --packages-select remibot_console remibot_bringup
source install/setup.bash
```

Run the full bringup:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py
```

Or use the wrapper script:

```bash
~/kitchen_arm_ws/start_remibot_system.sh
```

The wrapper keeps `joy_arm_control.py` disabled by default because continuous joystick command output can compete with GUI or MoveIt goals. Enable joystick command output only for joystick-control sessions:

```bash
START_JOY_CONTROL=true ~/kitchen_arm_ws/start_remibot_system.sh
```

Useful launch arguments:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py --show-args
```

Common examples:

```bash
# GUI/RViz simulation without hardware bridge
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_candle:=false \
  start_joint4_mapper:=false

# Disable RViz window capture
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_rviz_capture:=false

# Use the 2D fallback renderer instead of RViz capture
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_rviz_capture:=false \
  start_renderer:=true
```

## Visualization Modes

### RViz Window Capture

The default visualization path is:

```text
RViz window -> rviz_capture_renderer -> /remibot/visualization/image -> Qt viewport
```

Run it manually:

```bash
ros2 run remibot_console rviz_capture_renderer
```

This is a practical prototype, not native RViz embedding. It depends on RViz being open, captures the whole RViz window, and can have noticeable latency.

### 2D Fallback Renderer

The fallback renderer publishes a simple 2D joint-state preview:

```bash
ros2 run remibot_console visualization_renderer
```

It publishes:

```text
/remibot/visualization/fallback_image
```

It does not appear in the GUI viewport unless deliberately remapped:

```bash
ros2 run remibot_console visualization_renderer --ros-args \
  -p image_topic:=/remibot/visualization/image
```

## Command Ownership

The console avoids writing raw motor commands in normal UI paths. In ROS2 mode, joint preview and waypoint execution are sent through `/arm_controller/follow_joint_trajectory` when that action server is available.

The GUI does not publish fallback `/joint_states` and does not overwrite displayed joint state with requested targets. Displayed joint values should come from `/joint_states` only. This prevents visible toggling between a requested target and the controller's actual state.

Long-term command ownership should be enforced by a dedicated ROS2 arbitration or mode-management node.

## Validation

Static syntax check:

```bash
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('ast ok')"
```

ROS2 build check:

```bash
cd ~/kitchen_arm_ws
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
colcon build --packages-select remibot_console remibot_bringup
```

Confirm executables:

```bash
source ~/kitchen_arm_ws/install/setup.bash
ros2 pkg executables remibot_console
```

Expected executables:

```text
remibot_console kitchen_arm_gui
remibot_console rviz_capture_renderer
remibot_console visualization_renderer
```

## Current Limitations

- RViz is not embedded natively. The current renderer captures the RViz window as an image stream.
- RViz capture requires an open RViz window and may be slow or brittle on Wayland, multi-monitor setups, or unusual window titles.
- Preview and execute currently depend on an available `/arm_controller/follow_joint_trajectory` action server.
- Homing, mode switching, tool identification, PID writes, and step tests still need real ROS2 services/actions behind the UI.
- The GUI provides operator-level guardrails, but final safety authority is not implemented in this repository.

## Roadmap

### Milestone 1: Native Visualization

- Replace RViz window capture with a C++ Qt/RViz integration or offscreen RViz renderer.
- Publish only the render panel or embed a native visualization widget rather than the whole RViz application window.
- Reduce latency and remove dependence on external window capture.

### Milestone 2: Control Authority And Mode Manager

- Add a ROS2 arbitration node for GUI, joystick, planner, homing, teaching, and safety command ownership.
- Replace UI-only authority indicators with service/action-backed authority requests.
- Prevent command-source contention at the ROS2 control layer.

### Milestone 3: Gravity Compensation Workflow

- Add a guided gravity compensation transition:
  - stop active command source
  - move home or safe pose
  - disable motors if required
  - switch controller mode
  - re-enable motors
  - verify mode and telemetry
- Block GUI, joystick, and planner commands during the transition.

### Milestone 4: Teaching And Hardware Mirroring

- Make teaching drag a real mode request.
- Record real hardware joint states with timestamps, tool metadata, and source provenance.
- Mirror hardware state into RViz and the GUI without treating simulation as authoritative.

### Milestone 5: Waypoint And Sequence Execution

- Add sequence editing and segmented execution.
- Replace direct trajectory goals with `/execute_waypoint` and `/execute_sequence` actions.
- Separate simulation preview from hardware execution with explicit precondition checks.

### Milestone 6: Diagnostics And Tuning

- Connect PID tuning, step tests, tool identification, and motor diagnostics to real ROS2 services/actions.
- Add fault history, controller status, motor enable state, and recovery guidance.

## Additional Documentation

- `docs/ros2_bringup_integration.md`
- `docs/operator_console_product_architecture.md`
