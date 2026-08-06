# Install a daily Windows Task Scheduler job (00:05 local time).
# Run once in PowerShell (Admin not required for current-user task):
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-windows-task.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root "scripts\local-nightly.ps1"
$TaskName = "AtamaMvpNightly"
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Create $EnvFile from .env.example first (TELEGRAM_*)."
}

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    $PythonCmd = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $PythonCmd) {
    Write-Error "Python not found on PATH. Install Python 3 and re-open PowerShell."
}
$Python = $PythonCmd.Source

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $Root

$trigger = New-ScheduledTaskTrigger -Daily -At "00:05"
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "atama-mvp: KK then SBB fetch + Telegram (home TR IP)" `
    -Force | Out-Null

Write-Host "Installed task: $TaskName"
Write-Host "Schedule: daily 00:05 (this PC local time)"
Write-Host "Run once:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "Logs:      $Root\logs\local-nightly.log"
Write-Host "Remove:    Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host ""
Write-Host "Also: Power Options → Sleep = Never (or Wake timers on) so 00:05 runs."
