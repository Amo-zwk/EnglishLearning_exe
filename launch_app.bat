@echo off
setlocal
cd /d "%~dp0"

set "RUNTIME_PY=%~dp0runtime\.venv\Scripts\python.exe"
if exist "%RUNTIME_PY%" (
    "%RUNTIME_PY%" scripts\launch_app.py
) else (
    echo Runtime environment was not found. Please run install_environment.bat first.
    python scripts\launch_app.py
)

if errorlevel 1 (
    echo.
    echo Launcher failed. Please check the message above.
)
pause
