# UR5 Pick-and-Place Simulation (ROS 2 / Jazzy)

ROS 2 迁移分支：`ros2-jazzy`  
工作区路径：`~/ros2/ur5_lego`  
原 ROS1 参考：`~/ros2/ref/UR5-Pick-and-Place-Simulation`（`main`）

> 本分支**不**运行 ROS Noetic / Gazebo Classic。目标栈为 **Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic**。

## 布局

```text
~/ros2/                          # 所有 ROS2 项目总目录
├── README.md
├── ref/UR5-Pick-and-Place-Simulation/   # ROS1 只读参考
└── ur5_lego/                    # 本仓库工作副本 (ros2-jazzy)
    ├── src/
    │   ├── ur5_lego_msgs/
    │   ├── ur5_lego_description/
    │   ├── ur5_lego_gazebo/     # 含乐高 mesh / sdf 资产
    │   ├── ur5_lego_bringup/
    │   ├── ur5_lego_vision/     # 含 YOLO weights
    │   ├── ur5_lego_motion/
    │   └── ur5_lego_attach/
    └── docs/MIGRATION.md
```

## 依赖（系统）

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-ur ros-jazzy-ur-simulation-gz ros-jazzy-ur-moveit-config \
  ros-jazzy-robotiq-description ros-jazzy-robotiq-controllers \
  ros-jazzy-moveit ros-jazzy-ros-gz ros-jazzy-cv-bridge \
  ros-jazzy-controller-manager ros-jazzy-joint-trajectory-controller \
  python3-colcon-common-extensions python3-rosdep
```

## 编译

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2/ur5_lego
colcon build --symlink-install
source install/setup.bash
```

## 冒烟测试（Phase 0）

官方 UR + Gazebo 仿真（需已安装 `ur_simulation_gz`）：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2/ur5_lego/install/setup.bash
ros2 launch ur5_lego_bringup sim_smoke.launch.py ur_type:=ur5
```

或直接：

```bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur5
```

（具体 launch 文件名以包内 `share/ur_simulation_gz/launch/` 为准。）

## 迁移阶段

详见 [docs/MIGRATION.md](docs/MIGRATION.md)。

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 目录/分支/骨架/官方 sim 冒烟 | 完成 |
| 1 | 场景 + 乐高 spawn | 进行中 |
| 2 | attach 服务 | 待做 |
| 3 | MoveIt pick-place（真值位姿） | 待做 |
| 4 | YOLO 视觉 | 待做 |
| 5 | 全管道 / 城堡 | 待做 |

## 资源注意

- 机器内存 ~8G、GPU 约 2GB：建议 YOLO 默认 CPU；Gazebo 可 `gui:=false`。
- 不要在 `~/ros2` 根目录执行 `colcon build`。

## License

MIT（见 [LICENSE](LICENSE)）。上游 ROS1 项目见原作者与 fork 历史。
