#!/bin/bash
set -e

ROS_DISTRO="${ROS_DISTRO:-humble}"
KITCHEN_WS="${KITCHEN_WS:-$HOME/kitchen_arm_ws}"
MOTOR_WS="${MOTOR_WS:-$HOME/motor_test_ws}"

source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${KITCHEN_WS}/install/setup.bash"

if [ -f "${MOTOR_WS}/install/setup.bash" ]; then
  source "${MOTOR_WS}/install/setup.bash"
fi

ros2 launch remibot_bringup kitchen_arm_system.launch.py \
  kitchen_ws:="${KITCHEN_WS}" \
  motor_ws:="${MOTOR_WS}" \
  start_joy_control:="${START_JOY_CONTROL:-false}"
