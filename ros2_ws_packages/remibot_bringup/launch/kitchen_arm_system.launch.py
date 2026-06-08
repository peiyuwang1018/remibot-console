from __future__ import annotations

import os
import shlex
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _source_prefix(workspace: Path) -> str:
    ros_distro = os.environ.get("ROS_DISTRO", "humble")
    return (
        f"source {shlex.quote(f'/opt/ros/{ros_distro}/setup.bash')} && "
        f"source {shlex.quote(str(workspace / 'install' / 'setup.bash'))}"
    )


def _system_actions(context, *_args, **_kwargs):
    kitchen_ws = Path(LaunchConfiguration("kitchen_ws").perform(context)).expanduser()
    motor_ws = Path(LaunchConfiguration("motor_ws").perform(context)).expanduser()
    python_executable = LaunchConfiguration("python_executable").perform(context)
    scripts_dir = kitchen_ws / "scripts"

    kitchen_prefix = _source_prefix(kitchen_ws)
    motor_prefix = f"{kitchen_prefix} && source {shlex.quote(str(motor_ws / 'install' / 'setup.bash'))}"

    moveit_launch = Path(get_package_share_directory("kitchen_arm_moveit_config")) / "launch" / "demo.launch.py"

    actions = [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(moveit_launch)),
            condition=IfCondition(LaunchConfiguration("start_moveit")),
        ),
        ExecuteProcess(
            cmd=["bash", "-lc", f"{motor_prefix} && ros2 run candle_ros2 candle_container"],
            output="screen",
            condition=IfCondition(LaunchConfiguration("start_candle")),
        ),
        TimerAction(
            period=9.0,
            actions=[
                Node(
                    package="joy",
                    executable="joy_node",
                    parameters=[{"device_id": 0}],
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_joy")),
                )
            ],
        ),
        TimerAction(
            period=12.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        "bash",
                        "-lc",
                        f"{motor_prefix} && {shlex.quote(python_executable)} {shlex.quote(str(scripts_dir / 'joint4_motor_mapper.py'))}",
                    ],
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_joint4_mapper")),
                )
            ],
        ),
        TimerAction(
            period=10.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        "bash",
                        "-lc",
                        f"{kitchen_prefix} && {shlex.quote(python_executable)} {shlex.quote(str(scripts_dir / 'joy_arm_control.py'))}",
                    ],
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_joy_control")),
                )
            ],
        ),
        TimerAction(
            period=8.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        "bash",
                        "-lc",
                        f"{kitchen_prefix} && {shlex.quote(python_executable)} {shlex.quote(str(scripts_dir / 'kitchen_scene.py'))}",
                    ],
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_scene")),
                )
            ],
        ),
        TimerAction(
            period=1.5,
            actions=[
                Node(
                    package="remibot_console",
                    executable="visualization_renderer",
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_renderer")),
                )
            ],
        ),
        TimerAction(
            period=6.0,
            actions=[
                Node(
                    package="remibot_console",
                    executable="rviz_capture_renderer",
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_rviz_capture")),
                )
            ],
        ),
        TimerAction(
            period=2.0,
            actions=[
                Node(
                    package="remibot_console",
                    executable="kitchen_arm_gui",
                    arguments=["--backend", "ros2"],
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("start_gui")),
                )
            ],
        ),
    ]
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("kitchen_ws", default_value=str(Path("~/kitchen_arm_ws").expanduser())),
            DeclareLaunchArgument("motor_ws", default_value=str(Path("~/motor_test_ws").expanduser())),
            DeclareLaunchArgument("python_executable", default_value="/usr/bin/python3"),
            DeclareLaunchArgument("start_moveit", default_value="true"),
            DeclareLaunchArgument("start_candle", default_value="true"),
            DeclareLaunchArgument("start_joy", default_value="true"),
            DeclareLaunchArgument("start_joint4_mapper", default_value="true"),
            DeclareLaunchArgument("start_joy_control", default_value="false"),
            DeclareLaunchArgument("start_scene", default_value="true"),
            DeclareLaunchArgument("start_renderer", default_value="true"),
            DeclareLaunchArgument("start_rviz_capture", default_value="false"),
            DeclareLaunchArgument("start_gui", default_value="true"),
            OpaqueFunction(function=_system_actions),
        ]
    )
