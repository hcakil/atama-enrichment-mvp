#!/usr/bin/env bash
# Install macOS LaunchAgent for local-nightly (00:05 Europe/Istanbul ≈ local clock).
# Does not print or commit secrets. Requires .env in project root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${ATAMA_PYTHON:-$(command -v python3)}"
LABEL="com.hcakil.atama-mvp.nightly"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT="$ROOT/scripts/local-nightly.sh"

chmod +x "$SCRIPT" "$ROOT/scripts/install-local-launchd.sh"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Create $ROOT/.env from .env.example first (TELEGRAM_*)." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"

cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SCRIPT}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>0</integer>
    <key>Minute</key>
    <integer>5</integer>
  </dict>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ATAMA_PYTHON</key>
    <string>${PYTHON}</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>${ROOT}/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/logs/launchd.err.log</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "Installed: $PLIST"
echo "Schedule: every day 00:05 (Mac local time)"
echo "Manual once:  launchctl kickstart -k gui/$(id -u)/${LABEL}"
echo "Logs:         $ROOT/logs/local-nightly.log"
echo "Unload later: launchctl bootout gui/$(id -u)/${LABEL}"
