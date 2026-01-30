@echo off
echo ========================================
echo  HYPERLIQUID CHARTS DASHBOARD LAUNCHER
echo ========================================
echo.
echo Starting services...
echo.

REM Start indicator manager with CVD
echo [1/2] Starting Indicator Manager with CVD...
start "Indicator Manager" cmd /k python indicator_manager.py --symbols BTC ETH SOL HYPE --indicators cvd open_interest funding_rate vwap bollinger volume_profile

REM Wait a bit for indicators to initialize
timeout /t 3 /nobreak >nul

REM Start Charts Dashboard
echo [2/2] Starting Charts Dashboard...
start "Charts Dashboard" cmd /k python -m streamlit run app_charts.py --server.port 8503 --server.headless true

echo.
echo ========================================
echo  SERVICES LAUNCHED SUCCESSFULLY!
echo ========================================
echo.
echo Access Points:
echo - Charts Dashboard: http://localhost:8503
echo - Simplified Dashboard: http://localhost:8502
echo - Enhanced Dashboard: http://localhost:8501
echo.
echo CVD indicator is now integrated into the main system.
echo.
echo Press any key to exit this window...
pause >nul