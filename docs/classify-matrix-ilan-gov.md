# Classification matrix — ilan.gov.tr detail vs Bildirio JobPostingDetail

Spike sample: **Gelir İdaresi Başkanlığı — 860 Gelir Uzman Yardımcısı**  
- Source: `GET …/AdDetail/GetAdDetail?Id=2188158`  
- Dump: `data/inspect/ilan_2188158.json` (gitignored under `data/`)  
- Heuristic output: `StructuredCriteria` via `atama_mvp.criteria`

## How to reproduce

```bash
export PYTHONPATH=src
python3 -m atama_mvp.cli inspect-ilan --id 2188158
python3 scripts/snapshot_bildirio_refs.py   # → data/refs/
```

## Matrix

| Bildirio `JobPostingDetail` field | In this announcement? | Auto extract (spike) | Difficulty | Notes |
|-----------------------------------|-----------------------|----------------------|------------|-------|
| `title` | Yes | Yes (API meta) | Easy | Direct from detail |
| `institution` | Yes | Yes (`advertiserName`) | Easy | |
| `external_url` | Yes | Yes | Easy | slug URL |
| `quota` | Yes (860 + city table) | Yes (`860`) | Easy | Total + per-province table in HTML |
| `min_age` / `max_age` | Yes (`35 yaşını doldurmamış`) | Heuristic → `max_age` | Med | Birth-date wording also present |
| `kpss_requirement` | Yes (KPSS(A), KPSSP17/18/… ≥65) | Yes → `kpss` | Easy–med | Score types still free-text in evidence |
| `education_level_ids` | Yes (4 yıllık lisans + fakülteler) | Hint `lisans` | Med | Faculty list → fields-of-study next |
| `required_field_of_study_ids` | Yes (hukuk, SBF, İİBF, …) | Partial / weak | Hard | Needs dedicated faculty-list parser |
| `province_codes` | Yes (assignment kontenjan table) | Name hints (many) | Med | Map via `data/refs/provinces.json` |
| `application_start` / `application_end` | Dense “başvuru” text | Weak on sample | Med | Prefer dated section headings |
| `gender` | No in sample | — | Easy if present | |
| `military_requirement` | No in sample | — | Med | |
| `required_license_class_codes` | No | — | Easy if present | |
| `profession_id` | Implicit (Gelir Uzman Yrd.) | Title hint | Hard | Fuzzy map `professions.json` |
| `variants` | City/ilçe kontenjan rows | No | Hard | Natural `JobPostingVariant` source |

## Bildirio references (public, no auth)

Base: `https://bildirio.app/api/v1` — snapshot counts from spike:

| Catalog | n |
|---------|---|
| education-levels | 5 |
| professions | 158 |
| fields-of-study | 862 |
| license-classes | 17 |
| provinces / cities | 81 |
| certificate-names | 49 |
| yds-languages | 18 |

Use as **offline vocabulary** for mapping hints → ids. Do not write to Bildirio APIs.

## Verdict

1. List cards alone are not enough for matching.  
2. `GetAdDetail.content` HTML **is** enough raw material for a large JobPostingDetail subset.  
3. Highest ROI parsers next: **quota**, **KPSS**, **education level**, **province table**, **application window**, then field-of-study lists.  
4. Human `review` remains mandatory before any user-facing match.
