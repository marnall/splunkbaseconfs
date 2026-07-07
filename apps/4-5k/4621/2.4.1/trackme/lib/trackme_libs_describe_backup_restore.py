#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.2.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import json
import time
import logging
from trackme_libs_logging import get_effective_logger

from trackme_libs_describe_tenant_home import _safe_int
from trackme_libs_describe_concierge import build_concierge_knowledge
from trackme_libs_describe_utils import (
    fetch_resource_group_describe,
    fetch_all_endpoint_describes,
)

# Endpoint registry for Backup & Restore resource group.
# Updated for the 3.0.0 multi-archive format (release 2.3.22): the new
# endpoints are auto-discovered by the parent handler's dir() scan, but we
# still declare them here so fetch_all_endpoint_describes pulls their
# describe blocks for the AI Assistant to reason over.
BACKUP_RESTORE_ENDPOINTS = [
    {"method": "get", "url": "backup_and_restore/backup"},
    {"method": "post", "url": "backup_and_restore/backup"},
    {"method": "delete", "url": "backup_and_restore/backup"},
    {"method": "post", "url": "backup_and_restore/restore"},
    {"method": "post", "url": "backup_and_restore/import_backup"},
    {"method": "post", "url": "backup_and_restore/export_backup"},
    # 3.0.0 — added in 2.3.22
    {"method": "get", "url": "backup_and_restore/backup_runs"},
    {"method": "post", "url": "backup_and_restore/backup_tenant"},
    {"method": "post", "url": "backup_and_restore/backup_global"},
    # Async restore job pattern — added 2.3.22 to avoid gateway-timeout
    # 504s on multi-GB / multi-minute restores. POST /restore takes a
    # new `async=true` body param; this endpoint is the polling
    # counterpart that returns the job's status + final response.
    {"method": "get", "url": "backup_and_restore/restore_job_status"},
    {"method": "delete", "url": "backup_and_restore/restore_job"},
]


def _build_knowledge_reference(api_endpoints=None, resource_group_info=None):
    """
    Build a knowledge reference section that provides the AI assistant
    with comprehensive understanding of Backup & Restore concepts,
    operations, and best practices for the 3.0.0 multi-archive format.

    Args:
        api_endpoints: List of dynamically fetched endpoint describe responses.
                       If None, a fallback note is included.
        resource_group_info: Resource group description dict from the handler.
    """
    ref = {
        # ----------------------------------------------------------
        # Multi-archive run model (3.0.0 — the format produced since 2.3.22)
        # ----------------------------------------------------------
        "multi_archive_run": {
            "summary": (
                "From release 2.3.22 onward, a backup RUN produces N+1 "
                "independent archives instead of one monolithic .tar.zst: "
                "one per enabled virtual tenant, plus exactly one global "
                "archive. Each archive is independently compressed, "
                "integrity-tested (zstd -t), sha256-stamped, and "
                "registered in kv_trackme_backup_archives_info."
            ),
            "central_correctness_change": (
                "A per-archive failure does NOT short-circuit the run. "
                "If tenant X's KV is corrupted at backup time, tenant X's "
                "archive is registered as status='failed' but every other "
                "archive is still produced and restorable. This is the "
                "exact failure mode that motivated the redesign — at "
                "large customer scale, a single tenant's data corruption "
                "made the whole monolithic backup unrestorable."
            ),
            "archive_filename_grammar": {
                "tenant": "trackme-backup-<RUN_ID>-tenant-<tenant_id>.tar.zst",
                "global": "trackme-backup-<RUN_ID>-global.tar.zst",
                "run_id_format": "YYYYMMDD-HHMMSS-XXXXXX (XXXXXX = 6-char random suffix)",
                "legacy": (
                    "trackme-backup-YYYYMMDD-HHMMSS.{tar.zst,tgz} "
                    "(produced by 2.3.21 and earlier — still restorable, "
                    "no longer produced)"
                ),
            },
            "in_archive_manifest": (
                "Every 3.0.0 archive carries a manifest.json at its root "
                "declaring archive_schema_version, archive_scope, "
                "tenant_id, run_id, the collections it contains, and "
                "(for tenant scope) vtenant_account_file + "
                "knowledge_objects_file. This is the source-of-truth "
                "signal that drives post_restore's 3.0.0 dispatch."
            ),
            "run_manifest_sidecar": (
                "Each run also writes a sidecar `<RUN_ID>.manifest.json` "
                "under the backup root. It's not load-bearing — the live "
                "UI summary comes from the KV collection — but is useful "
                "for forensic / out-of-band tooling."
            ),
        },

        # ----------------------------------------------------------
        # Async restore job pattern — added 2.3.22 to avoid
        # gateway-timeout 504s on multi-GB / multi-minute restores.
        # ----------------------------------------------------------
        "async_restore_jobs": {
            "summary": (
                "POST /restore body={..., async: true} returns "
                "immediately with {job_id, status: 'queued'} and runs "
                "the restore in a background thread. The frontend "
                "polls GET /restore_job_status?job_id=... every few "
                "seconds; when status reaches 'completed' or 'failed' "
                "the response field carries the same shape the "
                "synchronous POST /restore would have returned."
            ),
            "why_it_matters": (
                "A multi-GB restore can take minutes-to-hours. The "
                "synchronous path (async=false) ties up an HTTP "
                "connection that long, which gateways / proxies "
                "typically terminate at the 5-minute neighbourhood "
                "with a 504. The operator sees a generic timeout with "
                "no signal whether the restore is still running, "
                "succeeded, or partially applied. The async pattern "
                "makes that ambiguity impossible — the job row in "
                "kv_trackme_backup_restore_jobs is the durable record."
            ),
            "cli_default": (
                "async defaults to false so every existing CLI / "
                "`| trackme url=... mode=post body={...}` SPL caller "
                "keeps the synchronous contract. Power users can "
                "opt into async from the CLI by passing async=true "
                "and polling via two more `| trackme` calls."
            ),
            "cancellation": (
                "DELETE /restore_job?job_id=... sets a cooperative "
                "cancel flag. The worker checks it before starting "
                "and aborts gracefully if set; the in-flight archive "
                "(if any) is allowed to finish so KV state stays "
                "consistent. Already-completed jobs return 409."
            ),
            "auto_purge": (
                "Terminal jobs (completed/failed/cancelled) older "
                "than 24h are auto-purged on every poll so the "
                "kv_trackme_backup_restore_jobs collection stays "
                "small. Running jobs are never auto-purged — the "
                "row stays for forensic analysis."
            ),
        },

        # ----------------------------------------------------------
        # Restore modes (3.0.0)
        # ----------------------------------------------------------
        "restore_modes": {
            "single_archive": (
                "POST /restore body={'archive_archive': '<3.0.0 filename>', "
                "'dry_run': true|false, ...}. Restores ONE archive (one "
                "tenant or the global). The handler reads the in-archive "
                "manifest, validates archive_scope and tenant_id against "
                "the KV row, and applies the payload (vtenant_account, "
                "knowledge_objects, KV collections) per the manifest."
            ),
            "whole_run": (
                "POST /restore body={'backup_run_id': '<RUN_ID>', "
                "'dry_run': true|false, ...}. Iterates every archive in "
                "the run and restores each one with per-archive "
                "isolation — a corrupt or remote-unreachable archive "
                "marks itself status='failed' but does not abort sibling "
                "archives. SHC-aware: archives owned by a remote peer "
                "are delegated to that peer with a recursion guard."
            ),
            "legacy_flat": (
                "POST /restore body={'backup_archive': "
                "'trackme-backup-YYYYMMDD-HHMMSS.tgz'}. Falls through to "
                "the pre-2.3.22 monolithic-archive code path (untouched). "
                "Customers with archives from 2.3.21 and earlier on cold "
                "storage can still restore them indefinitely."
            ),
        },

        # ----------------------------------------------------------
        # Selective restore (3.0.0+) — per-archive overrides
        # ----------------------------------------------------------
        "selective_restore": {
            "purpose": (
                "Restore ONLY a subset of items from one or more "
                "archives in a run, instead of restoring everything the "
                "archive contains. The majority recovery scenario at "
                "scale: 'I corrupted kv_trackme_dsm_priority_tenant_X, "
                "I just want that one collection back from the latest "
                "tenant archive — leave the other collections, leave "
                "the other tenants, leave global alone.' The flat "
                "kvstore_collections_scope / knowledge_objects_lists "
                "filters apply uniformly to every archive in a run; "
                "archives_scope lets you scope per archive."
            ),
            "body_param": "archives_scope",
            "shape": (
                "{\"<archive_filename>\": {\"collections\": [\"...\"] | "
                "\"all\", \"knowledge_objects\": [\"...\"] | \"all\"}, ...}. "
                "Filename keys match the basename of each archive (the "
                "same `archive_filename` returned in the dry-run "
                "response's archives[] entries)."
            ),
            "behaviour": (
                "When set for an archive, takes precedence over the "
                "flat filters for THAT archive only. Archives absent "
                "from the map fall through to the flat filters. Empty "
                "dict / omitted = today's flat-filter behaviour "
                "preserved (CLI compat). KO entries are honoured only "
                "for tenant-scope archives (global archives carry no "
                "knowledge objects)."
            ),
            "cross_tenant_ko_collisions": (
                "Two tenants may have a knowledge object with the same "
                "title. The flat knowledge_objects_lists can't "
                "disambiguate (it would restore the title to BOTH "
                "tenants). archives_scope sidesteps that — each "
                "archive's KO list applies only to that archive's "
                "tenant. This is why the multiselects in the UI are "
                "grouped per archive."
            ),
            "response_signal": (
                "Each archive in the response carries "
                "selective_restore=true|false so an audit reader can "
                "tell apart 'everything was restored' from 'only the "
                "explicitly-selected items were restored'."
            ),
            "ui_population": (
                "The frontend populates the per-archive Multiselect "
                "components from the dry-run response: each archive "
                "exposes preview.collections (already returned by the "
                "manifest read) and preview.available_knowledge_objects "
                "(NEW — the KO file is parsed once during the dry-run "
                "extraction, the title list is added to the response "
                "without further I/O at apply time)."
            ),
            "examples": [
                "{\"trackme-backup-<RUN>-tenant-<tid>.tar.zst\": "
                "{\"collections\": [\"kv_trackme_dsm_priority_tenant_<tid>\"]}}",
                "{\"trackme-backup-<RUN>-global.tar.zst\": "
                "{\"collections\": [\"kv_trackme_bank_holidays\"]}}",
                "Multi-archive: same body carries entries for both the "
                "tenant archive and the global archive — restored in "
                "one async run, with per-archive isolation.",
            ],
        },

        # ----------------------------------------------------------
        # Missing-tenant safety guard (3.0.0)
        # ----------------------------------------------------------
        "missing_tenant_safety_guard": (
            "When restoring a tenant archive whose tenant_id is absent "
            "from kv_trackme_virtual_tenants (anomalous — the global "
            "archive normally carries that collection), the handler "
            "auto-recreates the tenant record from the archive's own "
            "vtenant_account JSON, deduces component enablement from the "
            "set of `_tenant_<tid>` collections present, marks the "
            "record `recreated_by_restore=true`, then proceeds with the "
            "restore. No opt-in flag — automatic with a clear warning "
            "in the audit trail."
        ),

        # ----------------------------------------------------------
        # SHC behaviour
        # ----------------------------------------------------------
        "shc_behaviour": (
            "kv_trackme_backup_archives_info is auto-replicated across "
            "SHC peers, so any peer can list runs and identify archive "
            "ownership via row.server_name. Per-archive operations "
            "(restore, delete, export) automatically delegate to the "
            "owning peer via REST with force_local=true to prevent "
            "recursive delegation. Per-archive isolation extends "
            "across peers — a remote-unreachable archive surfaces as "
            "status='failed_remote_unreachable' but doesn't block "
            "sibling archives."
        ),

        # ----------------------------------------------------------
        # Endpoint reference (high-level, complementary to api_endpoints)
        # ----------------------------------------------------------
        "endpoint_reference": {
            "GET /backup_runs": (
                "Lists runs grouped from kv_trackme_backup_archives_info. "
                "Pre-2.3.22 archives fold into a synthetic 'legacy' run "
                "that always sorts last. SHC-aware out of the box."
            ),
            "POST /backup": (
                "Create a multi-archive backup run. Body params include "
                "tenants_scope (csv or 'all'), include_global (bool), "
                "comment, blocklist."
            ),
            "POST /backup_tenant": (
                "Thin wrapper that pins tenants_scope=[<tid>] + "
                "include_global=false. Produces ONLY the named tenant's "
                "archive. Useful for hot-tenant snapshots."
            ),
            "POST /backup_global": (
                "Thin wrapper that pins tenants_scope=[] + "
                "include_global=true. Produces ONLY the global archive."
            ),
            "POST /restore": (
                "Restore one archive (archive_name) or a whole run "
                "(backup_run_id). dry_run=true (default) gives a preview "
                "without applying anything; dry_run=false applies the "
                "restore. Honours kvstore_collections_scope, "
                "kvstore_collections_blocklist, "
                "kvstore_collections_restore_non_tenants_collections, "
                "knowledge_objects_lists, knowledge_objects_blocklist, "
                "and the legacy backup_archive parameter for "
                "pre-2.3.22 archives. NEW in 2.3.22+: archives_scope "
                "(dict) lets you narrow per archive — see selective_restore "
                "below. Also supports async=true for long restores; the "
                "response carries a job_id pollable via /restore_job_status."
            ),
            "DELETE /backup": (
                "Delete a single archive (archive_name) or a whole run "
                "(backup_run_id, 3.0.0 only) or sweep by retention "
                "(retention_days). Run-mode delete iterates every "
                "archive in the run with SHC delegation per-archive."
            ),
            "POST /import_backup, POST /export_backup": (
                "Single-archive import/export — works for 3.0.0 and "
                "legacy archives interchangeably (each is a "
                "self-describing compressed tarball)."
            ),
        },

        # ----------------------------------------------------------
        # Guardian integration
        # ----------------------------------------------------------
        "guardian_integration": {
            "backup_archive_too_old": (
                "Anchors on the most-recent archive_scope='global' row "
                "(one per run) — a late-finishing tenant archive cannot "
                "mask a stale run. Severity warning at cadence × 1.5, "
                "critical at 7 days. Falls back to 'newest archive "
                "overall' on un-upgraded installs."
            ),
            "backup_run_incomplete": (
                "(NEW in 2.3.22) Warns when the latest run produced "
                "fewer tenant archives than there are enabled tenants. "
                "metadata.missing_tenants names the gap. Self-healing "
                "once the next complete run lands. This is the "
                "per-tenant DR-degradation signal that the redesign "
                "exists to surface."
            ),
        },

        # ----------------------------------------------------------
        # Best practices (updated for 3.0.0)
        # ----------------------------------------------------------
        "best_practices": [
            "Run a fresh backup after upgrading to 2.3.22 to gain "
            "per-tenant restore granularity.",
            "Always run dry_run=true first when restoring; the response "
            "previews exactly which collections will be touched.",
            "When recovering a single tenant's corruption, restore ONLY "
            "that tenant's archive (POST /restore with archive_name=...) "
            "— don't whole-run-restore unless multiple tenants or the "
            "global is corrupted.",
            "When recovering ONE specific KV collection (the most "
            "common single-collection scenario), use archives_scope to "
            "narrow per-archive: archives_scope={\"<archive_filename>\": "
            "{\"collections\": [\"<one_collection>\"]}}. The frontend "
            "exposes this via per-archive multiselects on the dry-run "
            "preview screen — operator unchecks items they don't want "
            "and clicks Apply.",
            "Investigate `backup_run_incomplete` Guardian alerts "
            "promptly: they identify tenants whose data is NOT "
            "restorable from the latest run.",
            "Test restore procedure periodically in a non-production "
            "environment using the dry_run preview.",
            "Backup archives are kept on each SH peer's local "
            "filesystem; pair with off-box tape/snapshot if you need "
            "SH-level disaster recovery.",
        ],

        # ----------------------------------------------------------
        # Reference docs
        # ----------------------------------------------------------
        "reference_doc": (
            "https://docs.trackme-solutions.com/latest/"
            "white_paper_trackme_backup_and_restore.html"
        ),
    }

    # Add dynamic API endpoint descriptions
    if api_endpoints:
        ref["api_endpoints"] = api_endpoints
    else:
        ref["api_endpoints"] = {
            "note": "Dynamic endpoint descriptions were not available."
        }

    # Add resource group info
    if resource_group_info:
        ref["resource_group"] = resource_group_info

    return ref


def build_backup_restore_description(service, request_info):
    """
    Build a comprehensive, AI-consumable description of Backup & Restore
    state for the Backup & Restore AI assistant.

    Args:
        service: Splunk service connection (system-level for KV store access)
        request_info: REST request info (for session key, server URI, user context)

    Returns:
        dict: Structured Backup & Restore description with both per-archive
        rows (sorted by mtime, last 50 for token efficiency) and grouped run
        summaries (so the AI can reason at run granularity without re-deriving
        from the raw rows).
    """

    backup_records = []
    total_backups = 0
    runs_summary = []
    error_note = None

    try:
        collection_name = "kv_trackme_backup_archives_info"
        collection = service.kvstore[collection_name]
        records = collection.data.query() or []
        total_backups = len(records)

        # Sort by mtime descending, limit per-row exposure to 50.
        records_sorted = sorted(
            records,
            key=lambda r: _safe_int(r.get("mtime", 0)),
            reverse=True,
        )
        for record in records_sorted[:50]:
            backup_records.append({
                "_key": record.get("_key", ""),
                "backup_archive": record.get("backup_archive", ""),
                "server_name": record.get("server_name", ""),
                "size": record.get("size", 0),
                "status": record.get("status", ""),
                "change_type": record.get("change_type", ""),
                "mtime": record.get("mtime", ""),
                "htime": record.get("htime", ""),
                "comment": record.get("comment", ""),
                # 3.0.0 fields — empty for legacy rows. Surfaced so the
                # AI can group by run without re-deriving.
                "backup_run_id": record.get("backup_run_id", ""),
                "archive_scope": record.get("archive_scope", ""),
                "tenant_id": record.get("tenant_id", ""),
                "archive_schema_version": record.get(
                    "archive_schema_version", ""
                ),
                "archive_sha256": record.get("archive_sha256", ""),
            })

        # Group ALL records (not just the top 50) into run summaries
        # using the same helper that GET /backup_runs uses, so the AI's
        # "what runs exist" mental model matches the listing endpoint.
        try:
            from trackme_libs_backup_archive import group_archives_by_run
            runs_summary = group_archives_by_run(records)
        except Exception as e:
            get_effective_logger().warning(
                f'function=build_backup_restore_description, '
                f'step="group_archives_by_run", exception="{str(e)}"'
            )

    except Exception as e:
        get_effective_logger().error(
            f'function=build_backup_restore_description, '
            f'step="query_kv_store", '
            f'exception="{str(e)}"'
        )
        error_note = (
            f"Unable to retrieve backup records from KV store: {str(e)}"
        )

    backup_summary = {
        "total_backups": total_backups,
        "recent_backups": backup_records,
        "runs": runs_summary,
        "run_count": len(runs_summary),
    }
    if error_note:
        backup_summary["error"] = error_note

    api_endpoints = None
    resource_group_info = None
    try:
        session_key = request_info.system_authtoken
        splunkd_uri = request_info.server_rest_uri
        resource_group_info = fetch_resource_group_describe(
            session_key, splunkd_uri, "backup_and_restore", "backup_and_restore"
        )
        api_endpoints = fetch_all_endpoint_describes(
            session_key, splunkd_uri, BACKUP_RESTORE_ENDPOINTS
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=build_backup_restore_description, '
            f'step="fetch_endpoint_describes", '
            f'exception="{str(e)}"'
        )

    knowledge_reference = _build_knowledge_reference(
        api_endpoints=api_endpoints,
        resource_group_info=resource_group_info,
    )

    # Embed the Concierge advisor knowledge so the chat LLM can propose
    # ``concierge_invocation`` action contracts when the user asks for an
    # action that requires a TrackMe REST API call (e.g. "trigger a backup
    # right now", "import this archive"). The Concierge block also ships
    # a compact projection of the live API catalog — without it the LLM
    # falls back to training-data guesses for paths.
    try:
        knowledge_reference["concierge_advisor"] = build_concierge_knowledge(
            splunkd_uri=request_info.server_rest_uri,
            session_key=request_info.system_authtoken,
            surface="global",
            feature_context="backup_and_restore",
        )
    except Exception as e:
        get_effective_logger().error(
            f'function=build_backup_restore_description, '
            f'step="build_concierge_knowledge", '
            f'exception="{str(e)}"'
        )

    return {
        "backup_restore_description": {
            "meta": {
                # Bumped to 3.0 to signal the multi-archive era. The AI
                # Assistant can branch its mental model on this if needed.
                "api_version": "3.0",
                "generated_at": time.time(),
                "context_type": "backup_restore",
                "total_backups": total_backups,
                "run_count": len(runs_summary),
            },
            "backup_summary": backup_summary,
            "knowledge_reference": knowledge_reference,
        }
    }
