"""MCP server registration + invocation handler.

v0.7.0 — implements `instructions/tool_credentials_and_mcp_design.md` §4.
Persists two KVStore collections (itmip_mcp_servers + itmip_mcp_tools),
calls upstream MCP servers via JSON-RPC over Streamable HTTP, and
audit-logs every invocation into `itmip_llm_custom_tool_calls`
(shared with the custom-tools handler so admins have one timeline).

Endpoints — REST under `/services/itmip_llm/mcp/...`:

  GET    /servers              List registered servers (visible-to-caller).
  POST   /servers              Create or update a server (admin only).
  DELETE /servers?key=<k>      Remove a server (admin only).
  POST   /servers/test_connect Connection-test + tools/list.
                               Body: { server_key | server } where
                               `server` is a draft McpServer for
                               testing before save.
  POST   /servers/refresh      Drift detection. Body: { server_key }.
  GET    /tools                List imported tools (visible-to-caller).
  POST   /tools                Import / save tool row. Admin only.
                               Body: { tool } or { tools: [...] } for
                               bulk import.
  DELETE /tools?key=<k>        Un-import a tool.
  POST   /invoke               Call an imported tool by exposed_name.
                               Body: { name, arguments, org, bu }.

The handler delegates JSON-RPC framing to McpClient (defined below).
Only Streamable HTTP transport is supported in v0.7.0 — stdio is
explicitly out of scope (spec §4.1), HTTP+SSE legacy is handled by the
same code path because Streamable HTTP is a superset.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
import uuid

# Splunk's persistent-handler runtime imports this file via
# importlib.util.spec_from_file_location, which does NOT add the
# script's directory to sys.path. Without this block, every
# `from itmip_llm_*` below would raise ImportError and Splunk would
# report the generic "Can't load script ..." with no traceback.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for _p in (APP_LIB, APP_BIN):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from splunk import rest
from splunk.persistconn import application

from itmip_llm_common import (
    APP_NAME,
    LLM_PASSWORD_REALM,
    err,
    is_admin,
    ok,
    rate_limit_check,
    system_token,
    user_name,
    user_token,
)
from itmip_llm_http_client import build_request, HTTPError, URLError
from itmip_llm_kvstore_changelog import emit_change
import _customer_auth
from itmip_llm_license import capability_enabled


# Collections — match collections.conf v0.7.0
MCP_SERVERS_COLLECTION = "itmip_mcp_servers"
MCP_TOOLS_COLLECTION = "itmip_mcp_tools"
AUDIT_COLLECTION = "itmip_llm_custom_tool_calls"  # shared with custom tools

DEFAULT_RATE_LIMIT = 60
DEFAULT_TIMEOUT_S = 30
HARD_MAX_BYTES = 512 * 1024
DEFAULT_MAX_BYTES = 32 * 1024
MCP_PROTOCOL_VERSION = "2025-11-25"


# ─────────────────────────────────────────────────────────────────────
# storage/passwords secret lookup (duplicated from custom_tools.py so
# this handler stays a self-contained module — keep these two impls in
# sync; both ultimately hit the same Splunk REST endpoint)
# ─────────────────────────────────────────────────────────────────────

def _resolve_secret(sys_token, name):
    if not name:
        return ""
    safe = "".join(c for c in name if c.isalnum() or c in "._-")
    if not safe:
        return ""
    path = (
        "/servicesNS/nobody/{app}/storage/passwords/"
        "{realm}%3A{name}%3A?output_mode=json"
    ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=safe)
    try:
        resp, content = rest.simpleRequest(path, sessionKey=sys_token, method="GET")
    except Exception as exc:
        msg = str(exc)
        if "404" in msg:
            return ""
        raise
    if getattr(resp, "status", 0) != 200:
        return ""
    data = json.loads(content)
    entries = data.get("entry") or []
    if not entries:
        return ""
    return (entries[0].get("content") or {}).get("clear_password") or ""


def _safe_lower(s):
    out = []
    for ch in (s or ""):
        c = ch.lower()
        if c.isalnum() or c in "_-":
            out.append(c)
    return "".join(out)


def _resolve_server_credential(sys_token, server, caller_org, caller_bu):
    """Resolve an MCP server's outbound credential per spec §4.3.

    Returns (secret, resolved_name, error) — mirrors the
    custom-tools resolver shape.
    """
    model = (server.get("credential_model") or "global").lower()
    ref = (server.get("credential_ref") or "").strip()
    if not ref:
        return "", "", None
    if model == "global":
        resolved = ref
    elif model == "per_tenant":
        resolved = (ref
                    .replace("{org}", _safe_lower(caller_org))
                    .replace("{bu}", _safe_lower(caller_bu)))
    else:
        # per_user explicitly rejected in v1 — spec §4.4
        return "", "", {
            "ok": False,
            "error": "MCP per_user credential model is not supported in v0.7.0.",
        }
    secret = _resolve_secret(sys_token, resolved)
    return secret, resolved, None


# ─────────────────────────────────────────────────────────────────────
# KVStore helpers
# ─────────────────────────────────────────────────────────────────────

def _coll_path(coll, rest_path=""):
    return "/servicesNS/nobody/{app}/storage/collections/data/{coll}{rest}".format(
        app=APP_NAME, coll=coll, rest=rest_path
    )


def _list_rows(sys_token, coll):
    path = _coll_path(coll) + "?output_mode=json"
    try:
        resp, content = rest.simpleRequest(path, sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) != 200:
            return []
        return json.loads(content) or []
    except Exception as exc:
        sys.stderr.write("itmip_llm_mcp _list_rows(%s) error: %s\n" % (coll, exc))
        return []


def _get_row(sys_token, coll, key):
    if not key:
        return None
    path = _coll_path(coll, "/" + key) + "?output_mode=json"
    try:
        resp, content = rest.simpleRequest(path, sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) != 200:
            return None
        return json.loads(content)
    except Exception:
        return None


def _upsert_row(sys_token, coll, row, key=None, user="unknown"):
    body = json.dumps(row)
    headers = [("Content-Type", "application/json"), ("Accept", "application/json")]
    if key:
        path = _coll_path(coll, "/" + key)
        rest.simpleRequest(
            path, sessionKey=sys_token, method="POST",
            jsonargs=body, getargs={"output_mode": "json"}, postargs=None,
            rawResult=True
        )
        emit_change(
            sys_token, coll, op="update", key=key,
            before=None, after=row, user=user,
        )
        return key
    path = _coll_path(coll)
    resp, content = rest.simpleRequest(
        path, sessionKey=sys_token, method="POST",
        jsonargs=body, getargs={"output_mode": "json"},
        rawResult=True
    )
    if getattr(resp, "status", 0) in (200, 201):
        try:
            new_key = (json.loads(content) or {}).get("_key") or ""
        except Exception:
            new_key = ""
        emit_change(
            sys_token, coll, op="create", key=new_key,
            before=None, after=row, user=user,
        )
        return new_key
    raise RuntimeError("Upsert into %s failed: %s" % (coll, getattr(resp, "status", 0)))


def _delete_row(sys_token, coll, key, user="unknown"):
    if not key:
        return
    path = _coll_path(coll, "/" + key)
    rest.simpleRequest(path, sessionKey=sys_token, method="DELETE", rawResult=True)
    emit_change(
        sys_token, coll, op="delete", key=key,
        before=None, after=None, user=user,
    )


def _audit(sys_token, doc):
    path = _coll_path(AUDIT_COLLECTION)
    try:
        rest.simpleRequest(
            path, sessionKey=sys_token, method="POST",
            jsonargs=json.dumps(doc),
            getargs={"output_mode": "json"},
            rawResult=True,
        )
    except Exception as exc:
        sys.stderr.write("itmip_llm_mcp audit error: %s\n" % exc)


# ─────────────────────────────────────────────────────────────────────
# Row encoding/decoding — JSON fields persisted as strings (KVStore
# enforceTypes=false; same pattern as custom tools).
# ─────────────────────────────────────────────────────────────────────

def _decode_server(row):
    if not isinstance(row, dict):
        return None
    return {
        "_key": row.get("_key") or "",
        "name": row.get("name") or "",
        "short": row.get("short") or "",
        "description": row.get("description") or "",
        "transport": row.get("transport") or "streamable_http",
        "endpoint_url": row.get("endpoint_url") or "",
        "org_short": row.get("org_short") or "DFLT",
        "bu_short": row.get("bu_short") or "*",
        "credential_model": row.get("credential_model") or "global",
        "credential_ref": row.get("credential_ref") or "",
        "auth_header_template": row.get("auth_header_template") or "",
        "proxy_url": row.get("proxy_url") or "",
        "proxy_credential_ref": row.get("proxy_credential_ref") or "",
        "customer_auth_hook": bool(row.get("customer_auth_hook")),
        "tls_ca_pem_ref": row.get("tls_ca_pem_ref") or "",
        "tls_skip_verify": bool(row.get("tls_skip_verify")),
        "health_status": row.get("health_status") or "unknown",
        "health_checked_at_epoch": row.get("health_checked_at_epoch") or 0,
        "created_by": row.get("created_by") or "",
        "created_at_epoch": row.get("created_at_epoch") or 0,
        "updated_by": row.get("updated_by") or "",
        "updated_at_epoch": row.get("updated_at_epoch") or 0,
    }


def _encode_server(doc, user):
    now = int(time.time())
    return {
        "name": doc.get("name") or "",
        "short": (doc.get("short") or "")[:8],
        "description": doc.get("description") or "",
        "transport": doc.get("transport") or "streamable_http",
        "endpoint_url": doc.get("endpoint_url") or "",
        "org_short": (doc.get("org_short") or "DFLT").upper(),
        "bu_short": (doc.get("bu_short") or "*").upper(),
        "credential_model": doc.get("credential_model") or "global",
        "credential_ref": doc.get("credential_ref") or "",
        "auth_header_template": doc.get("auth_header_template") or "Bearer {token}",
        "proxy_url": doc.get("proxy_url") or "",
        "proxy_credential_ref": doc.get("proxy_credential_ref") or "",
        "customer_auth_hook": bool(doc.get("customer_auth_hook")),
        "tls_ca_pem_ref": doc.get("tls_ca_pem_ref") or "",
        "tls_skip_verify": bool(doc.get("tls_skip_verify")),
        "health_status": doc.get("health_status") or "unknown",
        "health_checked_at_epoch": int(doc.get("health_checked_at_epoch") or 0),
        "created_by": doc.get("created_by") or user,
        "created_at_epoch": int(doc.get("created_at_epoch") or now),
        "updated_by": user,
        "updated_at_epoch": now,
    }


def _decode_tool(row):
    if not isinstance(row, dict):
        return None
    out = {
        "_key": row.get("_key") or "",
        "server_id": row.get("server_id") or "",
        "upstream_name": row.get("upstream_name") or "",
        "exposed_name": row.get("exposed_name") or "",
        "upstream_description": row.get("upstream_description") or "",
        "description_addendum": row.get("description_addendum") or "",
        "short_description": row.get("short_description") or "",
        "category": row.get("category") or "other",
        "org_short": row.get("org_short") or "DFLT",
        "bu_short": row.get("bu_short") or "*",
        "enabled": bool(row.get("enabled", True)),
        "upstream_drift": bool(row.get("upstream_drift")),
        "upstream_removed": bool(row.get("upstream_removed")),
        "last_refreshed_at_epoch": row.get("last_refreshed_at_epoch") or 0,
        "created_by": row.get("created_by") or "",
        "created_at_epoch": row.get("created_at_epoch") or 0,
        "updated_by": row.get("updated_by") or "",
        "updated_at_epoch": row.get("updated_at_epoch") or 0,
    }
    for src, dst in (
        ("upstream_input_schema_json", "upstream_input_schema"),
        ("response_json", "response"),
        ("guardrails_json", "guardrails"),
        ("tags_json", "tags"),
    ):
        raw = row.get(src) or ""
        if raw:
            try:
                out[dst] = json.loads(raw)
            except Exception:
                out[dst] = None
    return out


def _encode_tool(doc, user):
    now = int(time.time())
    return {
        "server_id": doc.get("server_id") or "",
        "upstream_name": doc.get("upstream_name") or "",
        "exposed_name": doc.get("exposed_name") or "",
        "upstream_description": doc.get("upstream_description") or "",
        "upstream_input_schema_json": json.dumps(doc.get("upstream_input_schema") or {}),
        "description_addendum": doc.get("description_addendum") or "",
        "short_description": doc.get("short_description") or "",
        "category": doc.get("category") or "other",
        "tags_json": json.dumps(doc.get("tags") or []),
        "org_short": (doc.get("org_short") or "DFLT").upper(),
        "bu_short": (doc.get("bu_short") or "*").upper(),
        "enabled": bool(doc.get("enabled", True)),
        "upstream_drift": bool(doc.get("upstream_drift")),
        "upstream_removed": bool(doc.get("upstream_removed")),
        "last_refreshed_at_epoch": int(doc.get("last_refreshed_at_epoch") or now),
        "response_json": json.dumps(doc.get("response") or {}),
        "guardrails_json": json.dumps(doc.get("guardrails") or {}),
        "created_by": doc.get("created_by") or user,
        "created_at_epoch": int(doc.get("created_at_epoch") or now),
        "updated_by": user,
        "updated_at_epoch": now,
    }


# ─────────────────────────────────────────────────────────────────────
# Visibility — same Org/BU + admin-bypass rule as custom tools
# ─────────────────────────────────────────────────────────────────────

def _row_visible_to(row, caller_org, caller_bu, admin):
    if admin:
        return True
    org = (row.get("org_short") or "DFLT").upper()
    bu = (row.get("bu_short") or "*").upper()
    o = (caller_org or "").upper()
    b = (caller_bu or "").upper()
    if org != "DFLT" and org != o:
        return False
    if bu != "*" and bu != b:
        return False
    return True


# ─────────────────────────────────────────────────────────────────────
# MCP client — JSON-RPC 2.0 over Streamable HTTP
# Spec: https://modelcontextprotocol.io/specification/2025-11-25
# ─────────────────────────────────────────────────────────────────────

class McpClient(object):
    """Minimal JSON-RPC 2.0 client for an MCP server over Streamable
    HTTP. Stateless — every call opens a fresh HTTP connection and
    sends a single JSON-RPC request. For our use case (initialize +
    tools/list + occasional tools/call) this is fine; long-lived
    sessions with server-initiated notifications would need an SSE
    reader, deferred to v0.8.0 when we add per-user OAuth.
    """

    def __init__(self, endpoint_url, auth_header=None,
                 proxy_url=None, proxy_credential=None,
                 ca_pem=None, extra_headers=None, timeout_s=30,
                 skip_verify=False):
        self.endpoint_url = endpoint_url
        self.auth_header = auth_header  # already-formatted "Bearer xyz" string
        self.proxy_url = proxy_url
        self.proxy_credential = proxy_credential
        self.ca_pem = ca_pem
        self.extra_headers = dict(extra_headers or {})
        self.timeout_s = timeout_s
        self.skip_verify = bool(skip_verify)
        self._next_id = 1

    def _rpc(self, method, params=None):
        """Send one JSON-RPC request, parse and return the result.

        Returns (result, error) — exactly one of which is non-None.
        Network errors / non-2xx HTTP responses are bubbled into
        `error` as a dict with `code: -32603, message: ..., http_status: ...`.
        """
        rpc_id = self._next_id
        self._next_id += 1
        body_obj = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params or {},
        }
        body_bytes = json.dumps(body_obj).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            # Streamable HTTP transport: accept BOTH single JSON and SSE,
            # per the 2025-11-25 spec. The server picks.
            "Accept": "application/json, text/event-stream",
        }
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        for k, v in self.extra_headers.items():
            if v is not None:
                headers[k] = v

        req, opener = build_request(
            self.endpoint_url, "POST", headers, body_bytes=body_bytes,
            proxy_url=self.proxy_url, proxy_credential=self.proxy_credential,
            ca_pem=self.ca_pem, skip_verify=self.skip_verify,
        )

        try:
            with opener.open(req, timeout=self.timeout_s) as resp:
                status = getattr(resp, "status", 0) or resp.getcode()
                content_type = resp.headers.get("Content-Type") or ""
                raw = resp.read(HARD_MAX_BYTES + 1)
                truncated = len(raw) > HARD_MAX_BYTES
                if truncated:
                    raw = raw[:HARD_MAX_BYTES]
        except HTTPError as he:
            try:
                body = he.read().decode("utf-8", errors="replace")[:512]
            except Exception:
                body = ""
            return None, {
                "code": he.code,
                "message": "HTTP %s from MCP server" % he.code,
                "http_status": he.code,
                "body": body,
            }
        except URLError as ue:
            return None, {
                "code": -32000,
                "message": "Network error talking to MCP server: %s" % ue,
                "http_status": 0,
            }
        except Exception as exc:
            return None, {
                "code": -32000,
                "message": "MCP transport error: %s" % exc,
                "http_status": 0,
            }

        # Parse — single-JSON path is by far the common case.
        text = raw.decode("utf-8", errors="replace")
        envelope = None
        if "text/event-stream" in content_type:
            # SSE: pick the first `data: {...}` frame that contains
            # the matching id. We don't stream — caller doesn't need
            # progress events for tools/list or tools/call.
            for line in text.split("\n"):
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str:
                    continue
                try:
                    cand = json.loads(data_str)
                except Exception:
                    continue
                if isinstance(cand, dict) and cand.get("id") == rpc_id:
                    envelope = cand
                    break
            if envelope is None:
                return None, {
                    "code": -32700,
                    "message": "SSE response carried no JSON-RPC frame matching id %d" % rpc_id,
                    "http_status": status,
                }
        else:
            try:
                envelope = json.loads(text)
            except Exception as exc:
                return None, {
                    "code": -32700,
                    "message": "Parse error: %s" % exc,
                    "http_status": status,
                    "raw_snippet": text[:256],
                }

        if not isinstance(envelope, dict):
            return None, {
                "code": -32700,
                "message": "JSON-RPC response was not an object",
                "http_status": status,
            }
        if envelope.get("error"):
            return None, envelope["error"]
        return envelope.get("result"), None

    def initialize(self, client_name="aiworkbench", client_version="0.7.0"):
        return self._rpc("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        })

    def tools_list(self):
        return self._rpc("tools/list", {})

    def tools_call(self, name, arguments):
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})


def _build_mcp_client_for_server(sys_token, server, caller_org="", caller_bu="", caller_user=""):
    """Construct a McpClient pre-loaded with proxy / CA / auth header
    derived from a server row + caller identity. Returns
    (client, error_dict|None)."""
    secret, resolved_name, struct_err = _resolve_server_credential(
        sys_token, server, caller_org, caller_bu
    )
    if struct_err:
        return None, struct_err

    auth_header = None
    template = server.get("auth_header_template") or ""
    # HTTP header values cannot contain newlines or other control
    # chars (urllib3 raises InvalidHeader on b'Bearer ...\n'). Bearer
    # tokens stored via the admin form sometimes carry a trailing
    # newline — paste-in-form artifact, or storage/passwords retaining
    # the trailing LF a copy-paste added. Strip whitespace before
    # forming the header. Only stripping endpoints, never the middle,
    # so PEM-shaped or otherwise structured values are unaffected.
    secret_for_header = secret.strip() if secret else secret
    if secret_for_header and template:
        auth_header = template.replace("{token}", secret_for_header)
    elif secret_for_header:
        auth_header = "Bearer " + secret_for_header

    proxy_url = server.get("proxy_url") or None
    proxy_cred_ref = server.get("proxy_credential_ref") or ""
    proxy_credential = _resolve_secret(sys_token, proxy_cred_ref) if proxy_cred_ref else None
    ca_pem_ref = server.get("tls_ca_pem_ref") or ""
    ca_pem = _resolve_secret(sys_token, ca_pem_ref) if ca_pem_ref else None
    # v0.9.5 — dev-mode TLS-skip. Refused on Splunk Cloud (compliance
    # posture) regardless of what's in KVStore. The flag may sit in the
    # stored config but takes no effect; an INFO line goes to
    # splunkd.log so admins see why.
    skip_verify = bool(server.get("tls_skip_verify"))
    if skip_verify:
        try:
            from itmip_llm_guid import is_splunk_cloud as _is_cloud
            if _is_cloud(sys_token):
                sys.stderr.write(
                    "itmip_llm_mcp: refusing tls_skip_verify on Splunk Cloud "
                    "for server '%s' — flag ignored, TLS verification stays on.\n"
                    % (server.get("name") or server.get("_key") or "?")
                )
                skip_verify = False
        except Exception:
            # Fail-safe: if Cloud detection fails, refuse the flag.
            skip_verify = False
    if skip_verify:
        sys.stderr.write(
            "itmip_llm_mcp: tls_verify_skipped=true endpoint=%s "
            "server=%s user=%s — dev-mode TLS skip is active.\n"
            % (server.get("endpoint_url") or "?",
               server.get("name") or server.get("_key") or "?",
               caller_user or "?")
        )

    extra_headers = {}
    if server.get("customer_auth_hook"):
        # Mint dynamic headers via the existing IAM hook with the new
        # target_kind="mcp" discriminator (spec §4.11, §7.1). A hook
        # failure is a hard refusal.
        hook_ctx = {
            "target_kind": "mcp",
            "mcp_server_name": server.get("name") or "",
            "mcp_endpoint_url": server.get("endpoint_url") or "",
            "splunk_user": caller_user or "",
            "splunk_session_key": "",
        }
        try:
            app_dir = sys.modules[__name__].__file__
            import os as _os
            app_dir = _os.path.dirname(_os.path.dirname(app_dir))
            hook_headers, hook_err = _customer_auth.invoke(app_dir, hook_ctx)
            if hook_err:
                return None, {
                    "ok": False,
                    "error": "customer_auth hook failed: %s" % hook_err,
                }
            for hk, hv in (hook_headers or {}).items():
                extra_headers[hk] = hv
        except Exception as exc:
            return None, {
                "ok": False,
                "error": "customer_auth hook crashed: %s" % exc,
            }

    client = McpClient(
        endpoint_url=server.get("endpoint_url") or "",
        auth_header=auth_header,
        proxy_url=proxy_url,
        proxy_credential=proxy_credential,
        ca_pem=ca_pem,
        extra_headers=extra_headers,
        timeout_s=DEFAULT_TIMEOUT_S,
        skip_verify=skip_verify,
    )
    # The resolved credential name flows into the audit row.
    client._credential_ref_resolved = resolved_name
    client._credential_model = (server.get("credential_model") or "global").lower()
    client._customer_auth_used = bool(server.get("customer_auth_hook"))
    client._tls_verify_skipped = skip_verify
    return client, None


# ─────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────

def _parse_query(args):
    qs = args.get("query") or []
    if isinstance(qs, list):
        return dict(qs)
    return dict(qs.items()) if hasattr(qs, "items") else {}


def _op_for(args):
    payload_raw = args.get("payload") or "{}"
    try:
        payload = json.loads(payload_raw) if payload_raw else {}
    except Exception:
        payload = {}
    if isinstance(payload, dict) and payload.get("op"):
        return payload.get("op"), payload
    # GET/DELETE callers carry the op discriminator in the query string
    # (no JSON body). Honor it BEFORE the path fallback — in this Splunk
    # build args["path_info"]/["path"] are empty, so the substring checks
    # below never match and every bodyless request would otherwise fall
    # through to the "servers" default (this is what made listMcpTools and
    # deleteMcpTool silently operate on servers → "Imported tools (0)").
    q = _parse_query(args)
    if q.get("op"):
        return q.get("op"), payload
    path = (args.get("path_info") or args.get("path") or "") or ""
    if "/servers/test_connect" in path:
        return "test_connect", payload
    if "/servers/refresh" in path:
        return "refresh", payload
    if "/servers" in path:
        return "servers", payload
    if "/tools" in path:
        return "tools", payload
    if "/invoke" in path:
        return "invoke", payload
    return "servers", payload


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if not user_token(args):
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")
            op, payload = _op_for(args)
            query = _parse_query(args)
            user = user_name(args)
            admin = is_admin(args, rest)

            # v1.4.1 — MCP server integrations are an Enterprise feature
            # (per-feature licensing). GET reads stay open so the UI can render
            # the greyed state; every ACTIVE MCP op (register/import/test/
            # refresh/invoke) is refused server-side below Enterprise. This is
            # authoritative — a direct REST call cannot bypass it. Fail-closed
            # via capability_enabled(). Spec: instructions/FEATURE_LICENSING_SPEC.md
            mcp_active = (
                op in ("invoke", "test_connect", "refresh")
                or (op == "servers" and method in ("POST", "DELETE"))
                or (op == "tools" and method in ("POST", "DELETE"))
            )
            if mcp_active and not capability_enabled(sys_token, "mcp_servers"):
                return err(
                    403, "MCP server integrations require an Enterprise license."
                )

            if op == "servers":
                return self._handle_servers(args, method, payload, query, sys_token, user, admin)
            if op == "test_connect":
                return self._handle_test_connect(args, method, payload, sys_token, user, admin)
            if op == "refresh":
                return self._handle_refresh(args, method, payload, sys_token, user, admin)
            if op == "tools":
                return self._handle_tools(args, method, payload, query, sys_token, user, admin)
            if op == "invoke":
                return self._handle_invoke(args, method, payload, sys_token, user, admin)
            return err(400, "Unknown op '%s'." % op)
        except Exception as exc:
            sys.stderr.write(
                "itmip_llm_mcp error: %s\n%s\n"
                % (exc, traceback.format_exc())
            )
            return err(500, "Internal error: %s" % exc)

    # ────── servers ──────

    def _handle_servers(self, args, method, payload, query, sys_token, user, admin):
        if method == "GET":
            rows = _list_rows(sys_token, MCP_SERVERS_COLLECTION)
            caller_org = (query.get("org") or payload.get("org") or "").upper()
            caller_bu = (query.get("bu") or payload.get("bu") or "").upper()
            visible = [r for r in rows if _row_visible_to(r, caller_org, caller_bu, admin)]
            return ok({"items": [_decode_server(r) for r in visible if r]})
        if method == "POST":
            if not admin:
                return err(403, "Only Splunk admins can manage MCP servers.")
            doc = payload.get("server") or payload
            doc = {k: v for k, v in doc.items() if k != "op"}
            if not doc.get("name"):
                return err(400, "'name' is required.")
            if not doc.get("endpoint_url"):
                return err(400, "'endpoint_url' is required.")
            if (doc.get("credential_model") or "global") == "per_user":
                return err(400, "MCP per_user credential model is rejected in v0.7.0 (spec §4.4).")
            row = _encode_server(doc, user)
            key = doc.get("_key") or None
            try:
                if key:
                    _upsert_row(sys_token, MCP_SERVERS_COLLECTION, row, key=key, user=user)
                    return ok({"ok": True, "_key": key})
                new_key = _upsert_row(sys_token, MCP_SERVERS_COLLECTION, row, user=user)
                return ok({"ok": True, "_key": new_key})
            except Exception as exc:
                return err(502, "Could not save MCP server: %s" % exc)
        if method == "DELETE":
            if not admin:
                return err(403, "Only Splunk admins can remove MCP servers.")
            key = query.get("key") or payload.get("_key") or ""
            if not key:
                return err(400, "'key' is required.")
            # Also un-import every tool that belonged to this server.
            tool_rows = _list_rows(sys_token, MCP_TOOLS_COLLECTION)
            for tr in tool_rows:
                if tr.get("server_id") == key:
                    try:
                        _delete_row(sys_token, MCP_TOOLS_COLLECTION, tr.get("_key") or "", user=user)
                    except Exception:
                        pass
            try:
                _delete_row(sys_token, MCP_SERVERS_COLLECTION, key, user=user)
                return ok({"ok": True, "_key": key})
            except Exception as exc:
                return err(502, "Could not delete server: %s" % exc)
        return err(405, "Only GET/POST/DELETE supported on /servers.")

    # ────── test_connect ──────

    def _handle_test_connect(self, args, method, payload, sys_token, user, admin):
        if method != "POST":
            return err(405, "Only POST is supported on /servers/test_connect.")
        if not admin:
            return err(403, "Only Splunk admins can test MCP servers.")
        # Accept either a server_key (already saved) or an inline draft.
        server = None
        key = payload.get("server_key") or ""
        if key:
            server = _get_row(sys_token, MCP_SERVERS_COLLECTION, key)
            if not server:
                return err(404, "Server '%s' not found." % key)
            server = _decode_server(server)
        else:
            draft = payload.get("server") or {}
            if not draft.get("endpoint_url"):
                return err(400, "'server.endpoint_url' is required for an inline test.")
            server = _decode_server(draft)

        caller_org = (payload.get("org") or "").upper()
        caller_bu = (payload.get("bu") or "").upper()
        client, build_err = _build_mcp_client_for_server(
            sys_token, server, caller_org, caller_bu, user
        )
        if build_err:
            return ok({"ok": False, "error": build_err.get("error") or "client_build_failed"})

        result, rpc_err = client.initialize()
        if rpc_err:
            return ok({
                "ok": False,
                "stage": "initialize",
                "error": rpc_err.get("message") or "initialize failed",
                "details": rpc_err,
            })
        server_info = {
            "name": (result.get("serverInfo") or {}).get("name") or "",
            "version": (result.get("serverInfo") or {}).get("version") or "",
            "protocol_version": result.get("protocolVersion") or "",
            "capabilities": result.get("capabilities") or {},
        }

        tools_result, rpc_err = client.tools_list()
        if rpc_err:
            return ok({
                "ok": False,
                "stage": "tools/list",
                "error": rpc_err.get("message") or "tools/list failed",
                "details": rpc_err,
                "server_info": server_info,
            })
        tools = (tools_result or {}).get("tools") or []

        # Update health on the persisted row (if it was the saved one).
        if key:
            row = _get_row(sys_token, MCP_SERVERS_COLLECTION, key) or {}
            row["health_status"] = "healthy"
            row["health_checked_at_epoch"] = int(time.time())
            try:
                _upsert_row(sys_token, MCP_SERVERS_COLLECTION, row, key=key, user=user)
            except Exception:
                pass

        return ok({
            "ok": True,
            "server_info": server_info,
            "tools": [{
                "name": t.get("name") or "",
                "description": t.get("description") or "",
                "inputSchema": t.get("inputSchema") or {},
            } for t in tools if isinstance(t, dict)],
        })

    # ────── refresh ──────

    def _handle_refresh(self, args, method, payload, sys_token, user, admin):
        if method != "POST":
            return err(405, "Only POST is supported on /servers/refresh.")
        if not admin:
            return err(403, "Only Splunk admins can refresh MCP servers.")
        key = payload.get("server_key") or ""
        if not key:
            return err(400, "'server_key' is required.")
        server_row = _get_row(sys_token, MCP_SERVERS_COLLECTION, key)
        if not server_row:
            return err(404, "Server '%s' not found." % key)
        server = _decode_server(server_row)
        client, build_err = _build_mcp_client_for_server(sys_token, server, "", "", user)
        if build_err:
            return ok({"ok": False, "error": build_err.get("error")})
        _init_ok, init_err = client.initialize()
        if init_err:
            return ok({"ok": False, "stage": "initialize", "error": init_err.get("message")})
        tools_result, list_err = client.tools_list()
        if list_err:
            return ok({"ok": False, "stage": "tools/list", "error": list_err.get("message")})
        upstream = {(t.get("name") or ""): t for t in (tools_result or {}).get("tools") or []}

        imported = [_decode_tool(r) for r in _list_rows(sys_token, MCP_TOOLS_COLLECTION)
                    if r.get("server_id") == key]
        changes = []
        for t in imported:
            uname = t.get("upstream_name") or ""
            current = upstream.get(uname)
            row = _get_row(sys_token, MCP_TOOLS_COLLECTION, t.get("_key") or "")
            if not row:
                continue
            if current is None:
                row["upstream_removed"] = True
                row["enabled"] = False
                changes.append({"exposed_name": t.get("exposed_name"), "kind": "removed"})
            else:
                cur_desc = current.get("description") or ""
                cur_schema = current.get("inputSchema") or {}
                drift = (
                    cur_desc != (t.get("upstream_description") or "")
                    or json.dumps(cur_schema, sort_keys=True)
                    != json.dumps(t.get("upstream_input_schema") or {}, sort_keys=True)
                )
                row["upstream_drift"] = drift
                if drift:
                    changes.append({"exposed_name": t.get("exposed_name"), "kind": "drift"})
            row["last_refreshed_at_epoch"] = int(time.time())
            try:
                _upsert_row(sys_token, MCP_TOOLS_COLLECTION, row, key=row.get("_key") or t.get("_key") or "", user=user)
            except Exception:
                pass

        new_upstream_names = set(upstream.keys()) - {t.get("upstream_name") for t in imported}
        return ok({
            "ok": True,
            "changes": changes,
            "available_upstream_tools": sorted(new_upstream_names),
        })

    # ────── tools (imports) ──────

    def _handle_tools(self, args, method, payload, query, sys_token, user, admin):
        if method == "GET":
            rows = _list_rows(sys_token, MCP_TOOLS_COLLECTION)
            caller_org = (query.get("org") or payload.get("org") or "").upper()
            caller_bu = (query.get("bu") or payload.get("bu") or "").upper()
            visible = [r for r in rows if _row_visible_to(r, caller_org, caller_bu, admin)]
            return ok({"items": [_decode_tool(r) for r in visible if r]})
        if method == "POST":
            if not admin:
                return err(403, "Only Splunk admins can manage imported tools.")
            many = payload.get("tools")
            if isinstance(many, list):
                keys = []
                for d in many:
                    row = _encode_tool(d, user)
                    keys.append(_upsert_row(sys_token, MCP_TOOLS_COLLECTION, row,
                                            key=(d.get("_key") or None), user=user))
                return ok({"ok": True, "keys": keys})
            doc = payload.get("tool") or payload
            doc = {k: v for k, v in doc.items() if k not in ("op",)}
            if not doc.get("server_id"):
                return err(400, "'server_id' is required.")
            if not doc.get("upstream_name"):
                return err(400, "'upstream_name' is required.")
            row = _encode_tool(doc, user)
            try:
                key = doc.get("_key") or None
                if key:
                    _upsert_row(sys_token, MCP_TOOLS_COLLECTION, row, key=key, user=user)
                    return ok({"ok": True, "_key": key})
                new_key = _upsert_row(sys_token, MCP_TOOLS_COLLECTION, row, user=user)
                return ok({"ok": True, "_key": new_key})
            except Exception as exc:
                return err(502, "Could not save imported tool: %s" % exc)
        if method == "DELETE":
            if not admin:
                return err(403, "Only Splunk admins can un-import tools.")
            key = query.get("key") or payload.get("_key") or ""
            if not key:
                return err(400, "'key' is required.")
            try:
                _delete_row(sys_token, MCP_TOOLS_COLLECTION, key, user=user)
                return ok({"ok": True, "_key": key})
            except Exception as exc:
                return err(502, "Could not delete tool: %s" % exc)
        return err(405, "Only GET/POST/DELETE supported on /tools.")

    # ────── invoke ──────

    def _handle_invoke(self, args, method, payload, sys_token, user, admin):
        if method != "POST":
            return err(405, "Only POST is supported on /invoke.")
        name = payload.get("name") or ""
        arguments = payload.get("arguments") or {}
        if not name:
            return err(400, "'name' is required (exposed_name).")
        if not isinstance(arguments, dict):
            return err(400, "'arguments' must be an object.")

        caller_org = (payload.get("org") or "").upper()
        caller_bu = (payload.get("bu") or "").upper()

        rows = _list_rows(sys_token, MCP_TOOLS_COLLECTION)
        tool_row = None
        for r in rows:
            if (r.get("exposed_name") or "") == name:
                tool_row = r
                break
        if not tool_row:
            return err(404, "MCP tool '%s' not found." % name)
        if not _row_visible_to(tool_row, caller_org, caller_bu, admin):
            return err(403, "MCP tool '%s' is not in scope for this user." % name)
        if not tool_row.get("enabled", True):
            return err(403, "MCP tool '%s' is disabled." % name)

        tool = _decode_tool(tool_row)
        server_row = _get_row(sys_token, MCP_SERVERS_COLLECTION, tool.get("server_id") or "")
        if not server_row:
            return err(502, "MCP server for tool '%s' has disappeared." % name)
        server = _decode_server(server_row)

        guard = tool.get("guardrails") or {}
        cap = int(guard.get("rate_limit_per_minute") or DEFAULT_RATE_LIMIT)
        if not rate_limit_check("mcp_tool:%s" % name, user, cap):
            return err(429, "Rate limit exceeded for MCP tool '%s'." % name)

        started = time.time()
        args_hash = hashlib.sha256(
            json.dumps(arguments, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        client, build_err = _build_mcp_client_for_server(
            sys_token, server, caller_org, caller_bu, user
        )
        if build_err:
            self._audit(sys_token, name, user, caller_org, caller_bu, args_hash,
                        "error", build_err.get("error") or "client_build_failed",
                        int((time.time() - started) * 1000),
                        cached=False, customer_auth_used=False,
                        credential_model=(server.get("credential_model") or "global"),
                        credential_ref_resolved="",
                        mcp_server_id=server.get("_key"),
                        mcp_upstream_name=tool.get("upstream_name"),
                        tls_verify_skipped=bool(server.get("tls_skip_verify")))
            return ok({"ok": False, "error": build_err.get("error")})

        # Initialise then call.
        _init_ok, init_err = client.initialize()
        if init_err:
            self._audit(sys_token, name, user, caller_org, caller_bu, args_hash,
                        "error", "initialize: " + str(init_err.get("message")),
                        int((time.time() - started) * 1000),
                        cached=False, customer_auth_used=client._customer_auth_used,
                        credential_model=client._credential_model,
                        credential_ref_resolved=client._credential_ref_resolved,
                        mcp_server_id=server.get("_key"),
                        mcp_upstream_name=tool.get("upstream_name"),
                        tls_verify_skipped=client._tls_verify_skipped)
            return ok({"ok": False, "stage": "initialize", "error": init_err.get("message")})

        call_result, rpc_err = client.tools_call(tool.get("upstream_name") or "", arguments)
        duration_ms = int((time.time() - started) * 1000)
        if rpc_err:
            self._audit(sys_token, name, user, caller_org, caller_bu, args_hash,
                        "error", "tools/call: " + str(rpc_err.get("message")),
                        duration_ms,
                        cached=False, customer_auth_used=client._customer_auth_used,
                        credential_model=client._credential_model,
                        credential_ref_resolved=client._credential_ref_resolved,
                        mcp_server_id=server.get("_key"),
                        mcp_upstream_name=tool.get("upstream_name"),
                        tls_verify_skipped=client._tls_verify_skipped)
            return ok({"ok": False, "stage": "tools/call",
                       "error": rpc_err.get("message"),
                       "upstream_status": rpc_err.get("http_status")})

        # Apply response-shaping (max_bytes + redact) — same conventions
        # as custom tools.
        response_cfg = tool.get("response") or {}
        max_bytes = min(int(response_cfg.get("max_bytes") or DEFAULT_MAX_BYTES), HARD_MAX_BYTES)
        serialized = (
            call_result if isinstance(call_result, str)
            else json.dumps(call_result, default=str)
        )
        truncated = False
        if len(serialized) > max_bytes:
            serialized = serialized[:max_bytes]
            truncated = True

        self._audit(sys_token, name, user, caller_org, caller_bu, args_hash,
                    "ok", "", duration_ms,
                    cached=False, customer_auth_used=client._customer_auth_used,
                    credential_model=client._credential_model,
                    credential_ref_resolved=client._credential_ref_resolved,
                    mcp_server_id=server.get("_key"),
                    mcp_upstream_name=tool.get("upstream_name"),
                    tls_verify_skipped=client._tls_verify_skipped)
        return ok({
            "ok": True,
            "result": serialized,
            "truncated": truncated,
            "kind": "mcp_tool",
            "name": tool.get("exposed_name") or "",
            "mcp_server_id": server.get("_key") or "",
            "mcp_upstream_name": tool.get("upstream_name") or "",
        })

    def _audit(self, sys_token, name, user, org, bu, args_hash, status_label,
               error_text, duration_ms, cached, customer_auth_used,
               credential_model, credential_ref_resolved,
               mcp_server_id="", mcp_upstream_name="",
               tls_verify_skipped=False):
        _audit(sys_token, {
            "tool_name": name,
            "user": user,
            "org_short": org,
            "bu_short": bu,
            "arguments_hash": args_hash,
            "status": status_label,
            "error": error_text,
            "duration_ms": duration_ms,
            "cached": bool(cached),
            "customer_auth_used": bool(customer_auth_used),
            "credential_model": credential_model or "",
            "credential_ref_resolved": credential_ref_resolved or "",
            "tls_verify_skipped": bool(tls_verify_skipped),
            "tool_kind": "mcp",
            "mcp_server_id": mcp_server_id or "",
            "mcp_upstream_name": mcp_upstream_name or "",
            "created_at": int(time.time() * 1000),
        })

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass


# Unique-id helpers — primarily for debugging when no upstream id flows.
def _new_uuid():
    return uuid.uuid4().hex
