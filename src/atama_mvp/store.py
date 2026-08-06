from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

from .criteria import StructuredCriteria
from .models import RawListing
from .turso_client import TursoClient, turso_configured

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "mvp.sqlite3"

# Lean schema: no raw HTML dumps. Meaningful Bildirio-aligned fields live on the row.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS listings (
    fingerprint TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_url TEXT NOT NULL,
    title TEXT NOT NULL,
    institution_name TEXT,
    category TEXT,
    published_at TEXT,
    application_window TEXT,
    application_start TEXT,
    application_end TEXT,
    quota INTEGER,
    kpss_requirement TEXT,
    education_levels TEXT,
    provinces TEXT,
    fields_of_study TEXT,
    min_age INTEGER,
    max_age INTEGER,
    gender TEXT,
    profession_hint TEXT,
    military_hints TEXT,
    license_hints TEXT,
    confidence REAL,
    enrich_status TEXT NOT NULL DEFAULT 'none',
    evidence_json TEXT,
    criteria_json TEXT,
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending','approved','rejected','skipped'))
);

CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT,
    created_at REAL NOT NULL
);
"""

DROP_LEGACY_SQL = """
DROP TABLE IF EXISTS enrichment_drafts;
DROP TABLE IF EXISTS review_events;
DROP TABLE IF EXISTS listings;
"""


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE from .env into os.environ if not already set."""
    env_path = path or Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _json_list(values: list[str] | None) -> str | None:
    if not values:
        return None
    return json.dumps(values, ensure_ascii=False)


def criteria_columns(criteria: StructuredCriteria | None) -> dict[str, Any]:
    if criteria is None:
        return {
            "application_start": None,
            "application_end": None,
            "quota": None,
            "kpss_requirement": None,
            "education_levels": None,
            "provinces": None,
            "fields_of_study": None,
            "min_age": None,
            "max_age": None,
            "gender": None,
            "profession_hint": None,
            "military_hints": None,
            "license_hints": None,
            "confidence": None,
            "evidence_json": None,
            "criteria_json": None,
        }
    # Cap province list in column; full list stays in criteria_json.
    provinces = criteria.province_hints[:20] if criteria.province_hints else []
    return {
        "application_start": criteria.application_start_hint,
        "application_end": criteria.application_end_hint,
        "quota": criteria.quota,
        "kpss_requirement": criteria.kpss_requirement,
        "education_levels": _json_list(criteria.education_level_hints),
        "provinces": _json_list(provinces),
        "fields_of_study": _json_list(criteria.field_of_study_hints[:10] or None),
        "min_age": criteria.min_age,
        "max_age": criteria.max_age,
        "gender": criteria.gender,
        "profession_hint": criteria.profession_hint,
        "military_hints": _json_list(criteria.military_hints or None),
        "license_hints": _json_list(criteria.license_class_hints or None),
        "confidence": criteria.confidence,
        "evidence_json": json.dumps(criteria.evidence, ensure_ascii=False) if criteria.evidence else None,
        "criteria_json": json.dumps(criteria.to_dict(), ensure_ascii=False),
    }


class Store:
    """Local SQLite or Turso (when TURSO_DATABASE_URL + TURSO_AUTH_TOKEN set)."""

    def __init__(self, db_path: Path | None = None) -> None:
        load_dotenv()
        self.use_turso = turso_configured()
        self.db_path = db_path or DEFAULT_DB
        if not self.use_turso:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._turso: TursoClient | None = TursoClient() if self.use_turso else None
        self._init()

    def backend(self) -> str:
        return "turso" if self.use_turso else f"sqlite:{self.db_path}"

    def _connect(self) -> sqlite3.Connection:
        if self.use_turso:
            raise RuntimeError("local sqlite connect called while Turso is configured")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        if self.use_turso:
            assert self._turso is not None
            self._turso.executescript(SCHEMA_SQL)
            return
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def reset(self) -> None:
        """Drop all tables and recreate lean schema (wipes data)."""
        if self.use_turso:
            assert self._turso is not None
            self._turso.executescript(DROP_LEGACY_SQL)
            self._turso.executescript(SCHEMA_SQL)
            return
        if self.db_path.exists():
            self.db_path.unlink()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _execute(self, sql: str, args: Sequence[Any] | tuple[Any, ...] = ()) -> None:
        if self.use_turso:
            assert self._turso is not None
            self._turso.execute(sql, args)
            return
        with self._connect() as conn:
            conn.execute(sql, args)

    def _query(self, sql: str, args: Sequence[Any] | tuple[Any, ...] = ()) -> list[Any]:
        if self.use_turso:
            assert self._turso is not None
            return list(self._turso.query(sql, args))
        with self._connect() as conn:
            return list(conn.execute(sql, args))

    def upsert_listings(
        self,
        listings: Iterable[RawListing],
        *,
        criteria_by_fp: dict[str, StructuredCriteria] | None = None,
        enrich_status_by_fp: dict[str, str] | None = None,
    ) -> dict[str, object]:
        now = time.time()
        stats: dict[str, object] = {"new": 0, "seen": 0, "new_fingerprints": []}
        new_fps: list[str] = []
        criteria_by_fp = criteria_by_fp or {}
        enrich_status_by_fp = enrich_status_by_fp or {}

        for item in listings:
            row = self._query(
                "SELECT fingerprint FROM listings WHERE fingerprint = ?",
                (item.fingerprint,),
            )
            crit = criteria_by_fp.get(item.fingerprint)
            cols = criteria_columns(crit)
            enrich_status = enrich_status_by_fp.get(item.fingerprint) or (
                "detail" if crit and crit.confidence >= 0.45 else ("list" if crit else "none")
            )
            # Prefer criteria window hints; keep source window as fallback display.
            app_window = item.application_window
            if crit and (crit.application_start_hint or crit.application_end_hint):
                parts = [p for p in [crit.application_start_hint, crit.application_end_hint] if p]
                if parts:
                    app_window = " – ".join(parts)

            values = (
                item.fingerprint,
                item.source,
                item.external_id,
                item.external_url,
                item.title,
                item.institution_name,
                item.category,
                item.published_at,
                app_window,
                cols["application_start"],
                cols["application_end"],
                cols["quota"],
                cols["kpss_requirement"],
                cols["education_levels"],
                cols["provinces"],
                cols["fields_of_study"],
                cols["min_age"],
                cols["max_age"],
                cols["gender"],
                cols["profession_hint"],
                cols["military_hints"],
                cols["license_hints"],
                cols["confidence"],
                enrich_status,
                cols["evidence_json"],
                cols["criteria_json"],
                now,
                now,
            )

            if not row:
                self._execute(
                    """
                    INSERT INTO listings (
                        fingerprint, source, external_id, external_url, title,
                        institution_name, category, published_at, application_window,
                        application_start, application_end, quota, kpss_requirement,
                        education_levels, provinces, fields_of_study, min_age, max_age,
                        gender, profession_hint, military_hints, license_hints,
                        confidence, enrich_status, evidence_json, criteria_json,
                        first_seen_at, last_seen_at, review_status
                    ) VALUES (
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                        'pending'
                    )
                    """,
                    values,
                )
                stats["new"] = int(stats["new"]) + 1
                new_fps.append(item.fingerprint)
            else:
                self._execute(
                    """
                    UPDATE listings SET
                        title = ?, institution_name = ?, category = ?,
                        published_at = ?, application_window = ?,
                        application_start = ?, application_end = ?,
                        quota = ?, kpss_requirement = ?, education_levels = ?,
                        provinces = ?, fields_of_study = ?, min_age = ?, max_age = ?,
                        gender = ?, profession_hint = ?, military_hints = ?,
                        license_hints = ?, confidence = ?, enrich_status = ?,
                        evidence_json = ?, criteria_json = ?,
                        last_seen_at = ?, external_url = ?
                    WHERE fingerprint = ?
                    """,
                    (
                        item.title,
                        item.institution_name,
                        item.category,
                        item.published_at,
                        app_window,
                        cols["application_start"],
                        cols["application_end"],
                        cols["quota"],
                        cols["kpss_requirement"],
                        cols["education_levels"],
                        cols["provinces"],
                        cols["fields_of_study"],
                        cols["min_age"],
                        cols["max_age"],
                        cols["gender"],
                        cols["profession_hint"],
                        cols["military_hints"],
                        cols["license_hints"],
                        cols["confidence"],
                        enrich_status,
                        cols["evidence_json"],
                        cols["criteria_json"],
                        now,
                        item.external_url,
                        item.fingerprint,
                    ),
                )
                stats["seen"] = int(stats["seen"]) + 1
        stats["new_fingerprints"] = new_fps
        return stats

    def get_by_fingerprints(self, fingerprints: list[str]) -> list[Any]:
        if not fingerprints:
            return []
        placeholders = ",".join("?" for _ in fingerprints)
        return self._query(
            f"""
            SELECT * FROM listings
            WHERE fingerprint IN ({placeholders})
            ORDER BY first_seen_at DESC
            """,
            fingerprints,
        )

    def pending(self, limit: int = 20) -> list[Any]:
        return self._query(
            """
            SELECT * FROM listings
            WHERE review_status = 'pending'
            ORDER BY first_seen_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def set_status(self, fingerprint: str, status: str, note: str | None = None) -> None:
        if status not in {"pending", "approved", "rejected", "skipped"}:
            raise ValueError(status)
        self._execute(
            "UPDATE listings SET review_status = ? WHERE fingerprint = ?",
            (status, fingerprint),
        )
        self._execute(
            """
            INSERT INTO review_events (fingerprint, action, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (fingerprint, status, note, time.time()),
        )

    def counts(self) -> dict[str, int]:
        rows = self._query("SELECT review_status, COUNT(*) AS c FROM listings GROUP BY review_status")
        out: dict[str, int] = {}
        for r in rows:
            out[str(r["review_status"])] = int(r["c"])
        total_rows = self._query("SELECT COUNT(*) AS c FROM listings")
        out["total"] = int(total_rows[0]["c"]) if total_rows else 0
        return out

    def recent(self, limit: int = 10) -> list[Any]:
        return self._query(
            """
            SELECT source, title, institution_name, quota, kpss_requirement,
                   max_age, education_levels, application_window, enrich_status,
                   confidence, external_url, review_status
            FROM listings
            ORDER BY last_seen_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def all_for_export(self, status: str = "all") -> list[Any]:
        return self._query(
            """
            SELECT * FROM listings
            WHERE (? = 'all' OR review_status = ?)
            ORDER BY first_seen_at DESC
            """,
            (status, status),
        )
