#!/usr/bin/env bash
# Local hybrid nightly: TR IP → KK and SBB as separate jobs + separate Telegram messages.
# Secrets: project .env (gitignored) or already-exported env vars.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

PYTHON="${ATAMA_PYTHON:-$(command -v python3)}"
LOG_DIR="${ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/local-nightly.log"

ts() { date '+%Y-%m-%d %H:%M:%S%z'; }

{
  echo "======== $(ts) local-nightly start ========"
  echo "root=$ROOT python=$PYTHON"

  if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "WARN: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing — fetch runs, notify may skip" >&2
  fi

  echo "--- $(ts) source=kk ---"
  "$PYTHON" -m atama_mvp.cli fetch --source kk --notify-telegram

  echo "--- $(ts) source=sbb ---"
  "$PYTHON" -m atama_mvp.cli fetch --source sbb --notify-telegram

  echo "======== $(ts) local-nightly done ========"
} >>"$LOG_FILE" 2>&1
