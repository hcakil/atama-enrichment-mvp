from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

from .models import EnrichmentDraft, RawListing
from .turso_client import TursoClient, turso_configured

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "mvp.sqlite3"

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
    image_url TEXT,
    summary TEXT,
    raw_json TEXT NOT NULL,
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending','approved','rejected','skipped'))
);

CREATE TABLE IF NOT EXISTS enrichment_drafts (
    fingerprint TEXT PRIMARY KEY,
    draft_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT,
    created_at REAL NOT NULL
);
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

    def upsert_listings(self, listings: Iterable[RawListing]) -> dict[str, object]:
        now = time.time()
        stats: dict[str, object] = {"new": 0, "seen": 0, "new_fingerprints": []}
        new_fps: list[str] = []
        for item in listings:
            row = self._query(
                "SELECT fingerprint FROM listings WHERE fingerprint = ?",
                (item.fingerprint,),
            )
            raw_json = json.dumps(item.raw, ensure_ascii=False)
            if not row:
                self._execute(
                    """
                    INSERT INTO listings (
                        fingerprint, source, external_id, external_url, title,
                        institution_name, category, published_at, application_window,
                        image_url, summary, raw_json, first_seen_at, last_seen_at,
                        review_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        item.fingerprint,
                        item.source,
                        item.external_id,
                        item.external_url,
                        item.title,
                        item.institution_name,
                        item.category,
                        item.published_at,
                        item.application_window,
                        item.image_url,
                        item.summary,
                        raw_json,
                        now,
                        now,
                    ),
                )
                stats["new"] = int(stats["new"]) + 1
                new_fps.append(item.fingerprint)
            else:
                self._execute(
                    """
                    UPDATE listings SET
                        title = ?, institution_name = ?, category = ?,
                        published_at = ?, application_window = ?, image_url = ?,
                        summary = ?, raw_json = ?, last_seen_at = ?,
                        external_url = ?
                    WHERE fingerprint = ?
                    """,
                    (
                        item.title,
                        item.institution_name,
                        item.category,
                        item.published_at,
                        item.application_window,
                        item.image_url,
                        item.summary,
                        raw_json,
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
            SELECT l.*, d.draft_json
            FROM listings l
            LEFT JOIN enrichment_drafts d ON d.fingerprint = l.fingerprint
            WHERE l.fingerprint IN ({placeholders})
            ORDER BY l.first_seen_at DESC
            """,
            fingerprints,
        )

    def save_draft(self, draft: EnrichmentDraft) -> None:
        self._execute(
            """
            INSERT INTO enrichment_drafts (fingerprint, draft_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                draft_json = excluded.draft_json,
                updated_at = excluded.updated_at
            """,
            (draft.listing_fingerprint, json.dumps(draft.to_dict(), ensure_ascii=False), time.time()),
        )

    def pending(self, limit: int = 20) -> list[Any]:
        return self._query(
            """
            SELECT l.*, d.draft_json
            FROM listings l
            LEFT JOIN enrichment_drafts d ON d.fingerprint = l.fingerprint
            WHERE l.review_status = 'pending'
            ORDER BY l.first_seen_at DESC
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
            SELECT source, title, institution_name, application_window, published_at,
                   external_url, review_status, first_seen_at
            FROM listings
            ORDER BY last_seen_at DESC
            LIMIT ?
            """,
            (limit,),
        )
