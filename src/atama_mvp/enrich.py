from __future__ import annotations

import re

from .models import EnrichmentDraft, RawListing

QUOTA_RE = re.compile(r"(\d+)\s*(?:ADET\s+)?", re.I)
KPSS_RE = re.compile(r"\bKPSS\b|\bP\d{1,3}\b|\b4/?B\b", re.I)


def draft_from_listing(item: RawListing) -> EnrichmentDraft:
    """
    Cheap heuristics only — human must approve before anything is 'published'.
    Does not invent eligibility fields (age/BMI/licenses); those need detail pages / PDFs.
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
