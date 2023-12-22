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

# Building ipc-shm lib with Make
cd ipc-shm-us
make IPC_UIO_MODULE_DIR="/lib/modules/5.15.85-rt55+g924dc871e528/extra"
cd ..

# Create 'build' directory and navigate into it
mkdir -p build
cd build

# Run cmake and make
cmake ..
make

# Navigate back to the parent directory
cd ..

# Validate that the binary file exists
if [ ! -f "$BINARY_PATH" ]; then
    echo "Error: The specified binary file does not exist: $BINARY_PATH"
    exit 1
fi

# Copy only the specified binary to the target location
cp "$BINARY_PATH" "greengrass-build/artifacts/$COMPONENT_NAME/NEXT_PATCH/"

# Copy recipe.yaml
cp recipe.yaml greengrass-build/recipes/
