#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e
set -x

COMPONENT_DIR=$(pwd)

# Check for the required arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <COMPONENT_NAME> <BINARY_PATH>"
    exit 1
fi

COMPONENT_NAME="$1"
BINARY_PATH="$2"

# Navigate to ros2 workspace
cd ~/ros2_ws/

# Run colcon build
source /opt/ros/galactic/setup.bash
source ./install/setup.bash
colcon build \
        --cmake-args \
          -DCMAKE_BUILD_TYPE=Release \
          -DFWE_STATIC_LINK=On \
          -DFWE_FEATURE_RICH_DATA=On \
          -DFWE_FEATURE_ROS2=On \
          -DFWE_FEATURE_GREENGRASSV2=On \
          -DBUILD_TESTING=Off 
# Navigate back to the parent directory
cd $COMPONENT_DIR

# Validate that the binary file exists
if [ ! -f "$BINARY_PATH" ]; then
    echo "Error: The specified binary file does not exist: $BINARY_PATH"
    exit 1
fi

# Copy only the specified binary to the target location
cp "$BINARY_PATH" "greengrass-build/artifacts/$COMPONENT_NAME/NEXT_PATCH/"

sed '/# FWE config goes here/{
    r /dev/stdin
    d
}' recipe.yaml < <(sed 's/^/      /' fwe-config.yaml) > recipe-fwe-config.yaml

# Copy recipe.yaml
cp recipe-fwe-config.yaml greengrass-build/recipes/recipe.yaml