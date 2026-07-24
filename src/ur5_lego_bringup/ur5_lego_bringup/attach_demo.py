#!/usr/bin/env python3
"""Spawn one brick at a fixed table pose and snap-attach to gripper.

Usage (sim_lego already running):
  ros2 run ur5_lego_bringup attach_demo -- --spawn
  ros2 run ur5_lego_bringup attach_demo -- --model X1-Y1-Z2_1
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from std_msgs.msg import Float64

from ur5_lego_msgs.srv import Attach, Detach

# Fixed pose on table, in front of UR base (easy to see in default view)
DEMO_XYZ = (0.25, -0.35, 0.78)
DEMO_BRICK = 'X1-Y1-Z2'


class AttachDemo(Node):
    def __init__(self):
        super().__init__('attach_demo')
        self.pub_l = self.create_publisher(Float64, '/gripper_left_cmd', 10)
        self.pub_r = self.create_publisher(Float64, '/gripper_right_cmd', 10)
        self.cli_a = self.create_client(Attach, 'attach')
        self.cli_d = self.create_client(Detach, 'detach')

    def grip(self, open_: bool, hold_s: float = 2.0):
        v = 0.04 if open_ else 0.0
        msg = Float64(data=v)
        t0 = time.time()
        while time.time() - t0 < hold_s and rclpy.ok():
            self.pub_l.publish(msg)
            self.pub_r.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(0.02)

    def call_attach(self, model: str) -> bool:
        if not self.cli_a.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('attach service not available')
            return False
        req = Attach.Request()
        req.model_name_1 = 'ur'
        req.link_name_1 = 'robotiq_85_base_link'
        req.model_name_2 = model
        req.link_name_2 = 'link'
        fut = self.cli_a.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=10.0)
        if not fut.done() or fut.result() is None:
            self.get_logger().error('attach call failed')
            return False
        res = fut.result()
        self.get_logger().info(f'attach: ok={res.ok} msg={res.message}')
        return res.ok

    def call_detach(self, model: str) -> bool:
        if not self.cli_d.wait_for_service(timeout_sec=5.0):
            return False
        req = Detach.Request()
        req.model_name_2 = model
        fut = self.cli_d.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=5.0)
        if fut.done() and fut.result():
            self.get_logger().info(f'detach: {fut.result().message}')
            return fut.result().ok
        return False


def list_models() -> list[str]:
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


def spawn_fixed() -> str | None:
    """Spawn one brick at DEMO_XYZ with a unique name."""
    share = get_package_share_directory('ur5_lego_gazebo')
    sdf = os.path.join(share, 'models', 'lego', DEMO_BRICK, 'model.sdf')
    if not os.path.isfile(sdf):
        print(f'missing sdf: {sdf}')
        return None
    # unique name
    existing = set(list_models())
    idx = 1
    while f'{DEMO_BRICK}_{idx}' in existing:
        idx += 1
    name = f'{DEMO_BRICK}_{idx}'
    x, y, z = DEMO_XYZ
    cmd = [
        'ros2', 'run', 'ros_gz_sim', 'create',
        '-world', 'ur5_world',
        '-file', sdf,
        '-name', name,
        '-x', str(x), '-y', str(y), '-z', str(z),
        '-R', '0', '-P', '0', '-Y', '0',
    ]
    print('spawning fixed:', ' '.join(cmd))
    r = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout)
    time.sleep(1.0)
    models = list_models()
    return name if name in models else (name if r.returncode == 0 else None)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default=None)
    parser.add_argument('--spawn', action='store_true', help='spawn brick at fixed table pose')
    parser.add_argument('--hold', type=float, default=20.0)
    args, _ = parser.parse_known_args(argv)

    rclpy.init()
    node = AttachDemo()
    time.sleep(0.5)

    model = args.model
    if args.spawn or not model:
        if args.spawn or not model:
            model = spawn_fixed()
        if not model:
            models = list_models()
            lego = [m for m in models if m.startswith('X')]
            if not lego:
                node.get_logger().error(f'no lego models: {models}')
                node.destroy_node()
                rclpy.shutdown()
                return 1
            model = lego[-1]
            node.get_logger().info(f'using existing model {model}')

    node.get_logger().info(
        f'brick={model} should appear near table ({DEMO_XYZ}), then snap under gripper'
    )
    node.get_logger().info('open gripper')
    node.grip(True, 1.5)
    node.get_logger().info(f'snap-attach {model}')
    if not node.call_attach(model):
        node.destroy_node()
        rclpy.shutdown()
        return 1
    node.get_logger().info('close gripper (visual); brick should be under gripper now')
    node.grip(False, 2.0)
    node.get_logger().info(
        f'holding {args.hold}s — brick should stay under gripper (watch tip)'
    )
    t0 = time.time()
    # Keep publishing close so fingers stay closed; brick is held by attach sticky
    while time.time() - t0 < args.hold and rclpy.ok():
        node.grip(False, 0.5)
        node.get_logger().info(
            f'... still holding {args.hold - (time.time() - t0):.0f}s left'
        )
    node.get_logger().info('detach')
    node.call_detach(model)
    node.grip(True, 1.0)
    node.get_logger().info('done')
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
