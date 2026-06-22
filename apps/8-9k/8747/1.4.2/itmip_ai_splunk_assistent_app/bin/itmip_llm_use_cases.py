"""GET /services/itmip_llm/use_cases — return all use-case templates.

Reads /servicesNS/nobody/<app>/storage/collections/data/itmip_ai_use_cases
with the system auth token (passSystemAuth=true) so non-admin Splunk users
can list templates without needing the list_storage_collections capability.

Falls back to the legacy itmip_claude_use_cases collection when the new
collection is empty AND legacy data exists — covers the window between
install and the first call to /itmip_llm/setup.

Writes (POST/DELETE) still go through the standard KVStore endpoint which
enforces admin-only via the collection ACL in metadata/default.meta.
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
from itmip_llm_license import effective_tier  # noqa: E402
from itmip_llm_license_tier import resolve_capabilities  # noqa: E402

COLLECTION = "itmip_ai_use_cases"
LEGACY_COLLECTION = "itmip_claude_use_cases"

# v1.4.1 — per-feature licensing. When a template row carries a
# `required_capability` the EFFECTIVE tier does not unlock, the row stays
# LISTED (name + short_description so the UI can grey it with an upsell) but its
# prompt_text / question_text are replaced with a refusal marker. This is the
# SERVER-AUTHORITATIVE gate (D2): a crafted REST call cannot pull the locked
# prompt because the strip happens here, not in the frontend. Forward-
# compatible: rows without the field are untouched.
# Spec: instructions/FEATURE_LICENSING_SPEC.md


def _gate_locked_prompts(items, sys_token):
    """Strip prompt bodies from templates the current license can't unlock.
    Fail-open ONLY on resolution error would leak paid prompts, so fail-CLOSED:
    any error collapses to the personal tier (most restrictive)."""
    try:
        caps = resolve_capabilities(effective_tier(sys_token))
    except Exception:
        caps = resolve_capabilities("personal")
    gated = []
    for row in items:
        if not isinstance(row, dict):
            gated.append(row)
            continue
        req = (row.get("required_capability") or "").strip()
        if req and not caps.get(req, False):
            row = dict(row)
            row["locked"] = True
            row["locked_capability"] = req
            row["prompt_text"] = (
                "This template requires a higher license tier "
                "(capability: %s). Activate a suitable license in the License "
                "tab to use it." % req
            )
            row["question_text"] = ""
        gated.append(row)
    return gated


def _query_collection(sys_token, collection):
    url = (
        "/servicesNS/nobody/{app}/storage/collections/data/{collection}"
        "?output_mode=json"
    ).format(app=APP_NAME, collection=collection)
    response, content = rest.simpleRequest(url, sessionKey=sys_token, method="GET")
    status_code = getattr(response, "status", 0)
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
                items = _query_collection(sys_token, COLLECTION)
                if not items:
                    # The new collection is empty — try the legacy one so
                    # users on a pre-migration install still see templates.
                    try:
                        items = _query_collection(sys_token, LEGACY_COLLECTION)
                    except Exception:
                        items = []
            except Exception as exc:
                return err(502, "Could not query KVStore: %s" % exc)

            items = _gate_locked_prompts(items, sys_token)
            return ok({"items": items})
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
