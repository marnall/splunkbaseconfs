"""REST handler for MCP guardrails settings.

GET  /mcp_guardrails  — returns current values as a flat JSON object.
POST /mcp_guardrails  — validates and writes a flat JSON object to mcp.conf.

FIELD_CONFIG is the single source of truth for which fields are exposed.
Adding or removing an entry here automatically propagates to GET responses,
POST validation, stanza routing, and conf writes. Each entry specifies:
  stanza       - mcp.conf stanza the key lives in ("server" | "rate_limits")
  cast         - type constructor applied on both read and write (float / int)
  min          - lower bound value
  min_inclusive - True means val >= min is required; False means val > min
  default      - fallback used by GET when the key is absent from conf
"""

import json
import os
import sys
import traceback
from typing import Any, Dict

from splunk.persistconn.application import PersistentServerConnectionApplication

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from base_rest_handler import AuthMode, BaseRestHandler
from conf_util import read_conf_stanza
from constants import (
    CONF_KEY_DEFAULT_ROW_LIMIT,
    CONF_KEY_GLOBAL_RATE_LIMIT,
    CONF_KEY_MAX_ROW_LIMIT,
    CONF_KEY_SAIA_TIMEOUT,
    CONF_KEY_TIMEOUT,
    CONF_MCP,
    DEFAULT_DEFAULT_ROW_LIMIT,
    DEFAULT_GLOBAL_RATE_LIMIT,
    DEFAULT_MAX_ROW_LIMIT,
    DEFAULT_SAIA_TIMEOUT,
    DEFAULT_TIMEOUT,
    SPLUNK_MCP_SERVER_APP,
    STANZA_RATE_LIMITS,
    STANZA_SERVER,
)
from http_utils import Request, Response
from logging_config import get_logger
from settings import MCPSettings

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Field configuration — edit here to add, remove, or rename guardrail fields
# ---------------------------------------------------------------------------

# Example: to add a new field "max_row_limit" to the [server] stanza, add:
#   "max_row_limit": {"stanza": "server", "cast": int, "min": 1, "min_inclusive": True, "default": 1000}
# That's all — GET, POST validation, and conf writes pick it up automatically.
FIELD_CONFIG: Dict[str, Dict[str, Any]] = {
    # timeout: the Splunk SDK hard-rejects values <= 0, so the minimum is
    # exclusive (0.01 is valid, 0 is not). "default" is the fallback shown by
    # GET when the key is absent from conf (must itself be a valid value).
    CONF_KEY_TIMEOUT: {
        "stanza": STANZA_SERVER,
        "cast": float,
        "min": 0,
        "min_inclusive": False,
        "default": DEFAULT_TIMEOUT,
    },
    CONF_KEY_SAIA_TIMEOUT: {
        "stanza": STANZA_SERVER,
        "cast": float,
        "min": 0,
        "min_inclusive": False,
        "default": DEFAULT_SAIA_TIMEOUT,
    },
    CONF_KEY_DEFAULT_ROW_LIMIT: {
        "stanza": STANZA_SERVER,
        "cast": int,
        "min": 1,
        "min_inclusive": True,
        "default": DEFAULT_DEFAULT_ROW_LIMIT,
    },
    # "global" is the catch-all rate limit (requests/60 s) across all tools.
    # Per-tool limits use the tool name as the key in the same [rate_limits] stanza.
    CONF_KEY_GLOBAL_RATE_LIMIT: {
        "stanza": STANZA_RATE_LIMITS,
        "cast": int,
        "min": 0,
        "min_inclusive": True,
        "default": DEFAULT_GLOBAL_RATE_LIMIT,
    },
}


class MCPGuardrailsHandler(BaseRestHandler, PersistentServerConnectionApplication):
    # Use the user token for conf I/O. ConfigFileManager uses the
    # servicesNS/nobody/{app}/properties/ path, which is accessible to any
    # user with the mcp_tool_admin capability — no elevated permissions needed.
    AUTH_MODE = AuthMode.USER
    SPLUNK_OWNER = "nobody"
    SPLUNK_APP = SPLUNK_MCP_SERVER_APP
    SPLUNK_SHARING = "app"

    def __init__(self, command_line: str, command_arg: str) -> None:
        BaseRestHandler.__init__(self)

    def handle(self, in_string: str) -> Dict[str, Any]:
        try:
            request_data = self.parse_request(in_string)
            MCPSettings.set_splunkd_url_from_request(request_data)
            session_key = self._extract_user_session_token(request_data)
            self.initialize_user_service({"token": session_key}, request_data)
        except ValueError as exc:
            logger.info("Guardrails auth/parse error: %s", exc)
            return Response.bad_request(str(exc)).build()

        try:
            request = Request(in_string)
            logger.info(
                "Guardrails handler received %s request — payload: %s",
                request.method,
                request.raw_payload if request.method == "POST" else "(none)",
            )
            if request.method == "GET":
                return self._handle_get()
            if request.method == "POST":
                return self._handle_post(request)
            logger.info(
                "Guardrails handler: unsupported method %s (allowed: GET, POST)",
                request.method,
            )
            return Response.method_not_allowed(request.method, ["GET", "POST"]).build()
        except Exception as exc:
            logger.exception(
                "Unexpected error in guardrails handler: %s", traceback.format_exc()
            )
            return Response.internal_server_error(str(exc)).build()

    def _handle_get(self) -> Dict[str, Any]:
        # Read each distinct stanza once. service.confs returns the fully
        # merged conf (default/ + local/), so no manual file merging needed.
        #
        # Example — FIELD_CONFIG has two stanzas ("server", "rate_limits"):
        #   stanza_cache = {
        #       "server":      {"timeout": "45.0", "default_row_limit": "50"},
        #       "rate_limits": {"global": "300"},
        #   }
        stanza_cache = {
            stanza: read_conf_stanza(self.service, CONF_MCP, stanza)
            for stanza in {meta["stanza"] for meta in FIELD_CONFIG.values()}
        }
        # Cast each raw string to its declared type. Falls back to "default"
        # when the key is absent from the conf (e.g. first install, stanza empty).
        #
        # Example result:
        #   {"timeout": 45.0, "default_row_limit": 50, "global": 300}
        result = {}
        for field, meta in FIELD_CONFIG.items():
            raw = stanza_cache[meta["stanza"]].get(field, meta["default"])
            try:
                result[field] = meta["cast"](raw)
            except (TypeError, ValueError):
                logger.info(
                    "Guardrails GET: '%s' value %r is malformed, using default %r",
                    field,
                    raw,
                    meta["default"],
                )
                result[field] = meta["default"]
        logger.info("Guardrails GET: %s", result)
        return Response.ok().json(result).build()

    def _handle_post(self, request: Request) -> Dict[str, Any]:
        # Parse and validate the incoming payload.
        try:
            body = json.loads(request.raw_payload or "")
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object.")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.info("Guardrails POST: invalid payload — %s", exc)
            return Response.bad_request(str(exc)).build()

        logger.info("Guardrails POST: received fields %s", list(body.keys()))

        # Read max_row_limit from the live conf so _validate can enforce that
        # default_row_limit never exceeds it. Falls back to 1000 if the key is
        # absent (e.g. fresh install before mcp.conf [server] is written).
        server_stanza = read_conf_stanza(self.service, CONF_MCP, STANZA_SERVER)
        try:
            max_row_limit = int(
                server_stanza.get(CONF_KEY_MAX_ROW_LIMIT, DEFAULT_MAX_ROW_LIMIT)
            )
        except (TypeError, ValueError):
            logger.info(
                "Guardrails POST: %s in conf is malformed (%r), using default %s",
                CONF_KEY_MAX_ROW_LIMIT,
                server_stanza.get(CONF_KEY_MAX_ROW_LIMIT),
                1000,
            )
            max_row_limit = DEFAULT_MAX_ROW_LIMIT
        logger.info("Guardrails POST: max_row_limit from conf = %s", max_row_limit)

        errors = self._validate(body, max_row_limit)
        if errors:
            logger.info(
                "Guardrails POST: validation failed — fields: %s, errors: %s",
                list(errors.keys()),
                errors,
            )
            return Response.bad_request(errors).build()

        logger.info("Guardrails POST: validation passed for all fields")

        # Group validated fields by stanza so each stanza gets one submit()
        # call (one HTTP round-trip per stanza instead of one per field).
        #
        # Example — body {"timeout": 60, "default_row_limit": 200, "global": 500}
        # produces:
        #   by_stanza = {
        #       "server":      {"timeout": 60.0, "default_row_limit": 200},
        #       "rate_limits": {"global": 500},
        #   }
        by_stanza: Dict[str, Dict[str, Any]] = {}
        for field, meta in FIELD_CONFIG.items():
            if field in body:
                by_stanza.setdefault(meta["stanza"], {})[field] = meta["cast"](
                    body[field]
                )

        # submit() is a merge write — only supplied keys change; everything
        # else already in the stanza (e.g. require_encrypted_token) is kept.
        # conf.create() is only needed the very first time a stanza doesn't
        # exist yet (e.g. fresh install where local/mcp.conf has no [rate_limits]).
        conf = self.service.confs[CONF_MCP]
        for stanza, data in by_stanza.items():
            try:
                stanza_obj = conf[stanza]
            except KeyError:
                logger.info(
                    "Guardrails POST: stanza [%s] not found in mcp.conf, creating it",
                    stanza,
                )
                stanza_obj = conf.create(stanza)
            stanza_obj.submit(data)
            logger.info("Guardrails POST: wrote [%s] %s", stanza, data)

        logger.info(
            "Guardrails POST: all stanzas written successfully (%s)",
            list(by_stanza.keys()),
        )
        return Response.ok().build()

    @staticmethod
    def _validate(data: Dict[str, Any], max_row_limit: int) -> Dict[str, str]:
        errors: Dict[str, str] = {}
        for field, meta in FIELD_CONFIG.items():
            if field not in data:
                logger.info(
                    "Guardrails validation: field '%s' is missing from payload", field
                )
                errors[field] = "Required."
                continue
            try:
                typed_val = meta["cast"](data[field])
                min_val = meta["min"]
                inclusive = meta["min_inclusive"]
                # Check lower bound: inclusive means >= min, exclusive means > min.
                below_min = typed_val < min_val if inclusive else typed_val <= min_val
                if below_min:
                    bound = ">=" if inclusive else ">"
                    logger.info(
                        "Guardrails validation: '%s' value %s rejected — must be %s %s",
                        field,
                        typed_val,
                        bound,
                        min_val,
                    )
                    errors[field] = f"Must be {bound} {min_val}."
                elif field == CONF_KEY_DEFAULT_ROW_LIMIT and typed_val > max_row_limit:
                    logger.info(
                        "Guardrails validation: default_row_limit %s rejected — exceeds max_row_limit %s",
                        typed_val,
                        max_row_limit,
                    )
                    errors[field] = f"Must be <= max_row_limit ({max_row_limit})."
                else:
                    logger.info(
                        "Guardrails validation: '%s' = %s accepted", field, typed_val
                    )
            except (ValueError, TypeError):
                logger.info(
                    "Guardrails validation: '%s' value %r is not a valid number",
                    field,
                    data[field],
                )
                errors[field] = "Must be a valid number."
        return errors
