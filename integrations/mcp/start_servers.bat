@echo off
echo ============================================================
echo Hyperliquid MCP Servers Launcher
echo ============================================================
echo.

echo Starting servers...
echo.

REM Start Mock Server (for testing)
start "Mock MCP Server" cmd /k "venv\Scripts\python.exe start_mock_server.py"
timeout /t 2 >nul

REM Start Python MCP Server
start "Python MCP Server" cmd /k "venv\Scripts\python.exe python_mcp_server.py"
timeout /t 2 >nul

echo.
echo Servers are starting...
echo.
echo Available servers:
echo   Mock Server: http://localhost:8888 (for testing without API keys)
echo   Python MCP: http://localhost:8001 (requires API keys in .env)
echo.
echo To test the servers, run:
echo   venv\Scripts\python.exe test_mcp_client.py
echo.
pause
