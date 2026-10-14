@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title CF-Dep-Manager 自动更新脚本

:: 切换到当前批处理文件所在目录
cd /d "%~dp0"

:: 与启动脚本保持一致的 Python 目录配置
set "PYTHON_DIR=E:\ComfyUI\python"

echo ==============================================
echo    CF-Dep-Manager GitHub 自动更新脚本
echo ==============================================

:: 1. 检查 Git 环境
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 未检测到 Git 命令，请确保已安装 Git 并配置了系统环境变量！
    echo.
    pause
    exit /b 1
)

:: 2. 检查是否为 Git 仓库
if not exist ".git" (
    echo.
    echo [ERROR] 当前目录尚未关联 Git 仓库，请确保是通过 git clone 下载的项目。
    echo.
    pause
    exit /b 1
)

:: 3. 获取当前分支
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
if "%BRANCH%"=="" set "BRANCH=main"

echo.
echo [*] 正在检查远程仓库是否有新版本...
git fetch origin %BRANCH% >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 连接远程仓库失败，请检查网络或 GitHub 访问情况！
    echo.
    pause
    exit /b 1
)

:: 4. 获取本地与远程最新 Commit
for /f "delims=" %%l in ('git rev-parse HEAD 2^>nul') do set "LOCAL_HASH=%%l"
for /f "delims=" %%r in ('git rev-parse origin/%BRANCH% 2^>nul') do set "REMOTE_HASH=%%r"

set "LOCAL_SHORT=%LOCAL_HASH:~0,7%"
set "REMOTE_SHORT=%REMOTE_HASH:~0,7%"

echo 当前分支: %BRANCH%
echo 本地版本: %LOCAL_SHORT%
echo 远程最新: %REMOTE_SHORT%

:: 5. 判断是否已是最新
if "%LOCAL_HASH%"=="%REMOTE_HASH%" (
    echo.
    echo ==============================================
    echo [OK] 代码已是最新版本，无需重复拉取！
    echo ==============================================
    echo.
    echo 按任意键退出窗口...
    pause >nul
    exit /b 0
)

:: 6. 列出待更新的 Commit
echo.
echo ==================== 待更新的提交记录 ====================
git log --pretty=format:"%%h | %%ad | %%s" --date=short HEAD..origin/%BRANCH%
echo.
echo ==========================================================
echo.
echo [*] 检测到远程有新版本更新！

:: 7. 检查本地是否有未提交的修改（如刚才修改的端口配置）
set "HAS_MODIFIED=0"
for /f "delims=" %%m in ('git status --porcelain 2^>nul') do set "HAS_MODIFIED=1"

if "%HAS_MODIFIED%"=="1" (
    echo [!] 检测到本地文件有改动（可能是自定义端口或脚本改动）。
    echo     为了防止更新失败，脚本将在拉取前自动暂存本地改动。
    echo.
    echo [*] 正在暂存本地修改...
    git stash push -u -m "cdm-autostash" >nul 2>&1
)

echo 请按任意键确认，开始拉取并合并最新代码...
pause >nul

echo.
echo [*] 正在拉取远程最新代码...
git pull origin %BRANCH%
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 更新失败！如果提示冲突，建议手动备份端口后执行: git reset --hard origin/%BRANCH%
    echo.
    pause
    exit /b 1
)

:: 8. 恢复之前修改的本地端口配置
if "%HAS_MODIFIED%"=="1" (
    echo.
    echo [*] 正在尝试恢复你的本地配置与端口...
    git stash pop >nul 2>&1
)

echo.
echo [OK] 更新成功！当前已是最新版本 (%REMOTE_SHORT%)。

:: 9. 检查并更新依赖包（优先使用 ComfyUI 的独立 Python 环境）
if exist "requirements.txt" (
    echo.
    echo [*] 正在检查并更新依赖包...

    if exist "%PYTHON_DIR%\python.exe" (
        "%PYTHON_DIR%\python.exe" -m pip install -r requirements.txt -q
    ) else if exist "venv\Scripts\pip.exe" (
        venv\Scripts\pip.exe install -r requirements.txt -q
    ) else if exist ".venv\Scripts\pip.exe" (
        .venv\Scripts\pip.exe install -r requirements.txt -q
    ) else (
        python -m pip install -r requirements.txt -q
    )
    echo [*] 依赖检查完成！
)

echo.
echo ==============================================
echo    更新完毕，请双击运行 launch_cdm.bat 启动
echo ==============================================
echo 按任意键退出窗口...
pause >nul
exit /b 0