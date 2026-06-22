"""Change-log emission helper for KVStore writes.

Phase 9.2 of instructions/kvstore_backup_design.md.

Existing write-path handlers (custom_tools, mcp, use_cases, tenancy,
etc.) call emit_change() after a successful KVStore mutation. The
event is POSTed to the itmip_changes index with sourcetype
itmip:kvstore:change.

Default behaviour is best-effort: any failure is silently swallowed
so the user's KVStore write succeeds even when the change index is
unavailable. The emission mode can be flipped to "mandatory" via
default/itmip_ai_workbench.conf [kvstore_backup] emission_mode —
in that mode emit_change() raises on failure so the caller can roll
back. Callers must opt in to that behaviour by catching the
RuntimeError; otherwise the default best-effort path always returns
without raising.
"""

import json
import os
import sys
import time

APP_BIN = os.path.dirname(os.path.abspath(__file__))
if APP_BIN not in sys.path:
    sys.path.insert(0, APP_BIN)

try:
    import splunk.rest as rest  # type: ignore
except Exception:  # pragma: no cover
    rest = None  # type: ignore

try:
    import splunk.clilib.cli_common as splunk_cli_common  # type: ignore
except Exception:  # pragma: no cover
    splunk_cli_common = None  # type: ignore

from itmip_llm_common import APP_NAME  # noqa: E402

CHANGES_INDEX = "itmip_changes"
CHANGES_SOURCETYPE = "itmip:kvstore:change"
CHANGES_SOURCE = "itmip_llm_kvstore_changelog"


# Collections we mirror to the change log. The audit collection
# (itmip_llm_custom_tool_calls) is deliberately excluded — it's
# append-only and high-volume, recovery value is low, see design §1.3.
TRACKED_COLLECTIONS = {
    "itmip_organisations",
    "itmip_business_units",
    "itmip_llm_configs",
    "itmip_tool_assignments",
    "itmip_tool_overrides",
    "itmip_ai_use_cases",
    # v0.9.6 — Skills layer. Same change-log treatment as templates.
    "itmip_ai_skills",
    # v0.9.7 — Authoring audit log. Append-only intent so the change-log
    # treats every row as a create; mostly redundant with the audit
    # rows themselves but keeps the security-review surface uniform.
    "itmip_authoring_changes",
    "itmip_llm_custom_tools",
    "itmip_mcp_servers",
    "itmip_mcp_tools",
    "itmip_llm_license",
    "itmip_llm_mltk_models",
    "itmip_user_history",
    # v1.0.0 — Knowledge layer. Track admin edits to connector
    # registry + library content so backup/restore + audit are uniform
    # with templates/skills/tools.
    "itmip_knowledge_connectors",
    "itmip_ai_knowledge_entries",
    "itmip_knowledge_static_rules",
}


def _app_version():
    """Read our own app's version from default/app.conf [launcher].

    See note in itmip_llm_kvstore_backup.py — the standard
    getConfStanza("app", "launcher") returns a system-merged view, not
    our own app's value. Parse the file directly.
    """
    path = os.path.join(
        os.path.dirname(APP_BIN), "default", "app.conf"
    )
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


def _resolve_mode(default_mode=None):
    """Read emission_mode from default/itmip_ai_workbench.conf if not
    overridden by the caller."""
    if default_mode:
        return str(default_mode).lower()
    if splunk_cli_common is None:
        return "best_effort"
    try:
        stanza = splunk_cli_common.getConfStanza("itmip_ai_workbench", "kvstore_backup")
        if isinstance(stanza, dict):
            mode = str(stanza.get("emission_mode") or "best_effort").lower()
            if mode in ("best_effort", "mandatory"):
                return mode
    except Exception:
        pass
    return "best_effort"


def emit_change(
    sys_token,
    collection,
    op,
    key,
    before,
    after,
    user,
    request_id="",
    mode=None,
):
    """Write a single change-log event.

    Args:
      sys_token: splunkd system token (used for receivers/simple POST).
      collection: KVStore collection name.
      op: "create" | "update" | "delete".
      key: row _key.
      before: dict | None — row state before the change (None on create).
      after: dict | None — row state after the change (None on delete).
      user: Splunk user who made the change.
      request_id: optional correlation id.
      mode: override emission mode for this call ("best_effort" |
            "mandatory"). Defaults to the [kvstore_backup] knob.

    Returns True on success, False on best-effort failure. Raises
    RuntimeError on failure when mode == "mandatory".
    """
    if not sys_token or rest is None:
        if (_resolve_mode(mode) == "mandatory"):
            raise RuntimeError("change-log emit: no system token")
        return False

    if collection not in TRACKED_COLLECTIONS:
        # Untracked collection — silently ignore. Lets callers wire
        # emit_change() unconditionally without per-collection guards.
        return True

    event = {
        "ts_epoch": int(time.time()),
        "user": user or "unknown",
        "collection": collection,
        "op": (op or "").lower(),
        "key": key or "",
        "before": before,
        "after": after,
        "request_id": request_id or "",
        "app_version": _app_version(),
    }

    # v1.3.0 — Real audit logging. Mirror governance mutations (templates,
    # tools, MCP, configs, orgs, …) into the owning Org's long-retention audit
    # index as a REDACTED governance_change. Best-effort + isolated so it can
    # never affect the change-log's own restore guarantee. History / authoring
    # collections are filtered out inside emit_governance().
    #
    # v1.4.1 — governance logging is an Enterprise feature (per-feature
    # licensing). Below the cap we SKIP the governance mirror only — the
    # change-log itself (above/below) still writes, so restore integrity is
    # untouched. Fail-closed: any resolution error suppresses the mirror.
    # Spec: instructions/FEATURE_LICENSING_SPEC.md
    try:
        from itmip_llm_license import capability_enabled
        _gov_ok = capability_enabled(sys_token, "governance_logging")
    except Exception:
        _gov_ok = False
    if _gov_ok:
        try:
            from itmip_llm_audit import emit_governance
            emit_governance(sys_token, collection, op, key, before, after, user)
        except Exception as _gexc:
            sys.stderr.write("itmip_llm_kvstore_changelog: governance audit emit failed: %s\n" % _gexc)

    url = (
        "/services/receivers/simple"
        "?index={idx}&sourcetype={st}&source={src}&host=ai_workbench"
    ).format(idx=CHANGES_INDEX, st=CHANGES_SOURCETYPE, src=CHANGES_SOURCE)

    resolved_mode = _resolve_mode(mode)
    try:
        resp, content = rest.simpleRequest(
            url,
            sessionKey=sys_token,
            method="POST",
            rawResult=True,
            jsonargs=json.dumps(event),
        )
        status = getattr(resp, "status", 0)
        if status in (200, 201):
            return True
        msg = "receivers/simple status %s" % status
    except Exception as exc:
        msg = "receivers/simple exception: %s" % exc

    if resolved_mode == "mandatory":
        raise RuntimeError("change-log emit failed: %s" % msg)
    return False
