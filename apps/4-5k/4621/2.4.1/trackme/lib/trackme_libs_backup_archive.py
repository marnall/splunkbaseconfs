#!/usr/bin/env python
# coding=utf-8

"""Helpers for the TrackMe multi-archive backup format (schema 3.0.0).

A backup *run* produces N+1 archives:
- One per enabled virtual tenant: ``trackme-backup-<RUN_ID>-tenant-<tid>.tar.zst``
- Exactly one global archive:     ``trackme-backup-<RUN_ID>-global.tar.zst``

Each archive is independently restorable. The functions in this module are
pure (no Splunk REST coupling) so they can be unit tested without a Splunk
runtime, and so the legacy single-archive code path and the new
multi-archive code path can share the same primitives.

Legacy archives produced by 2.3.21 and earlier (filename
``trackme-backup-YYYYMMDD-HHMMSS.{tar.zst,tgz}``) are recognised by
``parse_archive_filename`` so the listing and grouping helpers route them
to a synthetic "legacy" run.
"""

import hashlib
import json
import os
import random
import re
import string
import time
from typing import Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARCHIVE_SCHEMA_VERSION = "3.0.0"
"""Schema version stamped into the in-archive ``manifest.json`` of every
archive produced by 2.3.22+."""

IN_ARCHIVE_MANIFEST_NAME = "manifest.json"
"""Filename of the per-archive manifest written at the archive root."""

RUN_MANIFEST_SUFFIX = ".manifest.json"
"""Sidecar suffix for the run-level manifest at
``<backuproot>/<run_id>.manifest.json``."""

ARCHIVE_SCOPE_TENANT = "tenant"
ARCHIVE_SCOPE_GLOBAL = "global"
ARCHIVE_SCOPE_LEGACY = "legacy"

STATEFUL_CHARTS_PREFIX = "kv_trackme_stateful_alerting_charts_tenant_"
"""Per-tenant collections matching this prefix are excluded from backups
(they hold transient chart payloads regenerated on demand)."""

LEGACY_RUN_ID = "legacy"
"""Synthetic run identifier under which all pre-3.0.0 archives are grouped
in ``GET /backup_runs`` responses."""

# ---------------------------------------------------------------------------
# Filename grammar
# ---------------------------------------------------------------------------

_RUN_ID_RE = r"\d{8}-\d{6}-[a-z0-9]{6}"
_LEGACY_TIMESTAMP_RE = r"\d{8}-\d{6}"
_TENANT_ID_RE = r"[A-Za-z0-9._-]+"
_EXT_RE = r"tar\.zst|tgz"

_NEW_FILENAME_RE = re.compile(
    r"^trackme-backup-(?P<run_id>" + _RUN_ID_RE + r")"
    r"-(?P<scope>tenant-(?P<tenant_id>" + _TENANT_ID_RE + r")|global)"
    r"\.(?P<ext>" + _EXT_RE + r")$"
)

_LEGACY_FILENAME_RE = re.compile(
    r"^trackme-backup-(?P<run_id>" + _LEGACY_TIMESTAMP_RE + r")"
    r"\.(?P<ext>" + _EXT_RE + r")$"
)

_RANDOM_SUFFIX_ALPHABET = string.ascii_lowercase + string.digits


def make_run_id() -> str:
    """Build a fresh ``RUN_ID`` of the form ``YYYYMMDD-HHMMSS-XXXXXX``.

    The 6-character random suffix avoids same-second collisions when two
    runs happen to land within the same second on a Search Head Cluster
    peer (e.g. concurrent on-demand and scheduled backups).
    Time component uses local time, matching the existing handler's
    ``time.strftime`` convention so on-disk timestamps remain consistent.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    suffix = "".join(random.choice(_RANDOM_SUFFIX_ALPHABET) for _ in range(6))
    return f"{timestamp}-{suffix}"


def archive_filename(run_id: str, scope: str, tenant_id: Optional[str] = None,
                     ext: str = "tar.zst") -> str:
    """Build the filename for an archive produced by a 3.0.0 run.

    Args:
        run_id: a value produced by :func:`make_run_id`.
        scope: ``"tenant"`` or ``"global"``.
        tenant_id: required when ``scope == "tenant"``; ignored for global.
        ext: ``"tar.zst"`` (default) or ``"tgz"`` (gzip fallback).

    Raises:
        ValueError: if the inputs don't form a parseable filename.
    """
    if scope == ARCHIVE_SCOPE_TENANT:
        if not tenant_id:
            raise ValueError("tenant_id is required for tenant-scope archives")
        name = f"trackme-backup-{run_id}-tenant-{tenant_id}.{ext}"
    elif scope == ARCHIVE_SCOPE_GLOBAL:
        name = f"trackme-backup-{run_id}-global.{ext}"
    else:
        raise ValueError(f"unknown archive scope: {scope!r}")
    if not _NEW_FILENAME_RE.match(name):
        raise ValueError(
            f"refusing to emit malformed archive filename {name!r} "
            f"(run_id, tenant_id, or ext violates the grammar)"
        )
    return name


def parse_archive_filename(name: str) -> Optional[Dict[str, str]]:
    """Parse an archive filename into its components.

    Returns a dict with keys ``run_id``, ``scope`` (``tenant``/``global``/
    ``legacy``), ``tenant_id`` (empty for global and legacy), ``ext``,
    or ``None`` if the filename doesn't match either grammar.

    Tries the 3.0.0 grammar first; falls back to the legacy single-archive
    grammar so customers' pre-2.3.22 archives keep round-tripping.
    """
    base = os.path.basename(name)
    m = _NEW_FILENAME_RE.match(base)
    if m:
        scope_token = m.group("scope")
        if scope_token == "global":
            scope = ARCHIVE_SCOPE_GLOBAL
            tenant_id = ""
        else:
            scope = ARCHIVE_SCOPE_TENANT
            tenant_id = m.group("tenant_id") or ""
        return {
            "run_id": m.group("run_id"),
            "scope": scope,
            "tenant_id": tenant_id,
            "ext": m.group("ext"),
        }
    m = _LEGACY_FILENAME_RE.match(base)
    if m:
        return {
            "run_id": m.group("run_id"),
            "scope": ARCHIVE_SCOPE_LEGACY,
            "tenant_id": "",
            "ext": m.group("ext"),
        }
    return None


# ---------------------------------------------------------------------------
# Collection partitioning
# ---------------------------------------------------------------------------

_TENANT_SUFFIX_RE = re.compile(r"_tenant_(?P<tenant_id>" + _TENANT_ID_RE + r")$")


def partition_collections(collections: Iterable[str],
                          tenant_ids: Iterable[str]) -> Dict[str, object]:
    """Split a flat list of KV collection names into per-tenant + global buckets.

    Routing rules:

    * Names matching the ``STATEFUL_CHARTS_PREFIX`` are excluded from any
      bucket (they hold transient chart payloads regenerated on demand,
      matching the existing handler's blocklist).
    * Names ending in ``_tenant_<tid>`` where ``<tid>`` is in ``tenant_ids``
      go into ``tenant[<tid>]``.
    * Names ending in ``_tenant_<tid>`` where ``<tid>`` is NOT in
      ``tenant_ids`` (orphans from a deleted tenant) are routed to
      ``orphan_tenant[<tid>]`` so they remain visible to the operator
      without being silently dropped.
    * Everything else is routed to ``global``.

    Args:
        collections: iterable of collection names (e.g. from
            ``/storage/collections/config``).
        tenant_ids: iterable of currently-enabled tenant ids.

    Returns:
        ``{"global": [...], "tenant": {tid: [...]}, "orphan_tenant": {tid: [...]}, "excluded": [...]}``
        — every input name appears in exactly one of the four buckets.
        ``tenant`` always has an entry for each id in ``tenant_ids`` even if
        empty, so callers can iterate enabled tenants without KeyErrors.
    """
    enabled = set(tenant_ids)
    out: Dict[str, object] = {
        "global": [],
        "tenant": {tid: [] for tid in enabled},
        "orphan_tenant": {},
        "excluded": [],
    }
    for name in collections:
        if name.startswith(STATEFUL_CHARTS_PREFIX):
            out["excluded"].append(name)
            continue
        m = _TENANT_SUFFIX_RE.search(name)
        if m:
            tid = m.group("tenant_id")
            if tid in enabled:
                out["tenant"][tid].append(name)
            else:
                out["orphan_tenant"].setdefault(tid, []).append(name)
            continue
        out["global"].append(name)
    # stable order for deterministic archive contents and tests
    out["global"].sort()
    out["excluded"].sort()
    for tid, names in out["tenant"].items():
        names.sort()
    for tid, names in out["orphan_tenant"].items():
        names.sort()
    return out


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def write_in_archive_manifest(workdir: str, manifest: Dict) -> str:
    """Write the in-archive ``manifest.json`` and return its path.

    The manifest is the source of truth for ``post_restore``'s schema
    detection: the presence of a 3.0.0 manifest at the archive root drives
    the new restore code path; its absence falls through to the legacy
    sidecar-driven detection.
    """
    path = os.path.join(workdir, IN_ARCHIVE_MANIFEST_NAME)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return path


def read_in_archive_manifest(workdir: str) -> Optional[Dict]:
    """Read the in-archive ``manifest.json`` if present, else return ``None``.

    Returning ``None`` (rather than raising) is the contract that lets
    ``post_restore`` cleanly fall through to the legacy detection path
    when handed a pre-3.0.0 archive.
    """
    path = os.path.join(workdir, IN_ARCHIVE_MANIFEST_NAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Run grouping
# ---------------------------------------------------------------------------

def group_archives_by_run(rows: Iterable[Dict]) -> List[Dict]:
    """Group ``kv_trackme_backup_archives_info`` rows into run summaries.

    Rows with ``backup_run_id`` set are grouped by that id. Rows lacking
    ``backup_run_id`` (legacy archives produced before 2.3.22) are folded
    into a single synthetic ``legacy`` run so the UI can render them as a
    distinct "Legacy archives" section.

    Returns a list sorted by ``started_epoch`` descending, with the legacy
    bucket (if any) always at the bottom regardless of its rows' mtimes.
    Each summary dict contains: ``run_id``, ``legacy`` (bool),
    ``server_name`` (the producing peer for non-legacy runs; empty for
    legacy), ``started_epoch``, ``finished_epoch``, ``archives`` (list of
    rows in the run), ``tenant_archive_count``, ``has_global``.
    """
    by_run: Dict[str, List[Dict]] = {}
    legacy_rows: List[Dict] = []
    for row in rows:
        run_id = row.get("backup_run_id")
        if run_id:
            by_run.setdefault(str(run_id), []).append(row)
        else:
            legacy_rows.append(row)
    summaries: List[Dict] = []
    for run_id, run_rows in by_run.items():
        mtimes = [_safe_float(r.get("mtime")) for r in run_rows]
        mtimes = [m for m in mtimes if m is not None]
        scopes = [r.get("archive_scope") for r in run_rows]
        servers = {r.get("server_name") for r in run_rows if r.get("server_name")}
        summaries.append({
            "run_id": run_id,
            "legacy": False,
            "server_name": next(iter(servers)) if len(servers) == 1 else "",
            "server_names": sorted(servers),
            "started_epoch": min(mtimes) if mtimes else 0.0,
            "finished_epoch": max(mtimes) if mtimes else 0.0,
            "archives": list(run_rows),
            "tenant_archive_count": sum(1 for s in scopes if s == ARCHIVE_SCOPE_TENANT),
            "has_global": any(s == ARCHIVE_SCOPE_GLOBAL for s in scopes),
        })
    summaries.sort(key=lambda s: s["finished_epoch"], reverse=True)
    if legacy_rows:
        legacy_mtimes = [_safe_float(r.get("mtime")) for r in legacy_rows]
        legacy_mtimes = [m for m in legacy_mtimes if m is not None]
        summaries.append({
            "run_id": LEGACY_RUN_ID,
            "legacy": True,
            "server_name": "",
            "server_names": sorted({r.get("server_name") for r in legacy_rows
                                    if r.get("server_name")}),
            "started_epoch": min(legacy_mtimes) if legacy_mtimes else 0.0,
            "finished_epoch": max(legacy_mtimes) if legacy_mtimes else 0.0,
            "archives": list(legacy_rows),
            "tenant_archive_count": 0,
            "has_global": False,
        })
    return summaries


def _safe_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Integrity helpers
# ---------------------------------------------------------------------------

_SHA256_BUFSIZE = 1024 * 1024  # 1 MiB


def compute_sha256(path: str) -> str:
    """Stream-hash a file; safe for the multi-GB archives this format
    exists to enable."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_SHA256_BUFSIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Run / archive identity helpers (used by post_restore, delete_backup, …)
# ---------------------------------------------------------------------------

def is_legacy_archive_name(name: str) -> bool:
    """True iff ``name`` matches the pre-2.3.22 single-archive grammar."""
    parsed = parse_archive_filename(name)
    return parsed is not None and parsed["scope"] == ARCHIVE_SCOPE_LEGACY


def is_new_archive_name(name: str) -> bool:
    """True iff ``name`` matches the 3.0.0 multi-archive grammar."""
    parsed = parse_archive_filename(name)
    return parsed is not None and parsed["scope"] in (
        ARCHIVE_SCOPE_TENANT, ARCHIVE_SCOPE_GLOBAL,
    )


# ---------------------------------------------------------------------------
# Selective restore body-param parsing (3.0.0+)
# ---------------------------------------------------------------------------


def parse_archives_scope(raw) -> Dict[str, Dict[str, List[str]]]:
    """Sanitise the ``archives_scope`` body parameter for selective restore.

    Accepts the user-supplied value (any type) and returns a clean
    dict mapping archive filename → ``{"collections": [...]?, "knowledge_objects": [...]?}``.
    Anything malformed silently collapses to an empty dict so the
    request behaves as if ``archives_scope`` were absent (= flat-filter
    fallback). Per-key validation is per-archive so a single malformed
    entry doesn't poison the whole map.

    Per-list shape rules:
      * Missing or ``"all"`` → omit the key (falls through to flat
        filter at apply time).
      * ``list`` → strings are coerced to str, stripped, empty entries
        dropped.
      * ``str`` → split on commas, stripped, empty entries dropped.
      * Anything else → omit the key.

    Extracted to this module so it can be unit-tested without
    importing the handler (which pulls in splunklib + all Splunk
    runtime). The handler's body parser delegates here.
    """
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, List[str]]] = {}
    for arc_name, scope_entry in raw.items():
        if not isinstance(arc_name, str) or not arc_name:
            continue
        if not isinstance(scope_entry, dict):
            continue
        clean_entry: Dict[str, List[str]] = {}
        for key in ("collections", "knowledge_objects"):
            value = scope_entry.get(key)
            if value == "all" or value is None:
                continue
            if isinstance(value, list):
                cleaned = [str(v).strip() for v in value if str(v).strip()]
                clean_entry[key] = cleaned
            elif isinstance(value, str):
                cleaned = [
                    x.strip() for x in value.split(",") if x.strip()
                ]
                clean_entry[key] = cleaned
            # Anything else is silently dropped — preserves the
            # handler's "request behaves as if archives_scope were
            # absent" contract on malformed input.
        if clean_entry:
            out[arc_name] = clean_entry
    return out


def resolve_per_archive_filters(
    archives_scope: Dict[str, Dict[str, List[str]]],
    archive_filename_str: str,
    flat_kvstore_scope,
    flat_ko_list,
) -> Dict[str, object]:
    """Resolve the effective per-archive filters for a single archive.

    Returns a dict with three keys:
      * ``effective_kv_scope`` — the resolved KV-collection filter
        (per-archive override OR ``flat_kvstore_scope``).
      * ``effective_ko_list`` — the resolved KO filter (per-archive
        override OR ``flat_ko_list``).
      * ``selective`` — True iff ``archives_scope`` has an entry for
        this archive (i.e. the operator narrowed the restore for this
        archive specifically).

    Used by the per-archive restore loop (in the handler) AND by unit
    tests that assert the override semantics. Pure function — no
    Splunk dependencies.
    """
    per_archive = (archives_scope or {}).get(archive_filename_str) or {}
    effective_kv_scope = per_archive.get("collections", flat_kvstore_scope)
    effective_ko_list = per_archive.get("knowledge_objects", flat_ko_list)
    return {
        "effective_kv_scope": effective_kv_scope,
        "effective_ko_list": effective_ko_list,
        "selective": bool(per_archive),
    }
