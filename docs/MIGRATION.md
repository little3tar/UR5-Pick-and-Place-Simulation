# ROS 1 → ROS 2 Jazzy 迁移说明

## 决策

| 项 | 选择 |
|----|------|
| 系统 | Ubuntu 24.04 WSL2（现环境） |
| 中间件 | ROS 2 Jazzy |
| 仿真 | Gazebo Harmonic (`ros_gz`) |
| 机械臂 | 官方 `ur_description` / `ur_simulation_gz`（不 vendoring ROS1 UR 栈） |
| 夹爪 | `robotiq_description` / `robotiq_controllers` |
| 规划 | MoveIt 2（弃用原 `kinematics.py` 手写 IK） |
| 仓库 | fork `little3tar/UR5-Pick-and-Place-Simulation` 分支 `ros2-jazzy` |
| 路径 | `~/ros2/ur5_lego`；参考仓 `~/ros2/ref/...` |

## 包映射

| ROS1 | ROS2 |
|------|------|
| levelManager | ur5_lego_gazebo + ur5_lego_bringup |
| vision | ur5_lego_vision |
| motion_planning | ur5_lego_motion |
| gazebo_ros_link_attacher | ur5_lego_attach（重写） |
| robot/* vendor | 系统 apt 包 |

## 已迁入资产

- 乐高 models → `ur5_lego_gazebo/models/lego/`
- 场景 models → `ur5_lego_gazebo/models/scene/`
- YOLO weights → `ur5_lego_vision/weights/`
- 接口草案 → `ur5_lego_msgs`（LegoDetection*、Attach/Detach/SetStatic）

## 下一步

1. 安装 `ros-jazzy-ur-simulation-gz` 等依赖并冒烟。
2. Phase 1：组合 world + spawn 乐高 + bridge。
3. Phase 2–3：attach + MoveIt 真值抓放 MVP。
