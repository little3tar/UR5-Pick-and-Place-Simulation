# ROS 1 → ROS 2 Jazzy 迁移计划与进度

> 最后更新：2026-07-24  
> 分支：`ros2-jazzy`  
> 工作区：`~/ros2/ur5_lego`  
> 参考（只读）：`~/ros2/ref/UR5-Pick-and-Place-Simulation`（`main` / ROS1）

---

## 1. 背景与目标

| 项 | 内容 |
|----|------|
| 原项目 | UR5 + Robotiq + Kinect + YOLOv5 乐高抓取（ROS **Noetic** + Gazebo **Classic 11** + catkin） |
| 本机环境 | **WSL2 Ubuntu 24.04** + **ROS 2 Jazzy** + Gazebo **Harmonic**（`ros_gz`） |
| 为何迁移 | Noetic 不支持 24.04；本机已装 Jazzy，不能直接 `gh clone` 后运行 ROS1 栈 |
| 目标 | 在 Jazzy + gz-sim 上重建：仿真世界 → 乐高 spawn → 附着抓取 → MoveIt 抓放 → YOLO → 全管道 |

**策略**：不原样移植 catkin；**官方栈替换厂商包**，只迁移业务逻辑与资产（mesh / weights / 关卡参数）。

---

## 2. 关键决策

| 项 | 选择 |
|----|------|
| 系统 | Ubuntu 24.04 WSL2（现环境） |
| 中间件 | ROS 2 Jazzy |
| 仿真 | Gazebo Harmonic（`ros_gz_sim` / `ros_gz_bridge`） |
| 机械臂 | apt：`ur_description`、`ur_simulation_gz`（**不** vendoring ROS1 `universal_robot`） |
| 夹爪 | apt：`robotiq_description`、`robotiq_controllers` |
| 规划 | MoveIt 2；**弃用**原 `kinematics.py` 手写 IK |
| Git | 同 fork `little3tar/UR5-Pick-and-Place-Simulation`，分支 **`ros2-jazzy`**（`main` 保留 ROS1） |
| 目录 | `~/ros2/` = 所有 ROS2 项目父目录；本项目 = `~/ros2/ur5_lego`（独立 colcon 工作区） |

### 明确不做

- 在 24.04 上硬装 Noetic  
- 把 `catkin_ws` 当 ament 包编译  
- 在 `~/ros2` **根**执行 `colcon build` 混编多项目  

---

## 3. 包映射

| ROS1 | ROS2 包 | 说明 |
|------|---------|------|
| levelManager | `ur5_lego_gazebo` + `ur5_lego_bringup` | world、spawn、launch |
| vision | `ur5_lego_vision` | YOLO 节点（待实现） |
| motion_planning | `ur5_lego_motion` | pick-place（待实现） |
| build_planning | （后期并入 motion 或独立包） | 城堡蓝图 |
| gazebo_ros_link_attacher | `ur5_lego_attach` | gz-sim 下重写 |
| robot/* / universal_robot / robotiq vendor | 系统 apt | 删除 vendored 拷贝 |
| （新） | `ur5_lego_msgs` | LegoDetection*、Attach/Detach/SetStatic |
| （新） | `ur5_lego_description` | 场景/组合 URDF 占位 |

---

## 4. 阶段计划与进度

| Phase | 内容 | 状态 | 验收标准 |
|-------|------|------|----------|
| **0** | 目录布局、分支、ament 骨架、apt 依赖、官方 UR sim 冒烟 | **完成** | `ur_sim_control` 起控制器 |
| **1** | 乐高场景 SDF、level_manager spawn、resource path | **进行中** | world + 积木可 spawn |
| **2** | attach/detach/setStatic（gz-sim） | 待做 | 积木随夹爪 / 可释放 |
| **3** | MoveIt2 pick-place（仿真真值位姿 MVP） | 待做 | level1 A→home |
| **4** | YOLO 视觉常驻节点 | 待做 | `/lego_detections` 稳定 |
| **5** | 全管道 + 城堡 / 文档收尾 | 待做 | level2–4 演示 |

### MVP 推荐顺序

```text
① 官方 ur_simulation_gz          ← Phase 0 已过
② 自己的 world + 桌子 + spawn 乐高  ← Phase 1
③ MoveIt 点到点 + 夹爪
④ attach 最小实现
⑤ 真值位姿 pick-place（无视觉）
⑥ YOLO 接入
⑦ 多积木 / 城堡
```

---

## 5. Phase 0 完成记录（2026-07-24）

### 5.1 布局

```text
~/ros2/
├── README.md
├── ref/UR5-Pick-and-Place-Simulation/   # ROS1 参考 main
└── ur5_lego/                            # colcon 工作区，分支 ros2-jazzy
    ├── src/ur5_lego_{msgs,description,gazebo,bringup,vision,motion,attach}/
    ├── docs/MIGRATION.md
    ├── build/ install/ log/
    └── README.md
```

### 5.2 已安装 apt（节选）

- `ros-jazzy-ur` / `ur-simulation-gz` / `ur-moveit-config`
- `ros-jazzy-robotiq-description` / `robotiq-controllers`
- `ros-jazzy-moveit`、`ros-gz`、`cv-bridge`
- `controller-manager`、`joint-trajectory-controller` 等

### 5.3 冒烟命令与结果

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py \
  ur_type:=ur5 gazebo_gui:=false launch_rviz:=false
```

**结果：通过**

- Gazebo Harmonic 启动，`world/empty` 初始化  
- 硬件接口 `ur` activate  
- `scaled_joint_trajectory_controller`、`joint_state_broadcaster` 配置并激活  
- spawner 正常退出  

有界面时可加 `gazebo_gui:=true` / 默认 RViz。

### 5.4 Git

| 提交 | 说明 |
|------|------|
| `0dbcee9` | bootstrap：去掉 catkin、7 个 ament 包、资产、msgs、smoke launch |
| `c64b855` | Phase1 骨架：world SDF、level_manager、lego_world launch |

远程：`origin/ros2-jazzy`  
`main` 未改，仍为 ROS1。

---

## 6. Phase 1 进度（进行中）

### 已有

| 文件 | 作用 |
|------|------|
| `ur5_lego_gazebo/worlds/main_scene.sdf` | Harmonic 世界（桌/基座/Kinect include，无 Classic 插件） |
| `ur5_lego_gazebo/scripts/level_manager.py` | rclpy 关卡 spawn（`ros_gz_sim create`） |
| `ur5_lego_gazebo/launch/lego_world.launch.py` | 设 `GZ_SIM_RESOURCE_PATH` + 启 gz |
| `ur5_lego_bringup/launch/lego_world.launch.py` | 转发 gazebo launch |
| `models/lego/*`、`models/scene/*` | 自 ROS1 迁入的 mesh/sdf |

### 待完成（Phase 1 收尾）

- [ ] 实测 `lego_world`：场景模型在 Harmonic 下能否解析（Classic SDF/material 可能要改）  
- [ ] 实测 `level_manager -l 1/2` spawn  
- [ ] 与官方 UR 同进程/同 world 组合（当前冒烟 world 为 `empty`，乐高 world 为 `ur5_world`）  
- [ ] 必要时改 mesh collision / material 以适配 gz-sim  
- [ ] bridge（相机/时钟）预留  

### 试用命令（Phase 1 自测）

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2/ur5_lego/install/setup.bash

# 仅乐高场景
ros2 launch ur5_lego_bringup lego_world.launch.py

# 另开终端：生成关卡（需 sim 已起）
ros2 run ur5_lego_gazebo level_manager.py -l 1
# 或 -l 2 全部 11 类
```

---

## 7. 已迁入资产

- 乐高 models → `src/ur5_lego_gazebo/models/lego/`  
- 场景 models → `src/ur5_lego_gazebo/models/scene/`  
- YOLO weights → `src/ur5_lego_vision/weights/`（`best.pt` / `depth.pt` / `orientation.pt`，体积较大）  
- 接口 → `ur5_lego_msgs`：`LegoDetection`、`LegoDetectionArray`、`Attach`、`Detach`、`SetStatic`  
- ROS1 msg 备份 → `docs/Lego_state.msg.ros1`  

---

## 8. 已知风险与资源

| 风险 | 缓解 |
|------|------|
| Classic SDF / `Gazebo/*` material 在 Harmonic 失效 | 改 material 为 PBR/简单 diffuse；逐模型验证 |
| `gazebo_ros_link_attacher` 无法复用 | Phase 2 自研 gz system 或简化“粘 TF” MVP |
| 自定义 IK 发散 | 不迁，用 MoveIt2 |
| vision 单帧 shutdown | ROS2 节点常驻设计 |
| 内存 ~7.6G / 显存 ~2G | `gazebo_gui:=false`；YOLO 默认 CPU |
| YOLO 权重 >50MB GitHub 警告 | 后续可考虑 Git LFS 或外链 |

---

## 9. 日常命令速查

```bash
# 环境
source /opt/ros/jazzy/setup.bash
source ~/ros2/ur5_lego/install/setup.bash

# 编译
cd ~/ros2/ur5_lego && colcon build --symlink-install

# Phase 0 官方冒烟
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur5

# 本仓库 smoke 入口（包装官方 launch）
ros2 launch ur5_lego_bringup sim_smoke.launch.py ur_type:=ur5
```

---

## 10. 下一步（按优先级）

1. **Phase 1 收尾**：跑通 `lego_world` + `level_manager`，修 SDF/路径问题  
2. **组合 UR5 + 乐高场景**（同一 gz world）  
3. **Phase 2**：attach 最小可用实现  
4. **Phase 3**：MoveIt 真值抓放 MVP（无视觉）  
5. Phase 4–5：YOLO 与全管道  

---

## 11. 变更日志（迁移相关）

| 日期 | 内容 |
|------|------|
| 2026-07-24 | 定方案 C（ROS2 长期迁移）；`~/ros2` 多项目布局；clone ref + `ur5_lego` |
| 2026-07-24 | 分支 `ros2-jazzy`；7 包骨架；资产迁入；msgs；colcon 通过 |
| 2026-07-24 | apt 安装 UR/MoveIt/robotiq/ros-gz；`ur_sim_control` 冒烟通过 |
| 2026-07-24 | Phase1：`main_scene.sdf`、`level_manager.py`、launch；文档本页 |
