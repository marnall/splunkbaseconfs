#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_backup_and_restore.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import hashlib
import json
import os
import shutil
import socket
import sys
import tarfile
import time
import re
import base64
import subprocess
import glob
import threading
import uuid
from os import listdir
from os.path import isfile, join

# Third-party libraries
import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.backup_and_restore", "trackme_rest_api_backup_and_restore.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_create_alert,
    trackme_create_kvcollection,
    trackme_create_kvtransform,
    trackme_create_macro,
    trackme_create_report,
    trackme_delete_kvcollection,
    trackme_delete_kvtransform,
    trackme_delete_macro,
    trackme_delete_report,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
)

# import TrackMe get data libs
from trackme_libs_get_data import (
    get_full_kv_collection,
)

# Multi-archive (3.0.0) helpers — pure functions, see PR #1459 (#1) for the
# foundation. The legacy single-archive code paths in this file (1.0.0 and
# 2.0.0 schema, used by post_restore for archives produced before 2.3.22)
# do not consume these helpers and continue to operate unchanged.
from trackme_libs_backup_archive import (
    ARCHIVE_SCHEMA_VERSION,
    ARCHIVE_SCOPE_GLOBAL,
    ARCHIVE_SCOPE_TENANT,
    LEGACY_RUN_ID,
    archive_filename as _bbk_archive_filename,
    compute_sha256 as _bbk_compute_sha256,
    group_archives_by_run as _bbk_group_archives_by_run,
    is_new_archive_name,
    make_run_id as _bbk_make_run_id,
    parse_archive_filename as _bbk_parse_archive_filename,
    parse_archives_scope as _bbk_parse_archives_scope,
    partition_collections as _bbk_partition_collections,
    read_in_archive_manifest as _bbk_read_in_archive_manifest,
    resolve_per_archive_filters as _bbk_resolve_per_archive_filters,
    write_in_archive_manifest as _bbk_write_in_archive_manifest,
)

# import Splunk libs
import splunklib.client as client

# import the collections dict
from collections_data import vtenant_account_default

# compression exec helpers
try:
    from trackme_compress_exec import (
        is_available as zstd_is_available,
        compress_tar as zstd_compress_tar,
        decompress as zstd_decompress,
        test_archive as zstd_test_archive,
    )
except Exception:
    # Safe fallbacks if helper cannot be imported
    def zstd_is_available():
        return False

    def zstd_compress_tar(_):
        raise RuntimeError("zstd not available")

    def zstd_decompress(*_, **__):
        raise RuntimeError("zstd not available")

    def zstd_test_archive(_):
        return 1

#
# Splunk Cloud certification notes: these functions create and manage archive files for the application in the following directory $SPLUNK/etc/apps/trackme/backup
# There are no options to perform any kind of file manipulations out of this application directory
#


# zstd command resolution moved to trackme_zstd_exec (lib)


def is_zstd_available():
    """Check if zstd compression is available on the system."""
    available = False
    try:
        available = bool(zstd_is_available())
    except Exception as e:
        logger.info(f"zstd is not available: {str(e)}")
        available = False
    if available:
        logger.info("zstd is available")
    else:
        logger.info("zstd command not found in PATH")
    return available


def create_compressed_archive(source_dir, archive_name):
    """Create a compressed archive using zstd if available, otherwise fall back to gzip."""
    # Get the backup directory path from the source_dir
    backup_dir = os.path.dirname(source_dir)

    if is_zstd_available():
        # Use zstd compression
        logger.info(
            f'Creating zstd compressed archive for="{source_dir}" with archive_name="{archive_name}"'
        )
        zst_name = os.path.join(backup_dir, f"{archive_name}.tar.zst")
        try:
            # Create tar file first
            tar_name = os.path.join(backup_dir, f"{archive_name}.tar")
            with tarfile.open(tar_name, mode="w") as archive:
                archive.add(source_dir, arcname="")

            # Compress with zstd
            zstd_compress_tar(tar_name)

            # Remove the uncompressed tar file
            os.remove(tar_name)

            return zst_name
        except Exception as e:
            logger.warning(
                f"Failed to create zstd archive, falling back to gzip: {str(e)}"
            )
            # Fall back to gzip
            pass

    else:
        logger.info(f"Compression using zstd is not available, falling back to gzip")

    # Fall back to gzip compression
    tgz_name = os.path.join(backup_dir, f"{archive_name}.tgz")
    with tarfile.open(tgz_name, mode="w:gz") as archive:
        archive.add(source_dir, arcname="")

    return tgz_name


def extract_archive(archive_path, extract_dir):
    """Extract an archive file (.tgz or .tar.zst) to the specified directory."""
    logger.info(
        f'Starting archive extraction: archive_path="{archive_path}", extract_dir="{extract_dir}"'
    )

    # Validate input parameters
    if not os.path.exists(archive_path):
        logger.error(f"Archive file does not exist: {archive_path}")
        return False

    if not os.path.isfile(archive_path):
        logger.error(f"Archive path is not a file: {archive_path}")
        return False

    # Check file size
    file_size = os.path.getsize(archive_path)
    logger.info(f"Archive file size: {file_size} bytes")
    if file_size == 0:
        logger.error(f"Archive file is empty: {archive_path}")
        return False

    # Ensure extract directory exists
    os.makedirs(extract_dir, exist_ok=True)

    # Security: Validate extract directory is absolute and safe
    extract_dir = os.path.abspath(extract_dir)
    logger.info(f"Using absolute extract directory: {extract_dir}")

    def safe_extract_member(tar, member, extract_dir):
        """Safely extract a single member from a tar archive, preventing path traversal attacks."""
        # Get the absolute path where this member would be extracted
        member_path = os.path.join(extract_dir, member.name)
        member_path = os.path.abspath(member_path)

        # Security check: ensure the member path is within the extract directory
        # Use os.path.commonpath to properly validate containment
        try:
            common_path = os.path.commonpath([extract_dir, member_path])
            if common_path != extract_dir:
                logger.error(
                    f'SECURITY VIOLATION: member "{member.name}" would extract outside allowed directory. Blocked path traversal attack.'
                )
                return False
        except ValueError:
            # commonpath raises ValueError if paths are on different drives (Windows)
            # or if one path is a prefix of the other but not a proper subdirectory
            logger.error(
                f'SECURITY VIOLATION: member "{member.name}" would extract outside allowed directory. Blocked path traversal attack.'
            )
            return False

        # Extract the member
        try:
            tar.extract(member, extract_dir)
            logger.debug(f"Safely extracted member: {member.name}")
            return True
        except Exception as e:
            logger.error(f'Failed to extract member "{member.name}": {str(e)}')
            return False

    if archive_path.endswith(".tar.zst"):
        # Extract zstd compressed archive
        logger.info(f"Detected zstd compressed archive: {archive_path}")
        if is_zstd_available():
            logger.info("zstd is available, proceeding with zstd extraction")
            try:
                # Create a temporary directory for the intermediate tar file
                import tempfile

                temp_dir = tempfile.mkdtemp(prefix="trackme_extract_")
                logger.info(f"Created temporary directory: {temp_dir}")

                try:
                    # Decompress with zstd first to a temporary location
                    tar_path = os.path.join(
                        temp_dir, os.path.basename(archive_path)[:-4]
                    )  # Remove .zst extension
                    logger.info(
                        f"Decompressing zstd archive to temporary tar file: {tar_path}"
                    )

                    # Use absolute paths and capture output for debugging
                    result = zstd_decompress(
                        os.path.abspath(archive_path),
                        tar_path,
                        cwd=temp_dir,
                    )
                    logger.info(f"zstd decompression output: {result.stdout}")
                    if result.stderr:
                        logger.info(f"zstd decompression stderr: {result.stderr}")

                    # Verify the decompressed tar file exists and has content
                    if not os.path.exists(tar_path):
                        logger.error(f"Failed to create temporary tar file: {tar_path}")
                        return False

                    tar_size = os.path.getsize(tar_path)
                    logger.info(f"Temporary tar file size: {tar_size} bytes")
                    if tar_size == 0:
                        logger.error(f"Temporary tar file is empty: {tar_path}")
                        return False

                    # Extract the tar file securely
                    logger.info(f"Extracting tar file to: {extract_dir}")
                    with tarfile.open(tar_path, mode="r") as tar:
                        # Security: Extract members one by one with path validation
                        for member in tar.getmembers():
                            if not safe_extract_member(tar, member, extract_dir):
                                logger.error(
                                    f"Failed to safely extract member: {member.name}"
                                )
                                return False

                    logger.info("zstd archive extraction completed successfully")
                    return True
                finally:
                    # Clean up the temporary directory and files
                    logger.info(f"Cleaning up temporary directory: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Failed to extract zstd archive: {str(e)}")
                return False
        else:
            logger.error("zstd is not available, cannot extract .tar.zst archive")
            return False
    elif archive_path.endswith(".tgz"):
        # Extract gzip compressed archive
        logger.info(f"Detected gzip compressed archive: {archive_path}")
        try:
            with tarfile.open(archive_path, mode="r:gz") as tar:
                # Security: Extract members one by one with path validation
                for member in tar.getmembers():
                    if not safe_extract_member(tar, member, extract_dir):
                        logger.error(f"Failed to safely extract member: {member.name}")
                        return False
            logger.info("gzip archive extraction completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to extract gzip archive: {str(e)}")
            return False
    else:
        logger.error(f"Unsupported archive format: {archive_path}")
        return False


def test_splunkd_connectivity(hostname, port, session_key, timeout=5):
    """
    Test connectivity to a Splunk instance by making a simple REST call.

    :param hostname: Target hostname or FQDN
    :param port: Splunkd REST port
    :param session_key: Session key for authentication
    :param timeout: Connection timeout in seconds
    :return: True if connectivity successful, False otherwise
    """
    try:
        target_url = f"https://{hostname}:{port}/services/server/info"
        headers = {
            "Authorization": f"Splunk {session_key}",
            "Content-Type": "application/json",
        }

        response = requests.get(
            target_url, headers=headers, verify=False, timeout=timeout
        )

        # Check if we get a valid response (200 or 401/403 are OK - means server is reachable)
        if response.status_code in [200, 401, 403]:
            logger.debug(
                f"Connectivity test successful for {hostname}:{port} (status: {response.status_code})"
            )
            return True
        else:
            logger.debug(
                f"Connectivity test failed for {hostname}:{port} (status: {response.status_code})"
            )
            return False

    except Exception as e:
        logger.debug(f"Connectivity test failed for {hostname}:{port} - {str(e)}")
        return False


def cleanup_backup_directories(backup_root, exclude_dir=None, min_age_seconds=3600):
    """Clean up any leftover temporary backup directories from failed attempts.

    Called at the start of every ``_post_backup_body`` (line ~1696) to sweep
    crashed-process orphan workdirs from previous failed backup runs.
    Filters by the ``trackme-backup-`` prefix.

    ``min_age_seconds`` defends against races with concurrent restore
    operations that legitimately create directories under ``backup_root``
    using the same prefix while they're still running:

    * ``_handle_restore_3_0_0`` extracts the target archive into
      ``backup_root/trackme-backup-restore-<stem>-<epoch>`` (line
      ~7525-7532) and reads from it for the duration of the restore.
    * ``_v3_restore_tenant_main_record_from_global`` (the central-record
      sync helper added in PR #1633) extracts the global archive into
      ``backup_root/trackme-backup-restore-vtenants-lookup-<stem>-<epoch>-<uuid>``
      (line ~8045-8052) for a few seconds to read
      ``kv_trackme_virtual_tenants.json``.

    Without an age filter, a scheduled backup firing during an in-flight
    restore would ``shutil.rmtree`` both dirs mid-restore. For the main
    restore extract dir that breaks the restore loudly; for the
    vtenants-lookup helper it silently regresses the PR #1633 fix
    (helper returns ``(False, None)`` → Priority B no-op → central
    record stays at live state instead of backup-time state). Bugbot
    finding on release PR #1575: "Restore temp dir vulnerable to
    concurrent backup cleanup" (commit 4a1a95b).

    Live restore operations finish in seconds (vtenants-lookup helper)
    to minutes (main extract dir for large tenant archives); the 1-hour
    default threshold is generous enough to cover any reasonable
    in-flight restore while still cleaning crashed-process orphans
    promptly on the next backup run.

    The threshold is on the directory's ``mtime`` (mirrors the existing
    retention-purge convention at line ~2947 which also reads
    ``stat.st_mtime``). Live restores touch their workdir constantly
    via tar extraction + JSON writes, so ``mtime`` stays close to "now"
    until the operation finishes.
    """
    now = time.time()
    try:
        for item in os.listdir(backup_root):
            item_path = os.path.join(backup_root, item)
            if os.path.isdir(item_path) and item.startswith("trackme-backup-"):
                # Skip the current backup directory if specified
                if exclude_dir and item_path == exclude_dir:
                    continue
                # Skip directories that are too young — they may belong
                # to an in-flight restore or another concurrent backup
                # whose workdir has been pre-created but not yet
                # registered via exclude_dir.
                try:
                    age = now - os.path.getmtime(item_path)
                except OSError:
                    # Stat failed (race with delete, broken symlink, …)
                    # — fall through to the legacy delete attempt;
                    # ``ignore_errors=True`` on rmtree below will swallow
                    # a benign ENOENT.
                    age = float("inf")
                if age < min_age_seconds:
                    logger.info(
                        f"Skipping recent backup directory "
                        f"(age {age:.0f}s < {min_age_seconds}s, may be "
                        f"in-flight): {item_path}"
                    )
                    continue
                logger.info(f"Cleaning up leftover backup directory: {item_path}")
                shutil.rmtree(item_path, ignore_errors=True)
                logger.info(
                    f"Successfully removed leftover backup directory: {item_path}"
                )
    except Exception as e:
        logger.warning(f"Failed to clean up leftover backup directories: {str(e)}")
        # Don't fail the backup process for cleanup errors


def _resolve_canonical_server_name():
    """Return the canonical SHC peer identifier for ``server_name`` rows
    written to ``kv_trackme_backup_archives_info``.

    Prefers ``socket.getfqdn()`` when it returns something distinct from
    the bare hostname AND isn't a ``.local`` mDNS suffix (which is the
    pattern macOS dev boxes hit); otherwise falls back to
    ``socket.gethostname()``. This matches the convention the
    ``get_backup`` auto-discovery branch and the ``post_import_backup``
    direct-registration path already use inline — both written before
    ``post_backup`` itself did, leaving ``post_backup`` as the only
    canonical write path that produced short-hostname rows.

    Operator-reported symptom this resolves
    ---------------------------------------

    Two backup-archives rows for the same SHC peer would appear in the
    UI with different ``server_name`` values:

      * Row from ``post_backup``        → ``sh-i-abcdef`` (short)
      * Row from ``post_import_backup`` → ``sh-i-abcdef.scde-X.splunkcloud.com`` (FQDN)

    Same host, two identifiers. By routing ``post_backup`` through the
    same helper as the other write paths, 2.3.23+ rows converge on the
    FQDN-preferring form.

    Why FQDN rather than the reverse direction
    ------------------------------------------

    * The two pre-existing write paths (auto-discovery + import) already
      use this convention; changing them to short instead would require
      a duplicate-check migration (a previous bugbot review of PR #1556
      explicitly added this convention to avoid duplicate-row inserts
      when discovery had already FQDN-registered something).
    * SHC delegation in ``_v3_delegate_restore_to_peer`` has a "try
      short → FQDN fallback" already; the asymmetry favours the FQDN-
      form server_name surviving short-only DNS environments better
      than the reverse.
    * The ``.local`` carve-out covers macOS dev boxes where ``getfqdn``
      otherwise returns ``hostname.local`` (mDNS), which doesn't
      resolve cluster-wide.

    Inline FQDN-preferring blocks at ``get_backup`` (~line 905) and
    ``post_import_backup`` (~line 10645) duplicate this convention —
    they'd ideally route through this helper too, but that's a pure
    refactor deliberately scoped out of this fix to keep the
    behavioural change minimal. Tracked for a future quality-pass PR.
    """
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    if fqdn and fqdn != hostname and not fqdn.endswith(".local"):
        return fqdn
    return hostname


def _derive_v3_fields_for_discovery(archive_basename, full_metadata):
    """Derive the 3.0.0 fields (``backup_run_id``, ``archive_scope``,
    ``tenant_id``, ``archive_schema_version``, ``archive_sha256``,
    ``run_total_archives``) for a row about to be inserted into
    ``kv_trackme_backup_archives_info`` by the auto-discovery path or by
    ``post_import_backup``. See Issue #1555.

    Resolution order:

    1. **Sidecar** — ``post_backup`` writes the 3.0.0 fields directly
       into ``<archive>.full.meta`` (see lines ~1665-1680). When an
       archive is exported from one instance and imported into another,
       the sidecar travels with it (the ``.tgz`` wrapper bundles
       ``<archive>.tar.zst`` + the two sidecars). When the sidecar
       carries the fields, we trust them — they are the source-of-truth
       written by the producing peer.

    2. **Filename grammar** — when the sidecar is missing 3.0.0 fields
       (e.g. an operator copied just the ``.tar.zst`` onto disk without
       sidecars, or the sidecar was hand-edited), fall back to
       ``parse_archive_filename``. The 3.0.0 grammar
       (``trackme-backup-<run_id>-tenant-<tid>.tar.zst`` /
       ``trackme-backup-<run_id>-global.tar.zst``) encodes
       ``run_id`` / ``scope`` / ``tenant_id`` losslessly, so this is
       a complete fallback for those three fields.
       ``archive_schema_version`` is pinned to the constant
       ``ARCHIVE_SCHEMA_VERSION`` (3.0.0 today — currently the only
       version that uses this filename grammar).
       ``archive_sha256`` / ``run_total_archives`` stay empty when
       the sidecar doesn't carry them: they're nice-to-have, not
       load-bearing for run grouping or restore.

    3. **Genuine legacy** — when the filename parses as legacy or
       doesn't parse at all, the return value is an empty dict. The
       caller's insert proceeds with the V2-only fields and the row
       lands in the synthetic legacy bucket. This preserves the legacy
       compatibility path for pre-2.3.22 archives.

    Args:
        archive_basename: ``os.path.basename`` of the archive on disk,
            e.g. ``"trackme-backup-20260512-020012-nfu0y0-global.tar.zst"``.
        full_metadata: parsed ``<archive>.full.meta`` JSON (may be empty
            or partial — both cases are handled).

    Returns:
        Dict of the 3.0.0 fields ready to merge into the KV insert
        record. Empty when the archive is not a 3.0.0 archive.
    """
    if not isinstance(full_metadata, dict):
        full_metadata = {}

    sidecar_run_id = full_metadata.get("backup_run_id") or ""
    sidecar_scope = full_metadata.get("archive_scope") or ""
    sidecar_tenant_id = full_metadata.get("tenant_id") or ""
    sidecar_schema = full_metadata.get("archive_schema_version") or ""
    sidecar_sha256 = full_metadata.get("archive_sha256") or ""
    sidecar_run_total = full_metadata.get("run_total_archives")

    # Resolution path A — sidecar carries the 3.0.0 fields. Trust it.
    if sidecar_run_id and sidecar_scope and sidecar_schema:
        out = {
            "backup_run_id": sidecar_run_id,
            "archive_scope": sidecar_scope,
            "tenant_id": sidecar_tenant_id,
            "archive_schema_version": sidecar_schema,
        }
        if sidecar_sha256:
            out["archive_sha256"] = sidecar_sha256
        if sidecar_run_total is not None:
            out["run_total_archives"] = sidecar_run_total
        return out

    # Resolution path B — fall back to filename grammar.
    parsed = None
    try:
        parsed = _bbk_parse_archive_filename(archive_basename)
    except Exception:
        parsed = None

    if parsed and parsed.get("scope") in (ARCHIVE_SCOPE_TENANT, ARCHIVE_SCOPE_GLOBAL):
        out = {
            "backup_run_id": parsed.get("run_id") or "",
            "archive_scope": parsed.get("scope") or "",
            "tenant_id": parsed.get("tenant_id") or "",
            "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
        }
        # Preserve any partial sidecar values that ARE present even
        # though the sidecar didn't qualify under path A (e.g. operator
        # hand-edited the sidecar and left sha256 intact).
        if sidecar_sha256:
            out["archive_sha256"] = sidecar_sha256
        if sidecar_run_total is not None:
            out["run_total_archives"] = sidecar_run_total
        return out

    # Resolution path C — genuine legacy or unparseable. Leave the
    # 3.0.0 fields empty; the row will land in the legacy bucket.
    return {}


class TrackMeHandlerBackupAndRestore_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerBackupAndRestore_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_backup_and_restore(self, request_info, **kwargs):
        response = {
            "resource_group_name": "backup_and_restore",
            "resource_group_desc": "These endpoints provide backup and restore facilities for the Kvstore collections created and managed in TrackMe, this includes the full scope of active and enabled tenants",
        }

        return {"payload": response, "status": 200}

    def get_export_backup(self, request_info, **kwargs):
        """
        Handles GET requests for token-based download of exported backup archives.
        Used when binary_mode=True to avoid loading large base64 strings in POST responses.
        """

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint streams a previously-exported backup "
                    "archive to the caller as a binary download. It is the "
                    "second half of the binary-mode export flow: a POST to "
                    "the backup-export endpoint with binary_mode=true stages "
                    "the archive on disk under the trackme/backup/downloads "
                    "directory and returns a single-use download_token; this "
                    "GET endpoint is then called with that token to retrieve "
                    "the file. Token-based download avoids loading large "
                    "base64-encoded archives into memory in a single REST "
                    "response. Returns HTTP 400 when download_token is "
                    "missing and HTTP 404 when the staged file cannot be "
                    "located (token expired, already consumed, or invalid)."
                ),
                "resource_desc": "Download a previously-staged backup archive using a single-use download_token",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/backup_and_restore/export_backup?download_token=abc123def456"',
                "options": [
                    {
                        "download_token": "REQUIRED. Single-use token returned by a prior binary-mode backup export request. Passed as a query-string parameter",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get download_token from query parameters
        download_token = None
        try:
            # Try different ways to access query parameters depending on Splunk version
            if hasattr(request_info, "query") and request_info.query:
                # Query parameters as dictionary
                if isinstance(request_info.query, dict):
                    download_token = request_info.query.get("download_token")
                # Query parameters as list (some Splunk versions)
                elif isinstance(request_info.query, list) and len(request_info.query) > 0:
                    download_token = request_info.query[0].get("download_token") if isinstance(request_info.query[0], dict) else None
            # Fallback to raw_args
            if not download_token and hasattr(request_info, "raw_args"):
                if isinstance(request_info.raw_args, dict) and "download_token" in request_info.raw_args:
                    download_token = request_info.raw_args["download_token"]
                # Handle case where raw_args might be a list
                elif isinstance(request_info.raw_args, list) and len(request_info.raw_args) > 0:
                    for arg in request_info.raw_args:
                        if isinstance(arg, dict) and "download_token" in arg:
                            download_token = arg["download_token"]
                            break
        except Exception as e:
            logger.error(f"Error extracting download_token: {str(e)}")
        
        if not download_token:
            return {
                "payload": {"error": "download_token parameter is required"},
                "status": 400,
            }
        
        # Locate the token file in downloads directory
        backup_dir = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
        downloads_dir = os.path.join(backup_dir, "downloads")
        
        if not os.path.exists(downloads_dir):
            return {
                "payload": {"error": "Downloads directory not found"},
                "status": 404,
            }
        
        # Find file matching the token (format: token_timestamp_filename.tgz)
        token_file = None
        try:
            for filename in os.listdir(downloads_dir):
                if filename.startswith(f"{download_token}_"):
                    token_file = os.path.join(downloads_dir, filename)
                    break
        except Exception as e:
            logger.error(f"Error searching for token file: {str(e)}")
            return {
                "payload": {"error": f"Error locating token file: {str(e)}"},
                "status": 500,
            }
        
        if not token_file or not os.path.exists(token_file):
            return {
                "payload": {"error": "Invalid or expired download token"},
                "status": 404,
            }
        
        # Extract original filename from token filename
        # Format: token_timestamp_filename.tgz
        try:
            parts = os.path.basename(token_file).split("_", 2)
            if len(parts) >= 3:
                original_filename = "_".join(parts[2:])
            else:
                original_filename = os.path.basename(token_file)
        except Exception:
            original_filename = "backup.tgz"
        
        try:
            # Read entire file and encode as base64
            # Note: We must encode the entire file as one unit to avoid invalid padding
            # in the middle of the base64 string (chunked encoding would add padding
            # after each chunk, which is invalid - padding must only be at the end)
            with open(token_file, "rb") as f:
                file_data = f.read()
            
            base64_data = base64.b64encode(file_data).decode("utf-8")
            
            # Clean up the file after reading
            try:
                os.remove(token_file)
                logger.info(f"Cleaned up token file: {token_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up token file {token_file}: {str(e)}")
            
            # Return as dict (consistent with POST handler) - Splunk framework will handle JSON encoding
            return {
                "payload": {
                    "archive_base64": base64_data,
                    "filename": original_filename,
                },
                "status": 200,
            }
        except Exception as e:
            logger.error(f"Error serving export file: {str(e)}")
            return {
                "payload": {"error": f"Failed to serve file: {str(e)}"},
                "status": 500,
            }

    # List backup archive files known from the KV, add any local file that the KV wouldn't do about
    def get_backup(self, request_info, **kwargs):
        """
        A simple function to safely retrieve all records from a KVstore collection with pagination
        """

        def get_full_collection_records(collection):
            collection_records = []
            collection_records_dict = {}
            collection_records_keys = set()

            end = False
            skip_tracker = 0
            while not end:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if process_collection_records:
                    for item in process_collection_records:
                        collection_records.append(item)
                        collection_records_dict[item.get("_key")] = (
                            item  # Add the entire item to the dictionary
                        )
                        collection_records_keys.add(item.get("_key"))
                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            return collection_records, collection_records_dict, collection_records_keys

        describe = False

        # init
        mode = "full"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            # mode summary
            try:
                mode = resp_dict["mode"]
                # valid mode: full | summary (defaults to full)
                if mode not in ("full", "summary"):
                    return {
                        "payload": f'Invalid mode="{mode}", valid modes are: full | summary',
                        "status": 400,
                    }
            except Exception as e:
                mode = "full"

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        if describe:
            response = {
                "describe": "This endpoint lists all the backup files available on the search head, files are stored in the TrackMe backup directory, it requires a GET call with the following arguments:",
                "resource_desc": "Get the list of backups known to TrackMe",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/backup_and_restore/backup"',
                "options": [
                    {
                        "mode": "(string) OPTIONAL: The output mode, valid values are full | summary, defaults to full",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        else:
            # Get splunkd port
            splunkd_port = request_info.server_rest_port

            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # Set backup root dir
            backuproot = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")

            # get local server name — FQDN-preferring, matching the
            # convention ``post_backup`` and ``post_import_backup``
            # now use.  Previously ``socket.gethostname()`` (short
            # form), which fed the dedup query at line 866 below.
            # PR #1568 changed ``post_backup`` to write the FQDN form
            # via ``_resolve_canonical_server_name`` but left this
            # top-level ``server_name`` on the short form, so on
            # Splunk Cloud (FQDN ≠ hostname) the dedup lookup would
            # miss the existing row and ``get_backup`` would insert a
            # duplicate on every auto-discovery pass.  Routing this
            # through the same helper closes the gap and aligns the
            # whole function on the FQDN form (the inline FQDN block
            # at lines ~959-966 now produces the same value and is
            # technically redundant — left in place as scoped-out
            # refactor, exactly as the helper's own docstring already
            # noted before this fix).  Bugbot caught this on the sync
            # PR against beta_ai_agent (Medium severity).
            server_name = _resolve_canonical_server_name()

            # check backup dir existence
            if not os.path.isdir(backuproot):
                logger.info(
                    f'TrackMe backup process, there are no backup archives available in directory="{backuproot}", instance="{server_name}"'
                )
                return {
                    "payload": {
                        "response": f'TrackMe backup process, there are no backup archives available in directory="{backuproot}", instance="{server_name}"'
                    },
                    "status": 200,
                }

            else:
                # store files in list (support both .tgz and .tar.zst)
                backup_files = [
                    join(backuproot, f)
                    for f in listdir(backuproot)
                    if isfile(join(backuproot, f))
                    and (f.endswith(".tgz") or f.endswith(".tar.zst"))
                ]

                if not backup_files:
                    logger.info(
                        f'TrackMe backup process, there are no backup archives available in directory="{backuproot}", instance="{server_name}"'
                    )
                    return {
                        "payload": {
                            "response": f'TrackMe backup process, there are no backup archives available in directory="{backuproot}", instance="{server_name}"'
                        },
                        "status": 200,
                    }

                else:
                    # Enter the list, verify for that for each archive file we have a corresponding record in the audit collection
                    # if there is no record, then we create a replacement record
                    for backupfile in backup_files:
                        # get the file mtime
                        try:
                            backup_file_mtime = round(os.path.getmtime(backupfile))
                        except Exception as e:
                            backup_file_mtime = None
                            logger.error(
                                f'failure to retrieve the tmime of the tar file archive="{backupfile}" with exception:"{str(e)}"'
                            )

                        # get the file size
                        try:
                            tar_filesize = os.path.getsize(backupfile)
                        except Exception as e:
                            tar_filesize = None
                            logger.error(
                                f'archive="{backupfile}", failure to retrieve the size of the tar file archive="{str(e)}"'
                            )

                        # Store a record in a backup audit collection

                        # Create a message
                        status_message = "discovered"

                        # record / key
                        record = None
                        key = None

                        # Define the KV query
                        query_string = {
                            "$and": [
                                {
                                    "backup_archive": backupfile,
                                    "server_name": server_name,
                                }
                            ]
                        }

                        # backup audit collection
                        collection_name_backup_archives_info = (
                            "kv_trackme_backup_archives_info"
                        )
                        service_backup_archives_info = client.connect(
                            owner="nobody",
                            app="trackme",
                            port=splunkd_port,
                            token=request_info.session_key,
                            timeout=600,
                        )
                        collection_backup_archives_info = (
                            service_backup_archives_info.kvstore[
                                collection_name_backup_archives_info
                            ]
                        )

                        try:
                            kvrecord = collection_backup_archives_info.data.query(
                                query=json.dumps(query_string)
                            )[0]
                            key = kvrecord.get("_key")

                        except Exception as e:
                            key = None

                        # If a record cannot be found, this backup file is not know to TrackMe currently, add a new record
                        if key is None:
                            # attempt to extract and get the backup details

                            # Attempt extraction
                            backup_file_is_valid = False

                            # From TrackMe 2.1.5, we generate a metadata file named as <tarfile>.full.meta and <tarfile>.light.meta
                            # Check if the metadata file exists
                            backup_file_has_metadata = False

                            # check for both metadata files
                            if os.path.isfile(
                                f"{backupfile}.full.meta"
                            ) and os.path.isfile(f"{backupfile}.light.meta"):
                                backup_file_has_metadata = True

                                try:
                                    with open(
                                        f"{backupfile}.full.meta", "r"
                                    ) as read_content:
                                        full_metadata = json.load(read_content)
                                except Exception as e:
                                    full_metadata = None
                                    backup_file_has_metadata = False
                                    logger.error(
                                        f'failed to load the full metadata file="{backupfile}.full.meta" with exception="{str(e)}"'
                                    )

                                try:
                                    with open(
                                        f"{backupfile}.light.meta", "r"
                                    ) as read_content:
                                        light_metadata = json.load(read_content)
                                except Exception as e:
                                    light_metadata = None
                                    backup_file_has_metadata = False
                                    logger.error(
                                        f'failed to load the light metadata file="{backupfile}.light.meta" with exception="{str(e)}"'
                                    )

                            # Set backup dir
                            backupdir = os.path.join(
                                backuproot, os.path.splitext(backupfile)[0]
                            )

                            try:
                                if extract_archive(backupfile, backupdir):
                                    backup_file_is_valid = True
                                else:
                                    backup_file_is_valid = False
                                    response = {
                                        "response": f'The archive name {backupfile} could not be extracted, restore cannot be processed, this backup file will not be considered, exception="file could not be opened successfully"',
                                    }
                                    logger.error(json.dumps(response, indent=2))
                            except Exception as e:
                                backup_file_is_valid = False
                                response = {
                                    "response": f'The archive name {backupfile} could not be extracted, restore cannot be processed, this backup file will not be considered, exception="{str(e)}"',
                                }
                                logger.error(json.dumps(response, indent=2))

                            # get the local server fqdn
                            hostname = socket.gethostname()
                            fqdn = socket.getfqdn()
                            server_fqdn = (
                                fqdn
                                if fqdn != hostname and not fqdn.endswith('.local')
                                else hostname
                            )

                            #
                            # backup file generated with TrackMe 2.1.5 and later
                            #

                            if backup_file_is_valid and backup_file_has_metadata:

                                logger.info(
                                    f'Discovered backup file="{backupfile}" with metadata compatibility mode.'
                                )

                                if full_metadata and light_metadata:

                                    # 3.0.0 field propagation (Issue #1555)
                                    #
                                    # `post_backup` writes the 3.0.0 fields
                                    # into the .full.meta sidecar (see lines
                                    # ~1665-1680). Earlier versions of this
                                    # auto-discovery block hardcoded a
                                    # V2-only insert set and dropped those
                                    # fields on the floor — every 3.0.0
                                    # archive copied or imported onto this
                                    # instance landed in
                                    # ``kv_trackme_backup_archives_info``
                                    # without ``backup_run_id`` /
                                    # ``archive_scope`` /
                                    # ``archive_schema_version``, so
                                    # ``group_archives_by_run`` routed them
                                    # to the legacy bucket. The UI then
                                    # badged them ``LEGACY`` and exposed
                                    # only the flat restore path.
                                    #
                                    # Defense in depth: prefer the
                                    # sidecar's own 3.0.0 fields when
                                    # present; otherwise fall back to
                                    # parsing the filename grammar
                                    # (`parse_archive_filename` already
                                    # recognises both 3.0.0 and legacy
                                    # filenames). When neither source
                                    # identifies a 3.0.0 archive, the
                                    # fields stay empty and the row falls
                                    # into the legacy bucket as intended
                                    # (correct behaviour for genuine
                                    # pre-2.3.22 archives).
                                    v3_fields = _derive_v3_fields_for_discovery(
                                        os.path.basename(backupfile),
                                        full_metadata,
                                    )

                                    insert_record = {
                                        "mtime": full_metadata.get("mtime"),
                                        "htime": full_metadata.get("htime"),
                                        "server_name": server_fqdn,
                                        "status": json.dumps(
                                            light_metadata, indent=4
                                        ),
                                        "change_type": "backup archive was missing from the info collection and added by automatic discovery (metadata compatibility mode)",
                                        "backup_archive": full_metadata.get(
                                            "backup_archive"
                                        ),
                                        "size": full_metadata.get("size"),
                                        "archive_details": json.dumps(
                                            full_metadata.get(
                                                "archive_details"
                                            ),
                                            indent=4,
                                        ),
                                    }
                                    # Merge 3.0.0 fields (only when the
                                    # helper actually identified a 3.0.0
                                    # archive; otherwise v3_fields is
                                    # empty and the merge is a no-op).
                                    insert_record.update(v3_fields)

                                    try:
                                        # Insert the record
                                        collection_backup_archives_info.data.insert(
                                            json.dumps(insert_record)
                                        )

                                    except Exception as e:
                                        logger.error(
                                            f'failed to insert a new KVstore record with exception="{str(e)}"'
                                        )
                                        return {
                                            "payload": {
                                                "response": f'failed to insert a new KVstore record with exception="{str(e)}"'
                                            },
                                            "status": 500,
                                        }

                            #
                            # backup file generated prior to TrackMe 2.1.5
                            #

                            elif backup_file_is_valid:

                                logger.info(
                                    f'Discovered backup file="{backupfile}" with legacy compatibility mode.'
                                )

                                # store the list of json files in a list
                                collections_json_files = [
                                    f
                                    for f in listdir(backupdir)
                                    if isfile(join(backupdir, f))
                                ]

                                # store the list of available collections in the archive
                                collections_available = []

                                # create a dictionary
                                collections_restore_dict = {}
                                for json_file in collections_json_files:
                                    # strip the extension
                                    collection_name = os.path.splitext(json_file)[0]

                                    # append to the list of available collections for restore
                                    collections_available.append(collection_name)

                                    # get the file size
                                    json_file_size = os.path.getsize(
                                        os.path.join(backupdir, json_file)
                                    )

                                    # get the file mtime
                                    json_file_mtime = round(
                                        os.path.getmtime(
                                            os.path.join(backupdir, json_file)
                                        )
                                    )

                                    # try getting the number of records
                                    try:
                                        with open(
                                            os.path.join(backupdir, json_file), "r"
                                        ) as read_content:
                                            json_file_records = len(
                                                json.load(read_content)
                                            )
                                    except Exception as e:
                                        json_file_records = None

                                    # add to the dict
                                    collections_restore_dict[collection_name] = {
                                        "file": json_file,
                                        "size": json_file_size,
                                        "mtime": json_file_mtime,
                                        "records": json_file_records,
                                    }

                                # remove backup dir
                                try:
                                    shutil.rmtree(backupdir)
                                except OSError as e:
                                    logger.error(
                                        f'failed to purge the extraction temporary directory="{backupdir}" with exception="{str(e)}"'
                                    )

                                try:
                                    # Insert the record
                                    collection_backup_archives_info.data.insert(
                                        json.dumps(
                                            {
                                                "mtime": str(backup_file_mtime),
                                                "htime": str(
                                                    time.strftime(
                                                        "%c",
                                                        time.localtime(
                                                            backup_file_mtime
                                                        ),
                                                    )
                                                ),
                                                "server_name": server_fqdn,
                                                "status": str(status_message),
                                                "change_type": "backup archive was missing from the info collection and added by automatic discovery (legacy archive compatibility mode)",
                                                "backup_archive": str(backupfile),
                                                "size": str(tar_filesize),
                                                "archive_details": json.dumps(
                                                    collections_restore_dict,
                                                    indent=4,
                                                ),
                                                # summary map of collection -> size (bytes) for quick access/search
                                                "kvstore_collections_size": json.dumps(
                                                    {
                                                        k: v.get("size", 0)
                                                        for k, v in collections_restore_dict.items()
                                                    },
                                                    indent=2,
                                                ),
                                            }
                                        )
                                    )

                                except Exception as e:
                                    logger.error(
                                        f'failed to insert a new KVstore record with exception="{str(e)}"'
                                    )
                                    return {
                                        "payload": {
                                            "response": f'failed to insert a new KVstore record with exception="{str(e)}"'
                                        },
                                        "status": 500,
                                    }

                    # Render

                    records = collection_backup_archives_info.data.query()
                    currently_known_archives = []
                    for record in records:
                        currently_known_archives.append(record.get("backup_archive"))

                    logger.info(
                        f'TrackMe get backup files finished successfully, archive_fields="{currently_known_archives}"'
                    )

                    (
                        collection_records,
                        collection_records_dict,
                        collection_records_keys,
                    ) = get_full_collection_records(collection_backup_archives_info)

                    if mode == "full":
                        return {
                            "payload": collection_records,
                            "status": 200,
                        }

                    elif mode == "summary":

                        backup_count = len(collection_records)
                        backup_files = []

                        for record in collection_records:
                            backup_files.append(record.get("backup_archive"))

                        return {
                            "payload": {
                                "backup_count": backup_count,
                                "backup_files": backup_files,
                            },
                            "status": 200,
                        }

    # ------------------------------------------------------------------
    # post_backup in-flight lock helpers (Issue #1557, PR #1558)
    # ------------------------------------------------------------------
    #
    # Per-peer mutex around ``post_backup`` to prevent concurrent backup
    # runs on the same SHC peer. The pre-existing
    # ``cleanup_backup_directories`` helper at the start of post_backup
    # wipes any sibling ``trackme-backup-*`` working directory — fatal
    # for any in-flight neighbour, which is why an earlier production
    # incident left thousands of mid-tar I/O errors after concurrent
    # tracker-triggered backups raced each other.
    #
    # This pair of helpers is what enforces the mutex. They are paired
    # in a try/finally in the post_backup wrapper so the lock is always
    # released when the function returns (success OR failure), and a
    # staleness rescue covers the rare case where the wrapper's finally
    # block is bypassed (process recycle, OOM kill, uncaught exception
    # in a path the wrapper can't observe).
    #
    # The schema-upgrade tracker has its own coordination lock
    # (``kv_trackme_schema_upgrade_backup_lock``) which gates the
    # decision "do I, as one of N trackers, fire a backup at all?".
    # This in-flight lock is one layer down: "given that someone wants
    # to call post_backup right now, is another post_backup already
    # running on this peer?". The two locks together close every
    # concurrency hole regardless of caller (scheduled cron,
    # schema-upgrade tracker, manual UI click, AI tool, automation
    # SPL).

    # Backups on a healthy fleet complete within ~30 min in
    # practice; SHC-replicated KV writes plus large-fleet KO
    # restore pushes the long-tail to ~2 h on the worst observed
    # case. We pick 4 h as the in-flight-lock staleness threshold
    # — twice the worst case — so a legitimate slow backup never
    # gets its lock yanked from under it, while an orphaned lock
    # (process died without releasing) blocks subsequent backups
    # for at most one cycle.
    _BACKUP_IN_FLIGHT_STALE_THRESHOLD_SECONDS = 14400

    def _backup_in_flight_lock_url(self, request_info, key=""):
        """Return the KV row URL for the in-flight lock, optionally
        scoped to a specific _key for GET / DELETE.
        """
        base = (
            f"{request_info.server_rest_uri}"
            f"/servicesNS/nobody/trackme/storage/collections/data/"
            f"kv_trackme_backup_in_flight_lock"
        )
        if key:
            return f"{base}/{key}"
        return base

    def _acquire_backup_in_flight_lock(
        self, request_info, server_name, caller_context="",
    ):
        """Try to claim the per-peer in-flight backup lock.

        Returns ``(acquired: bool, conflict_response_or_None: dict|None)``.

        * ``acquired=True, None`` — caller owns the lock and may proceed.
          MUST call ``_release_backup_in_flight_lock`` before returning.
        * ``acquired=False, conflict_response`` — another backup is in
          flight on this peer (and the existing lock is fresh enough to
          trust). The caller should return ``conflict_response`` to the
          REST client unchanged; it's already shaped as
          ``{"payload": ..., "status": 409}``.

        Staleness rescue: if the existing lock's ``mtime`` is older than
        ``_BACKUP_IN_FLIGHT_STALE_THRESHOLD_SECONDS``, the prior holder
        crashed without releasing. DELETE the stale row and re-INSERT
        with our own key. KV's primary-key uniqueness still serializes
        simultaneous rescuers (only ONE can win the post-DELETE INSERT;
        rest see another 409 and back off).

        Fail-open: if KV itself is unreachable / returns unexpected HTTP
        codes, the caller is allowed to proceed (we log a warning).
        Better to risk re-storming than to silently block every backup
        because of a KV blip.
        """
        lock_key = f"backup_in_flight_{server_name}"
        url = self._backup_in_flight_lock_url(request_info, key="")
        now_epoch = int(round(time.time()))
        try:
            user = getattr(request_info, "user", "") or ""
        except Exception:
            user = ""
        lock_record = {
            "_key": lock_key,
            "mtime": now_epoch,
            "htime": time.strftime("%c", time.localtime(now_epoch)),
            "server_name": server_name,
            "acquired_by_user": str(user),
            "caller_context": str(caller_context or ""),
            # run_id is empty at acquisition — only known after
            # _bbk_make_run_id() runs inside the body.
            "run_id": "",
        }
        headers = {
            "Authorization": f"Splunk {request_info.session_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(lock_record),
                verify=False,
                timeout=30,
            )
        except Exception as e:
            logger.warning(
                f"post_backup in-flight lock: INSERT raised "
                f"exception='{str(e)}'; proceeding without lock "
                f"(fail-open)."
            )
            return (True, None)

        if response.status_code in (200, 201):
            logger.info(
                f"post_backup in-flight lock: acquired key='{lock_key}', "
                f"caller_context='{caller_context}'"
            )
            return (True, None)

        if response.status_code != 409:
            logger.warning(
                f"post_backup in-flight lock: INSERT returned unexpected "
                f"http_status={response.status_code}, "
                f"body={response.text[:300]!r}; proceeding without lock "
                f"(fail-open)."
            )
            return (True, None)

        # 409 — existing lock. Inspect mtime to decide whether to rescue.
        existing_mtime = 0
        existing_caller = ""
        try:
            existing_response = requests.get(
                self._backup_in_flight_lock_url(request_info, key=lock_key),
                headers={"Authorization": f"Splunk {request_info.session_key}"},
                verify=False,
                timeout=30,
            )
            if existing_response.status_code == 200:
                existing_row = existing_response.json()
                if isinstance(existing_row, dict):
                    try:
                        existing_mtime = int(
                            float(existing_row.get("mtime") or 0)
                        )
                    except (TypeError, ValueError):
                        existing_mtime = 0
                    existing_caller = existing_row.get("caller_context", "")
        except Exception as e:
            logger.warning(
                f"post_backup in-flight lock: GET on existing row "
                f"raised exception='{str(e)}'; treating as fresh, "
                f"returning 409 to caller."
            )

        lock_age_seconds = now_epoch - existing_mtime if existing_mtime > 0 else -1
        is_stale = (
            existing_mtime > 0
            and lock_age_seconds > self._BACKUP_IN_FLIGHT_STALE_THRESHOLD_SECONDS
        )

        if not is_stale:
            err = (
                f"Another backup is currently in flight on this peer "
                f"(server_name='{server_name}', age={lock_age_seconds}s, "
                f"prior_caller_context='{existing_caller}'). "
                f"Backups are serialised per peer to avoid working-"
                f"directory cannibalisation; the in-flight backup must "
                f"finish (or the lock must time out at "
                f"{self._BACKUP_IN_FLIGHT_STALE_THRESHOLD_SECONDS}s) "
                f"before another can start. Retry shortly."
            )
            logger.warning(
                f"post_backup in-flight lock: refused new acquisition, "
                f"key='{lock_key}', age={lock_age_seconds}s, "
                f"caller_context='{caller_context}'"
            )
            return (False, {
                "payload": {"response": err, "backup_in_flight": True},
                "status": 409,
            })

        # Stale — rescue.
        logger.warning(
            f"post_backup in-flight lock: STALE lock detected "
            f"(age={lock_age_seconds}s > threshold="
            f"{self._BACKUP_IN_FLIGHT_STALE_THRESHOLD_SECONDS}s, "
            f"prior_caller_context='{existing_caller}'); attempting rescue."
        )
        try:
            requests.delete(
                self._backup_in_flight_lock_url(request_info, key=lock_key),
                headers={"Authorization": f"Splunk {request_info.session_key}"},
                verify=False,
                timeout=30,
            )
            # Refresh mtime so the rescue starts a fresh clock.
            lock_record["mtime"] = int(round(time.time()))
            lock_record["htime"] = time.strftime(
                "%c", time.localtime(lock_record["mtime"]),
            )
            rescue_response = requests.post(
                url,
                headers=headers,
                data=json.dumps(lock_record),
                verify=False,
                timeout=30,
            )
            if rescue_response.status_code in (200, 201):
                logger.info(
                    f"post_backup in-flight lock: RESCUED stale lock, "
                    f"key='{lock_key}', caller_context='{caller_context}'"
                )
                return (True, None)
            if rescue_response.status_code == 409:
                # Another caller rescued first — back off.
                logger.info(
                    f"post_backup in-flight lock: another caller rescued "
                    f"the stale lock first, key='{lock_key}'; returning "
                    f"409 to caller."
                )
                return (False, {
                    "payload": {
                        "response": (
                            "Another backup just took over the stale "
                            "lock on this peer. Retry shortly."
                        ),
                        "backup_in_flight": True,
                    },
                    "status": 409,
                })
            logger.warning(
                f"post_backup in-flight lock: rescue INSERT returned "
                f"unexpected http_status={rescue_response.status_code}, "
                f"body={rescue_response.text[:300]!r}; proceeding "
                f"without lock (fail-open)."
            )
            return (True, None)
        except Exception as e:
            logger.warning(
                f"post_backup in-flight lock: rescue raised "
                f"exception='{str(e)}'; proceeding without lock "
                f"(fail-open)."
            )
            return (True, None)

    def _release_backup_in_flight_lock(self, request_info, server_name):
        """Release the per-peer in-flight backup lock. Idempotent —
        safe to call even if acquisition was via the fail-open path
        (DELETE-404 is silently fine).
        """
        lock_key = f"backup_in_flight_{server_name}"
        try:
            requests.delete(
                self._backup_in_flight_lock_url(
                    request_info, key=lock_key,
                ),
                headers={
                    "Authorization": f"Splunk {request_info.session_key}",
                },
                verify=False,
                timeout=30,
            )
            logger.info(
                f"post_backup in-flight lock: released key='{lock_key}'"
            )
        except Exception as e:
            logger.warning(
                f"post_backup in-flight lock: release raised "
                f"exception='{str(e)}' for key='{lock_key}'; the "
                f"staleness rescue (>"
                f"{self._BACKUP_IN_FLIGHT_STALE_THRESHOLD_SECONDS}s) "
                f"will eventually allow new acquisitions."
            )

    # Take a backup
    def post_backup(self, request_info, **kwargs):
        """REST entry for backup. Acquires the per-peer in-flight lock,
        delegates to ``_post_backup_body``, and guarantees release in
        try/finally — see Issue #1557 / PR #1558 for the design.
        """
        # ------------------------------------------------------------------
        # Fast-path describe queries: no work, no lock.
        # ------------------------------------------------------------------
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None
        if isinstance(resp_dict, dict):
            describe_flag = str(resp_dict.get("describe", "")).lower() == "true"
            if describe_flag:
                return self._post_backup_body(request_info, **kwargs)
            # Forensic field — record what the caller declared themselves
            # to be (free-form). Trusted operationally; we don't gate on
            # this value.
            caller_context = str(resp_dict.get("caller_context") or "")
        else:
            caller_context = ""

        # ------------------------------------------------------------------
        # Acquire the per-peer in-flight lock for the real work path.
        # Use the same canonical server-name convention as the archive-row
        # write paths so the lock's ``server_name`` field matches what
        # operators see in the UI listing and what any future cross-path
        # inspection would query for.
        # ------------------------------------------------------------------
        local_server = _resolve_canonical_server_name()
        acquired, conflict_response = self._acquire_backup_in_flight_lock(
            request_info, local_server, caller_context=caller_context,
        )
        if not acquired:
            return conflict_response

        try:
            return self._post_backup_body(request_info, **kwargs)
        finally:
            self._release_backup_in_flight_lock(request_info, local_server)

    def _post_backup_body(self, request_info, **kwargs):
        """Create a multi-archive backup run (schema 3.0.0).

        Produces N+1 archives per call:
          * one ``trackme-backup-<RUN_ID>-tenant-<tid>.tar.zst`` per enabled tenant
          * exactly one ``trackme-backup-<RUN_ID>-global.tar.zst`` (unless
            ``include_global=false``)

        Each archive is independently restorable. A per-archive failure
        does NOT short-circuit the run — the other archives are still
        produced. This is the central correctness change vs. the
        pre-2.3.22 monolithic format, which aborted the whole backup on
        a single failure and left customers without per-tenant recovery
        granularity.

        Legacy 1.0.0/2.0.0 archives produced before 2.3.22 remain
        restorable via post_restore but are no longer produced.
        """

        describe = False
        comment = f"Backup initiated by {request_info.user}, date: {time.strftime('%c')}"

        # ----------------------------------------------------------------
        # 1. parse body params
        # ----------------------------------------------------------------
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        tenants_scope = "all"  # default: every enabled tenant
        include_global = True  # default: include the global archive
        blocklist = []

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            try:
                comment = resp_dict.get("comment")
                if not comment:
                    comment = None
            except Exception:
                comment = None
            if not comment:
                comment = f"Backup initiated by {request_info.user}, date: {time.strftime('%c')}"

            try:
                blocklist = resp_dict.get("blocklist", [])
                if isinstance(blocklist, str):
                    blocklist = [x.strip() for x in blocklist.split(",") if x.strip()]
                elif not isinstance(blocklist, list):
                    blocklist = []
            except Exception:
                blocklist = []

            try:
                ts = resp_dict.get("tenants_scope", "all")
                if isinstance(ts, str):
                    ts = ts.strip()
                    if ts.lower() == "all" or not ts:
                        tenants_scope = "all"
                    else:
                        tenants_scope = [x.strip() for x in ts.split(",") if x.strip()]
                elif isinstance(ts, list):
                    tenants_scope = [str(x).strip() for x in ts if str(x).strip()]
                else:
                    tenants_scope = "all"
            except Exception:
                tenants_scope = "all"

            try:
                include_global = str(resp_dict.get("include_global", True)).lower() not in (
                    "false", "0", "no",
                )
            except Exception:
                include_global = True
        else:
            describe = False

        if describe:
            response = {
                "describe": (
                    "Create a multi-archive backup run (schema 3.0.0). One archive "
                    "per enabled virtual tenant plus one global archive are produced "
                    "under $SPLUNK_HOME/etc/apps/trackme/backup. A per-archive failure "
                    "does not short-circuit the run — the other archives are still "
                    "produced. Legacy 1.0.0/2.0.0 archives produced before 2.3.22 "
                    "remain restorable via post_restore but are no longer produced."
                ),
                "resource_desc": "Start a TrackMe multi-archive backup run",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/backup_and_restore/backup"',
                "options": [
                    {
                        "comment": "OPTIONAL: comment to be added to every archive in the run.",
                        "blocklist": "OPTIONAL: comma-separated list (or array) of KVstore collection names to exclude from backup. Applied across all archives in the run.",
                        "tenants_scope": "OPTIONAL: 'all' (default) or comma-separated list (or array) of tenant_ids. Tenant archives are produced only for the listed tenants. Disabled tenants are always skipped regardless.",
                        "include_global": "OPTIONAL: 'true' (default) to produce the global archive. Set to 'false' for tenant-only runs.",
                    },
                ],
            }
            return {"payload": response, "status": 200}

        # ----------------------------------------------------------------
        # 2. connect
        # ----------------------------------------------------------------
        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )
        header = {
            "Authorization": f"Splunk {request_info.session_key}",
            "Content-Type": "application/json",
        }

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackme_version = trackme_conf.get("trackme_version", "unknown")

        # ----------------------------------------------------------------
        # 3. resolve filesystem layout + run identity
        # ----------------------------------------------------------------
        backuproot = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
        if not os.path.isdir(backuproot):
            os.mkdir(backuproot)

        run_id = _bbk_make_run_id()

        # Sweep stale per-archive workdirs from previous failed runs. Each
        # archive's workdir is a direct child of backuproot using the same
        # ``trackme-backup-`` prefix as the legacy code, so the existing
        # cleanup helper picks them up. Note: archives produced by the
        # CURRENT run are written inside this same parent — but they're
        # `.tar.zst` / `.tgz` files, not directories, so the helper (which
        # only matches `os.path.isdir`) leaves them alone.
        cleanup_backup_directories(backuproot, exclude_dir=None)

        # Use the FQDN-preferring convention shared with get_backup
        # auto-discovery and post_import_backup so all three write paths
        # produce identical ``server_name`` values for the same SHC peer.
        # Operators previously saw mixed short-hostname / FQDN forms in
        # the UI listing because ``post_backup`` was the odd one out
        # (plain ``socket.gethostname()``) until 2.3.23.
        server_name = _resolve_canonical_server_name()
        started_epoch = int(round(time.time()))

        logger.info(
            f'TrackMe multi-archive backup run starting, run_id="{run_id}", '
            f'server_name="{server_name}", backuproot="{backuproot}", '
            f'tenants_scope="{tenants_scope}", include_global={include_global}'
        )

        # ----------------------------------------------------------------
        # 4. enumerate enabled tenants (filtered by tenants_scope if given)
        # ----------------------------------------------------------------
        vtenants_collection = service.kvstore["kv_trackme_virtual_tenants"]
        vtenants_records, _, _ = get_full_kv_collection(
            vtenants_collection, "kv_trackme_virtual_tenants"
        )
        enabled_tenant_ids = [
            r.get("tenant_id")
            for r in vtenants_records
            if r.get("tenant_status") == "enabled" and r.get("tenant_id")
        ]
        if isinstance(tenants_scope, list):
            scoped = set(tenants_scope)
            enabled_tenant_ids = [t for t in enabled_tenant_ids if t in scoped]

        # ----------------------------------------------------------------
        # 5. enumerate KV collections + partition into per-bucket sets
        # ----------------------------------------------------------------
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        searchquery = '| rest splunk_server=local "/servicesNS/nobody/trackme/storage/collections/config" | where \'eai:acl.app\'="trackme" AND disabled=0 | table title | stats values(title) as collections | tojson | fields _raw'

        collections_list = []
        try:
            reader = run_splunk_search(service, searchquery, kwargs_search, 24, 5)
            for item in reader:
                if isinstance(item, dict):
                    collections_list = json.loads(item.get("_raw")).get(
                        "collections", []
                    ) or []
                    break
        except Exception as e:
            logger.error(
                f'failed to enumerate KV collections, run_id="{run_id}", exception="{str(e)}"'
            )

        if not collections_list:
            # No per-run wrapper directory exists in the current design, so
            # nothing to clean up here. Per-archive workdirs (which would be
            # created later by _build_one_archive) haven't been created yet
            # at this point in the flow.
            err = (
                "TrackMe backup run failed: could not enumerate KV collections."
            )
            logger.error(err)
            return {
                "payload": {
                    "response": err,
                    "backup_run_id": run_id,
                },
                "status": 500,
            }

        # Apply user-supplied blocklist before partitioning so excluded names
        # never reach any bucket. The stateful-charts blocklist is enforced
        # by partition_collections() itself (kept identical to the legacy
        # behaviour to preserve restore compatibility).
        if blocklist:
            collections_list = [c for c in collections_list if c not in blocklist]

        partition = _bbk_partition_collections(collections_list, enabled_tenant_ids)

        logger.info(
            f'partitioned KV collections, run_id="{run_id}", '
            f'global={len(partition["global"])}, '
            f'tenants={ {t: len(v) for t, v in partition["tenant"].items()} }, '
            f'orphan_tenants={list(partition["orphan_tenant"].keys())}, '
            f'excluded={len(partition["excluded"])}'
        )

        # ----------------------------------------------------------------
        # 6. inner helpers (closure over service / header / request_info)
        # ----------------------------------------------------------------

        def _dump_collection(target_dir, collection_name, archive_details):
            """Returns (was_empty: bool, error_or_None)."""
            try:
                collection = service.kvstore[collection_name]
                records, _, _ = get_full_kv_collection(collection, collection_name)
                target = os.path.join(target_dir, f"{collection_name}.json")
                with open(target, "w") as f:
                    f.write(json.dumps(records, indent=1))
                archive_details[collection_name] = {
                    "file": f"{collection_name}.json",
                    "size": os.path.getsize(target),
                    "mtime": round(os.path.getmtime(target)),
                    "records": len(records),
                }
                return (len(records) == 0, None)
            except Exception as e:
                return (False, f'collection="{collection_name}" failure: {str(e)}')

        def _dump_tenant_account(target_dir, tenant_id, archive_details):
            """Returns error_or_None."""
            url = (
                f"{request_info.server_rest_uri}"
                "/services/trackme/v2/configuration/admin/get_vtenant_account"
            )
            try:
                response = requests.post(
                    url,
                    headers=header,
                    data=json.dumps({"tenant_id": tenant_id}),
                    verify=False,
                    timeout=600,
                )
                response.raise_for_status()
                virtual_tenant_account = response.json().get("vtenant_account")
                target = os.path.join(
                    target_dir, f"tenant_{tenant_id}_vtenant_account.json"
                )
                with open(target, "w") as f:
                    f.write(json.dumps(virtual_tenant_account, indent=1))
                archive_details[f"tenant_{tenant_id}_vtenant_account"] = {
                    "file": f"tenant_{tenant_id}_vtenant_account.json",
                    "size": os.path.getsize(target),
                    "mtime": round(os.path.getmtime(target)),
                }
                return None
            except Exception as e:
                return f'tenant_account fetch failure tenant_id="{tenant_id}": {str(e)}'

        def _dump_tenant_kos(target_dir, tenant_id, archive_details):
            """Returns (counts_dict, error_or_None)."""
            counts = {
                "total": 0, "kvstore_collections": 0, "transforms": 0,
                "reports": 0, "alerts": 0, "macros": 0,
            }
            url = (
                f"{request_info.server_rest_uri}"
                "/services/trackme/v2/configuration/get_tenant_knowledge_objects"
            )
            try:
                response = requests.post(
                    url,
                    headers=header,
                    data=json.dumps({"tenant_id": tenant_id}),
                    verify=False,
                    timeout=600,
                )
                response.raise_for_status()
                response_json = response.json()
            except Exception as e:
                return (counts, f'KO fetch failure tenant_id="{tenant_id}": {str(e)}')

            trackme_knowledge_objects = {}
            for item in response_json:
                type_ = item.get("type")
                title = item.get("title")
                object_dict = {
                    "type": type_,
                    "title": title,
                    "properties": item.get("properties", {}),
                }
                counts["total"] += 1
                if type_ == "savedsearches":
                    counts["reports"] += 1
                    object_dict["definition"] = item.get("definition")
                elif type_ == "alerts":
                    counts["alerts"] += 1
                    object_dict["definition"] = item.get("definition")
                    object_dict["alert_properties"] = item.get("alert_properties")
                elif type_ == "macros":
                    counts["macros"] += 1
                    object_dict["definition"] = item.get("definition")
                elif type_ == "lookup_definitions":
                    counts["transforms"] += 1
                    object_dict["collection"] = item.get("collection")
                    object_dict["fields_list"] = item.get("fields_list")
                elif type_ == "kvstore_collections":
                    counts["kvstore_collections"] += 1
                trackme_knowledge_objects[title] = object_dict

            target = os.path.join(target_dir, f"tenant_{tenant_id}_knowledge_objects.json")
            try:
                with open(target, "w") as f:
                    f.write(json.dumps(trackme_knowledge_objects, indent=1))
            except Exception as e:
                return (counts, f'KO write failure tenant_id="{tenant_id}": {str(e)}')

            archive_details[f"tenant_{tenant_id}_knowledge_objects"] = {
                "file": f"tenant_{tenant_id}_knowledge_objects.json",
                "size": os.path.getsize(target),
                "mtime": round(os.path.getmtime(target)),
                "count_knowledge_objects": counts["total"],
                "count_kvstore_collections": counts["kvstore_collections"],
                "count_transforms": counts["transforms"],
                "count_reports": counts["reports"],
                "count_alerts": counts["alerts"],
                "count_macros": counts["macros"],
            }
            return (counts, None)

        def _build_one_archive(scope, tenant_id, collection_names):
            """Build a single tenant or global archive.

            NEVER raises — captures any failure into the returned summary's
            ``status``/``errors`` fields so the run loop continues with the
            other buckets. This is the central correctness contract: a
            tenant's data may be corrupted, but its sibling tenants' archives
            still get built. The whole body runs under a top-level
            ``try``/``except`` so an unexpected exception (e.g. from
            archive_filename validation, os.makedirs, or any future code
            change) is still captured into a ``status="failed"`` summary
            rather than propagating up and aborting the rest of the run.
            """
            try:
                ext = "tar.zst" if is_zstd_available() else "tgz"
                archive_basename = _bbk_archive_filename(
                    run_id, scope, tenant_id=tenant_id, ext=ext,
                )
                if archive_basename.endswith(".tar.zst"):
                    stem = archive_basename[: -len(".tar.zst")]
                elif archive_basename.endswith(".tgz"):
                    stem = archive_basename[: -len(".tgz")]
                else:
                    stem = archive_basename

                # archive_workdir is a direct child of backuproot. It MUST be
                # — create_compressed_archive uses os.path.dirname(source_dir)
                # as the output directory, so the resulting archive file
                # lands alongside it in backuproot. (An earlier draft of this
                # rewrite nested workdirs under a per-run wrapper directory
                # which then got removed at end-of-run, taking the freshly
                # created archives with it. See PR #1460 bugbot finding.)
                archive_workdir = os.path.join(backuproot, stem)
                os.makedirs(archive_workdir, exist_ok=True)

                archive_details = {"trackme_version": trackme_version}
                bucket_failures = []
                kos_counts = {}
                empty_count = 0
                non_empty_count = 0
                # Track each tenant-meta dump independently so the manifest
                # can record exactly which payload files were written. The
                # has-payload guard below is OR of the two; the manifest's
                # vtenant_account_file field only references the file when
                # the corresponding dump actually succeeded (otherwise the
                # restore path would try to open a file that was never
                # created).
                tenant_account_ok = False
                tenant_kos_ok = False

                # Tenant-only payload: vtenant_account + KOs
                if scope == ARCHIVE_SCOPE_TENANT:
                    err = _dump_tenant_account(archive_workdir, tenant_id, archive_details)
                    if err:
                        bucket_failures.append(err)
                        logger.error(f'run_id="{run_id}" tenant_id="{tenant_id}" {err}')
                    else:
                        tenant_account_ok = True
                    kos_counts, err = _dump_tenant_kos(
                        archive_workdir, tenant_id, archive_details
                    )
                    if err:
                        bucket_failures.append(err)
                        logger.error(f'run_id="{run_id}" tenant_id="{tenant_id}" {err}')
                    else:
                        tenant_kos_ok = True

                # KV collections (bucket-specific subset)
                for cname in collection_names:
                    was_empty, err = _dump_collection(archive_workdir, cname, archive_details)
                    if err:
                        bucket_failures.append(err)
                        logger.error(f'run_id="{run_id}" {err}')
                    elif was_empty:
                        empty_count += 1
                    else:
                        non_empty_count += 1

                # Refuse to produce an archive that has no usable payload —
                # such an archive would register a KV row pointing at an
                # almost-empty .tar.zst (just manifest.json), confusing the
                # operator at restore time. "No payload" means: every KV
                # collection failed AND, for tenant scope, neither the
                # vtenant_account nor the KO list was successfully captured.
                # An archive with zero collections but a successful
                # vtenant_account dump is still useful (it recreates the
                # tenant record on a fresh deployment), so a successful
                # vtenant_account or KOs dump alone is enough payload to
                # keep going.
                has_kv_payload = (non_empty_count + empty_count) > 0
                has_payload = (
                    has_kv_payload or
                    (scope == ARCHIVE_SCOPE_TENANT and (tenant_account_ok or tenant_kos_ok))
                )
                if not has_payload and bucket_failures:
                    shutil.rmtree(archive_workdir, ignore_errors=True)
                    return {
                        "scope": scope,
                        "tenant_id": tenant_id or "",
                        "run_id": run_id,
                        "status": "failed",
                        "errors": bucket_failures,
                    }

                # In-archive manifest — the source-of-truth signal that
                # drives post_restore's 3.0.0 dispatch.
                in_manifest = {
                    "run_id": run_id,
                    "archive_scope": scope,
                    "tenant_id": tenant_id or "",
                    "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
                    "trackme_version": trackme_version,
                    "server_name": server_name,
                    "comment": comment,
                    "started_epoch": started_epoch,
                    "collections": [
                        {
                            "name": k,
                            "file": v.get("file"),
                            "size": v.get("size"),
                            "records": v.get("records"),
                        }
                        for k, v in archive_details.items()
                        if k.startswith("kv_")
                    ],
                    "knowledge_objects": (
                        kos_counts if scope == ARCHIVE_SCOPE_TENANT else {}
                    ),
                    # Reference the vtenant_account file ONLY if the dump
                    # actually succeeded — otherwise the restore path
                    # (PR 3) would try to open a file that was never
                    # written into the archive. None signals to the
                    # restore code that this archive lacks a tenant
                    # account record.
                    "vtenant_account_file": (
                        f"tenant_{tenant_id}_vtenant_account.json"
                        if scope == ARCHIVE_SCOPE_TENANT and tenant_account_ok
                        else None
                    ),
                    # Same shape contract for the KOs file: only reference
                    # it when the dump succeeded.
                    "knowledge_objects_file": (
                        f"tenant_{tenant_id}_knowledge_objects.json"
                        if scope == ARCHIVE_SCOPE_TENANT and tenant_kos_ok
                        else None
                    ),
                    # Snapshot of bucket_failures at archive-seal time. This
                    # is what gets baked into the .tar.zst — subsequent
                    # appends to bucket_failures (sidecar write, KV insert)
                    # do NOT mutate this list. The .full.meta sidecar and
                    # KV row carry their own snapshots taken later, so all
                    # three artifacts stay consistent with each other but
                    # may differ in failure-list contents depending on what
                    # was known at the moment they were serialized.
                    "failures": list(bucket_failures),
                }
                try:
                    _bbk_write_in_archive_manifest(archive_workdir, in_manifest)
                except Exception as e:
                    # The in-archive manifest is the source-of-truth signal
                    # that drives post_restore's 3.0.0 dispatch — without it
                    # the archive is fundamentally unrestorable through the
                    # intended 3.0.0 path. Fail-fast (same posture as a
                    # compression failure below) rather than registering a
                    # KV row pointing at a useless archive.
                    bucket_failures.append(f"manifest write failure: {str(e)}")
                    logger.error(
                        f'run_id="{run_id}" scope="{scope}" tenant_id="{tenant_id or ""}" '
                        f'manifest write failure — refusing to compress: {str(e)}'
                    )
                    shutil.rmtree(archive_workdir, ignore_errors=True)
                    return {
                        "scope": scope,
                        "tenant_id": tenant_id or "",
                        "run_id": run_id,
                        "status": "failed",
                        "errors": bucket_failures,
                    }

                # Compress
                try:
                    archive_path = create_compressed_archive(archive_workdir, stem)
                except Exception as e:
                    bucket_failures.append(f"compression failure: {str(e)}")
                    shutil.rmtree(archive_workdir, ignore_errors=True)
                    return {
                        "scope": scope,
                        "tenant_id": tenant_id or "",
                        "run_id": run_id,
                        "status": "failed",
                        "errors": bucket_failures,
                    }

                # Integrity probe — catches the zstd-93 corruption class
                # that surfaced in production with the legacy monolithic
                # archive and made restore impossible. For .tgz we skip;
                # gzip's CRC validates implicitly during extraction.
                # Fail-fast on integrity failure: registering a KV row that
                # points at a corrupted archive defeats the entire purpose
                # of this probe. Same posture as compression / manifest
                # failures above. We also remove the corrupted file from
                # disk so a later operator inspection doesn't mistake it
                # for a recoverable backup.
                integrity_failed = False
                if archive_path.endswith(".tar.zst"):
                    try:
                        if zstd_test_archive(archive_path) != 0:
                            bucket_failures.append(
                                f"archive integrity test failed (zstd -t non-zero): {archive_path}"
                            )
                            integrity_failed = True
                    except Exception as e:
                        bucket_failures.append(
                            f"archive integrity test exception: {str(e)}"
                        )
                        integrity_failed = True
                if integrity_failed:
                    logger.error(
                        f'run_id="{run_id}" scope="{scope}" tenant_id="{tenant_id or ""}" '
                        f'archive integrity test failed — discarding corrupted file: {archive_path}'
                    )
                    try:
                        os.remove(archive_path)
                    except OSError:
                        pass
                    shutil.rmtree(archive_workdir, ignore_errors=True)
                    return {
                        "scope": scope,
                        "tenant_id": tenant_id or "",
                        "run_id": run_id,
                        "status": "failed",
                        "errors": bucket_failures,
                    }

                # sha256 + size
                try:
                    archive_sha256 = _bbk_compute_sha256(archive_path)
                    archive_size = os.path.getsize(archive_path)
                except Exception as e:
                    bucket_failures.append(f"sha256/size failure: {str(e)}")
                    archive_sha256 = ""
                    archive_size = 0

                # Sidecars (.full.meta + .light.meta) and KV record share
                # the same shape and content so get_backup's discovery
                # fallback (which reconstructs a KV row from .full.meta
                # when one is missing — see lines ~820 of get_backup) and
                # tools like trackmecheckbackups continue to work
                # unchanged.
                #
                # The status field is a fresh dict (NOT a reference to
                # in_manifest) carrying the live failures list. The
                # in-archive manifest baked into the .tar.zst earlier has
                # its own frozen snapshot — see the in_manifest write
                # above. All three artifacts (in-archive manifest,
                # .full.meta, KV row) are internally consistent at their
                # own serialization moment.
                finished_epoch = int(round(time.time()))
                live_status = {
                    "run_id": run_id,
                    "archive_scope": scope,
                    "tenant_id": tenant_id or "",
                    "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
                    "trackme_version": trackme_version,
                    "server_name": server_name,
                    "comment": comment,
                    "started_epoch": started_epoch,
                    "finished_epoch": finished_epoch,
                    "collections": list(in_manifest["collections"]),
                    "knowledge_objects": (
                        kos_counts if scope == ARCHIVE_SCOPE_TENANT else {}
                    ),
                    "vtenant_account_file": in_manifest["vtenant_account_file"],
                    "knowledge_objects_file": in_manifest["knowledge_objects_file"],
                    "size": archive_size,
                    "sha256": archive_sha256,
                    "collections_count_non_empty": non_empty_count,
                    "collections_count_empty": empty_count,
                    # Live snapshot of bucket_failures at sidecar-write
                    # time. May contain failures (e.g. sha256 issue) that
                    # post-date the in-archive manifest's frozen list.
                    "failures": list(bucket_failures),
                }

                # full_meta carries the LEGACY shape (mtime / htime /
                # backup_archive / size / archive_details /
                # kvstore_collections_size) so get_backup's discovery
                # path keeps working when KV is wiped or diverges, AND
                # the new 3.0.0 keys for forward consumers.
                kvstore_collections_size_map = {
                    k: v.get("size", 0)
                    for k, v in archive_details.items()
                    if k.startswith("kv_")
                }
                full_meta = {
                    "mtime": str(finished_epoch),
                    "htime": str(time.strftime("%c", time.localtime(finished_epoch))),
                    "server_name": str(server_name),
                    "comment": str(comment),
                    "status": live_status,
                    "change_type": "backup archive created",
                    "backup_archive": str(archive_path),
                    "size": archive_size,
                    "archive_details": archive_details,
                    "kvstore_collections_size": kvstore_collections_size_map,
                    # 3.0.0 fields
                    "backup_run_id": run_id,
                    "archive_scope": scope,
                    "tenant_id": tenant_id or "",
                    "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
                    "archive_sha256": archive_sha256,
                }
                try:
                    with open(f"{archive_path}.full.meta", "w") as f:
                        f.write(json.dumps(full_meta, indent=2))
                    with open(f"{archive_path}.light.meta", "w") as f:
                        f.write(json.dumps(live_status, indent=2))
                except Exception as e:
                    bucket_failures.append(f"sidecar write failure: {str(e)}")
                    # NB: bucket_failures grew, but live_status was already
                    # serialized to disk with the prior snapshot — that's
                    # by design (snapshot at write time, not by reference).

                shutil.rmtree(archive_workdir, ignore_errors=True)

                # Insert KV row — the Guardian's freshness check,
                # GET /backup, and the new GET /backup_runs (PR 4) all
                # read this collection. Use the same live_status as the
                # .full.meta sidecar so the two can be cross-checked. If
                # bucket_failures grew during sidecar write the KV row
                # picks that up too via a fresh snapshot below.
                kv_status = dict(live_status, failures=list(bucket_failures))
                kvrecord = {
                    "mtime": str(finished_epoch),
                    "htime": str(time.strftime("%c", time.localtime(finished_epoch))),
                    "server_name": str(server_name),
                    "comment": str(comment),
                    "status": json.dumps(kv_status, indent=2),
                    "change_type": "backup archive created",
                    "backup_archive": str(archive_path),
                    "size": archive_size,
                    "archive_details": json.dumps(archive_details, indent=2),
                    "kvstore_collections_size": json.dumps(
                        kvstore_collections_size_map, indent=2
                    ),
                    # 3.0.0 fields
                    "backup_run_id": run_id,
                    "archive_scope": scope,
                    "tenant_id": tenant_id or "",
                    "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
                    "archive_sha256": archive_sha256,
                }
                try:
                    kv = service.kvstore["kv_trackme_backup_archives_info"]
                    kv.data.insert(json.dumps(kvrecord))
                except Exception as e:
                    bucket_failures.append(f"KV insert failure: {str(e)}")
                    logger.error(f'run_id="{run_id}" KV insert failure: {str(e)}')

                return {
                    "scope": scope,
                    "tenant_id": tenant_id or "",
                    "run_id": run_id,
                    "archive_path": archive_path,
                    "size": archive_size,
                    "sha256": archive_sha256,
                    "collections_count_non_empty": non_empty_count,
                    "collections_count_empty": empty_count,
                    "knowledge_objects": kos_counts,
                    "errors": bucket_failures,
                    "status": "ok" if not bucket_failures else "partial",
                }
            except Exception as e:
                # Top-level catch-all — honours the function's no-raise
                # contract for unexpected exceptions (e.g. archive_filename
                # validation, os.makedirs, or any future code change). The
                # run loop relies on this to keep building sibling archives.
                logger.exception(
                    f'unhandled exception in _build_one_archive '
                    f'scope="{scope}" tenant_id="{tenant_id or ""}" '
                    f'run_id="{run_id}"'
                )
                # Best-effort cleanup if we managed to create the workdir
                # before the exception.
                try:
                    if "archive_workdir" in locals():
                        shutil.rmtree(archive_workdir, ignore_errors=True)
                except Exception:
                    pass
                return {
                    "scope": scope,
                    "tenant_id": tenant_id or "",
                    "run_id": run_id,
                    "status": "failed",
                    "errors": [f"unhandled exception: {str(e)}"],
                }

        # ----------------------------------------------------------------
        # 7. run loop — sequential, per-bucket isolation
        # ----------------------------------------------------------------
        archives_summary = []

        # Tenant archives first, then the global archive. Ordering matters
        # for the Guardian's freshness check, which uses
        # max(mtime where archive_scope='global'). The global row's
        # mtime should be the latest in a successful run.
        for tid in enabled_tenant_ids:
            archives_summary.append(
                _build_one_archive(
                    ARCHIVE_SCOPE_TENANT,
                    tid,
                    partition["tenant"].get(tid, []),
                )
            )

        if include_global:
            archives_summary.append(
                _build_one_archive(
                    ARCHIVE_SCOPE_GLOBAL,
                    None,
                    partition["global"],
                )
            )

        # ----------------------------------------------------------------
        # 8. write run-level manifest sidecar
        # ----------------------------------------------------------------
        finished_epoch = int(round(time.time()))
        run_manifest = {
            "run_id": run_id,
            "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
            "trackme_version": trackme_version,
            "server_name": server_name,
            "comment": comment,
            "started_epoch": started_epoch,
            "finished_epoch": finished_epoch,
            "tenants_scope": (
                tenants_scope
                if isinstance(tenants_scope, str)
                else list(tenants_scope)
            ),
            "include_global": include_global,
            "blocklist": blocklist,
            "stateful_charts_excluded": partition.get("excluded", []),
            "orphan_tenant_collections": partition.get("orphan_tenant", {}),
            "archives": archives_summary,
        }
        run_manifest_path = os.path.join(backuproot, f"{run_id}.manifest.json")
        try:
            with open(run_manifest_path, "w") as f:
                json.dump(run_manifest, f, indent=2, sort_keys=True)
        except Exception as e:
            logger.error(
                f'failed to write run manifest run_id="{run_id}", exception="{str(e)}"'
            )

        # ----------------------------------------------------------------
        # 9. (no run-level workdir cleanup needed: each archive's workdir
        # is removed inside _build_one_archive after compression — see the
        # `shutil.rmtree(archive_workdir)` calls there. Stale workdirs from
        # crashed runs are swept at the start of the next run by
        # cleanup_backup_directories, which matches the trackme-backup-
        # prefix the workdir stems share with the archive files.)
        # ----------------------------------------------------------------

        # ----------------------------------------------------------------
        # 10. response
        # ----------------------------------------------------------------

        # Backwards-compat field: SPL parsers built around the pre-2.3.22
        # response expected `backup_archive` to be a single path. Set it to
        # the global archive path when one was produced, else to the first
        # produced archive, else empty string.
        legacy_backup_archive = ""
        for a in archives_summary:
            if a.get("scope") == ARCHIVE_SCOPE_GLOBAL and a.get("archive_path"):
                legacy_backup_archive = a.get("archive_path")
                break
        if not legacy_backup_archive:
            for a in archives_summary:
                if a.get("archive_path"):
                    legacy_backup_archive = a.get("archive_path")
                    break

        total_failed = sum(1 for a in archives_summary if a.get("status") == "failed")
        total_partial = sum(1 for a in archives_summary if a.get("status") == "partial")
        total_ok = sum(1 for a in archives_summary if a.get("status") == "ok")

        if archives_summary and total_failed == len(archives_summary):
            logger.error(
                f'TrackMe backup run completed with NO successful archives, '
                f'run_id="{run_id}", failed={total_failed}'
            )
        elif total_failed or total_partial:
            logger.warning(
                f'TrackMe backup run completed with partial failures, '
                f'run_id="{run_id}", ok={total_ok}, partial={total_partial}, '
                f'failed={total_failed}'
            )
        else:
            logger.info(
                f'TrackMe backup run completed successfully, '
                f'run_id="{run_id}", archives={len(archives_summary)}'
            )

        response = {
            "response": (
                f"TrackMe backup run {run_id} produced {len(archives_summary)} archive(s) "
                f"(ok={total_ok}, partial={total_partial}, failed={total_failed})."
            ),
            "backup_run_id": run_id,
            "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
            "server_name": server_name,
            "started_epoch": started_epoch,
            "finished_epoch": finished_epoch,
            "comment": comment,
            "archives": archives_summary,
            "manifest_path": run_manifest_path,
            # Backwards-compat fields used by the saved-search SPL and any
            # external consumer of the pre-2.3.22 response shape.
            "backup_archive": legacy_backup_archive,
            "size": sum(a.get("size", 0) or 0 for a in archives_summary),
        }

        # If every archive failed, surface a 500 so the saved-search SPL
        # logs the run as a failure rather than appending a "successful"
        # event to the audit index.
        if archives_summary and total_failed == len(archives_summary):
            return {"payload": {"response": response}, "status": 500}

        return {"payload": {"response": response}, "status": 200}

    # Purge older backup archives based on a retention
    def delete_backup(self, request_info, **kwargs):

        def cleanup_timestamped_temp_directories(backup_root_dir):
            """
            Clean up any timestamped temporary directories (backup_temp_ddmmyyyy) found in the backup directory.
            This function handles both local and remote cleanup scenarios.
            """
            try:
                # Look for timestamped temp directories with pattern backup_temp_*
                temp_dir_pattern = os.path.join(backup_root_dir, "backup_temp_*")
                temp_dirs = glob.glob(temp_dir_pattern)
                
                cleaned_dirs = []
                for temp_dir in temp_dirs:
                    try:
                        if os.path.isdir(temp_dir):
                            logger.info(f"Found timestamped temp directory to clean: {temp_dir}")
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            cleaned_dirs.append(temp_dir)
                            logger.info(f"Successfully cleaned timestamped temp directory: {temp_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to clean temp directory {temp_dir}: {str(e)}")
                
                if cleaned_dirs:
                    logger.info(f"Cleaned up {len(cleaned_dirs)} timestamped temp directories: {cleaned_dirs}")
                else:
                    logger.info("No timestamped temp directories found to clean")
                    
                return cleaned_dirs
                
            except Exception as e:
                logger.error(f"Error during timestamped temp directory cleanup: {str(e)}")
                return []

        def purge_kv_record_for_archive(archive_name, archive_path=None):
            """
            Remove the KVstore record(s) that reference the given archive.
            Tries exact path match first (when archive_path is provided), then
            falls back to a regex on the archive_name.
            Returns True if at least one record was deleted, False otherwise.
            """
            removed = False
            try:
                collection_name = "kv_trackme_backup_archives_info"
                service = client.connect(
                    owner="nobody",
                    app="trackme",
                    port=splunkd_port,
                    token=request_info.session_key,
                    timeout=600,
                )
                collection = service.kvstore[collection_name]

                # Exact path match when available
                if archive_path:
                    try:
                        kvrec = collection.data.query(query=json.dumps({"backup_archive": archive_path}))[0]
                        key = kvrec.get("_key")
                        if key:
                            collection.data.delete(json.dumps({"_key": key}))
                            removed = True
                    except Exception:
                        # ignore and try regex fallback below
                        pass

                # Regex fallback on file name
                try:
                    kvrecs = collection.data.query(query=json.dumps({"backup_archive": {"$regex": f".*{archive_name}$"}}))
                    for kvrec in kvrecs:
                        key = kvrec.get("_key")
                        if key:
                            try:
                                collection.data.delete(json.dumps({"_key": key}))
                                removed = True
                            except Exception as e:
                                logger.warning(f"Failed to delete KV record key={key}: {str(e)}")
                except Exception as e:
                    logger.warning(f"KVstore regex cleanup failed for archive '{archive_name}': {str(e)}")
            except Exception as e:
                logger.warning(f"KVstore cleanup failed for archive '{archive_name}': {str(e)}")

            return removed

        describe = False
        retention_days = 30  # default to 30 days of retention if not specified
        force_local = False  # default to False, will be set from request if provided
        archive_name = None  # optional targeted deletion
        target_server_name = None  # optional explicit server to contact remotely
        backup_run_id_param = None  # 3.0.0 multi-archive run-mode delete

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get local server name
        #
        # ``server_name`` (short form) is kept for backward compatibility
        # with the targeted-deletion dual-form ownership check below
        # (``current_server_name`` → ``local_short`` at line ~2693) which
        # explicitly assumes a short hostname for the suffix-stripping
        # comparison. ``canonical_server_name`` is the FQDN-preferring
        # value that matches what ``_post_backup_body`` writes to
        # ``kv_trackme_backup_archives_info`` via
        # ``_resolve_canonical_server_name()`` (the 2.3.23 FQDN-convention
        # alignment). It is used at the two sites where this method's
        # local identity is compared against KV-stored ``server_name``
        # values:
        #   1. The retention sweep's per-server fan-out below —
        #      otherwise post-2.3.23 FQDN-form rows for the local SH
        #      would be classified as remote and trigger a wasteful HTTP
        #      self-delegation (perf-only; the delegated call hard-codes
        #      ``force_local=True`` so it short-circuits — but the
        #      round-trip is spammy in the log).
        #   2. The defensive second-pass cleanup KV query inside the
        #      retention sweep — otherwise the short-form filter would
        #      silently return zero matches against FQDN-form rows,
        #      leaving stale rows uncleared whenever the primary
        #      inner-loop cleanup misses one (e.g. a row whose
        #      ``backup_archive`` path differs slightly from the on-disk
        #      file). Bugbot finding d8586255 on release PR #1575.
        server_name = socket.gethostname()
        canonical_server_name = _resolve_canonical_server_name()

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            # Get the retention_days parameter
            try:
                retention_days = resp_dict["retention_days"]

                # convert to an integer
                try:
                    retention_days = int(retention_days)

                except Exception as e:
                    logger.error(
                        f'Invalid retention_days="{retention_days}", expecting an integer'
                    )
                    return {
                        "payload": {
                            "response": f'Invalid retention_days="{retention_days}", expecting an integer, exception="{str(e)}"',
                        },
                        "status": 500,
                    }

            except Exception as e:
                # default to 30 days
                retention_days = 30

            # Optional targeted deletion parameters
            try:
                archive_name = resp_dict.get("archive_name")
            except Exception:
                archive_name = None

            # 3.0.0 multi-archive — delete an entire backup run. When set,
            # the handler iterates every archive in the run and deletes
            # each one (delegating per-archive to the owning SH peer
            # under SHC). The retention sweep below interprets a run as a
            # single unit (all-or-nothing pruning) so a mixed-mtime run
            # is never partially deleted by retention.
            try:
                backup_run_id_param = resp_dict.get("backup_run_id")
            except Exception:
                backup_run_id_param = None

            try:
                target_server_name = resp_dict.get("server_name")
            except Exception:
                target_server_name = None

            # Get the force_local parameter
            try:
                force_local = resp_dict.get("force_local", False)
                if force_local:
                    # accept booleans or strings: true/True/1
                    if isinstance(force_local, bool):
                        force_local = force_local
                    elif isinstance(force_local, str):
                        if force_local in ("true", "True", "1"):
                            force_local = True
                        elif force_local in ("false", "False", "0"):
                            force_local = False
                        else:
                            return {
                                "payload": {"error": "force_local must be true or false"},
                                "status": 400,
                            }
                    else:
                        force_local = False

            except Exception as e:
                # default to False
                force_local = False

        else:
            # body is not required in this endpoint
            describe = False

        if describe:
            response = {
                "describe": "This endpoint deletes backups. It supports either: (1) a targeted deletion by archive_name, or (2) a retention-based purge of files older than retention_days.",
                "resource_desc": "Delete TrackMe backup archives",
                "resource_spl_example": "| trackme url=/services/trackme/v2/backup_and_restore/backup mode=delete body=\"{'archive_name': 'trackme-backup-20210205-142635.tgz', 'force_local': 'true'}\" OR | trackme url=/services/trackme/v2/backup_and_restore/backup mode=delete body=\"{'retention_days': '30'}\"",
                "options": [
                    {
                        "retention_days": "(integer) OPTIONAL: the maximal retention for backup archive files in days, if not specified defaults to 30 days",
                    },
                    {
                        "archive_name": "(string) OPTIONAL: Name of the backup archive to delete. If provided, performs a targeted deletion instead of retention purge.",
                    },
                    {
                        "force_local": "(true / false) OPTIONAL: if true, the endpoint will only process local backup archives and will not attempt to delegate to remote servers in a Search Head Cluster context. For targeted deletion with server_name, remote call will force_local=True.",
                    },
                    {
                        "server_name": "(string) OPTIONAL: If provided with archive_name, the endpoint will attempt to call that remote server to delete the archive (with force_local=true on the remote).",
                    },
                    {
                        "backup_run_id": "(string) OPTIONAL (3.0.0 multi-archive only): the backup_run_id of a run to delete. The handler iterates every archive in the run and deletes each one (with SHC delegation per-archive). Mutually exclusive with archive_name. The retention sweep also honours this concept — a run is pruned all-or-nothing based on its newest archive's mtime, so a mixed-mtime run is never partially deleted.",
                    },
                ],
            }

            return {"payload": response, "status": 200}

        else:
            # ----------------------------------------------------------
            # 3.0.0 run-mode delete dispatch (added 2.3.22).
            # When backup_run_id is set, look up every archive in the
            # run and delete each one (delegating per-archive to the
            # owning SH peer under SHC). Falls through to the legacy
            # path for archive_name / retention_days requests.
            # ----------------------------------------------------------
            if backup_run_id_param:
                logger.info(
                    f"delete_backup: 3.0.0 run-mode delete for "
                    f"backup_run_id='{backup_run_id_param}', force_local={force_local}"
                )
                return self._v3_delete_run(
                    request_info, backup_run_id_param, force_local, splunkd_port,
                )

            # Set backup root dir
            backuproot = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")

            # Clean up any timestamped temporary directories first
            logger.info("Starting cleanup of timestamped temporary directories...")
            cleaned_temp_dirs = cleanup_timestamped_temp_directories(backuproot)

            # If archive_name is provided, perform targeted deletion logic
            if archive_name:
                logger.info(f"delete_backup targeted deletion requested for archive_name='{archive_name}', force_local='{force_local}', server_name='{target_server_name}'")

                # Determine if we should handle locally or remotely
                current_server_name = server_name

                # By default, assume local handling
                handle_local = True
                remote_target_name = None

                # If an explicit server_name is provided, handle locally if it targets this host (short or FQDN)
                if target_server_name:
                    try:
                        local_short = current_server_name.lower()
                        local_fqdn = socket.getfqdn().lower()
                        target_lower = str(target_server_name).lower()
                        target_short = target_lower.split('.', 1)[0]

                        if target_lower in (local_short, local_fqdn) or target_short == local_short:
                            handle_local = True
                            remote_target_name = None
                        else:
                            handle_local = False
                            remote_target_name = target_server_name
                    except Exception:
                        # On any resolution error, fall back to previous behavior
                        if target_server_name != current_server_name:
                            handle_local = False
                            remote_target_name = target_server_name
                else:
                    # If not forced local, try to resolve server_name via KVstore metadata
                    if not force_local:
                        try:
                            collection_name = "kv_trackme_backup_archives_info"
                            service = client.connect(
                                owner="nobody",
                                app="trackme",
                                port=splunkd_port,
                                token=request_info.session_key,
                                timeout=600,
                            )
                            collection = service.kvstore[collection_name]
                            kv_query = {"backup_archive": {"$regex": f".*{archive_name}$"}}
                            kvrecords = collection.data.query(query=json.dumps(kv_query))
                            if len(kvrecords) > 0:
                                backup_server_name = kvrecords[0].get("server_name")
                                if backup_server_name and backup_server_name != current_server_name:
                                    handle_local = False
                                    remote_target_name = backup_server_name
                        except Exception as e:
                            logger.warning(f"KVstore lookup for targeted deletion failed: {str(e)}")

                if handle_local:
                    # Perform local deletion
                    try:
                        archive_path = os.path.join(backuproot, archive_name)
                        if not os.path.exists(archive_path):
                            # File missing locally: purge KVstore record(s) anyway
                            purged = purge_kv_record_for_archive(archive_name, archive_path)
                            msg = f"Archive not found locally ({archive_path}). KVstore record removed={purged}"
                            logger.warning(msg)
                            return {
                                "payload": {"error": msg},
                                "status": 404,
                            }

                        # delete archive file
                        os.remove(archive_path)

                        # delete optional metadata files if present
                        for meta_suffix in [".light.meta", ".full.meta"]:
                            try:
                                meta_path = f"{archive_path}{meta_suffix}"
                                if os.path.exists(meta_path):
                                    os.remove(meta_path)
                            except Exception as e:
                                logger.warning(f"Failed to delete metadata file '{meta_path}': {str(e)}")

                        # purge KVstore record(s)
                        purge_kv_record_for_archive(archive_name, archive_path)

                        response = {
                            "status": f"Successfully deleted backup archive {archive_name} on server {current_server_name}",
                            "local_operation": {
                                "status": "success",
                                "backup_files": [archive_path],
                                "temp_directories_cleaned": len(cleaned_temp_dirs),
                                "temp_directories": cleaned_temp_dirs,
                            },
                            "remote_operations": [],
                        }
                        logger.info(json.dumps(response, indent=4))
                        return {"payload": response, "status": 200}
                    except Exception as e:
                        logger.error(f"Error deleting local archive '{archive_name}': {str(e)}")
                        return {"payload": {"error": str(e)}, "status": 500}

                else:
                    # Perform remote deletion by calling the endpoint on the remote server with force_local=True
                    try:
                        # Determine the best reachable name (short vs FQDN)
                        target_name = remote_target_name
                        if not test_splunkd_connectivity(
                            remote_target_name,
                            request_info.server_rest_port,
                            request_info.session_key,
                        ):
                            # FQDN-suffix fallback. Skip the suffix-append
                            # entirely when ``remote_target_name`` is already
                            # an FQDN (contains a dot) — post-PR-#1568 KV
                            # rows store FQDN-form ``server_name``, so the
                            # naive ``f"{X}.{suffix}"`` would produce a
                            # double-suffixed target like
                            # ``host.domain.com.domain.com`` that will never
                            # resolve. Mirrors the canonical fix at
                            # ``_v3_delegate_restore_to_peer`` (PR #1627,
                            # bugbot ID cf36f216).
                            remote_server_fqdn = None
                            if "." not in remote_target_name:
                                local_fqdn = socket.getfqdn()
                                fqdn_suffix = (
                                    local_fqdn.split(".", 1)[1]
                                    if "." in local_fqdn
                                    else "local"
                                )
                                remote_server_fqdn = f"{remote_target_name}.{fqdn_suffix}"
                            if remote_server_fqdn:
                                logger.info(
                                    f"Short hostname failed, trying FQDN: {remote_server_fqdn}"
                                )
                            if remote_server_fqdn and test_splunkd_connectivity(
                                remote_server_fqdn,
                                request_info.server_rest_port,
                                request_info.session_key,
                            ):
                                target_name = remote_server_fqdn
                            else:
                                # Branch-aware error reflects whether the
                                # FQDN-suffix fallback ran or was skipped.
                                if remote_server_fqdn:
                                    err_detail = (
                                        f"short ({remote_target_name!r}) and "
                                        f"FQDN-suffix fallback "
                                        f"({remote_server_fqdn!r}) both failed"
                                    )
                                else:
                                    err_detail = (
                                        f"FQDN form ({remote_target_name!r}) "
                                        f"failed; no short->FQDN fallback "
                                        f"applicable"
                                    )
                                return {
                                    "payload": {
                                        "error": (
                                            f"Connectivity failed to remote "
                                            f"server {remote_target_name} "
                                            f"({err_detail})"
                                        )
                                    },
                                    "status": 500,
                                }

                        target_server_uri = f"https://{target_name}:{request_info.server_rest_port}"
                        target_url = f"{target_server_uri}/services/trackme/v2/backup_and_restore/backup"
                        request_payload = {"archive_name": archive_name, "force_local": True}
                        logger.info(f"Delegating targeted deletion to remote server {target_name} with payload={json.dumps(request_payload)}")

                        response = requests.delete(
                            target_url,
                            json=request_payload,
                            headers={
                                "Authorization": f"Splunk {request_info.session_key}",
                                "Content-Type": "application/json",
                            },
                            verify=False,
                            timeout=300,
                        )

                        if response.status_code == 200:
                            response_data = response.json()
                            remote_info = {
                                "server": target_name,
                                "status": "success",
                                "remote_response": response_data,
                            }
                            overall = {
                                "status": f"Successfully delegated deletion of {archive_name} to remote server {target_name}",
                                "local_operation": {
                                    "status": "delegated",
                                    "backup_files": [],
                                    "temp_directories_cleaned": len(cleaned_temp_dirs),
                                    "temp_directories": cleaned_temp_dirs,
                                },
                                "remote_operations": [remote_info],
                            }
                            logger.info(json.dumps(overall, indent=4))
                            return {"payload": overall, "status": 200}
                        else:
                            logger.error(f"Remote server {target_name} returned error: {response.status_code} - {response.text}")
                            # If remote deletion failed due to 404 (missing file) or connectivity issues (5xx),
                            # still purge the local KVstore record referencing this archive
                            if response.status_code in (404, 502, 503, 504):
                                purge_kv_record_for_archive(archive_name)
                            return {
                                "payload": {
                                    "error": f"Remote deletion failed on {target_name}: HTTP {response.status_code}: {response.text}"
                                },
                                "status": response.status_code,
                            }
                    except Exception as e:
                        logger.error(f"Error during remote targeted deletion to {remote_target_name}: {str(e)}")
                        # On connectivity error, purge KVstore record locally
                        purge_kv_record_for_archive(archive_name)
                        return {"payload": {"error": str(e)}, "status": 500}

            # For reporting purposes (retention-based purge)
            purgedlist = []
            # Subset of ``purgedlist`` that contains ONLY archive files
            # (``.tgz`` / ``.tar.zst``). Sidecars (``.full.meta`` /
            # ``.light.meta``) and run manifests (``.manifest.json``)
            # added in 2.3.23 don't have their own
            # ``kv_trackme_backup_archives_info`` rows, so the
            # downstream outer-cleanup KV loop (further below) and the
            # ``len > 2`` gate that decides whether to run it both key
            # off this archives-only count. Without this distinction
            # the outer loop would issue ~17 wasted KV queries per
            # expired 3.0.0 run (one per sidecar / manifest, each
            # returning empty) AND the threshold gate would trivially
            # pass for any single-archive expiration. Bugbot finding
            # (PR #1579).
            purged_archives = []
            remote_purged_results = []

            # retention_days = 30

            time_in_secs = time.time() - (retention_days * 24 * 60 * 60)
            for root, dirs, files in os.walk(backuproot, topdown=False):
                for file_ in files:
                    full_path = os.path.join(root, file_)
                    stat = os.stat(full_path)

                    if stat.st_mtime <= time_in_secs:
                        if os.path.isdir(full_path):
                            try:
                                os.rmdir(full_path)
                                purgedlist.append(full_path)

                            except Exception as e:
                                logger.error(
                                    f'Failed to delete the backup archive="{full_path}" with exception="{str(e)}"'
                                )
                                return {
                                    "payload": {
                                        "response": f'Failed to delete the backup archive="{full_path}" with exception="{str(e)}"',
                                    },
                                    "status": 500,
                                }

                        else:
                            # ── Retention sweep — file matching ──
                            #
                            # Three families of TrackMe backup-related
                            # files live in the backup root:
                            #
                            #   * Archives — ``.tgz`` (legacy 1.0.0/2.0.0)
                            #     and ``.tar.zst`` (3.0.0). One KV row in
                            #     ``kv_trackme_backup_archives_info`` per
                            #     archive.
                            #   * Per-archive sidecars — ``<archive>.full.meta``
                            #     and ``<archive>.light.meta`` (2.1.5+).
                            #     No KV row of their own — they accompany
                            #     the archive.
                            #   * Run manifest — ``<run_id>.manifest.json``
                            #     (3.0.0). One per multi-archive run. No
                            #     KV row.
                            #
                            # Pre-2.3.23 the retention sweep only matched
                            # the first family and silently left sidecars +
                            # run manifests on disk forever. At fleet
                            # scale (19+ files per 3.0.0 run × daily backups
                            # × 30-day retention), the backup directory
                            # accumulated ~1,140 orphan sidecars at steady
                            # state. KB-scale per file so disk-space-wise
                            # not catastrophic, but operationally messy
                            # and unbounded.
                            #
                            # All three families now get unlinked when
                            # their mtime is past the retention horizon.
                            # KV cleanup is still gated on ``is_archive``
                            # because sidecars and manifests don't carry
                            # their own rows.
                            is_archive = (
                                full_path.endswith(".tgz")
                                or full_path.endswith(".tar.zst")
                            )
                            is_sidecar = (
                                full_path.endswith(".full.meta")
                                or full_path.endswith(".light.meta")
                            )
                            is_run_manifest = full_path.endswith(".manifest.json")

                            if not (is_archive or is_sidecar or is_run_manifest):
                                # Not a TrackMe backup artifact; skip
                                # without touching it. Matches the
                                # pre-2.3.23 conservative behaviour for
                                # unrecognised files in the backup root.
                                continue

                            if not os.path.exists(full_path):
                                # Race with another deletion (e.g. an
                                # earlier iteration removed this file
                                # already if it was already enumerated
                                # by os.walk). Idempotent skip.
                                continue

                            try:
                                os.remove(full_path)
                                purgedlist.append(full_path)
                                if is_archive:
                                    purged_archives.append(full_path)
                            except Exception as e:
                                logger.warning(
                                    f"retention: failed to delete "
                                    f"\"{full_path}\" with exception="
                                    f"\"{str(e)}\" — continuing the "
                                    f"sweep (other files may still be "
                                    f"reclaimed)."
                                )
                                continue

                            # Only archives have KV rows. Sidecars and
                            # run manifests are unlinked above; no KV
                            # bookkeeping to do for them.
                            if is_archive:
                                # Purge the record from the KVstore.

                                # Define the KV query
                                query_string = {
                                    "backup_archive": full_path,
                                }

                                # backup audit collection
                                collection_name_backup_archives_info = (
                                    "kv_trackme_backup_archives_info"
                                )
                                service_backup_archives_info = client.connect(
                                    owner="nobody",
                                    app="trackme",
                                    port=splunkd_port,
                                    token=request_info.session_key,
                                    timeout=600,
                                )
                                collection_backup_archives_info = (
                                    service_backup_archives_info.kvstore[
                                        collection_name_backup_archives_info
                                    ]
                                )

                                try:
                                    kvrecord = (
                                        collection_backup_archives_info.data.query(
                                            query=json.dumps(query_string)
                                        )[0]
                                    )
                                    key = kvrecord.get("_key")

                                except Exception as e:
                                    key = None

                                # If a record cannot be found, this backup file is not know to TrackMe currently, add a new record
                                if key is not None:
                                    try:
                                        # Delete the record
                                        collection_backup_archives_info.data.delete(
                                            json.dumps({"_key": key})
                                        )

                                    except Exception as e:
                                        logger.error(
                                            f'Failed to purge the KVstore record in collection="{collection_name_backup_archives_info}" with exception="{str(e)}"'
                                        )
                                        return {
                                            "payload": {
                                                "response": f'Failed to purge the KVstore record in collection="{collection_name_backup_archives_info}" with exception="{str(e)}"',
                                            },
                                            "status": 500,
                                        }

            # Query KVstore to get all unique server names for remote member handling
            # Only do this if force_local is False (default behavior)
            if not force_local:
                collection_name_backup_archives_info = "kv_trackme_backup_archives_info"
                service_backup_archives_info = client.connect(
                    owner="nobody",
                    app="trackme",
                    port=splunkd_port,
                    token=request_info.session_key,
                    timeout=600,
                )
                collection_backup_archives_info = service_backup_archives_info.kvstore[
                    collection_name_backup_archives_info
                ]

                # Get all unique server names from the KVstore
                try:
                    all_records = collection_backup_archives_info.data.query()
                    unique_servers = set()
                    # Compare KV ``server_name`` against BOTH the short form
                    # (legacy/pre-2.3.23 archives) AND the canonical FQDN
                    # form (post-2.3.23 archives) before classifying a row
                    # as remote. Without the canonical match, post-2.3.23
                    # FQDN-form rows for the local SH would be added to
                    # ``unique_servers`` and trigger a wasteful HTTP
                    # self-delegation. The delegated call hard-codes
                    # ``force_local=True`` so it short-circuits cleanly, but
                    # the round-trip is spammy in the log. Bugbot finding
                    # d8586255 on release PR #1575.
                    for record in all_records:
                        server_name_from_kv = record.get("server_name")
                        if server_name_from_kv and server_name_from_kv not in (
                            server_name,
                            canonical_server_name,
                        ):
                            unique_servers.add(server_name_from_kv)
                    
                    logger.info(f"Found {len(unique_servers)} remote servers in KVstore: {list(unique_servers)}")
                    
                    # For each remote server, make a call to delete backups with force_local=True
                    for remote_server in unique_servers:
                        try:
                            logger.info(f"Delegating backup deletion to remote server: {remote_server}")
                            
                            # Test connectivity with short hostname first, then FQDN if needed
                            target_server_name = remote_server
                            
                            if not test_splunkd_connectivity(
                                remote_server,
                                request_info.server_rest_port,
                                request_info.session_key,
                            ):
                                # FQDN-suffix fallback. Skip the suffix-append
                                # entirely when ``remote_server`` is already
                                # an FQDN (contains a dot) — post-PR-#1568 KV
                                # rows store FQDN-form ``server_name``, so the
                                # naive ``f"{X}.{suffix}"`` would produce a
                                # double-suffixed target like
                                # ``host.domain.com.domain.com`` that will
                                # never resolve. Mirrors the canonical fix at
                                # ``_v3_delegate_restore_to_peer`` (PR #1627,
                                # bugbot ID cf36f216).
                                remote_server_fqdn = None
                                if "." not in remote_server:
                                    local_fqdn = socket.getfqdn()
                                    fqdn_suffix = (
                                        local_fqdn.split(".", 1)[1]
                                        if "." in local_fqdn
                                        else "local"
                                    )
                                    remote_server_fqdn = f"{remote_server}.{fqdn_suffix}"
                                if remote_server_fqdn:
                                    logger.info(
                                        f"Short hostname failed, trying FQDN: {remote_server_fqdn}"
                                    )
                                if remote_server_fqdn and test_splunkd_connectivity(
                                    remote_server_fqdn,
                                    request_info.server_rest_port,
                                    request_info.session_key,
                                ):
                                    target_server_name = remote_server_fqdn
                                    logger.info(
                                        f"FQDN connectivity successful, using: {target_server_name}"
                                    )
                                else:
                                    # Branch-aware warning reflects whether
                                    # the FQDN-suffix fallback ran or was
                                    # skipped.
                                    if remote_server_fqdn:
                                        warn_detail = (
                                            f"short ({remote_server!r}) and "
                                            f"FQDN-suffix fallback "
                                            f"({remote_server_fqdn!r}) both "
                                            f"failed"
                                        )
                                    else:
                                        warn_detail = (
                                            f"FQDN form ({remote_server!r}) "
                                            f"failed; no short->FQDN fallback "
                                            f"applicable"
                                        )
                                    logger.warning(
                                        f"Connectivity failed for {remote_server} "
                                        f"({warn_detail}), skipping remote deletion"
                                    )
                                    remote_purged_results.append({
                                        "server": remote_server,
                                        "status": "failed",
                                        "error": "Connectivity failed"
                                    })
                                    continue
                            else:
                                logger.info(
                                    f"Short hostname connectivity successful, using: {target_server_name}"
                                )

                            # support only https
                            target_server_uri = (
                                f"https://{target_server_name}:{request_info.server_rest_port}"
                            )

                            # Prepare the request payload
                            request_payload = {
                                "retention_days": retention_days,
                                "force_local": True,
                            }

                            target_url = f"{target_server_uri}/services/trackme/v2/backup_and_restore/backup"

                            # Make REST call to target server
                            try:
                                response = requests.delete(
                                    target_url,
                                    json=request_payload,
                                    headers={
                                        "Authorization": f"Splunk {request_info.session_key}",
                                        "Content-Type": "application/json",
                                    },
                                    verify=False,
                                    timeout=300,
                                )

                                if response.status_code == 200:
                                    response_data = response.json()
                                    logger.info(
                                        f"Successfully deleted backups on remote server {remote_server}"
                                    )
                                    
                                    # Extract relevant information from remote response
                                    remote_status = response_data.get("status", "Unknown status")
                                    remote_files_purged = 0
                                    if "local_operation" in response_data:
                                        remote_files_purged = response_data["local_operation"].get("files_purged", 0)
                                    elif "backup_files" in response_data:
                                        remote_files_purged = len(response_data["backup_files"])
                                    
                                    remote_purged_results.append({
                                        "server": remote_server,
                                        "status": "success",
                                        "local_status": remote_status,
                                        "files_purged": remote_files_purged
                                    })
                                else:
                                    logger.error(
                                        f"Remote server {remote_server} returned error: {response.status_code} - {response.text}"
                                    )
                                    remote_purged_results.append({
                                        "server": remote_server,
                                        "status": "failed",
                                        "error": f"HTTP {response.status_code}: {response.text}"
                                    })

                            except requests.exceptions.ConnectionError as e:
                                logger.error(
                                    f"Connection error to remote server {remote_server}: {str(e)}"
                                )
                                remote_purged_results.append({
                                    "server": remote_server,
                                    "status": "failed",
                                    "error": f"Connection error: {str(e)}"
                                })
                            except Exception as e:
                                logger.error(
                                    f"Error making REST call to remote server {remote_server}: {str(e)}"
                                )
                                remote_purged_results.append({
                                    "server": remote_server,
                                    "status": "failed",
                                    "error": f"REST call error: {str(e)}"
                                })

                        except Exception as e:
                            logger.error(
                                f"Error processing remote server {remote_server}: {str(e)}"
                            )
                            remote_purged_results.append({
                                "server": remote_server,
                                "status": "failed",
                                "error": f"Processing error: {str(e)}"
                            })

                except Exception as e:
                    logger.error(
                        f"Failed to query KVstore for remote servers: {str(e)}"
                    )
                    # Continue with local processing even if remote query fails

            # Gate the outer cleanup pass on the count of ARCHIVES
            # purged, not all artefacts. Pre-2.3.23 ``purgedlist`` only
            # contained archives so this condition was about archive
            # count; preserving that semantic now that the list also
            # contains sidecars + manifests. Bugbot finding (PR #1579).
            if not len(purged_archives) > 2:
                # Determine overall status based on local and remote results
                local_status = f"No local backup files older than {retention_days} days found"
                remote_success_count = sum(1 for result in remote_purged_results if result.get("status") == "success")
                remote_failed_count = len(remote_purged_results) - remote_success_count
                
                if remote_purged_results:
                    if remote_failed_count == 0:
                        overall_status = f"{local_status}. Remote cleanup: {remote_success_count} server(s) processed successfully"
                    elif remote_success_count == 0:
                        overall_status = f"{local_status}. Remote cleanup: {remote_failed_count} server(s) failed"
                    else:
                        overall_status = f"{local_status}. Remote cleanup: {remote_success_count} server(s) succeeded, {remote_failed_count} server(s) failed"
                else:
                    overall_status = local_status

                response = {
                    "status": overall_status,
                    "local_operation": {
                        "status": local_status,
                        "files_purged": 0,
                        "temp_directories_cleaned": len(cleaned_temp_dirs),
                        "temp_directories": cleaned_temp_dirs
                    },
                    "remote_operations": remote_purged_results
                }

                logger.info(json.dumps(response, indent=4))
                return {"payload": response, "status": 200}

            else:
                # For each backup archive, if a record is found in the collection info, remove the record

                # backup audit collection
                collection_name_backup_archives_info = "kv_trackme_backup_archives_info"
                service_backup_archives_info = client.connect(
                    owner="nobody",
                    app="trackme",
                    port=splunkd_port,
                    token=request_info.session_key,
                    timeout=600,
                )
                collection_backup_archives_info = service_backup_archives_info.kvstore[
                    collection_name_backup_archives_info
                ]

                # Iterate ARCHIVES only — sidecars + run manifests
                # don't have ``kv_trackme_backup_archives_info`` rows
                # so querying for them would issue ~17 wasted REST
                # calls per expired 3.0.0 run. The inner KV cleanup in
                # the main retention loop above already removes the
                # row paired with each archive; this outer loop is a
                # defensive second pass for any rows that the inner
                # pass missed (e.g. a stale row whose ``backup_archive``
                # path differs slightly from the on-disk file). Bugbot
                # finding (PR #1579).
                for backupfile in purged_archives:
                    key = None
                    record = None

                    # Define the KV query.
                    #
                    # The ``server_name`` filter must accept BOTH the short
                    # form (legacy/pre-2.3.23 rows that
                    # ``post_backup``-pre-2.3.23 wrote via plain
                    # ``socket.gethostname()``) AND the canonical FQDN form
                    # (post-2.3.23 rows that ``_post_backup_body`` writes
                    # via ``_resolve_canonical_server_name()``). A
                    # short-form-only filter would silently return zero
                    # matches against FQDN-form rows on FQDN deployments
                    # (Splunk Cloud, most enterprise SHCs), defeating the
                    # belt-and-braces second-pass cleanup that exists
                    # precisely to catch stale rows the inner loop missed.
                    # Bugbot finding d8586255 on release PR #1575.
                    query_string = {
                        "$and": [
                            {
                                "backup_archive": backupfile,
                                "server_name": {
                                    "$in": [server_name, canonical_server_name],
                                },
                            }
                        ]
                    }

                    try:
                        kvrecord = collection_backup_archives_info.data.query(
                            query=json.dumps(query_string)
                        )[0]
                        key = kvrecord.get("_key")

                    except Exception as e:
                        key = None

                    # If a record is found, it shall be purged
                    if key is not None:
                        # Remove the record
                        try:
                            collection_backup_archives_info.data.delete(
                                json.dumps({"_key": key})
                            )

                        except Exception as e:
                            logger.error(
                                f'Failed to purge the KVstore record in collection="{collection_name_backup_archives_info}" with exception="{str(e)}"'
                            )
                            return {
                                "payload": {
                                    "response": f'Failed to purge the KVstore record in collection="{collection_name_backup_archives_info}" with exception="{str(e)}"',
                                },
                                "status": 500,
                            }

                # Determine overall status based on local and remote results
                local_status = f"Successfully purged {len(purgedlist)} local backup files older than {retention_days} days"
                remote_success_count = sum(1 for result in remote_purged_results if result.get("status") == "success")
                remote_failed_count = len(remote_purged_results) - remote_success_count
                
                if remote_purged_results:
                    if remote_failed_count == 0:
                        overall_status = f"{local_status}. Remote cleanup: {remote_success_count} server(s) processed successfully"
                    elif remote_success_count == 0:
                        overall_status = f"{local_status}. Remote cleanup: {remote_failed_count} server(s) failed"
                    else:
                        overall_status = f"{local_status}. Remote cleanup: {remote_success_count} server(s) succeeded, {remote_failed_count} server(s) failed"
                else:
                    overall_status = local_status

                response = {
                    "status": overall_status,
                    "local_operation": {
                        "status": local_status,
                        "files_purged": len(purgedlist),
                        "backup_files": purgedlist,
                        "temp_directories_cleaned": len(cleaned_temp_dirs),
                        "temp_directories": cleaned_temp_dirs
                    },
                    "remote_operations": remote_purged_results
                }

                logger.info(json.dumps(response, indent=4))
                return {"payload": response, "status": 200}

    # Restore collections from a backup archive
    # For Splunk Cloud certification purposes, the archive must be located in the backup directory of the application

    def post_restore(self, request_info, **kwargs):

        def clean_backup_dir(backupdir):
            """
            A simple function to remove the backup dir
            """
            try:
                shutil.rmtree(backupdir)
                return True
            except OSError as e:
                logger.error(
                    f'failed to purge the extraction temporary directory="{backupdir}" with exception="{str(e)}"'
                )

        def restore_kvstore_records(
            service,
            collection_name,
            collections_restore_dict,
            backupdir,
            kvstore_collections_global_records_to_be_restored,
            kvstore_collections_global_records_restored,
            kvstore_collections_restored_warning,
            restore_results_dict,
            kvstore_collections_clean_empty,
        ):
            """
            Restore KVstore records from a backup JSON file, with an option to clean existing records.

            Args:
                service: Splunk service object for KVstore access.
                collection_name: The name of the KVstore collection to restore.
                collections_restore_dict: Dictionary containing metadata of collections.
                backupdir: Path to the backup directory.
                kvstore_collections_global_records_to_be_restored: Global counter for total records to be restored.
                kvstore_collections_global_records_restored: Global counter for successfully restored records.
                kvstore_collections_restored_warning: List of collections with restoration warnings.
                restore_results_dict: Dictionary to store restoration results.
                kvstore_collections_clean_empty: Boolean indicating whether to clean the collection if it was empty in the backup.

            Returns:
                A tuple containing updated global counters, as well as summary dict describing the operation:
                - kvstore_collections_global_records_to_be_restored
                - kvstore_collections_global_records_restored
                - kvstore_collection_restore_summary_dict
            """

            # Check if collection exists in restore dict
            if collection_name not in collections_restore_dict:
                error_msg = f'Collection "{collection_name}" not found in backup data. This may be due to the collection being excluded from backups (e.g., stateful charts collections).'
                logger.warning(error_msg)
                raise KeyError(error_msg)

            # Get collection metadata
            source_json_file = collections_restore_dict[collection_name]["file"]
            source_json_file_size = collections_restore_dict[collection_name]["size"]
            source_json_file_records = collections_restore_dict[collection_name][
                "records"
            ]

            # init dict summary
            kvstore_collection_restore_summary_dict = {
                "collection_name": collection_name,
                "source_json_file": source_json_file,
                "source_json_file_size": source_json_file_size,
                "source_json_file_records": source_json_file_records,
            }

            # Check if this is a stateful charts collection that should be excluded
            if collection_name.startswith(
                "kv_trackme_stateful_alerting_charts_tenant_"
            ):
                info_msg = f'TrackMe restore kvstore records process, skipping restoration of stateful charts collection="{collection_name}" on purpose. KVstore records for stateful charts collections are not restored.'
                logger.info(info_msg)
                tasks_list.append(info_msg)

                # Add results to restore_results_dict with 0 restored records
                restore_results_dict[collection_name] = {
                    "source_json_file": source_json_file,
                    "source_json_file_size": source_json_file_size,
                    "source_json_file_records": source_json_file_records,
                    "restored_records": 0,
                    "skipped": True,
                    "skip_reason": "Stateful charts collection - excluded on purpose",
                }

                # Return with unchanged global counters since we're not restoring any records
                kvstore_collection_restore_summary_dict["restored_records"] = 0
                kvstore_collection_restore_summary_dict["skipped"] = True
                kvstore_collection_restore_summary_dict["skip_reason"] = (
                    "Stateful charts collection - excluded on purpose"
                )

                return (
                    kvstore_collections_global_records_to_be_restored,
                    kvstore_collections_global_records_restored,
                    kvstore_collection_restore_summary_dict,
                )

            # Log start of the process
            logger.info(
                f'TrackMe restore kvstore records process starting, processing restore of collection_name="{collection_name}", '
                f'source_json_file="{source_json_file}", source_json_file_size="{source_json_file_size}", '
                f'source_json_file_records="{source_json_file_records}"'
            )

            # Connect to the KVstore collection
            try:
                collection = service.kvstore[collection_name]
            except Exception as e:
                error_nsg = f'TrackMe restore kvstore records process, failed to connect to KVstore collection="{collection_name}" with exception="{str(e)}"'
                logger.error(error_nsg)
                kvstore_collections_restored_warning.append(collection_name)
                errors_list.append(error_nsg)
                return (
                    kvstore_collections_global_records_to_be_restored,
                    kvstore_collections_global_records_restored,
                    kvstore_collection_restore_summary_dict,
                )

            # Handle kvstore_collections_clean_empty
            if kvstore_collections_clean_empty and source_json_file_records == 0:
                try:
                    collection.data.delete()  # Delete all records in the collection
                    info_nsg = f'TrackMe restore kvstore records process, collection "{collection_name}" was empty in the backup. Existing records have been cleared.'
                    logger.info(info_nsg)
                    tasks_list.append(info_nsg)
                except Exception as e:
                    error_msg = f'TrackMe restore kvstore records process, failed to clear records in collection="{collection_name}" with exception="{str(e)}"'
                    logger.error(error_msg)
                    errors_list.append(error_msg)
                    kvstore_collections_restored_warning.append(collection_name)
                    return (
                        kvstore_collections_global_records_to_be_restored,
                        kvstore_collections_global_records_restored,
                        kvstore_collection_restore_summary_dict,
                    )

            # Load the JSON data
            counter = 0
            try:
                with open(os.path.join(backupdir, source_json_file), "r") as f:
                    data = json.load(f)

                # Update global counters
                kvstore_collections_global_records_to_be_restored += len(data)

                # Process data in chunks
                chunks = [data[i : i + 500] for i in range(0, len(data), 500)]
                for chunk in chunks:
                    try:
                        collection.data.batch_save(*chunk)
                        kvstore_collections_global_records_restored += len(chunk)
                        counter += len(chunk)
                    except Exception as e:
                        error_msg = (
                            f'TrackMe restore kvstore records process, failed to restore records in collection="{collection_name}" with exception="{str(e)}"'
                            f'collection_name="{collection_name}", '
                            f'source_json_file="{source_json_file}", source_json_file_size="{source_json_file_size}", '
                        )
                        logger.error(error_msg)
                        errors_list.append(error_msg)
                        kvstore_collections_restored_warning.append(collection_name)

                # Add results to restore_results_dict
                restore_results_dict[collection_name] = {
                    "source_json_file": source_json_file,
                    "source_json_file_size": source_json_file_size,
                    "source_json_file_records": source_json_file_records,
                    "restored_records": counter,
                }

                # Log success or mismatch in record counts
                if int(source_json_file_records) != int(counter):
                    info_msg = (
                        f"TrackMe restore kvstore records process finished but could not verify the number of restored records "
                        f'to equal the number of records in the source file, collection_name="{collection_name}", '
                        f'source_json_file="{source_json_file}", source_json_file_size="{source_json_file_size}", '
                        f'source_json_file_records="{source_json_file_records}", restored_records="{counter}"'
                    )
                    logger.error(info_msg)
                    errors_list.append(info_msg)
                else:

                    info_msg = (
                        f'TrackMe restore kvstore records process finished successfully, collection_name="{collection_name}", '
                        f'source_json_file="{source_json_file}", source_json_file_size="{source_json_file_size}", '
                        f'source_json_file_records="{source_json_file_records}", restored_records="{counter}"'
                    )
                    logger.info(info_msg)
                    tasks_list.append(info_msg)

            except Exception as e:
                restore_results_dict[collection_name] = {
                    "source_json_file": source_json_file,
                    "source_json_file_size": source_json_file_size,
                    "source_json_file_records": source_json_file_records,
                    "restored_records": 0,
                    "exception": f'TrackMe restore kvstore records process, failed to open JSON file="{os.path.join(backupdir, source_json_file)}" for reading with exception="{str(e)}"',
                }
                kvstore_collections_restored_warning.append(collection_name)
                error_msg = (
                    f'TrackMe restore kvstore records process, failed to open JSON file="{os.path.join(backupdir, source_json_file)}" for reading with exception="{str(e)}"'
                    f'collection_name="{collection_name}", '
                    f'source_json_file="{source_json_file}", source_json_file_size="{source_json_file_size}", '
                    f'source_json_file_records="{source_json_file_records}", restored_records="{counter}"'
                )
                logger.error(error_msg)
                errors_list.append(error_msg)

            # add counters to the summary dict
            kvstore_collection_restore_summary_dict["restored_records"] = counter

            return (
                kvstore_collections_global_records_to_be_restored,
                kvstore_collections_global_records_restored,
                kvstore_collection_restore_summary_dict,
            )

        describe = False

        # init
        dry_run = True

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:
                # The legacy 1.0.0/2.0.0 path requires `backup_archive`.
                # The 3.0.0 path (added 2.3.22) accepts either
                # `backup_archive` (single 3.0.0 archive) OR
                # `backup_run_id` (run-mode restore). Hold off on the
                # validation error until we've seen the full body — the
                # 3.0.0 dispatch below decides whether `backup_run_id` on
                # its own is sufficient.
                backup_archive = resp_dict.get("backup_archive")
                _has_run_id = bool(resp_dict.get("backup_run_id"))
                if not backup_archive and not _has_run_id:
                    response = {
                        "response": (
                            "The backup_archive name (or, for 3.0.0 "
                            "multi-archive runs, backup_run_id) is required "
                            "in the body of the request."
                        )
                    }
                    logger.error(json.dumps(response, indent=2))
                    return {"payload": response, "status": 500}

                # Dry run mode, preview and verify the restore operation, but do not do anything
                # default to True
                try:
                    dry_run = resp_dict["dry_run"]
                    if dry_run in ("True", "true", "1", 1):
                        dry_run = True
                    elif dry_run in ("False", "false", "0", 0):
                        dry_run = False
                    else:
                        return {
                            "payload": {
                                "response": f'Invalid value for dry_run, received="{dry_run}", expecting a boolean value or true / false'
                            },
                            "status": 500,
                        }

                except Exception as e:
                    dry_run = True

                #
                # restore_knowledge_objects (False/True)
                #

                try:
                    restore_knowledge_objects = resp_dict["restore_knowledge_objects"]
                    if restore_knowledge_objects in ("True", "true", "1", 1):
                        restore_knowledge_objects = True
                    else:
                        restore_knowledge_objects = False
                except Exception as e:
                    restore_knowledge_objects = True

                #
                # knowledge_objects_tenants_scope (all / comma separated list of tenant_id)
                #

                try:
                    knowledge_objects_tenants_scope = resp_dict[
                        "knowledge_objects_tenants_scope"
                    ]
                    if knowledge_objects_tenants_scope == "all":
                        knowledge_objects_tenants_scope = "all"
                    else:
                        if not isinstance(knowledge_objects_tenants_scope, list):
                            knowledge_objects_tenants_scope = (
                                knowledge_objects_tenants_scope.split(",")
                            )
                        # for each entry in the list, strip and remove any empty char before or after the list entry
                        knowledge_objects_tenants_scope = [
                            x.strip() for x in knowledge_objects_tenants_scope
                        ]
                except Exception as e:
                    knowledge_objects_tenants_scope = "all"

                #
                # knowledge_objects_lists (all / comma separated list of objects to be restored)
                #

                try:
                    knowledge_objects_lists = resp_dict["knowledge_objects_lists"]
                    if knowledge_objects_lists == "all":
                        knowledge_objects_lists = "all"
                    else:
                        if not isinstance(knowledge_objects_lists, list):
                            knowledge_objects_lists = knowledge_objects_lists.split(",")
                        # for each entry in the list, strip and remove any empty char before or after the list entry
                        knowledge_objects_lists = [
                            x.strip() for x in knowledge_objects_lists
                        ]
                except Exception as e:
                    knowledge_objects_lists = "all"

                #
                # knowledge_objects_replace_existing (False/True) - If the object already exists, it will be replaced
                #

                try:
                    knowledge_objects_replace_existing = resp_dict[
                        "knowledge_objects_replace_existing"
                    ]
                    if knowledge_objects_replace_existing in ("True", "true", "1", 1):
                        knowledge_objects_replace_existing = True
                    else:
                        knowledge_objects_replace_existing = False
                except Exception as e:
                    knowledge_objects_replace_existing = True

                #
                # restore_kvstore_collections (False/True)
                #

                try:
                    restore_kvstore_collections = resp_dict[
                        "restore_kvstore_collections"
                    ]
                    if restore_kvstore_collections in ("True", "true", "1", 1):
                        restore_kvstore_collections = True
                    else:
                        restore_kvstore_collections = False
                except Exception as e:
                    restore_kvstore_collections = True

                #
                # kvstore_collections_scope (all / comma separated list of KVstore collections)
                #

                try:
                    kvstore_collections_scope = resp_dict["kvstore_collections_scope"]
                    if kvstore_collections_scope == "all":
                        kvstore_collections_scope = "all"
                    else:
                        if not isinstance(kvstore_collections_scope, list):
                            kvstore_collections_scope = kvstore_collections_scope.split(
                                ","
                            )
                        # for each entry in the list, strip and remove any empty char before or after the list entry
                        kvstore_collections_scope = [
                            x.strip() for x in kvstore_collections_scope
                        ]
                except Exception as e:
                    kvstore_collections_scope = "all"

                #
                # kvstore_collections_clean_empty (False/True) - If the collection was empty in the backup, restoring will empty any existing record in the collection
                #

                try:
                    kvstore_collections_clean_empty = resp_dict[
                        "kvstore_collections_clean_empty"
                    ]
                    if kvstore_collections_clean_empty in ("True", "true", "1", 1):
                        kvstore_collections_clean_empty = True
                    else:
                        kvstore_collections_clean_empty = False
                except Exception as e:
                    kvstore_collections_clean_empty = True

                #
                # kvstore_collections_restore_non_tenants_collections (False/True) - Restore non-tenants collections
                #

                try:
                    kvstore_collections_restore_non_tenants_collections = resp_dict[
                        "kvstore_collections_restore_non_tenants_collections"
                    ]
                    if kvstore_collections_restore_non_tenants_collections in (
                        "True",
                        "true",
                        "1",
                        1,
                    ):
                        kvstore_collections_restore_non_tenants_collections = True
                    else:
                        kvstore_collections_restore_non_tenants_collections = False
                except Exception as e:
                    kvstore_collections_restore_non_tenants_collections = True

                #
                # restore_virtual_tenant_accounts (False/True) - Restore virtual tenant accounts
                #

                try:
                    restore_virtual_tenant_accounts = resp_dict[
                        "restore_virtual_tenant_accounts"
                    ]
                    if restore_virtual_tenant_accounts in ("True", "true", "1", 1):
                        restore_virtual_tenant_accounts = True
                    else:
                        restore_virtual_tenant_accounts = False

                except Exception as e:
                    restore_virtual_tenant_accounts = True

                #
                # restore_virtual_tenant_main_kvrecord (False/True) - Restore virtual tenant main record
                #

                try:
                    restore_virtual_tenant_main_kvrecord = resp_dict[
                        "restore_virtual_tenant_main_kvrecord"
                    ]
                    if restore_virtual_tenant_main_kvrecord in ("True", "true", "1", 1):
                        restore_virtual_tenant_main_kvrecord = True
                    else:
                        restore_virtual_tenant_main_kvrecord = False

                except Exception as e:
                    restore_virtual_tenant_main_kvrecord = True

                # ----------------------------------------------------------
                # `force_local` — recursive-delegation guard for SHC
                # cross-peer restores. When the dispatcher delegates to
                # the peer that owns the archive, it passes
                # force_local=true in the body so the receiving peer
                # restores locally instead of looking at server_name and
                # potentially re-delegating (which would loop forever
                # if the KV row's server_name doesn't normalise to the
                # peer's own hostname — e.g. KV stores FQDN but the
                # receiving peer reads socket.gethostname() as the short
                # name).
                try:
                    _force_local = resp_dict.get("force_local")
                    force_local = str(_force_local).lower() in ("true", "1", "yes")
                except Exception:
                    force_local = False

                # `async` — opt-in async dispatch for the 3.0.0 path.
                # When true, the handler spawns a background thread,
                # writes a job row to kv_trackme_backup_restore_jobs,
                # and returns immediately with
                # {"job_id", "status": "queued"}. The frontend polls
                # /restore_job_status to wait for completion — this is
                # the only way to avoid gateway-timeout 504s on
                # multi-GB restores that take minutes-to-hours.
                # Default false preserves the synchronous contract
                # every CLI / `| trackme` SPL caller relies on. Note:
                # the JSON body key is `async` even though it's a
                # Python reserved word — we read it via .get() rather
                # than as a Python identifier.
                try:
                    _async_flag = resp_dict.get("async")
                    async_flag = str(_async_flag).lower() in ("true", "1", "yes")
                except Exception:
                    async_flag = False

                # Blocklist parameters — parsed here (before the 3.0.0
                # dispatch) so both the legacy and 3.0.0 code paths see
                # them. The legacy path used to parse them later in the
                # `else:` block; that block is preserved for backward
                # compat (it overwrites these values), so legacy
                # behaviour is unchanged.
                # ----------------------------------------------------------
                try:
                    knowledge_objects_blocklist = resp_dict.get(
                        "knowledge_objects_blocklist", []
                    )
                    if isinstance(knowledge_objects_blocklist, str):
                        knowledge_objects_blocklist = [
                            x.strip()
                            for x in knowledge_objects_blocklist.split(",")
                            if x.strip()
                        ]
                    elif not isinstance(knowledge_objects_blocklist, list):
                        knowledge_objects_blocklist = []
                except Exception:
                    knowledge_objects_blocklist = []

                try:
                    kvstore_collections_blocklist = resp_dict.get(
                        "kvstore_collections_blocklist", []
                    )
                    if isinstance(kvstore_collections_blocklist, str):
                        kvstore_collections_blocklist = [
                            x.strip()
                            for x in kvstore_collections_blocklist.split(",")
                            if x.strip()
                        ]
                    elif not isinstance(kvstore_collections_blocklist, list):
                        kvstore_collections_blocklist = []
                except Exception:
                    kvstore_collections_blocklist = []

                # ----------------------------------------------------------
                # archives_scope (3.0.0 only) — per-archive selective
                # restore. Map of archive filename → {collections,
                # knowledge_objects}. When set for a given archive, takes
                # precedence over the flat kvstore_collections_scope /
                # knowledge_objects_lists for THAT archive only.
                # Archives absent from the map fall through to the flat
                # filter behaviour.
                #
                # Shape:
                #   {
                #     "<archive_filename>": {
                #       "collections": ["kv_trackme_..."] | "all",
                #       "knowledge_objects": ["title_a", ...] | "all",
                #     },
                #     ...
                #   }
                #
                # Use case: the operator wants to restore only one
                # specific KV collection from a tenant archive (the
                # majority recovery scenario per customer feedback) AND
                # one specific KV from the global archive in the same
                # run, without touching the rest. The flat filter alone
                # can't express this because it applies to every archive
                # uniformly, and KO titles can collide across tenants
                # (so a flat KO list is ambiguous in run mode).
                #
                # Parsing logic lives in trackme_libs_backup_archive.py
                # (`parse_archives_scope`) so it can be unit-tested
                # without importing the handler runtime — see
                # unit_tests/check_backup_archives_scope.py.
                # ----------------------------------------------------------
                try:
                    archives_scope = _bbk_parse_archives_scope(
                        resp_dict.get("archives_scope")
                    )
                except Exception:
                    archives_scope = {}

                # ----------------------------------------------------------
                # SHC cluster-KV completion-signalling: extract the
                # originating peer's async job_id (if any). Set only by
                # ``_v3_delegate_restore_to_peer`` when it issues the
                # delegated POST to this peer. Threaded through to
                # ``_handle_restore_3_0_0`` so this (receiving) peer
                # can write the terminal status to
                # ``kv_trackme_backup_restore_jobs`` directly when its
                # work completes — bypassing the synchronous HTTP
                # response chain that the originating peer's worker
                # is blocked on. See ``_handle_restore_3_0_0`` docstring
                # for the full rationale.
                # ----------------------------------------------------------
                _v3_origin_job_id_param = ""
                try:
                    raw = resp_dict.get("_v3_origin_job_id")
                    if raw is not None:
                        _v3_origin_job_id_param = str(raw).strip()
                except Exception:
                    _v3_origin_job_id_param = ""

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint can be used to restore TrackMe Knowledge Objects and/or KVstore collections from a backup archive, the archive must be a tarball compressed made available in the backup directory of the application. ($SPLUNK_HOME/etc/apps/trackme/backup) - Restore operations for both knowledge objects and KVstore records are fully based on Splunk API usage, therefore compatible indifferently with Splunk Enterprise and Splunk Cloud, in a standalone or Search Head Cluster context. As of release 2.3.22 the endpoint dispatches between two code paths based on the archive format: 3.0.0 multi-archive (per-tenant + global archives produced by post_backup since 2.3.22) is the modern path; pre-2.3.22 1.0.0/2.0.0 monolithic archives keep using the legacy path unchanged. Pass `backup_archive` with a 3.0.0 filename (e.g. `trackme-backup-<RUN_ID>-tenant-<tid>.tar.zst`) for a single-archive restore, or `backup_run_id` for a run-mode restore that iterates every archive in the run. It requires a POST call with the following arguments:",
                "resource_desc": "Restore TrackMe Knowledge Objects and/or KVstore collections from a backup archive",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/backup_and_restore/restore\" mode=\"post\" body=\"{'backup_archive': 'trackme-backup-20210205-142635.tgz', 'dry_run': 'false', 'target': 'all'}\"",
                "options": [
                    {
                        "dry_run": "(true / false) OPTIONAL: if true, the endpoint will only verify that the archive can be found and successfully extracted, there will be no modifications at all. (default to true)",
                        "backup_run_id": "(string) OPTIONAL (3.0.0 only): the backup_run_id of a multi-archive run to restore. When set, every archive belonging to that run (one per tenant + the global archive) is restored sequentially with per-archive isolation — a corrupt tenant archive does not block the others. Mutually exclusive with `backup_archive` for single-archive restore; if both are provided `backup_run_id` wins.",
                        "restore_virtual_tenant_accounts": "(true / false) OPTIONAL: check and restore the virtual tenant accounts from the submitted archive (default to true)",
                        "restore_virtual_tenant_main_kvrecord": "(true / false) OPTIONAL: check and restore the virtual tenant main record from the submitted archive (default to true)",
                        "restore_knowledge_objects": "(true / false) OPTIONAL: restore the knowledge objects from the submitted archive (default to true) - This requires a backup archive generated with TrackMe 2.1.5 or later",
                        "knowledge_objects_tenants_scope": "(all / comma separated list of tenant_id) OPTIONAL: restore the knowledge objects for all tenants or provide a comma separated list of tenant_id to be restored (defaults to all) - This requires a backup archive generated with TrackMe 2.1.5 or later",
                        "knowledge_objects_lists": "(all / comma separated list of objects to be restored) OPTIONAL: restore all knowledge objects that were backed up in the submitted archive, or provide a comma separated list of objects to be restored (defaults to all) - This requires a backup archive generated with TrackMe 2.1.5 or later",
                        "knowledge_objects_replace_existing": "(true / false) OPTIONAL: if the object already exists, it will be replaced (default to true) - This requires a backup archive generated with TrackMe 2.1.5 or later",
                        "restore_kvstore_collections": "(true / false) OPTIONAL: restore the KVstore collections from the submitted archive (default to true)",
                        "kvstore_collections_scope": "(all / comma separated list of KVstore collections) OPTIONAL: restore all collections that were backed up in the submitted archive, or provide a comma separated list of collections to be restored (defaults to all)",
                        "kvstore_collections_clean_empty": "(true / false) OPTIONAL: if the collection was empty in the backup, restoring will empty any existing record in the collection (default to true)",
                        "kvstore_collections_restore_non_tenants_collections": "(true / false) OPTIONAL: restore non-tenants collections (default to true), non tenants collections are KVstore collections which are tenant specific, such as user preferences, user settings, etc. If set to True, the content of the collection content will be restored from the backup.",
                        "backup_archive": "The archive file to be restored, the tarball compressed file must be located in the backup directory of the trackMe application.",
                        "knowledge_objects_blocklist": "(comma separated list or native list) OPTIONAL: list of knowledge objects that should not be restored",
                        "kvstore_collections_blocklist": "(comma separated list or native list) OPTIONAL: list of KVstore collections that should not be restored",
                        "archives_scope": "(dict) OPTIONAL (3.0.0 only): per-archive selective restore. Map of archive filename → {\"collections\": [list of collection names] | \"all\", \"knowledge_objects\": [list of KO titles] | \"all\"}. When set for a given archive, takes precedence over the flat kvstore_collections_scope / knowledge_objects_lists for THAT archive only. Archives absent from the map fall through to the flat-filter behaviour. Use this to restore one specific KV collection from one tenant archive plus one specific KV from the global archive in the same run, without touching the rest. CLI / SPL callers can use either the flat filters (today's behaviour) or this richer map. Example: {\"trackme-backup-<RUN_ID>-tenant-<tid>.tar.zst\": {\"collections\": [\"kv_trackme_dsm_priority_tenant_<tid>\"], \"knowledge_objects\": \"all\"}}",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        else:
            # ----------------------------------------------------------------
            # 3.0.0 dispatch — added in 2.3.22.
            #
            # Detect whether the request targets a 3.0.0 multi-archive
            # backup (produced by post_backup since 2.3.22) and route to
            # the new code path. Otherwise fall through to the legacy
            # 1.0.0/2.0.0 logic below — those archives are still
            # restorable indefinitely; the legacy code path is frozen and
            # untouched on this PR.
            #
            # The dispatch is body-driven:
            #   - `backup_run_id` set            → run-mode restore (3.0.0)
            #   - `backup_archive` is 3.0.0 name → single-archive (3.0.0)
            #   - `backup_archive` is legacy     → fall through to legacy
            # ----------------------------------------------------------------
            backup_run_id_param = None
            try:
                backup_run_id_param = resp_dict.get("backup_run_id") if resp_dict else None
            except Exception:
                backup_run_id_param = None

            wants_3_0_0 = bool(backup_run_id_param) or (
                backup_archive
                and is_new_archive_name(os.path.basename(str(backup_archive)))
            )

            if wants_3_0_0:
                logger.info(
                    f'TrackMe restore — dispatching to 3.0.0 path '
                    f'(backup_run_id="{backup_run_id_param}", '
                    f'backup_archive="{backup_archive}", dry_run={dry_run}, '
                    f'async={async_flag})'
                )
                # Bundle the body params so both the sync and async
                # paths take the same shape — async dispatch hands this
                # to the background worker, sync dispatch unpacks it
                # into the existing _handle_restore_3_0_0 signature.
                body_params = {
                    "backup_archive": backup_archive,
                    "backup_run_id": backup_run_id_param,
                    "dry_run": dry_run,
                    "force_local": force_local,
                    "restore_kvstore_collections": restore_kvstore_collections,
                    "kvstore_collections_scope": kvstore_collections_scope,
                    "kvstore_collections_clean_empty": kvstore_collections_clean_empty,
                    "kvstore_collections_blocklist": kvstore_collections_blocklist,
                    "kvstore_collections_restore_non_tenants_collections": (
                        kvstore_collections_restore_non_tenants_collections
                    ),
                    "restore_knowledge_objects": restore_knowledge_objects,
                    "knowledge_objects_replace_existing": knowledge_objects_replace_existing,
                    "knowledge_objects_lists": knowledge_objects_lists,
                    "knowledge_objects_blocklist": knowledge_objects_blocklist,
                    "restore_virtual_tenant_accounts": restore_virtual_tenant_accounts,
                    "restore_virtual_tenant_main_kvrecord": restore_virtual_tenant_main_kvrecord,
                    # Per-archive selective restore overrides (3.0.0).
                    # Empty dict means "no overrides" — flat filters apply.
                    "archives_scope": archives_scope,
                }

                # Async dispatch — even a dry-run might choose async if
                # the run is large, but in practice dry-runs are fast
                # (manifest read only). We honour async_flag uniformly
                # so the frontend can treat both consistently.
                if async_flag:
                    return self._dispatch_restore_async(
                        request_info, body_params,
                    )

                return self._handle_restore_3_0_0(
                    request_info=request_info,
                    backup_archive=backup_archive,
                    backup_run_id=backup_run_id_param,
                    dry_run=dry_run,
                    force_local=force_local,
                    restore_kvstore_collections=restore_kvstore_collections,
                    kvstore_collections_scope=kvstore_collections_scope,
                    kvstore_collections_clean_empty=kvstore_collections_clean_empty,
                    kvstore_collections_blocklist=kvstore_collections_blocklist,
                    kvstore_collections_restore_non_tenants_collections=(
                        kvstore_collections_restore_non_tenants_collections
                    ),
                    restore_knowledge_objects=restore_knowledge_objects,
                    knowledge_objects_replace_existing=knowledge_objects_replace_existing,
                    knowledge_objects_lists=knowledge_objects_lists,
                    knowledge_objects_blocklist=knowledge_objects_blocklist,
                    restore_virtual_tenant_accounts=restore_virtual_tenant_accounts,
                    restore_virtual_tenant_main_kvrecord=restore_virtual_tenant_main_kvrecord,
                    archives_scope=archives_scope,
                    # SHC cluster-KV completion signalling — empty string
                    # for non-delegated calls; non-empty when this peer
                    # received the call via _v3_delegate_restore_to_peer.
                    _v3_origin_job_id=_v3_origin_job_id_param,
                )

            # ----------------------------------------------------------------
            # Legacy 1.0.0 / 2.0.0 code path — UNCHANGED.
            # Kept for restoring archives produced before 2.3.22. Customers
            # may pull such an archive off cold storage years from now; the
            # path must not bit-rot. See plan §"Retro-compatibility".
            # ----------------------------------------------------------------

            # Get splunkd port
            splunkd_port = request_info.server_rest_port

            # Get service
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            # header
            header = {
                "Authorization": "Splunk %s" % request_info.session_key,
                "Content-Type": "application/json",
            }

            # set loglevel
            loglevel = trackme_getloglevel(
                request_info.system_authtoken, request_info.server_rest_port
            )
            logger.setLevel(loglevel)

            # Set backup root dir
            backuproot = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")

            # Set the submitted full path of the archive file
            backupfile = os.path.join(backuproot, backup_archive)

            # Set the full path of the directory for the extraction
            backupdir = os.path.splitext(backupfile)[0]

            # A dict for kvstore records summary
            kvstore_collections_restore_summary_dict = {}

            #
            # knowledge_objects_blocklist (comma separated list or native list)
            #

            try:
                knowledge_objects_blocklist = resp_dict["knowledge_objects_blocklist"]
                if not isinstance(knowledge_objects_blocklist, list):
                    knowledge_objects_blocklist = knowledge_objects_blocklist.split(",")
                # for each entry in the list, strip and remove any empty char before or after the list entry
                knowledge_objects_blocklist = [
                    x.strip() for x in knowledge_objects_blocklist
                ]
            except Exception as e:
                knowledge_objects_blocklist = []

            #
            # kvstore_collections_blocklist (comma separated list or native list)
            #

            try:
                kvstore_collections_blocklist = resp_dict[
                    "kvstore_collections_blocklist"
                ]
                if not isinstance(kvstore_collections_blocklist, list):
                    kvstore_collections_blocklist = kvstore_collections_blocklist.split(
                        ","
                    )
                # for each entry in the list, strip and remove any empty char before or after the list entry
                kvstore_collections_blocklist = [
                    x.strip() for x in kvstore_collections_blocklist
                ]
            except Exception as e:
                kvstore_collections_blocklist = []

            #################
            # Task: log start
            #################

            logger.info(
                f'TrackMe restore process is starting requested by user="{request_info.user}", request="{json.dumps(resp_dict, indent=3)}"'
            )

            # log the value for each argument
            logger.info(
                f"TrackMe restore process, listing arguments summary, "
                f'backup_archive="{backup_archive}", dry_run="{dry_run}", '
                f'restore_virtual_tenant_accounts="{restore_virtual_tenant_accounts}", '
                f'restore_virtual_tenant_main_kvrecord="{restore_virtual_tenant_main_kvrecord}", '
                f'restore_knowledge_objects="{restore_knowledge_objects}", '
                f'knowledge_objects_tenants_scope="{knowledge_objects_tenants_scope}", knowledge_objects_lists="{knowledge_objects_lists}", '
                f'knowledge_objects_replace_existing="{knowledge_objects_replace_existing}", restore_kvstore_collections="{restore_kvstore_collections}", '
                f'kvstore_collections_scope="{kvstore_collections_scope}", kvstore_collections_clean_empty="{kvstore_collections_clean_empty}", '
                f'kvstore_collections_restore_non_tenants_collections="{kvstore_collections_restore_non_tenants_collections}", '
                f'knowledge_objects_blocklist="{knowledge_objects_blocklist}", kvstore_collections_blocklist="{kvstore_collections_blocklist}"'
            )

            ################################################
            # Task: Identify if archive is available locally
            ################################################

            # Assume False
            archive_exists_locally = False

            if os.path.isfile(backupfile):
                archive_exists_locally = True

            if not archive_exists_locally:

                #
                # Export
                #

                # check if we have a KVstore record for this backup archive
                collection_name = "kv_trackme_backup_archives_info"
                collection = service.kvstore[collection_name]

                query_string = {"backup_archive": {"$regex": f".*{backup_archive}$"}}

                try:
                    kvrecords = collection.data.query(query=json.dumps(query_string))
                    kvrecord = kvrecords[0]
                except Exception as e:
                    kvrecords = []
                    kvrecord = None

                # if we do not have a KVrecord, stop and raise a failure, the user needs to export/import the backup archive manually
                if not kvrecord:
                    response = {
                        "response": f"The archive name {backup_archive} could not be found in the KVstore, restore cannot be processed. You can manually export/import the backup archive through the user interface.",
                    }
                    logger.error(json.dumps(response, indent=2))
                    return {"payload": response, "status": 500}

                #
                # remote host handling
                #

                backup_server_name = kvrecord.get("server_name")

                # Query the KVstore collection to get the server_name for this backup archive
                logger.info(
                    f"Backup archive is on different server ({backup_server_name}), delegating export to target server"
                )

                # Determine the best target server name for communication by testing connectivity
                target_server_name = backup_server_name

                # Test connectivity with short hostname first, then FQDN if needed
                logger.info(
                    f"Testing connectivity with short hostname: {backup_server_name}"
                )
                if not test_splunkd_connectivity(
                    backup_server_name,
                    request_info.server_rest_port,
                    request_info.session_key,
                ):
                    # FQDN-suffix fallback. Skip the suffix-append entirely
                    # when ``backup_server_name`` is already an FQDN (contains
                    # a dot) — post-PR-#1568 KV rows store FQDN-form
                    # ``server_name``, so the naive ``f"{X}.{suffix}"`` would
                    # produce a double-suffixed target like
                    # ``host.domain.com.domain.com`` that will never resolve.
                    # Mirrors the canonical fix at
                    # ``_v3_delegate_restore_to_peer`` (PR #1627, bugbot ID
                    # cf36f216).
                    backup_server_fqdn = None
                    if "." not in backup_server_name:
                        local_fqdn = socket.getfqdn()
                        fqdn_suffix = (
                            local_fqdn.split(".", 1)[1]
                            if "." in local_fqdn
                            else "local"
                        )
                        backup_server_fqdn = f"{backup_server_name}.{fqdn_suffix}"
                    if backup_server_fqdn:
                        logger.info(
                            f"Short hostname failed, trying FQDN: {backup_server_fqdn}"
                        )
                    if backup_server_fqdn and test_splunkd_connectivity(
                        backup_server_fqdn,
                        request_info.server_rest_port,
                        request_info.session_key,
                    ):
                        target_server_name = backup_server_fqdn
                        logger.info(
                            f"FQDN connectivity successful, using: {target_server_name}"
                        )
                    else:
                        # Branch-aware warning reflects whether the FQDN-
                        # suffix fallback ran or was skipped.
                        if backup_server_fqdn:
                            warn_detail = (
                                f"short ({backup_server_name!r}) and "
                                f"FQDN-suffix fallback "
                                f"({backup_server_fqdn!r}) both failed"
                            )
                        else:
                            warn_detail = (
                                f"FQDN form ({backup_server_name!r}) failed; "
                                f"no short->FQDN fallback applicable"
                            )
                        logger.warning(
                            f"Connectivity failed for {backup_server_name} "
                            f"({warn_detail})"
                        )
                else:
                    logger.info(
                        f"Short hostname connectivity successful, using: {target_server_name}"
                    )

                # support only https
                target_server_uri = (
                    f"https://{target_server_name}:{request_info.server_rest_port}"
                )

                # Make REST call to target server
                headers = {
                    "Authorization": f"Splunk {request_info.session_key}",
                    "Content-Type": "application/json",
                }

                # Prepare the request payload
                # Explicitly set binary_mode=False for server-to-server transfers to ensure
                # we get direct base64 data (not a token) for import
                request_payload = {
                    "archive_name": backup_archive,
                    "force_local": True,
                    "binary_mode": False,
                }

                target_url = f"{target_server_uri}/services/trackme/v2/backup_and_restore/export_backup"

                logger.info(f"Making REST call to target server: {target_url}")

                try:
                    response = requests.post(
                        target_url,
                        headers=headers,
                        data=json.dumps(request_payload),
                        verify=False,
                        timeout=600,
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        logger.info(
                            f"Successfully exported backup from target server {backup_server_name}"
                        )
                        # Check if we got a download_token (binary_mode=True) or archive_base64
                        download_token = response_data.get("download_token")
                        base64_data = response_data.get("archive_base64")
                        
                        # Validate that we have base64_data
                        if not base64_data:
                            if download_token:
                                error_msg = f"Remote server returned download_token instead of archive_base64. Server-to-server restore requires direct base64 data. Please ensure binary_mode=False is used for restore operations."
                            else:
                                error_msg = f"Remote server response missing archive_base64 field. Response keys: {list(response_data.keys())}"
                            logger.error(error_msg)
                            return {
                                "payload": {
                                    "error": error_msg
                                },
                                "status": 500,
                            }

                    else:
                        logger.error(
                            f"Target server {backup_server_name} returned error: {response.status_code} - {response.text}, url={target_url}, request_payload={json.dumps(request_payload)}"
                        )
                        return {
                            "payload": {
                                "error": f"Failed to export from target server {backup_server_name}: {response.text}, url={target_url}, request_payload={json.dumps(request_payload)}"
                            },
                            "status": response.status_code,
                        }

                except requests.exceptions.ConnectionError as e:
                    logger.error(
                        f"Connection error to target server {backup_server_name}: {str(e)}"
                    )
                    return {
                        "payload": {
                            "error": f"Failed to connect to target server {backup_server_name}. Please ensure the server is reachable and TrackMe is installed."
                        },
                        "status": 500,
                    }
                except Exception as e:
                    logger.error(
                        f"Error making REST call to target server {backup_server_name}: {str(e)}, url={target_url}, request_payload={json.dumps(request_payload)}"
                    )
                    return {
                        "payload": {
                            "error": f"Failed to export from target server {backup_server_name}: {str(e)}, url={target_url}, request_payload={json.dumps(request_payload)}"
                        },
                        "status": 500,
                    }

                #
                # Import
                #

                # url
                url = f"{request_info.server_rest_uri}/services/trackme/v2/backup_and_restore/import_backup"
                header = {
                    "Authorization": "Splunk %s" % request_info.session_key,
                    "Content-Type": "application/json",
                }
                
                try:
                    response = requests.post(
                        url,
                        headers=header,
                        json={"archive_base64": base64_data},
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code != 200:
                        response = {
                            "response": f"The archive name {backup_archive} could not be imported, restore cannot be processed. You can manually import the backup archive through the user interface.",
                        }
                        logger.error(json.dumps(response, indent=2))
                        return {"payload": response, "status": 500}
                    else:
                        # Archive is now imported and extracted, mark as available locally
                        archive_exists_locally = True
                        logger.info(f"Successfully imported archive {backup_archive} from remote server")
                except Exception as e:
                    response = {
                        "response": f"The archive name {backup_archive} could not be imported, restore cannot be processed. You can manually import the backup archive through the user interface.",
                    }
                    logger.error(json.dumps(response, indent=2))
                    return {"payload": response, "status": 500}

                 # The archive is now imported and available locally, we simply can continue with the local restore process

            ##########################
            # Task: Archive Extraction
            ##########################

            # First, check the backup archive existence (skip if already imported from remote)
            if not archive_exists_locally and not os.path.isfile(backupfile):
                response = {
                    "response": f"The archive name {backupfile} could not be found on the file-system, restore cannot be processed",
                }
                logger.error(json.dumps(response, indent=2))
                return {"payload": response, "status": 500}

            # Attempt extraction using the extract_archive function that supports both .tgz and .tar.zst
            if not extract_archive(backupfile, backupdir):
                response = {
                    "response": f"The archive name {backupfile} could not be extracted, restore cannot be processed, exception='file could not be opened successfully'",
                }
                logger.error(json.dumps(response, indent=2))
                return {"payload": response, "status": 500}

            ######################
            # Task: Check metadata
            ######################

            # default to 2.0.0 (metadata compatibility, generated with TrackMe >= 2.1.5)
            archive_schema_version = "2.0.0"

            # check metadata files
            full_metadata_file = f"{backupfile}.full.meta"
            light_metadata_file = f"{backupfile}.light.meta"

            # From TrackMe 2.1.5, we generate a metadata file named as <tarfile>.full.meta and <tarfile>.light.meta
            # Check if the metadata file exists
            backup_file_has_metadata = False

            # check for both metadata files

            if os.path.isfile(full_metadata_file) and os.path.isfile(
                light_metadata_file
            ):

                backup_file_has_metadata = True

                # full metadata
                try:
                    with open(f"{backupfile}.full.meta", "r") as read_content:
                        full_metadata = json.load(read_content)
                except Exception as e:
                    full_metadata = None
                    backup_file_has_metadata = False
                    logger.error(
                        f'failed to load the full metadata file="{backupfile}.full.meta" with exception="{str(e)}"'
                    )

                # light metadata
                try:
                    with open(f"{backupfile}.light.meta", "r") as read_content:
                        light_metadata = json.load(read_content)
                except Exception as e:
                    light_metadata = None
                    backup_file_has_metadata = False
                    logger.error(
                        f'failed to load the light metadata file="{backupfile}.light.meta" with exception="{str(e)}"'
                    )

                # if we do not have full metadata or light metadata, the archive schema version is 1.0.0 (Only KVstore collections can be restored)
                if not full_metadata or not light_metadata:
                    archive_schema_version = "1.0.0"

            ############################################
            # Task: Parse restorable KVstore collections
            ############################################

            # store the list of KVstore collection json files in a list
            collections_json_files = [
                f
                for f in listdir(backupdir)
                if isfile(join(backupdir, f)) and f.startswith("kv_")
            ]

            # store the list of available collections in the archive
            collections_available = []

            # create a dictionary
            collections_restore_dict = {}
            for json_file in collections_json_files:
                # strip the extension
                collection_name = os.path.splitext(json_file)[0]

                # append to the list of available collections for restore
                collections_available.append(collection_name)

                # get the file size
                json_file_size = os.path.getsize(os.path.join(backupdir, json_file))

                # get the file mtime
                json_file_mtime = round(
                    os.path.getmtime(os.path.join(backupdir, json_file))
                )

                # try getting the number of records
                try:
                    with open(os.path.join(backupdir, json_file), "r") as read_content:
                        json_file_records = len(json.load(read_content))
                except Exception as e:
                    json_file_records = None

                # add to the dict
                is_empty = False
                if json_file_records == 0:
                    is_empty = True

                collections_restore_dict[collection_name] = {
                    "file": json_file,
                    "size": json_file_size,
                    "mtime": json_file_mtime,
                    "records": json_file_records,
                    "is_empty": is_empty,
                }

            ##############
            # dry_run mode
            ##############

            # if dry run
            if dry_run:

                # init dry_run response
                dry_run_response = {}

                # add response
                response_message = f"Success, the archive {backupfile} could be successfully extracted, consult metadata information added to this response for more insights. You can run this command with dry_run=false to perform the restoration."
                dry_run_response["response"] = response_message

                # if metadata files are available, add the light_metadata as metadata
                if backup_file_has_metadata:
                    dry_run_response["knowledge_objects_summary"] = light_metadata.get(
                        "knowledge_objects_summary"
                    )
                    dry_run_response["metadata"] = light_metadata

                # add collections
                dry_run_response["kvstore_collections_json_files"] = (
                    collections_json_files
                )
                dry_run_response["kvstore_collections_details"] = (
                    collections_restore_dict
                )
                # Provide a simplified summary: collection -> size (bytes)
                dry_run_response["kvstore_collections_size"] = {
                    k: v.get("size", 0) for k, v in collections_restore_dict.items()
                }

                # iterate through knowledge objects files and add to the response_message, as well as the virtual tenant account
                knowledge_objects_json_files = [
                    f
                    for f in listdir(backupdir)
                    if isfile(join(backupdir, f))
                    and f.startswith("tenant_")
                    and f.endswith("_knowledge_objects.json")
                ]

                for knowledge_objects_json_file in knowledge_objects_json_files:

                    # extract the tenant_id
                    tenant_id = knowledge_objects_json_file.split("_")[1]

                    if (
                        knowledge_objects_tenants_scope == "all"
                        or tenant_id in knowledge_objects_tenants_scope
                    ):

                        # open and load the json file
                        try:
                            with open(
                                os.path.join(backupdir, knowledge_objects_json_file),
                                "r",
                            ) as read_content:
                                knowledge_objects_json = json.load(read_content)
                        except Exception as e:
                            clean_backup_dir(backupdir)
                            knowledge_objects_json = None
                            logger.error(
                                f'failed to load the knowledge_objects_json file="{knowledge_objects_json_file}" with exception="{str(e)}"'
                            )

                        # iterate through the knowledge objects lists, add each category of objects to the response
                        # categories: savedsearches, alerts, macros, lookup_definitions, kvstore_collections
                        savedsearches_list = []
                        alerts_list = []
                        macros_list = []
                        lookup_definitions_list = []
                        kvstore_collections_list = []

                        # Iterate through the values of the dictionary
                        for ko in knowledge_objects_json.values():
                            type_ko = ko.get("type")
                            if type_ko == "savedsearches":
                                savedsearches_list.append(ko)
                            elif type_ko == "alerts":
                                alerts_list.append(ko)
                            elif type_ko == "macros":
                                macros_list.append(ko)
                            elif type_ko == "lookup_definitions":
                                lookup_definitions_list.append(ko)
                            elif type_ko == "kvstore_collections":
                                kvstore_collections_list.append(ko)

                        # Add to the response
                        dry_run_response[f"tenant_{tenant_id}_knowledge_objects"] = {
                            "savedsearches": savedsearches_list,
                            "alerts": alerts_list,
                            "macros": macros_list,
                            "lookup_definitions": lookup_definitions_list,
                            "kvstore_collections": kvstore_collections_list,
                        }

                        # check that the virtual account backup file exists, if not log and skip
                        tenant_json_file = f"tenant_{tenant_id}_vtenant_account.json"

                        if not os.path.isfile(
                            os.path.join(backupdir, tenant_json_file)
                        ):
                            clean_backup_dir(backupdir)
                            error_message = f'failed to find the backup file="{tenant_json_file}" for tenant_id="{tenant_id}", the tenant cannot be restored'
                            logger.error(error_message)
                            return {
                                "payload": {
                                    "response": error_message,
                                },
                                "status": 500,
                            }

                        # load the tenant json file
                        try:
                            f = open(os.path.join(backupdir, tenant_json_file), "r")
                            vtenant_account_data = json.loads(f.read())
                            info_message = f'loaded the tenant backup file="{tenant_json_file}" for tenant_id="{tenant_id}"'
                            logger.info(info_message)

                        except Exception as e:
                            clean_backup_dir(backupdir)
                            error_message = f'failed to open json file="{os.path.join(backupdir, tenant_json_file)}" for reading with exception="{str(e)}", cannot restore tenant_id="{tenant_id}"'
                            logger.error(error_message)
                            return {
                                "payload": {
                                    "response": error_message,
                                },
                                "status": 500,
                            }

                        # add to the response
                        dry_run_response[f"tenant_{tenant_id}_vtenant_account"] = (
                            vtenant_account_data
                        )

                # log and render

                # remove backup dir
                clean_backup_dir(backupdir)
                logger.info(response_message)
                return {"payload": dry_run_response, "status": 200}

            else:

                ###################
                # Live restore mode
                ###################

                # create a dict to store the restore results
                restore_results_dict = {}

                # create global counters
                kvstore_collections_global_records_to_be_restored = 0
                kvstore_collections_global_records_restored = 0

                # store collections with failures in a specific list
                kvstore_collections_restored_warning = []

                # Things are serious now, let's restore collection per collection

                # set the list of collections to be restored
                kvstore_collections_to_be_restored = []

                # set the list of collections that were restored
                kvstore_collections_restored = []

                # if kvstore_collections_scope is all, add every collection that can be restored
                if kvstore_collections_scope == "all":
                    # Loop through the collections
                    for collection_name in collections_restore_dict:
                        # Skip stateful charts collections as they are excluded from backups
                        if collection_name.startswith(
                            "kv_trackme_stateful_alerting_charts_tenant_"
                        ):
                            info_msg = f'TrackMe restore kvstore collections process, skipping stateful charts collection="{collection_name}" on purpose. Stateful charts collections are excluded from backups and restores.'
                            logger.info(info_msg)
                            continue
                        # Only add if not in blocklist
                        if collection_name not in kvstore_collections_blocklist:
                            kvstore_collections_to_be_restored.append(collection_name)

                else:
                    # Loop and check if the requested collection is available for restore and not in blocklist
                    for collection_name in kvstore_collections_scope:
                        # Skip stateful charts collections as they are excluded from backups
                        if collection_name.startswith(
                            "kv_trackme_stateful_alerting_charts_tenant_"
                        ):
                            info_msg = f'TrackMe restore kvstore collections process, skipping stateful charts collection="{collection_name}" on purpose. Stateful charts collections are excluded from backups and restores.'
                            logger.info(info_msg)
                            continue

                        if not collection_name in collections_available:
                            # an impossible operation is requested, we cannot proceed
                            response = {
                                "action": "failure",
                                "response": f'the collection="{collection_name}" requested for restoration is not available in the backup archive file, restore cannot be procceded',
                                "collections_available": collections_available,
                            }

                            return {"payload": response, "status": 500}

                        elif collection_name not in kvstore_collections_blocklist:
                            kvstore_collections_to_be_restored.append(collection_name)

                #########
                # Proceed
                #########

                # init final response_dict
                response_dict = {}

                # init tasks list
                tasks_list = []

                # init errors list
                errors_list = []

                #####################################
                # Task: Restore the Knowledge Objects
                #####################################

                if archive_schema_version == "2.0.0" and restore_knowledge_objects:
                    logger.info(
                        f'Detected archive_schema_version="{archive_schema_version}", Processing restore operations of Knowledge Objects'
                    )

                    # Helper: resolve owner to an existing local user or fallback to "nobody"
                    def _resolve_owner(target_owner):
                        try:
                            if not target_owner or str(target_owner).lower() == "nobody":
                                return "nobody"
                            # service is available in this scope; verify user exists
                            _ = service.users[str(target_owner)]
                            return str(target_owner)
                        except Exception:
                            logger.warning(
                                f'Owner "{target_owner}" not found on target system, falling back to "nobody"'
                            )
                            return "nobody"

                    # knowledge_objects_json_files: list of json files in the backup archive
                    # each file is named as:
                    # tenant_<tenant_id>_knowledge_objects.json

                    tenants_id_restorable = []
                    tenants_id_available = []

                    knowledge_objects_json_files = [
                        f
                        for f in listdir(backupdir)
                        if isfile(join(backupdir, f))
                        and f.startswith("tenant_")
                        and f.endswith("_knowledge_objects.json")
                    ]

                    for knowledge_objects_json_file in knowledge_objects_json_files:
                        # extract the tenant_id
                        tenant_id = knowledge_objects_json_file.split("_")[1]

                        # add to available
                        tenants_id_available.append(tenant_id)

                        if knowledge_objects_tenants_scope == "all":
                            tenants_id_restorable.append(tenant_id)
                        else:
                            if tenant_id in knowledge_objects_tenants_scope:
                                tenants_id_restorable.append(tenant_id)

                    # if a specific tenant_id was requested, but not found in the backup archive, stop and return an error
                    if knowledge_objects_tenants_scope != "all":
                        for tenant_id in knowledge_objects_tenants_scope:
                            if tenant_id not in tenants_id_restorable:
                                error_message = f'failed to find the backup file for tenant_id="{tenant_id}", the tenant cannot be restored, verify that your input is valid.'
                                logger.error(error_message)
                                return {
                                    "payload": {
                                        "response": error_message,
                                        "tenants_id_available": tenants_id_available,
                                    },
                                    "status": 500,
                                }
                            # only keep in tenants_id_restorable the list of tenants provided in knowledge_objects_tenants_scope
                            tenants_id_restorable = [
                                tenant_id
                                for tenant_id in tenants_id_restorable
                                if tenant_id in knowledge_objects_tenants_scope
                            ]

                    ###############################################
                    # subtask: load the central KVstore from backup
                    ###############################################

                    collection_name_main = "kv_trackme_virtual_tenants"

                    # connect to live KVstore collection
                    try:
                        collection = service.kvstore[collection_name_main]
                    except Exception as e:
                        error_message = f'failed to connect to KVstore collection="{collection_name_main}" with exception="{str(e)}"'
                        logger.error(error_message)
                        return {
                            "payload": {
                                "response": error_message,
                            },
                            "status": 500,
                        }

                    # backup file name
                    source_json_file = collections_restore_dict[collection_name_main][
                        "file"
                    ]

                    # try loading the json data
                    try:
                        f = open(os.path.join(backupdir, source_json_file), "r")
                        vtenants_main_records = json.loads(f.read())

                    except Exception as e:
                        error_message = f'failed to open json file="{os.path.join(backupdir, source_json_file)}" for reading with exception="{str(e)}"'
                        logger.error(error_message)
                        return {
                            "payload": {
                                "response": error_message,
                            },
                            "status": 500,
                        }

                    ###################################################
                    # subtask: restore per tenant the knowledge objects
                    ###################################################

                    # Loop through the restorable tenants, and proceed
                    for tenant_id in tenants_id_restorable:
                        logger.info(
                            f'Processing with restore operations for tenant_id="{tenant_id}"'
                        )

                        #############################################
                        # subtask: restore the Virtual Tenant account
                        #############################################

                        # check that the virtual account backup file exists, if not log and skip
                        tenant_json_file = f"tenant_{tenant_id}_vtenant_account.json"

                        if not os.path.isfile(
                            os.path.join(backupdir, tenant_json_file)
                        ):
                            error_message = f'failed to find the backup file="{tenant_json_file}" for tenant_id="{tenant_id}", the tenant cannot be restored'
                            logger.error(error_message)
                            errors_list.append(error_message)
                            break

                        # load the tenant json file
                        try:
                            f = open(os.path.join(backupdir, tenant_json_file), "r")
                            data = json.loads(f.read())
                            info_message = f'loaded the tenant backup file="{tenant_json_file}" for tenant_id="{tenant_id}"'
                            logger.info(info_message)
                            tasks_list.append(info_message)

                        except Exception as e:
                            error_message = f'failed to open json file="{os.path.join(backupdir, tenant_json_file)}" for reading with exception="{str(e)}", cannot restore tenant_id="{tenant_id}"'
                            logger.error(error_message)
                            errors_list.append(error_message)
                            break

                        #
                        # Proceed
                        #

                        if not restore_virtual_tenant_accounts:
                            info_message = f'restore_virtual_tenant_accounts is set to False, the Virtual Tenant account for tenant_id="{tenant_id}" will not be restored'
                            logger.info(info_message)
                            tasks_list.append(info_message)

                        else:

                            # If the Virtual Account exists, it must be deleted to be restored

                            # Del the vtenant account
                            url = "%s/servicesNS/nobody/trackme/trackme_vtenants/%s" % (
                                request_info.server_rest_uri,
                                tenant_id,
                            )

                            # Retrieve and set the tenant idx, if any failure, logs and use the global index
                            try:
                                response = requests.delete(
                                    url, headers=header, verify=False, timeout=600
                                )
                                if response.status_code not in (200, 201, 204):
                                    # this can be expected if the tenant does not exist, do not consider this as an error
                                    info_message = f'tenant_id="{tenant_id}", delete vtenant account was not required, response.status_code="{response.status_code}"'
                                    logger.info(info_message)
                                    tasks_list.append(info_message)
                                else:
                                    info_message = f'deleted the Virtual Tenant account for tenant_id="{tenant_id}"'
                                    logger.info(info_message)
                                    tasks_list.append(info_message)
                            except Exception as e:
                                # this is an error
                                error_message = f'failed to delete the Virtual Tenant account for tenant_id="{tenant_id}" with exception="{str(e)}"'
                                logger.error(error_message)
                                errors_list.append(error_message)

                            # Remove keys that start with "eai:"
                            keys_to_remove = [
                                k for k in data.keys() if k.startswith("eai:")
                            ]
                            for k in keys_to_remove:
                                del data[k]

                            # also remove disabled
                            if "disabled" in data:
                                del data["disabled"]

                            # in data, add the key name equal to the tenant_id
                            data["name"] = tenant_id

                            # for key value in vtenant_account_default, check if a key is missing from vtenant_data, if so, add it
                            for key, value in vtenant_account_default.items():
                                if key not in data:
                                    data[key] = value

                            # for key value in vetant_data, if the value is null, empty or None, take the value from vtenant_account_default
                            for key, value in data.items():
                                if value is None:
                                    data[key] = vtenant_account_default.get(key)
                                elif isinstance(value, str) and value == "":
                                    data[key] = vtenant_account_default.get(key)

                            # set vtenant_data as any key that is in data and as well listed in default keys from vtenant_account_default
                            vtenant_data = {
                                key: value
                                for key, value in data.items()
                                if key in vtenant_account_default
                            }
                            # ensure stanza name is provided for creation
                            vtenant_data["name"] = tenant_id

                            #
                            # force attempt a delete and ignore errors
                            #

                            # set the url
                            url = "%s/servicesNS/nobody/trackme/trackme_vtenants/%s" % (
                                request_info.server_rest_uri,
                                tenant_id,
                            )

                            # Retrieve and set the tenant idx, if any failure, logs and use the global index
                            try:
                                response = requests.delete(
                                    url, headers=header, verify=False, timeout=600
                                )
                                if response.status_code not in (200, 201, 204):
                                    logger.warning(
                                        f'delete vtenant account has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                                    )
                                else:
                                    logger.info(
                                        f'delete vtenant account was operated successfully, response.status_code="{response.status_code}"'
                                    )
                            except Exception as e:
                                logger.warning(f'delete vtenant account has failed, exception="{str(e)}"')

                            #
                            # attempt to create the Virtual Tenant account, but don't stop in case of error
                            #

                            # Add the vtenant account
                            url = "%s/servicesNS/nobody/trackme/trackme_vtenants" % (
                                request_info.server_rest_uri
                            )

                            # Run the POST call
                            try:

                                response = requests.post(
                                    url,
                                    headers=header,
                                    data=vtenant_data,
                                    verify=False,
                                    timeout=600,
                                )
                                response.raise_for_status()
                                info_message = f'added the Virtual Tenant account for tenant_id="{tenant_id}"'
                                logger.info(info_message)
                                tasks_list.append(info_message)

                            except Exception as e:
                                error_message = f'failed to add the Virtual Tenant account for tenant_id="{tenant_id}" with exception="{str(e)}", vtenant_data="{json.dumps(vtenant_data, indent=2)}"'
                                logger.error(error_message)
                                errors_list.append(error_message)

                        #####################################################
                        # subtask: restore the central record for this tenant
                        #####################################################

                        #
                        # Proceed
                        #

                        if not restore_virtual_tenant_main_kvrecord:

                            info_message = f'restore_virtual_tenant_main_kvrecord is set to False, the main KVstore record for tenant_id="{tenant_id}" will not be restored'
                            logger.info(info_message)
                            tasks_list.append(info_message)

                        else:

                            tenant_id_main_record = None
                            for record in vtenants_main_records:
                                if record["tenant_id"] == tenant_id:
                                    tenant_id_main_record = record
                                    break

                            if not tenant_id_main_record:
                                error_message = f'failed to find the tenant_id="{tenant_id}" in the backup file="{source_json_file}", the tenant cannot be restored'
                                logger.error(error_message)
                                errors_list.append(error_message)
                                break
                            else:
                                logger.info(
                                    f'Found tenant_id="{tenant_id}" in the backup file="{source_json_file}", the tenant can be restored'
                                )

                            # in live KVstore, check if the tenant_id already exists, it it does, replace the record, otherwise create it
                            try:
                                existing_record = collection.data.query(
                                    query=json.dumps({"tenant_id": tenant_id})
                                )[0]
                            except Exception as e:
                                existing_record = None

                            # if the tenant_id already exists, replace the record
                            if existing_record:
                                try:
                                    collection.data.update(
                                        existing_record["_key"],
                                        json.dumps(tenant_id_main_record),
                                    )
                                    tasks_list.append(
                                        f'updated the tenant_id="{tenant_id}" in the KVstore collection="{collection_name_main}"'
                                    )
                                except Exception as e:
                                    error_message = f'failed to update the tenant_id="{tenant_id}" in the KVstore collection="{collection_name_main}" with exception="{str(e)}"'
                                    logger.error(error_message)
                                    return {
                                        "payload": {
                                            "response": error_message,
                                        },
                                        "status": 500,
                                    }
                            else:
                                try:
                                    collection.data.insert(
                                        json.dumps(tenant_id_main_record)
                                    )
                                    tasks_list.append(
                                        f'inserted the tenant_id="{tenant_id}" in the KVstore collection="{collection_name_main}"'
                                    )
                                except Exception as e:
                                    error_message = f'failed to insert the tenant_id="{tenant_id}" in the KVstore collection="{collection_name_main}" with exception="{str(e)}"'
                                    logger.error(error_message)
                                    return {
                                        "payload": {
                                            "response": error_message,
                                        },
                                        "status": 500,
                                    }

                        ##########################################################
                        # task: load knowledge objects backup file for this tenant
                        ##########################################################

                        knowledge_objects_json_file = (
                            f"tenant_{tenant_id}_knowledge_objects.json"
                        )
                        try:
                            f = open(
                                os.path.join(backupdir, knowledge_objects_json_file),
                                "r",
                            )
                            data = json.loads(f.read())
                            info_message = f'loaded the knowledge objects backup file="{knowledge_objects_json_file}" for tenant_id="{tenant_id}"'
                            logger.info(info_message)
                            tasks_list.append(info_message)
                        except Exception as e:
                            error_message = f'failed to open json file="{os.path.join(backupdir, knowledge_objects_json_file)}" for reading with exception="{str(e)}", cannot restore knowledge objects for tenant_id="{tenant_id}"'
                            logger.error(error_message)
                            errors_list.append(error_message)
                            break

                        # init lists and dicts of knowledge objects for this tenant in the backup data
                        kvstore_collections_restorable_list = []
                        kvstore_collections_restorable_dict = {}
                        kvstore_transforms_restorable_list = []
                        kvstore_transforms_restorable_dict = {}
                        macros_restorable_list = []
                        macros_restorable_dict = {}
                        savedsearches_restorable_list = []
                        savedsearches_restorable_dict = {}
                        alerts_restorable_list = []
                        alerts_restorable_dict = {}

                        # Initialize lists to track failed objects for second attempt
                        failed_transforms = []
                        failed_macros = []
                        failed_savedsearches = []
                        failed_alerts = []

                        # first parse the data, get the type of object and the name, add to the appropriate list, log and add to the tasks list
                        for record in data.values():

                            if record["type"] == "kvstore_collections":
                                kvstore_collections_restorable_list.append(
                                    record["title"]
                                )
                                kvstore_collections_restorable_dict[record["title"]] = (
                                    record
                                )
                            if record["type"] == "lookup_definitions":
                                kvstore_transforms_restorable_list.append(
                                    record["title"]
                                )
                                kvstore_transforms_restorable_dict[record["title"]] = (
                                    record
                                )
                            if record["type"] == "macros":
                                macros_restorable_list.append(record["title"])
                                macros_restorable_dict[record["title"]] = record
                            if record["type"] == "savedsearches":
                                savedsearches_restorable_list.append(record["title"])
                                savedsearches_restorable_dict[record["title"]] = record
                            if record["type"] == "alerts":
                                alerts_restorable_list.append(record["title"])
                                alerts_restorable_dict[record["title"]] = record

                        info_message = f'knowledge objects backup file="{knowledge_objects_json_file}" for tenant_id="{tenant_id}" parsed successfully, number of restorable kvstore collections="{len(kvstore_collections_restorable_list)}", number of restorable transforms definitions="{len(kvstore_transforms_restorable_list)}", number of restorable macros="{len(macros_restorable_list)}", number of restorable saved searches="{len(savedsearches_restorable_list)}"'
                        logger.info(info_message)
                        tasks_list.append(info_message)

                        # add to response_dict
                        response_dict[f"knowledge_objects_tenant_id_{tenant_id}"] = {
                            "kvstore_collections": kvstore_collections_restorable_list,
                            "transforms_definitions": kvstore_transforms_restorable_list,
                            "macros": macros_restorable_list,
                            "savedsearches": savedsearches_restorable_list,
                            "alerts": alerts_restorable_list,
                        }

                        ##########################################################
                        # task: restore kvstore collections definitions for tenant
                        ##########################################################

                        # Loop through the restorable collections, and proceed
                        if restore_kvstore_collections:
                            for collection_name in kvstore_collections_restorable_list:
                                logger.info(
                                    f'TrackMe restore process starting, knowledge objects, processing restore of kvstore definition for collection_name="{collection_name}" for tenant_id="{tenant_id}"'
                                )

                                # check if the collection exists already
                                collection_exists = False

                                try:
                                    collection = service.kvstore[collection_name]
                                    collection_exists = True

                                except Exception as e:
                                    pass

                                # if knowledge_objects_replace_existing, systematically attempt to delete the collection
                                if (
                                    collection_exists
                                    and not knowledge_objects_replace_existing
                                ):

                                    logger.info(
                                        f'collection="{collection_name}" already exists and the replace_existing option is set to False, skipping the restore operation'
                                    )
                                    result = {
                                        "object": collection_name,
                                        "object_type": "kvstore collection",
                                        "action": "restore",
                                        "result": "skipped",
                                        "reason": "already exists and replace_existing is set to False",
                                    }
                                    logger.info(json.dumps(result, indent=4))
                                    tasks_list.append(result)
                                    continue

                                else:

                                    if collection_exists:
                                        try:
                                            action = trackme_delete_kvcollection(
                                                request_info.system_authtoken,
                                                request_info.server_rest_uri,
                                                tenant_id,
                                                collection_name,
                                            )
                                            logger.info(
                                                f'collection="{collection_name}" was deleted successfully, response="{action}"'
                                            )
                                            result = {
                                                "object": collection_name,
                                                "object_type": "kvstore collection",
                                                "action": "delete",
                                                "result": "success",
                                            }
                                            tasks_list.append(result)
                                        except Exception as e:
                                            pass  # no need to log or report, the collection might not exist yet

                                try:

                                    ko_acl = {
                                        "owner": kvstore_collections_restorable_dict[
                                            collection_name
                                        ]["properties"]["eai:acl.owner"],
                                        "sharing": kvstore_collections_restorable_dict[
                                            collection_name
                                        ]["properties"]["eai:acl.sharing"],
                                        "perms.write": kvstore_collections_restorable_dict[
                                            collection_name
                                        ][
                                            "properties"
                                        ][
                                            "eai:acl.perms.write"
                                        ],
                                        "perms.read": kvstore_collections_restorable_dict[
                                            collection_name
                                        ][
                                            "properties"
                                        ][
                                            "eai:acl.perms.read"
                                        ],
                                    }

                                    # ensure owner exists locally, otherwise fallback
                                    ko_acl["owner"] = _resolve_owner(ko_acl.get("owner"))

                                    trackme_create_kvcollection(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        collection_name,
                                        ko_acl,
                                    )
                                    result = {
                                        "object": collection_name,
                                        "object_type": "kvstore collection",
                                        "action": "restore",
                                        "result": "success",
                                    }
                                    tasks_list.append(result)
                                except Exception as e:
                                    result = {
                                        "object": collection_name,
                                        "object_type": "kvstore collection",
                                        "action": "restore",
                                        "result": "failure",
                                        "exception": str(e),
                                    }
                                    logger.error(json.dumps(result, indent=4))
                                    errors_list.append(result)

                                # restore the collection records for this collection and add to the list of restored collections
                                try:
                                    (
                                        kvstore_collections_global_records_to_be_restored,
                                        kvstore_collections_global_records_restored,
                                        kvstore_collection_restore_summary_dict,
                                    ) = restore_kvstore_records(
                                        service,
                                        collection_name,
                                        collections_restore_dict,
                                        backupdir,
                                        kvstore_collections_global_records_to_be_restored,
                                        kvstore_collections_global_records_restored,
                                        kvstore_collections_restored_warning,
                                        restore_results_dict,
                                        kvstore_collections_clean_empty,
                                    )
                                except KeyError as e:
                                    # Handle case where collection is not in collections_restore_dict
                                    error_msg = f'Collection "{collection_name}" not found in backup data, skipping restore. This may be due to the collection being excluded from backups (e.g., stateful charts collections).'
                                    logger.warning(error_msg)
                                    result = {
                                        "object": collection_name,
                                        "object_type": "kvstore collection",
                                        "action": "restore",
                                        "result": "skipped",
                                        "reason": "collection not found in backup data",
                                    }
                                    tasks_list.append(result)
                                    continue
                                except Exception as e:
                                    # Handle any other errors during restore
                                    error_msg = f'Failed to restore collection "{collection_name}": {str(e)}'
                                    logger.error(error_msg)
                                    result = {
                                        "object": collection_name,
                                        "object_type": "kvstore collection",
                                        "action": "restore",
                                        "result": "failure",
                                        "exception": str(e),
                                    }
                                    errors_list.append(result)
                                    continue

                                kvstore_collections_restored.append(collection_name)

                                # add to dict
                                kvstore_collections_restore_summary_dict[
                                    collection_name
                                ] = kvstore_collection_restore_summary_dict

                        #########################################################
                        # task: restore kvstore transforms definitions for tenant
                        #########################################################

                        # Loop through the restorable collections transforms, and proceed

                        # if knowledge_objects_lists is not equal to all, filter the list to its value
                        if knowledge_objects_lists != "all":
                            kvstore_transforms_restorable_list = [
                                transform
                                for transform in kvstore_transforms_restorable_list
                                if transform in knowledge_objects_lists
                            ]

                        # Filter out any transforms in the blocklist
                        kvstore_transforms_restorable_list = [
                            transform
                            for transform in kvstore_transforms_restorable_list
                            if transform not in knowledge_objects_blocklist
                        ]

                        for transforms_name in kvstore_transforms_restorable_list:

                            logger.info(
                                f'TrackMe restore process starting, knowledge objects, processing restore of kvstore transforms definition for transforms_name="{transforms_name}" for tenant_id="{tenant_id}"'
                            )

                            # check if the transforms exists already
                            transforms_exists = False

                            try:
                                transforms_object = service.confs["transforms"][
                                    transforms_name
                                ]
                                transforms_exists = True

                            except Exception as e:
                                pass

                            if (
                                transforms_exists
                                and not knowledge_objects_replace_existing
                            ):
                                logger.info(
                                    f'transforms="{transforms_name}" already exists and the replace_existing option is set to False, skipping the restore operation'
                                )
                                result = {
                                    "object": transforms_name,
                                    "object_type": "kvstore transforms",
                                    "action": "restore",
                                    "result": "skipped",
                                    "reason": "already exists and replace_existing is set to False",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)
                                continue

                            else:

                                if transforms_exists:

                                    try:
                                        action = trackme_delete_kvtransform(
                                            request_info.system_authtoken,
                                            request_info.server_rest_uri,
                                            tenant_id,
                                            transforms_name,
                                        )
                                        result = {
                                            "object": transforms_name,
                                            "object_type": "transform",
                                            "action": "delete",
                                            "result": "success",
                                        }
                                        logger.info(json.dumps(result, indent=4))
                                        tasks_list.append(result)

                                    except Exception as e:
                                        result = {
                                            "object": transforms_name,
                                            "object_type": "transform",
                                            "action": "delete",
                                            "result": "failure",
                                            "exception": str(e),
                                        }
                                        logger.error(json.dumps(result, indent=4))
                                        errors_list.append(result)

                                try:

                                    ko_acl = {
                                        "owner": kvstore_transforms_restorable_dict[
                                            transforms_name
                                        ]["properties"]["eai:acl.owner"],
                                        "sharing": kvstore_transforms_restorable_dict[
                                            transforms_name
                                        ]["properties"]["eai:acl.sharing"],
                                        "perms.write": kvstore_transforms_restorable_dict[
                                            transforms_name
                                        ][
                                            "properties"
                                        ][
                                            "eai:acl.perms.write"
                                        ],
                                        "perms.read": kvstore_transforms_restorable_dict[
                                            transforms_name
                                        ][
                                            "properties"
                                        ][
                                            "eai:acl.perms.read"
                                        ],
                                    }

                                    # ensure owner exists locally, otherwise fallback
                                    ko_acl["owner"] = _resolve_owner(ko_acl.get("owner"))

                                    trackme_create_kvtransform(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        transforms_name,
                                        kvstore_transforms_restorable_dict[
                                            transforms_name
                                        ]["fields_list"],
                                        kvstore_transforms_restorable_dict[
                                            transforms_name
                                        ]["collection"],
                                        ko_acl.get("owner"),
                                        ko_acl,
                                    )
                                    result = {
                                        "object": transforms_name,
                                        "object_type": "kvstore transforms",
                                        "action": "restore",
                                        "result": "success",
                                    }
                                    logger.info(json.dumps(result, indent=4))
                                    tasks_list.append(result)

                                except Exception as e:
                                    result = {
                                        "object": transforms_name,
                                        "object_type": "kvstore transforms",
                                        "action": "restore",
                                        "result": "failure",
                                        "exception": str(e),
                                    }
                                    logger.error(json.dumps(result, indent=4))
                                    failed_transforms.append(
                                        {
                                            "name": transforms_name,
                                            "tenant_id": tenant_id,
                                            "transform_fields_list": kvstore_transforms_restorable_dict[
                                                transforms_name
                                            ][
                                                "fields_list"
                                            ],
                                            "transform_collection": kvstore_transforms_restorable_dict[
                                                transforms_name
                                            ][
                                                "collection"
                                            ],
                                            "owner": ko_acl.get("owner"),
                                            "acl": ko_acl,
                                        }
                                    )

                        #############################################
                        # task: restore macros definitions for tenant
                        #############################################

                        # Loop through the restorable macros, and proceed

                        # if knowledge_objects_lists is not equal to all, filter the list to its value
                        if knowledge_objects_lists != "all":
                            macros_restorable_list = [
                                macro
                                for macro in macros_restorable_list
                                if macro in knowledge_objects_lists
                            ]

                        # Filter out any macros in the blocklist
                        macros_restorable_list = [
                            macro
                            for macro in macros_restorable_list
                            if macro not in knowledge_objects_blocklist
                        ]

                        for macro_name in macros_restorable_list:

                            logger.info(
                                f'TrackMe restore process starting, knowledge objects, processing restore of macro definition for macro_name="{macro_name}" for tenant_id="{tenant_id}"'
                            )

                            # check if the macro exists already
                            macro_exists = False

                            try:
                                macro_object = service.confs["macros"][macro_name]
                                macro_exists = True
                            except Exception as e:
                                pass

                            if macro_exists and not knowledge_objects_replace_existing:
                                logger.info(
                                    f'macro="{macro_name}" already exists and the replace_existing option is set to False, skipping the restore operation'
                                )
                                result = {
                                    "object": macro_name,
                                    "object_type": "macro",
                                    "action": "restore",
                                    "result": "skipped",
                                    "reason": "already exists and replace_existing is set to False",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)
                                continue

                            else:

                                if macro_exists:

                                    try:
                                        action = trackme_delete_macro(
                                            request_info.system_authtoken,
                                            request_info.server_rest_uri,
                                            tenant_id,
                                            macro_name,
                                        )
                                        logger.info(
                                            f'macro="{macro_name}" was deleted successfully, response="{action}"'
                                        )
                                        result = {
                                            "object": macro_name,
                                            "object_type": "macro",
                                            "action": "delete",
                                            "result": "success",
                                        }
                                        logger.info(json.dumps(result, indent=4))
                                        tasks_list.append(result)

                                    except Exception as e:
                                        result = {
                                            "object": macro_name,
                                            "object_type": "macro",
                                            "action": "delete",
                                            "result": "failure",
                                            "exception": str(e),
                                        }
                                        logger.error(json.dumps(result, indent=4))
                                        errors_list.append(result)

                                try:

                                    ko_acl = {
                                        "owner": macros_restorable_dict[macro_name][
                                            "properties"
                                        ]["eai:acl.owner"],
                                        "sharing": macros_restorable_dict[macro_name][
                                            "properties"
                                        ]["eai:acl.sharing"],
                                        "perms.write": macros_restorable_dict[
                                            macro_name
                                        ]["properties"]["eai:acl.perms.write"],
                                        "perms.read": macros_restorable_dict[
                                            macro_name
                                        ]["properties"]["eai:acl.perms.read"],
                                    }

                                    # ensure owner exists locally, otherwise fallback
                                    ko_acl["owner"] = _resolve_owner(ko_acl.get("owner"))

                                    trackme_create_macro(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        macro_name,
                                        macros_restorable_dict[macro_name][
                                            "definition"
                                        ],
                                        ko_acl.get("owner"),
                                        ko_acl,
                                    )

                                    result = {
                                        "object": macro_name,
                                        "object_type": "macro",
                                        "action": "restore",
                                        "result": "success",
                                    }
                                    logger.info(json.dumps(result, indent=4))
                                    tasks_list.append(result)

                                except Exception as e:
                                    result = {
                                        "object": macro_name,
                                        "object_type": "macro",
                                        "action": "restore",
                                        "result": "failure",
                                        "exception": str(e),
                                    }
                                    logger.error(json.dumps(result, indent=4))
                                    failed_macros.append(
                                        {
                                            "name": macro_name,
                                            "tenant_id": tenant_id,
                                            "macro_definition": macros_restorable_dict[
                                                macro_name
                                            ]["definition"],
                                            "owner": ko_acl.get("owner"),
                                            "acl": ko_acl,
                                        }
                                    )

                        ####################################################
                        # task: restore savedsearches definitions for tenant
                        ####################################################

                        # Save available savedsearches in a main list
                        savedsearches_restorable_list_origin = []
                        for savedsearch in savedsearches_restorable_dict:
                            savedsearches_restorable_list_origin.append(savedsearch)

                        # If knowledge_objects_lists is not equal to "all", filter the list to its value
                        if knowledge_objects_lists != "all":
                            savedsearches_restorable_list = [
                                savedsearch
                                for savedsearch in savedsearches_restorable_list_origin
                                if savedsearch in knowledge_objects_lists
                            ]
                        else:
                            savedsearches_restorable_list = (
                                savedsearches_restorable_list_origin.copy()
                            )

                        # Filter out any saved searches in the blocklist
                        savedsearches_restorable_list = [
                            savedsearch
                            for savedsearch in savedsearches_restorable_list
                            if savedsearch not in knowledge_objects_blocklist
                        ]

                        # Restoring saved searches has some challenges, if the search itself refers to another saved search, we need to
                        # restore this saved search first, and then restore the search that refers to it.

                        # Init a list of restored saved searches
                        savedsearches_restored = []

                        for savedsearch_name in savedsearches_restorable_list:

                            logger.info(
                                f'TrackMe restore process starting, knowledge objects, processing restore of savedsearch definition for savedsearch_name="{savedsearch_name}" for tenant_id="{tenant_id}"'
                            )

                            # First, get the search definition
                            savedsearch_definition = savedsearches_restorable_dict[
                                savedsearch_name
                            ]["definition"]

                            # Use regex to find the parent search
                            parent_search_match = re.search(
                                r"\| savedsearch\s+\"{0,1}([^\"]+)\"{0,1}",
                                savedsearch_definition,
                            )

                            # Extract parent search name if found
                            parent_search_name = (
                                parent_search_match.group(1)
                                if parent_search_match
                                else None
                            )

                            if parent_search_name:
                                # Check if the parent search exists in the original restorable list
                                if (
                                    parent_search_name
                                    in savedsearches_restorable_list_origin
                                ):
                                    # Ensure the parent search is restored first
                                    if parent_search_name not in savedsearches_restored:
                                        logger.info(
                                            f'TrackMe restore process: parent search "{parent_search_name}" detected for savedsearch "{savedsearch_name}". Restoring parent first.'
                                        )
                                        # Recursive restore call for the parent search
                                        if (
                                            parent_search_name
                                            in savedsearches_restorable_list
                                        ):
                                            savedsearches_restorable_list.remove(
                                                parent_search_name
                                            )  # Avoid duplicate processing
                                        savedsearches_restorable_list.insert(
                                            0, parent_search_name
                                        )  # Prioritize restoring the parent search
                                else:
                                    # Log an error and skip the child search if the parent isn't available
                                    error_message = {
                                        "object": savedsearch_name,
                                        "object_type": "savedsearch",
                                        "action": "restore",
                                        "result": "failure",
                                        "reason": f"Parent search '{parent_search_name}' not found in restorable list.",
                                    }
                                    logger.error(json.dumps(error_message, indent=4))
                                    errors_list.append(error_message)
                                    continue  # Skip restoring the current search

                            # Proceed with the restoration logic for the current saved search
                            savedsearch_exists = False
                            try:
                                savedsearch_object = service.saved_searches[
                                    savedsearch_name
                                ]
                                savedsearch_search = savedsearch_object.content[
                                    "search"
                                ]
                                savedsearch_exists = True

                            except Exception:
                                pass

                            if (
                                savedsearch_exists
                                and not knowledge_objects_replace_existing
                            ):
                                logger.info(
                                    f'savedsearch="{savedsearch_name}" already exists and the replace_existing option is set to False, skipping the restore operation'
                                )
                                result = {
                                    "object": savedsearch_name,
                                    "object_type": "savedsearch",
                                    "action": "restore",
                                    "result": "skipped",
                                    "reason": "already exists and replace_existing is set to False",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)
                            else:
                                # Restore logic
                                try:
                                    if savedsearch_exists:
                                        # Delete existing savedsearch if required
                                        action = trackme_delete_report(
                                            request_info.system_authtoken,
                                            request_info.server_rest_uri,
                                            tenant_id,
                                            savedsearch_name,
                                        )
                                        logger.info(
                                            f'savedsearch="{savedsearch_name}" was deleted successfully, response="{action}"'
                                        )

                                    # Prepare properties for restoration
                                    savedsearch_properties = {
                                        "description": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]["description"],
                                        "is_scheduled": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]["is_scheduled"],
                                        "schedule_window": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ][
                                            "properties"
                                        ][
                                            "schedule_window"
                                        ],
                                    }

                                    # Set dispatch.earliest_time, default to -5m if not valid
                                    earliest_time = savedsearches_restorable_dict[
                                        savedsearch_name
                                    ]["properties"].get("earliest_time")
                                    if not earliest_time or earliest_time in (
                                        None,
                                        "None",
                                        "null",
                                    ):
                                        earliest_time = "-5m"
                                    savedsearch_properties[
                                        "dispatch.earliest_time"
                                    ] = earliest_time

                                    # Set dispatch.latest_time, default to now if not valid
                                    latest_time = savedsearches_restorable_dict[
                                        savedsearch_name
                                    ]["properties"].get("latest_time")
                                    if not latest_time or latest_time in (
                                        None,
                                        "None",
                                        "null",
                                    ):
                                        latest_time = "now"
                                    savedsearch_properties[
                                        "dispatch.latest_time"
                                    ] = latest_time

                                    # Only add cron_schedule if it's not None or "None"
                                    cron_schedule = savedsearches_restorable_dict[
                                        savedsearch_name
                                    ]["properties"].get("cron_schedule")
                                    if cron_schedule and cron_schedule not in (
                                        None,
                                        "None",
                                        "null",
                                    ):
                                        savedsearch_properties["cron_schedule"] = (
                                            cron_schedule
                                        )

                                    # if dispatch.sample_ratio is set in the restorable dict, add it to the properties
                                    if (
                                        "dispatch.sample_ratio"
                                        in savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]
                                    ):
                                        savedsearch_properties[
                                            "dispatch.sample_ratio"
                                        ] = savedsearches_restorable_dict[
                                            savedsearch_name
                                        ][
                                            "properties"
                                        ][
                                            "dispatch.sample_ratio"
                                        ]

                                    ko_acl = {
                                        "owner": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]["eai:acl.owner"],
                                        "sharing": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]["eai:acl.sharing"],
                                        "perms.write": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]["eai:acl.perms.write"],
                                        "perms.read": savedsearches_restorable_dict[
                                            savedsearch_name
                                        ]["properties"]["eai:acl.perms.read"],
                                    }

                                    # ensure owner exists locally, otherwise fallback
                                    ko_acl["owner"] = _resolve_owner(ko_acl.get("owner"))

                                    # Restore the savedsearch
                                    trackme_create_report(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        savedsearch_name,
                                        savedsearches_restorable_dict[savedsearch_name][
                                            "definition"
                                        ],
                                        savedsearch_properties,
                                        ko_acl,
                                    )

                                    result = {
                                        "object": savedsearch_name,
                                        "object_type": "savedsearch",
                                        "action": "restore",
                                        "result": "success",
                                    }
                                    logger.info(json.dumps(result, indent=4))
                                    tasks_list.append(result)
                                    savedsearches_restored.append(
                                        savedsearch_name
                                    )  # Mark as restored

                                except Exception as e:
                                    result = {
                                        "object": savedsearch_name,
                                        "object_type": "savedsearch",
                                        "action": "restore",
                                        "result": "failure",
                                        "exception": str(e),
                                    }
                                    logger.error(json.dumps(result, indent=4))
                                    failed_savedsearches.append(
                                        {
                                            "name": savedsearch_name,
                                            "tenant_id": tenant_id,
                                            "savedsearch_definition": savedsearches_restorable_dict[
                                                savedsearch_name
                                            ][
                                                "definition"
                                            ],
                                            "savedsearch_properties": savedsearch_properties,
                                            "owner": ko_acl.get("owner"),
                                            "acl": ko_acl,
                                        }
                                    )

                        #############################################
                        # task: restore alerts definitions for tenant
                        #############################################

                        # Save available alerts in a main list
                        alerts_restorable_list_origin = []
                        for alert in alerts_restorable_dict:
                            alerts_restorable_list_origin.append(alert)

                        # If knowledge_objects_lists is not equal to "all", filter the list to its value
                        if knowledge_objects_lists != "all":
                            alerts_restorable_list = [
                                alert
                                for alert in alerts_restorable_list_origin
                                if alert in knowledge_objects_lists
                            ]
                        else:
                            alerts_restorable_list = (
                                alerts_restorable_list_origin.copy()
                            )

                        # Filter out any alerts in the blocklist
                        alerts_restorable_list = [
                            alert
                            for alert in alerts_restorable_list
                            if alert not in knowledge_objects_blocklist
                        ]

                        # Restoring saved searches has some challenges, if the search itself refers to another saved search, we need to
                        # restore this saved search first, and then restore the search that refers to it.

                        # Init a list of restored saved searches
                        alerts_restored = []

                        for alert_name in alerts_restorable_list:

                            logger.info(
                                f'TrackMe restore process starting, knowledge objects, processing restore of alert definition for alert_name="{alert_name}" for tenant_id="{tenant_id}"'
                            )

                            # First, get the search definition
                            alert_definition = alerts_restorable_dict[alert_name][
                                "definition"
                            ]

                            # Proceed with the restoration logic for the current saved search
                            alert_exists = False
                            try:
                                alert_object = service.saved_searches[alert_name]
                                alert_search = alert_object.content["search"]
                                alert_exists = True

                            except Exception:
                                pass

                            if alert_exists and not knowledge_objects_replace_existing:
                                logger.info(
                                    f'alert="{alert_name}" already exists and the replace_existing option is set to False, skipping the restore operation'
                                )
                                result = {
                                    "object": alert_name,
                                    "object_type": "alert",
                                    "action": "restore",
                                    "result": "skipped",
                                    "reason": "already exists and replace_existing is set to False",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)

                            else:
                                # Restore logic
                                logger.info(
                                    f'alert_name="{alert_name}" does not exist, restoring it'
                                )

                                if alert_exists:
                                    # Delete existing alert if required
                                    try:
                                        action = trackme_delete_report(
                                            request_info.system_authtoken,
                                            request_info.server_rest_uri,
                                            tenant_id,
                                            alert_name,
                                        )
                                        logger.info(
                                            f'alert="{alert_name}" was deleted successfully, response="{action}"'
                                        )
                                    except Exception as e:
                                        pass

                                # Prepare properties for restoration
                                properties = {
                                    "description": alerts_restorable_dict[alert_name][
                                        "properties"
                                    ]["description"],
                                    "is_scheduled": alerts_restorable_dict[alert_name][
                                        "properties"
                                    ]["is_scheduled"],
                                    "schedule_window": alerts_restorable_dict[
                                        alert_name
                                    ]["properties"]["schedule_window"],
                                }

                                # Set dispatch.earliest_time, default to -5m if not valid
                                earliest_time = alerts_restorable_dict[alert_name][
                                    "properties"
                                ].get("earliest_time")
                                if not earliest_time or earliest_time in (
                                    None,
                                    "None",
                                    "null",
                                ):
                                    earliest_time = "-5m"
                                properties["dispatch.earliest_time"] = earliest_time

                                # Set dispatch.latest_time, default to now if not valid
                                latest_time = alerts_restorable_dict[alert_name][
                                    "properties"
                                ].get("latest_time")
                                if not latest_time or latest_time in (
                                    None,
                                    "None",
                                    "null",
                                ):
                                    latest_time = "now"
                                properties["dispatch.latest_time"] = latest_time

                                # Only add cron_schedule if it's not None or "None"
                                cron_schedule = alerts_restorable_dict[alert_name][
                                    "properties"
                                ].get("cron_schedule")
                                if cron_schedule and cron_schedule not in (
                                    None,
                                    "None",
                                    "null",
                                ):
                                    properties["cron_schedule"] = cron_schedule

                                # if dispatch.sample_ratio is set in the restorable dict, add it to the properties
                                if (
                                    "dispatch.sample_ratio"
                                    in alerts_restorable_dict[alert_name]["properties"]
                                ):
                                    properties["dispatch.sample_ratio"] = (
                                        alerts_restorable_dict[alert_name][
                                            "properties"
                                        ]["dispatch.sample_ratio"]
                                    )

                                ko_acl = {
                                    "owner": alerts_restorable_dict[alert_name][
                                        "properties"
                                    ]["eai:acl.owner"],
                                    "sharing": alerts_restorable_dict[alert_name][
                                        "properties"
                                    ]["eai:acl.sharing"],
                                    "perms.write": alerts_restorable_dict[alert_name][
                                        "properties"
                                    ]["eai:acl.perms.write"],
                                    "perms.read": alerts_restorable_dict[alert_name][
                                        "properties"
                                    ]["eai:acl.perms.read"],
                                }

                                # ensure owner exists locally, otherwise fallback
                                ko_acl["owner"] = _resolve_owner(ko_acl.get("owner"))

                                alert_properties = alerts_restorable_dict[alert_name][
                                    "alert_properties"
                                ]

                                # enabling alert actions:
                                alert_actions = []

                                if (
                                    int(
                                        alert_properties.get(
                                            "action.trackme_stateful_alert", 0
                                        )
                                    )
                                    == 1
                                ):
                                    alert_actions.append("trackme_stateful_alert")

                                if (
                                    int(
                                        alert_properties.get("action.trackme_notable"),
                                        0,
                                    )
                                    == 1
                                ):
                                    alert_actions.append("trackme_notable")

                                if (
                                    int(
                                        alert_properties.get("action.trackme_auto_ack"),
                                        0,
                                    )
                                    == 1
                                ):
                                    alert_actions.append("trackme_auto_ack")

                                # turn the list into a csv string and add to alert_properties
                                alert_properties["actions"] = ",".join(alert_actions)

                                # prevents issues with external alerts, parse alert_properties,
                                # and remove any field which action.<parameter> which does start as:
                                # actions.trackme*

                                # Remove any keys that start with "action." but don't start with "action.trackme"
                                keys_to_remove = [
                                    key
                                    for key in alert_properties.keys()
                                    if key.startswith("action.")
                                    and not key.startswith("action.trackme")
                                ]
                                for key in keys_to_remove:
                                    del alert_properties[key]

                                logger.info(
                                    f'calling trackme_create_alert with properties="{json.dumps(properties, indent=2)}", alert_properties="{json.dumps(alert_properties, indent=2)}"'
                                )

                                try:

                                    # Restore the alert
                                    trackme_create_alert(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        alert_name,
                                        alerts_restorable_dict[alert_name][
                                            "definition"
                                        ],
                                        properties,
                                        alert_properties,
                                        ko_acl,
                                    )

                                    result = {
                                        "object": alert_name,
                                        "object_type": "alert",
                                        "action": "restore",
                                        "result": "success",
                                    }
                                    logger.info(json.dumps(result, indent=4))
                                    tasks_list.append(result)
                                    alerts_restored.append(
                                        alert_name
                                    )  # Mark as restored

                                except Exception as e:
                                    result = {
                                        "object": alert_name,
                                        "object_type": "alert",
                                        "action": "restore",
                                        "result": "failure",
                                        "exception": str(e),
                                    }
                                    logger.error(json.dumps(result, indent=4))
                                    failed_alerts.append(
                                        {
                                            "name": alert_name,
                                            "tenant_id": tenant_id,
                                            "alert_definition": alerts_restorable_dict[
                                                alert_name
                                            ]["definition"],
                                            "properties": properties,
                                            "alert_properties": alert_properties,
                                            "owner": ko_acl.get("owner"),
                                            "acl": ko_acl,
                                        }
                                    )

                        ################################################
                        # task: second attempt to restore failed objects
                        ################################################

                        # Retry failed transforms
                        for failed_transform in failed_transforms:
                            logger.info(
                                f'Second attempt to restore transform="{failed_transform["name"]}" for tenant_id="{failed_transform["tenant_id"]}"'
                            )

                            try:
                                trackme_create_kvtransform(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    failed_transform["name"],
                                    failed_transform["transform_fields_list"],
                                    failed_transform["transform_collection"],
                                    failed_transform["owner"],
                                    failed_transform["acl"],
                                )

                                result = {
                                    "object": failed_transform["name"],
                                    "object_type": "transform",
                                    "action": "restore",
                                    "result": "success",
                                    "attempt": "second",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)

                            except Exception as e:
                                result = {
                                    "object": failed_transform["name"],
                                    "object_type": "transform",
                                    "action": "restore",
                                    "result": "failure",
                                    "exception": str(e),
                                }
                                logger.error(json.dumps(result, indent=4))
                                errors_list.append(result)

                        # Retry failed macros
                        for failed_macro in failed_macros:
                            logger.info(
                                f'Second attempt to restore macro="{failed_macro["name"]}" for tenant_id="{failed_macro["tenant_id"]}"'
                            )

                            try:
                                trackme_create_macro(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    failed_macro["name"],
                                    failed_macro["macro_definition"],
                                    failed_macro["owner"],
                                    failed_macro["acl"],
                                )

                                result = {
                                    "object": failed_macro["name"],
                                    "object_type": "macro",
                                    "action": "restore",
                                    "result": "success",
                                    "attempt": "second",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)

                            except Exception as e:
                                result = {
                                    "object": failed_macro["name"],
                                    "object_type": "macro",
                                    "action": "restore",
                                    "result": "failure",
                                    "exception": str(e),
                                }
                                logger.error(json.dumps(result, indent=4))
                                errors_list.append(result)

                        # Retry failed saved searches
                        for failed_savedsearch in failed_savedsearches:
                            logger.info(
                                f'Second attempt to restore savedsearch="{failed_savedsearch["name"]}" for tenant_id="{failed_savedsearch["tenant_id"]}"'
                            )

                            try:
                                trackme_create_report(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    failed_savedsearch["name"],
                                    failed_savedsearch["savedsearch_definition"],
                                    failed_savedsearch["savedsearch_properties"],
                                    failed_savedsearch["acl"],
                                )

                                result = {
                                    "object": failed_savedsearch["name"],
                                    "object_type": "savedsearch",
                                    "action": "restore",
                                    "result": "success",
                                    "attempt": "second",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)

                            except Exception as e:
                                result = {
                                    "object": failed_savedsearch["name"],
                                    "object_type": "savedsearch",
                                    "action": "restore",
                                    "result": "failure",
                                    "exception": str(e),
                                }
                                logger.error(json.dumps(result, indent=4))
                                errors_list.append(result)

                        # Retry failed alerts
                        for failed_alert in failed_alerts:
                            logger.info(
                                f'Second attempt to restore alert="{failed_alert["name"]}" for tenant_id="{failed_alert["tenant_id"]}", properties="{json.dumps(failed_alert["properties"], indent=2)}", alert_properties="{json.dumps(failed_alert["alert_properties"], indent=2)}"'
                            )

                            try:
                                trackme_create_alert(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    failed_alert["name"],
                                    failed_alert["alert_definition"],
                                    failed_alert["properties"],
                                    failed_alert["alert_properties"],
                                    failed_alert["acl"],
                                )

                                result = {
                                    "object": failed_alert["name"],
                                    "object_type": "alert",
                                    "action": "restore",
                                    "result": "success",
                                    "attempt": "second",
                                }
                                logger.info(json.dumps(result, indent=4))
                                tasks_list.append(result)

                            except Exception as e:
                                result = {
                                    "object": failed_alert["name"],
                                    "object_type": "alert",
                                    "action": "restore",
                                    "result": "failure",
                                    "exception": str(e),
                                }
                                logger.error(json.dumps(result, indent=4))
                                errors_list.append(result)

                #######################################
                # Task: Restore the KVstore collections
                #######################################

                if (
                    restore_kvstore_collections
                    and kvstore_collections_restore_non_tenants_collections
                ):
                    logger.info(
                        f"TrackMe restore process starting, processing restore of KVstore collections"
                    )

                    # if knowledge_objects_tenants_scope is not all, then we need to filter the collections to be restored
                    # and remove kv_trackme_virtual_tenants and kv_trackme_virtual_tenants_entities_summary
                    if knowledge_objects_tenants_scope != "all":
                        kvstore_collections_to_be_restored = [
                            collection_name
                            for collection_name in kvstore_collections_to_be_restored
                            if collection_name
                            not in [
                                "kv_trackme_virtual_tenants",
                                "kv_trackme_virtual_tenants_entities_summary",
                            ]
                        ]

                    # Loop through the restorable collections, and proceed
                    for collection_name in kvstore_collections_to_be_restored:

                        # Skip if collection is not in the tenant scope
                        if knowledge_objects_tenants_scope != "all":
                            # Extract tenant_id from collection name if it's a tenant-specific collection
                            tenant_id = None
                            if (
                                collection_name.startswith("kv_trackme_")
                                and "_tenant_" in collection_name
                            ):
                                try:
                                    tenant_id = collection_name.split("_tenant_")[
                                        1
                                    ].split("_")[0]
                                except:
                                    pass

                            # Skip if this is a tenant-specific collection and the tenant is not in scope
                            if (
                                tenant_id
                                and tenant_id not in knowledge_objects_tenants_scope
                            ):
                                logger.info(
                                    f'Skipping collection="{collection_name}" as it belongs to tenant="{tenant_id}" which is not in the restore scope'
                                )
                                continue

                        if (
                            collection_name not in kvstore_collections_restored
                            and collection_name != "kv_trackme_backup_archives_info"
                        ):  # restore collections that were not restored with the knowledge objects for the tenant
                            try:
                                (
                                    kvstore_collections_global_records_to_be_restored,
                                    kvstore_collections_global_records_restored,
                                    kvstore_collection_restore_summary_dict,
                                ) = restore_kvstore_records(
                                    service,
                                    collection_name,
                                    collections_restore_dict,
                                    backupdir,
                                    kvstore_collections_global_records_to_be_restored,
                                    kvstore_collections_global_records_restored,
                                    kvstore_collections_restored_warning,
                                    restore_results_dict,
                                    kvstore_collections_clean_empty,
                                )
                            except KeyError as e:
                                # Handle case where collection is not in collections_restore_dict
                                error_msg = f'Collection "{collection_name}" not found in backup data, skipping restore. This may be due to the collection being excluded from backups (e.g., stateful charts collections).'
                                logger.warning(error_msg)
                                continue
                            except Exception as e:
                                # Handle any other errors during restore
                                error_msg = f'Failed to restore collection "{collection_name}": {str(e)}'
                                logger.error(error_msg)
                                continue

                            # add to dict
                            kvstore_collections_restore_summary_dict[
                                collection_name
                            ] = kvstore_collection_restore_summary_dict

                #######################################
                # End: clean up the temporary directory
                #######################################

                clean_backup_dir(backupdir)

            # investigate the results of the kvstore records restoration
            if (
                kvstore_collections_global_records_to_be_restored
                == kvstore_collections_global_records_restored
            ):
                kvstore_records_restore_summary = {
                    "response": "KVstore records restore operation is now complete and no errors were reported",
                    "action": "success",
                    "total_records_to_be_restored": kvstore_collections_global_records_to_be_restored,
                    "total_records_restored": kvstore_collections_global_records_restored,
                    "kvstore_collections_restore_summary_dict": kvstore_collections_restore_summary_dict,
                }

            else:
                kvstore_records_restore_summary = {
                    "response": "KVstore records restore operation is now complete but some errors were reported",
                    "action": "warning",
                    "message": "one or more KVstore collection could not be fully restored",
                    "total_records_to_be_restored": kvstore_collections_global_records_to_be_restored,
                    "total_records_restored": kvstore_collections_global_records_restored,
                    "kvstore_collections_restored_warning": kvstore_collections_restored_warning,
                    "kvstore_collections_restore_summary_dict": kvstore_collections_restore_summary_dict,
                }

            ##########################################
            # task: force clean up any disable tenants
            ##########################################

            # main vtenant collection
            collection_vtenants_name = "kv_trackme_virtual_tenants"
            collection_vtenants = service.kvstore[collection_vtenants_name]

            # Get records
            vtenants_records, vtenants_collection_keys, vtenants_collection_dict = (
                get_full_kv_collection(collection_vtenants, collection_vtenants_name)
            )

            # Iterate over the Virtual Tenants
            for vtenant_record in vtenants_records:

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # get the status
                tenant_status = vtenant_record.get("tenant_status")

                # only consider disabled tenants
                if tenant_status == "disabled":

                    logger.info(
                        f'Detected a disabled tenant_id="{tenant_id}", processing to the forced deletion'
                    )

                    # url
                    url = f"{request_info.server_rest_uri}/services/trackme/v2/vtenants/admin/del_tenant"

                    try:
                        response = requests.delete(
                            url,
                            headers=header,
                            data=json.dumps({"tenant_id": tenant_id, "force": "true"}),
                            verify=False,
                            timeout=600,
                        )

                        response_json = response.json()
                        tasks_list.append(
                            f'Detected a disabled tenant_id="{tenant_id}", forced deletion of tenant was processed, results: {response_json}'
                        )

                    except Exception as e:
                        error_msg = f'forced deletion of Virtual Tenants reported errors, exception="{str(e)}"'
                        logger.error(error_msg)
                        errors_list.append(error_msg)

            ######################
            # task: final response
            ######################

            # define action value, if errors_list is empty, set success, otherwise set warning
            action = "success" if not errors_list else "warning"
            response_dict["action"] = action

            # define response
            response = (
                "restore operation is now complete and no errors were reported, please reload TrackMe"
                if not errors_list
                else "restore operation is now complete but some errors were reported, please review these issues and reload TrackMe"
            )

            # add backupfile name
            response_dict["backupfile"] = backupfile

            # add the archive schema version
            response_dict["archive_schema_version"] = archive_schema_version

            # add the kvstore records restore results
            response_dict["kvstore_records_restore_summary"] = (
                kvstore_records_restore_summary
            )

            # add tasks list
            response_dict["tasks_executed"] = tasks_list

            # add errors list
            response_dict["tasks_errors"] = errors_list

            logger.info(json.dumps(response_dict, indent=4))
            return {"payload": response_dict, "status": 200}

    # ====================================================================
    # 3.0.0 multi-archive restore
    #
    # All methods below are dispatched from post_restore when the request
    # targets a 3.0.0 archive (`backup_archive` is a 3.0.0 filename) or a
    # 3.0.0 run (`backup_run_id` set). The legacy 1.0.0/2.0.0 code path
    # in post_restore stays untouched and continues to handle archives
    # produced before 2.3.22.
    # ====================================================================

    def _handle_restore_3_0_0(
        self,
        request_info,
        backup_archive,
        backup_run_id,
        dry_run,
        force_local,
        restore_kvstore_collections,
        kvstore_collections_scope,
        kvstore_collections_clean_empty,
        kvstore_collections_blocklist,
        kvstore_collections_restore_non_tenants_collections,
        restore_knowledge_objects,
        knowledge_objects_replace_existing,
        knowledge_objects_lists,
        knowledge_objects_blocklist,
        restore_virtual_tenant_accounts,
        restore_virtual_tenant_main_kvrecord,
        archives_scope=None,
        _v3_origin_job_id=None,
    ):
        """Entry point for the 3.0.0 restore path.

        Two modes:
          * Single archive — ``backup_archive`` is a 3.0.0 filename.
          * Run — ``backup_run_id`` is set; every archive belonging to
            that run is restored sequentially with per-archive isolation.

        ``archives_scope`` (optional) — per-archive selective restore.
        Map of archive filename → ``{"collections": [...] | "all",
        "knowledge_objects": [...] | "all"}``. When set for a given
        archive, takes precedence over the flat
        ``kvstore_collections_scope`` / ``knowledge_objects_lists``
        for THAT archive only. Archives absent from the map fall
        through to the flat filter behaviour. Empty dict / None ≡ flat
        filters apply uniformly (the legacy contract). The frontend
        (RestoreFormModal) populates this from the dry-run preview's
        per-archive multiselects; CLI / SPL callers can use either
        the flat filters (today's behaviour) or this richer map.

        ``_v3_origin_job_id`` (optional, internal) — the job_id of the
        async restore job that initiated this call on the ORIGINATING
        peer in a SHC scenario. Carries forward through SHC delegation
        so the RECEIVING peer can write the terminal status directly
        to the cluster-replicated ``kv_trackme_backup_restore_jobs``
        row when its work completes — bypassing the synchronous HTTP
        response chain. Why this matters: Splunk's REST framework on
        the receiving peer holds the HTTP response open for arbitrary
        post-write housekeeping time (config refresh, SHC bundle
        replication after saved-search CRUD). The originating peer's
        worker thread is blocked inside the synchronous HTTP-POST
        helper for that whole window. By writing the terminal status
        to the KV row directly, the UI sees ``completed`` as soon as
        the work finishes, without depending on the HTTP response
        latency. Field test on PRD5 SHC: 100s of actual work, 1+
        hour observed UI lag waiting for the HTTP response.

        Returns the standard ``{"payload": ..., "status": int}`` dict.
        Per-archive errors collect into ``archives[i].errors[]`` but do
        not abort the run — same isolation contract as post_backup.
        """
        splunkd_port = request_info.server_rest_port
        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.system_authtoken,
                timeout=600,
            )
        except Exception as e:
            logger.exception(f"3.0.0 restore: failed to connect to splunkd")
            return {
                "payload": {
                    "response": f"Failed to connect to splunkd: {str(e)}",
                },
                "status": 500,
            }

        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Resolve which archives we need to operate on by reading the
        # info collection (which is auto-replicated across SHC peers, so
        # this works on any peer regardless of which one produced the
        # archives).
        archives, lookup_err = self._v3_lookup_archives(
            service, backup_archive=backup_archive, backup_run_id=backup_run_id,
        )
        if lookup_err:
            return {
                "payload": {"response": lookup_err},
                "status": 404,
            }
        if not archives:
            return {
                "payload": {
                    "response": (
                        f"No archives found for backup_run_id={backup_run_id!r} / "
                        f"backup_archive={backup_archive!r}. Verify the input "
                        f"matches a row in kv_trackme_backup_archives_info."
                    ),
                },
                "status": 404,
            }

        # SHC cluster-KV completion-signalling: only propagate the
        # originating job_id to delegated receivers when this call
        # is a SINGLE-archive restore. For multi-archive run-mode
        # restores, each archive delegation triggers a separate
        # ``_handle_restore_3_0_0`` on a different receiving peer,
        # and each receiver only sees its own archive's outcome
        # (not the aggregate). If we propagated the job_id to all
        # of them, the first one to finish would write its single-
        # archive terminal status to the cluster-KV row and — via
        # the idempotent finalise contract — lock the job's status
        # to that single archive's outcome. Subsequent receivers
        # and the originating peer's aggregate-correct finalise
        # would all become no-ops, so the job's terminal status
        # would silently misrepresent the run.
        #
        # In single-archive mode, ``len(archives) == 1`` and the
        # receiver's outcome IS the whole job's outcome — safe to
        # propagate and let the receiver write directly (the fast-
        # UI-update path this PR exists for).
        #
        # In multi-archive run mode, we leave the body_params field
        # empty for delegations → no receiver-side write → the
        # aggregate write at the end of THIS method (below) is the
        # single source of truth for the terminal status. Slower
        # UI in run-mode SHC (waits for every HTTP response), but
        # correct.
        _propagate_job_id_to_receivers = bool(_v3_origin_job_id) and len(archives) == 1
        body_params = {
            "dry_run": dry_run,
            "restore_kvstore_collections": restore_kvstore_collections,
            "kvstore_collections_scope": kvstore_collections_scope,
            "kvstore_collections_clean_empty": kvstore_collections_clean_empty,
            "kvstore_collections_blocklist": kvstore_collections_blocklist or [],
            "kvstore_collections_restore_non_tenants_collections": (
                kvstore_collections_restore_non_tenants_collections
            ),
            "restore_knowledge_objects": restore_knowledge_objects,
            "knowledge_objects_replace_existing": knowledge_objects_replace_existing,
            "knowledge_objects_lists": knowledge_objects_lists,
            "knowledge_objects_blocklist": knowledge_objects_blocklist or [],
            "restore_virtual_tenant_accounts": restore_virtual_tenant_accounts,
            "restore_virtual_tenant_main_kvrecord": restore_virtual_tenant_main_kvrecord,
            # Per-archive selective restore — see method docstring.
            # Empty dict means "no overrides" → flat filters apply.
            "archives_scope": archives_scope or {},
            # Origin job_id for SHC-delegation cluster-KV completion
            # signalling. See the gating block above.
            "_v3_origin_job_id": (
                _v3_origin_job_id if _propagate_job_id_to_receivers else ""
            ),
            # Resumable-restore task tracking job_id. Distinct from
            # ``_v3_origin_job_id`` (which is gated on single-archive
            # mode to avoid the SHC-delegation aggregation issue
            # documented above): task tracking ALWAYS uses the same
            # job_id for LOCAL operations on this SH, regardless of
            # how many archives are in the run. This is the key the
            # per-step task hooks in ``_v3_restore_one_archive`` read
            # to decide whether to record progress. Empty string when
            # this call isn't part of an async job (synchronous CLI /
            # SPL caller) → task tracking is a no-op in that path.
            "_v3_task_tracking_job_id": _v3_origin_job_id or "",
        }

        results = []
        # Align with the FQDN-preferring convention every backup-archive
        # write path uses (``post_backup``, ``get_backup`` auto-discovery,
        # ``post_import_backup``). Without this, archive rows produced by
        # ``post_backup`` after PR #1568 carry the FQDN while
        # ``socket.gethostname()`` returns the short hostname on the same
        # peer, so ``is_remote_owner`` is always True for locally-owned
        # archives on a SHC deployment and the explicit SHC-local async
        # self-delegation path designed in PR #1551 (Issue #1550) becomes
        # unreachable. Restores still complete via cross-peer delegation
        # back to the FQDN of self (DNS resolves to local + receiver
        # short-circuits via ``force_local=true``), but that path is
        # less direct and depends on FQDN resolving locally. Using the
        # same helper here closes the gap and makes the explicit path
        # fire as designed. Loop protection still rests on
        # ``force_local=true`` at the receiver, not on this comparison.
        local_server = _resolve_canonical_server_name()
        # Detect SHC membership ONCE per call — every archive in the
        # same _handle_restore_3_0_0 invocation shares the same peer
        # context, so probing /services/server/roles once is enough.
        # The cache also keeps the per-archive loop free of HTTP
        # latency. Initialised lazily on first need so standalone
        # restores never pay the probe cost. See Issue #1550.
        _shc_cache = {"checked": False, "is_shc": False}

        def _is_shc():
            if not _shc_cache["checked"]:
                _shc_cache["is_shc"] = self._v3_is_shc_member(request_info)
                _shc_cache["checked"] = True
            return _shc_cache["is_shc"]

        # Resumable-restore: initialise the per-archive task lists in
        # the job row's ``tasks`` field BEFORE we start the work loop,
        # so a status-endpoint poll firing in the gap between dispatch
        # and the first task transition sees the full pending list.
        # The init is idempotent: if ``tasks`` is already populated
        # (resumed worker), the helper leaves it alone. Only triggers
        # when the async dispatcher passed an origin job_id AND this
        # is not a dry-run (dry-runs don't update job state — they
        # short-circuit out of ``_v3_restore_one_archive`` early).
        _task_list_job_id = (
            _v3_origin_job_id if (_v3_origin_job_id and not dry_run) else ""
        )
        if _task_list_job_id:
            try:
                full_task_list = []
                for arch_row in archives:
                    full_task_list.extend(
                        self._restore_job_compute_archive_tasks(arch_row, body_params)
                    )
                self._restore_job_init_tasks(
                    request_info, _task_list_job_id, full_task_list,
                )
            except Exception as e:
                # Init failure is non-fatal — the per-step task hooks
                # in _v3_restore_one_archive are best-effort, and a
                # missing task list just means the resume path can't
                # checkpoint-skip (it'll re-run from scratch instead).
                logger.warning(
                    f'resumable restore: task-list init failed for '
                    f'job_id="{_task_list_job_id}": {str(e)}'
                )

        for archive_row in archives:
            owner = archive_row.get("server_name") or local_server
            # `force_local=true` short-circuits the SHC delegation step
            # entirely. The dispatcher peer that delegates to this peer
            # always passes force_local=true, which prevents an
            # infinite delegation loop if the row's server_name does not
            # normalise to the receiving peer's socket.gethostname()
            # value (e.g. KV stores FQDN, peer reads short hostname).
            is_remote_owner = owner.lower() != local_server.lower()

            # SHC LOCAL async self-delegation (Issue #1550).
            #
            # When the originating call is async (``_v3_origin_job_id``
            # set) AND we're on an SHC peer AND the archive is owned by
            # the LOCAL peer, route the work through the same HTTP-POST
            # delegation path the cross-peer case uses — but target the
            # local peer's own splunkd. The receiving call lands in a
            # fresh REST-handler subprocess that is independent of the
            # async daemon thread's parent subprocess.
            #
            # Why this matters: a Python ``threading.Thread(daemon=True)``
            # spawned from a persistent REST handler dies when splunkd
            # recycles the parent subprocess. After the initial HTTP
            # response, splunkd considers the request done and may
            # recycle at any point. If the daemon dies before the
            # in-process work completes, the terminal-status KV write
            # at the end of ``_handle_restore_3_0_0`` is killed too —
            # the job KV row stays at ``status=running`` forever.
            #
            # Cross-peer SHC restores already escape this trap by virtue
            # of running in the REMOTE peer's subprocess (independent
            # of the local daemon's fate). This block extends the same
            # protection to the SHC-local case by routing the work into
            # an independent local subprocess. PR #1529's cluster-KV
            # completion-signalling path (in this same method, below)
            # writes the terminal status from the receiver — so as long
            # as the receiver is in a separate subprocess from the
            # daemon, the job row reaches a terminal state regardless
            # of daemon survival.
            #
            # Gated narrowly:
            #   * ``_v3_origin_job_id`` set → only async paths (sync
            #     restores keep the in-process path; the request thread
            #     is naturally alive for the work duration)
            #   * SHC member → standalone deployments don't have
            #     subprocess-recycle pressure at the same intensity
            #   * single-archive call site → for run-mode restores the
            #     PR #1529 propagation gate already empties
            #     ``_v3_origin_job_id`` for receivers; preserving that
            #     contract here means we only self-delegate when the
            #     receiver's outcome IS the job's outcome
            #   * not ``force_local`` → don't re-delegate when we're
            #     ALREADY a delegated receiver
            in_async_shc_local = (
                bool(body_params.get("_v3_origin_job_id"))
                and not force_local
                and not is_remote_owner
                and _is_shc()
            )

            if not force_local and (is_remote_owner or in_async_shc_local):
                if in_async_shc_local:
                    logger.info(
                        f"v3 SHC self-delegation (Issue #1550): "
                        f"archive={os.path.basename(str(archive_row.get('backup_archive') or ''))!r}, "
                        f"owner={owner!r} == local_server={local_server!r} — "
                        f"routing through HTTP POST to local splunkd so the "
                        f"work runs in an independent subprocess decoupled "
                        f"from the async daemon's lifecycle"
                    )
                # SHC: delegate to the peer that owns the file (which
                # may be the LOCAL peer when ``in_async_shc_local``).
                results.append(
                    self._v3_delegate_restore_to_peer(
                        request_info, archive_row, body_params,
                    )
                )
                continue

            results.append(
                self._v3_restore_one_archive(
                    request_info, service, archive_row, body_params,
                )
            )

        # Aggregate response. Status code rules:
        #   - 200 if at least one archive completed (ok or partial)
        #   - 500 if every archive failed (allows the saved-search SPL
        #     to flag the call as a failure, mirroring post_backup)
        ok_count = sum(1 for r in results if r.get("status") == "ok")
        partial_count = sum(1 for r in results if r.get("status") == "partial")
        failed_count = sum(1 for r in results if r.get("status") == "failed")

        response = {
            "response": (
                f"TrackMe 3.0.0 restore completed: ok={ok_count}, "
                f"partial={partial_count}, failed={failed_count}"
            ),
            "dry_run": dry_run,
            "backup_run_id": backup_run_id or "",
            "archives": results,
        }
        # The Splunk REST framework already wraps `payload` in the wire
        # response, so we return `response` directly (matching the legacy
        # success path's shape `{"payload": response_dict}`). Wrapping in
        # `{"response": response}` would double-nest the `response` key.
        http_status = 500 if (archives and failed_count == len(archives)) else 200

        # SHC cluster-KV completion signalling — see docstring of this
        # method for the full rationale.
        #
        # When ``_v3_origin_job_id`` is set, this call was initiated by
        # an async restore worker on a different peer
        # (``_v3_delegate_restore_to_peer`` ships the originating
        # job_id in the request body). Write the terminal status to
        # ``kv_trackme_backup_restore_jobs`` directly RIGHT HERE,
        # before returning, so the UI sees ``completed`` /
        # ``failed`` as soon as the actual work finishes — instead of
        # waiting for Splunk's REST framework to flush the HTTP
        # response back to the originating peer (which can take
        # arbitrary post-write time after saved-search CRUD).
        #
        # ``_restore_job_finalise`` is idempotent w.r.t. terminal
        # states: when the originating peer's worker later receives
        # the HTTP response and tries to finalise, the existing
        # terminal status is preserved (no overwrite).
        #
        # Gated on:
        #   * not dry_run — dry-runs are synchronous from the UI's
        #     perspective, no async job KV row exists
        #   * non-empty _v3_origin_job_id — explicit opt-in
        if not dry_run and _v3_origin_job_id:
            try:
                terminal = "completed" if http_status < 400 else "failed"
                self._restore_job_finalise(
                    request_info, _v3_origin_job_id,
                    status=terminal,
                    response=response,
                )
                logger.info(
                    f"v3 SHC delegation: receiving peer wrote terminal "
                    f"status={terminal!r} to "
                    f"kv_trackme_backup_restore_jobs for "
                    f"job_id={_v3_origin_job_id!r} (originating peer "
                    f"will see this via KV replication regardless of "
                    f"HTTP response latency)"
                )
            except Exception as e:
                # Best-effort. If this fails (KV unavailable, race with
                # cancellation, etc.) the originating peer's worker
                # will still finalise via the normal path when its
                # synchronous HTTP-POST helper returns. The KV-write
                # here is purely a latency optimisation, not a
                # correctness gate.
                logger.warning(
                    f"v3 SHC delegation: receiving peer failed to write "
                    f"terminal status to kv_trackme_backup_restore_jobs "
                    f"for job_id={_v3_origin_job_id!r}: {str(e)} — "
                    f"originating peer will finalise via the HTTP path"
                )

        return {"payload": response, "status": http_status}

    def _v3_is_shc_member(self, request_info):
        """Return True iff this splunkd instance is a Search Head Cluster
        member (i.e. ``/services/server/roles`` advertises ``shc_member``).

        Used by the SHC-local async self-delegation path in
        ``_handle_restore_3_0_0`` — see Issue #1550 for the full
        rationale. Briefly: on a SHC peer, an async restore worker is a
        daemon thread inside the persistent-REST-handler subprocess and
        that subprocess may be recycled by splunkd at any point after
        the initial HTTP response. If the work happens in-process and
        the daemon dies mid-flight, the terminal-status KV write at the
        end of ``_handle_restore_3_0_0`` is killed too and the job KV
        row is stranded at ``status=running``. Routing the work through
        an HTTP POST to the local peer's own splunkd lands it in a
        fresh, independent subprocess whose lifecycle is decoupled from
        the daemon's — the receiver writes the terminal status to KV
        before returning, so the cluster-replicated job row reaches a
        terminal state regardless of whether the originating daemon
        survived.

        Reuses the same ``shc_member`` probe pattern proven in
        ``trackme_libs_licensing.py`` lines 828-845. Best-effort:
        network / auth failures return False so the caller falls back
        to the legacy in-process path (no regression vs. pre-fix
        behaviour on a degraded SHC).
        """
        try:
            target_url = (
                f"{request_info.server_rest_uri}/services/server/roles"
            )
            headers = {
                "Authorization": f"Splunk {request_info.session_key}",
            }
            response = requests.get(
                target_url, headers=headers, verify=False, timeout=30,
            )
            if response.status_code >= 400:
                return False
            # Plain literal pattern — no regex metacharacters needed. The
            # earlier version of this pattern carried unnecessary
            # backslash-escapes (``\<``, ``\>``, ``\/``) copied from
            # ``trackme_libs_licensing.py``. Those are no-ops in current
            # Python (``\<`` is treated as the literal ``<``) but
            # constitute "unknown escapes" that future Python releases
            # may upgrade to ``re.error``. The function's outer
            # ``try/except`` would have silently swallowed such a future
            # exception → SHC detection returns False → the self-
            # delegation fix this method exists to enable is silently
            # disabled. Using the literal form removes that risk and
            # matches the same XML payload.
            return "<s:item>shc_member</s:item>" in response.text
        except Exception as e:
            logger.warning(
                f"v3 SHC member probe failed (treating as non-SHC, "
                f"in-process path will be used): {str(e)}"
            )
            return False

    def _v3_lookup_archives(self, service, backup_archive=None, backup_run_id=None):
        """Look up archives in ``kv_trackme_backup_archives_info``.

        Returns ``(rows, error_message_or_None)``. The error message is
        non-None only on KV access failure or when the input doesn't
        match the expected shape.
        """
        try:
            kv = service.kvstore["kv_trackme_backup_archives_info"]
            all_rows, _, _ = get_full_kv_collection(
                kv, "kv_trackme_backup_archives_info"
            )
        except Exception as e:
            return ([], f"Failed to read kv_trackme_backup_archives_info: {str(e)}")

        if backup_run_id:
            matched = [r for r in all_rows if r.get("backup_run_id") == backup_run_id]
            return (matched, None)

        if backup_archive:
            base = os.path.basename(str(backup_archive))
            matched = []
            for r in all_rows:
                row_path = r.get("backup_archive") or ""
                if os.path.basename(str(row_path)) == base:
                    matched.append(r)
            return (matched, None)

        return ([], "Either backup_archive or backup_run_id must be provided")

    def _v3_delegate_restore_to_peer(self, request_info, archive_row, body_params):
        """SHC delegation — invoke ``post_restore`` on the peer that owns
        the archive file. The remote handler's _handle_restore_3_0_0
        sees the row and proceeds locally.

        Returns a per-archive result dict with the standard shape so the
        run-level aggregation looks the same regardless of where the
        archive lives.
        """
        # Align ``local_server`` with the FQDN-preferring convention every
        # other write/comparison path in this release uses (#1568/#1571/
        # #1576/#1577 — see ``_resolve_canonical_server_name`` at the
        # module level). This value is consumed only as the fallback
        # default for ``owner`` when ``archive_row`` lacks a
        # ``server_name`` (corrupted / orphan row); but ``owner`` is then
        # used as the URL host in the delegation POST a few lines below,
        # so the FQDN form is the safer default — DNS resolves the FQDN
        # cluster-wide on every deployment ``post_backup``'s convention
        # was introduced to support.
        local_server = _resolve_canonical_server_name()
        owner = archive_row.get("server_name") or local_server
        archive_name = os.path.basename(str(archive_row.get("backup_archive") or ""))

        # Reuse the same hostname → FQDN fallback dance the legacy
        # delegation paths use. The connectivity probe is the existing
        # test_splunkd_connectivity helper (line ~341); it makes an
        # authenticated GET against /services/server/info on the target.
        #
        # AUTH TOKEN CHOICE — use ``session_key``, NOT ``system_authtoken``.
        #
        # In a Splunk Search Head Cluster, splunkd replicates a user's
        # ``session_key`` across all SHC peers via the cluster's session
        # storage. A token issued by the SH the user authenticated to
        # is therefore accepted by every other SH in the cluster. This
        # is the contract every legacy delegation path in this handler
        # relies on (search for ``Authorization": f"Splunk
        # {request_info.session_key}"`` in the legacy DELETE / export
        # paths) and it has shipped at scale for years.
        #
        # ``system_authtoken`` (the ``splunk-system-user`` session token
        # the persistent-server-connection framework hands the handler)
        # is NOT a cluster-wide credential — it is per-instance. A token
        # issued on SH-A is rejected on SH-B with HTTP 401
        # ``call not properly authenticated``. An earlier iteration of
        # this code preferred ``system_authtoken`` for "async-worker
        # session-expiry resilience"; that was based on a misreading of
        # how SHC trust works (``pass4SymmKey`` covers internal
        # splunkd-to-splunkd traffic, not custom REST endpoints). The
        # user's first SHC restore test surfaced the bug — sh1 → sh3
        # delegation 401'd on every call.
        #
        # Async-worker survivability: if a user submits an async restore
        # and the session_key expires mid-restore, cross-peer delegation
        # for any unfinished archives will start to 401. That is an
        # honest limitation we accept — there is no Splunk-side token
        # mechanism that is BOTH cluster-wide AND survives user-session
        # expiry. In practice this is a rare edge: even multi-GB
        # restores complete well within session lifetimes, and the
        # session is refreshed on every UI poll of the job-status
        # endpoint while the operator is watching. If it ever bites,
        # the operator just resubmits the run on the owning peer
        # directly.
        target = owner
        port = request_info.server_rest_port
        delegation_token = request_info.session_key
        if not test_splunkd_connectivity(target, port, delegation_token):
            try:
                # FQDN-suffix fallback for the case where ``owner`` is a
                # bare short hostname (legacy / pre-PR-#1568 archive rows,
                # or the empty-server_name fallback that picks up
                # ``local_server``). Cache ``getfqdn`` once so the suffix
                # extraction and the eventual fallback target stay
                # consistent.
                #
                # IMPORTANT: skip the suffix-append entirely when ``owner``
                # is already an FQDN (contains a dot). Post-PR-#1568
                # archive rows store FQDN-form ``server_name``, so the
                # naive ``f"{owner}.{fqdn_suffix}"`` would produce a
                # double-suffixed target like ``host.domain.com.domain.com``
                # which will never resolve. Bugbot finding on PR #1627.
                fqdn_target = None
                if "." not in owner:
                    local_fqdn = socket.getfqdn()
                    fqdn_suffix = (
                        local_fqdn.split(".", 1)[1] if "." in local_fqdn else "local"
                    )
                    fqdn_target = f"{owner}.{fqdn_suffix}"
                if fqdn_target and test_splunkd_connectivity(
                    fqdn_target, port, delegation_token,
                ):
                    target = fqdn_target
                else:
                    # Reflect which probes actually ran. When ``owner`` is
                    # already an FQDN the suffix-append branch is skipped
                    # and ``fqdn_target`` stays None, so the legacy
                    # "short and FQDN both failed" wording would mislead
                    # troubleshooting.
                    if fqdn_target:
                        probe_summary = (
                            f"short ({owner!r}) and FQDN-suffix fallback "
                            f"({fqdn_target!r}) both failed"
                        )
                    else:
                        probe_summary = (
                            f"FQDN form ({owner!r}) failed; no short→FQDN "
                            f"fallback applicable"
                        )
                    err_msg = (
                        f"failed_remote_unreachable: cannot reach owning peer "
                        f"{owner!r} ({probe_summary}) for "
                        f"archive={archive_name!r}"
                    )
                    logger.error(
                        f"v3 SHC delegation: archive={archive_name!r}, "
                        f"owner={owner!r}, fqdn_target={fqdn_target!r} — "
                        f"{err_msg}"
                    )
                    return {
                        "scope": archive_row.get("archive_scope") or "",
                        "tenant_id": archive_row.get("tenant_id") or "",
                        "archive_path": archive_row.get("backup_archive") or "",
                        "status": "failed",
                        "errors": [err_msg],
                    }
            except Exception as e:
                logger.exception(
                    f"v3 SHC delegation: archive={archive_name!r}, "
                    f"owner={owner!r} — connectivity probe raised"
                )
                return {
                    "scope": archive_row.get("archive_scope") or "",
                    "tenant_id": archive_row.get("tenant_id") or "",
                    "archive_path": archive_row.get("backup_archive") or "",
                    "status": "failed",
                    "errors": [f"failed_remote_unreachable: {str(e)}"],
                }

        target_url = f"https://{target}:{request_info.server_rest_port}/services/trackme/v2/backup_and_restore/restore"
        # Always delegate as SINGLE-archive (the run mode would re-invoke
        # the lookup on the remote and pull in archives the local peer
        # already handles, defeating per-peer fan-out). And always pass
        # `force_local=true` so the receiving peer goes straight to a
        # local restore instead of comparing server_name to its own
        # hostname and potentially re-delegating — that comparison can
        # mis-fire when KV stores FQDN but the peer reads short
        # hostname (or vice versa), creating an infinite delegation
        # loop. Mirrors the legacy delegation paths' contract.
        #
        # Per-archive selective restore (archives_scope): forward ONLY
        # this archive's entry to the peer. The peer dispatches as a
        # single-archive restore (force_local=True), so it'll look up
        # archives_scope[archive_name] for THIS archive — no need to
        # ship the whole map. Filtering also avoids leaking peers'
        # archive-name knowledge into a delegation that's about a
        # single file.
        peer_archives_scope = {}
        global_archives_scope = body_params.get("archives_scope") or {}
        if archive_name in global_archives_scope:
            peer_archives_scope[archive_name] = global_archives_scope[archive_name]
        request_payload = {
            "backup_archive": archive_name,
            "force_local": True,
            "dry_run": body_params.get("dry_run"),
            "restore_kvstore_collections": body_params.get("restore_kvstore_collections"),
            "kvstore_collections_scope": body_params.get("kvstore_collections_scope"),
            "kvstore_collections_clean_empty": body_params.get("kvstore_collections_clean_empty"),
            "kvstore_collections_blocklist": body_params.get(
                "kvstore_collections_blocklist", []
            ),
            "kvstore_collections_restore_non_tenants_collections": body_params.get(
                "kvstore_collections_restore_non_tenants_collections"
            ),
            "restore_knowledge_objects": body_params.get("restore_knowledge_objects"),
            "knowledge_objects_replace_existing": body_params.get("knowledge_objects_replace_existing"),
            "knowledge_objects_lists": body_params.get("knowledge_objects_lists"),
            "knowledge_objects_blocklist": body_params.get(
                "knowledge_objects_blocklist", []
            ),
            "archives_scope": peer_archives_scope,
            "restore_virtual_tenant_accounts": body_params.get("restore_virtual_tenant_accounts"),
            "restore_virtual_tenant_main_kvrecord": body_params.get("restore_virtual_tenant_main_kvrecord"),
            # SHC cluster-KV completion-signalling channel. The
            # receiving peer uses this job_id to write the terminal
            # status to ``kv_trackme_backup_restore_jobs`` directly
            # when its work completes — decoupling completion
            # visibility from the HTTP response latency. Empty when
            # the call is not part of an async-dispatched restore.
            "_v3_origin_job_id": body_params.get("_v3_origin_job_id") or "",
        }
        headers = {
            # Same session_key chosen above — the SHC-replicated user
            # session token, accepted by every peer in the cluster.
            # See the AUTH TOKEN CHOICE comment block at the top of
            # this method for the full rationale.
            "Authorization": f"Splunk {delegation_token}",
            "Content-Type": "application/json",
        }
        logger.info(
            f"v3 SHC delegation: archive={archive_name!r}, "
            f"local_server={local_server!r} → target={target!r}, "
            f"dry_run={request_payload.get('dry_run')!r} — "
            f"POST starting (timeout=1800s)"
        )
        # Timeout intentionally generous (1800s = 30 min). At
        # large-scale production deployments a single archive's
        # restore on the receiving SH can legitimately take many
        # minutes — large KV collections, many knowledge objects,
        # slow splunkd config-refresh cycles, etc. Tightening this
        # to a more aggressive bound risked false-failure timeouts
        # on healthy-but-slow restores. Mirrors the legacy v2
        # delegation timeout. See PR #1523 review feedback.
        try:
            response = requests.post(
                target_url,
                headers=headers,
                data=json.dumps(request_payload),
                verify=False,
                timeout=1800,
            )
        except Exception as e:
            logger.exception(
                f"v3 SHC delegation: archive={archive_name!r}, "
                f"target={target!r} — POST raised"
            )
            return {
                "scope": archive_row.get("archive_scope") or "",
                "tenant_id": archive_row.get("tenant_id") or "",
                "archive_path": archive_row.get("backup_archive") or "",
                "status": "failed",
                "errors": [f"failed_remote_unreachable: peer call exception: {str(e)}"],
            }
        logger.info(
            f"v3 SHC delegation: archive={archive_name!r}, "
            f"target={target!r} — POST returned http_status={response.status_code}"
        )

        if response.status_code >= 400:
            # Truncate the body to keep splunkd.log readable but include
            # enough to identify the error class (HTTP 401 with the
            # ``call not properly authenticated`` message, HTTP 5xx with
            # the splunkd error trace, etc.). The full body is preserved
            # in the response payload for the operator-facing UI.
            body_excerpt = (response.text or "")[:500]
            logger.error(
                f"v3 SHC delegation FAILED: archive={archive_name!r}, "
                f"target={target!r}, http_status={response.status_code}, "
                f"body_excerpt={body_excerpt!r}"
            )
            return {
                "scope": archive_row.get("archive_scope") or "",
                "tenant_id": archive_row.get("tenant_id") or "",
                "archive_path": archive_row.get("backup_archive") or "",
                "status": "failed",
                "errors": [
                    f"remote peer {target!r} returned HTTP "
                    f"{response.status_code}: {response.text[:200]}"
                ],
            }

        try:
            # The peer's handler returns {"payload": <response_dict>, ...}
            # and Splunk's REST framework unwraps `payload` onto the wire,
            # so `response.json()` gives us the response dict directly.
            remote_payload = response.json() or {}
            remote_archives = remote_payload.get("archives") or []
            if remote_archives:
                # Return the remote's per-archive summary — annotated so
                # the operator can tell where the work happened.
                remote_first = remote_archives[0]
                remote_first.setdefault("delegated_from", local_server)
                remote_first.setdefault("delegated_to", target)
                # Promote remote-side per-archive errors to splunkd.log
                # on the originating peer too — without this, an
                # operator grepping splunkd.log on sh1 for a sh1→sh3
                # delegated restore would see the dispatch but not
                # the outcome (the outcome lives in sh3's splunkd.log).
                remote_status = remote_first.get("status") or ""
                remote_errs = remote_first.get("errors") or []
                if remote_status in ("failed", "partial") or remote_errs:
                    logger.error(
                        f"v3 SHC delegation outcome: archive={archive_name!r}, "
                        f"target={target!r}, remote_status={remote_status!r}, "
                        f"remote_errors={remote_errs!r}"
                    )
                else:
                    logger.info(
                        f"v3 SHC delegation outcome: archive={archive_name!r}, "
                        f"target={target!r}, remote_status={remote_status!r}"
                    )
                return remote_first
            logger.info(
                f"v3 SHC delegation outcome: archive={archive_name!r}, "
                f"target={target!r}, http_status={response.status_code} "
                f"(no per-archive entries in remote response)"
            )
            return {
                "scope": archive_row.get("archive_scope") or "",
                "tenant_id": archive_row.get("tenant_id") or "",
                "archive_path": archive_row.get("backup_archive") or "",
                "status": "ok" if response.status_code == 200 else "partial",
                "errors": [],
                "delegated_to": target,
                "remote_response": remote_payload,
            }
        except Exception as e:
            logger.exception(
                f"v3 SHC delegation: archive={archive_name!r}, "
                f"target={target!r} — failed to parse remote response"
            )
            return {
                "scope": archive_row.get("archive_scope") or "",
                "tenant_id": archive_row.get("tenant_id") or "",
                "archive_path": archive_row.get("backup_archive") or "",
                "status": "partial",
                "errors": [f"could not parse remote peer response: {str(e)}"],
                "delegated_to": target,
            }

    def _v3_restore_one_archive(self, request_info, service, archive_row, body_params):
        """Restore ONE 3.0.0 archive whose file lives on this SH.

        Honours the no-raise contract: any unexpected exception is
        captured into the returned summary's ``errors`` and ``status``
        fields rather than propagating up and aborting the run loop.

        Selective restore (``body_params["archives_scope"]``) — when an
        entry exists for THIS archive's filename, its ``collections``
        and ``knowledge_objects`` lists override the flat filters.
        Computed once at the top of the method and passed into the
        per-helper calls below; archives absent from the map fall
        through to the flat-filter behaviour unchanged.
        """
        archive_path = archive_row.get("backup_archive") or ""
        archive_scope = archive_row.get("archive_scope") or ""
        tenant_id = archive_row.get("tenant_id") or ""
        run_id = archive_row.get("backup_run_id") or ""
        dry_run = bool(body_params.get("dry_run", True))

        # Resumable-restore: the async dispatcher threads its job_id
        # through ``body_params["_v3_task_tracking_job_id"]``. When
        # set, we gate every step on the task-list checkpoint state so
        # a resumed worker skips work that was already done by the
        # previous (now-dead) worker. When unset (synchronous restore
        # or no async wrapper), every helper below is a no-op — the
        # method behaves as before.
        #
        # NOTE: this is the TASK TRACKING job_id, distinct from
        # ``_v3_origin_job_id``. The latter is gated on single-archive
        # mode (for SHC-delegation aggregation correctness — see the
        # ``_propagate_job_id_to_receivers`` block in
        # ``_handle_restore_3_0_0``). Task tracking, by contrast, MUST
        # work for both single-archive and multi-archive run-mode
        # restores; gating it the same way would lose progress
        # tracking for whole-run restores.
        _resume_job_id = body_params.get("_v3_task_tracking_job_id") or ""
        _archive_filename_for_tasks = os.path.basename(archive_path)
        _task_prefix = f"arch:{_archive_filename_for_tasks}"

        def _task_done(task_id):
            """Returns True if the task is already in a terminal state
            (done/skipped) according to KV. Loads tasks fresh so a
            concurrent resume worker's writes are visible."""
            if not _resume_job_id:
                return False
            tasks, _ = self._restore_job_load_tasks(
                request_info, _resume_job_id,
            )
            return self._restore_job_is_task_done(tasks, task_id)

        def _task_status(task_id):
            """Returns the task's current KV status string
            (``"done"`` / ``"skipped"`` / ``"failed"`` /
            ``"in_progress"`` / ``"pending"``) or ``None`` if not in
            async mode or task absent. Used by the resume worker to
            distinguish prior-``done`` from prior-``skipped`` so the
            operator-visible ``tasks`` list reflects what actually
            happened. Bugbot finding on AI-Agent-sync PR #1648."""
            if not _resume_job_id:
                return None
            tasks, _ = self._restore_job_load_tasks(
                request_info, _resume_job_id,
            )
            return self._restore_job_get_task_status(tasks, task_id)

        def _task_mark(task_id, status, error_msg="", info_dict=None):
            """Mark a task transition in KV. No-op when not in async
            mode (resume_job_id empty). Status: in_progress / done /
            skipped / failed. ``info_dict`` (optional) stores outcome
            bools the resumed worker needs to read back via
            ``_task_info`` when skipping a previously-done task.
            """
            if not _resume_job_id:
                return
            self._restore_job_mark_task(
                request_info, _resume_job_id, task_id, status,
                error_msg=error_msg,
                info_dict=info_dict,
            )

        def _task_info(task_id):
            """Read the ``info`` dict for a task from KV. Returns
            ``{}`` when not in async mode or no info recorded. Used by
            the resumed worker to recover outcome bools on skip."""
            if not _resume_job_id:
                return {}
            tasks_now, _ = self._restore_job_load_tasks(
                request_info, _resume_job_id,
            )
            return self._restore_job_get_task_info(tasks_now, task_id)

        # Resolve per-archive selective-restore overrides. The keys in
        # archives_scope are bare filenames (matches the way archives
        # surface in dry-run previews and in the run manifest), so
        # we key off basename(archive_path). Falling back to the flat
        # filters preserves CLI / SPL compatibility — those callers
        # never populate archives_scope. Resolution lives in
        # trackme_libs_backup_archive.resolve_per_archive_filters so
        # the override semantics are unit-testable without spinning
        # up the handler runtime — see
        # unit_tests/check_backup_archives_scope.py.
        archives_scope = body_params.get("archives_scope") or {}
        archive_filename = os.path.basename(archive_path)
        _filters = _bbk_resolve_per_archive_filters(
            archives_scope,
            archive_filename,
            body_params.get("kvstore_collections_scope", "all"),
            body_params.get("knowledge_objects_lists", "all"),
        )
        effective_kv_scope = _filters["effective_kv_scope"]
        effective_ko_list = _filters["effective_ko_list"]
        # Track whether we narrowed via archives_scope vs flat filter
        # so the response surfaces this for the operator's audit trail.
        # (A 200 response with selective_restore=true tells you what
        # got restored is a strict subset of what's in the archive —
        # without this signal an operator reading the response can't
        # tell apart "I restored everything" from "I restored only
        # the things I explicitly selected".)
        selective_restore = bool(_filters["selective"])

        # Defensive defaults so the no-raise contract holds even if a
        # variable used in the failure-return path isn't reached. The
        # accumulator is named ``errs`` consistently — the catch-all
        # except block at the bottom of this method reads from it, so
        # any partial-restore errors collected before an unexpected
        # exception are still surfaced in the response (rather than
        # being silently lost).
        extract_dir = None
        errs = []

        try:
            if not os.path.isfile(archive_path):
                return {
                    "scope": archive_scope,
                    "tenant_id": tenant_id,
                    "run_id": run_id,
                    "archive_path": archive_path,
                    "status": "failed",
                    "errors": [
                        f"archive file not found on disk: {archive_path}. "
                        f"The KV row claims it exists but the filesystem "
                        f"disagrees — was it deleted out-of-band?"
                    ],
                }

            # Extract under a unique temp dir alongside the archive so
            # the legacy cleanup_backup_directories sweep also picks up
            # any leftovers if we crash mid-restore.
            stem = os.path.basename(archive_path)
            for ext in (".tar.zst", ".tgz"):
                if stem.endswith(ext):
                    stem = stem[: -len(ext)]
                    break
            backup_root = os.path.dirname(archive_path)
            extract_dir = os.path.join(
                backup_root, f"trackme-backup-restore-{stem}-{int(time.time())}"
            )
            os.makedirs(extract_dir, exist_ok=True)

            # Extract task — ALWAYS re-runs on resume regardless of
            # previous worker's mark, because the extract_dir is
            # cleaned up at end-of-run (and may also be swept by the
            # cleanup_backup_directories age filter). Tracking is for
            # operator visibility, not for skip-on-resume.
            _task_mark(f"{_task_prefix}:step:extract", "in_progress")
            ok = extract_archive(archive_path, extract_dir)
            if not ok:
                _task_mark(
                    f"{_task_prefix}:step:extract", "failed",
                    error_msg=f"archive extraction failed: {archive_path}",
                )
                return {
                    "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                    "archive_path": archive_path, "status": "failed",
                    "errors": [f"archive extraction failed: {archive_path}"],
                }
            _task_mark(f"{_task_prefix}:step:extract", "done")

            manifest = _bbk_read_in_archive_manifest(extract_dir)
            if manifest is None:
                return {
                    "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                    "archive_path": archive_path, "status": "failed",
                    "errors": [
                        "in-archive manifest.json missing — this is the "
                        "source-of-truth signal for 3.0.0 restore. The "
                        "archive may have been produced by a buggy build "
                        "(skip the manifest write), been corrupted, or "
                        "be a legacy archive misclassified as 3.0.0.",
                    ],
                }
            if manifest.get("archive_schema_version") != ARCHIVE_SCHEMA_VERSION:
                return {
                    "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                    "archive_path": archive_path, "status": "failed",
                    "errors": [
                        f"unexpected archive_schema_version in manifest: "
                        f"{manifest.get('archive_schema_version')!r} "
                        f"(expected {ARCHIVE_SCHEMA_VERSION!r})",
                    ],
                }

            manifest_scope = manifest.get("archive_scope") or ""
            manifest_tenant = manifest.get("tenant_id") or ""

            # Sanity-check KV row ↔ manifest agreement. A mismatch means
            # the row was pointed at the wrong file (e.g. operator copied
            # an archive between deployments and re-keyed). Refuse to
            # restore — the wrong tenant's data into ours would be
            # catastrophic.
            if manifest_scope != archive_scope or manifest_tenant != tenant_id:
                return {
                    "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                    "archive_path": archive_path, "status": "failed",
                    "errors": [
                        f"manifest/KV mismatch — KV says scope={archive_scope!r} "
                        f"tenant_id={tenant_id!r}, but the archive's manifest "
                        f"declares scope={manifest_scope!r} tenant_id={manifest_tenant!r}. "
                        f"Refusing to restore to avoid cross-tenant data leak.",
                    ],
                }

            # In dry-run mode we already know what would be restored
            # (the manifest is parsed). Return a preview without
            # mutating any KV.
            #
            # ENRICHMENT (selective-restore feature): also surface the
            # actual list of KO titles available in this archive
            # (manifest carries only counts). Frontend uses this as
            # the source of truth for the per-archive KO multiselect —
            # without it the multiselect would have to either re-fetch
            # the manifest or run a second probe of the archive,
            # neither of which is available without dry-run output.
            #
            # CRITICAL: this whole block is gated on `if dry_run:`. An
            # unconditional return here would short-circuit every
            # restore (dry-run or not) and the actual KV-mutating
            # logic below would become dead code — see bugbot review
            # of aaafd7b8.
            if dry_run:
                available_ko_titles = []
                kos_file_for_preview = manifest.get("knowledge_objects_file")
                if (
                    archive_scope == ARCHIVE_SCOPE_TENANT
                    and kos_file_for_preview
                ):
                    try:
                        kos_path = os.path.join(extract_dir, kos_file_for_preview)
                        with open(kos_path) as f:
                            kos_data_for_preview = json.load(f)
                        # The KO json is a dict keyed by title — preserve
                        # ordering for a deterministic multiselect render
                        # (sorted titles), and cap at a sane upper bound
                        # so a tenant with thousands of KOs doesn't bloat
                        # the response.
                        available_ko_titles = sorted(
                            list(kos_data_for_preview.keys())
                        )[:5000]
                    except Exception as e:
                        # Best-effort — a KO-list parse failure must not
                        # fail the dry-run as a whole. The frontend
                        # gracefully degrades to "all KOs" (the existing
                        # default) if the array is missing.
                        logger.warning(
                            f'dry-run: failed to enumerate KO titles from '
                            f'{kos_file_for_preview!r}: {str(e)}'
                        )
                        available_ko_titles = []
                return {
                    "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                    "archive_path": archive_path,
                    "archive_filename": archive_filename,
                    "status": "ok",
                    "dry_run": True,
                    "preview": {
                        "collections": [c.get("name") for c in manifest.get("collections", [])],
                        "collection_count": len(manifest.get("collections", [])),
                        "knowledge_objects": manifest.get("knowledge_objects") or {},
                        # NEW (selective restore): list of KO title strings
                        # the operator can pick in the multiselect. Empty
                        # list for global archives (no KOs by design).
                        "available_knowledge_objects": available_ko_titles,
                        "vtenant_account_file": manifest.get("vtenant_account_file"),
                        "knowledge_objects_file": manifest.get("knowledge_objects_file"),
                        "manifest_failures_at_seal": manifest.get("failures") or [],
                    },
                    "errors": [],
                }

            # ---- actual restore ------------------------------------------
            tasks = []
            # NB: `errs` is initialised at the top of the function so the
            # outer except handler can surface any partial errors collected
            # here even if a later step raises unexpectedly.

            # Diagnostic logging at every step transition. The async
            # restore worker on the originating SH waits on the HTTP
            # response from the receiving SH (in SHC delegation mode);
            # without these logs an operator cannot tell which step
            # the receiving SH is in (or where it might be stuck).
            # Cheap and additive — restoring a tenant emits ~6 INFO
            # lines per archive, vastly outweighed by the ~100s of
            # per-KO INFO lines the existing path already emits.
            logger.info(
                f"v3 restore: starting archive={archive_filename!r} "
                f"scope={archive_scope!r} tenant_id={tenant_id!r}"
            )

            # 1. Tenant central-record sync (tenant scope only).
            #
            #    A tenant archive does NOT carry kv_trackme_virtual_tenants
            #    — that collection lives in the GLOBAL archive of the same
            #    run. Without this step, a single-tenant restore would
            #    silently inherit whatever the live deployment currently
            #    holds in kv_trackme_virtual_tenants for this tenant, which
            #    may have drifted from backup time (component flags
            #    toggled, schema_version bumped, tenant_dsm_hybrid_objects
            #    JSON edited, RBAC roles changed). That makes the restore
            #    inconsistent: the per-tenant KV collections land at
            #    backup-time state but the central registry record stays
            #    live.
            #
            #    Two-stage operation — ORDER MATTERS:
            #
            #    Stage 1a (infrastructure guard, FIRST):
            #    ``_v3_recreate_missing_tenant_if_needed`` is the only
            #    path that calls ``post_add_tenant`` to materialise the
            #    full tenant infrastructure (per-tenant KV collections,
            #    ACLs, transforms, saved searches, tracker schedules)
            #    when the tenant has been deleted out-of-band. It must
            #    run BEFORE the record overlay below — otherwise stage
            #    1b's KV upsert would put a tenant record in
            #    ``kv_trackme_virtual_tenants`` first, stage 1a's
            #    "if tenant exists, no-op" check at line ~8138 would
            #    short-circuit and skip the infrastructure recreation,
            #    and stage 4 (KV records restore) would then fail
            #    writing the archive's records to non-existent
            #    per-tenant collections.
            #
            #    Stage 1b (central-record overlay, SECOND):
            #    ``_v3_restore_tenant_main_record_from_global`` finds
            #    the global archive of the same run on this SH, reads
            #    its ``kv_trackme_virtual_tenants.json`` snapshot, and
            #    overlays the gold-standard record for this tenant_id
            #    onto whatever is currently in the live KV (whether
            #    that's the just-recreated record from stage 1a or a
            #    pre-existing, possibly stale, record).
            #
            #    Outcome matrix:
            #      * Existing tenant + global archive available →
            #        1a no-op, 1b overlays from global. Record reflects
            #        backup-time state.
            #      * Existing tenant + global archive missing →
            #        1a no-op, 1b returns (False, None) and no-ops.
            #        Live record stays (existing pre-PR behaviour).
            #      * Deleted tenant + global archive available →
            #        1a recreates full infrastructure (with a deduced
            #        record), 1b overlays the gold-standard record on
            #        top. Subsequent KV-records restore at stage 4
            #        succeeds because the per-tenant collections now
            #        exist.
            #      * Deleted tenant + global archive missing →
            #        1a recreates full infrastructure with the deduced
            #        record from the in-archive vtenant_account JSON,
            #        1b no-ops. Existing behaviour preserved.
            #
            #    The deleted-tenant + global-available case was the
            #    original PR #1633 regression caught by bugbot 13044ada:
            #    running 1b first short-circuited 1a, breaking
            #    infrastructure recreation.
            tenant_recreated = False
            tenant_record_restored_from_global = False
            if archive_scope == ARCHIVE_SCOPE_TENANT and bool(
                body_params.get("restore_virtual_tenant_main_kvrecord", True)
            ):
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 1/4 (tenant central-record sync) — start"
                )
                # Stage 1a: infrastructure guard (no-op if tenant exists).
                _t1a = f"{_task_prefix}:step:step_1a_safety_guard"
                if _task_done(_t1a):
                    # Recover the original worker's outcome from the
                    # task's ``info`` field so the response dict
                    # reports the correct ``tenant_recreated``.
                    # Without this, the resumed worker's hardcoded
                    # False would misrepresent a True result from the
                    # original worker. Bugbot finding on PR #1647
                    # (Low).
                    _info1a = _task_info(_t1a)
                    tenant_recreated = bool(_info1a.get("tenant_recreated", False))
                    recreate_err = None
                    logger.info(
                        f"v3 restore: archive={archive_filename!r} "
                        f"resumed worker skipping {_t1a} (already done, "
                        f"recovered tenant_recreated={tenant_recreated})"
                    )
                else:
                    _task_mark(_t1a, "in_progress")
                    tenant_recreated, recreate_err = self._v3_recreate_missing_tenant_if_needed(
                        service, tenant_id, extract_dir, manifest, request_info,
                    )
                    if recreate_err:
                        errs.append(recreate_err)
                        _task_mark(_t1a, "failed", error_msg=recreate_err)
                    else:
                        # Store the bool so a resumed worker can
                        # recover the accurate value on skip.
                        _task_mark(
                            _t1a, "done",
                            info_dict={"tenant_recreated": tenant_recreated},
                        )

                # Stage 1b: central-record overlay from the global archive.
                # Runs after 1a — for the existing-tenant case it syncs
                # the live record back to backup-time state; for the
                # just-recreated-tenant case it overwrites the deduced
                # record from 1a with the authoritative one from the
                # global archive's ``kv_trackme_virtual_tenants.json``
                # snapshot.
                #
                # GATE: skip 1b when 1a returned an error (``recreate_err``
                # set). 1a's error mode is ``post_add_tenant`` failing
                # to create the per-tenant KV collections / ACLs /
                # transforms / tracker schedules for a deleted tenant.
                # If 1b still ran in that case it would insert the
                # tenant record into ``kv_trackme_virtual_tenants``
                # without the backing infrastructure — on operator
                # retry, 1a's "tenant exists?" early-return at line
                # ~8228 would find that orphan record and silently skip
                # the infrastructure recreation that's still needed,
                # permanently poisoning the retry path. Step 4 (KV
                # records restore) would then fail writing the
                # archive's records to non-existent per-tenant
                # collections with no clear root-cause signal.
                #
                # Bugbot finding on PR #1639 (sync of #1633 to AI Agent
                # branch): "Stage 1b poisons retry when 1a fails for
                # deleted tenant". The root regression is in this
                # ``_handle_restore_3_0_0`` step 1/4 (introduced by
                # #1633), so the fix lands on ``version_2323`` and
                # flows back through the normal sync cycle.
                _t1b = f"{_task_prefix}:step:step_1b_global_overlay"
                if recreate_err:
                    logger.warning(
                        f"v3 restore: archive={archive_filename!r} "
                        f"step 1b skipped (stage 1a returned error: "
                        f"{recreate_err!r}). Skipping the central-"
                        f"record overlay avoids inserting a tenant "
                        f"record into kv_trackme_virtual_tenants "
                        f"without the backing per-tenant collections, "
                        f"which would poison any operator retry by "
                        f"making stage 1a's 'tenant exists?' check "
                        f"early-return and skip the infrastructure "
                        f"recreation."
                    )
                    # IMPORTANT: do NOT mark 1b as ``skipped`` here.
                    # 1a's failure is a TRANSIENT gate — on resume,
                    # 1a re-runs (``failed`` is non-terminal); if 1a
                    # then succeeds, 1b becomes applicable again.
                    # Marking 1b ``skipped`` (terminal) would
                    # permanently bypass 1b on the next worker
                    # iteration, leaving the tenant with 1a's deduced
                    # record instead of the authoritative global-
                    # archive overlay. Leaving 1b's status untouched
                    # (``pending``) lets a future iteration re-
                    # evaluate the gate based on the then-current
                    # ``recreate_err`` value. Bugbot finding on PR
                    # #1647 (Medium).
                elif _task_done(_t1b):
                    # Recover the original worker's outcome for the
                    # response dict — mirrors the 1a pattern above.
                    _info1b = _task_info(_t1b)
                    tenant_record_restored_from_global = bool(
                        _info1b.get("tenant_record_restored_from_global", False)
                    )
                    logger.info(
                        f"v3 restore: archive={archive_filename!r} "
                        f"resumed worker skipping {_t1b} (already done, "
                        f"recovered restored_from_global="
                        f"{tenant_record_restored_from_global})"
                    )
                else:
                    _task_mark(_t1b, "in_progress")
                    tenant_record_restored_from_global, restore_err = (
                        self._v3_restore_tenant_main_record_from_global(
                            service, tenant_id, manifest.get("run_id"),
                        )
                    )
                    if restore_err:
                        errs.append(restore_err)
                        _task_mark(_t1b, "failed", error_msg=restore_err)
                    else:
                        # Store the bool so a resumed worker can
                        # recover the accurate value on skip.
                        _task_mark(
                            _t1b, "done",
                            info_dict={
                                "tenant_record_restored_from_global":
                                    tenant_record_restored_from_global,
                            },
                        )
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 1/4 — done "
                    f"(tenant_recreated={tenant_recreated}, "
                    f"restored_from_global={tenant_record_restored_from_global})"
                )

            # 2. Restore vtenant_account record (if file present and
            #    enabled by body params).
            if archive_scope == ARCHIVE_SCOPE_TENANT and bool(
                body_params.get("restore_virtual_tenant_accounts", True)
            ):
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 2/4 (vtenant_account) — start"
                )
                _t2 = f"{_task_prefix}:step:step_2_vtenant_account"
                _t2_prior_status = _task_status(_t2)
                if _t2_prior_status == "done":
                    # Preserve the human-readable description so the
                    # terminal response reflects work the original
                    # worker did, not just this resumed worker.
                    # Bugbot finding on PR #1647 (Low).
                    tasks.append(
                        f"restored vtenant_account for tenant_id="
                        f"{tenant_id!r} (preserved from earlier worker)"
                    )
                    logger.info(
                        f"v3 restore: archive={archive_filename!r} "
                        f"resumed worker skipping {_t2} (already done)"
                    )
                elif _t2_prior_status == "skipped":
                    # Original worker recorded NO restore work (e.g. no
                    # ``vtenant_account_file`` in the archive manifest,
                    # or ``restore_virtual_tenant_accounts=false`` in
                    # body_params on the original call). Do NOT append
                    # the misleading
                    # ``"restored vtenant_account ... (preserved from earlier worker)"``
                    # line to the operator-visible task list — match
                    # the fresh-worker behaviour, which also emits
                    # nothing to ``tasks`` on this skip path (the
                    # forensic ``status=skipped`` record persists in
                    # KV via the original ``_task_mark`` call). Bugbot
                    # finding on AI-Agent-sync PR #1648 (Low), upstream
                    # SHA ``5e827a51`` (PR #1647).
                    logger.info(
                        f"v3 restore: archive={archive_filename!r} "
                        f"resumed worker skipping {_t2} "
                        f"(prior status=skipped — original worker "
                        f"recorded no restore work)"
                    )
                else:
                    vacc_file = manifest.get("vtenant_account_file")
                    if vacc_file:
                        _task_mark(_t2, "in_progress")
                        vacc_err = self._v3_restore_vtenant_account(
                            request_info, tenant_id, extract_dir, vacc_file,
                        )
                        if vacc_err:
                            errs.append(vacc_err)
                            _task_mark(_t2, "failed", error_msg=vacc_err)
                        else:
                            tasks.append(f"restored vtenant_account for tenant_id={tenant_id!r}")
                            _task_mark(_t2, "done")
                    else:
                        # No vacc file in manifest — nothing to do.
                        # Mark as skipped (not done) so the absence is
                        # visible in the forensic task list.
                        _task_mark(
                            _t2, "skipped",
                            error_msg="no vtenant_account_file in manifest",
                        )
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 2/4 — done"
                )

            # 3. Restore knowledge objects (if file present and enabled).
            #    `effective_ko_list` is `archives_scope[arc].knowledge_objects`
            #    if that map has an entry for THIS archive, else falls
            #    back to the flat `knowledge_objects_lists` from
            #    body_params. Computed at the top of this method.
            if archive_scope == ARCHIVE_SCOPE_TENANT and bool(
                body_params.get("restore_knowledge_objects", True)
            ):
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 3/4 (knowledge objects) — start"
                )
                _t3 = f"{_task_prefix}:step:step_3_knowledge_objects"
                _t3_prior_status = _task_status(_t3)
                if _t3_prior_status == "done":
                    # Preserve the human-readable description (see
                    # step 2 comment above). Bugbot finding on PR
                    # #1647 (Low).
                    tasks.append(
                        f"restored knowledge_objects for tenant_id="
                        f"{tenant_id!r} (preserved from earlier worker)"
                    )
                    logger.info(
                        f"v3 restore: archive={archive_filename!r} "
                        f"resumed worker skipping {_t3} (already done)"
                    )
                elif _t3_prior_status == "skipped":
                    # Mirrors the step-2 ``skipped`` branch above —
                    # original worker recorded no KO restore work
                    # (no ``knowledge_objects_file`` in manifest, or
                    # ``restore_knowledge_objects=false`` in
                    # body_params). Suppress the misleading
                    # ``(preserved from earlier worker)`` line.
                    # Bugbot finding on AI-Agent-sync PR #1648 (Low),
                    # upstream SHA ``5e827a51`` (PR #1647).
                    logger.info(
                        f"v3 restore: archive={archive_filename!r} "
                        f"resumed worker skipping {_t3} "
                        f"(prior status=skipped — original worker "
                        f"recorded no restore work)"
                    )
                else:
                    kos_file = manifest.get("knowledge_objects_file")
                    if kos_file:
                        _task_mark(_t3, "in_progress")
                        ko_err = self._v3_restore_knowledge_objects(
                            request_info, service, tenant_id, extract_dir, kos_file,
                            body_params.get("knowledge_objects_replace_existing", True),
                            effective_ko_list,
                            body_params.get("knowledge_objects_blocklist", []),
                        )
                        if ko_err:
                            errs.append(ko_err)
                            _task_mark(_t3, "failed", error_msg=ko_err)
                        else:
                            tasks.append(f"restored knowledge_objects for tenant_id={tenant_id!r}")
                            _task_mark(_t3, "done")
                    else:
                        _task_mark(
                            _t3, "skipped",
                            error_msg="no knowledge_objects_file in manifest",
                        )
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 3/4 — done"
                )

            # 4. Restore KV collections (if enabled).
            #
            # Two enable conditions are stacked:
            #   * `restore_kvstore_collections` — global on/off
            #   * `kvstore_collections_restore_non_tenants_collections`
            #     — when False, suppress KV restore on the GLOBAL archive
            #     specifically (its KV collections are by definition the
            #     non-tenant ones — kv_trackme_virtual_tenants,
            #     maintenance_mode, bank_holidays, ML models, etc.).
            #     Tenant archives are unaffected by this flag.
            kv_summary = []
            kv_enabled = bool(body_params.get("restore_kvstore_collections", True))
            if (
                archive_scope == ARCHIVE_SCOPE_GLOBAL
                and not bool(body_params.get(
                    "kvstore_collections_restore_non_tenants_collections", True,
                ))
            ):
                kv_enabled = False
                tasks.append(
                    "skipped KV restore for global archive "
                    "(kvstore_collections_restore_non_tenants_collections=false)"
                )
            _t4 = f"{_task_prefix}:step:step_4_kv"
            if not kv_enabled:
                # The flag-driven skip path above already logged its
                # reasoning and pushed to ``tasks``. Mark the task as
                # ``skipped`` so the forensic record matches.
                _task_mark(
                    _t4, "skipped",
                    error_msg="kv_enabled=false",
                )
            elif _task_done(_t4):
                # Preserve the human-readable description for step 4
                # so the terminal response reflects work the original
                # worker did. Bugbot finding on PR #1647 (Low).
                tasks.append(
                    f"restored KV records ({archive_filename}) "
                    f"(preserved from earlier worker)"
                )
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"resumed worker skipping {_t4} (already done)"
                )
                kv_summary = []
                kv_errs = []
            else:
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 4/4 (KV records) — start"
                )
                _task_mark(_t4, "in_progress")
                # `effective_kv_scope` honours archives_scope first
                # (per-archive selective restore), falls through to the
                # flat `kvstore_collections_scope` otherwise. Computed
                # at the top of this method.
                kv_summary, kv_errs = self._v3_restore_kv_collections_from_manifest(
                    service, extract_dir, manifest,
                    request_info=request_info,
                    tenant_id=tenant_id,
                    scope_filter=effective_kv_scope,
                    clean_empty=body_params.get("kvstore_collections_clean_empty", True),
                    blocklist=body_params.get("kvstore_collections_blocklist", []),
                )
                if kv_errs:
                    _task_mark(
                        _t4, "failed",
                        error_msg=f"{len(kv_errs)} collection errors: "
                        f"{'; '.join(str(e) for e in kv_errs[:3])}",
                    )
                else:
                    _task_mark(_t4, "done")
                logger.info(
                    f"v3 restore: archive={archive_filename!r} "
                    f"step 4/4 — done (collections={len(kv_summary)}, "
                    f"errors={len(kv_errs)})"
                )
                errs.extend(kv_errs)

            archive_status = "ok" if not errs else "partial"
            logger.info(
                f"v3 restore: archive={archive_filename!r} — "
                f"all 4 steps done. status={archive_status!r}, "
                f"errors_count={len(errs)}"
            )
            return {
                "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                "archive_path": archive_path,
                "archive_filename": archive_filename,
                "status": archive_status,
                "tasks": tasks,
                "errors": errs,
                # True when step 1/4 stage 1a recreated the full tenant
                # infrastructure via post_add_tenant because the tenant
                # was absent from kv_trackme_virtual_tenants. May be True
                # simultaneously with tenant_record_restored_from_global
                # (the deleted-tenant + global-available case): 1a
                # rebuilds the per-tenant KV collections + ACLs +
                # transforms + tracker schedules with a deduced record,
                # 1b then overlays the gold-standard record on top.
                "tenant_recreated": tenant_recreated,
                # True when step 1/4 stage 1b successfully overlaid the
                # tenant's central record in kv_trackme_virtual_tenants
                # from the global archive of the same run. False means
                # either the global archive wasn't available on this SH
                # (record left at whatever stage 1a wrote, or
                # pre-existing live state), or the archive wasn't a
                # tenant archive.
                "tenant_record_restored_from_global": tenant_record_restored_from_global,
                "kvstore_records_restore_summary": kv_summary,
                # True when archives_scope narrowed the restore for
                # this archive. Lets the operator (and the audit log)
                # tell apart "everything was restored" from "only the
                # explicitly selected items were restored".
                "selective_restore": selective_restore,
            }
        except Exception as e:
            logger.exception(
                f'unhandled exception in _v3_restore_one_archive for '
                f'archive_path={archive_path!r}'
            )
            return {
                "scope": archive_scope, "tenant_id": tenant_id, "run_id": run_id,
                "archive_path": archive_path, "status": "failed",
                # `errs` carries any partial-restore errors collected
                # before this exception. Concatenate so the operator sees
                # both the in-flight failures and the final exception.
                "errors": list(errs) + [f"unhandled exception: {str(e)}"],
            }
        finally:
            # Best-effort temp dir cleanup.
            if extract_dir and os.path.isdir(extract_dir):
                try:
                    shutil.rmtree(extract_dir, ignore_errors=True)
                except Exception:
                    pass

    def _v3_restore_tenant_main_record_from_global(
        self, service, tenant_id, run_id,
    ):
        """Restore the tenant's record in ``kv_trackme_virtual_tenants``
        from the GLOBAL archive of the same backup run.

        Returns ``(restored: bool, error_or_None)``. When ``restored`` is
        ``False`` AND ``error_or_None`` is ``None``, the caller falls
        through to the existing missing-tenant safety guard. Any
        unexpected exception is caught, logged, and surfaced as
        ``error_or_None`` (the restore continues — this stage is
        best-effort).

        Why this exists
        ---------------

        A tenant archive does NOT carry the global
        ``kv_trackme_virtual_tenants`` collection — that collection is
        in the GLOBAL archive of the same run. Without this step, a
        single-tenant restore would silently inherit whatever the live
        deployment currently holds for this tenant's central registry
        record, which may have drifted from backup time (component
        flags toggled, ``schema_version`` bumped,
        ``tenant_dsm_hybrid_objects`` JSON edited, RBAC roles changed).
        That made the restore inconsistent: per-tenant KV collections
        landed at backup-time state but the central registry record
        stayed live.

        Algorithm
        ---------

        1. Find the global archive row for ``run_id`` in
           ``kv_trackme_backup_archives_info``. If absent → return
           ``(False, None)`` so the caller can try the safety guard.
        2. Verify the archive file exists on this SH's filesystem. In
           SHC, single-tenant restore is delegated to the SH that owns
           the tenant archive; by the design of ``post_backup``, the
           global archive of the same run lives on the same SH. If the
           file is missing (operator-deleted, partial run) → return
           ``(False, None)``.
        3. Extract the global archive to a temp dir alongside it. The
           archive is typically small (KB-MB range — non-tenant KV
           data only), so a full extract is fine and avoids the cost
           of duplicating the streaming-extraction helper.
        4. Read ``kv_trackme_virtual_tenants.json`` from the extracted
           dir. Find the record where ``tenant_id`` matches.
        5. Upsert the record into the live KV. Key resolution:
           prefer the archived ``_key`` (which IS sha256 of
           ``tenant_id`` by the live KV's keying scheme); fall back to
           computing ``sha256(tenant_id)`` if the dump format ever
           drops ``_key``.
        6. Clean up the temp extraction dir in ``finally``.

        Safety
        ------

        * Any non-success path returns ``(False, None)`` — never
          raises — so the caller's safety guard runs.
        * Whole-run restore (``backup_run_id=…`` mode) remains correct:
          step 4/4 of the global archive's restore writes the full
          ``kv_trackme_virtual_tenants`` collection, overwriting this
          single-record upsert with the same data. No conflict.
        * Concurrent UI edits to the live record during restore are
          last-write-wins by KV semantics. The restore wins as intended.
        """
        if not run_id:
            return (False, None)

        global_extract_dir = None
        try:
            # Step 1: locate the global archive row for this run.
            try:
                archives_col = service.kvstore["kv_trackme_backup_archives_info"]
                rows, _, _ = get_full_kv_collection(
                    archives_col, "kv_trackme_backup_archives_info",
                )
            except Exception as e:
                logger.warning(
                    f"tenant central-record sync: cannot read "
                    f"kv_trackme_backup_archives_info "
                    f"(tenant_id={tenant_id!r}, run_id={run_id!r}): {str(e)}"
                )
                return (False, None)

            global_row = next(
                (
                    r for r in rows
                    if r.get("backup_run_id") == run_id
                    and r.get("archive_scope") == ARCHIVE_SCOPE_GLOBAL
                ),
                None,
            )
            if not global_row:
                logger.info(
                    f"tenant central-record sync: no global archive in "
                    f"kv_trackme_backup_archives_info for run_id={run_id!r} "
                    f"(tenant_id={tenant_id!r}). Falling through to "
                    f"missing-tenant safety guard."
                )
                return (False, None)

            # Step 2: verify the file exists on this SH.
            global_path = global_row.get("backup_archive")
            if not global_path or not os.path.isfile(global_path):
                logger.info(
                    f"tenant central-record sync: global archive for "
                    f"run_id={run_id!r} not present on this SH "
                    f"(path={global_path!r}, tenant_id={tenant_id!r}). "
                    f"Falling through to missing-tenant safety guard."
                )
                return (False, None)

            # Step 3: extract to a unique temp dir alongside the archive.
            stem = os.path.basename(global_path)
            for ext in (".tar.zst", ".tgz"):
                if stem.endswith(ext):
                    stem = stem[: -len(ext)]
                    break
            global_extract_dir = os.path.join(
                os.path.dirname(global_path),
                f"trackme-backup-restore-vtenants-lookup-"
                f"{stem}-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            )
            os.makedirs(global_extract_dir, exist_ok=True)
            if not extract_archive(global_path, global_extract_dir):
                logger.warning(
                    f"tenant central-record sync: failed to extract "
                    f"global archive {global_path!r} for "
                    f"tenant_id={tenant_id!r}. Falling through to "
                    f"missing-tenant safety guard."
                )
                return (False, None)

            # Step 4: locate kv_trackme_virtual_tenants.json. The dump
            # writes it at the archive root, but walk the tree to be
            # robust against any future repacking convention.
            vt_json_path = None
            for root_dir, _, files in os.walk(global_extract_dir):
                if "kv_trackme_virtual_tenants.json" in files:
                    vt_json_path = os.path.join(
                        root_dir, "kv_trackme_virtual_tenants.json",
                    )
                    break
            if not vt_json_path:
                logger.warning(
                    f"tenant central-record sync: global archive "
                    f"{global_path!r} does not contain "
                    f"kv_trackme_virtual_tenants.json "
                    f"(tenant_id={tenant_id!r}). Falling through to "
                    f"missing-tenant safety guard."
                )
                return (False, None)

            try:
                with open(vt_json_path) as f:
                    vt_records = json.load(f)
            except Exception as e:
                logger.warning(
                    f"tenant central-record sync: cannot parse "
                    f"kv_trackme_virtual_tenants.json from global "
                    f"archive {global_path!r} "
                    f"(tenant_id={tenant_id!r}): {str(e)}. Falling "
                    f"through to missing-tenant safety guard."
                )
                return (False, None)

            if not isinstance(vt_records, list):
                logger.warning(
                    f"tenant central-record sync: unexpected JSON shape "
                    f"in kv_trackme_virtual_tenants.json (expected list, "
                    f"got {type(vt_records).__name__}). Falling through "
                    f"to missing-tenant safety guard."
                )
                return (False, None)

            # Step 5: find the record for this tenant.
            target_record = next(
                (
                    r for r in vt_records
                    if isinstance(r, dict)
                    and r.get("tenant_id") == tenant_id
                ),
                None,
            )
            if not target_record:
                logger.warning(
                    f"tenant central-record sync: tenant_id={tenant_id!r} "
                    f"not found in the global archive's "
                    f"kv_trackme_virtual_tenants snapshot for "
                    f"run_id={run_id!r}. Falling through to "
                    f"missing-tenant safety guard."
                )
                return (False, None)

            # Step 6: upsert the record into live KV. Match by the
            # archived _key (sha256(tenant_id) by the live KV's keying
            # scheme) so the upsert collides cleanly with any existing
            # row. Fallback to computing the hash ourselves if the
            # dump format ever drops _key.
            record_key = target_record.get("_key")
            if not record_key:
                record_key = hashlib.sha256(
                    tenant_id.encode("utf-8")
                ).hexdigest()

            # Strip _key from the payload — splunk's KV API takes _key
            # via the URL path (data/<_key>), not in the JSON body.
            payload = {
                k: v for k, v in target_record.items() if k != "_key"
            }

            kv = service.kvstore["kv_trackme_virtual_tenants"]
            try:
                # Try update first (record exists locally).
                kv.data.update(record_key, json.dumps(payload))
                action = "updated"
            except Exception as update_err:
                # Decide whether to fall back to insert based on the
                # update error's nature: only "not found" / 404 is a
                # legitimate "record doesn't exist yet, try insert"
                # signal. Any other failure (auth, replication
                # conflict, payload serialisation, KV connectivity)
                # would also fail the subsequent insert, but the
                # insert's exception would mask the original
                # diagnostic context — making the root cause harder
                # to identify in operator logs. Bugbot finding on
                # release PR #1575 (Low).
                err_str = str(update_err)
                err_str_upper = err_str.upper()
                looks_like_not_found = (
                    "404" in err_str
                    or "HTTP 404" in err_str_upper
                    or "not found" in err_str.lower()
                )
                if not looks_like_not_found:
                    # Surface the real cause. The outer try/except
                    # catches and reports it; the helper falls back
                    # to the missing-tenant safety guard at the
                    # caller. Insert would have failed with the same
                    # underlying issue but with a different (less
                    # informative) message.
                    logger.warning(
                        f"tenant central-record sync: kv.data.update "
                        f"failed for tenant_id={tenant_id!r} with a "
                        f"non-404 error: {err_str}. Not attempting "
                        f"insert fallback — the underlying issue "
                        f"(auth / replication / serialisation) would "
                        f"likely affect insert too, and the insert's "
                        f"exception would mask this diagnostic."
                    )
                    raise
                # 404 / not-found path — insert is the right fallback.
                # Include _key in the body for insert (Splunk KV
                # insert accepts _key in body to deterministically
                # set the key).
                payload_for_insert = dict(payload)
                payload_for_insert["_key"] = record_key
                kv.data.insert(json.dumps(payload_for_insert))
                action = "inserted"

            logger.info(
                f"tenant central-record sync: {action} "
                f"kv_trackme_virtual_tenants record for "
                f"tenant_id={tenant_id!r} from global archive of "
                f"run_id={run_id!r} (_key={record_key!r}, "
                f"path={global_path!r})"
            )
            return (True, None)

        except Exception as e:
            # Catch-all so the restore never crashes here. Surface the
            # error in the response so operators see what went wrong,
            # and let the caller fall back to the safety guard.
            logger.exception(
                f"tenant central-record sync: unexpected exception for "
                f"tenant_id={tenant_id!r}, run_id={run_id!r}"
            )
            return (
                False,
                f"tenant central-record sync (from global archive) "
                f"unexpected exception for tenant_id={tenant_id!r}: "
                f"{str(e)}",
            )
        finally:
            if global_extract_dir and os.path.isdir(global_extract_dir):
                try:
                    shutil.rmtree(global_extract_dir, ignore_errors=True)
                except Exception:
                    pass

    def _v3_recreate_missing_tenant_if_needed(
        self, service, tenant_id, extract_dir, manifest, request_info,
    ):
        """Auto-recreate a deleted tenant's full infrastructure when
        restoring its archive. Returns ``(recreated: bool, error_or_None)``.

        Anomalous case: it shouldn't normally happen because the global
        archive carries kv_trackme_virtual_tenants. But operators do
        delete tenants out-of-band; this guard prevents an honest
        single-tenant restore from failing because of that earlier
        delete.

        Implementation note (correctness — see the testing report on
        the deleted-tenant scenario): an earlier implementation just
        inserted the kv_trackme_virtual_tenants row directly. That
        looked sufficient — the row is what `_v3_restore_vtenant_account`
        and the KV-record loader read for routing — but in practice it
        left every per-tenant KV collection physically non-existent on
        disk. Subsequent ``service.kvstore[<col>]`` lookups all
        failed with ``kvstore connect failed: UrlEncoded(...)`` and the
        archive's records had nowhere to land. The fix invokes the
        existing ``post_add_tenant`` REST endpoint, which materialises
        the full tenant infrastructure (KV collections + ACLs +
        transforms + saved searches + tracker schedules) — same code
        path the Add Tenant wizard uses. The downstream
        ``_v3_restore_vtenant_account`` then overwrites the
        post_add_tenant default vtenant_account with the archived
        config, and the KV-record loop populates the now-existing
        collections. Net result: the deleted-tenant restore reaches
        a fully functional tenant.

        Caveats / known limitations of this stage-1 fix:
          * Custom user knowledge objects (operator-defined macros,
            saved searches, alerts) that lived inside the tenant are
            NOT yet restored — ``_v3_restore_knowledge_objects``
            still 404s on the missing
            ``/configuration/restore_tenant_knowledge_objects`` endpoint.
            That fix is a follow-up PR (it requires porting the
            ~900-line legacy KO-restore loop into a shared helper).
            For the deleted-tenant scenario specifically, this is OK
            because post_add_tenant has just installed the standard
            tracker set; only customisations are missing.
          * Component enablement is deduced from the per-tenant
            collections present in the archive. If the original
            tenant had a component enabled but no rows were ever
            written to its collections, the archive may not contain
            that component's collections and the recreated tenant
            won't enable it. Operator can flip the component on
            after the restore via the tenant config modal.
        """
        try:
            kv = service.kvstore["kv_trackme_virtual_tenants"]
            existing, _, _ = get_full_kv_collection(kv, "kv_trackme_virtual_tenants")
            if any(r.get("tenant_id") == tenant_id for r in existing):
                return (False, None)

            vacc_file = manifest.get("vtenant_account_file")
            if not vacc_file:
                return (
                    False,
                    f"missing-tenant safety guard: tenant_id={tenant_id!r} not in "
                    f"kv_trackme_virtual_tenants and the archive carries no "
                    f"vtenant_account file to deduce a record from. The tenant "
                    f"must be re-created manually before restore.",
                )
            vacc_path = os.path.join(extract_dir, vacc_file)
            if not os.path.isfile(vacc_path):
                return (
                    False,
                    f"missing-tenant safety guard: vtenant_account_file "
                    f"declared in manifest as {vacc_file!r} but not found in "
                    f"the extracted archive at {vacc_path}",
                )
            with open(vacc_path) as f:
                vacc_data = json.load(f)

            # Deduce component enablement from the set of _tenant_<tid>
            # collections present in the archive. Only six recognised
            # component prefixes — anything else (common, label, etc.)
            # doesn't gate a tenant_*_enabled flag.
            components_enabled = []
            for col in manifest.get("collections", []):
                name = col.get("name") or ""
                m = re.match(
                    r"kv_trackme_(?P<comp>dsm|dhm|mhm|flx|fqm|wlk)_tenant_",
                    name,
                )
                if m and m.group("comp") not in components_enabled:
                    components_enabled.append(m.group("comp"))

            # Helper: read a vtenant_account field with a default.
            # The archived JSON is the UCC `entry[0].content` shape so
            # all the tenant_* fields the Add-Tenant body wants live
            # at the top level.
            def _vacc(key, default=None):
                if isinstance(vacc_data, dict):
                    val = vacc_data.get(key)
                    if val not in (None, "", []):
                        return val
                return default

            # Defensive default: post_add_tenant rejects a tenant
            # with zero components enabled, BUT it does so with
            # HTTP 200 + error payload (``"at least one component
            # needs to be enabled"``), not a 4xx. Our subsequent
            # ``response.status_code >= 400`` check would miss that
            # and treat the failure as a successful tenant
            # creation, leaving every downstream restore step
            # operating on a phantom tenant. See bugbot review of
            # 62cbc3be. Defend by defaulting to DSM when the
            # archive yields zero deduced components — DSM is the
            # most common component, the operator can flip others
            # on after the restore via the tenant config modal.
            # Logged loudly so the operator notices.
            if not components_enabled:
                logger.warning(
                    f"missing-tenant safety guard: archive for tenant_id="
                    f"{tenant_id!r} has zero per-tenant component collections "
                    f"— defaulting to DSM-enabled so post_add_tenant accepts "
                    f"the request. Operator: review tenant configuration after "
                    f"restore."
                )
                components_enabled = ["dsm"]

            # Build the post_add_tenant body from the archived
            # vtenant_account fields. We pass the deduced component
            # flags rather than trusting the archived ones because the
            # archive's `tenant_*_enabled` could be stale relative to
            # what data is actually present in the per-tenant
            # collections — better to enable exactly what we have data
            # for. Operator can flip components on later if needed.
            add_tenant_body = {
                "tenant_name": tenant_id,
                "tenant_desc": _vacc(
                    "tenant_desc",
                    f"Recreated by missing-tenant safety guard during "
                    f"restore from run {manifest.get('run_id') or 'unknown'}",
                ),
                "tenant_owner": _vacc("tenant_owner", "admin"),
                "tenant_idx_settings": _vacc("tenant_idx_settings", "global"),
                "tenant_roles_admin": _vacc("tenant_roles_admin", "trackme_admin"),
                "tenant_roles_power": _vacc("tenant_roles_power", "trackme_power"),
                "tenant_roles_user": _vacc("tenant_roles_user", "trackme_user"),
                "tenant_dsm_enabled": "true" if "dsm" in components_enabled else "false",
                "tenant_dhm_enabled": "true" if "dhm" in components_enabled else "false",
                "tenant_mhm_enabled": "true" if "mhm" in components_enabled else "false",
                "tenant_flx_enabled": "true" if "flx" in components_enabled else "false",
                "tenant_fqm_enabled": "true" if "fqm" in components_enabled else "false",
                "tenant_wlk_enabled": "true" if "wlk" in components_enabled else "false",
                "tenant_replica": _vacc("tenant_replica", "false"),
                "update_comment": (
                    f"Recreated automatically by the backup-restore "
                    f"missing-tenant safety guard (archive run "
                    f"{manifest.get('run_id') or 'unknown'})"
                ),
            }

            # Invoke post_add_tenant via REST. Same auth pattern
            # everything else in v3 uses — see the _restore_job_kv
            # docstring for the system_authtoken rationale.
            auth_token = (
                getattr(request_info, "system_authtoken", None)
                or request_info.session_key
            )
            add_url = (
                f"{request_info.server_rest_uri}"
                "/services/trackme/v2/vtenants/admin/add_tenant"
            )
            try:
                response = requests.post(
                    add_url,
                    headers={
                        "Authorization": f"Splunk {auth_token}",
                        "Content-Type": "application/json",
                    },
                    data=json.dumps(add_tenant_body),
                    verify=False,
                    # Tenant creation is heavy (creates ~30 collections
                    # + transforms + saved searches per component). 600s
                    # matches the same ceiling the rest of v3 uses.
                    timeout=600,
                )
            except Exception as call_err:
                return (
                    False,
                    f"missing-tenant safety guard: post_add_tenant call "
                    f"failed for tenant_id={tenant_id!r}: {str(call_err)}",
                )
            if response.status_code >= 400:
                return (
                    False,
                    f"missing-tenant safety guard: post_add_tenant "
                    f"returned HTTP {response.status_code} for "
                    f"tenant_id={tenant_id!r}: {response.text[:300]}",
                )
            # Some failure modes return HTTP 200 with an error
            # payload (notably the "at least one component needs to
            # be enabled" rejection). The defensive default above
            # avoids the most common one, but also detect any
            # remaining 200-with-error response by parsing the body
            # as JSON and inspecting structured fields — better a
            # clear error than a phantom-tenant restore.
            #
            # Only act on STRUCTURED signals (parsed JSON with
            # explicit failure markers) to avoid the substring-
            # matching false-positive that an earlier iteration of
            # this guard had — a successful response containing
            # ``"error": null`` would have been misclassified as a
            # failure. See bugbot review of a4de7fcc.
            try:
                body_text = response.text or ""
                parsed = json.loads(body_text) if body_text else None
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                err_payload = parsed.get("response") or parsed
                if isinstance(err_payload, dict):
                    result_val = err_payload.get("result")
                    action_val = err_payload.get("action")
                    response_str = (
                        str(err_payload.get("response", ""))
                        if "response" in err_payload else ""
                    )
                else:
                    result_val = action_val = ""
                    response_str = str(err_payload or "")
                # Treat as failure ONLY when one of these structured
                # markers explicitly says so. ``error: null`` /
                # ``errors: []`` / similar non-failure payloads
                # don't trigger the false-positive any more.
                is_failure = (
                    str(result_val).lower() == "failure"
                    or str(action_val).lower() == "failure"
                    or response_str.lower().startswith("error,")
                    or "needs to be enabled" in response_str.lower()
                )
                if is_failure:
                    return (
                        False,
                        f"missing-tenant safety guard: post_add_tenant "
                        f"returned HTTP 200 with a structured failure "
                        f"payload for tenant_id={tenant_id!r}: "
                        f"{body_text[:300]}",
                    )

            # Belt-and-braces: confirm the kv_trackme_virtual_tenants
            # row was actually created by post_add_tenant. If the row
            # is still missing we hit the phantom-tenant case bugbot
            # warned about — surface it clearly rather than letting
            # the restore proceed against nothing.
            try:
                refreshed_check, _, _ = get_full_kv_collection(
                    kv, "kv_trackme_virtual_tenants"
                )
                if not any(
                    r.get("tenant_id") == tenant_id for r in refreshed_check
                ):
                    return (
                        False,
                        f"missing-tenant safety guard: post_add_tenant "
                        f"reported success but kv_trackme_virtual_tenants "
                        f"still has no record for tenant_id={tenant_id!r}. "
                        f"Phantom tenant — restore aborted.",
                    )
            except Exception:
                # KV read failure is rare and not necessarily fatal
                # (the marker step below would surface it too); keep
                # going.
                pass

            # Mark the freshly-created kv_trackme_virtual_tenants record
            # so the operator (and any future audit) knows this tenant
            # was reconstructed by the safety guard rather than created
            # directly. Best-effort — failure to set the marker doesn't
            # break the restore.
            try:
                refreshed, _, _ = get_full_kv_collection(kv, "kv_trackme_virtual_tenants")
                for r in refreshed:
                    if r.get("tenant_id") == tenant_id and r.get("_key"):
                        marker_record = dict(r)
                        marker_record["recreated_by_restore"] = True
                        marker_record["recreated_at_epoch"] = int(round(time.time()))
                        marker_record["recreated_from_archive"] = (
                            manifest.get("run_id") or ""
                        )
                        marker_record.pop("_key", None)
                        kv.data.update(r["_key"], json.dumps(marker_record))
                        break
            except Exception as marker_err:
                logger.warning(
                    f"missing-tenant safety guard: post_add_tenant "
                    f"succeeded but failed to apply recreated_* markers "
                    f"for tenant_id={tenant_id!r}: {str(marker_err)}"
                )

            logger.warning(
                f'missing-tenant safety guard activated: recreated full '
                f'tenant infrastructure for tenant_id={tenant_id!r} via '
                f'post_add_tenant (run_id={manifest.get("run_id")!r}, '
                f'components_enabled={components_enabled})'
            )
            return (True, None)
        except Exception as e:
            logger.exception(
                f"missing-tenant safety guard failed for tenant_id={tenant_id!r}"
            )
            return (
                False,
                f"missing-tenant safety guard exception: {str(e)}",
            )

    def _v3_restore_vtenant_account(
        self, request_info, tenant_id, extract_dir, vacc_file,
    ):
        """Push the archived vtenant_account JSON back into the UCC-managed
        ``trackme_vtenants`` config endpoint. Returns error_or_None.

        The earlier implementation tried to POST a custom v2 endpoint
        ``/configuration/admin/post_vtenant_account`` that does not
        exist — every tenant-archive restore then failed with HTTP 404
        on the vtenant_account step, leaving the kv_trackme_virtual_tenants
        record stale relative to the archive (the legacy
        2.0.0/1.0.0 path was unaffected because it inlines its own
        UCC POST). This rewrite mirrors the legacy pattern exactly:
        DELETE the existing record (idempotent — a 404 here is fine,
        means the tenant already had no record), then POST the
        cleaned-up archived vtenant_account fields to the UCC config
        endpoint. Form-encoded body, the same Splunk-managed REST
        interface ``post_add_tenant`` uses internally.
        """
        try:
            vacc_path = os.path.join(extract_dir, vacc_file)
            with open(vacc_path) as f:
                vacc_data = json.load(f)
            # See _restore_job_kv / _v3_delegate_restore_to_peer for the
            # full rationale: prefer system_authtoken so the async worker
            # path keeps working past user-session expiry. Fallback to
            # session_key on the off-chance system_authtoken is missing.
            auth_token = (
                getattr(request_info, "system_authtoken", None)
                or request_info.session_key
            )
            headers = {
                "Authorization": f"Splunk {auth_token}",
            }

            # 1. Delete any existing record. The UCC endpoint requires a
            #    delete-before-create for idempotent updates. A 404 here
            #    just means the tenant has no record yet (e.g. the
            #    missing-tenant safety guard's post_add_tenant hasn't
            #    inserted one, or this is a deleted-tenant flow), which
            #    is fine — proceed to the POST.
            del_url = (
                f"{request_info.server_rest_uri}"
                f"/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}"
            )
            try:
                requests.delete(del_url, headers=headers, verify=False, timeout=600)
            except Exception:
                # Best-effort delete. Failures swallowed because the
                # subsequent POST is what actually matters; if the POST
                # fails we'll surface that as the operator-visible error.
                pass

            # 2. Sanitise the archived dict before POSTing. The UCC
            #    config endpoint (``trackme_vtenants``) rejects any
            #    field not declared in globalConfig.json with
            #    ``"Argument X is not supported by this handler"``.
            #    To survive schema drift between the archive and the
            #    target deployment, mirror the legacy 2.0.0 path's
            #    full sanitisation pipeline (see lines 4215-4248):
            #
            #      a. strip Splunk-internal ``eai:*`` metadata + the
            #         derived ``disabled`` flag (UCC re-derives it
            #         from ``tenant_status``);
            #      b. fill any key missing from the archive with its
            #         default from ``vtenant_account_default`` — this
            #         is what makes a v2.3.20 archive restorable on a
            #         v2.3.22 install when newer fields exist;
            #      c. replace ``None`` / empty-string values with
            #         their defaults — older archives sometimes shipped
            #         null-valued fields the new UCC handler rejects;
            #      d. filter the dict down to only keys present in
            #         ``vtenant_account_default`` — this is the
            #         load-bearing step that keeps unknown / removed /
            #         renamed legacy fields from triggering UCC
            #         rejection;
            #      e. re-set ``name`` last (it is the UCC stanza key,
            #         not part of ``vtenant_account_default``, but is
            #         required for the POST to land in the right slot).
            #
            #    Without (b)-(d), every cross-version restore that
            #    crossed a vtenant schema boundary would fail with
            #    HTTP 400 from UCC even though all the data was
            #    technically present. See bugbot review of 1a2fe62d.
            if isinstance(vacc_data, dict):
                data = {
                    k: v for k, v in vacc_data.items()
                    if not (isinstance(k, str) and k.startswith("eai:"))
                }
                data.pop("disabled", None)
            else:
                data = {}

            # (b) fill missing keys
            for default_key, default_val in vtenant_account_default.items():
                if default_key not in data:
                    data[default_key] = default_val

            # (c) replace null / empty values with defaults
            for key in list(data.keys()):
                value = data[key]
                if value is None:
                    data[key] = vtenant_account_default.get(key)
                elif isinstance(value, str) and value == "":
                    data[key] = vtenant_account_default.get(key)

            # (d) filter to only keys the UCC handler accepts. This
            # discards any legacy / removed / renamed field that
            # would otherwise trip the
            # ``"Argument X is not supported by this handler"``
            # rejection.
            cleaned = {
                key: value
                for key, value in data.items()
                if key in vtenant_account_default
            }

            # (e) UCC stanza key — must equal tenant_id for the record
            #     to land in the right slot. Set last so it survives
            #     the filter step regardless of whether ``name`` is in
            #     vtenant_account_default.
            cleaned["name"] = tenant_id

            # 3. POST the cleaned record. Form-encoded (UCC config
            #    endpoints do not accept JSON bodies).
            post_url = (
                f"{request_info.server_rest_uri}"
                "/servicesNS/nobody/trackme/trackme_vtenants"
            )
            response = requests.post(
                post_url,
                headers=headers,
                data=cleaned,
                verify=False,
                timeout=600,
            )
            if response.status_code >= 400:
                return (
                    f"vtenant_account restore failed for tenant_id={tenant_id!r}: "
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
            return None
        except Exception as e:
            return f"vtenant_account restore exception for tenant_id={tenant_id!r}: {str(e)}"

    @staticmethod
    def _v3_resolve_owner(service, target_owner):
        """Resolve a record's archived owner to an owner that exists on
        the local SH. If the original owner doesn't exist (a tenant
        was restored to a different deployment, or the user was
        deleted), fall back to ``"nobody"`` — matches the legacy 2.0.0
        path's ``_resolve_owner`` helper.
        """
        try:
            if not target_owner or str(target_owner).lower() == "nobody":
                return "nobody"
            _ = service.users[str(target_owner)]
            return str(target_owner)
        except Exception:
            logger.warning(
                f'KO restore: owner "{target_owner}" not found on target system, '
                f'falling back to "nobody"'
            )
            return "nobody"

    @staticmethod
    def _v3_extract_acl(record):
        """Extract a Splunk-style ACL dict (``owner``, ``sharing``,
        ``perms.write``, ``perms.read``) from an archived KO record's
        ``properties`` block. The archived JSON keys are ``eai:acl.*``;
        the helpers expect the eai-prefix-stripped form.
        """
        props = (record or {}).get("properties") or {}
        return {
            "owner": props.get("eai:acl.owner"),
            "sharing": props.get("eai:acl.sharing"),
            "perms.write": props.get("eai:acl.perms.write"),
            "perms.read": props.get("eai:acl.perms.read"),
        }

    @staticmethod
    def _v3_format_create_error_with_delete_context(
        ko_type, name, create_err, delete_failures, retry_err=None,
    ):
        """Build the operator-facing error string for a failed KO
        create call, weaving in the earlier delete failure for the
        same ``(ko_type, name)`` if one was tracked.

        Without this, a silently-swallowed delete failure produces a
        confusing ``"create failed (already exists)"`` with no
        explanation of why the existing record wasn't cleared first
        — the exact pattern an operator hit during a deleted-tenant
        restore test in PRD3 (pre-existing reports stalled the
        restore for ~60 minutes with no actionable error message).

        ``delete_failures`` is the per-restore dict keyed by
        ``(ko_type, name)`` and populated when the matching delete
        attempt raised. Pure function — extracted from the inner
        restore loop's closure so it can be unit-tested in isolation
        (see ``unit_tests/check_backup_conflict_error_format.py``).
        """
        base = f"{ko_type} {name!r}: create failed: {str(create_err)}"
        if retry_err is not None:
            base += f" (retry: {str(retry_err)})"
        del_err = (delete_failures or {}).get((ko_type, name))
        if del_err:
            base += (
                f" — pre-existing record could not be removed "
                f"first: {del_err}. Manually delete the "
                f"existing {ko_type} {name!r} on the target SH "
                f"and retry the restore."
            )
        return base

    def _v3_restore_knowledge_objects(
        self,
        request_info,
        service,
        tenant_id,
        extract_dir,
        kos_file,
        replace_existing,
        objects_filter,
        blocklist=None,
    ):
        """Outer wrapper that enforces the no-raise contract on the
        KO restore. The inner worker has its own per-type try/except
        blocks for individual object failures (so one bad saved
        search doesn't kill the rest of the run), but unexpected
        shapes — e.g. a corrupted KO JSON file that deserialises to
        a list rather than a dict — would otherwise raise out of the
        worker and propagate up through ``_v3_restore_one_archive``,
        skipping the KV-record restore entirely. This wrapper turns
        any uncaught exception into the same ``error_or_None``
        return contract every other v3 restore helper provides, so
        the per-archive failure-isolation pattern keeps holding even
        in the worst case.

        See bugbot review of f214d6b4 for the original gap report.
        """
        try:
            return self._v3_restore_knowledge_objects_inner(
                request_info, service, tenant_id, extract_dir, kos_file,
                replace_existing, objects_filter, blocklist,
            )
        except Exception as e:
            logger.exception(
                f"v3 KO restore: unhandled exception for "
                f"tenant_id={tenant_id!r}"
            )
            return (
                f"knowledge_objects restore: unhandled exception for "
                f"tenant_id={tenant_id!r}: {str(e)}"
            )

    def _v3_restore_knowledge_objects_inner(
        self,
        request_info,
        service,
        tenant_id,
        extract_dir,
        kos_file,
        replace_existing,
        objects_filter,
        blocklist=None,
    ):
        """Restore the per-tenant knowledge objects from the archived
        KO JSON file. Mirrors the legacy 2.0.0 KO restore loop exactly,
        in the same order: KV collections → transforms → macros →
        saved searches → alerts. Same architectural reasoning the
        legacy path encoded:

          * KV collections must physically exist BEFORE the KV-record
            loader can write to them (see ``_v3_ensure_kv_collection_exists``
            for the v3-side fallback that catches anything missed
            here).
          * Transforms reference collections — must come AFTER the
            collections.
          * Saved searches that reference other saved searches via
            ``| savedsearch <name>`` must restore the parent first;
            the loop reorders the restore queue accordingly.
          * Alert object types are saved-searches-with-actions in
            Splunk's data model — restored separately so the action
            properties (``action.trackme_*`` flags) get materialised.
          * Failed transforms / macros / saved searches / alerts get
            one second-attempt pass before being declared failed.
            Mirrors the legacy retry behaviour — a transform whose
            target collection wasn't quite ready yet typically
            succeeds on the retry.

        ``objects_filter``: ``"all"`` or list of KO titles — only those
        in the list are restored.
        ``blocklist``: list of KO titles to exclude even if the filter
        would include them. Applied after the filter.

        Returns error_or_None — None on success, a single
        operator-readable summary string on partial / total failure.
        Per-object outcomes are logged at info/error level for
        forensic audit; the response carries the high-level summary.
        """
        try:
            kos_path = os.path.join(extract_dir, kos_file)
            with open(kos_path) as f:
                kos_data = json.load(f)
        except Exception as e:
            return (
                f"knowledge_objects restore: failed to load KO file "
                f"{kos_file!r} for tenant_id={tenant_id!r}: {str(e)}"
            )

        # Resolve the auth token ONCE for every downstream
        # trackme_* helper call below. Same fallback pattern
        # `_v3_recreate_missing_tenant_if_needed`,
        # `_v3_restore_vtenant_account`, and
        # `_v3_ensure_kv_collection_exists` use: prefer
        # `system_authtoken` so the async restore worker path
        # keeps working past user-session expiry; fall back to
        # `session_key` if `system_authtoken` is missing.
        # Without this fallback, ~14 call sites below would
        # raise `AttributeError` on a `request_info` instance
        # that lacks `system_authtoken`, propagating out of
        # the inner worker and skipping the KV collections
        # restore step for the entire archive (the outer
        # wrapper catches it but the archive is already
        # half-restored at that point). See bugbot review
        # of 70ccdcd9.
        auth_token = (
            getattr(request_info, "system_authtoken", None)
            or request_info.session_key
        )

        # Bucket archived records by type. Mirrors the legacy
        # `<type>_restorable_dict` / `<type>_restorable_list`
        # split — kept separate so the per-type filter / blocklist
        # rules can apply independently and so saved-searches /
        # alerts can keep their distinct restore patterns.
        kvc_by_name = {}
        tr_by_name = {}
        macros_by_name = {}
        ss_by_name = {}
        alerts_by_name = {}
        for title, record in (kos_data or {}).items():
            rtype = (record or {}).get("type")
            if rtype == "kvstore_collections":
                kvc_by_name[title] = record
            elif rtype == "lookup_definitions":
                tr_by_name[title] = record
            elif rtype == "macros":
                macros_by_name[title] = record
            elif rtype == "savedsearches":
                ss_by_name[title] = record
            elif rtype == "alerts":
                alerts_by_name[title] = record
            # any unknown type is silently dropped — the archive
            # shouldn't carry them, but guard against future
            # formats and keep going.

        # Apply objects_filter (positive include) + blocklist
        # (negative exclude). Same shape the legacy path uses for
        # every type — extracted once, re-applied per dimension.
        block_set = set(blocklist or [])

        def _filter_titles(titles):
            if isinstance(objects_filter, list):
                titles = [t for t in titles if t in objects_filter]
            return [t for t in titles if t not in block_set]

        kvc_titles = _filter_titles(list(kvc_by_name.keys()))
        tr_titles = _filter_titles(list(tr_by_name.keys()))
        macros_titles = _filter_titles(list(macros_by_name.keys()))
        ss_titles_origin = _filter_titles(list(ss_by_name.keys()))
        alerts_titles = _filter_titles(list(alerts_by_name.keys()))

        counts = {
            "kvstore_collections": {"total": len(kvc_titles), "restored": 0,
                                    "skipped": 0, "failed": 0},
            "transforms": {"total": len(tr_titles), "restored": 0,
                           "skipped": 0, "failed": 0},
            "macros": {"total": len(macros_titles), "restored": 0,
                       "skipped": 0, "failed": 0},
            "savedsearches": {"total": len(ss_titles_origin), "restored": 0,
                              "skipped": 0, "failed": 0},
            "alerts": {"total": len(alerts_titles), "restored": 0,
                       "skipped": 0, "failed": 0},
        }
        # Failure accumulators for the second-attempt retry pass —
        # legacy parity. Each entry carries enough state to re-issue
        # the create call without re-deriving from the archived dict.
        failed_transforms = []
        failed_macros = []
        failed_savedsearches = []
        failed_alerts = []
        # Pre-existing-resource delete-failure tracker. Keyed by
        # ``(ko_type, name)``, value is the delete error string. When
        # the matching create call subsequently fails (most likely
        # with an HTTP 409 conflict because the resource is still
        # there), the error message we surface to the operator
        # combines BOTH errors so the root cause is visible. Without
        # this, a silently-swallowed delete failure produces a
        # confusing "create failed (already exists)" with no
        # explanation of why the existing record wasn't cleared
        # first. See the conflict-handling audit in PR following
        # the deleted-tenant restore test in PRD3.
        delete_failures = {}

        def _verify_deleted(probe, name, ko_type):
            """Return delete-failure error string if the resource is
            still present after the delete API call, else None.

            Splunk's REST framework occasionally acks a delete with
            HTTP 200 while the underlying resource cache hasn't yet
            evicted the entry. A subsequent create then conflicts.
            Re-probe ``service.<resource>[name]`` so we know the
            ground-truth state and can surface a structured error
            instead of letting the create call fail with an
            uninformative ``already exists`` message.
            """
            try:
                _ = probe(name)
            except Exception:
                # Not present — delete is real.
                return None
            return (
                f"delete API call returned 200 but the resource "
                f"is still present on the SH (cache not evicted "
                f"or replication-pending state)"
            )

        def _record_create_error(ko_type, name, create_err, retry_err=None):
            """Closure adapter — delegates to the static formatter
            with this restore call's ``delete_failures`` map. Kept
            as a closure to avoid threading the dict through every
            call site, while the underlying formatter stays pure
            and unit-testable as
            ``_v3_format_create_error_with_delete_context``.
            """
            return self._v3_format_create_error_with_delete_context(
                ko_type, name, create_err, delete_failures,
                retry_err=retry_err,
            )
        # Operator-facing error strings (one per object that ended in
        # the "failed" bucket after the retry pass). Logged in full
        # with structured fields; surfaced in the response as a
        # truncated summary.
        operator_errors = []

        # ─────────────────────────────────────────────
        # 1. KV collections
        # ─────────────────────────────────────────────
        for cname in kvc_titles:
            record = kvc_by_name[cname]
            collection_exists = False
            try:
                _ = service.kvstore[cname]
                collection_exists = True
            except Exception:
                pass

            if collection_exists and not replace_existing:
                logger.info(
                    f'KO restore: collection={cname!r} already exists and '
                    f'replace_existing=False — skipping'
                )
                counts["kvstore_collections"]["skipped"] += 1
                continue

            if collection_exists:
                # Track delete failures so the operator-facing error
                # surfaced from the create call (line ~7370 below)
                # carries the root-cause delete error as context.
                # Without this, a silent delete failure produces a
                # confusing "create failed (already exists)" with no
                # explanation.
                try:
                    trackme_delete_kvcollection(
                        auth_token,
                        request_info.server_rest_uri,
                        tenant_id, cname,
                    )
                except Exception as del_err:
                    delete_failures[("collection", cname)] = str(del_err)
                    logger.warning(
                        f"KO restore: collection={cname!r} pre-existing — "
                        f"delete failed: {str(del_err)}; create will "
                        f"likely conflict"
                    )
                else:
                    # Post-delete verification: the API may ack with
                    # 200 while the resource is still cached. Catch
                    # that here so the operator sees ground truth.
                    still_there = _verify_deleted(
                        lambda n: service.kvstore[n], cname, "collection",
                    )
                    if still_there:
                        delete_failures[("collection", cname)] = still_there
                        logger.warning(
                            f"KO restore: collection={cname!r} delete "
                            f"API succeeded but {still_there}"
                        )

            ko_acl = self._v3_extract_acl(record)
            ko_acl["owner"] = self._v3_resolve_owner(service, ko_acl.get("owner"))
            try:
                trackme_create_kvcollection(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, cname, ko_acl,
                )
                counts["kvstore_collections"]["restored"] += 1
                logger.info(f"KO restore: collection={cname!r} restored OK")
            except Exception as e:
                counts["kvstore_collections"]["failed"] += 1
                msg = _record_create_error("collection", cname, e)
                operator_errors.append(msg)
                logger.error(f"KO restore: collection={cname!r} create FAILED: {msg}")

        # ─────────────────────────────────────────────
        # 2. Transforms (lookup definitions)
        # ─────────────────────────────────────────────
        for tname in tr_titles:
            record = tr_by_name[tname]
            transforms_exists = False
            try:
                _ = service.confs["transforms"][tname]
                transforms_exists = True
            except Exception:
                pass

            if transforms_exists and not replace_existing:
                logger.info(
                    f'KO restore: transform={tname!r} already exists and '
                    f'replace_existing=False — skipping'
                )
                counts["transforms"]["skipped"] += 1
                continue

            if transforms_exists:
                try:
                    trackme_delete_kvtransform(
                        auth_token,
                        request_info.server_rest_uri,
                        tenant_id, tname,
                    )
                except Exception as del_err:
                    delete_failures[("transform", tname)] = str(del_err)
                    logger.warning(
                        f"KO restore: transform={tname!r} pre-existing — "
                        f"delete failed: {str(del_err)}; create will "
                        f"likely conflict"
                    )
                else:
                    still_there = _verify_deleted(
                        lambda n: service.confs["transforms"][n],
                        tname, "transform",
                    )
                    if still_there:
                        delete_failures[("transform", tname)] = still_there
                        logger.warning(
                            f"KO restore: transform={tname!r} delete "
                            f"API succeeded but {still_there}"
                        )

            ko_acl = self._v3_extract_acl(record)
            ko_acl["owner"] = self._v3_resolve_owner(service, ko_acl.get("owner"))
            try:
                trackme_create_kvtransform(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, tname,
                    record.get("fields_list"),
                    record.get("collection"),
                    ko_acl.get("owner"),
                    ko_acl,
                )
                counts["transforms"]["restored"] += 1
                logger.info(f"KO restore: transform={tname!r} restored OK")
            except Exception as e:
                # Don't count as "failed" yet — give the retry pass
                # a chance. Common transient cause: target collection
                # not quite ready. Retry succeeds in practice.
                failed_transforms.append({
                    "name": tname,
                    "fields_list": record.get("fields_list"),
                    "collection": record.get("collection"),
                    "owner": ko_acl.get("owner"),
                    "acl": ko_acl,
                    "first_error": str(e),
                })

        # ─────────────────────────────────────────────
        # 3. Macros
        # ─────────────────────────────────────────────
        for mname in macros_titles:
            record = macros_by_name[mname]
            macro_exists = False
            try:
                _ = service.confs["macros"][mname]
                macro_exists = True
            except Exception:
                pass

            if macro_exists and not replace_existing:
                counts["macros"]["skipped"] += 1
                continue

            if macro_exists:
                try:
                    trackme_delete_macro(
                        auth_token,
                        request_info.server_rest_uri,
                        tenant_id, mname,
                    )
                except Exception as del_err:
                    delete_failures[("macro", mname)] = str(del_err)
                    logger.warning(
                        f"KO restore: macro={mname!r} pre-existing — "
                        f"delete failed: {str(del_err)}; create will "
                        f"likely conflict"
                    )
                else:
                    still_there = _verify_deleted(
                        lambda n: service.confs["macros"][n],
                        mname, "macro",
                    )
                    if still_there:
                        delete_failures[("macro", mname)] = still_there
                        logger.warning(
                            f"KO restore: macro={mname!r} delete "
                            f"API succeeded but {still_there}"
                        )

            ko_acl = self._v3_extract_acl(record)
            ko_acl["owner"] = self._v3_resolve_owner(service, ko_acl.get("owner"))
            try:
                trackme_create_macro(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, mname,
                    record.get("definition"),
                    ko_acl.get("owner"),
                    ko_acl,
                )
                counts["macros"]["restored"] += 1
                logger.info(f"KO restore: macro={mname!r} restored OK")
            except Exception as e:
                failed_macros.append({
                    "name": mname,
                    "definition": record.get("definition"),
                    "owner": ko_acl.get("owner"),
                    "acl": ko_acl,
                    "first_error": str(e),
                })

        # ─────────────────────────────────────────────
        # 4. Saved searches (with parent-search dependency reorder)
        # ─────────────────────────────────────────────
        # If a saved search's SPL references another via
        # ``| savedsearch "<parent>"``, the parent must exist first
        # or the dependent search will fail to register.
        #
        # The legacy path "hoisted" the parent to the front of the
        # queue on each iteration. That works for one-level
        # parent→child chains but breaks for multi-level chains
        # (C→B→A): processing B hoists A to front; then processing
        # C hoists B to front, displacing A. The result places B
        # before A, which is wrong because B itself depends on A.
        # The retry pass masked the bug at customer scale, but the
        # purpose of the reorder (avoiding first-pass failures) was
        # defeated for any non-trivial dependency chain. See bugbot
        # review of 9fd39102.
        #
        # Replace with a proper topological sort: build a
        # child→parent dependency map across the in-scope set, then
        # walk a DFS that emits each name only after its parent.
        # Cycle detection guards against pathological cases (a saved
        # search that ``| savedsearch`` references itself directly
        # or via a cycle — non-zero risk because the regex picks
        # only the first ``| savedsearch`` match in a definition).
        ss_origin_set = set(ss_titles_origin)
        ss_parent = {}
        # Match `| savedsearch <name>` where <name> is either a
        # double-quoted string (which may contain spaces) OR an
        # unquoted identifier (no spaces, terminated by whitespace
        # or end-of-string). The earlier single-group regex used
        # `[^"]+` which greedily consumed the rest of the SPL up
        # to the next quote — so for an unquoted reference like
        # `| savedsearch parent | stats count` the capture was
        # `parent | stats count`, the `parent in ss_origin_set`
        # check failed, and the dependency edge was silently
        # dropped (defeating the topological sort for any
        # non-trivial chain). Two-branch alternation fixes this:
        #   - group 1: quoted name (preserved-as-is, may contain
        #     spaces / pipes)
        #   - group 2: unquoted token (\S+ stops at whitespace)
        # The retry pass would have masked the symptom at run
        # time, but the bug was meaningful — see bugbot review of
        # b71c7d58.
        _ss_dep_re = re.compile(
            r'\|\s*savedsearch\s+(?:"([^"]+)"|(\S+))'
        )
        for ss_name in ss_titles_origin:
            definition = (ss_by_name.get(ss_name) or {}).get("definition") or ""
            m = _ss_dep_re.search(definition)
            parent = (m.group(1) or m.group(2)) if m else None
            if parent and parent != ss_name and parent in ss_origin_set:
                ss_parent[ss_name] = parent

        ss_titles = []
        visited = set()
        in_progress = set()

        def _visit(name):
            if name in visited or name not in ss_origin_set:
                return
            if name in in_progress:
                # Cycle — leave the name where the original input
                # order put it; the create call will either succeed
                # (Splunk tolerates the self-reference for
                # already-registered searches) or fail and end up
                # in the retry bucket. The unwinding caller (the
                # frame that opened ``in_progress`` for this name)
                # is the one that will add it to ``visited`` /
                # ``ss_titles``; this branch deliberately defers.
                logger.warning(
                    f"v3 KO restore: saved-search dependency cycle "
                    f"detected involving {name!r}; restoring in input "
                    f"order"
                )
                return
            in_progress.add(name)
            parent = ss_parent.get(name)
            if parent is not None:
                _visit(parent)
            in_progress.discard(name)
            # Idempotent append: ``visited`` is the single source
            # of truth for ss_titles membership. The pre-check at
            # the top of this function already short-circuits
            # repeat outer-loop calls, but this guard makes the
            # post-order step structurally idempotent regardless
            # of recursion shape — even in a pathological diamond
            # plus cycle, no name lands in ss_titles twice. See
            # bugbot review of 4ce2d4db.
            if name not in visited:
                visited.add(name)
                ss_titles.append(name)

        for ss_name in ss_titles_origin:
            _visit(ss_name)

        for ss_name in ss_titles:
            record = ss_by_name[ss_name]
            ss_exists = False
            try:
                _ = service.saved_searches[ss_name]
                ss_exists = True
            except Exception:
                pass

            if ss_exists and not replace_existing:
                counts["savedsearches"]["skipped"] += 1
                continue

            if ss_exists:
                try:
                    trackme_delete_report(
                        auth_token,
                        request_info.server_rest_uri,
                        tenant_id, ss_name,
                    )
                except Exception as del_err:
                    delete_failures[("savedsearch", ss_name)] = str(del_err)
                    logger.warning(
                        f"KO restore: savedsearch={ss_name!r} pre-existing — "
                        f"delete failed: {str(del_err)}; create will "
                        f"likely conflict"
                    )
                else:
                    still_there = _verify_deleted(
                        lambda n: service.saved_searches[n],
                        ss_name, "savedsearch",
                    )
                    if still_there:
                        delete_failures[("savedsearch", ss_name)] = still_there
                        logger.warning(
                            f"KO restore: savedsearch={ss_name!r} delete "
                            f"API succeeded but {still_there}"
                        )

            props_in = record.get("properties") or {}
            ss_props = {
                "description": props_in.get("description"),
                "is_scheduled": props_in.get("is_scheduled"),
                "schedule_window": props_in.get("schedule_window"),
            }
            # Defaults match the legacy path so a missing /
            # null / "None" earliest+latest falls to a sane window
            # rather than blowing up the save call.
            earliest = props_in.get("earliest_time")
            if not earliest or earliest in (None, "None", "null"):
                earliest = "-5m"
            ss_props["dispatch.earliest_time"] = earliest
            latest = props_in.get("latest_time")
            if not latest or latest in (None, "None", "null"):
                latest = "now"
            ss_props["dispatch.latest_time"] = latest
            cron_schedule = props_in.get("cron_schedule")
            if cron_schedule and cron_schedule not in (None, "None", "null"):
                ss_props["cron_schedule"] = cron_schedule
            if "dispatch.sample_ratio" in props_in:
                ss_props["dispatch.sample_ratio"] = props_in["dispatch.sample_ratio"]

            ko_acl = self._v3_extract_acl(record)
            ko_acl["owner"] = self._v3_resolve_owner(service, ko_acl.get("owner"))
            try:
                trackme_create_report(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, ss_name,
                    record.get("definition"),
                    ss_props, ko_acl,
                    max_failures_count=self._RESTORE_CREATE_RETRY_ATTEMPTS,
                    sleep_time=self._RESTORE_CREATE_RETRY_SLEEP,
                )
                counts["savedsearches"]["restored"] += 1
                logger.info(f"KO restore: savedsearch={ss_name!r} restored OK")
            except Exception as e:
                failed_savedsearches.append({
                    "name": ss_name,
                    "definition": record.get("definition"),
                    "savedsearch_properties": ss_props,
                    "owner": ko_acl.get("owner"),
                    "acl": ko_acl,
                    "first_error": str(e),
                })

        # ─────────────────────────────────────────────
        # 5. Alerts (saved searches with action flags)
        # ─────────────────────────────────────────────
        for alert_name in alerts_titles:
            record = alerts_by_name[alert_name]
            alert_exists = False
            try:
                _ = service.saved_searches[alert_name]
                alert_exists = True
            except Exception:
                pass

            if alert_exists and not replace_existing:
                counts["alerts"]["skipped"] += 1
                continue

            if alert_exists:
                try:
                    trackme_delete_report(
                        auth_token,
                        request_info.server_rest_uri,
                        tenant_id, alert_name,
                    )
                except Exception as del_err:
                    delete_failures[("alert", alert_name)] = str(del_err)
                    logger.warning(
                        f"KO restore: alert={alert_name!r} pre-existing — "
                        f"delete failed: {str(del_err)}; create will "
                        f"likely conflict"
                    )
                else:
                    still_there = _verify_deleted(
                        lambda n: service.saved_searches[n],
                        alert_name, "alert",
                    )
                    if still_there:
                        delete_failures[("alert", alert_name)] = still_there
                        logger.warning(
                            f"KO restore: alert={alert_name!r} delete "
                            f"API succeeded but {still_there}"
                        )

            props_in = record.get("properties") or {}
            properties = {
                "description": props_in.get("description"),
                "is_scheduled": props_in.get("is_scheduled"),
                "schedule_window": props_in.get("schedule_window"),
            }
            earliest = props_in.get("earliest_time")
            if not earliest or earliest in (None, "None", "null"):
                earliest = "-5m"
            properties["dispatch.earliest_time"] = earliest
            latest = props_in.get("latest_time")
            if not latest or latest in (None, "None", "null"):
                latest = "now"
            properties["dispatch.latest_time"] = latest
            cron_schedule = props_in.get("cron_schedule")
            if cron_schedule and cron_schedule not in (None, "None", "null"):
                properties["cron_schedule"] = cron_schedule
            if "dispatch.sample_ratio" in props_in:
                properties["dispatch.sample_ratio"] = props_in["dispatch.sample_ratio"]

            ko_acl = self._v3_extract_acl(record)
            ko_acl["owner"] = self._v3_resolve_owner(service, ko_acl.get("owner"))

            # Recombine the trackme alert-action flags into a CSV
            # ``actions`` field. Only the four trackme actions matter
            # — third-party action.* keys are stripped (some get
            # rejected by Splunk's REST framework when the action's
            # app isn't installed on the target SH).
            alert_properties = dict(record.get("alert_properties") or {})
            alert_actions = []
            try:
                if int(alert_properties.get("action.trackme_stateful_alert", 0) or 0) == 1:
                    alert_actions.append("trackme_stateful_alert")
            except Exception:
                pass
            try:
                if int(alert_properties.get("action.trackme_notable", 0) or 0) == 1:
                    alert_actions.append("trackme_notable")
            except Exception:
                pass
            try:
                if int(alert_properties.get("action.trackme_auto_ack", 0) or 0) == 1:
                    alert_actions.append("trackme_auto_ack")
            except Exception:
                pass
            alert_properties["actions"] = ",".join(alert_actions)
            for k in [
                k for k in list(alert_properties.keys())
                if k.startswith("action.") and not k.startswith("action.trackme")
            ]:
                del alert_properties[k]

            try:
                trackme_create_alert(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, alert_name,
                    record.get("definition"),
                    properties, alert_properties, ko_acl,
                    max_failures_count=self._RESTORE_CREATE_RETRY_ATTEMPTS,
                    sleep_time=self._RESTORE_CREATE_RETRY_SLEEP,
                )
                counts["alerts"]["restored"] += 1
                logger.info(f"KO restore: alert={alert_name!r} restored OK")
            except Exception as e:
                failed_alerts.append({
                    "name": alert_name,
                    "definition": record.get("definition"),
                    "properties": properties,
                    "alert_properties": alert_properties,
                    "owner": ko_acl.get("owner"),
                    "acl": ko_acl,
                    "first_error": str(e),
                })

        # ─────────────────────────────────────────────
        # 6. Second-attempt retry pass (legacy parity)
        # ─────────────────────────────────────────────
        # Most retry-bucket entries succeed on the second try because
        # their target dependency just needed a moment to settle.
        # Anything still failing after the retry is declared failed
        # and goes into operator_errors.
        for ft in failed_transforms:
            try:
                trackme_create_kvtransform(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, ft["name"],
                    ft["fields_list"], ft["collection"],
                    ft["owner"], ft["acl"],
                )
                counts["transforms"]["restored"] += 1
                logger.info(f"KO restore: transform={ft['name']!r} restored on 2nd attempt")
            except Exception as e:
                counts["transforms"]["failed"] += 1
                operator_errors.append(
                    _record_create_error(
                        "transform", ft["name"], ft["first_error"], retry_err=e,
                    )
                )
        for fm in failed_macros:
            try:
                trackme_create_macro(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, fm["name"],
                    fm["definition"], fm["owner"], fm["acl"],
                )
                counts["macros"]["restored"] += 1
                logger.info(f"KO restore: macro={fm['name']!r} restored on 2nd attempt")
            except Exception as e:
                counts["macros"]["failed"] += 1
                operator_errors.append(
                    _record_create_error(
                        "macro", fm["name"], fm["first_error"], retry_err=e,
                    )
                )
        for fs in failed_savedsearches:
            try:
                trackme_create_report(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, fs["name"],
                    fs["definition"],
                    fs["savedsearch_properties"], fs["acl"],
                    max_failures_count=self._RESTORE_CREATE_RETRY_ATTEMPTS,
                    sleep_time=self._RESTORE_CREATE_RETRY_SLEEP,
                )
                counts["savedsearches"]["restored"] += 1
                logger.info(f"KO restore: savedsearch={fs['name']!r} restored on 2nd attempt")
            except Exception as e:
                counts["savedsearches"]["failed"] += 1
                operator_errors.append(
                    _record_create_error(
                        "savedsearch", fs["name"], fs["first_error"], retry_err=e,
                    )
                )
        for fa in failed_alerts:
            try:
                trackme_create_alert(
                    auth_token,
                    request_info.server_rest_uri,
                    tenant_id, fa["name"],
                    fa["definition"],
                    fa["properties"], fa["alert_properties"], fa["acl"],
                    max_failures_count=self._RESTORE_CREATE_RETRY_ATTEMPTS,
                    sleep_time=self._RESTORE_CREATE_RETRY_SLEEP,
                )
                counts["alerts"]["restored"] += 1
                logger.info(f"KO restore: alert={fa['name']!r} restored on 2nd attempt")
            except Exception as e:
                counts["alerts"]["failed"] += 1
                operator_errors.append(
                    _record_create_error(
                        "alert", fa["name"], fa["first_error"], retry_err=e,
                    )
                )

        # Structured info-level summary the audit / forensic reader
        # uses. The operator-facing error string below carries the
        # high-level shape only.
        logger.info(
            f"KO restore: tenant_id={tenant_id!r} summary={json.dumps(counts)}"
        )
        if not operator_errors:
            return None
        # Keep the response readable — cap the surfaced detail and
        # tell the operator where the rest lives.
        head = "; ".join(operator_errors[:5])
        more = (
            f" (+{len(operator_errors) - 5} more in splunkd.log)"
            if len(operator_errors) > 5 else ""
        )
        return (
            f"knowledge_objects restore for tenant_id={tenant_id!r}: "
            f"{sum(c['failed'] for c in counts.values())} object(s) failed "
            f"after retry — {head}{more}"
        )

    # Default ACL applied to any collection the v3 restore loop has
    # to materialise on the fly because it doesn't exist on the local
    # SH. The legacy KO-restore path uses the archived ACLs from the
    # KO file, but the v3 KO restore path is still broken (separate
    # follow-up). This default keeps the restore unblocked: tenant
    # owner = nobody, sharing = global, write = trackme_admin/power,
    # read = trackme_admin/power/user — the same defaults
    # ``post_add_tenant`` applies to the per-tenant collections it
    # creates. Operator can re-tighten ACLs after the restore.
    #
    # Plain dict (NOT json.dumps()ed). ``trackme_create_kvcollection``
    # passes this straight to the underlying HTTP client's data
    # argument, which form-encodes a dict but ships a string as the
    # raw HTTP body. Splunk's ``/storage/collections/config/<name>/acl``
    # endpoint only accepts form-encoded input — a JSON-string body
    # would silently fail to apply the ACL, leaving the collection
    # with whatever defaults Splunk picks. Every other caller of the
    # helper in this codebase also passes a dict.
    _V3_DEFAULT_RESTORE_KVCOLLECTION_ACL = {
        "owner": "nobody",
        "sharing": "global",
        "perms.write": "trackme_admin,trackme_power",
        "perms.read": "trackme_admin,trackme_power,trackme_user",
    }

    # Retry budget passed to ``trackme_create_report`` /
    # ``trackme_create_alert`` from the v3 KO-restore loop. Set to
    # the legacy default (24 × 5 s = 120 s per call) — generous on
    # purpose because the dominant non-conflict failure mode here is
    # the macro-cache-refresh race: a saved search references a
    # macro that was created moments earlier in step 3, but splunkd
    # hasn't yet propagated the macro to its REST cache. Field test
    # on PRD5 SHC restore: short retries (3 × 2 s = 6 s) caused 6
    # saved searches to fail permanently when the macro propagation
    # took longer than 6 s.
    #
    # Conflict scenarios (the original reason for shrinking this
    # window) are handled by the HTTP 409 fast-fail check inside
    # ``trackme_create_report`` / ``trackme_create_alert`` — those
    # bail out in milliseconds regardless of the retry budget. So
    # the longer window does NOT regress the conflict-handling fix
    # from PR #1497.
    _RESTORE_CREATE_RETRY_ATTEMPTS = 24
    _RESTORE_CREATE_RETRY_SLEEP = 5

    def _v3_ensure_kv_collection_exists(self, service, request_info, cname, tenant_id):
        """Materialise a KV collection on the local SH if it doesn't
        already exist. Returns True iff the collection is usable
        post-call.

        Architectural ordering (the principle the legacy restore path
        encoded and the v3 path was implicitly relying on): a KV
        collection MUST physically exist on disk before any
        ``service.kvstore[name]`` lookup or record write. The legacy
        2.0.0 path enforced this by recreating collections from the
        archived KO file's ``kvstore_collections`` records BEFORE
        replaying KV records. The v3 KO restore is currently broken
        (``_v3_restore_knowledge_objects`` 404s — separate follow-up),
        so the v3 KV-record loader has to take responsibility for
        ensuring the collections exist itself.

        Without this pre-create step, every collection that's in the
        archive's manifest but missing locally (because the tenant
        was deleted, a component was disabled, an upgrade added new
        collections, etc.) fails with the cryptic ``kvstore connect
        failed: UrlEncoded(<name>)`` error and the records are
        dropped. With this step, the restore proceeds.
        """
        # ``service.kvstore`` membership / lookup is an SDK call to
        # ``GET /servicesNS/.../storage/collections/config`` — the
        # SDK can raise on transient kvstore unavailability (kvstore
        # restart, captain election, etc.). Wrap defensively so a
        # transient blip on one collection doesn't escape the helper
        # and abort the whole ``for col_meta in manifest.collections``
        # loop in _v3_restore_kv_collections_from_manifest. See
        # bugbot review of f214d6b4.
        try:
            if cname in service.kvstore:
                return True
        except Exception as e:
            logger.warning(
                f"v3 restore: existence probe for collection {cname!r} "
                f"raised; will attempt creation anyway: {str(e)}"
            )
        # Same auth fallback every other v3 helper uses — see
        # _restore_job_kv docstring for the system_authtoken
        # rationale. Direct attribute access used to fail silently
        # if request_info ever lacked system_authtoken; the helper
        # caught the resulting bad-token error and dropped records
        # for that collection. See bugbot review of 62cbc3be.
        auth_token = (
            getattr(request_info, "system_authtoken", None)
            or request_info.session_key
        )
        try:
            trackme_create_kvcollection(
                auth_token,
                request_info.server_rest_uri,
                tenant_id or "v3-restore",
                cname,
                self._V3_DEFAULT_RESTORE_KVCOLLECTION_ACL,
            )
            # The Splunk REST framework's create()/POST is async on
            # the indexer side: a brief refresh delay between create
            # and lookup is possible. Force a fresh service.kvstore
            # read by indexing into the SDK's internal collection
            # iterator — this nudges the Python SDK to re-fetch the
            # collection list and pick up our just-created entry.
            # Same defensive wrap as the pre-create probe above.
            try:
                return cname in service.kvstore
            except Exception as e:
                logger.warning(
                    f"v3 restore: post-create existence probe for "
                    f"collection {cname!r} raised: {str(e)}"
                )
                return False
        except Exception as e:
            logger.warning(
                f"v3 restore: failed to materialise collection {cname!r}: "
                f"{str(e)}"
            )
            return False

    def _v3_restore_kv_collections_from_manifest(
        self,
        service,
        extract_dir,
        manifest,
        scope_filter,
        clean_empty,
        blocklist=None,
        request_info=None,
        tenant_id=None,
    ):
        """Restore every KV collection declared in the manifest.

        Returns ``(per_collection_summaries: list, errors: list)``.

        ``scope_filter``: ``"all"`` or list of collection names — only
        collections whose name is in the list are restored.
        ``blocklist``: list of collection names that are explicitly
        excluded from restore even if scope_filter would include them.
        Stateful charts collections are always excluded (architectural
        contract; matches post_backup behaviour).

        ``request_info`` / ``tenant_id`` (optional, but the caller in
        ``_v3_restore_one_archive`` always passes both): used to
        materialise a collection on demand when it doesn't exist on
        the local SH — see ``_v3_ensure_kv_collection_exists``. The
        legacy 2.0.0 restore enforced "create collection from KO file
        BEFORE replaying records"; the v3 path inherits the same
        ordering invariant via the on-demand pre-create. When
        ``request_info`` is None we fall through to the original
        behaviour (a missing collection becomes an error rather than
        a self-heal) — that mode exists only for unit tests that
        instantiate the helper without a Splunk runtime.
        """
        summaries = []
        errors = []
        scope_set = None
        if isinstance(scope_filter, list):
            scope_set = set(scope_filter)
        block_set = set(blocklist or [])

        all_collections = [
            (c.get("name") or "")
            for c in (manifest.get("collections", []) or [])
            if c.get("name")
        ]
        logger.info(
            f"v3 KV-record restore: starting — "
            f"manifest_collections={len(all_collections)}, "
            f"scope_filter={'all' if scope_set is None else len(scope_set)}, "
            f"blocklist={len(block_set)}"
        )

        for idx, col_meta in enumerate(manifest.get("collections", []) or [], 1):
            cname = col_meta.get("name") or ""
            if not cname:
                continue
            if scope_set is not None and cname not in scope_set:
                continue
            if cname in block_set:
                summaries.append({
                    "collection_name": cname, "skipped": True,
                    "skip_reason": "in kvstore_collections_blocklist",
                })
                continue
            if cname.startswith("kv_trackme_stateful_alerting_charts_tenant_"):
                # Stateful charts are excluded from backups by design — if
                # one slipped through, skip restore on the same grounds.
                summaries.append({
                    "collection_name": cname, "skipped": True,
                    "skip_reason": "stateful charts collection — excluded",
                })
                continue

            file_name = col_meta.get("file") or f"{cname}.json"
            json_path = os.path.join(extract_dir, file_name)
            if not os.path.isfile(json_path):
                err_msg = (
                    f"collection {cname!r}: declared in manifest but file "
                    f"{file_name!r} not present in archive"
                )
                logger.error(f"v3 KV-record restore: {err_msg}")
                errors.append(err_msg)
                summaries.append({
                    "collection_name": cname,
                    "restored_records": 0,
                    "error": "missing JSON file",
                })
                continue

            try:
                with open(json_path) as f:
                    data = json.load(f)
            except Exception as e:
                err_msg = f"collection {cname!r}: failed to read JSON: {str(e)}"
                logger.error(f"v3 KV-record restore: {err_msg}")
                errors.append(err_msg)
                summaries.append({
                    "collection_name": cname,
                    "restored_records": 0,
                    "error": f"json read failure: {str(e)}",
                })
                continue

            # Per-collection progress log. Critical for diagnosing
            # where restore hangs in production — without this an
            # operator can't tell which collection of N is currently
            # being processed when the worker silently waits on
            # splunkd's KV API. The cost is one INFO line per
            # collection (~30-40 lines for a typical tenant), which
            # is negligible compared to the per-record verbosity
            # already in the legacy path.
            logger.info(
                f"v3 KV-record restore: collection={cname!r} "
                f"({idx}) source_records={len(data)} — restoring"
            )

            # ORDERING INVARIANT — the legacy 2.0.0 restore path
            # encoded a strict order: "create the collection from the
            # archived KO file BEFORE replaying any records into it".
            # Without that order, ``service.kvstore[name]`` raises
            # the cryptic ``kvstore connect failed: UrlEncoded(...)``
            # error and the records are dropped. The v3 KO restore
            # path is currently broken (separate follow-up — see
            # ``_v3_restore_knowledge_objects``), so v3 KV-record
            # replay has to defend itself: if the collection is
            # missing locally, materialise it on the fly with safe
            # default ACLs. Only called when the caller supplied a
            # ``request_info`` (the production path always does);
            # unit-test callers without a Splunk runtime hit the
            # legacy-style ``service.kvstore[name]`` raise + error
            # bookkeeping instead.
            if request_info is not None:
                self._v3_ensure_kv_collection_exists(
                    service, request_info, cname, tenant_id,
                )
            try:
                col = service.kvstore[cname]
            except Exception as e:
                err_msg = f"collection {cname!r}: kvstore connect failed: {str(e)}"
                logger.error(f"v3 KV-record restore: {err_msg}")
                errors.append(err_msg)
                summaries.append({
                    "collection_name": cname,
                    "restored_records": 0,
                    "error": f"kvstore connect: {str(e)}",
                })
                continue

            if clean_empty and len(data) == 0:
                try:
                    col.data.delete()
                except Exception as e:
                    err_msg = (
                        f"collection {cname!r}: clean_empty delete failed: {str(e)}"
                    )
                    logger.warning(f"v3 KV-record restore: {err_msg}")
                    errors.append(err_msg)

            restored = 0
            chunk_errs = []
            chunks = [data[i : i + 500] for i in range(0, len(data), 500)]
            for chunk in chunks:
                try:
                    col.data.batch_save(*chunk)
                    restored += len(chunk)
                except Exception as e:
                    chunk_errs.append(str(e))
                    err_msg = (
                        f"collection {cname!r}: batch_save failed: {str(e)}"
                    )
                    logger.error(f"v3 KV-record restore: {err_msg}")
                    errors.append(err_msg)

            summaries.append({
                "collection_name": cname,
                "source_records": len(data),
                "restored_records": restored,
                "errors": chunk_errs,
            })
            logger.info(
                f"v3 KV-record restore: collection={cname!r} — "
                f"done (restored={restored}/{len(data)}, "
                f"chunk_errors={len(chunk_errs)})"
            )
        logger.info(
            f"v3 KV-record restore: all collections processed — "
            f"summaries={len(summaries)}, errors={len(errors)}"
        )
        return (summaries, errors)

    # ====================================================================
    # 3.0.0 multi-archive — listing + thin wrappers
    #
    # These endpoints are added for the 2.3.22 multi-archive format. They
    # are auto-discovered by the base RESTHandler's dir() scan, so no
    # trackmeapiautodocs.py registration is needed (the parent handler is
    # already registered there).
    # ====================================================================

    def get_backup_runs(self, request_info, **kwargs):
        """List backup runs grouped from kv_trackme_backup_archives_info.

        A run is one or more rows that share a ``backup_run_id``. Rows
        without a ``backup_run_id`` (legacy 1.0.0/2.0.0 archives produced
        before 2.3.22) are grouped under a synthetic ``"legacy"`` run so
        they remain visible alongside the new format.

        Returns the list sorted by ``finished_epoch`` descending, with
        the legacy bucket always at the bottom (so the UI's "latest run"
        affordance always surfaces a 3.0.0 run when one exists).
        """
        if trackme_parse_describe_flag(request_info):
            return {
                "payload": {
                    "describe": (
                        "Lists backup runs grouped from "
                        "kv_trackme_backup_archives_info. A run is one or "
                        "more archives sharing a backup_run_id (3.0.0 format, "
                        "produced since 2.3.22). Legacy 1.0.0/2.0.0 archives "
                        "without backup_run_id are folded into a synthetic "
                        "'legacy' run that always sorts last. The KV "
                        "collection is auto-replicated across SHC peers, so "
                        "this endpoint works on any peer."
                    ),
                    "resource_desc": "List backup runs (3.0.0 multi-archive format + legacy bucket)",
                    "resource_spl_example": (
                        '| trackme mode=get url='
                        '"/services/trackme/v2/backup_and_restore/backup_runs"'
                    ),
                    "options": [{}],
                },
                "status": 200,
            }

        try:
            # Use session_key (the calling user's session) for parity
            # with every other client.connect call in this file —
            # _v3_delete_run, post_backup, post_restore, etc. all
            # consistently use session_key. system_authtoken would carry
            # system-level privileges and bypass user-level ACLs, which
            # would be inconsistent with the rest of the handler's
            # auth posture.
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.session_key,
                timeout=600,
            )
            kv = service.kvstore["kv_trackme_backup_archives_info"]
            rows, _, _ = get_full_kv_collection(
                kv, "kv_trackme_backup_archives_info"
            )
        except Exception as e:
            logger.exception("get_backup_runs: KV read failed")
            return {
                "payload": {"response": f"Failed to read archive info: {str(e)}"},
                "status": 500,
            }

        runs = _bbk_group_archives_by_run(rows)
        return {
            "payload": {
                "runs": runs,
                "run_count": len(runs),
                "archive_count": sum(len(r.get("archives") or []) for r in runs),
                "legacy_run_id": LEGACY_RUN_ID,
            },
            "status": 200,
        }

    def post_backup_tenant(self, request_info, **kwargs):
        """Thin wrapper around post_backup that pins
        ``tenants_scope=[<tenant_id>]`` and ``include_global=false``.

        Useful for advanced operator workflows (e.g. an hourly snapshot
        of a hot tenant) without polluting the global archive cadence.
        """
        if trackme_parse_describe_flag(request_info):
            return {
                "payload": {
                    "describe": (
                        "Thin wrapper around POST /backup that produces "
                        "ONLY the named tenant's archive (no global "
                        "archive). Useful for hot-tenant snapshots."
                    ),
                    "resource_desc": "Backup a single tenant (3.0.0 format)",
                    "resource_spl_example": (
                        '| trackme mode=post url='
                        '"/services/trackme/v2/backup_and_restore/backup_tenant" '
                        "body=\"{'tenant_id':'<tid>'}\""
                    ),
                    "options": [{
                        "tenant_id": "REQUIRED. The tenant_id to back up.",
                        "comment": "OPTIONAL: comment to be added to the archive.",
                        "blocklist": "OPTIONAL: collection-name blocklist (csv or list).",
                    }],
                },
                "status": 200,
            }

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None
        if not resp_dict or not resp_dict.get("tenant_id"):
            return {
                "payload": {
                    "response": "tenant_id is required in the body of the request",
                },
                "status": 400,
            }

        # Forward to post_backup by mutating the payload to pin the
        # multi-archive params. post_backup's body parser reads from
        # request_info.raw_args["payload"], so we rewrite the payload
        # here and call through. This is the same shape as the legacy
        # tenant snapshot path and keeps post_backup as the single
        # source of truth for backup orchestration.
        forwarded = dict(resp_dict)
        forwarded["tenants_scope"] = [str(resp_dict["tenant_id"]).strip()]
        forwarded["include_global"] = False
        request_info.raw_args["payload"] = json.dumps(forwarded)
        return self.post_backup(request_info, **kwargs)

    def _v3_delete_run(self, request_info, backup_run_id, force_local, splunkd_port):
        """Delete every archive belonging to a 3.0.0 backup run.

        Iterates the rows in ``kv_trackme_backup_archives_info`` matching
        ``backup_run_id`` and issues one DELETE-by-archive_name per row.
        Each per-archive call carries the row's ``server_name`` so the
        existing single-archive delete logic delegates to the owning SH
        peer when needed (SHC-aware), with ``force_local=true`` on the
        delegated call to prevent recursive delegation.

        Returns an aggregate response with one entry per archive in
        ``deleted_archives[]``, mirroring the per-archive isolation
        contract of post_backup / post_restore — a corrupt or remote-
        unreachable archive does not abort the rest of the run-level
        deletion.
        """
        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=600,
            )
            kv = service.kvstore["kv_trackme_backup_archives_info"]
            all_rows, _, _ = get_full_kv_collection(
                kv, "kv_trackme_backup_archives_info"
            )
        except Exception as e:
            logger.exception("_v3_delete_run: KV read failed")
            return {
                "payload": {
                    "response": f"Failed to read archive info: {str(e)}",
                    "backup_run_id": backup_run_id,
                },
                "status": 500,
            }

        archives = [r for r in all_rows if r.get("backup_run_id") == backup_run_id]
        if not archives:
            return {
                "payload": {
                    "response": (
                        f"No archives found for backup_run_id="
                        f"{backup_run_id!r}. Either the run was already "
                        "deleted or the id is wrong."
                    ),
                    "backup_run_id": backup_run_id,
                    "deleted_archives": [],
                },
                "status": 404,
            }

        local_server = socket.gethostname()
        own_url = (
            f"https://{local_server}:{request_info.server_rest_port}"
            "/services/trackme/v2/backup_and_restore/backup"
        )
        headers = {
            "Authorization": f"Splunk {request_info.session_key}",
            "Content-Type": "application/json",
        }

        results = []
        for row in archives:
            archive_path = row.get("backup_archive") or ""
            archive_name = os.path.basename(str(archive_path))
            owner = row.get("server_name") or local_server

            # SAFETY: skip rows with no archive_name. If we proceeded
            # with archive_name="" the per-archive call would fall
            # through delete_backup's `if archive_name:` check and
            # silently trigger a retention-based purge of every old
            # archive on the cluster (wrong scope, mass-delete risk).
            # Surface the row as a per-archive failure instead so the
            # operator can investigate the corrupted KV record.
            if not archive_name:
                results.append({
                    "archive_name": "",
                    "server_name": owner,
                    "scope": row.get("archive_scope") or "",
                    "tenant_id": row.get("tenant_id") or "",
                    "status": "failed",
                    "errors": [
                        "skipped — KV row has empty backup_archive field. "
                        "This is a corrupted record; the run-mode delete "
                        "refuses to fan out without an explicit archive "
                        "filename to avoid triggering an unrelated "
                        "retention sweep. Inspect the row manually "
                        "(maybe via | inputlookup trackme_backup_archives_info).",
                    ],
                })
                continue

            # Per-archive delete: hand the body to delete_backup via a
            # fresh REST call so the legacy delegation logic (which is
            # battle-tested at scale) handles the SHC routing. We always
            # call the LOCAL server's delete endpoint; the legacy logic
            # then either deletes locally or delegates to the owning
            # peer based on row.server_name. force_local is propagated
            # so a delegated call doesn't re-delegate.
            payload = {
                "archive_name": archive_name,
                "server_name": owner,
                "force_local": bool(force_local),
            }
            try:
                resp = requests.delete(
                    own_url,
                    headers=headers,
                    data=json.dumps(payload),
                    verify=False,
                    timeout=600,
                )
                ok = resp.status_code < 400
                try:
                    parsed = resp.json()
                except Exception:
                    parsed = {"raw": resp.text[:200]}
                results.append({
                    "archive_name": archive_name,
                    "server_name": owner,
                    "scope": row.get("archive_scope") or "",
                    "tenant_id": row.get("tenant_id") or "",
                    "status": "ok" if ok else "failed",
                    "http_status": resp.status_code,
                    "response": parsed,
                })
            except Exception as e:
                results.append({
                    "archive_name": archive_name,
                    "server_name": owner,
                    "scope": row.get("archive_scope") or "",
                    "tenant_id": row.get("tenant_id") or "",
                    "status": "failed",
                    "errors": [f"per-archive delete exception: {str(e)}"],
                })

        # Best-effort: also remove the run-level manifest sidecar from
        # this peer's filesystem (each peer keeps its own; ignore
        # missing).
        try:
            backuproot = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
            run_manifest = os.path.join(backuproot, f"{backup_run_id}.manifest.json")
            if os.path.isfile(run_manifest):
                os.remove(run_manifest)
        except Exception as e:
            logger.warning(
                f"_v3_delete_run: failed to remove run manifest sidecar: {str(e)}"
            )

        ok_count = sum(1 for r in results if r.get("status") == "ok")
        failed_count = sum(1 for r in results if r.get("status") == "failed")
        return {
            "payload": {
                "response": (
                    f"TrackMe 3.0.0 run delete completed: ok={ok_count}, "
                    f"failed={failed_count} (run_id={backup_run_id})"
                ),
                "backup_run_id": backup_run_id,
                "deleted_archives": results,
            },
            "status": 500 if archives and failed_count == len(archives) else 200,
        }

    def post_backup_global(self, request_info, **kwargs):
        """Thin wrapper around post_backup that pins
        ``include_global=true`` and ``tenants_scope=[]``.

        Useful for refreshing only the global archive between full runs.
        """
        if trackme_parse_describe_flag(request_info):
            return {
                "payload": {
                    "describe": (
                        "Thin wrapper around POST /backup that produces "
                        "ONLY the global archive (no per-tenant archives)."
                    ),
                    "resource_desc": "Backup the global archive only (3.0.0 format)",
                    "resource_spl_example": (
                        '| trackme mode=post url='
                        '"/services/trackme/v2/backup_and_restore/backup_global"'
                    ),
                    "options": [{
                        "comment": "OPTIONAL: comment to be added to the archive.",
                        "blocklist": "OPTIONAL: collection-name blocklist (csv or list).",
                    }],
                },
                "status": 200,
            }

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = {}
        forwarded = dict(resp_dict or {})
        forwarded["tenants_scope"] = []
        forwarded["include_global"] = True
        request_info.raw_args["payload"] = json.dumps(forwarded)
        return self.post_backup(request_info, **kwargs)

    # ====================================================================
    # 3.0.0 multi-archive — async restore job pattern
    #
    # Mirrors the AI Assistant async pattern (kv_trackme_ai_chat_jobs +
    # threading.Thread(daemon=True) + a polling endpoint). Avoids
    # gateway-timeout 504s on multi-GB / multi-minute restores while
    # preserving the synchronous contract for CLI / `| trackme` SPL
    # callers.
    #
    # Lifecycle:
    #   POST /restore body={..., async: true}
    #     → row inserted in kv_trackme_backup_restore_jobs status=queued
    #     → worker thread started (daemon, so SIGTERM doesn't hang)
    #     → handler returns {job_id, status: "queued"} immediately
    #   Worker:
    #     status: queued → running (records started_epoch)
    #     iterates archives (calls _handle_restore_3_0_0)
    #     status: completed | failed (records finished_epoch + response)
    #   Frontend polls GET /restore_job_status?job_id=X every 2-3s
    #     until status in (completed, failed, cancelled).
    #   DELETE /restore_job?job_id=X sets cancel_requested=1; the
    #     worker checks between archives and aborts gracefully.
    # ====================================================================

    _RESTORE_JOB_KV_COLLECTION = "kv_trackme_backup_restore_jobs"

    # How long to keep terminal (completed/failed/cancelled) jobs in KV
    # before auto-purging. 24h gives the operator a wide window to
    # inspect the response after a long restore. Running jobs are never
    # auto-purged — the worker writes status updates so stale-detection
    # would only fire on a true crash, and we'd rather keep the row
    # for forensic analysis than silently delete it.
    _RESTORE_JOB_TERMINAL_TTL_SECONDS = 24 * 3600

    # Auto-purge gate. The frontend polls /restore_job_status every
    # 2–3s while a restore is running, and an unconditional purge would
    # mean two KV connections + one full table scan per poll per
    # concurrent frontend. Since terminal rows live 24h before they're
    # eligible for purging, a coarse 60s gate collapses the
    # purge-attempt rate by ~30× without changing observable behaviour
    # (the worst case is that a row's actual deletion is delayed by up
    # to 60s past its TTL, which is already a 24-hour grace window).
    # Class-level so the gate is shared across handler instances —
    # splunkd reuses PersistentServerConnectionApplication instances
    # across requests, but we don't rely on that; a fresh instance just
    # restarts the gate from 0 and runs one purge, then quiets down.
    _RESTORE_JOB_PURGE_MIN_INTERVAL_SECONDS = 60
    _restore_job_last_purge_epoch = 0

    def _restore_job_kv(self, request_info):
        """Open a service connection scoped to the local SH and return
        the kv_trackme_backup_restore_jobs collection handle. Used by
        every async helper — extracted so the connection params stay
        consistent.

        IMPORTANT: uses ``system_authtoken``, NOT ``session_key``. The
        worker thread can outlive the user's session for a long restore
        (multi-GB / multi-minute is the entire reason this async pattern
        exists), and ``session_key`` would silently expire mid-flight.
        Every helper here (``_restore_job_update_status``,
        ``_restore_job_is_cancelled``, ``_restore_job_finalise``) wraps
        its KV calls in best-effort try/except, so an expired
        ``session_key`` would not raise — it would silently no-op,
        stranding the row in ``status="running"`` forever. Auto-purge
        skips non-terminal rows, so the orphaned job would never be
        cleaned up. ``system_authtoken`` is the splunkd-issued system
        token that does not expire on user-session timeout — the same
        choice the AI Assistant chat handler makes for its long-running
        async jobs (see ``trackme_rest_handler_ai_chat.py``).
        """
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        return service.kvstore[self._RESTORE_JOB_KV_COLLECTION]

    def _restore_job_record(
        self,
        job_id,
        status,
        body_params,
        request_info,
        progress=None,
        response=None,
        cancel_requested=None,
        started_epoch=None,
        finished_epoch=None,
    ):
        """Build the KV record dict for a job. Centralised so insert
        and every status update use the same shape.

        ``last_heartbeat_epoch`` is seeded with ``now`` on every build
        — most importantly the initial INSERT in
        :py:meth:`_dispatch_restore_async`. This closes a duplicate-
        worker race: the watchdog (``_restore_job_should_resume`` at
        the status-poll endpoint) treats a missing ``hb`` field as
        "stale" so that pre-resumable rows surviving an upgrade get
        recovered on the first poll. Without this seed, every freshly
        spawned job lived in a brief "no hb" window between the row
        insert and the heartbeat thread's first write. A frontend
        status-poll arriving in that window saw the row as stale,
        claimed the resume slot, and spawned a second worker — which
        delegated to the owning SHC peer in parallel with the
        original worker. The duplicate workers race each step's
        create-call, producing ``HTTP 409 Conflict`` on every
        per-tenant collection / transform / saved search, and most
        critically on ``post_add_tenant``'s ``kv_trackme_virtual_tenants``
        insert (missing-tenant safety guard path). With step 1a
        erroring, step 1b is gated off (see PR #1639), leaving the
        operator with the safety-guard's placeholder ``tenant_desc``
        instead of the authoritative record from the global archive
        overlay.
        """
        now = int(round(time.time()))
        record = {
            "_key": job_id,
            "job_id": job_id,
            "status": status,
            "mtime": now,
            "last_heartbeat_epoch": now,
            "submitted_by": (
                getattr(request_info, "user", None) or "unknown"
            ),
        }
        if started_epoch is not None:
            record["started_epoch"] = int(started_epoch)
        if finished_epoch is not None:
            record["finished_epoch"] = int(finished_epoch)
        if progress is not None:
            record["progress"] = str(progress)
        if cancel_requested is not None:
            record["cancel_requested"] = "1" if cancel_requested else "0"
        # Always serialise body_params + response as JSON strings so
        # the KV row carries enough context for forensic analysis even
        # if the frontend has long since closed the modal.
        if body_params is not None:
            try:
                record["request_args"] = json.dumps(body_params)
            except Exception:
                record["request_args"] = ""
        if response is not None:
            try:
                record["response"] = json.dumps(response)
            except Exception:
                record["response"] = json.dumps({"error": "response not serialisable"})
        return record

    def _dispatch_restore_async(self, request_info, body_params):
        """Insert a queued job row, spawn a daemon worker, return
        immediately with the job_id.
        """
        job_id = str(uuid.uuid4())
        started_epoch = int(round(time.time()))
        try:
            kv = self._restore_job_kv(request_info)
        except Exception as e:
            logger.exception("async restore: failed to access job KV")
            return {
                "payload": {
                    "response": (
                        f"Failed to open kv_trackme_backup_restore_jobs: {str(e)}"
                    ),
                },
                "status": 500,
            }

        # Insert the queued row BEFORE spawning the thread so the
        # frontend's first poll always finds the job (no race between
        # the response landing and the worker reaching its first
        # status update).
        record = self._restore_job_record(
            job_id=job_id,
            status="queued",
            body_params=body_params,
            request_info=request_info,
            started_epoch=started_epoch,
            finished_epoch=0,
            progress="queued",
            cancel_requested=False,
        )
        try:
            kv.data.insert(json.dumps(record))
        except Exception as e:
            logger.exception("async restore: failed to insert queued row")
            return {
                "payload": {
                    "response": f"Failed to register restore job: {str(e)}",
                },
                "status": 500,
            }

        # Auth context the worker needs. Captured here in the request
        # thread because request_info isn't safe to read from the
        # daemon thread (Splunk may close the request once the handler
        # returns).
        worker_session_key = request_info.session_key
        worker_port = request_info.server_rest_port
        worker_rest_uri = request_info.server_rest_uri
        worker_authtoken = request_info.system_authtoken
        worker_user = getattr(request_info, "user", None) or "unknown"

        # Build the worker request-info shim BEFORE spawning the thread,
        # so the variable is always bound when _worker's exception
        # handler runs. Building it inside the try-block (as a previous
        # iteration did) meant that if the very assignment raised —
        # OOM, attribute-set quirk, etc. — the outer except would hit
        # an UnboundLocalError accessing `worker_req` and the row
        # would stay in "queued" forever (auto-purge skips non-terminal
        # rows). Builds out here, captured by the _worker closure.
        class _WorkerRequestInfo:
            pass
        worker_req = _WorkerRequestInfo()
        worker_req.session_key = worker_session_key
        worker_req.server_rest_port = worker_port
        worker_req.server_rest_uri = worker_rest_uri
        worker_req.system_authtoken = worker_authtoken
        worker_req.user = worker_user

        def _worker():
            """Background restore. Catches every exception so the
            daemon thread never crashes silently — every terminal
            state writes a row with status in (completed, failed).

            Cancel semantics — known limitation
            ------------------------------------

            The worker only checks ``_restore_job_is_cancelled`` ONCE,
            right before calling ``_handle_restore_3_0_0``. Once the
            handler is running, the worker thread is blocked inside
            it (most often inside a synchronous HTTP POST issued by
            the SHC-delegation helper) and cannot poll the cancel
            flag.

            Practical implication: if an operator clicks "Cancel job"
            after the worker has crossed into ``_handle_restore_3_0_0``,
            the cancel request is recorded in the KV row
            (``cancel_requested=1``) but won't take effect until:
              * the synchronous step the worker is currently on
                returns naturally (typically seconds for local KV
                writes, up to the HTTP timeout for SHC delegation),
                or
              * the HTTP timeout in ``_v3_delegate_restore_to_peer``
                fires (1800s — kept generous to avoid false-failure
                timeouts on healthy-but-slow large-scale restores),
                at which point the worker unblocks and the outer
                exception handler finalises with status=failed.

            Honouring a cancel mid-archive (e.g. interrupting a
            ``batch_save`` or aborting an in-flight HTTP POST) would
            require either a separate watcher thread that aborts the
            request, or refactoring ``_handle_restore_3_0_0`` to
            yield control between work units. Both are larger
            architectural changes than the current design supports;
            documenting the limitation here so future work knows
            where the boundary is.
            """
            # Heartbeat thread (resumable-restore feature). Refreshes
            # ``last_heartbeat_epoch`` every HEARTBEAT_PERIOD seconds
            # so the status endpoint's stale-detector can tell the
            # difference between a healthy long-running task and a
            # silently-dead worker. Started right before the try-block
            # so even an early exception path triggers the finally
            # cleanup. Stopped in the finally — must NOT outlive the
            # worker (the heartbeat surviving a dead worker would
            # defeat the stale-detector). Daemon-flagged for the same
            # splunkd-recycle reason as the worker thread.
            hb_thread, hb_stop = self._restore_job_start_heartbeat(
                worker_req, job_id,
            )

            try:

                # Mark as running (records the moment the worker
                # actually picked the job up — useful when diagnosing
                # queue backpressure).
                #
                # NB: we pass `worker_req` (NOT the original
                # `request_info`) to every KV helper from this point
                # forward. The original request_info becomes unsafe to
                # read once the request thread returns to splunkd —
                # accessing it from the daemon thread can yield stale
                # / closed values, silently failing every status
                # update and stranding the job in "queued" forever.
                self._restore_job_update_status(
                    worker_req, job_id,
                    status="running",
                    progress="running",
                )

                # Cooperative cancel check before doing anything. See
                # the docstring for the limitation: this is the only
                # cancel-check point on the worker's hot path, so the
                # cancel only takes effect if it arrives before
                # _handle_restore_3_0_0 starts.
                if self._restore_job_is_cancelled(worker_req, job_id):
                    # Stop heartbeat BEFORE finalising — see the
                    # ordering note on the post-success finalise
                    # below. Bugbot finding on PR #1648 (Low).
                    try:
                        hb_stop.set()
                    except Exception:
                        pass
                    self._restore_job_finalise(
                        worker_req, job_id,
                        status="cancelled",
                        response={
                            "response": (
                                "Restore cancelled before any archive "
                                "was applied."
                            ),
                            "cancelled": True,
                        },
                    )
                    return

                # The actual work — synchronous from the worker's
                # perspective, but the gateway timeout doesn't apply
                # because there's no client connection waiting.
                response_payload = self._handle_restore_3_0_0(
                    request_info=worker_req,
                    backup_archive=body_params.get("backup_archive"),
                    backup_run_id=body_params.get("backup_run_id"),
                    dry_run=body_params.get("dry_run", True),
                    force_local=body_params.get("force_local", False),
                    restore_kvstore_collections=body_params.get(
                        "restore_kvstore_collections", True
                    ),
                    kvstore_collections_scope=body_params.get(
                        "kvstore_collections_scope", "all"
                    ),
                    kvstore_collections_clean_empty=body_params.get(
                        "kvstore_collections_clean_empty", True
                    ),
                    kvstore_collections_blocklist=body_params.get(
                        "kvstore_collections_blocklist", []
                    ),
                    kvstore_collections_restore_non_tenants_collections=body_params.get(
                        "kvstore_collections_restore_non_tenants_collections", True
                    ),
                    restore_knowledge_objects=body_params.get(
                        "restore_knowledge_objects", True
                    ),
                    knowledge_objects_replace_existing=body_params.get(
                        "knowledge_objects_replace_existing", True
                    ),
                    knowledge_objects_lists=body_params.get(
                        "knowledge_objects_lists", "all"
                    ),
                    knowledge_objects_blocklist=body_params.get(
                        "knowledge_objects_blocklist", []
                    ),
                    restore_virtual_tenant_accounts=body_params.get(
                        "restore_virtual_tenant_accounts", True
                    ),
                    restore_virtual_tenant_main_kvrecord=body_params.get(
                        "restore_virtual_tenant_main_kvrecord", True
                    ),
                    # Per-archive selective restore — must be forwarded
                    # to the call site or the async path silently
                    # ignores the operator's narrow selection and
                    # falls back to the flat-filter behaviour. (The
                    # synchronous path in post_restore picks this up
                    # via the same body_params dict; only the async
                    # worker rebuilds kwargs explicitly, which is why
                    # missing it here was a quiet regression.)
                    archives_scope=body_params.get("archives_scope") or {},
                    # Thread the worker's job_id through so any SHC
                    # delegation (``_v3_delegate_restore_to_peer``)
                    # can ship it to the receiving peer, which then
                    # writes the terminal status to
                    # ``kv_trackme_backup_restore_jobs`` directly when
                    # its work completes. Without this, the UI on the
                    # originating peer stays at ``running`` until the
                    # synchronous HTTP response from the receiving
                    # peer comes back — which Splunk's REST framework
                    # can hold for arbitrary post-write housekeeping
                    # time after saved-search CRUD operations.
                    _v3_origin_job_id=job_id,
                )

                # _handle_restore_3_0_0 returns {"payload": ..., "status": int}.
                # Unwrap to the bare response dict for the KV row.
                response_dict = response_payload.get("payload") or {}
                http_status = response_payload.get("status", 200)
                terminal = "completed" if http_status < 400 else "failed"
                # Stop the heartbeat BEFORE finalising. ``hb_stop.set()``
                # signals the heartbeat loop to exit at its next
                # check, but an in-flight iteration (already past the
                # status read, about to write) will complete its
                # write and could revert the terminal status to
                # ``running``. The terminal-status guard inside
                # ``_restore_job_heartbeat`` is the second line of
                # defence; this ordering is the first. Bugbot finding
                # on PR #1648 (Low).
                try:
                    hb_stop.set()
                except Exception:
                    pass
                self._restore_job_finalise(
                    worker_req, job_id,
                    status=terminal,
                    response=response_dict,
                )
            except Exception as e:
                logger.exception(
                    f'async restore worker crashed: job_id="{job_id}"'
                )
                # Stop heartbeat before the failure finalise — same
                # ordering rationale as the success path above.
                try:
                    hb_stop.set()
                except Exception:
                    pass
                try:
                    self._restore_job_finalise(
                        worker_req, job_id,
                        status="failed",
                        response={
                            "response": f"Worker exception: {str(e)}",
                            "exception": str(e),
                        },
                    )
                except Exception:
                    # If even the finalise write fails the row stays
                    # in `running` — but with the resumable-restore
                    # feature, the stale-detector will pick it up on
                    # the next poll (heartbeat thread is stopped just
                    # below, so it stops refreshing) and either resume
                    # or mark failed once MAX_RESUMES is exhausted.
                    pass
            finally:
                # Stop the heartbeat — defence in depth. The
                # in-line ``hb_stop.set()`` calls before each
                # ``_restore_job_finalise`` above are the primary
                # ordering guarantee against the heartbeat-vs-finalise
                # race. This finally block catches the early-return
                # paths (e.g. cancel-before-start above) and any
                # future exit path that forgets to stop the heartbeat
                # before finalising.
                try:
                    hb_stop.set()
                except Exception:
                    pass

        # Daemon thread so a splunkd restart doesn't hang on it. The
        # restore is idempotent at the per-archive level (post_restore
        # writes records into KV) so a half-finished restore is
        # recoverable by re-running once the SH comes back.
        thread = threading.Thread(
            target=_worker,
            name=f"trackme-restore-{job_id}",
            daemon=True,
        )
        thread.start()
        logger.info(
            f'async restore: spawned worker for job_id="{job_id}", '
            f'backup_run_id="{body_params.get("backup_run_id")}", '
            f'archive_name="{body_params.get("backup_archive")}", '
            f'dry_run={body_params.get("dry_run")}'
        )

        return {
            "payload": {
                "response": "Restore submitted asynchronously.",
                "job_id": job_id,
                "status": "queued",
                "started_epoch": started_epoch,
                "poll_url": (
                    "/services/trackme/v2/backup_and_restore/"
                    f"restore_job_status?job_id={job_id}"
                ),
            },
            "status": 202,
        }

    def _restore_job_update_status(
        self,
        request_info,
        job_id,
        status,
        progress=None,
        response=None,
    ):
        """Update a job row's status. Best-effort — failures are
        logged but not propagated (the worker carries on; the operator
        sees the row eventually settle into a terminal state).

        Splunk's KV store update is full-document replace — there's no
        native PATCH semantics. To minimise the TOCTOU window where a
        concurrent DELETE /restore_job might set cancel_requested=1
        between this method's read and write (and the worker's
        full-doc write would silently overwrite the cancel back to 0),
        we re-read cancel_requested IMMEDIATELY before the write. The
        race window collapses from "duration of update_status" to
        "few microseconds between final read and write". This isn't
        perfect (a true CAS would be), but it's two orders of
        magnitude smaller than human DELETE latency and the cancel
        check between archives provides a second line of defence.
        """
        now = int(round(time.time()))
        try:
            kv = self._restore_job_kv(request_info)
            existing = kv.data.query_by_id(job_id)
            new_record = dict(existing or {})
            new_record["status"] = status
            new_record["mtime"] = now
            if progress is not None:
                new_record["progress"] = str(progress)
            if response is not None:
                try:
                    new_record["response"] = json.dumps(response)
                except Exception:
                    new_record["response"] = json.dumps(
                        {"error": "response not serialisable"}
                    )
            # Re-read cancel_requested immediately before writing —
            # narrows the TOCTOU race window to microseconds. If
            # delete_restore_job fired between this method's first
            # read and now, we honour the cancel rather than overwriting it.
            try:
                fresh = kv.data.query_by_id(job_id)
                if fresh and "cancel_requested" in fresh:
                    new_record["cancel_requested"] = fresh["cancel_requested"]
            except Exception:
                pass
            # `_key` is implicit when we use update_by_id; strip it from
            # the payload to avoid Splunk REST rejecting the duplicate.
            new_record.pop("_key", None)
            kv.data.update(job_id, json.dumps(new_record))
        except Exception as e:
            logger.warning(
                f'async restore: status update failed for job_id="{job_id}", '
                f'status="{status}": {str(e)}'
            )

    def _restore_job_finalise(
        self,
        request_info,
        job_id,
        status,
        response,
    ):
        """Terminal status update — sets finished_epoch and the final
        response payload.

        Idempotent w.r.t. terminal states: if the row is already in a
        terminal status (``completed`` / ``failed`` / ``cancelled``),
        this call is a no-op. Necessary because in SHC scenarios two
        peers may try to finalise the same row:

          * the RECEIVING peer of a delegated restore writes the
            terminal status at the end of ``_handle_restore_3_0_0``
            (cluster-KV completion-signalling path — see that method's
            docstring), and
          * the ORIGINATING peer's async worker then receives the
            HTTP response and tries to finalise normally.

        Without the idempotency guard, the second writer would
        overwrite the first's terminal payload with a possibly
        stale-looking one (e.g. ``failed`` from a late HTTP error
        even though ``completed`` was already written). Trust the
        first-wins terminal state.

        Same TOCTOU mitigation as _restore_job_update_status: re-read
        cancel_requested just before the write so a late-arriving
        DELETE /restore_job isn't silently lost. Once finalise lands,
        delete_restore_job's 409 check ensures no further cancel
        attempts are accepted on this row.
        """
        now = int(round(time.time()))
        try:
            kv = self._restore_job_kv(request_info)
            existing = kv.data.query_by_id(job_id)
            current_status = (existing or {}).get("status")
            if current_status in ("completed", "failed", "cancelled"):
                # Already terminal — trust the first writer. This is the
                # idempotency contract required by the SHC cluster-KV
                # completion-signalling path. Without it, sh1's worker
                # would overwrite sh3's already-written terminal status
                # when the HTTP response eventually comes back.
                logger.info(
                    f'async restore: job_id="{job_id}" already finalised '
                    f'as "{current_status}"; skipping this finalise '
                    f'attempt (caller wanted status="{status}")'
                )
                return
            new_record = dict(existing or {})
            new_record["status"] = status
            new_record["mtime"] = now
            new_record["finished_epoch"] = now
            new_record["progress"] = status
            try:
                new_record["response"] = json.dumps(response)
            except Exception:
                new_record["response"] = json.dumps(
                    {"error": "response not serialisable"}
                )
            # Same TOCTOU mitigation — see _restore_job_update_status.
            try:
                fresh = kv.data.query_by_id(job_id)
                if fresh and "cancel_requested" in fresh:
                    new_record["cancel_requested"] = fresh["cancel_requested"]
            except Exception:
                pass
            new_record.pop("_key", None)
            kv.data.update(job_id, json.dumps(new_record))
            logger.info(
                f'async restore: job_id="{job_id}" finalised as "{status}"'
            )
        except Exception as e:
            logger.error(
                f'async restore: finalise failed for job_id="{job_id}", '
                f'status="{status}": {str(e)}'
            )

    def _restore_job_is_cancelled(self, request_info, job_id):
        """Worker-side cancel check. Returns True if DELETE
        /restore_job has set cancel_requested=1 on this row."""
        try:
            kv = self._restore_job_kv(request_info)
            existing = kv.data.query_by_id(job_id)
            return str((existing or {}).get("cancel_requested", "0")) == "1"
        except Exception:
            return False

    def _restore_job_purge_stale(self, request_info):
        """Opportunistic auto-purge — called from get_restore_job_status
        before a read. Removes terminal jobs older than the TTL.
        Running rows are never purged (see comment on the TTL constant).

        Rate-limited by ``_RESTORE_JOB_PURGE_MIN_INTERVAL_SECONDS``: the
        frontend polls every 2–3s and the underlying purge work is a
        full table scan + delete loop, so without the gate two KV
        connections + one unbounded scan would fire per poll per
        concurrent frontend. The gate skips purging if a recent purge
        already ran; the worst case is that a row's deletion is delayed
        by up to the gate interval past its TTL, which is fine on a
        24-hour terminal grace window.
        """
        now = int(round(time.time()))
        if now - type(self)._restore_job_last_purge_epoch < self._RESTORE_JOB_PURGE_MIN_INTERVAL_SECONDS:
            return
        # Update the gate before doing the work — even if the purge
        # itself raises, we don't want a permanently failing purge to
        # turn every poll into a retry storm.
        type(self)._restore_job_last_purge_epoch = now
        cutoff = now - self._RESTORE_JOB_TERMINAL_TTL_SECONDS
        try:
            kv = self._restore_job_kv(request_info)
            rows = kv.data.query() or []
            for row in rows:
                status = str(row.get("status", ""))
                finished = int(row.get("finished_epoch", 0) or 0)
                if status in ("completed", "failed", "cancelled") and finished and finished < cutoff:
                    try:
                        kv.data.delete_by_id(row.get("_key"))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"async restore: auto-purge failed: {str(e)}")

    # ====================================================================
    # Resumable restore — task-list + heartbeat + auto-recover
    #
    # Problem this solves: the daemon worker thread can die silently
    # mid-restore (splunkd subprocess recycling during a long-blocking
    # call, an uncaught exception in a less-traveled code path, OOM
    # killers, etc.). Before this addition, that left the job row stuck
    # in ``status=running`` forever — auto-purge skips non-terminal
    # rows, so the orphan would never be cleaned up, and the operator
    # had no way to know the restore actually died. The UI just spun.
    #
    # Design:
    #   1. At first dispatch, the worker enumerates the full task list
    #      (per archive × per step) and writes it to the job row's
    #      ``tasks`` field as a JSON array.
    #   2. A daemon heartbeat thread runs alongside the restore worker,
    #      updating ``last_heartbeat_epoch`` every ``HEARTBEAT_PERIOD``.
    #      If the worker dies, so does the heartbeat (same subprocess);
    #      stale heartbeat is the signal that something went wrong.
    #   3. Before running each task, the worker checks ``status`` in
    #      the in-memory task list (refreshed from KV on resume). If
    #      already ``done``, the task is skipped — restore resumes
    #      exactly from the first incomplete task.
    #   4. After each task completes, the worker writes the updated
    #      status to KV.
    #   5. ``GET /restore_job_status`` checks: if ``status==running``
    #      AND ``now - last_heartbeat_epoch > STALE_THRESHOLD``, it
    #      atomically claims the worker slot (CAS via ``worker_epoch``)
    #      and spawns a fresh daemon worker. The fresh worker reads
    #      the task list, skips done tasks, runs the rest.
    #
    # The recovery is bounded by ``MAX_RESUMES`` to avoid an infinite
    # retry loop in pathological cases where a specific task always
    # fails. Once that ceiling is hit, the job is finalised with
    # ``status=failed`` so the operator can investigate.
    #
    # Per-task idempotency requirements (the restore code already
    # honours these — they're the reason the existing per-archive
    # restart contract works):
    #   * step 1a (safety guard): "tenant in KV?" check makes it a
    #     no-op on retry.
    #   * step 1b (central record overlay): kv.data.update / insert by
    #     ``_key`` is deterministic upsert.
    #   * step 2 (vtenant_account): overwrites existing.
    #   * step 3 (knowledge objects): governed by
    #     ``knowledge_objects_replace_existing``; restore honours True
    #     by default — re-runs cleanly.
    #   * step 4 (KV records): ``batch_save`` with same ``_key`` is
    #     upsert; the per-collection clean-empty option re-applies
    #     deterministically.
    # ====================================================================

    # Heartbeat the worker writes while alive — chosen so a stale
    # heartbeat is unambiguously a dead worker (legitimate long tasks
    # like ``post_add_tenant`` finish in 60-90s on SHC, well under the
    # stale threshold).
    _RESTORE_JOB_HEARTBEAT_PERIOD_SECONDS = 30

    # If ``last_heartbeat_epoch`` is older than this, the worker is
    # presumed dead and the resume path is triggered on the next poll.
    # Generous (5 min) so transient KV-write delays don't false-trigger
    # a resume — the worker writes at task transitions AND every
    # ``HEARTBEAT_PERIOD`` seconds via the heartbeat thread, so the
    # observed gap is normally under 30s.
    _RESTORE_JOB_STALE_THRESHOLD_SECONDS = 300

    # Cap on resume attempts. If the worker keeps dying at the same
    # task, repeated resumes would loop forever — instead, after this
    # many resumes the job is finalised as ``failed`` and the operator
    # is notified via the response.
    _RESTORE_JOB_MAX_RESUMES = 5

    def _restore_job_compute_archive_tasks(self, archive_row, body_params):
        """Build the task list for ONE archive — invoked by the worker
        once we know the archive's scope and tenant_id. Returns an
        ordered list of task dicts (id, label, status, started_epoch,
        completed_epoch, error).

        Task granularity (this PR — per archive × per step):
          * ``extract``               — decompress + tar-extract the archive.
          * ``step_1a_safety_guard``  — recreate missing tenant (tenant scope only).
          * ``step_1b_global_overlay``— overlay central record from global archive (tenant scope only).
          * ``step_2_vtenant_account``— restore vtenant_account JSON (tenant scope only).
          * ``step_3_knowledge_objects`` — restore tenant KOs (tenant scope only).
          * ``step_4_kv``             — restore KV collection records (all scopes).

        Steps gated on ``body_params`` flags are still emitted as
        tasks; the worker marks them ``skipped`` rather than ``done``
        so the operator can see what was bypassed on purpose vs.
        what actually executed. Skipped is a terminal state for resume
        purposes (the worker doesn't re-attempt them).

        For run-mode restores the caller concatenates per-archive task
        lists into the full job task list — the task IDs are
        archive-scoped (``arch:<basename>:...``) so they don't collide.
        """
        archive_path = archive_row.get("backup_archive") or ""
        archive_filename = os.path.basename(archive_path)
        archive_scope = archive_row.get("archive_scope") or ""
        prefix = f"arch:{archive_filename}"

        is_tenant = archive_scope == ARCHIVE_SCOPE_TENANT
        # Step gates — mirror the conditions in _v3_restore_one_archive.
        gate_1 = is_tenant and bool(
            body_params.get("restore_virtual_tenant_main_kvrecord", True)
        )
        gate_2 = is_tenant and bool(
            body_params.get("restore_virtual_tenant_accounts", True)
        )
        gate_3 = is_tenant and bool(
            body_params.get("restore_knowledge_objects", True)
        )
        kv_enabled = bool(body_params.get("restore_kvstore_collections", True))
        # Global-archive KV-restore can be additionally suppressed via
        # the legacy non-tenants flag — mirror that here so the task
        # list reflects what the worker will actually do.
        if (
            archive_scope == ARCHIVE_SCOPE_GLOBAL
            and not bool(body_params.get(
                "kvstore_collections_restore_non_tenants_collections", True
            ))
        ):
            kv_enabled = False

        def _t(task_id, label, gated_on):
            return {
                "id": task_id,
                "label": label,
                "status": "pending" if gated_on else "skipped",
                "started_epoch": 0,
                "completed_epoch": 0,
                "error": "",
                # JSON-encoded dict carrying outcome data the
                # resumed worker needs to reconstruct ``tenant_recreated``
                # / ``tenant_record_restored_from_global`` accurately
                # when skipping a previously-done task. Empty string
                # when no outcome data is recorded. Bugbot finding on
                # PR #1647 (Low).
                "info": "",
            }

        tasks = [
            _t(f"{prefix}:step:extract", f"Extract {archive_filename}", True),
            _t(f"{prefix}:step:step_1a_safety_guard",
               f"Recreate tenant if missing ({archive_filename})", gate_1),
            _t(f"{prefix}:step:step_1b_global_overlay",
               f"Overlay central record from global archive ({archive_filename})", gate_1),
            _t(f"{prefix}:step:step_2_vtenant_account",
               f"Restore vtenant_account ({archive_filename})", gate_2),
            _t(f"{prefix}:step:step_3_knowledge_objects",
               f"Restore knowledge objects ({archive_filename})", gate_3),
            _t(f"{prefix}:step:step_4_kv",
               f"Restore KV collection records ({archive_filename})", kv_enabled),
        ]
        return tasks

    def _restore_job_init_tasks(self, request_info, job_id, tasks_list):
        """First-write of the task list to the job row. Idempotent on
        resume: if ``tasks`` is already present, leaves it alone —
        the original list (with completion markers) IS the source of
        truth for the resume path.

        Also seeds ``last_heartbeat_epoch`` and ``worker_epoch`` so
        the stale-detector has values to read on the first poll.
        """
        try:
            kv = self._restore_job_kv(request_info)
            existing = kv.data.query_by_id(job_id) or {}
        except Exception as e:
            logger.warning(
                f'resumable restore: init_tasks read failed for '
                f'job_id="{job_id}": {str(e)}'
            )
            return
        if existing.get("tasks"):
            # Resume path — preserve the existing list (with whatever
            # done/pending markers the previous worker had committed).
            return
        now = int(time.time())
        new_record = dict(existing)
        new_record["tasks"] = json.dumps(tasks_list)
        new_record["last_heartbeat_epoch"] = now
        # Bump worker_epoch on every (re-)start. First start: 1.
        new_record["worker_epoch"] = int(existing.get("worker_epoch", 0)) + 1
        new_record["resume_count"] = int(existing.get("resume_count", 0))
        new_record["mtime"] = now
        new_record.pop("_key", None)
        try:
            kv.data.update(job_id, json.dumps(new_record))
        except Exception as e:
            logger.warning(
                f'resumable restore: init_tasks write failed for '
                f'job_id="{job_id}": {str(e)}'
            )

    def _restore_job_load_tasks(self, request_info, job_id):
        """Read the task list back from KV. Returns the list (or [] on
        failure) and the parsed row for context. Used by the worker on
        every task transition so the in-memory view doesn't drift from
        what the status endpoint / a concurrent claim would see.
        """
        try:
            kv = self._restore_job_kv(request_info)
            row = kv.data.query_by_id(job_id) or {}
            raw = row.get("tasks") or "[]"
            tasks = json.loads(raw) if isinstance(raw, str) else (raw or [])
            if not isinstance(tasks, list):
                tasks = []
            return tasks, row
        except Exception as e:
            logger.warning(
                f'resumable restore: load_tasks failed for '
                f'job_id="{job_id}": {str(e)}'
            )
            return [], {}

    def _restore_job_mark_task(
        self, request_info, job_id, task_id, status, error_msg="",
        info_dict=None,
    ):
        """Update one task's status in KV. Also updates
        ``last_heartbeat_epoch`` to ``now`` (every task transition is
        a natural heartbeat) and writes a one-line progress string for
        the existing UI/log surface.

        ``status`` is one of: ``in_progress``, ``done``, ``skipped``,
        ``failed``. ``error_msg`` populates the per-task ``error``
        field on failure for forensic readouts.

        ``info_dict`` (optional) — outcome data the resumed worker
        may need to reconstruct return-value bools accurately when
        skipping a previously-done task. Stored as a JSON-encoded
        string in the task's ``info`` field. Read back via
        ``_restore_job_get_task_info``. Bugbot finding on PR #1647
        (Low).
        """
        try:
            tasks, row = self._restore_job_load_tasks(request_info, job_id)
        except Exception:
            return
        if not tasks:
            return
        now = int(time.time())
        found = False
        for t in tasks:
            if t.get("id") == task_id:
                t["status"] = status
                if status == "in_progress" and not t.get("started_epoch"):
                    t["started_epoch"] = now
                if status in ("done", "skipped", "failed"):
                    t["completed_epoch"] = now
                if error_msg:
                    t["error"] = str(error_msg)[:1000]
                if info_dict is not None:
                    try:
                        t["info"] = json.dumps(info_dict)
                    except Exception:
                        # Non-serialisable info — leave field alone
                        # rather than store malformed JSON.
                        pass
                found = True
                break
        if not found:
            # Defensive: a task that's not in the list shouldn't be
            # marked. Log so a future maintainer notices the drift.
            logger.warning(
                f'resumable restore: mark_task called with unknown '
                f'task_id="{task_id}" for job_id="{job_id}"'
            )
            return
        try:
            kv = self._restore_job_kv(request_info)
            new_record = dict(row)
            new_record["tasks"] = json.dumps(tasks)
            new_record["last_heartbeat_epoch"] = now
            new_record["mtime"] = now
            new_record["progress"] = f"{task_id}={status}"
            new_record.pop("_key", None)
            kv.data.update(job_id, json.dumps(new_record))
        except Exception as e:
            logger.warning(
                f'resumable restore: mark_task write failed for '
                f'job_id="{job_id}", task_id="{task_id}", status="{status}": {str(e)}'
            )

    def _restore_job_get_task_info(self, tasks, task_id):
        """Read the JSON-encoded outcome dict from a task's ``info``
        field. Returns ``{}`` on missing / malformed / no task. Used
        by resumed workers to reconstruct outcome bools when
        skipping a previously-done task. Bugbot finding on PR #1647
        (Low).
        """
        for t in (tasks or []):
            if t.get("id") == task_id:
                raw = t.get("info") or ""
                if not raw:
                    return {}
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
        return {}

    def _restore_job_is_task_done(self, tasks, task_id):
        """In-memory check: is this task already in a terminal state?
        Used by the worker to skip tasks on resume. ``done`` and
        ``skipped`` are both terminal (skipped means the body_params
        flag was off — re-running wouldn't change anything). ``failed``
        is NOT considered terminal here: a failed task gets re-tried
        on resume up to MAX_RESUMES, since the original failure may
        have been transient (e.g. the silent thread death we're
        protecting against).
        """
        for t in (tasks or []):
            if t.get("id") == task_id:
                return t.get("status") in ("done", "skipped")
        return False

    def _restore_job_get_task_status(self, tasks, task_id):
        """In-memory lookup: return the task's current status string
        (``"done"``, ``"skipped"``, ``"failed"``, ``"in_progress"``,
        ``"pending"``) or ``None`` if the task is absent.

        Companion to :py:meth:`_restore_job_is_task_done`. Where that
        helper collapses ``done`` and ``skipped`` into a single
        terminal boolean (used to decide whether to re-run a step on
        resume), this helper preserves the distinction so the resume
        worker can craft accurate operator-visible messaging.

        Without this distinction, a prior-``skipped`` step (e.g. the
        archive manifest had no ``vtenant_account_file`` or
        ``knowledge_objects_file`` so the original worker correctly
        skipped that step) would surface on the resumed worker as
        ``"restored ... (preserved from earlier worker)"`` — misleading
        the operator into thinking work was performed when nothing was
        actually restored. Bugbot finding on PR #1647 (Low) /
        AI-Agent-sync PR #1648.
        """
        for t in (tasks or []):
            if t.get("id") == task_id:
                return t.get("status")
        return None

    def _restore_job_heartbeat(self, request_info, job_id):
        """Write a heartbeat — refreshes ``last_heartbeat_epoch`` to
        ``now`` without touching task statuses or progress strings.
        Called periodically by the heartbeat thread while the worker
        is alive. Cheap (one KV update) and the stale-detector reads
        only this field, so a misfire here is the failure mode we
        accept (worse case: a false-positive resume gets triggered;
        the resume itself is idempotent).

        TOCTOU mitigation against concurrent ``_restore_job_mark_task``
        writes: do a single read immediately before the write. The
        narrowing comes from the proximity of read-to-write
        (microseconds, just dict-update + JSON-serialise), not from
        doing two reads.

        Defense against the heartbeat-vs-finalise race: skip the
        write entirely when the row is already in a terminal status
        (``completed`` / ``failed`` / ``cancelled``). Without this,
        a heartbeat in flight when ``_restore_job_finalise`` writes
        could revert the terminal status back to ``running``
        (heartbeat read at T → finalise write at T+epsilon →
        heartbeat write at T+2*epsilon with the stale ``running``
        snapshot). The dispatcher also stops the heartbeat thread
        BEFORE finalising (see ``_dispatch_restore_async._worker``
        and ``_resume_worker``), but ``hb_stop.set()`` only signals
        the loop to exit at its next check — an in-flight iteration
        completes its write. The terminal-status check here is the
        defence-in-depth that closes the window. Bugbot finding on
        PR #1648 (Low).
        """
        try:
            kv = self._restore_job_kv(request_info)
            # Single read just before write. If a concurrent
            # ``_restore_job_mark_task`` writes BETWEEN this read
            # and our write, its update would be overwritten — but
            # that window is microseconds (just dict-update +
            # JSON-serialise) and the worker's mark_task calls are
            # spaced by full step durations (seconds to minutes), so
            # the practical collision rate is negligible.
            row = kv.data.query_by_id(job_id) or {}
            if not row:
                return
            # Skip the heartbeat write if the row has already reached
            # a terminal status — writing here would revert it.
            if str(row.get("status") or "") in ("completed", "failed", "cancelled"):
                return
            new_record = dict(row)
            new_record["last_heartbeat_epoch"] = int(time.time())
            new_record.pop("_key", None)
            kv.data.update(job_id, json.dumps(new_record))
        except Exception:
            # Heartbeat failures are non-fatal — they just delay the
            # stale-detector's view of the worker's liveness. Log at
            # debug-only verbosity in a future iteration if this
            # becomes too chatty.
            pass

    def _restore_job_start_heartbeat(self, request_info, job_id):
        """Spawn a daemon thread that calls ``_restore_job_heartbeat``
        every ``HEARTBEAT_PERIOD`` seconds until ``stop_event`` is set.
        Returns ``(thread, stop_event)`` so the worker can stop it
        cleanly on exit. Daemon-flagged so a splunkd recycle doesn't
        leave it dangling.

        Note on the thread-death failure mode: if the splunkd
        subprocess gets recycled, BOTH the worker thread AND this
        heartbeat thread die together (same Python interpreter
        instance). That's exactly the property the stale-detector
        relies on — the heartbeat stops being refreshed, the gap
        exceeds the threshold, and the status endpoint's resume path
        fires. If the heartbeat thread happened to survive while the
        worker died, the resume would never trigger; daemon-flagging
        and shared-interpreter binding ensures that doesn't happen.
        """
        stop_event = threading.Event()

        def _hb():
            while not stop_event.is_set():
                self._restore_job_heartbeat(request_info, job_id)
                # ``Event.wait(timeout)`` is interruptible — we get a
                # clean shutdown the moment the worker calls
                # ``stop_event.set()`` rather than waiting up to the
                # full HEARTBEAT_PERIOD.
                if stop_event.wait(self._RESTORE_JOB_HEARTBEAT_PERIOD_SECONDS):
                    return

        thread = threading.Thread(
            target=_hb,
            name=f"trackme-restore-hb-{job_id[:8]}",
            daemon=True,
        )
        thread.start()
        return thread, stop_event

    # Minimum job age before the watchdog is permitted to claim a
    # resume. Defends against the duplicate-worker race even if a
    # future regression re-introduces a missing-``last_heartbeat_epoch``
    # window between row-insert and the worker's first heartbeat.
    # Set conservatively: the heartbeat thread is started right after
    # the row insert (sub-second) and writes its first heartbeat
    # immediately, so 60s is comfortably larger than any plausible
    # cold-start latency on a healthy SHC peer. A genuinely-dead
    # worker is detected via the normal
    # ``STALE_THRESHOLD_SECONDS=300`` path so this grace period is
    # immaterial to real-world recovery latency.
    _RESTORE_JOB_MIN_AGE_BEFORE_RESUME_SECONDS = 60

    def _restore_job_should_resume(self, row):
        """Stale-detection predicate. Returns True if the job row
        looks like a dead worker that needs to be resumed.

        Conditions (ALL must hold):
          * ``status == "running"`` — we don't resume queued (not yet
            started — let the original dispatch flow), nor terminal
            states.
          * Job age (``now - started_epoch``) is greater than
            ``MIN_AGE_BEFORE_RESUME`` — defends against the
            duplicate-worker race: even if ``last_heartbeat_epoch``
            looks stale (missing / zero / very old), don't resume a
            row whose worker is still in its cold-start window.
            ``_restore_job_record`` now seeds ``last_heartbeat_epoch``
            on the initial INSERT so the missing-hb window has been
            closed at source; this gate is the second line of
            defence so a future regression that re-introduces the
            window doesn't quietly re-spawn duplicate workers.
            Defaults to "old enough" when ``started_epoch`` is
            missing so legacy pre-resumable rows still get recovered.
          * ``last_heartbeat_epoch`` is older than ``STALE_THRESHOLD``.
            Missing field counts as "stale" — pre-resumable rows have
            no heartbeat, so any old job in ``running`` from before
            this PR will be resumed on the first poll after upgrade.
          * ``resume_count < MAX_RESUMES`` — circuit-breaker to avoid
            infinite retry on a persistently-broken task.
        """
        status = str(row.get("status") or "")
        if status != "running":
            return False
        now = int(time.time())
        # Cold-start grace period — see class-level comment on
        # _RESTORE_JOB_MIN_AGE_BEFORE_RESUME_SECONDS.
        try:
            started = int(row.get("started_epoch") or 0)
        except (TypeError, ValueError):
            started = 0
        if started and (now - started) < self._RESTORE_JOB_MIN_AGE_BEFORE_RESUME_SECONDS:
            return False
        try:
            hb = int(row.get("last_heartbeat_epoch") or 0)
        except (TypeError, ValueError):
            hb = 0
        if hb and now - hb < self._RESTORE_JOB_STALE_THRESHOLD_SECONDS:
            return False
        try:
            resume_count = int(row.get("resume_count") or 0)
        except (TypeError, ValueError):
            resume_count = 0
        if resume_count >= self._RESTORE_JOB_MAX_RESUMES:
            return False
        return True

    def _restore_job_try_claim_resume(self, request_info, job_id):
        """CAS-style attempt to claim the resume slot. Returns True if
        we successfully claimed it (and should spawn a worker); False
        if someone else got there first or the row no longer looks
        stale.

        Mechanism: read the current ``worker_epoch``, check the
        staleness predicate, then update with ``worker_epoch =
        current + 1`` AND ``last_heartbeat_epoch = now``. Splunk KV
        doesn't have native CAS, so this isn't perfectly atomic —
        the race window is one KV-read + one KV-write apart. We
        partially mitigate by re-reading just before the write and
        confirming ``worker_epoch`` hasn't moved. Worst case if two
        polls race: both spawn workers; the second one immediately
        sees the first's heartbeat and exits (the worker's first act
        on entry is to verify it still owns ``worker_epoch``).
        """
        try:
            kv = self._restore_job_kv(request_info)
            row = kv.data.query_by_id(job_id) or {}
        except Exception as e:
            logger.warning(
                f'resumable restore: claim_resume read failed for '
                f'job_id="{job_id}": {str(e)}'
            )
            return False
        if not row:
            return False
        if not self._restore_job_should_resume(row):
            return False
        try:
            current_epoch = int(row.get("worker_epoch") or 0)
            resume_count = int(row.get("resume_count") or 0)
        except (TypeError, ValueError):
            current_epoch = 0
            resume_count = 0
        # Re-read to narrow the CAS window. If worker_epoch moved
        # between the first read and now, someone else claimed it.
        try:
            fresh = kv.data.query_by_id(job_id) or {}
            try:
                fresh_epoch = int(fresh.get("worker_epoch") or 0)
            except (TypeError, ValueError):
                fresh_epoch = 0
            if fresh_epoch != current_epoch:
                return False
        except Exception:
            return False
        new_epoch = current_epoch + 1
        now = int(time.time())
        new_record = dict(fresh)
        new_record["worker_epoch"] = new_epoch
        new_record["resume_count"] = resume_count + 1
        new_record["last_heartbeat_epoch"] = now
        new_record["mtime"] = now
        new_record["progress"] = f"resuming (attempt {resume_count + 1})"
        new_record.pop("_key", None)
        try:
            kv.data.update(job_id, json.dumps(new_record))
        except Exception as e:
            logger.warning(
                f'resumable restore: claim_resume write failed for '
                f'job_id="{job_id}": {str(e)}'
            )
            return False
        logger.info(
            f'resumable restore: claimed resume for job_id="{job_id}" '
            f'(worker_epoch {current_epoch}→{new_epoch}, '
            f'resume_count {resume_count}→{resume_count + 1})'
        )
        return True

    def _restore_job_spawn_resume_worker(self, request_info, job_id):
        """Spawn a fresh daemon worker that re-enters
        ``_handle_restore_3_0_0`` for the same job_id. The worker reads
        the existing task list from KV and skips tasks already marked
        ``done`` or ``skipped``, picking up exactly where the previous
        worker died. Authentication and connection params are captured
        in the request-thread closure (same pattern as the original
        ``_dispatch_restore_async``) so the daemon thread never reads
        ``request_info`` after splunkd may have closed it.
        """
        try:
            kv = self._restore_job_kv(request_info)
            row = kv.data.query_by_id(job_id) or {}
        except Exception as e:
            logger.warning(
                f'resumable restore: spawn_resume read failed for '
                f'job_id="{job_id}": {str(e)}'
            )
            return False
        if not row:
            return False
        # Deserialise the original body_params so the resumed worker
        # makes the same call shape the original did. The fresh worker
        # builds its task list from the same body, so the resume path
        # matches the original task IDs exactly.
        try:
            body_params = json.loads(row.get("request_args") or "{}")
        except Exception as e:
            logger.error(
                f'resumable restore: cannot parse request_args for '
                f'job_id="{job_id}": {str(e)}; resume aborted'
            )
            return False

        # Capture auth context in this thread.
        worker_port = request_info.server_rest_port
        worker_rest_uri = request_info.server_rest_uri
        worker_authtoken = request_info.system_authtoken
        worker_session_key = request_info.session_key
        worker_user = getattr(request_info, "user", None) or "unknown"

        class _WorkerRequestInfo:
            pass
        worker_req = _WorkerRequestInfo()
        worker_req.session_key = worker_session_key
        worker_req.server_rest_port = worker_port
        worker_req.server_rest_uri = worker_rest_uri
        worker_req.system_authtoken = worker_authtoken
        worker_req.user = worker_user

        # Snapshot the claimed worker_epoch so the resumed worker can
        # verify it still owns the slot before starting heavy work.
        # If a SECOND status endpoint poll spawned another resume after
        # we already did, that resume will bump worker_epoch further;
        # this worker, finding its captured value no longer current,
        # exits cleanly without doing duplicate work.
        #
        # IMPORTANT: by the time this code runs, ``_restore_job_try_claim_resume``
        # has already written the bumped worker_epoch to KV, so the
        # row we just re-read above ALREADY reflects the post-claim
        # value. An earlier iteration of this code added ``+ 1`` here,
        # producing a value one higher than what KV actually held —
        # the worker's ownership check then ALWAYS mismatched and the
        # resume silently no-op'd. Bugbot finding on PR #1647 (High).
        try:
            claimed_epoch = int(row.get("worker_epoch") or 0)
        except (TypeError, ValueError):
            claimed_epoch = 0

        def _resume_worker():
            try:
                # Confirm we still own the slot we claimed before
                # starting heavy work. If a parallel resume bumped the
                # epoch further, defer to that worker.
                try:
                    fresh = self._restore_job_kv(worker_req).data.query_by_id(job_id) or {}
                    try:
                        fresh_epoch = int(fresh.get("worker_epoch") or 0)
                    except (TypeError, ValueError):
                        fresh_epoch = 0
                    if fresh_epoch != claimed_epoch:
                        logger.info(
                            f'resumable restore: resumed worker for '
                            f'job_id="{job_id}" found worker_epoch '
                            f'{fresh_epoch} (expected {claimed_epoch}); '
                            f'another resume took over, exiting'
                        )
                        return
                except Exception:
                    # Lost the ability to verify — defer rather than
                    # risk duplicate work.
                    logger.warning(
                        f'resumable restore: resumed worker for '
                        f'job_id="{job_id}" cannot verify ownership; '
                        f'exiting'
                    )
                    return

                # Cooperative cancel check before any work — mirrors
                # the same check the original ``_dispatch_restore_async``
                # worker performs (line ~10584). Without it, an
                # operator's ``cancel_requested=1`` set while the
                # original worker was dying would be silently ignored
                # by the resumed worker, which would complete the
                # restore against the user's explicit cancellation
                # intent. Bugbot finding on PR #1647 (Medium).
                #
                # NB: the heartbeat thread isn't started yet at this
                # point (it's started just below), so there's no
                # ``hb_stop.set()`` to call before finalising here.
                if self._restore_job_is_cancelled(worker_req, job_id):
                    self._restore_job_finalise(
                        worker_req, job_id,
                        status="cancelled",
                        response={
                            "response": (
                                "Restore cancelled before resumed "
                                "worker resumed any task."
                            ),
                            "cancelled": True,
                        },
                    )
                    return

                # Start the heartbeat for this resumed worker so the
                # next poll sees fresh liveness signals. Stop on exit.
                hb_thread, hb_stop = self._restore_job_start_heartbeat(
                    worker_req, job_id,
                )
                try:
                    response_payload = self._handle_restore_3_0_0(
                        request_info=worker_req,
                        backup_archive=body_params.get("backup_archive"),
                        backup_run_id=body_params.get("backup_run_id"),
                        dry_run=body_params.get("dry_run", True),
                        force_local=body_params.get("force_local", False),
                        restore_kvstore_collections=body_params.get(
                            "restore_kvstore_collections", True
                        ),
                        kvstore_collections_scope=body_params.get(
                            "kvstore_collections_scope", "all"
                        ),
                        kvstore_collections_clean_empty=body_params.get(
                            "kvstore_collections_clean_empty", True
                        ),
                        kvstore_collections_blocklist=body_params.get(
                            "kvstore_collections_blocklist", []
                        ),
                        kvstore_collections_restore_non_tenants_collections=body_params.get(
                            "kvstore_collections_restore_non_tenants_collections", True
                        ),
                        restore_knowledge_objects=body_params.get(
                            "restore_knowledge_objects", True
                        ),
                        knowledge_objects_replace_existing=body_params.get(
                            "knowledge_objects_replace_existing", True
                        ),
                        knowledge_objects_lists=body_params.get(
                            "knowledge_objects_lists", "all"
                        ),
                        knowledge_objects_blocklist=body_params.get(
                            "knowledge_objects_blocklist", []
                        ),
                        restore_virtual_tenant_accounts=body_params.get(
                            "restore_virtual_tenant_accounts", True
                        ),
                        restore_virtual_tenant_main_kvrecord=body_params.get(
                            "restore_virtual_tenant_main_kvrecord", True
                        ),
                        archives_scope=body_params.get("archives_scope") or {},
                        _v3_origin_job_id=job_id,
                    )
                    response_dict = response_payload.get("payload") or {}
                    http_status = response_payload.get("status", 200)
                    terminal = "completed" if http_status < 400 else "failed"
                    # Stop the heartbeat BEFORE finalising. Same race
                    # rationale as the original worker — see the
                    # ordering note in ``_dispatch_restore_async._worker``.
                    # Bugbot finding on PR #1648 (Low).
                    try:
                        hb_stop.set()
                    except Exception:
                        pass
                    self._restore_job_finalise(
                        worker_req, job_id,
                        status=terminal,
                        response=response_dict,
                    )
                finally:
                    # Defence in depth — the inline ``hb_stop.set()``
                    # above the finalise is the primary ordering
                    # guarantee. This finally catches any future exit
                    # path that forgets to stop the heartbeat before
                    # finalising.
                    try:
                        hb_stop.set()
                    except Exception:
                        pass
            except Exception as e:
                logger.exception(
                    f'resumable restore: resumed worker crashed for '
                    f'job_id="{job_id}"'
                )
                # Stop the heartbeat BEFORE the failure finalise —
                # explicit primary-ordering guarantee, matching the
                # pattern in ``_dispatch_restore_async._worker``'s
                # except block and the success path above. The inner
                # finally above also stops the heartbeat, but only
                # IF we reached the inner try (i.e. ``hb_stop`` is
                # bound). If ``_restore_job_start_heartbeat`` itself
                # raised, ``hb_stop`` is unbound — the ``locals()``
                # guard handles that cleanly without NameError.
                # Bugbot finding on PR #1649 (Low).
                if "hb_stop" in locals():
                    try:
                        hb_stop.set()
                    except Exception:
                        pass
                try:
                    self._restore_job_finalise(
                        worker_req, job_id,
                        status="failed",
                        response={
                            "response": f"Resumed worker exception: {str(e)}",
                            "exception": str(e),
                        },
                    )
                except Exception:
                    pass

        thread = threading.Thread(
            target=_resume_worker,
            name=f"trackme-restore-resume-{job_id[:8]}",
            daemon=True,
        )
        thread.start()
        logger.info(
            f'resumable restore: spawned resume worker for '
            f'job_id="{job_id}"'
        )
        return True

    def get_restore_job_status(self, request_info, **kwargs):
        """Poll the status of an async restore job.

        Required query parameter: job_id (UUID returned by the async
        POST /restore submission).

        Returns the current row from kv_trackme_backup_restore_jobs.
        When status is in (completed, failed, cancelled) the
        `response` field carries the same shape the synchronous
        POST /restore response would have — the frontend renders it
        identically regardless of which dispatch path was used.

        Auto-purges terminal rows older than 24h on every call so the
        collection doesn't grow unboundedly across many restore cycles.
        """
        if trackme_parse_describe_flag(request_info):
            return {
                "payload": {
                    "describe": (
                        "Polls the status of an async restore job "
                        "submitted via POST /restore with async=true. "
                        "Required query parameter: job_id (UUID). "
                        "Returns the kv_trackme_backup_restore_jobs row, "
                        "which includes status (queued | running | "
                        "completed | failed | cancelled), progress, "
                        "and (for terminal statuses) the same response "
                        "shape the synchronous POST /restore would have "
                        "returned. Auto-purges terminal rows older than "
                        "24h on every call. ALSO acts as the watchdog "
                        "for the resumable-restore feature: if the "
                        "worker hasn't heartbeated within the stale "
                        "threshold (default 5 min) it claims the resume "
                        "slot (CAS via worker_epoch) and spawns a fresh "
                        "daemon worker that picks up from the first "
                        "non-done task. Hardcoded ceiling of 5 resume "
                        "attempts before the job is finalised as "
                        "failed. The row's `tasks_parsed` field "
                        "exposes the per-task progress (id / label / "
                        "status / started_epoch / completed_epoch / "
                        "error)."
                    ),
                    "resource_desc": (
                        "Poll the status of an async restore job"
                    ),
                    "resource_spl_example": (
                        '| trackme mode=get url='
                        '"/services/trackme/v2/backup_and_restore/restore_job_status?job_id=<uuid>"'
                    ),
                    "options": [{
                        "job_id": "REQUIRED. The job UUID returned by POST /restore async=true.",
                    }],
                },
                "status": 200,
            }

        # Resolve job_id from query / body — same defensive accessors
        # as get_export_backup uses.
        job_id = None
        try:
            if hasattr(request_info, "query") and request_info.query:
                if isinstance(request_info.query, dict):
                    job_id = request_info.query.get("job_id")
                elif isinstance(request_info.query, list) and request_info.query:
                    first = request_info.query[0]
                    if isinstance(first, dict):
                        job_id = first.get("job_id")
            if not job_id and hasattr(request_info, "raw_args"):
                if isinstance(request_info.raw_args, dict):
                    job_id = request_info.raw_args.get("job_id")
                    if not job_id and "payload" in request_info.raw_args:
                        try:
                            payload = json.loads(str(request_info.raw_args["payload"]))
                            if isinstance(payload, dict):
                                job_id = payload.get("job_id")
                        except Exception:
                            pass
        except Exception:
            pass

        if not job_id:
            return {
                "payload": {"error": "job_id parameter is required"},
                "status": 400,
            }

        # Auto-purge stale terminal rows. Cheap to do on every poll
        # because the collection stays small (one row per active or
        # recent restore).
        self._restore_job_purge_stale(request_info)

        try:
            kv = self._restore_job_kv(request_info)
            row = kv.data.query_by_id(job_id)
        except Exception as e:
            # Splunk SDK's query_by_id raises HTTPError(404) for missing
            # records — see the AI Assistant pattern in trackme_libs_ai.py
            # (cancel_chat_job, around line 2347) which catches it
            # broadly. Detect that case via the exception message and
            # surface a clean 404 so frontends polling for a purged or
            # invalid job_id don't see a misleading 500. The if-not-row
            # branch below stays as a defence in depth in case a future
            # SDK version returns None instead of raising.
            err = str(e)
            if "404" in err or "HTTP 404" in err.upper() or "not found" in err.lower():
                return {
                    "payload": {
                        "error": f"Job not found (or already auto-purged): {job_id}",
                        "job_id": job_id,
                    },
                    "status": 404,
                }
            return {
                "payload": {
                    "error": f"Failed to read job row: {err}",
                    "job_id": job_id,
                },
                "status": 500,
            }

        if not row:
            return {
                "payload": {
                    "error": f"Job not found (or already auto-purged): {job_id}",
                    "job_id": job_id,
                },
                "status": 404,
            }

        # Resumable-restore: stale-detection + auto-resume. The polling
        # endpoint doubles as a watchdog: if the worker hasn't updated
        # ``last_heartbeat_epoch`` within ``STALE_THRESHOLD_SECONDS``,
        # claim the resume slot and spawn a fresh daemon worker. The
        # claim is CAS-style on ``worker_epoch`` so concurrent polls
        # from a single frontend (or multiple frontends) don't spawn
        # duplicate workers. ``MAX_RESUMES`` caps the retry count so
        # a job that fails the same way repeatedly is finalised as
        # failed rather than looping forever.
        #
        # The resumed worker re-enters ``_handle_restore_3_0_0`` with
        # the same body_params; the task-list checkpoints make it
        # pick up from where the previous worker died rather than
        # restarting from scratch. The status endpoint itself returns
        # the current row (which now shows ``resume_count`` bumped and
        # a "resuming (attempt N)" progress string), so the frontend
        # sees the recovery happening rather than the job appearing
        # frozen.
        resumed_this_poll = False
        try:
            if self._restore_job_should_resume(row):
                if self._restore_job_try_claim_resume(request_info, job_id):
                    spawned = self._restore_job_spawn_resume_worker(
                        request_info, job_id,
                    )
                    if spawned:
                        resumed_this_poll = True
                        # Re-read so the response reflects the post-
                        # claim row (resume_count bumped, progress
                        # string updated, heartbeat refreshed).
                        try:
                            row = kv.data.query_by_id(job_id) or row
                        except Exception:
                            pass
            else:
                # Circuit-breaker: finalise the job as failed ONLY when
                # BOTH conditions hold:
                #   1. resume_count >= MAX_RESUMES (we've already used
                #      up the recovery budget), AND
                #   2. the latest worker's heartbeat is stale (the
                #      last-resort worker is also dead).
                #
                # An earlier iteration only checked (1), which would
                # fire on a fresh-heartbeat healthy worker once the
                # resume_count cap had been hit. Picture: 5 resumes
                # have happened, the 5th resumed worker is alive and
                # actively making progress — the elif would still fire
                # and kill the healthy job. Bugbot finding on PR #1647
                # (Medium). Gating on the AND-of-both ensures the
                # circuit-breaker only fires when the system has both
                # exhausted retries AND failed again.
                try:
                    last_hb = int(row.get("last_heartbeat_epoch") or 0)
                except (TypeError, ValueError):
                    last_hb = 0
                try:
                    resume_count = int(row.get("resume_count") or 0)
                except (TypeError, ValueError):
                    resume_count = 0
                now = int(time.time())
                heartbeat_age = (now - last_hb) if last_hb else -1
                cb_resumes_exhausted = (
                    str(row.get("status") or "") == "running"
                    and resume_count >= self._RESTORE_JOB_MAX_RESUMES
                )
                cb_heartbeat_stale = (
                    last_hb == 0
                    or heartbeat_age >= self._RESTORE_JOB_STALE_THRESHOLD_SECONDS
                )
                if cb_resumes_exhausted and cb_heartbeat_stale:
                    logger.warning(
                        f'resumable restore: job_id="{job_id}" hit '
                        f'MAX_RESUMES ({self._RESTORE_JOB_MAX_RESUMES}) '
                        f'AND heartbeat is stale (age={heartbeat_age}s); '
                        f'finalising as failed'
                    )
                    self._restore_job_finalise(
                        request_info, job_id,
                        status="failed",
                        response={
                            "response": (
                                f"Restore worker died and could not be "
                                f"recovered after "
                                f"{self._RESTORE_JOB_MAX_RESUMES} resume "
                                f"attempts. Inspect the job row's tasks "
                                f"field for the last task to make progress."
                            ),
                            "max_resumes_exceeded": True,
                        },
                    )
                    try:
                        row = kv.data.query_by_id(job_id) or row
                    except Exception:
                        pass
        except Exception as e:
            # Resume logic is best-effort — a failure here must NOT
            # block the polling endpoint from returning the current
            # row. Log and continue.
            logger.warning(
                f'resumable restore: stale-detection failed for '
                f'job_id="{job_id}": {str(e)}'
            )

        # Parse the JSON-stringified response field so the frontend
        # sees structured data, not a string-of-JSON.
        try:
            row["response_parsed"] = (
                json.loads(row["response"])
                if row.get("response") else None
            )
        except Exception:
            row["response_parsed"] = None
        try:
            row["request_args_parsed"] = (
                json.loads(row["request_args"])
                if row.get("request_args") else None
            )
        except Exception:
            row["request_args_parsed"] = None
        try:
            row["tasks_parsed"] = (
                json.loads(row["tasks"])
                if row.get("tasks") else []
            )
        except Exception:
            row["tasks_parsed"] = []
        # Surface whether we just triggered a resume on this poll so
        # the frontend can show a "Recovering…" hint if it wants. The
        # row's own progress string carries the same signal but this
        # is the explicit boolean.
        if resumed_this_poll:
            row["resumed_this_poll"] = "1"

        return {"payload": row, "status": 200}

    def delete_restore_job(self, request_info, **kwargs):
        """Best-effort cancellation of a running restore job.

        Sets cancel_requested=1 on the row. The worker checks this
        flag between archives in run-mode restore (and right before
        the first archive in single-archive mode) and aborts
        gracefully — the in-flight archive completes, remaining
        archives are not touched, and the job's terminal status
        becomes "cancelled". Already-completed jobs cannot be
        cancelled (returns 409); ones with status "queued" cancel
        before any archive is touched.

        Required body parameter: job_id (UUID).
        """
        if trackme_parse_describe_flag(request_info):
            return {
                "payload": {
                    "describe": (
                        "Best-effort cancellation of a running restore "
                        "job. Sets cancel_requested=1; the worker "
                        "checks between archives and aborts gracefully. "
                        "Already-completed jobs return 409. The "
                        "in-flight archive is allowed to finish so the "
                        "KV state remains consistent — restoring a half "
                        "archive would leave the tenant in an "
                        "ambiguous state."
                    ),
                    "resource_desc": (
                        "Cancel an async restore job (cooperative)"
                    ),
                    "resource_spl_example": (
                        '| trackme mode=delete url='
                        '"/services/trackme/v2/backup_and_restore/restore_job" '
                        "body=\"{'job_id':'<uuid>'}\""
                    ),
                    "options": [{
                        "job_id": "REQUIRED. The job UUID to cancel.",
                    }],
                },
                "status": 200,
            }

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None
        job_id = (resp_dict or {}).get("job_id")
        if not job_id:
            return {
                "payload": {"error": "job_id is required in the body"},
                "status": 400,
            }

        try:
            kv = self._restore_job_kv(request_info)
            row = kv.data.query_by_id(job_id)
        except Exception as e:
            # Splunk SDK's query_by_id raises HTTPError(404) for missing
            # records. Same handling as get_restore_job_status — see
            # that method's docstring for the full rationale. Defence
            # in depth: the if-not-row branch below stays for any
            # future SDK version that returns None instead of raising.
            err = str(e)
            if "404" in err or "HTTP 404" in err.upper() or "not found" in err.lower():
                return {
                    "payload": {
                        "error": f"Job not found: {job_id}",
                        "job_id": job_id,
                    },
                    "status": 404,
                }
            return {
                "payload": {
                    "error": f"Failed to read job row: {err}",
                    "job_id": job_id,
                },
                "status": 500,
            }

        if not row:
            return {
                "payload": {
                    "error": f"Job not found: {job_id}",
                    "job_id": job_id,
                },
                "status": 404,
            }

        status = str(row.get("status", ""))
        if status in ("completed", "failed", "cancelled"):
            return {
                "payload": {
                    "response": (
                        f"Job is already in terminal status '{status}'. "
                        "Cancellation is a no-op."
                    ),
                    "job_id": job_id,
                    "status": status,
                },
                "status": 409,
            }

        try:
            # TOCTOU mitigation — symmetric to the worker-side
            # _restore_job_update_status / _restore_job_finalise
            # protections. Splunk KV updates are full-document replace,
            # so without this re-read the DELETE handler would write
            # stale fields (status, finished_epoch, response, progress)
            # back over a worker that finalised between the read at
            # line ~7674 and the write here. The worker has already
            # exited at that point and auto-purge skips non-terminal
            # rows, so the row would be silently orphaned. Re-read
            # immediately before write, recheck terminal status, and
            # carry forward any worker progress that landed mid-flight.
            try:
                fresh = kv.data.query_by_id(job_id)
            except Exception:
                fresh = None
            # Compute the most-current observed status. The downstream
            # log line + response reference this so the operator sees
            # the actual transition (e.g. "queued" → "running" between
            # the two reads), not the stale value from the initial read.
            effective_status = status
            if fresh:
                fresh_status = str(fresh.get("status", ""))
                effective_status = fresh_status or status
                if fresh_status in ("completed", "failed", "cancelled"):
                    # The worker raced ahead and finalised the row
                    # between our initial read and now. Don't overwrite
                    # the terminal record — return the same 409 the
                    # earlier branch would have produced.
                    return {
                        "payload": {
                            "response": (
                                f"Job is already in terminal status "
                                f"'{fresh_status}'. Cancellation is a no-op."
                            ),
                            "job_id": job_id,
                            "status": fresh_status,
                        },
                        "status": 409,
                    }
                # Use the fresh row as the base — preserves any
                # worker-written progress / mtime / partial response
                # rather than reverting to the stale snapshot.
                new_record = dict(fresh)
            else:
                new_record = dict(row)
            new_record["cancel_requested"] = "1"
            new_record["mtime"] = int(round(time.time()))
            new_record["progress"] = "cancellation_requested"
            new_record.pop("_key", None)
            kv.data.update(job_id, json.dumps(new_record))
        except Exception as e:
            return {
                "payload": {
                    "error": f"Failed to set cancel flag: {str(e)}",
                    "job_id": job_id,
                },
                "status": 500,
            }

        logger.info(
            f'async restore: cancellation requested for job_id="{job_id}" '
            f'(current status: {effective_status})'
        )
        return {
            "payload": {
                "response": (
                    "Cancellation requested. The worker will abort "
                    "between archives — the in-flight archive (if any) "
                    "completes before the run halts."
                ),
                "job_id": job_id,
                "previous_status": effective_status,
            },
            "status": 200,
        }

    def post_import_backup(self, request_info, **kwargs):
        """
        Handles the import_backup functionality.
        """
        describe = False

        # Retrieve the payload
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            try:
                describe = resp_dict.get("describe", False)
                if str(describe).lower() == "true":
                    describe = True
            except Exception:
                describe = False

        if describe:
            response = {
                "describe": "This endpoint imports a backup from a Base64-encoded compressed archive file (.tgz or .tar.zst).",
                "resource_desc": "Import a backup archive",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/backup_and_restore/import_backup\" body=\"{'archive_base64': '<base64_string>'}\" (supports both .tgz and .tar.zst)",
                "options": [
                    {
                        "archive_base64": "(string) REQUIRED: Base64 string of the backup archive."
                    },
                ],
            }
            return {"payload": response, "status": 200}

        # Process the import
        try:
            archive_base64 = resp_dict.get("archive_base64")
            if not archive_base64:
                return {
                    "payload": {"error": "archive_base64 is required"},
                    "status": 400,
                }

            # Decode base64 and write to a temporary file
            decoded_data = base64.b64decode(archive_base64)
            temp_dir = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
            os.makedirs(temp_dir, exist_ok=True)

            # Determine file extension based on content (try to detect format)
            # For now, we'll use a generic name and let the extract function handle it
            temp_file_path = os.path.join(temp_dir, "temp_import.archive")

            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(decoded_data)

            # Try to determine archive type and validate
            archive_type = None
            if temp_file_path.endswith(".tar.zst") or temp_file_path.endswith(".zst"):
                archive_type = "zstd"
            elif temp_file_path.endswith(".tgz") or temp_file_path.endswith(".tar.gz"):
                archive_type = "gzip"
            else:
                # Try to detect by content
                try:
                    # Try zstd first
                    if is_zstd_available():
                        return_code = zstd_test_archive(temp_file_path)
                        result = type("_", (), {"returncode": return_code})()
                        if result.returncode == 0:
                            archive_type = "zstd"
                        else:
                            # Try gzip
                            if tarfile.is_tarfile(temp_file_path):
                                archive_type = "gzip"
                except:
                    # Fall back to gzip check
                    if tarfile.is_tarfile(temp_file_path):
                        archive_type = "gzip"

            if not archive_type:
                os.remove(temp_file_path)
                return {
                    "payload": {"error": "Invalid or unsupported archive format"},
                    "status": 400,
                }

            # Validate the archive content
            if archive_type == "zstd":
                # For zstd, we'll validate during extraction
                # We need to extract to a temporary location to check metadata
                temp_extract_dir = os.path.join(temp_dir, "temp_extract")
                os.makedirs(temp_extract_dir, exist_ok=True)

                # Rename the temp file to have the proper extension for extract_archive
                temp_file_with_ext = os.path.join(temp_dir, "temp_import.tar.zst")
                os.rename(temp_file_path, temp_file_with_ext)

                if not extract_archive(temp_file_with_ext, temp_extract_dir):
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                    os.remove(temp_file_with_ext)
                    return {
                        "payload": {"error": "Failed to extract zstd archive"},
                        "status": 400,
                    }

                # Check metadata files
                members = os.listdir(temp_extract_dir)
                full_metadata_found = False
                light_metadata_found = False
                archive_name = None

                for member in members:
                    if member.startswith("trackme-backup-") and member.endswith(
                        "full.meta"
                    ):
                        full_metadata_found = True
                        # extract the archive_name from the full metadata file
                        archive_name = member.split(".full.meta")[0]
                        break

                for member in members:
                    if member.startswith("trackme-backup-") and member.endswith(
                        "light.meta"
                    ):
                        light_metadata_found = True
                        break

                if not full_metadata_found or not light_metadata_found:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                    os.remove(temp_file_with_ext)
                    return {
                        "payload": {
                            "error": f"Missing metadata files, this archive is corrupted, or not a TrackMe backup, or not created with TrackMe 2.1.5 and later (only archive_schema_version 2.0.0 and later can be imported), see available archive content: {members}"
                        },
                        "status": 400,
                    }

                # Clean up temp extraction
                shutil.rmtree(temp_extract_dir, ignore_errors=True)

            elif archive_type == "gzip":
                # Rename the temp file to have the proper extension for tarfile
                temp_file_with_ext = os.path.join(temp_dir, "temp_import.tgz")
                os.rename(temp_file_path, temp_file_with_ext)

                with tarfile.open(temp_file_with_ext, "r:gz") as tar:
                    members = tar.getnames()
                    full_metadata_found = False
                    light_metadata_found = False
                    archive_name = None

                    # check for metadata files
                    for member in members:
                        if member.startswith("trackme-backup-") and member.endswith(
                            "full.meta"
                        ):
                            full_metadata_found = True
                            # extract the archive_name from the full metadata file
                            archive_name = member.split(".full.meta")[0]
                            break

                    for member in members:
                        if member.startswith("trackme-backup-") and member.endswith(
                            "light.meta"
                        ):
                            light_metadata_found = True
                            break

                    if not full_metadata_found or not light_metadata_found:
                        os.remove(temp_file_with_ext)
                        return {
                            "payload": {
                                "error": f"Missing metadata files, this archive is corrupted, or not a TrackMe backup, or not created with TrackMe 2.1.5 and later (only archive_schema_version 2.0.0 and later can be imported), see available archive content: {members}"
                            },
                            "status": 400,
                        }

            # Extract the archive in backupdir
            try:
                backupdir = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
                os.makedirs(backupdir, exist_ok=True)

                # Use the renamed file with proper extension
                final_temp_file = (
                    temp_file_with_ext
                    if "temp_file_with_ext" in locals()
                    else temp_file_path
                )

                if not extract_archive(final_temp_file, backupdir):
                    return {
                        "payload": {"error": f"Failed to extract the archive"},
                        "status": 500,
                    }

                os.remove(final_temp_file)

                # Direct KV registration for 3.0.0 archives (Issue #1555).
                #
                # Historically post_import_backup ends by issuing a GET
                # to /backup, relying on that endpoint's auto-discovery
                # sweep to create the KV row. That sweep was V2-only and
                # silently dropped the 3.0.0 fields, so every imported
                # archive landed in the legacy bucket. The auto-discovery
                # path has now been fixed (see lines ~817+), but the
                # import path can do better: read the on-disk
                # ``.full.meta`` sidecar that just landed in backupdir
                # and register the KV row directly with the 3.0.0 fields
                # baked in. The subsequent /backup call then finds the
                # existing row and skips discovery.
                #
                # Best-effort: any failure here falls through to the
                # discovery-based registration (which now also handles
                # 3.0.0 correctly), so the import still succeeds.
                try:
                    if archive_name:
                        imported_archive_path = os.path.join(backupdir, archive_name)
                        full_meta_path = f"{imported_archive_path}.full.meta"
                        light_meta_path = f"{imported_archive_path}.light.meta"
                        if (
                            os.path.isfile(imported_archive_path)
                            and os.path.isfile(full_meta_path)
                            and os.path.isfile(light_meta_path)
                        ):
                            try:
                                with open(full_meta_path, "r") as f:
                                    imported_full_meta = json.load(f)
                            except Exception:
                                imported_full_meta = {}
                            try:
                                with open(light_meta_path, "r") as f:
                                    imported_light_meta = json.load(f)
                            except Exception:
                                imported_light_meta = {}

                            # Honour the existing row if any (e.g. the
                            # operator re-imported the same archive).
                            # Discovery's same-path / same-server query
                            # would short-circuit anyway, but we check
                            # here to avoid a duplicate-insert exception.
                            # ``server_name`` is resolved through the same
                            # helper as the other write paths so all three
                            # converge on a single identifier per peer.
                            local_server_name = _resolve_canonical_server_name()
                            import_service = client.connect(
                                owner="nobody",
                                app="trackme",
                                port=request_info.server_rest_port,
                                token=request_info.session_key,
                                timeout=600,
                            )
                            import_kv = import_service.kvstore[
                                "kv_trackme_backup_archives_info"
                            ]
                            existing_query = {
                                "$and": [
                                    {
                                        "backup_archive": imported_archive_path,
                                        "server_name": local_server_name,
                                    }
                                ]
                            }
                            try:
                                existing_rows = import_kv.data.query(
                                    query=json.dumps(existing_query)
                                )
                            except Exception:
                                existing_rows = []

                            if not existing_rows:
                                v3_fields = _derive_v3_fields_for_discovery(
                                    archive_name, imported_full_meta,
                                )
                                # File size from the actual archive on
                                # disk — more reliable than trusting a
                                # potentially out-of-date sidecar value.
                                try:
                                    imported_size = os.path.getsize(
                                        imported_archive_path
                                    )
                                except Exception:
                                    imported_size = imported_full_meta.get("size")
                                # ``imported_mtime`` MUST be an int (or
                                # None) so the subsequent
                                # ``time.localtime(...)`` fallback below
                                # doesn't raise TypeError. ``post_backup``
                                # stores ``mtime`` as a string in the
                                # sidecar via ``str(backup_file_mtime)``,
                                # so the sidecar fallback returns a string
                                # — must coerce. Bugbot finding (PR #1556).
                                imported_mtime = None
                                try:
                                    imported_mtime = int(round(
                                        os.path.getmtime(imported_archive_path)
                                    ))
                                except Exception:
                                    sidecar_mtime = imported_full_meta.get("mtime")
                                    if sidecar_mtime is not None:
                                        try:
                                            imported_mtime = int(
                                                float(sidecar_mtime)
                                            )
                                        except (TypeError, ValueError):
                                            imported_mtime = None

                                import_record = {
                                    "mtime": str(imported_mtime) if imported_mtime is not None else "",
                                    "htime": imported_full_meta.get("htime") or (
                                        time.strftime(
                                            "%c", time.localtime(imported_mtime)
                                        ) if imported_mtime is not None else ""
                                    ),
                                    "server_name": local_server_name,
                                    "status": json.dumps(
                                        imported_light_meta, indent=4
                                    ),
                                    "change_type": (
                                        "backup archive imported via "
                                        "post_import_backup"
                                    ),
                                    "backup_archive": imported_archive_path,
                                    "size": imported_size,
                                    "archive_details": json.dumps(
                                        imported_full_meta.get("archive_details"),
                                        indent=4,
                                    ),
                                }
                                import_record.update(v3_fields)
                                try:
                                    import_kv.data.insert(json.dumps(import_record))
                                    logger.info(
                                        f'post_import_backup: registered KV row '
                                        f'for archive="{archive_name}", '
                                        f'v3_fields={list(v3_fields.keys())!r}'
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f'post_import_backup: direct KV '
                                        f'registration failed for '
                                        f'archive="{archive_name}" — falling '
                                        f'through to discovery path; '
                                        f'exception="{str(e)}"'
                                    )
                except Exception as e:
                    # Defensive — any failure in direct registration
                    # falls through to the discovery-driven path which
                    # now also handles 3.0.0 correctly.
                    logger.warning(
                        f'post_import_backup: direct KV registration '
                        f'block raised, falling through to discovery '
                        f'path; exception="{str(e)}"'
                    )

            except Exception as e:
                final_temp_file = (
                    temp_file_with_ext
                    if "temp_file_with_ext" in locals()
                    else temp_file_path
                )
                os.remove(final_temp_file)
                return {
                    "payload": {
                        "error": f"Failed to extract the archive, error={str(e)}"
                    },
                    "status": 500,
                }

            # Call get_restore

            # url
            url = f"{request_info.server_rest_uri}/services/trackme/v2/backup_and_restore/backup"

            # header
            header = {
                "Authorization": "Splunk %s" % request_info.session_key,
                "Content-Type": "application/json",
            }

            response = requests.get(
                url,
                headers=header,
                verify=False,
                timeout=600,
            )

            if response.status_code != 200:
                return {
                    "payload": {
                        "error": f"Failed to call get_restore, http.status={response.status_code}, http.response={response.text}"
                    },
                    "status": 500,
                }

            else:
                return {
                    "payload": {"success": "Backup imported successfully"},
                    "status": 200,
                }

        except Exception as e:
            logger.error(f"Error in post_import_backup: {str(e)}")
            return {"payload": {"error": str(e)}, "status": 500}

    def post_export_backup(self, request_info, **kwargs):
        """
        Handles the export_backup functionality.
        """
        describe = False

        # Retrieve the payload
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            try:
                describe = resp_dict.get("describe", False)
                if str(describe).lower() == "true":
                    describe = True
            except Exception:
                describe = False

        if describe:
            response = {
                "describe": "This endpoint exports a backup to a Base64-encoded compressed archive file (.tgz or .tar.zst).",
                "resource_desc": "Export a backup archive",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/backup_and_restore/export_backup\" body=\"{'archive_name': 'trackme-backup-20210205-142635.tgz'}\" (supports both .tgz and .tar.zst)",
                "options": [
                    {
                        "archive_name": "(string) REQUIRED: Name of the backup archive to export.",
                        "force_local": "(true / false) OPTIONAL: if true, the endpoint will assume the backup file is hosted on the local server and will not verify if the backup file is hosted on a different server",
                        "binary_mode": "(true / false) OPTIONAL: if true, returns a download_token instead of archive_base64 for memory-efficient downloads (default: false)",
                    },
                ],
            }
            return {"payload": response, "status": 200}

        # get archive_name
        archive_name = resp_dict.get("archive_name")
        if not archive_name:
            return {"payload": {"error": "archive_name is required"}, "status": 400}

        # Get the force_local parameter
        try:
            force_local = resp_dict.get("force_local", False)
            if force_local:
                # accept booleans or strings: true/True/1
                if isinstance(force_local, bool):
                    force_local = force_local
                elif isinstance(force_local, str):
                    if force_local in ("true", "True", "1"):
                        force_local = True
                    elif force_local in ("false", "False", "0"):
                        force_local = False
                    else:
                        return {
                            "payload": {"error": "force_local must be true or false"},
                            "status": 400,
                        }
                else:
                    force_local = False

        except Exception as e:
            # default to False
            force_local = False

        # Get the binary_mode parameter
        try:
            binary_mode = resp_dict.get("binary_mode", False)
            # Handle different types: bool, str, int, or default to False
            if isinstance(binary_mode, bool):
                binary_mode = binary_mode
            elif isinstance(binary_mode, str):
                if binary_mode in ("true", "True", "1"):
                    binary_mode = True
                elif binary_mode in ("false", "False", "0"):
                    binary_mode = False
                else:
                    return {
                        "payload": {"error": "binary_mode must be true or false"},
                        "status": 400,
                    }
            elif isinstance(binary_mode, int):
                # Handle integer values: 1 = True, 0 = False, anything else is invalid
                if binary_mode == 1:
                    binary_mode = True
                elif binary_mode == 0:
                    binary_mode = False
                else:
                    return {
                        "payload": {"error": "binary_mode must be true/false or 1/0"},
                        "status": 400,
                    }
            else:
                # For any other type (including None), default to False for backward compatibility
                binary_mode = False
        except Exception as e:
            # default to False for backward compatibility
            binary_mode = False

        # Get current server name (short hostname as default)
        current_server_name = socket.gethostname()

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # Query the backup archives info collection
        collection_name = "kv_trackme_backup_archives_info"
        collection = service.kvstore[collection_name]

        # Query the KVstore collection in all cases
        query_string = {"backup_archive": {"$regex": f".*{archive_name}$"}}

        try:
            kvrecords = collection.data.query(query=json.dumps(query_string))
            kvrecord = kvrecords[0]
        except Exception as e:
            kvrecords = []
            kvrecord = None

        # handle_local boolean
        handle_local = True

        if not kvrecord or force_local:
            handle_local = True

        else:

            # log kvrecord extracts
            kvrecord_extracts = {
                "_key": kvrecord.get("_key"),
                "htime": kvrecord.get("htime"),
                "server_name": kvrecord.get("server_name"),
                "backup_archive": kvrecord.get("backup_archive"),
                "change_type": kvrecord.get("change_type"),
                "status": kvrecord.get("status"),
                "comment": kvrecord.get("comment"),
            }
            logger.info(
                f"found backup info collection record: {json.dumps(kvrecord_extracts, indent=2)}"
            )

            # Get the server_name from the first matching record
            backup_server_name = kvrecord.get("server_name")

            # Dual-form normalisation — mirrors the pattern delete_backup
            # uses at lines ~2692-2697. Without this, the post-PR-#1568
            # FQDN ``server_name`` written by ``post_backup`` would never
            # match the short hostname returned by ``socket.gethostname()``
            # on deployments where ``socket.getfqdn() != socket.gethostname()``
            # (Splunk Cloud, most enterprise SHCs), so every locally-owned
            # archive would trigger a single-hop HTTP self-delegation.
            # The receiver short-circuits cleanly via the ``force_local=True``
            # value passed in the delegation payload below, but the round-
            # trip is needless and spammy in the log.
            local_short = current_server_name.lower()
            local_fqdn = socket.getfqdn().lower()
            backup_lower = (backup_server_name or "").lower()
            backup_short = backup_lower.split(".", 1)[0]

            if backup_lower in (local_short, local_fqdn) or backup_short == local_short:
                handle_local = True
            else:
                logger.info(
                    f"Backup archive is on different server ({backup_server_name}), delegating export to target server"
                )
                handle_local = False

        # process
        if handle_local:

            #
            # local host handling
            #

            logger.info(
                f"Backup archive is on the same server ({current_server_name}), proceeding with local export"
            )

            # Local export (original logic)
            # Locate the archive
            backup_dir = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
            archive_path = os.path.join(backup_dir, archive_name)

            if not os.path.exists(archive_path):
                return {
                    "payload": {
                        "error": f"Archive not found, file {archive_path} does not exists."
                    },
                    "status": 404,
                }

            try:
                # Create a timestamped temporary directory for the export
                timestamp = time.strftime("%d%m%Y_%H%M%S", time.localtime())
                temp_dir = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
                temp_export_dir = os.path.join(temp_dir, f"backup_temp_{timestamp}")
                
                # Remove existing temp directory if it exists
                if os.path.exists(temp_export_dir):
                    logger.info(f"Removing existing temporary directory: {temp_export_dir}")
                    shutil.rmtree(temp_export_dir, ignore_errors=True)
                
                # Create the new temporary directory
                os.makedirs(temp_export_dir, exist_ok=True)
                logger.info(f"Created temporary export directory: {temp_export_dir}")

                # Copy the archive and metadata files to temp directory
                shutil.copy2(archive_path, os.path.join(temp_export_dir, archive_name))
                shutil.copy2(
                    f"{archive_path}.light.meta",
                    os.path.join(temp_export_dir, f"{archive_name}.light.meta"),
                )
                shutil.copy2(
                    f"{archive_path}.full.meta",
                    os.path.join(temp_export_dir, f"{archive_name}.full.meta"),
                )

                # Create a tgz archive containing the zst archive and metadata files
                archive_name_base = os.path.splitext(archive_name)[
                    0
                ]  # Remove extension
                if archive_name.endswith(".tar.zst"):
                    archive_name_base = archive_name_base[:-4]  # Remove .tar part

                # Create the tgz archive
                tgz_path = os.path.join(temp_dir, f"{archive_name_base}.tgz")
                with tarfile.open(tgz_path, mode="w:gz") as tgz_archive:
                    tgz_archive.add(temp_export_dir, arcname="")

                # get the size of the tgz archive (MB)
                tgz_size = round(os.path.getsize(tgz_path) / 1024 / 1024, 2)

                # log success
                logger.info(
                    f"Successfully exported backup archive {archive_name} to {tgz_path}, size={tgz_size} MB, binary_mode={binary_mode}"
                )

                # Handle binary_mode: token-based download vs direct base64
                if binary_mode:
                    # Binary mode: Create token and store file for GET endpoint
                    download_token = str(uuid.uuid4())
                    
                    # Ensure downloads directory exists
                    downloads_dir = os.path.join(backup_dir, "downloads")
                    os.makedirs(downloads_dir, exist_ok=True)
                    
                    # Create token-based filename: token_timestamp_original_filename
                    timestamp = int(time.time())
                    token_filename = f"{download_token}_{timestamp}_{archive_name_base}.tgz"
                    token_file_path = os.path.join(downloads_dir, token_filename)
                    
                    # Move tgz file to downloads directory with token-based name
                    shutil.move(tgz_path, token_file_path)
                    
                    logger.info(
                        f"Export prepared: {token_file_path}, token={download_token}, size={tgz_size} MB"
                    )
                    
                    # Clean up temporary directory
                    shutil.rmtree(temp_export_dir, ignore_errors=True)
                    logger.info(f"Cleaned up temporary export directory: {temp_export_dir}")
                    
                    return {
                        "payload": {
                            "download_token": download_token,
                            "filename": f"{archive_name_base}.tgz",
                            "size": f"{tgz_size} MB",
                        },
                        "status": 200,
                    }
                else:
                    # Direct mode: Encode the tgz archive in Base64
                    with open(tgz_path, "rb") as tgz_file:
                        base64_data = base64.b64encode(tgz_file.read()).decode("utf-8")

                    # Clean up temporary files
                    os.remove(tgz_path)
                    shutil.rmtree(temp_export_dir, ignore_errors=True)
                    logger.info(f"Cleaned up temporary export directory: {temp_export_dir}")

                    return {
                        "payload": {"archive_base64": base64_data},
                        "status": 200,
                    }

            except Exception as e:
                logger.error(f"Error in local export: {str(e)}")
                return {
                    "payload": {"error": f"Failed to export backup: {str(e)}"},
                    "status": 500,
                }

        else:

            #
            # remote host handling
            #

            # Query the KVstore collection to get the server_name for this backup archive
            logger.info(
                f"Backup archive is on different server ({backup_server_name}), delegating export to target server"
            )

            # Determine the best target server name for communication by testing connectivity
            target_server_name = backup_server_name

            # Test connectivity with short hostname first, then FQDN if needed
            logger.info(
                f"Testing connectivity with short hostname: {backup_server_name}"
            )
            if not test_splunkd_connectivity(
                backup_server_name,
                request_info.server_rest_port,
                request_info.session_key,
            ):
                # FQDN-suffix fallback. Skip the suffix-append entirely when
                # ``backup_server_name`` is already an FQDN (contains a dot)
                # — post-PR-#1568 KV rows store FQDN-form ``server_name``,
                # so the naive ``f"{X}.{suffix}"`` would produce a
                # double-suffixed target like ``host.domain.com.domain.com``
                # that will never resolve. Mirrors the canonical fix at
                # ``_v3_delegate_restore_to_peer`` (PR #1627, bugbot ID
                # cf36f216).
                backup_server_fqdn = None
                if "." not in backup_server_name:
                    local_fqdn = socket.getfqdn()
                    fqdn_suffix = (
                        local_fqdn.split(".", 1)[1]
                        if "." in local_fqdn
                        else "local"
                    )
                    backup_server_fqdn = f"{backup_server_name}.{fqdn_suffix}"
                if backup_server_fqdn:
                    logger.info(
                        f"Short hostname failed, trying FQDN: {backup_server_fqdn}"
                    )
                if backup_server_fqdn and test_splunkd_connectivity(
                    backup_server_fqdn,
                    request_info.server_rest_port,
                    request_info.session_key,
                ):
                    target_server_name = backup_server_fqdn
                    logger.info(
                        f"FQDN connectivity successful, using: {target_server_name}"
                    )
                else:
                    # Branch-aware warning reflects whether the FQDN-suffix
                    # fallback ran or was skipped.
                    if backup_server_fqdn:
                        warn_detail = (
                            f"short ({backup_server_name!r}) and "
                            f"FQDN-suffix fallback "
                            f"({backup_server_fqdn!r}) both failed"
                        )
                    else:
                        warn_detail = (
                            f"FQDN form ({backup_server_name!r}) failed; "
                            f"no short->FQDN fallback applicable"
                        )
                    logger.warning(
                        f"Connectivity failed for {backup_server_name} "
                        f"({warn_detail})"
                    )
            else:
                logger.info(
                    f"Short hostname connectivity successful, using: {target_server_name}"
                )

            # support only https
            target_server_uri = (
                f"https://{target_server_name}:{request_info.server_rest_port}"
            )

            # Make REST call to target server
            headers = {
                "Authorization": f"Splunk {request_info.session_key}",
                "Content-Type": "application/json",
            }

            # Prepare the request payload. Hard-code ``force_local=True``
            # so the receiving peer short-circuits its own ownership
            # comparison and handles the export locally. Mirrors the
            # established pattern from ``delete_backup`` (line ~2806)
            # and ``_v3_delegate_restore_to_peer`` (line ~4145). Without
            # this, the FQDN-vs-short-hostname mismatch at line ~11132
            # would re-fail on the receiver (KV stores FQDN post-PR-#1568,
            # ``socket.gethostname()`` returns short on FQDN deployments),
            # causing infinite self-delegation until the 600 s HTTP
            # timeout fires.
            request_payload = {
                "archive_name": archive_name,
                "force_local": True,
                "binary_mode": binary_mode,  # Forward binary_mode to remote server
            }

            target_url = f"{target_server_uri}/services/trackme/v2/backup_and_restore/export_backup"

            logger.info(f"Making REST call to target server: {target_url}, binary_mode={binary_mode}")

            try:
                response = requests.post(
                    target_url,
                    headers=headers,
                    data=json.dumps(request_payload),
                    verify=False,
                    timeout=600,
                )

                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(
                        f"Successfully exported backup from target server {backup_server_name} (binary mode: {binary_mode})"
                    )
                    
                    # Handle binary_mode response
                    if binary_mode and "download_token" in response_data:
                        # Remote server returned a token (Option B: proxy approach)
                        # Fetch the file from remote server using the token
                        remote_token = response_data.get("download_token")
                        # Extract base filename from archive_name
                        archive_name_base = os.path.splitext(archive_name)[0]
                        if archive_name.endswith(".tar.zst"):
                            archive_name_base = archive_name_base[:-4]  # Remove .tar part
                        remote_filename = response_data.get("filename", f"{archive_name_base}.tgz")
                        
                        # Make GET request to remote server to fetch the base64 data
                        get_url = f"{target_url}?download_token={remote_token}"
                        logger.info(f"Fetching file from remote server using token: {get_url}")
                        
                        get_response = requests.get(
                            get_url,
                            headers=headers,
                            verify=False,
                            timeout=600,
                        )
                        
                        if get_response.status_code == 200:
                            get_response_data = get_response.json()
                            remote_base64 = get_response_data.get("archive_base64")
                            
                            if not remote_base64:
                                logger.error(
                                    f"Failed to get archive_base64 from remote server {backup_server_name}, response keys: {list(get_response_data.keys()) if isinstance(get_response_data, dict) else 'not a dict'}"
                                )
                                return {
                                    "payload": {
                                        "error": f"Failed to export from target server {backup_server_name}: No archive_base64 in download response"
                                    },
                                    "status": 500,
                                }
                            
                            # Create local token and store the base64 data as a file
                            # This allows frontend to always use local GET endpoint
                            download_token = str(uuid.uuid4())
                            backup_dir = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")
                            downloads_dir = os.path.join(backup_dir, "downloads")
                            os.makedirs(downloads_dir, exist_ok=True)
                            
                            # Decode base64 and save to file
                            try:
                                file_data = base64.b64decode(remote_base64)
                                timestamp = int(time.time())
                                token_filename = f"{download_token}_{timestamp}_{os.path.splitext(remote_filename)[0]}.tgz"
                                token_file_path = os.path.join(downloads_dir, token_filename)
                                
                                with open(token_file_path, "wb") as f:
                                    f.write(file_data)
                                
                                file_size = round(len(file_data) / 1024 / 1024, 2)
                                logger.info(
                                    f"Created local token file from remote server: {token_file_path}, token={download_token}, size={file_size} MB"
                                )
                                
                                return {
                                    "payload": {
                                        "download_token": download_token,
                                        "filename": remote_filename,
                                        "size": f"{file_size} MB",
                                    },
                                    "status": 200,
                                }
                            except Exception as e:
                                logger.error(f"Error creating local token file from remote data: {str(e)}")
                                return {
                                    "payload": {
                                        "error": f"Failed to process remote archive data: {str(e)}"
                                    },
                                    "status": 500,
                                }
                        else:
                            logger.error(
                                f"Failed to fetch file from remote server using token: {get_response.status_code} - {get_response.text}"
                            )
                            return {
                                "payload": {
                                    "error": f"Failed to fetch file from target server {backup_server_name} using token: {get_response.text}"
                                },
                                "status": get_response.status_code,
                            }
                    else:
                        # Direct base64 response (binary_mode=False or remote server doesn't support binary_mode)
                        base64_data = response_data.get("archive_base64")
                        if not base64_data:
                            logger.error(
                                f"Failed to get archive_base64 from remote server {backup_server_name}, response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'not a dict'}"
                            )
                            return {
                                "payload": {
                                    "error": f"Failed to export from target server {backup_server_name}: No archive_base64 in response"
                                },
                                "status": 500,
                            }
                        return {
                            "payload": {"archive_base64": base64_data},
                            "status": 200,
                        }

                else:
                    logger.error(
                        f"Target server {backup_server_name} returned error: {response.status_code} - {response.text}, url={target_url}, request_payload={json.dumps(request_payload)}"
                    )
                    return {
                        "payload": {
                            "error": f"Failed to export from target server {backup_server_name}: {response.text}, url={target_url}, request_payload={json.dumps(request_payload)}"
                        },
                        "status": response.status_code,
                    }

            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Connection error to target server {backup_server_name}: {str(e)}"
                )
                return {
                    "payload": {
                        "error": f"Failed to connect to target server {backup_server_name}. Please ensure the server is reachable and TrackMe is installed."
                    },
                    "status": 500,
                }
            except Exception as e:
                logger.error(
                    f"Error making REST call to target server {backup_server_name}: {str(e)}, url={target_url}, request_payload={json.dumps(request_payload)}"
                )
                return {
                    "payload": {
                        "error": f"Failed to export from target server {backup_server_name}: {str(e)}, url={target_url}, request_payload={json.dumps(request_payload)}"
                    },
                    "status": 500,
                }
