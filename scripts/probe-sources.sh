#!/usr/bin/env bash
# Quick reachability probe for candidate VPS IPs (no secrets needed).
# Exit 0 only if both sources respond within timeout.
set -euo pipefail

UA='Mozilla/5.0 (compatible; AtamaEnrichmentMVP/0.1; +https://github.com/hcakil/atama-enrichment-mvp)'
TIMEOUT="${PROBE_TIMEOUT:-20}"

probe() {
  local name="$1" url="$2"
  local t0 t1 code elapsed
  t0=$(date +%s)
  code=$(curl -sS -o /dev/null -w '%{http_code}' -m "$TIMEOUT" -A "$UA" -L "$url" || echo "000")
  t1=$(date +%s)
  elapsed=$((t1 - t0))
  echo "[$name] http=$code in ${elapsed}s  $url"
  [[ "$code" =~ ^2 ]]
}

ok=0
probe "kariyer_kapisi" "https://kariyerkapisi.gov.tr/RSS" && ok=$((ok + 1)) || true
probe "sbb_kamuilan" "https://kamuilan.sbb.gov.tr/" && ok=$((ok + 1)) || true

echo "---"
echo "public_ip=$(curl -sS -m 10 https://api.ipify.org || echo unknown)"
echo "ok_sources=$ok/2"
[[ "$ok" -eq 2 ]]
