"""KVStore backup scripted input.

Phases 9.1 + 9.3 of instructions/kvstore_backup_design.md.

Wakes every 600 seconds via default/inputs.conf. On each tick:
  1. Reads default/itmip_ai_workbench.conf [kvstore_backup] for the
     daily_time + retention + secrets_backup knobs.
  2. Decides if today's daily snapshot is due (state file in
     $SPLUNK_DB/itmip_kvstore_backup_state.json).
  3. If due, walks every critical-tier and user-personal collection,
     POSTs one snapshot event per row to /services/receivers/simple
     with index=itmip_snapshots and sourcetype=
     itmip:kvstore:snapshot.
  4. Emits a manifest event (sourcetype itmip:kvstore:manifest) with
     row counts + SHA-256 per collection.
  5. Runs a verification pass via a oneshot search and emits an
     itmip:kvstore:verification event with ok=true/false.
  6. Computes the referenced-credentials inventory (Phase 9.3 / §5.1)
     and emits an itmip:kvstore:secrets_inventory event.
  7. Updates state.

Per-tick stdout produces a single itmip:kvstore:tick event so the
modular-input pipeline has something to consume and admins can see
heartbeats via SPL. All real backup data is POSTed to receivers/simple
so each event lands with the correct sourcetype/index.
"""

import datetime
import hashlib
import json
import os
import re
import sys
import time
import uuid

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.rest as rest  # type: ignore  # noqa: E402

try:
    # Preferred read path — respects default/ then local/ precedence.
    import splunk.clilib.cli_common as splunk_cli_common  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover
    splunk_cli_common = None  # type: ignore

from itmip_llm_common import APP_NAME, LLM_PASSWORD_REALM  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Collection inventory (mirrors design doc §1)
# ─────────────────────────────────────────────────────────────────────

CRITICAL_COLLECTIONS = [
    "itmip_organisations",
    "itmip_business_units",
    "itmip_llm_configs",
    "itmip_tool_assignments",
    "itmip_tool_overrides",
    "itmip_ai_use_cases",
    # v0.9.6 — Skills layer. Same backup treatment as templates.
    "itmip_ai_skills",
    # v0.9.7 — End-user authoring audit log. High signal for security
    # review (records attempted_override_fields on every call), so we
    # want the daily snapshot too.
    "itmip_authoring_changes",
    "itmip_llm_custom_tools",
    "itmip_mcp_servers",
    "itmip_mcp_tools",
    "itmip_llm_license",
    "itmip_llm_mltk_models",
    # v1.0.0 — Knowledge layer. Connector registry + curated entries +
    # static-library trigger rules. Same backup treatment as templates
    # / skills (admin-edited content; recovery value is high).
    "itmip_knowledge_connectors",
    "itmip_ai_knowledge_entries",
    "itmip_knowledge_static_rules",
]
PERSONAL_COLLECTIONS = ["itmip_user_history"]
LEGACY_COLLECTIONS_WARN = ["itmip_claude_use_cases"]

SNAPSHOT_INDEX = "itmip_snapshots"

CONF_FILE = "itmip_ai_workbench"
CONF_STANZA = "kvstore_backup"

# Defaults mirror default/itmip_ai_workbench.conf [kvstore_backup]
# so the script keeps working even if the conf load fails.
DEFAULTS = {
    "enabled": "1",
    "daily_time": "02:00",
    "emission_mode": "best_effort",
    "retention_critical_days": "30",
    "retention_critical_weekly_weeks": "26",
    "retention_critical_monthly_months": "24",
    "retention_history_days": "14",
    "verify_email_recipients": "",
    "secrets_backup.mode": "inventory_only",
    "secrets_backup.include_per_user_tokens": "0",
}

# Local-state file. Tracks last successful backup date so we don't
# re-snapshot more than once per local day.
STATE_FILE = os.path.join(
    os.environ.get("SPLUNK_DB", "/tmp"),
    "itmip_kvstore_backup_state.json",
)


# ─────────────────────────────────────────────────────────────────────
# Splunkd helpers
# ─────────────────────────────────────────────────────────────────────

def _splunkd_session_key():
    return sys.stdin.readline().strip() if not sys.stdin.isatty() else ""


def _emit_tick_event(payload):
    """Heartbeat to stdout — picked up by the modular-input pipeline
    under sourcetype itmip:kvstore:tick from inputs.conf."""
    payload = dict(payload)
    payload["ts_epoch"] = int(time.time())
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _post_event(sys_token, index, sourcetype, body):
    """POST a single event via /services/receivers/simple with explicit
    index + sourcetype. Returns (ok: bool, error: str)."""
    url = (
        "/services/receivers/simple"
        "?index={index}&sourcetype={sourcetype}&source={source}&host=ai_workbench"
    ).format(
        index=index,
        sourcetype=sourcetype,
        source="itmip_llm_kvstore_backup",
    )
    try:
        resp, content = rest.simpleRequest(
            url,
            sessionKey=sys_token,
            method="POST",
            rawResult=True,
            jsonargs=body if isinstance(body, str) else json.dumps(body),
        )
        status = getattr(resp, "status", 0)
        if status in (200, 201):
            return True, ""
        return False, "receivers/simple status %s: %s" % (
            status,
            (content if isinstance(content, str) else content.decode("utf-8", "replace"))[:200],
        )
    except Exception as exc:
        return False, "receivers/simple exception: %s" % exc


def _load_conf():
    """Read [kvstore_backup] from itmip_ai_workbench.conf with defaults."""
    settings = dict(DEFAULTS)
    if splunk_cli_common is None:
        return settings
    try:
        stanza = splunk_cli_common.getConfStanza(CONF_FILE, CONF_STANZA)
        if isinstance(stanza, dict):
            for k, v in stanza.items():
                if v is None:
                    continue
                settings[k] = str(v)
    except Exception:
        # Conf file might not exist yet or the stanza is missing.
        # We fall back to DEFAULTS — safe.
        pass
    return settings


def _bool(val, fallback=False):
    s = str(val or "").strip().lower()
    if s in ("1", "true", "yes", "on", "enabled"):
        return True
    if s in ("0", "false", "no", "off", "disabled"):
        return False
    return fallback


def _read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_state(state):
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, STATE_FILE)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────
# Decide-if-due
# ─────────────────────────────────────────────────────────────────────

def _today_local_iso():
    return datetime.date.today().isoformat()


def _is_backup_due(settings, state):
    """True if today's daily snapshot has not yet run and local time
    has crossed the configured daily_time."""
    if not _bool(settings.get("enabled"), True):
        return False, "disabled"
    raw = (settings.get("daily_time") or "02:00").strip()
    try:
        hh, mm = raw.split(":")
        hour = int(hh)
        minute = int(mm)
    except Exception:
        hour, minute = 2, 0
    now = datetime.datetime.now()
    daily_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    today = _today_local_iso()
    if state.get("last_backup_date") == today:
        return False, "already_ran_today"
    if now < daily_dt:
        return False, "before_daily_time"
    return True, "due"


# ─────────────────────────────────────────────────────────────────────
# Collection I/O
# ─────────────────────────────────────────────────────────────────────

def _coll_url(coll, suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{suffix}"
    ).format(app=APP_NAME, coll=coll, suffix=suffix)


def _list_collection_rows(sys_token, coll):
    """Return list of row dicts (each contains _key and the row fields).

    Pages via Splunk's count/offset pagination because KVStore caps
    /storage/collections/data/<coll> at 50,000 rows per request.

    On HTTP 503 (KVStore service unavailable — most commonly because
    Mongo is still warming up after a Splunk restart) retry up to 3
    times with backoff. On other non-2xx the error message captures
    the first 500 chars of the response body so the operator can see
    what splunkd actually said.
    """
    out = []
    offset = 0
    page = 5000
    while True:
        url = _coll_url(
            coll,
            suffix="?output_mode=json&count={count}&skip={skip}".format(
                count=page, skip=offset
            ),
        )

        # Up to 3 attempts on 503; KVStore can return 503 transiently
        # for ~10s after a Splunk restart while Mongo is starting.
        # On a 404 (collection registered in collections.conf but not
        # yet materialised in KVStore — happens for new-in-this-release
        # collections until the first row gets written, OR if splunkd
        # hasn't been restarted since the collections.conf change),
        # treat as an empty collection — same behaviour the existing
        # /services/itmip_llm/use_cases handler uses.
        attempts = 0
        resp = None
        content = None
        last_status = 0
        last_body = ""
        while attempts < 3:
            attempts += 1
            try:
                resp, content = rest.simpleRequest(
                    url, sessionKey=sys_token, method="GET"
                )
                last_status = getattr(resp, "status", 0)
                try:
                    last_body = (content or b"").decode("utf-8") if isinstance(content, bytes) else str(content or "")
                except Exception:
                    last_body = ""
            except Exception as exc:
                # splunk.rest.simpleRequest raises splunk.RESTException
                # on non-2xx by default; the exception message is of the
                # form "[HTTP <code>] <url>". Match the code so we
                # can treat 404 as empty (same as the non-raising path).
                msg = str(exc)
                m = re.search(r"\[HTTP\s+(\d+)\]", msg)
                if m:
                    last_status = int(m.group(1))
                    last_body = msg
                else:
                    raise RuntimeError(
                        "KVStore list %s failed (transport error attempt %d): %s"
                        % (coll, attempts, exc)
                    )
            if last_status == 503 and attempts < 3:
                # Transient — back off + retry.
                time.sleep(2 * attempts)
                continue
            break

        if last_status == 404:
            # Collection isn't materialised in KVStore yet — empty.
            # (Backup-side this is a no-op; the manifest will record
            # row_count=0 with the SHA of an empty list, which the
            # verification step naturally matches.)
            return []
        if last_status != 200:
            # Include the first 500 chars of the response body so the
            # operator can see WHY splunkd returned non-200. Common
            # causes for 503: KVStore service not running (check
            # `splunk show kvstore-status`), Mongo migration in
            # progress on Splunk upgrade, or SHC captain re-election.
            preview = last_body[:500].replace("\n", " ")
            raise RuntimeError(
                "KVStore list %s status %s after %d attempt(s); response: %s"
                % (coll, last_status, attempts, preview or "<empty body>")
            )
        try:
            page_data = json.loads(content)
        except Exception:
            raise RuntimeError(
                "KVStore list %s returned invalid JSON: %s"
                % (coll, (last_body or "")[:200])
            )
        if not isinstance(page_data, list):
            return []
        out.extend(page_data)
        if len(page_data) < page:
            break
        offset += page
    return out


def _canonical_row_blob(row):
    """Deterministic JSON for SHA-256 over a single row. Sort keys."""
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_over_rows(rows):
    h = hashlib.sha256()
    # Sort by _key so SHA is stable regardless of KVStore return order.
    for r in sorted(rows, key=lambda x: str(x.get("_key", ""))):
        h.update(_canonical_row_blob(r).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────
# Snapshot emission
# ─────────────────────────────────────────────────────────────────────

def _snapshot_collection(sys_token, coll, backup_id, backup_epoch, app_version):
    """Emit one event per row. Returns (row_count, sha256, errors)."""
    errors = []
    try:
        rows = _list_collection_rows(sys_token, coll)
    except Exception as exc:
        return 0, "", ["list_failed: %s" % exc]
    sha = _sha256_over_rows(rows)
    for seq, row in enumerate(sorted(rows, key=lambda x: str(x.get("_key", "")))):
        event = {
            "backup_id": backup_id,
            "backup_time_epoch": backup_epoch,
            "collection": coll,
            "key": row.get("_key", ""),
            "row": row,
            "sequence_number": seq,
            "app_version": app_version,
        }
        ok_, err = _post_event(
            sys_token,
            SNAPSHOT_INDEX,
            "itmip:kvstore:snapshot",
            event,
        )
        if not ok_:
            errors.append("row_emit_failed key=%s err=%s" % (row.get("_key", ""), err))
    return len(rows), sha, errors


# ─────────────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────────────

def _verify_backup(sys_token, backup_id, per_coll_stats):
    """Re-read just-emitted events and recompute counts + SHA-256.

    Indexing is near-real-time on splunkd so we wait ~10 seconds for
    propagation before issuing the verification search. Returns
    (ok: bool, per_collection_check: dict, error_msg: str).
    """
    time.sleep(10)
    # Pull _raw and re-parse the JSON ourselves. Splunk's results JSON
    # serialises nested objects awkwardly (the `row` dict often comes
    # back as None even though the raw event has it), so we don't
    # rely on field extraction here.
    search_str = (
        "search index={idx} backup_id=\"{bid}\" "
        "sourcetype=itmip:kvstore:snapshot "
        "| sort collection, sequence_number "
        "| fields _raw"
    ).format(idx=SNAPSHOT_INDEX, bid=backup_id)
    job_url = "/services/search/jobs"
    try:
        resp, content = rest.simpleRequest(
            job_url,
            sessionKey=sys_token,
            method="POST",
            postargs={
                "search": search_str,
                "exec_mode": "oneshot",
                "output_mode": "json",
                "count": 0,
            },
        )
    except Exception as exc:
        return False, {}, "verify_search_failed: %s" % exc
    status = getattr(resp, "status", 0)
    if status not in (200, 201):
        return False, {}, "verify_search_status_%s" % status
    try:
        data = json.loads(content)
    except Exception:
        return False, {}, "verify_search_bad_json"
    results = data.get("results") or []
    by_coll = {}
    for r in results:
        raw = r.get("_raw") or ""
        try:
            event = json.loads(raw)
        except Exception:
            continue
        coll = event.get("collection", "")
        row_obj = event.get("row")
        if not isinstance(row_obj, dict):
            row_obj = {"_key": event.get("key", "")}
        by_coll.setdefault(coll, []).append(row_obj)
    per_check = {}
    overall_ok = True
    for coll, expected in per_coll_stats.items():
        seen_rows = by_coll.get(coll, [])
        recount = len(seen_rows)
        resha = _sha256_over_rows(seen_rows)
        ok_ = (recount == expected["row_count"]) and (resha == expected["sha256"])
        per_check[coll] = {
            "expected_row_count": expected["row_count"],
            "observed_row_count": recount,
            "expected_sha256": expected["sha256"],
            "observed_sha256": resha,
            "ok": ok_,
        }
        if not ok_:
            overall_ok = False
    return overall_ok, per_check, ""


def _urlquote(s):
    try:
        from urllib.parse import quote
        return quote(s, safe="")
    except Exception:
        return s


# ─────────────────────────────────────────────────────────────────────
# Referenced-credentials inventory (Phase 9.3, §5.1)
# ─────────────────────────────────────────────────────────────────────

def _credential_present(sys_token, name):
    """HEAD-style probe of storage/passwords for realm:name presence.

    Splunk's REST returns 200 with empty entries for a missing name OR
    a 404 — we treat both as 'missing'. We DO NOT request cleartext.
    """
    if not name:
        return False
    safe = _urlquote("%s:%s:" % (LLM_PASSWORD_REALM, name))
    url = "/servicesNS/nobody/{app}/storage/passwords/{ref}?output_mode=json".format(
        app=APP_NAME, ref=safe
    )
    try:
        resp, content = rest.simpleRequest(url, sessionKey=sys_token, method="GET")
        status = getattr(resp, "status", 0)
        if status != 200:
            return False
        data = json.loads(content)
        return bool((data or {}).get("entry"))
    except Exception:
        return False


def _expand_template(template, org_short, bu_short, user=None):
    if not template:
        return ""
    out = template
    out = out.replace("{org}", org_short or "")
    out = out.replace("{bu}", bu_short or "")
    if user is not None:
        out = out.replace("{user}", user)
    return out


def _walk_custom_tools(sys_token, tools, orgs, bus_by_org):
    """Yield (credential_name, source_ref, model) tuples for custom tools.

    `tools` is the list of itmip_llm_custom_tools rows already pulled
    by the snapshot loop. The implementation block is JSON-as-string
    on disk; parse on read.
    """
    out = []
    for t in tools:
        impl_raw = t.get("implementation_json") or ""
        try:
            impl = json.loads(impl_raw) if impl_raw else {}
        except Exception:
            impl = {}
        auth = (impl.get("auth") or {}) if isinstance(impl, dict) else {}
        model = (auth.get("credential_model") or "global").lower()
        source = "itmip_llm_custom_tools/%s" % t.get("_key", "")
        if model == "global":
            ref = auth.get("credential_ref") or ""
            if ref:
                out.append({"name": ref, "source": source, "model": "global"})
        elif model == "per_tenant":
            tmpl = auth.get("credential_ref_template") or auth.get("credential_ref") or ""
            for org in orgs:
                for bu in bus_by_org.get(org, [""]) or [""]:
                    ref = _expand_template(tmpl, org, bu)
                    if ref:
                        out.append({"name": ref, "source": source, "model": "per_tenant"})
        elif model == "per_user":
            # v0.8.0 doesn't have the user list yet; emit the template
            # itself as a notice with the user placeholder intact.
            tmpl = auth.get("credential_ref_template") or auth.get("credential_ref") or ""
            if tmpl:
                out.append(
                    {
                        "name": tmpl,
                        "source": source,
                        "model": "per_user",
                        "note": "per-user template; expansion deferred to v0.9.0 (Phase 3 OAuth)",
                    }
                )
        # proxy + TLS CA refs are global-style names today
        proxy_ref = impl.get("proxy_credential_ref") or ""
        if proxy_ref:
            out.append({"name": proxy_ref, "source": source + ":proxy", "model": "global"})
        tls_ref = impl.get("tls_ca_pem_ref") or ""
        if tls_ref:
            out.append({"name": tls_ref, "source": source + ":tls_ca", "model": "global"})
    return out


def _walk_mcp_servers(servers):
    out = []
    for s in servers:
        source = "itmip_mcp_servers/%s" % s.get("_key", "")
        model = (s.get("credential_model") or "global").lower()
        ref = s.get("credential_ref") or ""
        if ref:
            out.append({"name": ref, "source": source, "model": model})
        proxy_ref = s.get("proxy_credential_ref") or ""
        if proxy_ref:
            out.append({"name": proxy_ref, "source": source + ":proxy", "model": "global"})
        tls_ref = s.get("tls_ca_pem_ref") or ""
        if tls_ref:
            out.append({"name": tls_ref, "source": source + ":tls_ca", "model": "global"})
    return out


def _walk_llm_configs(configs):
    out = []
    for c in configs:
        key = c.get("_key") or ""
        if not key:
            continue
        # Conventional name from itmip_llm_secret.py: realm + per-config _key.
        out.append(
            {
                "name": key,
                "source": "itmip_llm_configs/%s" % key,
                "model": "global",
                "note": "per-LLM-config API key (storage/passwords realm=%s)" % LLM_PASSWORD_REALM,
            }
        )
    return out


def _compute_secrets_inventory(sys_token, snapshotted_rows):
    """Build the §5.1 inventory. Probes storage/passwords for presence
    but never pulls cleartext. Returns the full inventory dict."""
    orgs_rows = snapshotted_rows.get("itmip_organisations", [])
    bus_rows = snapshotted_rows.get("itmip_business_units", [])
    tools_rows = snapshotted_rows.get("itmip_llm_custom_tools", [])
    mcp_rows = snapshotted_rows.get("itmip_mcp_servers", [])
    cfg_rows = snapshotted_rows.get("itmip_llm_configs", [])

    orgs = [str(o.get("short") or "").upper() for o in orgs_rows if o.get("short")]
    bus_by_org = {}
    for b in bus_rows:
        org = str(b.get("org_short") or "").upper()
        bu = str(b.get("short") or "").upper()
        if not org:
            continue
        bus_by_org.setdefault(org, []).append(bu)

    refs = []
    refs.extend(_walk_custom_tools(sys_token, tools_rows, orgs, bus_by_org))
    refs.extend(_walk_mcp_servers(mcp_rows))
    refs.extend(_walk_llm_configs(cfg_rows))

    # Deduplicate by (name, source).
    seen = set()
    dedup = []
    for r in refs:
        key = (r["name"], r.get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    # Probe presence — but skip the per_user template placeholders
    # (they contain {user} and would always be absent).
    present_count = 0
    missing_count = 0
    for r in dedup:
        if r.get("model") == "per_user" and "{user}" in r.get("name", ""):
            r["present_at_backup_time"] = None
            continue
        present = _credential_present(sys_token, r["name"])
        r["present_at_backup_time"] = present
        if present:
            present_count += 1
        else:
            missing_count += 1

    return {
        "referenced_credentials": dedup,
        "summary": {
            "referenced": len(dedup),
            "present": present_count,
            "missing": missing_count,
        },
    }


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def _app_version():
    """Read our own app's version from default/app.conf [launcher].

    splunk.clilib.cli_common.getConfStanza("app", "launcher") returns a
    system-merged view across all installed apps, so it hits the wrong
    [launcher] stanza. Parse our own file directly instead.
    """
    path = os.path.join(APP_DIR, "default", "app.conf")
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


def _legacy_warning(sys_token, all_snapshotted):
    """If a legacy collection has rows, emit a tick-style warning."""
    notes = []
    for coll in LEGACY_COLLECTIONS_WARN:
        try:
            rows = _list_collection_rows(sys_token, coll)
        except Exception:
            continue
        if rows:
            notes.append({"collection": coll, "stragglers": len(rows)})
    if notes:
        _emit_tick_event({"event": "legacy_collection_warning", "notes": notes})


def main():
    sys_token = _splunkd_session_key()
    if not sys_token:
        # No auth → can't do anything. Emit a tick and bail.
        _emit_tick_event({"event": "no_auth"})
        return

    # v1.4.1 — automated KVStore backups are a Professional+ feature
    # (per-feature licensing). On Free/personal the snapshot tick is a no-op:
    # emit a status event and bail before touching any collection. Fail-closed
    # (capability_enabled collapses to personal on doubt). Lazy import keeps the
    # modular-input startup path dependency-light.
    # Spec: instructions/FEATURE_LICENSING_SPEC.md
    try:
        from itmip_llm_license import capability_enabled
        backups_ok = capability_enabled(sys_token, "backups")
    except Exception:
        backups_ok = False
    if not backups_ok:
        _emit_tick_event({"event": "skip", "reason": "license_no_backups"})
        return

    settings = _load_conf()
    state = _read_state()
    due, reason = _is_backup_due(settings, state)
    if not due:
        _emit_tick_event({"event": "skip", "reason": reason})
        return

    backup_id = str(uuid.uuid4())
    backup_epoch = int(time.time())
    app_version = _app_version()

    # Snapshot every critical-tier + personal-tier collection.
    per_coll_stats = {}
    snapshotted_rows = {}
    total_errors = []
    for coll in CRITICAL_COLLECTIONS + PERSONAL_COLLECTIONS:
        try:
            rows = _list_collection_rows(sys_token, coll)
        except Exception as exc:
            total_errors.append({"collection": coll, "stage": "list", "err": str(exc)})
            per_coll_stats[coll] = {"row_count": 0, "sha256": ""}
            snapshotted_rows[coll] = []
            continue
        sha = _sha256_over_rows(rows)
        # Emit per-row events.
        errs = []
        for seq, row in enumerate(sorted(rows, key=lambda x: str(x.get("_key", "")))):
            event = {
                "backup_id": backup_id,
                "backup_time_epoch": backup_epoch,
                "collection": coll,
                "key": row.get("_key", ""),
                "row": row,
                "sequence_number": seq,
                "app_version": app_version,
            }
            ok_, err = _post_event(
                sys_token, SNAPSHOT_INDEX, "itmip:kvstore:snapshot", event
            )
            if not ok_:
                errs.append(err)
        per_coll_stats[coll] = {"row_count": len(rows), "sha256": sha}
        snapshotted_rows[coll] = rows
        if errs:
            total_errors.append(
                {"collection": coll, "stage": "emit", "first_error": errs[0], "total": len(errs)}
            )

    # Manifest event.
    manifest = {
        "backup_id": backup_id,
        "backup_time_epoch": backup_epoch,
        "app_version": app_version,
        "collections": [
            {"name": c, "row_count": per_coll_stats[c]["row_count"], "sha256": per_coll_stats[c]["sha256"]}
            for c in (CRITICAL_COLLECTIONS + PERSONAL_COLLECTIONS)
        ],
        "errors": total_errors,
    }
    _post_event(sys_token, SNAPSHOT_INDEX, "itmip:kvstore:manifest", manifest)

    # Verification.
    ok_, per_check, verr = _verify_backup(sys_token, backup_id, per_coll_stats)
    verification_event = {
        "backup_id": backup_id,
        "backup_time_epoch": backup_epoch,
        "checked_at_epoch": int(time.time()),
        "ok": bool(ok_),
        "per_collection": per_check,
        "error": verr,
    }
    _post_event(
        sys_token, SNAPSHOT_INDEX, "itmip:kvstore:verification", verification_event
    )

    # Phase 9.3 — referenced credentials inventory (no cleartext).
    secrets_mode = (settings.get("secrets_backup.mode") or "inventory_only").lower()
    inventory = _compute_secrets_inventory(sys_token, snapshotted_rows)
    inventory_event = {
        "backup_id": backup_id,
        "backup_time_epoch": backup_epoch,
        "mode": secrets_mode,
        "referenced_credentials": inventory["referenced_credentials"],
        "summary": inventory["summary"],
    }
    if secrets_mode == "cleartext_restricted":
        # Phase 9.6 — not yet implemented in this version.
        inventory_event["warning"] = (
            "cleartext_restricted is configured but Phase 9.6 has not "
            "shipped yet — only the inventory was written."
        )
    _post_event(
        sys_token,
        SNAPSHOT_INDEX,
        "itmip:kvstore:secrets_inventory",
        inventory_event,
    )

    # Sunset check for the legacy collection.
    _legacy_warning(sys_token, snapshotted_rows)

    # Update state.
    new_state = {
        "last_backup_date": _today_local_iso(),
        "last_backup_id": backup_id,
        "last_backup_epoch": backup_epoch,
        "last_verification_ok": bool(ok_),
    }
    state_written = _write_state(new_state)

    _emit_tick_event(
        {
            "event": "backup_done",
            "backup_id": backup_id,
            "verification_ok": bool(ok_),
            "collections": len(per_coll_stats),
            "total_rows": sum(s["row_count"] for s in per_coll_stats.values()),
            "errors": len(total_errors),
            "secrets_referenced": inventory["summary"]["referenced"],
            "secrets_missing": inventory["summary"]["missing"],
            "state_written": state_written,
        }
    )


if __name__ == "__main__":
    main()
