from setuptools import find_packages, setup

package_name = 'ur5_lego_attach'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='little3tar',
    maintainer_email='little3tar@users.noreply.github.com',
    description='Gazebo link attach/detach services (TF sticky MVP)',
    license='MIT',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'attach_node = ur5_lego_attach.attach_node:main',
        ],
    },
)
