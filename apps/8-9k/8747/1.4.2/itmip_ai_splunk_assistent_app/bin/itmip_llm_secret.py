"""GET/POST/DELETE /services/itmip_llm/secret — per-LLM-config secret store.

Each LLM configuration owns its own API key / Access token. We store the
secret in Splunk's storage/passwords under realm=itmip_llm_assistent_app,
name=<llm_config_id>. The endpoint uses passSystemAuth so any authenticated
user can READ a central-scoped secret (matching the v0.1 central-key
pattern), while WRITES require admin via the URL namespace + ACL.

GET  ?name=<id>            -> { value: "..." } or 404 if not present
POST  body={name, value}   -> { ok: true } (admin only)
DELETE ?name=<id>          -> { ok: true } (admin only)
"""

import json
import os
import sys
from urllib.parse import urlencode

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
    LLM_PASSWORD_REALM,
    err,
    is_admin,
    is_user_allowed_for_llm_config,
    load_llm_config,
    ok,
    rate_limit_check,
    system_token,
    user_name,
    user_token,
)


def _parse_query(args):
    qs = args.get("query") or []
    if isinstance(qs, list):
        return dict(qs)
    return dict(qs.items()) if hasattr(qs, "items") else {}


def _safe_name(raw):
    return "".join(c for c in (raw or "") if c.isalnum() or c in "._-")


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if not user_token(args):
                return err(401, "Not authenticated.")

            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")

            # SECURITY: GET is permitted to all authenticated users so they
            # can read the secret of an LLM config that's been granted to
            # them via Org/BU/extra_roles/extra_users — the front-end
            # already filters configs server-side. POST and DELETE are
            # write operations that must be gated on admin role; the v0.1
            # design relied on `passSystemAuth + KVStore ACL` for this,
            # but storage/passwords is NOT a KVStore collection so its ACL
            # was never enforcing admin-write. Check explicitly here.
            if method in ("POST", "DELETE"):
                if not is_admin(args, rest):
                    return err(
                        403,
                        "Only Splunk admins can write or delete LLM secrets.",
                    )

            query = _parse_query(args)
            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw) if payload_raw else {}
            except Exception:
                payload = {}

            name_raw = query.get("name") or payload.get("name") or ""
            name = _safe_name(name_raw)
            if not name:
                return err(400, "'name' is required and must be alphanumeric/._-.")

            # SECURITY: GET previously returned the secret for any
            # LLM-config name to any authenticated user — a non-admin
            # could `| rest /services/itmip_llm/secret?name=<known>` and
            # exfiltrate someone else's key. Require either admin, or
            # that the user is explicitly allowed for the LLM config the
            # secret belongs to. Rate-limit per user to slow probing.
            if method == "GET":
                if not rate_limit_check("secret_get", user_name(args), 30):
                    return err(429, "Too many secret-read requests; slow down.")
                if not is_admin(args, rest):
                    cfg = load_llm_config(sys_token, name, rest)
                    if not cfg:
                        return err(403, "Refused.")
                    if not is_user_allowed_for_llm_config(args, rest, cfg):
                        return err(
                            403,
                            "You aren't authorised to read this LLM config's secret.",
                        )

            entry_path = (
                "/servicesNS/nobody/{app}/storage/passwords/"
                "{realm}%3A{name}%3A?output_mode=json"
            ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)

            if method == "GET":
                # A missing secret is a normal state (e.g. the bootstrap
                # Anthropic config that lives in TS and uses the legacy
                # v0.1 key path). Return 200 with an empty value rather
                # than 404 so the browser console stays clean — the
                # front-end already treats empty value as "fall through
                # to the legacy api_key endpoint".
                try:
                    response, content = rest.simpleRequest(
                        entry_path, sessionKey=sys_token, method="GET"
                    )
                except Exception as exc:
                    msg = str(exc)
                    if "[HTTP 404]" in msg or "HTTP 404" in msg:
                        return ok({"name": name, "value": "", "found": False})
                    return err(502, "Could not query storage/passwords: %s" % exc)
                status = getattr(response, "status", 0)
                if status == 404:
                    return ok({"name": name, "value": "", "found": False})
                if status != 200:
                    return err(502, "storage/passwords returned %s" % status)
                try:
                    data = json.loads(content)
                except Exception:
                    return err(502, "Bad JSON from storage/passwords.")
                entries = data.get("entry") or []
                value = ""
                if entries:
                    value = (entries[0].get("content") or {}).get("clear_password") or ""
                if not value:
                    return ok({"name": name, "value": "", "found": False})
                return ok({"name": name, "value": value, "found": True})

            if method == "POST":
                value = payload.get("value") or ""
                if not value:
                    return err(400, "'value' is required.")
                # Try update first.
                update_path = (
                    "/servicesNS/nobody/{app}/storage/passwords/"
                    "{realm}%3A{name}%3A"
                ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)
                try:
                    resp, _content = rest.simpleRequest(
                        update_path,
                        sessionKey=sys_token,
                        method="POST",
                        postargs={"password": value},
                    )
                    if getattr(resp, "status", 0) in (200, 201):
                        return ok({"ok": True, "name": name, "mode": "updated"})
                except Exception:
                    pass
                # Fall through to create.
                create_path = "/servicesNS/nobody/{app}/storage/passwords".format(
                    app=APP_NAME
                )
                try:
                    resp, content = rest.simpleRequest(
                        create_path,
                        sessionKey=sys_token,
                        method="POST",
                        postargs={
                            "name": name,
                            "realm": LLM_PASSWORD_REALM,
                            "password": value,
                        },
                    )
                    status = getattr(resp, "status", 0)
                    if status in (200, 201):
                        return ok({"ok": True, "name": name, "mode": "created"})
                    return err(502, "storage/passwords create returned %s: %s" % (status, (content or "")[:200]))
                except Exception as exc:
                    return err(502, "Could not create secret: %s" % exc)

            if method == "DELETE":
                delete_path = (
                    "/servicesNS/nobody/{app}/storage/passwords/"
                    "{realm}%3A{name}%3A"
                ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)
                try:
                    resp, _content = rest.simpleRequest(
                        delete_path, sessionKey=sys_token, method="DELETE"
                    )
                    status = getattr(resp, "status", 0)
                    if status in (200, 404):
                        return ok({"ok": True, "name": name})
                    return err(502, "storage/passwords delete returned %s" % status)
                except Exception as exc:
                    return err(502, "Could not delete secret: %s" % exc)

            return err(405, "Only GET/POST/DELETE supported.")
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
