"""KVStore backup admin REST handler.

Phase 9.5 of instructions/kvstore_backup_design.md — the Web UI surface
for listing manifests, drilling into per-backup detail, and triggering
an out-of-schedule backup. Restore CLI / REST / commit logic is
Phase 9.4 + the restore engine — deferred to a later release.

Endpoints — REST under `/services/itmip_llm/kvstore_admin/...`:

  GET    /backups               List recent manifests (newest first).
                                Query: ?count=<n> (default 30).
                                Returns one entry per backup_id with
                                row counts, app_version, verification
                                summary, secrets-inventory summary.
  GET    /backups/<id>          Manifest detail for one backup_id.
                                Includes per-collection rows, the full
                                verification event, and the
                                referenced-credentials inventory.
  POST   /backups/now           Trigger a fresh backup out of schedule.
                                Admin only. Deletes the state file so
                                the next scheduled-input tick runs the
                                snapshot, then synchronously invokes
                                the snapshot once via subprocess so the
                                caller gets immediate feedback. Returns
                                the new backup_id.

Admin only — all endpoints refuse non-admin callers with HTTP 403.
"""

import json
import os
import subprocess
import sys
from urllib.parse import quote, urlencode

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for _p in (APP_LIB, APP_BIN):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import splunk.persistconn.application as application  # type: ignore  # noqa: E402
import splunk.rest as rest  # type: ignore  # noqa: E402

from itmip_llm_common import (  # noqa: E402
    APP_NAME,
    err,
    is_admin,
    ok,
    system_token,
    user_name,
    user_token,
)
from itmip_llm_kvstore_restore import (  # noqa: E402
    ALL_RESTORABLE,
    break_stale_lock,
    build_plan,
    commit_plan,
    get_lock_state,
)


SNAPSHOT_INDEX = "itmip_snapshots"
STATE_FILE = os.path.join(
    os.environ.get("SPLUNK_DB", "/tmp"),
    "itmip_kvstore_backup_state.json",
)
BACKUP_SCRIPT = os.path.join(APP_BIN, "itmip_llm_kvstore_backup.py")


# ─────────────────────────────────────────────────────────────────────
# Search helpers
# ─────────────────────────────────────────────────────────────────────

def _oneshot_search(sys_token, search_str):
    """Run a oneshot search; return parsed JSON or {} on error."""
    try:
        resp, content = rest.simpleRequest(
            "/services/search/jobs",
            sessionKey=sys_token,
            method="POST",
            postargs={
                "search": search_str,
                "exec_mode": "oneshot",
                "output_mode": "json",
                "count": 0,
            },
        )
    except Exception:
        return {}
    if getattr(resp, "status", 0) not in (200, 201):
        return {}
    try:
        return json.loads(content)
    except Exception:
        return {}


def _parse_raw(event):
    """Each manifest / verification / inventory event has its full JSON
    in _raw. Splunk's field extraction sometimes loses nested keys, so
    we re-parse _raw ourselves."""
    raw = event.get("_raw") or ""
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    try:
        return json.loads(raw)
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────
# List backups
# ─────────────────────────────────────────────────────────────────────

def _list_backups(sys_token, count):
    """Return a list of backup-summary dicts (newest first).

    Joins the manifest, verification, and secrets_inventory events for
    each backup_id so the UI list row has everything it needs without
    a second round trip.
    """
    # Pull recent manifests.
    manifests = _oneshot_search(
        sys_token,
        (
            "search index={idx} sourcetype=itmip:kvstore:manifest "
            "| sort - _time "
            "| head {count} "
            "| fields _time, _raw"
        ).format(idx=SNAPSHOT_INDEX, count=int(count)),
    )
    results = manifests.get("results") or []
    if not results:
        return []

    backup_ids = []
    summaries_by_id = {}
    for r in results:
        m = _parse_raw(r)
        bid = m.get("backup_id")
        if not bid:
            continue
        backup_ids.append(bid)
        coll_rows = []
        total_rows = 0
        for c in m.get("collections") or []:
            cnt = int(c.get("row_count") or 0)
            total_rows += cnt
            coll_rows.append(
                {
                    "name": c.get("name") or "",
                    "row_count": cnt,
                    "sha256": c.get("sha256") or "",
                }
            )
        summaries_by_id[bid] = {
            "backup_id": bid,
            "backup_time_epoch": int(m.get("backup_time_epoch") or 0),
            "_time": r.get("_time"),
            "app_version": m.get("app_version") or "",
            "collections": coll_rows,
            "total_rows": total_rows,
            "errors": m.get("errors") or [],
            "verification": None,
            "secrets_inventory": None,
        }

    if not backup_ids:
        return []

    # Bulk fetch verification events for these backup_ids.
    ids_filter = " OR ".join('backup_id="{}"'.format(b) for b in backup_ids)
    verifications = _oneshot_search(
        sys_token,
        (
            "search index={idx} sourcetype=itmip:kvstore:verification "
            "({ids}) | sort - _time | fields _raw"
        ).format(idx=SNAPSHOT_INDEX, ids=ids_filter),
    )
    for r in (verifications.get("results") or []):
        v = _parse_raw(r)
        bid = v.get("backup_id")
        if bid in summaries_by_id and summaries_by_id[bid]["verification"] is None:
            summaries_by_id[bid]["verification"] = {
                "ok": bool(v.get("ok")),
                "checked_at_epoch": int(v.get("checked_at_epoch") or 0),
                "error": v.get("error") or "",
            }

    # Bulk fetch secrets_inventory events.
    inventories = _oneshot_search(
        sys_token,
        (
            "search index={idx} sourcetype=itmip:kvstore:secrets_inventory "
            "({ids}) | sort - _time | fields _raw"
        ).format(idx=SNAPSHOT_INDEX, ids=ids_filter),
    )
    for r in (inventories.get("results") or []):
        inv = _parse_raw(r)
        bid = inv.get("backup_id")
        if bid in summaries_by_id and summaries_by_id[bid]["secrets_inventory"] is None:
            summary = inv.get("summary") or {}
            summaries_by_id[bid]["secrets_inventory"] = {
                "mode": inv.get("mode") or "",
                "referenced": int(summary.get("referenced") or 0),
                "present": int(summary.get("present") or 0),
                "missing": int(summary.get("missing") or 0),
            }

    # Preserve the original (newest-first) order.
    return [summaries_by_id[b] for b in backup_ids if b in summaries_by_id]


# ─────────────────────────────────────────────────────────────────────
# Backup detail
# ─────────────────────────────────────────────────────────────────────

def _backup_detail(sys_token, backup_id):
    """Pull manifest + verification + inventory for one backup_id."""
    safe = "".join(c for c in (backup_id or "") if c.isalnum() or c in "-")
    if not safe:
        return None
    detail = {
        "backup_id": safe,
        "manifest": None,
        "verification": None,
        "secrets_inventory": None,
    }
    base_search = (
        'search index={idx} backup_id="{bid}" sourcetype={st} '
        '| sort - _time | head 1 | fields _raw'
    )
    for kind, key in (
        ("itmip:kvstore:manifest", "manifest"),
        ("itmip:kvstore:verification", "verification"),
        ("itmip:kvstore:secrets_inventory", "secrets_inventory"),
    ):
        result = _oneshot_search(
            sys_token,
            base_search.format(idx=SNAPSHOT_INDEX, bid=safe, st=kind),
        )
        rows = result.get("results") or []
        if rows:
            detail[key] = _parse_raw(rows[0])

    # Bail out if we found nothing at all (probably a bad backup_id).
    if detail["manifest"] is None:
        return None

    return detail


# ─────────────────────────────────────────────────────────────────────
# Trigger backup now
# ─────────────────────────────────────────────────────────────────────

def _trigger_backup_now(sys_token):
    """Delete the state file and invoke the snapshot script directly.

    Running synchronously lets the UI report success / failure on the
    same request. The scripted-input tick will see the updated state
    and skip its own run for the rest of the day. Returns the script's
    final stdout event (a tick event with backup_done payload).
    """
    # Clear the state file so the script re-runs unconditionally.
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
    except Exception as exc:
        return False, "could_not_clear_state: %s" % exc

    # Invoke the snapshot script with the system token on stdin.
    # Splunk ships a wrapper at $SPLUNK_HOME/bin/python3 that primes
    # SPLUNK_HOME and PYTHONPATH for us.
    splunk_python = os.path.join(
        os.environ.get("SPLUNK_HOME", "/opt/splunk"), "bin", "python3"
    )
    if not os.path.exists(splunk_python):
        # Fallback to whatever python is in PATH.
        splunk_python = "python3"

    try:
        proc = subprocess.run(
            [splunk_python, BACKUP_SCRIPT],
            input=sys_token + "\n",
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ),
        )
    except subprocess.TimeoutExpired:
        return False, "timeout_after_120s"
    except Exception as exc:
        return False, "exec_failed: %s" % exc

    if proc.returncode != 0:
        return False, "exit_code=%s stderr=%s" % (
            proc.returncode,
            (proc.stderr or "")[:500],
        )

    # The script emits one JSON-per-line tick event on stdout.
    # The last line is the backup_done summary.
    last_line = ""
    for line in (proc.stdout or "").splitlines():
        if line.strip():
            last_line = line.strip()
    try:
        return True, json.loads(last_line)
    except Exception:
        return True, {"raw_stdout": (proc.stdout or "")[:1000]}


# ─────────────────────────────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────────────────────────────

def _parse_query(args):
    qs = args.get("query") or []
    if isinstance(qs, list):
        return dict(qs)
    return dict(qs.items()) if hasattr(qs, "items") else {}


def _split_path(args):
    """Split the path-info beneath /itmip_llm/kvstore_admin.

    Splunk's persistent handler passes the path under `path_info`
    (sometimes `path`). For a request to
    `/services/itmip_llm/kvstore_admin/backups/<id>` the value here is
    `/backups/<id>` — i.e. the suffix beneath the restmap `match`.
    """
    raw_path = (
        args.get("path_info")
        or args.get("path")
        or args.get("rest_path")
        or args.get("restPath")
        or ""
    )
    parts = [p for p in (raw_path or "").strip("/").split("/") if p]
    return parts


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
            if not is_admin(args, rest):
                return err(403, "Admin role required.")

            query = _parse_query(args)
            parts = _split_path(args)

            # POST /restore — dry-run OR commit
            # GET  /restore/lock — current lock state
            # POST /restore/lock/break — break a stale lock
            # GET  /restore/collections — restorable collection list
            if parts and parts[0] == "restore":
                if len(parts) == 1 and method == "POST":
                    return self._handle_restore(args, sys_token)
                if (
                    len(parts) == 2
                    and parts[1] == "lock"
                    and method == "GET"
                ):
                    return ok(get_lock_state(sys_token))
                if (
                    len(parts) == 3
                    and parts[1] == "lock"
                    and parts[2] == "break"
                    and method == "POST"
                ):
                    try:
                        break_stale_lock(sys_token, user_name(args))
                    except Exception as exc:
                        return err(409, "Cannot break: %s" % exc)
                    return ok({"ok": True})
                if (
                    len(parts) == 2
                    and parts[1] == "collections"
                    and method == "GET"
                ):
                    return ok({"items": list(ALL_RESTORABLE)})
                return err(405, "Method not allowed on this restore sub-path.")

            # GET /backups — list manifests
            # GET /backups/<id> — manifest detail
            if parts and parts[0] == "backups":
                if method == "GET":
                    if len(parts) == 1:
                        try:
                            count = int(query.get("count") or 30)
                        except Exception:
                            count = 30
                        count = max(1, min(count, 200))
                        items = _list_backups(sys_token, count)
                        return ok({"items": items})
                    # /backups/<id>
                    bid = parts[1]
                    detail = _backup_detail(sys_token, bid)
                    if detail is None:
                        return err(404, "No manifest for backup_id '%s'." % bid)
                    return ok(detail)
                if method == "POST" and len(parts) == 2 and parts[1] == "now":
                    ok_, info = _trigger_backup_now(sys_token)
                    if not ok_:
                        return err(502, "Backup-now failed: %s" % info)
                    return ok({"ok": True, "result": info})
                return err(405, "Method not allowed.")

            return err(
                404,
                "Unknown path. Expected /backups[/<id>] /backups/now "
                "/restore /restore/lock /restore/collections.",
            )
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def _handle_restore(self, args, sys_token):
        """POST /restore — dry-run when `dry_run=true`, commit otherwise.

        Request body:
          {
            "backup_id": "<uuid>",
            "collections": [...],   # optional — defaults to ALL_RESTORABLE
            "dry_run": true,        # required for dry-run
            "acknowledge": true,    # required for commit
          }
        """
        payload_raw = args.get("payload") or "{}"
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except Exception:
            return err(400, "Invalid JSON payload.")
        backup_id = (payload.get("backup_id") or "").strip()
        if not backup_id:
            return err(400, "'backup_id' is required.")
        collections = payload.get("collections")
        if collections is not None:
            if not isinstance(collections, list):
                return err(400, "'collections' must be a list of names.")
            collections = [str(c) for c in collections if isinstance(c, str)]
            if not collections:
                return err(400, "'collections' empty after sanitisation.")
        dry_run = bool(payload.get("dry_run", False))
        acknowledge = bool(payload.get("acknowledge", False))
        user = user_name(args)

        if dry_run:
            try:
                plan = build_plan(sys_token, backup_id, collections)
            except Exception as exc:
                return err(502, "Could not build plan: %s" % exc)
            return ok(plan)

        if not acknowledge:
            return err(
                400,
                "Refusing commit without acknowledge=true. Set the "
                "acknowledgement checkbox before restoring.",
            )
        try:
            result = commit_plan(
                sys_token, backup_id, collections, user, acknowledge=True
            )
        except Exception as exc:
            return err(502, "Restore failed: %s" % exc)
        return ok(result)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
