@echo off
echo =======================================================
echo    Banking Sector Stock Intelligence - Daily Sync
echo =======================================================
echo.
echo Starting the Data Engineering Pipeline...
echo This will fetch new market data and sync to AWS S3.
echo.

:: Change to the directory where the batch file is located
cd /d "%~dp0"

:: Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .venv!
    echo Please ensure the project dependencies are installed.
    pause
    exit /b 1
)

:: Run the pipeline using the virtual environment's Python
call .venv\Scripts\python main.py

echo.
echo =======================================================
echo    Pipeline execution finished.
echo    You can now refresh Power BI to see the latest data.
echo =======================================================
echo.
pause
