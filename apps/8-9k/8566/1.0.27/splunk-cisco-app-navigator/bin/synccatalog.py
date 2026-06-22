# coding=utf-8
"""
synccatalog.py — Custom search command for SCAN

Compares the local products.conf version stamp against the S3 copy.
If S3 is newer, downloads and replaces products.conf, backs up the
original, and reloads the configuration.

Version stamp format: YYYY_MM_DD_HHMM on line 1 of products.conf
    # version = 2026_03_11_1700
    # min_app_version = 1.0.13   (optional; if present, sync only when running app >= this)

Usage:
    | synccatalog dryrun=false
    | synccatalog dryrun=true
"""

import logging
import os
import os.path
import re
import shutil
import sys
import time
from datetime import datetime
from typing import Generator

import requests
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    validators,
    dispatch,
)

APP_NAME = "splunk-cisco-app-navigator"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]
S3_BASE_URL = "https://is4s.s3.amazonaws.com/"
S3_FILE_PATH = "scan/products.conf"
DESTINATION_DIR = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "default")
DESTINATION_FILE_NAME = "products.conf"

BACKUP_DIR = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "backup")
MAX_BACKUPS = 5

LOG_FILE_NAME = "synccatalog.log"
LOG_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", LOG_FILE_NAME)
LOGGER = logging.getLogger("synccatalog")
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_STREAM_FORMAT = "[%(levelname)s] %(message)s"

DEBUG = LOGGER.debug
INFO = LOGGER.info
ERROR = LOGGER.error
WARN = LOGGER.warning


class _UTCFormatter(logging.Formatter):
    """Formatter that always emits UTC timestamps with +0000 suffix."""
    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime(LOG_DATE_FORMAT, ct)
        return f"{s}+0000"


def set_up_logging():
    if LOGGER.handlers:
        return
    LOGGER.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOG_PATH)
    fh.setFormatter(_UTCFormatter(LOG_FILE_FORMAT, LOG_DATE_FORMAT))
    fh.setLevel(logging.DEBUG)
    LOGGER.addHandler(fh)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter(LOG_STREAM_FORMAT))
    sh.setLevel(logging.WARNING)
    LOGGER.addHandler(sh)
    LOGGER.propagate = False


def parse_min_app_version(content: bytes) -> str:
    """Parse min_app_version from the first few lines of products.conf. Returns '' if not found."""
    try:
        for raw_line in content.splitlines()[:15]:
            line = raw_line.decode("utf-8").strip()
            match = re.search(r"#?\s*min_app_version\s*=\s*(\S+)", line)
            if match:
                return match.group(1).strip()
    except (UnicodeDecodeError, IndexError):
        pass
    return ""


def get_running_app_version() -> str:
    """Read [id] version from the app's default/app.conf."""
    app_conf_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "default", "app.conf")
    if not os.path.isfile(app_conf_path):
        return "0.0.0"
    try:
        with open(app_conf_path, "r", encoding="utf-8") as f:
            in_id = False
            for line in f:
                line = line.strip()
                if line == "[id]":
                    in_id = True
                    continue
                if in_id and line.startswith("version"):
                    match = re.search(r"version\s*=\s*(\S+)", line)
                    if match:
                        return match.group(1).strip()
                    break
                if in_id and line.startswith("["):
                    break
    except (IOError, OSError):
        pass
    return "0.0.0"


def version_at_least(running: str, required: str) -> bool:
    """True if running >= required (semver-like comparison, e.g. 1.0.13 >= 1.0.15 -> False)."""
    if not required:
        return True
    def parts(v):
        return [int(x) if x.isdigit() else 0 for x in (v or "0").split(".")[:3]]
    rp = parts(running)
    qp = parts(required)
    while len(rp) < 3:
        rp.append(0)
    while len(qp) < 3:
        qp.append(0)
    return rp >= qp


def get_file_version(content: bytes) -> int:
    """Parses a YYYY_MM_DD_HHMM version from the first line of products.conf."""
    try:
        if not content:
            INFO("File content is empty, no version to parse.")
            return 0
        first_line = content.splitlines()[0].decode("utf-8").strip()
        DEBUG(f"Parsing version from first line: '{first_line}'")
        match = re.search(r"#?\s*version\s*=\s*(\d{4}_?\d{2}_?\d{2}_?\d{4})", first_line)
        if match:
            version_str = match.group(1)
            version_int = int(version_str.replace("_", ""))
            INFO(f"Found version string: {version_str} -> {version_int}")
            return version_int
        WARN(f"Version string not found in first line: '{first_line}'")
    except (IndexError, UnicodeDecodeError, ValueError) as e:
        ERROR(f"Could not parse version from file content: {e}")
    return 0


def format_version_timestamp(version_int: int) -> str:
    """Converts a YYYYMMDDHHMM integer to a human-readable string."""
    if version_int == 0:
        return "Not Found"
    try:
        dt_obj = datetime.strptime(str(version_int), "%Y%m%d%H%M")
        return dt_obj.strftime("%B %d, %Y, %I:%M %p UTC")
    except ValueError:
        return f"Invalid Format ({version_int})"


def backup_existing_file(source_path: str):
    """Copies the source file to a timestamped backup."""
    if not os.path.exists(source_path):
        INFO(f"No existing file at {source_path} to back up.")
        return None
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_filename = f"{DESTINATION_FILE_NAME}.{timestamp}.bak"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        shutil.copy2(source_path, backup_path)
        INFO(f"Backed up '{source_path}' to '{backup_path}'")
        return backup_path
    except Exception as e:
        ERROR(f"Failed to create backup for '{source_path}': {e}")
        return None


def prune_old_backups():
    """Keeps only the most recent MAX_BACKUPS backup files."""
    INFO(f"Pruning old backups. Keeping the latest {MAX_BACKUPS}.")
    try:
        backup_files = sorted(
            [f for f in os.listdir(BACKUP_DIR)
             if f.startswith(DESTINATION_FILE_NAME) and f.endswith(".bak")],
            reverse=True,
        )
        if len(backup_files) > MAX_BACKUPS:
            for filename in backup_files[MAX_BACKUPS:]:
                file_path = os.path.join(BACKUP_DIR, filename)
                os.remove(file_path)
                INFO(f"Deleted old backup: {file_path}")
    except Exception as e:
        ERROR(f"Failed to prune old backups: {e}")


@Configuration(type="events")
class SyncCatalog(GeneratingCommand):
    """
    synccatalog: compare local products.conf version against S3 and update if newer.

    ``| synccatalog dryrun=false``
    """

    dryrun = Option(validate=validators.Boolean())

    def write_output(self, data: bytes):
        full_path = os.path.join(DESTINATION_DIR, DESTINATION_FILE_NAME)
        INFO(f"Writing {len(data)} bytes to {full_path}")
        try:
            os.makedirs(DESTINATION_DIR, exist_ok=True)
            with open(full_path, "wb") as f:
                bytes_written = f.write(data)
            INFO(f"Wrote {bytes_written} bytes to {full_path}")
            return full_path, bytes_written
        except IOError as e:
            ERROR(f"Failed to write to {full_path}: {e}")
            raise

    def reload_products_conf(self, session_key: str, splunkd_uri: str) -> dict:
        reload_url = f"{splunkd_uri}/services/configs/conf-products/_reload"
        headers = {"Authorization": f"Splunk {session_key}"}
        INFO(f"Triggering config reload at: {reload_url}")
        try:
            certifi_path = os.path.join(SPLUNK_HOME, "etc", "auth", "cacert.pem")
            verify_tls = certifi_path if os.path.isfile(certifi_path) else False
            response = requests.post(reload_url, headers=headers, verify=verify_tls)
            INFO(f"Reload returned status {response.status_code}")
            response.raise_for_status()
            return {"status": "Success", "message": "Reloaded conf-products."}
        except requests.exceptions.RequestException as e:
            msg = f"Failed to reload conf-products: {e}"
            ERROR(msg)
            return {"status": "Failed", "message": msg}

    def generate(self) -> Generator[dict, None, None]:
        INFO(f"Starting synccatalog. dryrun={self.dryrun}")

        if self.dryrun is None:
            WARN("No option provided.")
            yield {
                "_time": time.time(),
                "status": "Error",
                "reason": "No option provided.",
                "message": "Specify dryrun=true to check or dryrun=false to update.",
            }
            return

        local_version = 0
        local_file_path = os.path.join(DESTINATION_DIR, DESTINATION_FILE_NAME)
        if os.path.exists(local_file_path):
            try:
                with open(local_file_path, "rb") as f:
                    local_content = f.read()
                local_version = get_file_version(local_content)
            except IOError as e:
                ERROR(f"Could not read local file: {e}")
        else:
            INFO("Local products.conf not found. Version = 0.")

        url = S3_BASE_URL + S3_FILE_PATH
        INFO(f"Fetching remote file: {url}")
        try:
            resp = requests.get(url, allow_redirects=True, verify=True)
            INFO(f"S3 responded with status {resp.status_code}")
            resp.raise_for_status()
            s3_content = resp.content
            s3_version = get_file_version(s3_content)
        except requests.exceptions.RequestException as e:
            ERROR(f"Failed to download from S3: {e}")
            yield {
                "_time": time.time(),
                "status": "Failed",
                "reason": "Could not download catalog from S3.",
                "message": f"Download failed: {e}",
                "error": str(e),
            }
            return

        INFO(f"Version check: local={local_version}, s3={s3_version}")

        if self.dryrun is True:
            reason = "Local is current or newer. No action needed."
            recommendation = reason
            if s3_version > local_version:
                min_required = parse_min_app_version(s3_content)
                running_version = get_running_app_version()
                if min_required and not version_at_least(running_version, min_required):
                    reason = f"Did not sync: catalog in S3 requires app v{min_required}+ (this instance is v{running_version}). Upgrade the app first."
                    recommendation = f"Newer catalog in S3 requires app v{min_required} or newer (this instance is v{running_version}). Upgrade the app, then run dryrun=false to update."
                else:
                    reason = "Newer catalog in S3; run dryrun=false to update."
                    recommendation = "Newer version in S3. Run dryrun=false to update."
            elif s3_version == 0 and local_version > 0:
                reason = "Did not sync: could not parse S3 catalog version; do not update."
                recommendation = "WARNING: Could not parse S3 version. Do not update."
            yield {
                "_time": time.time(),
                "status": "Dry Run",
                "reason": reason,
                "local_version": format_version_timestamp(local_version),
                "s3_version": format_version_timestamp(s3_version),
                "recommendation": recommendation,
            }
            return

        if s3_version <= local_version:
            INFO("S3 version is not newer. Skipping update.")
            yield {
                "_time": time.time(),
                "status": "Skipped",
                "reason": "Did not sync: local catalog is current or newer than S3; no update needed.",
                "message": f"Local ({format_version_timestamp(local_version)}) is current or newer than S3 ({format_version_timestamp(s3_version)}).",
                "local_version": format_version_timestamp(local_version),
                "s3_version": format_version_timestamp(s3_version),
            }
            return

        min_required = parse_min_app_version(s3_content)
        if min_required:
            running_version = get_running_app_version()
            if not version_at_least(running_version, min_required):
                INFO(f"Catalog requires app >= {min_required}; running app is {running_version}. Skipping overwrite.")
                yield {
                    "_time": time.time(),
                    "status": "Skipped",
                    "reason": f"Did not sync: catalog requires app v{min_required} or newer; this instance is v{running_version}. Upgrade the app to use this catalog.",
                    "message": f"Catalog requires app v{min_required} or newer. This instance is v{running_version}. Upgrade the app to use this catalog.",
                    "local_version": format_version_timestamp(local_version),
                    "s3_version": format_version_timestamp(s3_version),
                    "min_app_version": min_required,
                    "running_app_version": running_version,
                }
                return

        INFO(f"Updating: S3 ({s3_version}) > local ({local_version}).")
        session_key = self.metadata.searchinfo.session_key
        splunkd_uri = self.metadata.searchinfo.splunkd_uri

        try:
            backup_file_path = backup_existing_file(local_file_path)
            full_path, bytes_written = self.write_output(s3_content)
            reload_result = self.reload_products_conf(session_key, splunkd_uri)
            if backup_file_path:
                prune_old_backups()

            INFO("Catalog sync completed successfully.")
            yield {
                "_time": time.time(),
                "status": "Success",
                "reason": f"Synced: updated catalog from {format_version_timestamp(local_version)} to {format_version_timestamp(s3_version)}.",
                "message": f"Updated from {local_version} to {s3_version}.",
                "bytes_written": bytes_written,
                "destination": full_path,
                "backup": backup_file_path or "N/A",
                "reload_status": reload_result["status"],
                "reload_message": reload_result["message"],
            }
        except Exception as e:
            ERROR(f"Update failed: {e}")
            yield {
                "_time": time.time(),
                "status": "Failed",
                "reason": "Did not sync: update failed (see error).",
                "message": str(e),
                "error": str(e),
            }


set_up_logging()
dispatch(SyncCatalog, sys.argv, sys.stdin, sys.stdout, __name__)
