from __future__ import annotations

import io
import urllib.parse
from typing import Any, Literal

from ..http_util import DEFAULT_UA, _ssl_context
from ..fetchers.ilan_gov_detail import _html_to_text

LIST_URL = "https://kamuilan.sbb.gov.tr/"
DETAIL_PATH = "ilanDetay.aspx"

Kind = Literal["pdf", "html", "empty"]


def normalize_sbb_detail_url(kod_or_url: str) -> str:
    """Accept full URL or raw kod query value."""
    s = (kod_or_url or "").strip()
    if not s:
        raise ValueError("empty SBB detail url/kod")
    if s.lower().startswith("http://") or s.lower().startswith("https://"):
        return s
    # Already a path?
    if "ilanDetay.aspx" in s:
        return urllib.parse.urljoin(LIST_URL, s.lstrip("/"))
    qs = urllib.parse.urlencode({"kod": s})
    return f"{LIST_URL}{DETAIL_PATH}?{qs}"


def _is_soft_404_html(text: str, html: str) -> bool:
    low = (html or "").casefold()
    if any(
        x in low
        for x in (
            "sayfa bulunamadı",
            "sayfa bulunamadi",
            "kayıt bulunamadı",
            "kayit bulunamadi",
            "not found",
        )
    ):
        return True
    # Very short / empty body after strip
    if len((text or "").strip()) < 80:
        return True
    # Homepage shell without announcement body
    if "ilandetay" not in low and "başvuru" not in low and "kpss" not in low and "öğrenci" not in low:
        if len(text.strip()) < 400:
            return True
    return False


def _pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def fetch_sbb_detail(kod_or_url: str, *, timeout: int = 60) -> dict[str, Any]:
    """
    Fetch SBB ilanDetay URL. Returns:
      kind: pdf | html | empty
      text: extracted plain text (may be empty)
      content_type, bytes_len, url
    Does not persist PDF/HTML bytes.
    """
    import urllib.error
    import urllib.request

    url = normalize_sbb_detail_url(kod_or_url)
    hdrs = {
        "User-Agent": DEFAULT_UA,
        "Accept": "application/pdf,text/html,application/xhtml+xml,*/*",
        "Accept-Language": "tr-TR,tr;q=0.9",
        "Referer": LIST_URL,
    }
    ctx = _ssl_context()
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = resp.read()
            final_url = resp.geturl() or url
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200]
        raise RuntimeError(f"SBB detail HTTP {exc.code}: {detail!r}") from exc

    bytes_len = len(data)
    out: dict[str, Any] = {
        "url": final_url,
        "content_type": content_type,
        "bytes_len": bytes_len,
        "kind": "empty",
        "text": "",
    }

    if not data:
        return out

    if data[:4] == b"%PDF" or "pdf" in content_type:
        try:
            text = _pdf_to_text(data)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"SBB PDF extract failed: {exc}") from exc
        if len(text.strip()) < 40:
            out["kind"] = "empty"
            out["text"] = text
            return out
        out["kind"] = "pdf"
        out["text"] = text
        return out

    # HTML (or mislabeled)
    html = data.decode("utf-8", errors="replace")
    text = _html_to_text(html)
    if _is_soft_404_html(text, html):
        out["kind"] = "empty"
        out["text"] = text
        return out
    out["kind"] = "html"
    out["text"] = text
    return out


def detail_url_from_listing_raw(raw: dict[str, Any] | None) -> str | None:
    """Prefer raw.detail_url_unreliable / href from SBB list card."""
    if not isinstance(raw, dict):
        return None
    for key in ("detail_url_unreliable", "href"):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            if val.startswith("http"):
                return val
            return urllib.parse.urljoin(LIST_URL, val.lstrip("/"))
    return None
