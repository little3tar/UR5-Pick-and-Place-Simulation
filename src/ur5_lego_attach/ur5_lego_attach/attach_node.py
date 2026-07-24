#!/usr/bin/env python3
"""TF sticky attach for Gazebo Harmonic (Phase 2 MVP).

Strategy (stable, no fly-away):
  attach: remove dynamic brick -> spawn STATIC proxy under gripper
          high-rate set_pose on static proxy (no gravity/collision fight)
  detach: remove proxy -> spawn DYNAMIC brick at last pose (falls with gravity)
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import threading
from dataclasses import dataclass

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

from ur5_lego_msgs.srv import Attach, Detach, SetStatic

BRICK_TYPES = {
    'X1-Y1-Z2', 'X1-Y2-Z1', 'X1-Y2-Z2', 'X1-Y2-Z2-CHAMFER', 'X1-Y2-Z2-TWINFILLET',
    'X1-Y3-Z2', 'X1-Y3-Z2-FILLET', 'X1-Y4-Z1', 'X1-Y4-Z2', 'X2-Y2-Z2', 'X2-Y2-Z2-FILLET',
}


def quat_multiply(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    )


def quat_inverse(q):
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        return (0.0, 0.0, 0.0, 1.0)
    return (-x / n, -y / n, -z / n, w / n)


def rotate_vec(q, v):
    qv = (v[0], v[1], v[2], 0.0)
    return quat_multiply(quat_multiply(q, qv), quat_inverse(q))[:3]


def pose_compose(p_a, q_a, p_b, q_b):
    rx, ry, rz = rotate_vec(q_a, p_b)
    return (p_a[0] + rx, p_a[1] + ry, p_a[2] + rz), quat_multiply(q_a, q_b)


def pose_relative(p_a, q_a, p_b, q_b):
    q_inv = quat_inverse(q_a)
    dx, dy, dz = p_b[0] - p_a[0], p_b[1] - p_a[1], p_b[2] - p_a[2]
    return rotate_vec(q_inv, (dx, dy, dz)), quat_multiply(q_inv, q_b)


def rpy_to_quat(roll, pitch, yaw):
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


def quat_to_rpy(q):
    x, y, z, w = q
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1 else math.asin(sinp)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


def brick_type_from_name(model: str) -> str | None:
    # X1-Y1-Z2_1 -> X1-Y1-Z2
    for t in sorted(BRICK_TYPES, key=len, reverse=True):
        if model == t or model.startswith(t + '_'):
            return t
    return None


@dataclass
class Sticky:
    model_name: str          # current gz entity name (proxy while attached)
    original_name: str       # name to restore on detach
    brick_type: str
    parent_frame: str
    p_rel: tuple
    q_rel: tuple
    is_proxy: bool


class AttachNode(Node):
    def __init__(self):
        super().__init__('ur5_lego_attach')
        self.declare_parameter('world', 'ur5_world')
        self.declare_parameter('rate_hz', 30.0)
        self.declare_parameter('default_parent_frame', 'robotiq_85_base_link')
        self.declare_parameter('tf_root', 'world')
        self.declare_parameter('mode', 'snap')
        self.declare_parameter('snap_offset_z', 0.12)
        self.world = self.get_parameter('world').get_parameter_value().string_value
        rate = self.get_parameter('rate_hz').get_parameter_value().double_value
        self.default_parent = (
            self.get_parameter('default_parent_frame').get_parameter_value().string_value
        )
        self.tf_root = self.get_parameter('tf_root').get_parameter_value().string_value
        self.mode = self.get_parameter('mode').get_parameter_value().string_value
        self.snap_z = abs(self.get_parameter('snap_offset_z').get_parameter_value().double_value)

        try:
            self.models_dir = os.path.join(
                get_package_share_directory('ur5_lego_gazebo'), 'models', 'lego'
            )
        except Exception:
            self.models_dir = ''

        self._lock = threading.Lock()
        self._sticky: dict[str, Sticky] = {}  # key = original_name

        self.tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_service(Attach, 'attach', self.on_attach)
        self.create_service(Detach, 'detach', self.on_detach)
        self.create_service(SetStatic, 'setstatic', self.on_setstatic)

        self.create_timer(1.0 / max(rate, 1.0), self._tick)
        self.get_logger().info(
            f'attach ready world={self.world} parent={self.default_parent} '
            f'rate={rate}Hz mode={self.mode} (static-proxy sticky)'
        )

    def _list_models(self) -> list[str]:
        try:
            r = subprocess.run(
                ['gz', 'model', '--list'],
                capture_output=True, text=True, timeout=3.0, check=False,
            )
        except Exception:
            return []
        names = []
        for line in (r.stdout or '').splitlines():
            line = line.strip()
            if line.startswith('- '):
                names.append(line[2:].strip())
        return names

    def _lookup_frame(self, frame: str):
        last_err = None
        for root in (self.tf_root, 'world', 'base_link'):
            try:
                tf = self.tf_buffer.lookup_transform(
                    root, frame, Time(), timeout=Duration(seconds=0.15)
                )
                t = tf.transform.translation
                r = tf.transform.rotation
                return (t.x, t.y, t.z), (r.x, r.y, r.z, r.w)
            except Exception as exc:
                last_err = exc
        raise RuntimeError(f'TF lookup failed for {frame}: {last_err}')

    def _gz_model_pose(self, model: str):
        try:
            r = subprocess.run(
                ['gz', 'model', '-m', model, '-p'],
                capture_output=True, text=True, timeout=2.0, check=False,
            )
        except Exception as exc:
            self.get_logger().warn(f'gz model pose failed: {exc}')
            return None
        out = (r.stdout or '') + '\n' + (r.stderr or '')
        if 'Unable' in out or 'not found' in out.lower() or r.returncode != 0:
            return None
        nums = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', out)
        if len(nums) >= 6:
            x, y, z = float(nums[0]), float(nums[1]), float(nums[2])
            roll, pitch, yaw = float(nums[3]), float(nums[4]), float(nums[5])
            return (x, y, z), rpy_to_quat(roll, pitch, yaw)
        if len(nums) >= 3:
            return (float(nums[0]), float(nums[1]), float(nums[2])), (0.0, 0.0, 0.0, 1.0)
        return None

    def _set_pose(self, model: str, p, q) -> bool:
        x, y, z = p
        qx, qy, qz, qw = q
        n = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
        if n < 1e-9:
            qx, qy, qz, qw = 0.0, 0.0, 0.0, 1.0
        else:
            qx, qy, qz, qw = qx / n, qy / n, qz / n, qw / n
        req_txt = (
            f'name: "{model}", '
            f'position: {{x: {x}, y: {y}, z: {z}}}, '
            f'orientation: {{x: {qx}, y: {qy}, z: {qz}, w: {qw}}}'
        )
        cmd = [
            'gz', 'service', '-s', f'/world/{self.world}/set_pose',
            '--reqtype', 'gz.msgs.Pose',
            '--reptype', 'gz.msgs.Boolean',
            '--timeout', '1000',
            '--req', req_txt,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0, check=False)
            text = ((r.stdout or '') + (r.stderr or '')).lower()
            return r.returncode == 0 and 'true' in text and 'false' not in text
        except Exception as exc:
            self.get_logger().warn(f'set_pose: {exc}')
            return False

    def _remove_model(self, model: str) -> bool:
        cmd = [
            'gz', 'service', '-s', f'/world/{self.world}/remove',
            '--reqtype', 'gz.msgs.Entity',
            '--reptype', 'gz.msgs.Boolean',
            '--timeout', '1500',
            '--req', f'name: "{model}", type: 2',
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=2.5, check=False)
            text = ((r.stdout or '') + (r.stderr or '')).lower()
            ok = r.returncode == 0 and 'true' in text
            if not ok:
                self.get_logger().warn(f'remove {model}: {(r.stdout or r.stderr or "")[:120]}')
            return ok
        except Exception as exc:
            self.get_logger().warn(f'remove exception: {exc}')
            return False

    def _spawn_brick(self, brick_type: str, name: str, p, q, static: bool) -> bool:
        sdf_path = os.path.join(self.models_dir, brick_type, 'model.sdf')
        if not os.path.isfile(sdf_path):
            self.get_logger().error(f'missing sdf {sdf_path}')
            return False
        # Read and force static flag
        try:
            sdf = open(sdf_path, encoding='utf-8').read()
        except Exception as exc:
            self.get_logger().error(f'read sdf: {exc}')
            return False
        if static:
            sdf = re.sub(
                r'<static>\s*false\s*</static>',
                '<static>true</static>',
                sdf,
                count=1,
                flags=re.IGNORECASE,
            )
            if '<static>' not in sdf:
                sdf = sdf.replace('<model', '<model', 1)
                sdf = re.sub(
                    r'(<model[^>]*>)',
                    r'\1\n    <static>true</static>',
                    sdf,
                    count=1,
                )
        else:
            sdf = re.sub(
                r'<static>\s*true\s*</static>',
                '<static>false</static>',
                sdf,
                count=1,
                flags=re.IGNORECASE,
            )

        # Write temp sdf with unique name attribute
        tmp = f'/tmp/ur5_lego_{name}.sdf'
        sdf = re.sub(
            r'<model name="[^"]*">',
            f'<model name="{name}">',
            sdf,
            count=1,
        )
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(sdf)

        roll, pitch, yaw = quat_to_rpy(q)
        cmd = [
            'ros2', 'run', 'ros_gz_sim', 'create',
            '-world', self.world,
            '-file', tmp,
            '-name', name,
            '-x', str(p[0]), '-y', str(p[1]), '-z', str(p[2]),
            '-R', str(roll), '-P', str(pitch), '-Y', str(yaw),
        ]
        # Ensure model:// mesh path resolves
        env = os.environ.copy()
        lego = self.models_dir
        scene = os.path.join(os.path.dirname(self.models_dir), 'scene') if self.models_dir else ''
        extra = ':'.join([p for p in (lego, scene) if p])
        if extra:
            env['GZ_SIM_RESOURCE_PATH'] = (
                extra + (':' + env['GZ_SIM_RESOURCE_PATH'] if env.get('GZ_SIM_RESOURCE_PATH') else '')
            )
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=8.0, check=False, env=env,
            )
            if r.returncode != 0:
                self.get_logger().warn(
                    f'spawn {name} failed: {(r.stderr or r.stdout or "")[:200]}'
                )
                return False
            return True
        except Exception as exc:
            self.get_logger().error(f'spawn exception: {exc}')
            return False

    def on_attach(self, req: Attach.Request, res: Attach.Response):
        parent_frame = (req.link_name_1 or '').strip() or self.default_parent
        model = (req.model_name_2 or '').strip() or (req.model_name_1 or '').strip()
        if not model:
            res.ok = False
            res.message = 'model_name_2 (brick) empty'
            return res

        with self._lock:
            if model in self._sticky or any(
                s.model_name == model or s.original_name == model for s in self._sticky.values()
            ):
                res.ok = False
                res.message = f'already attached: {model}'
                return res

        models = self._list_models()
        if models and model not in models:
            lego = [m for m in models if m.startswith('X')]
            res.ok = False
            res.message = f'model "{model}" not in world. available: {lego or models}'
            self.get_logger().error(res.message)
            return res

        btype = brick_type_from_name(model)
        if not btype:
            res.ok = False
            res.message = f'cannot parse brick type from name {model}'
            return res

        try:
            p_g, q_g = self._lookup_frame(parent_frame)
        except Exception as exc:
            res.ok = False
            res.message = str(exc)
            return res

        # Target pose: under gripper in WORLD -Z
        if self.mode == 'relative':
            brick = self._gz_model_pose(model)
            if brick is None:
                p_tgt = (p_g[0], p_g[1], p_g[2] - self.snap_z)
                q_tgt = (0.0, 0.0, 0.0, 1.0)
            else:
                p_tgt, q_tgt = brick
        else:
            p_tgt = (p_g[0], p_g[1], p_g[2] - self.snap_z)
            q_tgt = (0.0, 0.0, 0.0, 1.0)

        p_rel, q_rel = pose_relative(p_g, q_g, p_tgt, q_tgt)

        # Replace dynamic brick with static proxy (no physics fight)
        proxy = f'{model}__held'
        self._remove_model(model)
        if not self._spawn_brick(btype, proxy, p_tgt, q_tgt, static=True):
            # try restore original dynamic at table if spawn failed
            self._spawn_brick(btype, model, p_tgt, q_tgt, static=False)
            res.ok = False
            res.message = f'failed to spawn static proxy for {model}'
            return res

        sticky = Sticky(
            model_name=proxy,
            original_name=model,
            brick_type=btype,
            parent_frame=parent_frame,
            p_rel=p_rel,
            q_rel=q_rel,
            is_proxy=True,
        )
        with self._lock:
            self._sticky[model] = sticky

        res.ok = True
        res.message = (
            f'attached {model} as static proxy {proxy} -> {parent_frame} '
            f'xyz=({p_tgt[0]:.3f},{p_tgt[1]:.3f},{p_tgt[2]:.3f})'
        )
        self.get_logger().info(res.message)
        return res

    def on_detach(self, req: Detach.Request, res: Detach.Response):
        model = (req.model_name_2 or '').strip() or (req.model_name_1 or '').strip()
        with self._lock:
            sticky = self._sticky.pop(model, None)
            if sticky is None:
                # also allow detaching by proxy name
                for k, s in list(self._sticky.items()):
                    if s.model_name == model:
                        sticky = self._sticky.pop(k)
                        model = k
                        break
        if sticky is None:
            res.ok = False
            res.message = f'not attached: {model}'
            self.get_logger().info(res.message)
            return res

        # Last pose from TF
        try:
            p_g, q_g = self._lookup_frame(sticky.parent_frame)
            p, q = pose_compose(p_g, q_g, sticky.p_rel, sticky.q_rel)
        except Exception:
            pose = self._gz_model_pose(sticky.model_name)
            if pose is None:
                res.ok = False
                res.message = f'detach: lost pose for {sticky.model_name}'
                return res
            p, q = pose

        self._remove_model(sticky.model_name)
        # Drop slightly so it is free of gripper mesh
        p_drop = (p[0], p[1], p[2] - 0.03)
        ok = self._spawn_brick(sticky.brick_type, sticky.original_name, p_drop, q, static=False)
        res.ok = ok
        res.message = (
            f'detached {sticky.original_name} (dynamic respawn, falls)'
            if ok else f'detach respawn failed for {sticky.original_name}'
        )
        self.get_logger().info(res.message)
        return res

    def on_setstatic(self, req: SetStatic.Request, res: SetStatic.Response):
        res.ok = True
        res.message = f'setstatic({req.model_name}, {req.set_static}) acknowledged (MVP)'
        return res

    def _tick(self):
        with self._lock:
            items = list(self._sticky.values())
        for s in items:
            try:
                p_g, q_g = self._lookup_frame(s.parent_frame)
            except Exception:
                continue
            p, q = pose_compose(p_g, q_g, s.p_rel, s.q_rel)
            self._set_pose(s.model_name, p, q)


def main():
    rclpy.init()
    node = AttachNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
