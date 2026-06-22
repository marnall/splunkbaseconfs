"""Knowledge-layer core: registry, router, federation, injection scanner.

This module is the runtime engine behind the four knowledge tools
(splunk_route_knowledge, splunk_search_knowledge,
splunk_get_knowledge_entry, splunk_report_knowledge_use). It is not a
REST handler itself — the handler in itmip_llm_knowledge.py imports
these functions.

Layout:
  - Registry I/O           (seed_registry, list_connectors, get_connector,
                            upsert_connector, delete_connector)
  - Probe / describe cache (refresh_probe_describe, _cached_describe)
  - Router                 (route_query)
  - Federation             (federated_search, federated_fetch)
  - Injection scanner      (scan_text_for_injection, apply_injection_scan)
  - Telemetry              (emit_metric)

For the design, see instructions/KNOWLEDGE_LAYER_IMPLEMENTATION_PLAN.md
§§ 5, 8.1, 9, 10, 22, 24.
"""

import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.parse

APP_BIN = os.path.dirname(os.path.abspath(__file__))
if APP_BIN not in sys.path:
    sys.path.insert(0, APP_BIN)

import splunk.rest as rest  # type: ignore  # noqa: E402

from itmip_llm_common import APP_NAME  # noqa: E402

import knowledge_connectors  # noqa: E402
import knowledge_seeds  # noqa: E402

REGISTRY_COLLECTION = "itmip_knowledge_connectors"
RULES_COLLECTION = "itmip_knowledge_static_rules"
ENTRIES_COLLECTION = "itmip_ai_knowledge_entries"
# v1.4.0 — live-platform-knowledge Tier B/Tier 1 overlays.
COMMAND_NOTES_COLLECTION = "itmip_command_notes"
VIZ_KNOWLEDGE_COLLECTION = "itmip_viz_knowledge"

# JSON-encoded fields on rules + entries (stored as strings in KVStore).
_RULE_JSON_FIELDS = (
    "trigger_pattern", "intent_kinds", "mitre_techniques",
    "data_sources", "data_models", "references", "tags",
    "injection_flags",
)
_ENTRY_JSON_FIELDS = (
    "mitre_techniques", "mitre_tactics", "kill_chain_phases",
    "data_sources", "data_models", "related_entries",
    "related_templates", "references", "tags", "trigger_pattern",
    "raw", "injection_flags",
)
# v1.4.0 overlay JSON fields (lists/objects stored as strings in KVStore).
_COMMAND_NOTE_JSON_FIELDS = (
    "good_for", "common_mistakes", "gotchas", "tags",
)
_VIZ_KNOWLEDGE_JSON_FIELDS = (
    "overlay", "data_contract", "declared_properties", "xml_emission", "tags",
)

# Federation defaults (also persisted per-connector in the registry).
DEFAULT_PROBE_CACHE_TTL_SEC = 300
DEFAULT_PROBE_COOLDOWN_SEC_ON_FAILURE = 3600
DEFAULT_DESCRIBE_CACHE_TTL_SEC = 300
DEFAULT_SEARCH_SOFT_DEADLINE_MS = 1500
DEFAULT_SEARCH_HARD_TIMEOUT_MS = 3000
DEFAULT_FETCH_SOFT_DEADLINE_MS = 1500
DEFAULT_FETCH_HARD_TIMEOUT_MS = 3000
DEFAULT_ROUTING_THRESHOLD = 0.3

# Security-flavoured intents — see plan §9.5: local-curated is always
# considered above threshold for these.
SECURITY_INTENTS = {
    "soc-investigation", "detection-engineering",
    "incident-response", "threat-hunting",
}

# Recognised intents — plan §9.3 + KNOWLEDGE_CONNECTOR_CONTRACT.md §4.
KNOWN_INTENTS = SECURITY_INTENTS | {
    "spl-authoring", "dashboard-authoring", "data-onboarding",
    "service-management", "troubleshooting", "general",
}

# Telemetry index used by emit_metric.
TELEMETRY_INDEX = "main"
TELEMETRY_SOURCETYPE = "ai_knowledge_metrics"
TELEMETRY_SOURCE = "itmip_knowledge"


# ──────────────────────────────────────────────────────────────────────
# Generic KVStore helpers
# ──────────────────────────────────────────────────────────────────────

def _http_get(session_key, url):
    try:
        resp, content = rest.simpleRequest(
            url, sessionKey=session_key, method="GET"
        )
        status = getattr(resp, "status", 0)
        body = content if isinstance(content, str) else (
            content.decode("utf-8", "replace") if content else ""
        )
        return status, body
    except Exception as exc:
        msg = str(exc)
        m = re.search(r"\[HTTP\s+(\d+)\]", msg)
        if m:
            return int(m.group(1)), msg
        return 0, msg


def _http_post_json(session_key, url, body):
    try:
        resp, content = rest.simpleRequest(
            url,
            sessionKey=session_key,
            method="POST",
            jsonargs=json.dumps(body),
        )
        return getattr(resp, "status", 0), content
    except Exception as exc:
        msg = str(exc)
        m = re.search(r"\[HTTP\s+(\d+)\]", msg)
        if m:
            return int(m.group(1)), msg
        return 0, msg


def _coll_url(coll, suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{suffix}"
    ).format(app=APP_NAME, coll=coll, suffix=suffix)


def _coll_config_url(coll):
    return (
        "/servicesNS/nobody/{app}/storage/collections/config/{coll}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=coll)


# ──────────────────────────────────────────────────────────────────────
# Registry I/O
# ──────────────────────────────────────────────────────────────────────

# Fields stored as JSON strings on disk (KVStore enforceTypes off).
_REGISTRY_JSON_FIELDS = (
    "backing_source", "last_probe_result", "last_describe_result",
    "default_kinds", "dependent_apps",
)


def _encode_registry_row(row):
    """Encode JSON-typed fields as strings for KVStore write."""
    out = dict(row)
    for f in _REGISTRY_JSON_FIELDS:
        if f in out and not isinstance(out[f], str):
            out[f] = json.dumps(out[f])
    return out


def _decode_registry_row(row):
    """Decode JSON-string fields back to native Python."""
    out = dict(row)
    for f in _REGISTRY_JSON_FIELDS:
        raw = out.get(f)
        if isinstance(raw, str) and raw:
            try:
                out[f] = json.loads(raw)
            except Exception:
                out[f] = None
    return out


def list_connectors(session_key, tenant_context=None, status=None):
    """Return decoded registry rows visible to the caller.

    Args:
      tenant_context: {"org_short", "bu_short", "splunk_user"} or None.
                      None means "no tenancy filter" (admin views).
      status:         optional filter, e.g. "operational".
    """
    status_, body = _http_get(session_key, _coll_url(
        REGISTRY_COLLECTION, "?output_mode=json"
    ))
    if status_ == 404:
        return []
    if status_ != 200:
        return []
    try:
        rows = json.loads(body)
    except Exception:
        return []
    if not isinstance(rows, list):
        return []

    decoded = [_decode_registry_row(r) for r in rows]
    if status:
        decoded = [r for r in decoded if (r.get("status") or "") == status]
    if tenant_context is not None:
        org = (tenant_context or {}).get("org_short") or "DFLT"
        bu = (tenant_context or {}).get("bu_short") or "DFLT"
        out = []
        for r in decoded:
            r_org = r.get("org_short") or "DFLT"
            r_bu = r.get("bu_short") or "DFLT"
            if (r_org, r_bu) == ("DFLT", "DFLT") or (r_org == org and r_bu == bu):
                out.append(r)
        decoded = out
    return decoded


def get_connector(session_key, name):
    """Find one registry row by `name`. None if not found."""
    for r in list_connectors(session_key, tenant_context=None, status=None):
        if r.get("name") == name:
            return r
    return None


def upsert_connector(session_key, row, user):
    """Insert or update a registry row. Returns (ok, row_or_error)."""
    now = int(time.time())
    existing = get_connector(session_key, row.get("name") or "")
    if existing:
        new = dict(existing)
        new.update(row)
        new["updated_at"] = now
        new["updated_by"] = user
        new["version"] = int(existing.get("version") or 1) + 1
        url = _coll_url(REGISTRY_COLLECTION, "/" + existing["_key"])
        status, body = _http_post_json(
            session_key, url, _encode_registry_row(new)
        )
        if status not in (200, 201):
            return False, "upsert failed (%s): %s" % (status, body[:200])
        return True, new
    else:
        new = dict(row)
        new.setdefault("creator", user)
        new.setdefault("status", "operational")
        new["created_at"] = now
        new["updated_at"] = now
        new["updated_by"] = user
        new["version"] = 1
        url = _coll_url(REGISTRY_COLLECTION)
        status, body = _http_post_json(
            session_key, url, _encode_registry_row(new)
        )
        if status not in (200, 201):
            return False, "insert failed (%s): %s" % (status, body[:200])
        try:
            data = json.loads(body) if isinstance(body, str) else body
            new["_key"] = (data or {}).get("_key") or new.get("_key")
        except Exception:
            pass
        return True, new


def delete_connector(session_key, key):
    """Delete a registry row by _key. Returns (ok, message)."""
    url = _coll_url(REGISTRY_COLLECTION, "/" + urllib.parse.quote(key))
    try:
        resp, _ = rest.simpleRequest(
            url, sessionKey=session_key, method="DELETE"
        )
        if getattr(resp, "status", 0) in (200, 204):
            return True, "deleted"
        return False, "status %s" % resp.status
    except Exception as exc:
        return False, str(exc)


def seed_registry(session_key):
    """Upsert OOTB built-in connector rows.

    Admin edits to existing rows survive — we only re-seed rows where
    version==1 and creator=='system' (matching the templates/skills
    pattern). Brand-new built-ins (e.g. ESCU when it lands in Phase 2)
    are inserted as new rows.
    """
    existing_by_name = {r.get("name"): r for r in list_connectors(
        session_key, tenant_context=None, status=None
    )}
    # Drop leftover system-owned rows for connectors that have been
    # retired (e.g. sse-bridge in v1.2.0). Admin-owned rows are left
    # alone — an admin who deliberately re-created one keeps it.
    for retired in getattr(knowledge_connectors, "RETIRED_CONNECTOR_NAMES", []):
        cur = existing_by_name.get(retired)
        if cur and cur.get("creator") == "system" and cur.get("_key"):
            delete_connector(session_key, cur["_key"])
            existing_by_name.pop(retired, None)
    for spec in knowledge_connectors.builtin_registry_specs():
        name = spec.get("name")
        if not name:
            continue
        cur = existing_by_name.get(name)
        if cur is None:
            # New built-in — insert with system metadata.
            row = dict(spec)
            row["creator"] = "system"
            upsert_connector(session_key, row, user="system")
        elif int(cur.get("version") or 1) == 1 and cur.get("creator") == "system":
            # Re-seed-eligible — refresh metadata while preserving _key
            # and any admin-tunable fields the admin may have left
            # at defaults. We only refresh the descriptive bits
            # (title, short_description_concise, default knobs not
            # touched by admin), not weight/priority/routing_threshold
            # which admins commonly tune.
            row = dict(spec)
            row["_key"] = cur.get("_key")
            for k in ("weight", "priority", "routing_threshold", "status"):
                if k in cur:
                    row[k] = cur[k]
            row["creator"] = "system"
            upsert_connector(session_key, row, user="system")


# ──────────────────────────────────────────────────────────────────────
# Content seeding — static rules + curated entries
# ──────────────────────────────────────────────────────────────────────

def _encode_seed_row(seed, json_fields):
    """JSON-encode any list/dict fields per the collection schema."""
    out = dict(seed)
    for f in json_fields:
        if f in out and not isinstance(out[f], str):
            out[f] = json.dumps(out[f])
    return out


def _seed_collection(session_key, coll, seeds, json_fields, name_field="name"):
    """Generic seed-upsert. Re-seed-eligible rows: creator='system' AND
    version==1. Admin edits survive."""
    # Read all existing rows.
    status, body = _http_get(session_key, _coll_url(
        coll, "?output_mode=json"
    ))
    if status == 404:
        existing_rows = []
    elif status != 200:
        return
    else:
        try:
            existing_rows = json.loads(body) or []
        except Exception:
            existing_rows = []
    by_name = {r.get(name_field): r for r in existing_rows}

    now = int(time.time())
    for seed in seeds:
        name = seed.get(name_field)
        if not name:
            continue
        cur = by_name.get(name)
        encoded = _encode_seed_row(seed, json_fields)
        if cur is None:
            row = dict(encoded)
            row.setdefault("status", "operational")
            row.setdefault("creator", "system")
            row["created_at"] = now
            row["updated_at"] = now
            row["updated_by"] = "system"
            row["version"] = 1
            row.setdefault("org_short", "DFLT")
            row.setdefault("bu_short", "DFLT")
            _http_post_json(session_key, _coll_url(coll), row)
        elif (cur.get("creator") == "system"
              and int(cur.get("version") or 1) == 1):
            row = dict(encoded)
            row["_key"] = cur.get("_key")
            row["creator"] = "system"
            row["status"] = cur.get("status") or "operational"
            row["created_at"] = cur.get("created_at") or now
            row["updated_at"] = now
            row["updated_by"] = "system"
            row["version"] = 1
            row.setdefault("org_short", cur.get("org_short") or "DFLT")
            row.setdefault("bu_short", cur.get("bu_short") or "DFLT")
            _http_post_json(
                session_key,
                _coll_url(coll, "/" + cur["_key"]),
                row,
            )


def seed_static_rules(session_key):
    _seed_collection(
        session_key, RULES_COLLECTION,
        knowledge_seeds.STATIC_RULE_SEEDS, _RULE_JSON_FIELDS,
    )


def seed_curated_entries(session_key):
    _seed_collection(
        session_key, ENTRIES_COLLECTION,
        knowledge_seeds.CURATED_ENTRY_SEEDS, _ENTRY_JSON_FIELDS,
    )


def seed_command_notes(session_key):
    _seed_collection(
        session_key, COMMAND_NOTES_COLLECTION,
        getattr(knowledge_seeds, "COMMAND_NOTE_SEEDS", []),
        _COMMAND_NOTE_JSON_FIELDS,
    )


def seed_viz_knowledge(session_key):
    _seed_collection(
        session_key, VIZ_KNOWLEDGE_COLLECTION,
        getattr(knowledge_seeds, "VIZ_KNOWLEDGE_SEEDS", []),
        _VIZ_KNOWLEDGE_JSON_FIELDS,
    )


# Module-level flag to avoid re-running seed passes on every REST call.
# Reset on app reload; the seeders are idempotent anyway, so this is a
# pure performance optimisation, not a correctness requirement.
_SEEDED_ALL = False


def ensure_seeded(session_key):
    """Best-effort lazy seed pass — registry + rules + curated entries.

    Called once per process from the REST handler on first request.
    Idempotent and best-effort: failures are silently absorbed so a
    seed bug never breaks a live federation call.
    """
    global _SEEDED_ALL
    if _SEEDED_ALL:
        return
    try:
        seed_registry(session_key)
    except Exception:
        pass
    try:
        seed_static_rules(session_key)
    except Exception:
        pass
    try:
        seed_curated_entries(session_key)
    except Exception:
        pass
    try:
        seed_command_notes(session_key)
    except Exception:
        pass
    try:
        seed_viz_knowledge(session_key)
    except Exception:
        pass
    _SEEDED_ALL = True


# ──────────────────────────────────────────────────────────────────────
# Connector module resolution + probe/describe cache
# ──────────────────────────────────────────────────────────────────────

def _get_module_for_row(row):
    """Return the Python connector module for a registry row, or None.

    Looks up by backing_source.module_name. Returns None for kinds we
    don't know how to invoke (custom-http / mcp ship in Phase 3/4).
    """
    bs = row.get("backing_source") or {}
    if not isinstance(bs, dict):
        return None
    mod_name = bs.get("module_name")
    if not mod_name:
        return None
    for n, mod in knowledge_connectors.discover():
        if n == mod_name:
            return mod
    return None


def _now():
    return int(time.time())


def refresh_probe_describe(session_key, row, force=False):
    """Refresh the connector's probe + describe cache on the registry row.

    Respects TTLs: probe_cache_ttl_sec on success, longer cooldown on
    failure. Returns (probe_result, describe_result_or_None).
    """
    mod = _get_module_for_row(row)
    if mod is None:
        return ({"available": False, "version": None,
                 "reason": "no module for kind=%s flavour=%s" % (
                     row.get("kind"), row.get("flavour"),
                 )}, None)

    bs = row.get("backing_source") or {}
    probe_ttl = int(row.get("probe_cache_ttl_sec") or DEFAULT_PROBE_CACHE_TTL_SEC)
    fail_cool = int(row.get("probe_cooldown_sec_on_failure")
                    or DEFAULT_PROBE_COOLDOWN_SEC_ON_FAILURE)
    describe_ttl = int(row.get("describe_cache_ttl_sec")
                       or DEFAULT_DESCRIBE_CACHE_TTL_SEC)

    now = _now()
    last_probe_at = int(row.get("last_probe_at") or 0)
    last_probe_result = row.get("last_probe_result") or {}
    last_describe_at = int(row.get("last_describe_at") or 0)
    last_describe_result = row.get("last_describe_result")

    probe_fresh = False
    if not force and last_probe_at:
        age = now - last_probe_at
        if last_probe_result.get("available"):
            probe_fresh = age < probe_ttl
        else:
            probe_fresh = age < fail_cool

    if probe_fresh:
        probe_result = last_probe_result
    else:
        try:
            probe_result = mod.probe(session_key, backing_source=bs)
        except Exception as exc:
            probe_result = {"available": False, "version": None,
                            "reason": "probe exception: %s" % exc}
        row["last_probe_at"] = now
        row["last_probe_result"] = probe_result

    describe_result = last_describe_result if (
        not force and last_describe_at and (now - last_describe_at) < describe_ttl
        and probe_result.get("available")
    ) else None

    if describe_result is None and probe_result.get("available"):
        try:
            describe_result = mod.describe(session_key, backing_source=bs)
        except Exception as exc:
            describe_result = None
            emit_metric(session_key, "ai_knowledge_describe", {
                "connector": row.get("name"), "ok": False,
                "error_reason": "describe exception: %s" % exc,
            })
        else:
            emit_metric(session_key, "ai_knowledge_describe", {
                "connector": row.get("name"), "ok": True,
            })
        row["last_describe_at"] = now
        row["last_describe_result"] = describe_result

    # Persist cache fields back to the registry. Best-effort — if it
    # fails the in-memory `row` is still good for this call.
    if not probe_fresh or describe_result is not None:
        try:
            url = _coll_url(REGISTRY_COLLECTION, "/" + row["_key"])
            _http_post_json(session_key, url, _encode_registry_row(row))
        except Exception:
            pass

    emit_metric(session_key, "ai_knowledge_probe", {
        "connector": row.get("name"),
        "ok": bool(probe_result.get("available")),
        "version": probe_result.get("version"),
        "reason": probe_result.get("reason"),
    })

    return probe_result, describe_result


def _dependent_apps_satisfied(session_key, row):
    deps = row.get("dependent_apps") or []
    if not isinstance(deps, list) or not deps:
        return True
    for d in deps:
        name = d.get("name") if isinstance(d, dict) else None
        if not name:
            continue
        url = (
            "/services/apps/local/{app}?output_mode=json"
        ).format(app=name)
        status, _ = _http_get(session_key, url)
        if status != 200:
            return False
    return True


# ──────────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────────

def _topic_overlap(query, keywords):
    if not query or not keywords:
        return 0.0
    q = query.lower()
    hits = 0
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in q:
            hits += 1
    return min(1.0, hits / max(len(keywords), 1) * 4)  # weight hits ~4x


def _antitopic_overlap(query, anti):
    if not query or not anti:
        return 0.0
    q = query.lower()
    return min(1.0, sum(1 for a in anti if a and a.lower() in q) / max(len(anti), 1) * 4)


def _intent_match(intent, intent_kinds):
    if not intent or not intent_kinds:
        return 0.0
    return 1.0 if intent in intent_kinds else 0.0


def _facet_match(filters, facets):
    if not facets:
        return 0.0
    if not filters:
        return 0.5
    supported = {k for k, v in facets.items() if v == "supported"}
    asked = set(filters.keys())
    if not asked:
        return 0.5
    overlap = asked & supported
    return len(overlap) / max(len(asked), 1)


def _spl_pattern_match(spl_excerpt, describe):
    # Reserved hook — describe() could expose SPL idioms in the future.
    # For Phase 1 this stays 0.0.
    return 0.0


def route_query(session_key, query, intent, filters=None,
                drafted_spl_excerpt=None, tenant_context=None):
    """Implement the router scoring formula (plan §9.5).

    Returns:
      {"shortlist": [...], "skipped": [...]}
    """
    intent = intent if intent in KNOWN_INTENTS else "general"
    candidates = list_connectors(
        session_key, tenant_context=tenant_context, status="operational"
    )
    shortlist = []
    skipped = []

    for row in candidates:
        if not _dependent_apps_satisfied(session_key, row):
            skipped.append({
                "connector": row.get("name"),
                "reason": "dependent apps not installed",
            })
            continue

        probe, describe = refresh_probe_describe(session_key, row)
        if not probe.get("available"):
            skipped.append({
                "connector": row.get("name"),
                "reason": "probe failed: %s" % (probe.get("reason") or "unknown"),
            })
            continue
        if not describe:
            skipped.append({
                "connector": row.get("name"),
                "reason": "describe missing",
            })
            continue

        hints = describe.get("routing_hints") or {}
        facets = describe.get("facets") or {}

        topic = _topic_overlap(query, hints.get("topic_keywords") or [])
        intent_s = _intent_match(intent, hints.get("intent_kinds") or [])
        facet_s = _facet_match(filters, facets)
        spl_s = _spl_pattern_match(drafted_spl_excerpt, describe)
        baseline = 1.0
        anti = _antitopic_overlap(query, hints.get("antitopic_keywords") or [])

        score = (
            0.50 * topic
            + 0.15 * intent_s
            + 0.15 * facet_s
            + 0.10 * spl_s
            + 0.10 * baseline
            - 0.30 * anti
        )

        is_slow = bool(describe.get("is_slow_connector"))
        if is_slow:
            score = score * 0.8 - 0.10

        # Apply admin-tunable weight as a soft adjustment.
        weight = float(row.get("weight") or 1.0)
        score = score * weight

        threshold = float(row.get("routing_threshold")
                          or DEFAULT_ROUTING_THRESHOLD)

        # local-curated is always-include for security intents
        # (plan §9.5 last paragraph).
        always_pass = (
            row.get("flavour") == "local-curated"
            and intent in SECURITY_INTENTS
        )

        why_bits = []
        if topic > 0:
            why_bits.append("topic match %.2f" % topic)
        if intent_s > 0:
            why_bits.append("intent_kind '%s' matches" % intent)
        if facet_s > 0.5:
            why_bits.append("facet match %.2f" % facet_s)
        if anti > 0:
            why_bits.append("antitopic penalty %.2f" % anti)
        if is_slow:
            why_bits.append("slow-connector penalty applied")
        if weight != 1.0:
            why_bits.append("admin weight %.2f" % weight)
        if always_pass:
            why_bits.append("always-included for security intent")
        why = "; ".join(why_bits) or "baseline"

        if score >= threshold or always_pass:
            shortlist.append({
                "connector": row.get("name"),
                "score": round(max(0.0, score), 3),
                "why": why,
            })
        else:
            skipped.append({
                "connector": row.get("name"),
                "reason": (
                    "below routing_threshold (%.2f < %.2f); %s"
                    % (score, threshold, why)
                ),
            })

    shortlist.sort(key=lambda c: -c["score"])
    return {"shortlist": shortlist, "skipped": skipped}


# ──────────────────────────────────────────────────────────────────────
# Federation — search + fetch
# ──────────────────────────────────────────────────────────────────────

def _do_search_one(session_key, row, query, filters, limit, tenant_context):
    mod = _get_module_for_row(row)
    if mod is None:
        return row.get("name"), None, "no module"
    start = time.time()
    try:
        result = mod.search(
            session_key, query, filters, limit, tenant_context,
            backing_source=row.get("backing_source") or {},
        )
    except Exception as exc:
        return row.get("name"), None, "exception: %s" % exc
    elapsed_ms = int((time.time() - start) * 1000)
    return row.get("name"), (result, elapsed_ms), None


def federated_search(session_key, query, filters, limit, tenant_context,
                     connectors=None, was_routed=False):
    """Fan out search() to the shortlisted connectors.

    If `connectors` is None, fall back to fast (non-slow) connectors —
    safe default per plan §9.7.
    """
    filters = filters or {}
    all_connectors = list_connectors(
        session_key, tenant_context=tenant_context, status="operational"
    )
    if connectors is not None:
        wanted = {c for c in connectors if isinstance(c, str)}
        targeted = [r for r in all_connectors if r.get("name") in wanted]
        if not targeted:
            # Bad shortlist — fall back to fast connectors only.
            targeted = [r for r in all_connectors
                        if not _row_is_slow(session_key, r)]
            was_routed = False
    else:
        targeted = [r for r in all_connectors
                    if not _row_is_slow(session_key, r)]

    # Filter on dependent_apps + probe availability.
    runnable = []
    for r in targeted:
        if not _dependent_apps_satisfied(session_key, r):
            continue
        probe, _describe = refresh_probe_describe(session_key, r)
        if probe.get("available"):
            runnable.append(r)

    soft_deadline_ms = max(
        int(r.get("search_soft_deadline_ms") or DEFAULT_SEARCH_SOFT_DEADLINE_MS)
        for r in runnable
    ) if runnable else DEFAULT_SEARCH_SOFT_DEADLINE_MS
    hard_timeout_ms = max(
        int(r.get("search_hard_timeout_ms") or DEFAULT_SEARCH_HARD_TIMEOUT_MS)
        for r in runnable
    ) if runnable else DEFAULT_SEARCH_HARD_TIMEOUT_MS

    timeouts = []
    errors = []
    merged = []

    if runnable:
        per_connector_limit = max(int(limit or 10), 5)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(len(runnable), 1)
        ) as ex:
            futures = {
                ex.submit(
                    _do_search_one,
                    session_key, r, query, filters,
                    per_connector_limit, tenant_context,
                ): r for r in runnable
            }
            try:
                for fut in concurrent.futures.as_completed(
                    futures, timeout=hard_timeout_ms / 1000.0
                ):
                    r = futures[fut]
                    try:
                        name, payload, err = fut.result(timeout=0.1)
                    except Exception as exc:
                        errors.append({
                            "connector": r.get("name"),
                            "error": "future exception: %s" % exc,
                        })
                        continue
                    if err:
                        errors.append({"connector": name, "error": err})
                        emit_metric(session_key, "ai_knowledge_search", {
                            "connector": name, "ok": False, "error_reason": err,
                            "was_routed": was_routed,
                        })
                        continue
                    result, elapsed_ms = payload
                    candidates = (result or {}).get("candidates") or []
                    warnings_inner = (result or {}).get("warnings") or []
                    weight = float(r.get("weight") or 1.0)
                    priority = int(r.get("priority") or 50)
                    for c in candidates:
                        c = dict(c)
                        c["connector"] = name
                        c["score"] = float(c.get("score") or 0.0) * weight
                        c["_priority"] = priority
                        merged.append(c)
                    for w in warnings_inner:
                        errors.append({"connector": name,
                                       "warning": str(w)})
                    emit_metric(session_key, "ai_knowledge_search", {
                        "connector": name, "ok": True,
                        "candidate_count": len(candidates),
                        "latency_ms": elapsed_ms,
                        "was_routed": was_routed,
                    })
            except concurrent.futures.TimeoutError:
                for fut, r in futures.items():
                    if not fut.done():
                        timeouts.append(r.get("name"))
                        fut.cancel()
                        emit_metric(session_key, "ai_knowledge_timeout", {
                            "connector": r.get("name"), "op": "search",
                        })

    # Dedup within connector by source_id
    seen = set()
    deduped = []
    for c in merged:
        key = (c.get("connector"), c.get("source_id"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    deduped.sort(key=lambda c: (
        -float(c.get("score") or 0.0),
        -int(c.get("_priority") or 50),
        str(c.get("connector") or ""),
    ))
    top = deduped[: max(int(limit or 10), 1)]
    for c in top:
        c.pop("_priority", None)

    warnings = []
    if timeouts:
        warnings.append("connectors timed out: " + ", ".join(timeouts))
    for e in errors:
        if "warning" in e:
            warnings.append("%s warning: %s" % (e["connector"], e["warning"]))
        else:
            warnings.append("%s error: %s" % (e["connector"], e.get("error")))

    return {
        "candidates": top,
        "warnings": warnings,
        "metadata": {
            "connectors_queried": [r.get("name") for r in runnable],
            "connectors_timed_out": timeouts,
            "connectors_errored": [e["connector"] for e in errors
                                   if "error" in e],
            "was_routed": was_routed,
            "result_count": len(top),
            "total_candidates_before_trim": len(deduped),
        },
    }


def _row_is_slow(session_key, row):
    """A connector is slow if either the registry row marks it so OR
    the cached describe() says so."""
    if bool(row.get("is_slow_connector")):
        return True
    cached = row.get("last_describe_result") or {}
    return bool(cached.get("is_slow_connector"))


def federated_fetch(session_key, connector, opaque_ref, tenant_context):
    """Fetch one entry. Returns envelope or {"error": ...}."""
    row = get_connector(session_key, connector)
    if row is None:
        return {"error": "unknown_connector", "connector": connector}
    if not _dependent_apps_satisfied(session_key, row):
        return {"error": "dependent_apps_missing", "connector": connector}
    mod = _get_module_for_row(row)
    if mod is None:
        return {"error": "no_module", "connector": connector}
    hard_timeout_s = int(row.get("fetch_hard_timeout_ms")
                         or DEFAULT_FETCH_HARD_TIMEOUT_MS) / 1000.0
    start = time.time()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(
                mod.fetch, session_key, opaque_ref, tenant_context,
                row.get("backing_source") or {},
            )
            try:
                env = fut.result(timeout=hard_timeout_s)
            except concurrent.futures.TimeoutError:
                emit_metric(session_key, "ai_knowledge_timeout", {
                    "connector": connector, "op": "fetch",
                })
                return {"error": "timeout", "connector": connector,
                        "opaque_ref": opaque_ref}
    except Exception as exc:
        return {"error": "exception", "connector": connector,
                "opaque_ref": opaque_ref, "detail": str(exc)}
    elapsed_ms = int((time.time() - start) * 1000)
    if not isinstance(env, dict):
        return {"error": "malformed_response", "connector": connector}
    if env.get("error"):
        emit_metric(session_key, "ai_knowledge_fetch", {
            "connector": connector, "ok": False,
            "error_reason": env.get("error"),
            "latency_ms": elapsed_ms,
        })
        return env
    env["connector"] = connector
    env = apply_injection_scan(env)
    emit_metric(session_key, "ai_knowledge_fetch", {
        "connector": connector, "ok": True,
        "source_id": env.get("source_id"),
        "kind": env.get("kind"),
        "latency_ms": elapsed_ms,
        "injection_flagged": bool(env.get("_injection_flags")),
    })
    return env


# ──────────────────────────────────────────────────────────────────────
# Prompt-injection passive scanner (plan §22)
# ──────────────────────────────────────────────────────────────────────

# Patterns are intentionally simple and over-cautious. False positives
# go to a warning surfaced to the admin UI; the LLM is told via the
# bootstrap skill to treat flagged content as untrusted but doesn't
# refuse to consider it.
_INJECTION_PATTERNS = [
    (re.compile(r"\bignore (?:all )?(?:previous|prior|preceding|above) (?:instructions|prompts|system messages)\b", re.IGNORECASE),
     "ignore-previous-instructions"),
    (re.compile(r"\byou are now\b.{0,40}\b(assistant|system|admin|root|llm)\b", re.IGNORECASE),
     "role-redefinition"),
    (re.compile(r"\bsystem\s*:\s*", re.IGNORECASE),
     "system-prompt-leak-attempt"),
    (re.compile(r"```(?:tool[_-]?call|tool[_-]?use|function[_-]?call)\b", re.IGNORECASE),
     "fake-tool-call-fence"),
    (re.compile(r"\{\s*\"(?:tool|function)(?:_name)?\"\s*:", re.IGNORECASE),
     "tool-call-shaped-json"),
    (re.compile(r"\bdisregard (?:the )?(?:above|previous|prior)\b", re.IGNORECASE),
     "disregard-prior"),
    (re.compile(r"\bprint (?:the |your )?(?:system )?prompt\b", re.IGNORECASE),
     "prompt-leak-attempt"),
]

# Fields scanned on each fetched envelope.
_INJECTION_FIELDS = (
    "summary", "spl_rationale", "tuning_advice", "response_guidance",
    "injected_guidance", "prerequisites",
)


def scan_text_for_injection(text):
    """Return a list of {pattern, where} dicts for matches in `text`."""
    if not isinstance(text, str) or not text:
        return []
    out = []
    for pat, label in _INJECTION_PATTERNS:
        if pat.search(text):
            out.append({"pattern": label})
    return out


def apply_injection_scan(envelope):
    """Add `_injection_flags` to the envelope if any prose field matches."""
    if not isinstance(envelope, dict):
        return envelope
    all_flags = []
    for f in _INJECTION_FIELDS:
        flags = scan_text_for_injection(envelope.get(f))
        for fl in flags:
            fl["field"] = f
        all_flags.extend(flags)
    # Also scan raw if present — it's an escape hatch but per plan §6.2
    # it gets scanned the same as anything else.
    raw = envelope.get("raw")
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, str):
                flags = scan_text_for_injection(v)
                for fl in flags:
                    fl["field"] = "raw." + k
                all_flags.extend(flags)
    if all_flags:
        envelope["_injection_flags"] = all_flags
    return envelope


# ──────────────────────────────────────────────────────────────────────
# Telemetry
# ──────────────────────────────────────────────────────────────────────

def emit_metric(session_key, kind, fields):
    """Best-effort write of a telemetry event to the metrics index.

    Failures are silently swallowed — telemetry is observability, not
    the source of truth, so we never let it block a knowledge call.
    """
    if not session_key:
        return
    event = {"ts_epoch": int(time.time()), "kind": kind}
    if isinstance(fields, dict):
        event.update(fields)
    url = (
        "/services/receivers/simple"
        "?index={idx}&sourcetype={st}&source={src}&host=ai_workbench"
    ).format(idx=TELEMETRY_INDEX, st=TELEMETRY_SOURCETYPE,
             src=TELEMETRY_SOURCE)
    try:
        rest.simpleRequest(
            url, sessionKey=session_key, method="POST",
            rawResult=True, jsonargs=json.dumps(event),
        )
    except Exception:
        pass
