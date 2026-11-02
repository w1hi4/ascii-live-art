@echo off
title ASCII.LIVE PRO - Instant Free Public Tunnel
echo ========================================================
echo     ASCII.LIVE PRO - Instant Free Public Tunnel
echo ========================================================
echo.
echo Make sure your server is running (start.bat)!
echo.
echo Connecting to free SSH tunnel (serveo.net) ...
echo This will give you an instant public HTTPS URL with:
echo - ZERO installation
echo - ZERO registration
echo - 100%% FREE OF COST
echo.
echo Press Ctrl+C at any time to stop the tunnel.
echo ========================================================
echo.
ssh -R 80:localhost:8080 serveo.net
pause

