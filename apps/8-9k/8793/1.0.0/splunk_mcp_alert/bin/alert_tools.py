"""Alert tool definitions and execution logic for Splunk MCP Alert."""

import json
import urllib.parse

# Common alert parameters explicitly defined for MCP client discoverability.
# Any Splunk saved/searches API parameter can also be passed via additional_params.
_COMMON_ALERT_PROPERTIES = {
    "name": {"type": "string", "description": "Alert name"},
    "search": {"type": "string", "description": "SPL search query"},
    "cron_schedule": {"type": "string", "description": "Cron expression for scheduling (e.g. '*/5 * * * *')"},
    "is_scheduled": {"type": "boolean", "description": "Whether alert is scheduled. Default: true"},
    "disabled": {"type": "boolean", "description": "Whether alert is disabled. Default: false"},
    "description": {"type": "string", "description": "Alert description"},
    # Alert trigger conditions
    "alert_type": {"type": "string", "description": "Alert type: 'number of events', 'number of hosts', 'number of sources', 'always', or 'custom'"},
    "alert_comparator": {"type": "string", "description": "Comparator: 'greater than', 'less than', 'equal to', 'rises by', 'drops by', etc."},
    "alert_threshold": {"type": "string", "description": "Threshold value for the comparator"},
    "alert_condition": {"type": "string", "description": "Custom SPL condition (used when alert_type='custom')"},
    # Alert behavior
    "alert.severity": {"type": "string", "description": "Alert severity: 1=Debug, 2=Info, 3=Warn, 4=Error, 5=Critical, 6=Fatal"},
    "alert.digest_mode": {"type": "boolean", "description": "If true, send a single notification for all results. If false, trigger per result"},
    "alert.expires": {"type": "string", "description": "Alert expiration time (e.g. '24h', '7d')"},
    "alert.track": {"type": "boolean", "description": "Whether to track this alert in Triggered Alerts"},
    # Suppression
    "alert.suppress": {"type": "boolean", "description": "Enable alert suppression"},
    "alert.suppress.fields": {"type": "string", "description": "Comma-separated fields for suppression grouping"},
    "alert.suppress.period": {"type": "string", "description": "Suppression period (e.g. '1h', '30m')"},
    # Dispatch / time range
    "dispatch.earliest_time": {"type": "string", "description": "Search time range start (e.g. '-15m', '-1h@h')"},
    "dispatch.latest_time": {"type": "string", "description": "Search time range end (e.g. 'now', '-5m')"},
    "dispatch.ttl": {"type": "string", "description": "Time to live for search artifacts in seconds"},
    "dispatch.buckets": {"type": "integer", "description": "Number of timeline buckets"},
    "dispatch.max_count": {"type": "integer", "description": "Maximum number of results"},
    "dispatch.max_time": {"type": "integer", "description": "Maximum search time in seconds"},
    # Scheduling
    "max_concurrent": {"type": "integer", "description": "Maximum concurrent instances of this search"},
    "realtime_schedule": {"type": "boolean", "description": "Use realtime scheduling. Default: true"},
    "schedule_window": {"type": "string", "description": "Schedule window in minutes or 'auto'"},
    "schedule_priority": {"type": "string", "description": "Schedule priority: 'default', 'higher', 'highest'"},
    "run_on_startup": {"type": "boolean", "description": "Run when Splunk starts"},
    "is_visible": {"type": "boolean", "description": "Whether alert is visible in the UI"},
    # Alert actions
    "actions": {"type": "string", "description": "Comma-separated alert action names (e.g. 'email', 'webhook', 'logevent', 'script')"},
    # Email action
    "action.email.to": {"type": "string", "description": "Email recipients (comma-separated)"},
    "action.email.subject": {"type": "string", "description": "Email subject line"},
    "action.email.format": {"type": "string", "description": "Email format: 'plain', 'html', 'csv', 'raw'"},
    "action.email.sendresults": {"type": "boolean", "description": "Include search results in email"},
    "action.email.inline": {"type": "boolean", "description": "Include results inline in email body"},
    "action.email.sendcsv": {"type": "boolean", "description": "Attach results as CSV"},
    "action.email.sendpdf": {"type": "boolean", "description": "Attach results as PDF"},
    "action.email.cc": {"type": "string", "description": "CC recipients"},
    "action.email.bcc": {"type": "string", "description": "BCC recipients"},
    "action.email.from": {"type": "string", "description": "Sender email address"},
    "action.email.content_type": {"type": "string", "description": "Content type: 'html' or 'plain'"},
    "action.email.message.alert": {"type": "string", "description": "Custom alert email message body"},
    "action.email.priority": {"type": "string", "description": "Email priority: 1=Highest, 3=Normal, 5=Lowest"},
    "action.email.maxresults": {"type": "integer", "description": "Max results to include in email"},
    # Webhook action
    "action.webhook.param.url": {"type": "string", "description": "Webhook URL"},
    # Script action
    "action.script.filename": {"type": "string", "description": "Script filename to execute"},
    # Summary index action
    "action.summary_index._name": {"type": "string", "description": "Summary index name"},
    # Catch-all for any other Splunk API parameter
    "additional_params": {
        "type": "object",
        "description": "Any other Splunk saved/searches API parameters not listed above (e.g. {'action.webhook.param.user_agent': 'MCP', 'auto_summarize': true}). See Splunk REST API docs for the full list of 400+ parameters.",
        "additionalProperties": True,
    },
}

# --- ES Detection validation constants ---
_ES_ENDPOINT = "/servicesNS/nobody/SplunkEnterpriseSecuritySuite/saved/searches"
_VALID_SEVERITIES = {"informational", "low", "medium", "high", "critical"}
_SEVERITY_MAP = {
    "1": "informational", "2": "low", "3": "medium", "4": "high", "5": "critical",
    "info": "informational",
}
_VALID_SECURITY_DOMAINS = {"access", "endpoint", "network", "threat", "identity"}
_VALID_RISK_OBJECT_TYPES = {"system", "user", "other"}


def _validate_es_detection(data, is_update=False):
    """Validate and auto-complete parameters for ES detection rules.

    Args:
        data: Mutable dict of parameters. Modified in-place.
        is_update: If True, skip required-field checks for fields that
                   are not being updated (e.g. search, cron_schedule).

    Raises ValueError with descriptive message on validation failure.
    Mutates ``data`` in-place to inject required defaults.
    """
    # === 1. Business logic validation (LLM-provided params) ===

    # name: must end with " - Rule"
    name = data.get("name", "")
    if not name:
        raise ValueError("ES detection rule requires a non-empty 'name'")
    if not name.endswith(" - Rule"):
        data["name"] = name + " - Rule"

    # search: non-empty (only required on create)
    if not is_update and not data.get("search"):
        raise ValueError("ES detection rule requires a non-empty 'search' (SPL query)")

    # severity: validate and normalize
    raw_severity = data.get("severity", "")
    severity = str(raw_severity).strip().lower() if raw_severity else ""
    if severity in _SEVERITY_MAP:
        severity = _SEVERITY_MAP[severity]
    if severity and severity not in _VALID_SEVERITIES:
        raise ValueError(
            f"Invalid severity '{raw_severity}'. "
            f"Must be one of: {sorted(_VALID_SEVERITIES)}"
        )
    if severity:
        data["action.notable.param.severity"] = severity
    data.pop("severity", None)

    # security_domain: validate
    raw_domain = data.get("security_domain", "")
    security_domain = str(raw_domain).strip().lower() if raw_domain else ""
    if security_domain and security_domain not in _VALID_SECURITY_DOMAINS:
        raise ValueError(
            f"Invalid security_domain '{raw_domain}'. "
            f"Must be one of: {sorted(_VALID_SECURITY_DOMAINS)}"
        )
    if security_domain:
        data["action.notable.param.security_domain"] = security_domain
    data.pop("security_domain", None)

    # === 2. ES engine scheduling (auto-inject) ===
    data["is_scheduled"] = "1"
    if not is_update and not data.get("cron_schedule"):
        raise ValueError("ES detection rule requires a 'cron_schedule'")
    data["action.correlationsearch.enabled"] = "1"
    data.setdefault("action.correlationsearch.label", data["name"])

    # === 3. Alert action injection ===
    actions = set(
        a.strip() for a in data.get("actions", "").split(",") if a.strip()
    )

    # Notable event action (default if no actions specified)
    if "notable" in actions or not actions:
        actions.add("notable")
        data["action.notable"] = "1"
        data.setdefault(
            "action.notable.param.rule_description",
            f"Auto-generated detection rule via MCP: {data['name']}",
        )

    # Risk (RBA) action
    if "risk" in actions:
        data["action.risk"] = "1"
        if not data.get("action.risk.param._risk_object"):
            raise ValueError(
                "RBA rule requires 'action.risk.param._risk_object' "
                "(e.g. 'src_ip', 'user')"
            )
        risk_type = data.get("action.risk.param._risk_object_type", "")
        if risk_type and risk_type not in _VALID_RISK_OBJECT_TYPES:
            raise ValueError(
                f"Invalid risk object type '{risk_type}'. "
                f"Must be one of: {sorted(_VALID_RISK_OBJECT_TYPES)}"
            )
        risk_score = data.get("action.risk.param._risk_score", "")
        if not risk_score:
            raise ValueError(
                "RBA rule requires 'action.risk.param._risk_score' "
                "(integer, e.g. '20')"
            )
        try:
            int(risk_score)
        except (ValueError, TypeError):
            raise ValueError(
                f"'action.risk.param._risk_score' must be an integer, "
                f"got '{risk_score}'"
            )

    data["actions"] = ",".join(sorted(actions))


def _create_alert_properties():
    """All properties for create_alert."""
    return dict(_COMMON_ALERT_PROPERTIES)


def _update_alert_properties():
    """All properties for update_alert (name is required, rest are optional)."""
    return dict(_COMMON_ALERT_PROPERTIES)


_ES_DETECTION_PROPERTIES = {
    "name": {"type": "string", "description": "Detection rule name (will auto-append ' - Rule' suffix if missing)"},
    "search": {"type": "string", "description": "SPL search query for the detection"},
    "cron_schedule": {"type": "string", "description": "Cron expression for scheduling (e.g. '*/5 * * * *')"},
    "description": {"type": "string", "description": "Detection rule description"},
    "severity": {
        "type": "string",
        "enum": ["informational", "low", "medium", "high", "critical"],
        "description": "Detection severity. Maps to action.notable.param.severity.",
    },
    "security_domain": {
        "type": "string",
        "enum": ["access", "endpoint", "network", "threat", "identity"],
        "description": "Security domain. Maps to action.notable.param.security_domain.",
    },
    "dispatch.earliest_time": {"type": "string", "description": "Search time range start (e.g. '-15m', '-1h@h')"},
    "dispatch.latest_time": {"type": "string", "description": "Search time range end (e.g. 'now', '-5m')"},
    "actions": {"type": "string", "description": "Comma-separated alert action names. Default: 'notable'. Use 'notable,risk' for RBA rules."},
    "action.notable.param.rule_description": {"type": "string", "description": "Notable event rule description. Auto-generated if not provided."},
    "action.risk.param._risk_object": {"type": "string", "description": "Risk object field name (e.g. 'src_ip', 'user'). Required when actions includes 'risk'."},
    "action.risk.param._risk_object_type": {
        "type": "string",
        "enum": ["system", "user", "other"],
        "description": "Risk object type. Required when actions includes 'risk'.",
    },
    "action.risk.param._risk_score": {"type": "string", "description": "Risk score (integer). Required when actions includes 'risk'."},
    "additional_params": {
        "type": "object",
        "description": "Any other Splunk saved/searches API parameters not listed above.",
        "additionalProperties": True,
    },
}


TOOLS = [
    {
        "name": "create_alert",
        "description": "Create a new standard Splunk alert (scheduled saved search with alert conditions). Supports all Splunk saved/searches API parameters.\n\n## LLM Behavior Guidelines\n1. Use this tool for standard Splunk alerts (infrastructure monitoring, log-based alerting, operational alerts).\n2. For Enterprise Security detection rules, use create_es_detection instead.\n3. Required: name, search, cron_schedule.\n4. Use additional_params for any Splunk API parameter not explicitly listed.",
        "inputSchema": {
            "type": "object",
            "properties": _create_alert_properties(),
            "required": ["name", "search", "cron_schedule"],
        },
    },
    {
        "name": "create_es_detection",
        "description": "Create an Enterprise Security event-based detection rule (correlation search).\n\nThis creates a scheduled saved search under the ES app (SplunkEnterpriseSecuritySuite) with global permissions, so it appears in ES Content Management.\n\n## Auto-injected parameters\nThe following are automatically set and do not need to be provided:\n- is_scheduled = 1\n- action.correlationsearch.enabled = 1\n- action.correlationsearch.label = name\n- actions includes 'notable' by default\n- action.notable = 1\n- Name auto-appended with ' - Rule' if missing\n\n## LLM Behavior Guidelines\n1. Use this tool when the user wants to create a security detection, correlation search, or ES rule.\n2. Required: name, search, cron_schedule.\n3. Recommended: severity, security_domain, description.\n4. For RBA rules, set actions to 'notable,risk' and provide risk object parameters.",
        "inputSchema": {
            "type": "object",
            "properties": _ES_DETECTION_PROPERTIES,
            "required": ["name", "search", "cron_schedule"],
        },
    },
    {
        "name": "list_alerts",
        "description": "List Splunk alerts. Supports pagination and filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of results to return. Default: 30"},
                "offset": {"type": "integer", "description": "Offset for pagination. Default: 0"},
                "search_filter": {"type": "string", "description": "Filter alerts by name"},
                "alerts_only": {"type": "boolean", "description": "Return only scheduled alerts. Default: true"},
            },
            "required": [],
        },
    },
    {
        "name": "get_alert",
        "description": "Get details of a specific Splunk alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the alert"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_alert",
        "description": "Update an existing Splunk alert. Supports all Splunk saved/searches API parameters.",
        "inputSchema": {
            "type": "object",
            "properties": _update_alert_properties(),
            "required": ["name"],
        },
    },
    {
        "name": "delete_alert",
        "description": "Delete a Splunk alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the alert to delete"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_es_detection",
        "description": "Update an existing Enterprise Security detection rule (correlation search).\n\nUpdates the saved search under the ES app namespace (SplunkEnterpriseSecuritySuite). The same validation and auto-injection rules as create_es_detection apply.\n\n## LLM Behavior Guidelines\n1. Use this tool to update ES detection rules created via create_es_detection.\n2. Only the parameters you provide will be updated; others remain unchanged.\n3. Required: name (must match the existing detection rule name).",
        "inputSchema": {
            "type": "object",
            "properties": _ES_DETECTION_PROPERTIES,
            "required": ["name"],
        },
    },
    {
        "name": "delete_es_detection",
        "description": "Delete an Enterprise Security detection rule (correlation search) from the ES app namespace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the ES detection rule to delete"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_fired_alerts",
        "description": "List recently fired Splunk alerts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of results to return. Default: 30"},
            },
            "required": [],
        },
    },
    {
        "name": "acknowledge_alert",
        "description": "Acknowledge a Splunk alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the alert to acknowledge"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "suppress_alert",
        "description": "Suppress a Splunk alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the alert to suppress"},
                "expiration": {"type": "string", "description": "Suppression expiration in seconds"},
            },
            "required": ["name"],
        },
    },
]

_TOOL_REQUIRED = {t["name"]: t["inputSchema"].get("required", []) for t in TOOLS}
_TOOL_NAMES = {t["name"] for t in TOOLS}


def _validate_args(tool_name, arguments):
    if tool_name not in _TOOL_NAMES:
        raise ValueError(f"Unknown tool: {tool_name}")
    required = _TOOL_REQUIRED[tool_name]
    missing = [r for r in required if r not in arguments]
    if missing:
        raise ValueError(f"Missing required arguments: {missing}")


def execute_tool(client, tool_name, arguments):
    _validate_args(tool_name, arguments)
    dispatch = {
        "create_alert": _create_alert,
        "create_es_detection": _create_es_detection,
        "list_alerts": _list_alerts,
        "get_alert": _get_alert,
        "update_alert": _update_alert,
        "delete_alert": _delete_alert,
        "update_es_detection": _update_es_detection,
        "delete_es_detection": _delete_es_detection,
        "list_fired_alerts": _list_fired_alerts,
        "acknowledge_alert": _acknowledge_alert,
        "suppress_alert": _suppress_alert,
    }
    return dispatch[tool_name](client, arguments)


def _create_alert(client, arguments):
    """Create a standard Splunk alert."""
    data = dict(arguments)
    extra = data.pop("additional_params", None)
    if extra and isinstance(extra, dict):
        for k, v in extra.items():
            data.setdefault(k, v)
    data.setdefault("is_scheduled", "1")
    result = client.call_api("POST", "/services/saved/searches", data=data)
    return json.dumps(result)


def _create_es_detection(client, arguments):
    """Create an ES detection rule under the ES app with global permissions."""
    data = dict(arguments)
    extra = data.pop("additional_params", None)
    if extra and isinstance(extra, dict):
        for k, v in extra.items():
            data.setdefault(k, v)
    _validate_es_detection(data)
    # Create under ES app namespace
    result = client.call_api(
        "POST",
        _ES_ENDPOINT,
        data=data,
    )
    # Set sharing to global so it appears in ES Content Management
    name = urllib.parse.quote(data["name"], safe="")
    try:
        client.call_api(
            "POST",
            f"{_ES_ENDPOINT}/{name}/acl",
            data={"sharing": "global", "owner": "nobody"},
        )
    except Exception as e:
        result["warning"] = (
            f"Detection rule created but failed to set global sharing: {e}. "
            "Manually set sharing to 'Global' in Splunk UI."
        )
    return json.dumps(result)


def _list_alerts(client, arguments):
    count = arguments.get("count", 30)
    offset = arguments.get("offset", 0)
    alerts_only = arguments.get("alerts_only", True)
    params = {"count": count, "offset": offset, "output_mode": "json"}
    if "search_filter" in arguments:
        search = arguments["search_filter"]
        if alerts_only:
            search = f"({search}) is_scheduled=1 AND alert_type!=always"
        params["search"] = search
    elif alerts_only:
        params["search"] = "is_scheduled=1 AND alert_type!=always"
    result = client.call_api("GET", "/services/saved/searches", params=params)
    return json.dumps(result)


def _get_alert(client, arguments):
    name = urllib.parse.quote(arguments["name"], safe="")
    result = client.call_api("GET", f"/services/saved/searches/{name}", params=None, data=None)
    return json.dumps(result)


def _update_alert(client, arguments):
    """Update alert — pass through all parameters to the Splunk API."""
    name = urllib.parse.quote(arguments["name"], safe="")
    data = {k: v for k, v in arguments.items() if k != "name"}
    extra = data.pop("additional_params", None)
    if extra and isinstance(extra, dict):
        for k, v in extra.items():
            data.setdefault(k, v)
    result = client.call_api("POST", f"/services/saved/searches/{name}", data=data)
    return json.dumps(result)


def _delete_alert(client, arguments):
    name = urllib.parse.quote(arguments["name"], safe="")
    result = client.call_api("DELETE", f"/services/saved/searches/{name}", params=None, data=None)
    return json.dumps(result)


def _update_es_detection(client, arguments):
    """Update an ES detection rule under the ES app namespace."""
    name_raw = arguments["name"]
    name = urllib.parse.quote(name_raw, safe="")
    data = {k: v for k, v in arguments.items() if k != "name"}
    extra = data.pop("additional_params", None)
    if extra and isinstance(extra, dict):
        for k, v in extra.items():
            data.setdefault(k, v)
    # Run ES validation with name included
    data["name"] = name_raw
    _validate_es_detection(data, is_update=True)
    data.pop("name", None)
    result = client.call_api("POST", f"{_ES_ENDPOINT}/{name}", data=data)
    return json.dumps(result)


def _delete_es_detection(client, arguments):
    """Delete an ES detection rule from the ES app namespace."""
    name = urllib.parse.quote(arguments["name"], safe="")
    result = client.call_api("DELETE", f"{_ES_ENDPOINT}/{name}", params=None, data=None)
    return json.dumps(result)


def _list_fired_alerts(client, arguments):
    count = arguments.get("count", 30)
    params = {"count": count, "output_mode": "json"}
    result = client.call_api("GET", "/services/alerts/fired_alerts", params=params)
    return json.dumps(result)


def _acknowledge_alert(client, arguments):
    name = urllib.parse.quote(arguments["name"], safe="")
    result = client.call_api("POST", f"/services/saved/searches/{name}/acknowledge", params=None, data=None)
    return json.dumps(result)


def _suppress_alert(client, arguments):
    name = urllib.parse.quote(arguments["name"], safe="")
    if "expiration" in arguments:
        result = client.call_api("POST", f"/services/saved/searches/{name}/suppress",
                                 data={"expiration": arguments["expiration"]})
    else:
        result = client.call_api("POST", f"/services/saved/searches/{name}/suppress", params=None, data=None)
    return json.dumps(result)
