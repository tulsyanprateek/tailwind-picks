@echo off
cd /d "%~dp0"
echo.
echo Step 1 of 2: connect your phone (Telegram)
echo In Telegram, message @BotFather, send /newbot, and copy the token it gives you.
echo.
.venv\Scripts\python telegram_setup.py
echo.
echo Step 2 of 2: run the check every evening at 6 pm
powershell -ExecutionPolicy Bypass -File setup_daily_run.ps1
echo.
echo All done. You will get a message on your phone every evening.
pause
