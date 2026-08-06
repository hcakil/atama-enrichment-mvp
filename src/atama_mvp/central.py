from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def listing_row_to_central(row: Any) -> dict[str, Any]:
    """Normalize listing row into lean central schema (no raw HTML)."""

    def g(key: str, default=None):
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except (KeyError, IndexError):
            return default

    def loads(key: str):
        val = g(key)
        if val is None or val == "":
            return None
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    return {
        "schema": "atama_mvp.central_listing.v2",
        "fingerprint": g("fingerprint"),
        "source": g("source"),
        "external_id": g("external_id"),
        "external_url": g("external_url"),
        "title": g("title"),
        "institution_name": g("institution_name"),
        "category": g("category"),
        "published_at": g("published_at"),
        "application_window": g("application_window"),
        "application_start": g("application_start"),
        "application_end": g("application_end"),
        "quota": g("quota"),
        "kpss_requirement": g("kpss_requirement"),
        "education_levels": loads("education_levels"),
        "provinces": loads("provinces"),
        "fields_of_study": loads("fields_of_study"),
        "min_age": g("min_age"),
        "max_age": g("max_age"),
        "gender": g("gender"),
        "profession_hint": g("profession_hint"),
        "military_hints": loads("military_hints"),
        "license_hints": loads("license_hints"),
        "confidence": g("confidence"),
        "enrich_status": g("enrich_status"),
        "evidence": loads("evidence_json"),
        "criteria": loads("criteria_json"),
        "review_status": g("review_status"),
        "first_seen_at": g("first_seen_at"),
        "last_seen_at": g("last_seen_at"),
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
