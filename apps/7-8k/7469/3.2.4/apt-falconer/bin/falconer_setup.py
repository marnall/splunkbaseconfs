"""bin/falconer_setup.py

Admin-only setup handler.

Responsibilities:
1) Read / write Falconer index macros (macros.conf stanzas)
2) Mark app as configured
3) Seed/upgrade default Context Actions into KVStore (upgrade-safe, non-destructive)

Upgrade policy implemented (Rule #2):
- If an action exists and user_modified==1 => NEVER overwrite
- If an action exists and user_modified==0 => update only if vendor content differs (content_hash changed)
- If missing => insert
"""

import hashlib
import json
import os
import time
import csv
from typing import Dict, Any, List, Tuple, Optional

from splunk import rest
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "apt-falconer"

# IMPORTANT: must match collections.conf
CONTEXTS_COLLECTION = "falconer_contexts"

SEED_CSV = os.path.join("lookups", "falconer_context_actions.csv")

INDEX_MACROS = [
    "zeek_index",
    "rita_index",
    "snort_index",
    "suricata_index",
    "stream_index",
    "sguild_index",
    "ossec_index",
    "win_index",
    "nix_index",
    "scripts_index",
    "sysmon_index",
    "cloudtrail_index",
    "esxi_index",
    "o365_index",
    "aws_index",
    "azure_index",
]

DEFAULT_INDEX = "index=*"


def _extract_session_key(request: Dict[str, Any]) -> str:
    """Handle common Splunk persistent handler request shapes."""
    if isinstance(request.get("sessionKey"), str) and request.get("sessionKey"):
        return request["sessionKey"]

    session = request.get("session")
    if isinstance(session, dict):
        return session.get("authtoken") or session.get("sessionKey") or ""

    if isinstance(session, str):
        return session.replace("Splunk ", "").strip()

    headers = request.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if isinstance(auth, str) and auth.lower().startswith("splunk "):
        return auth.replace("Splunk ", "").strip()

    return ""


class FalconerSetup(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        try:
            super(FalconerSetup, self).__init__()
        except Exception:
            pass

    def handle(self, in_string):
        request = json.loads(in_string or "{}")

        method = (request.get("method") or request.get("http_method") or "GET").upper()
        session_key = _extract_session_key(request)

        debug = {
            "saw_method": method,
            "has_session_key": bool(session_key),
            "keys_present": sorted(list(request.keys())),
            "session_shape": type(request.get("session")).__name__,
            "has_sessionKey_field": bool(request.get("sessionKey")),
            "has_headers": bool(request.get("headers")),
        }

        if not session_key:
            return self._json({"status": "error", "error": "Missing session token", "debug": debug}, 401)

        if method == "GET":
            resp = self._list_macros(session_key)
            try:
                body = json.loads(resp["payload"])
                body["debug"] = debug
                resp["payload"] = json.dumps(body)
            except Exception:
                pass
            return resp

        if method == "POST":
            payload = self._normalize_payload(request.get("payload") or {})
            resp = self._update_macros_and_seed(session_key, payload)
            try:
                body = json.loads(resp["payload"])
                body["debug"] = debug
                resp["payload"] = json.dumps(body)
            except Exception:
                pass
            return resp

        return self._json({"status": "error", "error": f"Unsupported method: {method}", "debug": debug}, 405)

    # ---------------------- Macros ----------------------

    def _normalize_payload(self, payload: Any) -> Dict[str, str]:
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except Exception:
                return {}
        if isinstance(payload, dict):
            return payload
        return {}

    def _list_macros(self, session_key: str):
        macros = {m: self._read_macro(session_key, m) for m in INDEX_MACROS}
        return self._json({"status": "ok", "macros": macros}, 200)

    def _update_macros_and_seed(self, session_key: str, payload: Dict[str, str]):
        for macro in INDEX_MACROS:
            definition = payload.get(macro) or self._read_macro(session_key, macro)
            self._write_macro(session_key, macro, definition)

        self._mark_configured(session_key)
        seed_result = self._seed_or_upgrade_contexts(session_key)

        return self._json({"status": "ok", **seed_result}, 200)

    def _read_macro(self, session_key: str, macro: str) -> str:
        try:
            path = f"/servicesNS/nobody/{APP_NAME}/configs/conf-macros/{macro}"
            response, content = rest.simpleRequest(
                path,
                sessionKey=session_key,
                getargs={"output_mode": "json"},
            )
            if response.get("status") == "200" and content:
                payload = json.loads(content.decode("utf-8"))
                entries = payload.get("entry") or []
                if entries:
                    definition = entries[0].get("content", {}).get("definition")
                    if definition:
                        return definition
        except Exception:
            pass
        return DEFAULT_INDEX

    def _write_macro(self, session_key: str, macro: str, definition: str):
        self._ensure_macro_exists(session_key, macro)
        path = f"/servicesNS/nobody/{APP_NAME}/configs/conf-macros/{macro}"
        rest.simpleRequest(
            path,
            sessionKey=session_key,
            method="POST",
            postargs={"definition": definition, "iseval": "0"},
            raiseAllErrors=True,
        )

    def _ensure_macro_exists(self, session_key: str, macro: str):
        path = f"/servicesNS/nobody/{APP_NAME}/configs/conf-macros/{macro}"
        try:
            response, _ = rest.simpleRequest(path, sessionKey=session_key)
            if response.get("status") == "200":
                return
        except Exception:
            pass

        rest.simpleRequest(
            f"/servicesNS/nobody/{APP_NAME}/configs/conf-macros",
            sessionKey=session_key,
            method="POST",
            postargs={"name": macro},
            raiseAllErrors=True,
        )

    def _mark_configured(self, session_key: str):
        rest.simpleRequest(
            f"/servicesNS/nobody/{APP_NAME}/properties/app/install/is_configured",
            sessionKey=session_key,
            method="POST",
            postargs={"value": "1"},
            raiseAllErrors=True,
        )

    # ---------------------- Context seeding / upgrade ----------------------

    def _app_root(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _read_app_version(self) -> str:
        """
        Best-effort: read version from app.conf (local first, then default).
        Falls back to 'unknown' if not found.
        """
        root = self._app_root()
        candidates = [
            os.path.join(root, "local", "app.conf"),
            os.path.join(root, "default", "app.conf"),
        ]
        for p in candidates:
            if not os.path.exists(p):
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith(";"):
                            continue
                        if line.lower().startswith("version"):
                            # version = x.y.z
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                return parts[1].strip()
            except Exception:
                pass
        return "unknown"

    def _load_seed_actions(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        path = os.path.join(self._app_root(), SEED_CSV)
        exists = os.path.exists(path)
        meta = {"seed_path": path, "seed_exists": exists}

        if not exists:
            return [], meta

        try:
            rows: List[Dict[str, Any]] = []
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not isinstance(row, dict):
                        continue
                    doc = {k: (v if v is not None else "") for k, v in row.items()}
                    doc_id = (doc.get("id") or "").strip()
                    if not doc_id:
                        continue
                    rows.append(doc)
            return rows, meta
        except Exception as e:
            return [], {**meta, "seed_error": str(e)}

    def _stable_hash(self, doc: Dict[str, Any]) -> str:
        """
        Hash only functional fields to detect vendor content changes.
        """
        core = {k: doc.get(k, "") for k in ["enabled", "field", "group", "subgroup", "label", "order", "target", "url", "value_regex", "view"]}
        s = json.dumps(core, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _kv_get_by_key(self, session_key: str, key: str) -> Optional[Dict[str, Any]]:
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{CONTEXTS_COLLECTION}/{key}"
        try:
            resp, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method="GET",
                getargs={"output_mode": "json"},
            )
            if resp.get("status") == "200" and content:
                return json.loads(content.decode("utf-8"))
        except Exception:
            return None
        return None

    def _kv_query_by_id(self, session_key: str, doc_id: str) -> List[Dict[str, Any]]:
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{CONTEXTS_COLLECTION}"
        query = json.dumps({"id": doc_id})
        try:
            resp, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method="GET",
                getargs={"output_mode": "json", "count": 0, "query": query},
                raiseAllErrors=True,
            )
            if resp.get("status") == "200" and content:
                rows = json.loads(content.decode("utf-8"))
                if isinstance(rows, list):
                    return rows
        except Exception:
            return []
        return []

    def _kv_delete(self, session_key: str, key: str):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{CONTEXTS_COLLECTION}/{key}"
        rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method="DELETE",
            raiseAllErrors=True,
        )

    def _rank_context_doc(self, doc: Dict[str, Any], doc_id: str) -> Tuple[int, int, int, int]:
        try:
            user_modified = int(doc.get("user_modified", 0))
        except Exception:
            user_modified = 0
        try:
            updated_time = int(doc.get("updated_time", 0))
        except Exception:
            updated_time = 0
        try:
            created_time = int(doc.get("created_time", 0))
        except Exception:
            created_time = 0
        return (
            user_modified,
            1 if doc.get("_key") == doc_id else 0,
            updated_time,
            created_time,
        )

    def _kv_insert(self, session_key: str, doc_id: str, doc: Dict[str, Any]):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{CONTEXTS_COLLECTION}"
        doc["_key"] = doc_id  # enforce uniqueness via _key
        rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method="POST",
            jsonargs=json.dumps(doc).encode("utf-8"),
            raiseAllErrors=True,
        )

    def _kv_update(self, session_key: str, doc_id: str, doc: Dict[str, Any]):
        uri = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{CONTEXTS_COLLECTION}/{doc_id}"
        doc["_key"] = doc_id
        rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method="POST",
            jsonargs=json.dumps(doc).encode("utf-8"),
            raiseAllErrors=True,
        )

    def _seed_or_upgrade_contexts(self, session_key: str) -> Dict[str, Any]:
        seed, seed_meta = self._load_seed_actions()
        if not seed:
            return {"seed": {"inserted": 0, "updated": 0, "skipped": 0, "protected": 0, "seed_count": 0, **seed_meta}}

        now = int(time.time())
        app_version = self._read_app_version()

        inserted = 0
        updated = 0
        skipped = 0
        protected = 0
        errors: List[str] = []

        for raw in seed:
            if not isinstance(raw, dict):
                continue

            doc_id = (raw.get("id") or "").strip()
            if not doc_id:
                continue

            try:
                existing_rows = self._kv_query_by_id(session_key, doc_id)
                existing = None
                if existing_rows:
                    existing = sorted(existing_rows, key=lambda d: self._rank_context_doc(d, doc_id), reverse=True)[0]
                desired_hash = self._stable_hash(raw)

                if existing:
                    # Rule #2: if user_modified, never touch
                    user_modified_val = existing.get("user_modified", 0)
                    try:
                        user_modified_val = int(user_modified_val)
                    except Exception:
                        user_modified_val = 0

                    if user_modified_val == 1:
                        protected += 1
                        continue

                    # vendor-managed and not user-modified: update only if changed
                    existing_hash = existing.get("content_hash") or ""
                    if existing_hash == desired_hash:
                        skipped += 1
                        continue

                    # Build updated doc: preserve created_* from existing, update functional fields to vendor defaults
                    doc = dict(existing)
                    # functional fields from seed
                    for k in ["enabled", "field", "group", "subgroup", "label", "order", "target", "url", "value_regex", "view"]:
                        if k in raw:
                            doc[k] = raw.get(k)

                    # vendor/governance
                    doc["source"] = "vendor"
                    doc["vendor_version"] = app_version
                    doc["app_managed"] = 1
                    doc["app_version"] = app_version
                    doc["content_hash"] = desired_hash
                    doc["user_modified"] = 0
                    doc["updated_time"] = now
                    doc["updated_by"] = "falconer_setup"

                    self._kv_update(session_key, doc_id, doc)
                    for dup in existing_rows:
                        dup_key = (dup.get("_key") or "").strip()
                        if dup_key and dup_key != doc_id:
                            try:
                                self._kv_delete(session_key, dup_key)
                            except Exception:
                                pass
                    updated += 1
                    continue

                # Insert new vendor default
                doc = dict(raw)
                doc["source"] = "vendor"
                doc["vendor_version"] = app_version
                doc["created_time"] = now
                doc["updated_time"] = now
                doc["updated_by"] = "falconer_setup"
                doc["app_managed"] = 1
                doc["app_version"] = app_version
                doc["content_hash"] = desired_hash
                doc["user_modified"] = 0

                self._kv_insert(session_key, doc_id, doc)
                for dup in existing_rows:
                    dup_key = (dup.get("_key") or "").strip()
                    if dup_key and dup_key != doc_id:
                        try:
                            self._kv_delete(session_key, dup_key)
                        except Exception:
                            pass
                inserted += 1

            except Exception as e:
                errors.append(f"{doc_id}: {e}")

        out = {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "protected": protected,
            "seed_count": len(seed),
            "app_version": app_version,
            **seed_meta,
        }
        if errors:
            out["errors"] = errors[:25]
        return {"seed": out}

    # ---------------------- Responses ----------------------

    def _json(self, payload: Dict[str, Any], status: int):
        return {
            "payload": json.dumps(payload),
            "status": status,
            "headers": {"Content-Type": "application/json"},
        }
