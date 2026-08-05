# Quick reachability probe for Windows (no secrets).
$ErrorActionPreference = "Continue"
$UA = "Mozilla/5.0 (compatible; AtamaEnrichmentMVP/0.1; +https://github.com/hcakil/atama-enrichment-mvp)"
$TimeoutSec = 20

function Probe([string]$Name, [string]$Url) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-WebRequest -Uri $Url -UserAgent $UA -TimeoutSec $TimeoutSec -UseBasicParsing
        $sw.Stop()
        Write-Host ("[{0}] http={1} in {2:N1}s  {3}" -f $Name, [int]$resp.StatusCode, $sw.Elapsed.TotalSeconds, $Url)
        return $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300
    } catch {
        $sw.Stop()
        Write-Host ("[{0}] FAILED after {1:N1}s — {2}" -f $Name, $sw.Elapsed.TotalSeconds, $_.Exception.Message)
        return $false
    }
}

$ok = 0
if (Probe "kariyer_kapisi" "https://kariyerkapisi.gov.tr/RSS") { $ok++ }
if (Probe "sbb_kamuilan" "https://kamuilan.sbb.gov.tr/") { $ok++ }

try {
    $ip = (Invoke-WebRequest -Uri "https://api.ipify.org" -TimeoutSec 10 -UseBasicParsing).Content
} catch { $ip = "unknown" }

Write-Host "---"
Write-Host "public_ip=$ip"
Write-Host "ok_sources=$ok/2"
if ($ok -ne 2) { exit 1 }
