from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StructuredCriteria:
    """
    Subset of Bildirio JobPostingDetail-compatible fields extracted heuristically
    from announcement text. Never auto-publish; human review required.
    """

    listing_fingerprint: str | None = None
    title: str | None = None
    institution_name: str | None = None
    quota: int | None = None
    kpss_requirement: str | None = None  # kpss | nokpss | tyt | unknown
    education_level_hints: list[str] = field(default_factory=list)
    field_of_study_hints: list[str] = field(default_factory=list)
    province_hints: list[str] = field(default_factory=list)
    min_age: int | None = None
    max_age: int | None = None
    gender: str | None = None  # male | female | any
    military_hints: list[str] = field(default_factory=list)
    license_class_hints: list[str] = field(default_factory=list)
    application_start_hint: str | None = None
    application_end_hint: str | None = None
    profession_hint: str | None = None
    evidence: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Turkish thousands: 3.250 / 3,250 → 3250
def _parse_tr_int(raw: str) -> int | None:
    s = (raw or "").strip().replace(" ", "")
    if not s:
        return None
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    else:
        s = s.replace(",", "")
        if s.count(".") == 1 and len(s.split(".")[-1]) == 3:
            s = s.replace(".", "")
        else:
            s = s.replace(".", "")
    try:
        n = int(s)
    except ValueError:
        return None
    return n


def _looks_like_year(n: int) -> bool:
    return 1990 <= n <= 2100


MONTHS_TR = (
    "ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|ağustos|agustos|"
    "eylül|eylul|ekim|kasım|kasim|aralık|aralik"
)

# Explicit total quota: "toplam (3.250) öğrenci" / "toplam 3250"
TOTAL_QUOTA_RE = re.compile(
    r"toplam\s*\(?\s*([\d.,]+)\s*\)?\s*"
    r"(?:kişilik\s+)?(?:öğrenci|personel|memur|işçi|uzman|adet|aday)?",
    re.I,
)
# "860 Gelir Uzman … alınacaktır" / "45 SÖZLEŞMELİ … ALACAK"
QUOTA_CONTEXT_RE = re.compile(
    r"(?:üzere[, ]+)?\(?\s*([\d.,]{1,6})\s*\)?\s*"
    r"(?:kişilik\s+)?(?:personel|memur|işçi|uzman|öğretim|öğrenci|adet|komiser|antrenör)?"
    r"[^\n.]{0,80}(?:alınacakt|alacak|istihdam|kontenjan|alımı\s+yapılacaktır)",
    re.I,
)
GENDER_QUOTA_RE = re.compile(
    r"\(?\s*([\d.,]+)\s*\)?\s*(erkek|kadın|bayan)\b",
    re.I,
)
# Prefer explicit KPSS word; avoid bare P2 from PDF noise.
KPSS_RE = re.compile(r"\bKPSS(?:\s*\([A-Z]\))?\b|\bKPSSP?\d{1,3}\b", re.I)
TYT_RE = re.compile(r"\bTYT\b", re.I)
NOKPSS_RE = re.compile(r"KPSS\s*(?:şartı\s*)?(?:aranmaz|yok)|kpss['']?siz|sınavsız", re.I)
AGE_RANGE_RE = re.compile(
    r"(?:yaş|yaşı)\s*(?:aralığı\s*)?(?:en\s+az\s*)?(\d{2})\s*[-–/]\s*(\d{2})",
    re.I,
)
AGE_MAX_RE = re.compile(
    r"(?:en\s+fazla|en\s+çok)\s*(\d{2})\s*yaş|"
    r"(\d{2})\s*yaşını\s*(?:bitirmemiş|doldurmamış)|"
    r"(\d{2})\s*yaşından\s*gün\s*almamış",
    re.I,
)
AGE_MIN_RE = re.compile(
    r"(?:en\s+az)\s*(\d{2})\s*yaş|"
    r"(\d{2})\s*yaşını\s*(?:doldurmuş|tamamlamış|tamamladıktan)",
    re.I,
)
BIRTH_RANGE_RE = re.compile(
    r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*[-–]\s*(\d{1,2}[./]\d{1,2}[./]\d{4})\s*"
    r"tarihleri\s*arasında\s*doğmuş",
    re.I,
)
DATE_RE = re.compile(r"\b(\d{1,2}[./]\d{1,2}[./]\d{2,4})\b")
# "07 - 13 Ağustos 2026"
TR_RANGE_RE = re.compile(
    rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+({MONTHS_TR})\s+(\d{{4}})",
    re.I,
)
LICENSE_RE = re.compile(
    r"\b([AMBCDE]|A1|A2|B1|BE|C1|C1E|CE|D1|D1E|DE)\s*(?:sınıfı)?\s*ehliyet",
    re.I,
)
APP_START_RE = re.compile(
    r"(?:başvuru(?:lar)?(?:ın)?\s*(?:başlangıç|start|tarihi)?[^\n.]{0,40}?)"
    r"(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
    re.I,
)
APP_END_RE = re.compile(
    r"(?:son\s*başvuru|başvuru(?:lar)?(?:ın)?\s*(?:bitiş|sonu|kapanış)[^\n.]{0,40}?)"
    r"(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
    re.I,
)
HEIGHT_RE = re.compile(
    r"(?:kadınlar\s*için\s*)?(\d{3})\s*cm[^\n.]{0,40}(?:erkekler\s*için\s*)?(\d{3})\s*cm|"
    r"erkekler\s*için\s*(\d{3})\s*cm[^\n.]{0,40}kadınlar\s*için\s*(\d{3})\s*cm",
    re.I,
)
BMI_RE = re.compile(
    r"beden\s*kitle\s*indeksi[^\n.]{0,40}?(\d{2})\s*\(?dahil\)?\s*(?:ile|-|–)\s*(\d{2})",
    re.I,
)

EDU_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("doktora", re.compile(r"\bdoktora\b", re.I)),
    ("yuksek_lisans", re.compile(r"\byüksek\s*lisans\b|\bmaster\b", re.I)),
    ("lisans", re.compile(r"\blisans\b|\bfakülte\b", re.I)),
    ("onlisans", re.compile(r"\bön\s*lisans\b|\bonlisans\b", re.I)),
    ("lise", re.compile(r"\blise\b|\bmeslek\s+lisesi\b|\blise\s+ve\s+dengi\b", re.I)),
    ("ortaokul", re.compile(r"\bortaokul\b|\bilköğretim\b", re.I)),
]

MILITARY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("completed", re.compile(r"askerlik\s*(?:hizmetini\s*)?(?:yapmış|tamamlamış)", re.I)),
    ("exempt", re.compile(r"askerlik(?:ten)?\s*muaf|muaf\s*olmak", re.I)),
    ("deferred", re.compile(r"tecilli|tecil\s*ettirmiş", re.I)),
    ("any", re.compile(r"askerlik\s*(?:durumu\s*)?(?:şart\s*)?(?:değil|aranmaz|fark\s*etmez)", re.I)),
]

GENDER_FEMALE_RE = re.compile(r"\bkadın\b|\bbayan\b", re.I)
GENDER_MALE_RE = re.compile(r"\berkek\b", re.I)

_RIZE = "Ri" + "ze"
PROVINCE_NAMES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin",
    "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan",
    "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta",
    "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla",
    "Muş", "Nevşehir", "Niğde", "Ordu", _RIZE, "Sakarya", "Samsun", "Siirt", "Sinop",
    "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat",
    "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın",
    "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce",
]


def _pick_quota(blob: str, title: str | None, evidence: dict[str, str]) -> int | None:
    m = TOTAL_QUOTA_RE.search(blob)
    if m:
        n = _parse_tr_int(m.group(1))
        if n is not None and not _looks_like_year(n) and 1 <= n <= 50000:
            evidence["quota"] = m.group(0)[:120]
            return n
    m = QUOTA_CONTEXT_RE.search(blob)
    if m:
        n = _parse_tr_int(m.group(1))
        if n is not None and not _looks_like_year(n) and 1 <= n <= 50000:
            evidence["quota"] = m.group(0)[:120]
            return n
    # Title: "860 GELİR…" / "45 SÖZLEŞMELİ…" — reject years like 2026
    if title:
        tm = re.search(r"\b(\d{1,5})\b", title)
        if tm:
            n = _parse_tr_int(tm.group(1))
            if n is not None and not _looks_like_year(n) and 1 <= n <= 50000:
                evidence["quota"] = f"title:{tm.group(0)}"
                return n
    return None


def parse_structured_criteria(
    *,
    content_text: str,
    title: str | None = None,
    institution: str | None = None,
    listing_fingerprint: str | None = None,
) -> StructuredCriteria:
    """Heuristic extraction from plain announcement text (HTML or PDF extract)."""
    text = content_text or ""
    blob = "\n".join(x for x in [title or "", institution or "", text] if x)
    evidence: dict[str, str] = {}
    conf = 0.15

    quota = _pick_quota(blob, title, evidence)
    if quota is not None:
        conf += 0.15 if "title:" not in evidence.get("quota", "") else 0.08

    # Gender split quotas (PMYO-style)
    male_q = female_q = None
    for gm in GENDER_QUOTA_RE.finditer(blob):
        n = _parse_tr_int(gm.group(1))
        label = gm.group(2).casefold()
        if n is None or _looks_like_year(n):
            continue
        if label.startswith("erkek"):
            male_q = n
            evidence["quota_male"] = gm.group(0)[:80]
        else:
            female_q = n
            evidence["quota_female"] = gm.group(0)[:80]
    if male_q is not None and female_q is not None and quota is None:
        quota = male_q + female_q
        evidence["quota"] = f"erkek+kadın={quota}"
        conf += 0.12

    kpss_requirement = "unknown"
    if NOKPSS_RE.search(blob):
        kpss_requirement = "nokpss"
        evidence["kpss_requirement"] = NOKPSS_RE.search(blob).group(0)[:80]
        conf += 0.1
    elif TYT_RE.search(blob) and not KPSS_RE.search(blob):
        kpss_requirement = "tyt"
        evidence["kpss_requirement"] = TYT_RE.search(blob).group(0)[:80]
        conf += 0.12
    elif KPSS_RE.search(blob):
        kpss_requirement = "kpss"
        evidence["kpss_requirement"] = KPSS_RE.search(blob).group(0)[:80]
        conf += 0.12
    elif TYT_RE.search(blob):
        # Both possible — prefer noting TYT in evidence, keep kpss if also present
        evidence["score_tyt"] = TYT_RE.search(blob).group(0)[:80]

    education_level_hints: list[str] = []
    for code, pat in EDU_PATTERNS:
        mm = pat.search(blob)
        if mm:
            education_level_hints.append(code)
            evidence[f"edu_{code}"] = mm.group(0)[:60]
    if education_level_hints:
        conf += 0.08

    min_age = max_age = None
    rm = AGE_RANGE_RE.search(blob)
    if rm:
        min_age, max_age = int(rm.group(1)), int(rm.group(2))
        if min_age > max_age:
            min_age, max_age = max_age, min_age
        evidence["age_range"] = rm.group(0)[:80]
        conf += 0.12
    else:
        mx = AGE_MAX_RE.search(blob)
        if mx:
            max_age = int(next(g for g in mx.groups() if g))
            evidence["max_age"] = mx.group(0)[:80]
            conf += 0.08
        mn = AGE_MIN_RE.search(blob)
        if mn:
            min_age = int(next(g for g in mn.groups() if g))
            evidence["min_age"] = mn.group(0)[:80]
            conf += 0.08
    br = BIRTH_RANGE_RE.search(blob)
    if br:
        evidence["birth_range"] = br.group(0)[:100]
        conf += 0.05

    gender = None
    has_f = bool(GENDER_FEMALE_RE.search(blob))
    has_m = bool(GENDER_MALE_RE.search(blob))
    if male_q is not None and female_q is not None:
        gender = "any"
        evidence["gender"] = f"erkek:{male_q} kadın:{female_q}"
        conf += 0.06
    elif has_f and not has_m:
        gender = "female"
        evidence["gender"] = "kadın/bayan"
        conf += 0.05
    elif has_m and not has_f:
        gender = "male"
        evidence["gender"] = "erkek"
        conf += 0.05
    elif has_f and has_m:
        gender = "any"

    military_hints: list[str] = []
    for code, pat in MILITARY_PATTERNS:
        mm = pat.search(blob)
        if mm:
            military_hints.append(code)
            evidence[f"military_{code}"] = mm.group(0)[:80]
    if military_hints:
        conf += 0.05

    license_class_hints = sorted({m.group(1).upper() for m in LICENSE_RE.finditer(blob)})
    if license_class_hints:
        evidence["license"] = ",".join(license_class_hints)
        conf += 0.05

    hm = HEIGHT_RE.search(blob)
    if hm:
        evidence["height_cm"] = hm.group(0)[:100]
        conf += 0.04
    bm = BMI_RE.search(blob)
    if bm:
        evidence["bmi"] = bm.group(0)[:100]
        conf += 0.04

    province_hints: list[str] = []
    for name in PROVINCE_NAMES:
        if re.search(rf"\b{re.escape(name)}\b", blob, re.I):
            province_hints.append(name)
    province_hints = province_hints[:25]
    if province_hints:
        conf += 0.08
        evidence["provinces"] = ",".join(province_hints[:8])

    application_start_hint = application_end_hint = None
    tr = TR_RANGE_RE.search(blob)
    if tr:
        d1, d2, month, year = tr.group(1), tr.group(2), tr.group(3), tr.group(4)
        application_start_hint = f"{d1} {month} {year}"
        application_end_hint = f"{d2} {month} {year}"
        evidence["application_window"] = tr.group(0)[:100]
        conf += 0.12
    else:
        sm = APP_START_RE.search(blob)
        if sm:
            application_start_hint = sm.group(1)
            evidence["application_start"] = sm.group(0)[:100]
            conf += 0.05
        em = APP_END_RE.search(blob)
        if em:
            application_end_hint = em.group(1)
            evidence["application_end"] = em.group(0)[:100]
            conf += 0.08
        if application_start_hint is None and application_end_hint is None:
            # Only use numeric dates if near "başvuru"
            near = re.search(
                r"başvuru[^\n]{0,80}" + DATE_RE.pattern + r"[^\n]{0,40}" + DATE_RE.pattern,
                blob,
                re.I,
            )
            if near:
                dates = DATE_RE.findall(near.group(0))
                if len(dates) >= 2:
                    application_start_hint, application_end_hint = dates[0], dates[1]
                    evidence["dates_fallback"] = f"{dates[0]} .. {dates[1]}"
                    conf += 0.05

    profession_hint = None
    if title:
        profession_hint = re.sub(r"^\s*\d+\s*", "", title).strip()[:120] or None

    field_of_study_hints: list[str] = []
    for mm in re.finditer(
        r"((?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+){0,4})\s+"
        r"(?:Mühendisliği|Öğretmenliği|Fakültesi|Bölümü|Programı))",
        blob,
    ):
        field_of_study_hints.append(mm.group(1).strip())
    seen: set[str] = set()
    uniq: list[str] = []
    for f in field_of_study_hints:
        key = f.casefold()
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    field_of_study_hints = uniq[:15]
    if field_of_study_hints:
        conf += 0.08
        evidence["fields"] = "; ".join(field_of_study_hints[:3])

    notes = (
        "Heuristic StructuredCriteria only. Map education/province hints to Bildirio "
        "reference ids offline via data/refs snapshot. Human review required."
    )
    return StructuredCriteria(
        listing_fingerprint=listing_fingerprint,
        title=title,
        institution_name=institution,
        quota=quota,
        kpss_requirement=kpss_requirement,
        education_level_hints=education_level_hints,
        field_of_study_hints=field_of_study_hints,
        province_hints=province_hints,
        min_age=min_age,
        max_age=max_age,
        gender=gender,
        military_hints=military_hints,
        license_class_hints=license_class_hints,
        application_start_hint=application_start_hint,
        application_end_hint=application_end_hint,
        profession_hint=profession_hint,
        evidence=evidence,
        confidence=round(min(conf, 0.92), 2),
        notes=notes,
    )
