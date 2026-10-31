@echo off
rem Double-click: start backend + frontend (dev) and open the UI.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1"
if errorlevel 1 (
    pause
    exit /b 1
)
timeout /t 4 /nobreak >nul
start "" http://localhost:5173
