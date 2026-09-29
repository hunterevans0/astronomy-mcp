"""Shared async HTTP helper with a small in-memory TTL cache.

Several upstream services are rate limited (Launch Library allows 15 requests
per hour without a key), and forecasts only change every hour or so, so callers
pass a `ttl` in seconds and repeated calls inside that window are served from
memory.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

USER_AGENT = "astronomy-mcp/0.3"

_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, Any]] = {}


class UpstreamError(RuntimeError):
    pass


def _key(url: str, params: dict[str, Any] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
    return url, tuple(sorted((k, str(v)) for k, v in (params or {}).items()))


async def _fetch(url: str, params: dict[str, Any] | None, source: str, timeout: float) -> httpx.Response:
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        try:
            resp = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Could not reach {source}: {exc}") from exc
    if resp.status_code == 429:
        raise UpstreamError(f"{source} rate limit reached; try again later.")
    if resp.status_code != 200:
        raise UpstreamError(f"{source} returned HTTP {resp.status_code}: {resp.text[:300]}")
    return resp


async def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    source: str,
    ttl: float = 0,
    timeout: float = 30,
) -> Any:
    """GET a JSON document, caching the parsed result for `ttl` seconds."""
    key = _key(url, params)
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    resp = await _fetch(url, params, source, timeout)
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


def clear_cache() -> None:
    _cache.clear()
