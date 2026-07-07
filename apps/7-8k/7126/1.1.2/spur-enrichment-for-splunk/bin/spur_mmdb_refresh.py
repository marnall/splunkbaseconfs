"""
Persistent REST handler that refreshes the local Spur IP-geo MMDB file on
behalf of the `spuriplocation` search command.

The handler runs with passSystemAuth = true so it can read the Spur API token
and proxy settings under system auth, then download the MMDB using the
existing `spurfeedingest.process_geo_feed` pipeline. Callers receive only the
resulting file path and a refreshed/cached flag — no credentials cross the
handler boundary.

A fast-path short-circuits the download when the local MMDB is already less
than one day old (the upstream Spur ipgeo feed regenerates daily), so
repeated calls from non-admin callers cannot coerce back-to-back downloads.
Concurrent refreshes are serialized by the existing `acquire_lock` helper
inside `process_geo_feed`.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunklib import client as splunk_client

from spurlib.api import get_proxy_settings
from spurlib.logging import setup_logging
from spurlib._sysauth import build_config_bundle
from spurfeedingest import mmdb_is_fresh

APP_NAME = "spur-enrichment-for-splunk"
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_DIR = os.path.join(APP_DIR, "local", "data")
MMDB_PATH = os.path.join(CHECKPOINT_DIR, "mmdb", "ipgeo.mmdb")

SUPPORTED_FEED_TYPES = {"ipgeo"}


class _NotifyAdapter:
    """Minimal shim so `spurlib.notify` helpers inside `process_geo_feed`
    can call `.service.messages.create(...)` during a handler invocation."""

    def __init__(self, service):
        self.service = service


def _response(status, payload_dict):
    return {"payload": json.dumps(payload_dict), "status": status}


def _error(status, msg):
    return _response(status, {"path": None, "refreshed": False, "error": msg})


class SpurMmdbRefresh(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        logger = setup_logging()
        try:
            req = json.loads(in_string)
        except (ValueError, TypeError) as e:
            logger.error("spur_mmdb_refresh: malformed request envelope: %s", e)
            return _error(400, "malformed request")

        method = (req.get("method") or "").upper()
        if method and method != "POST":
            return _error(405, "method not allowed; use POST")

        system_authtoken = req.get("system_authtoken")
        if not system_authtoken:
            logger.error("spur_mmdb_refresh: missing system_authtoken (passSystemAuth not set?)")
            return _error(500, "missing system auth")

        caller_user = (req.get("session") or {}).get("user", "unknown")

        form = dict(req.get("form") or [])
        feed_type = form.get("feed_type")
        if not feed_type:
            try:
                payload = json.loads(req.get("payload") or "{}")
                feed_type = payload.get("feed_type")
            except (ValueError, TypeError):
                feed_type = None
        feed_type = feed_type or "ipgeo"

        if feed_type not in SUPPORTED_FEED_TYPES:
            logger.warning(
                "spur_mmdb_refresh: rejected feed_type=%s (user=%s)", feed_type, caller_user
            )
            return _error(400, "unsupported feed_type: %s" % feed_type)

        if mmdb_is_fresh(MMDB_PATH):
            logger.info(
                "spur_mmdb_refresh: fast-path cache hit feed_type=%s user=%s", feed_type, caller_user
            )
            return _response(
                200,
                {"path": MMDB_PATH, "refreshed": False, "error": None},
            )

        try:
            os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        except OSError as e:
            logger.error("spur_mmdb_refresh: cannot create checkpoint dir %s: %s", CHECKPOINT_DIR, e)
            return _error(500, "cannot create checkpoint dir")

        try:
            service = splunk_client.Service(
                token=system_authtoken,
                app=APP_NAME,
                owner="nobody",
            )
            bundle = build_config_bundle(service)
        except Exception as e:
            logger.error("spur_mmdb_refresh: config read failed for user=%s: %s", caller_user, e)
            return _error(500, "config read failed")

        token = bundle.get("token")
        if not token:
            logger.warning("spur_mmdb_refresh: no token configured (user=%s)", caller_user)
            return _error(500, "no token configured")

        proxy_handler_config = get_proxy_settings(bundle, logger)

        try:
            from spurfeedingest import process_geo_feed
        except Exception as e:
            logger.error("spur_mmdb_refresh: cannot import process_geo_feed: %s", e)
            return _error(500, "feed pipeline unavailable")

        adapter = _NotifyAdapter(service)
        try:
            process_geo_feed(
                adapter,
                logger,
                token,
                proxy_handler_config,
                feed_type,
                "spur_mmdb_refresh",
                None,
                CHECKPOINT_DIR,
            )
        except Exception as e:
            logger.error("spur_mmdb_refresh: feed download failed for user=%s: %s", caller_user, e)
            return _error(502, "feed download failed: %s" % e)

        if not os.path.exists(MMDB_PATH):
            logger.error(
                "spur_mmdb_refresh: feed pipeline completed but file missing at %s (user=%s)",
                MMDB_PATH,
                caller_user,
            )
            return _error(502, "feed pipeline did not produce an mmdb file")

        logger.info(
            "spur_mmdb_refresh: refreshed feed_type=%s path=%s user=%s",
            feed_type,
            MMDB_PATH,
            caller_user,
        )
        return _response(
            200,
            {"path": MMDB_PATH, "refreshed": True, "error": None},
        )
