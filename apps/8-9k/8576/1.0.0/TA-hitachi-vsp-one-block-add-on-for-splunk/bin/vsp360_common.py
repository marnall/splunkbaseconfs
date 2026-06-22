# -*- coding: utf-8 -*-
"""
Shared VSP 360 utilities for Splunk Add-on modular inputs.

- Enforce HTTPS-only base URL
- OAuth2 client-credentials token handling (refresh at ~80% lifetime)
- Time helpers for yyyyMMdd_HHmmss format
- Signature parsing into (storage_serial, instance_id)
- Scalar unwrapping, timeseries expansion
- utcOffset normalization (emit canonical 'UTC±HH:MM')
"""

import json
import math
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

TIME_FMT = "%Y%m%d_%H%M%S"


def b(x: Any, default: bool = False) -> bool:
    if x is None:
        return default
    return str(x).strip().lower() in ("1", "true", "t", "yes", "y", "on")


def force_https_base_url(base_url: str) -> str:
    u = (base_url or "").strip()
    if not u:
        return u
    low = u.lower()
    if low.startswith("http://"):
        raise ValueError("vsp360_base_url must be HTTPS (http:// is not allowed).")
    if low.startswith("https://"):
        return u.rstrip("/")
    return ("https://" + u.lstrip("/")).rstrip("/")


def vsp360_host_label(base_url: str) -> str:
    """Return a stable host[:port] label for the VSP 360 endpoint."""
    u = force_https_base_url(base_url)
    p = urlparse(u)
    return p.netloc or u


def normalize_utc_offset(utc_offset: Optional[str]) -> Optional[str]:
    """
    Normalize utcOffset inputs into canonical format: 'UTC±HH:MM'.

    Accepts: 'UTC+0000', '+0000', 'UTC+00:00', '+00:00', 'Z',
             'UTC-0700', '-0700', '+05:30', 'UTC+0530', etc.
    """
    if utc_offset is None:
        return None
    s = str(utc_offset).strip()
    if s == "":
        return None
    up = s.upper()
    if up == "Z":
        return "UTC+00:00"
    if up.startswith("UTC"):
        up = up[3:]
    up = up.strip()

    m = re.fullmatch(r"^([+-])(\d{2})(?::?(\d{2}))?$", up)
    if not m:
        raise ValueError(f"Invalid utc_offset format: {s!r}. Expected like 'UTC+00:00' or '+0000'.")
    sign = m.group(1)
    hh = int(m.group(2))
    mm = int(m.group(3) or "00")
    if hh > 23 or mm > 59:
        raise ValueError(f"Invalid utc_offset value: {s!r}. Hour/min out of range.")
    return f"UTC{sign}{hh:02d}:{mm:02d}"


def _parse_utc_offset_tz(utc_offset: Optional[str]) -> Optional[timezone]:
    if not utc_offset:
        return None
    norm = normalize_utc_offset(utc_offset)
    m = re.fullmatch(r"^UTC([+-])(\d{2}):(\d{2})$", norm)
    if not m:
        return None
    sign, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
    delta = timedelta(hours=hh, minutes=mm)
    if sign == "-":
        delta = -delta
    return timezone(delta)


def parse_csad_time(s: str, utc_offset: Optional[str] = None) -> int:
    dt = datetime.strptime(s, TIME_FMT)
    tz = _parse_utc_offset_tz(utc_offset) if utc_offset else None
    if tz is not None:
        dt = dt.replace(tzinfo=tz)
        return int(dt.timestamp())
    return int(dt.timestamp())


def format_csad_time(epoch: int, utc_offset: Optional[str] = None) -> str:
    tz = _parse_utc_offset_tz(utc_offset) if utc_offset else None
    if tz is not None:
        return datetime.fromtimestamp(epoch, tz=tz).strftime(TIME_FMT)
    return datetime.fromtimestamp(epoch).strftime(TIME_FMT)


def chunk_list(items: List[str], chunk_size: int) -> List[List[str]]:
    if chunk_size <= 0:
        return [items]
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def parse_signature(sig: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse signature into (storage_serial, instance_id)."""
    if not sig or "#" not in sig:
        return None, None

    resource_type, right = sig.split("#", 1)
    right = right.strip()

    if resource_type in {"raidConsumer", "sp"}:
        return None, right or None

    if "-" in right:
        left, inst = right.split("-", 1)
        left = left.strip()
        inst = inst.strip()
        if re.fullmatch(r"\d+", left or ""):
            return left, inst or None
        return None, right or None

    if re.fullmatch(r"\d+", right or ""):
        return right, None

    return None, right or None


def stanza_name(helper) -> str:
    raw = None
    try:
        raw = helper.get_input_stanza_names()
    except Exception:
        raw = None
    if isinstance(raw, list):
        return str(raw[0]) if raw else "default"
    if raw:
        return str(raw)
    return "default"


def mql_for(category: str, resource_type: str, attrs: List[str]) -> str:
    q = resource_type
    for a in attrs:
        a = (a or "").strip()
        if not a:
            continue
        if category in ("performance", "synthetic"):
            q += f"[@{a} rx b .*]"
        else:
            q += f"[={a} rx .*]"
    return q


def expand_timeseries(metric_obj: Any, utc_offset: Optional[str] = None) -> Iterable[Tuple[int, float, int, str]]:
    if not isinstance(metric_obj, list):
        return
    for block in metric_obj:
        if not isinstance(block, dict):
            continue
        interval = int(block.get("interval") or 0)
        start = block.get("start")
        data = block.get("data") or []
        if not start or interval <= 0 or not isinstance(data, list):
            continue
        base_epoch = parse_csad_time(start, utc_offset)
        unit = str(block.get("unit") or "")
        for i, v in enumerate(data):
            if v is None:
                continue
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                continue
            if not isinstance(v, (int, float)):
                try:
                    v = float(v)
                except Exception:
                    continue
            yield base_epoch + (i * interval), float(v), interval, unit


def coerce_scalar_value(x: Any) -> Any:
    if not isinstance(x, str):
        return x
    s = x.strip()
    if not s:
        return x
    if re.match(r"^-?\d+$", s):
        try:
            return int(s)
        except Exception:
            return x
    if re.match(r"^-?\d+\.\d+$", s):
        try:
            return float(s)
        except Exception:
            return x
    return x


def unwrap_scalar(obj: Any, numeric_coerce: bool = False) -> Tuple[Any, Optional[str], Optional[str]]:
    if isinstance(obj, dict) and obj.get("type") == "scalar" and "data" in obj:
        data = obj.get("data")
        if numeric_coerce:
            data = coerce_scalar_value(data)
        return data, obj.get("name"), obj.get("unit")
    return obj, None, None


class VSP360Client:
    def __init__(self, base_url: str, realm: str, dataset: str,
                 client_id: str, client_secret: str, timeout: int):
        self.base_url = force_https_base_url(base_url)
        self.realm = (realm or "vsp360").strip()
        self.dataset = (dataset or "defaultDs").strip()
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.timeout = int(timeout)

        self.session = requests.Session()
        self.session.trust_env = False
        self._token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

    def close(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass

    def _token_valid(self) -> bool:
        return bool(self._token) and bool(self._token_expires_at) and time.time() < float(self._token_expires_at)

    def get_token(self) -> str:
        url = f"{self.base_url}/auth/realms/{self.realm}/protocol/openid-connect/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = self.session.post(url, data=payload, headers=headers, verify=True, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Token response missing access_token")
        expires_in = int(data.get("expires_in", 3600))
        self._token = token
        self._token_expires_at = time.time() + max(30, int(expires_in * 0.8))
        return token

    def ensure_token(self) -> str:
        if not self._token_valid():
            return self.get_token()
        return self._token or ""

    def query(self, mql: str, start_time: str, end_time: str,
              process_sync: bool, utc_offset: Optional[str]) -> Dict[str, Any]:
        token = self.ensure_token()
        url = f"{self.base_url}/clearsightadvanced/dbapi.do"
        params = {"action": "query", "dataset": self.dataset, "processSync": "true" if process_sync else "false"}
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
        payload: Dict[str, Any] = {"query": mql, "startTime": start_time, "endTime": end_time}
        if utc_offset:
            payload["utcOffset"] = normalize_utc_offset(utc_offset)
        r = self.session.post(url, params=params, json=payload, headers=headers, verify=True, timeout=self.timeout)
        if r.status_code in (200, 206):
            return r.json()
        try:
            body = r.json()
        except Exception:
            body = r.text
        raise RuntimeError(f"VSP 360 query failed: status={r.status_code} body={body}")
