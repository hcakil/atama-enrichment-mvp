from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Sequence


def turso_configured() -> bool:
    return bool(os.environ.get("TURSO_DATABASE_URL", "").strip() and os.environ.get("TURSO_AUTH_TOKEN", "").strip())


def _http_base(url: str) -> str:
    u = url.strip().rstrip("/")
    if u.startswith("libsql://"):
        return "https://" + u[len("libsql://") :]
    if u.startswith("turso://"):
        return "https://" + u[len("turso://") :]
    if u.startswith("https://") or u.startswith("http://"):
        return u
    return "https://" + u


def _arg(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        # libSQL has no bool; store as integer
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        # Hrana expects a JSON number for float, not a string.
        return {"type": "float", "value": float(value)}
    if isinstance(value, (bytes, bytearray)):
        import base64

        return {"type": "blob", "base64": base64.b64encode(value).decode("ascii")}
    return {"type": "text", "value": str(value)}


def _cell_value(cell: dict[str, Any]) -> Any:
    t = cell.get("type")
    if t == "null" or t is None:
        return None
    if t == "integer":
        v = cell.get("value")
        return int(v) if v is not None else None
    if t == "float":
        v = cell.get("value")
        return float(v) if v is not None else None
    if t == "text":
        return cell.get("value")
    if t == "blob":
        return cell.get("base64")
    return cell.get("value")


class TursoRow(dict):
    """dict that also supports sqlite3.Row-style index/key access."""

    def __getitem__(self, key: Any) -> Any:  # type: ignore[override]
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class TursoClient:
    """Minimal Turso SQL-over-HTTP client (stdlib)."""

    def __init__(self, database_url: str | None = None, auth_token: str | None = None) -> None:
        self.database_url = (database_url or os.environ.get("TURSO_DATABASE_URL", "")).strip()
        self.auth_token = (auth_token or os.environ.get("TURSO_AUTH_TOKEN", "")).strip()
        if not self.database_url or not self.auth_token:
            raise RuntimeError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are required")
        self.base = _http_base(self.database_url)

    def pipeline(self, statements: Sequence[tuple[str, Sequence[Any] | None]]) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        for sql, args in statements:
            stmt: dict[str, Any] = {"sql": sql}
            if args:
                stmt["args"] = [_arg(a) for a in args]
            requests.append({"type": "execute", "stmt": stmt})
        requests.append({"type": "close"})
        body = json.dumps({"requests": requests}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/v2/pipeline",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Turso HTTP {exc.code}: {detail}") from exc

        out: list[dict[str, Any]] = []
        for item in payload.get("results") or []:
            if item.get("type") == "error":
                err = item.get("error") or item
                raise RuntimeError(f"Turso execute error: {err}")
            if item.get("type") != "ok":
                continue
            response = item.get("response") or {}
            if response.get("type") == "close":
                continue
            if response.get("type") == "execute":
                out.append(response.get("result") or {})
        return out

    def execute(self, sql: str, args: Sequence[Any] | None = None) -> dict[str, Any]:
        results = self.pipeline([(sql, args)])
        return results[0] if results else {}

    def executescript(self, script: str) -> None:
        # Split on semicolons carefully enough for our DDL.
        parts = [p.strip() for p in script.split(";")]
        stmts = [(p, None) for p in parts if p]
        if stmts:
            self.pipeline(stmts)

    def query(self, sql: str, args: Sequence[Any] | None = None) -> list[TursoRow]:
        result = self.execute(sql, args)
        cols = [c.get("name") for c in (result.get("cols") or [])]
        rows: list[TursoRow] = []
        for raw in result.get("rows") or []:
            values = [_cell_value(cell) for cell in raw]
            rows.append(TursoRow(zip(cols, values)))
        return rows
