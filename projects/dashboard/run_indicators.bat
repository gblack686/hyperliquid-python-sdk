@echo off
echo ========================================
echo Starting Indicator Manager
echo ========================================
echo.

REM Start the indicator manager
python indicator_manager.py --symbols BTC ETH SOL HYPE --indicators open_interest funding_rate

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo Error occurred! Check logs above.
    echo ========================================
    pause
)