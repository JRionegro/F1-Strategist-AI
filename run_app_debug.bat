@echo off
:: F1 Strategist AI - Debug Mode Launcher
:: ======================================

echo.
echo ========================================
echo   F1 STRATEGIST AI - DEBUG MODE
echo ========================================
echo.

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Set debug environment variables
set DASH_DEBUG=true
set FLASK_ENV=development

echo [INFO] Debug mode enabled
echo [INFO] Hot reload is active - changes will auto-refresh
echo [INFO] Open your browser at: http://localhost:8501
echo.

python app_dash.py

pause
