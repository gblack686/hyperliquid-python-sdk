@echo off
echo ========================================
echo Starting CVD System
echo ========================================
echo.

echo [1] Starting CVD Calculator with Supabase...
start "CVD Calculator" cmd /k python cvd_supabase_integration.py

timeout /t 3 /nobreak > nul

echo [2] Starting Monitor Server...
start "CVD Monitor" cmd /k python cvd_monitor_server.py

timeout /t 2 /nobreak > nul

echo.
echo ========================================
echo CVD System Running!
echo ========================================
echo.
echo Dashboard: http://localhost:8001
echo API Docs:  http://localhost:8001/docs
echo.
echo Press Ctrl+C in each window to stop
echo ========================================
pause