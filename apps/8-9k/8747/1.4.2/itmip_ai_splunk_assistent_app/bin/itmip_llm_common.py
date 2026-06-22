"""Shared helpers for AiWorkbench REST handlers.

Each Splunk persistent REST handler must live in its own .py file with
exactly one class implementing PersistentServerConnectionApplication —
Splunk's loader refuses scripts containing more than one. This module
holds the helpers each handler imports.

The Splunk app folder is still named itmip_ai_splunk_assistent_app
(renaming the folder would break every install). The password realm and
the previously-saved central Anthropic key still use that name so
existing data keeps working after the v0.2 rename.
"""

import json
import re

APP_NAME = "itmip_ai_splunk_assistent_app"
# Backwards-compat: realm name where the v0.1 Anthropic key was saved.
LEGACY_PASSWORD_REALM = "itmip_ai_splunk_assistent_app"
LEGACY_PASSWORD_NAME = "anthropic_api_key"
# Going forward: every LLM config stores its API key in storage/passwords
# under realm = LLM_PASSWORD_REALM, name = <llm_config_id>.
LLM_PASSWORD_REALM = "itmip_llm_assistent_app"
# Telemetry events go to a regular EVENT index ("main" by default — always
# present on every Splunk install). Customers can override in
# local/macros.conf if they want a dedicated index. We deliberately do
# NOT write to a metrics-type index (e.g. _metrics) because the
# `receivers/simple` endpoint doesn't produce metric-format data.
DEFAULT_METRICS_INDEX = "main"
USAGE_SOURCETYPE = "ai_assistant_usage"
USAGE_SOURCE = "ai_assistant"


def json_response(status, payload):
    return {
        "payload": json.dumps(payload),
        "status": status,
        "headers": {"Content-Type": "application/json"},
    }


def err(status, message):
    return json_response(status, {"error": message})


def ok(payload):
    return json_response(200, payload)


def system_token(args):
    return args.get("system_authtoken") or args.get("systemAuthToken") or ""


def user_name(args):
    session = args.get("session") or {}
    return session.get("user") or "unknown"


def user_token(args):
    session = args.get("session") or {}
    return session.get("authtoken") or ""


def user_roles(args, rest):
    """Return the list of Splunk roles for the calling user.

    Uses the user's own auth token (NOT the system token), so this
    request fails closed if the caller can't authenticate. Used by the
    sensitive handlers to gate POST/DELETE on admin-equivalent roles.
    """
    tok = user_token(args)
    if not tok:
        return []
    try:
        response, content = rest.simpleRequest(
            "/services/authentication/current-context?output_mode=json",
            sessionKey=tok,
            method="GET",
        )
        if getattr(response, "status", 0) != 200:
            return []
        data = json.loads(content)
        entries = data.get("entry") or []
        if not entries:
            return []
        c = entries[0].get("content") or {}
        roles = c.get("roles") or []
        if isinstance(roles, list):
            return [str(r) for r in roles]
    except Exception:
        pass
    return []


def is_admin(args, rest):
    """True if the calling user has the `admin` or `splunk_admin` role."""
    for r in user_roles(args, rest):
        if r.lower() in ("admin", "splunk_admin"):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────
# Authorisation: can this user use this LLM config?
# ─────────────────────────────────────────────────────────────────────
def load_llm_config(sys_token, config_key, rest):
    """Look up an itmip_llm_configs record by _key. Returns dict or None.

    Mirrors the lookup in itmip_llm_proxy but factored out so both that
    handler and the secret handler share the same source of truth.
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
    # Synthetic bootstrap fallback for the built-in Anthropic config that
    # isn't in KVStore by default.
    if safe == "DFLT_DFLT_anthropic_central":
        return {
            "_key": safe,
            "name": safe,
            "provider_kind": "anthropic",
            "scope": "central",
            "org_short": "DFLT",
            "bu_short": "DFLT",
            "endpoint": "https://api.anthropic.com/v1/messages",
            "model": "claude-sonnet-4-6",
            "call_mode": "splunk_proxy",
        }
    return None


def owns_personal_config(user, cfg):
    """True if `user` owns this personal LlmConfig.

    Prefers an explicit `owner_user`; for legacy rows without it, matches
    the username as an exact TOKEN of the config name (split on
    non-alphanumerics) — never a substring, so `ad` no longer matches
    `administrator` (B3 / Analysis Findings F3)."""
    u = (user or "").strip().lower()
    if not u:
        return False
    owner = (cfg.get("owner_user") or "").strip().lower()
    if owner:
        return u == owner
    name = (cfg.get("name") or "").lower()
    return u in [t for t in re.split(r"[^a-z0-9]+", name) if t]


def is_user_allowed_for_llm_config(args, rest, cfg):
    """Return True if the calling user is allowed to use this LlmConfig.

    Rules (most permissive first):
      1. Admins can use any config.
      2. The DFLT/DFLT central bootstrap config is open to everyone.
      3. The user is in `cfg.extra_user_names`.
      4. The user has a role intersecting `cfg.extra_role_patterns`.
      5. Personal configs: the user OWNS it (exact owner_user / name-token —
         see owns_personal_config). [B3]
      6. Org/BU-scoped configs: the user is a MEMBER of that Org (and BU),
         resolved server-side from their own roles. This replaces the old
         conservative refusal so the proxy gate accepts what the Ask-tab
         dropdown shows. [B1]
    """
    user = user_name(args)
    roles = user_roles(args, rest)
    lower_roles = {r.lower() for r in roles}
    if "admin" in lower_roles or "splunk_admin" in lower_roles:
        return True
    org = (cfg.get("org_short") or "").upper()
    bu = (cfg.get("bu_short") or "").upper()
    scope = (cfg.get("scope") or "").lower()
    if scope == "central" and org == "DFLT" and bu == "DFLT":
        return True
    extras_users = cfg.get("extra_user_names") or []
    if isinstance(extras_users, list) and user in extras_users:
        return True
    extras_roles = cfg.get("extra_role_patterns") or []
    if isinstance(extras_roles, list):
        for r in roles:
            if r in extras_roles:
                return True
    if scope == "personal":
        return owns_personal_config(user, cfg)
    return _is_member_of_config_tenant(rest, system_token(args), cfg, user, roles)


def _is_member_of_config_tenant(rest, sys_token, cfg, user, roles):
    """True if `user` is a member (by their own roles) of the Org — and,
    for a BU-scoped config, the BU — this config is scoped to. Lets Org/BU
    members use their tenant's configs without an explicit extra_* grant
    (B1). Membership is resolved server-side; never from client input."""
    org_short = (cfg.get("org_short") or "").upper()
    if not org_short or org_short == "DFLT":
        return False
    orgs = [_norm_org(r) for r in kv_list(rest, sys_token, "itmip_organisations")]
    org = next((o for o in orgs if o.get("short") == org_short), None)
    if not org or not any(_tenant_any_match(org.get("role_patterns"), r) for r in roles):
        return False
    bu_short = (cfg.get("bu_short") or "DFLT").upper()
    if bu_short == "DFLT":
        return True
    bus = [_norm_bu(r) for r in kv_list(rest, sys_token, "itmip_business_units")]
    bu = next(
        (b for b in bus if b.get("org_short") == org_short and b.get("short") == bu_short),
        None,
    )
    if not bu:
        return False
    return user in (bu.get("extra_user_names") or []) or any(
        _tenant_any_match(bu.get("extra_role_patterns"), r) for r in roles
    )


# ─────────────────────────────────────────────────────────────────────
# Simple in-process per-user rate limit
# ─────────────────────────────────────────────────────────────────────
import time as _time

_rate_buckets = {}


def rate_limit_check(bucket, user, cap_per_minute):
    """Return True when the call is allowed, False when over the cap.

    The state is a process-local dict — fine for the splunkd persistent
    handler lifecycle. On worker recycling the bucket resets; that's
    acceptable for a defensive rate limit.
    """
    now = _time.time()
    cutoff = now - 60.0
    b = _rate_buckets.setdefault(bucket, {})
    entries = [t for t in b.get(user, []) if t >= cutoff]
    if len(entries) >= cap_per_minute:
        b[user] = entries
        return False
    entries.append(now)
    b[user] = entries
    return True


# ─────────────────────────────────────────────────────────────────────
# Tenancy resolution (server-side port of src/services/tenancy.ts)
#
# Authorisation must be derived from the caller's OWN roles, never from a
# client-supplied org/bu. `resolve_caller_tenant` is the server
# counterpart of resolveTenant() in the React layer and is the single
# source of truth the sensitive handlers should use to decide which Org /
# BU a request belongs to. See docs/Analysis Findings.md F1.
# ─────────────────────────────────────────────────────────────────────

def kv_list(rest, sys_token, collection):
    """GET a whole KVStore collection with the system token. Returns a
    list (possibly empty); never raises."""
    url = (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=collection)
    try:
        resp, content = rest.simpleRequest(url, sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) != 200:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _tenant_pattern_matches(pattern, value):
    """Glob-ish match mirroring tenancy.ts patternMatches:
    "" -> False, "*" -> True, "ab*" -> startswith, otherwise the pattern
    is treated as a regex with '*' -> '.*', anchored, case-insensitive.
    A malformed pattern fails closed (no match) rather than raising."""
    if not pattern:
        return False
    if pattern == "*":
        return True
    lc = (value or "").lower()
    pat = pattern.lower()
    if pat.endswith("*") and "*" not in pat[:-1]:
        return lc.startswith(pat[:-1])
    try:
        return re.match("^" + pat.replace("*", ".*") + "$", lc) is not None
    except re.error:
        return False


def _tenant_any_match(patterns, value):
    if not isinstance(patterns, list):
        return False
    return any(_tenant_pattern_matches(p, value) for p in patterns)


_DEFAULT_ORG = {
    "short": "DFLT",
    "name": "Default",
    "app_patterns": ["*"],
    "role_patterns": ["admin"],
}
_DEFAULT_BU = {
    "org_short": "DFLT",
    "short": "DFLT",
    "name": "Default",
    "app_patterns": [],
    "extra_role_patterns": [],
    "extra_user_names": [],
}


def _norm_org(r):
    ap = r.get("app_patterns")
    rp = r.get("role_patterns")
    # Fall back to the _key (which IS the Org short) if `short` was blanked by
    # the pre-1.3.1 partial-update bug — otherwise the resolver returns a blank
    # org_short, the header shows "Org: •", and per-Org audit config can't be
    # matched (so nothing gets logged).
    return {
        "short": str(r.get("short") or r.get("_key") or "").upper(),
        "name": r.get("name") or "",
        "app_patterns": ap if isinstance(ap, list) else [],
        "role_patterns": rp if isinstance(rp, list) else [],
    }


def _norm_bu(r):
    ap = r.get("app_patterns")
    erp = r.get("extra_role_patterns")
    eun = r.get("extra_user_names")
    # BU _key is the composite "<ORG>_<BU>" — recover org_short / short from it
    # if either was blanked by the pre-1.3.1 partial-update bug.
    key = str(r.get("_key") or "")
    key_org, _, key_bu = key.partition("_")
    return {
        "org_short": str(r.get("org_short") or key_org or "DFLT").upper(),
        "short": str(r.get("short") or key_bu or "").upper(),
        "name": r.get("name") or "",
        "app_patterns": ap if isinstance(ap, list) else [],
        "extra_role_patterns": erp if isinstance(erp, list) else [],
        "extra_user_names": eun if isinstance(eun, list) else [],
    }


def _resolve_tenant_pure(orgs, bus, user, roles, admin, app):
    """Pure resolver (no REST). orgs/bus must already be normalised.
    Faithful port of tenancy.ts resolveTenant — kept side-effect-free so
    it can be unit-tested directly."""
    for org in orgs:
        app_ok = _tenant_any_match(org.get("app_patterns"), app)
        role_ok = admin or any(_tenant_any_match(org.get("role_patterns"), r) for r in roles)
        if not app_ok or not role_ok:
            continue
        org_bus = [b for b in bus if b.get("org_short") == org.get("short")]
        chosen = None
        for b in org_bus:
            # A BU's app_patterns are a subset of the Org's: if set, the
            # current app must match one; empty inherits the Org's apps.
            bu_apps = b.get("app_patterns") or []
            app_ok = (not bu_apps) or _tenant_any_match(bu_apps, app)
            if b.get("short") != "DFLT" and app_ok and (
                user in (b.get("extra_user_names") or [])
                or any(_tenant_any_match(b.get("extra_role_patterns"), r) for r in roles)
            ):
                chosen = b
                break
        if chosen is None:
            chosen = next((b for b in org_bus if b.get("short") == "DFLT"), None)
        if chosen is None:
            chosen = dict(_DEFAULT_BU, org_short=org.get("short"))
        return {
            "org_short": org.get("short"),
            "org_name": org.get("name") or org.get("short"),
            "bu_short": chosen.get("short"),
            "bu_name": chosen.get("name") or chosen.get("short"),
            "is_default": org.get("short") == "DFLT" and chosen.get("short") == "DFLT",
            "is_unassigned": False,
        }
    # No Org matched: admins still fall through to DFLT/DFLT so they can
    # configure the app; non-admins are flagged unassigned.
    return {
        "org_short": _DEFAULT_ORG["short"],
        "org_name": _DEFAULT_ORG["name"],
        "bu_short": _DEFAULT_BU["short"],
        "bu_name": _DEFAULT_BU["name"],
        "is_default": True,
        "is_unassigned": not admin,
    }


def resolve_caller_tenant(args, rest, sys_token, url_app=None, roles=None, is_admin_flag=None):
    """Server-authoritative Org/BU for the calling user.

    Trusts ONLY the caller's own roles (via `user_roles`). `url_app` is a
    non-authoritative context hint used for app_patterns matching — a
    spoofed app cannot grant access, because an Org matches only when the
    caller's REAL roles also match its role_patterns.

    Pass precomputed `roles` / `is_admin_flag` to avoid a duplicate
    current-context lookup when the caller already has them.
    """
    user = user_name(args)
    if roles is None:
        roles = user_roles(args, rest)
    if is_admin_flag is None:
        lower = {str(r).lower() for r in roles}
        is_admin_flag = ("admin" in lower) or ("splunk_admin" in lower)
    orgs = [_norm_org(r) for r in kv_list(rest, sys_token, "itmip_organisations")] or [dict(_DEFAULT_ORG)]
    bus = [_norm_bu(r) for r in kv_list(rest, sys_token, "itmip_business_units")] or [dict(_DEFAULT_BU)]
    return _resolve_tenant_pure(orgs, bus, user, roles, bool(is_admin_flag), url_app or APP_NAME)
