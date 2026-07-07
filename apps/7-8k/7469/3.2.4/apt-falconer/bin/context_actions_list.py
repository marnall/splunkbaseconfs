import json
import csv
import time
from pathlib import Path
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

APP = "apt-falconer"
COLLECTION = "falconer_contexts"
APP_ROOT = Path(__file__).resolve().parents[1]
SEED_LOOKUP = APP_ROOT / "lookups" / "falconer_context_actions.csv"
REMOVED_APP_MANAGED_IDS = {"mitre_host_defense"}

def _json_response(payload, status=200):
    return {
        "payload": json.dumps(payload),
        "status": status,
        "headers": [("Content-Type", "application/json")]
    }

def _error_response(message, status=500):
    return _json_response({"status": "error", "error": message}, status=status)


def _as_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _dedupe_rows(rows):
    deduped = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        action_id = (row.get("id") or row.get("_key") or "").strip()
        if not action_id:
            continue

        existing = deduped.get(action_id)
        if not existing:
            deduped[action_id] = row
            continue

        def rank(doc):
            return (
                _as_int(doc.get("user_modified"), 0),
                1 if (doc.get("_key") == action_id) else 0,
                _as_int(doc.get("updated_time"), 0),
                _as_int(doc.get("created_time"), 0)
            )

        if rank(row) > rank(existing):
            deduped[action_id] = row

    return list(deduped.values())


def _truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_seed_rows():
    if not SEED_LOOKUP.is_file():
        return []

    rows = []
    with SEED_LOOKUP.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not isinstance(row, dict):
                continue
            row.setdefault("app_managed", 1)
            row.setdefault("user_modified", 0)
            row.setdefault("source", "falconer_seed")
            rows.append(row)
    return rows


def _merge_seed_rows(kv_rows):
    seed_rows = _load_seed_rows()
    seed_ids = {(row.get("id") or "").strip() for row in seed_rows if row.get("id")}
    merged = list(seed_rows)

    for row in kv_rows:
        action_id = (row.get("id") or row.get("_key") or "").strip()
        if action_id in REMOVED_APP_MANAGED_IDS and not _truthy(row.get("user_modified")):
            continue
        if action_id and action_id not in seed_ids and _truthy(row.get("app_managed")):
            continue
        merged.append(row)

    return merged

class ContextActionsList(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        # Some Splunk versions instantiate PSC handlers with args; accept them safely.
        try:
            super(ContextActionsList, self).__init__()
        except Exception:
            # If base init signature differs, we still want the handler to start.
            pass
            
    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            #session_key = request.get("session", {}).get("authtoken") or request.get("sessionKey")
            session = request.get("session")
            session_key = ""

            if isinstance(session, dict):
                session_key = session.get("authtoken") or session.get("sessionKey") or ""
            elif isinstance(session, str):
                session_key = session.replace("Splunk ", "").strip()

            if not session_key:
                session_key = request.get("sessionKey") or ""

            if not session_key:
                return _error_response("Missing session key", status=401)

            # NOTE: Do NOT pass 'sort' here (it breaks on some Splunk versions)
            url = f"/servicesNS/nobody/{APP}/storage/collections/data/{COLLECTION}"
            args = {"output_mode": "json", "count": 0}  # count=0 -> return all

            resp, content = rest.simpleRequest(
                url,
                sessionKey=session_key,
                method="GET",
                getargs=args,
                raiseAllErrors=True
            )

            rows = json.loads(content) if content else []
            if not isinstance(rows, list):
                rows = []

            rows = _dedupe_rows(_merge_seed_rows(rows))

            # Python-side sort: order ASC, label ASC (stable + version-proof)
            def _order_val(r):
                v = r.get("order", 999999)
                try:
                    return int(v)
                except Exception:
                    return 999999

            rows.sort(key=lambda r: (_order_val(r), str(r.get("label", "")).lower()))

            return _json_response({
                "status": "ok",
                "count": len(rows),
                "actions": rows,
                "payload": rows,
                "ts": int(time.time())
            })

        except Exception as e:
            # surface the underlying exception to your JS console (matches your current pattern)
            return _error_response(str(e), status=500)
