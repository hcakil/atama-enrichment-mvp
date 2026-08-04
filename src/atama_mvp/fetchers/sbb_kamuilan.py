from __future__ import annotations

import hashlib
import html as html_lib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from ..models import RawListing

LIST_URL = "https://kamuilan.sbb.gov.tr/"
USER_AGENT = "AtamaEnrichmentMVP/0.1 (+research; polite; contact: local)"


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


def _get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def _stable_id(href: str) -> str:
    """SBB kod query is long/encrypted; hash for stable fingerprint."""
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    kod = (qs.get("kod") or [href])[0]
    return hashlib.sha256(kod.encode("utf-8")).hexdigest()[:24]


def _abs_url(href: str) -> str:
    return urllib.parse.urljoin(LIST_URL, href)


def fetch_sbb_kamuilan(list_url: str = LIST_URL) -> list[RawListing]:
    """Fetch SBB Kamu İlan homepage slides and normalize list cards."""
    page = _get(list_url)
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
        external_url = _abs_url(href)
        external_id = _stable_id(href)
        title = patrol or institution or external_id
        out.append(
            RawListing(
                source="sbb_kamuilan",
                external_id=external_id,
                external_url=external_url,
                title=title,
                institution_name=institution,
                published_at=stamp,
                application_window=window,
                image_url=_abs_url(item["image_src"]) if item.get("image_src") else None,
                summary=f"{institution or ''} — {patrol}".strip(" —"),
                raw={"href": href, "stamp": stamp, "list_url": list_url},
            )
        )
    return out
