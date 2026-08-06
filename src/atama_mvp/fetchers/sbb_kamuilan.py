from __future__ import annotations

import hashlib
import html as html_lib
import re
import urllib.parse
from html.parser import HTMLParser

from ..http_util import fetch_text
from ..models import RawListing

LIST_URL = "https://kamuilan.sbb.gov.tr/"


class _SlidesParser(HTMLParser):
    """Parse kamuilan homepage carousel / slides list items."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[dict[str, str]] = []
        self._in_slides = False
        self._depth = 0
        self._cur: dict[str, str] | None = None
        self._capture_span_class: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        if tag == "ul" and "slides" in ad.get("class", ""):
            self._in_slides = True
            self._depth = 1
            return
        if not self._in_slides:
            return
        if tag == "ul":
            self._depth += 1
        if tag == "li" and self._depth == 1:
            self._cur = {}
        if tag == "a" and self._cur is not None and "href" in ad:
            href = ad["href"]
            if "ilanDetay.aspx" in href:
                self._cur["href"] = href
        if tag == "img" and self._cur is not None and "src" in ad:
            src = ad["src"]
            self._cur["image_src"] = src
            # stamp often in fragment: logo.png#4.08.2026 00:00:00
            if "#" in src:
                self._cur["stamp"] = src.split("#", 1)[1].strip().rstrip("/")
        if tag == "span" and self._cur is not None:
            cls = ad.get("class", "").strip()
            if cls in {"black", "patrol", "h5date"}:
                self._capture_span_class = cls
                self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if not self._in_slides:
            return
        if tag == "span" and self._capture_span_class and self._cur is not None:
            text = html_lib.unescape("".join(self._buf)).strip()
            self._cur[self._capture_span_class] = text
            self._capture_span_class = None
            self._buf = []
        if tag == "li" and self._cur is not None and self._depth == 1:
            if self._cur.get("href"):
                self.items.append(self._cur)
            self._cur = None
        if tag == "ul":
            self._depth -= 1
            if self._depth <= 0:
                self._in_slides = False
                self._depth = 0

    def handle_data(self, data: str) -> None:
        if self._capture_span_class is not None:
            self._buf.append(data)


def _stable_id(institution: str | None, title: str, href: str) -> str:
    """
    Prefer institution+title so rotating SBB `kod` tokens do not duplicate the same card.
    Fall back to kod hash if title is empty.
    """
    key = f"{(institution or '').strip()}|{(title or '').strip()}".casefold()
    if key.strip("|"):
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    kod = (qs.get("kod") or [href])[0]
    return hashlib.sha256(kod.encode("utf-8")).hexdigest()[:24]


def _abs_url(href: str) -> str:
    return urllib.parse.urljoin(LIST_URL, href)


def fetch_sbb_kamuilan(list_url: str = LIST_URL) -> list[RawListing]:
    """Fetch SBB Kamu İlan homepage slides and normalize list cards."""
    page = fetch_text(
        list_url,
        timeout=60,
        retries=4,
        headers={"Accept": "text/html,application/xhtml+xml"},
    )
    parser = _SlidesParser()
    parser.feed(page)

    # Fallback: regex if markup class spacing differs
    if not parser.items:
        for m in re.finditer(
            r"href='(ilanDetay\.aspx\?kod=[^']+)'[^>]*>.*?<span\s+class\s*=\s*'black'>(.*?)</span>.*?<span class='patrol'>\s*(.*?)</span>.*?<span class='h5date'\s*>(.*?)</span>",
            page,
            flags=re.I | re.S,
        ):
            parser.items.append(
                {
                    "href": m.group(1),
                    "black": re.sub(r"<[^>]+>", "", m.group(2)).strip(),
                    "patrol": re.sub(r"<[^>]+>", "", m.group(3)).strip(),
                    "h5date": re.sub(r"<[^>]+>", "", m.group(4)).strip(),
                }
            )

    out: list[RawListing] = []
    for item in parser.items:
        href = item.get("href") or ""
        institution = item.get("black")
        patrol = (item.get("patrol") or "").strip()
        window = item.get("h5date")
        stamp = item.get("stamp")
        detail_href = _abs_url(href)
        title = patrol or institution or "sbb"
        external_id = _stable_id(institution, title, href)
        # SBB ilanDetay.aspx?kod=… soft-404s; store homepage as public URL.
        out.append(
            RawListing(
                source="sbb_kamuilan",
                external_id=external_id,
                external_url=LIST_URL,
                title=title,
                institution_name=institution,
                published_at=stamp,
                application_window=window,
                image_url=None,
                summary=f"{institution or ''} — {patrol}".strip(" —"),
                raw={
                    "href": href,
                    "detail_url_unreliable": detail_href,
                    "stamp": stamp,
                    "list_url": list_url,
                },
            )
        )
    return out
