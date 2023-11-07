cmake_minimum_required(VERSION 3.1)

project (greengrass_pubGGProc)

# this will enable sending of random generated data to iot core
OPTION(DEFINE_DEBUG "Debug flag if not working on target board")

IF(DEFINE_DEBUG)
    ADD_DEFINITIONS(-DDEBUG)
ENDIF(DEFINE_DEBUG)

file(GLOB MAIN_SRC
        "*.h"
        "*.cpp"
        )
add_executable(${PROJECT_NAME} ${MAIN_SRC})

set_target_properties(${PROJECT_NAME} PROPERTIES
        LINKER_LANGUAGE CXX
        CXX_STANDARD 11)

find_package(GreengrassIpc-cpp)
find_package(EventstreamRpc-cpp)
find_package(aws-crt-cpp)
find_package(aws-c-common)
find_package(fmt)

target_link_libraries(${PROJECT_NAME}
        GreengrassIpc-cpp
        EventstreamRpc-cpp
        aws-crt-cpp
        aws-c-common
        fmt
        pthread)