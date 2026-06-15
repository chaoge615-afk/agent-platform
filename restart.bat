@echo off
chcp 65001 >nul
echo ============================================================
echo Agent Platform - 重启脚本
echo ============================================================
echo.

echo [1/5] 停止现有服务...
taskkill /F /IM python.exe 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       ✓ 已停止 Python 进程
) else (
    echo       - 无运行中的 Python 进程
)
echo.

echo [2/5] 清理缓存...
if exist "src\__pycache__" (
    rmdir /S /Q "src\__pycache__"
    echo       ✓ 已清理 src/__pycache__
)
if exist "src\agent\__pycache__" (
    rmdir /S /Q "src\agent\__pycache__"
    echo       ✓ 已清理 src/agent/__pycache__
)
echo.

echo [3/5] 启动服务器...
start /B venv\Scripts\python.exe -m src.main > server.log 2>&1
echo       ✓ 服务器启动中...
echo.

echo [4/5] 等待服务就绪...
timeout /t 3 /nobreak >nul

:check_health
curl -s http://localhost:8001/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       - 等待中...
    timeout /t 2 /nobreak >nul
    goto check_health
)

echo       ✓ 服务已就绪
echo.

echo [5/5] 服务状态
echo ============================================================
curl -s http://localhost:8001/health | venv\Scripts\python.exe -m json.tool
echo.

echo ============================================================
echo ✓ 重启完成！
echo.
echo 访问地址：
echo   - API 文档：http://localhost:8001/docs
echo   - 健康检查：http://localhost:8001/health
echo   - 对话接口：http://localhost:8001/api/chat
echo.
echo 测试命令：
echo   venv\Scripts\python.exe test_api.py
echo   venv\Scripts\python.exe test_multiturn.py
echo ============================================================
pause
