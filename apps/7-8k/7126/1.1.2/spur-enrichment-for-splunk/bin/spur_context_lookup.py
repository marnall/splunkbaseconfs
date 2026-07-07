"""
Persistent REST handler that performs Spur Context API lookups on behalf of
search commands.

The handler runs with passSystemAuth = true so it can read storage/passwords
and the app's `api.conf` / `customalerts.conf` / `server.conf` stanzas under
the system auth token regardless of the caller's role. Credentials are used
only to make the upstream HTTPS request — the response returned to the caller
contains only enrichment data, a remaining-balance counter, and the configured
low-balance notification threshold. Neither the token nor the proxy password
is ever included in the response body.

This endpoint replaces the legacy `/spur_get_credentials` handler, which
returned cleartext credentials and was therefore a credential-exfiltration
primitive reachable by any authenticated user via the Splunk REST API.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunklib import client as splunk_client

from spurlib.api import do_context_lookup
from spurlib.logging import setup_logging
from spurlib._sysauth import build_config_bundle

APP_NAME = "spur-enrichment-for-splunk"


def _response(status, payload_dict):
    return {"payload": json.dumps(payload_dict), "status": status}


def _error(status, msg):
    return _response(status, {"data": None, "balance": 0, "low_query_threshold": 0, "error": msg})


class SpurContextLookup(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        logger = setup_logging()
        try:
            req = json.loads(in_string)
        except (ValueError, TypeError) as e:
            logger.error("spur_context_lookup: malformed request envelope: %s", e)
            return _error(400, "malformed request")

        method = (req.get("method") or "").upper()
        if method and method != "POST":
            return _error(405, "method not allowed; use POST")

        system_authtoken = req.get("system_authtoken")
        if not system_authtoken:
            logger.error("spur_context_lookup: missing system_authtoken (passSystemAuth not set?)")
            return _error(500, "missing system auth")

        caller_user = (req.get("session") or {}).get("user", "unknown")

        form = dict(req.get("form") or [])
        ip = form.get("ip")
        if not ip:
            try:
                payload = json.loads(req.get("payload") or "{}")
                ip = payload.get("ip")
            except (ValueError, TypeError):
                ip = None
        if not ip:
            logger.warning("spur_context_lookup: missing ip (user=%s)", caller_user)
            return _error(400, "missing ip")

        try:
            service = splunk_client.Service(
                token=system_authtoken,
                app=APP_NAME,
                owner="nobody",
            )
            bundle = build_config_bundle(service)
        except Exception as e:
            logger.error("spur_context_lookup: config read failed for user=%s: %s", caller_user, e)
            return _error(500, "config read failed")

        if not bundle.get("token"):
            logger.warning("spur_context_lookup: no token configured (user=%s)", caller_user)
            return _error(500, "no token configured")

        try:
            data, balance = do_context_lookup(logger, bundle, ip)
        except ValueError as e:
            logger.warning("spur_context_lookup: bad request from user=%s: %s", caller_user, e)
            return _error(400, str(e))
        except Exception as e:
            logger.error("spur_context_lookup: upstream error for user=%s: %s", caller_user, e)
            return _error(502, "upstream error: %s" % e)

        low_threshold = 0
        try:
            low_threshold = int(((bundle.get("alerts") or {}).get("low_query_threshold") or 0))
        except (TypeError, ValueError):
            low_threshold = 0

        logger.info(
            "spur_context_lookup: served lookup ip=%s user=%s balance=%s",
            ip,
            caller_user,
            balance,
        )
        return _response(
            200,
            {
                "data": data,
                "balance": balance,
                "low_query_threshold": low_threshold,
                "error": None,
            },
        )
