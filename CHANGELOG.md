# UR5 Pick-and-Place Simulation — 更新日志

> 上游: [pietrolechthaler/UR5-Pick-and-Place-Simulation](https://github.com/pietrolechthaler/UR5-Pick-and-Place-Simulation)
> Fork: [little3tar/UR5-Pick-and-Place-Simulation](https://github.com/little3tar/UR5-Pick-and-Place-Simulation)
> 环境: Ubuntu 20.04 WSL2 / ROS Noetic / Gazebo 11 / CUDA 13.1 (MX450)

---

## [0.3.0] — 2026-06-21

### 🔧 Bug 修复

#### 修复 1: vision 节点一帧后退出导致 motion_planning 崩溃

**文件**: `catkin_ws/src/vision/scripts/lego-vision.py`

| 行 | 修改前 | 修改后 |
|----|--------|--------|
| 429 | `rospy.signal_shutdown(0)` | **删除** |
| 416 | `cv.waitKey()` | `cv.waitKey(1)` |

- **问题**: `process_CB` 回调在每帧 YOLOv5 检测完成后调用 `rospy.signal_shutdown(0)`，导致 ROS 节点立即关闭。`motion_planning.py` 在接收 `/lego_detections` 后进入后续处理时收到 `rospy.exceptions.ROSInterruptException`，管道崩溃。
- **修复**: 删除 shutdown 调用，vision 改为持续运行（实测 100+ 帧无退出），`/lego_detections` 持续发布 ~16Hz，motion_planning 不再因 ROS shutdown 崩溃。附带将 `cv.waitKey()` 改为 `cv.waitKey(1)` 使 `-show` 模式不再每帧阻塞。
- **关联**: 上游项目已知 bug，已在 DEBUG_LOG 中记录。

---

#### 修复 2: trajectory_controller 启动时序竞态

**文件**: `catkin_ws/src/robot/ur5/ur5_gazebo/launch/ur5_controllers.launch`

| 行 | 修改前 | 修改后 |
|----|--------|--------|
| 16 | `args="joint_state_controller trajectory_controller gripper_controller"` | `args="--no-timeout joint_state_controller trajectory_controller gripper_controller"` |

- **问题**: `controller_manager/spawner` 与 Gazebo 在 launch 文件中并行启动。spawner 默认超时 30 秒，但 Gazebo 初始化 + UR5 模型生成需要 5-10 秒，其内部的 `controller_manager` ROS 接口在此期间不可用。spawner 在服务出现前超时退出，控制器停留在 `initialized` 状态，需手动调用 `switch_controller`。
- **修复**: 添加 `--no-timeout` 使 spawner 无限等待 `controller_manager` 服务就绪。一条 `roslaunch levelManager lego_world.launch` 即可完成全部初始化，三个控制器全部自动进入 `running` 状态。

---

### 🏗️ 环境配置

- **XTDrone 多工作区共存**: `~/catkin_ws`（XTDrone 定制 `gazebo_ros_pkgs`）通过 `--extend` 编译，与 `~/UR5-Pick-and-Place-Simulation/catkin_ws` 和 `/opt/ros/noetic` 构成三工作区链，`gazebo_ros` 使用 XTDrone 版，UR5 专有包（`gazebo_ros_link_attacher`、`ur_gazebo` 等）不受影响。
- **`.bashrc` 调整**: 在工作区链中正确插入 `source ~/catkin_ws/devel/setup.bash`。

---

## [0.2.0] — 2026-06-20

**Commit**: [`d11ebd4`](https://github.com/little3tar/UR5-Pick-and-Place-Simulation/commit/d11ebd4)

### 📝 文档重写

#### README 中英双语化 & 踩坑指南

**文件**: `README.md`

- **中英双语重写**: 全部章节双语（项目描述、目录结构、环境要求、安装步骤、使用方法）
- **新增 Known Pitfalls（已知踩坑指南）章节**: 从 DEBUG_LOG 提炼 8 个坑，每个包含 Problem / Fix：
  1. vision.py 一帧退出 + motion_planning 崩溃
  2. 逆运动学求解发散
  3. building.json 缺失
  4. `#!/usr/bin/env python` 在 Ubuntu 20.04 上不存在
  5. Python 依赖版本冲突（numpy/matplotlib/setuptools）
  6. catkin-tools 缺少 osrf-pycommon
  7. tzdata 交互式安装卡住
  8. gzserver GPU 显存占用
- **修正错误指令**: `vision.py` → `lego-vision.py`，pip install 方案改为 `--user` 安装
- **新增 Python 环境管理警告**: 明确禁止使用 venv/conda，ROS 包仅系统 Python 3.8 可用
- **新增贡献者表格**
- **新增 Fork 说明**

#### DEBUG_LOG 更新

**文件**: `DEBUG_LOG.md`

- 新增「零、最新测试结果 (2026-06-20)」章节，完整仿真全流程结果表
- 确认 **vision shutdown → motion_planning 崩溃** 为当前管道最大阻塞点

---

**Commit**: [`b55d3e9`](https://github.com/little3tar/UR5-Pick-and-Place-Simulation/commit/b55d3e9)

### 📝 新增 WSL2 调试日志

**文件**: `DEBUG_LOG.md`（新建，205 行）

完整记录从零开始在 WSL2 + Ubuntu 20.04 + ROS Noetic 上搭建并调试本项目的全过程：

- **环境搭建**: 各组件版本与安装方式矩阵
- **项目编译**: 21/21 包全部成功，3 个命名规范警告
- **核心踩坑记录**（7 个坑，每个包含表现 + 解决方案）:
  1. Python 依赖地狱（numpy/matplotlib/setuptools 版本冲突链）
  2. apt install ros-noetic-desktop-full 卡 tzdata
  3. `/usr/bin/python` 不存在
  4. motion_planning.py 和 vision.py 的时序耦合（wait_for_message 无限等待）
  5. apt 锁竞争
  6. gh CLI 安装反复失败
  7. catkin-tools 报 osrf-pycommon 缺失
- **可通过修改仓库修复的问题**（4 个 + 1 个新建文件方案）
- **无法通过修改仓库避免的环境问题**（4 个）
- **最终可用状态**
- **常用命令速查**

---

## [0.1.0] — 2022-07-24

**Commits**: `d139dc1`, `ee4cb63`（Pietro Lechthaler）

### 🎉 初始版本

- UR5 + Robotiq 85 夹爪 Gazebo 仿真
- Xbox Kinect 相机模型
- YOLOv5 视觉识别管道（类型检测 + 深度估计 + 朝向检测）
- 11 种乐高积木生成系统（Level 1-4 关卡）
- 自定义 UR5 DH 参数逆运动学求解
- link_attacher 插件（抓取/释放/固定）
- motion_planning 拾取-分类-摆放逻辑
- build_planning 城堡搭建模式

---

## 已知未修复问题

### 🔴 P0: 逆运动学求解发散

**文件**: `catkin_ws/src/motion_planning/scripts/kinematics.py`

手写 UR5 DH 参数解析解在随机积木位姿下，关节目标接近奇异点时 `wait_for_position` 进入死循环，CPU 占用 200%+，关节在目标附近微震但无法收敛。

**方向**: 将自定义 IK 替换为 MoveIt 的 `ur_kinematics`（项目已通过 apt 安装 `ros-noetic-moveit-kinematics`）。

---

### 🔴 P1: build_planning 城堡搭建模式不可用

**文件**: `catkin_ws/src/motion_planning/scripts/build_planning.py:78`

引用仓库中不存在的 `building.json` 配置文件，直接运行会崩溃。需要创建 `building.json` 或添加文件存在性检查并给出清晰错误提示。

---

### 🟡 P2: YOLOv5 分类警告

**文件**: `catkin_ws/src/vision/scripts/lego-vision.py`

运行时频繁打印 `[Warning] Error in classification` / `Classification not found`。某些视角下部分积木类型无法被模型识别，不影响已检出积木的处理。

**方向**: 检查 `depth.pt` / `orientation.pt` 模型权重是否覆盖全部 11 种积木类型。

---

### 🟢 P3: Python shebang 兼容性

**文件**: `catkin_ws/src/gazebo_ros_link_attacher/scripts/*.py`（7 个文件）

脚本首行使用 `#!/usr/bin/env python`，Ubuntu 20.04 只有 `python3` 命令。

**临时方案**: `sudo ln -sf /usr/bin/python3 /usr/bin/python`

---

### 🟢 P4: Python 依赖版本冲突

ROS 系统包（apt）与 ML 包（pip）共存时存在版本冲突链：

| 冲突 | 表现 | 锁定版本 |
|------|------|----------|
| numpy 1.24 vs pandas | `AttributeError: module 'numpy' has no attribute 'bool'` | `numpy==1.23.5` |
| matplotlib 3.7 vs mpl_toolkits | `KeyError: 'scale'` | `matplotlib==3.5.3` |
| setuptools 75 vs importlib-metadata 4.13 | `AttributeError: 'EntryPoints' not found` | `importlib-metadata>=8.0` |
| ultralytics 缺 gitpython | AutoUpdate 循环失败 | `pip install gitpython` |
| ultralytics 缺 tqdm | `ModuleNotFoundError` | `pip install tqdm PyYAML seaborn` |

仓库缺少 `requirements.txt`，新用户需手动锁定版本。

---

### 🟢 P5: 缺少一键启动脚本

README 描述了分步启动流程（`roslaunch` → `rosservice call` → `rosrun levelManager` → `rosrun vision` → `rosrun motion_planning`），但没有自动化脚本。

**方向**: 编写 `start_simulation.sh`，自动完成 Gazebo 启动 → 等待就绪 → 生成积木 → 启动 vision → 启动 motion_planning。

---

## 环境问题（系统级，不属仓库修复范围）

| 问题 | 修复 |
|------|------|
| `/usr/bin/python` symlink | `sudo ln -sf /usr/bin/python3 /usr/bin/python` |
| catkin-tools 缺 osrf-pycommon | `pip3 install --user osrf-pycommon` |
| tzdata 交互式安装 | 安装前 `debconf-set-selections` 预设时区 |
| apt 锁竞争 | `kill -9 $(pgrep -f apt) && rm -f /var/lib/dpkg/lock-frontend` |
| pip venv/conda 与 ROS 冲突 | 所有 ML 依赖装到系统 Python 的 `--user` 路径 |

---

## 验证通过的功能

- ✅ Gazebo 11 仿真启动 + WSLg 图形显示（`DISPLAY=:0`）
- ✅ UR5 + Robotiq 85 夹爪模型加载与控制（6 关节 + 2 指）
- ✅ 11 种乐高积木生成（Level 1–4 关卡系统）
- ✅ Xbox Kinect RGB+Depth 相机（20–25Hz 发布）
- ✅ YOLOv5 视觉识别：类型检测 (`best.pt`) + 深度估计 (`depth.pt`) + 朝向检测 (`orientation.pt`)，CUDA 加速，~16Hz 持续推理
- ✅ link_attacher 插件（`/link_attacher_node/attach|detach|setstatic`）
- ✅ trajectory_controller 自动启动（三控制器全部自动 `running`）
- ✅ vision → motion_planning 管道连通（`/lego_detections` → 关节轨迹 → UR5 移动）
- ✅ UR5 关节运动控制（joint_states 变化验证关节实际移动）
