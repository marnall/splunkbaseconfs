"""POST /services/itmip_llm/proxy — Splunk-server-side LLM proxy.

When an LLM configuration is set to call_mode=splunk_proxy, the browser
posts here instead of going to the provider directly. The Splunk server
forwards the request to the configured endpoint (resolving the API key
from storage/passwords by config name) and returns the provider's response
verbatim. This unblocks providers without browser CORS (OpenAI, Bedrock,
AzureOpenAI, Groq, Gemini) and lets sensitive keys stay server-side.

Request body (JSON):
  llm_config_id : string  -- KVStore _key of an itmip_llm_configs entry
                              (server reads endpoint/model/proxy from it)
  provider_kind : string  -- "openai" | "anthropic" | "azure_openai" | ...
  body          : object  -- provider-specific request body, verbatim
  extra_headers : object  -- optional headers to add (e.g. for Azure / OpenRouter)

Response (JSON): { status, headers, body }  where body is the provider's
response decoded as JSON if possible, otherwise the raw text.

This proxy uses Python's urllib so we don't need any third-party HTTP
library on the Splunk host. A configured server proxy is honoured.
"""

import json
import os
import ssl
import sys
from urllib import request as urllib_request
from urllib import error as urllib_error

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import (  # noqa: E402
    APP_NAME,
    LEGACY_PASSWORD_NAME,
    LEGACY_PASSWORD_REALM,
    LLM_PASSWORD_REALM,
    err,
    is_user_allowed_for_llm_config,
    ok,
    rate_limit_check,
    resolve_caller_tenant,
    system_token,
    user_name,
    user_roles,
    user_token,
)
from itmip_llm_audit import emit_audit, resolve_audit_cfg  # noqa: E402
from itmip_llm_license import capability_enabled  # noqa: E402
import _customer_auth  # noqa: E402  — shared with itmip_llm_custom_tools.py

BOOTSTRAP_CONFIG_KEY = "DFLT_DFLT_anthropic_central"
BOOTSTRAP_CONFIG = {
    "_key": BOOTSTRAP_CONFIG_KEY,
    "name": BOOTSTRAP_CONFIG_KEY,
    "provider_kind": "anthropic",
    "scope": "central",
    "org_short": "DFLT",
    "bu_short": "DFLT",
    "endpoint": "https://api.anthropic.com/v1/messages",
    "model": "claude-sonnet-4-6",
    "request_timeout_ms": 200000,
    "call_mode": "splunk_proxy",
}

def _invoke_customer_auth_hook(cfg, args, raw_body):
    """Build the LLM-flavoured context and call the shared hook.

    Returns ({headers}, None) on success, ({}, error_str) on failure.
    The proxy turns error_str into a 502 with a clean message.
    Hook resolution / validation lives in _customer_auth; this just
    assembles the LLM-side context.
    """
    try:
        preview = raw_body if isinstance(raw_body, str) else (raw_body or b"").decode(
            "utf-8", errors="replace"
        )
    except Exception:
        preview = ""
    context = {
        "target_kind": "llm",
        "llm_config": cfg or {},
        "splunk_session_key": user_token(args) or "",
        "splunk_user": user_name(args) or "",
        "body_preview": preview[:256],
    }
    return _customer_auth.invoke(APP_DIR, context)


def _load_llm_config(sys_token, config_key):
    """Look up an itmip_llm_configs record by _key. Returns dict or None.

    Falls back to the synthetic bootstrap Anthropic config when the
    caller asked for DFLT_DFLT_anthropic_central and KVStore has no
    record (typical on fresh installs that haven't run the Promote /
    Edit migration yet).
    """
    safe = "".join(c for c in (config_key or "") if c.isalnum() or c in "._-")
    if not safe:
        return None
    url = (
        "/servicesNS/nobody/{app}/storage/collections/data/itmip_llm_configs/{key}"
        "?output_mode=json"
    ).format(app=APP_NAME, key=safe)
    try:
        resp, content = rest.simpleRequest(url, sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) == 200:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    if safe == BOOTSTRAP_CONFIG_KEY:
        return dict(BOOTSTRAP_CONFIG)
    return None


def _load_secret(sys_token, name):
    safe = "".join(c for c in (name or "") if c.isalnum() or c in "._-")
    if not safe:
        return None
    entry_path = (
        "/servicesNS/nobody/{app}/storage/passwords/"
        "{realm}%3A{name}%3A?output_mode=json"
    ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=safe)
    try:
        resp, content = rest.simpleRequest(entry_path, sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) == 200:
            data = json.loads(content)
            entries = data.get("entry") or []
            if entries:
                clear = (entries[0].get("content") or {}).get("clear_password") or None
                if clear:
                    return clear
    except Exception:
        pass
    # Fallback for the bootstrap config: try the v0.1 single-key path
    # (realm=LEGACY_PASSWORD_REALM, name=LEGACY_PASSWORD_NAME). This is
    # what makes splunk_proxy mode work for the built-in
    # DFLT_DFLT_anthropic_central config without requiring an admin to
    # promote it first.
    if safe == BOOTSTRAP_CONFIG_KEY:
        legacy_path = (
            "/servicesNS/nobody/{app}/storage/passwords/"
            "{realm}%3A{name}%3A?output_mode=json"
        ).format(
            app=APP_NAME,
            realm=LEGACY_PASSWORD_REALM,
            name=LEGACY_PASSWORD_NAME,
        )
        try:
            resp, content = rest.simpleRequest(
                legacy_path, sessionKey=sys_token, method="GET"
            )
            if getattr(resp, "status", 0) == 200:
                data = json.loads(content)
                entries = data.get("entry") or []
                if entries:
                    return (entries[0].get("content") or {}).get("clear_password") or None
        except Exception:
            pass
    return None


def _build_ssl_context(ca_pem, skip_verify=False):
    """Return an SSL context that trusts the system CAs PLUS the given
    PEM-encoded bundle. If `ca_pem` is empty/None and `skip_verify` is
    False, returns None so the default context is used.

    When `skip_verify` is True (dev-mode escape hatch, gated in the UI
    behind a red warning and refused on Splunk Cloud), the returned
    context has hostname checking and cert verification disabled.
    Mirrors the shared `itmip_llm_http_client.build_ssl_context`
    contract."""
    if not ca_pem and not skip_verify:
        return None
    ctx = ssl.create_default_context()
    if ca_pem:
        try:
            ctx.load_verify_locations(cadata=ca_pem)
        except Exception:
            # If the PEM is malformed, surface the failure as a normal SSL
            # error during the request rather than crashing the handler.
            pass
    if skip_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _build_request(endpoint, method, headers, body_obj, proxy_url,
                   ca_pem=None, skip_verify=False):
    body_bytes = None
    if body_obj is not None:
        body_bytes = json.dumps(body_obj).encode("utf-8")
    req = urllib_request.Request(endpoint, data=body_bytes, method=method)
    for k, v in (headers or {}).items():
        if v is not None:
            req.add_header(str(k), str(v))
    handlers = []
    if proxy_url:
        handlers.append(urllib_request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
    ssl_ctx = _build_ssl_context(ca_pem, skip_verify=skip_verify)
    if ssl_ctx is not None:
        handlers.append(urllib_request.HTTPSHandler(context=ssl_ctx))
    opener = urllib_request.build_opener(*handlers) if handlers else urllib_request.build_opener()
    return req, opener


try:
    from itmip_llm_guid import is_splunk_cloud as _is_splunk_cloud  # noqa: E402
except Exception:  # pragma: no cover
    def _is_splunk_cloud(_sys_token):
        # Fail-safe: assume Cloud, refuse the flag. Better to leave an
        # admin stuck than silently disable TLS in prod.
        return True


def _provider_headers(provider_kind, api_key, extra):
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    pk = (provider_kind or "").lower()
    if pk == "anthropic":
        if api_key:
            h["x-api-key"] = api_key
        h["anthropic-version"] = "2023-06-01"
    elif pk in ("openai", "groq", "openrouter", "azure_openai"):
        if api_key:
            if pk == "azure_openai":
                h["api-key"] = api_key
            else:
                h["Authorization"] = "Bearer " + api_key
    elif pk == "gemini":
        # Gemini uses ?key=... in URL; no header needed.
        pass
    elif pk == "bedrock":
        # Bedrock requires AWS SigV4 — out of scope for this proxy in v0.2.
        # Honour an explicit Authorization header passed in extra_headers.
        pass
    elif pk == "ollama":
        # Local; no auth by default.
        pass
    for k, v in (extra or {}).items():
        h[str(k)] = str(v)
    return h


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "POST").upper()
            if method != "POST":
                return err(405, "Only POST is supported.")
            if not user_token(args):
                return err(401, "Not authenticated.")

            sys_token = system_token(args) or user_token(args)

            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw)
            except Exception:
                return err(400, "Invalid JSON payload.")

            config_id = payload.get("llm_config_id") or ""
            provider_kind = (payload.get("provider_kind") or "").lower()
            body = payload.get("body")
            caller_extras = payload.get("extra_headers") or {}

            if not provider_kind:
                return err(400, "'provider_kind' is required.")

            # SECURITY: never trust a caller-supplied endpoint. The proxy
            # loads the central API key with the system token, so a
            # caller-chosen endpoint would let any authenticated user
            # exfiltrate the key to attacker-controlled hosts. The
            # endpoint MUST come from the LlmConfig record in KVStore.
            if not config_id:
                return err(400, "'llm_config_id' is required.")
            cfg = _load_llm_config(sys_token, config_id)
            if not cfg:
                return err(404, "LLM config not found: %s" % config_id)
            endpoint = cfg.get("endpoint") or ""
            if not endpoint:
                return err(400, "LLM config has no endpoint stored.")

            # SECURITY: a non-admin user shouldn't be able to call ANY
            # LLM config — only configs explicitly granted to them.
            # Otherwise a non-admin could burn admin-owned API budget by
            # spamming the central key via the proxy. The DFLT/DFLT
            # central config remains open to everyone (rule 2 in the
            # helper).
            if not is_user_allowed_for_llm_config(args, rest, cfg):
                return err(
                    403,
                    "You aren't authorised to invoke this LLM configuration.",
                )

            # Defensive rate-limit on the proxy so a runaway loop can't
            # exhaust paid API budget. 30 calls/minute per user is well
            # above any legitimate conversation rate.
            if not rate_limit_check("proxy", user_name(args), 30):
                return err(429, "Too many proxy calls; slow down.")

            # v1.3.0 — single-user free-tier gate (server-side). A no-license
            # (personal) install binds to its first user; everyone else is
            # blocked from the central-key LLM path until a license is added.
            # Admins are NOT exempt — "never more than one user" is the point.
            try:
                from itmip_llm_license import free_tier_status
                _fts = free_tier_status(sys_token, user_name(args))
                if _fts.get("locked"):
                    return err(
                        403,
                        "AiWorkbench is in single-user (free) mode and is "
                        "licensed to '%s'. Add a license (License tab) to "
                        "enable more users." % (_fts.get("owner") or "another user"),
                    )
            except Exception as _ftexc:
                sys.stderr.write("itmip_llm_proxy: free-tier check failed: %s\n" % _ftexc)

            # Pin the host of the outbound call to the host of the
            # configured endpoint (defence in depth — even if a future
            # change re-introduces an override path). Azure OpenAI rewrites
            # the path but keeps the host, so this still works for it.
            stored_host = ""
            try:
                from urllib.parse import urlparse
                stored_host = urlparse(endpoint).netloc.lower()
            except Exception:
                pass

            # SECURITY: only allow specific extra header names. Customer
            # gateway tokens are configured at admin-write time in the
            # KVStore config (`cfg.extra_headers`) and merged below.
            # Callers can only contribute a small known-safe set so a
            # poisoned LLM prompt can't smuggle arbitrary auth headers.
            ALLOWED_CALLER_HEADERS = {
                "x-request-id",
                "x-amzn-bedrock-authorization",
                "x-correlation-id",
            }
            extra_headers = {}
            if isinstance(caller_extras, dict):
                for k, v in caller_extras.items():
                    if isinstance(k, str) and k.lower() in ALLOWED_CALLER_HEADERS:
                        extra_headers[k] = v

            # For Bedrock the proxy is a passthrough — we don't sign here.
            # The browser must supply a pre-signed Authorization header in
            # extra_headers, or use call_mode=browser_direct via the AWS SDK.
            api_key = None
            if provider_kind != "bedrock":
                api_key = _load_secret(sys_token, config_id)

            # For Gemini, append the API key as ?key= if not already present.
            if provider_kind == "gemini" and api_key and "key=" not in endpoint:
                sep = "&" if "?" in endpoint else "?"
                endpoint = endpoint + sep + "key=" + api_key

            # Merge in the LLM config's stored extra_headers (e.g. a customer-
            # internal gateway token) on top of any extras the caller supplied.
            merged_extras = {}
            if cfg and isinstance(cfg.get("extra_headers"), dict):
                merged_extras.update(cfg["extra_headers"])
            if isinstance(extra_headers, dict):
                merged_extras.update(extra_headers)

            # Customer auth hook: dynamic, per-request headers for LLMs
            # behind a corporate IAM gateway (WebEAM.Next, Ping, Okta).
            # Runs only when admin opted-in on this config; the hook wins
            # over the static merges above so it can refresh expiring
            # tokens. A hook failure is a hard 502 — admin needs to know.
            if cfg and cfg.get("customer_auth_enabled"):
                # v1.4.1 — the IAM gateway hook is an Enterprise feature
                # (per-feature licensing). Refuse to run a configured hook
                # below the cap so a downgraded install can't keep minting
                # gateway headers. Fail-closed.
                # Spec: instructions/FEATURE_LICENSING_SPEC.md
                if not capability_enabled(sys_token, "iam_gateway_hook"):
                    return err(
                        403, "The customer IAM gateway hook requires an "
                        "Enterprise license."
                    )
                hook_headers, hook_err = _invoke_customer_auth_hook(
                    cfg, args, body
                )
                if hook_err:
                    return err(502, hook_err)
                merged_extras.update(hook_headers)

            headers = _provider_headers(provider_kind, api_key, merged_extras)

            proxy_url = ""
            if cfg:
                sp = cfg.get("server_proxy") or {}
                if isinstance(sp, dict) and sp.get("proxy_url"):
                    proxy_url = sp["proxy_url"]

            ca_pem = ""
            if cfg and isinstance(cfg.get("tls_ca_pem"), str):
                ca_pem = cfg["tls_ca_pem"]

            # v0.9.5 — dev-mode TLS-skip toggle. Refused on Splunk Cloud
            # (compliance posture) regardless of what's stored in KVStore.
            # On Enterprise (single SH, single-site SHC, multi-site SHC),
            # honour the flag and emit a splunkd.log warning so ops have
            # visibility into every call that ran without TLS verification.
            skip_verify = bool(cfg and cfg.get("tls_skip_verify"))
            if skip_verify and _is_splunk_cloud(sys_token):
                sys.stderr.write(
                    "itmip_llm_proxy: refusing tls_skip_verify on Splunk Cloud "
                    "for config '%s' — flag ignored, TLS verification stays on.\n"
                    % config_id
                )
                skip_verify = False
            if skip_verify:
                sys.stderr.write(
                    "itmip_llm_proxy: tls_verify_skipped=true endpoint=%s "
                    "config=%s user=%s — dev-mode TLS skip is active.\n"
                    % (endpoint, config_id, user_name(args))
                )

            # ── v1.3.0 — Real audit logging (bypass-proof) ─────────────
            # Record this server-side provider call BEFORE making it, so the
            # disclosure is auditable however the proxy was reached (UI, curl,
            # script). Under an Org in `enforce` mode this is FAIL-CLOSED — a
            # failed audit write means the provider is NOT called. The rich
            # turn-level llm_request (user input, template, consent) is emitted
            # by the browser; this per-round-trip record guarantees no provider
            # call escapes the audit. See REAL_AUDIT_LOGGING_SPEC.md §10.1.
            # v1.4.1 — audit logging is now an ENTERPRISE capability (per-feature
            # licensing). Below the tier we force an EMPTY audit config so the
            # per-call audit neither writes nor enforces — a stale audit_index
            # left over from a pre-1.4.1 Professional install must not keep
            # logging or fail-close LLM calls. (Truthy-but-index-less so
            # emit_audit no-ops instead of re-resolving the real config.)
            _audit_cap = capability_enabled(sys_token, "audit_logging")
            try:
                _roles = user_roles(args, rest)
                # Resolve the tenant against the HOST app the caller is in (sent
                # by the browser as `splunk_app`). WITHOUT this, resolution
                # defaults to the assistant app's own name, which an Org's
                # app_patterns don't match → the turn falls through to DFLT (no
                # audit index) and the proxy audit is silently dropped. This is
                # the same app context the browser audit pre-flight passes.
                _host_app = (payload.get("splunk_app") or "").strip() or None
                _tenant = resolve_caller_tenant(
                    args, rest, sys_token, url_app=_host_app, roles=_roles
                )
                _org = _tenant.get("org_short") or "DFLT"
                _bu = _tenant.get("bu_short") or "DFLT"
                _acfg = (resolve_audit_cfg(sys_token, _org) if _audit_cap
                         else {"audit_index": "", "audit_enforcement": "best_effort"})
            except Exception as _texc:
                sys.stderr.write("itmip_llm_proxy: audit tenant resolve failed: %s\n" % _texc)
                _org, _bu, _acfg = "DFLT", "DFLT", {"audit_enforcement": "best_effort"}
            _enforce = _acfg.get("audit_enforcement") == "enforce"
            _audit_in = payload.get("audit") if isinstance(payload.get("audit"), dict) else {}
            try:
                _ares = emit_audit(
                    sys_token, _org, _bu, user_name(args), _roles,
                    "proxy_provider_call",
                    {
                        "request_id": _audit_in.get("request_id") or None,
                        "session_id": str(_audit_in.get("session_id") or "")[:128],
                        "transport": "splunk_proxy",
                        "provider_kind": provider_kind,
                        "model": str((cfg or {}).get("model") or "")[:96],
                        "llm_config_key": config_id,
                        "llm_config_name": str((cfg or {}).get("name") or "")[:128],
                        "endpoint_host": stored_host,
                    },
                    audit_cfg=_acfg,
                    # Verified fallback writer for internal (`_*`) audit indexes:
                    # a system-token `| collect` mis-routes them, so emit_audit
                    # re-tries under the user token when the system write does
                    # not verify (see bin/itmip_llm_audit.py _collect_oneshot).
                    user_token=user_token(args),
                )
            except Exception as _aexc:
                sys.stderr.write("itmip_llm_proxy: audit emit failed: %s\n" % _aexc)
                _ares = {"logged": False, "reason": str(_aexc)}
            if _enforce and not _ares.get("logged"):
                return err(
                    503,
                    "Audit logging is required for your Org and is currently "
                    "unavailable, so the request was not sent. Contact your "
                    "administrator. (%s)" % (_ares.get("reason") or "no audit_index"),
                )

            req, opener = _build_request(
                endpoint, "POST", headers, body, proxy_url,
                ca_pem=ca_pem, skip_verify=skip_verify,
            )

            timeout_ms = int((cfg or {}).get("request_timeout_ms") or 200000)
            try:
                resp = opener.open(req, timeout=timeout_ms / 1000.0)
                status_code = resp.getcode()
                raw = resp.read()
                resp_headers = dict(resp.headers.items()) if hasattr(resp, "headers") else {}
            except urllib_error.HTTPError as e:
                status_code = e.code
                raw = e.read() if hasattr(e, "read") else b""
                resp_headers = dict(e.headers.items()) if getattr(e, "headers", None) else {}
            except Exception as exc:
                return err(502, "Provider call failed: %s" % exc)

            try:
                body_out = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                body_out = {"raw": raw.decode("utf-8", errors="replace")}

            return ok(
                {
                    "status": status_code,
                    "headers": resp_headers,
                    "body": body_out,
                    "user": user_name(args),
                }
            )
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
