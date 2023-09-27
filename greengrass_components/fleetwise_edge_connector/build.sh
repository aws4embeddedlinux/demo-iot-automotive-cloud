#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e
set -x

# Check for the required arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <COMPONENT_NAME> <BINARY_PATH>"
    exit 1
fi

COMPONENT_NAME="$1"
BINARY_PATH="$2"

# Create 'build' directory and navigate into it
cd aws-iot-fleetwise-edge
mkdir -p build
cd build

# Run cmake and make
cmake -DCMAKE_BUILD_TYPE=Release -DFWE_STATIC_LINK=On -DBUILD_TESTING=Off -DFWE_FEATURE_GREENGRASSV2=On -DCMAKE_TOOLCHAIN_FILE=/usr/local/aarch64-linux-gnu/lib/cmake/arm64-toolchain.cmake ..
make -j`nproc`

# Navigate back to the parent directory
cd ../../

# Validate that the binary file exists
if [ ! -f "$BINARY_PATH" ]; then
    echo "Error: The specified binary file does not exist: $BINARY_PATH"
    exit 1
fi

# Copy only the specified binary to the target location
cp "$BINARY_PATH" "greengrass-build/artifacts/$COMPONENT_NAME/NEXT_PATCH/"

# Copy recipe.yaml
cp recipe.yaml greengrass-build/recipes/