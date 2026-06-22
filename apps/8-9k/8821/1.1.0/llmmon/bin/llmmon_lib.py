"""Shared utilities for LLMmon: route storage and Splunk logging."""

import csv
import http.client
import json
import ssl
from pathlib import Path

APP_DIR        = Path(__file__).parent.parent
ROUTES_CSV     = APP_DIR / "lookups" / "llmmon_routes.csv"
LOG_INDEX      = "llmmon_logs"
LOG_SOURCETYPE = "llmmon:gateway"

ROUTE_FIELDS = ["id", "name", "provider", "upstream_url", "api_key",
                "match_type", "match_value", "enabled"]


def get_routes():
    if not ROUTES_CSV.exists():
        return []
    try:
        with open(ROUTES_CSV, "r", newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def get_route_for_request(model, headers):
    """Return the first enabled route matching the request's headers or model, else default."""
    headers_lower = {k.lower(): v.strip().lower() for k, v in (headers or {}).items()}
    default_route = None
    for route in get_routes():
        if route.get("enabled", "1") != "1":
            continue
        mt = route.get("match_type", "default")
        mv = route.get("match_value", "")
        if mt == "default" or mv in ("*", ""):
            if default_route is None:
                default_route = route
            continue
        if mt == "header" and ":" in mv:
            h_name, _, h_val = mv.partition(":")
            if headers_lower.get(h_name.strip().lower(), "") == h_val.strip().lower():
                return route
        elif mt == "model" and model:
            if model.startswith(mv) or mv in model:
                return route
    return default_route


def log_to_splunk(session_key, event_data):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection("localhost", 8089, context=ctx, timeout=5)
        conn.request(
            "POST",
            f"/services/receivers/simple?index={LOG_INDEX}&sourcetype={LOG_SOURCETYPE}&output_mode=json",
            body=json.dumps(event_data).encode("utf-8"),
            headers={
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            },
        )
        r = conn.getresponse()
        r.read()
        return r.status in (200, 201)
    except Exception:
        return False
