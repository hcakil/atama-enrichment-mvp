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
from .fetchers.sbb_detail import detail_url_from_listing_raw, fetch_sbb_detail
from .gemini_criteria import (
    extract_criteria_gemini,
    gemini_configured,
    merge_prefer_llm,
    needs_llm,
    usage_snapshot,
)
from .models import EnrichmentDraft, RawListing

QUOTA_RE = re.compile(r"(\d+)\s*(?:ADET\s+)?", re.I)
KPSS_RE = re.compile(r"\bKPSS\b|\bKPSSP?\d{1,3}\b|\b4/?B\b", re.I)


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
            n = int(m.group(1))
            if not (1990 <= n <= 2100):
                quota = n
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


def _enrich_sbb(item: RawListing) -> tuple[RawListing, str]:
    detail_url = detail_url_from_listing_raw(item.raw)
    if not detail_url:
        return item, "list"
    bundle = fetch_sbb_detail(detail_url)
    kind = bundle.get("kind")
    text = (bundle.get("text") or "").strip()
    if kind in {"pdf", "html"} and text:
        item.raw = {
            **(item.raw or {}),
            "detail": {
                "kind": kind,
                "content_type": bundle.get("content_type"),
                "bytes_len": bundle.get("bytes_len"),
                "content_text_len": len(text),
                "detail_url": bundle.get("url") or detail_url,
            },
            "content_text": text,
        }
        # Prefer working detail URL when we successfully extracted text.
        item.external_url = str(bundle.get("url") or detail_url)
        if len(text) > 200:
            item.summary = text[:197] + "…"
        else:
            item.summary = text or item.summary
        return item, "detail"
    return item, "list"


def enrich_collected(
    items: Iterable[RawListing],
    *,
    detail_ilan: bool = True,
    detail_sbb: bool = True,
    use_llm: bool | None = None,
) -> tuple[list[RawListing], dict[str, StructuredCriteria], dict[str, str]]:
    """
    Attach StructuredCriteria for each listing.
    ilan.gov → GetAdDetail HTML; SBB → PDF/HTML detail when available.
    Regex first; Gemini only when detail text is rich and regex confidence is low
    (token-saving gate). Bulky body text stripped before DB upsert.
    """
    out: list[RawListing] = []
    criteria_by_fp: dict[str, StructuredCriteria] = {}
    enrich_status: dict[str, str] = {}
    llm_on = gemini_configured() if use_llm is None else bool(use_llm and gemini_configured())

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
        elif detail_sbb and item.source == "sbb_kamuilan":
            t0 = time.perf_counter()
            try:
                item, status = _enrich_sbb(item)
                print(
                    f"  [enrich] sbb {item.external_id} {status} "
                    f"({time.perf_counter() - t0:.1f}s)",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"  [enrich] sbb {item.external_id} detail FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                status = "list"

        content_text = ""
        if isinstance(item.raw, dict):
            content_text = str(item.raw.get("content_text") or "")
        regex_crit = criteria_from_listing_detail(item)
        crit = regex_crit
        if llm_on and content_text and needs_llm(regex_crit, detail_text_len=len(content_text)):
            t0 = time.perf_counter()
            llm_crit, meta = extract_criteria_gemini(
                content_text=content_text,
                title=item.title,
                institution=item.institution_name,
                listing_fingerprint=item.fingerprint,
            )
            crit = merge_prefer_llm(regex_crit, llm_crit)
            usage = meta.get("usage") or {}
            print(
                f"  [enrich] llm {item.fingerprint} "
                f"skipped={meta.get('skipped')} err={meta.get('error')} "
                f"tok={usage.get('totalTokenCount') or meta.get('prompt_tokens_est')} "
                f"({time.perf_counter() - t0:.1f}s) conf {regex_crit.confidence}→{crit.confidence}",
                flush=True,
            )
            # Free-tier RPM is low (~5); pace nightly force mode.
            from .gemini_criteria import llm_force

            if llm_force() and not meta.get("skipped"):
                time.sleep(13)
        elif llm_on and content_text:
            print(
                f"  [enrich] llm skip {item.fingerprint} "
                f"(regex conf={regex_crit.confidence})",
                flush=True,
            )

        # Strip bulky text before upsert — never persist announcement HTML/PDF body in DB.
        if isinstance(item.raw, dict):
            lean = {k: v for k, v in item.raw.items() if k not in {"content_text", "content_html"}}
            detail = lean.get("detail")
            if isinstance(detail, dict):
                keep = (
                    "adNo",
                    "adSourceCode",
                    "adSourceName",
                    "content_text_len",
                    "content_html_len",
                    "kind",
                    "content_type",
                    "bytes_len",
                    "detail_url",
                )
                lean["detail"] = {k: detail[k] for k in keep if k in detail}
            item.raw = lean
            if status == "detail" and item.summary and len(item.summary) > 200:
                item.summary = item.summary[:197] + "…"

        criteria_by_fp[item.fingerprint] = crit
        enrich_status[item.fingerprint] = status
        out.append(item)

    if llm_on:
        print(f"  [enrich] gemini usage {usage_snapshot()}", flush=True)
    return out, criteria_by_fp, enrich_status
