"""Profile-based listing match for invite-only Telegram alerts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


def _parse_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            return [value.strip()] if value.strip() else []
    return []


def _norm(s: str) -> str:
    return s.casefold().strip()


@dataclass
class AlertProfile:
    """Candidate prefs. Empty list / None means no filter on that axis."""

    provinces: list[str] = field(default_factory=list)
    education_levels: list[str] = field(default_factory=list)
    kpss_requirement: list[str] = field(default_factory=list)
    age: int | None = None
    sources: list[str] = field(default_factory=list)
    min_confidence: float = 0.35
    keywords: list[str] = field(default_factory=list)
    require_detail: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertProfile:
        return cls(
            provinces=_parse_list(data.get("provinces")),
            education_levels=_parse_list(data.get("education_levels")),
            kpss_requirement=_parse_list(data.get("kpss_requirement")),
            age=int(data["age"]) if data.get("age") is not None else None,
            sources=_parse_list(data.get("sources")),
            min_confidence=float(data.get("min_confidence") or 0.35),
            keywords=_parse_list(data.get("keywords")),
            require_detail=bool(data.get("require_detail") or False),
        )

    @classmethod
    def load(cls, path: Path | str) -> AlertProfile:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("alert profile must be a JSON object")
        return cls.from_dict(payload)


def _get(row: Any, key: str):
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def _overlap(want: list[str], have: list[str]) -> bool:
    if not want:
        return True
    if not have:
        # Listing silent on this axis → do not block (national / unknown).
        return True
    want_n = {_norm(x) for x in want}
    have_n = {_norm(x) for x in have}
    return bool(want_n & have_n)


def match_listing(row: Any, profile: AlertProfile) -> bool:
    try:
        conf = float(_get(row, "confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < profile.min_confidence:
        return False

    if profile.require_detail and str(_get(row, "enrich_status") or "") != "detail":
        return False

    if profile.sources:
        src = str(_get(row, "source") or "")
        if src not in profile.sources:
            return False

    if not _overlap(profile.provinces, _parse_list(_get(row, "provinces"))):
        return False

    if not _overlap(profile.education_levels, _parse_list(_get(row, "education_levels"))):
        return False

    if profile.kpss_requirement:
        kpss = str(_get(row, "kpss_requirement") or "").strip()
        allowed = {_norm(x) for x in profile.kpss_requirement}
        if kpss and _norm(kpss) not in allowed and "any" not in allowed:
            return False

    if profile.age is not None:
        age = profile.age
        min_age = _get(row, "min_age")
        max_age = _get(row, "max_age")
        try:
            if min_age is not None and age < int(min_age):
                return False
            if max_age is not None and age > int(max_age):
                return False
        except (TypeError, ValueError):
            pass

    if profile.keywords:
        blob = " ".join(
            str(x or "")
            for x in (
                _get(row, "title"),
                _get(row, "institution_name"),
                _get(row, "profession_hint"),
                _get(row, "category"),
            )
        )
        blob_n = _norm(blob)
        if not any(_norm(k) in blob_n for k in profile.keywords):
            return False

    return True


def filter_matches(rows: Sequence[Any], profile: AlertProfile) -> list[Any]:
    return [row for row in rows if match_listing(row, profile)]
