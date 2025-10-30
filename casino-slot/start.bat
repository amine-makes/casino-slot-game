@echo off
REM Casino Slot Quick Start Script for Windows

echo 🎰 Casino Slot Machine - Quick Start
echo ====================================
echo.

REM Check if in correct directory
if not exist "backend" (
    echo ❌ Error: Please run this script from the casino-slot directory
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed
    exit /b 1
)

echo ✓ Python found
echo.

REM Install backend dependencies
echo 📦 Installing backend dependencies...
cd backend
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)
echo ✓ Dependencies installed
echo.

REM Start backend server
echo 🚀 Starting backend API server...
start /B python app.py
timeout /t 3 /nobreak >nul
echo ✓ Backend running at http://localhost:5000
echo.

REM Start frontend
cd ..\frontend
echo 🌐 Starting frontend server...
echo 📱 Open browser at http://localhost:8000
echo.
echo Press Ctrl+C to stop servers
echo.

REM Start simple HTTP server
python -m http.server 8000
