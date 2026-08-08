"""Bring up MoveIt + ros2_control against a real (or simulated-via-parol6-server)
PAROL6 arm, instead of the mock_components/GenericSystem used by demo.launch.py.

Starts parol6_bridge (TCP<->UDP daemon, see the parol6_bridge package) and then
the usual MoveIt demo stack, with the ros2_control URDF built using
Parol6SystemInterface (parol6_hardware_interface package) instead of the mock
plugin -- see parol6.ros2_control.xacro's use_real_hardware arg.

Prerequisite: parol6-server must already be running and reachable at
robot_host:robot_port (default 127.0.0.1:5001) -- this launch file does not
start it.

Usage:
    ros2 launch parol6_moveit real_robot.launch.py
    ros2 launch parol6_moveit real_robot.launch.py robot_host:=192.168.1.50
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import (
    generate_move_group_launch,
    generate_moveit_rviz_launch,
    generate_rsp_launch,
    generate_spawn_controllers_launch,
)


def _launch_setup(context, *args, **kwargs):
    # MoveItConfigsBuilder.robot_description(mappings=...) only reliably
    # threads every mapping through to the xacro if *all* values are plain
    # strings -- that's the only case that takes its eager load_xacro()
    # path. A dict mixing plain strings (use_real_hardware) with
    # LaunchConfiguration substitutions (bridge_host/bridge_port) takes the
    # other branch (a deferred launch_ros Xacro substitution), which was
    # found to silently drop use_real_hardware: the resulting robot
    # description kept loading mock_components/GenericSystem even with
    # use_real_hardware="true" in the mappings dict. Resolving every value
    # to a concrete string here (via .perform(context), since this now runs
    # inside an OpaqueFunction) avoids that branch entirely. Same pattern
    # parol6_bringup's parol6_control.launch.py uses for the same reason.
    bridge_host = LaunchConfiguration("bridge_host").perform(context)
    bridge_port = LaunchConfiguration("bridge_port").perform(context)

    bridge_process = ExecuteProcess(
        cmd=[
            LaunchConfiguration("bridge_python").perform(context),
            "-m",
            "parol6_bridge.bridge_node",
            "--robot-host",
            LaunchConfiguration("robot_host").perform(context),
            "--robot-port",
            LaunchConfiguration("robot_port").perform(context),
            "--bind-host",
            bridge_host,
            "--bind-port",
            bridge_port,
        ],
        name="parol6_bridge",
        output="screen",
    )

    moveit_config = (
        MoveItConfigsBuilder("parol6", package_name="parol6_moveit")
        .robot_description(
            mappings={
                "use_real_hardware": "true",
                "bridge_host": bridge_host,
                "bridge_port": bridge_port,
            }
        )
        .planning_scene_monitor(
            publish_robot_description=True, publish_robot_description_semantic=True
        )
        .to_moveit_configs()
    )

    # Deliberately NOT using moveit_configs_utils.launches.generate_demo_launch()
    # here: it works by including a handful of standalone, MoveIt-Setup-
    # Assistant-generated launch files (rsp.launch.py, move_group.launch.py,
    # moveit_rviz.launch.py, ...) via IncludeLaunchDescription -- and each of
    # those independently reconstructs its own `moveit_config = MoveItConfigsBuilder(
    # "parol6", package_name="parol6_moveit").to_moveit_configs()` with no
    # mappings at all, ignoring the use_real_hardware="true"/bridge_host/
    # bridge_port mappings built above entirely. rsp.launch.py's
    # robot_state_publisher is what actually publishes the /robot_description
    # topic controller_manager subscribes to (see the remap below), so this
    # silently loaded the mock_components/GenericSystem plugin regardless of
    # what real_robot.launch.py configured -- found by tracing why
    # controller_manager kept logging "Loaded hardware 'FakeSystem' from
    # plugin 'mock_components/GenericSystem'" even with everything else
    # (bridge_host/bridge_port resolution, use_real_hardware="true" mapping)
    # correct. The individual generate_*_launch(moveit_config) functions
    # below use the moveit_config object passed to them directly instead of
    # rebuilding their own, so they all agree on the same robot description.
    rsp_launch = generate_rsp_launch(moveit_config)
    move_group_launch = generate_move_group_launch(moveit_config)
    rviz_launch = generate_moveit_rviz_launch(moveit_config)
    spawn_controllers_launch = generate_spawn_controllers_launch(moveit_config)

    # As of this ros2_control generation, controller_manager does not
    # forward its own --params-file to spawned controller sub-nodes (see
    # determine_controller_node_options() in controller_manager.cpp:
    # use_global_arguments(false)) -- each controller needing parameters
    # beyond its bare declaration (anything other than
    # joint_state_broadcaster, which tolerates an empty config) must be told
    # where to find them via a <controller_name>.params_file parameter
    # declared on controller_manager itself. Same fix as
    # parol6_bringup's parol6_control.launch.py and the
    # moveit_configs_utils.launches.generate_demo_launch() patch in this
    # workspace's moveit2_ws checkout.
    controllers_yaml_path = str(
        moveit_config.package_path / "config" / "ros2_controllers.yaml"
    )
    controller_names = moveit_config.trajectory_execution.get(
        "moveit_simple_controller_manager", {}
    ).get("controller_names", [])
    controller_params_files = {
        f"{name}.params_file": controllers_yaml_path for name in controller_names
    }
    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[controllers_yaml_path, controller_params_files],
        remappings=[
            ("/controller_manager/robot_description", "/robot_description"),
        ],
        output="screen",
    )

    entities = (
        list(rsp_launch.entities)
        + list(move_group_launch.entities)
        + [ros2_control_node]
        + list(spawn_controllers_launch.entities)
    )
    if context.launch_configurations.get("use_rviz", "true") == "true":
        entities += list(rviz_launch.entities)

    # Give parol6_bridge a couple seconds to bind and connect to
    # parol6-server before robot_state_publisher/controller_manager try to
    # reach it. Parol6SystemInterface also retries internally
    # (connect_timeout_sec in the xacro), so this is a courtesy, not a hard
    # requirement.
    delayed_demo = TimerAction(period=2.0, actions=entities)

    return [bridge_process, delayed_demo]


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            "robot_host", default_value="127.0.0.1", description="parol6-server host"
        ),
        DeclareLaunchArgument(
            "robot_port", default_value="5001", description="parol6-server UDP port"
        ),
        DeclareLaunchArgument(
            "bridge_host",
            default_value="127.0.0.1",
            description="address parol6_bridge listens on (loopback only, unauthenticated)",
        ),
        DeclareLaunchArgument(
            "bridge_port", default_value="6001", description="port parol6_bridge listens on"
        ),
        DeclareLaunchArgument(
            "bridge_python",
            default_value="python3",
            description=(
                "Python interpreter to run parol6_bridge with -- must have the 'parol6' pip "
                "package importable. Point this at a venv's python if parol6 isn't installed "
                "for the system interpreter, e.g. /home/you/parol6-server/.venv/bin/python3"
            ),
        ),
        DeclareLaunchArgument(
            "use_rviz", default_value="true", description="Launch RViz alongside move_group"
        ),
    ]

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=_launch_setup)])
