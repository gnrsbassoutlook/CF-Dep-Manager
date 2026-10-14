@echo off
chcp 65001 >nul
setlocal

set "PORT=8186"
set "PYTHON_DIR=E:\ComfyUI\python"
set "SCRIPT_FILE=%~dp0CF-Dep-Manager.py"

if not exist "%PYTHON_DIR%\python.exe" (
    echo [ERROR] Python not found: %PYTHON_DIR%\python.exe
    echo Please edit this bat file and set correct PYTHON_DIR
    pause
    exit /b 1
)

if not exist "%SCRIPT_FILE%" (
    echo [ERROR] Script not found: %SCRIPT_FILE%
    echo Please keep launch_cdm.bat and CF-Dep-Manager.py in the same folder
    pause
    exit /b 1
)

echo ==============================================
echo    CF-Dep-Manager 启动中
echo    URL: http://127.0.0.1:%PORT%
echo    关闭此窗口即可停止服务
echo ==============================================
echo.

"%PYTHON_DIR%\python.exe" "%SCRIPT_FILE%" --port %PORT%

pause