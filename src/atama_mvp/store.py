from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from .models import EnrichmentDraft, RawListing

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "mvp.sqlite3"


class Store:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
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
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (fingerprint) REFERENCES listings(fingerprint)
                );

                CREATE TABLE IF NOT EXISTS review_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    action TEXT NOT NULL,
                    note TEXT,
                    created_at REAL NOT NULL
                );
                """
            )

    def upsert_listings(self, listings: Iterable[RawListing]) -> dict[str, object]:
        now = time.time()
        stats: dict[str, object] = {"new": 0, "seen": 0, "new_fingerprints": []}
        new_fps: list[str] = []
        with self._connect() as conn:
            for item in listings:
                row = conn.execute(
                    "SELECT fingerprint FROM listings WHERE fingerprint = ?",
                    (item.fingerprint,),
                ).fetchone()
                payload = (
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
                    json.dumps(item.raw, ensure_ascii=False),
                    now,
                    now,
                )
                if row is None:
                    conn.execute(
                        """
                        INSERT INTO listings (
                            fingerprint, source, external_id, external_url, title,
                            institution_name, category, published_at, application_window,
                            image_url, summary, raw_json, first_seen_at, last_seen_at,
                            review_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                        """,
                        payload,
                    )
                    stats["new"] = int(stats["new"]) + 1
                    new_fps.append(item.fingerprint)
                else:
                    conn.execute(
                        """
                        UPDATE listings SET
                            title = ?, institution_name = ?, category = ?,
                            published_at = ?, application_window = ?, image_url = ?,
                            summary = ?, raw_json = ?, last_seen_at = ?
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
                            json.dumps(item.raw, ensure_ascii=False),
                            now,
                            item.fingerprint,
                        ),
                    )
                    stats["seen"] = int(stats["seen"]) + 1
        stats["new_fingerprints"] = new_fps
        return stats

    def get_by_fingerprints(self, fingerprints: list[str]) -> list[sqlite3.Row]:
        if not fingerprints:
            return []
        placeholders = ",".join("?" for _ in fingerprints)
        with self._connect() as conn:
            return list(
                conn.execute(
                    f"""
                    SELECT l.*, d.draft_json
                    FROM listings l
                    LEFT JOIN enrichment_drafts d ON d.fingerprint = l.fingerprint
                    WHERE l.fingerprint IN ({placeholders})
                    ORDER BY l.first_seen_at DESC
                    """,
                    fingerprints,
                )
            )

    def save_draft(self, draft: EnrichmentDraft) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO enrichment_drafts (fingerprint, draft_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    draft_json = excluded.draft_json,
                    updated_at = excluded.updated_at
                """,
                (draft.listing_fingerprint, json.dumps(draft.to_dict(), ensure_ascii=False), time.time()),
            )

    def pending(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return list(
                conn.execute(
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
            )

    def set_status(self, fingerprint: str, status: str, note: str | None = None) -> None:
        if status not in {"pending", "approved", "rejected", "skipped"}:
            raise ValueError(status)
        with self._connect() as conn:
            conn.execute(
                "UPDATE listings SET review_status = ? WHERE fingerprint = ?",
                (status, fingerprint),
            )
            conn.execute(
                """
                INSERT INTO review_events (fingerprint, action, note, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (fingerprint, status, note, time.time()),
            )

    def counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT review_status, COUNT(*) AS c FROM listings GROUP BY review_status"
            ).fetchall()
            out = {r["review_status"]: r["c"] for r in rows}
            total = conn.execute("SELECT COUNT(*) AS c FROM listings").fetchone()["c"]
            out["total"] = total
            return out
