#!/bin/bash

echo "🚀 Starting MarketFish Simulation Engine..."

# 1. Start FastAPI Backend in the background
echo "Starting Backend (FastAPI on Port 8000)..."
python -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# 2. Start React Frontend
echo "Starting Frontend (React Vite)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "======================================================="
echo "✅ MarketFish is running!"
echo "👉 Backend API: http://localhost:8000"
echo "👉 Frontend Dashboard: http://localhost:5173"
echo "======================================================="
echo "Press Ctrl+C to stop both servers."

# Wait for user to press Ctrl+C
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
