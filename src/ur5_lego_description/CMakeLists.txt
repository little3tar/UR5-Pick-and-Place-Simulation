cmake_minimum_required(VERSION 3.8)
project(ur5_lego_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config urdf meshes
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

ament_package()
