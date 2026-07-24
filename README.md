# UR5 Pick-and-Place Simulation (ROS 2 / Jazzy)

ROS 2 迁移分支：`ros2-jazzy`  
工作区：`~/ros2/ur5_lego`  
原 ROS1 参考：`~/ros2/ref/UR5-Pick-and-Place-Simulation`（`main`）

> **不**运行 Noetic / Gazebo Classic。目标：**Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic**。

## 进度（2026-07-24）

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 官方 UR sim 冒烟 | **完成** |
| 1 | 乐高场景 + spawn + UR 同世界 | **完成** |
| 2 | 夹爪开合 + attach/detach MVP | **完成**（static-proxy 复测通过） |
| 3 | MoveIt 真值抓放 | 待做 |
| 4 | YOLO | 待做 |
| 5 | 全管道 / 城堡 | 待做 |

完整记录：**[docs/MIGRATION.md](docs/MIGRATION.md)**。

## 快速开始

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2/ur5_lego && colcon build --symlink-install
source install/setup.bash

# 主入口：UR5 + 夹爪 + 乐高世界 + attach
ros2 launch ur5_lego_bringup sim_lego.launch.py ur_type:=ur5

# 另开终端
ros2 run ur5_lego_bringup gripper_test
ros2 run ur5_lego_bringup attach_demo -- --spawn --hold 15
```

## 依赖

```bash
sudo apt install -y \
  ros-jazzy-ur ros-jazzy-ur-simulation-gz ros-jazzy-ur-moveit-config \
  ros-jazzy-robotiq-description ros-jazzy-robotiq-controllers \
  ros-jazzy-moveit ros-jazzy-ros-gz ros-jazzy-cv-bridge \
  ros-jazzy-controller-manager ros-jazzy-joint-trajectory-controller \
  python3-colcon-common-extensions
```

## 注意

- 不要在 `~/ros2` 根目录 `colcon build`。
- 夹爪为 **简化平行指**（dartsim 不支持 mimic 完整 2F-85）。
- 抓取为 **attach 粘合**（与原 ROS1 link_attacher 同思路），非真实摩擦夹取。
- 内存紧：可 `gazebo_gui:=false`、保持 `launch_rviz:=false`。

## License

MIT（见 [LICENSE](LICENSE)）。
