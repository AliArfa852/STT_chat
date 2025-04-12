@echo off
:: Launcher for STT System Tray application
:: Save as start_stt_tray.bat

:: Change to script directory
cd /d %~dp0

:: Start the STT tray icon application (hidden)
start /min python stt_tray.py

echo Speech-to-Text tray icon launched.
echo You should see an icon in the system tray.
echo Right-click the icon to access controls.

timeout /t 5