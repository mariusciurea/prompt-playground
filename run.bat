@echo off
REM AI Playground Startup Script for Windows
REM This script sets up and launches the Streamlit application

echo.
echo ========================================
echo   AI Playground - Starting Application
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

REM Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip is not installed
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)

REM Check and install dependencies
echo Checking dependencies...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo Dependencies already installed
)

echo.
echo ========================================
echo   Launching AI Playground...
echo   URL: http://localhost:8501
echo   Press Ctrl+C to stop
echo ========================================
echo.

REM Run the Streamlit app
streamlit run app.py

pause
