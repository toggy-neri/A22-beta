@echo off
chcp 65001 >nul
echo ============================================================
echo 停止所有数字人服务
echo ============================================================
echo.

echo 正在查找并停止 Python 进程...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *app.py*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *start_all*" 2>nul

echo.
echo 服务已停止
pause
