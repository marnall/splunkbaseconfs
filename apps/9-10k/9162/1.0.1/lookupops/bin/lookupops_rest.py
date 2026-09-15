#!/usr/bin/env python3
"""Federal AI LookupOps persistent REST handler.

Routes /services/lookupops/* to the Api layer. Authentication comes from the
Splunk session that splunkd already validated (requireAuthentication=true in
restmap.conf); authorization is re-derived server-side for every request.
Responses are JSON only, with stable error codes and safe messages.
"""
import json
import logging
import logging.handlers
import os
import sys

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402

from lookupops_lib import errors  # noqa: E402
from lookupops_lib.api import Api  # noqa: E402
from lookupops_lib.limits import Limits  # noqa: E402
from lookupops_lib.splunk_client import SplunkClient  # noqa: E402

LOG = logging.getLogger("lookupops")
if not LOG.handlers:
    LOG.setLevel(logging.INFO)
    splunk_home = os.environ.get("SPLUNK_HOME")
    if splunk_home:
        try:
            handler = logging.handlers.RotatingFileHandler(
                os.path.join(splunk_home, "var", "log", "splunk",
                             "lookupops.log"),
                maxBytes=10485760, backupCount=5, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"))
            LOG.addHandler(handler)
        except OSError:
            pass


def _json_response(status, payload):
    return {"status": status,
            "payload": json.dumps(payload),
            "headers": {"Content-Type": "application/json",
                        "X-Content-Type-Options": "nosniff",
                        "Cache-Control": "no-store"}}


class LookupOpsHandler(PersistentServerConnectionApplication):
    """Narrow, capability-checked JSON API. No HTML is ever emitted."""

    def __init__(self, command_line, command_arg):
        super().__init__()

    # ------------------------------------------------------------ dispatch
    def handle(self, in_string):
        try:
            request = json.loads(in_string)
        except ValueError:
            return _json_response(400, {"error": "bad_request",
                                        "message": "Malformed request."})
        try:
            return self._route(request)
        except errors.LookupOpsError as exc:
            return _json_response(exc.http_status, exc.to_dict())
        except Exception:  # noqa: BLE001
            LOG.exception("Unhandled error")
            return _json_response(500, {
                "error": "internal_error",
                "message": "An internal error occurred. See lookupops.log."})

    @staticmethod
    def _session_key(request):
        session = request.get("session") or {}
        key = session.get("authtoken")
        if not key:
            raise errors.unauthorized()
        return key

    @staticmethod
    def _body(request):
        """Read the request body regardless of how splunkd delivered it.

        splunkd reliably populates the `form` field for form-urlencoded POSTs
        but does not consistently surface a raw JSON body in `payload` through
        Splunk Web's proxy. The UI therefore sends bodies as a single form
        field `payload` containing a JSON string; a raw `payload` (JSON string
        or already-parsed dict) is still accepted for direct API callers.
        """
        payload = request.get("payload")
        for pair in request.get("form") or []:
            if isinstance(pair, (list, tuple)) and len(pair) == 2 and \
                    pair[0] == "payload":
                payload = pair[1]
                break
        if payload in (None, ""):
            return {}
        if isinstance(payload, dict):
            return payload
        try:
            parsed = json.loads(payload)
        except ValueError:
            raise errors.bad_request("The request body must be JSON.")
        if not isinstance(parsed, dict):
            raise errors.bad_request("The request body must be a JSON object.")
        return parsed

    @staticmethod
    def _query(request):
        out = {}
        for pair in request.get("query") or []:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                out[pair[0]] = pair[1]
        return out

    def _route(self, request):
        method = (request.get("method") or "GET").upper()
        path = (request.get("path_info") or "").strip("/")
        parts = [p for p in path.split("/") if p]
        session_key = self._session_key(request)
        client = SplunkClient(session_key)
        api = Api(client, Limits())
        query = self._query(request)

        if method == "GET" and (not parts or parts[0] == "health"):
            return _json_response(200, api.health())
        if method == "GET" and parts[0] == "context":
            return _json_response(200, api.context())

        if parts[0] == "lookups":
            if method == "GET" and len(parts) == 1:
                return _json_response(200, api.list_lookups())
            if method == "GET" and len(parts) == 2 and parts[1] == "detail":
                return _json_response(200, api.lookup_detail(
                    query.get("kind", "csv"), query.get("app", ""),
                    query.get("name", "")))
            if method == "GET" and len(parts) == 2 and parts[1] == "dependencies":
                return _json_response(200, api.lookup_dependencies(
                    query.get("name", "")))

        if parts[0] == "policies":
            if method == "GET" and len(parts) == 1:
                return _json_response(200, api.list_policies())
            if method == "POST" and len(parts) == 1:
                return _json_response(200, api.save_policy(self._body(request)))
            if method == "DELETE" and len(parts) == 2:
                return _json_response(200, api.delete_policy(parts[1]))

        if parts[0] == "requests":
            if method == "POST" and len(parts) == 1:
                return _json_response(201, api.create_request(self._body(request)))
            if method == "GET" and len(parts) == 1:
                return _json_response(200, api.list_requests(
                    state=query.get("state"),
                    mine=query.get("mine") in ("1", "true"),
                    limit=query.get("limit", 200)))
            if len(parts) == 2 and method == "GET":
                return _json_response(200, api.get_request(parts[1]))
            if len(parts) == 3:
                rid, action = parts[1], parts[2]
                body = self._body(request) if method == "POST" else {}
                if method == "GET" and action == "diff":
                    return _json_response(200, api.get_diff(rid))
                if method == "GET" and action == "evidence":
                    return _json_response(200, api.evidence(rid))
                if method == "GET" and action == "report":
                    return _json_response(200, api.evidence_report(rid))
                if method == "GET" and action == "ai-reviews":
                    return _json_response(200, api.ai_reviews(rid))
                if method == "POST":
                    dispatch = {
                        "validate": lambda: api.validate_request(rid),
                        "revise": lambda: api.revise_request(rid, body),
                        "submit": lambda: api.submit_request(rid),
                        "ai-review": lambda: api.ai_review(rid, body),
                        "approve": lambda: api.approve_request(rid, body),
                        "reject": lambda: api.reject_request(rid, body),
                        "publish": lambda: api.publish_request(rid, body),
                        "rollback": lambda: api.rollback_request(rid, body),
                    }
                    if action in dispatch:
                        return _json_response(200, dispatch[action]())

        if parts[0] == "bundles":
            if method == "POST" and len(parts) == 2 and parts[1] == "export":
                return _json_response(200, api.export_request_bundle(
                    self._body(request)))
            if method == "POST" and len(parts) == 2 and parts[1] == "import":
                return _json_response(201, api.import_request_bundle(
                    self._body(request)))

        if parts[0] == "settings":
            if method == "GET" and len(parts) == 1:
                return _json_response(200, api.get_app_settings())
            if method == "POST" and len(parts) == 1:
                return _json_response(200, api.update_app_settings(
                    self._body(request)))
            if method == "POST" and len(parts) == 2 and parts[1] == "credential":
                return _json_response(200, api.set_ai_credential(
                    self._body(request)))

        if parts[0] == "ai" and method == "GET" and len(parts) == 2 \
                and parts[1] == "status":
            return _json_response(200, api.ai_status())

        raise errors.not_found("The endpoint", "unknown_endpoint")
