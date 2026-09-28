"""Shared async HTTP client with per-host rate limiting and provider health tracking."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.config import app_config
from backend.utils.logging_setup import get_logger
from backend.utils import provider_health

log = get_logger("provider")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


class ProviderError(Exception):
    def __init__(self, provider: str, message: str, status: int | None = None):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.message = message
        self.status = status

    @property
    def rate_limited(self) -> bool:
        return self.status == 429


class RateLimiter:
    """Sliding-window limiter: at most N requests per 60s per host."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def limit_for(self, host: str) -> int:
        limits = app_config().get("rate_limits_per_minute", {})
        return int(limits.get(host, limits.get("default", 60)))

    async def acquire(self, host: str) -> None:
        limit = self.limit_for(host)
        async with self._locks[host]:
            q = self._events[host]
            while True:
                now = time.monotonic()
                while q and now - q[0] > 60:
                    q.popleft()
                if len(q) < limit:
                    q.append(now)
                    return
                await asyncio.sleep(max(0.05, 60 - (now - q[0])))


limiter = RateLimiter()
_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=True,
            headers={"User-Agent": BROWSER_UA, "Accept": "*/*"},
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def request(
    provider: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    data: Any = None,
    timeout: float | None = None,
    expect_json: bool = True,
    retries: int = 1,
) -> Any:
    """Perform a rate-limited request, recording provider health. Raises ProviderError."""
    host = urlparse(url).hostname or "default"
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        await limiter.acquire(host)
        provider_health.record_request(provider)
        started = time.monotonic()
        try:
            resp = await client().request(
                method, url, params=params, headers=headers, json=json_body, data=data,
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
            elapsed = (time.monotonic() - started) * 1000
            if resp.status_code == 429:
                provider_health.record_failure(provider, "HTTP 429 rate limited", rate_limited=True)
                raise ProviderError(provider, "rate limited by upstream (HTTP 429)", 429)
            if resp.status_code >= 400:
                raise ProviderError(provider, f"HTTP {resp.status_code}", resp.status_code)
            log.info(f"{provider} {method} {host}{urlparse(url).path} {resp.status_code} {elapsed:.0f}ms")
            provider_health.record_success(provider)
            if not expect_json:
                return resp.text
            return resp.json()
        except ProviderError as exc:
            last_exc = exc
            if exc.status in (429, 401, 403, 404):
                break
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = ProviderError(provider, f"{type(exc).__name__}: {exc}".strip(": "))
        if attempt < retries:
            await asyncio.sleep(0.6 * (attempt + 1))
    assert last_exc is not None
    err = last_exc if isinstance(last_exc, ProviderError) else ProviderError(provider, str(last_exc))
    if not err.rate_limited:
        provider_health.record_failure(provider, err.message)
    log.warning(f"{provider} failed {method} {host}{urlparse(url).path}: {err.message}")
    raise err


async def get_json(provider: str, url: str, **kw: Any) -> Any:
    return await request(provider, "GET", url, **kw)


async def get_text(provider: str, url: str, **kw: Any) -> str:
    return await request(provider, "GET", url, expect_json=False, **kw)
