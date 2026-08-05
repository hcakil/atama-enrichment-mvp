from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atama_mvp.enrich import draft_from_listing
from atama_mvp.fetchers.kariyer_kapisi import fetch_kariyer_kapisi
from atama_mvp.fetchers.sbb_kamuilan import fetch_sbb_kamuilan
from atama_mvp.models import RawListing
from atama_mvp.notify import format_new_candidates, send_telegram_message, telegram_configured
from atama_mvp.store import Store


def cmd_fetch(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    collected: list[RawListing] = []
    failures: list[str] = []
    attempted = 0

    def _run(label: str, fn) -> None:
        nonlocal attempted
        attempted += 1
        print(f"Fetching {label}…")
        try:
            items = fn()
            print(f"  {len(items)} items")
            collected.extend(items)
        except Exception as exc:  # noqa: BLE001 — isolate source failures for cron
            msg = f"{label}: {type(exc).__name__}: {exc}"
            failures.append(msg)
            print(f"  FAILED: {msg}", file=sys.stderr)

    if args.source in ("all", "kk", "kariyer_kapisi"):
        _run("Kariyer Kapısı RSS", fetch_kariyer_kapisi)
    if args.source in ("all", "sbb", "sbb_kamuilan"):
        _run("SBB Kamu İlan homepage", fetch_sbb_kamuilan)

    if not collected and failures:
        print("All sources failed.", file=sys.stderr)
        return 1

    stats = store.upsert_listings(collected)
    for item in collected:
        store.save_draft(draft_from_listing(item))

    new_fps = list(stats.get("new_fingerprints") or [])
    print(f"Upsert: new={stats['new']} updated={stats['seen']}")
    print("Counts:", store.counts())
    if failures:
        print(f"Source failures ({len(failures)}/{attempted}):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)

    if args.notify_telegram:
        if not telegram_configured():
            print("Telegram skipped: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", file=sys.stderr)
            return 0
        parts: list[str] = []
        if new_fps:
            rows = store.get_by_fingerprints(new_fps)
            parts.append(format_new_candidates(rows))
            print(f"Telegram will include {len(new_fps)} new candidate(s).")
        elif failures:
            parts.append("Yeni aday yok; bazı kaynaklar başarısız.")
        else:
            print("No new candidates; Telegram not sent.")
            return 0
        if failures:
            parts.append("")
            parts.append(f"Kaynak hataları ({len(failures)}/{attempted}):")
            for f in failures:
                parts.append(f"• {f}")
        send_telegram_message("\n".join(parts))
        print("Telegram sent.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    print(json.dumps(store.counts(), ensure_ascii=False, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    rows = store.pending(limit=args.limit)
    if not rows:
        print("No pending items.")
        return 0

    print(f"{len(rows)} pending item(s). Commands: a=approve r=reject s=skip q=quit\n")
    for row in rows:
        draft = json.loads(row["draft_json"]) if row["draft_json"] else {}
        print("=" * 72)
        print(f"[{row['source']}] {row['title']}")
        print(f"institution: {row['institution_name']}")
        print(f"url:         {row['external_url']}")
        print(f"published:   {row['published_at']}")
        print(f"window:      {row['application_window']}")
        print(f"category:    {row['category']}")
        print(f"fingerprint: {row['fingerprint']}")
        if draft:
            print("--- draft ---")
            print(f"  suggested_title:        {draft.get('suggested_title')}")
            print(f"  suggested_institution:  {draft.get('suggested_institution')}")
            print(f"  suggested_quota:        {draft.get('suggested_quota')}")
            print(f"  suggested_kpss:         {draft.get('suggested_kpss')}")
            print(f"  confidence:             {draft.get('confidence')}")
            print(f"  notes: {draft.get('notes')}")
        while True:
            choice = input("action [a/r/s/q]: ").strip().lower()
            if choice in {"a", "r", "s", "q"}:
                break
        if choice == "q":
            print("Stopped.")
            return 0
        mapping = {"a": "approved", "r": "rejected", "s": "skipped"}
        store.set_status(row["fingerprint"], mapping[choice])
        print(f"→ {mapping[choice]}")
    print("Done. Counts:", store.counts())
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    status = args.status
    with store._connect() as conn:
        rows = conn.execute(
            """
            SELECT l.*, d.draft_json
            FROM listings l
            LEFT JOIN enrichment_drafts d ON d.fingerprint = l.fingerprint
            WHERE (? = 'all' OR l.review_status = ?)
            ORDER BY l.first_seen_at DESC
            """,
            (status, status),
        ).fetchall()
    payload = []
    for row in rows:
        item = dict(row)
        if item.get("draft_json"):
            item["draft"] = json.loads(item.pop("draft_json"))
        else:
            item.pop("draft_json", None)
        if item.get("raw_json"):
            item["raw"] = json.loads(item.pop("raw_json"))
        payload.append(item)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} rows → {out}")
    return 0


def cmd_notify_test(args: argparse.Namespace) -> int:
    if not telegram_configured():
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first.", file=sys.stderr)
        return 1
    send_telegram_message(args.message)
    print("Test message sent.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atama-mvp",
        description="Human-in-the-loop ingest for Kariyer Kapısı RSS + SBB Kamu İlan",
    )
    p.add_argument("--db", default=None, help="SQLite path (default: ./data/mvp.sqlite3)")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="Pull sources, upsert, write enrichment drafts")
    f.add_argument(
        "--source",
        default="all",
        choices=["all", "kk", "kariyer_kapisi", "sbb", "sbb_kamuilan"],
    )
    f.add_argument(
        "--notify-telegram",
        action="store_true",
        help="If new listings appear, send a Telegram digest (needs env vars)",
    )
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("status", help="Show review_status counts")
    s.set_defaults(func=cmd_status)

    r = sub.add_parser("review", help="Interactive approve/reject queue")
    r.add_argument("--limit", type=int, default=20)
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("export", help="Export listings JSON")
    e.add_argument("--status", default="approved", choices=["all", "pending", "approved", "rejected", "skipped"])
    e.add_argument("--out", default="data/export.json")
    e.set_defaults(func=cmd_export)

    n = sub.add_parser("notify-test", help="Send a test Telegram message")
    n.add_argument("--message", default="atama-mvp: Telegram bağlantısı çalışıyor.")
    n.set_defaults(func=cmd_notify_test)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
