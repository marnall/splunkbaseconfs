#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


SAFETY_TEXT = (
    "CryptView Collector collects cryptographic metadata only. "
    "It does not collect private keys, passwords, keystore secrets, tokens, cookies, "
    "or confidential file contents."
)


def _bootstrap_repo_path() -> None:
    """
    Resolve the CryptView collector package for import.

    Resolution order:
      1. Bundled `bin/lib/` — self-contained tarball case (v0.1.1+ Splunkbase build).
         The packaging script vendors cryptview.collector and
         cryptview.parsers.cert_file_parser here so the wrapper works out of the
         box with no CRYPTVIEW_HOME configuration.
      2. `CRYPTVIEW_HOME` env var — points at a full CryptView repository checkout.
         Kept for private-beta / dev installs.
      3. Repo guess (`../../` from this file) — supports running the wrapper
         directly out of a repo tree without setting CRYPTVIEW_HOME.
    """
    candidates = []

    bundled_lib = Path(__file__).resolve().parent / "lib"
    if (bundled_lib / "cryptview" / "collector").exists():
        candidates.append(bundled_lib)

    env_home = os.environ.get("CRYPTVIEW_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())

    repo_guess = Path(__file__).resolve().parents[2]
    candidates.append(repo_guess)

    for candidate in candidates:
        cryptview_dir = candidate / "cryptview"
        if cryptview_dir.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
            return


def _status_event(message: str) -> dict:
    try:
        from cryptview.collector.core import COLLECTOR_VERSION, SCHEMA_VERSION
    except Exception:
        collector_version = "0.1.0"
        schema_version = "0.1"
    else:
        collector_version = COLLECTOR_VERSION
        schema_version = SCHEMA_VERSION

    return {
        "time": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "event_type": "collector_status",
        "asset_id": None,
        "asset_type": "collector_status",
        "host": os.environ.get("HOSTNAME") or "localhost",
        "source_type": "filesystem_scan",
        "path_hash": None,
        "path_hint": None,
        "file_extension": None,
        "file_size_bytes": None,
        "modified_time": None,
        "collector_version": collector_version,
        "schema_version": schema_version,
        "risk_flags": [],
        "level": "warning",
        "message": message,
    }


def main() -> int:
    _bootstrap_repo_path()

    try:
        from cryptview.collector.core import build_collector_config, collect_filesystem_events, write_ndjson
    except Exception as exc:
        print(f"CryptView Collector wrapper error: failed to import cryptview.collector: {exc}", file=sys.stderr)
        print(
            "Set CRYPTVIEW_HOME to the CryptView repository root or install the shared collector package for the Splunk Python environment.",
            file=sys.stderr,
        )
        return 1

    raw_paths = os.environ.get("CRYPTVIEW_COLLECTOR_PATHS", "").strip()
    if not raw_paths:
        write_ndjson([_status_event("collector_not_configured:set_CRYPTVIEW_COLLECTOR_PATHS")], sys.stdout)
        return 0

    paths = [segment.strip() for segment in raw_paths.split(",") if segment.strip()]
    redact_paths = os.environ.get("CRYPTVIEW_COLLECTOR_REDACT_PATHS", "true").strip().lower() != "false"
    follow_symlinks = os.environ.get("CRYPTVIEW_COLLECTOR_FOLLOW_SYMLINKS", "false").strip().lower() == "true"
    max_file_size_bytes = int(os.environ.get("CRYPTVIEW_COLLECTOR_MAX_FILE_SIZE_BYTES", str(5 * 1024 * 1024)))

    config = build_collector_config(
        paths=paths,
        redact_paths=redact_paths,
        follow_symlinks=follow_symlinks,
        max_file_size_bytes=max_file_size_bytes,
    )
    events = collect_filesystem_events(config)
    write_ndjson(events, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
