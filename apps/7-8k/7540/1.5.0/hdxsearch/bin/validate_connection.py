#!/usr/bin/env python3
"""
REST handler: validates a Hydrolix cluster connection.

Registered in restmap.conf as /hdx_validate_connection.
Accepts POST with JSON body:
    {cluster, endpoint, authType, username, password, apiToken}
Returns JSON:
    {success: true, databases: [...]}  or  {success: false, error: "..."}

SSRF mitigation: endpoint must match strict `hostname` or `hostname:port` pattern --
no schemes, paths, query strings, or fragments are accepted.
"""

import json
import logging
import os
import re
import sys
from typing import Optional

_bin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_bin_dir, "..", "lib"))
sys.path.insert(0, _bin_dir)

from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402

from cluster_config import ClusterConfig  # noqa: E402
from errors import HdxCommandFatalError  # noqa: E402
from errors import HdxClientError  # noqa: E402
from proxy_config import ProxyConfig  # noqa: E402
from splunklib.client import Service as SplunkService  # noqa: E402

logger = logging.getLogger("hdxsearch.validate_connection")

# Matches hostname or hostname:port -- no scheme, no path, no query, no fragment.
# hostname: letters, digits, hyphens, dots; port (optional): 1-65535.
_ENDPOINT_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9\-\.]*[A-Za-z0-9])?(:[0-9]{1,5})?$")


def _get_splunk_service(request: dict) -> "Optional[SplunkService]":
    """Create a Splunk service from the request's session token, or None on failure."""
    try:
        token = request["session"]["authtoken"]
        return SplunkService(token=token, host="localhost", port=8089, app="hdxsearch", owner="nobody")
    except Exception:
        return None


class ValidateConnection(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def handle(self, in_string) -> dict:
        request = json.loads(in_string)
        method = request.get("method", "").upper()
        if method != "POST":
            return self._json_response(405, {"success": False, "error": "Method not allowed"})

        user = request.get("session", {}).get("user", "<unknown>")
        try:
            body = json.loads(request.get("payload", "{}"))
        except (json.JSONDecodeError, TypeError):
            return self._json_response(400, {"success": False, "error": "Invalid JSON payload"})

        # SSRF mitigation: strict format validation
        if (endpoint := body.get("endpoint")) and not _ENDPOINT_RE.match(endpoint):
            return self._json_response(
                400,
                {
                    "success": False,
                    "error": (
                        "Invalid endpoint format. Expected hostname or hostname:port "
                        "(e.g. cluster.example.com or cluster.example.com:8443). "
                        "Schemes, paths, and query strings are not allowed."
                    ),
                },
            )

        logger.info(f"validate_connection: user: {user} endpoint: {endpoint} attempting connection")

        proxy = None
        try:
            if service := _get_splunk_service(request):
                proxy = ProxyConfig.infer_proxy_for(
                    service,
                    body.get("cluster") or None,
                    body.get("endpoint") or None,
                )
        except Exception:
            logger.debug("validate_connection: could not resolve proxy, proceeding without")

        try:
            # NB `body` contains fields from both the hdxsearch.conf cluster config and the passwords.conf cluster secrets
            config = ClusterConfig.from_dicts(body, body, proxy)
            client = config.make_client(logger)
            databases = client.show_databases()
        except HdxCommandFatalError as exc:
            logger.warning(f"validate_connection: user: {user} endpoint: {endpoint} config error: {exc}")
            return self._json_response(400, {"success": False, "error": str(exc)})
        except HdxClientError as exc:
            logger.warning(
                f"validate_connection: user: {user} endpoint: {endpoint} unable to confirm cluster reachability: {exc.message}"
            )
            return self._json_response(200, {"success": False, "error": exc.message})

        logger.info(
            f"validate_connection: user: {user} endpoint: {endpoint} confirmed cluster reachability, databases: {len(databases)}"
        )
        return self._json_response(200, {"success": True, "databases": databases})

    @staticmethod
    def _json_response(status: int, payload: dict) -> dict:
        return {
            "status": status,
            "payload": payload,
            "headers": {"Content-Type": "application/json"},
        }


if __name__ == "__main__":
    from splunk.persistconn.appserver import PersistentServerConnectionApplicationServer

    PersistentServerConnectionApplicationServer().run()
