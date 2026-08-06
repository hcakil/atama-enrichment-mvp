from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


# Canonical record written to central JSONL (one object per line).
# Compatible with future remote SQLite/Turso sync; human-readable for MVP.


def listing_row_to_central(row: Any) -> dict[str, Any]:
    """Normalize sqlite3.Row / dict listing (+ optional draft) into central schema."""

    def g(key: str, default=None):
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except (KeyError, IndexError):
            return default

    draft = None
    draft_json = g("draft_json")
    if draft_json:
        try:
            draft = json.loads(draft_json) if isinstance(draft_json, str) else draft_json
        except json.JSONDecodeError:
            draft = None

    raw = None
    raw_json = g("raw_json")
    if raw_json:
        try:
            raw = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except json.JSONDecodeError:
            raw = {"_unparsed": True}

    return {
        "schema": "atama_mvp.central_listing.v1",
        "fingerprint": g("fingerprint"),
        "source": g("source"),
        "external_id": g("external_id"),
        "external_url": g("external_url"),
        "title": g("title"),
        "institution_name": g("institution_name"),
        "category": g("category"),
        "published_at": g("published_at"),
        "application_window": g("application_window"),
        "summary": g("summary"),
        "image_url": g("image_url"),
        "review_status": g("review_status"),
        "first_seen_at": g("first_seen_at"),
        "last_seen_at": g("last_seen_at"),
        "draft": draft,
        "raw": raw,
    }


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
            n += 1
    return n
