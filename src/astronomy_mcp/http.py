"""Shared async HTTP helper with a small in-memory TTL cache.

Several upstream services are rate limited (Launch Library allows 15 requests
per hour without a key), and forecasts only change every hour or so, so callers
pass a `ttl` in seconds and repeated calls inside that window are served from
memory.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

USER_AGENT = "astronomy-mcp/0.3"

_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, Any]] = {}


class UpstreamError(RuntimeError):
    pass


def _key(url: str, params: dict[str, Any] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
    return url, tuple(sorted((k, str(v)) for k, v in (params or {}).items()))


async def _fetch(
    url: str, params: dict[str, Any] | None, source: str, timeout: float, accept: tuple[int, ...] = (200,)
) -> httpx.Response:
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        try:
            resp = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Could not reach {source}: {exc}") from exc
    if resp.status_code == 429:
        raise UpstreamError(f"{source} rate limit reached; try again later.")
    if resp.status_code not in accept:
        raise UpstreamError(f"{source} returned HTTP {resp.status_code}: {resp.text[:300]}")
    return resp


async def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    source: str,
    ttl: float = 0,
    timeout: float = 30,
    accept: tuple[int, ...] = (200,),
) -> Any:
    """GET a JSON document, caching the parsed result for `ttl` seconds.

    `accept` lists the HTTP statuses that carry a usable body (SBDB answers an ambiguous
    name with 300 and a list of candidates).
    """
    key = _key(url, params)
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    resp = await _fetch(url, params, source, timeout, accept)
    try:
        data = resp.json()
    except ValueError as exc:
        raise UpstreamError(f"{source} returned a non-JSON response: {resp.text[:200]}") from exc
    if ttl > 0:
        _cache[key] = (time.monotonic() + ttl, data)
    return data


async def get_bytes(url: str, *, source: str, timeout: float = 60) -> bytes:
    """GET a raw document (used for one-off bulk downloads, never cached in memory)."""
    return (await _fetch(url, None, source, timeout)).content


async def get_json_file(
    url: str,
    params: dict[str, Any] | None,
    path: Path,
    *,
    source: str,
    max_age: float,
    timeout: float = 60,
) -> Any:
    """GET a JSON document through an on-disk cache that survives restarts.

    For bulk data that changes slowly and whose hosts limit downloads (CelesTrak blocks
    clients that fetch the same file more than once every two hours). A stale copy is
    served if the refresh fails.
    """
    try:
        fresh = time.time() - path.stat().st_mtime < max_age
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        fresh, cached = False, None
    if fresh:
        return cached
    try:
        data = await get_json(url, params, source=source, timeout=timeout)
    except UpstreamError:
        if cached is not None:
            return cached
        raise
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def clear_cache() -> None:
    _cache.clear()
