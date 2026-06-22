"""POST /services/itmip_llm/tenancy — wrapper for Org / BU writes.

The frontend used to talk to KVStore directly for Org / BU CRUD. That
worked but left server-side license-tier enforcement at the UI layer
only — a determined admin could `| rest`-POST past the cap. This
handler is the chokepoint: every Org / BU write is funnelled through
here so caps land in code paths the user can't bypass.

  POST /services/itmip_llm/tenancy  body {action, ...payload}

Actions:
  create_org    {short, name, description?, app_patterns?, role_patterns?}
  update_org    {_key, name?, description?, app_patterns?, role_patterns?}
  delete_org    {_key}
  create_bu     {org_short, short, name, description?, app_patterns?, extra_role_patterns?, extra_user_names?}
  update_bu     {_key, name?, description?, app_patterns?, extra_role_patterns?, extra_user_names?}
  delete_bu     {_key}

Cap enforcement:
  - create_org refuses with 403 when current org count >= license max_orgs.
  - create_bu refuses with 403 when current BU count in that Org >=
    license max_bus_per_org.
  - Updates / deletes are NOT capped (they don't grow the count).
"""

import json
import os
import sys
import time

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
    LLM_PASSWORD_REALM,
    err,
    is_admin,
    ok,
    system_token,
    user_name,
    user_token,
)
from itmip_llm_guid import get_environment_guid  # noqa: E402
from itmip_llm_kvstore_changelog import emit_change  # noqa: E402
from itmip_llm_license_tier import caps_for, resolve_tier  # noqa: E402
from itmip_llm_audit import VALID_CONTENT_MODES, emit_audit  # noqa: E402


ORG_COLLECTION = "itmip_organisations"
BU_COLLECTION = "itmip_business_units"
LICENSE_SECRET_NAME = "license_blob"


# ---------- KV helpers ---------------------------------------------------


def _coll_url(collection, suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{sfx}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=collection, sfx=suffix)


def _list_collection(sys_token, collection):
    try:
        resp, content = rest.simpleRequest(
            _coll_url(collection), sessionKey=sys_token, method="GET"
        )
    except Exception:
        return []
    if getattr(resp, "status", 0) != 200:
        return []
    try:
        data = json.loads(content)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _create_in_collection(sys_token, collection, doc, user="unknown"):
    resp, content = rest.simpleRequest(
        _coll_url(collection),
        sessionKey=sys_token,
        method="POST",
        jsonargs=json.dumps(doc),
    )
    if getattr(resp, "status", 0) not in (200, 201):
        raise RuntimeError(
            "create %s -> %s: %s"
            % (collection, getattr(resp, "status", 0), (content or "")[:200])
        )
    result = json.loads(content)
    emit_change(
        sys_token,
        collection,
        op="create",
        key=str(result.get("_key") or ""),
        before=None,
        after=doc,
        user=user,
    )
    return result


def _update_in_collection(sys_token, collection, key, doc, user="unknown"):
    resp, content = rest.simpleRequest(
        _coll_url(collection, "/" + key),
        sessionKey=sys_token,
        method="POST",
        jsonargs=json.dumps(doc),
    )
    if getattr(resp, "status", 0) not in (200, 201):
        raise RuntimeError(
            "update %s/%s -> %s"
            % (collection, key, getattr(resp, "status", 0))
        )
    emit_change(
        sys_token,
        collection,
        op="update",
        key=key,
        before=None,
        after=doc,
        user=user,
    )


def _delete_in_collection(sys_token, collection, key, user="unknown"):
    try:
        rest.simpleRequest(
            _coll_url(collection, "/" + key),
            sessionKey=sys_token,
            method="DELETE",
        )
    except Exception as exc:
        # Swallow 404s (idempotent delete); raise on anything else.
        msg = str(exc)
        if "[HTTP 404]" in msg or "HTTP 404" in msg:
            return
        raise
    emit_change(
        sys_token,
        collection,
        op="delete",
        key=key,
        before=None,
        after=None,
        user=user,
    )


# ---------- License-derived caps ----------------------------------------


def _password_path(name):
    return (
        "/servicesNS/nobody/{app}/storage/passwords/"
        "{realm}%3A{name}%3A?output_mode=json"
    ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)


def _load_license_blob(sys_token):
    try:
        resp, content = rest.simpleRequest(
            _password_path(LICENSE_SECRET_NAME),
            sessionKey=sys_token,
            method="GET",
        )
    except Exception as exc:
        msg = str(exc)
        if "[HTTP 404]" in msg or "HTTP 404" in msg:
            return None
        return None
    if getattr(resp, "status", 0) != 200:
        return None
    try:
        data = json.loads(content)
        entries = data.get("entry") or []
        if not entries:
            return None
        raw = (entries[0].get("content") or {}).get("clear_password") or ""
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _current_caps(sys_token):
    """Return the cap dict for the live license, factoring in expiry
    and node-lock mismatch."""
    blob = _load_license_blob(sys_token)
    license_key = (blob or {}).get("licenseKey") if isinstance(blob, dict) else None
    guid_state = get_environment_guid(sys_token)
    tier_state = resolve_tier(license_key, current_guid=guid_state["guid"])
    return caps_for(tier_state["effective_tier"]), tier_state


# ---------- field sanitisers --------------------------------------------


def _safe_short(raw):
    """Org / BU shorts: 1–4 chars, alnum + dash. Uppercase enforced."""
    s = "".join(c for c in (raw or "") if c.isalnum() or c == "-").upper()
    return s[:4]


def _safe_string(raw, max_len=256):
    s = (raw or "").strip()
    return s[:max_len]


def _safe_string_list(raw, max_items=64, max_item_len=128):
    if not isinstance(raw, list):
        return []
    out = []
    for v in raw[:max_items]:
        if isinstance(v, str):
            out.append(v.strip()[:max_item_len])
    return out


# ---------- audit config (v1.3.0) --------------------------------------


def _safe_index_name(raw):
    s = "".join(c for c in (raw or "") if c.isalnum() or c in "_-").strip()
    return s[:128]


def _index_exists(sys_token, name):
    try:
        resp, _ = rest.simpleRequest(
            "/services/data/indexes/%s?output_mode=json" % name,
            sessionKey=sys_token, method="GET",
        )
        return getattr(resp, "status", 0) == 200
    except Exception:
        return False  # 404 / error → treat as absent


def _org_has_proxy_config(sys_token, org_short):
    """True if the Org can run an `enforce` (splunk_proxy-only) turn —
    i.e. it has at least one splunk_proxy LLM config. DFLT always can
    (the built-in central Anthropic config is splunk_proxy)."""
    short = (org_short or "").upper()
    for c in _list_collection(sys_token, "itmip_llm_configs"):
        if (str(c.get("org_short") or "").upper() == short
                and str(c.get("call_mode") or "").lower() == "splunk_proxy"):
            return True
    return short == "DFLT"


def _validate_index_writable(sys_token, name, org_short):
    """Emit a typed `audit_config` bootstrap event (§9.3 step 2). Returns
    (ok, reason)."""
    cfg = {
        "audit_index": name, "audit_content_mode": "metadata_only",
        "audit_enforcement": "best_effort", "audit_dpia_ack": False,
        "audit_role_patterns": [],
    }
    res = emit_audit(
        sys_token, org_short, "DFLT", "system", [],
        "audit_config", {"op": "index_initialised"}, audit_cfg=cfg,
    )
    return bool(res.get("logged")), res.get("reason")


def _apply_audit_fields(sys_token, payload, doc, existing, is_create, short,
                        audit_enabled=True):
    """Validate + write the per-Org audit fields onto `doc`.

    Computes the EFFECTIVE config (existing row overlaid with payload) and
    enforces §9.3 invariants. Returns an error string, or None on success
    (mutating `doc` in place). Partial for update; full for create.
    `audit_enabled` is the license cap — v1.4.1 audit is an ENTERPRISE feature
    (`audit_logging`; moved from Professional).
    """
    has = lambda k: k in payload  # noqa: E731
    eff_idx = (_safe_index_name(payload.get("audit_index")) if has("audit_index")
               else _safe_index_name(existing.get("audit_index")))
    eff_mode = ((payload.get("audit_content_mode") if has("audit_content_mode")
                 else existing.get("audit_content_mode")) or "").lower()
    eff_enf = ((payload.get("audit_enforcement") if has("audit_enforcement")
                else existing.get("audit_enforcement")) or "best_effort").lower()
    eff_dpia = (bool(payload.get("audit_dpia_ack")) if has("audit_dpia_ack")
                else bool(existing.get("audit_dpia_ack")))

    # v1.3.0 — audit logging is a paid feature. Refuse ENABLING it (setting
    # an index / enforce) on a tier without the cap. Clearing it is allowed.
    # v1.4.1 — the cap moved to Enterprise (audit_logging).
    if not audit_enabled and has("audit_index") and eff_idx:
        return ("Audit logging requires an Enterprise license. "
                "Activate one in the License tab to configure auditing.")

    # v1.3.3 — NOTE on underscore-prefixed audit indexes (e.g. `_itmip_audit_X`):
    # they are admin-only-readable by default (ordinary roles lack `_*` in
    # srchIndexesAllowed), which is desirable for audit data. Splunk's
    # receivers/simple endpoint refuses `_*` indexes, so emit_audit() writes
    # those via `| collect` instead (the only writer that accepts internal
    # indexes). Both index styles are therefore valid — no block here.

    # Validate the index only when it is (re)supplied — avoids a slow REST
    # check on unrelated Org edits. A missing/un-writable index HARD-BLOCKS
    # only under `enforce` (which needs a working index or it would block
    # every LLM call). Under `best_effort` we ALLOW the save — otherwise an
    # admin can't record the intended index name before provisioning the
    # index (chicken-and-egg). Auditing just won't write until it exists.
    if has("audit_index") and eff_idx and eff_enf == "enforce":
        if not _index_exists(sys_token, eff_idx):
            return ("Audit index '%s' not found. Enforced auditing requires a "
                    "working index — create it first (Splunk Cloud: via ACS), "
                    "then save." % eff_idx)
        wok, reason = _validate_index_writable(sys_token, eff_idx, short)
        if not wok:
            return ("Audit index '%s' is not writable: %s. Enforced auditing "
                    "needs a writable index." % (eff_idx, reason or "unknown"))
    if eff_idx and eff_mode not in VALID_CONTENT_MODES:
        return ("Choose an audit content mode (metadata_only | prompt_hash | "
                "truncated_prompt | full_prompt) when an audit index is set.")
    if eff_mode == "full_prompt" and not eff_dpia:
        return ("Saving 'full_prompt' requires ticking the DPIA "
                "acknowledgement (audit_dpia_ack).")
    if eff_enf == "enforce":
        if not eff_idx:
            return "Enforced auditing requires an audit index."
        if not _org_has_proxy_config(sys_token, short):
            return ("Enforced auditing requires a splunk_proxy LLM connection "
                    "for this Org (browser_direct is disabled under enforce).")
    if eff_enf not in ("enforce", "best_effort"):
        eff_enf = "best_effort"

    if is_create or has("audit_index"):
        doc["audit_index"] = eff_idx
    if is_create or has("audit_content_mode"):
        doc["audit_content_mode"] = eff_mode
    if is_create or has("audit_enforcement"):
        doc["audit_enforcement"] = eff_enf
    if is_create or has("audit_dpia_ack"):
        doc["audit_dpia_ack"] = eff_dpia
    if has("audit_role_patterns") or is_create:
        doc["audit_role_patterns"] = _safe_string_list(payload.get("audit_role_patterns"))
    if has("audit_retention_note") or is_create:
        doc["audit_retention_note"] = _safe_string(payload.get("audit_retention_note"), 512)
    return None


# ---------- action handlers ---------------------------------------------


def _do_create_org(sys_token, payload, user="unknown"):
    caps, tier_state = _current_caps(sys_token)
    existing = _list_collection(sys_token, ORG_COLLECTION)
    if caps["max_orgs"] is not None and len(existing) >= caps["max_orgs"]:
        return err(
            403,
            "License '%s' allows up to %d Org(s); already have %d. Upgrade "
            "in the License tab to create more."
            % (tier_state["effective_tier"], caps["max_orgs"], len(existing)),
        )
    short = _safe_short(payload.get("short"))
    if not short:
        return err(400, "'short' is required (1-4 alphanumeric chars).")
    if any(o.get("short") == short for o in existing):
        return err(409, "An Org with short '%s' already exists." % short)
    now = int(time.time() * 1000)
    doc = {
        "_key": short,
        "short": short,
        "name": _safe_string(payload.get("name")) or short,
        "description": _safe_string(payload.get("description"), max_len=1024),
        "app_patterns": _safe_string_list(payload.get("app_patterns")),
        "role_patterns": _safe_string_list(payload.get("role_patterns")),
        "created_at": now,
        "updated_at": now,
    }
    audit_err = _apply_audit_fields(
        sys_token, payload, doc, {}, True, short,
        audit_enabled=bool(caps.get("audit_enabled")),
    )
    if audit_err:
        return err(400, audit_err)
    result = _create_in_collection(sys_token, ORG_COLLECTION, doc, user=user)
    return ok({"ok": True, "org": {**doc, "_key": result.get("_key", short)}})


def _do_update_org(sys_token, payload, user="unknown"):
    key = (payload.get("_key") or "").strip()
    if not key:
        return err(400, "'_key' is required.")
    existing = next(
        (o for o in _list_collection(sys_token, ORG_COLLECTION)
         if o.get("_key") == key or o.get("short") == key),
        {},
    )
    doc = {"updated_at": int(time.time() * 1000)}
    for field in ("name", "description"):
        if field in payload:
            doc[field] = _safe_string(
                payload[field], max_len=1024 if field == "description" else 256
            )
    for field in ("app_patterns", "role_patterns"):
        if field in payload:
            doc[field] = _safe_string_list(payload[field])
    caps, _ = _current_caps(sys_token)
    audit_err = _apply_audit_fields(
        sys_token, payload, doc, existing, False,
        str(existing.get("short") or key).upper(),
        audit_enabled=bool(caps.get("audit_enabled")),
    )
    if audit_err:
        return err(400, audit_err)
    # KVStore POST-to-_key REPLACES the whole record — a partial `doc` would
    # silently drop fields the editor doesn't resend (notably the immutable
    # `short`, plus `created_at`). Merge onto the existing row and pin the
    # identity (restoring it from the _key if a prior partial write already
    # blanked it — this self-heals such rows on the next save).
    merged = {**existing, **doc}
    merged.pop("_user", None)  # KVStore manages the owner; don't re-POST it
    merged["short"] = (str(existing.get("short") or key)).upper()
    _update_in_collection(sys_token, ORG_COLLECTION, key, merged, user=user)
    return ok({"ok": True})


def _do_delete_org(sys_token, payload, user="unknown"):
    key = (payload.get("_key") or "").strip()
    if not key:
        return err(400, "'_key' is required.")
    # Cascade-delete the BUs under this Org so we don't leave orphans.
    bus = _list_collection(sys_token, BU_COLLECTION)
    for bu in bus:
        if bu.get("org_short") == key:
            child_key = bu.get("_key") or "%s_%s" % (bu.get("org_short"), bu.get("short"))
            _delete_in_collection(sys_token, BU_COLLECTION, child_key, user=user)
    _delete_in_collection(sys_token, ORG_COLLECTION, key, user=user)
    return ok({"ok": True})


def _do_create_bu(sys_token, payload, user="unknown"):
    org_short = _safe_short(payload.get("org_short"))
    short = _safe_short(payload.get("short"))
    if not org_short or not short:
        return err(400, "'org_short' and 'short' are required.")
    caps, tier_state = _current_caps(sys_token)
    existing = _list_collection(sys_token, BU_COLLECTION)
    in_org = [b for b in existing if b.get("org_short") == org_short]
    if caps["max_bus_per_org"] is not None and len(in_org) >= caps["max_bus_per_org"]:
        return err(
            403,
            "License '%s' allows up to %d BU(s) per Org; '%s' already has %d. "
            "Upgrade in the License tab to create more."
            % (
                tier_state["effective_tier"],
                caps["max_bus_per_org"],
                org_short,
                len(in_org),
            ),
        )
    composite_key = "%s_%s" % (org_short, short)
    if any(b.get("_key") == composite_key for b in existing):
        return err(409, "A BU '%s' already exists." % composite_key)
    now = int(time.time() * 1000)
    doc = {
        "_key": composite_key,
        "org_short": org_short,
        "short": short,
        "name": _safe_string(payload.get("name")) or composite_key,
        "description": _safe_string(payload.get("description"), max_len=1024),
        "app_patterns": _safe_string_list(payload.get("app_patterns")),
        "extra_role_patterns": _safe_string_list(payload.get("extra_role_patterns")),
        "extra_user_names": _safe_string_list(payload.get("extra_user_names")),
        "created_at": now,
        "updated_at": now,
    }
    result = _create_in_collection(sys_token, BU_COLLECTION, doc, user=user)
    return ok({"ok": True, "bu": {**doc, "_key": result.get("_key", composite_key)}})


def _do_update_bu(sys_token, payload, user="unknown"):
    key = (payload.get("_key") or "").strip()
    if not key:
        return err(400, "'_key' is required.")
    existing = next(
        (b for b in _list_collection(sys_token, BU_COLLECTION)
         if b.get("_key") == key),
        {},
    )
    doc = {"updated_at": int(time.time() * 1000)}
    for field in ("name", "description"):
        if field in payload:
            doc[field] = _safe_string(
                payload[field], max_len=1024 if field == "description" else 256
            )
    for field in ("app_patterns", "extra_role_patterns", "extra_user_names"):
        if field in payload:
            doc[field] = _safe_string_list(payload[field])
    # KVStore POST-to-_key REPLACES the record — a partial `doc` would drop the
    # immutable identity fields (`short`, `org_short`) the editor doesn't
    # resend, breaking the BU's tenant linkage. Merge onto the existing row and
    # restore identity from the composite `_key` ("<ORG>_<BU>") if a prior
    # partial write already blanked it (self-heals on the next save).
    merged = {**existing, **doc}
    merged.pop("_user", None)  # KVStore manages the owner; don't re-POST it
    org_short = existing.get("org_short")
    bu_short = existing.get("short")
    if not org_short or not bu_short:
        org_part, _, bu_part = key.partition("_")
        org_short = org_short or org_part
        bu_short = bu_short or bu_part
    merged["org_short"] = str(org_short or "").upper()
    merged["short"] = str(bu_short or "").upper()
    _update_in_collection(sys_token, BU_COLLECTION, key, merged, user=user)
    return ok({"ok": True})


def _do_delete_bu(sys_token, payload, user="unknown"):
    key = (payload.get("_key") or "").strip()
    if not key:
        return err(400, "'_key' is required.")
    _delete_in_collection(sys_token, BU_COLLECTION, key, user=user)
    return ok({"ok": True})


ACTIONS = {
    "create_org": _do_create_org,
    "update_org": _do_update_org,
    "delete_org": _do_delete_org,
    "create_bu": _do_create_bu,
    "update_bu": _do_update_bu,
    "delete_bu": _do_delete_bu,
}


# ---------- handler ------------------------------------------------------


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
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")
            if not is_admin(args, rest):
                return err(403, "Admin role required.")

            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw) if payload_raw else {}
            except Exception:
                return err(400, "Invalid JSON payload.")

            action = (payload.get("action") or "").lower()
            fn = ACTIONS.get(action)
            if not fn:
                return err(
                    400,
                    "Unknown action '%s'. Expected one of: %s"
                    % (action, ", ".join(sorted(ACTIONS.keys()))),
                )
            return fn(sys_token, payload, user=user_name(args))
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
