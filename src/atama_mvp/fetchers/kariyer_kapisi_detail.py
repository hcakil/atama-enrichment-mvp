from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from ..http_util import DEFAULT_UA, _ssl_context
from ..models import RawListing

API_BASE = "https://api.kariyerkapisi.gov.tr/api"
PREVIEW_PATH = "/ilan/GetIlanPreviewPublic"
ALT_PATH = "/altilan/GetAltIlanInfoByIlanIdPublic"
PAGE_BASE = "https://kariyerkapisi.gov.tr/IlanDetay"


def _post_json_any(url: str, payload: dict[str, Any], *, timeout: int = 45) -> Any:
    body = json.dumps(payload).encode("utf-8")
    hdrs = {
        "User-Agent": DEFAULT_UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://kariyerkapisi.gov.tr",
        "Referer": "https://kariyerkapisi.gov.tr/",
        "Accept-Language": "tr-TR,tr;q=0.9",
    }
    ctx = _ssl_context()
    last: BaseException | None = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read().decode("utf-8")
                if not raw.strip():
                    return None
                return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.5 * attempt)
    assert last is not None
    raise last


_BBCODE_RE = re.compile(r"\[/?[^\]]+\]")


def _bbcode_to_text(s: str | None) -> str:
    if not s:
        return ""
    text = _BBCODE_RE.sub(" ", s)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_kariyer_kapisi_detail(ilan_guid: str) -> dict[str, Any]:
    """
    Public KK APIs (same as browser IlanDetay page).
    Returns preview dict + alt_ilan list + combined content_text for criteria/LLM.
    """
    guid = (ilan_guid or "").strip()
    if not guid:
        raise ValueError("empty kariyer_kapisi ilan guid")

    preview = _post_json_any(API_BASE + PREVIEW_PATH, {"ilanGuid": guid})
    if not isinstance(preview, dict):
        raise RuntimeError(f"KK GetIlanPreviewPublic empty/invalid for {guid}")

    alt = _post_json_any(API_BASE + ALT_PATH, {"ilanGuid": guid})
    if not isinstance(alt, list):
        alt = []

    parts: list[str] = []
    for key in ("kurumAdi", "birimAdi", "ilanBaslik", "ilanTuru"):
        val = preview.get(key)
        if val:
            parts.append(f"{key}: {val}")
    if preview.get("basTarih") or preview.get("bitTarih"):
        parts.append(f"başvuru: {preview.get('basTarih')} – {preview.get('bitTarih')}")
    if preview.get("kontenjan"):
        parts.append(f"kontenjan: {preview.get('kontenjan')}")
    main = _bbcode_to_text(preview.get("ilanMetni"))
    if main:
        parts.append(main)

    kpss_variants: list[dict[str, Any]] = []
    for i, item in enumerate(alt):
        if not isinstance(item, dict):
            continue
        title = item.get("ilanBaslik") or item.get("unvan") or f"alt-{i+1}"
        parts.append(f"\n--- Alt ilan: {title} ---")
        if item.get("unvan"):
            parts.append(f"unvan: {item['unvan']}")
        body = _bbcode_to_text(item.get("ilanMetni"))
        if body:
            parts.append(body)
        for k in item.get("kontenjanList") or []:
            if isinstance(k, dict):
                parts.append(f"kontenjan: {k.get('il')} = {k.get('kontenjan')}")
        for stage in item.get("degerlemeAsamaList") or []:
            if not isinstance(stage, dict):
                continue
            tur = stage.get("turu") or stage.get("asamaAdi")
            parts.append(f"değerlendirme: {tur} ağırlık={stage.get('agirlik')}")
            if str(tur or "").upper() == "KPSS" or "KPSS" in str(stage.get("asamaAdi") or "").upper():
                kpss_variants.append(
                    {
                        "alt_title": title,
                        "unvan": item.get("unvan"),
                        "asama": stage.get("asamaAdi"),
                        "turu": stage.get("turu"),
                        "agirlik": stage.get("agirlik"),
                    }
                )
            # Pull P94-style hints from body into variants note
        m = re.search(
            r"KPSS[^\n.]{0,40}?(P\d{1,3})[^\n.]{0,40}?(?:en\s+az\s+)?(\d{1,3})",
            body,
            re.I,
        )
        if m:
            kpss_variants.append(
                {
                    "alt_title": title,
                    "unvan": item.get("unvan"),
                    "kpss_score_type": m.group(1).upper(),
                    "min_score": int(m.group(2)),
                    "evidence": m.group(0)[:120],
                }
            )

    content_text = "\n".join(parts).strip()
    return {
        "ilan_guid": guid,
        "preview": {
            k: preview.get(k)
            for k in (
                "ilanBaslik",
                "kurumAdi",
                "birimAdi",
                "ilanTuru",
                "basTarih",
                "bitTarih",
                "kontenjan",
                "ilN_NO",
            )
        },
        "alt_count": len(alt),
        "kpss_variants": kpss_variants,
        "content_text": content_text,
        "content_text_len": len(content_text),
    }


def enrich_listing_from_kk_detail(listing: RawListing, bundle: dict[str, Any]) -> RawListing:
    """Attach KK API detail text onto listing for criteria/LLM (no raw HTML dump)."""
    preview = bundle.get("preview") or {}
    text = bundle.get("content_text") or ""
    if preview.get("ilanBaslik"):
        listing.title = str(preview["ilanBaslik"]).strip() or listing.title
    if preview.get("kurumAdi"):
        listing.institution_name = str(preview["kurumAdi"]).strip() or listing.institution_name
    if preview.get("ilanTuru"):
        listing.category = str(preview["ilanTuru"]).strip() or listing.category
    start, end = preview.get("basTarih"), preview.get("bitTarih")
    if start or end:
        listing.application_window = " – ".join(str(x) for x in [start, end] if x)
    listing.external_url = f"{PAGE_BASE}?i={bundle.get('ilan_guid') or listing.external_id}"
    listing.summary = (text[:200] + "…") if len(text) > 200 else (text or listing.summary)
    listing.raw = {
        **(listing.raw or {}),
        "detail": {
            "kind": "kk_api",
            "alt_count": bundle.get("alt_count"),
            "content_text_len": bundle.get("content_text_len"),
            "kpss_variants": bundle.get("kpss_variants") or [],
            "preview": preview,
        },
        "content_text": text,
    }
    return listing
