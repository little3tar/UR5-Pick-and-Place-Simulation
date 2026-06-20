<p align="center">
  <h2 align="center">UR5 Pick and Place Simulation in ROS/Gazebo</h2>
  <h3 align="center">ROS/Gazebo 中 UR5 拾取与放置仿真</h3>
</p>
<br>

<img src="https://github.com/pietrolechthaler/UR5-Pick-and-Place-Simulation/blob/main/main.png">

## Table of contents / 目录

- [Description / 项目描述](#description--项目描述)
- [Requirements / 环境要求](#requirements--环境要求)
- [Folder / 目录结构](#folder--目录结构)
- [Setup / 安装步骤](#setup--安装步骤)
- [Usage / 使用方法](#usage--使用方法)
- [Known Pitfalls / 已知踩坑指南](#known-pitfalls--已知踩坑指南)
- [Contributors / 贡献者](#contributors--贡献者)

---

### Description / 项目描述

This repository demonstrates UR5 pick-and-place in ROS and Gazebo. The UR5 uses an Xbox Kinect camera to detect eleven types of Lego Bricks and publishes their position and orientation.

本仓库演示了在 ROS 和 Gazebo 中 UR5 的拾取与放置。UR5 使用 Xbox Kinect 相机检测 11 种乐高积木，并发布它们的位置和姿态。

The goals of this project are / 项目目标：
- Simulate the interaction of a UR5 robot with Lego bricks
- 模拟 UR5 机器人与乐高积木的交互
- The robotic arm must be able to move a block from position A to B and construct a castle by assembling different bricks
- 机械臂能够将积木从 A 点移动到 B 点，并通过拼装不同积木来搭建城堡

<img src="https://github.com/pietrolechthaler/UR5-Pick-and-Place-Simulation/blob/main/intro.gif">

---

### Folder / 目录结构

```
UR5-Pick-and-Place-Simulation/catkin_ws/
├── levelManager          # 关卡管理：启动世界、生成积木
├── vision                # 视觉识别：YOLOv5 检测积木类型和朝向
├── motion_planning       # 运动规划：机器人移动、拾取和放置逻辑
├── build_planning        # 城堡搭建：按蓝图组装积木
├── gazebo_ros_link_attacher  # Gazebo 链接吸附插件
└── robot                 # 机器人模型：UR5 + Robotiq 夹爪 + 控制器配置
```

- **levelManager**: Launches the world and spawns bricks / 启动仿真世界并生成乐高积木
- **vision**: YOLOv5-based object type and orientation recognition / 基于 YOLOv5 的物体类型和朝向识别
- **motion_planning**: Robot movement, pick-and-place logic / 机器人运动、拾取与放置逻辑
- **build_planning**: Castle building from a blueprint (requires building.json) / 按蓝图搭建城堡（需要 building.json）
- **gazebo_ros_link_attacher**: Gazebo plugin for attaching/detaching links / Gazebo 链接吸附插件
- **robot**: Robot model definition with appropriate PID settings / 机器人模型定义及 PID 参数

---

### Requirements / 环境要求

**System / 系统**:
- Ubuntu 20.04 (Focal Fossa), with WSL2 on Windows 11 also supported / 也支持 Win11 WSL2
- Python 3.8 (comes with Ubuntu 20.04 / 系统自带)

**ROS & Simulation / ROS 与仿真**:
- [ROS Noetic](http://wiki.ros.org/noetic/Installation) (full desktop recommended / 推荐 desktop-full)
- [Gazebo 11](https://classic.gazebosim.org/tutorials?tut=ros_installing&cat=connect_ros) (included with ROS desktop-full / 随 ROS 安装)

**Build Tools / 编译工具**:
- [catkin-tools](https://catkin-tools.readthedocs.io/en/latest/) (`sudo apt install python3-catkin-tools`)
- `python3-rosdep`, `python3-wstool`, `python3-vcstool`

**ROS Packages (apt)**:
```
ros-noetic-moveit ros-noetic-moveit-kinematics ros-noetic-moveit-ros-planning
ros-noetic-cv-bridge ros-noetic-image-transport
ros-noetic-gazebo-ros-control ros-noetic-ros-control ros-noetic-ros-controllers
ros-noetic-joint-state-controller ros-noetic-effort-controllers
ros-noetic-position-controllers ros-noetic-joint-trajectory-controller
ros-noetic-controller-manager ros-noetic-tf-conversions
```

**YOLOv5**:
- Clone to `~/yolov5`: `git clone https://github.com/ultralytics/yolov5 ~/yolov5`
- YOLO weights (`best.pt`, `depth.pt`, `orientation.pt`) should be placed in `catkin_ws/src/vision/weigths/` (included in the repo / 已包含在仓库中)

**Python Packages (pip)**:
> ⚠️ CRITICAL: Do NOT use venv or conda! Install with `pip3 install --user` to the system Python. ROS packages (rospy, cv_bridge) are installed via apt and only available in system Python 3.8. Mixing with venv/conda will cause `ImportError`.

> ⚠️ 重要: 不要使用 venv 或 conda！使用 `pip3 install --user` 安装到系统 Python。ROS 包（rospy、cv_bridge）通过 apt 安装，仅在系统 Python 3.8 中可用。与 venv/conda 混用会导致 `ImportError`。

```
pip3 install --user osrf-pycommon pyquaternion
pip3 install --user numpy==1.23.5
pip3 install --user matplotlib==3.5.3
pip3 install --user importlib-metadata>=8.0
pip3 install --user torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip3 install --user ultralytics tqdm PyYAML seaborn pandas gitpython
```

**Optional / 可选**:
- [GitHub CLI](https://cli.github.com/) (`gh`) for fork management / 用于 fork 管理

---

### Setup / 安装步骤

```bash
# 1. Clone the repository / 克隆仓库
git clone https://github.com/pietrolechthaler/UR5-Pick-and-Place-Simulation/
# or your fork: git clone https://github.com/YOUR_USERNAME/UR5-Pick-and-Place-Simulation/

# 2. Build the workspace / 编译工作空间
cd UR5-Pick-and-Place-Simulation/catkin_ws
source /opt/ros/noetic/setup.bash
catkin build
source devel/setup.bash
echo "source $PWD/devel/setup.bash" >> ~/.bashrc

# 3. Clone and install YOLOv5 / 克隆并安装 YOLOv5
cd ~
git clone https://github.com/ultralytics/yolov5
# Note: DO NOT simply run `pip3 install -r requirements.txt` from the yolo repo!
# Instead, install the Python packages listed above with locked versions.
# 注意：不要直接运行 yolo 仓库的 `pip3 install -r requirements.txt`！
# 请使用上面列出的锁定版本安装 Python 包。

# 4. Install Python dependencies / 安装 Python 依赖 (see Requirements section above)
pip3 install --user pyquaternion numpy==1.23.5 matplotlib==3.5.3
pip3 install --user torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip3 install --user ultralytics tqdm PyYAML seaborn pandas gitpython

# 5. Initialize rosdep / 初始化 rosdep
sudo rosdep init
rosdep update
```

---

### Usage / 使用方法

```bash
# Source the workspace / 加载工作空间
source /opt/ros/noetic/setup.bash
source ~/UR5-Pick-and-Place-Simulation/catkin_ws/devel/setup.bash

# 1. Launch the simulation / 启动仿真
roslaunch levelManager lego_world.launch paused:=true gui:=true

# 2. Unpause physics and spawn bricks / 取消暂停并生成积木
rosservice call /gazebo/unpause_physics "{}"
rosrun levelManager levelManager.py -l [1-4]  # 1=1 brick, 2=all 11 types

# 3. Start vision recognition / 启动视觉识别
rosrun vision lego-vision.py -show
# `-show`: display recognition results in a window / 在窗口中显示识别结果
# Note: In the current version, vision processes one frame then exits.
# 注意：当前版本中 vision 处理一帧后就会退出。

# 4. Start motion planning / 启动运动规划
rosrun motion_planning motion_planning.py
```

---

### Known Pitfalls / 已知踩坑指南

> Detailed debugging log: see [DEBUG_LOG.md](./DEBUG_LOG.md) / 详细调试日志见 [DEBUG_LOG.md](./DEBUG_LOG.md)

#### 1. vision.py shuts down after one frame / vision.py 处理一帧后退出

**Problem**: `lego-vision.py` line 429 calls `rospy.signal_shutdown(0)`, which terminates the ROS node after processing a single frame. `motion_planning.py` then fails with `ROSInterruptException` when waiting for `/lego_detections`.

**问题**: `lego-vision.py` 第 429 行调用 `rospy.signal_shutdown(0)`，处理一帧后就关闭 ROS 节点。`motion_planning.py` 在等待 `/lego_detections` 时收到 `ROSInterruptException` 而崩溃。

**Workaround**: Run motion_planning first, then vision. / **临时方案**：先启动 motion_planning，再启动 vision。
**Fix**: Change `rospy.signal_shutdown(0)` to let vision keep running. / **修复**: 删除或注释掉 shutdown 调用。

#### 2. IK solver divergence / 逆运动学求解发散

**Problem**: `kinematics.py` uses a custom analytical IK solver for UR5. In random brick poses near singularities, `wait_for_position` loops forever (CPU 200%+).

**问题**: `kinematics.py` 使用手写的 UR5 DH 参数解析解。在接近奇异点的随机积木位姿下，`wait_for_position` 进入死循环（CPU 200%+）。

**Fix**: Replace custom IK with MoveIt's `ur_kinematics` (already installed via apt). / **修复**: 将自定义 IK 替换为 MoveIt 的 `ur_kinematics`（已通过 apt 安装）。

#### 3. Missing `building.json` / 缺少 building.json

**Problem**: `build_planning.py` line 78 references a `building.json` file that doesn't exist in the repository. Running `build_planning.py` crashes immediately.

**问题**: `build_planning.py` 第 78 行引用一个仓库中不存在的 `building.json` 配置文件。运行 `build_planning.py` 会直接崩溃。

**Fix**: Create a `building.json` or add a file-existence check with a clear error message. / **修复**: 创建 `building.json` 或添加文件存在性检查。

#### 4. `#!/usr/bin/env python` on Ubuntu 20.04

**Problem**: Ubuntu 20.04 has only `python3`, no `python` command. Scripts in `gazebo_ros_link_attacher/scripts/` use `#!/usr/bin/env python` and fail with "No such file or directory".

**问题**: Ubuntu 20.04 只有 `python3` 命令，没有 `python`。`gazebo_ros_link_attacher/scripts/` 下的脚本使用 `#!/usr/bin/env python`，报错 "No such file or directory"。

**Fix**: Either create a symlink (`sudo ln -sf /usr/bin/python3 /usr/bin/python`) or change all shebangs to `#!/usr/bin/env python3`. / **修复**: 创建 python symlink 或将所有 shebang 改为 `#!/usr/bin/env python3`。

#### 5. Python dependency conflicts / Python 依赖版本冲突

**Problem**: Mixing ROS system packages (apt) with pip packages causes version conflicts: numpy vs pandas, matplotlib vs mpl_toolkits, setuptools vs importlib-metadata.

**问题**: ROS 系统包 (apt) 与 pip 包混合导致版本冲突：numpy 与 pandas、matplotlib 与 mpl_toolkits、setuptools 与 importlib-metadata。

**Fix**: Lock versions as listed in Requirements above. / **修复**: 使用上面 Requirements 中列出的锁定版本。

#### 6. `catkin-tools` missing `osrf-pycommon` / catkin-tools 缺少 osrf-pycommon

**Problem**: `catkin build` fails with `DistributionNotFound: osrf-pycommon`.

**问题**: `catkin build` 报错 `DistributionNotFound: osrf-pycommon`。

**Fix**: `pip3 install --user osrf-pycommon` / **修复**: `pip3 install --user osrf-pycommon`

#### 7. Interactive `tzdata` hangs during ROS install / 安装 ROS 时 tzdata 交互式卡住

**Problem**: `apt install ros-noetic-desktop-full` hangs at `tzdata` timezone selection.

**问题**: `apt install ros-noetic-desktop-full` 在 `tzdata` 时区选择时卡住。

**Fix**: Preset timezone before install. / **修复**: 安装前预设时区：
```bash
echo "tzdata tzdata/Areas select Asia" | sudo debconf-set-selections
echo "tzdata tzdata/Zones/Asia select Shanghai" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt install -y ros-noetic-desktop-full
```

#### 8. `gzserver` GPU memory / gzserver 显存占用

**Problem**: `gzserver` takes ~1GB VRAM. Running YOLOv5 inference on the same GPU (e.g., MX450 2GB) may be tight.

**问题**: `gzserver` 占用约 1GB 显存。在同一 GPU 上运行 YOLOv5 推理（如 MX450 2GB）可能会显存不足。

**Fix**: Launch Gazebo with `gui:=false` to reduce VRAM or use CPU-only torch. / **修复**: 使用 `gui:=false` 启动 Gazebo 以减小显存占用，或使用 CPU 版 torch。

---

### Contributors / 贡献者

| Name                 | GitHub                               |
|----------------------|--------------------------------------|
| Davide Cerpelloni    | https://github.com/davidecerpelloni  |
| Leonardo Collizzolli | https://github.com/leocolliz         |
| Pietro Lechthaler    | https://github.com/pietrolechthaler  |
| Stefano Rizzi        | https://github.com/StefanoRizzi      |

---

### Fork / 派生

This fork maintained by [little3tar](https://github.com/little3tar/UR5-Pick-and-Place-Simulation) with:
- Bilingual README (EN/中文)
- Known pitfalls guide based on WSL2 + Ubuntu 20.04 debugging
- Version-locked Python dependency list

> Also see [DEBUG_LOG.md](./DEBUG_LOG.md) for the full WSL2 debugging log.
