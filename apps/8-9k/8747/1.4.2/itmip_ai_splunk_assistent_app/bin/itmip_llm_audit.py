"""POST /services/itmip_llm/audit — real audit logging (v1.3.0).

Writes structured audit events to each Org's operator-provisioned audit
index via /services/receivers/simple, using the system token
(passSystemAuth=true) so a user can be made to write to an index they
cannot read and cannot suppress their own audit.

This HTTP surface handles the events the BROWSER produces:
  - llm_request        (browser_direct best_effort pre-flight)
  - llm_response       (browser_direct completion)
  - consent_acceptance (the SECURITY CONFIRMATION accept, both transports)

splunk_proxy turns are audited SERVER-SIDE by bin/itmip_llm_proxy.py, which
imports emit_audit()/render_content()/resolve_audit_cfg() from here directly
(bypass-proof — see REAL_AUDIT_LOGGING_SPEC.md §10.1). governance_change /
audit_config events are emitted server-side by the relevant handlers, not
through this endpoint.

Design of record: instructions/REAL_AUDIT_LOGGING_SPEC.md (rev 5).
"""

import hashlib
import json
import os
import re
import socket
import sys
import time
import uuid

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import (  # noqa: E402
    err,
    kv_list,
    ok,
    rate_limit_check,
    resolve_caller_tenant,
    system_token,
    user_name,
    user_roles,
    user_token,
)

# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────
AUDIT_SCHEMA_VERSION = 1
AUDIT_SOURCETYPE = "itmip:ai:audit"
AUDIT_SOURCE = "ai_workbench_audit"
ORG_COLLECTION = "itmip_organisations"

# §7.3.1 — byte-pinned body caps (UTF-8 bytes, measured before envelope).
MAX_BODY_BYTES = 1048576           # 1 MiB per body
TOTAL_EVENT_CEILING_BYTES = 3145728  # ~3 MiB body+envelope guard

VALID_CONTENT_MODES = (
    "metadata_only", "prompt_hash", "truncated_prompt", "full_prompt",
)
DEFAULT_CONTENT_MODE = "metadata_only"  # safest fallback if an Org is mis-set
TRUNCATED_PREVIEW_CHARS = 200

# Event types the BROWSER may submit through this HTTP endpoint.
CLIENT_EVENT_TYPES = ("llm_request", "llm_response", "consent_acceptance")

# §7.5 — secret redaction denylist for governance_change before/after rows.
_REDACT_EXACT = {"aws_access_key_id", "tls_ca_pem", "clear_password", "password"}
_REDACT_RE = re.compile(
    r"(secret|token|password|api_key|apikey|credential|_pem|private_key)",
    re.IGNORECASE,
)
_REDACTED = "***"


# ─────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────
def _app_version():
    path = os.path.join(os.path.dirname(APP_BIN), "default", "app.conf")
    try:
        import configparser
        cp = configparser.RawConfigParser(strict=False)
        cp.read(path)
        if cp.has_section("launcher") and cp.has_option("launcher", "version"):
            return cp.get("launcher", "version").strip() or "unknown"
        if cp.has_section("id") and cp.has_option("id", "version"):
            return cp.get("id", "version").strip() or "unknown"
    except Exception:
        pass
    return "unknown"


def _uuid():
    return uuid.uuid4().hex


def _now():
    return time.time()


def _sha256_text(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _search_head():
    try:
        return socket.gethostname() or "unknown"
    except Exception:
        return "unknown"


def _client_ip(args):
    # Best-effort — persistent handlers don't reliably surface the peer
    # address. Try a few keys; default to "" rather than guessing.
    for k in ("client_ip", "remoteAddr", "remote_addr"):
        v = args.get(k)
        if v:
            return str(v)[:64]
    headers = args.get("headers") or {}
    if isinstance(headers, dict):
        xff = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
        if xff:
            return str(xff).split(",")[0].strip()[:64]
    return ""


def _str(v, n=512):
    return str(v if v is not None else "")[:n]


def _names_only(attachments):
    """Keep ONLY {kind, name} from attachments — never their content."""
    out = []
    if isinstance(attachments, list):
        for a in attachments[:64]:
            if isinstance(a, dict):
                out.append({"kind": _str(a.get("kind"), 48),
                            "name": _str(a.get("name"), 256)})
    return out


# ─────────────────────────────────────────────────────────────────────
# Org audit configuration
# ─────────────────────────────────────────────────────────────────────
def resolve_audit_cfg(sys_token, org_short):
    """Return the audit config for an Org from its raw KVStore row.

    {audit_index, audit_content_mode, audit_enforcement, audit_dpia_ack,
     audit_role_patterns}. Missing index → "" (no real audit logging).
    DFLT deliberately has NO default index (spec §9.2).
    """
    row = None
    want = (org_short or "").upper()
    for r in kv_list(rest, sys_token, ORG_COLLECTION):
        # Match on short, falling back to _key — a row whose `short` was blanked
        # by the pre-1.3.1 partial-update bug is still identified by its _key
        # (which equals the Org short). Without this the per-Org audit index
        # can't be found and nothing is logged.
        if str(r.get("short") or r.get("_key") or "").upper() == want:
            row = r
            break
    row = row or {}
    mode = str(row.get("audit_content_mode") or "").lower()
    if mode not in VALID_CONTENT_MODES:
        mode = DEFAULT_CONTENT_MODE
    enforce = str(row.get("audit_enforcement") or "best_effort").lower()
    if enforce not in ("enforce", "best_effort"):
        enforce = "best_effort"
    rp = row.get("audit_role_patterns")
    return {
        "audit_index": _str(row.get("audit_index"), 256).strip(),
        "audit_content_mode": mode,
        "audit_enforcement": enforce,
        "audit_dpia_ack": bool(row.get("audit_dpia_ack")),
        "audit_role_patterns": rp if isinstance(rp, list) else [],
    }


# ─────────────────────────────────────────────────────────────────────
# Content-mode rendering (§7.2 / §7.3.1) — hash BEFORE truncate
# ─────────────────────────────────────────────────────────────────────
def _cap_body(text, max_bytes=MAX_BODY_BYTES):
    """Return (stored_text, sha256_of_FULL, truncated, full_bytes, full_chars).

    The hash is over the COMPLETE untruncated body; only the stored copy is
    cut, on a UTF-8 boundary, so a suspected full text can still be proven.
    """
    full = text or ""
    raw = full.encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    if len(raw) <= max_bytes:
        return full, sha, False, len(raw), len(full)
    stored = raw[:max_bytes].decode("utf-8", "ignore")
    return stored, sha, True, len(raw), len(full)


def render_content(mode, user_input):
    """Render the user-input fields for an llm_request per the Org mode.

    `metadata_only` keeps no body; the heavier modes add hash/preview/full.
    Always called SERVER-SIDE so the client cannot under- or over-report.
    """
    text = user_input or ""
    if mode == "metadata_only" or not text:
        return {"user_input_present": bool(text)} if mode != "metadata_only" \
            else {}
    if mode == "prompt_hash":
        return {
            "user_input_sha256": _sha256_text(text),
            "user_input_chars": len(text),
            "user_input_bytes": len(text.encode("utf-8")),
        }
    if mode == "truncated_prompt":
        return {
            "user_input_preview": text[:TRUNCATED_PREVIEW_CHARS],
            "user_input_sha256": _sha256_text(text),
            "user_input_chars": len(text),
            "user_input_bytes": len(text.encode("utf-8")),
        }
    # full_prompt
    stored, sha, trunc, fb, fc = _cap_body(text)
    out = {
        "user_input_full": stored,
        "user_input_sha256": sha,
        "user_input_chars": fc,
        "user_input_bytes": fb,
    }
    if trunc:
        out["user_input_truncated"] = True
    return out


def render_response(mode, text):
    """Render the response body fields per the Org content mode — symmetric
    with render_content() so a privacy-conservative Org (metadata_only /
    prompt_hash) does not retain LLM response bodies either."""
    if not text or mode == "metadata_only":
        return {}
    if mode == "prompt_hash":
        return {"response_sha256": _sha256_text(text),
                "response_chars": len(text),
                "response_bytes": len(text.encode("utf-8"))}
    if mode == "truncated_prompt":
        return {"response_preview": text[:TRUNCATED_PREVIEW_CHARS],
                "response_sha256": _sha256_text(text),
                "response_chars": len(text),
                "response_bytes": len(text.encode("utf-8"))}
    # full_prompt
    stored, sha, trunc, fb, fc = _cap_body(text)
    out = {"response_full": stored, "response_sha256": sha,
           "response_chars": fc, "response_bytes": fb}
    if trunc:
        out["response_full_truncated"] = True
    return out


# ─────────────────────────────────────────────────────────────────────
# Secret redaction (§7.5) — used by governance_change emitters
# ─────────────────────────────────────────────────────────────────────
def redact_row(value, _redacted=None):
    """Recursively mask sensitive keys. Returns (redacted, sorted_field_list)."""
    if _redacted is None:
        _redacted = set()

    def _walk(v):
        if isinstance(v, dict):
            out = {}
            for k, vv in v.items():
                if k in _REDACT_EXACT or _REDACT_RE.search(str(k)):
                    out[k] = _REDACTED
                    _redacted.add(k)
                else:
                    out[k] = _walk(vv)
            return out
        if isinstance(v, list):
            return [_walk(x) for x in v]
        return v

    cleaned = _walk(value)
    return cleaned, sorted(_redacted)


# ─────────────────────────────────────────────────────────────────────
# Per-stream integrity hash-chain (§5.3 — accidental-gap detection only)
# ─────────────────────────────────────────────────────────────────────
_HASH_TAIL = {}  # (org_short, search_head) -> prev event_hash


def _chain(stream_key, event):
    prev = _HASH_TAIL.get(stream_key, "")
    event["prev_hash"] = prev
    canonical = json.dumps(event, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    event["event_hash"] = h
    _HASH_TAIL[stream_key] = h
    return event


# ─────────────────────────────────────────────────────────────────────
# Consent registry (process-local, MVP server-verification of consent)
# ─────────────────────────────────────────────────────────────────────
_CONSENT = {}  # (user, session_id, llm_config_key) -> ts


def _consent_key(user, session_id, llm_key):
    return (user or "", session_id or "", llm_key or "")


def record_consent(user, session_id, llm_key, ts):
    _CONSENT[_consent_key(user, session_id, llm_key)] = ts


def consent_confirmed(user, session_id, llm_key):
    return _consent_key(user, session_id, llm_key) in _CONSENT


# ─────────────────────────────────────────────────────────────────────
# Write-failure visibility — a best_effort Org silently swallowing a failed
# audit write is exactly how audit data goes missing unnoticed. Surface it to
# $SPLUNK_HOME/var/log/splunk/itmip_llm_audit.log (index=_internal
# source=*itmip_llm_audit.log*).
# ─────────────────────────────────────────────────────────────────────
def _audit_logger():
    import logging
    import logging.handlers
    lg = logging.getLogger("itmip_llm_audit")
    if not lg.handlers:
        try:
            sh = os.environ.get("SPLUNK_HOME") or "/opt/splunk"
            path = os.path.join(sh, "var", "log", "splunk", "itmip_llm_audit.log")
            h = logging.handlers.RotatingFileHandler(
                path, maxBytes=5 * 1024 * 1024, backupCount=3)
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            lg.addHandler(h)
            lg.setLevel(logging.INFO)
        except Exception:
            pass
    return lg


def _audit_write_failed(index, reason):
    try:
        _audit_logger().error("audit write FAILED index=%s reason=%s", index, reason)
    except Exception:
        pass


def _audit_info(msg, *a):
    try:
        _audit_logger().info(msg, *a)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────
# `| collect` writer for internal (`_*`) audit indexes.
#
# ROOT CAUSE this guards against (diagnosed 2026-06-10): `collect`'s
# DESTINATION-INDEX authorization uses the *dispatching* role's OWN
# `srchIndexesAllowed`, IGNORING imported allowances. The `passSystemAuth`
# identity `splunk-system-user` has an EMPTY own `srchIndexesAllowed` (it only
# inherits `_*` via `imported_srchIndexesAllowed`), so when it runs
# `| collect index=_itmip_audit_<ORG>`, collect cannot authorize the requested
# internal index and SILENTLY REDIRECTS the event to a fallback internal index
# (observed: `_itmip_audit_dflt`) — while the search still returns HTTP 200 and
# `info=completed`. The old code trusted the 200 and returned `logged=true`, so
# `llm_response` (and `llm_request`) events were written to the WRONG index and
# never appeared in the Org's configured audit index → the Audit UI showed 0
# tokens and "—" outcome.
#
# Fix: (1) run collect, (2) PARSE the oneshot `messages` for the
# "Successfully wrote file" INFO, (3) VERIFY the event actually landed in the
# INTENDED index by reading back its event_id, (4) if the system-token write
# did not verify, RETRY under the USER token — a user whose own role grants
# `_*` (admins, customer auditor roles) lands the event correctly; a user
# without that access fails honestly. Only return logged=true when read-back in
# the intended index succeeds; otherwise logged=false + reason (no more silent
# loss / false-positive success).
# ─────────────────────────────────────────────────────────────────────
def _collect_oneshot(token, search):
    """Run a `| collect` oneshot under `token`. Returns (status, content, wrote)
    where `wrote` is True iff the oneshot reported "Successfully wrote file"
    (HTTP 200 alone is NOT trusted — see module note)."""
    resp, content = rest.simpleRequest(
        "/services/search/jobs/oneshot",
        sessionKey=token, method="POST",
        postargs={"search": search, "output_mode": "json"},
        rawResult=True,
    )
    status = getattr(resp, "status", 0)
    wrote = False
    try:
        msgs = (json.loads(content or b"{}") or {}).get("messages") or []
        for m in msgs:
            if "successfully wrote file" in str(m.get("text", "")).lower():
                wrote = True
                break
    except Exception:
        pass
    return status, content, wrote


def _verify_landed(token, index, event_id):
    """Read back `event_id` from the INTENDED index to confirm the collect did
    not mis-route. Returns True only if exactly that event is searchable in that
    index. Best-effort: a read failure (e.g. token can't search `_*`) returns
    False so the caller does not falsely claim success."""
    if not event_id:
        return False
    # Bounded, fast verification window — collect→stash→index has a few-second
    # lag, so retry briefly. event_id is a uuid hex: exact, index-scoped match.
    spl = ('search index=%s sourcetype="%s" event_id=%s earliest=-5m latest=+1y '
           "| head 1 | stats count") % (index, AUDIT_SOURCETYPE, event_id)
    for _ in range(8):
        try:
            resp, content = rest.simpleRequest(
                "/services/search/jobs/oneshot",
                sessionKey=token, method="POST",
                postargs={"search": spl, "output_mode": "json"},
                rawResult=True,
            )
            if getattr(resp, "status", 0) in (200, 201):
                rows = (json.loads(content or b"{}") or {}).get("results") or []
                if rows and int(rows[0].get("count") or 0) >= 1:
                    return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


# ─────────────────────────────────────────────────────────────────────
# Core emitter — write one event to the Org's audit index
# ─────────────────────────────────────────────────────────────────────
def emit_audit(sys_token, org_short, bu_short, actor_user, actor_roles,
               event_type, fields, audit_cfg=None, client_ip="",
               search_head=None, user_token=None):
    """Stamp the authoritative envelope, chain, and POST to the Org index.

    Returns {ok, logged, request_id, event_hash?, reason?}. `logged=False`
    with a reason means the write did not land (the caller decides whether to
    fail closed). Never raises.

    `user_token` (optional): the calling user's own auth token. Used ONLY as a
    verified fallback for internal (`_*`) audit indexes, where a system-token
    `| collect` silently mis-routes (see _collect_oneshot note). Server-side
    emitters that have no user token (governance/tenancy) omit it and rely on
    the system-token write + read-back verification.
    """
    cfg = audit_cfg or resolve_audit_cfg(sys_token, org_short)
    index = cfg.get("audit_index") or ""
    request_id = (fields or {}).get("request_id") or _uuid()
    if not index:
        return {"ok": False, "logged": False, "request_id": request_id,
                "reason": "no audit_index configured for Org %s" % org_short}

    sh = search_head or _search_head()
    event = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "event_type": event_type,
        "event_id": _uuid(),
        "request_id": request_id,
        "ts_request": round(_now(), 3),
        "actor_user": actor_user or "unknown",
        "actor_roles": list(actor_roles or []),
        "org_short": org_short or "DFLT",
        "bu_short": bu_short or "DFLT",
        "search_head": sh,
        "client_ip": client_ip or "",
        "app_version": _app_version(),
    }
    for k, v in (fields or {}).items():
        if k == "request_id":
            continue
        event[k] = v

    _chain((event["org_short"], sh), event)

    body = json.dumps(event, ensure_ascii=False)
    if len(body.encode("utf-8")) > TOTAL_EVENT_CEILING_BYTES:
        # Drop the largest body further rather than let Splunk cut the event.
        for big in ("user_input_full", "response_full"):
            if event.get(big):
                keep = max(MAX_BODY_BYTES // 2, 4096)
                event[big] = event[big].encode("utf-8")[:keep].decode("utf-8", "ignore")
                event[big + "_truncated"] = True
        _chain((event["org_short"], sh), event)  # re-chain after edit
        body = json.dumps(event, ensure_ascii=False)

    # Two writers, chosen by index style:
    #  - Internal (`_*`) indexes are admin-only-readable by default (good for
    #    audit data) but Splunk's receivers/simple endpoint REFUSES them
    #    ("supplied index … missing"). `| collect` is the only writer that
    #    accepts internal indexes → route those through a oneshot collect
    #    search, then VERIFY the event landed in the intended index (the
    #    system token mis-routes `_*` collects — see _collect_oneshot note —
    #    so we fall back to the user token when the system write doesn't
    #    verify). One or two search dispatches per event; audit volume is
    #    human-paced so the overhead is acceptable.
    #  - Normal indexes use the fast synchronous receivers/simple path.
    if index.startswith("_"):
        ev_ts = event.get("ts_request") or _now()
        event_id = event.get("event_id")
        spl_raw = '"' + body.replace("\\", "\\\\").replace('"', '\\"') + '"'
        search = (
            "| makeresults count=1 | eval _raw=%s, _time=%s "
            '| collect index=%s sourcetype="%s" source="%s" output_format=raw'
        ) % (spl_raw, ev_ts, index, AUDIT_SOURCETYPE, AUDIT_SOURCE)
        # Permanent, useful diagnostics: the exact search + (below) the oneshot
        # outcome land in $SPLUNK_HOME/var/log/splunk/itmip_llm_audit.log.
        _audit_info("collect attempt index=%s event_type=%s event_id=%s search=%s",
                    index, event_type, event_id, search)

        last_reason = ""
        # Try the system token first (bypass-proof for the user), then — only if
        # the write does not VERIFY in the intended index — the user token, which
        # lands when the caller's own role grants `_*` (admins / auditor roles).
        # A token is tried only once and only if present/distinct.
        tried = []
        candidates = [("system", sys_token)]
        if user_token and user_token != sys_token:
            candidates.append(("user", user_token))
        for label, token in candidates:
            if not token:
                continue
            tried.append(label)
            try:
                status, content, wrote = _collect_oneshot(token, search)
            except Exception as exc:
                last_reason = "collect[%s] exception: %s" % (label, exc)
                _audit_write_failed(index, last_reason)
                continue
            snippet = (content or b"")[:200]
            _audit_info("collect[%s] index=%s http=%s wrote_file=%s msgs=%s",
                        label, index, status, wrote, snippet)
            if status not in (200, 201):
                last_reason = "collect[%s] http %s: %s" % (label, status, snippet)
                _audit_write_failed(index, last_reason)
                continue
            if not wrote:
                last_reason = ("collect[%s] no 'Successfully wrote file' message: %s"
                               % (label, snippet))
                _audit_write_failed(index, last_reason)
                continue
            # HTTP 200 + stash written is NOT enough: a system-token collect can
            # write to a FALLBACK internal index. Confirm it landed where asked.
            if _verify_landed(token, index, event_id):
                _audit_info("collect[%s] VERIFIED in index=%s event_id=%s",
                            label, index, event_id)
                return {"ok": True, "logged": True, "request_id": request_id,
                        "event_hash": event.get("event_hash")}
            last_reason = ("collect[%s] reported success but event_id=%s did NOT "
                           "land in index=%s (collect mis-routed — the dispatching "
                           "role's own srchIndexesAllowed does not grant this "
                           "internal index)" % (label, event_id, index))
            _audit_write_failed(index, last_reason)

        reason = last_reason or ("collect could not write to internal index %s "
                                 "(tried: %s)" % (index, ",".join(tried) or "none"))
        return {"ok": False, "logged": False, "request_id": request_id,
                "reason": reason}

    url = (
        "/services/receivers/simple"
        "?index={idx}&sourcetype={st}&source={src}&host={host}"
    ).format(idx=index, st=AUDIT_SOURCETYPE, src=AUDIT_SOURCE, host=sh)
    try:
        resp, content = rest.simpleRequest(
            url, sessionKey=sys_token, method="POST",
            rawResult=True, jsonargs=body,
        )
        status = getattr(resp, "status", 0)
        if status not in (200, 201):
            reason = "receivers/simple %s: %s" % (status, (content or b"")[:160])
            _audit_write_failed(index, reason)
            return {"ok": False, "logged": False, "request_id": request_id,
                    "reason": reason}
    except Exception as exc:
        reason = "receivers/simple exception: %s" % exc
        _audit_write_failed(index, reason)
        return {"ok": False, "logged": False, "request_id": request_id,
                "reason": reason}
    return {"ok": True, "logged": True, "request_id": request_id,
            "event_hash": event.get("event_hash")}


# ─────────────────────────────────────────────────────────────────────
# governance_change (§7.5) — emitted from emit_change() at every mutation
# ─────────────────────────────────────────────────────────────────────
# Collection → audited object label. Only GOVERNANCE collections produce a
# governance_change; history/authoring-audit collections are excluded (they
# are not governance and would mis-route / double-log).
_GOV_OBJECT = {
    "itmip_ai_use_cases": "template",
    "itmip_ai_skills": "skill",
    "itmip_tool_assignments": "tool_assignment",
    "itmip_tool_overrides": "tool_override",
    "itmip_llm_custom_tools": "custom_tool",
    "itmip_mcp_servers": "mcp_server",
    "itmip_mcp_tools": "mcp_tool",
    "itmip_llm_configs": "llm_config",
    "itmip_organisations": "org",
    "itmip_business_units": "business_unit",
    "itmip_knowledge_connectors": "knowledge_connector",
    "itmip_ai_knowledge_entries": "knowledge_entry",
    "itmip_knowledge_static_rules": "knowledge_static_rule",
}
GOVERNANCE_COLLECTIONS = frozenset(_GOV_OBJECT.keys())


def emit_governance(sys_token, collection, op, key, before, after, user):
    """Mirror a KVStore mutation into the owning Org's audit index as a
    redacted governance_change. Best-effort; never raises. Called from
    emit_change() so every governance mutation site is covered at once.
    """
    if collection not in GOVERNANCE_COLLECTIONS:
        return
    row = after if isinstance(after, dict) else (before if isinstance(before, dict) else {})
    if collection == "itmip_organisations":
        org = str(row.get("short") or key or "DFLT").upper()
    else:
        org = str(row.get("org_short") or row.get("owner_org_short") or "").upper() or "DFLT"
    cfg = resolve_audit_cfg(sys_token, org)
    if not cfg.get("audit_index"):
        # Un-audited Org (e.g. DFLT not yet configured): the change still
        # lives in itmip_changes (60d). No long-term governance audit here.
        return
    rb, fb = (redact_row(before) if isinstance(before, dict) else (before, []))
    ra, fa = (redact_row(after) if isinstance(after, dict) else (after, []))
    fields = {
        "object": _GOV_OBJECT.get(collection, collection),
        "object_name": _str(row.get("name") or row.get("short") or key, 256),
        "object_key": _str(key, 128),
        "op": _str(op, 24),
        "before": rb,
        "after": ra,
        "redacted_fields": sorted(set(fb) | set(fa)),
    }
    # actor_roles are not available at the emit_change call site — user is
    # the authoritative identity; roles snapshot is a known MVP gap.
    emit_audit(sys_token, org, "DFLT", user, [], "governance_change",
               fields, audit_cfg=cfg)


# ─────────────────────────────────────────────────────────────────────
# Build the per-family fields from a client payload (server-authoritative)
# ─────────────────────────────────────────────────────────────────────
def _build_llm_request_fields(payload, cfg, user, session_id):
    llm_key = _str(payload.get("llm_config_key"), 128)
    confirmed = consent_confirmed(user, session_id, llm_key)
    fields = {
        "transport": "browser_direct",  # this HTTP path is browser_direct only
        "llm_config_key": llm_key,
        "llm_config_name": _str(payload.get("llm_config_name"), 128),
        "provider_kind": _str(payload.get("provider_kind"), 48),
        "model": _str(payload.get("model"), 96),
        "endpoint_host": _str(payload.get("endpoint_host"), 160),
        "key_mode": _str(payload.get("key_mode"), 24),
        "prompt_source": ("template_questionnaire"
                          if payload.get("template_ref") else "freeform"),
        "template_ref": payload.get("template_ref")
        if isinstance(payload.get("template_ref"), dict) else None,
        "audit_content_mode": cfg["audit_content_mode"],
        "attachments": _names_only(payload.get("attachments")),
        "consent_accepted_at": payload.get("consent_accepted_at"),
        "consent_text_version": _str(payload.get("consent_text_version"), 64),
        "consent_text_sha256": _str(payload.get("consent_text_sha256"), 64),
        "consent_status": "confirmed" if confirmed else "client_asserted_unconfirmed",
        "is_followup_turn": bool(payload.get("is_followup_turn")),
    }
    fields.update(render_content(cfg["audit_content_mode"],
                                 payload.get("user_input")))
    return fields


def _build_llm_response_fields(payload, cfg):
    fields = {
        "outcome": _str(payload.get("outcome") or "ok", 32),
        "error": _str(payload.get("error"), 512),
        "ts_response": payload.get("ts_response") or round(_now(), 3),
        "duration_ms": int(payload.get("duration_ms") or 0),
        "tokens_in": int(payload.get("tokens_in") or 0),
        "tokens_out": int(payload.get("tokens_out") or 0),
        "cache_read": int(payload.get("cache_read") or 0),
        "cost_usd": float(payload.get("cost_usd") or 0.0),
        "tool_calls": [_str(t, 64) for t in (payload.get("tool_calls") or [])][:64],
        "emitted_by": "client",
    }
    if isinstance(payload.get("request_id"), str):
        fields["request_id"] = payload["request_id"]
    fields.update(render_response(cfg["audit_content_mode"],
                                  payload.get("response_full")))
    return fields


def _build_consent_fields(payload):
    return {
        "consent_accepted_at": payload.get("consent_accepted_at") or round(_now(), 3),
        "consent_text_version": _str(payload.get("consent_text_version"), 64),
        "consent_text_sha256": _str(payload.get("consent_text_sha256"), 64),
        "consent_scope": _str(payload.get("llm_config_key"), 128),
        "consent_trigger": _str(payload.get("consent_trigger") or "ask", 24),
        "provider_kind": _str(payload.get("provider_kind"), 48),
        "endpoint_host": _str(payload.get("endpoint_host"), 160),
    }


# ─────────────────────────────────────────────────────────────────────
# HTTP handler
# ─────────────────────────────────────────────────────────────────────
class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "POST").upper()
            if method != "POST":
                return err(405, "Only POST is supported.")
            usr_token = user_token(args)
            if not usr_token:
                return err(401, "Not authenticated.")
            sys_token = system_token(args) or usr_token

            user = user_name(args)
            # Pre-flight + completion can be ~2 events/turn; 300/min is ample.
            if not rate_limit_check("audit", user, 300):
                return err(429, "Too many audit writes; slow down.")

            try:
                payload = json.loads(args.get("payload") or "{}")
            except Exception:
                return err(400, "Invalid JSON payload.")

            event_type = (payload.get("event_type") or "").strip()
            if event_type not in CLIENT_EVENT_TYPES:
                return err(400, "event_type must be one of %s."
                           % ", ".join(CLIENT_EVENT_TYPES))

            roles = user_roles(args, rest)
            tenant = resolve_caller_tenant(
                args, rest, sys_token,
                url_app=_str(payload.get("splunk_app"), 64) or None,
                roles=roles,
            )
            org_short = tenant.get("org_short") or "DFLT"
            bu_short = tenant.get("bu_short") or "DFLT"
            cfg = resolve_audit_cfg(sys_token, org_short)
            session_id = _str(payload.get("session_id"), 128)
            client_ip = _client_ip(args)

            if event_type == "consent_acceptance":
                record_consent(user, session_id,
                               _str(payload.get("llm_config_key"), 128),
                               payload.get("consent_accepted_at") or _now())
                fields = _build_consent_fields(payload)
            elif event_type == "llm_request":
                fields = _build_llm_request_fields(payload, cfg, user, session_id)
            else:  # llm_response
                fields = _build_llm_response_fields(payload, cfg)

            res = emit_audit(sys_token, org_short, bu_short, user, roles,
                             event_type, fields, audit_cfg=cfg,
                             client_ip=client_ip, user_token=usr_token)
            # The browser uses `audit_enforcement` + `logged` to fail-closed on
            # an llm_request pre-flight when the Org is `enforce` (§10). This
            # HTTP path itself never hard-blocks — the UI decides.
            return ok({
                "ok": True,
                "logged": bool(res.get("logged")),
                "request_id": res.get("request_id"),
                "event_hash": res.get("event_hash"),
                "audit_enforcement": cfg.get("audit_enforcement"),
                "audit_index_configured": bool(cfg.get("audit_index")),
                "reason": res.get("reason"),
            })
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
