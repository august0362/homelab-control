@echo off
rem Double-click: stop the dev servers started by start.bat.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
timeout /t 3 >nul
