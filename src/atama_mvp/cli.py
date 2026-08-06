from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from atama_mvp.central import listing_row_to_central, write_jsonl
from atama_mvp.enrich import enrich_collected
from atama_mvp.fetchers.ilan_gov import fetch_ilan_gov
from atama_mvp.fetchers.ilan_gov_detail import inspect_bundle
from atama_mvp.fetchers.kariyer_kapisi import fetch_kariyer_kapisi
from atama_mvp.fetchers.sbb_kamuilan import fetch_sbb_kamuilan
from atama_mvp.models import RawListing
from atama_mvp.notify import format_new_candidates, send_telegram_message, telegram_configured
from atama_mvp.store import Store


def cmd_fetch(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    collected: list[RawListing] = []
    failures: list[str] = []
    source_logs: list[str] = []
    attempted = 0

    def _run(label: str, fn) -> None:
        nonlocal attempted
        attempted += 1
        print(f"[{label}] starting…", flush=True)
        t0 = time.perf_counter()
        try:
            items = fn()
            elapsed = time.perf_counter() - t0
            line = f"[{label}] ok in {elapsed:.1f}s — {len(items)} ilan"
            print(line, flush=True)
            source_logs.append(line)
            collected.extend(items)
        except Exception as exc:  # noqa: BLE001 — isolate source failures for cron
            elapsed = time.perf_counter() - t0
            err = f"{type(exc).__name__}: {exc}"
            line = f"[{label}] FAILED after {elapsed:.1f}s — {err}"
            failures.append(line)
            source_logs.append(line)
            print(line, file=sys.stderr, flush=True)

    if args.source in ("all", "kk", "kariyer_kapisi"):
        _run("kariyer_kapisi", fetch_kariyer_kapisi)
    if args.source in ("all", "sbb", "sbb_kamuilan"):
        _run("sbb_kamuilan", fetch_sbb_kamuilan)
    if args.source in ("all", "ilan", "ilan_gov"):
        _run("ilan_gov", fetch_ilan_gov)

    if not collected and failures:
        print("All sources failed.", file=sys.stderr)
        return 1

    print(f"[enrich] parsing criteria for {len(collected)} listing(s)…", flush=True)
    detail_ilan = not getattr(args, "skip_detail", False)
    enriched, criteria_by_fp, enrich_status = enrich_collected(
        collected, detail_ilan=detail_ilan
    )
    stats = store.upsert_listings(
        enriched,
        criteria_by_fp=criteria_by_fp,
        enrich_status_by_fp=enrich_status,
    )

    new_fps = list(stats.get("new_fingerprints") or [])
    counts = store.counts()
    detail_n = sum(1 for s in enrich_status.values() if s == "detail")
    print(
        f"Upsert: new={stats['new']} updated={stats['seen']} | "
        f"enrich_detail={detail_n} | Counts: {counts}",
        flush=True,
    )
    if failures:
        print(f"Source failures ({len(failures)}/{attempted})", file=sys.stderr, flush=True)

    if args.notify_telegram:
        if not telegram_configured():
            print("Telegram skipped: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", file=sys.stderr)
            return 0
        parts: list[str] = [
            "atama-mvp fetch",
            "",
            *source_logs,
            "",
            f"Upsert: new={stats['new']} updated={stats['seen']} | detail={detail_n}",
            f"DB: {counts}",
        ]
        if new_fps:
            rows = store.get_by_fingerprints(new_fps)
            parts.append("")
            parts.append(format_new_candidates(rows))
            print(f"Telegram will include {len(new_fps)} new candidate(s).", flush=True)
        send_telegram_message("\n".join(parts))
        print("Telegram sent.", flush=True)
    return 0


def cmd_reset_db(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    print(f"Resetting backend={store.backend()} …", flush=True)
    store.reset()
    print("Done. Counts:", store.counts(), flush=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    payload = {"backend": store.backend(), "counts": store.counts()}
    if args.recent:
        payload["recent"] = [dict(r) for r in store.recent(args.recent)]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else None)
    rows = store.pending(limit=args.limit)
    if not rows:
        print("No pending items.")
        return 0

    print(f"{len(rows)} pending item(s). Commands: a=approve r=reject s=skip q=quit\n")
    for row in rows:
        print("=" * 72)
        print(f"[{row['source']}] {row['title']}")
        print(f"institution: {row['institution_name']}")
        print(f"url:         {row['external_url']}")
        print(f"window:      {row['application_window']}")
        print(f"quota:       {row['quota']}")
        print(f"kpss:        {row['kpss_requirement']}")
        print(f"edu:         {row['education_levels']}")
        print(f"age:         {row['min_age']}–{row['max_age']}")
        print(f"provinces:   {row['provinces']}")
        print(f"enrich:      {row['enrich_status']} conf={row['confidence']}")
        print(f"fingerprint: {row['fingerprint']}")
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
    rows = store.all_for_export(args.status)
    payload = [listing_row_to_central(row) for row in rows]
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


def cmd_inspect_ilan(args: argparse.Namespace) -> int:
    """Fetch one ilan.gov detail (GetAdDetail), dump JSON, optional criteria parse. No Telegram."""
    from atama_mvp.criteria import parse_structured_criteria

    ad_id = args.id
    if not ad_id:
        print("Resolving latest personel listing from AdsByFilter…", flush=True)
        items = fetch_ilan_gov(max_per_category=5)
        if not items:
            print("No ilan.gov listings found.", file=sys.stderr)
            return 1
        ad_id = items[0].external_id
        print(f"Using id={ad_id} title={items[0].title}", flush=True)

    print(f"[inspect-ilan] GetAdDetail id={ad_id}…", flush=True)
    t0 = time.perf_counter()
    bundle = inspect_bundle(ad_id)
    elapsed = time.perf_counter() - t0
    print(
        f"[inspect-ilan] ok in {elapsed:.1f}s — html={bundle['content_html_len']} "
        f"text={bundle['content_text_len']} chars",
        flush=True,
    )

    criteria = parse_structured_criteria(
        content_text=bundle["content_text"],
        title=(bundle.get("meta") or {}).get("title"),
        institution=(bundle.get("meta") or {}).get("advertiserName"),
    )
    out_payload = {
        **bundle,
        "structured_criteria": criteria.to_dict(),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ilan_{ad_id}.json"
    out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)

    sc = criteria.to_dict()
    print("StructuredCriteria preview:", flush=True)
    for key in (
        "quota",
        "kpss_requirement",
        "education_level_hints",
        "province_hints",
        "min_age",
        "max_age",
        "gender",
        "military_hints",
        "confidence",
        "evidence",
    ):
        if key in sc and sc[key] not in (None, [], {}):
            print(f"  {key}: {sc[key]}", flush=True)
    return 0


def cmd_export_central(args: argparse.Namespace) -> int:
    """Export all (or filtered) listings to canonical JSONL for shared/central use."""
    store = Store(Path(args.db) if args.db else None)
    rows = store.all_for_export(args.status)
    records = [listing_row_to_central(row) for row in rows]
    out = Path(args.out)
    n = write_jsonl(out, records)
    meta = {
        "schema": "atama_mvp.central_export.v2",
        "count": n,
        "status_filter": args.status,
        "out": str(out),
    }
    meta_path = out.with_suffix(out.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {n} records → {out}")
    print(f"Meta → {meta_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atama-mvp",
        description="Human-in-the-loop ingest for Kariyer Kapısı, SBB Kamu İlan, ilan.gov.tr",
    )
    p.add_argument("--db", default=None, help="SQLite path (default: ./data/mvp.sqlite3)")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="Pull sources, enrich criteria, upsert lean rows")
    f.add_argument(
        "--source",
        default="all",
        choices=["all", "kk", "kariyer_kapisi", "sbb", "sbb_kamuilan", "ilan", "ilan_gov"],
    )
    f.add_argument(
        "--notify-telegram",
        action="store_true",
        help="Send Telegram digest from enriched rows",
    )
    f.add_argument(
        "--skip-detail",
        action="store_true",
        help="Skip ilan.gov GetAdDetail (list-only criteria)",
    )
    f.set_defaults(func=cmd_fetch)

    reset = sub.add_parser("reset-db", help="Wipe listings/review tables (Turso or local SQLite)")
    reset.set_defaults(func=cmd_reset_db)

    s = sub.add_parser("status", help="Show review_status counts")
    s.add_argument("--recent", type=int, default=0, help="Also print N most recently seen listings")
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

    insp = sub.add_parser(
        "inspect-ilan",
        help="Fetch one ilan.gov AdDetail + dump JSON/text (research; no Telegram)",
    )
    insp.add_argument("--id", default=None, help="ilan.gov ad id (default: first from list fetch)")
    insp.add_argument("--out-dir", default="data/inspect", help="Dump directory (gitignored under data/)")
    insp.set_defaults(func=cmd_inspect_ilan)

    c = sub.add_parser(
        "export-central",
        help="Export listings to canonical JSONL (shared/central dump)",
    )
    c.add_argument("--status", default="all", choices=["all", "pending", "approved", "rejected", "skipped"])
    c.add_argument("--out", default="data/central/listings.jsonl")
    c.set_defaults(func=cmd_export_central)
    return p


def main(argv: list[str] | None = None) -> int:
    from atama_mvp.store import load_dotenv

    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
