@echo off
REM ============================================================
REM GameAssistant 启动脚本（Windows）
REM 双击运行：自动激活 venv → 进入项目目录
REM ============================================================

setlocal

REM 推断项目根目录（脚本所在目录）
set "PROJECT_ROOT=%~dp0"
set "VENV_DIR=%PROJECT_ROOT%..\game-helper\venv"

echo ============================================
echo  GameAssistant 启动器
echo  项目根目录: %PROJECT_ROOT%
echo  venv 路径:   %VENV_DIR%
echo ============================================

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [错误] 找不到 venv: %VENV_DIR%
    echo 请先创建虚拟环境并安装依赖。
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"
cd /d "%PROJECT_ROOT%"

echo.
echo venv 已激活。可用命令：
echo   python scripts\collect_for_yolo.py    采集数据
echo   python scripts\split_dataset.py        划分数据集
echo   python ml\training_scripts\train_yolo.py   训练模型
echo   python ml\training_scripts\yolo_detector.py   测试推理
echo.

cmd /k
