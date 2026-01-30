@echo off
echo ============================================================
echo HYPERLIQUID MCP SERVERS LAUNCHER
echo ============================================================
echo.

echo Checking Python virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python setup_python_only.py
    pause
    exit /b 1
)

echo.
echo Starting MCP servers...
echo.

REM Start Mock Server (for testing without API keys)
echo Starting Mock Server on port 8888...
start "Mock MCP Server" cmd /k "venv\Scripts\python.exe start_mock_server.py"
timeout /t 2 >nul

REM Start Python MCP Server
echo Starting Python MCP Server on port 8001...
start "Python MCP Server" cmd /k "venv\Scripts\python.exe python_mcp_server.py"
timeout /t 2 >nul

REM Start JavaScript servers (if npm is available)
where npm >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Starting JavaScript servers...
    
    if exist "javascript\mektigboy\index.js" (
        echo Starting Mektigboy server on port 8004...
        start "JS Mektigboy MCP" cmd /k "cd javascript\mektigboy && npm start"
        timeout /t 2 >nul
    )
    
    if exist "javascript\tradingbalthazar\index.js" (
        echo Starting TradingBalthazar server on port 8005...
        start "JS Balthazar MCP" cmd /k "cd javascript\tradingbalthazar && npm start"
        timeout /t 2 >nul
    )
) else (
    echo [WARNING] npm not found - skipping JavaScript servers
)

echo.
echo ============================================================
echo SERVERS STARTING...
echo ============================================================
echo.
echo Available servers:
echo   Mock Server:    http://localhost:8888 (no API key needed)
echo   Python MCP:     http://localhost:8001 (requires API key)
echo   JS Mektigboy:   http://localhost:8004 (if npm available)
echo   JS Balthazar:   http://localhost:8005 (if npm available)
echo.
echo To test servers, run in another terminal:
echo   venv\Scripts\python.exe test_all_servers.py
echo.
echo To stop servers, close the command windows.
echo.
pause