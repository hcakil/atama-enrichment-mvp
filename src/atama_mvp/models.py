from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RawListing:
    """Normalized listing candidate before human approval."""

    source: str  # kariyer_kapisi | sbb_kamuilan | ilan_gov
    external_id: str
    external_url: str
    title: str
    institution_name: str | None = None
    category: str | None = None
    published_at: str | None = None
    application_window: str | None = None
    image_url: str | None = None
    summary: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        return f"{self.source}:{self.external_id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnrichmentDraft:
    """Best-effort structured fields for reviewer; never auto-published."""

    listing_fingerprint: str
    suggested_title: str
    suggested_institution: str | None
    suggested_quota: int | None
    suggested_kpss: str | None
    notes: str
    confidence: float  # 0..1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
