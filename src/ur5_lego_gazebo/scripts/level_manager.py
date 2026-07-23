#!/usr/bin/env python3
"""Spawn Lego bricks into Gazebo Harmonic (Phase 1 port of ROS1 levelManager)."""

import argparse
import math
import os
import random
import subprocess
import sys
import time

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Point, Pose, Quaternion
from rclpy.node import Node


BRICK_DICT = {
    'X1-Y1-Z2': (0, (0.031, 0.031, 0.057)),
    'X1-Y2-Z1': (1, (0.031, 0.063, 0.038)),
    'X1-Y2-Z2': (2, (0.031, 0.063, 0.057)),
    'X1-Y2-Z2-CHAMFER': (3, (0.031, 0.063, 0.057)),
    'X1-Y2-Z2-TWINFILLET': (4, (0.031, 0.063, 0.057)),
    'X1-Y3-Z2': (5, (0.031, 0.095, 0.057)),
    'X1-Y3-Z2-FILLET': (6, (0.031, 0.095, 0.057)),
    'X1-Y4-Z1': (7, (0.031, 0.127, 0.038)),
    'X1-Y4-Z2': (8, (0.031, 0.127, 0.057)),
    'X2-Y2-Z2': (9, (0.063, 0.063, 0.057)),
    'X2-Y2-Z2-FILLET': (10, (0.063, 0.063, 0.057)),
}
BRICK_LIST = list(BRICK_DICT.keys())

SPAWN_POS = (-0.35, -0.42, 0.74)
SPAWN_DIM = (0.32, 0.23)
MIN_SPACE = 0.010
MIN_DISTANCE = 0.15


def quat_from_euler(roll, pitch, yaw):
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    return Quaternion(
        x=sr * cp * cy - cr * sp * sy,
        y=cr * sp * cy + sr * cp * sy,
        z=cr * cp * sy - sr * sp * cy,
        w=cr * cp * cy + sr * sp * sy,
    )


class LevelManager(Node):
    def __init__(self, level: int, brick: str | None, world: str):
        super().__init__('level_manager')
        self.level = level
        self.select_brick = brick
        self.world = world
        share = get_package_share_directory('ur5_lego_gazebo')
        self.models_dir = os.path.join(share, 'models', 'lego')
        self.counters = {b: 0 for b in BRICK_LIST}
        self.lego = []  # (name, type, pose, radius)
        self.get_logger().info(
            f'level={level} brick={brick} world={world} models={self.models_dir}'
        )

    def model_sdf_path(self, brick_type: str) -> str:
        path = os.path.join(self.models_dir, brick_type, 'model.sdf')
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return path

    def random_pose(self, brick_type: str):
        _, dim = BRICK_DICT[brick_type]
        rot_z = random.uniform(-math.pi, math.pi)
        px = random.uniform(-SPAWN_DIM[0], SPAWN_DIM[0])
        py = random.uniform(-SPAWN_DIM[1], SPAWN_DIM[1])
        pz = dim[2] / 2.0
        pose = Pose(
            position=Point(x=px, y=py, z=pz),
            orientation=quat_from_euler(0.0, 0.0, rot_z),
        )
        return pose, dim[0], dim[1]

    def valid_pose(self, brick_type: str) -> tuple[Pose, float]:
        for _ in range(1000):
            pos, d1, d2 = self.random_pose(brick_type)
            radius = math.sqrt(d1 ** 2 + d2 ** 2) / 2.0
            ok = True
            for _n, _t, p, r2 in self.lego:
                min_dist = max(radius + r2 + MIN_SPACE, MIN_DISTANCE)
                dx = p.position.x - pos.position.x
                dy = p.position.y - pos.position.y
                if dx * dx + dy * dy < min_dist * min_dist:
                    ok = False
                    break
            if ok:
                # offset into spawn area center (world frame of invisible spawn marker)
                pos.position.x += SPAWN_POS[0]
                pos.position.y += SPAWN_POS[1]
                pos.position.z += SPAWN_POS[2]
                return pos, radius
        raise RuntimeError('No free space in spawn area')

    def gz_create(self, name: str, sdf_file: str, pose: Pose) -> bool:
        # Euler from quat for CLI
        q = pose.orientation
        # yaw-pitch-roll approximate for nearly flat bricks
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        cmd = [
            'ros2', 'run', 'ros_gz_sim', 'create',
            '-world', self.world,
            '-file', sdf_file,
            '-name', name,
            '-x', str(pose.position.x),
            '-y', str(pose.position.y),
            '-z', str(pose.position.z),
            '-R', '0', '-P', '0', '-Y', str(yaw),
        ]
        self.get_logger().info(' '.join(cmd))
        try:
            r = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                self.get_logger().error(r.stderr or r.stdout or f'exit {r.returncode}')
                return False
            return True
        except Exception as exc:
            self.get_logger().error(f'create failed: {exc}')
            return False

    def spawn_brick(self, brick_type: str | None = None):
        if brick_type is None:
            brick_type = random.choice(BRICK_LIST)
        self.counters[brick_type] += 1
        name = f'{brick_type}_{self.counters[brick_type]}'
        pose, radius = self.valid_pose(brick_type)
        path = self.model_sdf_path(brick_type)
        if self.gz_create(name, path, pose):
            self.lego.append((name, brick_type, pose, radius))
            self.get_logger().info(f'spawned {name}')
        else:
            self.counters[brick_type] -= 1

    def run_level(self):
        if self.level == 1:
            self.spawn_brick(self.select_brick)
        elif self.level == 2:
            for b in BRICK_LIST:
                self.spawn_brick(b)
        elif self.level == 3:
            for b in BRICK_LIST[:4]:
                self.spawn_brick(b)
            for _ in range(3):
                self.spawn_brick('X1-Y2-Z2')
        elif self.level == 4:
            # simplified: same as level 2 for now
            for b in BRICK_LIST:
                self.spawn_brick(b)
        else:
            self.get_logger().error(f'unknown level {self.level}')
            return
        self.get_logger().info(f'done: {len(self.lego)} bricks')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--level', type=int, default=1, choices=[1, 2, 3, 4])
    parser.add_argument('-b', '--brick', type=str, default=None, choices=BRICK_LIST)
    parser.add_argument('--world', type=str, default='ur5_world')
    # allow ros args after --
    args, ros_args = parser.parse_known_args(argv)
    rclpy.init(args=ros_args)
    node = LevelManager(args.level, args.brick, args.world)
    try:
        time.sleep(1.0)  # wait sim plugins
        node.run_level()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
