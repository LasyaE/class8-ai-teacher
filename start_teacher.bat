@echo off
cd /d C:\Projects\class8-ai-teacher

echo =====================================
echo Starting Class 8 AI Teacher
echo =====================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m flask --app webapp.app run --host 127.0.0.1 --port 5000

echo.
echo Application stopped.
pause
