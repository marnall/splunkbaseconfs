"""GET/POST/DELETE /services/itmip_llm/custom_tools — admin-defined LLM tools.

Two logical sub-resources, dispatched via the `op` payload field on POST
or the URL tail:

  GET    .../definitions          -> list visible tool definitions
  POST   .../definitions          -> upsert (admin only)
  DELETE .../definitions?key=...  -> delete (admin only)
  POST   .../invoke               -> { name, arguments } -> tool result

The definitions endpoint round-trips the JSON-shaped `CustomToolDefinition`
described in src/types.ts. The browser only ever sees the {name, version,
title, description, parameters, scope, enabled} surface — the
`implementation` block stays on the search head so admins can store
credential references that never reach the client.

Security:
- WRITE (POST/DELETE on definitions) is admin-only.
- /invoke is open to any authenticated user, but the definition must be
  in-scope for that user's Org/BU.
- Every /invoke renders `{{ name }}` placeholders into url/query/headers/body
  using a strict whitelist (no Python eval), then re-checks the resolved
  host against `allowed_hosts`.
- RFC1918 / loopback hosts are refused unless the definition opts in via
  `implementation.allow_internal = true`.
- Credentials are resolved server-side from storage/passwords (realm =
  itmip_llm_assistent_app) and never logged.
- Per (user, tool) rate-limit (default 30/min, override via guardrails).
- In-memory result cache keyed by (name, arguments_hash) with the
  configured TTL.
- Successful & failed invocations are audited into
  itmip_llm_custom_tool_calls (admin-readable).
"""

import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
import traceback
from urllib.parse import urlencode, urlparse

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

import _customer_auth  # noqa: E402  — shared with itmip_llm_proxy.py
from itmip_llm_common import (  # noqa: E402
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
from itmip_llm_kvstore_changelog import emit_change  # noqa: E402
from itmip_llm_license import capability_enabled  # noqa: E402


COLLECTION = "itmip_llm_custom_tools"
AUDIT_COLLECTION = "itmip_llm_custom_tool_calls"

TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Strict whitelist substitution: only `{{ name }}` where name is a
# parameter key. NO arbitrary Python expressions.
TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

DEFAULT_TIMEOUT_S = 10
DEFAULT_RATE_LIMIT = 30
DEFAULT_MAX_BYTES = 8192
HARD_MAX_BYTES = 64 * 1024


# Process-local cache: (tool_name, args_hash) -> (expires_epoch, payload)
_cache = {}


# ─────────────────────────────────────────────────────────────────────
# Definition validation
# ─────────────────────────────────────────────────────────────────────

ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
ALLOWED_IMPL_TYPES = {"http", "splunk_search", "kvstore_lookup", "python"}
SUPPORTED_IMPL_TYPES = {"http"}  # MVP — others reserved but reject at /invoke
ALLOWED_SHARING = {"private", "app", "global"}
ALLOWED_TRANSFORMS = {"none", "jq", "jsonpath", None, ""}


def _validate_parameters_schema(p):
    """Light JSON Schema draft-07 sanity check. We don't pull jsonschema
    as a dep — admins typing free-form schemas hit a parser anyway, and
    we just want to refuse the obviously wrong shapes."""
    if not isinstance(p, dict):
        return "parameters must be an object."
    if p.get("type") != "object":
        return "parameters.type must be 'object'."
    props = p.get("properties")
    if props is not None and not isinstance(props, dict):
        return "parameters.properties must be an object."
    req = p.get("required")
    if req is not None and not isinstance(req, list):
        return "parameters.required must be an array."
    if isinstance(req, list):
        for r in req:
            if not isinstance(r, str):
                return "parameters.required entries must be strings."
            if isinstance(props, dict) and r not in props:
                return "parameters.required entry '%s' is not in parameters.properties." % r
    return None


def _is_internal_host(host):
    """True for RFC1918, loopback, link-local. host can be a literal IP
    or a name. For names, do a best-effort DNS resolution; if it fails,
    treat as NOT internal (we then fall through to allowlist check, which
    is the actual gate)."""
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        pass
    try:
        info = socket.getaddrinfo(host, None)
        for fam, _t, _p, _c, sa in info:
            addr = sa[0]
            try:
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return True
            except ValueError:
                continue
    except Exception:
        pass
    return False


def _validate_definition(doc):
    """Return None on success, an error string on failure."""
    name = doc.get("name") or ""
    if not TOOL_NAME_RE.match(name):
        return ("Tool name must match ^[a-z][a-z0-9_]{2,63}$ "
                "(lowercase, starts with a letter).")
    version = doc.get("version") or ""
    if not VERSION_RE.match(version):
        return "Tool version must be semver (e.g. '1.0.0')."
    desc = doc.get("description") or ""
    if not isinstance(desc, str) or len(desc.strip()) < 8:
        return "Description is required (>= 8 characters)."

    scope = doc.get("scope") or {}
    if not isinstance(scope, dict):
        return "scope must be an object."
    if scope.get("sharing") not in ALLOWED_SHARING:
        return "scope.sharing must be one of: private, app, global."
    if not isinstance(scope.get("owner_org") or "", str):
        return "scope.owner_org must be a string."
    if not isinstance(scope.get("owner_bu") or "", str):
        return "scope.owner_bu must be a string."

    err_msg = _validate_parameters_schema(doc.get("parameters"))
    if err_msg:
        return err_msg

    impl = doc.get("implementation") or {}
    if not isinstance(impl, dict):
        return "implementation must be an object."
    itype = impl.get("type")
    if itype not in ALLOWED_IMPL_TYPES:
        return ("implementation.type must be one of: %s."
                % ", ".join(sorted(ALLOWED_IMPL_TYPES)))
    if itype == "http":
        method = (impl.get("method") or "GET").upper()
        if method not in ALLOWED_METHODS:
            return "implementation.method must be one of: %s." % ", ".join(sorted(ALLOWED_METHODS))
        url = impl.get("url") or ""
        if not isinstance(url, str) or not url.strip():
            return "implementation.url is required."
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return "implementation.url must use http or https."
        allowed = impl.get("allowed_hosts") or []
        if not isinstance(allowed, list) or not allowed:
            return "implementation.allowed_hosts must be a non-empty array."
        for h in allowed:
            if not isinstance(h, str) or not h.strip():
                return "implementation.allowed_hosts entries must be strings."
        # If the literal URL host is internal AND the def doesn't opt
        # in, refuse — same gate /invoke applies at call time.
        if not impl.get("allow_internal"):
            for h in allowed:
                if _is_internal_host(h):
                    return ("Host '%s' resolves to a private/loopback address. "
                            "Set implementation.allow_internal=true to permit it."
                            % h)
        timeout = impl.get("timeout_seconds")
        if timeout is not None and not isinstance(timeout, (int, float)):
            return "implementation.timeout_seconds must be a number."
        auth = impl.get("auth") or {}
        if auth and auth.get("type") not in (None, "none", "basic", "bearer", "header"):
            return "implementation.auth.type must be one of: none, basic, bearer, header."
        # customer_auth is a parallel layer that composes with auth.type.
        # Either or both may be set; both together is the common
        # "static X-Api-Key + IAM-minted bearer" compound case.
        if "customer_auth" in impl and not isinstance(impl.get("customer_auth"), bool):
            return "implementation.customer_auth must be a boolean."

    resp = doc.get("response") or {}
    if resp:
        if not isinstance(resp, dict):
            return "response must be an object."
        t = resp.get("transform")
        if t not in ALLOWED_TRANSFORMS:
            return "response.transform must be one of: none, jq, jsonpath."

    guard = doc.get("guardrails") or {}
    if guard and not isinstance(guard, dict):
        return "guardrails must be an object."

    return None


# ─────────────────────────────────────────────────────────────────────
# Scope filtering
# ─────────────────────────────────────────────────────────────────────

def _user_caller_scope(args, rest_mod):
    """Cheap proxy for the caller's Org/BU. The full tenancy resolution
    lives in the React layer; the handler only needs to scope-filter
    so an end-user listing tools doesn't see private tools that aren't
    theirs. Admins always see everything.
    """
    # The browser passes the resolved org/bu in the request payload so we
    # don't duplicate the entire tenancy logic on the server. Validated
    # against the user's own roles for admin-only writes.
    return None


def _doc_visible_to(doc, caller_org, caller_bu, is_admin_flag):
    """True when the calling user is allowed to see this tool definition."""
    if is_admin_flag:
        return True
    if not doc.get("enabled", True):
        return False
    sharing = doc.get("scope_sharing") or "private"
    owner_org = (doc.get("scope_owner_org") or "").upper()
    owner_bu = (doc.get("scope_owner_bu") or "").upper()
    co = (caller_org or "").upper()
    cb = (caller_bu or "").upper()
    if sharing == "global":
        return True
    if sharing == "app":
        return owner_org == co
    if sharing == "private":
        return owner_org == co and owner_bu == cb
    return False


# ─────────────────────────────────────────────────────────────────────
# KVStore I/O
# ─────────────────────────────────────────────────────────────────────

def _coll_path(rest_segment=""):
    return "/servicesNS/nobody/{app}/storage/collections/data/{coll}{rest}".format(
        app=APP_NAME, coll=COLLECTION, rest=rest_segment
    )


def _audit_path():
    return "/servicesNS/nobody/{app}/storage/collections/data/{coll}".format(
        app=APP_NAME, coll=AUDIT_COLLECTION
    )


def _decode_row(row):
    """Convert the persisted shape (JSON-as-string fields) back to the
    full CustomToolDefinition envelope."""
    if not isinstance(row, dict):
        return None
    out = {
        "_key": row.get("_key", ""),
        "name": row.get("name", ""),
        "version": row.get("version", ""),
        "title": row.get("title", ""),
        "description": row.get("description", ""),
        "scope": {
            "sharing": row.get("scope_sharing", "private"),
            "owner_org": row.get("scope_owner_org", ""),
            "owner_bu": row.get("scope_owner_bu", ""),
        },
        "enabled": row.get("enabled", True),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
    for src, dst in (
        ("parameters_json", "parameters"),
        ("implementation_json", "implementation"),
        ("response_json", "response"),
        ("guardrails_json", "guardrails"),
    ):
        raw = row.get(src) or ""
        if raw:
            try:
                out[dst] = json.loads(raw)
            except Exception:
                out[dst] = None
    return out


def _encode_doc(doc, user):
    """Convert a validated definition into the flat row we persist."""
    now = int(time.time() * 1000)
    return {
        "name": doc.get("name", ""),
        "version": doc.get("version", ""),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "scope_sharing": (doc.get("scope") or {}).get("sharing", "private"),
        "scope_owner_org": (doc.get("scope") or {}).get("owner_org", ""),
        "scope_owner_bu": (doc.get("scope") or {}).get("owner_bu", ""),
        "parameters_json": json.dumps(doc.get("parameters") or {}),
        "implementation_json": json.dumps(doc.get("implementation") or {}),
        "response_json": json.dumps(doc.get("response") or {}),
        "guardrails_json": json.dumps(doc.get("guardrails") or {}),
        "enabled": bool(doc.get("enabled", True)),
        "created_by": user,
        "created_at": doc.get("created_at") or now,
        "updated_at": now,
    }


def _list_rows(sys_token):
    resp, content = rest.simpleRequest(
        _coll_path() + "?output_mode=json",
        sessionKey=sys_token,
        method="GET",
    )
    status = getattr(resp, "status", 0)
    if status == 404:
        return []
    if status != 200:
        raise RuntimeError("KVStore list returned %s" % status)
    data = json.loads(content)
    return data if isinstance(data, list) else []


def _find_row_by_name(sys_token, name):
    rows = _list_rows(sys_token)
    for r in rows:
        if r.get("name") == name:
            return r
    return None


def _upsert_row(sys_token, row, key=None):
    if key:
        path = _coll_path("/{}".format(key))
        resp, content = rest.simpleRequest(
            path,
            sessionKey=sys_token,
            method="POST",
            jsonargs=json.dumps(row),
        )
        status = getattr(resp, "status", 0)
        if status in (200, 201):
            return key
        raise RuntimeError("KVStore upsert returned %s: %s" % (status, (content or "")[:200]))
    resp, content = rest.simpleRequest(
        _coll_path(),
        sessionKey=sys_token,
        method="POST",
        jsonargs=json.dumps(row),
    )
    status = getattr(resp, "status", 0)
    if status in (200, 201):
        try:
            body = json.loads(content)
            return body.get("_key", "")
        except Exception:
            return ""
    raise RuntimeError("KVStore insert returned %s: %s" % (status, (content or "")[:200]))


def _delete_row(sys_token, key):
    resp, _content = rest.simpleRequest(
        _coll_path("/{}".format(key)),
        sessionKey=sys_token,
        method="DELETE",
    )
    status = getattr(resp, "status", 0)
    if status in (200, 204, 404):
        return True
    raise RuntimeError("KVStore delete returned %s" % status)


def _audit(sys_token, doc):
    try:
        rest.simpleRequest(
            _audit_path(),
            sessionKey=sys_token,
            method="POST",
            jsonargs=json.dumps(doc),
        )
    except Exception:
        # Auditing must never block the tool call.
        pass


# ─────────────────────────────────────────────────────────────────────
# Template substitution
# ─────────────────────────────────────────────────────────────────────

def _render(value, arguments):
    """Substitute `{{ name }}` placeholders against `arguments`. Strings
    only — recurses through dicts and lists. Missing keys raise
    KeyError so we fail closed instead of silently sending blanks."""
    if isinstance(value, str):
        def sub(match):
            key = match.group(1)
            if key not in arguments:
                raise KeyError(key)
            v = arguments[key]
            if isinstance(v, (dict, list)):
                return json.dumps(v)
            return str(v)
        return TEMPLATE_RE.sub(sub, value)
    if isinstance(value, dict):
        return {k: _render(v, arguments) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, arguments) for v in value]
    return value


# ─────────────────────────────────────────────────────────────────────
# Secret resolution
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
    """Normalise an Org/BU/user fragment for credential-name templates.
    Only [a-z0-9_-] survives — anything else becomes ''. Mirrors what
    storage/passwords names accept, and stops a hostile Org name from
    breaking the credential lookup."""
    out = []
    for ch in (s or ""):
        c = ch.lower()
        if c.isalnum() or c in "_-":
            out.append(c)
    return "".join(out)


def _resolve_credential_for_auth(sys_token, auth, ctx):
    """v0.7.0 — resolve a credential under the three-tier model.

    `auth` is the tool's auth block (the dict at
    definition.implementation.auth). `ctx` carries the per-call
    identity:
      - ctx["user"], ctx["org"], ctx["bu"]

    Returns a triple `(secret, resolved_ref, error)`:
      - secret: the cleartext, or "" when missing.
      - resolved_ref: the actual storage/passwords name that was
        looked up (for audit). Empty when no credential is configured.
      - error: a structured dict per spec §2.4 when the credential is
        missing in a way the caller needs to act on (per-user OAuth
        flow), OR None to signal "not actionable, just empty".

    Backward compatibility (spec §2.3): when `credential_model` is
    absent and `credential_ref` is set, this is interpreted as the
    `global` model with `credential_ref` as the literal name.
    """
    if not auth:
        return "", "", None

    model = (auth.get("credential_model") or "global").lower()
    legacy_ref = (auth.get("credential_ref") or "").strip()
    template = (auth.get("credential_ref_template") or "").strip()

    # Determine the resolved name per the model.
    if model == "global":
        # If a template was given on a global tool, allow it but the
        # only substitutions performed are the trivial empty-arg case.
        resolved = template or legacy_ref
    elif model == "per_tenant":
        if not template:
            return "", "", {"ok": False, "error": "per_tenant credential_ref_template is required."}
        org = _safe_lower(ctx.get("org"))
        bu = _safe_lower(ctx.get("bu"))
        resolved = (template
                    .replace("{org}", org)
                    .replace("{bu}", bu)
                    .replace("{user}", ""))
    elif model == "per_user":
        # Phase 3 — full OAuth flow not implemented in v0.7.0. For now
        # we resolve the credential name but if it's missing we
        # return the spec §2.4 structured error so the LLM can ask the
        # user to connect their account. The auth_url is null until
        # Phase 3 lands the actual OAuth redirect endpoint.
        if not template:
            return "", "", {"ok": False, "error": "per_user credential_ref_template is required."}
        user = _safe_lower(ctx.get("user"))
        resolved = (template
                    .replace("{user}", user)
                    .replace("{org}", _safe_lower(ctx.get("org")))
                    .replace("{bu}", _safe_lower(ctx.get("bu"))))
    else:
        return "", "", {"ok": False, "error": "Unknown credential_model '%s'." % model}

    if not resolved:
        return "", "", None

    secret = _resolve_secret(sys_token, resolved)
    if not secret and model == "per_user":
        return "", resolved, {
            "ok": False,
            "error": "no_user_credential",
            "auth_url": None,  # Phase 3 will populate this with the OAuth-start URL
            "message": ("No per-user credential is stored for '%s'. "
                        "Connect your account in Settings → Tool credentials, "
                        "then re-try.") % resolved,
        }
    return secret, resolved, None


# ─────────────────────────────────────────────────────────────────────
# HTTP runtime
# ─────────────────────────────────────────────────────────────────────

def _apply_redact(value, fields):
    fields_set = {f for f in (fields or []) if isinstance(f, str)}
    if not fields_set:
        return value

    def walk(v):
        if isinstance(v, dict):
            return {
                k: ("[REDACTED]" if k in fields_set else walk(vv))
                for k, vv in v.items()
            }
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    return walk(value)


def _apply_transform(parsed, transform, expression):
    if not transform or transform == "none" or not expression:
        return parsed, False
    if transform == "jq":
        try:
            import jq  # type: ignore
            return jq.compile(expression).input(parsed).first(), False
        except ImportError:
            # jq not available — fall back to returning the parsed body
            # and signalling that the transform was skipped. The audit
            # log will reflect the skip; the LLM still gets data.
            return parsed, True
        except Exception:
            return parsed, True
    if transform == "jsonpath":
        try:
            from jsonpath_ng import parse as jp_parse  # type: ignore
            matches = [m.value for m in jp_parse(expression).find(parsed)]
            if len(matches) == 1:
                return matches[0], False
            return matches, False
        except ImportError:
            return parsed, True
        except Exception:
            return parsed, True
    return parsed, False


def _http_invoke(sys_token, definition, arguments, caller_user="", caller_org="", caller_bu=""):
    """Execute the declarative HTTP implementation. Returns the dict that
    becomes the /invoke response payload.

    When the outcome dict contains the key ``_customer_auth_used``
    (True/False), the caller MUST pop it before returning to the LLM
    and pass the value to the audit row — that's the internal signal
    saying "the IAM hook ran on this call".

    Similarly the outcome may carry ``_credential_model`` and
    ``_credential_ref_resolved`` for the audit row — pop them before
    returning to the LLM.
    """
    impl = definition.get("implementation") or {}
    method = (impl.get("method") or "GET").upper()
    tool_name = definition.get("name") or ""

    # 1. Render templates
    try:
        url = _render(impl.get("url") or "", arguments)
        query = _render(impl.get("query") or {}, arguments) or {}
        headers = _render(impl.get("headers") or {}, arguments) or {}
        body = impl.get("body")
        if body is not None:
            body = _render(body, arguments)
    except KeyError as ke:
        return {"ok": False, "error": "Missing required argument: %s" % ke.args[0]}

    # 2. Re-check allowed_hosts AFTER substitution (parameter-driven URLs)
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = impl.get("allowed_hosts") or []
    if host not in allowed:
        return {"ok": False, "error": "Host '%s' is not in allowed_hosts." % host}
    if not impl.get("allow_internal") and _is_internal_host(host):
        return {"ok": False, "error": "Host '%s' resolves to a private network." % host}

    # 3a. Static auth — resolved through the three-tier credential
    # model (spec §2). The hook layer below can also produce headers;
    # if both set the same key, the hook wins so it can refresh
    # expiring tokens without the admin having to flip auth.type.
    auth = impl.get("auth") or {}
    auth_type = auth.get("type") or "none"
    credential_model_used = ""
    credential_ref_resolved = ""
    if auth_type and auth_type != "none":
        credential_model_used = (auth.get("credential_model") or "global").lower()
        secret, credential_ref_resolved, struct_err = _resolve_credential_for_auth(
            sys_token,
            auth,
            ctx={"user": caller_user, "org": caller_org, "bu": caller_bu},
        )
        if struct_err is not None:
            # per_user with no credential — pass the structured error
            # straight through. The LLM sees error="no_user_credential"
            # and can prompt the user to connect.
            return dict(struct_err, **{
                "_customer_auth_used": False,
                "_credential_model": credential_model_used,
                "_credential_ref_resolved": credential_ref_resolved,
            })
        if not secret:
            return {
                "ok": False,
                "error": (
                    "credential_ref '%s' is missing or empty."
                    % (credential_ref_resolved or auth.get("credential_ref") or "")
                ),
                "_customer_auth_used": False,
                "_credential_model": credential_model_used,
                "_credential_ref_resolved": credential_ref_resolved,
            }
        # HTTP header values cannot contain newlines / control chars
        # (urllib3 raises InvalidHeader on b'Bearer ...\n'). Bearer
        # tokens or API keys stored via the admin form sometimes carry
        # a trailing newline — paste-in-form artifact, or
        # storage/passwords retaining the trailing LF copy-paste
        # added. Strip endpoints before forming any header. Only
        # stripping endpoints, never the middle, so PEM-shaped or
        # otherwise structured values are unaffected.
        secret_for_header = secret.strip() if secret else secret
        if auth_type == "bearer":
            headers.setdefault("Authorization", "Bearer %s" % secret_for_header)
        elif auth_type == "basic":
            import base64
            user_part = auth.get("username") or ""
            token = base64.b64encode(("%s:%s" % (user_part, secret_for_header)).encode("utf-8")).decode("ascii")
            headers.setdefault("Authorization", "Basic %s" % token)
        elif auth_type == "header":
            hname = auth.get("header_name") or "X-Api-Key"
            headers.setdefault(hname, secret_for_header)

    # 3b. Customer-auth hook (IAM gateway / SSO-fronted target). Runs
    # AFTER the static-auth block so its headers can override stale
    # static tokens. A hook failure is a hard refusal — we never fall
    # back to an unauthenticated upstream call.
    customer_auth_used = False
    if impl.get("customer_auth"):
        hook_ctx = {
            "target_kind": "tool",
            "tool_name": tool_name,
            "tool_target_url": url,
            "tool_target_host": host,
            "tool_method": method,
            "splunk_user": caller_user or "",
            # Tool flow does not currently forward the user's session
            # key — the dispatcher already authenticated the caller.
            # Hooks that need it can read it via splunk.rest.
            "splunk_session_key": "",
        }
        hook_headers, hook_err = _customer_auth.invoke(APP_DIR, hook_ctx)
        if hook_err:
            return {
                "ok": False,
                "error": "customer_auth hook failed: %s" % hook_err,
                "_customer_auth_used": False,
            }
        # Hook headers override static ones (intentional — see comment
        # above the static block).
        for hk, hv in (hook_headers or {}).items():
            headers[hk] = hv
        customer_auth_used = True

    # 4. Append query string
    if query:
        sep = "&" if "?" in url else "?"
        url = url + sep + urlencode(query)

    # 5. Build body
    data = None
    if method in ("POST", "PUT", "PATCH"):
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            data = body.encode("utf-8")

    # 6. Make the request via the shared client (proxy + CA aware).
    timeout = float(impl.get("timeout_seconds") or DEFAULT_TIMEOUT_S)
    try:
        from itmip_llm_http_client import build_request, HTTPError, URLError
    except Exception as exc:
        return {"ok": False, "error": "shared HTTP client unavailable: %s" % exc}

    # Resolve per-tool proxy + CA. Spec §5.
    proxy_url = (impl.get("proxy_url") or "").strip() or None
    proxy_cred_ref = (impl.get("proxy_credential_ref") or "").strip()
    proxy_credential = _resolve_secret(sys_token, proxy_cred_ref) if proxy_cred_ref else None
    tls_ca_ref = (impl.get("tls_ca_pem_ref") or "").strip()
    ca_pem = _resolve_secret(sys_token, tls_ca_ref) if tls_ca_ref else None
    # v0.9.5 — dev-mode TLS-skip. Refused on Splunk Cloud (compliance
    # posture) regardless of what's in the stored impl JSON. The flag
    # may sit in KVStore but takes no effect; an INFO line goes to
    # splunkd.log so admins see why.
    skip_verify = bool(impl.get("tls_skip_verify"))
    if skip_verify:
        try:
            from itmip_llm_guid import is_splunk_cloud as _is_cloud
            if _is_cloud(sys_token):
                sys.stderr.write(
                    "itmip_llm_custom_tools: refusing tls_skip_verify on Splunk "
                    "Cloud for tool '%s' — flag ignored, TLS verification stays on.\n"
                    % (definition.get("name") or "?")
                )
                skip_verify = False
        except Exception:
            # Fail-safe: if Cloud detection fails, refuse the flag.
            skip_verify = False
    if skip_verify:
        sys.stderr.write(
            "itmip_llm_custom_tools: tls_verify_skipped=true url=%s tool=%s "
            "user=%s — dev-mode TLS skip is active.\n"
            % (url, definition.get("name") or "?", caller_user or "?")
        )

    req, opener = build_request(
        url, method, headers, body_bytes=data,
        proxy_url=proxy_url, proxy_credential=proxy_credential, ca_pem=ca_pem,
        skip_verify=skip_verify,
    )
    http_status = 0
    raw = b""
    try:
        with opener.open(req, timeout=timeout) as resp:
            http_status = getattr(resp, "status", 0) or resp.getcode()
            raw = resp.read(HARD_MAX_BYTES + 1)
    except HTTPError as he:
        http_status = he.code
        try:
            raw = he.read()
        except Exception:
            raw = b""
    except URLError as ue:
        return {"ok": False, "error": "Network error: %s" % ue}
    except Exception as exc:
        return {"ok": False, "error": "Request failed: %s" % exc}

    truncated = len(raw) > HARD_MAX_BYTES
    if truncated:
        raw = raw[:HARD_MAX_BYTES]

    # 7. Parse JSON if requested or content-type hints at it
    expect_json = impl.get("expect_json", True)
    parsed_body = None
    text_body = ""
    try:
        text_body = raw.decode("utf-8", errors="replace")
    except Exception:
        text_body = ""
    if expect_json:
        try:
            parsed_body = json.loads(text_body)
        except Exception:
            parsed_body = None
    payload = parsed_body if parsed_body is not None else text_body

    # 8. Transform
    response_cfg = definition.get("response") or {}
    transform = response_cfg.get("transform")
    expression = response_cfg.get("expression")
    transformed, transform_skipped = _apply_transform(payload, transform, expression)

    # 9. Redact
    guard = definition.get("guardrails") or {}
    transformed = _apply_redact(transformed, guard.get("redact_fields"))

    # 10. Enforce max_bytes (post-transform)
    max_bytes = int(response_cfg.get("max_bytes") or DEFAULT_MAX_BYTES)
    max_bytes = min(max_bytes, HARD_MAX_BYTES)
    serialized = transformed if isinstance(transformed, str) else json.dumps(transformed, default=str)
    final_truncated = False
    if len(serialized) > max_bytes:
        serialized = serialized[:max_bytes]
        final_truncated = True

    return {
        "ok": http_status < 400,
        "result": serialized,
        "http_status": http_status,
        "truncated": truncated or final_truncated,
        "transform_skipped": transform_skipped,
        "_customer_auth_used": customer_auth_used,
        "_credential_model": credential_model_used,
        "_credential_ref_resolved": credential_ref_resolved,
        "_tls_verify_skipped": skip_verify,
    }


# ─────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────

def _cache_get(key):
    entry = _cache.get(key)
    if not entry:
        return None
    expires, payload = entry
    if expires < time.time():
        _cache.pop(key, None)
        return None
    return payload


def _cache_put(key, ttl, payload):
    if ttl <= 0:
        return
    _cache[key] = (time.time() + ttl, payload)


# ─────────────────────────────────────────────────────────────────────
# Operation dispatcher
# ─────────────────────────────────────────────────────────────────────

def _parse_query(args):
    qs = args.get("query") or []
    if isinstance(qs, list):
        return dict(qs)
    return dict(qs.items()) if hasattr(qs, "items") else {}


def _operation_for(args):
    """Pick which sub-resource the call is for. The dispatcher accepts:
      - explicit `op` field in the JSON payload (preferred for POST)
      - URL tail (/definitions or /invoke)
      - default = definitions (list).
    """
    payload_raw = args.get("payload") or "{}"
    try:
        payload = json.loads(payload_raw) if payload_raw else {}
    except Exception:
        payload = {}
    if isinstance(payload, dict) and payload.get("op"):
        return payload.get("op"), payload

    path = (args.get("path_info") or args.get("path") or "") or ""
    if "/invoke" in path:
        return "invoke", payload
    return "definitions", payload


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

            op, payload = _operation_for(args)
            query = _parse_query(args)
            user = user_name(args)

            # v1.4.1 — custom HTTP tools are an Enterprise feature (per-feature
            # licensing). Listing (GET) stays open so the UI renders the greyed
            # state; authoring (POST) and execution (/invoke) are refused
            # server-side below Enterprise (authoritative — a direct REST call
            # cannot bypass it). Spec: instructions/FEATURE_LICENSING_SPEC.md
            ct_active = (op == "invoke") or (op == "definitions" and method == "POST")
            if ct_active and not capability_enabled(sys_token, "custom_http_tools"):
                return err(
                    403, "Custom HTTP tools require an Enterprise license."
                )

            if op == "definitions":
                return self._handle_definitions(args, method, payload, query, sys_token, user)
            if op == "invoke":
                return self._handle_invoke(args, method, payload, sys_token, user)
            return err(400, "Unknown op '%s'." % op)
        except Exception as exc:
            sys.stderr.write(
                "itmip_llm_custom_tools error: %s\n%s\n"
                % (exc, traceback.format_exc())
            )
            return err(500, "Internal error: %s" % exc)

    # ────────────────────────────────────────────────────────────────
    # /definitions
    # ────────────────────────────────────────────────────────────────
    def _handle_definitions(self, args, method, payload, query, sys_token, user):
        if method == "GET":
            try:
                rows = _list_rows(sys_token)
            except Exception as exc:
                return err(502, "Could not list custom tools: %s" % exc)
            admin = is_admin(args, rest)
            caller_org = (query.get("org") or payload.get("org") or "").upper()
            caller_bu = (query.get("bu") or payload.get("bu") or "").upper()
            visible = [r for r in rows if _doc_visible_to(r, caller_org, caller_bu, admin)]
            decoded = [_decode_row(r) for r in visible if r]
            # Spec §2.4 — per-tenant tools without a stored credential for
            # the caller's (Org, BU) are dropped from the advertised list
            # rather than failing at invoke. Per-user tools stay visible
            # so the LLM can ask the user to connect. Global tools are
            # never dropped here (config-time failure if their credential
            # is missing).
            ctx = {"user": user, "org": caller_org, "bu": caller_bu}
            filtered = []
            for d in decoded:
                if not d:
                    continue
                auth = ((d.get("implementation") or {}).get("auth")) or {}
                model = (auth.get("credential_model") or "global").lower()
                if model == "per_tenant" and (auth.get("type") or "none") != "none":
                    secret, _resolved, struct_err = _resolve_credential_for_auth(sys_token, auth, ctx)
                    if not secret and struct_err is None:
                        # No credential for this (Org, BU) — silently drop.
                        continue
                filtered.append(d)
            return ok({"items": filtered})

        if method == "POST":
            if not is_admin(args, rest):
                return err(403, "Only Splunk admins can author custom tools.")
            doc = payload.get("definition") or payload
            # Strip envelope fields the validator doesn't expect.
            doc = {k: v for k, v in doc.items() if k != "op"}
            err_msg = _validate_definition(doc)
            if err_msg:
                return err(400, err_msg)
            row = _encode_doc(doc, user)
            key = doc.get("_key") or None
            # Enforce unique tool name. If the row exists with a different
            # key, refuse — admin should DELETE the old one explicitly.
            existing = _find_row_by_name(sys_token, doc.get("name") or "")
            if existing and (not key or existing.get("_key") != key):
                return err(409, "A tool named '%s' already exists." % doc.get("name"))
            try:
                if key:
                    _upsert_row(sys_token, row, key=key)
                    emit_change(
                        sys_token, COLLECTION, op="update", key=key,
                        before=None, after=row, user=user,
                    )
                    return ok({"ok": True, "_key": key})
                new_key = _upsert_row(sys_token, row)
                emit_change(
                    sys_token, COLLECTION, op="create", key=new_key,
                    before=None, after=row, user=user,
                )
                return ok({"ok": True, "_key": new_key})
            except Exception as exc:
                return err(502, "Could not save custom tool: %s" % exc)

        if method == "DELETE":
            if not is_admin(args, rest):
                return err(403, "Only Splunk admins can delete custom tools.")
            key = query.get("key") or payload.get("_key") or ""
            if not key:
                return err(400, "'key' is required.")
            try:
                _delete_row(sys_token, key)
                emit_change(
                    sys_token, COLLECTION, op="delete", key=key,
                    before=None, after=None, user=user_name(args),
                )
                return ok({"ok": True, "_key": key})
            except Exception as exc:
                return err(502, "Could not delete custom tool: %s" % exc)

        return err(405, "Only GET/POST/DELETE supported on /definitions.")

    # ────────────────────────────────────────────────────────────────
    # /invoke
    # ────────────────────────────────────────────────────────────────
    def _handle_invoke(self, args, method, payload, sys_token, user):
        if method != "POST":
            return err(405, "Only POST is supported on /invoke.")
        name = payload.get("name") or ""
        arguments = payload.get("arguments") or {}
        if not name:
            return err(400, "'name' is required.")
        if not isinstance(arguments, dict):
            return err(400, "'arguments' must be an object.")

        caller_org = (payload.get("org") or "").upper()
        caller_bu = (payload.get("bu") or "").upper()
        admin = is_admin(args, rest)

        row = _find_row_by_name(sys_token, name)
        if not row:
            return err(404, "Tool '%s' not found." % name)
        if not _doc_visible_to(row, caller_org, caller_bu, admin):
            return err(403, "Tool '%s' is not in scope for this user." % name)
        if not row.get("enabled", True):
            return err(403, "Tool '%s' is disabled." % name)

        definition = _decode_row(row)
        impl = definition.get("implementation") or {}
        itype = impl.get("type")
        if itype not in SUPPORTED_IMPL_TYPES:
            return err(501, "implementation.type '%s' is not supported yet." % itype)

        guard = definition.get("guardrails") or {}
        cap = int(guard.get("rate_limit_per_minute") or DEFAULT_RATE_LIMIT)
        if not rate_limit_check("custom_tool:%s" % name, user, cap):
            return err(429, "Rate limit exceeded for tool '%s'." % name)

        args_hash = hashlib.sha256(
            json.dumps(arguments, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        # v0.7.0 — cache key is scoped per credential_model (spec §2.2).
        # global: (tool, args). per_tenant: (tool, org, bu, args).
        # per_user: (tool, user, args) — and per-user defaults to
        # cache_ttl=0 unless the admin opted in explicitly, since per-
        # user data collisions on argument hash would otherwise serve
        # one user's results to another.
        impl = definition.get("implementation") or {}
        auth = impl.get("auth") or {}
        credential_model = (auth.get("credential_model") or "global").lower()
        if credential_model == "per_user":
            cache_key = (name, user, args_hash)
        elif credential_model == "per_tenant":
            cache_key = (name, caller_org, caller_bu, args_hash)
        else:
            cache_key = (name, args_hash)
        ttl = int(guard.get("cache_ttl_seconds") or 0)
        cached = _cache_get(cache_key) if ttl > 0 else None
        started = time.time()
        if cached is not None:
            result = dict(cached)
            result["cached"] = True
            # Cache hits don't re-run the IAM hook by design — the
            # cached response is what the gateway-authorised call
            # returned. customer_auth_used=False distinguishes
            # cached responses from fresh gateway calls in the audit
            # log.
            audit_cred_model = result.pop("_credential_model", credential_model)
            audit_cred_ref = result.pop("_credential_ref_resolved", "")
            audit_tls_skipped = bool(result.pop("_tls_verify_skipped", False))
            result.pop("_customer_auth_used", None)
            self._record_audit(
                sys_token, name, user, caller_org, caller_bu,
                args_hash, "ok", "",
                int((time.time() - started) * 1000),
                True, False,
                credential_model=audit_cred_model,
                credential_ref_resolved=audit_cred_ref,
                tls_verify_skipped=audit_tls_skipped,
            )
            return ok(result)

        outcome = _http_invoke(
            sys_token, definition, arguments,
            caller_user=user, caller_org=caller_org, caller_bu=caller_bu,
        )
        # Pop the internal audit signals before the outcome reaches
        # the LLM. Tools that didn't hit the hook (most of them) won't
        # have the key.
        customer_auth_used = bool(outcome.pop("_customer_auth_used", False))
        audit_cred_model = outcome.pop("_credential_model", credential_model)
        audit_cred_ref = outcome.pop("_credential_ref_resolved", "")
        audit_tls_skipped = bool(outcome.pop("_tls_verify_skipped", False))
        outcome["cached"] = False
        if outcome.get("ok") and ttl > 0:
            _cache_put(cache_key, ttl, outcome)
        status_label = "ok" if outcome.get("ok") else "error"
        self._record_audit(
            sys_token, name, user, caller_org, caller_bu,
            args_hash, status_label, str(outcome.get("error") or "")[:200],
            int((time.time() - started) * 1000), False, customer_auth_used,
            credential_model=audit_cred_model,
            credential_ref_resolved=audit_cred_ref,
            tls_verify_skipped=audit_tls_skipped,
        )
        return ok(outcome)

    def _record_audit(self, sys_token, name, user, org, bu, args_hash,
                      status_label, error_text, duration_ms, cached,
                      customer_auth_used=False,
                      credential_model="", credential_ref_resolved="",
                      tool_kind="http_custom",
                      mcp_server_id="", mcp_upstream_name="",
                      tls_verify_skipped=False):
        """Spec §2.5 + §4.12 — audit row also captures which credential
        model + resolved name was used (so admins can reconstruct
        identity per call) and which kind of tool ran (built-in, custom
        HTTP, or MCP-imported). v0.9.5 — `tls_verify_skipped` records
        when the dev-mode TLS-skip toggle was active for the call so
        ops can flag any row that shouldn't have used it."""
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
            "tool_kind": tool_kind,
            "mcp_server_id": mcp_server_id,
            "mcp_upstream_name": mcp_upstream_name,
            "created_at": int(time.time() * 1000),
        })

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
