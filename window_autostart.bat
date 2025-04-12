@echo off
:: Windows Startup Script for Speech-to-Text Background Service
:: Save as stt_autostart.bat

:: Change to script directory
cd /d %~dp0

:: Start the STT service in background
start /min pythonw voice_activated.py

echo Speech-to-Text service started in background.
timeout /t 5