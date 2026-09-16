@echo off
chcp 65001 >nul
setlocal

set "PYTHON_DIR=E:\ComfyUI\python"
set "SCRIPT_FILE=%~dp0comfyui_dep_manager.py"

if not exist "%PYTHON_DIR%\python.exe" (
    echo [ERROR] Python not found: %PYTHON_DIR%\python.exe
    echo Please edit this bat file and set correct PYTHON_DIR
    pause
    exit /b 1
)

if not exist "%SCRIPT_FILE%" (
    echo [ERROR] Script not found: %SCRIPT_FILE%
    echo Please keep launch.bat and comfyui_dep_manager.py in the same folder
    pause
    exit /b 1
)

echo ==============================================
echo    ComfyUI Dep Manager
echo    URL: http://127.0.0.1:8186
echo    Close this window to stop service
echo ==============================================
echo.

"%PYTHON_DIR%\python.exe" "%SCRIPT_FILE%"

pause
