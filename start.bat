@echo off
REM OmniMarket Intelligence Terminal - double-click launcher (Windows)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
