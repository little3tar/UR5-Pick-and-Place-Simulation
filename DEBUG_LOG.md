# UR5-Pick-and-Place 项目 WSL2 调试经验总结

> Fork: https://github.com/little3tar/UR5-Pick-and-Place-Simulation
> 上游: https://github.com/pietrolechthaler/UR5-Pick-and-Place-Simulation
> 环境: Ubuntu 20.04 WSL2 + ROS Noetic + Gazebo 11 + CUDA 13.1 (MX450)

---

## 一、环境搭建

| 组件 | 版本 | 安装方式 |
|---|---|---|
| Ubuntu | 20.04 WSL2 | 系统自带 |
| ROS Noetic | desktop-full | apt (阿里云镜像) |
| Gazebo | 11.5.1 | 随 ROS 安装 |
| catkin-tools | 0.5.0 | apt |
| MoveIt | Noetic 全系列 | apt |
| YOLOv5 | v7.0 | git clone 到 `~/yolov5/` |
| PyTorch | 2.4.1+cu121 | pip install --user |
| GitHub CLI | 2.95.0 | apt (官方源) |

**GPU**: NVIDIA GeForce MX450，CUDA 13.1 驱动，torch 用 cu121 前向兼容正常。gzserver 占用约 1GB 显存。

**WSLg**: Win11 自带，`DISPLAY=:0` 无需额外配置，Gazebo 和 RViz 窗口直接弹到桌面。

---

## 二、项目编译

21/21 包全部编译成功，3 个包有命名规范警告（`levelManager`、`robotName_description` 大小写混用），不影响功能:

```
levelManager              ✅ 乐高世界启动 + 积木生成
vision                    ✅ YOLOv5 视觉识别（类型 + 姿态检测）
motion_planning           ✅ 逆运动学 + 抓取规划 + 分类摆放
build_planning            ✅ 城堡搭建模式（缺少 building.json 配置文件）
gazebo_ros_link_attacher  ✅ 抓取/释放/固定积木的 Gazebo 插件
robot (ur5 + robotiq)    ✅ UR5 机械臂 + Robotiq 夹爪模型和控制器
universal_robot           ✅ UR 驱动 + 运动学 + Gazebo 接口
```

---

## 三、核心踩坑记录

### 坑 1: Python 依赖地狱 ⭐最难

这是本次调试最大的痛点。项目有三个 Python 环境需求互斥：

- **ROS 包**（cv_bridge、rospy、sensor_msgs 等）只能通过 apt 装在系统 Python 3.8
- **PyTorch + CUDA** 需要从 PyPI 安装，与 `~/.local` 的用户包混在一起
- **YOLOv5 依赖** ultralytics、pandas、matplotlib、seaborn 等

**错误方案**: 用 venv/conda 隔离 ROS 和 ML 依赖。`source /opt/ros/noetic/setup.bash` 会把 ROS Python 路径注入，venv 的隔离机制与它冲突，导致 `ImportError: No module named 'rospy'`。

**正确方案**: 把所有 ML 依赖装在系统 Python 的 `--user` 路径 (`~/.local/lib/python3.8/site-packages`)，让 ROS 和 torch 在同一环境中共存。

#### 遇到的版本冲突及解决方案:

| 冲突 | 表现 | 解决 |
|---|---|---|
| numpy 1.24 vs 系统 pandas | `AttributeError: module 'numpy' has no attribute 'bool'` | 降级到 `numpy==1.23.5` |
| matplotlib 3.7 vs 系统 mpl_toolkits | `KeyError: 'scale'` | 降级到 `matplotlib==3.5.3` |
| setuptools 75 vs importlib-metadata 4.13 | `AttributeError: 'EntryPoints' not found` | 升级到 `importlib-metadata>=8.0` |
| ultralytics 缺 gitpython | AutoUpdate 循环失败 | `pip install gitpython` |
| triton 3.0 import setuptools | distutils 冲突 | 修复 importlib-metadata 后自动解决 |
| ultralytics 缺 tqdm | `ModuleNotFoundError: No module named 'tqdm'` | `pip install tqdm PyYAML seaborn` |

---

### 坑 2: apt install ros-noetic-desktop-full 卡 tzdata

`ros-noetic-desktop-full` 有 1800+ 个包，下载 897MB 后配置 `tzdata` 时需要交互式选择时区，导致 dpkg 一直等待输入。

**解决方案**: 安装前预设时区：

```bash
echo "tzdata tzdata/Areas select Asia" | sudo debconf-set-selections
echo "tzdata tzdata/Zones/Asia select Shanghai" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt install -y ros-noetic-desktop-full
```

如果已经卡住: `kill -9` 相关进程 → 清理 dpkg 锁 → 预设时区 → `dpkg --configure -a`。

---

### 坑 3: `/usr/bin/python` 不存在

Ubuntu 20.04 只有 `python3`，没有 `python` symlink。link_attacher 的 `demo.py` 和 `attach.py` 用了 `#!/usr/bin/env python`，直接报 `No such file or directory`。

```bash
sudo ln -sf /usr/bin/python3 /usr/bin/python
```

---

### 坑 4: motion_planning.py 和 vision.py 的时序耦合

这是项目原有设计问题。完整的 task pipeline 是：

```
camera → YOLOv5检测 → /lego_detections → motion_planning订阅
       → straighten(扶正) → 抓取 → link_attacher吸附
       → IK逆解 → joint_trajectory → PID → 机器人运动
       → 分类放置 → setStatic → 释放
```

但实现上有两个 bug：

1. **时序问题**: `motion_planning.py` 启动后 `wait_for_message("/lego_detections")` **无限等待**；而 `vision.py` 处理一帧后调用 `rospy.signal_shutdown(0)` **立即退出**。必须精确配合：先起 motion，再起 vision。

2. **IK 发散问题**: 即使时序正确，motion_planning 的自定义 IK 逆解（`kinematics.py` 手写 UR5 DH 参数解析解）在随机积木位姿下经常发散，`wait_for_position` 进入死循环（CPU 200%+），关节在目标位姿附近微震却永远无法收敛。

**临时方案**: `build_planning.py` 从 Gazebo 直接读积木位姿（不需要 vision），但缺少 `building.json` 配置文件。

**根本修复方向**: 将 motion_planning 的自定义 IK 换成 MoveIt 的 `ur_kinematics`（项目已安装），稳定性好很多。

---

### 坑 5: apt 锁竞争

多次 `apt install` 被丢到后台执行，然后又在前台发新的 `apt install`，两个进程抢 `/var/lib/dpkg/lock-frontend`，互相等待超时。

**教训**: apt 不能并发，后台跑一个就要等它完成。卡住时：

```bash
sudo kill -9 $(pgrep -f apt)
sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock
sudo dpkg --configure -a
```

---

### 坑 6: gh CLI 安装反复失败

完全由坑 5 导致——后台 apt 持有锁，前台 apt 永远等待。你手动在前台执行一条命令就成功了。此外之前用错了密钥路径（`/usr/share/keyrings/` 而非官方的 `/etc/apt/keyrings/`），但源已配好后就只剩锁的问题。

---

### 坑 7: catkin-tools 报 osrf-pycommon 缺失

```
pkg_resources.DistributionNotFound: The 'osrf-pycommon>0.1.1' distribution was not found
```

Ubuntu 20.04 的 `python3-catkin-tools` apt 包依赖不完整:

```bash
pip3 install --user osrf-pycommon
```

---

## 四、最终可用状态

| 功能 | 状态 | 备注 |
|---|---|---|
| Gazebo 仿真 + UR5 + 11种乐高 | ✅ | `roslaunch levelManager lego_world.launch` |
| Level 1-4 关卡系统 | ✅ | `rosrun levelManager levelManager.py -l 2` |
| YOLOv5 视觉识别 | ✅ | CUDA 加速，检测类型+朝向 |
| 轨迹控制器 (IK) | ✅ | 6 关节 + 夹爪 |
| link_attacher | ✅ | attach/detach/setstatic |
| **完整抓取-分类** | ❌ | IK 发散需修复 |
| build_planning | ❌ | 缺 building.json |

---

## 五、常用命令速查

### 启动仿真

```bash
# 终端 1: 启动 Gazebo + UR5
source /opt/ros/noetic/setup.bash
source ~/UR5-Pick-and-Place-Simulation/catkin_ws/devel/setup.bash
roslaunch levelManager lego_world.launch paused:=true gui:=true

# 取消暂停
rosservice call /gazebo/unpause_physics "{}"

# 生成积木
rosrun levelManager levelManager.py -l 2
```

### 编译

```bash
cd ~/UR5-Pick-and-Place-Simulation/catkin_ws
source /opt/ros/noetic/setup.bash
catkin build
source devel/setup.bash
```

### 同步上游

```bash
git fetch upstream
git merge upstream/main
```

### 重新编译单个包

```bash
catkin build motion_planning --no-deps
```
