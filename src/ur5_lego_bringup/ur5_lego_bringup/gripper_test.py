#!/usr/bin/env python3
"""Open/close parallel gripper via gz JointPositionController topics."""
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


class GripperTest(Node):
    def __init__(self):
        super().__init__('gripper_test')
        self.pub_l = self.create_publisher(Float64, '/gripper_left_cmd', 10)
        self.pub_r = self.create_publisher(Float64, '/gripper_right_cmd', 10)

    def wait_subs(self, timeout_s: float = 8.0) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout_s and rclpy.ok():
            n_l = self.pub_l.get_subscription_count()
            n_r = self.pub_r.get_subscription_count()
            if n_l > 0 and n_r > 0:
                self.get_logger().info(f'bridge subscribed (L={n_l}, R={n_r})')
                return True
            rclpy.spin_once(self, timeout_sec=0.05)
            time.sleep(0.1)
        self.get_logger().warn(
            'no subscribers on /gripper_*_cmd yet — is sim_lego + bridge running?'
        )
        return False

    def send(self, left: float, right: float, hold_s: float = 3.0):
        msg_l = Float64(data=float(left))
        msg_r = Float64(data=float(right))
        self.get_logger().info(
            f'command L={left:.3f} R={right:.3f} m  (0=closed, 0.04=open) for {hold_s}s'
        )
        t0 = time.time()
        n = 0
        while time.time() - t0 < hold_s and rclpy.ok():
            self.pub_l.publish(msg_l)
            self.pub_r.publish(msg_r)
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(0.02)
            n += 1
        self.get_logger().info(f'published {n} msgs')


def main():
    rclpy.init()
    node = GripperTest()
    node.wait_subs()
    # open → close → open (hold longer so motion is visible)
    node.send(0.04, 0.04, 2.0)
    node.send(0.0, 0.0, 4.0)
    node.send(0.04, 0.04, 3.0)
    node.get_logger().info('done')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
