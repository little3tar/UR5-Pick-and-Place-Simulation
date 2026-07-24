from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'ur5_lego_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='little3tar',
    maintainer_email='little3tar@users.noreply.github.com',
    description='Launch files for UR5 Lego simulation',
    license='MIT',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'gripper_test = ur5_lego_bringup.gripper_test:main',
            'attach_demo = ur5_lego_bringup.attach_demo:main',
        ],
    },
)
