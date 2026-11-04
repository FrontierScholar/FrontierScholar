"""HTTP client for fs-api v1. Standard library only.

Client().call("search/paper", {"query": "..."}) returns the response body (dict). Errors raise FsError with the
server's code, message, field, limit and hint. Rate limits, timeouts and dropped connections are retried with
backoff before giving up.
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

DEFAULT_BASE = "https://frontier-scholar.com"      # the public endpoint; FS_BASE points elsewhere
RETRY_CODES = {"rate_limited", "unavailable"}     # 1.2.1: a timeout is deterministic (the same call times out again)
# 1.2.3: non-JSON answers from a proxy in front of the service (too many requests, restarting, tunnel down)
RETRY_HTTP = {"http_429", "http_502", "http_503"}
MAX_WAIT = 90          # seconds; a longer retry_after (a daily allowance used up) is reported, not slept through


class FsError(Exception):
    def __init__(self, code: str, message: str = "", *, status: Optional[int] = None, details: Optional[dict] = None):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.status, self.details = code, message, status, details or {}

    def as_dict(self) -> Dict[str, Any]:
        out = {"code": self.code, "message": self.message}
        if self.status:
            out["status"] = self.status
        out.update({k: v for k, v in self.details.items() if k not in ("code", "message", "status")})
        return out


def _opener(base: str):
    host = urllib.request.urlparse(base).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1"):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))   # never send loopback through a proxy
    return urllib.request.build_opener()


class Client:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, *, timeout: float = 60,
                 retries: int = 4, on_wait: Optional[Callable[[FsError, float, int], None]] = None):
        self.api_key = api_key or os.environ.get("FS_API_KEY") or os.environ.get("FRONTIER_SCHOLAR_API_KEY") or ""
        self.base = (base_url or os.environ.get("FS_BASE") or DEFAULT_BASE).rstrip("/")
        self.timeout, self.retries = timeout, retries
        self.on_wait = on_wait                 # called before each retry with (error, seconds, attempt)
        self._open = _opener(self.base).open

    def __repr__(self) -> str:
        return f"Client(base_url={self.base!r}, api_key={'set' if self.api_key else 'missing'})"

    def health(self) -> Dict[str, Any]:
        with self._open(urllib.request.Request(self.base + "/api/v1/fs/health"), timeout=10) as r:
            return json.loads(r.read())

    def call(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # No key is a valid anonymous call on the public endpoint; the server decides (and answers 401 if it needs one).
        # Only unset values are dropped; 0 is sent, so the server can reject e.g. topk=0 instead of using its default.
        body = json.dumps({k: v for k, v in (arguments or {}).items()
                           if v is not None and v is not False and v != "" and v != []}).encode()
        delay = 0.5
        for attempt in range(self.retries + 1):
            headers = {"Content-Type": "application/json", "User-Agent": "frontier-scholar-fs/1"}
            if self.api_key:                       # anonymous calls on the public endpoint carry no key
                headers["X-API-Key"] = self.api_key
            req = urllib.request.Request(f"{self.base}/api/v1/fs/{command}", data=body, method="POST", headers=headers)
            try:
                with self._open(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as exc:
                try:
                    err = json.loads(exc.read()).get("error") or {}
                except ValueError:
                    err = {}
                error = FsError(err.get("code") or f"http_{exc.code}", err.get("message", ""), status=exc.code, details=err)
                try:
                    retry_after = float(err.get("retry_after") or exc.headers.get("Retry-After") or 0)
                except (TypeError, ValueError):
                    retry_after = 0
            except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
                error = FsError("unavailable", f"cannot reach {self.base}: {getattr(exc, 'reason', exc)}")
                retry_after = 0
            if (error.code not in RETRY_CODES | RETRY_HTTP) or attempt == self.retries or retry_after > MAX_WAIT:
                raise error
            wait = max(retry_after, delay) + random.uniform(0, delay / 2)
            if self.on_wait:
                self.on_wait(error, wait, attempt + 1)
            time.sleep(wait)
            delay *= 2
        raise AssertionError("unreachable")
