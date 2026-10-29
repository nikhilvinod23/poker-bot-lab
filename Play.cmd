@echo off
cd /d "%~dp0"
python -m pokerbot
if errorlevel 1 pause
