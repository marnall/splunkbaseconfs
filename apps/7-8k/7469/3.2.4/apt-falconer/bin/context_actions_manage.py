import json
import logging
import time
import urllib.parse
import hashlib

import splunk.persistconn.application as app
import splunk.rest as rest

logger = logging.getLogger('falconer_context_actions_manage')
logger.setLevel(logging.INFO)

APP_NAME = "apt-falconer"
COLLECTION = "falconer_contexts"


def _now_epoch():
    return int(time.time())


def _stable_hash(doc: dict) -> str:
    core = {k: doc.get(k, "") for k in ["enabled", "field", "group", "subgroup", "label", "order", "target", "url", "value_regex", "view"]}
    s = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _as_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


class ContextActionsManage(app.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(ContextActionsManage, self).__init__()

    def _list_to_dict(self, maybe_list):
        out = {}
        if isinstance(maybe_list, list):
            for item in maybe_list:
                if isinstance(item, dict) and "name" in item:
                    out[item["name"]] = item.get("value")
        return out

    def _parse_string_payload(self, s: str) -> dict:
        s = (s or "").strip()
        if not s:
            return {}
        try:
            val = json.loads(s)
            if isinstance(val, dict):
                return val
            if isinstance(val, list):
                return self._list_to_dict(val)
        except Exception:
            pass

        try:
            qs = urllib.parse.parse_qs(s, keep_blank_values=True)
            flat = {}
            for k, vals in qs.items():
                if vals:
                    flat[k] = urllib.parse.unquote_plus(vals[0])
            return flat
        except Exception:
            return {}

    def _unwrap_payload(self, raw_payload):
        if isinstance(raw_payload, list):
            raw_payload = self._list_to_dict(raw_payload)

        if isinstance(raw_payload, dict):
            inner = raw_payload.get("payload")
            if isinstance(inner, str) and inner.strip():
                return self._parse_string_payload(inner)
            return raw_payload

        if isinstance(raw_payload, str):
            return self._parse_string_payload(raw_payload)

        return {}

    def _parse_args(self, in_string):
        try:
            outer = json.loads(in_string or "{}")
        except Exception:
            outer = {}

        if isinstance(outer, list):
            outer = self._list_to_dict(outer)

        raw_payload = outer.get("payload")
        body = self._unwrap_payload(raw_payload)
        if isinstance(body, dict) and isinstance(body.get("payload"), str):
            body = self._parse_string_payload(body["payload"])

        return outer, body

    def _query_by_id(self, session_key, action_id):
        uri_base = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION}"
        query = json.dumps({"id": action_id})
        resp, content = rest.simpleRequest(
            uri_base,
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json", "count": 0, "query": query},
            raiseAllErrors=True,
        )
        rows = json.loads(content.decode("utf-8")) if hasattr(content, "decode") else json.loads(content or "[]")
        return rows if isinstance(rows, list) else []

    def _rank_doc(self, doc, action_id):
        return (
            _as_int(doc.get("user_modified"), 0),
            1 if (doc.get("_key") == action_id) else 0,
            _as_int(doc.get("updated_time"), 0),
            _as_int(doc.get("created_time"), 0),
        )

    def _pick_canonical(self, rows, action_id):
        if not rows:
            return None
        return sorted(rows, key=lambda d: self._rank_doc(d, action_id), reverse=True)[0]

    def _delete_by_key(self, session_key, key):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION}/{urllib.parse.quote(key)}"
        rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method="DELETE",
            raiseAllErrors=True,
        )

    def handle(self, in_string):
        """
        Expects (typical):
          { payload: "{ actions: [ {...}, {...} ] }" }

        Behavior:
        - Non-destructive by default: upsert by `_key = id`
        - Destructive replace is explicit only: { "replace_all": true }
        """
        try:
            outer, body = self._parse_args(in_string)

            session = outer.get("session")
            session_key = ""
            if isinstance(session, dict):
                session_key = session.get("authtoken") or session.get("sessionKey") or ""
            elif isinstance(session, str):
                session_key = session.replace("Splunk ", "").strip()

            if not session_key:
                return {
                    "payload": json.dumps({"status": "error", "error": "Missing session token"}),
                    "status": 401,
                    "headers": {"Content-Type": "application/json"},
                }

            # Explicit only (safe default)
            replace_all = bool(outer.get("replace_all") or body.get("replace_all"))

            if "actions" in outer and not body:
                body = outer

            actions = body.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            uri_base = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION}"

            # Optional destructive mode (explicit only)
            if replace_all:
                rest.simpleRequest(
                    uri_base,
                    sessionKey=session_key,
                    method="DELETE",
                    raiseAllErrors=True,
                )

            now = _now_epoch()
            inserted = 0
            updated = 0
            skipped = 0

            for a in actions:
                if not isinstance(a, dict):
                    continue

                action_id = (a.get("id") or "").strip()
                if not action_id:
                    skipped += 1
                    continue

                # Prepare doc
                doc = dict(a)
                doc["_key"] = action_id

                # Normalize key governance/meta for UI-managed docs
                doc.setdefault("created_time", now)
                doc["updated_time"] = now
                doc["updated_by"] = doc.get("updated_by") or "falconer_admin"

                doc["source"] = "falconer_ui"
                doc.setdefault("vendor_version", "")
                doc["app_managed"] = 0
                doc["user_modified"] = 1
                doc["content_hash"] = _stable_hash(doc)

                key_uri = f"{uri_base}/{urllib.parse.quote(action_id)}"
                existing_rows = self._query_by_id(session_key, action_id)
                canonical = self._pick_canonical(existing_rows, action_id)

                if canonical:
                    created_time = canonical.get("created_time", now)
                    doc["created_time"] = created_time

                    # Normalize on the canonical key = id going forward.
                    try:
                        rest.simpleRequest(
                            key_uri,
                            sessionKey=session_key,
                            method="GET",
                            getargs={"output_mode": "json"},
                            raiseAllErrors=True,
                        )
                        rest.simpleRequest(
                            key_uri,
                            sessionKey=session_key,
                            method="POST",
                            jsonargs=json.dumps(doc).encode("utf-8"),
                            raiseAllErrors=True,
                        )
                    except Exception:
                        rest.simpleRequest(
                            uri_base,
                            sessionKey=session_key,
                            method="POST",
                            jsonargs=json.dumps(doc).encode("utf-8"),
                            raiseAllErrors=True,
                        )

                    # Remove any legacy duplicates, including non-canonical keys.
                    for row in existing_rows:
                        row_key = (row.get("_key") or "").strip()
                        if row_key and row_key != action_id:
                            try:
                                self._delete_by_key(session_key, row_key)
                            except Exception:
                                logger.exception("Failed deleting legacy duplicate context row for id=%s key=%s", action_id, row_key)
                    updated += 1
                    continue

                rest.simpleRequest(
                    uri_base,
                    sessionKey=session_key,
                    method="POST",
                    jsonargs=json.dumps(doc).encode("utf-8"),
                    raiseAllErrors=True,
                )
                inserted += 1

            return {
                "payload": json.dumps({
                    "status": "ok",
                    "inserted": inserted,
                    "updated": updated,
                    "skipped": skipped,
                    "replace_all": replace_all
                }),
                "status": 200,
                "headers": {"Content-Type": "application/json"},
            }

        except Exception as e:
            logger.exception("Error managing context actions")
            return {
                "payload": json.dumps({"status": "error", "error": str(e)}),
                "status": 500,
                "headers": {"Content-Type": "application/json"},
            }
