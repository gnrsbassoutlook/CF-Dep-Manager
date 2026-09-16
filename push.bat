@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo ==========================================
echo    ComfyUI 依赖管理器 自动推送脚本
echo ==========================================

:: GitHub 仓库地址（HTTPS 方式，无需配置 SSH）
set REMOTE_URL=https://github.com/gnrsbassoutlook/ComfyUI-Dep-Manager.git

:: 检查是否已初始化 git
if not exist ".git" (
    echo 正在初始化 Git 仓库...
    git init
    git branch -M main
    git remote add origin %REMOTE_URL%
)

:: 校验远程地址
for /f "delims=" %%a in ('git remote get-url origin 2^>nul') do set CURRENT_URL=%%a
if "!CURRENT_URL!"=="" (
    git remote add origin %REMOTE_URL%
) else if NOT "!CURRENT_URL!"=="%REMOTE_URL%" (
    echo 更新远程仓库地址为: %REMOTE_URL%
    git remote set-url origin %REMOTE_URL%
)

echo.
echo 当前文件改动状态：
git status -s
set "STATUS_OUT="
for /f "delims=" %%i in ('git status -s') do set STATUS_OUT=%%i
echo.

:: 无改动直接退出
if "!STATUS_OUT!"=="" (
    echo ✅ 工作区无改动，无需提交推送。
    echo.
    pause >nul
    exit /b
)

:: 输入提交信息
set "msg="
set /p msg=👉 请输入 Commit 说明 (直接回车默认: 更新依赖管理器):
if "!msg!"=="" (
    for /f %%a in ('powershell Get-Date -Format "yyyy-MM-dd HH:mm:ss"') do set msg=更新依赖管理器: %%a
)

echo.
echo ⏳ 正在提交并推送到 GitHub...
git add .
git commit -m "!msg!" --allow-empty
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo 🎉 推送成功！代码已同步至 GitHub。
) else (
    echo.
    echo ⚠️ 推送遇到冲突，尝试拉取合并后重新推送...
    git pull origin main --rebase
    if %errorlevel% neq 0 (
        echo ❌ 合并失败，请手动解决冲突后再推送。
    ) else (
        git push -u origin main
    )
)

echo.
pause
endlocal
