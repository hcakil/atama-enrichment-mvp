# Local hybrid nightly on Windows (TR home IP).
# Separate KK then SBB → separate Telegram messages.
# Secrets: project .env (gitignored) — never commit.

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "local-nightly.log"

function Write-Log([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:sszzz"), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $name = $line.Substring(0, $i).Trim()
        $value = $line.Substring($i + 1).Trim().Trim('"').Trim("'")
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Import-DotEnv (Join-Path $Root ".env")
$env:PYTHONPATH = Join-Path $Root "src"

$Python = if ($env:ATAMA_PYTHON) { $env:ATAMA_PYTHON } else { "python" }

Write-Log "======== local-nightly start ========"
Write-Log "root=$Root python=$Python"

if (-not $env:TELEGRAM_BOT_TOKEN -or -not $env:TELEGRAM_CHAT_ID) {
    Write-Log "WARN: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing"
}

Write-Log "--- source=kk ---"
& $Python -m atama_mvp.cli fetch --source kk --notify-telegram
if ($LASTEXITCODE -ne 0) { Write-Log "WARN: kk exit=$LASTEXITCODE" }

Write-Log "--- source=sbb ---"
& $Python -m atama_mvp.cli fetch --source sbb --notify-telegram
if ($LASTEXITCODE -ne 0) { Write-Log "WARN: sbb exit=$LASTEXITCODE" }

Write-Log "--- export-central ---"
& $Python -m atama_mvp.cli export-central --status all --out data/central/listings.jsonl
if ($LASTEXITCODE -ne 0) { Write-Log "WARN: export-central exit=$LASTEXITCODE" }

Write-Log "======== local-nightly done ========"
