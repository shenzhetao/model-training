@echo off
REM 一键启动 YOLO 采集脚本（自动用 venv）
setlocal
set "PROJECT_ROOT=%~dp0.."
set "VENV_PY=%PROJECT_ROOT%\..\game-helper\venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [错误] 找不到 venv: %VENV_PY%
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
"%VENV_PY%" scripts\collect_for_yolo.py
endlocal
