@echo off
echo ========================================
echo Hyperliquid Trading Dashboard Docker
echo ========================================
echo.

:: Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please create .env file with your credentials.
    exit /b 1
)

:: Parse command
if "%1"=="" (
    set COMMAND=help
) else (
    set COMMAND=%1
)

if "%COMMAND%"=="build" (
    echo Building Docker images...
    docker-compose build
    echo.
    echo [OK] Images built successfully
    
) else if "%COMMAND%"=="up" (
    echo Starting all services...
    docker-compose up -d
    echo.
    echo [OK] Services started
    echo.
    echo View logs: docker-compose logs -f
    
) else if "%COMMAND%"=="down" (
    echo Stopping all services...
    docker-compose down
    echo.
    echo [OK] Services stopped
    
) else if "%COMMAND%"=="restart" (
    echo Restarting all services...
    docker-compose restart
    echo.
    echo [OK] Services restarted
    
) else if "%COMMAND%"=="logs" (
    if "%2"=="" (
        docker-compose logs -f
    ) else (
        docker-compose logs -f %2
    )
    
) else if "%COMMAND%"=="status" (
    echo Service Status:
    echo ----------------------------------------
    docker-compose ps
    
) else if "%COMMAND%"=="test" (
    echo Running tests in Docker...
    docker-compose run --rm indicators python test_paper_trading.py
    
) else if "%COMMAND%"=="shell" (
    if "%2"=="" (
        echo Entering indicators container...
        docker-compose exec indicators /bin/bash
    ) else (
        echo Entering %2 container...
        docker-compose exec %2 /bin/bash
    )
    
) else if "%COMMAND%"=="clean" (
    echo Cleaning up Docker resources...
    docker-compose down -v
    docker system prune -f
    echo.
    echo [OK] Cleanup complete
    
) else if "%COMMAND%"=="indicators-only" (
    echo Starting indicators service only...
    docker-compose up -d indicators
    echo.
    echo [OK] Indicators service started
    
) else if "%COMMAND%"=="trigger-only" (
    echo Starting trigger services only...
    docker-compose up -d trigger-analyzer trigger-streamer
    echo.
    echo [OK] Trigger services started
    
) else if "%COMMAND%"=="paper-only" (
    echo Starting paper trading only...
    docker-compose up -d paper-trader
    echo.
    echo [OK] Paper trading started
    
) else if "%COMMAND%"=="full" (
    echo Starting all services with supervisor...
    docker-compose --profile full up -d all-services
    echo.
    echo [OK] All-in-one service started
    
) else (
    echo Usage: docker-run.bat [command] [args]
    echo.
    echo Commands:
    echo   build           - Build all Docker images
    echo   up              - Start all services
    echo   down            - Stop all services
    echo   restart         - Restart all services
    echo   logs [service]  - View logs (all or specific service)
    echo   status          - Show service status
    echo   test            - Run tests in Docker
    echo   shell [service] - Enter container shell
    echo   clean           - Clean up Docker resources
    echo   indicators-only - Run only indicators service
    echo   trigger-only    - Run only trigger services
    echo   paper-only      - Run only paper trading
    echo   full            - Run all-in-one with supervisor
    echo.
    echo Services: indicators, trigger-analyzer, trigger-streamer, paper-trader
)