#!/bin/bash


# Default command
cmd="echo Hello, world!"

# Check for user input via environment variable
if [ -n "$CUSTOM_CMD" ]; then
  cmd=$CUSTOM_CMD
fi
# Execute the command
eval $cmd