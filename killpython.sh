#!/bin/bash

# Us this script to kill off python running Pixil. 
# usage: sudo ./killpython.sh

# Check if running as sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Kill all sudo processes running python
echo "Killing sudo python processes..."
pkill -9 -f "sudo.*python"

# Kill remaining python processes
echo "Killing remaining python processes..."
pkill -9 -f "python"

# Final check
echo "Checking for remaining processes..."
ps aux | grep "[p]ython"

if pgrep -f python > /dev/null; then
    echo "Warning: Some Python processes still remain."
    exit 1
else
    echo "All Python processes have been terminated."
    exit 0
fi
