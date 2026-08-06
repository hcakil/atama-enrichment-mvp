#!/usr/bin/env python3
"""Snapshot public Bildirio /api/v1/references/* into data/refs/ (gitignored)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://bildirio.app/api/v1"
REF_PATHS = [
    "/references/education-levels",
    "/references/professions",
    "/references/fields-of-study",
    "/references/lise-types",
    "/references/lise-fields-of-study",
    "/references/license-classes",
    "/references/provinces",
    "/references/cities",
    "/references/certificate-names",
    "/references/yds-languages",
]


def fetch_json(path: str) -> dict:
    url = BASE + path
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AtamaEnrichmentMVP/0.1 (+research; refs snapshot)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "data" / "refs"
    out_dir.mkdir(parents=True, exist_ok=True)
    index: dict[str, int | str] = {"base": BASE}

    for path in REF_PATHS:
        name = path.rstrip("/").split("/")[-1]
        print(f"GET {path} …", flush=True)
        try:
            payload = fetch_json(path)
        except urllib.error.HTTPError as exc:
            print(f"  FAIL HTTP {exc.code}", file=sys.stderr)
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {exc}", file=sys.stderr)
            continue
        data = payload.get("data")
        n = len(data) if isinstance(data, list) else (1 if data is not None else 0)
        out_path = out_dir / f"{name}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        index[name] = n
        print(f"  wrote {out_path.name} n={n}", flush=True)

    (out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Done → {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
