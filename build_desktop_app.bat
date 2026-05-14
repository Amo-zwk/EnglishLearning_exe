@echo off
setlocal
cd /d "%~dp0"

set "RUNTIME_PY=%~dp0runtime\.venv\Scripts\python.exe"
if not exist "%RUNTIME_PY%" (
    py -3.12 scripts\install_environment.py
)

if not exist "%RUNTIME_PY%" (
    echo Runtime Python was not created.
    pause
    exit /b 1
)

"%RUNTIME_PY%" -m pip install pyinstaller
if errorlevel 1 (
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

"%RUNTIME_PY%" scripts\install_environment.py
if errorlevel 1 (
    echo Failed to install runtime dependencies.
    pause
    exit /b 1
)

"%RUNTIME_PY%" scripts\build_desktop_app.py
if errorlevel 1 (
    echo Desktop build failed.
    pause
    exit /b 1
)

pause
