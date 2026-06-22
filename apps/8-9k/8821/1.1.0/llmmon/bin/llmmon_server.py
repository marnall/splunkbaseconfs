#!/usr/bin/env python3
"""
LLMmon OpenAI-compatible gateway server.
Full protocol + streaming. Runs on port 9000 as a Splunk scripted input.
"""

import csv
import http.client
import http.server
import json
import socket
import ssl
import sys
import threading
import time
import uuid
import urllib.parse
from pathlib import Path

PORT       = 9000
APP_NAME   = "llmmon"
APP_DIR    = Path(__file__).parent.parent
ROUTES_CSV = APP_DIR / "lookups" / "llmmon_routes.csv"
LOG_INDEX  = "llmmon_logs"
LOG_SRC    = "llmmon:gateway"
CRED_REALM = "llmmon_admin"   # storage/passwords realm holding the Splunk admin creds

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ── Splunk logging ─────────────────────────────────────────────────────────────

_sk_cache      = {"key": "", "ts": 0}
_creds         = {"username": "", "password": ""}
_bootstrap_key = ""   # session token handed to us by Splunk via inputs.conf passAuth


def _read_stored_credentials(session_key):
    """Load the Splunk admin username/password configured in the Settings UI.

    Credentials are stored encrypted in Splunk's storage/passwords (realm
    'llmmon_admin'); nothing is hardcoded. Reading clear_password requires a
    session key with the admin_all_objects/list_storage_passwords capability —
    the splunk-system-user token we receive via passAuth qualifies."""
    if not session_key:
        return False
    try:
        conn = http.client.HTTPSConnection("localhost", 8089, context=SSL_CTX, timeout=5)
        conn.request(
            "GET",
            f"/servicesNS/nobody/{APP_NAME}/storage/passwords?output_mode=json&count=0",
            headers={"Authorization": f"Splunk {session_key}"})
        data = json.loads(conn.getresponse().read())
        for entry in data.get("entry", []):
            content = entry.get("content", {})
            if content.get("realm") == CRED_REALM:
                _creds["username"] = content.get("username", "")
                _creds["password"] = content.get("clear_password", "")
                return bool(_creds["username"] and _creds["password"])
    except Exception:
        pass
    return False


def _bootstrap():
    """Splunk passes a session token for splunk-system-user on stdin
    (inputs.conf passAuth). Use it to load the configured credentials.
    Runs in a daemon thread so a missing/blocking stdin never stalls startup."""
    global _bootstrap_key
    try:
        line = sys.stdin.readline()
        _bootstrap_key = (line or "").strip()
    except Exception:
        _bootstrap_key = ""
    if _bootstrap_key:
        _read_stored_credentials(_bootstrap_key)


def _login(username, password):
    conn = http.client.HTTPSConnection("localhost", 8089, context=SSL_CTX, timeout=5)
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    conn.request("POST", "/services/auth/login?output_mode=json", body=body,
                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(conn.getresponse().read()).get("sessionKey", "")


def _session_key():
    c = _sk_cache
    if c["key"] and time.time() - c["ts"] < 300:
        return c["key"]
    # Lazily (re)load creds in case the Settings page was saved after startup.
    if not (_creds["username"] and _creds["password"]) and _bootstrap_key:
        _read_stored_credentials(_bootstrap_key)
    user, pwd = _creds["username"], _creds["password"]
    if user and pwd:
        try:
            key = _login(user, pwd)
            if key:
                c["key"], c["ts"] = key, time.time()
                return key
        except Exception:
            pass
    # Fall back to the bootstrap (splunk-system-user) token until it expires.
    return _bootstrap_key


def _log(event):
    try:
        key = _session_key()
        if not key:
            return
        conn = http.client.HTTPSConnection("localhost", 8089, context=SSL_CTX, timeout=3)
        body = json.dumps(event).encode()
        conn.request("POST",
            f"/services/receivers/simple?index={LOG_INDEX}&sourcetype={LOG_SRC}&output_mode=json",
            body=body,
            headers={"Authorization": f"Splunk {key}", "Content-Type": "application/json"})
        conn.getresponse().read()
    except Exception:
        pass


# ── Route helpers ──────────────────────────────────────────────────────────────

def _routes():
    if not ROUTES_CSV.exists():
        return []
    try:
        with open(ROUTES_CSV, "r", newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _find_route(model, headers):
    hl = {k.lower(): v.strip().lower() for k, v in headers.items()}
    default = None
    for r in _routes():
        if r.get("enabled", "1") != "1":
            continue
        mt, mv = r.get("match_type", "default"), r.get("match_value", "")
        if mt == "default" or mv in ("*", ""):
            if default is None:
                default = r
        elif mt == "header" and ":" in mv:
            hn, _, hv = mv.partition(":")
            if hl.get(hn.strip().lower(), "") == hv.strip().lower():
                return r
    return default


def _upstream_conn(url):
    p = urllib.parse.urlparse(url)
    scheme = p.scheme or "https"
    host   = p.hostname
    port   = p.port or (443 if scheme == "https" else 80)
    base   = (p.path or "").rstrip("/")
    if scheme == "https":
        conn = http.client.HTTPSConnection(host, port, context=SSL_CTX, timeout=90)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=90)
    return conn, base


# ── Request handler ────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # keep stdout clean for Splunk scripted input

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type,X-Requested-With")

    def _json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # GET /v1/models — query each upstream and aggregate
    def do_GET(self):
        path = self.path.split("?")[0]
        if "/models" in path:
            all_models = []
            for route in _routes():
                if route.get("enabled", "1") != "1":
                    continue
                upstream = route.get("upstream_url", "").rstrip("/")
                api_key  = route.get("api_key", "")
                try:
                    conn, base = _upstream_conn(upstream)
                    hdrs = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    conn.request("GET", base + "/models", headers=hdrs)
                    resp = conn.getresponse()
                    data = json.loads(resp.read())
                    all_models.extend(data.get("data", []))
                except Exception:
                    all_models.append({
                        "id": route.get("name", "unknown"), "object": "model",
                        "created": int(time.time()), "owned_by": route.get("provider", "custom"),
                    })
            self._json(200, {"object": "list", "data": all_models})
        else:
            self._proxy("GET", b"")

    def do_POST(self):
        n    = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n) if n else b""
        self._proxy("POST", body)

    def do_PUT(self):
        n    = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n) if n else b""
        self._proxy("PUT", body)

    def do_DELETE(self):
        self._proxy("DELETE", b"")

    def _proxy(self, method, body):
        try:
            req_json = json.loads(body) if body else {}
        except Exception:
            req_json = {}

        # Backward-compat: list_routes action
        if req_json.get("action") == "list_routes":
            safe = [
                {"name": r.get("name",""), "provider": r.get("provider",""),
                 "upstream_url": r.get("upstream_url",""), "api_key": r.get("api_key",""),
                 "match_type": r.get("match_type","default"), "match_value": r.get("match_value","*"),
                 "enabled": r.get("enabled","1")}
                for r in _routes() if r.get("enabled","1") == "1"
            ]
            self._json(200, {"routes": safe})
            return

        model  = req_json.get("model", "unknown")
        stream = req_json.get("stream", False)
        rid    = str(uuid.uuid4())
        t0     = time.time()
        path   = self.path.split("?")[0]

        route = _find_route(model, dict(self.headers))
        if not route:
            self._json(503, {"error": {"message": f"No route for model: {model}", "type": "gateway_error"}})
            return

        upstream = route.get("upstream_url", "").rstrip("/")
        api_key  = route.get("api_key", "").strip()
        auth     = f"Bearer {api_key}" if api_key else self.headers.get("Authorization", "")

        # Strip /v1 prefix — upstream URL already contains it
        if path.startswith("/v1/"):
            fwd = path[3:]
        elif path.startswith("/v1"):
            fwd = path[3:] or "/"
        else:
            fwd = path

        _log({"event_type": "llm_request", "request_id": rid, "timestamp": t0,
              "model": model, "method": method, "path": path, "stream": str(stream),
              "request_body": body.decode("utf-8", "replace")[:10000]})

        try:
            conn, base = _upstream_conn(upstream)
            fwd_headers = {
                "Content-Type":   self.headers.get("Content-Type", "application/json"),
                "Authorization":  auth,
                "Content-Length": str(len(body)),
            }
            if stream:
                fwd_headers["Accept"] = "text/event-stream"

            conn.request(method, base + fwd, body=body, headers=fwd_headers)
            up = conn.getresponse()

            if stream and up.status == 200:
                self._stream(up, rid, model, route, t0)
            else:
                resp_body = up.read()
                elapsed   = time.time() - t0
                try:
                    resp_json = json.loads(resp_body)
                    usage     = resp_json.get("usage", {})
                    pt  = usage.get("prompt_tokens",     usage.get("input_tokens",  0))
                    ct_ = usage.get("completion_tokens", usage.get("output_tokens", 0))
                    tt  = usage.get("total_tokens", pt + ct_)
                    resp_model = resp_json.get("model", model)
                except Exception:
                    pt = ct_ = tt = 0
                    resp_model = model
                _log({"event_type": "llm_response", "request_id": rid,
                      "model": resp_model, "provider": route.get("provider",""),
                      "route_name": route.get("name",""), "status_code": up.status,
                      "elapsed_seconds": round(elapsed, 3),
                      "prompt_tokens": pt, "completion_tokens": ct_, "total_tokens": tt,
                      "response_body": resp_body.decode("utf-8","replace")[:10000]})
                ct = dict(up.getheaders()).get("Content-Type", "application/json")
                self.send_response(up.status)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(resp_body)))
                self._cors()
                self.end_headers()
                self.wfile.write(resp_body)
                self.wfile.flush()

        except Exception as e:
            self._json(502, {"error": {"message": str(e), "type": "gateway_error"}})

    def _stream(self, up, rid, model, route, t0):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()

        content = []
        pt = ct_ = tt = 0
        try:
            while True:
                line = up.readline()
                if not line:
                    break
                self.wfile.write(line)
                self.wfile.flush()
                if line.startswith(b"data: ") and b"[DONE]" not in line:
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            content.append(delta)
                        # Some APIs include usage in the last chunk
                        usage = chunk.get("usage", {})
                        if usage:
                            pt  = usage.get("prompt_tokens",     usage.get("input_tokens",  pt))
                            ct_ = usage.get("completion_tokens", usage.get("output_tokens", ct_))
                            tt  = usage.get("total_tokens", pt + ct_)
                    except Exception:
                        pass
        except Exception:
            pass

        _log({"event_type": "llm_response", "request_id": rid, "model": model,
              "provider": route.get("provider",""), "route_name": route.get("name",""),
              "status_code": 200, "elapsed_seconds": round(time.time() - t0, 3),
              "stream": True, "prompt_tokens": pt, "completion_tokens": ct_, "total_tokens": tt,
              "response_content": "".join(content)[:5000]})


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    # If port already taken, another instance is running — exit quietly
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            print(f"LLMmon server already running on port {PORT}", file=sys.stderr)
            return

    # Pick up the splunk-system-user token (passAuth) and load configured creds.
    threading.Thread(target=_bootstrap, daemon=True).start()

    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"LLMmon server listening on port {PORT}", file=sys.stderr)
    sys.stderr.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
