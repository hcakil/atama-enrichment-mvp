from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Sequence


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


def _get(row: Any, key: str):
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def _parse_json_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return [str(x) for x in data]
        except json.JSONDecodeError:
            return [value]
    return []


def _score_label(kpss: Any) -> str | None:
    if not kpss or kpss in {"unknown", "None"}:
        return None
    if kpss == "tyt":
        return "puan:TYT"
    if kpss == "nokpss":
        return "KPSS:yok"
    if kpss == "kpss":
        return "KPSS:var"
    return f"puan:{kpss}"


def _kpss_variant_bits(row: Any) -> list[str]:
    """Optional P93/P94 lines from KK API detail.kpss_variants (JSON/list)."""
    raw = _get(row, "criteria_json")
    variants = None
    # Prefer explicit column if we ever add it; else dig evidence / ignore.
    # Temp tests pass kpss_variants on the card dict directly.
    variants = _get(row, "kpss_variants")
    if not variants and isinstance(raw, str):
        try:
            crit = json.loads(raw)
            ev = crit.get("evidence") or {}
            if ev.get("kpss_score_type"):
                return [f"KPSS:{ev.get('kpss_score_type')}≥{ev.get('min_score')}"]
        except json.JSONDecodeError:
            pass
    if not variants:
        return []
    if isinstance(variants, str):
        try:
            variants = json.loads(variants)
        except json.JSONDecodeError:
            return []
    bits: list[str] = []
    seen: set[str] = set()
    for v in variants or []:
        if not isinstance(v, dict):
            continue
        st = v.get("kpss_score_type")
        ms = v.get("min_score")
        if st and ms is not None:
            label = f"{st}≥{ms}"
            if label not in seen:
                seen.add(label)
                bits.append(label)
    if bits:
        return [f"KPSS:{','.join(bits[:4])}"]
    return []


def format_listing_card(row: Any) -> list[str]:
    """One meaningful Telegram card from lean DB row (skip unknown noise)."""
    source = _get(row, "source")
    title = _get(row, "title")
    institution = _get(row, "institution_name")
    url = _get(row, "external_url")
    window = _get(row, "application_window")
    quota = _get(row, "quota")
    kpss = _get(row, "kpss_requirement")
    min_age = _get(row, "min_age")
    max_age = _get(row, "max_age")
    edu = _parse_json_list(_get(row, "education_levels"))
    provinces = _parse_json_list(_get(row, "provinces"))
    enrich = _get(row, "enrich_status")
    confidence = _get(row, "confidence")
    try:
        conf_f = float(confidence) if confidence is not None else 0.0
    except (TypeError, ValueError):
        conf_f = 0.0

    lines = [f"• [{source}] {institution or '?'} — {title}"]

    bits: list[str] = []
    if quota is not None:
        bits.append(f"kota:{quota}")
    score = _score_label(kpss)
    if score:
        bits.append(score)
    bits.extend(_kpss_variant_bits(row))
    if edu:
        bits.append(f"eğitim:{','.join(edu)}")
    if min_age is not None or max_age is not None:
        bits.append(f"yaş:{min_age or '?'}–{max_age or '?'}")
    if window:
        bits.append(f"süre:{window}")
    if enrich == "detail":
        bits.append("enrich:detail")
    if conf_f >= 0.35:
        bits.append(f"conf:{confidence}")
    if bits:
        lines.append(f"  {' | '.join(bits)}")

    if provinces and conf_f >= 0.35:
        shown = provinces[:8]
        extra = len(provinces) - len(shown)
        prov = ", ".join(shown) + (f" (+{extra})" if extra > 0 else "")
        lines.append(f"  iller: {prov}")

    if source == "sbb_kamuilan":
        if enrich == "detail" and url and "ilanDetay.aspx" in str(url):
            lines.append(f"  {url}")
        elif url and "kamuilan.sbb.gov.tr" in str(url) and "ilanDetay" not in str(url):
            lines.append("  liste: https://kamuilan.sbb.gov.tr/ (detay yok/404)")
        elif url:
            lines.append(f"  {url}")
    elif url:
        lines.append(f"  {url}")
    return lines


def format_new_candidates(rows: Sequence[object], *, max_items: int = 12) -> str:
    """Build a human-readable digest from lean enriched listing rows."""
    total = len(rows)
    lines = [
        f"Yeni ilan: {total}",
        "Review: python -m atama_mvp.cli review --limit 20",
        "",
    ]
    for row in list(rows)[:max_items]:
        lines.extend(format_listing_card(row))
        lines.append("")
    if total > max_items:
        lines.append(f"… +{total - max_items} daha")
    return "\n".join(lines).rstrip()
