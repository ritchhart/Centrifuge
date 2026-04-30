cmake_minimum_required(VERSION 3.15)
project(CentrifugeMixed LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(centrifuge SHARED
    src/cpp_lib/centrifuge.cpp
)

target_include_directories(centrifuge PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp_lib
)

if(MSVC)
    target_compile_definitions(centrifuge PRIVATE CENTRIFUGE_EXPORTS)
endif()

set_target_properties(centrifuge PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/centrifuge
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/centrifuge
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/centrifuge
)
