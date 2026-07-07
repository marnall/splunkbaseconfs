import datetime
import hashlib
import json
import os
import re
import sys
from urllib.parse import parse_qs, unquote_plus

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "apt-falconer", "bin"))

APP_NAME = "apt-falconer"
SIGNALS_COLLECTION = "falconer_signals"
HUNTS_COLLECTION = "falconer_hunts"

SCOPE_MAP = {
    "all_configured": "(`zeek_index` OR `stream_index` OR `suricata_index` OR `sysmon_index` OR `win_index` OR `nix_index` OR `o365_index`)",
    "network": "(`zeek_index` OR `stream_index` OR `suricata_index`)",
    "host": "(`sysmon_index` OR `win_index` OR `nix_index`)",
    "email": "(`o365_index` OR `win_index`)",
}

FIELD_CANDIDATES = {
    "ip": ["src", "dest", "src_ip", "dest_ip", "id.orig_h", "id.resp_h", "dvc", "clientip", "ip"],
    "domain": ["query", "domain", "host", "dest_host", "url_domain", "http_host"],
    "http": ["url", "uri", "http_uri", "request", "http_user_agent", "http_referrer"],
    "file": ["file_hash", "hash", "md5", "sha1", "sha256", "process_hash", "file_name"],
    "email": ["sender", "recipient", "src_user", "dest_user", "email", "subject"],
    "certificate": ["certificate_issuer", "certificate_subject", "certificate_serial", "ssl_issuer", "ssl_subject", "serial"],
    "process": ["process", "process_name", "process_file_name", "NewProcessName"],
    "registry": ["registry_path", "registry_value_name", "registry_value_text", "TargetObject"],
    "service": ["service", "service_name", "service_file_hash", "service_dll_file_hash"],
    "user": ["user", "src_user", "dest_user", "account", "account_name"],
}


def _json_response(payload, status=200):
    return {"payload": json.dumps(payload), "status": status, "headers": [("Content-Type", "application/json")]}


def _error_response(message, status=500):
    return _json_response({"status": "error", "error": str(message)}, status=status)


def _now_epoch():
    return int(datetime.datetime.utcnow().timestamp())


def _list_to_dict(maybe_list):
    out = {}
    if isinstance(maybe_list, list):
        for item in maybe_list:
            if isinstance(item, dict) and "name" in item:
                out[item["name"]] = item.get("value")
    return out


def _parse_string_payload(value):
    value = (value or "").strip()
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return _list_to_dict(parsed)
    except Exception:
        pass
    try:
        qs = parse_qs(value, keep_blank_values=True)
        if "payload" in qs:
            return _parse_string_payload(unquote_plus(qs["payload"][0]))
        return {k: v[0] for k, v in qs.items() if v}
    except Exception:
        return {}


def _parse_args(in_string):
    try:
        args = json.loads(in_string) if in_string else {}
    except Exception:
        args = {}
    if isinstance(args, list):
        args = _list_to_dict(args)
    if not isinstance(args, dict):
        args = {}
    method = (args.get("method") or "GET").upper()
    payload = args.get("payload")
    payload = payload if isinstance(payload, dict) else _parse_string_payload(payload)
    query_payload = args.get("query")
    if query_payload:
        merged = _parse_string_payload(query_payload)
        merged.update(payload)
        payload = merged
    return method, payload, args


def _session_key(args):
    session = args.get("session") or {}
    if isinstance(session, dict):
        return session.get("authtoken") or session.get("sessionKey") or ""
    if isinstance(session, str):
        return session.replace("Splunk ", "").strip()
    return args.get("sessionKey") or ""


def _quote(value):
    return '"' + str(value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def _regex_quote(value):
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"').replace(".", "\\.").replace("*", "\\*").replace("+", "\\+").replace("?", "\\?").replace("|", "\\|").replace("(", "\\(").replace(")", "\\)").replace("[", "\\[").replace("]", "\\]").replace("{", "\\{").replace("}", "\\}").replace("^", "\\^").replace("$", "\\$")


def _safe_relative_time(value, field_name):
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    if not re.match(r"^[A-Za-z0-9_@:+./-]+$", value):
        raise ValueError(f"{field_name} contains unsupported characters")
    return value


def _safe_scope(payload):
    scope = str(payload.get("scope") or "all_configured").strip()
    if scope == "custom":
        custom = str(payload.get("custom_scope") or "").strip()
        if not custom:
            raise ValueError("custom_scope is required when scope=custom")
        if any(ch in custom for ch in ("|", ";", "\n", "\r", "`")):
            raise ValueError("custom_scope cannot include pipes, semicolons, backticks, or newlines")
        return f"({custom})", scope
    return SCOPE_MAP.get(scope, SCOPE_MAP["all_configured"]), scope


def _candidate_eval(indicator_type):
    fields = FIELD_CANDIDATES[indicator_type]
    parts = []
    for field in fields:
        ref = f"'{field}'" if "." in field else field
        value_expr = f"lower({ref})" if indicator_type != "ip" else ref
        parts.append(f'if(isnotnull({ref}),"{field}=".{value_expr},null())')
    return "mvappend(" + ", ".join(parts) + ")"


def _field_filter(indicator_type, indicator):
    value = indicator if indicator_type == "ip" else indicator.lower()
    parts = []
    for field in FIELD_CANDIDATES[indicator_type]:
        ref = f"'{field}'" if "." in field else field
        parts.append(f"{ref}={_quote(value)}")
    return "(" + " OR ".join(parts) + ")"


def _build_search(payload):
    from intel_schema import TYPE_ALIASES, canonical_type

    indicator_type = canonical_type(payload.get("indicator_type"))
    if indicator_type not in FIELD_CANDIDATES:
        raise ValueError("indicator_type must be one of " + ", ".join(FIELD_CANDIDATES.keys()))
    indicator = str(payload.get("indicator") or "").strip()
    if indicator_type in ("domain", "http", "file", "email", "user"):
        indicator = indicator.lower()
    if not indicator:
        raise ValueError("indicator is required")

    earliest = _safe_relative_time(payload.get("earliest"), "earliest")
    latest = _safe_relative_time(payload.get("latest"), "latest")
    scope_spl, scope_name = _safe_scope(payload)
    max_events = max(1, min(int(payload.get("max_events") or 100), 1000))
    match_value = indicator if indicator_type == "ip" else indicator.lower()
    filter_spl = _field_filter(indicator_type, indicator)

    search = (
        f"search earliest={earliest} latest={latest} {scope_spl} {filter_spl} NOT index=_* "
        f"| eval _candidate={_candidate_eval(indicator_type)} "
        "| mvexpand _candidate "
        '| rex field=_candidate "^(?<matched_field>[^=]+)=(?<matched_value>.*)$" '
        f"| eval _match_pos=mvfind(matched_value,{_quote('^' + _regex_quote(match_value) + '$')}) "
        "| where _match_pos>=0 "
        "| eval matched_field=mvindex(matched_field,_match_pos), matched_value=mvindex(matched_value,_match_pos) "
        "| eventstats count as _total_events min(_time) as _first_seen max(_time) as _last_seen "
        "| eval event_time=strftime(_time,\"%Y-%m-%d %H:%M:%S %Z\") "
        "| fields _time event_time index sourcetype host matched_field matched_value _total_events _first_seen _last_seen "
        f"| head {max_events}"
    )
    return search, indicator_type, indicator, scope_name


def _export_search(session_key, search):
    resp, content = rest.simpleRequest(
        "/services/search/jobs/export",
        method="POST",
        postargs={"search": search, "output_mode": "json", "exec_mode": "oneshot"},
        sessionKey=session_key,
        raiseAllErrors=True,
    )
    rows = []
    text = content.decode("utf-8", errors="replace") if content else ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        result = item.get("result") if isinstance(item, dict) else None
        if isinstance(result, dict):
            rows.append(result)
    return rows


def _collection_uri(collection):
    return f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection}"


def _key_uri(collection, key):
    return f"{_collection_uri(collection)}/{key}"


def _kv_get(session_key, collection, key):
    resp, content = rest.simpleRequest(_key_uri(collection, key), method="GET", getargs={"output_mode": "json"}, sessionKey=session_key, raiseAllErrors=False)
    if int(resp.get("status", 0) or 0) not in (200, 201) or not content:
        return {}
    try:
        doc = json.loads(content.decode("utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def _kv_upsert(session_key, collection, key, doc):
    existing = _kv_get(session_key, collection, key)
    if existing.get("user_modified") in (1, "1", True):
        return "preserved", existing
    body = dict(existing)
    body.update(doc)
    body["_key"] = key
    method_uri = _key_uri(collection, key) if existing else _collection_uri(collection)
    resp, content = rest.simpleRequest(
        method_uri,
        method="POST",
        getargs={"output_mode": "json"},
        jsonargs=json.dumps(body).encode("utf-8"),
        sessionKey=session_key,
        raiseAllErrors=False,
    )
    status = int(resp.get("status", 0) or 0)
    if status == 409:
        body.pop("_key", None)
        resp, content = rest.simpleRequest(
            _key_uri(collection, key),
            method="POST",
            getargs={"output_mode": "json"},
            jsonargs=json.dumps(body).encode("utf-8"),
            sessionKey=session_key,
            raiseAllErrors=False,
        )
        status = int(resp.get("status", 0) or 0)
    if status not in (200, 201, 204):
        raise RuntimeError(f"KV upsert failed for {collection}/{key} (HTTP {status})")
    return "updated" if existing else "created", body


def _promote(session_key, payload, indicator_type, indicator, rows, scope_name):
    now = _now_epoch()
    total = 0
    first_seen = None
    last_seen = None
    indexes = set()
    sourcetypes = set()
    hosts = set()
    fields = set()
    values = set()
    for row in rows:
        total = max(total, int(float(row.get("_total_events") or 0)))
        if row.get("_first_seen"):
            first_seen = min(first_seen or int(float(row["_first_seen"])), int(float(row["_first_seen"])))
        if row.get("_last_seen"):
            last_seen = max(last_seen or int(float(row["_last_seen"])), int(float(row["_last_seen"])))
        for source, target in (("index", indexes), ("sourcetype", sourcetypes), ("host", hosts), ("matched_field", fields), ("matched_value", values)):
            value = str(row.get(source) or "").strip()
            if value:
                target.add(value)

    if not total:
        total = len(rows)
    first_seen = first_seen or now
    last_seen = last_seen or now
    hunt_id = "intel-" + hashlib.sha256(f"{indicator_type}|{indicator}".encode("utf-8")).hexdigest()[:16]
    signal_key = "intel_retro:" + hashlib.sha256(f"{indicator_type}|{indicator}|{scope_name}".encode("utf-8")).hexdigest()[:24]
    signal_id = hashlib.sha256(f"falconer_intel_retro|{indicator_type}|{indicator}|{scope_name}".encode("utf-8")).hexdigest()
    notes = str(payload.get("notes") or "").strip()
    actor = str(payload.get("owner") or "intel_retro_hunt").strip()

    hunt_doc = {
        "hunt_id": hunt_id,
        "status": "open",
        "title": f"Intel Hunt: {indicator}",
        "description": f"Retro hunt for {indicator_type} indicator {indicator}. {notes}".strip(),
        "origin": "falconer_intel_retro_hunt",
        "signal_count": 1,
        "entity_count": 1,
        "created_time": now,
        "created_by": actor,
        "updated_time": now,
        "updated_by": actor,
        "last_activity_time": now,
        "app_managed": 1,
        "app_version": "3.2.1",
        "user_modified": 0,
        "content_hash": hashlib.md5(f"{hunt_id}|{total}|{last_seen}".encode("utf-8")).hexdigest(),
    }
    signal_doc = {
        "signal": indicator,
        "signal_id": signal_id,
        "signal_type": "threat_intel",
        "entity_type": indicator_type,
        "entity_value": indicator,
        "hunt_id": hunt_id,
        "root_signal": 1,
        "field": ",".join(sorted(fields)),
        "value": ",".join(sorted(values)) or indicator,
        "category": "threat_intel",
        "confidence": str(payload.get("confidence") or "medium"),
        "status": "open",
        "title": f"Falconer Retro Intel Match: {indicator}",
        "description": f"Manual retro hunt found {total} event(s) for {indicator_type} indicator {indicator}. Scope={scope_name}; indexes={', '.join(sorted(indexes))}; sourcetypes={', '.join(sorted(sourcetypes))}; hosts={', '.join(sorted(hosts))}. {notes}".strip(),
        "signal_source": "falconer_intel_retro_hunt",
        "earliest": str(payload.get("earliest") or ""),
        "latest": str(payload.get("latest") or ""),
        "created_time": now,
        "created_by": actor,
        "updated_time": now,
        "updated_by": actor,
        "app_managed": 1,
        "app_version": "3.2.1",
        "user_modified": 0,
        "content_hash": hashlib.md5(f"{signal_id}|{total}|{last_seen}".encode("utf-8")).hexdigest(),
    }
    signal_doc["first_seen"] = first_seen
    signal_doc["last_seen"] = last_seen
    signal_doc["event_count"] = total
    signal_doc["matched_indexes"] = ",".join(sorted(indexes))
    signal_doc["matched_sourcetypes"] = ",".join(sorted(sourcetypes))
    signal_doc["matched_hosts"] = ",".join(sorted(hosts))
    signal_doc["notes"] = notes

    hunt_action, _ = _kv_upsert(session_key, HUNTS_COLLECTION, hunt_id, hunt_doc)
    signal_action, _ = _kv_upsert(session_key, SIGNALS_COLLECTION, signal_key, signal_doc)
    return {"hunt_id": hunt_id, "signal_key": signal_key, "signal_id": signal_id, "hunt_action": hunt_action, "signal_action": signal_action}


class IntelRetroHunt(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        super(IntelRetroHunt, self).__init__()

    def handle(self, in_string):
        try:
            method, payload, args = _parse_args(in_string)
            if method != "POST":
                return _error_response("Only POST supported", status=405)
            session_key = _session_key(args)
            if not session_key:
                raise ValueError("Missing session key")
            action = str(payload.get("action") or "preview").strip().lower()
            if action not in ("preview", "promote"):
                raise ValueError("action must be preview or promote")

            search, indicator_type, indicator, scope_name = _build_search(payload)
            rows = _export_search(session_key, search)
            total = int(float(rows[0].get("_total_events") or len(rows))) if rows else 0
            response = {
                "status": "success",
                "action": action,
                "indicator": indicator,
                "indicator_type": indicator_type,
                "scope": scope_name,
                "event_count": total,
                "preview_count": len(rows),
                "results": rows,
            }
            if action == "promote":
                if not rows:
                    raise ValueError("No matching events found to promote")
                response["promotion"] = _promote(session_key, payload, indicator_type, indicator, rows, scope_name)
            return _json_response(response, status=200)
        except Exception as e:
            return _error_response(e, status=500)

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
