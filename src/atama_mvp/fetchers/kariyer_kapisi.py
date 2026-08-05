from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from ..http_util import fetch_bytes
from ..models import RawListing

RSS_URL = "https://kariyerkapisi.gov.tr/RSS"


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    return el.text.strip() or None


def _guid_id(guid: str | None, link: str | None) -> str:
    value = guid or link or ""
    m = re.search(r"[?&]i=([0-9a-fA-F-]{36})", value)
    if m:
        return m.group(1).lower()
    return value


def _split_title(title: str) -> tuple[str | None, str]:
    # Many items: "KURUM - İLAN BAŞLIĞI"
    if " - " in title:
        left, right = title.split(" - ", 1)
        return left.strip() or None, right.strip() or title
    return None, title


def fetch_kariyer_kapisi(rss_url: str = RSS_URL) -> list[RawListing]:
    """Fetch official Kariyer Kapısı RSS and normalize list cards."""
    xml = fetch_bytes(
        rss_url,
        headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"},
    )
    root = ET.fromstring(xml)
    channel = root.find("channel")
    if channel is None:
        return []

    out: list[RawListing] = []
    for item in channel.findall("item"):
        title = _text(item.find("title")) or ""
        link = _text(item.find("link"))
        guid = _text(item.find("guid"))
        category = _text(item.find("category"))
        description = _text(item.find("description"))
        pub_date = _text(item.find("pubDate"))
        enclosure = item.find("enclosure")
        image_url = enclosure.get("url") if enclosure is not None else None
        institution, short_title = _split_title(title)
        external_id = _guid_id(guid, link)
        if not external_id or not link:
            continue
        out.append(
            RawListing(
                source="kariyer_kapisi",
                external_id=external_id,
                external_url=link,
                title=short_title,
                institution_name=institution,
                category=category,
                published_at=pub_date,
                image_url=image_url,
                summary=description,
                raw={
                    "guid": guid,
                    "full_title": title,
                    "rss_url": rss_url,
                },
            )
        )
    return out
