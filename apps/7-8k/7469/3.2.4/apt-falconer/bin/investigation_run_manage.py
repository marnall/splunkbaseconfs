import csv
import datetime
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import splunk
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "apt-falconer"
RUNS_COLLECTION = "falconer_investigation_runs"
HUNTS_COLLECTION = "falconer_hunts"
SIGNALS_COLLECTION = "falconer_signals"
SEED_LOOKUP = Path(__file__).resolve().parents[1] / "lookups" / "falconer_context_actions.csv"
DASHBOARD_CATALOG = Path(__file__).resolve().parents[2] / "TA-apt-falconer-ai" / "prompt_packs" / "falconer_workflows" / "dashboard_catalog.json"

ENTITY_PRIORITY = [
    ("host", 10),
    ("process", 20),
    ("user", 30),
    ("ip", 40),
    ("domain", 50),
    ("hash", 60),
    ("file", 70),
    ("registry", 80),
    ("port", 90),
    ("email", 100),
]

FIELD_ALIASES = {
    "host": {"host", "hostname", "dest"},
    "process": {"process", "process_name", "newprocessname", "parent_process_name", "command_line"},
    "user": {"user", "src_user", "dest_user", "account_name"},
    "ip": {"src", "src_ip", "dest_ip", "ip", "peer_ip"},
    "domain": {"domain", "query", "uri_host", "host_header", "orig_hostname"},
    "hash": {"file_hash", "md5", "sha1", "sha256"},
    "file": {"file", "file_name", "filename", "path", "targetfilename", "objectname", "newname", "oldname"},
    "registry": {"registry_path", "registry_key_name", "registry_value_name", "targetobject", "objectname", "key_path", "registry_key"},
    "port": {"src_port", "dest_port", "dport", "sport", "port", "service_port"},
    "email": {"src_email", "dest_email", "recipient", "sender", "mail_from", "rcpt_to", "email"},
}

LABEL_TO_SEED_ID = {
    "Raw Search - Host": "generic_search_host",
    "Raw Search - Process": "generic_search_proc",
    "Raw Search - User": "generic_search_user",
    "Raw Search - IP": "generic_search_ip",
    "Raw Search - Domain": "generic_search_domain",
    "Raw Search - Hash": "generic_search_hash",
    "Raw Search - File Name": "generic_search_file",
    "Raw Search - Registry": "generic_search_registry",
    "Raw Search - Port": "generic_search_port",
}

LEGACY_TACTIC_EXPANSIONS = {
    "defense evasion": ["stealth", "defense impairment"],
}


def _json_response(payload, status=200):
    return {
        "payload": json.dumps(payload),
        "status": status,
        "headers": [("Content-Type", "application/json")],
    }


def _error_response(message, status=500):
    return _json_response({"status": "error", "error": message}, status=status)


def _as_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _now_epoch():
    return int(datetime.datetime.utcnow().timestamp())


def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _kv_url(collection, key=None):
    base = "/servicesNS/nobody/{}/storage/collections/data/{}".format(
        quote(APP_NAME, safe=""),
        quote(collection, safe=""),
    )
    if key is None:
        return base
    return "{}/{}".format(base, quote(key, safe=""))


def _read_json_bytes(content):
    if not content:
        return None
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    try:
        return json.loads(content)
    except Exception:
        return None


def _simple_request(session_key, uri, method="GET", getargs=None, jsonargs=None):
    try:
        return rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method=method,
            getargs=getargs,
            jsonargs=jsonargs,
            raiseAllErrors=False,
        )
    except splunk.ResourceNotFound:
        return None, None


def _kv_get(session_key, collection, key):
    resp, content = _simple_request(
        session_key,
        _kv_url(collection, key),
        method="GET",
        getargs={"output_mode": "json"},
    )
    if not resp or int(resp.status) != 200:
        return None
    data = _read_json_bytes(content)
    return data if isinstance(data, dict) else None


def _kv_query(session_key, collection, query):
    resp, content = _simple_request(
        session_key,
        _kv_url(collection),
        method="GET",
        getargs={"output_mode": "json", "query": json.dumps(query or {}), "count": "0"},
    )
    if not resp or int(resp.status) != 200:
        return []
    data = _read_json_bytes(content)
    return data if isinstance(data, list) else []


def _kv_upsert(session_key, collection, key, record):
    payload = dict(record)
    payload["_key"] = key
    resp, _ = _simple_request(
        session_key,
        _kv_url(collection, key),
        method="POST",
        jsonargs=json.dumps(payload).encode("utf-8"),
    )
    if resp and int(resp.status) in (200, 201):
        return True
    if resp is None or int(resp.status) == 404:
        create_resp, _ = _simple_request(
            session_key,
            _kv_url(collection),
            method="POST",
            jsonargs=json.dumps(payload).encode("utf-8"),
        )
        return create_resp is not None and int(create_resp.status) in (200, 201)
    return False


def _session_key_from_request(request):
    session = request.get("session")
    if isinstance(session, dict):
        return session.get("authtoken") or session.get("sessionKey") or ""
    if isinstance(session, str):
        return session.replace("Splunk ", "").strip()
    return request.get("sessionKey") or ""


def _username_from_request(request):
    user = request.get("user")
    if isinstance(user, dict):
        return user.get("name") or user.get("username") or "unknown"
    if isinstance(user, str) and user:
        return user
    return "unknown"


def _payload_from_request(request):
    raw_payload = request.get("payload") or "{}"
    if isinstance(raw_payload, dict):
        return dict(raw_payload)
    try:
        parsed = json.loads(raw_payload)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    payload = {}
    for key in ("form", "query"):
        items = request.get(key) or []
        if isinstance(items, dict):
            payload.update(items)
            continue
        for item in items:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                payload[item[0]] = item[1]
            elif isinstance(item, dict):
                name = item.get("name")
                if name:
                    payload[name] = item.get("value")
    return payload


def _load_seed_actions():
    if not SEED_LOOKUP.is_file():
        return {}

    actions = {}
    with SEED_LOOKUP.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not isinstance(row, dict):
                continue
            if str(row.get("enabled") or "").strip() not in {"1", "true", "True"}:
                continue
            action_id = (row.get("id") or "").strip()
            if not action_id:
                continue
            actions[action_id] = row
    return actions


@lru_cache(maxsize=1)
def _load_tactic_dashboard_catalog():
    if not DASHBOARD_CATALOG.is_file():
        return {}

    try:
        payload = json.loads(DASHBOARD_CATALOG.read_text(encoding="utf-8"))
    except Exception:
        return {}

    tactic_map = {}
    for row in payload.get("dashboards", []) or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("workflow_category") or "") != "attack_tactic_context":
            continue
        view = str(row.get("view") or "").strip()
        label = str(row.get("label") or "").strip()
        if not view or not label:
            continue
        tactic_map[label.lower()] = {"label": label, "view": view}
        for tactic_name in row.get("applicable_tactics", []) or []:
            normalized = str(tactic_name or "").strip().lower()
            if normalized and normalized not in tactic_map:
                tactic_map[normalized] = {"label": label, "view": view}
        for tactic_name in row.get("mitre_tactics", []) or []:
            normalized = str(tactic_name or "").strip().lower()
            if normalized and normalized not in tactic_map:
                tactic_map[normalized] = {"label": label, "view": view}
    return tactic_map


def _normalize_field_name(value):
    return str(value or "").strip().lower()


def _clean_value(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 180:
        return ""
    lowered = text.lower()
    if "encodedcommand" in lowered:
        return ""
    if text.count(" ") > 18 and any(token in lowered for token in ("powershell", "cmd.exe", "rundll32", "mshta")):
        return ""
    return text


def _classify_entity(field_name, entity_type):
    normalized = _normalize_field_name(entity_type) or _normalize_field_name(field_name)
    for category, names in FIELD_ALIASES.items():
        if normalized in names:
            return category
    return ""


def _collect_entities(hunt, signals):
    entities = {category: [] for category, _ in ENTITY_PRIORITY}
    seen = set()

    def add_entity(category, field_name, value, source):
        clean = _clean_value(value)
        if not category or not clean:
            return
        marker = (category, clean.lower())
        if marker in seen:
            return
        seen.add(marker)
        entities[category].append(
            {
                "field": field_name or category,
                "value": clean,
                "source": source,
            }
        )

    if isinstance(hunt, dict):
        add_entity("host", "dest", hunt.get("dest"), "hunt")
        add_entity("user", "user", hunt.get("user"), "hunt")
        add_entity("domain", "domain", hunt.get("domain"), "hunt")

    for row in signals or []:
        field_name = row.get("field") or row.get("entity_type") or ""
        entity_type = row.get("entity_type") or ""
        value = row.get("value") or row.get("entity_value") or row.get("signal") or ""
        category = _classify_entity(field_name, entity_type)
        add_entity(category, field_name, value, "signal")

    return entities


def _best_signal(signals):
    rows = list(signals or [])

    def sort_key(row):
        root_signal = _as_int(row.get("root_signal"), 0)
        updated = _as_int(row.get("updated_time") or row.get("created_time"), 0)
        return (root_signal, updated)

    rows.sort(key=sort_key, reverse=True)
    return rows[0] if rows else {}


def _build_action_url(action_row, field_name, value, hunt_id):
    template = str(action_row.get("url") or "")
    return (
        template.replace("${value}", quote(str(value or ""), safe=""))
        .replace("${field}", quote(str(field_name or ""), safe=""))
        .replace("${earliest}", quote("-24h@h", safe=""))
        .replace("${latest}", quote("now", safe=""))
        .replace("${view}", quote("signal_story", safe=""))
        .replace("${hunt_id}", quote(str(hunt_id or ""), safe=""))
    )


def _build_plan_steps(hunt, signals, entities):
    seed_actions = _load_seed_actions()
    steps = []
    run_goal_parts = []
    tactic_text = str((hunt or {}).get("tactic") or "").strip()
    technique_text = str((hunt or {}).get("technique") or "").strip()
    root_signal = _best_signal(signals)

    if tactic_text:
        run_goal_parts.append("Validate {} activity".format(tactic_text))
    if technique_text:
        run_goal_parts.append("check technique context for {}".format(technique_text))
    if root_signal.get("title"):
        run_goal_parts.append("explain {}".format(root_signal.get("title")))

    for category, _priority in ENTITY_PRIORITY:
        candidates = entities.get(category) or []
        if not candidates:
            continue
        entity = candidates[0]
        label = {
            "host": "Raw Search - Host",
            "process": "Raw Search - Process",
            "user": "Raw Search - User",
            "ip": "Raw Search - IP",
            "domain": "Raw Search - Domain",
            "hash": "Raw Search - Hash",
            "file": "Raw Search - File Name",
            "registry": "Raw Search - Registry",
            "port": "Raw Search - Port",
            "email": "Raw Search - Email",
        }.get(category)
        if not label:
            continue
        action_row = seed_actions.get(LABEL_TO_SEED_ID.get(label, ""))
        if not action_row:
            continue
        steps.append(
            {
                "step_id": LABEL_TO_SEED_ID.get(label, category),
                "label": label,
                "field": entity["field"],
                "value": entity["value"],
                "group": action_row.get("group") or "Investigate",
                "target": action_row.get("target") or "_blank",
                "url": _build_action_url(action_row, entity["field"], entity["value"], (hunt or {}).get("hunt_id", "")),
                "rationale": {
                    "host": "Establish which execution scope and nearby activity on the affected system matters first.",
                    "process": "Confirm whether the process pattern is isolated, repeated, or launched by a suspicious parent.",
                    "user": "Determine which account executed or authenticated around this hunt and whether the activity fits that user.",
                    "ip": "Check peer relationships, port context, and nearby network activity tied to this signal.",
                    "domain": "Assess whether the domain appears in suspicious resolution, connection, or follow-on host activity.",
                    "hash": "Validate whether the file hash is already known and whether it appears across more than one host.",
                    "file": "Check whether the file/path changed, where it appeared, and which processes referenced it.",
                    "registry": "Confirm whether persistence, policy, or execution-related registry changes exist for the same hunt.",
                    "port": "Determine whether the port value represents expected service behavior or a suspicious channel.",
                    "email": "Review whether the email artifact appears across related messages or surrounding execution.",
                }.get(category, "Use this pivot to gather the next bounded evidence slice."),
                "status": "pending",
            }
        )

    if tactic_text and entities.get("host"):
        tactic_catalog = _load_tactic_dashboard_catalog()
        normalized_tactics = []
        seen_tactics = set()
        for part in [part.strip().lower() for part in tactic_text.replace("/", ",").split(",") if part.strip()]:
            for tactic in LEGACY_TACTIC_EXPANSIONS.get(part, [part]):
                if tactic not in seen_tactics:
                    seen_tactics.add(tactic)
                    normalized_tactics.append(tactic)
        for tactic in normalized_tactics:
            tactic_info = tactic_catalog.get(tactic)
            if not tactic_info:
                continue
            host_entity = entities["host"][0]
            steps.append(
                {
                    "step_id": "mitre_{}".format(tactic_info["view"]),
                    "label": tactic_info["label"],
                    "field": host_entity["field"],
                    "value": host_entity["value"],
                    "group": "MITRE",
                    "target": "_blank",
                    "url": "/app/{}/{}?form.dest={}&form.time_tok.earliest=-24h@h&form.time_tok.latest=now&form.hunt_id={}".format(
                        APP_NAME,
                        tactic_info["view"],
                        quote(str(host_entity["value"]), safe=""),
                        quote(str((hunt or {}).get("hunt_id") or ""), safe=""),
                    ),
                    "rationale": "Review the hunt against the tactic-aligned Falconer dashboard to widen coverage around the same host.",
                    "status": "pending",
                }
            )
            if len(steps) >= 6:
                break

    steps = steps[:6]
    summary = "Start with the closest Falconer pivots for this hunt, then capture what changed the conclusion."
    if run_goal_parts:
        summary = "{}.".format("; ".join(run_goal_parts[:3]))
    return steps, summary


def _build_evidence_gaps(hunt, signals, entities):
    gaps = []
    if not entities.get("host"):
        gaps.append("No clean host pivot is present; the hunt may stay narrow until host context is added.")
    if not entities.get("process"):
        gaps.append("Process attribution is weak; confirm the actual tool or command family before closing the hunt.")
    if not entities.get("user"):
        gaps.append("User/account context is missing; assess whether the activity is authorized before disposition.")
    if not entities.get("ip") and not entities.get("domain"):
        gaps.append("Network follow-on context is missing; verify whether the behavior reached out to internal or external infrastructure.")
    if len(signals or []) < 2:
        gaps.append("This hunt has very few breadcrumbs; add confirmed related entities before final review if the case remains open.")
    if not str((hunt or {}).get("technique_id") or "").strip():
        gaps.append("Technique labeling is absent; keep the analyst summary explicit about what behavior was actually observed.")
    return gaps[:5]


def _serialize_run(record):
    output = dict(record)
    for field in ("steps_json", "entity_summary_json", "evidence_gaps_json"):
        raw = output.get(field)
        try:
            output[field[:-5]] = json.loads(raw) if raw else []
        except Exception:
            output[field[:-5]] = []
    return output


def _latest_run(session_key, hunt_id):
    runs = _kv_query(session_key, RUNS_COLLECTION, {"hunt_id": hunt_id})
    runs.sort(key=lambda row: _as_int(row.get("updated_time"), 0), reverse=True)
    return runs[0] if runs else None


class InvestigationRunManage(PersistentServerConnectionApplication):
    def __init__(self, *args, **kwargs):
        try:
            super(InvestigationRunManage, self).__init__()
        except Exception:
            pass

    def handle(self, in_string):
        try:
            request = json.loads(in_string) if in_string else {}
            method = str(request.get("method") or "GET").upper()
            session_key = _session_key_from_request(request)
            if not session_key:
                return _error_response("Missing session key", status=401)

            if method == "GET":
                params = {}
                for item in request.get("query", []) or []:
                    if isinstance(item, dict):
                        params[item.get("name")] = item.get("value")
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        params[item[0]] = item[1]
                hunt_id = str(params.get("hunt_id") or "").strip()
                if not hunt_id:
                    return _error_response("Missing hunt_id", status=400)
                run = _latest_run(session_key, hunt_id)
                return _json_response({"status": "success", "run": _serialize_run(run) if run else None})

            if method != "POST":
                return _error_response("Method not supported", status=405)

            payload = _payload_from_request(request)
            hunt_id = str(payload.get("hunt_id") or "").strip()
            if not hunt_id:
                return _error_response("Missing hunt_id", status=400)

            username = _username_from_request(request)
            now_epoch = _now_epoch()
            now_iso = _now_iso()
            action = str(payload.get("action") or "generate").strip().lower()
            run_id = str(payload.get("run_id") or "").strip()

            if action == "save":
                if not run_id:
                    return _error_response("Missing run_id", status=400)
                existing = _kv_get(session_key, RUNS_COLLECTION, run_id)
                if not existing:
                    return _error_response("Run not found", status=404)
                if existing.get("hunt_id") != hunt_id:
                    return _error_response("Run/hunt mismatch", status=400)

                updated = dict(existing)
                updated["status"] = str(payload.get("status") or existing.get("status") or "active").strip().lower()
                updated["operator_notes"] = str(payload.get("operator_notes") or "").strip()
                updated["captured_evidence"] = str(payload.get("captured_evidence") or "").strip()
                steps = payload.get("steps")
                if isinstance(steps, list):
                    for step in steps:
                        if isinstance(step, dict):
                            step["status"] = str(step.get("status") or "pending").strip().lower()
                    updated["steps_json"] = json.dumps(steps)
                updated["updated_at"] = now_iso
                updated["updated_time"] = now_epoch
                updated["updated_by"] = username
                updated["content_hash"] = hashlib.md5(
                    "{}|{}|{}|{}".format(
                        run_id,
                        updated.get("status", ""),
                        updated.get("captured_evidence", ""),
                        updated.get("operator_notes", ""),
                    ).encode("utf-8")
                ).hexdigest()
                if not _kv_upsert(session_key, RUNS_COLLECTION, run_id, updated):
                    return _error_response("Failed to update run", status=500)
                return _json_response({"status": "success", "run": _serialize_run(updated)})

            hunt = _kv_query(session_key, HUNTS_COLLECTION, {"hunt_id": hunt_id})
            hunt_doc = hunt[0] if hunt else None
            if not hunt_doc:
                return _error_response("Hunt not found", status=404)

            signals = _kv_query(session_key, SIGNALS_COLLECTION, {"hunt_id": hunt_id})
            entities = _collect_entities(hunt_doc, signals)
            steps, plan_summary = _build_plan_steps(hunt_doc, signals, entities)
            evidence_gaps = _build_evidence_gaps(hunt_doc, signals, entities)

            if not run_id:
                run_seed = "{}:{}:{}".format(hunt_id, now_epoch, username)
                run_id = "run-{}".format(hashlib.md5(run_seed.encode("utf-8")).hexdigest()[:12])

            entity_summary = []
            for category, _priority in ENTITY_PRIORITY:
                values = entities.get(category) or []
                if not values:
                    continue
                display_values = [item.get("value", "") for item in values[:3] if item.get("value")]
                entity_summary.append(
                    {
                        "category": category,
                        "count": len(values),
                        "sample": values[0]["value"],
                        "values": display_values,
                    }
                )

            existing = _kv_get(session_key, RUNS_COLLECTION, run_id) or {}
            record = dict(existing)
            record.update(
                {
                    "run_id": run_id,
                    "hunt_id": hunt_id,
                    "story_id": str(payload.get("story_id") or hunt_id).strip() or hunt_id,
                    "status": "active",
                    "plan_summary": plan_summary,
                    "steps_json": json.dumps(steps),
                    "entity_summary_json": json.dumps(entity_summary),
                    "evidence_gaps_json": json.dumps(evidence_gaps),
                    "captured_evidence": str(payload.get("captured_evidence") or existing.get("captured_evidence") or "").strip(),
                    "operator_notes": str(payload.get("operator_notes") or existing.get("operator_notes") or "").strip(),
                    "root_signal_title": str((_best_signal(signals) or {}).get("title") or "").strip(),
                    "created_at": existing.get("created_at") or now_iso,
                    "updated_at": now_iso,
                    "created_time": _as_int(existing.get("created_time"), now_epoch) or now_epoch,
                    "updated_time": now_epoch,
                    "created_by": existing.get("created_by") or username,
                    "updated_by": username,
                    "app_managed": 1,
                    "app_version": "vNext",
                    "user_modified": 1,
                }
            )
            record["content_hash"] = hashlib.md5(
                "{}|{}|{}|{}".format(run_id, plan_summary, json.dumps(steps, sort_keys=True), json.dumps(evidence_gaps)).encode("utf-8")
            ).hexdigest()

            if not _kv_upsert(session_key, RUNS_COLLECTION, run_id, record):
                return _error_response("Failed to save run", status=500)

            return _json_response({"status": "success", "run": _serialize_run(record)})
        except Exception as exc:
            return _error_response(str(exc), status=500)
