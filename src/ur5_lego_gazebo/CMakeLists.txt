cmake_minimum_required(VERSION 3.8)
project(ur5_lego_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY models worlds launch
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

install(PROGRAMS
  scripts/level_manager.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
