"""GET /services/itmip_llm/skills — return all itmip_ai_skills entries.

v0.9.6 — Skills layer. Mirrors itmip_llm_use_cases.py: reads
/servicesNS/nobody/<app>/storage/collections/data/itmip_ai_skills with
the system auth token (passSystemAuth=true) so non-admin Splunk users
can list skills without needing the list_storage_collections capability.
The dispatcher needs this for `splunk_get_use_case_template_prompt` to
resolve a template's `includes_skills` into skill bodies at fetch time.

Writes (POST/DELETE) go through the standard KVStore endpoint and are
admin-only via the collection ACL in metadata/default.meta.
"""

import json
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import (  # noqa: E402
    APP_NAME,
    err,
    ok,
    system_token,
    user_token,
)

COLLECTION = "itmip_ai_skills"


def _query_collection(sys_token):
    """List itmip_ai_skills rows. Treats 404 as an empty collection —
    KVStore creates a collection lazily on first write, so a fresh
    install where no skill has been seeded yet (and the auto-seed
    pass hasn't run) gets 404 here. Returning [] makes the dispatcher
    transparently fall back to the in-bundle seed catalogue. Splunk's
    `splunk.rest.simpleRequest` raises `splunk.RESTException` on
    non-2xx by default, so we also catch + parse the embedded status
    code (the response message is of the form `[HTTP <code>] <url>`).
    """
    import re
    url = (
        "/servicesNS/nobody/{app}/storage/collections/data/{collection}"
        "?output_mode=json"
    ).format(app=APP_NAME, collection=COLLECTION)
    try:
        response, content = rest.simpleRequest(url, sessionKey=sys_token, method="GET")
        status_code = getattr(response, "status", 0)
    except Exception as exc:
        m = re.search(r"\[HTTP\s+(\d+)\]", str(exc))
        if m:
            status_code = int(m.group(1))
            content = None
        else:
            raise
    if status_code == 404:
        return []
    if status_code != 200:
        raise RuntimeError("KVStore returned %s" % status_code)
    data = json.loads(content)
    return data if isinstance(data, list) else []


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if method != "GET":
                return err(405, "Only GET is supported on this endpoint.")

            if not user_token(args):
                return err(401, "Not authenticated.")

            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")

            try:
                items = _query_collection(sys_token)
            except Exception as exc:
                return err(502, "Could not query KVStore: %s" % exc)

            return ok({"items": items})
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
