@echo off
echo ==========================================
echo Starting Both HYPE Trading Systems
echo ==========================================
echo.
echo 1. Confluence Dashboard (Already Running)
echo    - URL: http://localhost:8501
echo    - Paper Trading: Active
echo    - Docker Containers: Running
echo.
echo 2. Starting Mean Reversion System...
echo.

REM Change to Mean Reversion directory
cd hype-trading-system

REM Start Mean Reversion in dry-run mode in new window
start "HYPE Mean Reversion System" cmd /k "python start.py --mode dry_run"

echo.
echo ==========================================
echo Both Systems Starting!
echo ==========================================
echo.
echo Confluence Dashboard: http://localhost:8501
echo Mean Reversion: Check new window
echo.
echo Press any key to open monitoring dashboard...
pause

REM Open the dashboard in browser
start http://localhost:8501

echo.
echo Systems are running!
echo Close this window when done.
pause