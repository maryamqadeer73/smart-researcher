@echo off
title Smart Researcher — AI Content Intelligence
color 0A
echo.
echo  ============================================
echo    SMART RESEARCHER — AI Content Intelligence
echo  ============================================
echo.
echo  Installing required packages...
pip install requests beautifulsoup4 feedparser flask flask-cors python-dotenv --quiet
echo.
echo  Starting server on http://localhost:5001
echo  Your browser will open automatically.
echo.
echo  HOW TO STOP: Press Ctrl+C in this window
echo  ============================================
echo.

REM Start server in background and wait
cd backend
start /min python server.py
timeout /t 3 /nobreak >nul
start http://localhost:5001

echo  Browser opened! If it didn't open, visit:
echo  http://localhost:5001
echo.
python server.py
pause
