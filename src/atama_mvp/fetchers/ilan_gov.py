from __future__ import annotations

import urllib.parse
from typing import Iterable

from ..http_util import post_json
from ..models import RawListing

API_URL = "https://www.ilan.gov.tr/api/api/services/app/Ad/AdsByFilter"
BASE_URL = "https://www.ilan.gov.tr"

# Personel-oriented taxonomy ids observed on ilan.gov.tr (AdsByFilter `txv`).
# 73 = akademik genel; 725 sözleşmeli; 727 memur; 728 uzman yd.; 724 işçi; 695 bilişim.
DEFAULT_TXV = (73, 725, 727, 728, 724, 695)


def _filter_value(ad: dict, key: str) -> str | None:
    for item in ad.get("adTypeFilters") or []:
        if item.get("key") == key:
            value = item.get("value")
            return str(value).strip() if value is not None else None
    return None


def _abs_url(url_str: str | None, ad_id: str) -> str:
    if url_str:
        return urllib.parse.urljoin(BASE_URL + "/", url_str.lstrip("/"))
    return f"{BASE_URL}/ilan/{ad_id}"


def _from_ad(ad: dict, *, txv: int) -> RawListing | None:
    ad_id = str(ad.get("id") or "").strip()
    if not ad_id:
        return None
    title = (ad.get("title") or "").strip() or ad_id
    institution = (ad.get("advertiserName") or "").strip() or None
    city = (ad.get("addressCityName") or "").strip() or None
    category = _filter_value(ad, "İlan Türü") or "PERSONEL ALIMI"
    published = ad.get("publishStartDate")
    if published is not None:
        published = str(published)
    rg_date = _filter_value(ad, "Resmî Gazete Yayım Tarihi")
    summary_parts = [p for p in [institution, city, ad.get("adSourceName"), ad.get("adNo")] if p]
    return RawListing(
        source="ilan_gov",
        external_id=ad_id,
        external_url=_abs_url(ad.get("urlStr"), ad_id),
        title=title,
        institution_name=institution,
        category=category,
        published_at=published,
        application_window=rg_date,
        summary=" — ".join(str(p) for p in summary_parts) or None,
        raw={
            "adNo": ad.get("adNo"),
            "city": city,
            "adSourceCode": ad.get("adSourceCode"),
            "adSourceName": ad.get("adSourceName"),
            "txv": txv,
            "slugifyTitle": ad.get("slugifyTitle"),
        },
    )


def fetch_ilan_gov(
    *,
    txv_ids: Iterable[int] = DEFAULT_TXV,
    max_per_category: int = 50,
) -> list[RawListing]:
    """Fetch personel-related ads from ilan.gov.tr public AdsByFilter API."""
    by_id: dict[str, RawListing] = {}
    headers = {
        "Origin": BASE_URL,
        "Referer": BASE_URL + "/",
    }
    for txv in txv_ids:
        payload = {
            "keys": {"txv": [int(txv)], "currentPage": [1]},
            "sorting": "publish_time desc",
            "skipCount": 0,
            "maxResultCount": int(max_per_category),
        }
        data = post_json(API_URL, payload, timeout=45, retries=3, headers=headers)
        ads = ((data.get("result") or {}).get("ads")) or []
        for ad in ads:
            item = _from_ad(ad, txv=int(txv))
            if item is None:
                continue
            # Prefer first category hit; keep stable external_id
            by_id.setdefault(item.external_id, item)
    return list(by_id.values())
