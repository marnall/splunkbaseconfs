# bin/hunts_list.py
import json
import datetime
from urllib.parse import parse_qs, unquote_plus

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP_NAME = "apt-falconer"
HUNTS_COLLECTION = "falconer_hunts"


def _now_epoch() -> int:
    return int(datetime.datetime.utcnow().timestamp())


class HuntsListHandler(PersistentServerConnectionApplication):
    """
    GET /falconer/hunts_list

    Query params (optional):
      - status=open|closed|all   (default: open)
      - limit=50                (default: 50; max 200)
      - sort=updated_time|last_activity_time|created_time (default: updated_time)
      - order=desc|asc          (default: desc)
      - q=<substring>           (optional title filter)

    Returns:
      {"status":"success","hunts":[...]}
    """

    def __init__(self, command_line, command_arg):
        super(HuntsListHandler, self).__init__()

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
            qs = parse_qs(s, keep_blank_values=True)
            flat = {}
            for k, vals in qs.items():
                if vals:
                    flat[k] = unquote_plus(vals[0])
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
            args = json.loads(in_string) if in_string else {}
        except Exception:
            args = {}

        if isinstance(args, list):
            args = self._list_to_dict(args)

        method = (args.get("method") or "GET").upper()
        raw_payload = args.get("payload")
        payload = self._unwrap_payload(raw_payload)

        # extra safety unwrap
        if isinstance(payload, dict) and isinstance(payload.get("payload"), str):
            payload = self._parse_string_payload(payload["payload"])

        return method, payload, args

    def _kv_list(self, session_key: str):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{HUNTS_COLLECTION}"
        resp, content = rest.simpleRequest(
            uri,
            method="GET",
            getargs={"output_mode": "json"},
            sessionKey=session_key,
            raiseAllErrors=False,
        )
        status = int(resp.get("status", 0) or 0)
        if status != 200:
            # return empty rather than exploding the UI
            return []
        try:
            data = json.loads(content.decode("utf-8")) if content else []
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def handle(self, in_string):
        try:
            method, payload, args = self._parse_args(in_string)

            if method != "GET":
                return {"payload": {"status": "error", "error": "Only GET supported"}, "status": 405}

            session_key = (args.get("session", {}) or {}).get("authtoken")
            if not session_key:
                return {"payload": {"status": "error", "error": "Missing sessionKey/authtoken"}, "status": 401}

            status = (payload.get("status") or "open").strip().lower()
            sort_field = (payload.get("sort") or "updated_time").strip()
            order = (payload.get("order") or "desc").strip().lower()
            q = (payload.get("q") or "").strip().lower()

            try:
                limit = int(payload.get("limit") or 50)
            except Exception:
                limit = 50
            limit = max(1, min(limit, 200))

            hunts = self._kv_list(session_key)

            # filter by status
            if status and status != "all":
                hunts = [h for h in hunts if str(h.get("status", "")).lower() == status]

            # optional substring search by title
            if q:
                hunts = [h for h in hunts if q in str(h.get("title", "")).lower()]

            # sort
            def keyfn(h):
                v = h.get(sort_field)
                try:
                    return int(v)
                except Exception:
                    return 0

            hunts.sort(key=keyfn, reverse=(order != "asc"))

            out = []
            for h in hunts[:limit]:
                out.append({
                    "hunt_id": h.get("hunt_id") or h.get("_key"),
                    "title": h.get("title") or "",
                    "status": h.get("status") or "",
                    "signal_count": int(h.get("signal_count") or 0),
                    "updated_time": int(h.get("updated_time") or 0),
                    "last_activity_time": int(h.get("last_activity_time") or 0),
                    "created_time": int(h.get("created_time") or 0),
                })

            return {"payload": {"status": "success", "hunts": out}, "status": 200}

        except Exception as e:
            return {"payload": {"status": "error", "error": str(e)}, "status": 500}

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass