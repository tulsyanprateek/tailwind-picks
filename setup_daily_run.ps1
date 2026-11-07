# Registers a Windows scheduled task that runs scan.py every evening at 6:00 pm.
# If the computer is off at 6 pm, it runs as soon as the computer is next on.
# Run once:      powershell -ExecutionPolicy Bypass -File setup_daily_run.ps1
# To remove it:  Unregister-ScheduledTask -TaskName "Stock Screener daily" -Confirm:$false

$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $project ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Error "Python environment not found at $python. See README, Setup."; exit 1 }

$action = New-ScheduledTaskAction -Execute $python -Argument "scan.py" -WorkingDirectory $project
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00pm
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "Stock Screener daily" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Runs the stock screener check every evening" -Force | Out-Null
Write-Output "Scheduled: scan.py runs every day at 6:00 pm (or when the computer is next on)."
