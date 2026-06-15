@echo off
chcp 65001 >nul
echo 停止 Agent Platform 服务...
taskkill /F /IM python.exe 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ 已停止
) else (
    echo - 无运行中的服务
)
