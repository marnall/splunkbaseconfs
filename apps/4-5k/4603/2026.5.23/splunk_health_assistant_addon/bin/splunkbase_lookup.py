#!/usr/bin/env python3
# coding=utf-8
""" 
A scripted lookup that takes CSV as input, performs a lookup against Splunkbase
CDN dumps to check if apps exist, then returns the CSV results.
Given an app_id (title or ID), returns the splunkbase_status (found/None).
"""

import csv
import sys
import os
import re
import requests
import splunk.clilib.cli_common as cli_common
from typing import Any, Dict, List, Optional, Tuple


# Status constants
STATUS_FOUND = "found"

# Networking config
CDN_TIMEOUT_SECS = 30


def _get_app_version() -> str:
    """Read the app version from app.conf."""
    app_conf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'default', 'app.conf')
    try:
        with open(app_conf_path, 'r') as lines:
            for line in lines:
                if line.strip().startswith('version'):
                    parts = line.split('=')
                    if len(parts) >= 2:
                        return parts[1].strip()
    except Exception:
        return "unknown"


def _get_cdn_urls_from_conf() -> Tuple[str, str]:
    """
    Read CDN URLs from server.conf using Splunk's cli_common library.
    """
    
    stanza = cli_common.getConfStanza("server", "applicationsManagement")
    if not stanza:
        raise RuntimeError(
            "Could not read [applicationsManagement] stanza from server.conf."
        )
    
    apps_dump_url = stanza.get("splunkbaseAppsDumpUrl")
    archived_apps_dump_url = stanza.get("archivedSplunkbaseAppsDumpUrl")
    
    if not apps_dump_url or not archived_apps_dump_url:
        raise RuntimeError(
            "Missing CDN URLs in server.conf [applicationsManagement] stanza. "
            "This feature requires network access to Splunkbase CDN endpoints. "
        )
    
    return apps_dump_url, archived_apps_dump_url


def _fetch_cdn_json(url: str) -> Any:
    """Fetch and parse JSON from CDN URL.
    
    Raises:
        RuntimeError: If the fetch fails or JSON parsing fails.
    """
    try:
        resp = requests.get(url, timeout=CDN_TIMEOUT_SECS)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise RuntimeError(
            f"Failed to fetch CDN JSON from {url}: {str(e)}. "
            "If this is an airgapped environment, this lookup requires network "
            "access to Splunkbase CDN."
        )
    except ValueError as e:
        raise RuntimeError(f"Failed to parse JSON from {url}: {str(e)}")


def _extract_apps_list(payload: Any) -> List[Dict]:
    """Handle various shapes: list or dict with known keys."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("apps", "results", "data", "items"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    return []


def _safe_str(v: Any) -> str:
    """Normalize lookup keys: lowercased string with trimmed whitespace."""
    if v is None:
        return ""
    return str(v).strip().lower()


def _build_indexes(apps: List[Dict]) -> Tuple[Dict, Dict]:
    """Build lookup indexes by title and by ID."""
    by_title = {}
    by_id = {}
    for app in apps:
        # Title index
        title = _safe_str(app.get("title"))
        if title and title not in by_title:
            by_title[title] = app

        # ID-like fields
        id_candidates = [
            app.get("app_id"),
            app.get("appid"),
            app.get("id"),
            app.get("slug"),
            app.get("name"),
        ]

        # Extract numeric id from path like https://.../app/7991/
        path = app.get("path")
        if path:
            path_match = re.search(r"/app/(\d+)/", str(path))
            if path_match:
                id_candidates.append(path_match.group(1))

        for cand in id_candidates:
            normalized_id = _safe_str(cand)
            if normalized_id and normalized_id not in by_id:
                by_id[normalized_id] = app

    return by_title, by_id


def _load_cdn_dumps() -> Tuple[Dict, Dict]:
    """Load CDN dumps and build indexes."""
    try:
        cdn_url_non_archived, cdn_url_archived = _get_cdn_urls_from_conf()
        non_arch_apps = _fetch_cdn_json(cdn_url_non_archived)
        arch_apps = _fetch_cdn_json(cdn_url_archived)
    except RuntimeError as e:
        sys.stderr.write(f"Error loading CDN data: {str(e)}\n")
        return {}, {}
    
    non_arch_apps = _extract_apps_list(non_arch_apps)
    arch_apps = _extract_apps_list(arch_apps)
    all_apps = non_arch_apps + arch_apps
    
    return _build_indexes(all_apps)


def lookup(app_id_value: Optional[str], apps_by_title: Dict, apps_by_id: Dict) -> Optional[str]:
    """Given an app_id (title or ID), find the status."""
    if not app_id_value:
        return None
    
    key = _safe_str(app_id_value)
    
    if apps_by_title.get(key) or apps_by_id.get(key):
        return STATUS_FOUND
    return None

def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: {} [app_id field] [splunkbase_status field]".format(os.path.basename(__file__)))
        sys.exit(1)

    app_id_field = sys.argv[1]
    status_field = sys.argv[2]

    csv_reader = csv.DictReader(sys.stdin)
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=csv_reader.fieldnames)
    csv_writer.writeheader()

    # Load CDN data once before processing records
    apps_by_title, apps_by_id = _load_cdn_dumps()

    for row in csv_reader:
        val = lookup(row.get(app_id_field, None), apps_by_title, apps_by_id)
        if val:
            row[status_field] = val
        csv_writer.writerow(row)


main()
