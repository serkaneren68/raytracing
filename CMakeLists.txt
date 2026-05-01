cmake_minimum_required(VERSION 3.16)

project(raytracing LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(raytracing
    main.cc
    color.h
    hittable.h
    hittable_list.h
    ray.h
    rtweekend.h
    sphere.h
    cylinder.h
    image.h
    quad.h
    vec3.h
    camera.h
    material.h
)
