cmake_minimum_required(VERSION 3.16)

project(raytracing LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(raytracing
    src/main.cc
    src/app.cc
    src/app.h
)

target_include_directories(raytracing PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include/raytracing
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)
