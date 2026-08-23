cmake_minimum_required(VERSION 3.8)
project(mower_web)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  launch
  mower_web
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
