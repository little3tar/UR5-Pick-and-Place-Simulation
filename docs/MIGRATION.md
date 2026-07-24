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

### 砖粘在夹爪「下方」是设计，不是故障

| 项 | 说明 |
|----|------|
| 现象 | attach 后砖停在夹爪下方约 `snap_offset_z`（默认 **0.12 m**，世界 −Z），而不是两指中间 |
| 原因 | MVP 用 **snap 到固定偏移** + static 代理，避免指尖穿模、乱飞；合爪主要是视觉 |
| 与真抓区别 | 真夹爪：砖在指缝间；当前：像吊在腕/夹爪下方的粘合点 |
| 与原 ROS1 | 同为 **attach 粘合**（非摩擦）；原为 fixed joint 粘 `wrist_3_link`，现为 sticky 跟 `robotiq_85_base_link` |
| 参数 | `ur5_lego_attach` / launch：`snap_offset_z`、`mode:=snap\|relative` |
| 后续可改 | MoveIt 接近后再 attach；或改相对指尖 TF / 减小偏移，使更像夹在中间 |

**不要**在未改需求前把「砖在下方」当成 bug 去修。

---

## 7. 新对话必读：设计约定（勿当 bug）

> 另开对话时**没有**本会话聊天记录。以下约定必须遵守，除非用户明确要求改设计。

### 7.1 目录与构建

| 约定 | 说明 |
|------|------|
| 工作区 | **只在** `~/ros2/ur5_lego` 执行 `colcon build` |
| 禁止 | `~/ros2` 根目录 colcon；不要编译 `ref/` 里的 ROS1 catkin |
| 分支 | 迁移开发在 **`ros2-jazzy`**；`main` 保留 ROS1 |
| 参考 | `~/ros2/ref/UR5-Pick-and-Place-Simulation` **只读** |
| 环境 | 先 `source /opt/ros/jazzy/setup.bash` 再 `source install/setup.bash` |

### 7.2 主入口与默认参数

| 项 | 值 |
|----|-----|
| 主 launch | `ros2 launch ur5_lego_bringup sim_lego.launch.py ur_type:=ur5` |
| 默认 RViz | **`launch_rviz:=false`**（省内存） |
| 无头仿真 | `gazebo_gui:=false` 可用 |
| 臂基座高度 | xacro `base_xyz` 默认 **`0 0 0.72`**（桌面附近，可微调） |
| 世界名 | **`ur5_world`**（与 `level_manager --world` 一致） |
| 机器人 gz 名 | spawn 名 **`ur`** |

`sim_lego.launch.py` 是**自建完整 launch**（含 `ParameterValue(..., value_type=str)`），**不要**改回单纯 Include 官方 `ur_sim_control` 而不处理长 URDF：否则会报 `Unable to parse robot_description as yaml`。

### 7.3 夹爪（简化平行指）

| 约定 | 说明 |
|------|------|
| 模型 | `robotiq_2f_85_simple.urdf.xacro`：**prismatic** 左右指，**非**官方完整 2F-85 四杆 |
| 为何不用完整版 | dartsim **不支持 URDF mimic**；continuous 关节会乱飞 |
| 驱动 | **不走** ros2_control 夹爪控制器；用 gz **`JointPositionController`** |
| 话题 | `/gripper_left_cmd`、`/gripper_right_cmd`（`std_msgs/Float64`） |
| 单位 | **米**；**0.0=合，0.04=开**（两侧同号同值，不是 ±rad） |
| 测试 | `ros2 run ur5_lego_bringup gripper_test` |
| 合爪含义 | **主要是视觉**；真正「抓住」靠 **attach**，不是摩擦 |

**不要**在未评估 mimic/物理前改回官方 `robotiq_2f_85_macro` 当仿真主路径。

### 7.4 积木 / 场景模型

| 约定 | 说明 |
|------|------|
| 碰撞 | 乐高用 **box collision**，**不要**改回 mesh collision（会 ODE trimesh 崩溃） |
| 质量 | 约 **0.02 kg**（太小会 detach 不掉落） |
| inertial pose | 必须 **6 个数**（xyz + rpy） |
| Kinect | 无 Classic 插件；**相机未做 ROS bridge**（YOLO 前再接） |
| 桌面纹理 | 文件名 `working_area.png`（无空格） |
| level_manager 随机区 | `SPAWN_POS≈(-0.35,-0.42,0.74)` 一带；可能偏视野外 |
| attach_demo spawn | 固定可见点 **`(0.25, -0.35, 0.78)`**，砖类型默认 `X1-Y1-Z2` |

### 7.5 Attach / Detach 接口与语义

| 约定 | 说明 |
|------|------|
| 服务 | `/attach`、`/detach`、`/setstatic`（`ur5_lego_msgs`） |
| 抓取语义 | 与 ROS1 相同：**粘合**，非物理夹紧 |
| attach 实现 | 删动态砖 → 生成 **static** 代理 **`{原名}__held`** → TF sticky `set_pose` |
| detach 实现 | 删代理 → 在略低处重生 **动态** 原名 → 应下落 |
| 默认 parent TF | **`robotiq_85_base_link`**（参数 `default_parent_frame`） |
| 请求字段习惯 | `model_name_2` = **砖在 gz 中的名字**；`link_name_1` = **夹爪 TF 帧** |
| 默认 mode | **`snap`**：吸附到夹爪**世界坐标下方** `snap_offset_z`（默认 0.12 m） |
| mode=relative | 保留附着瞬间相对位姿（砖可仍在桌上，夹爪不动时看不出「抓起」） |
| setstatic | **MVP 仅 acknowledge**，未实现真正 static |
| 砖名必须真实 | 用 `gz model --list` 或 spawn 日志名；错名会 attach 失败 |

**不要**把「夹爪下方偏移」「合爪不产生夹紧力」「代理名 `__held`」当成 bug。

### 7.6 臂控制与后续 Phase

| 约定 | 说明 |
|------|------|
| 当前臂控制 | `scaled_joint_trajectory_controller`（ros2_control + gz） |
| MoveIt | **未接入**；`ur5_lego_motion` 空壳 |
| 手写 IK | **不迁** `kinematics.py` |
| YOLO | weights 在 `ur5_lego_vision/weights/`，**节点未实现** |
| 下一优先 | Phase 3：MoveIt 点到点 → 真值接近 → attach → 抬起 |

### 7.7 资源与运行

| 约定 | 说明 |
|------|------|
| 内存 | 主机/WSL 约 **8GB** 级；优先无 RViz、可关 GUI |
| 改代码后 | `colcon build` + **重启** sim（attach/夹爪插件在进程内） |
| 推送 | 远程 `origin` = GitHub fork；本地可能 ahead，push 需网络/鉴权 |

---

## 8. 原项目抓取对照

| | ROS1 | 本仓库 ROS2 |
|--|------|-------------|
| 合爪 | gripper action | `/gripper_left_cmd` `/gripper_right_cmd`（m） |
| 粘住 | Classic **fixed joint** 插件 | **static 代理 + set_pose** |
| 粘着 link | `wrist_3_link` | TF `robotiq_85_base_link` |
| 放置固定 | attach ground + setstatic | 未完整复刻 |

---

## 9. 已知风险 / 待办

| 项 | 说明 |
|----|------|
| attach static-proxy | **2026-07-24 复测通过**（`attach_demo --spawn --hold 15`） |
| 相机 bridge | Kinect 仅占位；YOLO 前要 gz 相机 + ros_gz_bridge |
| MoveIt | 未接；臂仅有 trajectory controller |
| 真机式固定关节 | Harmonic 无等价 ros 插件；长期可评估 DetachableJoint / 自定义 system |
| 内存 ~8G | 默认 `launch_rviz:=false`；可 `gazebo_gui:=false` |
| snap 观感 | 砖在夹爪下而非指间 = 设计（见 §7.5） |

---

## 10. 下一步（优先级）

1. **Phase 3**：MoveIt 点到点 → 真值位姿接近 → attach → 抬起  
2. 可选：放置 setstatic / 固定到桌面  
3. Phase 4：相机 bridge + YOLO 常驻  
4. Phase 5：多关卡 / 城堡 / 文档收尾  

---

## 11. 变更日志（迁移）

| 日期 | 内容 |
|------|------|
| 2026-07-24 | 方案 C；`~/ros2` 布局；分支 `ros2-jazzy`；7 包骨架 |
| 2026-07-24 | Phase0 冒烟；Phase1 world/level_manager |
| 2026-07-24 | Phase1 实测：pose/box collision/Kinect/纹理修复；11 砖稳定 |
| 2026-07-24 | Step E：`sim_lego` UR+乐高同世界 |
| 2026-07-24 | Step F：简化夹爪 + gz JointPositionController 开合通过 |
| 2026-07-24 | Step G：attach MVP；迭代 sticky → static-proxy；砖质量 0.02kg |
| 2026-07-24 | Phase2 复测通过：`attach_demo --spawn --hold 15` 稳定粘合、detach 下落 |
| 2026-07-24 | 文档：§7 新对话必读设计约定（夹爪/attach/构建/勿当 bug） |

---

## 12. 日常命令速查

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2/ur5_lego/install/setup.bash
cd ~/ros2/ur5_lego && colcon build --symlink-install

ros2 launch ur5_lego_bringup sim_lego.launch.py ur_type:=ur5
ros2 run ur5_lego_bringup gripper_test
ros2 run ur5_lego_bringup attach_demo -- --spawn --hold 15
ros2 run ur5_lego_gazebo level_manager.py -l 2
```
