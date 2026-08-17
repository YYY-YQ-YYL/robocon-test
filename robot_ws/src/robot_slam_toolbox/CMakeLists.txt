cmake_minimum_required(VERSION 3.8)
project(robot_slam_toolbox)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(slam_toolbox REQUIRED)

# 纯数据包：安装 config / launch / rviz 目录
install(DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
