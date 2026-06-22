#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
migrate_v3_to_v4.py — one-shot data migration from v3.0.x to v4.0.0.

Idempotent. Re-running is safe and effectively a no-op.

What it does:
  1. Backfills `thread_id` on existing `mcp_query_history` rows. Each historic
     query becomes its own single-message thread named
     "<user>:legacy-<query_id[:8]>". This lets the v4 UI list past queries
     as conversations even though they were never multi-turn.

  2. Seeds the new `mcp_conversation_threads` collection with one record per
     unique thread_id from step 1 so the conversation-list UI doesn't need
     to scan messages.

  3. No deletion or destructive ops — v3 KV data is preserved.

Run as:
    splunk cmd python bin/migrate_v3_to_v4.py

Or wire into setup wizard:
    splunk cmd python bin/install_deps.py && \\
    splunk cmd python bin/migrate_v3_to_v4.py

Exit codes:
  0  success / nothing to migrate
  1  KV-store error
"""
from __future__ import annotations

import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import splunk.entity as entity  # type: ignore
import splunklib.client as client  # type: ignore

from kv_store import KVStoreClient, KVStoreError  # type: ignore

LOG = logging.getLogger("migrate_v3_to_v4")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

APP_NAME = "AI_Query_Assistant_for_Splunk"


def _service_from_env():
    """Build an authenticated Service from environment / mgmt URI defaults."""
    # When run by `splunk cmd python ...`, SPLUNK_HOME + a session token are
    # available via the splunk.entity helper. Fall back to localhost mgmt.
    token = os.environ.get("SPLUNK_SESSION_KEY")
    if token:
        return client.connect(token=token, owner="nobody", app=APP_NAME)
    # CLI / manual run — splunk binary will inject auth via stdin.
    return client.connect(
        host="localhost",
        port=int(os.environ.get("SPLUNKD_PORT", "8089")),
        scheme="https",
        username=os.environ.get("SPLUNK_USER", "admin"),
        password=os.environ.get("SPLUNK_PASSWORD", ""),
        owner="nobody",
        app=APP_NAME,
    )


def main() -> int:
    try:
        svc = _service_from_env()
    except Exception as e:
        LOG.error("could not connect to splunkd: %s", e)
        return 1

    try:
        history = KVStoreClient(svc, "mcp_query_history")
        threads = KVStoreClient(svc, "mcp_conversation_threads")
    except Exception as e:
        LOG.error("cannot open KV collections: %s", e)
        return 1

    LOG.info("scanning mcp_query_history for rows missing thread_id...")
    try:
        rows = history.query(query={})
    except KVStoreError as e:
        LOG.error("failed to scan history: %s", e)
        return 1

    seen_threads: dict[str, dict] = {}
    backfilled = 0
    for r in rows:
        if r.get("thread_id"):
            continue
        user = r.get("user", "unknown")
        qid = r.get("query_id", "")
        thread_id = f"{user}:legacy-{qid[:8]}" if qid else f"{user}:legacy-{int(time.time())}"

        try:
            history.update(r["_key"], {**r, "thread_id": thread_id})
            backfilled += 1
        except Exception as e:
            LOG.warning("failed to update history row %s: %s", r.get("_key"), e)
            continue

        seen_threads.setdefault(thread_id, {
            "thread_id": thread_id,
            "user": user,
            "title": (r.get("natural_language") or "")[:80],
            "last_activity": r.get("timestamp", int(time.time())),
            "message_count": 1,
            "archived": False,
            "created_at": r.get("timestamp", int(time.time())),
        })

    LOG.info("backfilled %d history rows", backfilled)

    LOG.info("seeding mcp_conversation_threads with %d threads...", len(seen_threads))
    seeded = 0
    for thread_id, meta in seen_threads.items():
        # Idempotency: skip if a row with this thread_id already exists.
        try:
            existing = threads.query(query={"thread_id": thread_id})
            if existing:
                continue
            threads.insert(meta)
            seeded += 1
        except Exception as e:
            LOG.warning("failed to insert thread %s: %s", thread_id, e)
            continue

    LOG.info("seeded %d new threads", seeded)
    LOG.info("migration complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
