"""
LLMmon Gateway — logs every LLM request/response and proxies to the matched route.
Registered at match=/proxy_llm — clients use: https://<splunk>:8089/services/proxy_llm
"""

import json
import http.client
import ssl
import sys
import time
import traceback
import urllib.parse
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llmmon_lib as lib

try:
    import splunk.rest as splunk_rest
    _BaseClass = splunk_rest.BaseRestHandler
except ImportError:
    class _BaseClass:
        def __init__(self, *a, **kw): pass


class GatewayHandler(_BaseClass):

    def handle_POST(self):   self._proxy()
    def handle_PUT(self):    self._proxy()
    def handle_GET(self):    self._proxy()
    def handle_DELETE(self): self._proxy()

    def _proxy(self):
        try:
            self._proxy_inner()
        except Exception:
            tb = traceback.format_exc()
            self.response.setHeader("Content-Type", "application/json")
            self.response.setStatus(500)
            self.response.write(json.dumps({"error": {"message": "Gateway error", "detail": tb}}))

    def _proxy_inner(self):
        req = getattr(self, "request", {}) or {}
        # Logging session key, in order of preference — no hardcoded credentials:
        #   1. the caller's own Splunk session key (authenticated requests)
        #   2. the system-level token Splunk hands us via restmap passSystemAuth
        #      (lets us log unauthenticated LLM-client traffic too)
        session_key = (getattr(self, "sessionKey", "")
                       or (req.get("systemAuth") if isinstance(req, dict) else "")
                       or "")

        body = req.get("rawArgs", req.get("payload", ""))
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8", errors="replace")
        body = body or ""

        method    = req.get("method", "POST").upper()
        rest_path = req.get("path", "") or req.get("pathInfo", "") or req.get("uri", "") or "/proxy_llm"

        # {"action":"list_routes"} → return route list without proxying
        try:
            req_json = json.loads(body) if body.strip() else {}
        except Exception:
            req_json = {}

        if req_json.get("action") == "list_routes":
            routes = lib.get_routes()
            safe = [
                {"name": r.get("name", ""), "provider": r.get("provider", ""),
                 "upstream_url": r.get("upstream_url", ""), "api_key": r.get("api_key", ""),
                 "match_type": r.get("match_type", "default"),
                 "match_value": r.get("match_value", "*"),
                 "enabled": r.get("enabled", "1")}
                for r in routes if r.get("enabled", "1") == "1"
            ]
            self._write_json(200, {"routes": safe})
            return

        raw_headers = req.get("headers", {}) or {}
        if not isinstance(raw_headers, dict):
            raw_headers = {}

        model      = req_json.get("model", "unknown")
        request_id = str(uuid.uuid4())
        t_start    = time.time()

        # Log full request
        lib.log_to_splunk(session_key, {
            "event_type":     "llm_request",
            "request_id":     request_id,
            "timestamp":      t_start,
            "model":          model,
            "method":         method,
            "path":           rest_path,
            "request_headers": json.dumps(raw_headers),
            "request_body":   body[:20000],
        })

        # Match route by header condition or model
        route = lib.get_route_for_request(model, raw_headers)
        if not route:
            lib.log_to_splunk(session_key, {
                "event_type": "route_error",
                "request_id": request_id,
                "model":      model,
                "error":      "no route configured",
            })
            self._write_json(503, {"error": {"message": f"No route for model: {model}", "type": "gateway_error"}})
            return

        # Use API key from route, fall back to client's Authorization header
        api_key = route.get("api_key", "").strip()
        if api_key:
            auth_header = f"Bearer {api_key}"
        else:
            auth_header = raw_headers.get("Authorization") or raw_headers.get("authorization") or ""

        # Always call /chat/completions on the upstream — the upstream_url is the full base
        # (e.g. https://api.openai.com/v1 or http://host:5000/nournetai/v1)
        upstream_url = route.get("upstream_url", "").rstrip("/")
        resp_status, resp_body = self._forward(upstream_url, "/chat/completions", method, body, auth_header)
        t_elapsed = time.time() - t_start

        try:
            resp_json = json.loads(resp_body)
        except Exception:
            resp_json = {}
        usage = resp_json.get("usage", {})

        # Log full response
        lib.log_to_splunk(session_key, {
            "event_type":        "llm_response",
            "request_id":        request_id,
            "timestamp":         time.time(),
            "model":             resp_json.get("model", model),
            "route_name":        route.get("name", ""),
            "provider":          route.get("provider", ""),
            "status_code":       resp_status,
            "elapsed_seconds":   round(t_elapsed, 3),
            "prompt_tokens":     usage.get("prompt_tokens", usage.get("input_tokens", 0)),
            "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
            "total_tokens":      usage.get("total_tokens", 0),
            "response_body":     resp_body[:20000],
        })

        self.response.setHeader("Content-Type", "application/json")
        self.response.setStatus(resp_status)
        self.response.write(resp_body)

    def _forward(self, base_url, path, method, body, auth_header):
        try:
            parsed    = urllib.parse.urlparse(base_url)
            scheme    = parsed.scheme or "https"
            host      = parsed.hostname or parsed.netloc
            port      = parsed.port or (443 if scheme == "https" else 80)
            full_path = (parsed.path or "").rstrip("/") + path

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE

            if scheme == "https":
                conn = http.client.HTTPSConnection(host, port, context=ctx, timeout=90)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=90)

            body_bytes = body.encode("utf-8") if isinstance(body, str) else (body or b"")
            conn.request(method, full_path, body=body_bytes, headers={
                "Content-Type":   "application/json",
                "Content-Length": str(len(body_bytes)),
                "Authorization":  auth_header,
            })
            resp = conn.getresponse()
            resp_body = resp.read()
            try:    resp_body = resp_body.decode("utf-8")
            except: resp_body = resp_body.decode("latin-1")
            return resp.status, resp_body
        except Exception as exc:
            return 502, json.dumps({"error": {"message": str(exc), "type": "gateway_connection_error"}})

    def _write_json(self, status, obj):
        self.response.setHeader("Content-Type", "application/json")
        self.response.setStatus(status)
        self.response.write(json.dumps(obj))
