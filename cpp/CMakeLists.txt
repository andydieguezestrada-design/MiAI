cmake_minimum_required(VERSION 3.16)
project(miai_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(miai_core STATIC
    core/miai_core.cpp
)

target_include_directories(miai_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/core
)
