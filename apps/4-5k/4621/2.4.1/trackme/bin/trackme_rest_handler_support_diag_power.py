#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_support_diag_power.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

"""
TrackMe Support Diagnostic REST Handler
---------------------------------------

Generates a diagnostic archive (.tgz) that TrackMe support engineers can
inspect when customers report issues. Two modes:

1. entity  — for a given tenant + component + list of object ids, exports:
             - entity record(s) from load_component_data
             - 7-day mstats window from the tenant metric index
             - latest summary/notable event per sourcetype
2. global  — system-wide snapshot:
             - central KV Store collections (tenants, exec_summary,
               entities_summary)
             - 24h scheduler skipping & performance reports
             - 24h TrackMe runtime metrics

The archive is written to $SPLUNK_HOME/etc/apps/trackme/backup/downloads/
and exposed via the same token-based download pattern already used by the
backup_and_restore handler.

Capability: trackmepoweroperations (admin + power roles).
"""

# Built-in libraries
import base64
import csv
import io
import json
import os
import shutil
import socket
import sys
import tarfile
import threading
import time
import uuid

# Third-party libraries
import requests  # noqa: F401  (kept for parity with other handlers)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test  # noqa: F401

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.support_diag",
    "trackme_rest_api_support_diag.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_getloglevel,
    trackme_idx_for_tenant,
    trackme_parse_describe_flag,
    trackme_reqinfo,
)

# import TrackMe get data libs
from trackme_libs_get_data import (
    get_full_kv_collection,
)

# import Splunk libs
import splunklib.client as client


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

VALID_COMPONENTS = {"dsm", "dhm", "mhm", "flx", "fqm", "wlk"}
MAX_ENTITIES_PER_REQUEST = 20

# Archive directory (under $SPLUNK_HOME/etc/apps/trackme/). Sibling of "backup/".
# Expired files in this directory are purged by the periodic
# trackmegeneralhealthmanager task, not by this handler.
DIAG_DIR_NAME = "diag"

# -----------------------------------------------------------------------------
# Async job state
# -----------------------------------------------------------------------------
#
# Support diag generation is dispatched to a background thread so that the
# initial POST /generate returns immediately (a {job_id}), well under any
# customer reverse-proxy idle timeout. The UI then polls GET /status until
# the job reaches a terminal state and fetches the archive with the existing
# GET /generate?download_token=<t> endpoint.
#
# Lifecycle: queued -> running -> complete | error | cancelled
#
# Pattern mirrors trackme_libs_ai.py (kv_trackme_ai_jobs).

_KV_JOBS_COLLECTION = "kv_trackme_support_diag_jobs"
# Generous default ceiling — large customer environments with many tenants
# and chatty _internal indexes can take well over 15 minutes for a global
# diag (KO collection per tenant + 7-day errors search are the usual long
# poles). 60 minutes is the cap before Phase-2 cleanup gives up on a
# worker; the heartbeat below keeps last_activity fresh so this only
# fires when the worker is genuinely dead, not just slow on one step.
_DEFAULT_JOB_TIMEOUT_SECONDS = 3600       # 60 min ceiling per job
_JOB_TTL_SECONDS = 1800                   # finished jobs auto-purge after 30 min
_STALE_RUNNING_BUFFER_SECONDS = 300       # grace beyond job timeout before declaring orphan
_HEARTBEAT_INTERVAL_SECONDS = 30          # how often the worker bumps last_activity
_CONCURRENCY_LIMIT = 3                    # max concurrent support-diag workers
_TERMINAL_STATUSES = {"complete", "error", "cancelled"}

# All concurrency and cancellation state lives in the
# kv_trackme_support_diag_jobs collection so it's correct across the
# multiple persistent REST-handler processes Splunk may spawn (each of
# which would otherwise own its own in-process copy of these globals).
# The per-process lock below only guards the check-then-insert window
# *within* a single process — it does not and cannot substitute for the
# shared KV view. In the tiny cross-process race that remains, the worst
# case is that we briefly run one extra job beyond the configured limit.


def _get_jobs_collection(service):
    return service.kvstore[_KV_JOBS_COLLECTION]


def _count_active_jobs(service):
    """Count jobs currently consuming a worker slot (queued or running)."""
    try:
        rows = _get_jobs_collection(service).data.query(
            query=json.dumps({"status": {"$in": ["queued", "running"]}})
        )
        # splunklib returns a list-ish; len() works, and we defensively
        # fall back to iterating if not.
        try:
            return len(rows)
        except TypeError:
            return sum(1 for _ in rows)
    except Exception as e:
        logger.debug(f"support_diag: _count_active_jobs failed: {e}")
        return 0


def _is_cancelled(service, job_id):
    """
    Has this job been cancelled? Source of truth is the KV record's
    status field, which the DELETE /cancel handler flips to "cancelled"
    and which is visible to any worker thread regardless of which
    persistent process handled the cancel call.
    """
    if not job_id:
        return False
    try:
        rec = _get_jobs_collection(service).data.query_by_id(job_id)
        return str((rec or {}).get("status") or "") == "cancelled"
    except Exception:
        return False


def _purge_expired_jobs(service):
    """
    Mirror of trackme_libs_ai _purge_expired_jobs: drop finished jobs past TTL
    and transition orphaned running jobs to error.
    """
    now = time.time()
    cutoff = now - _JOB_TTL_SECONDS
    # Phase 1: drop finished jobs past TTL. Target terminal statuses
    # explicitly — "$ne: running" also matches queued jobs, which are
    # still active and must not be wiped.
    try:
        collection = _get_jobs_collection(service)
        finished = collection.data.query(
            query=json.dumps({"status": {"$in": list(_TERMINAL_STATUSES)}})
        )
        for job in finished:
            try:
                created_at = float(job.get("created_at", 0))
            except (ValueError, TypeError):
                created_at = 0.0
            try:
                last_activity = float(job.get("last_activity", 0))
            except (ValueError, TypeError):
                last_activity = 0.0
            reference_time = max(created_at, last_activity) if last_activity > 0 else created_at
            if reference_time > 0 and reference_time < cutoff:
                jid = job.get("_key", "")
                if jid:
                    try:
                        collection.data.delete(json.dumps({"_key": jid}))
                    except Exception:
                        pass
    except Exception:
        pass
    # Phase 2: error-mark stale running jobs (orphaned workers)
    try:
        collection = _get_jobs_collection(service)
        running = collection.data.query(query=json.dumps({"status": "running"}))
        for job in running:
            try:
                created_at = float(job.get("created_at", 0))
            except (ValueError, TypeError):
                created_at = 0.0
            try:
                last_activity = float(job.get("last_activity", 0))
            except (ValueError, TypeError):
                last_activity = 0.0
            reference_time = max(created_at, last_activity) if last_activity > 0 else created_at
            if reference_time <= 0:
                continue
            job_timeout = float(job.get("timeout", _DEFAULT_JOB_TIMEOUT_SECONDS))
            if now > reference_time + job_timeout + _STALE_RUNNING_BUFFER_SECONDS:
                jid = job.get("_key", "")
                try:
                    collection.data.update(
                        jid,
                        json.dumps(
                            {
                                "status": "error",
                                "error": "Job timed out — worker thread may have terminated unexpectedly.",
                                "last_activity": now,
                            }
                        ),
                    )
                except Exception:
                    pass
    except Exception:
        pass


def _create_job(service, mode, tenant_id="", component="", object_ids=None, user="unknown",
                timeout=None, anonymise_tenants=False):
    job_id = uuid.uuid4().hex
    now = time.time()
    record = {
        "_key": job_id,
        "status": "queued",
        "mode": mode,
        "tenant_id": tenant_id or "",
        "component": component or "",
        "requested_objects": len(object_ids or []),
        "progress_message": "queued",
        "download_token": "",
        "filename": "",
        "error": "",
        "anonymise_tenants": "true" if anonymise_tenants else "false",
        # tenant_mapping is populated by the worker when anonymise_tenants
        # is true; it's returned via GET /status so the UI can show the
        # real -> anon map to the user (the archive itself never contains
        # this mapping, otherwise anonymisation would be pointless).
        "tenant_mapping": "",
        "user": user or "unknown",
        "created_at": now,
        "last_activity": now,
        "timeout": float(timeout if timeout is not None else _DEFAULT_JOB_TIMEOUT_SECONDS),
    }
    try:
        _get_jobs_collection(service).data.insert(json.dumps(record))
    except Exception as e:
        logger.error(f"support_diag: failed to insert job record: {e}")
        raise
    _purge_expired_jobs(service)
    return job_id


def _update_job(service, job_id, **kwargs):
    """
    Update job record fields. Always bumps last_activity.

    Splunk KV Store's POST-to-keyed-endpoint (what splunklib's
    collection.data.update() calls under the hood) performs a full
    document replacement, NOT a partial merge — sending only the changed
    fields wipes everything else (status, created_at, mode, ...). Every
    other TrackMe handler that updates a KV record therefore does
    read-modify-write with the full record. We do the same here.
    """
    if not job_id:
        return
    try:
        collection = _get_jobs_collection(service)
        # Read existing record so the write preserves unrelated fields.
        record = {}
        try:
            existing = collection.data.query_by_id(job_id)
            if isinstance(existing, dict):
                record = dict(existing)
        except Exception:
            pass
        # _key is supplied via the URL and should not appear in the body.
        record.pop("_key", None)
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                record[k] = json.dumps(v)
            elif v is None:
                record[k] = ""
            elif isinstance(v, bool):
                record[k] = str(v).lower()
            else:
                record[k] = v
        # Always mark activity so stale-job detection sees movement.
        record["last_activity"] = time.time()
        collection.data.update(job_id, json.dumps(record))
    except Exception as e:
        logger.error(f"support_diag: failed to update job {job_id}: {e}")


def _get_job(service, job_id):
    try:
        return _get_jobs_collection(service).data.query_by_id(job_id)
    except Exception:
        return None


class _HeartbeatThread(threading.Thread):
    """
    Bumps the job record's last_activity every _HEARTBEAT_INTERVAL_SECONDS
    while the worker is alive. Without this, a single long step (e.g. a
    7-day errors search on a chatty _internal index, or knowledge-objects
    fetch for a very large tenant) would let last_activity go stale and
    Phase-2 of _purge_expired_jobs would mistakenly mark the still-running
    worker as an orphan.
    """

    def __init__(self, service, job_id, interval=_HEARTBEAT_INTERVAL_SECONDS):
        super(_HeartbeatThread, self).__init__(
            daemon=True, name=f"support_diag_heartbeat_{job_id[:8]}",
        )
        self._service = service
        self._job_id = job_id
        self._interval = interval
        # NOTE: _do not_ name this `_stop` — that shadows the internal
        # threading.Thread._stop() method which the join() machinery
        # calls during cleanup, raising TypeError ("Event is not
        # callable") and skipping internal state teardown.
        self._stop_event = threading.Event()

    def stop(self):
        """Signal the heartbeat to exit on the next wait tick."""
        self._stop_event.set()

    def stop_and_join(self, timeout=10):
        """
        Signal stop AND wait for the thread to exit, so any in-flight
        read-modify-write completes before the caller's terminal
        _update_job runs. Without this, a heartbeat write that lands
        after the worker's terminal write would clobber status back to
        "running".
        """
        self._stop_event.set()
        try:
            self.join(timeout=timeout)
        except Exception:
            pass

    def run(self):
        # Event.wait returns True when set() is called and False on
        # timeout — so this loops every `interval` seconds until stopped.
        while not self._stop_event.wait(self._interval):
            try:
                # _update_job with no kwargs still bumps last_activity
                # via its read-modify-write pass; cheap enough at 30s.
                _update_job(self._service, self._job_id)
            except Exception:
                # Best-effort. If KV is unreachable the worker has bigger
                # problems; the next tick will retry.
                pass


def _extract_query_arg(request_info, key):
    """Best-effort extraction of a query-string arg across Splunk versions."""
    try:
        if hasattr(request_info, "query") and request_info.query:
            if isinstance(request_info.query, dict):
                v = request_info.query.get(key)
                if v is not None:
                    return str(v).strip()
            elif isinstance(request_info.query, list) and request_info.query:
                first = request_info.query[0]
                if isinstance(first, dict) and key in first:
                    return str(first[key]).strip()
        if hasattr(request_info, "raw_args"):
            raw_args = request_info.raw_args
            if isinstance(raw_args, dict) and key in raw_args:
                return str(raw_args[key]).strip()
    except Exception as e:
        logger.debug(f"support_diag: _extract_query_arg({key}) failed: {e}")
    return ""


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_payload(request_info):
    """Extract and JSON-decode the request payload. Returns dict or None."""
    try:
        raw = request_info.raw_args.get("payload")
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return None
            return json.loads(raw)
        if isinstance(raw, dict):
            return raw
        return None
    except Exception as e:
        logger.error(f"_parse_payload failed: {e}")
        return None


def _write_csv(path, reader, max_rows=500000):
    """
    Write results from a JSONResultsReader-like iterator to a CSV file.

    Returns the number of rows written.
    """
    rows_written = 0
    truncated = False
    headers = []
    header_set = set()

    # Buffer rows so we can emit a stable header ordering; bound at max_rows.
    buffer_rows = []
    for item in reader:
        if not isinstance(item, dict):
            continue
        if any(k.startswith("ERROR") for k in item.keys()):
            continue
        # drop internal splunk-meta fields
        row = {k: v for k, v in item.items() if not k.startswith("_bkt") and k != "_cd"}
        buffer_rows.append(row)
        for k in row.keys():
            if k not in header_set:
                header_set.add(k)
                headers.append(k)
        rows_written += 1
        if rows_written >= max_rows:
            truncated = True
            break

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in buffer_rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in headers})

    return {"rows": rows_written, "truncated": truncated}


def _run_search_to_csv(service, query, earliest, latest, csv_path, max_rows=500000):
    """Execute an SPL search and write the results to csv_path."""
    kwargs = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        # count=0 returns all rows. This helper writes results to CSV up to
        # max_rows (default 500k); the Splunk default of 100 would silently
        # cap the export regardless of max_rows.
        "count": 0,
    }
    logger.info(
        f'support_diag: running search, csv_path="{csv_path}", earliest="{earliest}", '
        f'latest="{latest}", query="{query[:500]}"'
    )
    reader = run_splunk_search(service, query, kwargs, max_retries=3, sleep_time=5)
    stats = _write_csv(csv_path, reader, max_rows=max_rows)
    logger.info(
        f'support_diag: search complete, csv_path="{csv_path}", rows={stats["rows"]}, '
        f'truncated={stats["truncated"]}'
    )
    return stats


def _escape_spl_value(value):
    """Escape a user-provided value for inclusion as a double-quoted SPL token."""
    if value is None:
        return ""
    s = str(value)
    # Defensive: strip control characters and escape double quotes + backslashes
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = "".join(ch for ch in s if ord(ch) >= 0x20)
    return s


def _load_component_data(session_key, splunkd_uri, tenant_id, component, object_ids):
    """
    Call /services/trackme/v2/component/load_component_data for a batch of
    object_ids. Returns the list of matched records.

    The endpoint is GET-only (handler exposes get_load_component_data, not
    post_load_component_data) — POST requests return 404. Parameters are
    passed as query string, matching the React UI caller.
    """
    # Normalise the splunkd URI before concatenating:
    #   - prepend "https://" only if no scheme is present
    #   - rewrite a bare "http://" scheme to "https://" (splunkd REST is TLS)
    base = splunkd_uri or ""
    if base.startswith("http://"):
        base = "https://" + base[len("http://"):]
    elif not base.startswith("https://"):
        base = f"https://{base}"
    url = f"{base}/services/trackme/v2/component/load_component_data"
    headers = {"Authorization": f"Splunk {session_key}"}
    params = {
        "tenant_id": tenant_id,
        "component": component,
        "page": "1",
        "size": "10000",
        "pagination_mode": "local",
    }
    matches = []
    try:
        resp = requests.get(url, headers=headers, params=params, verify=False, timeout=120)
        if not resp.ok:
            logger.warning(
                f"support_diag: load_component_data returned HTTP {resp.status_code}, "
                f"body={resp.text[:500]}"
            )
            return matches
        data = resp.json()
        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # Try common shapes. Splunk's framework sometimes nests under "payload".
            payload = data.get("payload", data)
            if isinstance(payload, list):
                records = payload
            elif isinstance(payload, dict):
                records = (
                    payload.get("results")
                    or payload.get("data")
                    or payload.get("records")
                    or []
                )
        wanted = set(object_ids)
        for rec in records:
            if not isinstance(rec, dict):
                continue
            if (
                rec.get("object_id") in wanted
                or rec.get("object") in wanted
                or rec.get("_key") in wanted
            ):
                matches.append(rec)
        logger.info(
            f'support_diag: load_component_data returned {len(records)} records, '
            f'{len(matches)} matched requested object_ids'
        )
    except Exception as e:
        logger.error(f"support_diag: load_component_data call failed: {e}")
    return matches


def _fetch_tenant_knowledge_objects(session_key, splunkd_uri, tenant_id):
    """
    POST /services/trackme/v2/configuration/get_tenant_knowledge_objects
    Returns the decoded JSON (a list of KO records) or raises on error.

    Mirrors the call shape used by trackme_rest_handler_backup_and_restore.
    """
    base = splunkd_uri or ""
    if base.startswith("http://"):
        base = "https://" + base[len("http://"):]
    elif not base.startswith("https://"):
        base = f"https://{base}"
    url = f"{base}/services/trackme/v2/configuration/get_tenant_knowledge_objects"
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }
    # Generous per-tenant timeout — large tenants with hundreds of saved
    # searches / lookup definitions can take several minutes to walk.
    resp = requests.post(
        url,
        headers=headers,
        data=json.dumps({"tenant_id": tenant_id}),
        verify=False,
        timeout=1200,
    )
    resp.raise_for_status()
    return resp.json()


def _build_tenant_mapping(vtenants_records, seed_tenant_id=None):
    """
    Build a {real_value: anon_alias} map that covers both tenant_id and
    tenant_alias for every tenant we've seen. Anon aliases are stable
    within one archive (indexed + short hex tail) so different tenants
    can still be told apart downstream when support is debugging.

    seed_tenant_id is the tenant selected in entity mode — it's added
    even if the caller didn't pass a vtenants listing (e.g. because the
    central KV dump was skipped).
    """
    mapping = {}
    ids_seen = []
    if seed_tenant_id:
        ids_seen.append(seed_tenant_id)
    for rec in vtenants_records or []:
        if not isinstance(rec, dict):
            continue
        tid = str(rec.get("tenant_id") or "").strip()
        if tid and tid not in ids_seen:
            ids_seen.append(tid)

    for idx, tid in enumerate(ids_seen):
        anon = f"tenant_anon_{idx:04d}_{uuid.uuid4().hex[:6]}"
        mapping[tid] = anon
        # Anonymise tenant_alias as well when it's not already the id;
        # pin it to the same anon so grepping the archive stays sane.
        alias = None
        for rec in vtenants_records or []:
            if (
                isinstance(rec, dict)
                and str(rec.get("tenant_id") or "").strip() == tid
            ):
                alias = str(rec.get("tenant_alias") or "").strip()
                break
        if alias and alias != tid and alias not in mapping:
            mapping[alias] = anon
    return mapping


def _apply_anonymisation(staging_dir, mapping):
    """
    Replace every key in `mapping` with its value across all text files
    in `staging_dir` (recursively), and rename files whose basename
    contains any key. Sort by key length desc so overlapping names
    (e.g. "prod" vs "production") don't cross-corrupt.
    """
    if not mapping or not os.path.isdir(staging_dir):
        return
    items = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)

    # Step 1 — rename files first, while the original names still match.
    for root, _dirs, files in os.walk(staging_dir):
        for fname in files:
            new_name = fname
            for real, anon in items:
                if real and real in new_name:
                    new_name = new_name.replace(real, anon)
            if new_name != fname:
                try:
                    os.rename(
                        os.path.join(root, fname),
                        os.path.join(root, new_name),
                    )
                except Exception as e:
                    logger.warning(
                        f'support_diag: anonymise rename failed: '
                        f'{fname} -> {new_name}: {e}'
                    )

    # Step 2 — rewrite text file contents.
    text_exts = {".json", ".csv", ".txt", ".log"}
    for root, _dirs, files in os.walk(staging_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in text_exts:
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                new_content = content
                for real, anon in items:
                    if real:
                        new_content = new_content.replace(real, anon)
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(new_content)
            except Exception as e:
                logger.warning(
                    f'support_diag: anonymise rewrite failed for {path}: {e}'
                )


def _record_step_failure(summary, step, error):
    """
    Append a non-fatal step failure to summary["step_failures"]. The
    archive is still produced; the UI uses this list to warn the user
    that part of the diag didn't make it.
    """
    if not isinstance(summary.get("step_failures"), list):
        summary["step_failures"] = []
    summary["step_failures"].append({"step": step, "error": str(error)[:500]})


def _normalise_knowledge_objects(raw):
    """
    Normalise the get_tenant_knowledge_objects response into the same
    {title: {type, title, properties, definition, ...}} shape the
    backup archive uses, so downstream tooling treats both the same way.
    """
    out = {}
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        ko_type = item.get("type")
        title = item.get("title")
        if not title:
            continue
        record = {
            "type": ko_type,
            "title": title,
            "properties": item.get("properties", {}),
        }
        if ko_type in ("savedsearches", "macros"):
            record["definition"] = item.get("definition")
        elif ko_type == "alerts":
            record["definition"] = item.get("definition")
            record["alert_properties"] = item.get("alert_properties")
        elif ko_type == "lookup_definitions":
            record["collection"] = item.get("collection")
            record["fields_list"] = item.get("fields_list")
        out[title] = record
    return out


# -----------------------------------------------------------------------------
# Handler
# -----------------------------------------------------------------------------


class TrackMeHandlerSupportDiag_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSupportDiag_v2, self).__init__(
            command_line, command_arg, logger
        )

    # -----------------------------
    # describe
    # -----------------------------

    def get_resource_group_desc_support_diag(self, request_info, **kwargs):
        response = {
            "resource_group_name": "support_diag",
            "resource_group_desc": (
                "Endpoints to generate a support diagnostic archive (.tgz) capturing "
                "either entity-scoped or system-wide state to accelerate TrackMe "
                "support triage."
            ),
        }
        return {"payload": response, "status": 200}

    # -----------------------------
    # POST /trackme/v2/support_diag/generate
    # -----------------------------

    def post_generate(self, request_info, **kwargs):
        """
        Start asynchronous generation of a diagnostic archive.

        Request JSON body:
            {
              "mode": "entity" | "global",
              "tenant_id": "...",            # entity mode
              "component": "dsm|dhm|mhm|flx|fqm|wlk",  # entity mode
              "object_ids": ["...", ...]     # entity mode, max 20
            }

        Response (202 Accepted):
            { "job_id": "<hex>", "status": "queued" }

        The request returns immediately. Poll GET /support_diag/status?job_id=<id>
        for progress and, on completion, retrieve the archive via GET
        /support_diag/generate?download_token=<t>.
        """

        # describe support
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "This endpoint kicks off asynchronous generation of a "
                        "TrackMe support diagnostic archive (.tgz) that "
                        "support engineers can inspect when investigating "
                        "customer issues. Two modes are supported: 'entity' "
                        "scopes the archive to a specific tenant + component "
                        "+ list of object_ids (entity records, 7-day mstats "
                        "window, latest summary/notable event per "
                        "sourcetype); 'global' captures a system-wide "
                        "snapshot (central KV collections, 24h scheduler / "
                        "performance reports, runtime metrics). Returns "
                        "{job_id, status='queued'} immediately so the "
                        "caller does not block on the (potentially "
                        "minutes-long) collection step. Poll "
                        "support_diag/status?job_id=<id> for progress; on "
                        "status=complete fetch the archive via "
                        "support_diag/generate?download_token=<t>."
                    ),
                    "resource": "support_diag/generate",
                    "methods": ["POST"],
                    "resource_desc": (
                        "Start asynchronous generation of a support diagnostic "
                        "archive. Returns {job_id, status} immediately; poll "
                        "support_diag/status?job_id=<id> for progress and fetch "
                        "the archive via support_diag/generate?download_token=<t> "
                        "when the job reports status=complete."
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/support_diag/generate" '
                        "mode=post body=\"{'mode':'global'}\""
                    ),
                    "options": [
                        {
                            "mode": "REQUIRED. One of: 'entity' or 'global'",
                            "tenant_id": "REQUIRED when mode=entity. The tenant identifier scoping the entity-mode capture",
                            "component": "REQUIRED when mode=entity. One of: dsm, dhm, mhm, flx, fqm, wlk",
                            "object_ids": "REQUIRED when mode=entity. List of entity object_ids to capture (max 20 entries)",
                            "anonymise_tenants": "OPTIONAL. When truthy, replaces real tenant identifiers with anonymised tokens in the archive and surfaces the mapping via support_diag/status. Accepts booleans, ints, or string forms ('1', 'true', 'yes', 'on'). Defaults to false",
                        }
                    ],
                },
                "status": 200,
            }

        try:
            # loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            payload = _parse_payload(request_info) or {}
            mode = str(payload.get("mode", "")).strip().lower()

            if mode not in ("entity", "global"):
                return {
                    "payload": {"error": "mode must be one of: entity, global"},
                    "status": 400,
                }

            tenant_id = ""
            component = ""
            object_ids = []

            # Optional anonymisation. Accepts booleans, ints, or common
            # string forms so the wire contract is forgiving.
            raw_anon = payload.get("anonymise_tenants")
            if isinstance(raw_anon, bool):
                anonymise_tenants = raw_anon
            elif isinstance(raw_anon, (int, float)):
                anonymise_tenants = bool(raw_anon)
            elif isinstance(raw_anon, str):
                anonymise_tenants = raw_anon.strip().lower() in ("1", "true", "yes", "on")
            else:
                anonymise_tenants = False

            if mode == "entity":
                raw_tenant = payload.get("tenant_id")
                tenant_id = str(raw_tenant).strip() if raw_tenant is not None else ""
                raw_component = payload.get("component")
                component = (
                    str(raw_component).strip().lower() if raw_component is not None else ""
                )
                raw_ids = payload.get("object_ids") or []
                if isinstance(raw_ids, str):
                    raw_ids = [s.strip() for s in raw_ids.split(",") if s.strip()]
                if not isinstance(raw_ids, list):
                    raw_ids = []
                object_ids = [str(x).strip() for x in raw_ids if str(x).strip()]

                if not tenant_id:
                    return {"payload": {"error": "tenant_id is required for entity mode"}, "status": 400}
                if component not in VALID_COMPONENTS:
                    return {
                        "payload": {
                            "error": f"component must be one of: {', '.join(sorted(VALID_COMPONENTS))}"
                        },
                        "status": 400,
                    }
                if len(object_ids) == 0:
                    return {"payload": {"error": "object_ids must not be empty for entity mode"}, "status": 400}
                if len(object_ids) > MAX_ENTITIES_PER_REQUEST:
                    return {
                        "payload": {
                            "error": f"object_ids limited to {MAX_ENTITIES_PER_REQUEST} entries, got {len(object_ids)}"
                        },
                        "status": 400,
                    }

            # Connect once here just to create the job record; the worker
            # thread will reconnect with a fresh client of its own.
            splunkd_port = request_info.server_rest_port
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=60,
            )

            # Self-heal before the capacity check. If previous workers
            # crashed without flipping their records to a terminal
            # status, they'd still count against _count_active_jobs and
            # the gate below would permanently return 429 with no path
            # out (_create_job only runs once we're past the gate).
            # Running the purge here gives stale-job cleanup a chance
            # to fire on every incoming request.
            _purge_expired_jobs(service)

            # Bounce early if the global pool is at capacity. We count
            # active (queued|running) records in the shared KV collection
            # so the limit is honoured across Splunk's persistent process
            # pool rather than per-process.
            if _count_active_jobs(service) >= _CONCURRENCY_LIMIT:
                return {
                    "payload": {
                        "error": (
                            f"Support diag capacity reached "
                            f"({_CONCURRENCY_LIMIT} concurrent generations). "
                            f"Please retry shortly."
                        )
                    },
                    "status": 429,
                }

            user = getattr(request_info, "user", "unknown")
            try:
                job_id = _create_job(
                    service,
                    mode=mode,
                    tenant_id=tenant_id,
                    component=component,
                    object_ids=object_ids,
                    user=user,
                    anonymise_tenants=anonymise_tenants,
                )
            except Exception as e:
                logger.exception(f"support_diag: failed to create job record: {e}")
                return {
                    "payload": {"error": "Failed to enqueue support diag job"},
                    "status": 500,
                }

            # Capture everything the worker needs so it can run detached from
            # this request. session_key is what the KV/search calls use;
            # server_rest_uri is needed by the internal vtenants/component
            # REST helpers.
            worker_args = {
                "job_id": job_id,
                "mode": mode,
                "tenant_id": tenant_id,
                "component": component,
                "object_ids": list(object_ids),
                "anonymise_tenants": anonymise_tenants,
                "user": user,
                "session_key": request_info.session_key,
                "system_authtoken": request_info.system_authtoken,
                "server_rest_uri": request_info.server_rest_uri,
                "server_rest_port": splunkd_port,
                "log_level": loglevel,
            }

            # IMPORTANT: if Thread construction or start() raises, we
            # must flip the job record out of the "queued" bucket or it
            # will keep counting against the concurrency limit forever
            # (the worker's finally block is the only other place that
            # would write a terminal status, and it never runs if the
            # thread didn't start).
            try:
                thread = threading.Thread(
                    target=self._worker_run, kwargs=worker_args, daemon=True,
                    name=f"support_diag_worker_{job_id[:8]}",
                )
                thread.start()
            except Exception as e:
                try:
                    _update_job(
                        service, job_id,
                        status="error",
                        error="worker thread failed to start",
                        progress_message="error",
                    )
                except Exception:
                    pass
                logger.exception(
                    f'support_diag: failed to spawn worker thread, job_id="{job_id}": {e}'
                )
                return {
                    "payload": {"error": "Failed to start support diag worker"},
                    "status": 500,
                }

            logger.info(
                f'support_diag: job enqueued, job_id="{job_id}", mode="{mode}", '
                f'tenant_id="{tenant_id}", component="{component}", '
                f'requested_objects={len(object_ids)}, user="{user}"'
            )

            return {
                "payload": {"job_id": job_id, "status": "queued"},
                "status": 202,
            }

        except Exception as e:
            logger.exception(f"support_diag: post_generate failed: {e}")
            return {
                "payload": {
                    "error": (
                        "support_diag generation failed — see "
                        "trackme_rest_api_support_diag.log for details"
                    )
                },
                "status": 500,
            }

    # -----------------------------
    # Worker (runs in a daemon thread)
    # -----------------------------

    def _worker_run(self, job_id, mode, tenant_id, component, object_ids, user,
                    session_key, system_authtoken, server_rest_uri, server_rest_port,
                    log_level, anonymise_tenants=False):
        """
        Background worker: runs the actual diag collection, builds the archive,
        and updates the job record with progress / terminal status.

        Partial-success: if individual collection steps fail (search timeout,
        single tenant KO fetch error, etc.) they are recorded into
        summary["step_failures"] and the worker keeps going. The archive is
        always built with whatever was successfully collected and the job
        ends status=complete with partial=true. The job only ends
        status=error if a fatal infrastructure problem prevents writing
        the archive at all (e.g. cannot write to disk, cannot tar).
        """
        try:
            logger.setLevel(log_level)
        except Exception:
            pass

        staging_dir = None
        service = None
        heartbeat = None

        # Minimal request_info shim so the existing _collect_* methods — which
        # pull a couple of fields off request_info — keep working inside the
        # worker without us having to plumb every field through as a kwarg.
        class _ReqInfoShim(object):
            pass

        req = _ReqInfoShim()
        req.session_key = session_key
        req.system_authtoken = system_authtoken
        req.server_rest_uri = server_rest_uri
        req.server_rest_port = server_rest_port
        req.user = user

        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=server_rest_port,
                token=session_key,
                timeout=600,
            )

            # Mark running as early as possible so the first poll sees movement.
            _update_job(service, job_id, status="running", progress_message="starting")

            # Spawn the heartbeat now that we have a job in "running" state.
            # It bumps last_activity every _HEARTBEAT_INTERVAL_SECONDS so the
            # Phase-2 stale-orphan watchdog only fires if the worker is truly
            # gone, not just busy on a single long step.
            heartbeat = _HeartbeatThread(service, job_id)
            heartbeat.start()

            if _is_cancelled(service, job_id):
                # Quiesce the heartbeat first so its in-flight write
                # can't clobber the terminal status back to "running".
                heartbeat.stop_and_join()
                _update_job(service, job_id, status="cancelled", progress_message="cancelled before start")
                return

            # Resolve trackme_conf once (used for version + global metric idx).
            trackme_conf = None
            trackme_version = "unknown"
            try:
                trackme_conf = trackme_reqinfo(system_authtoken, server_rest_uri)
                trackme_version = trackme_conf.get("trackme_version", "unknown")
            except Exception:
                pass

            # Prepare directories
            app_root = os.path.join(splunkhome, "etc", "apps", "trackme")
            diag_dir = os.path.join(app_root, DIAG_DIR_NAME)
            if not os.path.isdir(diag_dir):
                os.makedirs(diag_dir, exist_ok=True)
            downloads_dir = diag_dir

            timestr = time.strftime("%Y%m%d-%H%M%S")
            staging_dir = os.path.join(
                diag_dir, f"staging_{mode}_{timestr}_{uuid.uuid4().hex[:8]}"
            )
            os.makedirs(staging_dir, exist_ok=True)

            server_name = socket.gethostname()
            summary = {
                "mode": mode,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "trackme_version": trackme_version,
                "server_name": server_name,
                "user": user,
                "files": [],
                # Populated by _collect_* helpers when individual steps
                # fail. The archive is still built around whatever did
                # succeed; this list is reflected in metadata.json and
                # surfaced via GET /status so the UI can warn the user.
                "step_failures": [],
            }
            if mode == "entity":
                summary.update({
                    "tenant_id": tenant_id,
                    "component": component,
                    "object_ids": object_ids,
                })

            # Collect — wrapped in try/except so a fatal collection-time
            # error still produces a (mostly empty) archive plus a clear
            # step_failures entry, rather than throwing away everything
            # that was already gathered.
            try:
                if mode == "entity":
                    self._collect_entity_diag(
                        service, req, tenant_id, component, object_ids,
                        staging_dir, summary, job_service=service, job_id=job_id,
                    )
                else:
                    self._collect_global_diag(
                        service, req, staging_dir, summary,
                        trackme_conf=trackme_conf, job_service=service, job_id=job_id,
                    )
            except Exception as collect_exc:
                logger.exception(
                    f'support_diag: collection step raised, '
                    f'job_id="{job_id}": {collect_exc}'
                )
                # Use the helper so the error string is truncated to 500
                # chars — same treatment as every other step_failures
                # call site, keeping the KV record and the GET /status
                # payload bounded.
                _record_step_failure(summary, "collect", collect_exc)

            if _is_cancelled(service, job_id):
                heartbeat.stop_and_join()
                _update_job(service, job_id, status="cancelled", progress_message="cancelled during collection")
                return

            # Anonymisation — applied after collection so _collect_* can
            # still reason about real tenant_ids, but before metadata is
            # written so summary.json reflects the anonymised identifiers
            # the reader will see. The mapping is stored on the job
            # record for the UI, NOT included in the archive.
            tenant_mapping = {}
            if anonymise_tenants:
                _update_job(service, job_id, progress_message="anonymising tenant names")
                vtenants_for_mapping = []
                try:
                    coll = service.kvstore["kv_trackme_virtual_tenants"]
                    vtenants_for_mapping, _keys, _dict = get_full_kv_collection(
                        coll, "kv_trackme_virtual_tenants"
                    )
                except Exception as e:
                    logger.warning(
                        f'support_diag: could not read vtenants for anonymisation: {e}'
                    )
                tenant_mapping = _build_tenant_mapping(
                    vtenants_for_mapping, seed_tenant_id=tenant_id or None
                )
                # Reflect the mapping in the in-memory summary so the
                # metadata.json we're about to write doesn't still carry
                # the real ids.
                if mode == "entity" and tenant_id and tenant_id in tenant_mapping:
                    summary["tenant_id"] = tenant_mapping[tenant_id]
                    summary["anonymised"] = True
                elif anonymise_tenants:
                    summary["anonymised"] = True
                _apply_anonymisation(staging_dir, tenant_mapping)

            # metadata
            _update_job(service, job_id, progress_message="writing metadata")
            metadata_path = os.path.join(staging_dir, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, default=str)

            # archive
            _update_job(service, job_id, progress_message="compressing archive")
            download_token = uuid.uuid4().hex
            archive_basename = f"trackme_support_diag_{mode}_{timestr}.tgz"
            token_filename = f"{download_token}_{timestr}_{archive_basename}"
            token_path = os.path.join(downloads_dir, token_filename)

            with tarfile.open(token_path, mode="w:gz") as tf:
                tf.add(staging_dir, arcname=os.path.basename(staging_dir))

            logger.info(
                f'support_diag: archive created, job_id="{job_id}", '
                f'path="{token_path}", mode="{mode}", size={os.path.getsize(token_path)}'
            )

            partial = bool(summary.get("step_failures"))
            # Quiesce the heartbeat *before* the terminal write so its
            # in-flight read-modify-write can't land afterwards and clobber
            # status="complete" back to "running".
            heartbeat.stop_and_join()
            _update_job(
                service, job_id,
                status="complete",
                progress_message=(
                    "complete (with partial failures)" if partial else "complete"
                ),
                download_token=download_token,
                filename=archive_basename,
                # Store as a JSON string; get_status decodes it back out
                # before returning to the UI. Empty when anonymise wasn't
                # requested — the UI treats that as "no mapping to show".
                tenant_mapping=json.dumps(tenant_mapping or {}),
                partial="true" if partial else "false",
                # Same pattern for step_failures so the UI can render a
                # short "what didn't make it into the archive" notice.
                step_failures=json.dumps(summary.get("step_failures") or []),
            )
        except Exception as e:
            # We only land here on infrastructure failures (couldn't connect
            # to splunkd to mark running, couldn't write to disk, couldn't
            # tar) — never on individual collection step failures, which are
            # caught upstream and recorded into summary["step_failures"].
            logger.exception(f"support_diag: worker failed, job_id={job_id}: {e}")
            try:
                if service is not None:
                    # Quiesce the heartbeat before the terminal write so
                    # we don't race with it.
                    if heartbeat is not None:
                        try:
                            heartbeat.stop_and_join()
                        except Exception:
                            pass
                    _update_job(
                        service, job_id,
                        status="error",
                        error="support_diag generation failed — see trackme_rest_api_support_diag.log",
                        progress_message="error",
                    )
            except Exception:
                pass
        finally:
            # Belt-and-braces: heartbeat may already have been stopped
            # earlier (happy path / cancel paths / error path), but make
            # sure it's quiesced even if we exited via a return that
            # bypassed those paths.
            if heartbeat is not None:
                try:
                    heartbeat.stop_and_join(timeout=5)
                except Exception:
                    pass
            # Always clean up staging dir. The job record has now reached
            # a terminal status, so it no longer counts against the
            # concurrency limit (which is derived from KV).
            if staging_dir:
                try:
                    shutil.rmtree(staging_dir, ignore_errors=True)
                except Exception:
                    pass

    # -----------------------------
    # GET /trackme/v2/support_diag/status?job_id=<id>
    # -----------------------------

    def get_status(self, request_info, **kwargs):
        """Poll the status of a running or completed support-diag job."""

        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "This endpoint polls the status of a support "
                        "diagnostic job previously started via POST "
                        "support_diag/generate. Status values are 'queued', "
                        "'running' (carries progress_message describing the "
                        "current step), 'complete' (additionally returns "
                        "download_token and filename for the archive, plus "
                        "any tenant_mapping when anonymisation was "
                        "requested), 'cancelled', or 'error' (carries a "
                        "human-readable error string). 'partial' is "
                        "surfaced when one or more collection steps failed "
                        "but the archive was still produced — step_failures "
                        "lists which steps were skipped."
                    ),
                    "resource": "support_diag/status",
                    "methods": ["GET"],
                    "resource_desc": (
                        "Poll the status of a support diag job previously started "
                        "via POST support_diag/generate. Returns status plus a "
                        "progress_message while running; on status=complete also "
                        "returns {download_token, filename} for use with GET "
                        "support_diag/generate."
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/support_diag/status?job_id=<id>" mode=get'
                    ),
                    "options": [
                        {
                            "job_id": "REQUIRED. The job_id returned by POST support_diag/generate. Passed as a query-string parameter",
                        }
                    ],
                },
                "status": 200,
            }

        job_id = _extract_query_arg(request_info, "job_id")
        if not job_id:
            return {"payload": {"error": "job_id parameter is required"}, "status": 400}
        if len(job_id) != 32 or any(c not in "0123456789abcdefABCDEF" for c in job_id):
            return {"payload": {"error": "Invalid job_id format"}, "status": 400}

        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.session_key,
                timeout=60,
            )
            record = _get_job(service, job_id)
        except Exception as e:
            logger.error(f"support_diag: get_status lookup failed for {job_id}: {e}")
            return {"payload": {"error": "Internal error looking up job"}, "status": 500}

        if not record:
            return {"payload": {"error": "Unknown job_id"}, "status": 404}

        status = str(record.get("status") or "running")
        payload = {
            "job_id": job_id,
            "status": status,
            "progress_message": record.get("progress_message") or "",
            "mode": record.get("mode") or "",
        }
        if status == "complete":
            payload["download_token"] = record.get("download_token") or ""
            payload["filename"] = record.get("filename") or ""
            # tenant_mapping is stored as a JSON string on the record; decode
            # it to a dict for the UI. Empty or invalid → no mapping to show.
            raw_map = record.get("tenant_mapping") or ""
            if raw_map:
                try:
                    decoded = json.loads(raw_map)
                    if isinstance(decoded, dict) and decoded:
                        payload["tenant_mapping"] = decoded
                except Exception:
                    pass
            # partial flag + step_failures so the UI can warn the user
            # that part of the archive didn't make it.
            payload["partial"] = (
                str(record.get("partial") or "").strip().lower() == "true"
            )
            raw_failures = record.get("step_failures") or ""
            if raw_failures:
                try:
                    decoded = json.loads(raw_failures)
                    if isinstance(decoded, list) and decoded:
                        payload["step_failures"] = decoded
                except Exception:
                    pass
        elif status == "error":
            payload["error"] = record.get("error") or "unknown error"
        return {"payload": payload, "status": 200}

    # -----------------------------
    # DELETE /trackme/v2/support_diag/cancel?job_id=<id>
    # -----------------------------

    def delete_cancel(self, request_info, **kwargs):
        """Request cancellation of a running support-diag job."""

        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "This endpoint requests cancellation of a running "
                        "support diagnostic job. Cancellation is "
                        "co-operative: the worker checks the cancel flag "
                        "between collection steps, so a mid-flight SPL "
                        "search will still complete to its natural "
                        "boundary, but no further steps run and the "
                        "archive is not built. The job transitions to "
                        "status='cancelled' and any subsequent GET status "
                        "calls return that marker. The endpoint is "
                        "idempotent — cancelling an already-cancelled job "
                        "is a no-op."
                    ),
                    "resource": "support_diag/cancel",
                    "methods": ["DELETE"],
                    "resource_desc": (
                        "Request cancellation of a running support diag job. "
                        "The worker checks the cancel flag between steps; a "
                        "mid-flight SPL search will still complete, but no "
                        "further steps will run and the archive will not be built."
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/support_diag/cancel?job_id=<id>" mode=delete'
                    ),
                    "options": [
                        {
                            "job_id": "REQUIRED. The job_id to cancel. Passed as a query-string parameter",
                        }
                    ],
                },
                "status": 200,
            }

        job_id = _extract_query_arg(request_info, "job_id")
        if not job_id:
            return {"payload": {"error": "job_id parameter is required"}, "status": 400}
        if len(job_id) != 32 or any(c not in "0123456789abcdefABCDEF" for c in job_id):
            return {"payload": {"error": "Invalid job_id format"}, "status": 400}

        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.session_key,
                timeout=60,
            )
            record = _get_job(service, job_id)
            if not record:
                return {"payload": {"error": "Unknown job_id"}, "status": 404}
            status = str(record.get("status") or "")
            if status in _TERMINAL_STATUSES:
                return {"payload": {"job_id": job_id, "status": status, "action": "noop"}, "status": 200}
            # The KV record is the single source of truth — the worker
            # (possibly in another process) consults it between every
            # step via _is_cancelled(service, job_id).
            _update_job(
                service, job_id,
                status="cancelled",
                progress_message="cancellation requested",
            )
        except Exception as e:
            logger.error(f"support_diag: delete_cancel failed for {job_id}: {e}")
            return {"payload": {"error": "Internal error cancelling job"}, "status": 500}

        return {"payload": {"job_id": job_id, "status": "cancelled", "action": "cancelled"}, "status": 200}

    # -----------------------------
    # GET /trackme/v2/support_diag/generate?download_token=<t>
    # -----------------------------

    def get_generate(self, request_info, **kwargs):
        """Return a previously-generated diag archive as base64, keyed by token."""

        # describe support
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "This endpoint streams a previously-generated "
                        "support diagnostic archive back to the caller as "
                        "base64-encoded bytes, keyed by the single-use "
                        "download_token that POST support_diag/generate "
                        "returned via GET support_diag/status. The token "
                        "file is removed from the downloads directory on "
                        "successful read so each archive can only be "
                        "fetched once. Returns HTTP 400 when the token is "
                        "missing or malformed (must be a 32-char hex "
                        "string), HTTP 404 when the staged archive cannot "
                        "be located (token expired, already consumed, or "
                        "never existed)."
                    ),
                    "resource": "support_diag/generate",
                    "methods": ["GET"],
                    "resource_desc": (
                        "Download a previously-generated support diag archive as "
                        "base64, using the download_token returned by POST."
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/support_diag/generate?download_token=<t>" mode=get'
                    ),
                    "options": [
                        {
                            "download_token": "REQUIRED. The single-use download_token returned by GET support_diag/status when the job reaches status=complete. Passed as a query-string parameter",
                        }
                    ],
                },
                "status": 200,
            }

        token_str = _extract_query_arg(request_info, "download_token")
        if not token_str:
            return {"payload": {"error": "download_token parameter is required"}, "status": 400}

        # Sanity: token must be a 32-char hex string (uuid4().hex). Without
        # the length check, a short value would pass the hex filter and match
        # any archive file by prefix — e.g. "a" would grab the first archive
        # whose token happens to start with "a".
        if (
            len(token_str) != 32
            or any(c not in "0123456789abcdefABCDEF" for c in token_str)
        ):
            return {"payload": {"error": "Invalid download_token format"}, "status": 400}

        downloads_dir = os.path.join(splunkhome, "etc", "apps", "trackme", DIAG_DIR_NAME)
        if not os.path.isdir(downloads_dir):
            return {"payload": {"error": "Downloads directory not found"}, "status": 404}

        token_file = None
        try:
            prefix = f"{token_str}_"
            for fname in os.listdir(downloads_dir):
                if fname.startswith(prefix):
                    token_file = os.path.join(downloads_dir, fname)
                    break
        except Exception as e:
            logger.error(f"support_diag: error locating token file: {e}")
            return {
                "payload": {"error": "Internal error locating token file"},
                "status": 500,
            }

        if not token_file or not os.path.exists(token_file):
            return {"payload": {"error": "Invalid or expired download token"}, "status": 404}

        try:
            parts = os.path.basename(token_file).split("_", 2)
            original_filename = "_".join(parts[2:]) if len(parts) >= 3 else os.path.basename(token_file)
        except Exception:
            original_filename = "trackme_support_diag.tgz"

        try:
            with open(token_file, "rb") as fh:
                file_data = fh.read()
            base64_data = base64.b64encode(file_data).decode("utf-8")
            try:
                os.remove(token_file)
                logger.info(f"support_diag: cleaned up token file {token_file}")
            except Exception as e:
                logger.warning(f"support_diag: failed to clean {token_file}: {e}")
            return {
                "payload": {
                    "archive_base64": base64_data,
                    "filename": original_filename,
                },
                "status": 200,
            }
        except Exception as e:
            logger.error(f"support_diag: error serving file: {e}")
            return {
                "payload": {"error": "Internal error serving support diag archive"},
                "status": 500,
            }

    # -----------------------------
    # Entity diag collection
    # -----------------------------

    def _collect_entity_diag(
        self,
        service,
        request_info,
        tenant_id,
        component,
        object_ids,
        staging_dir,
        summary,
        job_service=None,
        job_id=None,
    ):
        def _progress(msg):
            if job_service and job_id:
                _update_job(job_service, job_id, progress_message=msg)

        def _should_abort():
            return bool(job_id and job_service and _is_cancelled(job_service, job_id))

        _progress(f"resolving tenant indexes for {tenant_id}")
        # Resolve tenant indexes
        try:
            tenant_indexes = trackme_idx_for_tenant(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
            )
        except Exception as e:
            logger.warning(f"support_diag: unable to resolve tenant indexes for {tenant_id}: {e}")
            tenant_indexes = {}
        # Index values come from tenant config, but treat them as
        # untrusted input — a mis-configured tenant could persist an index
        # name containing a double-quote and break out of the SPL string
        # context below. _escape_spl_value quotes such payloads into an
        # inert form that Splunk will then simply fail to match, rather
        # than running unexpected SPL.
        metric_idx = _escape_spl_value(
            tenant_indexes.get("trackme_metric_idx", "trackme_metrics")
        )
        summary_idx = _escape_spl_value(
            tenant_indexes.get("trackme_summary_idx", "trackme_summary")
        )
        notable_idx = _escape_spl_value(
            tenant_indexes.get("trackme_notable_idx", "trackme_notable")
        )

        summary["resolved_indexes"] = {
            "trackme_metric_idx": metric_idx,
            "trackme_summary_idx": summary_idx,
            "trackme_notable_idx": notable_idx,
        }

        # Entity records via load_component_data
        _progress("loading entity records")
        if _should_abort():
            return
        records = _load_component_data(
            request_info.session_key,
            request_info.server_rest_uri,
            tenant_id,
            component,
            object_ids,
        )
        entities_path = os.path.join(staging_dir, "entities.json")
        with open(entities_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, default=str)
        summary["files"].append(
            {"file": "entities.json", "matched_records": len(records), "requested": len(object_ids)}
        )

        # Per-entity searches
        #
        # safe_name is a sanitized version of the object id for use in
        # filenames. Different object ids can map to the same safe_name
        # after sanitization (e.g. "foo:bar" and "foo/bar" both become
        # "foo_bar"), so we prefix each file with the zero-padded request
        # index to guarantee uniqueness within the archive.
        total = len(object_ids)
        width = max(2, len(str(max(total - 1, 0))))
        for idx, obj in enumerate(object_ids):
            if _should_abort():
                return
            _progress(f"entity {idx + 1}/{total}: running 7d mstats")
            obj_escaped = _escape_spl_value(obj)
            safe_body = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in obj)[:120]
            if not safe_body:
                safe_body = "entity"
            safe_name = f"{idx:0{width}d}_{safe_body}"

            # metrics_7d.csv
            mstats_query = (
                f'| mstats max(_value) as metric '
                f'where index="{metric_idx}" metric_name=* '
                f'(object="{obj_escaped}" OR object_id="{obj_escaped}") '
                f'by metric_name span=1m'
            )
            metrics_csv = os.path.join(staging_dir, f"{safe_name}__metrics_7d.csv")
            try:
                stats = _run_search_to_csv(
                    service,
                    mstats_query,
                    earliest="-7d",
                    latest="now",
                    csv_path=metrics_csv,
                )
                summary["files"].append(
                    {"file": os.path.basename(metrics_csv), "rows": stats["rows"], "truncated": stats["truncated"]}
                )
            except Exception as e:
                logger.error(f"support_diag: mstats search failed for {obj}: {e}")
                summary["files"].append(
                    {"file": os.path.basename(metrics_csv), "error": str(e)}
                )
                _record_step_failure(summary, f"entity_metrics:{obj}", e)

            if _should_abort():
                return
            _progress(f"entity {idx + 1}/{total}: collecting latest events")
            # latest_events.csv
            events_query = (
                f'search (index="{summary_idx}" OR index="{notable_idx}") '
                f'(object="{obj_escaped}" OR object_id="{obj_escaped}") '
                f'| stats latest(_raw) as _raw by index, sourcetype, source'
            )
            events_csv = os.path.join(staging_dir, f"{safe_name}__latest_events.csv")
            try:
                stats = _run_search_to_csv(
                    service,
                    events_query,
                    earliest="-7d",
                    latest="now",
                    csv_path=events_csv,
                )
                summary["files"].append(
                    {"file": os.path.basename(events_csv), "rows": stats["rows"], "truncated": stats["truncated"]}
                )
            except Exception as e:
                logger.error(f"support_diag: latest events search failed for {obj}: {e}")
                summary["files"].append(
                    {"file": os.path.basename(events_csv), "error": str(e)}
                )
                _record_step_failure(summary, f"entity_events:{obj}", e)

    # -----------------------------
    # Global diag collection
    # -----------------------------

    def _collect_global_diag(
        self, service, request_info, staging_dir, summary, trackme_conf=None,
        job_service=None, job_id=None,
    ):
        def _progress(msg):
            if job_service and job_id:
                _update_job(job_service, job_id, progress_message=msg)

        def _should_abort():
            return bool(job_id and job_service and _is_cancelled(job_service, job_id))

        _progress("resolving global metric index")
        # Resolve the global metric index (from trackme_settings.conf
        # [index_settings]) rather than hardcoding "trackme_metrics" — the
        # admin may have configured a different name.
        #
        # Reuse the trackme_conf payload already fetched in post_generate
        # when possible; fall back to a fresh call only if the caller didn't
        # pass one (or if the earlier fetch failed).
        global_metric_idx = "trackme_metrics"
        try:
            if not trackme_conf:
                trackme_conf = trackme_reqinfo(
                    request_info.system_authtoken, request_info.server_rest_uri
                )
            idx_settings = (
                (trackme_conf or {}).get("trackme_conf", {}).get("index_settings", {})
            )
            if idx_settings.get("trackme_metric_idx"):
                global_metric_idx = str(idx_settings["trackme_metric_idx"]).strip()
        except Exception as e:
            logger.warning(
                f'support_diag: could not resolve global trackme_metric_idx, '
                f'falling back to "trackme_metrics": {e}'
            )
        # Escape for safe inclusion in double-quoted SPL — same rationale
        # as the entity-mode path above.
        global_metric_idx = _escape_spl_value(global_metric_idx)
        summary["resolved_indexes"] = {"trackme_metric_idx": global_metric_idx}

        # Central KV Store collections. We hold on to the vtenants records
        # because the per-tenant knowledge-objects step below iterates them.
        kv_collections = [
            "kv_trackme_virtual_tenants",
            "kv_trackme_virtual_tenants_exec_summary",
            "kv_trackme_virtual_tenants_entities_summary",
        ]
        vtenants_records = []
        for coll_name in kv_collections:
            if _should_abort():
                return
            _progress(f"dumping {coll_name}")
            out_path = os.path.join(staging_dir, f"{coll_name}.json")
            try:
                coll = service.kvstore[coll_name]
                records, _keys, _dict = get_full_kv_collection(coll, coll_name)
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump(records, fh, indent=2, default=str)
                summary["files"].append(
                    {"file": os.path.basename(out_path), "records": len(records)}
                )
                if coll_name == "kv_trackme_virtual_tenants":
                    vtenants_records = records or []
            except Exception as e:
                logger.error(f"support_diag: failed to dump {coll_name}: {e}")
                summary["files"].append(
                    {"file": os.path.basename(out_path), "error": str(e)}
                )
                _record_step_failure(summary, f"kv_dump:{coll_name}", e)

        # Per-tenant knowledge objects — mirrors what backup_and_restore
        # captures via /configuration/get_tenant_knowledge_objects (saved
        # searches, alerts, macros, kvstore_collections, lookup_definitions).
        # Only enabled tenants are walked.
        ko_summary = {
            "tenants_processed": 0,
            "total_knowledge_objects": 0,
            "failures": [],
        }
        enabled_tenants = [
            r for r in vtenants_records
            if (r or {}).get("tenant_status") == "enabled"
        ]
        for t_idx, trecord in enumerate(enabled_tenants):
            if _should_abort():
                break
            t_id = str(trecord.get("tenant_id") or "").strip()
            if not t_id:
                continue
            _progress(
                f"collecting knowledge objects for tenant {t_idx + 1}/{len(enabled_tenants)} "
                f"({t_id})"
            )
            try:
                kos = _fetch_tenant_knowledge_objects(
                    request_info.session_key,
                    request_info.server_rest_uri,
                    t_id,
                )
            except Exception as e:
                msg = f'tenant_id="{t_id}", knowledge-objects fetch failed: {e}'
                logger.error(f"support_diag: {msg}")
                ko_summary["failures"].append(msg)
                _record_step_failure(summary, f"knowledge_objects:{t_id}", e)
                continue

            # Preserve the same file layout/shape backup_and_restore uses so
            # anything downstream that already understands a backup archive
            # can read this too.
            out_path = os.path.join(
                staging_dir, f"tenant_{t_id}_knowledge_objects.json"
            )
            try:
                normalised = _normalise_knowledge_objects(kos)
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump(normalised, fh, indent=1, default=str)
                count = len(normalised)
                ko_summary["tenants_processed"] += 1
                ko_summary["total_knowledge_objects"] += count
                summary["files"].append(
                    {
                        "file": os.path.basename(out_path),
                        "tenant_id": t_id,
                        "knowledge_objects": count,
                    }
                )
            except Exception as e:
                logger.error(
                    f'support_diag: failed to write knowledge objects file '
                    f'for tenant_id="{t_id}": {e}'
                )
                ko_summary["failures"].append(
                    f'tenant_id="{t_id}", write failed: {e}'
                )
                _record_step_failure(summary, f"knowledge_objects_write:{t_id}", e)
        summary["knowledge_objects"] = ko_summary

        # Scheduler skipping report (-24h) — across ALL trackme scheduler
        # activity, not just stateful trackers, so health-tracker / feeds /
        # etc. also show up when we're triaging generalised skipping.
        if _should_abort():
            return
        _progress("running 24h scheduler skipping report")
        skip_query = (
            'search (index=_internal sourcetype=scheduler app="trackme") '
            '| eval status=case(status=="success" OR status=="completed", "completed", '
            'status=="skipped", "skipped", status=="continued", "deferred") '
            '| stats count(eval(status=="completed")) as count_completed, '
            'count(eval(status=="skipped")) as count_skipped, count by savedsearch_name '
            '| eval pct_completed=round(((count_completed / count) * 100),2) '
            '| sort 0 - count_skipped'
        )
        self._run_named_search_to_csv(
            service, skip_query, "scheduler_skipping_24h.csv", "-24h", "now", staging_dir, summary
        )

        # Scheduler performance report (-24h) — same rationale: keep the
        # scope to the whole trackme app rather than filtering on stateful.
        if _should_abort():
            return
        _progress("running 24h scheduler performance report")
        perf_query = (
            'search (index=_internal sourcetype=scheduler app="trackme" run_time=*) '
            '| stats avg(run_time) as avg_run_time, max(run_time) as max_run_time, '
            'perc95(run_time) as perc95, min(run_time) as min_run_time by savedsearch_name '
            '| sort 0 - avg_run_time'
        )
        self._run_named_search_to_csv(
            service, perf_query, "scheduler_perf_24h.csv", "-24h", "now", staging_dir, summary
        )

        if _should_abort():
            return
        _progress("running 24h TrackMe runtime metrics")
        # TrackMe runtime metrics (-24h) — uses the globally-configured
        # metric index resolved above, properly quoted.
        runtime_query = (
            '| mstats avg(trackme.components_register.runtime) as runtime '
            f'where index="{global_metric_idx}" '
            'by tenant_id, tracker span=1m '
            '| stats avg(runtime) as avg_run_time, max(runtime) as max_run_time, '
            'perc95(runtime) as perc95, min(runtime) as min_runtime by tenant_id, tracker'
        )
        self._run_named_search_to_csv(
            service, runtime_query, "trackme_runtime_24h.csv", "-24h", "now", staging_dir, summary
        )

        # Last 10k ERROR events across all TrackMe components over the
        # past 7 days — REST API logs, custom command logs, and alert
        # action logs. `remote_configs_proxy.py` is excluded because its
        # noise is known/expected on distributed deployments. The rex +
        # eval collapse the three sourcetype shapes into a single
        # "command" column so the CSV is easy to filter on.
        if _should_abort():
            return
        _progress("collecting last 10k ERROR events across TrackMe components (7d)")
        errors_query = (
            'search (index=_internal OR index=cim_modactions) '
            '((sourcetype=trackme:rest_api OR sourcetype=trackme:custom_commands:*) '
            'OR sourcetype=modular_alerts:trackme_*) '
            'log_level="ERROR" NOT "remote_configs_proxy.py" '
            '| rex field=sourcetype "trackme:custom_commands:(?<command>.*)" '
            '| rex field=sourcetype "modular_alerts:(?<alert_command>.*)" '
            '| eval command=case('
            'sourcetype="trackme:rest_api", "rest_api", '
            'isnotnull(alert_command), alert_command, '
            'isnotnull(command), command) '
            '| where isnotnull(command) '
            '| fields - alert_command '
            '| table _time, log_level, command, sourcetype, _raw '
            '| sort - _time '
            '| head 10000'
        )
        self._run_named_search_to_csv(
            service, errors_query, "trackme_errors_7d.csv", "-7d", "now", staging_dir, summary,
            max_rows=10000,
        )

    def _run_named_search_to_csv(
        self, service, query, filename, earliest, latest, staging_dir, summary,
        max_rows=None,
    ):
        path = os.path.join(staging_dir, filename)
        try:
            kwargs = {}
            if max_rows is not None:
                kwargs["max_rows"] = max_rows
            stats = _run_search_to_csv(service, query, earliest, latest, path, **kwargs)
            summary["files"].append(
                {"file": filename, "rows": stats["rows"], "truncated": stats["truncated"]}
            )
        except Exception as e:
            logger.error(f"support_diag: search {filename} failed: {e}")
            summary["files"].append({"file": filename, "error": str(e)})
            _record_step_failure(summary, f"search:{filename}", e)
