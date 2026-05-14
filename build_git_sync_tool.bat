@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=runtime\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" scripts\build_git_sync_tool.py
if errorlevel 1 (
    echo.
    echo Build failed. Please run install_environment.bat first, then retry.
    pause
    exit /b 1
)

echo.
echo Git sync tool is ready:
echo dist\QuickGitSync.exe
pause
