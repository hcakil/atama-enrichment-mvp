from __future__ import annotations

import html as html_lib
import re
import urllib.parse
from typing import Any

from ..http_util import fetch_bytes
from ..models import RawListing

DETAIL_URL = "https://www.ilan.gov.tr/api/api/services/app/AdDetail/GetAdDetail"
BASE_URL = "https://www.ilan.gov.tr"


def _html_to_text(content: str | None) -> str:
    if not content:
        return ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", content)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"(?i)</tr\s*>", "\n", text)
    text = re.sub(r"(?i)</(div|h[1-6]|li|table)\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_ilan_gov_detail(ad_id: str) -> dict[str, Any]:
    """
    Fetch official AdDetail payload for one ilan.gov.tr listing.
    Returns ABP-style JSON with result.content (HTML body of the announcement).
    """
    import json

    qs = urllib.parse.urlencode({"Id": str(ad_id)})
    url = f"{DETAIL_URL}?{qs}"
    raw = fetch_bytes(
        url,
        timeout=45,
        retries=3,
        headers={
            "Accept": "application/json",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/",
        },
    )
    payload = json.loads(raw.decode("utf-8"))
    if not payload.get("success", True) and payload.get("result") is None:
        raise RuntimeError(f"ilan.gov GetAdDetail failed for id={ad_id}: {payload.get('error')}")
    return payload


def detail_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("ilan.gov GetAdDetail returned empty result")
    return result


def enrich_listing_from_detail(listing: RawListing, result: dict[str, Any]) -> RawListing:
    """Attach detail metadata onto a copy-like update of listing.raw / summary."""
    content_html = result.get("content") or ""
    text = _html_to_text(content_html if isinstance(content_html, str) else str(content_html))
    external_url = listing.external_url
    link = result.get("link") or result.get("urlStr")
    if link and isinstance(link, str):
        external_url = urllib.parse.urljoin(BASE_URL + "/", link.lstrip("/"))
    elif result.get("slugifyTitle") and result.get("id"):
        external_url = f"{BASE_URL}/ilan/{result['id']}/{result['slugifyTitle']}"

    listing.title = (result.get("title") or listing.title or "").strip() or listing.title
    listing.institution_name = (result.get("advertiserName") or listing.institution_name or None)
    listing.external_url = external_url
    listing.summary = (text[:500] + "…") if len(text) > 500 else (text or listing.summary)
    listing.raw = {
        **(listing.raw or {}),
        "detail": {
            "adNo": result.get("adNo"),
            "adSourceCode": result.get("adSourceCode"),
            "adSourceName": result.get("adSourceName"),
            "filters": result.get("filters"),
            "files": result.get("files"),
            "adTypeFilters": result.get("adTypeFilters"),
            "content_html_len": len(content_html) if isinstance(content_html, str) else 0,
            "content_text_len": len(text),
        },
        "content_text": text,
        "content_html": content_html if isinstance(content_html, str) else None,
    }
    return listing


def inspect_bundle(ad_id: str) -> dict[str, Any]:
    """Full inspect payload for research dumps (no Telegram)."""
    payload = fetch_ilan_gov_detail(ad_id)
    result = detail_result(payload)
    content_html = result.get("content") if isinstance(result.get("content"), str) else ""
    text = _html_to_text(content_html)
    meta = {k: result.get(k) for k in sorted(result.keys()) if k not in {"content", "photos"}}
    return {
        "ad_id": str(ad_id),
        "meta": meta,
        "content_html": content_html,
        "content_text": text,
        "content_html_len": len(content_html),
        "content_text_len": len(text),
    }
