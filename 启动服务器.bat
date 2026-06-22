@echo off
chcp 65001 >nul
title 爆款拆解机 - 服务器运行中（关闭此窗口即停止服务）

cd /d "%~dp0backend"

:: Check if venv exists, if not create it
if not exist "venv\Scripts\python.exe" (
    echo [信息] 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败！请确认 Python 已安装。
        pause
        exit /b 1
    )
)

:: Install/update dependencies
echo [信息] 正在检查依赖...
venv\Scripts\python.exe -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [警告] 依赖安装有问题，尝试继续...
)

echo.
echo ============================================
echo   爆款拆解机 v1.0
echo ============================================
echo.
echo   服务地址: http://127.0.0.1:8000
echo   前端页面: http://127.0.0.1:8000/static/index.html
echo.
echo   ★ 请勿关闭此窗口，关闭即停止服务 ★
echo ============================================
echo.

venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info

echo.
echo ============================================
echo   服务器已停止
echo ============================================
pause
