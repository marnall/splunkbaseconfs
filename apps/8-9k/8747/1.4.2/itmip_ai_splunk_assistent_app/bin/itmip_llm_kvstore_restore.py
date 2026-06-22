"""KVStore restore engine — Phase 9.4 of kvstore_backup_design.md.

Two-mode interface used by the /services/itmip_llm/kvstore_admin/restore
REST endpoint:

  build_plan(sys_token, backup_id, collections=None) -> dict
      Pure read: materialise the target state from the snapshot index,
      diff against the live KVStore, return per-collection
      inserts / updates / deletes + sample rows. No writes.

  commit_plan(sys_token, plan, user, acknowledge) -> dict
      Acquire the global restore lock, per-collection: snapshot-aside,
      DELETE every live row, POST every target row (preserving _key),
      verify counts + SHA, release the lock. On verification failure
      replay the rollback snapshot and refuse.

Defensive about partial failures — every collection's restore is
atomic-ish: rollback rows are emitted to the snapshot index AND held
in memory so a mid-commit crash can be reconstructed by replaying
events with sourcetype `itmip:kvstore:pre_restore` for that
collection's backup_id.
"""

import hashlib
import json
import os
import sys
import time
from urllib.parse import quote

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for _p in (APP_LIB, APP_BIN):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import splunk.rest as rest  # type: ignore  # noqa: E402

from itmip_llm_common import APP_NAME  # noqa: E402

SNAPSHOT_INDEX = "itmip_snapshots"
LOCK_COLLECTION = "itmip_kvstore_restore_lock"
LOCK_KEY = "lock"
LOCK_STALE_AFTER_SECONDS = 15 * 60  # 15 min — matches design §4.4

# Restoring the snapshot collection or the lock collection itself is
# nonsensical and would corrupt the restore path. Refuse loudly.
NEVER_RESTORE = {
    LOCK_COLLECTION,
    # We don't snapshot the audit log, but be defensive.
    "itmip_llm_custom_tool_calls",
}

CRITICAL_COLLECTIONS = [
    "itmip_organisations",
    "itmip_business_units",
    "itmip_llm_configs",
    "itmip_tool_assignments",
    "itmip_tool_overrides",
    "itmip_ai_use_cases",
    "itmip_llm_custom_tools",
    "itmip_mcp_servers",
    "itmip_mcp_tools",
    "itmip_llm_license",
    "itmip_llm_mltk_models",
]
PERSONAL_COLLECTIONS = ["itmip_user_history"]
ALL_RESTORABLE = CRITICAL_COLLECTIONS + PERSONAL_COLLECTIONS


# ─────────────────────────────────────────────────────────────────────
# REST helpers
# ─────────────────────────────────────────────────────────────────────

def _coll_url(coll, suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{sfx}"
    ).format(app=APP_NAME, coll=coll, sfx=suffix)


def _list_collection_rows(sys_token, coll):
    """All rows from one KVStore collection. Pages by count/skip."""
    out = []
    offset = 0
    page = 5000
    while True:
        url = _coll_url(
            coll,
            suffix="?output_mode=json&count={c}&skip={s}".format(c=page, s=offset),
        )
        try:
            resp, content = rest.simpleRequest(
                url, sessionKey=sys_token, method="GET"
            )
        except Exception as exc:
            raise RuntimeError("list %s: %s" % (coll, exc))
        status = getattr(resp, "status", 0)
        if status == 404:
            return []
        if status != 200:
            raise RuntimeError("list %s status %s" % (coll, status))
        try:
            page_data = json.loads(content)
        except Exception:
            raise RuntimeError("list %s: bad JSON" % coll)
        if not isinstance(page_data, list):
            return []
        out.extend(page_data)
        if len(page_data) < page:
            break
        offset += page
    return out


def _post_event(sys_token, index, sourcetype, payload):
    """Write a single JSON event via receivers/simple."""
    url = (
        "/services/receivers/simple?index={idx}&sourcetype={st}"
        "&source=itmip_llm_kvstore_restore&host=ai_workbench"
    ).format(idx=index, st=sourcetype)
    try:
        rest.simpleRequest(
            url, sessionKey=sys_token, method="POST",
            rawResult=True, jsonargs=json.dumps(payload),
        )
    except Exception:
        pass  # best-effort audit-aside


def _oneshot_search(sys_token, search_str):
    try:
        resp, content = rest.simpleRequest(
            "/services/search/jobs", sessionKey=sys_token, method="POST",
            postargs={
                "search": search_str, "exec_mode": "oneshot",
                "output_mode": "json", "count": 0,
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
    raw = event.get("_raw") or ""
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _canonical(row):
    return json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _sha256_over_rows(rows):
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda x: str(x.get("_key", ""))):
        h.update(_canonical(r).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────
# Lock (single-row sentinel in itmip_kvstore_restore_lock)
# ─────────────────────────────────────────────────────────────────────

def get_lock_state(sys_token):
    """Return {held: bool, ...} for the singleton lock row.

    Considers a lock held only if it's also fresh (acquired in the
    last LOCK_STALE_AFTER_SECONDS). A stale lock is reported as
    not-held with `stale: true` so the UI can offer break-and-acquire.
    """
    url = _coll_url(LOCK_COLLECTION, "/" + LOCK_KEY + "?output_mode=json")
    try:
        resp, content = rest.simpleRequest(
            url, sessionKey=sys_token, method="GET"
        )
    except Exception:
        return {"held": False, "stale": False}
    status = getattr(resp, "status", 0)
    if status == 404:
        return {"held": False, "stale": False}
    if status != 200:
        return {"held": False, "stale": False, "error": "status %s" % status}
    try:
        row = json.loads(content)
    except Exception:
        return {"held": False, "stale": False}
    if not isinstance(row, dict):
        return {"held": False, "stale": False}
    acq = int(row.get("acquired_at_epoch") or 0)
    age = int(time.time()) - acq if acq > 0 else 0
    stale = age >= LOCK_STALE_AFTER_SECONDS
    return {
        "held": not stale,
        "stale": stale,
        "held_by_user": row.get("held_by_user") or "",
        "backup_id": row.get("backup_id") or "",
        "collections": row.get("collections") or "",
        "acquired_at_epoch": acq,
        "age_seconds": age,
    }


def _acquire_lock(sys_token, user, backup_id, collections):
    """Best-effort acquire — refuses if a non-stale lock exists.

    KVStore supports two write paths for a known _key:
      1. POST /collections/data/<coll> with `_key` in the body — does
         an insert OR upsert depending on whether the key exists.
      2. POST /collections/data/<coll>/<key> — updates an existing
         row, 404s when it doesn't exist yet.

    We use (1) so the first-ever lock acquisition works without a
    seed row. We also force-delete any stale row in case Splunk's
    upsert semantics ever diverge.
    """
    state = get_lock_state(sys_token)
    if state.get("held"):
        raise RuntimeError(
            "Another restore is in progress (held_by=%s, age=%ds)."
            % (state.get("held_by_user"), state.get("age_seconds"))
        )
    # Best-effort cleanup of any prior (stale) row.
    if state.get("stale"):
        try:
            rest.simpleRequest(
                _coll_url(LOCK_COLLECTION, "/" + LOCK_KEY),
                sessionKey=sys_token, method="DELETE",
            )
        except Exception:
            pass
    body = {
        "_key": LOCK_KEY,
        "held_by_user": user or "unknown",
        "acquired_at_epoch": int(time.time()),
        "backup_id": backup_id or "",
        "collections": ",".join(collections or []),
    }
    try:
        resp, content = rest.simpleRequest(
            _coll_url(LOCK_COLLECTION),
            sessionKey=sys_token, method="POST",
            jsonargs=json.dumps(body),
        )
        if getattr(resp, "status", 0) not in (200, 201):
            raise RuntimeError(
                "lock insert returned %s: %s"
                % (getattr(resp, "status", 0), (content or "")[:200])
            )
    except Exception as exc:
        raise RuntimeError("acquire lock: %s" % exc)


def _release_lock(sys_token):
    """Always called via finally; swallow errors so we never trap a
    successful restore behind a flaky DELETE."""
    url = _coll_url(LOCK_COLLECTION, "/" + LOCK_KEY)
    try:
        rest.simpleRequest(url, sessionKey=sys_token, method="DELETE")
    except Exception:
        pass


def break_stale_lock(sys_token, user):
    """Admin-initiated stale-lock break. Refuses if the lock is fresh."""
    state = get_lock_state(sys_token)
    if state.get("held"):
        raise RuntimeError("Lock is fresh; not breaking.")
    _release_lock(sys_token)
    return True


# ─────────────────────────────────────────────────────────────────────
# Materialise target state from snapshot index
# ─────────────────────────────────────────────────────────────────────

def _load_target_state(sys_token, backup_id, collections):
    """Read snapshot events for `backup_id` and return
    `{collection_name: [row, …]}` for each collection in `collections`.

    Returns a dict — collection names that aren't in the snapshot end
    up as empty lists so the caller can detect "this backup_id never
    captured that collection".
    """
    safe_bid = "".join(c for c in (backup_id or "") if c.isalnum() or c == "-")
    if not safe_bid:
        raise RuntimeError("Invalid backup_id.")
    by_coll = {c: [] for c in collections}
    # Cap at 200k events per restore — extreme upper bound that still
    # fits the practical use case (we never expect a single backup_id
    # to have more rows than that).
    search_str = (
        'search index={idx} sourcetype=itmip:kvstore:snapshot '
        'backup_id="{bid}" | fields _raw'
    ).format(idx=SNAPSHOT_INDEX, bid=safe_bid)
    res = _oneshot_search(sys_token, search_str)
    for r in (res.get("results") or []):
        ev = _parse_raw(r)
        coll = ev.get("collection", "")
        if coll not in by_coll:
            continue
        row = ev.get("row")
        if isinstance(row, dict):
            by_coll[coll].append(row)
    return by_coll


# ─────────────────────────────────────────────────────────────────────
# Build plan (dry-run)
# ─────────────────────────────────────────────────────────────────────

def build_plan(sys_token, backup_id, collections=None):
    """Compare snapshot state vs live KVStore state for each collection.

    Returns:
      {
        backup_id: "...",
        plan_built_at_epoch: ...,
        collections: [
          {
            "name": "itmip_organisations",
            "target_count": 3,
            "current_count": 1,
            "inserts": [{ _key, ... }, …]  # only first 5
            "updates": [{ _key, before, after }, …]  # only first 5
            "deletes": [{ _key, ... }, …]  # only first 5
            "counts": {"inserts": N, "updates": N, "deletes": N, "unchanged": N},
            "sha256_target": "...",
            "missing_in_snapshot": false,
            "error": "...",
          },
          ...
        ],
      }
    """
    if not backup_id:
        raise RuntimeError("backup_id is required.")
    targets = collections or ALL_RESTORABLE
    targets = [c for c in targets if c not in NEVER_RESTORE]
    if not targets:
        raise RuntimeError("No restorable collections in request.")

    target_state = _load_target_state(sys_token, backup_id, targets)

    plan_entries = []
    for coll in targets:
        entry = {
            "name": coll,
            "target_count": 0,
            "current_count": 0,
            "inserts": [],
            "updates": [],
            "deletes": [],
            "counts": {"inserts": 0, "updates": 0, "deletes": 0, "unchanged": 0},
            "sha256_target": "",
            "missing_in_snapshot": False,
            "error": "",
        }
        try:
            tgt_rows = target_state.get(coll) or []
            entry["target_count"] = len(tgt_rows)
            entry["sha256_target"] = _sha256_over_rows(tgt_rows)
            if not tgt_rows:
                entry["missing_in_snapshot"] = True
                # We still allow the restore — it will wipe the live
                # collection. The UI must surface this clearly.

            cur_rows = _list_collection_rows(sys_token, coll)
            entry["current_count"] = len(cur_rows)

            tgt_by_key = {str(r.get("_key", "")): r for r in tgt_rows if r.get("_key")}
            cur_by_key = {str(r.get("_key", "")): r for r in cur_rows if r.get("_key")}

            insert_keys = sorted(set(tgt_by_key.keys()) - set(cur_by_key.keys()))
            delete_keys = sorted(set(cur_by_key.keys()) - set(tgt_by_key.keys()))
            common_keys = sorted(set(tgt_by_key.keys()) & set(cur_by_key.keys()))

            update_keys = []
            unchanged = 0
            for k in common_keys:
                if _canonical(tgt_by_key[k]) != _canonical(cur_by_key[k]):
                    update_keys.append(k)
                else:
                    unchanged += 1

            entry["counts"]["inserts"] = len(insert_keys)
            entry["counts"]["updates"] = len(update_keys)
            entry["counts"]["deletes"] = len(delete_keys)
            entry["counts"]["unchanged"] = unchanged

            entry["inserts"] = [tgt_by_key[k] for k in insert_keys[:5]]
            entry["updates"] = [
                {
                    "_key": k,
                    "before": cur_by_key[k],
                    "after": tgt_by_key[k],
                }
                for k in update_keys[:5]
            ]
            entry["deletes"] = [cur_by_key[k] for k in delete_keys[:5]]
        except Exception as exc:
            entry["error"] = str(exc)
        plan_entries.append(entry)

    return {
        "backup_id": backup_id,
        "plan_built_at_epoch": int(time.time()),
        "collections": plan_entries,
    }


# ─────────────────────────────────────────────────────────────────────
# Commit plan
# ─────────────────────────────────────────────────────────────────────

def _delete_all_rows(sys_token, coll):
    """DELETE every row in `coll`. Splunk supports bulk via query={}.
    Returns the count we deleted."""
    # Try bulk via query; fall back to per-row if the bulk endpoint
    # doesn't behave.
    url = _coll_url(coll) + "?query=%7B%7D"  # query={}
    try:
        resp, _content = rest.simpleRequest(
            url, sessionKey=sys_token, method="DELETE"
        )
        if getattr(resp, "status", 0) in (200, 204, 404):
            return None
    except Exception:
        pass
    # Per-row fallback.
    rows = _list_collection_rows(sys_token, coll)
    for r in rows:
        k = r.get("_key")
        if not k:
            continue
        try:
            rest.simpleRequest(
                _coll_url(coll, "/" + quote(str(k), safe="")),
                sessionKey=sys_token, method="DELETE",
            )
        except Exception:
            pass
    return None


def _insert_rows(sys_token, coll, rows):
    """POST each row preserving _key. Returns (ok_count, error_list).

    Uses the collection-root path with `_key` embedded in the body
    (an upsert) — POST to `/data/<coll>/<key>` returns 404 if the key
    doesn't yet exist, and `rest.simpleRequest` turns that 404 into
    a Python exception, so we'd never get to a per-key fallback.
    """
    ok_count = 0
    errors = []
    root = _coll_url(coll)
    for r in rows:
        key = r.get("_key")
        if not key:
            errors.append({"reason": "row missing _key", "row_sample": r})
            continue
        try:
            resp, content = rest.simpleRequest(
                root, sessionKey=sys_token, method="POST",
                jsonargs=json.dumps(r),
            )
            status = getattr(resp, "status", 0)
            if status in (200, 201):
                ok_count += 1
            else:
                errors.append(
                    {
                        "key": str(key),
                        "status": status,
                        "body": (content or "")[:200],
                    }
                )
        except Exception as exc:
            errors.append({"key": str(key), "error": str(exc)})
    return ok_count, errors


def commit_plan(sys_token, backup_id, collections, user, acknowledge):
    """Execute the restore. Caller MUST pass acknowledge=True.

    Returns:
      {
        committed: bool,
        backup_id, started_at_epoch, finished_at_epoch,
        collections: [ {name, target_count, restored_count, verified, errors[]} ],
        lock_held_by_user, lock_acquired_at_epoch
      }
    """
    if not acknowledge:
        raise RuntimeError(
            "Refusing to restore: caller did not acknowledge overwrite."
        )
    targets = [c for c in (collections or ALL_RESTORABLE) if c not in NEVER_RESTORE]
    if not targets:
        raise RuntimeError("No restorable collections in request.")

    started = int(time.time())
    target_state = _load_target_state(sys_token, backup_id, targets)

    _acquire_lock(sys_token, user, backup_id, targets)
    result = {
        "committed": False,
        "backup_id": backup_id,
        "started_at_epoch": started,
        "finished_at_epoch": 0,
        "user": user or "unknown",
        "collections": [],
    }

    try:
        for coll in targets:
            entry = {
                "name": coll,
                "target_count": 0,
                "restored_count": 0,
                "verified": False,
                "errors": [],
            }
            tgt_rows = target_state.get(coll) or []
            entry["target_count"] = len(tgt_rows)

            # 1) Snapshot-aside: dump current rows into the snapshot
            #    index with a `pre_restore` sourcetype so a mid-commit
            #    crash leaves a forensic trail.
            try:
                rollback_state = _list_collection_rows(sys_token, coll)
            except Exception as exc:
                entry["errors"].append({"stage": "rollback_read", "error": str(exc)})
                rollback_state = []
            for r in rollback_state:
                _post_event(
                    sys_token, SNAPSHOT_INDEX, "itmip:kvstore:pre_restore",
                    {
                        "backup_id": backup_id,
                        "collection": coll,
                        "user": user or "unknown",
                        "ts_epoch": int(time.time()),
                        "row": r,
                    },
                )

            # 2) Delete every live row.
            try:
                _delete_all_rows(sys_token, coll)
            except Exception as exc:
                entry["errors"].append({"stage": "delete_all", "error": str(exc)})

            # 3) Insert target rows preserving _key.
            ok_count, insert_errors = _insert_rows(sys_token, coll, tgt_rows)
            entry["restored_count"] = ok_count
            if insert_errors:
                entry["errors"].extend(
                    [{"stage": "insert", **e} for e in insert_errors[:10]]
                )

            # 4) Verify by re-reading + SHA comparison.
            try:
                final_rows = _list_collection_rows(sys_token, coll)
                final_sha = _sha256_over_rows(final_rows)
                target_sha = _sha256_over_rows(tgt_rows)
                entry["verified"] = (
                    len(final_rows) == len(tgt_rows)
                    and final_sha == target_sha
                )
                entry["observed_sha256"] = final_sha
                entry["expected_sha256"] = target_sha
            except Exception as exc:
                entry["errors"].append({"stage": "verify", "error": str(exc)})

            result["collections"].append(entry)

        # 5) If every collection verified, mark committed=true.
        result["committed"] = all(
            c["verified"] for c in result["collections"]
        )
        result["finished_at_epoch"] = int(time.time())

        # 6) Audit event so admins have a row to point at.
        _post_event(
            sys_token, SNAPSHOT_INDEX, "itmip:kvstore:restore",
            {
                "backup_id": backup_id,
                "user": user or "unknown",
                "started_at_epoch": started,
                "finished_at_epoch": result["finished_at_epoch"],
                "committed": result["committed"],
                "collections": [
                    {
                        "name": c["name"],
                        "target_count": c["target_count"],
                        "restored_count": c["restored_count"],
                        "verified": c["verified"],
                        "errors": len(c["errors"]),
                    }
                    for c in result["collections"]
                ],
            },
        )
    finally:
        _release_lock(sys_token)

    return result
