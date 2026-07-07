from __future__ import annotations

import json
import logging
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, make_splunkhome_path(["etc", "apps", "alphasoc_for_splunk", "bin"]))

from a4slib.config import ConfigError, CredentialError
from a4slib.http_client import AlphaSOCHttpClient, APIError
from a4slib.splunk_service import service_from_request

logger = logging.getLogger(__name__)

_EXPIRED_ERROR = "Your API key has expired."


def json_response(body: dict[str, object], status: int = 200) -> dict[str, object]:
    return {
        "status": status,
        "payload": json.dumps(body),
        "headers": {"Content-Type": "application/json"},
    }


def error_response(message: str, status: int = 200) -> dict[str, object]:
    return json_response({"success": False, "error": message}, status=status)


def _account_status_error(exc: APIError) -> str:
    """Map an APIError from /v1/account/status to a user-facing message."""
    if exc.status_code in (401, 403):
        if "expired" in str(exc).lower():
            return _EXPIRED_ERROR
        return "Invalid API key."
    if exc.status_code is None:
        return "Unable to validate API key. Check your connection and try again."
    return str(exc)


class AccountStatusHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line: str, _command_arg: str) -> None:
        super().__init__()

    def handle(self, in_string: str) -> dict[str, object]:
        request = json.loads(in_string)

        method = str(request.get("method", "GET")).upper()
        if method != "GET":
            return error_response(f"Method {method} not allowed.", status=405)

        try:
            service = service_from_request(request)
        except ValueError:
            return error_response("Internal error. Check the AlphaSOC app logs.")

        try:
            client = AlphaSOCHttpClient.from_service(service)
        except (CredentialError, ConfigError) as exc:
            logger.exception("Failed to build AlphaSOC client for account status validation.")
            return error_response(str(exc))

        try:
            data = client.account_status()
        except APIError as exc:
            return error_response(_account_status_error(exc))

        if data.get("expired") is True:
            return error_response(_EXPIRED_ERROR)
        return json_response({"success": True})
