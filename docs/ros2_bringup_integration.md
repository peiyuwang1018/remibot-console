# ROS2 Bringup Integration

## Recommended Direction

The Qt operator console should become a normal Python ROS2 package inside:

```text
/home/peiyu/kitchen_arm_ws/src/remibot_console
```

RViz, MoveIt, robot drivers, joystick control, scene loading, and the GUI should be launched by one bringup layer. The GUI should not privately start RViz or MoveIt, because those processes depend on the same ROS2 graph, controller manager, robot description, and hardware workspace.

## Package Split

Keep these responsibilities separate:

- `kitchen_arm_moveit_config`: robot description, MoveIt config, RViz config, MoveIt launch files.
- `kitchen_arm_bringup` or `remibot_bringup`: one-shot system launch for MoveIt, RViz, CANdle, joystick, scene, and GUI.
- `remibot_console`: Qt GUI plus ROS2 backend adapter.
- Existing controller or driver packages: CANdle and motor interfaces.

The current loose scripts in `/home/peiyu/kitchen_arm_ws/scripts` should eventually move into a Python ROS2 package as console entry points:

- `joy_arm_control`
- `joint4_motor_mapper`
- `kitchen_scene`

## Launch Shape

The first useful bringup should mirror the existing `start_kitchen_arm.sh` order:

1. Launch `kitchen_arm_moveit_config demo.launch.py`.
2. Start `candle_ros2 candle_container`.
3. Start `joy joy_node`.
4. Start `joint4_motor_mapper`.
5. Start `joy_arm_control`.
6. Start `kitchen_scene`.
7. Start the Qt operator console.

For development, a tmux script is still practical because it keeps logs visible in separate panes. For long-term ROS2 packaging, use a Python launch file with `IncludeLaunchDescription`, `Node`, and `ExecuteProcess`.

## RViz Linkage

RViz follows ROS2 state. The console should not manipulate RViz internals.

Required graph:

```text
/joint_states
robot_description
/tf and /tf_static
/planning_scene or monitored_planning_scene
/target_marker
/stir_trail
```

The GUI should integrate through backend calls:

- subscribe `/joint_states` for telemetry
- call `/mode_request`
- call `/homing/start`
- publish or action-send joint targets through the control layer
- call `/motor_controller/set_pid`
- use actions for step tests, waypoint execution, and tool identification

## Immediate Next Step

Implemented v0.1:

- `remibot_console` was added as a ROS2 Python package.
- `remibot_bringup` was added as a ROS2 Python package.
- `/home/peiyu/kitchen_arm_ws/start_remibot_system.sh` was added as a one-command wrapper.

The source templates are kept in this repository under:

```text
ros2_ws_packages/remibot_console
ros2_ws_packages/remibot_bringup
ros2_ws_packages/start_remibot_system.sh
```

They have also been synchronized into:

```text
/home/peiyu/kitchen_arm_ws/src/remibot_console
/home/peiyu/kitchen_arm_ws/src/remibot_bringup
/home/peiyu/kitchen_arm_ws/start_remibot_system.sh
```

After building the workspace, the GUI can be launched as:

```bash
ros2 run remibot_console kitchen_arm_gui
```

The system bringup entry is:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py
```

or:

```bash
~/kitchen_arm_ws/start_remibot_system.sh
```

This replaces ad hoc GUI-launched RViz and gives one system-owned lifecycle.

## Development Test Commands

Build only the new packages:

```bash
cd ~/kitchen_arm_ws
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
colcon build --packages-select remibot_console remibot_bringup
source install/setup.bash
```

Confirm the GUI executable exists:

```bash
ros2 pkg executables remibot_console
```

The GUI entry point is launched by ROS2's `/usr/bin/python3`, so PySide6 must be available there:

```bash
/usr/bin/python3 -c "import PySide6; print(PySide6.__file__)"
```

If that import fails:

```bash
/usr/bin/python3 -m pip install "PySide6>=6.7"
```

Inspect bringup arguments:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py --show-args
```

Run GUI only:

```bash
ros2 run remibot_console kitchen_arm_gui --backend ros2
```

Test GUI-to-RViz preview:

1. Start MoveIt/RViz and the GUI without hardware:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_candle:=false \
  start_joint4_mapper:=false
```

2. Open the GUI `Teleop` tab.
3. Move the joint sliders.
4. Click `Preview Sliders in RViz`.
5. If `/arm_controller/follow_joint_trajectory` is available, the GUI sends a short preview trajectory to the simulated controller. The controller then owns `/joint_states`, so RViz should settle at the target pose without flickering.
6. If no trajectory controller is available, the GUI falls back to publishing preview `/joint_states` directly.

This preview path is for simulation and planning only. It is not the final hardware command path.

## Control Source And Waypoints

The Teleop tab shows two operator-state indicators:

- `Joystick`: whether `/joy` messages have been seen, and whether the controller is currently active.
- `Active`: whether the last active source is `GUI` or `Joystick`.

This is the first UI guard against accidental source conflicts. The next safety step is to route both GUI and joystick through a shared mode/arbitration node before enabling real hardware motion.

Waypoint workflow:

1. Use the GUI sliders to reach a pose in RViz.
2. Click `Preview Sliders in RViz`.
3. Save the current pose in the Waypoints tab.
4. Select a saved waypoint and click `Preview` to return the RViz/simulated arm to that pose.
5. Select a saved waypoint and click `Plan/Execute` to send a trajectory to the controller.

Today `Preview` and `Plan/Execute` both use `/arm_controller/follow_joint_trajectory` when available. They are separated in the UI so the backend can later make `Preview` simulation-only and `Plan/Execute` mode-gated for real hardware.

Run simulation/visualization without hardware bridge:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_candle:=false \
  start_joint4_mapper:=false
```

By default, `joy_arm_control.py` is not started from the ROS2 launch or wrapper because it continuously sends trajectory goals and can compete with GUI waypoint preview. Enable it only when testing joystick authority:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_joy_control:=true
```

Run full system:

```bash
~/kitchen_arm_ws/start_remibot_system.sh
```

To start the full-system wrapper with joystick command output enabled:

```bash
START_JOY_CONTROL=true ~/kitchen_arm_ws/start_remibot_system.sh
```

For GUI/RViz simulation preview, keep joystick control output off.

In the GUI, use `Use GUI` or `Use Joystick` to mark the intended control authority. When joystick authority is active, GUI slider and waypoint commands are blocked. This is a UI-level guard; the long-term control authority should be enforced by a ROS2 arbitration/lifecycle node.

## Visualization Frame Stream Experiment

The Workbench now contains a Qt image widget for rendered frames. This does not embed RViz itself. It subscribes image topics and displays the newest frame:

```text
/remibot/visualization/image
/rviz/rendered_image
/camera/image_raw
/remibot/visualization/image/compressed
/rviz/rendered_image/compressed
```

To test the GUI-only pipeline, launch the GUI in mock mode; it emits a synthetic arm preview frame.

Implemented RViz capture renderer:

```bash
ros2 run remibot_console rviz_capture_renderer
```

This node captures the RViz window with Qt screen capture and publishes:

```text
/remibot/visualization/image
```

The bringup launch starts RViz capture by default:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py
```

Disable it when testing another image source:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py start_rviz_capture:=false
```

Fallback 2D renderer:

```bash
ros2 run remibot_console visualization_renderer
```

This lightweight node subscribes `/joint_states`, draws a three-view 2D arm preview, and publishes to a separate fallback topic by default:

```text
/remibot/visualization/fallback_image
```

The fallback frame is intended for low-cost deployment and degraded visualization modes:

- J1 top view
- J2-J3-J4 side view
- J5 tool roll view

Verify the fallback image stream:

```bash
ros2 topic echo --once /remibot/visualization/fallback_image --field height
ros2 topic echo --once /remibot/visualization/fallback_image --field width
ros2 topic echo --once /remibot/visualization/fallback_image --field encoding
```

Expected values are `540`, `960`, and `rgb8`.

Start the fallback renderer from bringup:

```bash
ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  start_rviz_capture:=false \
  start_renderer:=true
```

To intentionally show the fallback renderer in the GUI viewport, remap its output to the main image topic:

```bash
ros2 run remibot_console visualization_renderer --ros-args \
  -p image_topic:=/remibot/visualization/image
```

This is still not true RViz embedding. It is a real RViz window frame stream into Qt. The preferred next step is a MuJoCo/offscreen viewport in Qt. A C++ Qt/RViz bridge is reserved as a contingency if MuJoCo cannot cover the required debugging workflow.

## Command Source Contention Notes

The ROS2 backend no longer publishes preview `/joint_states` directly and no longer mutates GUI joint state optimistically when a command is sent. Joint state shown in the GUI should come from `/joint_states` only. This prevents the GUI from toggling between "requested target" and "actual controller state".

The wrapper also keeps `joy_arm_control.py` disabled by default. Enable it only for joystick-command sessions:

```bash
START_JOY_CONTROL=true ~/kitchen_arm_ws/start_remibot_system.sh
```
