@echo off
REM Fake News Detector Backend Startup Script

echo.
echo ======================================
echo Fake News Detector - Backend Startup
echo ======================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please create a .env file with: HF_TOKEN=your_token
    pause
    exit /b 1
)

echo Checking dependencies...
pip list | find "fastapi" > nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo Dependencies already installed.
)

echo.
echo Starting FastAPI server...
echo Server will be available at: http://127.0.0.1:8000
echo.
echo Press CTRL+C to stop the server
echo.

uvicorn main:app --reload

pause
