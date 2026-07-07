# bin/hunt_signal_add.py
import os
import json
import uuid
import hashlib
import datetime
from urllib.parse import parse_qs, unquote_plus

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME = "apt-falconer"
HUNTS_COLLECTION = "falconer_hunts"
SIGNALS_COLLECTION = "falconer_signals"

DEBUG_ENABLED = True
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
    entity_type = (entity_type or "unknown").strip().lower()
    value = (value or "").strip()
    if entity_type in ("ip", "domain", "hash", "email", "host", "user", "process"):
        return value.lower()
    return value


def _stable_signal_key(hunt_id: str, entity_type: str, entity_value: str) -> str:
    """
    Deterministic KV _key so "add same entity to same hunt" is idempotent.
    """
    normalized_entity = _normalize_entity(entity_type, entity_value)
    base = f"{hunt_id}|{entity_type}|{normalized_entity}".encode("utf-8")
    h = hashlib.sha256(base).hexdigest()
    return f"hunt_sig:{hunt_id}:{h[:16]}"


def _infer_entity_type(field: str, value: str) -> str:
    f = (field or "").lower().strip()
    v = (value or "").strip()

    if not v:
        return "unknown"

    # field hints
    if f in ("user", "src_user", "dest_user", "account", "account_name", "identity", "user_id"):
        return "user"
    if f in ("src", "dest", "src_ip", "dest_ip", "ip"):
        # may still become "domain/other" if value isn't an IP, but keep simple
        pass
    if f in ("hash", "md5", "sha1", "sha256", "file_hash"):
        return "hash"
    if f in ("url", "uri", "uri_path", "path"):
        return "uri"

    # value hints
    import re
    ipv4 = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    ipv6 = re.compile(r"^(?:(?:[A-Fa-f0-9]*)?:){1,7}[A-Fa-f0-9]*$")
    if ipv4.match(v) or ipv6.match(v):
        return "ip"

    if "@" in v:
        return "email"

    if re.fullmatch(r"[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64}", v):
        return "hash"

    if "." in v and " " not in v:
        return "domain"

    return "other"


class HuntSignalAddHandler(PersistentServerConnectionApplication):
    """
    POST /falconer/hunt_signal_add

    mode=new_hunt:
      - creates hunt_id
      - creates hunt doc (if missing)
      - creates ROOT signal (root_signal=1)

    mode=existing_hunt:
      - requires hunt_id
      - creates NON-root signal (root_signal=0)
      - idempotent on (hunt_id, entity_type, entity_value)
    """

    def __init__(self, command_line, command_arg):
        super(HuntSignalAddHandler, self).__init__()

    def log(self, msg: str):
        if not DEBUG_ENABLED:
            return
        try:
            ts = datetime.datetime.utcnow().isoformat()
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [hunt_signal_add] {msg}\n")
        except Exception:
            pass

    # -------------------------
    # Payload parsing helpers
    # -------------------------
    def _list_to_dict(self, maybe_list):
        """
        Splunk sometimes sends args/payload as:
          [{"name":"x","value":"y"}, ...]
        """
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
        # try JSON
        try:
            val = json.loads(s)
            if isinstance(val, dict):
                return val
            if isinstance(val, list):
                return self._list_to_dict(val)
        except Exception:
            pass

        # fallback: querystring
        try:
            qs = parse_qs(s, keep_blank_values=True)
            flat = {}
            for k, vals in qs.items():
                if vals:
                    flat[k] = unquote_plus(vals[0])
            return flat
        except Exception:
            return {}

    def _unwrap_payload(self, raw_payload):
        """
        raw_payload may be:
          - dict (sometimes containing "payload": "{json}")
          - list-of-kv
          - json string
        """
        if isinstance(raw_payload, list):
            raw_payload = self._list_to_dict(raw_payload)

        if isinstance(raw_payload, dict):
            # common wrapper: {"payload":"{...}", "output_mode":"json"}
            inner = raw_payload.get("payload")
            if isinstance(inner, str) and inner.strip():
                return self._parse_string_payload(inner)
            # otherwise the dict itself is the payload
            return raw_payload

        if isinstance(raw_payload, str):
            return self._parse_string_payload(raw_payload)

        return {}

    def _parse_args(self, in_string):
        try:
            args = json.loads(in_string) if in_string else {}
        except Exception:
            args = {}

        if isinstance(args, list):
            args = self._list_to_dict(args)

        method = (args.get("method") or "GET").upper()
        raw_payload = args.get("payload")
        payload = self._unwrap_payload(raw_payload)

        # Splunk Web REST calls can carry URL/form parameters either inside
        # payload=... or as top-level persistent handler args. Keep top-level
        # values as defaults, then let the explicit payload override them.
        top_level_payload = {}
        for key, value in args.items():
            if key in ("method", "payload", "session", "headers", "query", "connection"):
                continue
            top_level_payload[key] = value
        query_payload = self._unwrap_payload(args.get("query"))
        merged_payload = {}
        if isinstance(query_payload, dict):
            merged_payload.update(query_payload)
        if isinstance(top_level_payload, dict):
            merged_payload.update(top_level_payload)
        if isinstance(payload, dict):
            merged_payload.update(payload)
        payload = merged_payload

        # extra safety: if still wrapped, unwrap again
        if isinstance(payload, dict) and isinstance(payload.get("payload"), str):
            outer_payload = {k: v for k, v in payload.items() if k not in ("payload", "output_mode")}
            inner_payload = self._parse_string_payload(payload["payload"])
            outer_payload.update(inner_payload)
            payload = outer_payload

        return method, payload, args

    # -------------------------
    # KVStore helpers
    # -------------------------
    def _kv_uri_collection(self, collection: str) -> str:
        return f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}"

    def _kv_uri_key(self, collection: str, key: str) -> str:
        return f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}/{key}"

    def _kv_create_with_key(self, session_key: str, collection: str, key: str, doc: dict):
        """
        Create document with explicit _key using POST to collection endpoint.
        Returns (status_int, parsed_json_or_raw)
        """
        uri = self._kv_uri_collection(collection)
        body = dict(doc)
        body["_key"] = key

        resp, content = rest.simpleRequest(
            uri,
            method="POST",
            getargs={"output_mode": "json"},
            jsonargs=json.dumps(body).encode("utf-8"),
            sessionKey=session_key,
            raiseAllErrors=False,
        )
        status = int(resp.get("status", 0) or 0)

        parsed = None
        if content:
            try:
                parsed = json.loads(content.decode("utf-8"))
            except Exception:
                parsed = content.decode("utf-8", errors="replace")

        return status, parsed

    def _kv_update_existing(self, session_key: str, collection: str, key: str, doc: dict):
        """
        Update existing document via POST /collection/key
        Returns (status_int, parsed_json_or_raw)
        """
        uri = self._kv_uri_key(collection, key)

        resp, content = rest.simpleRequest(
            uri,
            method="POST",
            getargs={"output_mode": "json"},
            jsonargs=json.dumps(doc).encode("utf-8"),
            sessionKey=session_key,
            raiseAllErrors=False,
        )
        status = int(resp.get("status", 0) or 0)

        parsed = None
        if content:
            try:
                parsed = json.loads(content.decode("utf-8"))
            except Exception:
                parsed = content.decode("utf-8", errors="replace")

        return status, parsed

    def _kv_get_by_key(self, session_key: str, collection: str, key: str):
        uri = self._kv_uri_key(collection, key)
        try:
            resp, content = rest.simpleRequest(
                uri,
                method="GET",
                getargs={"output_mode": "json"},
                sessionKey=session_key,
                raiseAllErrors=False,
            )
        except Exception as e:
            if "404" in str(e):
                return None
            raise
        status = int(resp.get("status", 0) or 0)
        if status == 404:
            return None
        if status not in (200, 201) or not content:
            return None
        try:
            doc = json.loads(content.decode("utf-8"))
            return doc if isinstance(doc, dict) else None
        except Exception:
            return None

    def _kv_query(self, session_key: str, collection: str, query: dict):
        uri = self._kv_uri_collection(collection)
        resp, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs={
                "output_mode": "json",
                "query": json.dumps(query),
                "count": "0",
            },
            sessionKey=session_key,
            raiseAllErrors=False,
        )
        status = int(resp.get("status", 0) or 0)
        if status not in (200, 201) or not content:
            return []
        try:
            rows = json.loads(content.decode("utf-8"))
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    def _recount_hunt_signals(self, session_key: str, hunt_id: str):
        rows = self._kv_query(session_key, SIGNALS_COLLECTION, {"hunt_id": hunt_id})
        entities = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            entity_value = _first_non_empty(row.get("entity_value"), row.get("value"), row.get("signal"))
            entity_type = _first_non_empty(row.get("entity_type"), row.get("field"), "unknown")
            if entity_value:
                entities.add((entity_type, _normalize_entity(entity_type, entity_value)))
        return len(rows), len(entities)

    def _find_existing_open_root_hunt(self, session_key: str, entity_type: str, normalized_entity: str):
        rows = self._kv_query(session_key, SIGNALS_COLLECTION, {"entity_type": entity_type, "normalized_entity": normalized_entity})
        if not rows:
            rows = [
                row for row in self._kv_query(session_key, SIGNALS_COLLECTION, {"entity_type": entity_type})
                if _normalize_entity(entity_type, _first_non_empty(row.get("entity_value"), row.get("value"), row.get("signal"))) == normalized_entity
            ]
        for row in rows:
            if not isinstance(row, dict):
                continue
            if _safe_int(row.get("root_signal"), 0) != 1:
                continue
            hunt_id = _first_non_empty(row.get("hunt_id"))
            if not hunt_id:
                continue
            hunt = self._kv_get_by_key(session_key, HUNTS_COLLECTION, hunt_id) or {}
            status = _first_non_empty(hunt.get("status"), "open").lower()
            if status not in ("closed", "archived", "complete", "completed"):
                return hunt_id, hunt, row
        return "", {}, {}

    def _kv_upsert(self, session_key: str, collection: str, key: str, doc: dict):
        """
        Real upsert:
          - try create with _key
          - if 409 exists => update
          - if update returns 404 => create again (race / odd state)
        """
        c_status, c_body = self._kv_create_with_key(session_key, collection, key, doc)
        if c_status in (200, 201):
            return c_status, c_body

        if c_status == 409:
            u_status, u_body = self._kv_update_existing(session_key, collection, key, doc)
            if u_status in (200, 201):
                return u_status, u_body
            if u_status == 404:
                # rare: doc vanished between create attempt & update
                c2_status, c2_body = self._kv_create_with_key(session_key, collection, key, doc)
                return c2_status, c2_body
            return u_status, u_body

        # Any other create error
        return c_status, c_body

    # -------------------------
    # Main handler
    # -------------------------
    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)
            self.log(f"hit method={method} payload={payload}")

            if method != "POST":
                return {"payload": {"status": "error", "error": "Only POST supported"}, "status": 405}

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                return {"payload": {"status": "error", "error": "Missing sessionKey/authtoken"}, "status": 401}

            mode = (payload.get("mode") or "existing_hunt").strip().lower()
            if mode not in ("new_hunt", "existing_hunt"):
                return {"payload": {"status": "error", "error": f"Invalid mode: {mode}"}, "status": 400}

            field = (payload.get("field") or "").strip()

            # ✅ THE IMPORTANT PART:
            # entity_value should always be "what you right-clicked"
            entity_value = (payload.get("entity_value") or payload.get("value") or payload.get("signal") or "").strip()
            if not entity_value:
                return {
                    "payload": {"status": "error", "error": "Missing required field: entity_value (or value/signal)"},
                    "status": 400,
                }

            entity_type = (payload.get("entity_type") or "").strip()
            if not entity_type:
                entity_type = _infer_entity_type(field, entity_value)
            entity_type = entity_type.lower()
            normalized_entity = _normalize_entity(entity_type, entity_value)

            now = _now_epoch()
            actor = _request_user(args, payload)

            # hunt_id rules
            reused_existing_hunt = False
            if mode == "new_hunt":
                force_new_hunt = str(payload.get("force_new_hunt") or "").strip().lower() in ("1", "true", "yes")
                if force_new_hunt:
                    hunt_id = str(uuid.uuid4())
                else:
                    hunt_id, existing_hunt, existing_root_signal = self._find_existing_open_root_hunt(
                        session_key,
                        entity_type,
                        normalized_entity,
                    )
                    reused_existing_hunt = bool(hunt_id)
                    if not hunt_id:
                        hunt_id = str(uuid.uuid4())
            else:
                hunt_id = (payload.get("hunt_id") or "").strip()
                if not hunt_id:
                    return {"payload": {"status": "error", "error": "Missing required field: hunt_id"}, "status": 400}

            # deterministic signal key (idempotent for existing hunt)
            signal_key = _stable_signal_key(hunt_id, entity_type, entity_value)
            existing_hunt = self._kv_get_by_key(session_key, HUNTS_COLLECTION, hunt_id) or {}
            existing_signal = self._kv_get_by_key(session_key, SIGNALS_COLLECTION, signal_key) or {}

            # 1) Ensure hunt exists/upsert it without replacing real metadata
            # with generic UI defaults on existing hunts or form/AJAX posts.
            submitted_hunt_title = _first_non_empty(payload.get("hunt_title"), payload.get("hunt_name"))
            submitted_hunt_description = _first_non_empty(payload.get("hunt_description"))
            if mode == "new_hunt":
                submitted_hunt_title = _first_non_empty(submitted_hunt_title, payload.get("title"))
                submitted_hunt_description = _first_non_empty(submitted_hunt_description, payload.get("description"))

            hunt_title = _first_non_empty(submitted_hunt_title, existing_hunt.get("title"))
            if not hunt_title:
                hunt_title = f"Manual seed ({entity_type}:{entity_value})" if mode == "new_hunt" else f"Hunt ({hunt_id})"

            hunt_doc = {k: v for k, v in existing_hunt.items() if k != "_key"}
            hunt_doc.update({
                "hunt_id": hunt_id,
                "owner": _first_non_empty(payload.get("hunt_owner"), payload.get("owner"), existing_hunt.get("owner"), actor),
                "status": _first_non_empty(payload.get("hunt_status"), existing_hunt.get("status"), payload.get("status"), "open").lower(),
                "title": hunt_title,
                "description": _first_non_empty(submitted_hunt_description, existing_hunt.get("description")),
                "origin": _first_non_empty(payload.get("origin"), payload.get("hunt_origin"), existing_hunt.get("origin"), "falconer_ui"),
                "created_time": _safe_int(existing_hunt.get("created_time"), now),
                "created_by": _first_non_empty(existing_hunt.get("created_by"), actor),
                "updated_time": now,
                "updated_by": _first_non_empty(actor, existing_hunt.get("updated_by")),
                "last_activity_time": now,
                "signal_count": _safe_int(existing_hunt.get("signal_count"), _safe_int(payload.get("signal_count"), 0)),
                "entity_count": _safe_int(existing_hunt.get("entity_count"), _safe_int(payload.get("entity_count"), 1)),
                "app_managed": 1,
                "app_version": _first_non_empty(existing_hunt.get("app_version"), "vNext"),
                "user_modified": _safe_int(existing_hunt.get("user_modified"), 0),
            })

            hs, hb = self._kv_upsert(session_key, HUNTS_COLLECTION, hunt_id, hunt_doc)
            if hs not in (200, 201):
                return {
                    "payload": {
                        "status": "error",
                        "error": f"Failed to upsert hunt (status={hs})",
                        "detail": hb,
                    },
                    "status": 500,
                }

            # 2) Build signal doc
            root_signal = 1 if mode == "new_hunt" else 0
            signal_id = _first_non_empty(existing_signal.get("signal_id"), str(uuid.uuid4()))

            title = _first_non_empty(payload.get("signal_title"), payload.get("title"), existing_signal.get("title"))
            if not title:
                title = f"Seed signal ({entity_type}:{entity_value})" if root_signal == 1 else f"Signal ({entity_type}:{entity_value})"

            description = _first_non_empty(payload.get("signal_description"), payload.get("description"), existing_signal.get("description"))
            if not description:
                description = "Seeded via Falconer UI" if root_signal == 1 else "Added via Falconer UI"

            signal_doc = {k: v for k, v in existing_signal.items() if k != "_key"}
            signal_doc.update({
                "signal_id": signal_id,
                "hunt_id": hunt_id,
                "owner": _first_non_empty(payload.get("signal_owner"), payload.get("owner"), existing_signal.get("owner"), actor),
                "parent_signal_id": _first_non_empty(payload.get("parent_signal_id"), existing_signal.get("parent_signal_id")),
                "root_signal": _safe_int(existing_signal.get("root_signal"), root_signal),

                "signal_type": _first_non_empty(payload.get("signal_type"), existing_signal.get("signal_type"), ("manual_seed" if root_signal == 1 else "manual")),
                "entity_type": entity_type,
                "entity_value": entity_value,
                "normalized_entity": normalized_entity,

                # legacy compatibility fields (keep both)
                "signal": entity_value,
                "field": field,
                "value": entity_value,

                "category": _first_non_empty(payload.get("category"), existing_signal.get("category"), "right-click"),
                "confidence": _first_non_empty(payload.get("confidence"), existing_signal.get("confidence"), "low"),
                "status": _first_non_empty(payload.get("signal_status"), existing_signal.get("status"), "open"),
                "title": title,
                "description": description,

                "signal_source": _first_non_empty(payload.get("signal_source"), existing_signal.get("signal_source"), "falconer:right-click"),
                "content_hash": signal_key,

                "created_time": _safe_int(existing_signal.get("created_time"), now),
                "created_by": _first_non_empty(existing_signal.get("created_by"), actor),
                "updated_time": now,
                "updated_by": _first_non_empty(actor, existing_signal.get("updated_by")),
                "first_seen": _safe_int(existing_signal.get("first_seen"), now),
                "last_seen": now,
                "seen_count": _safe_int(existing_signal.get("seen_count"), 0) + 1,

                "app_managed": 1,
                "app_version": _first_non_empty(existing_signal.get("app_version"), "vNext"),
                "user_modified": _safe_int(existing_signal.get("user_modified"), 0),

                # extra context (helpful later)
                "view": (payload.get("view") or "").strip(),
                "page_url": (payload.get("page_url") or "").strip(),
                "earliest": (payload.get("earliest") or "").strip(),
                "latest": (payload.get("latest") or "").strip(),
            })

            # 3) Upsert signal doc
            ss, sb = self._kv_upsert(session_key, SIGNALS_COLLECTION, signal_key, signal_doc)
            if ss not in (200, 201):
                # If this is "existing_hunt", treat 409 as idempotent success
                if ss == 409 and mode == "existing_hunt":
                    return {
                        "payload": {
                            "status": "success",
                            "idempotent": True,
                            "mode": mode,
                            "hunt_id": hunt_id,
                            "signal_key": signal_key,
                        },
                        "status": 200,
                    }

                return {
                    "payload": {
                        "status": "error",
                        "error": f"Failed to upsert signal (status={ss})",
                        "detail": sb,
                    },
                    "status": 500,
                }

            signal_count, entity_count = self._recount_hunt_signals(session_key, hunt_id)
            hunt_doc["signal_count"] = signal_count
            hunt_doc["entity_count"] = entity_count or 1
            hunt_doc["updated_time"] = now
            hunt_doc["last_activity_time"] = now
            hs2, hb2 = self._kv_update_existing(session_key, HUNTS_COLLECTION, hunt_id, hunt_doc)
            if hs2 not in (200, 201):
                return {
                    "payload": {
                        "status": "error",
                        "error": f"Failed to update hunt counts (status={hs2})",
                        "detail": hb2,
                    },
                    "status": 500,
                }

            return {
                "payload": {
                    "status": "success",
                    "action": "updated" if existing_signal else "created",
                    "idempotent": bool(existing_signal) or reused_existing_hunt,
                    "reused_existing_hunt": reused_existing_hunt,
                    "mode": mode,
                    "hunt_id": hunt_id,
                    "signal_key": signal_key,
                    "signal_id": signal_id,
                    "root_signal": root_signal,
                    "entity_type": entity_type,
                    "entity_value": entity_value,
                    "normalized_entity": normalized_entity,
                    "signal_count": signal_count,
                    "entity_count": entity_count,
                },
                "status": 200,
            }

        except Exception as e:
            self.log(f"Exception: {e}")
            return {"payload": {"status": "error", "error": str(e)}, "status": 500}

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
