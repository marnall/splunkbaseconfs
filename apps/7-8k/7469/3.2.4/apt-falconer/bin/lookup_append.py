# bin/lookup_append.py

import os
import json
import datetime
import uuid
import hashlib
from urllib.parse import parse_qs, unquote_plus

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME        = "apt-falconer"
COLLECTION_NAME = "falconer_signals"
DEBUG_ENABLED   = True

DEBUG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var",
    "log",
    "splunk",
    "falconer_lookup_debug.log",
)


def _now_epoch() -> int:
    return int(datetime.datetime.utcnow().timestamp())


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _first_non_empty(*values) -> str:
    for value in values:
        if value is None:
            continue
        s = str(value).strip()
        if s:
            return s
    return ""


def _request_user(args: dict, payload: dict = None) -> str:
    payload = payload or {}
    session = args.get("session") if isinstance(args, dict) else {}
    if not isinstance(session, dict):
        session = {}
    return _first_non_empty(
        payload.get("owner"),
        payload.get("assignee"),
        payload.get("assigned_to"),
        payload.get("updated_by"),
        payload.get("created_by"),
        args.get("user") if isinstance(args, dict) else "",
        args.get("username") if isinstance(args, dict) else "",
        args.get("userName") if isinstance(args, dict) else "",
        session.get("user"),
        session.get("username"),
        session.get("userName"),
    )


def _normalize_entity(entity_type: str, value: str) -> str:
    entity_type = (entity_type or "generic").strip().lower()
    value = (value or "").strip()
    if entity_type in ("ip", "domain", "hash", "email", "host", "user", "process"):
        return value.lower()
    return value


def _infer_entity_type(field: str, value: str) -> str:
    field = (field or "").strip().lower()
    value = (value or "").strip()

    if field in ("host", "hostname", "dest", "dvc_host", "ComputerName".lower()):
        return "host"
    if field in ("uri", "uri_path", "url", "path"):
        return "uri"
    if field in ("src", "src_ip", "dest_ip", "ip"):
        return "ip"
    if field in ("user", "src_user", "dest_user", "account_name"):
        return "user"
    if field in ("process", "process_name", "NewProcessName".lower()):
        return "process"
    if field in ("file_hash", "md5", "sha1", "sha256", "hash"):
        return "hash"

    import re
    if re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", value):
        return "ip"
    if re.fullmatch(r"[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64}", value):
        return "hash"
    if "@" in value:
        return "email"
    if value.startswith("/") or value.startswith("http://") or value.startswith("https://"):
        return "uri"
    if "." in value and " " not in value and "/" not in value:
        return "domain"
    return "generic"


def _stable_signal_key(entity_type: str, normalized_entity: str) -> str:
    base = f"{entity_type}|{normalized_entity}".encode("utf-8")
    return "signal:" + hashlib.sha256(base).hexdigest()[:24]


class LookupAppend(PersistentServerConnectionApplication):
    """
    /falconer/lookup_append
    """

    def __init__(self, command_line, command_arg):
        super(LookupAppend, self).__init__()

    # ------------- Helpers -------------

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [lookup_append] {msg}\n")
        except Exception:
            # best-effort only
            pass

    def _parse_args(self, in_string):
        """
        Parse the persistent handler input.

        For a jQuery call like:

            $.ajax({
              url: '/en-US/splunkd/__raw/falconer/lookup_append',
              type: 'POST',
              data: {
                payload: JSON.stringify(params),
                output_mode: 'json'
              }
            })

        Splunk typically provides `in_string` JSON like:

            {
              "method": "POST",
              "payload": "payload=%7B...%7D&output_mode=json",
              "session": { "authtoken": "..." },
              ...
            }

        We handle:
          - payload as dict
          - payload as raw JSON string
          - payload as URL-encoded query string containing an inner JSON 'payload'
        """
        try:
            args = json.loads(in_string) if in_string else {}
        except Exception as e:
            self.log(f"Failed to parse in_string as JSON: {e}")
            args = {}

        method = (args.get("method") or "GET").upper()
        raw_payload = args.get("payload")

        payload: dict = {}

        if isinstance(raw_payload, dict):
            # Already a dict
            payload = raw_payload

        elif isinstance(raw_payload, str):
            # 1) Try direct JSON
            tried_json = False
            try:
                payload = json.loads(raw_payload)
                tried_json = True
                self.log("Parsed raw_payload as JSON directly")
            except Exception:
                payload = {}
                tried_json = True

            # 2) If that didn't work, treat as query string (payload=...&output_mode=json)
            if not payload:
                try:
                    qs = parse_qs(raw_payload, keep_blank_values=True)
                    if "payload" in qs:
                        inner = qs["payload"][0]
                        inner = unquote_plus(inner)
                        try:
                            payload = json.loads(inner)
                            self.log("Parsed inner payload JSON from query-string")
                        except Exception as e2:
                            self.log(f"Failed to parse inner payload JSON: {e2}")
                            payload = {}
                    else:
                        # No nested 'payload', flatten the qs as a dict
                        flat = {}
                        for k, vals in qs.items():
                            if not vals:
                                continue
                            flat[k] = vals[0]
                        payload = flat
                        if flat:
                            self.log("Using flattened query-string as payload")
                except Exception as e:
                    self.log(f"Failed to parse raw_payload as query-string: {e}")
                    if not tried_json:
                        payload = {}

        else:
            # No payload key; last resort, treat args themselves as payload
            self.log("No explicit payload key; falling back to top-level args")
            payload = args

        return method, payload, args

    def _kv_collection_uri(self):
        return f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION_NAME}"

    def _kv_key_uri(self, key: str):
        return f"{self._kv_collection_uri()}/{key}"

    def _kv_create_with_key(self, session_key, key: str, doc: dict):
        uri = self._kv_collection_uri()
        body = dict(doc)
        body["_key"] = key

        resp, content = rest.simpleRequest(
            uri,
            method="POST",
            getargs={"output_mode": "json"},
            jsonargs=json.dumps(body).encode("utf-8"),
            raiseAllErrors=False,
            sessionKey=session_key,
        )
        return int(resp.get("status", 0) or 0), content

    def _kv_update_existing(self, session_key, key: str, doc: dict):
        resp, content = rest.simpleRequest(
            self._kv_key_uri(key),
            method="POST",
            getargs={"output_mode": "json"},
            jsonargs=json.dumps(doc).encode("utf-8"),
            raiseAllErrors=False,
            sessionKey=session_key,
        )
        return int(resp.get("status", 0) or 0), content

    def _kv_get_by_key(self, session_key, key: str):
        try:
            resp, content = rest.simpleRequest(
                self._kv_key_uri(key),
                method="GET",
                getargs={"output_mode": "json"},
                raiseAllErrors=False,
                sessionKey=session_key,
            )
        except Exception as e:
            if "404" in str(e):
                return None
            raise
        status = int(resp.get("status", 0) or 0)
        if status == 404 or status not in (200, 201) or not content:
            return None
        try:
            doc = json.loads(content.decode("utf-8"))
            return doc if isinstance(doc, dict) else None
        except Exception:
            return None

    def _kv_query(self, session_key, query: dict):
        resp, content = rest.simpleRequest(
            self._kv_collection_uri(),
            method="GET",
            getargs={"output_mode": "json", "query": json.dumps(query), "count": "0"},
            raiseAllErrors=False,
            sessionKey=session_key,
        )
        status = int(resp.get("status", 0) or 0)
        if status not in (200, 201) or not content:
            return []
        try:
            rows = json.loads(content.decode("utf-8"))
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    def _find_existing_signal(self, session_key, signal_key: str, entity_type: str, normalized_entity: str, entity_value: str):
        existing = self._kv_get_by_key(session_key, signal_key)
        if existing:
            return signal_key, existing

        candidates = self._kv_query(session_key, {"entity_type": entity_type, "normalized_entity": normalized_entity})
        if not candidates and entity_value:
            candidates = self._kv_query(session_key, {"entity_type": entity_type, "entity_value": entity_value})
        if not candidates:
            candidates = [
                row for row in self._kv_query(session_key, {"entity_type": entity_type})
                if _normalize_entity(entity_type, _first_non_empty(row.get("entity_value"), row.get("value"), row.get("signal"))) == normalized_entity
            ]

        for row in candidates:
            if row.get("hunt_id"):
                continue
            key = row.get("_key")
            if key:
                return key, row
        return signal_key, {}

    def _kv_upsert(self, session_key, key: str, doc: dict, existing: dict):
        if existing:
            return self._kv_update_existing(session_key, key, doc)

        status, content = self._kv_create_with_key(session_key, key, doc)
        if status in (200, 201):
            return status, content
        if status == 409:
            return self._kv_update_existing(session_key, key, doc)
        return status, content

    # ------------- Main handler -------------

    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)
            self.log(f"📥 /falconer/lookup_append method={method} payload={payload}")

            if method != "POST":
                return {
                    "payload": {"status": "error", "error": "Only POST supported"},
                    "status": 405,
                }

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                raise ValueError("Missing sessionKey/authtoken")

            # --- Required core field ---
            signal = payload.get("signal")

            # Fallback: if JS didn't explicitly send "signal", use "value"
            if not signal:
                fallback = payload.get("value")
                self.log(f"No explicit 'signal' provided, using fallback value={fallback!r}")
                signal = fallback

            if not signal:
                raise ValueError("Missing required field: signal")

            epoch = _now_epoch()

            # --- Description & context fields ---
            description = payload.get("description")
            view        = (payload.get("view") or "").strip()
            field       = (payload.get("field") or "").strip()
            page_url    = (payload.get("page_url") or "").strip()

            if not description:
                sig = str(signal)
                parts = []

                if field and sig:
                    parts.append(f"Added {field}={sig}")
                elif sig:
                    parts.append(f"Added {sig}")
                elif field:
                    parts.append(f"Added {field}")

                if view:
                    parts.append(f"from {view}")
                if page_url:
                    parts.append(f"at {page_url}")

                if not parts:
                    parts.append("Added via APT Falconer UI")

                description = " ".join(parts)

            entity_type = (
                payload.get("entity_type")
                or payload.get("type")
                or _infer_entity_type(field, signal)
            )
            entity_type = str(entity_type).strip().lower() or "generic"
            inferred_type = _infer_entity_type(field, signal)
            if entity_type in ("url", "uri") and inferred_type in ("host", "domain"):
                entity_type = inferred_type
            entity_value = _first_non_empty(payload.get("entity_value"), signal)
            normalized_entity = _normalize_entity(entity_type, entity_value)
            signal_key = _stable_signal_key(entity_type, normalized_entity)
            existing_key, existing_doc = self._find_existing_signal(
                session_key,
                signal_key,
                entity_type,
                normalized_entity,
                entity_value,
            )

            actor = _first_non_empty(_request_user(args, payload), "lookup_append")
            created_by = _first_non_empty(payload.get("created_by"), actor)
            updated_by = _first_non_empty(payload.get("updated_by"), actor)

            doc = {k: v for k, v in existing_doc.items() if k != "_key"}
            seen_count = _safe_int(existing_doc.get("seen_count"), 0) + 1
            doc.update({
                "signal": signal,
                "signal_id": _first_non_empty(existing_doc.get("signal_id"), payload.get("signal_id"), str(uuid.uuid4())),
                "owner": _first_non_empty(payload.get("signal_owner"), payload.get("owner"), existing_doc.get("owner"), actor),
                "entity_type": entity_type,
                "entity_value": entity_value,
                "normalized_entity": normalized_entity,
                "field": payload.get("field") or payload.get("entity_type") or payload.get("type") or "entity",
                "value": payload.get("value") or signal,
                "signal_source": (
                    payload.get("signal_source")
                    or payload.get("category")
                    or "manual"
                ),
                "signal_type": payload.get("signal_type") or "manual",
                "category": (
                    payload.get("category")
                    or payload.get("signal_source")
                    or "manual"
                ),
                "status": _first_non_empty(existing_doc.get("status"), payload.get("status"), "new"),
                "description": _first_non_empty(existing_doc.get("description"), description),
                "latest_description": description,
                "page_url": page_url,
                "created_by": _first_non_empty(existing_doc.get("created_by"), created_by),
                "updated_by": updated_by,
                "created_time": _safe_int(existing_doc.get("created_time"), epoch),
                "updated_time": epoch,
                "first_seen": _safe_int(existing_doc.get("first_seen"), epoch),
                "last_seen": epoch,
                "seen_count": seen_count,
                "content_hash": existing_key,
            })

            status_code, content = self._kv_upsert(session_key, existing_key, doc, existing_doc)

            self.log(f"KV UPSERT status={status_code} key={existing_key} content={content[:500] if content else b''}")

            if status_code not in (200, 201, 204):
                return {
                    "payload": {
                        "status": "error",
                        "error": f"KV upsert failed (HTTP {status_code})",
                    },
                    "status": status_code,
                }

            action = "updated" if existing_doc else "created"
            return {
                "payload": {
                    "status": "success",
                    "action": action,
                    "idempotent": bool(existing_doc),
                    "signal": signal,
                    "signal_key": existing_key,
                    "signal_id": doc.get("signal_id"),
                    "entity_type": entity_type,
                    "entity_value": entity_value,
                    "normalized_entity": normalized_entity,
                    "seen_count": seen_count,
                    "doc": doc,
                },
                "status": 200,
            }

        except Exception as e:
            self.log(f"❌ Exception in LookupAppend: {e}")
            return {
                "payload": {"status": "error", "error": str(e)},
                "status": 500,
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
