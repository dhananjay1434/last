#!/bin/bash

echo "========================================"
echo " Slide Extractor - Gradio Application"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed"
        echo "Please install Python 3.8 or higher"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "Python found:"
$PYTHON_CMD --version

echo
echo "Starting Slide Extractor Gradio Application..."
echo

# Run the startup script
$PYTHON_CMD start_gradio_app.py

echo
echo "Application has stopped."
read -p "Press Enter to continue..."
