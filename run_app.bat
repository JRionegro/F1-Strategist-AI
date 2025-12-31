@echo off
:: F1 Strategist AI - Application Launcher
:: ========================================

echo.
echo ========================================
echo   F1 STRATEGIST AI - DASH APPLICATION
echo ========================================
echo.

:: Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] No virtual environment found, using system Python
)

:: Check if required packages are installed
echo [INFO] Checking dependencies...
python -c "import dash" 2>nul
if errorlevel 1 (
    echo [ERROR] Dash not installed. Installing requirements...
    pip install -r requirements.txt
)

:: Run the application
echo.
echo [INFO] Starting F1 Strategist AI Dashboard...
echo [INFO] Open your browser at: http://localhost:8501
echo [INFO] Press Ctrl+C to stop the server
echo.

python app_dash.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo [ERROR] Application crashed. Check the logs above.
    pause
)
