from __future__ import annotations

import re
import sys
import time
from typing import Iterable

from .criteria import StructuredCriteria, parse_structured_criteria
from .fetchers.ilan_gov_detail import (
    detail_result,
    enrich_listing_from_detail,
    fetch_ilan_gov_detail,
)
from .models import EnrichmentDraft, RawListing

QUOTA_RE = re.compile(r"(\d+)\s*(?:ADET\s+)?", re.I)
KPSS_RE = re.compile(r"\bKPSS\b|\bP\d{1,3}\b|\b4/?B\b", re.I)


def draft_from_listing(item: RawListing) -> EnrichmentDraft:
    """
    Cheap heuristics only — human must approve before anything is 'published'.
    Prefer StructuredCriteria from enrich_listing for DB/Telegram.
    """
    blob = " ".join(
        x
        for x in [
            item.title,
            item.institution_name,
            item.summary,
            item.category,
            item.application_window,
        ]
        if x
    )
    quota = None
    m = QUOTA_RE.search(item.title) or (QUOTA_RE.search(item.summary or "") if item.summary else None)
    if m:
        try:
            quota = int(m.group(1))
        except ValueError:
            quota = None

    kpss = None
    if KPSS_RE.search(blob):
        kpss = "likely_kpss_or_4b"

    notes_parts = [
        "Auto-draft only. Verify against official source before use.",
        f"source={item.source}",
        f"url={item.external_url}",
    ]
    if item.application_window:
        notes_parts.append(f"application_window={item.application_window}")
    if item.published_at:
        notes_parts.append(f"published_at={item.published_at}")

    confidence = 0.35
    if item.institution_name:
        confidence += 0.2
    if quota is not None:
        confidence += 0.15
    if item.external_url:
        confidence += 0.1
    confidence = min(confidence, 0.85)

    return EnrichmentDraft(
        listing_fingerprint=item.fingerprint,
        suggested_title=item.title,
        suggested_institution=item.institution_name,
        suggested_quota=quota,
        suggested_kpss=kpss,
        notes=" | ".join(notes_parts),
        confidence=round(confidence, 2),
    )


def criteria_from_listing_detail(item: RawListing) -> StructuredCriteria:
    """Build StructuredCriteria from listing + optional detail text in item.raw."""
    content_text = ""
    if isinstance(item.raw, dict):
        content_text = str(item.raw.get("content_text") or "")
    if not content_text:
        content_text = " ".join(
            x for x in [item.title, item.institution_name, item.summary, item.category] if x
        )
    return parse_structured_criteria(
        content_text=content_text,
        title=item.title,
        institution=item.institution_name,
        listing_fingerprint=item.fingerprint,
    )


def enrich_collected(
    items: Iterable[RawListing],
    *,
    detail_ilan: bool = True,
) -> tuple[list[RawListing], dict[str, StructuredCriteria], dict[str, str]]:
    """
    Attach StructuredCriteria for each listing.
    For ilan.gov, optionally fetch GetAdDetail (no HTML stored on the listing).
    """
    out: list[RawListing] = []
    criteria_by_fp: dict[str, StructuredCriteria] = {}
    enrich_status: dict[str, str] = {}

    for item in items:
        status = "list"
        if detail_ilan and item.source == "ilan_gov":
            t0 = time.perf_counter()
            try:
                payload = fetch_ilan_gov_detail(item.external_id)
                result = detail_result(payload)
                item = enrich_listing_from_detail(item, result)
                status = "detail"
                print(
                    f"  [enrich] ilan_gov {item.external_id} detail ok "
                    f"({time.perf_counter() - t0:.1f}s)",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"  [enrich] ilan_gov {item.external_id} detail FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                status = "list"

        crit = criteria_from_listing_detail(item)
        # Strip bulky text before upsert — never persist announcement HTML/body in DB.
        if isinstance(item.raw, dict):
            lean = {k: v for k, v in item.raw.items() if k not in {"content_text", "content_html"}}
            detail = lean.get("detail")
            if isinstance(detail, dict):
                lean["detail"] = {
                    k: detail[k]
                    for k in (
                        "adNo",
                        "adSourceCode",
                        "adSourceName",
                        "content_text_len",
                        "content_html_len",
                    )
                    if k in detail
                }
            item.raw = lean
            # Clear long summary; criteria holds the signal.
            if status == "detail" and item.summary and len(item.summary) > 200:
                item.summary = item.summary[:197] + "…"

        criteria_by_fp[item.fingerprint] = crit
        enrich_status[item.fingerprint] = status
        out.append(item)

    return out, criteria_by_fp, enrich_status
