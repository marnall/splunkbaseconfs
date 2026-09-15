#!/usr/bin/env python3
"""Federal AI Agent Assurance persistent REST handler.

Routes /services/faaa/* to the Api layer. Authentication comes from the
Splunk session splunkd already validated (requireAuthentication=true);
authorization is re-derived server-side for every request. JSON only;
stable error codes; request IDs on every response; no stack traces, paths,
or secrets in responses or logs.
"""
import json
import logging
import logging.handlers
import os
import sys
import uuid

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402

from faaa_lib import errors  # noqa: E402
from faaa_lib.api import Api  # noqa: E402
from faaa_lib.limits import Limits  # noqa: E402
from faaa_lib.splunk_client import SplunkClient  # noqa: E402

LOG = logging.getLogger("faaa")
if not LOG.handlers:
    LOG.setLevel(logging.INFO)
    _home = os.environ.get("SPLUNK_HOME")
    if _home:
        try:
            _h = logging.handlers.RotatingFileHandler(
                os.path.join(_home, "var", "log", "splunk", "faaa.log"),
                maxBytes=10485760, backupCount=5, encoding="utf-8")
            _h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"))
            LOG.addHandler(_h)
        except OSError:
            pass


def _json_response(status, payload):
    return {"status": status,
            "payload": json.dumps(payload),
            "headers": {"Content-Type": "application/json",
                        "X-Content-Type-Options": "nosniff",
                        "Cache-Control": "no-store"}}


class AgentAssuranceHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(AgentAssuranceHandler, self).__init__()

    def handle(self, in_string):
        request_id = "req-" + uuid.uuid4().hex[:16]
        try:
            request = json.loads(in_string)
        except ValueError:
            return _json_response(400, {"error": "bad_request",
                                        "message": "Malformed request.",
                                        "request_id": request_id})
        try:
            return self._route(request, request_id)
        except errors.LookupOpsError as exc:
            payload = exc.to_dict()
            payload["request_id"] = request_id
            LOG.info("request_id=%s error=%s status=%d", request_id,
                     exc.code, exc.http_status)
            return _json_response(exc.http_status, payload)
        except Exception:  # noqa: BLE001
            LOG.exception("request_id=%s unhandled error", request_id)
            return _json_response(500, {
                "error": "internal_error",
                "message": "An internal error occurred. See faaa.log.",
                "request_id": request_id})

    @staticmethod
    def _session_key(request):
        key = (request.get("session") or {}).get("authtoken")
        if not key:
            raise errors.unauthorized()
        return key

    @staticmethod
    def _body(request, limits):
        """Read the request body regardless of how splunkd delivered it.

        splunkd reliably populates the `form` field for form-urlencoded
        POSTs but does not consistently surface a raw JSON body in `payload`
        through Splunk Web's proxy. The UI therefore sends bodies as a single
        form field `payload` containing a JSON string; we also accept a raw
        `payload` (JSON string or already-parsed dict) for direct API callers.
        """
        raw = request.get("payload")
        # Prefer a form field named 'payload' when present.
        for pair in request.get("form") or []:
            if isinstance(pair, (list, tuple)) and len(pair) == 2 and \
                    pair[0] == "payload":
                raw = pair[1]
                break
        if raw in (None, ""):
            return {}
        if isinstance(raw, dict):
            parsed = raw
        else:
            if isinstance(raw, str) and len(raw) > limits.max_body_bytes:
                raise errors.payload_too_large(
                    "The request body exceeds the configured limit.")
            try:
                parsed = json.loads(raw)
            except ValueError:
                raise errors.bad_request("The request body must be JSON.")
        if not isinstance(parsed, dict):
            raise errors.bad_request("The request body must be a JSON "
                                     "object.")
        from faaa_lib.validate import check_depth
        check_depth(parsed, limits.max_json_depth)
        return parsed

    @staticmethod
    def _query(request):
        out = {}
        for pair in request.get("query") or []:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                out[pair[0]] = pair[1]
        return out

    def _route(self, request, request_id):
        method = (request.get("method") or "GET").upper()
        path = (request.get("path_info") or "").strip("/")
        parts = [p for p in path.split("/") if p]
        limits = Limits()
        client = SplunkClient(self._session_key(request))
        api = Api(client, limits, request_id=request_id)
        query = self._query(request)
        body = self._body(request, limits) if method in ("POST", "DELETE") \
            else {}

        def ok(payload, status=200):
            return _json_response(status, payload)

        if method == "GET" and (not parts or parts[0] == "health"):
            return ok(api.health())
        if method == "GET" and parts[0] == "context":
            return ok(api.context())

        if parts[0] == "agents":
            if method == "GET" and len(parts) == 1:
                return ok(api.list_agents(
                    page=query.get("page", 0),
                    page_size=query.get("page_size"),
                    include_archived=query.get("include_archived") == "1"))
            if method == "POST" and len(parts) == 1:
                return ok(api.register_agent(body), 201)
            if method == "POST" and len(parts) == 3 and parts[2] == "archive":
                return ok(api.archive_agent(parts[1], body))

        if parts[0] == "releases":
            if method == "GET" and len(parts) == 1:
                return ok(api.list_releases(
                    state=query.get("state"), agent_id=query.get("agent_id"),
                    page=query.get("page", 0),
                    page_size=query.get("page_size")))
            if method == "POST" and len(parts) == 1:
                return ok(api.create_release(body), 201)
            if len(parts) == 2 and method == "GET":
                return ok(api.get_release(parts[1]))
            if len(parts) == 3:
                rid, action = parts[1], parts[2]
                if method == "GET":
                    gets = {"diff": lambda: api.diff_release(rid),
                            "waivers": lambda: api.list_waivers(rid)}
                    if action in gets:
                        return ok(gets[action]())
                if method == "POST":
                    posts = {
                        "manifest": lambda: api.update_draft_manifest(rid, body),
                        "evaluate": lambda: api.evaluate_release(rid, body),
                        "tevv": lambda: api.import_and_evaluate(rid, body),
                        "submit": lambda: api.submit(rid, body),
                        "record-tests": lambda: api.record_tests(rid, body),
                        "review": lambda: api.review(rid, body),
                        "reopen": lambda: api.reopen(rid, body),
                        "accept-risk": lambda: api.accept_risk(rid, body),
                        "authorize": lambda: api.authorize(rid, body),
                        "suspend": lambda: api.suspend(rid, body),
                        "reinstate": lambda: api.reinstate(rid, body),
                        "revoke": lambda: api.revoke(rid, body),
                        "waiver": lambda: api.request_waiver(rid, body),
                        "attest": lambda: api.attest_observation(rid, body),
                        "export": lambda: api.export_evidence(rid, body),
                        "ai-review": lambda: api.ai_review(rid, body),
                    }
                    if action in posts:
                        return ok(posts[action]())

        if parts[0] == "policies":
            if method == "GET" and len(parts) == 1:
                return ok(api.list_policies())
            if method == "POST" and len(parts) == 1:
                return ok(api.save_policy(body), 201)

        if parts[0] == "test-suites":
            if method == "GET" and len(parts) == 1:
                return ok(api.list_test_suites())
            if method == "POST" and len(parts) == 1:
                return ok(api.save_test_suite(body), 201)

        if parts[0] == "waivers" and len(parts) == 3 and \
                parts[2] == "decide" and method == "POST":
            return ok(api.decide_waiver(parts[1], body))

        if parts[0] == "observations" and method == "POST" and \
                len(parts) == 1:
            return ok(api.import_observation(body), 201)

        if parts[0] == "dependencies":
            if method == "POST" and len(parts) == 2 and \
                    parts[1] == "import-lookupops":
                return ok(api.import_lookupops_evidence(body), 201)
            if method == "POST" and len(parts) == 2 and \
                    parts[1] == "report-change":
                return ok(api.report_dependency_change(body))

        if parts[0] == "evidence":
            if method == "POST" and len(parts) == 2 and parts[1] == "verify":
                return ok(api.verify_evidence(body))
            if method == "POST" and len(parts) == 2 and parts[1] == "import":
                return ok(api.import_evidence(body), 201)

        if parts[0] == "audit" and method == "GET":
            if len(parts) == 2 and parts[1] == "verify":
                return ok(api.verify_audit(query.get("chain_id")))

        if parts[0] == "maintenance" and method == "POST" and \
                len(parts) == 2 and parts[1] == "sweep-expirations":
            return ok(api.sweep_expirations())

        if parts[0] == "settings":
            if method == "GET" and len(parts) == 1:
                return ok(api.get_app_settings())
            if method == "POST" and len(parts) == 1:
                return ok(api.update_app_settings(body))
            if method == "POST" and len(parts) == 2 and \
                    parts[1] == "credential":
                return ok(api.set_ai_credential(body))

        if parts[0] == "ai" and method == "GET" and len(parts) == 2 and \
                parts[1] == "status":
            return ok(api.ai_status())

        if parts[0] == "admin" and method == "POST" and len(parts) == 2:
            if parts[1] == "load-samples":
                return ok(api.load_samples(body))
            if parts[1] == "self-test":
                return ok(api.self_test(body))

        raise errors.not_found("The endpoint", "unknown_endpoint")
