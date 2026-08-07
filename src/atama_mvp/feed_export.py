"""B2B / partner demo feed export (JSON + CSV + metrics)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from .central import listing_row_to_central

# Partner-facing columns (no raw evidence / full criteria dump in --demo).
FEED_FIELDS = [
    "fingerprint",
    "source",
    "external_id",
    "external_url",
    "title",
    "institution_name",
    "category",
    "published_at",
    "application_window",
    "application_start",
    "application_end",
    "quota",
    "kpss_requirement",
    "education_levels",
    "provinces",
    "fields_of_study",
    "min_age",
    "max_age",
    "gender",
    "profession_hint",
    "military_hints",
    "license_hints",
    "confidence",
    "enrich_status",
    "review_status",
    "first_seen_at",
    "last_seen_at",
]


def _row_get(row: Any, key: str, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def _conf(row: Any) -> float:
    raw = _row_get(row, "confidence")
    try:
        return float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def filter_feed_rows(
    rows: Sequence[Any],
    *,
    min_confidence: float = 0.0,
    enrich_detail_only: bool = False,
    limit: int | None = None,
) -> list[Any]:
    out: list[Any] = []
    for row in rows:
        if _conf(row) < min_confidence:
            continue
        if enrich_detail_only and str(_row_get(row, "enrich_status") or "") != "detail":
            continue
        out.append(row)
        if limit is not None and len(out) >= limit:
            break
    return out


def to_feed_record(row: Any, *, demo: bool = False) -> dict[str, Any]:
    """Lean partner record. demo=True drops evidence/criteria internals."""
    central = listing_row_to_central(row)
    rec = {k: central.get(k) for k in FEED_FIELDS}
    rec["schema"] = "atama_mvp.b2b_feed.v1"
    if not demo:
        rec["evidence"] = central.get("evidence")
        # Keep compact criteria subset useful for pilots, not full prompt dumps.
        crit = central.get("criteria")
        if isinstance(crit, dict):
            rec["criteria_summary"] = {
                k: crit.get(k)
                for k in (
                    "quota",
                    "kpss_requirement",
                    "education_level_hints",
                    "province_hints",
                    "min_age",
                    "max_age",
                    "confidence",
                )
                if crit.get(k) not in (None, [], {})
            }
        else:
            rec["criteria_summary"] = None
    return rec


def feed_metrics(records: Sequence[dict[str, Any]], *, source_rows: int) -> dict[str, Any]:
    by_source = Counter(str(r.get("source") or "?") for r in records)
    by_enrich = Counter(str(r.get("enrich_status") or "?") for r in records)
    confs = [float(r["confidence"]) for r in records if r.get("confidence") is not None]
    with_quota = sum(1 for r in records if r.get("quota") is not None)
    with_kpss = sum(
        1 for r in records if r.get("kpss_requirement") not in (None, "", "unknown")
    )
    with_edu = sum(1 for r in records if r.get("education_levels"))
    with_prov = sum(1 for r in records if r.get("provinces"))
    with_age = sum(1 for r in records if r.get("min_age") is not None or r.get("max_age") is not None)
    n = len(records)
    return {
        "schema": "atama_mvp.b2b_feed_metrics.v1",
        "source_row_count": source_rows,
        "exported_count": n,
        "by_source": dict(by_source),
        "by_enrich_status": dict(by_enrich),
        "field_coverage": {
            "quota": with_quota / n if n else 0.0,
            "kpss_requirement": with_kpss / n if n else 0.0,
            "education_levels": with_edu / n if n else 0.0,
            "provinces": with_prov / n if n else 0.0,
            "age": with_age / n if n else 0.0,
        },
        "confidence": {
            "min": min(confs) if confs else None,
            "max": max(confs) if confs else None,
            "avg": (sum(confs) / len(confs)) if confs else None,
        },
    }


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_feed(
    records: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    out_stem: Path,
) -> dict[str, Path]:
    """Write out_stem.json, out_stem.csv, out_stem.metrics.json."""
    out_stem = Path(out_stem)
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_stem.with_suffix(".json") if out_stem.suffix != ".json" else out_stem
    # Allow --out data/demo/feed (no suffix) → feed.json / feed.csv / feed.metrics.json
    if out_stem.suffix in {".json", ".csv"}:
        stem = out_stem.with_suffix("")
    else:
        stem = out_stem
        json_path = Path(str(stem) + ".json")

    csv_path = Path(str(stem) + ".csv")
    metrics_path = Path(str(stem) + ".metrics.json")

    json_path.write_text(json.dumps(list(records), ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = ["schema", *FEED_FIELDS]
    # Optional non-demo extras
    if records and "criteria_summary" in records[0]:
        fieldnames.append("criteria_summary")
    if records and "evidence" in records[0]:
        fieldnames.append("evidence")

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: _csv_cell(rec.get(k)) for k in fieldnames})

    return {"json": json_path, "csv": csv_path, "metrics": metrics_path}
