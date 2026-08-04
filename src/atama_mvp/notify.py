from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Sequence


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def telegram_configured() -> bool:
    return bool(_env("TELEGRAM_BOT_TOKEN") and _env("TELEGRAM_CHAT_ID"))


def send_telegram_message(text: str, *, token: str | None = None, chat_id: str | None = None) -> None:
    """Send a plain text message via Bot API. Raises on HTTP/API errors."""
    token = token or _env("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or _env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text[:3900],
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {detail}") from exc

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")


def format_new_candidates(rows: Sequence[object], *, max_items: int = 15) -> str:
    """Build a human-readable digest for newly discovered listings."""
    total = len(rows)
    lines = [
        f"Yeni ilan adayı: {total}",
        "Bunlar henüz onaylanmadı — review CLI ile bak.",
        "",
    ]
    for row in list(rows)[:max_items]:
        # sqlite3.Row or mapping-like
        source = row["source"] if not isinstance(row, dict) else row.get("source")
        title = row["title"] if not isinstance(row, dict) else row.get("title")
        institution = row["institution_name"] if not isinstance(row, dict) else row.get("institution_name")
        url = row["external_url"] if not isinstance(row, dict) else row.get("external_url")
        lines.append(f"• [{source}] {institution or '?'} — {title}")
        lines.append(f"  {url}")
    if total > max_items:
        lines.append("")
        lines.append(f"… ve {total - max_items} aday daha (pending).")
    lines.append("")
    lines.append("Komut: python -m atama_mvp.cli review --limit 20")
    return "\n".join(lines)
