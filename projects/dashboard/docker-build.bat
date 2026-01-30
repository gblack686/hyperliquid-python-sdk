@echo off
echo ========================================
echo Building CVD Docker Containers
echo ========================================
echo.

echo [1] Building CVD Calculator image...
docker build -t cvd-calculator:latest -f Dockerfile .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build CVD Calculator
    exit /b 1
)

echo.
echo [2] Building Monitor Server image...
docker build -t cvd-monitor:latest -f Dockerfile.monitor .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build Monitor Server
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo To run with docker-compose:
echo   docker-compose up -d
echo.
echo To view logs:
echo   docker-compose logs -f
echo ========================================