# PAROL6-ROS2-MOVEIT

This repository provides ROS 2 MoveIt 2 integration for the [PAROL6](https://github.com/PCrnjak/PAROL6-Desktop-robot-arm) 6-DOF open-source robotic arm. It includes a simulation demo, URDF models, and launch files for testing and planning.

![PAROL6 Demo](MEDIA/PAROL6_moveit_gif.gif)

---

## 🛠️ Installation & Setup

**Tested on:**
- Ubuntu 22.04
- ROS 2 Humble

### 1. Install ROS 2 Humble and MoveIt 2

You can follow [this guide](https://aleksandarhaber.com/how-to-properly-install-moveit2-in-ros2-humble-and-fix-tutorial-errors/) or install via APT:

```bash
sudo apt update
sudo apt install ros-humble-desktop ros-humble-moveit
```

### 1. Create and build a workspace

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/your_username/PAROL6-ROS2-MOVEIT.git 
## OR Copy this repo manually to ros2_ws/src
cd ~/ros2_ws
colcon build
```

### 1.  Source the environment

```bash
colcon build
source /opt/ros/humble/setup.bash
source install/setup.bash
```

### 🚀 Run the Simulation
```bash
LC_NUMERIC=en_US.UTF-8 ros2 launch parol6_moveit demo.launch.py
```

### 🤖 Run Against Real Hardware

`real_robot.launch.py` brings up the same MoveIt 2 stack as the demo above, but
backed by [`ros2_control`](https://control.ros.org/) talking to an actual (or
software-simulated) PAROL6 instead of `mock_components/GenericSystem`.

The `ros2_control` hardware interface itself (`parol6_hardware_interface`) and
the TCP/UDP bridge daemon it talks to (`parol6_bridge`) live in a separate
repo, [`parol6_ros2_control`](https://github.com/grahas/parol6_ros2_control) —
standard ROS 2 practice is to keep a robot's `ros2_control` hardware interface
out of its MoveIt config package, so it can be reused by other launch files
(e.g. a no-MoveIt bringup) without pulling MoveIt in. Clone it alongside this
repo:

```bash
cd ~/ros2_ws/src
git clone https://github.com/grahas/parol6_ros2_control.git
cd ~/ros2_ws
colcon build
```

You'll also need [`parol6-server`](https://github.com/PCrnjak/PAROL6-python-API)
running and reachable (real serial port, or its `PAROL6_FAKE_SERIAL=1`
simulator mode) — `real_robot.launch.py` connects to it via `parol6_bridge`
but does not start it itself:

```bash
ros2 launch parol6_moveit real_robot.launch.py \
    bridge_python:=/path/to/venv/bin/python3   # must have the `parol6` pip package installed
```

See `parol6_ros2_control`'s README for the full `ros2_control`-side setup and
known environment gotchas.

### 📚 Helpful Resources
- [Link1](https://www.youtube.com/watch?v=M2yiVbJmzKY&list=PLeEzO_sX5H6TNMBiworxO8RpQlcYfl54y&index=10)
- [Link2](https://www.youtube.com/watch?v=nZqTdzGAfYs)


### 🛠️ Troubleshoot

Fix common MoveIt 2 issues : 

```bash
sudo apt install --reinstall ros-humble-geometric-shapes
```

MoveIt Setup Assistant (Optional):
```bash
ros2 run moveit_setup_assistant moveit_setup_assistant
ros2 launch moveit_robot_arm_sim demo.launch.py
```

⚠️ Note: All URDF/XACRO names must be lowercase to avoid issues!
⚠️ Note: - [Common_errors](https://robotics.stackexchange.com/questions/103300/error-loading-custom-robotic-manipulator-model-in-moveit2-on-ros2-humbleerror-l)


### ✅ TODO

- [x] Connect with real PAROL6 robot
- [ ] Move PAROL6  