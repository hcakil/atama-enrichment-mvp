from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


DEFAULT_UA = (
    "Mozilla/5.0 (compatible; AtamaEnrichmentMVP/0.1; "
    "+https://github.com/hcakil/atama-enrichment-mvp)"
)


def fetch_bytes(
    url: str,
    *,
    timeout: int = 45,
    retries: int = 3,
    backoff_sec: float = 2.0,
    headers: dict[str, str] | None = None,
) -> bytes:
    """GET url with retries. Raises last error if all attempts fail."""
    hdrs = {
        "User-Agent": DEFAULT_UA,
        "Accept": "*/*",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
    if headers:
        hdrs.update(headers)

    last: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt >= retries:
                break
            time.sleep(backoff_sec * attempt)
    assert last is not None
    raise last


def fetch_text(
    url: str,
    *,
    timeout: int = 45,
    retries: int = 3,
    backoff_sec: float = 2.0,
    headers: dict[str, str] | None = None,
    encoding: str | None = None,
) -> str:
    raw = fetch_bytes(
        url,
        timeout=timeout,
        retries=retries,
        backoff_sec=backoff_sec,
        headers=headers,
    )
    if encoding:
        return raw.decode(encoding, errors="replace")
    return raw.decode("utf-8", errors="replace")


def post_json(
    url: str,
    payload: dict,
    *,
    timeout: int = 45,
    retries: int = 3,
    backoff_sec: float = 2.0,
    headers: dict[str, str] | None = None,
) -> dict:
    """POST JSON body, return parsed object. Raises last error if all attempts fail."""
    hdrs = {
        "User-Agent": DEFAULT_UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
    if headers:
        hdrs.update(headers)

    body = json.dumps(payload).encode("utf-8")
    last: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = exc
            if attempt >= retries:
                break
            time.sleep(backoff_sec * attempt)
    assert last is not None
    raise last
