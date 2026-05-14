@echo off
setlocal
cd /d "%~dp0"

set "RUNTIME_PY=%~dp0runtime\.venv\Scripts\python.exe"
if exist "%RUNTIME_PY%" (
    "%RUNTIME_PY%" scripts\configure_environment.py
) else (
    echo Runtime environment was not found. Falling back to system Python.
    python scripts\configure_environment.py
)

if errorlevel 1 (
    echo.
    echo Configuration failed. Please check the message above.
)
pause
