"""GET/POST/DELETE /services/itmip_llm/history — per-user persistent history.

Records live in KVStore collection itmip_user_history. Each user can read
and write their own records via passSystemAuth; the ACL on the collection
allows owner-scoped read but the persistent handler enforces per-user
isolation explicitly here (we filter by `user` field server-side).

GET                       -> { items: [...] }  (the calling user's only)
POST  body=<entry json>   -> { ok, _key }       (insert)
POST  body={_key, ...}    -> { ok, _key }       (upsert when _key present)
DELETE ?key=<_key>        -> { ok }
DELETE ?all=true          -> deletes every entry for the calling user
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
    err,
    ok,
    system_token,
    user_name,
    user_token,
)
from itmip_llm_kvstore_changelog import emit_change  # noqa: E402

COLLECTION = "itmip_user_history"


def _parse_query(args):
    qs = args.get("query") or []
    if isinstance(qs, list):
        return dict(qs)
    return dict(qs.items()) if hasattr(qs, "items") else {}


def _collection_url(rest_path=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{rest}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=COLLECTION, rest=rest_path)


def _safe_key(raw):
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

            sys_token = system_token(args) or user_token(args)
            user = user_name(args)
            query = _parse_query(args)

            if method == "GET":
                try:
                    resp, content = rest.simpleRequest(
                        _collection_url(), sessionKey=sys_token, method="GET"
                    )
                except Exception as exc:
                    return err(502, "KVStore read failed: %s" % exc)
                status = getattr(resp, "status", 0)
                if status == 404:
                    return ok({"items": []})
                if status != 200:
                    return err(502, "KVStore returned %s" % status)
                try:
                    data = json.loads(content)
                except Exception:
                    return err(502, "Bad JSON from KVStore.")
                items = data if isinstance(data, list) else []
                # Server-side filter: only this user's rows.
                filtered = [i for i in items if i.get("user") == user]
                return ok({"items": filtered})

            if method == "POST":
                payload_raw = args.get("payload") or "{}"
                try:
                    entry = json.loads(payload_raw)
                except Exception:
                    return err(400, "Invalid JSON payload.")
                entry["user"] = user  # force ownership
                key = entry.pop("_key", None)
                # SECURITY: when the caller supplies a _key (upsert), we
                # MUST verify the existing row at that _key is owned by
                # the same Splunk user. Otherwise user "alice" could
                # POST {_key: "bobs-row-id"} and overwrite Bob's history.
                if key:
                    safe_key = _safe_key(key)
                    if not safe_key:
                        return err(400, "Invalid _key.")
                    get_url = _collection_url("/{k}".format(k=safe_key))
                    try:
                        resp_g, content_g = rest.simpleRequest(
                            get_url, sessionKey=sys_token, method="GET"
                        )
                        status_g = getattr(resp_g, "status", 0)
                        if status_g == 200:
                            existing = json.loads(content_g)
                            if (
                                isinstance(existing, dict)
                                and existing.get("user")
                                and existing["user"] != user
                            ):
                                return err(
                                    403,
                                    "Refused: _key is owned by another user.",
                                )
                        # status 404 = no existing row, OK to insert at this key
                    except Exception:
                        pass
                    key = safe_key
                url = _collection_url("/{k}".format(k=key)) if key else _collection_url()
                try:
                    resp, content = rest.simpleRequest(
                        url,
                        sessionKey=sys_token,
                        method="POST",
                        jsonargs=json.dumps(entry),
                    )
                except Exception as exc:
                    return err(502, "KVStore write failed: %s" % exc)
                status = getattr(resp, "status", 0)
                if status not in (200, 201):
                    return err(502, "KVStore POST returned %s: %s" % (status, (content or "")[:200]))
                try:
                    out = json.loads(content)
                    new_key = out.get("_key") or key or ""
                except Exception:
                    new_key = key or ""
                emit_change(
                    sys_token, COLLECTION,
                    op="update" if key else "create",
                    key=new_key, before=None, after=entry, user=user,
                )
                return ok({"ok": True, "_key": new_key})

            if method == "DELETE":
                if (query.get("all") or "").lower() == "true":
                    # Bulk delete via KVStore query string {user: <user>}.
                    # We urlencode() the params so a username containing
                    # unusual characters can't corrupt the URL — and we
                    # use a single format step (not a chained format()+%
                    # which corrupted the URL when the encoded payload
                    # contained a literal `%`).
                    base = (
                        "/servicesNS/nobody/{app}/storage/collections/data/{coll}"
                    ).format(app=APP_NAME, coll=COLLECTION)
                    qs = urlencode(
                        {"query": json.dumps({"user": user}), "output_mode": "json"}
                    )
                    url = base + "?" + qs
                    try:
                        resp, _content = rest.simpleRequest(
                            url, sessionKey=sys_token, method="DELETE"
                        )
                    except Exception as exc:
                        return err(502, "Bulk delete failed: %s" % exc)
                    status = getattr(resp, "status", 0)
                    if status in (200, 404):
                        # Best-effort change-log marker for the bulk wipe.
                        emit_change(
                            sys_token, COLLECTION, op="delete", key="*",
                            before=None,
                            after={"_bulk": True, "filter": {"user": user}},
                            user=user,
                        )
                        return ok({"ok": True})
                    return err(502, "Bulk delete returned %s" % status)

                raw_key = query.get("key") or ""
                key = _safe_key(raw_key)
                if not key:
                    return err(400, "'key' is required.")
                url = _collection_url("/{k}".format(k=key))
                try:
                    resp, _content = rest.simpleRequest(
                        url, sessionKey=sys_token, method="DELETE"
                    )
                except Exception as exc:
                    return err(502, "Delete failed: %s" % exc)
                status = getattr(resp, "status", 0)
                if status in (200, 404):
                    emit_change(
                        sys_token, COLLECTION, op="delete", key=key,
                        before=None, after=None, user=user,
                    )
                    return ok({"ok": True})
                return err(502, "Delete returned %s" % status)

            return err(405, "Only GET/POST/DELETE supported.")
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
