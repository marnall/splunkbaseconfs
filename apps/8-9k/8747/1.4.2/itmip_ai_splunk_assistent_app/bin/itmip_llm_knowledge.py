"""Knowledge-layer REST handler (v1.0.0).

Dispatches on path_info to the LLM-facing tools and admin operations:

  LLM tools (any authenticated user):
    POST  /itmip_llm/knowledge/route        → splunk_route_knowledge
    POST  /itmip_llm/knowledge/search       → splunk_search_knowledge
    POST  /itmip_llm/knowledge/fetch        → splunk_get_knowledge_entry
    POST  /itmip_llm/knowledge/report       → splunk_report_knowledge_use

  Admin operations (admin / sc_admin only):
    GET   /itmip_llm/knowledge/connectors                     → list
    POST  /itmip_llm/knowledge/connectors                     → upsert
    DELETE /itmip_llm/knowledge/connectors?key=<k>            → delete
    POST  /itmip_llm/knowledge/connectors/refresh?key=<k>     → force probe
    POST  /itmip_llm/knowledge/connectors/test_routing        → debug pane

Reads sub-path from args["path_info"] — the prefix
`/itmip_llm/knowledge` is matched by restmap.conf.
"""

import json
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_BIN = os.path.dirname(os.path.abspath(__file__))
APP_LIB = os.path.join(APP_DIR, "lib")
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore  # noqa: E402
import splunk.rest as rest  # type: ignore  # noqa: E402

from itmip_llm_common import (  # noqa: E402
    err, is_admin, json_response, ok, system_token,
    user_name, user_token,
)
import itmip_knowledge_core as core  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# Tenant resolution (lightweight — full resolver is in
# itmip_llm_tenancy.py and could be wired in later if needed)
# ──────────────────────────────────────────────────────────────────────

def _resolve_tenant(args):
    """Best-effort tenancy. Reads org_short / bu_short from the request
    body if provided; defaults to DFLT/DFLT otherwise. The UI passes
    the resolved tenant via splunkContext on every call."""
    try:
        body = json.loads(args.get("payload") or "{}")
    except Exception:
        body = {}
    return {
        "splunk_user": user_name(args),
        "org_short": (body.get("org_short") or "DFLT").upper(),
        "bu_short": (body.get("bu_short") or "DFLT").upper(),
    }


def _parse_body(args):
    try:
        return json.loads(args.get("payload") or "{}")
    except Exception:
        return {}


def _path_tail(args):
    """Return the path suffix AFTER /itmip_llm/knowledge."""
    full = args.get("path_info") or ""
    # restmap match = /itmip_llm/knowledge; splunkd hands us either
    # the trailing portion or the full path depending on version.
    for prefix in (
        "/itmip_llm/knowledge",
        "itmip_llm/knowledge",
    ):
        if full.startswith(prefix):
            return full[len(prefix):].strip("/")
    return full.strip("/")


def _query_param(args, key):
    """Read a query-string parameter from the args.

    splunkd passes them as a list of [k, v] pairs under args["query"].
    """
    for pair in args.get("query") or []:
        if isinstance(pair, list) and len(pair) >= 2 and pair[0] == key:
            return pair[1]
    return None


# ──────────────────────────────────────────────────────────────────────
# LLM tool endpoints
# ──────────────────────────────────────────────────────────────────────

def _ep_route(args, sys_token, tenant):
    body = _parse_body(args)
    query = body.get("query") or ""
    intent = body.get("intent") or "general"
    filters = body.get("filters") or None
    drafted = body.get("drafted_spl_excerpt") or None
    if not query:
        return err(400, "Missing 'query'.")
    result = core.route_query(
        sys_token, query, intent,
        filters=filters, drafted_spl_excerpt=drafted,
        tenant_context=tenant,
    )
    core.emit_metric(sys_token, "ai_knowledge_route", {
        "shortlist_size": len(result.get("shortlist") or []),
        "skipped_count": len(result.get("skipped") or []),
        "intent": intent, "user": tenant.get("splunk_user"),
        "tenant_org": tenant.get("org_short"),
        "tenant_bu": tenant.get("bu_short"),
    })
    return ok({"ok": True, **result})


def _ep_search(args, sys_token, tenant):
    body = _parse_body(args)
    query = body.get("query") or ""
    filters = body.get("filters") or {}
    limit = int(body.get("limit") or 10)
    if limit > 25:
        limit = 25
    connectors = body.get("connectors")
    if not query:
        return err(400, "Missing 'query'.")
    was_routed = connectors is not None
    result = core.federated_search(
        sys_token, query, filters, limit, tenant,
        connectors=connectors, was_routed=was_routed,
    )
    return ok({"ok": True, **result})


def _ep_fetch(args, sys_token, tenant):
    body = _parse_body(args)
    connector = body.get("connector") or ""
    opaque_ref = body.get("opaque_ref") or ""
    if not connector or not opaque_ref:
        return err(400, "Missing 'connector' or 'opaque_ref'.")
    env = core.federated_fetch(sys_token, connector, opaque_ref, tenant)
    if env.get("error"):
        return ok({"ok": False, "entry": None, **env})
    return ok({"ok": True, "entry": env})


def _ep_report(args, sys_token, tenant):
    body = _parse_body(args)
    connector = body.get("connector") or ""
    source_id = body.get("source_id") or ""
    used = bool(body.get("used"))
    if not connector or not source_id:
        return err(400, "Missing 'connector' or 'source_id'.")
    core.emit_metric(sys_token, "ai_knowledge_static_rule_match", {
        "connector": connector, "source_id": source_id, "used": used,
        "user": tenant.get("splunk_user"),
        "tenant_org": tenant.get("org_short"),
        "tenant_bu": tenant.get("bu_short"),
    })
    return ok({"ok": True})


# ──────────────────────────────────────────────────────────────────────
# Admin endpoints
# ──────────────────────────────────────────────────────────────────────

def _ep_connectors_list(args, sys_token):
    # ensure_seeded() already ran at the top of handle(); no need to
    # repeat the registry seed here.
    rows = core.list_connectors(sys_token, tenant_context=None, status=None)
    # Don't echo the cached probe/describe blobs (large + can include
    # vendor metadata that's noisy). Send a stripped summary instead.
    summary = []
    for r in rows:
        probe = r.get("last_probe_result") or {}
        describe = r.get("last_describe_result") or {}
        summary.append({
            "_key": r.get("_key"),
            "name": r.get("name"),
            "title": r.get("title"),
            "short_description_concise": r.get("short_description_concise"),
            "kind": r.get("kind"),
            "flavour": r.get("flavour"),
            "status": r.get("status"),
            "org_short": r.get("org_short"),
            "bu_short": r.get("bu_short"),
            "weight": r.get("weight"),
            "priority": r.get("priority"),
            "routing_threshold": r.get("routing_threshold"),
            "is_slow_connector": r.get("is_slow_connector")
                                  or describe.get("is_slow_connector"),
            "dependent_apps": r.get("dependent_apps"),
            "last_probe_at": r.get("last_probe_at"),
            "last_probe_ok": bool(probe.get("available")),
            "last_probe_reason": probe.get("reason"),
            "last_probe_version": probe.get("version"),
            "last_describe_at": r.get("last_describe_at"),
            "kb_size_estimate": describe.get("kb_size_estimate"),
            "creator": r.get("creator"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "version": r.get("version"),
        })
    return ok({"items": summary})


def _ep_connectors_upsert(args, sys_token):
    body = _parse_body(args)
    if not body.get("name"):
        return err(400, "Missing 'name'.")
    # Admins can only edit a small set of fields safely. Everything
    # else (backing_source, kind, flavour, etc.) is preserved from
    # the existing row when one exists.
    user = user_name(args)
    existing = core.get_connector(sys_token, body["name"])
    if existing:
        editable = {
            k: body[k] for k in (
                "title", "short_description_concise", "status",
                "weight", "priority", "routing_threshold",
                "is_slow_connector",
                "probe_cache_ttl_sec", "probe_cooldown_sec_on_failure",
                "describe_cache_ttl_sec",
                "search_soft_deadline_ms", "search_hard_timeout_ms",
                "fetch_soft_deadline_ms", "fetch_hard_timeout_ms",
            ) if k in body
        }
        editable["name"] = body["name"]
        ok_, payload = core.upsert_connector(sys_token, editable, user)
    else:
        ok_, payload = core.upsert_connector(sys_token, body, user)
    if not ok_:
        return err(502, "Upsert failed: %s" % payload)
    return ok({"row": payload})


def _ep_connectors_delete(args, sys_token):
    key = _query_param(args, "key") or ""
    if not key:
        return err(400, "Missing 'key' query parameter.")
    existing = next(
        (r for r in core.list_connectors(sys_token, tenant_context=None,
                                         status=None)
         if r.get("_key") == key),
        None,
    )
    if existing is None:
        return err(404, "Not found.")
    if existing.get("creator") == "system":
        return err(403, "Built-in connector cannot be deleted.")
    ok_, msg = core.delete_connector(sys_token, key)
    if not ok_:
        return err(502, "Delete failed: %s" % msg)
    return ok({"deleted": key})


def _ep_connectors_refresh(args, sys_token):
    key = _query_param(args, "key") or ""
    rows = core.list_connectors(sys_token, tenant_context=None, status=None)
    targets = [r for r in rows if (not key) or r.get("_key") == key]
    if key and not targets:
        return err(404, "Not found.")
    results = []
    for r in targets:
        probe, describe = core.refresh_probe_describe(
            sys_token, r, force=True
        )
        results.append({
            "name": r.get("name"),
            "available": bool(probe.get("available")),
            "reason": probe.get("reason"),
            "version": probe.get("version"),
            "described": describe is not None,
        })
    return ok({"refreshed": results})


def _ep_connectors_test_routing(args, sys_token):
    body = _parse_body(args)
    query = body.get("query") or ""
    intent = body.get("intent") or "general"
    filters = body.get("filters") or None
    drafted = body.get("drafted_spl_excerpt") or None
    if not query:
        return err(400, "Missing 'query'.")
    result = core.route_query(
        sys_token, query, intent,
        filters=filters, drafted_spl_excerpt=drafted,
        # Admin debug pane: no tenant filter — see everything.
        tenant_context=None,
    )
    return ok({"ok": True, "intent": intent, **result})


# ──────────────────────────────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────────────────────────────

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

            tail = _path_tail(args)
            tenant = _resolve_tenant(args)

            # Lazy seed pass on first request per process. Idempotent
            # and best-effort — failures don't block the call.
            core.ensure_seeded(sys_token)

            # LLM tool endpoints — any authenticated user
            if tail == "route" and method == "POST":
                return _ep_route(args, sys_token, tenant)
            if tail == "search" and method == "POST":
                return _ep_search(args, sys_token, tenant)
            if tail == "fetch" and method == "POST":
                return _ep_fetch(args, sys_token, tenant)
            if tail == "report" and method == "POST":
                return _ep_report(args, sys_token, tenant)

            # Admin endpoints — gate on role
            if tail.startswith("connectors"):
                if not is_admin(args, rest):
                    return err(403, "Admin role required.")
                if tail == "connectors":
                    if method == "GET":
                        return _ep_connectors_list(args, sys_token)
                    if method == "POST":
                        return _ep_connectors_upsert(args, sys_token)
                    if method == "DELETE":
                        return _ep_connectors_delete(args, sys_token)
                    return err(405, "Method not allowed.")
                if tail == "connectors/refresh" and method == "POST":
                    return _ep_connectors_refresh(args, sys_token)
                if tail == "connectors/test_routing" and method == "POST":
                    return _ep_connectors_test_routing(args, sys_token)

            return err(404, "Unknown sub-path: '%s'" % tail)
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
