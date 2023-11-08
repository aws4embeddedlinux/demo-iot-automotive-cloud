#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e
set -x

# Check for the required arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <COMPONENT_NAME> <APP_PATH>"
    exit 1
fi

COMPONENT_NAME="$1"
APP_PATH="$2"


# Validate that the binary file exists
if [ ! -f "$APP_PATH" ]; then
    echo "Error: The specified binary file does not exist: $APP_PATH"
    exit 1
fi

# Copy only the specified binary to the target location
cp "$APP_PATH" "greengrass-build/artifacts/$COMPONENT_NAME/NEXT_PATCH/"

# Copy recipe.yaml
cp recipe.yaml greengrass-build/recipes/