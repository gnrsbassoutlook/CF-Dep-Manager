@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo    ComfyUI 依赖管理器 更新脚本
echo ==========================================

if not exist ".git" (
    echo ❌ 未检测到 Git 仓库，请先执行 push.bat 完成首次初始化
    pause
    exit /b 1
)

echo ⏳ 正在从 GitHub 拉取最新版本...
git pull origin main

if %errorlevel% equ 0 (
    echo.
    echo ✅ 更新完成！本地代码已是最新版本。
) else (
    echo.
    echo ❌ 更新失败，请检查网络或手动解决冲突。
)

echo.
pause
