@echo off
echo ========================================
echo  Slide Extractor - Gradio Application
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo Python found: 
python --version

echo.
echo Starting Slide Extractor Gradio Application...
echo.

REM Run the startup script
python start_gradio_app.py

echo.
echo Application has stopped.
pause
