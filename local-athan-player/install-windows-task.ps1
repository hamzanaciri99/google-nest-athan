<#
Registers a Scheduled Task that runs athan_player.py at startup (under the
SYSTEM account, so it doesn't need anyone logged in) and restarts it
automatically if it ever crashes - the Windows equivalent of the systemd
unit used on Linux.

Run this from an elevated ("Run as Administrator") PowerShell, from inside
the local-athan-player folder:

    powershell -ExecutionPolicy Bypass -File .\install-windows-task.ps1

Logs are appended to athan_player.log in this same folder.
Uninstall with: Unregister-ScheduledTask -TaskName "AthanPlayer"
#>

$pythonExe = (Get-Command python).Source
$scriptDir = $PSScriptRoot
$logFile = Join-Path $scriptDir "athan_player.log"

$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$pythonExe`" athan_player.py >> `"$logFile`" 2>&1" `
    -WorkingDirectory $scriptDir

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask -TaskName "AthanPlayer" `
    -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description "Casts the Athan to a Google Nest speaker at each prayer time" `
    -Force

Write-Host "Task 'AthanPlayer' registered. Starting it now..."
Start-ScheduledTask -TaskName "AthanPlayer"
Write-Host "Logs: $logFile"
