#!/usr/bin/env bash

# Blender paths
BLENDER_EXE="/c/Program Files/Blender Foundation/Blender 5.0/Blender.exe"
BLENDER_PYTHON="/c/Program Files/Blender Foundation/Blender 5.0/5.0/python/bin/python.exe"

# Define a shell function instead of alias
blender() {
    "$BLENDER_EXE" "$@"
}


# Export python path
export BLENDER_PYTHON

echo "Local dev environment ready. Use 'blender' to launch Blender."
echo "BLENDER_PYTHON=$BLENDER_PYTHON"