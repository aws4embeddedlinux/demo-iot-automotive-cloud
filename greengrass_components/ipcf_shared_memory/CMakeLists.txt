cmake_minimum_required(VERSION 3.0)
project(greengrass_pubIPC C CXX)

# Compiler setup
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -g") # Add any additional CFLAGS here
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -g -fpermissive") # Add any additional CXXFLAGS here

# Define PLATFORM and PLATFORM_FLAVOR
set(PLATFORM "S32V234" CACHE STRING "Platform name. Supported platforms: S32V234, S32GEN1")
set(PLATFORM_FLAVOR "s32g2" CACHE STRING "Platform flavor. Supported flavors: s32g2, s32r45, s32g3")

# Validate PLATFORM
set(supported_platforms "S32V234;S32GEN1")
list(FIND supported_platforms "${PLATFORM}" platform_index)
if (platform_index EQUAL -1)
    message(FATAL_ERROR "Set PLATFORM variable to a supported platform: ${supported_platforms}")
endif()

# Validate PLATFORM_FLAVOR
set(supported_platform_flavors "s32g2;s32r45;s32g3")
list(FIND supported_platform_flavors "${PLATFORM_FLAVOR}" platform_flavor_index)
if (platform_flavor_index EQUAL -1)
    message(FATAL_ERROR "Set PLATFORM_FLAVOR variable to a supported flavor: ${supported_platform_flavors}")
endif()

# Define POLLING option
option(POLLING "Enable polling" OFF)
if(POLLING)
    add_compile_definitions(POLLING)
endif()

# Define libipc_dir

#include_directories(${CMAKE_SOURCE_DIR}/ipc-shm-us)
link_directories(${CMAKE_SOURCE_DIR}/ipc-shm-us)
set(libipc_dir "${CMAKE_CURRENT_SOURCE_DIR}/ipc-shm-us")

# Add include directories
include_directories(${libipc_dir}/common)
add_compile_definitions(CONFIG_SOC_${PLATFORM})

# Build the executable
set(elf_name greengrass_pubIPC.elf)
set(src_files
    ipcf.c
    ipcf_Ip_Cfg_${PLATFORM_FLAVOR}.c
    main.cpp
)
add_executable(${elf_name} ${src_files})

# Link against the required libraries

target_link_libraries(${elf_name}
    GreengrassIpc-cpp
    EventstreamRpc-cpp
    aws-crt-cpp 
    aws-c-common
    fmt
    ipc-shm
    pthread
    rt
)
