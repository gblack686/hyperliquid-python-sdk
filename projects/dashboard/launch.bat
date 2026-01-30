@echo off
echo ============================================
echo  Hyperliquid Trading Dashboard Launcher
echo ============================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import streamlit, pandas, plotly, supabase, quantpylib" 2>nul
if errorlevel 1 (
    echo Installing missing dependencies...
    pip install -r requirements.txt
    pip install matplotlib beautifulsoup4 lxml seaborn statsmodels pyyaml scikit-learn setuptools msgpack orjson numba
)

echo.
echo Starting Hyperliquid Trading Dashboard...
echo.
echo Dashboard will open at: http://localhost:8501
echo Press Ctrl+C to stop the server
echo.

REM Run the Streamlit app
python -m streamlit run app.py

pause