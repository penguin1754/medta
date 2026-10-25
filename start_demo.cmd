@echo off
cd /d "%~dp0"
echo Starting MedTA backend on http://127.0.0.1:8787 ...
start "MedTA backend" /min python backend\app.py --port 8787
ping -n 3 127.0.0.1 >nul
start "" http://127.0.0.1:8787
echo.
echo Page should open in your browser now.
echo To stop the service, close the minimized window titled "MedTA backend".
