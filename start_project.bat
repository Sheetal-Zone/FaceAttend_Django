@echo off
echo ========================================
echo Face Attendance System - Startup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo Python found. Starting backend...
echo.

REM Start backend
cd backend
python start_backend.py

echo.
echo Backend started successfully!
echo You can access the application at: http://localhost:8000
echo.
echo Admin credentials:
echo Username: admin
echo Password: admin123
echo.
pause
