#!/bin/bash

# Casino Slot Quick Start Script

echo "🎰 Casino Slot Machine - Quick Start"
echo "===================================="
echo ""

# Check if in correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the casino-slot directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
python3 -m pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo ""

# Start backend server in background
echo "🚀 Starting backend API server..."
python3 app.py &
BACKEND_PID=$!
echo "✓ Backend running (PID: $BACKEND_PID)"
echo ""

# Wait for backend to start
sleep 2

# Check if backend is running
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✓ Backend API is ready at http://localhost:5000"
else
    echo "⚠️  Backend may still be starting..."
fi
echo ""

# Start frontend
cd ../frontend
echo "🌐 Starting frontend server..."
echo "📱 Opening browser at http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start simple HTTP server
python3 -m http.server 8000

# Cleanup on exit
echo ""
echo "🛑 Shutting down..."
kill $BACKEND_PID 2>/dev/null
echo "✓ Servers stopped"
