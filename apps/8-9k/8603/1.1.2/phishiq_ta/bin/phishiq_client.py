"""
PhishIQ API client for Splunk add-on.
Calls PhishIQ batch or single predict API with optional local cache.
Deploy on Heavy Forwarder: all API calls happen outside Splunk Cloud.
"""

from __future__ import absolute_import

import hashlib
import json
import logging
import random
import time
from collections import OrderedDict
from threading import Lock

import requests

logger = logging.getLogger(__name__)


class LRUCache:
    """Simple thread-safe LRU cache with TTL."""

    def __init__(self, max_entries=10000, ttl_seconds=86400):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = Lock()

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, ts in self._timestamps.items() if now - ts > self.ttl_seconds]
        for k in expired:
            self._cache.pop(k, None)
            self._timestamps.pop(k, None)

    def _evict_lru(self):
        while len(self._cache) >= self.max_entries and self._cache:
            k, _ = self._cache.popitem(last=False)
            self._timestamps.pop(k, None)

    def get(self, key):
        with self._lock:
            self._evict_expired()
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key, value):
        with self._lock:
            self._evict_expired()
            self._evict_lru()
            self._cache[key] = value
            self._cache.move_to_end(key)
            self._timestamps[key] = time.time()

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def stats(self):
        with self._lock:
            self._evict_expired()
            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
            }


class PhishIQClient:
    """
    Client for PhishIQ predict API.
    Supports single URL (/predict/v1) and batch (/predict/v1/batch).
    """

    def __init__(
        self,
        base_url,
        api_key,
        timeout_seconds=30,
        ssl_verify=True,
        cache_enabled=True,
        cache_ttl_seconds=86400,
        cache_max_entries=10000,
        retry_max_attempts=3,
        retry_base_delay_ms=250,
        retry_max_delay_ms=5000,
        circuit_breaker_failures=5,
        circuit_breaker_reset_seconds=60,
        degraded_mode="emit_error_event",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # Requests timeout can be a float or a (connect, read) tuple.
        # We use (connect, read) to avoid hanging during DNS/connect.
        self.timeout = (min(5, timeout_seconds), timeout_seconds)
        self.ssl_verify = ssl_verify
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["x-api-key"] = api_key
        self.retry_max_attempts = max(1, int(retry_max_attempts))
        self.retry_base_delay_ms = max(50, int(retry_base_delay_ms))
        self.retry_max_delay_ms = max(self.retry_base_delay_ms, int(retry_max_delay_ms))
        self.circuit_breaker_failures = max(1, int(circuit_breaker_failures))
        self.circuit_breaker_reset_seconds = max(5, int(circuit_breaker_reset_seconds))
        self.degraded_mode = degraded_mode
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        self._metrics = {
            "requests": 0,  # logical requests (single/batch chunk)
            "attempts": 0,  # HTTP attempts including retries
            "retries": 0,  # attempts beyond the first
            "success": 0,
            "fail": 0,
            "circuit_open": 0,
            "last_error": None,
            "last_status": None,
        }
        self.cache = None
        if cache_enabled:
            self.cache = LRUCache(
                max_entries=cache_max_entries,
                ttl_seconds=cache_ttl_seconds,
            )

    def _url_hash(self, url):
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _is_circuit_open(self):
        return time.time() < self._circuit_open_until

    def _note_success(self):
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def _note_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_breaker_failures:
            self._circuit_open_until = time.time() + self.circuit_breaker_reset_seconds

    def _sleep_backoff(self, attempt, retry_after_seconds=None):
        if retry_after_seconds is not None:
            delay = float(retry_after_seconds)
        else:
            # exponential backoff with jitter
            base = self.retry_base_delay_ms / 1000.0
            delay = min(self.retry_max_delay_ms / 1000.0, base * (2 ** max(0, attempt - 1)))
            delay = delay * (0.5 + random.random())
        time.sleep(max(0.0, delay))

    def _request_json_with_retries(self, endpoint, payload):
        """
        Reliability contract:
        - Retry only on transient errors: network/timeouts and 5xx.
        - 4xx are client/config errors: do not retry (except 429 honoring Retry-After).
        - Circuit breaker opens after N consecutive failures.
        Returns (ok: bool, data_or_error: dict/str, status_code: int|None).
        """
        self._metrics["requests"] += 1
        if self._is_circuit_open():
            self._metrics["circuit_open"] += 1
            self._metrics["last_error"] = "circuit_open"
            self._metrics["last_status"] = None
            return False, "circuit_open", None

        last_err = None
        last_status = None

        for attempt in range(1, self.retry_max_attempts + 1):
            try:
                self._metrics["attempts"] += 1
                if attempt > 1:
                    self._metrics["retries"] += 1
                r = self.session.post(
                    endpoint,
                    json=payload,
                    timeout=self.timeout,
                    verify=self.ssl_verify,
                )
                last_status = r.status_code
                self._metrics["last_status"] = r.status_code

                # 2xx
                if 200 <= r.status_code < 300:
                    self._note_success()
                    self._metrics["success"] += 1
                    self._metrics["last_error"] = None
                    return True, r.json(), r.status_code

                # 401/403: auth/config issue - fail fast
                if r.status_code in (401, 403):
                    self._note_failure()
                    self._metrics["fail"] += 1
                    self._metrics["last_error"] = "auth_error"
                    return False, "auth_error", r.status_code

                # 400-499: client issue - fail fast (except 429)
                if 400 <= r.status_code < 500 and r.status_code != 429:
                    self._note_failure()
                    self._metrics["fail"] += 1
                    self._metrics["last_error"] = "client_error"
                    return False, "client_error", r.status_code

                # 429: rate limit - retry with backoff if attempts remain
                if r.status_code == 429:
                    self._note_failure()
                    retry_after = r.headers.get("Retry-After")
                    if attempt >= self.retry_max_attempts:
                        self._metrics["fail"] += 1
                        self._metrics["last_error"] = "rate_limited"
                        return False, "rate_limited", r.status_code
                    try:
                        retry_after_seconds = int(retry_after) if retry_after else None
                    except Exception:
                        retry_after_seconds = None
                    self._sleep_backoff(attempt, retry_after_seconds=retry_after_seconds)
                    continue

                # 5xx: transient server error - retry with backoff
                if 500 <= r.status_code < 600:
                    self._note_failure()
                    if attempt >= self.retry_max_attempts:
                        self._metrics["fail"] += 1
                        self._metrics["last_error"] = "server_error"
                        return False, "server_error", r.status_code
                    self._sleep_backoff(attempt)
                    continue

                # Other status: treat as failure without retry
                self._note_failure()
                self._metrics["fail"] += 1
                self._metrics["last_error"] = "unexpected_status"
                return False, "unexpected_status", r.status_code

            except requests.Timeout as e:
                last_err = e
                self._note_failure()
                last_status = None
                self._metrics["last_status"] = None
                if attempt >= self.retry_max_attempts:
                    self._metrics["fail"] += 1
                    self._metrics["last_error"] = "timeout"
                    return False, "timeout", None
                self._sleep_backoff(attempt)
                continue
            except requests.RequestException as e:
                last_err = e
                self._note_failure()
                last_status = None
                self._metrics["last_status"] = None
                if attempt >= self.retry_max_attempts:
                    self._metrics["fail"] += 1
                    self._metrics["last_error"] = "network_error"
                    return False, "network_error", None
                self._sleep_backoff(attempt)
                continue

        # Should not reach here
        if last_err:
            self._metrics["fail"] += 1
            self._metrics["last_error"] = "exception"
            return False, str(last_err), last_status
        self._metrics["fail"] += 1
        self._metrics["last_error"] = "unknown_error"
        return False, "unknown_error", last_status

    def get_and_reset_metrics(self):
        m = dict(self._metrics)
        self._metrics["requests"] = 0
        self._metrics["attempts"] = 0
        self._metrics["retries"] = 0
        self._metrics["success"] = 0
        self._metrics["fail"] = 0
        self._metrics["circuit_open"] = 0
        self._metrics["last_error"] = None
        self._metrics["last_status"] = None
        return m

    def clear_cache(self):
        if self.cache:
            self.cache.clear()

    def cache_stats(self):
        if self.cache:
            return self.cache.stats()
        return {"enabled": False}

    def _single_predict(self, url):
        """POST /predict/v1 - single URL."""
        endpoint = f"{self.base_url}/predict/v1"
        ok, data_or_err, _status = self._request_json_with_retries(endpoint, {"url": url})
        if ok:
            return data_or_err
        logger.warning("PhishIQ single predict failed for %s: %s", url[:80], data_or_err)
        return None

    def predict_single(self, url):
        """Get prediction for one URL; use cache if enabled."""
        key = self._url_hash(url)
        if self.cache:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        result = self._single_predict(url)
        if result is not None and self.cache:
            self.cache.set(key, result)
        return result

    def predict_batch(self, urls, fast_mode=False):
        """
        POST /predict/v1/batch - up to 100 URLs per request.
        Returns list of prediction dicts (same order as urls); None for failures.
        """
        if not urls:
            return []
        endpoint = f"{self.base_url}/predict/v1/batch"
        results = [None] * len(urls)
        # Batch API allows max 100 per request
        chunk_size = 100
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i : i + chunk_size]
            ok, data_or_err, _status = self._request_json_with_retries(
                endpoint, {"urls": chunk, "fast_mode": fast_mode}
            )
            if not ok:
                logger.warning("PhishIQ batch predict failed: %s", data_or_err)
                continue
            data = data_or_err
            preds = data.get("predictions", [])
            for j, p in enumerate(preds):
                if i + j < len(results):
                    results[i + j] = p
                    if self.cache and p is not None:
                        u = chunk[j]
                        key = self._url_hash(u)
                        self.cache.set(key, p)
        return results

    def test_connection(self):
        """Validate API key and base URL with a minimal request."""
        endpoint = f"{self.base_url}/predict/v1"
        ok, data_or_err, status = self._request_json_with_retries(endpoint, {"url": "https://www.google.com"})
        if ok:
            return True, "OK"
        if data_or_err == "auth_error" or status in (401, 403):
            return False, "Authentication failed ({}). Check API Key and Base URL.".format(status or "401")
        if data_or_err == "rate_limited" or status == 429:
            return False, "Rate limit exceeded (429). Reduce frequency or upgrade your plan."
        if data_or_err == "timeout":
            return False, "Timeout contacting PhishIQ API. Check network and increase timeout."
        if data_or_err == "circuit_open":
            return False, "Circuit breaker open due to repeated failures. Will retry later."
        return False, "Connection test failed: {}{}".format(data_or_err, "" if status is None else " (status {})".format(status))
