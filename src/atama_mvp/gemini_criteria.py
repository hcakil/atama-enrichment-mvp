from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from .criteria import StructuredCriteria

# In-process cache: content hash → criteria dict (avoids re-paying for same PDF text).
_CACHE: dict[str, dict[str, Any]] = {}
_USAGE: dict[str, int] = {
    "calls": 0,
    "skipped_cache": 0,
    "skipped_conf": 0,
    "skipped_short": 0,
    "prompt_chars": 0,
    "prompt_tokens_est": 0,
    "candidates_tokens": 0,
}


def gemini_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def gemini_model() -> str:
    return (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()


def llm_min_conf() -> float:
    raw = os.environ.get("ATAMA_LLM_MIN_CONF", "0.55").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.55


def llm_max_chars() -> int:
    raw = os.environ.get("ATAMA_LLM_MAX_CHARS", "10000").strip()
    try:
        return max(2000, int(raw))
    except ValueError:
        return 10000


def usage_snapshot() -> dict[str, int]:
    return dict(_USAGE)


def reset_usage() -> None:
    for k in _USAGE:
        _USAGE[k] = 0
    _CACHE.clear()


def _est_tokens(chars: int) -> int:
    # Rough TR/English mix: ~3.5 chars/token
    return max(1, chars // 3)


_SECTION_HINT = re.compile(
    r"(başvuru|aranan\s+şart|nitelik|kontenjan|kpss|tyt|yaş|eğitim|öğrenim|"
    r"askerlik|kota|alınacak|duyuru)",
    re.I,
)


def truncate_for_llm(text: str, *, max_chars: int | None = None) -> str:
    """
    Keep head + keyword-rich windows to cut tokens without losing criteria sections.
    """
    limit = max_chars if max_chars is not None else llm_max_chars()
    text = (text or "").strip()
    if len(text) <= limit:
        return text

    head_n = min(3500, limit // 2)
    chunks = [text[:head_n]]
    used = head_n
    # Collect windows around criterion keywords
    for m in _SECTION_HINT.finditer(text):
        start = max(0, m.start() - 200)
        end = min(len(text), m.end() + 500)
        piece = text[start:end]
        if piece in "".join(chunks):
            continue
        if used + len(piece) + 20 > limit:
            break
        chunks.append("\n…\n" + piece)
        used += len(piece) + 20
    out = "".join(chunks)
    if len(out) > limit:
        out = out[:limit]
    return out + "\n\n[truncated for token budget]"


def llm_force() -> bool:
    flag = os.environ.get("ATAMA_LLM_FORCE", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def needs_llm(regex_crit: StructuredCriteria, *, detail_text_len: int) -> bool:
    """
    Call Gemini when detail text exists and (force mode OR regex looks incomplete).
    """
    if detail_text_len < 120:
        _USAGE["skipped_short"] += 1
        return False
    if llm_force():
        return True
    if regex_crit.confidence >= llm_min_conf():
        has_window = bool(regex_crit.application_start_hint or regex_crit.application_end_hint)
        has_core = regex_crit.quota is not None or bool(regex_crit.education_level_hints)
        if has_window or (has_core and regex_crit.confidence >= 0.7):
            _USAGE["skipped_conf"] += 1
            return False
    return True


_SYSTEM = """Sen Türk kamu personel alım duyurularından yapılandırılmış alan çıkaran bir asistanısın.
Sadece verilen metne dayan. Uydurma. Emin değilsen null / boş dizi kullan.
Her dolu alan için evidence içine metinden kısa birebir alıntı koy.
kpss_requirement yalnız: kpss | nokpss | tyt | unknown
gender yalnız: male | female | any | null
education_level_hints: lise, onlisans, lisans, yuksek_lisans, doktora, ortaokul
quota: toplam kişi sayısı (yıl sayısı değil; 2026 kota değildir)
Yanıtın yalnızca JSON olsun."""


def _schema_hint() -> dict[str, Any]:
    # Gemini responseSchema uses OpenAPI-like types (uppercase) + nullable.
    return {
        "type": "OBJECT",
        "properties": {
            "quota": {"type": "INTEGER", "nullable": True},
            "kpss_requirement": {
                "type": "STRING",
                "enum": ["kpss", "nokpss", "tyt", "unknown"],
            },
            "education_level_hints": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "field_of_study_hints": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "province_hints": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "min_age": {"type": "INTEGER", "nullable": True},
            "max_age": {"type": "INTEGER", "nullable": True},
            "gender": {"type": "STRING", "nullable": True},
            "military_hints": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "license_class_hints": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "application_start_hint": {"type": "STRING", "nullable": True},
            "application_end_hint": {"type": "STRING", "nullable": True},
            "profession_hint": {"type": "STRING", "nullable": True},
            "evidence": {"type": "OBJECT"},
            "confidence": {"type": "NUMBER"},
            "notes": {"type": "STRING", "nullable": True},
        },
        "required": ["kpss_requirement", "confidence", "evidence"],
    }


def extract_criteria_gemini(
    *,
    content_text: str,
    title: str | None = None,
    institution: str | None = None,
    listing_fingerprint: str | None = None,
    force: bool = False,
) -> tuple[StructuredCriteria | None, dict[str, Any]]:
    """
    Returns (criteria|None, meta) where meta has skipped/reason/usage/tokens.
    """
    meta: dict[str, Any] = {"provider": "gemini", "model": gemini_model()}
    if not gemini_configured():
        meta["skipped"] = "no_api_key"
        return None, meta

    trimmed = truncate_for_llm(content_text)
    meta["prompt_chars"] = len(trimmed)
    meta["prompt_tokens_est"] = _est_tokens(len(trimmed))

    digest = hashlib.sha256(trimmed.encode("utf-8")).hexdigest()[:32]
    meta["content_hash"] = digest
    if digest in _CACHE and not force:
        _USAGE["skipped_cache"] += 1
        meta["skipped"] = "cache_hit"
        cached = _CACHE[digest]
        return _dict_to_criteria(cached, title, institution, listing_fingerprint), meta

    api_key = os.environ["GEMINI_API_KEY"].strip()
    model = gemini_model()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    user_blob = "\n".join(
        x
        for x in [
            f"Başlık: {title}" if title else "",
            f"Kurum: {institution}" if institution else "",
            "Duyuru metni:",
            trimmed,
        ]
        if x
    )
    body = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user_blob}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": _schema_hint(),
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    payload: dict[str, Any] | None = None
    last_err = ""
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            last_err = f"HTTP {exc.code}: {detail}"
            if exc.code == 429:
                # Free tier often ~5 RPM; back off and retry.
                time.sleep(min(20, 4 * attempt))
                continue
            meta["error"] = last_err
            return None, meta
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
            meta["error"] = last_err
            return None, meta
    if payload is None:
        meta["error"] = last_err or "empty_response"
        return None, meta

    usage = payload.get("usageMetadata") or {}
    prompt_tok = int(usage.get("promptTokenCount") or 0)
    cand_tok = int(usage.get("candidatesTokenCount") or 0)
    _USAGE["calls"] += 1
    _USAGE["prompt_chars"] += len(trimmed)
    _USAGE["prompt_tokens_est"] += prompt_tok or _est_tokens(len(trimmed))
    _USAGE["candidates_tokens"] += cand_tok
    meta["usage"] = {
        "promptTokenCount": prompt_tok,
        "candidatesTokenCount": cand_tok,
        "totalTokenCount": int(usage.get("totalTokenCount") or (prompt_tok + cand_tok)),
    }

    try:
        text_out = payload["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text_out)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        meta["error"] = f"bad_response: {exc}"
        return None, meta

    _CACHE[digest] = data
    crit = _dict_to_criteria(data, title, institution, listing_fingerprint)
    # Prefer slightly lower than 1.0 — human review still required.
    if crit.confidence and crit.confidence > 0.9:
        crit.confidence = 0.9
    crit.notes = (crit.notes or "") + " | source=gemini"
    meta["skipped"] = None
    return crit, meta


def _dict_to_criteria(
    data: dict[str, Any],
    title: str | None,
    institution: str | None,
    listing_fingerprint: str | None,
) -> StructuredCriteria:
    def _list(key: str) -> list[str]:
        val = data.get(key) or []
        if not isinstance(val, list):
            return []
        return [str(x) for x in val if x]

    kpss = data.get("kpss_requirement") or "unknown"
    if kpss not in {"kpss", "nokpss", "tyt", "unknown"}:
        kpss = "unknown"
    gender = data.get("gender")
    if gender not in {"male", "female", "any", None}:
        gender = None
    conf = data.get("confidence")
    try:
        conf_f = float(conf) if conf is not None else 0.5
    except (TypeError, ValueError):
        conf_f = 0.5
    evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    evidence = {str(k): str(v)[:200] for k, v in evidence.items()}

    quota = data.get("quota")
    try:
        quota_i = int(quota) if quota is not None else None
    except (TypeError, ValueError):
        quota_i = None
    if quota_i is not None and 1990 <= quota_i <= 2100:
        quota_i = None  # reject year-as-quota

    return StructuredCriteria(
        listing_fingerprint=listing_fingerprint,
        title=title,
        institution_name=institution,
        quota=quota_i,
        kpss_requirement=kpss,
        education_level_hints=_list("education_level_hints"),
        field_of_study_hints=_list("field_of_study_hints")[:15],
        province_hints=_list("province_hints")[:25],
        min_age=int(data["min_age"]) if data.get("min_age") is not None else None,
        max_age=int(data["max_age"]) if data.get("max_age") is not None else None,
        gender=gender,
        military_hints=_list("military_hints"),
        license_class_hints=_list("license_class_hints"),
        application_start_hint=data.get("application_start_hint"),
        application_end_hint=data.get("application_end_hint"),
        profession_hint=data.get("profession_hint") or title,
        evidence=evidence,
        confidence=round(min(max(conf_f, 0.0), 0.9), 2),
        notes=str(data.get("notes") or "Gemini structured extract. Human review required."),
    )


def merge_prefer_llm(
    regex_crit: StructuredCriteria,
    llm_crit: StructuredCriteria | None,
) -> StructuredCriteria:
    if llm_crit is None:
        return regex_crit
    # Prefer LLM for core fields when present; keep regex evidence extras.
    evidence = dict(regex_crit.evidence)
    evidence.update(llm_crit.evidence or {})
    evidence["enricher"] = "gemini+regex"
    return StructuredCriteria(
        listing_fingerprint=llm_crit.listing_fingerprint or regex_crit.listing_fingerprint,
        title=llm_crit.title or regex_crit.title,
        institution_name=llm_crit.institution_name or regex_crit.institution_name,
        quota=llm_crit.quota if llm_crit.quota is not None else regex_crit.quota,
        kpss_requirement=(
            llm_crit.kpss_requirement
            if llm_crit.kpss_requirement and llm_crit.kpss_requirement != "unknown"
            else regex_crit.kpss_requirement
        ),
        education_level_hints=llm_crit.education_level_hints or regex_crit.education_level_hints,
        field_of_study_hints=llm_crit.field_of_study_hints or regex_crit.field_of_study_hints,
        province_hints=llm_crit.province_hints or regex_crit.province_hints,
        min_age=llm_crit.min_age if llm_crit.min_age is not None else regex_crit.min_age,
        max_age=llm_crit.max_age if llm_crit.max_age is not None else regex_crit.max_age,
        gender=llm_crit.gender or regex_crit.gender,
        military_hints=llm_crit.military_hints or regex_crit.military_hints,
        license_class_hints=llm_crit.license_class_hints or regex_crit.license_class_hints,
        application_start_hint=llm_crit.application_start_hint or regex_crit.application_start_hint,
        application_end_hint=llm_crit.application_end_hint or regex_crit.application_end_hint,
        profession_hint=llm_crit.profession_hint or regex_crit.profession_hint,
        evidence=evidence,
        confidence=max(regex_crit.confidence, llm_crit.confidence),
        notes=llm_crit.notes,
    )
