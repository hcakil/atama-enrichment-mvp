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
    kpss_requirement: str | None = None  # kpss | nokpss | unknown
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


QUOTA_CONTEXT_RE = re.compile(
    r"(?:üzere[, ]+|toplam\s+)?(\d{1,4})\s*(?:\([^)]+\)\s*)?"
    r"(?:kişilik\s+)?(?:personel|memur|işçi|uzman|öğretim|adet)?"
    r"[^\n.]{0,60}(?:alınacakt|istihdam|kontenjan)",
    re.I,
)
KPSS_RE = re.compile(r"\bKPSS\b|\bP\d{1,3}\b", re.I)
NOKPSS_RE = re.compile(r"KPSS\s*(?:şartı\s*)?(?:aranmaz|yok)|kpss['']?siz|sınavsız", re.I)
AGE_RANGE_RE = re.compile(
    r"(?:yaş|yaşı)\s*(?:aralığı\s*)?(?:en\s+az\s*)?(\d{2})\s*[-–/]\s*(\d{2})",
    re.I,
)
AGE_MAX_RE = re.compile(
    r"(?:en\s+fazla|en\s+çok)\s*(\d{2})\s*yaş|"
    r"(\d{2})\s*yaşını\s*(?:bitirmemiş|doldurmamış)",
    re.I,
)
AGE_MIN_RE = re.compile(
    r"(?:en\s+az)\s*(\d{2})\s*yaş|(\d{2})\s*yaşını\s*doldurmuş",
    re.I,
)
DATE_RE = re.compile(r"\b(\d{1,2}[./]\d{1,2}[./]\d{2,4})\b")
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

EDU_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("doktora", re.compile(r"\bdoktora\b", re.I)),
    ("yuksek_lisans", re.compile(r"\byüksek\s*lisans\b|\bmaster\b", re.I)),
    ("lisans", re.compile(r"\blisans\b|\bfakülte\b", re.I)),
    ("onlisans", re.compile(r"\bön\s*lisans\b|\bonlisans\b", re.I)),
    ("lise", re.compile(r"\blise\b|\bmeslek\s+lisesi\b", re.I)),
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

# 81 provinces (ASCII-safe construction for Rize)
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


def parse_structured_criteria(
    *,
    content_text: str,
    title: str | None = None,
    institution: str | None = None,
    listing_fingerprint: str | None = None,
) -> StructuredCriteria:
    """Heuristic extraction from plain announcement text."""
    text = content_text or ""
    blob = "\n".join(x for x in [title or "", institution or "", text] if x)
    evidence: dict[str, str] = {}
    conf = 0.15

    quota = None
    m = QUOTA_CONTEXT_RE.search(blob)
    if m:
        quota = int(m.group(1))
        evidence["quota"] = m.group(0)[:120]
        conf += 0.15
    elif title:
        tm = re.search(r"\b(\d{2,4})\b", title)
        if tm and int(tm.group(1)) >= 10:
            quota = int(tm.group(1))
            evidence["quota"] = f"title:{tm.group(0)}"
            conf += 0.08

    kpss_requirement = "unknown"
    if NOKPSS_RE.search(blob):
        kpss_requirement = "nokpss"
        evidence["kpss_requirement"] = NOKPSS_RE.search(blob).group(0)[:80]
        conf += 0.1
    elif KPSS_RE.search(blob):
        kpss_requirement = "kpss"
        evidence["kpss_requirement"] = KPSS_RE.search(blob).group(0)[:80]
        conf += 0.12

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
            conf += 0.06
        mn = AGE_MIN_RE.search(blob)
        if mn:
            min_age = int(next(g for g in mn.groups() if g))
            evidence["min_age"] = mn.group(0)[:80]
            conf += 0.06

    gender = None
    has_f = bool(GENDER_FEMALE_RE.search(blob))
    has_m = bool(GENDER_MALE_RE.search(blob))
    if has_f and not has_m:
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

    province_hints: list[str] = []
    upper_blob = blob
    for name in PROVINCE_NAMES:
        if re.search(rf"\b{re.escape(name)}\b", upper_blob, re.I):
            province_hints.append(name)
    province_hints = province_hints[:25]
    if province_hints:
        conf += 0.08
        evidence["provinces"] = ",".join(province_hints[:8])

    application_start_hint = application_end_hint = None
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
        dates = DATE_RE.findall(blob)
        if len(dates) >= 2:
            application_start_hint, application_end_hint = dates[0], dates[1]
            evidence["dates_fallback"] = f"{dates[0]} .. {dates[1]}"
            conf += 0.03

    profession_hint = None
    if title:
        # Drop leading quota digits from title for profession-ish hint
        profession_hint = re.sub(r"^\s*\d+\s*", "", title).strip()[:120] or None

    field_of_study_hints: list[str] = []
    for mm in re.finditer(
        r"((?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+){0,4})\s+"
        r"(?:Mühendisliği|Öğretmenliği|Fakültesi|Bölümü|Programı))",
        blob,
    ):
        field_of_study_hints.append(mm.group(1).strip())
    # dedupe preserve order
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
        confidence=round(min(conf, 0.85), 2),
        notes=notes,
    )
