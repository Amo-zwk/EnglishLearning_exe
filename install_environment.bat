@echo off
setlocal
cd /d "%~dp0"

py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if %errorlevel%==0 (
    py -3.12 scripts\install_environment.py
) else (
    python scripts\install_environment.py
)

if errorlevel 1 (
    echo.
    echo Installation failed. Please check the message above.
)
pause
