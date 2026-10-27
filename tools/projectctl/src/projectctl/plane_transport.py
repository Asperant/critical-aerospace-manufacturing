"""One serialized, paced API v1 request path; no secret-bearing diagnostics."""

import math
from contextlib import suppress
from email.utils import parsedate_to_datetime
from threading import RLock
from time import monotonic, sleep, time

import httpx


class PlaneError(ValueError):
    """Safe diagnostics: never include credential values or response bodies."""


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


def rate_headers(headers, attempt=1):
    remaining = _number(headers.get("X-RateLimit-Remaining"))
    reset = _number(headers.get("X-RateLimit-Reset"))
    retry = _number(headers.get("Retry-After"))
    if retry is None and headers.get("Retry-After"):
        with suppress(ValueError, TypeError, OverflowError):
            retry = max(
                0, parsedate_to_datetime(headers["Retry-After"]).timestamp() - time()
            )
    delay = (
        retry
        if retry is not None
        else max(0, reset - time())
        if reset is not None
        else min(2**attempt, 30)
    )
    return {
        "remaining": remaining,
        "reset_epoch": reset,
        "retry_after_seconds": retry,
        "delay_seconds": delay,
    }


class RequestGate:
    """Transient process-wide serialization/pacing, shared by reads and writes."""

    def __init__(self):
        self.lock = RLock()
        self.last_started = None
        self.not_before = 0.0
        self.last_interval = 1.25

    def wait(self, interval):
        target = self.not_before
        if self.last_started is not None:
            target = max(target, self.last_started + max(interval, self.last_interval))
        while target > monotonic():
            sleep(min(target - monotonic(), 30))
        self.last_started, self.last_interval = monotonic(), interval

    def defer(self, seconds):
        self.not_before = max(self.not_before, monotonic() + seconds)


GATE = RequestGate()


class PlaneStream:
    MAX_ATTEMPTS = 5

    def __init__(self, config, transport=None, gate=None):
        self.interval = config.request_interval_seconds
        self.gate = GATE if gate is None else gate
        self.events = []
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/") + "/api/v1/",
            headers={"X-API-Key": config.api_key},
            timeout=20,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def close(self):
        self._client.close()

    def defer(self, seconds):
        with self.gate.lock:
            self.gate.defer(seconds)

    def request(
        self, method, path, *, params=None, json=None, idempotent=False, attempt=1
    ):
        if (
            path.startswith("/")
            or ":" in path
            or ".." in path
            or method not in {"GET", "POST", "PATCH", "DELETE"}
        ):
            raise PlaneError("Unsafe Plane request path or method")
        limit = self.MAX_ATTEMPTS if method == "GET" or idempotent else 1
        with self.gate.lock:
            for retry in range(limit):
                self.gate.wait(self.interval)
                event = {
                    "method": method,
                    "path": "/api/v1/" + path,
                    "attempt": attempt + retry,
                }
                self.events.append(event)
                try:
                    response = self._client.request(
                        method, path, params=params, json=json
                    )
                except httpx.HTTPError:
                    event["outcome"] = "TRANSPORT_FAILURE"
                    self.gate.defer(min(2 ** (attempt + retry), 30))
                    raise PlaneError(
                        "Plane transport failure (details redacted)"
                    ) from None
                event["status"] = response.status_code
                rate = rate_headers(response.headers, attempt + retry)
                event["rate_limit"] = rate
                if (
                    response.status_code == 429
                    or rate["remaining"] == 0
                    or response.status_code >= 500
                    and rate["retry_after_seconds"] is not None
                ):
                    self.gate.defer(
                        rate["delay_seconds"]
                        if response.status_code == 429
                        or rate["retry_after_seconds"] is not None
                        or rate["reset_epoch"] is not None
                        else 60
                    )
                if response.status_code != 429 or limit == 1:
                    return response
            raise PlaneError(
                "Plane rate-limit retries exhausted after 5 attempts (HTTP 429)"
            )
