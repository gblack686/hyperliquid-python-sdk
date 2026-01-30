@echo off
echo ======================================
echo Starting Hyperliquid Trading Dashboard
echo ======================================
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found, using system Python
)

echo.
echo Starting Streamlit dashboard on port 8501...
echo Dashboard will open at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the dashboard
echo ======================================
echo.

streamlit run app.py --server.port 8501 --server.address localhost

pause
