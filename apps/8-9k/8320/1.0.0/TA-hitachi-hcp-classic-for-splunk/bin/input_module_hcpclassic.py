#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HCP Prometheus to Splunk modular input.

Reads metrics from the Prometheus HTTPS API and writes them as Splunk events.

"""

import base64
import hashlib
import json
import logging
import time
import urllib.parse
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

VERIFY_SSL = True

# -------------------- label surfacing policy --------------------

DEFAULT_SURFACE = ()

PER_METRIC_SURFACE = {
    "configured_storage_bytes": ("tenant", "capacity"),
    "cpu_utilization": ("space",),
    "directories_count_per_region": ("region_name",),

    "disk_io_kilobytes_per_second": ("disk_name", "io_type"),
    "disk_transfers_per_second": ("disk_name",),
    "disk_utilization": ("disk_name",),

    "gateway_operation_latency_milliseconds_bucket":
        ("interface", "namespace", "request_method", "response_code", "tenant", "le"),
    "gateway_operation_latency_milliseconds_count":
        ("interface", "namespace", "request_method", "response_code", "tenant"),
    "gateway_operation_latency_milliseconds_created":
        ("interface", "namespace", "request_method", "response_code", "tenant"),
    "gateway_operation_latency_milliseconds_sum":
        ("interface", "namespace", "request_method", "response_code", "tenant"),

    "gateway_operation_size_bytes_bucket":
        ("interface", "namespace", "request_method", "response_code", "tenant", "le"),
    "gateway_operation_size_bytes_count":
        ("interface", "namespace", "request_method", "response_code", "tenant"),
    "gateway_operation_size_bytes_created":
        ("interface", "namespace", "request_method", "response_code", "tenant"),
    "gateway_operation_size_bytes_sum":
        ("interface", "namespace", "request_method", "response_code", "tenant"),

    "http_connections": (),
    "http_connections_limit": (),
    "https_connections": (),
    "https_connections_limit": (),
    "internal_file_system_usage": ("location",),
    "system_events_created": ("severity",),
    "system_events_total": ("severity",),
    "volume_storage_bytes": ("name", "capacity"),
    "replication_backlog_bytes_per_namespace": ("namespace", "link_name"),
    "replication_backlog_objects_per_namespace": ("namespace", "link_name"),
    "replication_bytes_pending": ("link_name",),
    "replication_bytes_pending_remote": ("link_name",),
    "replication_bytes_per_second": ("link_name",),
    "replication_errors_per_second": ("link_name",),
    "replication_objects_pending": ("link_name",),
    "replication_objects_pending_remote": ("link_name",),
    "replication_objects_verified": ("link_name",),
    "replication_operations_per_second": ("link_name",),
    "replication_up_to_date_as_of_millis": ("link_name",),
    "s_series_cpu_utilization": ("name",),
    "s_series_network_bandwidth_bytes": ("name", "capacity"),
    "s_series_storage_bytes": ("name", "capacity"),
    "service_events_created": ("action", "service"),
    "service_events_total": ("action", "service"),
}

AUTO_SURFACE_CANDIDATES = (
    "tenant", "bucket", "capacity", "operation",
    "namespace", "kubernetes_namespace",
    "region_name", "region", "node",
    "kubernetes_pod", "pod",
    "interface", "request_method", "response_code", "le",
    "disk_name", "io_type", "space",
)

# -------------------- small utils --------------------


def _b(s, default=False):
    if s is None:
        return default
    return str(s).strip().lower() in ("1", "true", "t", "yes", "y", "on")


def retry(max_retries=3, backoff=1.0, retriable=(requests.RequestException,)):
    def deco(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            last_exc = None
            for i in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except retriable as e:
                    last_exc = e
                    if i == max_retries - 1:
                        raise
                    wait = backoff * (2 ** i)
                    helper = args[0] if args else None
                    if helper and hasattr(helper, "log_warning"):
                        helper.log_warning(
                            f"{fn.__name__} failed (attempt {i+1}/{max_retries}): {e}; "
                            f"retrying in {wait:.1f}s"
                        )
                    time.sleep(wait)
            raise last_exc
        return inner
    return deco


def _force_https_base_url(base_url: str) -> str:
    """
    Enforce HTTPS-only usage.
    """
    u = (base_url or "").strip()
    if not u:
        return u

    low = u.lower()
    if low.startswith("http://"):
        raise ValueError(
            "hcp_base_url is configured with http:// but this input is HTTPS-only for production. "
            "Please change it to https://<host>:9094[/ui/prometheus] or https://<host>:9094/api/v1"
        )
    if low.startswith("https://"):
        return u

    # No scheme provided: assume https
    return "https://" + u.lstrip("/")


def normalize_api_root(base_url: str) -> str:
    """
    Turn any HCP Prometheus URL into an /api/v1 root (HTTPS enforced).
    Accepts:
      - https://host:9094
      - https://host:9094/ui/prometheus
      - https://host:9094/api/v1
      - https://host:9094/api/v1/query (etc)
    """
    u = _force_https_base_url(base_url).rstrip("/")

    # Strip common endpoints if user pasted a specific API URL
    for tail in ("/query_range", "/query", "/metadata", "/label/__name__/values"):
        if u.endswith(tail):
            u = u[: -len(tail)]

    # Ensure we end at /api/v1
    if not u.endswith("/api/v1"):
        if "/api/v1" in u:
            u = u[: u.index("/api/v1")] + "/api/v1"
        else:
            if u.endswith("/ui/prometheus"):
                u += "/api/v1"
            else:
                # If they gave just https://host:9094, append /api/v1
                u += "/api/v1"

    return u.rstrip("/")


def url_join(root: str, path: str, params: Optional[dict] = None) -> str:
    root = root.rstrip("/")
    path = path if path.startswith("/") else "/" + path
    if params:
        q = urllib.parse.urlencode(params, doseq=True, safe=":[]")
        return f"{root}{path}?{q}"
    return f"{root}{path}"


def make_hcp_token(username: str, password: str) -> str:
    """
    Make HCP auth token: base64(username) : md5(password)
    """
    u_b64 = base64.b64encode(username.encode("utf-8")).decode("ascii")
    p_md5 = hashlib.md5(password.encode("utf-8")).hexdigest()
    return f"{u_b64}:{p_md5}"


def safe_log_url(url: str) -> str:
    low = url.lower()
    if any(x in low for x in ("authorization", "token=", "password=", "access_token=")):
        return url.split("?")[0] + "?***REDACTED***"
    return url

# -------------------- hardened HTTPS-only session --------------------


def _build_session(verify_ssl: bool) -> requests.Session:
    s = requests.Session()
    s.trust_env = False  

    retry_cfg = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_cfg, pool_connections=4, pool_maxsize=8)

    # HTTPS only
    s.mount("https://", adapter)

    s.verify = verify_ssl
    return s

# -------------------- HTTP --------------------


@retry(max_retries=4, backoff=0.8)
def prom_get(helper, session, url, headers, verify_ssl):
    if not (url or "").lower().startswith("https://"):
        raise RuntimeError(f"HTTPS-only enforced. Refusing non-HTTPS URL: {safe_log_url(url)}")

    helper.log_info(f"GET {safe_log_url(url)}")
    local_headers = dict(headers or {})
    local_headers.setdefault("Accept", "application/json")
    local_headers.setdefault("User-Agent", "HCP-Prometheus-Collector/1.3")
    local_headers["Connection"] = "close"

    r = session.get(
        url,
        headers=local_headers,
        verify=verify_ssl,
        timeout=(3, 45),
        allow_redirects=False,
    )
    helper.log_info(f"HTTP {r.status_code} for {safe_log_url(url)}")
    r.raise_for_status()
    ctype = (r.headers.get("Content-Type", "") or "").lower()
    if "application/json" not in ctype:
        raise RuntimeError(f"Non-JSON response from {safe_log_url(url)}")
    return r.json()

# -------------------- event shaping --------------------


def _surface_keys_for_metric(metric_name, labels_dict):
    surfaced = set(DEFAULT_SURFACE)
    extra = PER_METRIC_SURFACE.get(metric_name)
    if extra:
        surfaced.update(extra)
    for k in AUTO_SURFACE_CANDIDATES:
        if k in labels_dict:
            surfaced.add(k)
    return tuple(surfaced)


def _pick_meta(meta_json, metric_name):
    data = (meta_json or {}).get("data") or {}
    arr = data.get(metric_name) or []
    if arr and isinstance(arr, list):
        x = arr[0]
        return {
            "type": x.get("type"),
            "help": x.get("help"),
            "unit": x.get("unit"),
        }
    return {}


def _result_vector(qjson):
    return (((qjson or {}).get("data") or {}).get("result")) or []


def _uniform_event(metric_name, meta, series_item, cluster_name, query_str):
    """
    Shape one Prometheus series item into a Splunk event dict.
    """
    labels = series_item.get("metric") or {}
    val = series_item.get("value") or []
    ts_raw, v_raw = (val + [None, None])[:2]

    now = time.time()
    try:
        ts = float(ts_raw) if ts_raw is not None else now
    except Exception:
        ts = now
    try:
        value = float(v_raw)
    except Exception:
        value = v_raw

    event_time = (
        datetime.fromtimestamp(ts, timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"
    )

    ev = {
        "metric_name": metric_name,
        "metric_type": (meta or {}).get("type"),
        "help": (meta or {}).get("help"),
        "unit": (meta or {}).get("unit"),
        "value": value,
        "timestamp_epoch": ts,
        "event_time": event_time,
        "cluster_name": cluster_name,
        "query": query_str,
    }

    if "instance" in labels:
        ev["instance"] = labels["instance"]
    if "job" in labels:
        ev["job"] = labels["job"]

    surfaced_keys = _surface_keys_for_metric(metric_name, labels)
    other_labels = {}

    for k, v in labels.items():
        if k == "__name__":
            continue
        if k in ("instance", "job"):
            continue
        if k in surfaced_keys:
            ev[k] = v
        else:
            other_labels[k] = v

    if other_labels:
        ev["other_labels"] = other_labels

    return ev

# -------------------- Splunk entrypoints --------------------


def validate_input(helper, validation_definition):
    """
    Validate per-input parameters only.
    """
    params = validation_definition.parameters

    metric_names = (params.get("metric_names", None) or "").strip()
    collect_all = _b(params.get("collect_all_metrics", None), False)

    if not collect_all and not metric_names:
        raise ValueError(
            "Either give one or more metric_names, or set collect_all_metrics to true."
        )

    return True


def collect_events(helper, ew):
    logger = logging.getLogger("splunk")
    logger.setLevel(logging.INFO)

    # ------------ globals ------------
    BASE_URL = (helper.get_global_setting("hcp_base_url") or "").strip()
    SEND_AUTH = _b(helper.get_global_setting("send_auth_header"), False)
    USERNAME = (helper.get_global_setting("hcp_username") or "").strip()
    PASSWORD = (helper.get_global_setting("hcp_password") or "").strip()
    CLUSTER_NAME = (helper.get_global_setting("cluster_name") or "").strip()

    if not BASE_URL:
        helper.log_error("Global setting 'hcp_base_url' is not configured.")
        return

    if SEND_AUTH and (not USERNAME or not PASSWORD):
        helper.log_error(
            "send_auth_header is true, but hcp_username or hcp_password is empty."
        )
        return

    # Enforce HTTPS-only at the earliest point (for both SEND_AUTH true/false)
    try:
        api_root = normalize_api_root(BASE_URL)
    except Exception as e:
        helper.log_error(str(e))
        return

    verify_ssl = VERIFY_SSL
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        helper.log_warning(
            "TLS certificate verification is disabled. Use this only in lab."
        )

    helper.log_info(f"HCP Prometheus API root (HTTPS-only): {api_root}")

    # ------------ per-input parameters ------------
    metric_names_csv = (helper.get_arg("metric_names") or "").strip()
    collect_all = _b(helper.get_arg("collect_all_metrics"), False)

    headers = {
        "Accept": "application/json",
        "User-Agent": "HCP-Prometheus-Collector/1.3",
    }
    if SEND_AUTH:
        token = make_hcp_token(USERNAME, PASSWORD)
        headers["Authorization"] = f"HCP {token}"

    session = _build_session(verify_ssl)

    try:
        total_ok, total_fail = 0, 0

        metrics = []
        if collect_all:
            names_url = url_join(api_root, "/label/__name__/values")
            names_js = prom_get(helper, session, names_url, headers, verify_ssl)
            metrics = (names_js or {}).get("data") or []
            helper.log_info(f"Discovered metric names: count={len(metrics)}")
        elif metric_names_csv:
            metrics = [m.strip() for m in metric_names_csv.split(",") if m.strip()]

        if not metrics:
            helper.log_warning(
                "No metrics to collect. Give metric_names or set collect_all_metrics=true."
            )
            return

        for m in metrics:
            try:
                meta_url = url_join(api_root, "/metadata", {"metric": m})
                meta_js = prom_get(helper, session, meta_url, headers, verify_ssl)
                meta = _pick_meta(meta_js, m)

                qurl = url_join(api_root, "/query", {"query": m})
                qjs = prom_get(helper, session, qurl, headers, verify_ssl)
                res = _result_vector(qjs)
                helper.log_info(
                    f"index {helper.get_output_index()} source {helper.get_input_type()} "
                    f"sourcetype {helper.get_sourcetype()} metric {m}: series={len(res)}"
                )

                if not res:
                    helper.log_warning(f"No series for metric '{m}'")
                    total_fail += 1
                    continue

                for item in res:
                    ev = _uniform_event(m, meta, item, CLUSTER_NAME, m)
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype(),
                        time=ev["timestamp_epoch"],
                        data=json.dumps(ev),
                    )
                    ew.write_event(event)
                    total_ok += 1

            except Exception as e:
                helper.log_error(f"Metric '{m}' failed: {e}")
                total_fail += 1

        helper.log_info(
            f"Finished collection: metrics={len(metrics)}, ok={total_ok}, failed={total_fail}"
        )

    finally:
        try:
            session.close()
        except Exception:
            pass