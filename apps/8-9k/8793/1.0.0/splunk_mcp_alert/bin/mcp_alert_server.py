"""MCP Alert Server — PersistentServerConnectionApplication handler.

Handles JSON-RPC 2.0 requests for alert management via the MCP protocol.
Supports: ping, initialize, tools/list, tools/call, notifications/initialized.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from splunk.persistconn.application import PersistentServerConnectionApplication

from alert_tools import TOOLS, execute_tool
from auth import validate_bearer_token
from rate_limiter import SlidingWindowRateLimiter
from splunk_api import SplunkAPIClient

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"
PUBLIC_METHODS = {"ping"}
SUPPORTED_METHODS = {"ping", "initialize", "tools/list", "tools/call", "notifications/initialized"}


class MCPAlertHandler(PersistentServerConnectionApplication):
    """Persistent REST endpoint for MCP Alert JSON-RPC."""

    MAX_PAYLOAD_BYTES = 131072

    def __init__(self, command_line: str, command_arg: str) -> None:
        super().__init__()
        max_requests, window_seconds = self._load_rate_limit_config()
        self._rate_limiter = SlidingWindowRateLimiter(
            max_requests=max_requests, window_seconds=window_seconds,
        )

    @staticmethod
    def _load_rate_limit_config():
        """Read rate limit settings from mcp_alert.conf, falling back to defaults."""
        max_requests = 600
        window_seconds = 60
        try:
            import configparser
            conf_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "default", "mcp_alert.conf",
            )
            if os.path.isfile(conf_path):
                parser = configparser.ConfigParser()
                parser.read(conf_path)
                max_requests = parser.getint("rate_limits", "global", fallback=max_requests)
                window_seconds = parser.getint("rate_limits", "time_window_seconds", fallback=window_seconds)
        except Exception as e:
            logger.warning("Failed to read mcp_alert.conf rate_limits: %s, using defaults", e)
        return max_requests, window_seconds

    def handle(self, in_string: str) -> Dict[str, Any]:
        """Handle incoming MCP JSON-RPC request."""
        try:
            request = json.loads(in_string)
        except (json.JSONDecodeError, TypeError):
            return self._error_response(400, None, -32700, "Parse error: invalid request envelope")

        payload_str = request.get("payload", "")
        system_authtoken = request.get("system_authtoken", "")
        server_info = request.get("server", {})
        base_url = server_info.get("rest_uri", "https://localhost:8089")

        try:
            rpc_req = json.loads(payload_str) if payload_str else {}
        except (json.JSONDecodeError, TypeError):
            return self._error_response(400, None, -32700, "Parse error: invalid JSON in payload")

        rpc_id = rpc_req.get("id")
        method = rpc_req.get("method", "")

        if method not in SUPPORTED_METHODS:
            return self._error_response(400, rpc_id, -32601, f"Method not found: {method}")

        if not self._rate_limiter.allow():
            return self._error_response(429, rpc_id, -32000, "Rate limit exceeded")

        if method not in PUBLIC_METHODS:
            auth_token = self._extract_bearer_token(request)
            if auth_token:
                # External MCP client with Bearer token
                valid, username, error = validate_bearer_token(
                    token=auth_token,
                    system_authtoken=system_authtoken,
                    base_url=base_url,
                )
                if not valid:
                    if username is not None:
                        return self._error_response(403, rpc_id, -32000, error or "Access denied")
                    return self._error_response(401, rpc_id, -32000, error or "Authentication failed")
            elif system_authtoken:
                # Browser request through Splunk Web proxy — already authenticated
                # Splunk injects system_authtoken for valid sessions
                auth_token = system_authtoken
                username = request.get("session", {}).get("user", "unknown")
            else:
                return self._error_response(401, rpc_id, -32000, "Missing Bearer token or Splunk session")
        else:
            auth_token = None
            username = None

        if method == "ping":
            return self._success_response(200, rpc_id, {"message": "pong"})
        elif method == "initialize":
            return self._success_response(200, rpc_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": "splunk-mcp-alert", "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            })
        elif method == "tools/list":
            return self._success_response(200, rpc_id, {"tools": TOOLS})
        elif method == "tools/call":
            return self._handle_tools_call(rpc_req, rpc_id, auth_token, base_url)
        elif method == "notifications/initialized":
            return self._success_response(200, rpc_id, {})

        return self._error_response(400, rpc_id, -32601, f"Method not found: {method}")

    def _handle_tools_call(self, rpc_req, rpc_id, auth_token, base_url):
        params = rpc_req.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            client = SplunkAPIClient(base_url=base_url, token=auth_token)
            result_text = execute_tool(client, tool_name, arguments)
            return self._success_response(200, rpc_id, {
                "content": [{"type": "text", "text": result_text}],
            })
        except ValueError as e:
            return self._error_response(400, rpc_id, -32602, str(e))
        except SplunkAPIClient.APIError as e:
            return self._error_response(502, rpc_id, -32603, f"Splunk API error: {e.message}")
        except Exception as e:
            logger.exception("Unexpected error in tools/call: %s", e)
            return self._error_response(500, rpc_id, -32603, "Internal server error")

    def _extract_bearer_token(self, request):
        headers = request.get("headers", [])
        for key, value in headers:
            if str(key).lower() == "authorization" and value.lower().startswith("bearer "):
                return value[7:].strip()
        return None

    def _success_response(self, status, rpc_id, result):
        return {
            "status": status,
            "headers": {"Content-Type": "application/json"},
            "payload": {"jsonrpc": "2.0", "id": rpc_id, "result": result},
        }

    def _error_response(self, status, rpc_id, code, message):
        return {
            "status": status,
            "headers": {"Content-Type": "application/json"},
            "payload": {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}},
        }
