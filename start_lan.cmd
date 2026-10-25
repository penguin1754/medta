@echo off
cd /d "%~dp0"
title MedTA 局域网模式
python tools\start_lan.py %*
pause
