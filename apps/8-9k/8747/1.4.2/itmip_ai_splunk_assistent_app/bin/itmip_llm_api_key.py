"""GET /services/itmip_llm/api_key — return the legacy centrally-stored
Anthropic API key (the v0.1 single-key path).

This endpoint exists for backwards compatibility: installs that ran v0.1
have the Anthropic key saved at realm=itmip_ai_splunk_assistent_app,
name=anthropic_api_key. New LLM configs (v0.2+) live in their own
storage/passwords entries keyed by the LLM config id and are fetched via
the /services/itmip_llm/llm_secret endpoint.

Reads via passSystemAuth=true so any authenticated Splunk user can use
the centrally-saved key without needing list_storage_passwords.
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
    LEGACY_PASSWORD_REALM,
    LEGACY_PASSWORD_NAME,
    err,
    is_admin,
    ok,
    system_token,
    user_token,
)


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

            # SECURITY: v0.1 returned the central Anthropic key to ANY
            # authenticated user, on the theory that the browser-side
            # Anthropic SDK needed it. In v0.2 the splunk_proxy call mode
            # removes that requirement — admins should migrate the
            # bootstrap config to splunk_proxy and stop calling this
            # endpoint. Until then, gate the read on admin-equivalent
            # roles (same audience that can read storage/passwords via
            # standard Splunk capabilities anyway).
            if not is_admin(args, rest):
                return err(
                    403,
                    "This endpoint is admin-only in v0.2+. "
                    "Promote the bootstrap LLM config from Settings → LLM "
                    "configurations, switch its call_mode to splunk_proxy, "
                    "and consumer calls will be served server-side without "
                    "sending the key to the browser.",
                )

            sys_token = system_token(args)
            if not sys_token:
                return err(
                    503,
                    "System auth token not provided. Verify restmap.conf has passSystemAuth=true.",
                )

            entry_path = (
                "/servicesNS/nobody/{app}/storage/passwords/"
                "{realm}%3A{name}%3A?output_mode=json"
            ).format(
                app=APP_NAME,
                realm=LEGACY_PASSWORD_REALM,
                name=LEGACY_PASSWORD_NAME,
            )

            try:
                response, content = rest.simpleRequest(
                    entry_path, sessionKey=sys_token, method="GET"
                )
            except Exception as exc:
                return err(502, "Could not query storage/passwords: %s" % exc)

            status_code = getattr(response, "status", 0)
            if status_code == 404:
                return err(
                    404,
                    "No central API key configured. An admin must save one in Settings.",
                )
            if status_code != 200:
                return err(502, "storage/passwords returned %s" % status_code)

            try:
                data = json.loads(content)
            except Exception:
                return err(502, "Bad JSON from storage/passwords.")

            entries = data.get("entry") or []
            if not entries:
                return err(404, "No central API key entry found.")

            api_key = (entries[0].get("content") or {}).get("clear_password") or ""
            if not api_key:
                return err(404, "Central API key entry has no value.")

            return ok({"api_key": api_key})
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
