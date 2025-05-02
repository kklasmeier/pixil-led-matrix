#!/bin/bash

# Use this script to kill off python running Pixil, including nohup processes
# Usage: sudo ./killpython.sh

# Check if running as sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

echo "Searching for Python processes..."
# Find all Python processes first and display them
ps aux | grep python | grep -v grep

echo ""
echo "Killing Python processes related to Pixil..."
# First try the specific Pixil pattern
pkill -9 -f "python.*Pixil\.py"

echo "Killing any sudo python processes..."
# Kill sudo python processes if any remain
pkill -9 -f "sudo.*python"

echo "Killing any remaining python processes..."
# Last resort - kill all remaining python processes
pkill -9 python

echo ""
echo "Checking for remaining processes..."
REMAINING=$(ps aux | grep python | grep -v grep)

if [ -n "$REMAINING" ]; then
    echo "Some Python processes still remain:"
    echo "$REMAINING"
    
    echo ""
    echo "Attempting to kill by PID directly..."
    # Extract and kill PIDs directly
    ps aux | grep python | grep -v grep | awk '{print $2}' | xargs -r sudo kill -9
    
    # Final check
    FINAL_CHECK=$(ps aux | grep python | grep -v grep)
    if [ -n "$FINAL_CHECK" ]; then
        echo "Warning: Some Python processes still remain after direct PID kill attempt:"
        echo "$FINAL_CHECK"
        exit 1
    else
        echo "All Python processes have been terminated."
    fi
else
    echo "All Python processes have been terminated."
fi

exit 0