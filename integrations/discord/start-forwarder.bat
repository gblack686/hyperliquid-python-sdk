@echo off
echo ========================================
echo Discord Multi-Channel Forwarder
echo ========================================
echo.
echo Monitoring 5 channels every 10 minutes:
echo   - 1193836001827770389 (columbus-trades)
echo   - 1259544407288578058 (sea-scalper-farouk)
echo   - 1379129142393700492 (quant-flow)
echo   - 1259479627076862075 (josh-the-navigator)
echo   - 1176852425534099548 (crypto-chat)
echo.
echo Forwarding to: 1408521881480462529
echo.
echo Press Ctrl+C to stop the forwarder
echo ========================================
echo.

set POLL_INTERVAL=600000
set TARGET_CHANNEL_ID=1408521881480462529
node multi-channel-forwarder.js