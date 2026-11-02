@echo off
title ASCII.LIVE PRO - Server
echo ========================================================
echo        ASCII.LIVE PRO - Terminal Animation Studio
echo ========================================================
echo.
echo Starting server on http://localhost:8080 ...
echo.
python "%~dp0server.py" 8080
pause

