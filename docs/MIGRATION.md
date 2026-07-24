# ROS 1 → ROS 2 Jazzy 迁移计划与进度

> 最后更新：2026-07-24（会话末进度快照）  
> 分支：`ros2-jazzy`  
> 工作区：`~/ros2/ur5_lego`  
> 参考（只读）：`~/ros2/ref/UR5-Pick-and-Place-Simulation`（`main` / ROS1）

---

## 1. 背景与目标

| 项 | 内容 |
|----|------|
| 原项目 | UR5 + Robotiq + Kinect + YOLOv5 乐高抓取（ROS **Noetic** + Gazebo **Classic 11** + catkin） |
| 本机环境 | **WSL2 Ubuntu 24.04** + **ROS 2 Jazzy** + Gazebo **Harmonic**（`ros_gz`） |
| 为何迁移 | Noetic 不支持 24.04；本机已装 Jazzy |
| 目标 | 仿真世界 → 乐高 spawn → 附着抓取 → MoveIt 抓放 → YOLO → 全管道 |

**策略**：不原样移植 catkin；**官方栈替换厂商包**，只迁移业务逻辑与资产。

---

## 2. 关键决策

| 项 | 选择 |
|----|------|
| 中间件 | ROS 2 Jazzy |
| 仿真 | Gazebo Harmonic（`ros_gz_sim` / `ros_gz_bridge`） |
| 机械臂 | apt：`ur_description`、`ur_simulation_gz` |
| 夹爪 | 官方 mesh + **简化平行 prismatic**（非完整 2F-85 四杆/mimic） |
| 抓取 | 对齐原项目思路：**attach 粘合**，非指尖摩擦；当前为 **static 代理 + TF sticky** |
| 规划 | MoveIt 2（**未做**）；弃用手写 IK |
| 目录 | `~/ros2/ur5_lego` 独立 colcon 工作区 |

### 明确不做

- 24.04 上硬装 Noetic  
- 把 `catkin_ws` 当 ament 编译  
- 在 `~/ros2` **根** `colcon build`  

---

## 3. 包状态

| 包 | 状态 | 说明 |
|----|------|------|
| `ur5_lego_msgs` | **可用** | LegoDetection*、Attach/Detach/SetStatic |
| `ur5_lego_gazebo` | **可用** | world、level_manager、乐高/场景模型（box collision） |
| `ur5_lego_description` | **可用** | `ur5_lego_gz.urdf.xacro`、简化夹爪、控制器 yaml |
| `ur5_lego_bringup` | **可用** | `sim_smoke` / `lego_world` / **`sim_lego`**；`gripper_test` / `attach_demo` |
| `ur5_lego_attach` | **MVP 可用** | static-proxy sticky attach/detach |
| `ur5_lego_motion` | 空壳 | 待 MoveIt pick-place |
| `ur5_lego_vision` | 空壳+weights | 待 YOLO 节点 |

---

## 4. 阶段进度（当前）

| Phase | 内容 | 状态 | 验收 |
|-------|------|------|------|
| **0** | 布局/分支/骨架/官方 UR 冒烟 | **完成** | 控制器 activate |
| **1** | 乐高场景 + spawn + UR 同世界 | **完成** | 11 砖稳定；`sim_lego` 起臂+桌 |
| **2** | 夹爪开合 + attach/detach | **完成** | 开合 OK；static-proxy attach 复测通过 |
| **3** | MoveIt2 真值抓放 | 待做 | level1 A→home |
| **4** | YOLO 常驻 | 待做 | `/lego_detections` |
| **5** | 全管道 / 城堡 | 待做 | level2–4 |

### 步骤完成度（会话内）

```text
✅ Step A–D  lego_world + level_manager + SDF/box collision 修复
✅ Step E    UR5 + 乐高同世界（sim_lego）
✅ Step F    简化夹爪开合（gz JointPositionController + bridge）
✅ Step G    attach MVP（static-proxy：不闪、不乱飞、detach 下落）
⬜ Step H    MoveIt 点到点 / 真值 pick-place
⬜ Step I–J  YOLO / 全管道
```

---

## 5. 主入口与自测命令

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2/ur5_lego/install/setup.bash
cd ~/ros2/ur5_lego && colcon build --symlink-install   # 有改动时

# 主仿真：UR5 + 夹爪 + 乐高 world + attach 节点
ros2 launch ur5_lego_bringup sim_lego.launch.py ur_type:=ur5

# 夹爪开合（0=合，0.04=开，单位 m）
ros2 run ur5_lego_bringup gripper_test

# 一键：固定桌面 spawn + snap attach + 保持 + detach
ros2 run ur5_lego_bringup attach_demo -- --spawn --hold 15

# 仅场景 / 关卡
ros2 launch ur5_lego_bringup lego_world.launch.py
ros2 run ur5_lego_gazebo level_manager.py -l 1   # 或 -l 2
```

### 关键文件

| 路径 | 作用 |
|------|------|
| `ur5_lego_bringup/launch/sim_lego.launch.py` | 一键：gz + UR + 夹爪 bridge + attach |
| `ur5_lego_description/urdf/ur5_lego_gz.urdf.xacro` | 臂 + 简化夹爪 + gz 插件 |
| `ur5_lego_description/urdf/robotiq_2f_85_simple.urdf.xacro` | 左右 **prismatic** 平行指 |
| `ur5_lego_description/config/ur_lego_controllers.yaml` | 臂轨迹控制器（夹爪不走 ros2_control） |
| `ur5_lego_attach/.../attach_node.py` | attach/detach 服务 |
| `ur5_lego_gazebo/scripts/level_manager.py` | 关卡 spawn |
| `ur5_lego_gazebo/worlds/main_scene.sdf` | 桌/基座/Kinect |

---

## 6. 技术结论（已踩坑）

### 场景 / 积木

| 问题 | 处理 |
|------|------|
| inertial `<pose>` 仅 3 个数 | 补成 6 元组 |
| mesh collision → ODE trimesh 崩溃 | 全改 **box collision** |
| Classic Kinect 插件 | 去掉 `libgazebo_ros_openni_kinect`，保留简易 camera |
| table visual 内非法 light | 删除 |
| 纹理 `working area.png` | 改名为 `working_area.png` |
| 砖质量 ~1e-5 kg 几乎不掉 | 统一约 **0.02 kg** |

### 夹爪

| 问题 | 处理 |
|------|------|
| dartsim **不支持 mimic** | 不用官方完整 2F-85 联动 |
| ros2_control 位置指令指关节不动 | 改用 **gz JointPositionController** + `/gripper_*_cmd` bridge |
| prismatic 开合慢 | `p_gain` 提到 ~2000，`initial_position=0.04` |
| 完整四杆 vs 简化 | **默认平行 prismatic**（抓取够用）；revolute 仅试过 |

### Attach（对齐原项目语义）

原 ROS1：**合爪动画 + `gazebo_ros_link_attacher` 创建 fixed joint**（非摩擦抓取）。

| 尝试 | 结果 |
|------|------|
| 动态砖 + 低频 set_pose | 重力导致闪现掉落 |
| 动态砖 + 100Hz set_pose | 与物理/碰撞冲突 → 乱飞 |
| disable_collision（MODEL/LINK） | 服务要求 **COLLISION** 类型，易失败 |
| **static 代理 + set_pose**（当前） | 粘住稳定；detach 重生动态砖应可下落 |

当前 attach 流程：

```text
attach: remove 动态砖 → spawn static 代理 `名字__held` → TF sticky set_pose
detach: remove 代理 → spawn 动态砖（略低）→ 重力下落
```

服务：`/attach` `/detach` `/setstatic`（setstatic 仍为 MVP 确认）。

---

## 7. 原项目抓取对照

| | ROS1 | 本仓库 ROS2 |
|--|------|-------------|
| 合爪 | gripper action | `/gripper_left_cmd` `/gripper_right_cmd` |
| 粘住 | Classic **fixed joint** 插件 | **static 代理 + set_pose** |
| 粘着 link | `wrist_3_link` | TF `robotiq_85_base_link` |
| 放置固定 | attach ground + setstatic | 未完整复刻 |

---

## 8. 已知风险 / 待办

| 项 | 说明 |
|----|------|
| attach static-proxy | **2026-07-24 复测通过**（`attach_demo --spawn --hold 15`） |
| 相机 bridge | Kinect 仅占位；YOLO 前要 gz 相机 + ros_gz_bridge |
| MoveIt | 未接；臂仅有 trajectory controller |
| 真机式固定关节 | Harmonic 无等价 ros 插件；长期可评估 DetachableJoint / 自定义 system |
| 内存 ~8G | 默认 `launch_rviz:=false`；可 `gazebo_gui:=false` |
| 未提交改动 | 大量本地修改（attach/夹爪/SDF），尚未 commit/push |

---

## 9. 下一步（优先级）

1. **Phase 3**：MoveIt 点到点 → 真值位姿接近 → attach → 抬起  
2. 可选：放置 setstatic / 固定到桌面  
3. Phase 4：相机 bridge + YOLO 常驻  
4. Phase 5：多关卡 / 城堡 / 文档收尾  
5. 建议 **git commit**（拆：gazebo 资产 / description+夹爪 / attach / docs）

---

## 10. 变更日志（迁移）

| 日期 | 内容 |
|------|------|
| 2026-07-24 | 方案 C；`~/ros2` 布局；分支 `ros2-jazzy`；7 包骨架 |
| 2026-07-24 | Phase0 冒烟；Phase1 world/level_manager |
| 2026-07-24 | Phase1 实测：pose/box collision/Kinect/纹理修复；11 砖稳定 |
| 2026-07-24 | Step E：`sim_lego` UR+乐高同世界 |
| 2026-07-24 | Step F：简化夹爪 + gz JointPositionController 开合通过 |
| 2026-07-24 | Step G：attach MVP；迭代 sticky → static-proxy；砖质量 0.02kg |
| 2026-07-24 | Phase2 复测通过：`attach_demo --spawn --hold 15` 稳定粘合、detach 下落 |

---

## 11. 日常命令速查

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2/ur5_lego/install/setup.bash
cd ~/ros2/ur5_lego && colcon build --symlink-install

ros2 launch ur5_lego_bringup sim_lego.launch.py ur_type:=ur5
ros2 run ur5_lego_bringup gripper_test
ros2 run ur5_lego_bringup attach_demo -- --spawn --hold 15
ros2 run ur5_lego_gazebo level_manager.py -l 2
```
