@echo off
chcp 65001 >nul
echo ================================
echo  实验室追踪器 · 打包为 exe
echo ================================
echo.

:: 检查 pyinstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
)

echo 正在打包，请稍候...
echo.

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "LabTracker" ^
    --add-data "lab_tracker_app.py;." ^
    lab_tracker_app.py

echo.
if exist "dist\LabTracker.exe" (
    echo ✅ 打包成功！
    echo 文件位置：dist\LabTracker.exe
    echo.
    echo 直接双击运行即可，首次会弹出设置界面。
) else (
    echo ❌ 打包失败，请查看上方错误信息。
)

pause
