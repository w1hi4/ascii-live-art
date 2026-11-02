@echo off
title ASCII.LIVE PRO - Docker Launcher
echo ========================================================
echo        ASCII.LIVE PRO - Docker Container Runner
echo ========================================================
echo.
echo Starting container via Docker Compose...
docker compose up -d
echo.
echo Container is running!
echo  -> Web Studio: http://localhost:8090/
echo  -> Stream in Terminal: curl -s http://localhost:8090/ciarl
echo.
pause

