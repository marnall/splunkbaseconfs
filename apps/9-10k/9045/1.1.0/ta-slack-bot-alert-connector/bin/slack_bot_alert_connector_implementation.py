
"""Implementation for the Slack Bot Alert Connector for Splunk custom alert action.

Splunk calls ``process_event`` through ``slack_bot_alert_connector.py`` when a
saved search alert fires. This module reads the configured Slack settings,
submits the alert to Slack, optionally joins the channel, and keeps secrets out
of logs and request bodies.
"""

import json
import re
from fnmatch import fnmatch
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

# Splunk runtimes can differ in which third-party libraries are available.
# Prefer requests when present, but keep a standard-library fallback for Splunk
# 10 Cloud compatibility and easier packaging.
try:
    import requests
except ImportError:
    requests = None


# Match Slack token families such as xoxb, xoxa, xoxp, xoxr, and xoxs.
SLACK_TOKEN_PATTERN = re.compile(r"\bxox[a-zA-Z]-[A-Za-z0-9-]+\b")
TOKEN_FIELD_PATTERN = re.compile(r"(?i)(token\s*[=:]\s*)[^\s,&]+")
AUTH_HEADER_PATTERN = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,&]+")
URL_PATTERN = re.compile(r"https?://[^\s>]+")
FIELD_PAIR_PATTERN = re.compile(r"([A-Za-z0-9_.-]+):\s*(.+?)(?=\s{2,}[A-Za-z0-9_.-]+:\s*|$)")
SLACK_API_TIMEOUT_SECONDS = 30
LOCAL_WEB_HOSTS = {"127.0.0.1", "localhost"}
EMPTY_METADATA_LINE_PATTERN = re.compile(r"^(title|actions|author|app):[\s,;:]*$", re.IGNORECASE)
DECORATIVE_LINE_PATTERN = re.compile(r"^[=\-_*#\s]{4,}$")
TOKEN_PLACEHOLDER_PATTERN = re.compile(r"^\$[A-Za-z0-9_.-]+\$$")


def redact_sensitive_text(value, *secrets):
    """Return log-safe text by masking configured secrets and token patterns."""
    text = "" if value is None else str(value)
    for secret in secrets:
        if secret:
            text = text.replace(str(secret), "[REDACTED]")
    text = SLACK_TOKEN_PATTERN.sub(lambda match: match.group(0).split("-", 1)[0] + "-[REDACTED]", text)
    text = TOKEN_FIELD_PATTERN.sub(r"\1[REDACTED]", text)
    return AUTH_HEADER_PATTERN.sub(r"\1[REDACTED]", text)


def log_error(helper, message, *secrets):
    """Write an error through Splunk's helper after applying redaction."""
    helper.log_error(redact_sensitive_text(message, *secrets))


def log_warn(helper, message, *secrets):
    """Write a warning through Splunk's helper after applying redaction."""
    helper.log_warn(redact_sensitive_text(message, *secrets))


def slack_auth_headers(token):
    """Build Slack Web API auth headers without placing the token in form data."""
    return {"Authorization": "Bearer {}".format(token)}


def is_truthy(value):
    """Normalize Splunk alert action boolean values from strings or numbers."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


def normalize_base_url(base_url):
    """Validate and normalize the configured Slack API base URL."""
    normalized = (base_url or "").strip().rstrip("/")
    if not normalized.lower().startswith("https://"):
        raise ValueError("Slack API base URL must use HTTPS.")
    return normalized


def normalize_channel_reference(channel):
    """Trim whitespace and a leading # for Slack channel-name lookups."""
    normalized = (channel or "").strip()
    if normalized.startswith("#"):
        return normalized[1:]
    return normalized


def get_helper_setting(helper, key, default=""):
    """Safely fetch a runtime setting exposed by the Splunk alert helper."""
    settings = getattr(helper, "settings", None)
    if isinstance(settings, dict):
        value = settings.get(key)
        if value not in (None, ""):
            return value
    return default


def get_helper_events(helper):
    """Safely read search-result events that triggered the current alert."""
    try:
        events = helper.get_events()
    except Exception:
        return []

    if not events:
        return []
    if isinstance(events, list):
        return events
    return list(events)


def post_slack_api(url, headers, data):
    """Post form data to Slack and return the parsed JSON response."""
    if requests is not None:
        response = requests.post(url, headers=headers, data=data, timeout=SLACK_API_TIMEOUT_SECONDS)
        return json.loads(response.text)

    # urllib is available in the Python standard library and avoids adding a
    # package dependency when Splunk does not ship requests in the runtime.
    encoded_data = urlencode(data).encode("utf-8")
    request = Request(url, data=encoded_data, headers=headers)
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(request, timeout=SLACK_API_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def slack_escape_text(value):
    """Escape reserved Slack markdown characters without changing plain text."""
    return (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_inline_urls(value):
    """Convert plain URLs in text into Slack mrkdwn links."""
    text = value or ""
    chunks = []
    last_index = 0

    for match in URL_PATTERN.finditer(text):
        chunks.append(slack_escape_text(text[last_index:match.start()]))
        chunks.append("<{0}>".format(match.group(0)))
        last_index = match.end()

    chunks.append(slack_escape_text(text[last_index:]))
    return "".join(chunks)


def extract_field_pairs(line):
    """Extract repeated key:value pairs separated by wide spaces on one line."""
    matches = FIELD_PAIR_PATTERN.findall(line or "")
    return [(key.strip(), value.strip()) for key, value in matches if key.strip() and value.strip()]


def extract_search_url(line):
    """Extract a Splunk link from a leading search: line when present."""
    normalized = (line or "").strip()
    if not normalized.lower().startswith("search:"):
        return ""
    match = URL_PATTERN.search(normalized)
    return match.group(0) if match else ""


def is_empty_metadata_line(line):
    """Return true for placeholder metadata rows that add noise but no value."""
    return bool(EMPTY_METADATA_LINE_PATTERN.match((line or "").strip()))


def is_decorative_line(line):
    """Return true for separator-only lines that should not appear in Slack."""
    return bool(DECORATIVE_LINE_PATTERN.match((line or "").strip()))


def is_token_placeholder_line(line):
    """Return true when a line is only a Splunk replacement token like $name$."""
    return bool(TOKEN_PLACEHOLDER_PATTERN.match((line or "").strip()))


def choose_title_icon(emoji, fallback_icon):
    """Use the configured emoji when present, otherwise fall back to the style icon."""
    normalized = (emoji or "").strip()
    if normalized:
        return normalized
    return fallback_icon


def format_title_line(line, alert_icon):
    """Turn the first alert line into a stronger Slack title."""
    normalized = (line or "").strip()
    if normalized.lower().startswith("alert:"):
        title = normalized.split(":", 1)[1].strip()
        return "{0} *{1}*".format(alert_icon, format_inline_urls(title))
    return "{0} *{1}*".format(alert_icon, format_inline_urls(normalized))


def format_body_line(line):
    """Apply light mrkdwn formatting to body text lines."""
    normalized = (line or "").strip()
    if not normalized:
        return ""
    if normalized.lower().startswith("runbook:"):
        value = normalized.split(":", 1)[1].strip()
        return "*Runbook:* {0}".format(format_inline_urls(value))
    return format_inline_urls(normalized)


def style_field_value(label, value):
    """Add light semantic styling to common field values."""
    normalized_label = (label or "").strip().lower()
    normalized_value = (value or "").strip()
    lowered_value = normalized_value.lower()

    if normalized_label == "status":
        if lowered_value in {"failed", "failure", "error", "critical", "down"}:
            return ":red_circle: *{0}*".format(format_inline_urls(normalized_value))
        if lowered_value in {"warning", "degraded"}:
            return ":large_orange_circle: *{0}*".format(format_inline_urls(normalized_value))
        if lowered_value in {"success", "succeeded", "resolved", "healthy", "ok", "passed"}:
            return ":large_green_circle: *{0}*".format(format_inline_urls(normalized_value))

    return format_inline_urls(normalized_value)


def choose_alert_chrome(title_line, body_lines, fields):
    """Pick a visual accent color and fallback icon based on alert language."""
    content = " ".join(
        [title_line or ""] + list(body_lines or []) + ["{0} {1}".format(label, value) for label, value in (fields or [])]
    ).lower()
    tokens = set(re.findall(r"[a-z0-9_]+", content))

    if "critical" in tokens or "sev1" in tokens or "fatal" in tokens or "panic" in tokens:
        return {"color": "#E3B341", "icon": ":rotating_light:", "footer": "Splunk Alert"}
    if any(term in tokens for term in ("failed", "failure", "error", "down", "stopped", "timeout", "timed", "out")):
        return {"color": "#E3B341", "icon": ":bell:", "footer": "Splunk Alert"}
    if any(term in tokens for term in ("warning", "degraded", "retry", "backlog")):
        return {"color": "#ECB22E", "icon": ":warning:", "footer": "Splunk Warning"}
    if any(term in tokens for term in ("success", "resolved", "healthy", "ok", "passed")):
        return {"color": "#2EB67D", "icon": ":white_check_mark:", "footer": "Splunk Recovery"}
    return {"color": "#E3B341", "icon": ":bell:", "footer": "Splunk Alert"}


def format_body_block(body_lines):
    """Render narrative lines as a clean Slack body block."""
    formatted_lines = [format_body_line(line) for line in (body_lines or []) if line.strip()]
    if not formatted_lines:
        return ""
    return "\n".join(formatted_lines)


def build_results_url(helper):
    """Construct a best-effort Splunk Web deep link for the current search SID."""
    sid = get_helper_setting(helper, "sid")
    server_uri = get_helper_setting(helper, "server_uri")
    if not sid or not server_uri:
        return ""

    parsed = urlsplit(server_uri)
    hostname = parsed.hostname
    if not hostname:
        return ""

    scheme = "http" if hostname in LOCAL_WEB_HOSTS else "https"
    netloc = "{0}:8000".format(hostname)
    query = urlencode({"sid": sid})
    return urlunsplit((scheme, netloc, "/en-US/app/search/search", query, ""))


def build_alert_url(helper):
    """Construct a best-effort Splunk Web link to the saved alert definition."""
    server_uri = get_helper_setting(helper, "server_uri")
    search_name = get_helper_setting(helper, "search_name")
    app = get_helper_setting(helper, "app", "search") or "search"
    if not server_uri or not search_name:
        return ""

    parsed = urlsplit(server_uri)
    hostname = parsed.hostname
    if not hostname:
        return ""

    scheme = "http" if hostname in LOCAL_WEB_HOSTS else "https"
    netloc = "{0}:8000".format(hostname)
    alert_ref = "/servicesNS/nobody/{0}/saved/searches/{1}".format(app, search_name)
    query = urlencode({"s": alert_ref})
    return urlunsplit((scheme, netloc, "/app/{0}/alert".format(quote(app, safe="")), query, ""))


def build_footer_context(helper, chrome):
    """Build a compact footer with search metadata."""
    return [{"type": "mrkdwn", "text": "*{0}*".format(chrome["footer"])}]


def normalize_attachment_mode(value):
    """Map configured attachment mode values to a supported rendering mode."""
    normalized = (value or "").strip().lower()
    if normalized in {"none", "link_to_alert", "message_attachment"}:
        return normalized
    return "message_attachment"


def collect_configured_fields(helper, field_names):
    """Extract selected fields from the first matching alert event."""
    requested_fields = [name.strip() for name in (field_names or "").split(",") if name.strip()]
    if not requested_fields:
        return []

    events = get_helper_events(helper)
    if not events:
        return []

    for event in events:
        if not isinstance(event, dict):
            continue

        collected_fields = []
        for requested_field in requested_fields:
            for label, value in event.items():
                if not fnmatch(label, requested_field):
                    continue
                if isinstance(value, (dict, list)):
                    rendered_value = json.dumps(value, sort_keys=True)
                else:
                    rendered_value = "" if value is None else str(value)
                rendered_value = rendered_value.strip()
                if rendered_value:
                    collected_fields.append((label, rendered_value))
                    break

        return collected_fields

    return []


def build_slack_message_payload(helper, message, attachment_mode, field_names, emoji):
    """Convert a plain Splunk alert body into a polished Slack alert card."""
    normalized_lines = [line.strip() for line in (message or "").splitlines()]
    title_line = None
    body_lines = []
    fields = collect_configured_fields(helper, field_names)
    explicit_results_url = ""

    for line in normalized_lines:
        if not line:
            if body_lines and body_lines[-1] != "":
                body_lines.append("")
            continue

        if title_line is None:
            title_line = line
            continue

        explicit_results_url = explicit_results_url or extract_search_url(line)
        if explicit_results_url and extract_search_url(line):
            continue

        if is_empty_metadata_line(line):
            continue

        if is_decorative_line(line):
            continue

        parsed_fields = extract_field_pairs(line)
        if parsed_fields and len(parsed_fields) >= 1 and not fields:
            fields.extend(parsed_fields)

        body_lines.append(line)

    search_name = get_helper_setting(helper, "search_name")
    if title_line and is_token_placeholder_line(title_line) and search_name:
        title_line = "Alert: {0}".format(search_name)
    alert_line_index = next(
        (index for index, line in enumerate(body_lines) if line.lower().startswith("alert:")),
        None,
    )
    if title_line and not title_line.lower().startswith("alert:") and alert_line_index is not None:
        title_line = body_lines.pop(alert_line_index)
        body_lines.insert(0, normalized_lines[0])
    elif title_line and not title_line.lower().startswith("alert:") and search_name and len(title_line.split()) > 8:
        body_lines.insert(0, title_line)
        title_line = "Alert: {0}".format(search_name)
    elif not title_line and search_name:
        title_line = "Alert: {0}".format(search_name)

    fallback_text = (title_line or search_name or "Splunk alert notification").strip()
    chrome = choose_alert_chrome(title_line, body_lines, fields)
    title_icon = choose_title_icon(emoji, chrome["icon"])
    render_mode = normalize_attachment_mode(attachment_mode)
    alert_url = build_alert_url(helper)
    results_url = explicit_results_url or build_results_url(helper)

    payload = {}
    formatted_body = format_body_block(body_lines)
    if formatted_body:
        payload["text"] = formatted_body

    if render_mode == "message_attachment":
        attachment = {
            "color": chrome["color"],
            "fallback": payload.get("text", fallback_text),
            "mrkdwn_in": ["text", "fields"],
        }

        if title_line:
            attachment["title"] = slack_escape_text(
                format_title_line(title_line, title_icon).replace("*", "").strip()
            )
        if alert_url:
            attachment["title_link"] = alert_url
        if results_url:
            attachment["text"] = "<{0}|Open alert in Splunk> :mag:".format(results_url)
        elif alert_url:
            attachment["text"] = "<{0}|Open alert in Splunk> :mag:".format(alert_url)
        if fields and len(fields) >= 3:
            attachment["fields"] = [
                {
                    "title": slack_escape_text(label),
                    "value": style_field_value(label, value),
                    "short": True,
                }
                for label, value in fields[:8]
            ]
        attachment["footer"] = chrome["footer"]
        payload["attachments"] = json.dumps([attachment])
        payload["text"] = payload.get("text", fallback_text)
        payload["unfurl_links"] = "false"
        payload["unfurl_media"] = "false"
    elif render_mode == "link_to_alert" and results_url:
        payload["text"] = "{0}\n<{1}|Show results in Splunk> :mag:".format(
            payload.get("text", fallback_text),
            results_url,
        ).strip()
    else:
        payload["text"] = payload.get("text", fallback_text)
    return payload

def process_event(helper, *args, **kwargs):
    """Entry point called by Splunk for each triggered alert event."""

    """
    # IMPORTANT
    # Do not remove the anchor macro:start and macro:end lines.
    # These lines are used to generate sample code. If they are
    # removed, the sample code will not be updated when configurations
    # are updated.

    [sample_code_macro:start]

    # The following example gets and sets the log level
    helper.set_log_level(helper.log_level)

    # The following example gets a non-secret setup parameter
    base_url = helper.get_global_setting("base_url")

    # The following example gets the alert action parameters
    channel = helper.get_param("channel")

    emoji = helper.get_param("emoji")

    bot_username = helper.get_param("bot_username")

    message = helper.get_param("message")

    auto_join_channel = helper.get_param("auto_join_channel")


    # The following example adds two sample events ("hello", "world")
    # and writes them to Splunk
    # NOTE: Call helper.writeevents() only once after all events
    # have been added
    helper.addevent("hello", sourcetype="sample_sourcetype")
    helper.addevent("world", sourcetype="sample_sourcetype")
    helper.writeevents(index="summary", host="localhost", source="localhost")

    # The following example gets the events that trigger the alert
    events = helper.get_events()
    for event in events:
        pass

    # helper.settings is a dict that includes environment configuration
    # Example usage: helper.settings["server_uri"]
    [sample_code_macro:end]
    """
    
    # Read the user-configured setup fields and alert action parameters. These
    # values are intentionally not logged because the token, message, channel,
    # and alert payload can contain sensitive operational or customer data.
    token = helper.get_global_setting("token")

    channel = helper.get_param("channel")
    emoji = helper.get_param("emoji")
    bot_username = helper.get_param("bot_username")
    message = helper.get_param("message")
    auto_join_channel = helper.get_param("auto_join_channel")
    attachment_mode = helper.get_param("attachment_mode")
    field_names = helper.get_param("fields")
    base_url = helper.get_global_setting("base_url")

    helper.log_info("Sending Slack alert action")
    post_message(
        helper,
        base_url,
        token,
        channel,
        bot_username,
        message,
        emoji,
        auto_join_channel,
        attachment_mode,
        field_names,
    )
    
    return 0

def post_message(
    helper,
    base_url,
    token,
    channel,
    bot_username,
    message,
    emoji,
    auto_join_channel,
    attachment_mode,
    field_names,
):
    """Send the alert message to Slack and optionally auto-join before retrying."""
    data = {"channel": channel}
    data.update(build_slack_message_payload(helper, message, attachment_mode, field_names, emoji))
    headers = slack_auth_headers(token)
    
    if emoji != "":
        data["icon_emoji"] = emoji

    if bot_username != "":
        data["username"] = bot_username
    
    slack_api_base_url = normalize_base_url(base_url)
    url = slack_api_base_url + "/chat.postMessage"
    
    response_object = post_slack_api(url, headers=headers, data=data)
    
    # If Slack says the bot is missing from the channel, join and retry once.
    # The retry preserves the original alert action behavior without logging the
    # channel name or message body.
    if not response_object["ok"] and response_object["error"] == "not_in_channel" and is_truthy(auto_join_channel):
        helper.log_info("Joining Slack channel before retrying alert action")
        join_channel(helper, slack_api_base_url, token, channel)
        response_object = post_slack_api(url, headers=headers, data=data)

    if not response_object["ok"]:
        log_error(helper, response_object["error"], token)
    else:
        helper.log_info("Successfully posted message to Slack")

def find_channel_id(helper, base_url, token, channel):
    """Resolve a Slack channel name to an ID for the conversations.join call."""
    slack_api_base_url = normalize_base_url(base_url)
    normalized_channel = normalize_channel_reference(channel)
    url = slack_api_base_url + "/conversations.list"
    
    data = {
        'limit': 1000
    }
    headers = slack_auth_headers(token)
    
    response_object = post_slack_api(url, headers=headers, data=data)
    
    if not response_object["ok"]:
         log_error(helper, response_object["error"], token)
    
    if "channels" in response_object:
        for channel_object in response_object["channels"]:
            if channel_object["name"] == normalized_channel:
                return channel_object["id"]
            
        
    while "response_metadata" in response_object and "next_cursor" in response_object["response_metadata"]:
        data["cursor"] = response_object["response_metadata"]["next_cursor"]
        
        response_object = post_slack_api(url, headers=headers, data=data)
        if "channels" in response_object:
            for channel_object in response_object["channels"]:
                if channel_object["name"] == normalized_channel:
                    return channel_object["id"]

    return ""

def join_channel(helper, base_url, token, channel):
    """Join the configured Slack channel so a message retry can succeed."""
    channel_id = find_channel_id(helper, base_url, token, channel)
    
    if channel_id != "":
        slack_api_base_url = normalize_base_url(base_url)
        url = slack_api_base_url + "/conversations.join"
    
        data = {
            'channel' : channel_id
        }
        headers = slack_auth_headers(token)
    
        response_object = post_slack_api(url, headers=headers, data=data)
    
        if not response_object["ok"]:
            log_error(helper, response_object["error"], token)
        elif "warning" in response_object:
            log_warn(helper, response_object["warning"], token)
        else:
            helper.log_info("Successfully joined Slack channel")
    else:
        helper.log_error("No Slack channel ID could be found for configured alert channel")
