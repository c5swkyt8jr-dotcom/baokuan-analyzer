@echo off
echo ========================================
echo   爆款拆解机 - 启动服务器
echo ========================================
echo.

cd /d "%~dp0backend"

REM Activate venv and install deps if needed
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Installing dependencies...
venv\Scripts\python.exe -m pip install -q -r requirements.txt

echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop
echo.

venv\Scripts\python.exe main.py
