@echo off
cd /d "%~dp0"
echo Setting up the evening check (every day at 6 pm)...
powershell -ExecutionPolicy Bypass -File setup_daily_run.ps1
echo.
echo Done. Every evening the report is saved to Google Drive, folder "Tailwind Picks".
echo Open it in the Google Drive app on your phone.
pause
