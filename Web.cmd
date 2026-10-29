@echo off
cd /d "%~dp0"
echo Open http://127.0.0.1:8000 in your browser.
python -m uvicorn pokerbot.web:app --host 127.0.0.1 --port 8000
if errorlevel 1 pause
