@echo off
echo ========================================
echo AUTOMATED TAKE PROFIT STRATEGY LAUNCHER
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing requirements...
    pip install hyperliquid-python-sdk pandas numpy matplotlib eth_account streamlit plotly
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Select an option:
echo 1. Run Strategy (Live Trading)
echo 2. Run Strategy (Dry Run - No Real Orders)
echo 3. Open Monitoring Dashboard
echo 4. View Backtest Results
echo 5. Edit Configuration
echo 6. Exit
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    echo.
    echo Starting LIVE trading strategy...
    echo WARNING: This will place real orders!
    echo Press Ctrl+C to stop at any time
    echo.
    pause
    python automated_tp_strategy.py
) else if "%choice%"=="2" (
    echo.
    echo Starting DRY RUN mode...
    echo No real orders will be placed
    echo.
    set DRY_RUN=true
    python automated_tp_strategy.py
) else if "%choice%"=="3" (
    echo.
    echo Opening monitoring dashboard...
    echo Dashboard will open in your browser
    echo.
    start streamlit run tp_strategy_monitor.py
) else if "%choice%"=="4" (
    echo.
    echo Running backtest analysis...
    python tp_strategy_simple.py
) else if "%choice%"=="5" (
    echo.
    echo Opening configuration file...
    notepad tp_strategy_config.json
) else if "%choice%"=="6" (
    echo.
    echo Exiting...
    exit
) else (
    echo Invalid choice!
    pause
    run_tp_strategy.bat
)

pause