# GitHub And Jetson Deployment

## Repository Shape

For this project, prefer publishing the whole ROS2 workspace source layout, not just one GUI package. The useful unit is the integrated robot development environment:

```text
kitchen_arm_ws/
  src/
    kitchen_arm.SLDASM/
    kitchen_arm_moveit_config/
    remibot_console/
    remibot_bringup/
  scripts/
    joy_arm_control.py
    joint4_motor_mapper.py
    kitchen_scene.py
  start_kitchen_arm.sh
  start_remibot_system.sh
```

Do not commit generated workspace outputs:

```text
build/
install/
log/
.ros/
```

If a dependency is developed elsewhere, such as a motor driver package, either document it as an external dependency or add it as a Git submodule only after its ownership and deployment path are stable.

## Suggested Git Ignore

```gitignore
build/
install/
log/
.ros/
__pycache__/
*.pyc
*.bag
*.db3
*.mcap
oak_captures/
```

Keep robot meshes and URDF/Xacro files if they are required for RViz and MoveIt to work on a fresh machine.

## Fresh Ubuntu Setup

Install ROS2, MoveIt, RViz, joystick support, and Python tooling:

```bash
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-colcon-common-extensions \
  ros-${ROS_DISTRO}-desktop \
  ros-${ROS_DISTRO}-moveit \
  ros-${ROS_DISTRO}-rviz2 \
  ros-${ROS_DISTRO}-joy \
  ros-${ROS_DISTRO}-joint-state-publisher \
  ros-${ROS_DISTRO}-joint-state-publisher-gui \
  ros-${ROS_DISTRO}-robot-state-publisher \
  ros-${ROS_DISTRO}-ros2-control \
  ros-${ROS_DISTRO}-ros2-controllers
```

Install Qt for the Python interpreter used by ROS2 entry points:

```bash
/usr/bin/python3 -m pip install "PySide6>=6.7"
```

Build:

```bash
cd ~/kitchen_arm_ws
source /opt/ros/${ROS_DISTRO}/setup.bash
colcon build
source install/setup.bash
```

Start:

```bash
~/kitchen_arm_ws/start_remibot_system.sh
```

## Jetson Notes

Use the ROS2 distribution that matches the Jetson OS image. If the Jetson image is not on the same Ubuntu base as the development machine, use a container or align the OS/ROS combination before debugging robot behavior.

GPU acceleration is not required for the Qt console itself, but RViz and camera/depth workloads benefit from a correctly configured NVIDIA graphics stack. Bring up in phases on Jetson:

1. `ros2 run remibot_console kitchen_arm_gui --backend mock`
2. `ros2 launch remibot_bringup kitchen_arm_system.launch.py start_candle:=false start_joint4_mapper:=false`
3. Add camera/depth nodes.
4. Add CANdle and motor bridge.
5. Enable real execution only after preview and state feedback are correct.
