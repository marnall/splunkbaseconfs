import json
import urllib
import sys
import hashlib
import base64
import html
import ipaddress
import re
import io
import os
import itertools
import traceback
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from oletools.olevba import VBA_Parser
import html2text
from zipfile import ZipFile, BadZipFile
from datetime import datetime
from email.parser import BytesParser
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from asn1crypto.cms import ContentInfo
from asn1crypto.x509 import Certificate


ACCESS_TOKEN = 'access_token'
TOKEN_CACHE = {}
LOG_DIRECTORY_NAME = 'logs'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.000Z'
DEFAULT_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
PURGE_SUCCESS_STATUS_CODES = {200, 201, 204}
PERMANENT_DELETE_FALLBACK_STATUS_CODES = {404, 405, 501}
REDACTED_KEYS = {
    'authorization',
    'access_token',
    'client_secret',
    'password',
    'contentbytes',
    'body',
    'internet-headers',
}
KNOWN_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "msclkid",
}
COMMON_SECOND_LEVEL_TLDS = {
    "ac",
    "co",
    "com",
    "edu",
    "gov",
    "net",
    "org",
}
EMAIL_ADDRESS_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
KNOWN_URL_SHORTENER_DOMAINS = {
    "amzn.to",
    "bit.ly",
    "buff.ly",
    "cutt.ly",
    "goo.gl",
    "is.gd",
    "lnkd.in",
    "ow.ly",
    "qrco.de",
    "rb.gy",
    "rebrand.ly",
    "s.id",
    "shorturl.at",
    "t.co",
    "tiny.one",
    "tinyurl.com",
    "trib.al",
}
REDIRECT_QUERY_PARAMETER_NAMES = {
    "continue",
    "dest",
    "destination",
    "next",
    "redirect",
    "redirect_uri",
    "redirect_url",
    "return",
    "returnto",
    "target",
    "url",
}
CREDENTIAL_HARVEST_TERMS = {
    "account",
    "auth",
    "authenticate",
    "credential",
    "login",
    "logon",
    "mfa",
    "otp",
    "password",
    "secure",
    "signin",
    "sign-in",
    "unlock",
    "validate",
    "verify",
}
ENCODED_COMMAND_TERMS = {
    "bash",
    "certutil",
    "cmd",
    "curl",
    "ftp",
    "mshta",
    "ping",
    "powershell",
    "pwsh",
    "python",
    "rundll32",
    "scp",
    "sh",
    "ssh",
    "wget",
}
BRAND_KEYWORDS = {
    "adobe",
    "amazon",
    "apple",
    "docusign",
    "dropbox",
    "gmail",
    "google",
    "linkedin",
    "microsoft",
    "office365",
    "okta",
    "onedrive",
    "outlook",
    "paypal",
    "sharepoint",
}
BRAND_KEYWORD_ALLOWED_DOMAINS = {
    "adobe": {"adobe.com"},
    "amazon": {"amazon.com", "amazonaws.com", "amzn.to"},
    "apple": {"apple.com", "icloud.com", "me.com"},
    "docusign": {"docusign.com", "docusign.net"},
    "dropbox": {"dropbox.com", "db.tt"},
    "gmail": {"gmail.com", "google.com", "googlemail.com"},
    "google": {"google.com", "googlemail.com", "youtube.com"},
    "linkedin": {"linkedin.com", "lnkd.in"},
    "microsoft": {
        "aka.ms",
        "live.com",
        "microsoft.com",
        "microsoftonline.com",
        "office.com",
        "office365.com",
        "outlook.com",
        "sharepoint.com",
    },
    "office365": {
        "aka.ms",
        "microsoft.com",
        "microsoftonline.com",
        "office.com",
        "office365.com",
        "outlook.com",
        "sharepoint.com",
    },
    "okta": {"okta.com"},
    "onedrive": {
        "aka.ms",
        "microsoft.com",
        "microsoftonline.com",
        "office.com",
        "office365.com",
        "onedrive.com",
        "outlook.com",
        "sharepoint.com",
    },
    "outlook": {
        "aka.ms",
        "live.com",
        "microsoft.com",
        "microsoftonline.com",
        "office.com",
        "office365.com",
        "outlook.com",
    },
    "paypal": {"paypal.com", "paypalobjects.com"},
    "sharepoint": {
        "aka.ms",
        "microsoft.com",
        "microsoftonline.com",
        "office.com",
        "office365.com",
        "outlook.com",
        "sharepoint.com",
    },
}
TRUSTED_REDIRECTOR_DOMAINS = {
    "aka.ms",
    "amzn.to",
    "db.tt",
    "lnkd.in",
    "t.co",
}
DANGEROUS_ATTACHMENT_EXTENSIONS = {
    "ade",
    "adp",
    "app",
    "apk",
    "bat",
    "chm",
    "cmd",
    "com",
    "cpl",
    "dll",
    "exe",
    "hta",
    "iso",
    "img",
    "jar",
    "js",
    "jse",
    "lib",
    "lnk",
    "mht",
    "mhtml",
    "msi",
    "ps1",
    "reg",
    "scr",
    "sct",
    "url",
    "vb",
    "vbe",
    "vbs",
    "ws",
    "wsc",
    "wsf",
    "wsh",
}
PHISHING_ATTACHMENT_EXTENSIONS = {
    "eml",
    "htm",
    "html",
    "msg",
    "one",
    "pdf",
    "svg",
}
ARCHIVE_ATTACHMENT_EXTENSIONS = {
    "7z",
    "ace",
    "arj",
    "bz2",
    "cab",
    "gz",
    "iso",
    "img",
    "rar",
    "tar",
    "tgz",
    "xz",
    "zip",
}
BENIGN_DISGUISE_EXTENSIONS = {
    "doc",
    "docx",
    "gif",
    "htm",
    "html",
    "jpeg",
    "jpg",
    "pdf",
    "png",
    "ppt",
    "pptx",
    "rtf",
    "svg",
    "txt",
    "xls",
    "xlsx",
}


#Regex statements
url_re = re.compile(r'(http|ftp|https|ftps|scp):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-;]*[\w@?^=%&\/~+#-])?')
domain_re = re.compile(r'\b((?=[a-z0-9-]{1,63}\.)(xn--)?[a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,63}\b')
ipv4_re = re.compile(r'((?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)')
ipv6_re = re.compile(r'(([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))')
pixeltrack_re = re.compile(r'<img[^>]+((width|height)=[\"\']1[\"\'] ?){2}[^>]*>')
base64_blob_re = re.compile(r'(?<![A-Za-z0-9+/=])(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?(?![A-Za-z0-9+/=])')
hex_blob_re = re.compile(r'(?<![A-Fa-f0-9])(?:[A-Fa-f0-9]{2}){8,}(?![A-Fa-f0-9])')
spaced_hex_blob_re = re.compile(r'(?<![A-Fa-f0-9])(?:[A-Fa-f0-9]{2}(?:[\t\r\n ]+)){7,}[A-Fa-f0-9]{2}(?![A-Fa-f0-9])')
encoded_command_re = re.compile(r'\b(?:' + "|".join(sorted(re.escape(term) for term in ENCODED_COMMAND_TERMS)) + r')\b')

ENCODED_CONTENT_DEFAULT_MAX_BLOB_LENGTH = 8192
ENCODED_CONTENT_DEFAULT_MAX_DECODED_PREVIEW_LENGTH = 512
ENCODED_CONTENT_DEFAULT_MAX_BLOBS = 5
ENCODED_CONTENT_RISK_MIN_BASE64_LENGTH = 48
ENCODED_CONTENT_RISK_MIN_HEX_LENGTH = 96

macro_file_types = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
    'application/vnd.ms-excel.sheet.macroenabled.12',
    'application/vnd.ms-excel.template.macroenabled.12',
    'application/vnd.ms-excel.addin.macroenabled.12',
    'application/vnd.ms-excel.sheet.binary.macroenabled.12',
    'application/vnd.ms-excel',
    'application/xml',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.template',
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
    'application/vnd.ms-powerpoint.addin.macroenabled.12',
    'application/vnd.ms-powerpoint.presentation.macroenabled.12',
    'application/vnd.ms-powerpoint.template.macroenabled.12',
    'application/vnd.ms-powerpoint.slideshow.macroenabled.12',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
    'application/vnd.ms-word.document.macroenabled.12',
    'application/vnd.ms-word.template.macroenabled.12'
]


class AnchorTagParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []
        self._current_href = None
        self._text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        self._current_href = attributes.get("href")
        self._text_parts = []

    def handle_data(self, data):
        if self._current_href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or self._current_href is None:
            return
        displayed_text = html.unescape("".join(self._text_parts)).strip()
        self.links.append(
            {
                "displayed_text": displayed_text,
                "href": html.unescape(self._current_href).strip(),
            }
        )
        self._current_href = None
        self._text_parts = []


class HTMLRiskParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.forms_count = 0
        self.remote_images = []
        self.tiny_images = []
        self.hidden_text_segments = []
        self.suspicious_css_elements = []
        self._hidden_stack = []

    def handle_starttag(self, tag, attrs):
        tag_name = tag.lower()
        attributes = dict(attrs)
        style = (attributes.get("style") or "").lower()

        if tag_name == "form":
            self.forms_count += 1

        hidden_by_style = has_hidden_style(style)
        suspicious_css = has_suspicious_css(style)
        if suspicious_css:
            self.suspicious_css_elements.append(
                {
                    "tag": tag_name,
                    "style": style,
                }
            )

        self._hidden_stack.append(bool("hidden" in attributes or hidden_by_style))

        if tag_name == "img":
            src = attributes.get("src")
            normalized_src = normalize_url(src)
            if normalized_src:
                image_details = {
                    "src": normalized_src,
                    "tag": tag_name,
                }
                self.remote_images.append(image_details)
                if is_tiny_image(attributes, style):
                    self.tiny_images.append(image_details)

    def handle_endtag(self, tag):
        if self._hidden_stack:
            self._hidden_stack.pop()

    def handle_data(self, data):
        if not any(self._hidden_stack):
            return
        text = html.unescape(data).strip()
        if text:
            self.hidden_text_segments.append(text)

#Setting minimum interval in TA to 60 seconds and max to 120 seconds
def validate_input(helper, definition):
    interval_in_seconds = int(definition.parameters.get('interval'))
    if (interval_in_seconds < 60):
        raise ValueError("field 'Interval' should be 60 seconds or higher")


def get_run_stats(helper):
    stats = getattr(helper, "_run_stats", None)
    if stats is None:
        stats = {
            "messages_fetched": 0,
            "messages_processed": 0,
            "messages_ingested": 0,
            "messages_processing_failed": 0,
            "messages_purge_failed": 0,
            "messages_skipped_pre_purge": 0,
            "pages_fetched": 0,
            "retry_count": 0,
            "throttle_events": 0,
            "calendar_events_deleted": 0,
        }
        setattr(helper, "_run_stats", stats)
    return stats


def is_debug_enabled(helper):
    return bool(helper.get_arg('debug_mode'))


def get_debug_sample_limit(helper):
    value = helper.get_arg('debug_sample_limit')
    if value in (None, ""):
        return 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def get_positive_int_arg(helper, arg_name, default_value, minimum=1):
    value = helper.get_arg(arg_name)
    if value in (None, ""):
        return default_value
    try:
        return max(int(value), minimum)
    except (TypeError, ValueError):
        return default_value


def get_debug_message_id(helper):
    value = helper.get_arg('debug_message_id')
    if value in (None, ""):
        return None
    return value


def should_emit_message_debug(helper, message_id=None):
    if not is_debug_enabled(helper):
        return False

    target_message_id = get_debug_message_id(helper)
    if target_message_id:
        return message_id == target_message_id

    sample_limit = get_debug_sample_limit(helper)
    if sample_limit <= 0:
        return True

    stats = get_run_stats(helper)
    return stats["messages_processed"] <= sample_limit


def sanitize_value(value, key_name=None):
    if key_name and key_name.lower() in REDACTED_KEYS:
        return "<redacted>"
    if isinstance(value, dict):
        return {key: sanitize_value(subvalue, key) for key, subvalue in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "...<truncated>"
    return value


def summarize_url(url):
    if "://" not in url:
        return url
    parts = url.split("://", 1)[1].split("/", 1)
    if len(parts) == 1:
        return "/"
    return "/" + parts[1]


def build_log_context(helper, **extra):
    context = {
        "input": getattr(helper, "input_name", "o365_email"),
        "tenant": helper.get_arg('tenant'),
        "mailbox": helper.get_arg('audit_email_account'),
        "endpoint": helper.get_arg('endpoint'),
    }
    for key, value in extra.items():
        if value not in (None, "", []):
            context[key] = value
    return context


def format_log_message(message, **context):
    if not context:
        return message
    ordered = ", ".join("{}={}".format(key, sanitize_value(value, key)) for key, value in sorted(context.items()))
    return "{} | {}".format(message, ordered)


def log_info(helper, message, **context):
    helper.log_info(format_log_message(message, **context))


def log_error(helper, message, **context):
    helper.log_error(format_log_message(message, **context))


def log_warning(helper, message, **context):
    helper.log_info(format_log_message("WARNING: " + message, **context))


def log_debug(helper, message, **context):
    helper.log_debug(format_log_message(message, **context))


def log_request_debug(helper, method, url, attempt=1, payload=None, message_id=None):
    if not should_emit_message_debug(helper, message_id):
        return
    log_debug(
        helper,
        "Graph request",
        **build_log_context(
            helper,
            method=method,
            path=summarize_url(url),
            attempt=attempt,
            payload=sanitize_value(payload),
            message_id=message_id,
        )
    )


def log_response_debug(helper, method, url, response, attempt=1, message_id=None):
    if not should_emit_message_debug(helper, message_id):
        return
    log_debug(
        helper,
        "Graph response",
        **build_log_context(
            helper,
            method=method,
            path=summarize_url(url),
            attempt=attempt,
            status_code=response.status_code,
            response_text=sanitize_value(getattr(response, "text", "")),
            message_id=message_id,
        )
    )


def log_message_debug(helper, message, item=None, message_items=None):
    message_id = None if item is None else item.get("id")
    if not should_emit_message_debug(helper, message_id):
        return

    summary = {}
    if item is not None:
        summary.update(
            {
                "message_id": item.get("id"),
                "subject": item.get("subject"),
                "has_attachments": item.get("hasAttachments"),
                "attachment_count": len(item.get("attachments", [])),
                "requested_read_receipt": item.get("isReadReceiptRequested"),
            }
        )
    if message_items is not None:
        summary["emitted_fields"] = sorted(message_items.keys())
    log_debug(helper, message, **build_log_context(helper, **summary))


def log_run_summary(helper, elapsed_seconds):
    stats = get_run_stats(helper)
    log_info(
        helper,
        "Run summary",
        **build_log_context(
            helper,
            elapsed_seconds=round(elapsed_seconds, 3),
            messages_fetched=stats["messages_fetched"],
            messages_processed=stats["messages_processed"],
            messages_ingested=stats["messages_ingested"],
            messages_processing_failed=stats["messages_processing_failed"],
            messages_purge_failed=stats["messages_purge_failed"],
            messages_skipped_pre_purge=stats["messages_skipped_pre_purge"],
            pages_fetched=stats["pages_fetched"],
            retries=stats["retry_count"],
            throttle_events=stats["throttle_events"],
            calendar_events_deleted=stats["calendar_events_deleted"],
        )
    )


def get_token_cache_key(helper):
    account = helper.get_arg('global_account')
    return (
        helper.get_arg('endpoint'),
        helper.get_arg('tenant'),
        account['username'],
    )


def get_retry_after_seconds(response, attempt):
    retry_after_header = getattr(response, "headers", {}).get("Retry-After")
    if retry_after_header:
        try:
            return max(int(retry_after_header), 1)
        except ValueError:
            pass
    return min(2 ** attempt, 30)


def send_request_with_retry(
    helper,
    url,
    method,
    headers=None,
    parameters=None,
    payload=None,
    timeout=(15.0, 90.0),
    max_attempts=4,
):
    last_exception = None

    for attempt in range(max_attempts):
        log_request_debug(helper, method, url, attempt + 1, payload=payload)
        try:
            response = helper.send_http_request(
                url,
                method,
                headers=headers,
                parameters=parameters,
                payload=payload,
                timeout=timeout,
            )
        except Exception as exc:
            last_exception = exc
            if attempt == max_attempts - 1:
                raise

            delay = min(2 ** attempt, 30)
            get_run_stats(helper)["retry_count"] += 1
            log_warning(
                helper,
                "Request failed; retrying",
                **build_log_context(
                    helper,
                    method=method,
                    path=summarize_url(url),
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    retry_in_seconds=delay,
                    error=str(exc),
                )
            )
            time.sleep(delay)
            continue

        log_response_debug(helper, method, url, response, attempt + 1)
        if response.status_code not in DEFAULT_RETRY_STATUS_CODES:
            return response

        if attempt == max_attempts - 1:
            return response

        delay = get_retry_after_seconds(response, attempt)
        stats = get_run_stats(helper)
        stats["retry_count"] += 1
        if response.status_code == 429:
            stats["throttle_events"] += 1
        log_warning(
            helper,
            "Received retryable response; retrying",
            **build_log_context(
                helper,
                method=method,
                path=summarize_url(url),
                attempt=attempt + 1,
                max_attempts=max_attempts,
                retry_in_seconds=delay,
                status_code=response.status_code,
            )
        )
        time.sleep(delay)

    if last_exception:
        raise last_exception

    raise RuntimeError("Request failed without a response: {} {}".format(method, url))

#Obtain access token via oauth2
def _get_access_token(helper):
    
    if helper.get_arg('endpoint') == 'worldwide':
        login_url = 'https://login.microsoftonline.com/'
        graph_url = 'https://graph.microsoft.com/'
    elif helper.get_arg('endpoint') == 'gcchigh':
        login_url = 'https://login.microsoftonline.us/'
        graph_url = 'https://graph.microsoft.us/'
        
    cache_key = get_token_cache_key(helper)
    now = datetime.utcnow().timestamp()
    cached_token = TOKEN_CACHE.get(cache_key)

    if cached_token is None or now >= cached_token['expires_at']:
        _data = {
            'client_id': helper.get_arg('global_account')['username'],
            'scope': graph_url + '.default',
            'client_secret': helper.get_arg('global_account')['password'],
            'grant_type': 'client_credentials',
            'Content-Type': 'application/x-www-form-urlencoded'
            }
        _url = login_url + helper.get_arg('tenant') + '/oauth2/v2.0/token'
        if (sys.version_info > (3, 0)):
            log_info(helper, "Getting auth token", **build_log_context(helper))
            access_token = send_request_with_retry(
                helper,
                _url,
                "POST",
                payload=urllib.parse.urlencode(_data),
                timeout=(15.0, 30.0),
            ).json()
        else:
            log_info(helper, "Getting auth token", **build_log_context(helper))
            access_token = send_request_with_retry(
                helper,
                _url,
                "POST",
                payload=urllib.urlencode(_data),
                timeout=(15.0, 30.0),
            ).json()

        expires_in = int(access_token.get("expires_in", 3600))
        TOKEN_CACHE[cache_key] = {
            'token': access_token[ACCESS_TOKEN],
            'expires_at': now + max(expires_in - 60, 0),
        }
        return access_token[ACCESS_TOKEN]

    else:
        return cached_token['token']

#Function to write events to Splunk
def _write_events(helper, ew, messages=None):
    if messages:
        for message in messages:
            event_time = None
            date_time = message.get('DateTime')
            if date_time:
                try:
                    event_time = datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                except ValueError:
                    log_debug(helper, "Unable to parse message DateTime for event time", **build_log_context(helper, date_time=date_time))

            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                time=event_time,
                data=json.dumps(message))
            ew.write_event(event)

def extract_email_address(value):
    try:
        return value['emailAddress']['address']
    except (KeyError, TypeError):
        return None

def extract_email_addresses(values):
    if not isinstance(values, list):
        return []

    addresses = []
    for value in values:
        address = extract_email_address(value)
        if address:
            addresses.append(address)
    return addresses


def extract_display_name(value):
    try:
        return value['emailAddress'].get('name')
    except (KeyError, TypeError, AttributeError):
        return None


def extract_display_names(values):
    if not isinstance(values, list):
        return []

    display_names = []
    for value in values:
        name = extract_display_name(value)
        if name:
            display_names.append(name)
    return display_names


def extract_domain_from_address(address):
    if not address or "@" not in address:
        return None
    return normalize_hostname(address.rsplit("@", 1)[1])


def normalize_hostname(hostname):
    if not hostname:
        return None
    normalized = hostname.strip().strip(".").lower()
    if not normalized:
        return None
    try:
        return normalized.encode("idna").decode("ascii")
    except UnicodeError:
        return normalized


def is_ip_literal(hostname):
    normalized = normalize_hostname(hostname)
    if not normalized:
        return False
    try:
        ipaddress.ip_address(normalized)
        return True
    except ValueError:
        return False


def get_registered_domain(hostname):
    normalized = normalize_hostname(hostname)
    if not normalized:
        return None
    if is_ip_literal(normalized):
        return normalized

    parts = normalized.split(".")
    if len(parts) <= 2:
        return normalized
    if len(parts[-1]) == 2 and parts[-2] in COMMON_SECOND_LEVEL_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def normalize_url(value):
    if not value:
        return None

    candidate = html.unescape(value).strip()
    if not candidate:
        return None
    if candidate.startswith("www."):
        candidate = "https://" + candidate
    if "://" not in candidate and domain_re.match(candidate):
        candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    if not parsed.scheme or not parsed.netloc:
        return None
    if parsed.scheme.lower() not in ("http", "https"):
        return None

    hostname = normalize_hostname(parsed.hostname)
    if not hostname:
        return None

    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key.startswith("utm_") or lowered_key in KNOWN_TRACKING_QUERY_KEYS:
            continue
        query_items.append((key, value))

    path = parsed.path or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            hostname,
            path,
            "",
            urlencode(query_items, doseq=True),
            "",
        )
    )


def looks_like_locator_text(value):
    if not value:
        return False
    candidate = value.strip()
    if not candidate:
        return False
    if EMAIL_ADDRESS_RE.match(candidate):
        return True
    if "://" in candidate or candidate.startswith("www."):
        return True
    return bool(domain_re.match(candidate))


def parse_displayed_locator(displayed_text):
    if not displayed_text:
        return (None, None, None)

    candidate = displayed_text.strip().strip("<>")
    if EMAIL_ADDRESS_RE.match(candidate):
        domain = extract_domain_from_address(candidate)
        return (candidate.lower(), candidate.lower(), domain)

    normalized_url = normalize_url(candidate)
    if normalized_url:
        parsed = urlparse(normalized_url)
        return (candidate, normalized_url, get_registered_domain(parsed.hostname))

    return (candidate, None, None)


def style_contains_any(style, values):
    lowered = (style or "").lower().replace(" ", "")
    return any(value in lowered for value in values)


def has_hidden_style(style):
    return style_contains_any(
        style,
        (
            "display:none",
            "visibility:hidden",
            "opacity:0",
            "font-size:0",
            "max-height:0",
            "max-width:0",
            "height:0",
            "width:0",
            "color:transparent",
            "text-indent:-9999",
            "left:-9999",
            "top:-9999",
        ),
    )


def has_suspicious_css(style):
    return style_contains_any(
        style,
        (
            "display:none",
            "visibility:hidden",
            "opacity:0",
            "font-size:0",
            "position:absolute",
            "position:fixed",
            "text-indent:-9999",
            "left:-9999",
            "top:-9999",
            "z-index:-",
            "color:transparent",
        ),
    )


def extract_dimension_value(value):
    if value is None:
        return None
    try:
        matched = re.search(r"\d+", str(value))
        if not matched:
            return None
        return int(matched.group(0))
    except (TypeError, ValueError):
        return None


def is_tiny_image(attributes, style):
    width = extract_dimension_value(attributes.get("width"))
    height = extract_dimension_value(attributes.get("height"))
    if width is not None and height is not None and width <= 1 and height <= 1:
        return True
    return style_contains_any(
        style,
        (
            "width:1px",
            "height:1px",
            "width:0",
            "height:0",
            "max-width:1px",
            "max-height:1px",
        ),
    )


def get_attachment_name(attachment_data):
    return attachment_data.get("name") or attachment_data.get("filename")


def get_attachment_extensions(attachment_name):
    if not attachment_name or "." not in attachment_name:
        return []
    return [part.lower() for part in attachment_name.split(".")[1:] if part]


def classify_attachment_risk(attachment_data):
    attachment_name = get_attachment_name(attachment_data)
    content_type = (attachment_data.get("contentType") or attachment_data.get("content_type") or "").lower()
    odata_type = attachment_data.get("odata_type", "")
    extensions = get_attachment_extensions(attachment_name)
    final_extension = extensions[-1] if extensions else None
    reasons = []
    score = 0

    if (
        odata_type == "#microsoft.graph.itemAttachment"
        or content_type == "message/rfc822"
        or final_extension in ("eml", "msg")
    ):
        reasons.append("embedded_message_attachment")
        score += 25

    if final_extension in DANGEROUS_ATTACHMENT_EXTENSIONS:
        reasons.append("risky_attachment_type")
        score += 40
    elif final_extension in PHISHING_ATTACHMENT_EXTENSIONS:
        reasons.append("risky_attachment_type")
        score += 20

    if (
        len(extensions) >= 2
        and final_extension in DANGEROUS_ATTACHMENT_EXTENSIONS
        and extensions[-2] in BENIGN_DISGUISE_EXTENSIONS
    ):
        reasons.append("double_extension")
        score += 30

    if attachment_data.get("macros_exist"):
        reasons.append("macros_present")
        score += 25

    zip_attention = attachment_data.get("attention")
    if zip_attention:
        reasons.append("archive_extraction_issue")
        score += 15

    if attachment_data.get("zip_files"):
        inner_extensions = [
            inner_extension
            for zip_name in attachment_data.get("zip_files", [])
            for inner_extension in get_attachment_extensions(zip_name)
        ]
        if any(inner_extension in ARCHIVE_ATTACHMENT_EXTENSIONS for inner_extension in inner_extensions):
            reasons.append("nested_archive")
            score += 15

    deduped_reasons = sorted(set(reasons))
    return {
        "attachment_risk_score": min(score, 100),
        "attachment_risk_reasons": deduped_reasons,
        "suspicious_attachment_type": "risky_attachment_type" in deduped_reasons,
        "double_extension": "double_extension" in deduped_reasons,
        "embedded_message_attachment": "embedded_message_attachment" in deduped_reasons,
        "nested_archive": "nested_archive" in deduped_reasons,
        "archive_extraction_issue": "archive_extraction_issue" in deduped_reasons,
        "attachment_macros_present": "macros_present" in deduped_reasons,
    }


def summarize_attachment_risks(attachment_entries):
    risky_attachments = [entry for entry in attachment_entries if entry.get("attachment_risk_score", 0) > 0]
    if not risky_attachments:
        return None

    all_reasons = sorted(
        {
            reason
            for entry in risky_attachments
            for reason in entry.get("attachment_risk_reasons", [])
        }
    )
    return {
        "attachment_risk_score": min(sum(entry.get("attachment_risk_score", 0) for entry in risky_attachments), 100),
        "attachment_risk_reasons": all_reasons,
        "suspicious_attachment_detected": True,
    }


def get_message_risk_level(score):
    if score <= 0:
        return "none"
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def add_risk_reason(reasons, reason, weight):
    reasons.append({"reason": reason, "weight": weight})


def calculate_message_risk(message_items):
    reasons = []
    score = 0

    if message_items.get("link_mismatch_detected"):
        score += 35
        add_risk_reason(reasons, "link_mismatch_detected", 35)

    if message_items.get("sender_impersonation_suspected"):
        score += 25
        add_risk_reason(reasons, "sender_impersonation_suspected", 25)

    dmarc_result = message_items.get("dmarc_result")
    if dmarc_result == "fail":
        score += 20
        add_risk_reason(reasons, "dmarc_failed", 20)
    elif message_items.get("dmarc_aligned") is False:
        score += 10
        add_risk_reason(reasons, "dmarc_not_aligned", 10)

    if message_items.get("spf_result") in ("fail", "softfail", "temperror", "permerror"):
        score += 10
        add_risk_reason(reasons, "spf_issue", 10)

    if message_items.get("dkim_result") in ("fail", "temperror", "permerror"):
        score += 10
        add_risk_reason(reasons, "dkim_issue", 10)

    if message_items.get("arc_result") in ("fail", "temperror", "permerror"):
        score += 5
        add_risk_reason(reasons, "arc_issue", 5)

    if message_items.get("url_risk_detected"):
        url_weight_map = (
            ("url_shortener_detected", "url_shortener_detected", 10),
            ("url_redirect_detected", "url_redirect_detected", 10),
            ("url_ip_literal_detected", "url_ip_literal_detected", 25),
            ("url_punycode_detected", "url_punycode_detected", 20),
            ("url_credential_harvest_detected", "url_credential_harvest_detected", 20),
            ("url_brand_keyword_mismatch_detected", "url_brand_keyword_mismatch_detected", 5),
        )
        for field_name, reason_name, weight in url_weight_map:
            if message_items.get(field_name):
                score += weight
                add_risk_reason(reasons, reason_name, weight)

    if message_items.get("html_risk_detected"):
        html_weight_map = (
            ("html_form_detected", "html_form_detected", 20),
            ("html_hidden_text_detected", "html_hidden_text_detected", 15),
            ("html_suspicious_css_detected", "html_suspicious_css_detected", 15),
            ("html_remote_image_detected", "html_remote_image_detected", 5),
        )
        for field_name, reason_name, weight in html_weight_map:
            if message_items.get(field_name):
                score += weight
                add_risk_reason(reasons, reason_name, weight)
        if message_items.get("html_tracking_indicator_count", 0) > 0:
            score += 10
            add_risk_reason(reasons, "html_tracking_indicators_detected", 10)

    attachment_score = message_items.get("attachment_risk_score", 0)
    if attachment_score > 0:
        weighted_attachment_score = min(attachment_score, 40)
        score += weighted_attachment_score
        add_risk_reason(reasons, "attachment_risk_detected", weighted_attachment_score)

    if message_items.get("encoded_content_risk_detected"):
        encoded_weight_map = (
            ("encoded_html_payload_detected", "encoded_html_payload_detected", 15),
            ("encoded_javascript_payload_detected", "encoded_javascript_payload_detected", 20),
            ("encoded_url_payload_detected", "encoded_url_payload_detected", 10),
            ("encoded_ip_payload_detected", "encoded_ip_payload_detected", 8),
            ("encoded_domain_payload_detected", "encoded_domain_payload_detected", 6),
            ("encoded_command_payload_detected", "encoded_command_payload_detected", 10),
            ("encoded_credential_payload_detected", "encoded_credential_payload_detected", 8),
            ("encoded_zip_payload_detected", "encoded_zip_payload_detected", 20),
        )
        for field_name, reason_name, weight in encoded_weight_map:
            if message_items.get(field_name):
                score += weight
                add_risk_reason(reasons, reason_name, weight)

    deduped_reasons = []
    seen = set()
    for reason in reasons:
        if reason["reason"] in seen:
            continue
        seen.add(reason["reason"])
        deduped_reasons.append(reason)

    final_score = min(score, 100)
    return {
        "message_risk_score": final_score,
        "message_risk_level": get_message_risk_level(final_score),
        "message_risk_detected": final_score > 0,
        "message_risk_reasons": [reason["reason"] for reason in deduped_reasons],
        "message_risk_breakdown": deduped_reasons,
    }


def extract_header_values(internet_message_headers, header_name):
    header_name = header_name.lower()
    return [
        header.get("value")
        for header in internet_message_headers
        if header.get("name", "").lower() == header_name and header.get("value")
    ]


def first_regex_group(pattern, value):
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def normalize_auth_results(helper, internet_message_headers, from_address):
    auth_results = extract_header_values(internet_message_headers, "Authentication-Results")
    received_spf_results = extract_header_values(internet_message_headers, "Received-SPF")
    from_domain = extract_domain_from_address(from_address)

    normalized = {
        "spf_result": None,
        "dkim_result": None,
        "dmarc_result": None,
        "arc_result": None,
        "dmarc_aligned": None,
    }

    spf_mailfrom_domain = None
    dkim_signing_domain = None
    dmarc_header_from_domain = None

    for auth_result in auth_results:
        if normalized["spf_result"] is None:
            normalized["spf_result"] = first_regex_group(r"\bspf=([a-z0-9_-]+)", auth_result)
        if normalized["dkim_result"] is None:
            normalized["dkim_result"] = first_regex_group(r"\bdkim=([a-z0-9_-]+)", auth_result)
        if normalized["dmarc_result"] is None:
            normalized["dmarc_result"] = first_regex_group(r"\bdmarc=([a-z0-9_-]+)", auth_result)
        if normalized["arc_result"] is None:
            normalized["arc_result"] = first_regex_group(r"\barc=([a-z0-9_-]+)", auth_result)
        if spf_mailfrom_domain is None:
            mailfrom_value = first_regex_group(r"\bsmtp\.mailfrom=([^\s;]+)", auth_result)
            spf_mailfrom_domain = extract_domain_from_address(mailfrom_value) if mailfrom_value else None
        if dkim_signing_domain is None:
            dkim_signing_domain = normalize_hostname(first_regex_group(r"\bheader\.d=([^\s;]+)", auth_result))
        if dmarc_header_from_domain is None:
            dmarc_header_from_domain = normalize_hostname(first_regex_group(r"\bheader\.from=([^\s;]+)", auth_result))

    if normalized["spf_result"] is None and received_spf_results:
        normalized["spf_result"] = first_regex_group(r"^\s*([a-z0-9_-]+)", received_spf_results[0])

    aligned_domains = []
    if spf_mailfrom_domain:
        aligned_domains.append(get_registered_domain(spf_mailfrom_domain))
    if dkim_signing_domain:
        aligned_domains.append(get_registered_domain(dkim_signing_domain))
    if dmarc_header_from_domain:
        aligned_domains.append(get_registered_domain(dmarc_header_from_domain))

    from_registered_domain = get_registered_domain(from_domain)
    if normalized["dmarc_result"] == "pass":
        normalized["dmarc_aligned"] = True
    elif from_registered_domain and aligned_domains:
        normalized["dmarc_aligned"] = from_registered_domain in aligned_domains

    summary_parts = []
    for key in ("spf_result", "dkim_result", "dmarc_result", "arc_result"):
        if normalized[key]:
            summary_parts.append("{}={}".format(key.replace("_result", ""), normalized[key]))
    if normalized["dmarc_aligned"] is not None:
        summary_parts.append("aligned={}".format(str(normalized["dmarc_aligned"]).lower()))

    normalized["auth_summary"] = ", ".join(summary_parts) if summary_parts else None
    log_message_debug(
        helper,
        "Normalized authentication results",
        message_items=sanitize_value(normalized),
    )
    return normalized


def analyze_link_mismatches(message_body):
    if not message_body or "<a" not in message_body.lower():
        return []

    parser = AnchorTagParser()
    parser.feed(message_body)
    suspicious_links = []

    for link in parser.links:
        displayed_text = link.get("displayed_text", "").strip()
        href = link.get("href", "")
        if not looks_like_locator_text(displayed_text):
            continue

        original_display, displayed_url, displayed_domain = parse_displayed_locator(displayed_text)
        actual_url = normalize_url(href)
        if not actual_url:
            continue

        actual_hostname = urlparse(actual_url).hostname
        actual_domain = get_registered_domain(actual_hostname)
        if not displayed_domain or not actual_domain or displayed_domain == actual_domain:
            continue

        suspicious_links.append(
            {
                "displayed_text": original_display,
                "displayed_url": displayed_url,
                "displayed_domain": displayed_domain,
                "actual_url": actual_url,
                "actual_domain": actual_domain,
                "link_mismatch": True,
                "mismatch_reason": "displayed_domain_differs_from_href_domain",
            }
        )

    return suspicious_links


def collect_message_urls(message_body):
    if not message_body:
        return []

    discovered = {}
    body_content = html.unescape(message_body)

    def add_url(url_value, source):
        normalized = normalize_url(url_value)
        if not normalized:
            return
        entry = discovered.setdefault(
            normalized,
            {
                "url": normalized,
                "sources": [],
            },
        )
        if source not in entry["sources"]:
            entry["sources"].append(source)

    if "<a" in body_content.lower():
        parser = AnchorTagParser()
        parser.feed(body_content)
        for link in parser.links:
            add_url(link.get("href"), "anchor_href")

    for match in url_re.finditer(body_content):
        add_url(match.group(0), "body_text")

    return list(discovered.values())


def get_redirect_target(normalized_url):
    parsed = urlparse(normalized_url)
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() not in REDIRECT_QUERY_PARAMETER_NAMES:
            continue
        redirect_target = normalize_url(value)
        if redirect_target:
            return key.lower(), redirect_target
    return None, None


def get_credential_terms(normalized_url):
    parsed = urlparse(normalized_url)
    search_space = " ".join(filter(None, [parsed.path, parsed.query])).lower()
    return sorted(term for term in CREDENTIAL_HARVEST_TERMS if term in search_space)


def is_allowed_brand_keyword_domain(keyword, registered_domain):
    if not registered_domain:
        return False
    if keyword in registered_domain:
        return True
    return registered_domain in BRAND_KEYWORD_ALLOWED_DOMAINS.get(keyword, set())


def get_brand_keywords(normalized_url, registered_domain, redirect_target_domain=None):
    parsed = urlparse(normalized_url)
    search_space = " ".join(filter(None, [parsed.path, parsed.query])).lower()
    if registered_domain in TRUSTED_REDIRECTOR_DOMAINS:
        return []
    return sorted(
        keyword
        for keyword in BRAND_KEYWORDS
        if keyword in search_space
        and not is_allowed_brand_keyword_domain(keyword, registered_domain)
        and not is_allowed_brand_keyword_domain(keyword, redirect_target_domain)
    )


def analyze_url_risks(message_body):
    risky_urls = []

    for url_entry in collect_message_urls(message_body):
        normalized_url = url_entry["url"]
        parsed = urlparse(normalized_url)
        hostname = normalize_hostname(parsed.hostname)
        registered_domain = get_registered_domain(hostname)
        indicators = []

        if registered_domain in KNOWN_URL_SHORTENER_DOMAINS:
            indicators.append("shortener_domain")

        redirect_parameter, redirect_target_url = get_redirect_target(normalized_url)
        redirect_target_domain = None
        if redirect_target_url:
            redirect_target_domain = get_registered_domain(urlparse(redirect_target_url).hostname)
            indicators.append("redirect_parameter_present")

        if is_ip_literal(hostname):
            indicators.append("ip_literal_host")

        if hostname and "xn--" in hostname:
            indicators.append("punycode_domain")

        credential_terms = get_credential_terms(normalized_url)
        if credential_terms:
            indicators.append("credential_harvest_terms")

        brand_keywords = get_brand_keywords(normalized_url, registered_domain, redirect_target_domain)
        if brand_keywords:
            indicators.append("brand_keyword_mismatch")

        if not indicators:
            continue

        risky_urls.append(
            {
                "url": normalized_url,
                "hostname": hostname,
                "registered_domain": registered_domain,
                "sources": sorted(url_entry["sources"]),
                "indicators": indicators,
                "credential_terms": credential_terms,
                "brand_keywords": brand_keywords,
                "redirect_parameter": redirect_parameter,
                "redirect_target_url": redirect_target_url,
                "redirect_target_domain": redirect_target_domain,
            }
        )

    return risky_urls


def analyze_html_risks(message_body):
    if not message_body or "<" not in message_body:
        return None

    parser = HTMLRiskParser()
    parser.feed(message_body)

    analysis = {
        "contains_form": parser.forms_count > 0,
        "form_count": parser.forms_count,
        "hidden_text_detected": bool(parser.hidden_text_segments),
        "hidden_text_count": len(parser.hidden_text_segments),
        "hidden_text_samples": parser.hidden_text_segments[:5],
        "remote_image_count": len(parser.remote_images),
        "remote_images": parser.remote_images[:10],
        "tiny_image_count": len(parser.tiny_images),
        "tiny_images": parser.tiny_images[:10],
        "suspicious_css_detected": bool(parser.suspicious_css_elements),
        "suspicious_css_count": len(parser.suspicious_css_elements),
        "suspicious_css_elements": parser.suspicious_css_elements[:10],
        "indicators": [],
    }

    if analysis["contains_form"]:
        analysis["indicators"].append("contains_form")
    if analysis["hidden_text_detected"]:
        analysis["indicators"].append("hidden_text")
    if analysis["remote_image_count"] > 0:
        analysis["indicators"].append("remote_images")
    if analysis["tiny_image_count"] > 0:
        analysis["indicators"].append("tiny_images")
    if analysis["suspicious_css_detected"]:
        analysis["indicators"].append("suspicious_css")

    if not analysis["indicators"]:
        return None
    return analysis


def get_encoded_content_limits(helper):
    return {
        "max_blob_length": get_positive_int_arg(
            helper,
            "encoded_content_max_blob_length",
            ENCODED_CONTENT_DEFAULT_MAX_BLOB_LENGTH,
        ),
        "max_decoded_preview_length": get_positive_int_arg(
            helper,
            "encoded_content_max_decoded_preview_length",
            ENCODED_CONTENT_DEFAULT_MAX_DECODED_PREVIEW_LENGTH,
        ),
        "max_blobs": get_positive_int_arg(
            helper,
            "encoded_content_max_blobs",
            ENCODED_CONTENT_DEFAULT_MAX_BLOBS,
        ),
    }


def iter_encoded_content_candidates(message_body, max_blob_length):
    if not message_body:
        return

    candidate_patterns = (
        ("base64", base64_blob_re, lambda value: value),
        ("hex", hex_blob_re, lambda value: value),
        ("hex", spaced_hex_blob_re, lambda value: re.sub(r"\s+", "", value)),
    )

    for encoding_type, pattern, normalizer in candidate_patterns:
        for match in pattern.finditer(message_body):
            candidate = match.group(0)
            normalized_candidate = normalizer(candidate)
            if len(normalized_candidate) > max_blob_length:
                continue
            previous_char = message_body[match.start() - 1] if match.start() > 0 else ""
            next_char = message_body[match.end()] if match.end() < len(message_body) else ""
            if (
                encoding_type == "base64"
                and candidate.isalpha()
                and previous_char in {"@", "."}
                and next_char in {"@", "."}
            ):
                continue
            yield {
                "encoding_type": encoding_type,
                "blob": normalized_candidate,
                "start": match.start(),
            }


def decode_encoded_blob(encoding_type, blob_value):
    try:
        if encoding_type == "base64":
            return base64.b64decode(blob_value, validate=True)
        if encoding_type == "hex":
            return bytes.fromhex(blob_value)
    except (TypeError, ValueError):
        return None
    return None


def get_encoded_blob_source(message_body, start_offset):
    context_window = message_body[max(0, start_offset - 64):start_offset].lower()
    if "data:" in context_window:
        return "data_uri"
    if "<script" in context_window:
        return "script_block"
    if "<style" in context_window:
        return "style_block"
    return "body_text"


def is_mostly_printable(decoded_bytes):
    if not decoded_bytes:
        return False
    printable_bytes = sum(
        1
        for byte in decoded_bytes
        if byte in (9, 10, 13) or 32 <= byte <= 126
    )
    return printable_bytes / float(len(decoded_bytes)) >= 0.85


def analyze_decoded_text_indicators(normalized_text):
    indicators = []

    if "http://" in normalized_text or "https://" in normalized_text:
        indicators.append("embedded_url_payload")
    elif normalized_text.strip().startswith("www.") or url_re.search(normalized_text):
        indicators.append("embedded_url_payload")

    if ipv4_re.search(normalized_text) or ipv6_re.search(normalized_text):
        indicators.append("decoded_text_contains_ip")

    domain_matches = {
        match.group(0)
        for match in domain_re.finditer(normalized_text)
        if "://" not in match.group(0)
    }
    if domain_matches:
        indicators.append("decoded_text_contains_domain")

    if encoded_command_re.search(normalized_text):
        indicators.append("decoded_text_contains_command")

    if any(term in normalized_text for term in CREDENTIAL_HARVEST_TERMS):
        indicators.append("decoded_text_contains_credential_term")

    return indicators


def classify_decoded_payload(decoded_bytes):
    if not decoded_bytes:
        return "empty", []

    inspection_window = decoded_bytes[:4096]
    indicators = []

    if inspection_window.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        indicators.append("zip_magic_bytes")
        return "zip_like", indicators

    normalized_text = inspection_window.decode("utf-8", errors="replace").lower()
    if any(token in normalized_text for token in ("<html", "<body", "<form", "<script", "<iframe", "<svg")):
        indicators.append("embedded_html_payload")
    if any(token in normalized_text for token in ("javascript:", "function(", "document.", "window.", "atob(", "createobjecturl", "fromcharcode(", "eval(")):
        indicators.append("embedded_javascript_payload")
    indicators.extend(analyze_decoded_text_indicators(normalized_text))
    indicators = sorted(set(indicators))

    if "embedded_html_payload" in indicators:
        return "html", indicators
    if "embedded_javascript_payload" in indicators:
        return "javascript", indicators
    if normalized_text.strip().startswith(("http://", "https://", "www.")):
        if "embedded_url_payload" not in indicators:
            indicators.append("embedded_url_payload")
        return "url", indicators
    if is_mostly_printable(inspection_window):
        return "text", indicators

    indicators.append("binary_payload")
    return "binary", indicators


def build_decoded_preview(decoded_bytes, max_decoded_preview_length):
    preview_text = decoded_bytes.decode("utf-8", errors="replace").replace("\x00", "")
    preview_text = re.sub(r"\s+", " ", preview_text).strip()
    truncated = len(preview_text) > max_decoded_preview_length
    return preview_text[:max_decoded_preview_length], truncated


def is_encoded_content_risk_candidate(entry):
    indicators = set(entry.get("indicators", []))
    if indicators - {"binary_payload"}:
        return True

    if "binary_payload" in indicators:
        if entry.get("source") in {"data_uri", "script_block", "style_block"}:
            return True
        if entry.get("encoding_type") == "base64":
            return entry.get("blob_length", 0) >= ENCODED_CONTENT_RISK_MIN_BASE64_LENGTH
        if entry.get("encoding_type") == "hex":
            return entry.get("blob_length", 0) >= ENCODED_CONTENT_RISK_MIN_HEX_LENGTH
        return False

    if entry.get("encoding_type") == "base64":
        return entry.get("blob_length", 0) >= ENCODED_CONTENT_RISK_MIN_BASE64_LENGTH
    if entry.get("encoding_type") == "hex":
        return entry.get("blob_length", 0) >= ENCODED_CONTENT_RISK_MIN_HEX_LENGTH
    return False


def analyze_encoded_content(helper, message_body):
    limits = get_encoded_content_limits(helper)
    decode_preview = bool(helper.get_arg("decode_encoded_content"))
    analysis = []
    flattened_indicators = set()
    seen_pairs = set()

    for candidate in iter_encoded_content_candidates(message_body, limits["max_blob_length"]):
        if len(analysis) >= limits["max_blobs"]:
            break

        dedupe_key = (candidate["encoding_type"], candidate["blob"])
        if dedupe_key in seen_pairs:
            continue
        seen_pairs.add(dedupe_key)

        decoded_bytes = decode_encoded_blob(candidate["encoding_type"], candidate["blob"])
        if decoded_bytes is None:
            continue

        decoded_classification, indicators = classify_decoded_payload(decoded_bytes)
        flattened_indicators.update(indicators)

        entry = {
            "encoding_type": candidate["encoding_type"],
            "source": get_encoded_blob_source(message_body, candidate["start"]),
            "blob_length": len(candidate["blob"]),
            "decoded_length": len(decoded_bytes),
            "decoded_classification": decoded_classification,
            "decoded_sha256": get_hash_hexdigest(decoded_bytes, "sha256"),
            "indicators": indicators,
        }
        entry["risk_candidate"] = is_encoded_content_risk_candidate(entry)
        if decode_preview:
            preview, truncated = build_decoded_preview(
                decoded_bytes,
                limits["max_decoded_preview_length"],
            )
            if preview:
                entry["decoded_preview"] = preview
            entry["decoded_preview_truncated"] = truncated
        analysis.append(entry)

    if not analysis:
        return None

    return {
        "encoded_content_analysis": analysis,
        "encoded_content_count": len(analysis),
        "encoded_content_types": sorted({entry["encoding_type"] for entry in analysis}),
        "encoded_content_indicators": sorted(flattened_indicators),
        "encoded_content_risk_detected": any(entry.get("risk_candidate") for entry in analysis),
    }


def analyze_sender_impersonation(helper, item, message_items):
    from_address = message_items.get("from")
    sender_address = message_items.get("sender")
    reply_to_addresses = message_items.get("replyTo", [])
    from_domain = extract_domain_from_address(from_address)
    sender_domain = extract_domain_from_address(sender_address)
    reply_to_domains = sorted(
        {
            domain
            for domain in (extract_domain_from_address(address) for address in reply_to_addresses)
            if domain
        }
    )
    from_display_name = extract_display_name(item.get("from"))
    sender_display_name = extract_display_name(item.get("sender"))
    internal_domain = extract_domain_from_address(helper.get_arg("audit_email_account"))
    indicators = []

    if sender_address and from_address and sender_address.lower() != from_address.lower():
        indicators.append("sender_address_differs_from_from_address")
    if reply_to_addresses and any(address.lower() != from_address.lower() for address in reply_to_addresses if address and from_address):
        indicators.append("reply_to_address_differs_from_from_address")
    if from_domain and any(domain != from_domain for domain in reply_to_domains):
        indicators.append("reply_to_domain_differs_from_from_domain")

    if from_display_name:
        display_name_lower = from_display_name.strip().lower()
        if EMAIL_ADDRESS_RE.match(display_name_lower) and display_name_lower != (from_address or "").lower():
            indicators.append("display_name_looks_like_different_email_address")
        elif domain_re.match(display_name_lower) and get_registered_domain(display_name_lower) != get_registered_domain(from_domain):
            indicators.append("display_name_looks_like_different_domain")

        if internal_domain and internal_domain in display_name_lower and from_domain != internal_domain:
            indicators.append("external_sender_uses_internal_domain_in_display_name")

    if from_display_name and sender_display_name and from_display_name.strip().lower() != sender_display_name.strip().lower():
        indicators.append("sender_display_name_differs_from_from_display_name")

    if not indicators:
        return None

    return {
        "suspected": True,
        "indicators": sorted(set(indicators)),
        "from_display_name": from_display_name,
        "sender_display_name": sender_display_name,
        "from_domain": from_domain,
        "sender_domain": sender_domain,
        "reply_to_domains": reply_to_domains,
    }

def get_hash_hexdigest(content, algorithm):
    hash_functions = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
    }
    hash_function = hash_functions.get(algorithm)
    if not hash_function:
        raise ValueError("Unknown hash algorithm: {}".format(algorithm))
    return hash_function(content).hexdigest()

def analyze_macro_content(helper, filename, content):
    macro_data = {
        'macros_exist': None,
        'macro_analysis': None,
        'attention': None
    }

    try:
        vbaparser = VBA_Parser(filename, data=content)

        if vbaparser.detect_vba_macros():
            macro_data['macros_exist'] = "true"

            macro_analysis = VBA_Parser.analyze_macros(vbaparser)
            log_debug(helper, "Macro analysis result", **build_log_context(helper, macro_analysis=sanitize_value(macro_analysis)))

            if macro_analysis == []:
                macro_data['macro_analysis'] = "Macro doesn't look bad, but I never trust macros."
            else:
                macro_data['macro_analysis'] = macro_analysis
        else:
            macro_data['macros_exist'] = "false"
    except Exception:
        macro_data['attention'] = 'could not extract the office document, may be encrypted'

    return macro_data

def get_calendar_events(helper, graph_url, headers):
    """
    Fetch all calendar events for a specific user mailbox via the Microsoft Graph API.
    """
    # Define the user mailbox to query
    mailbox = helper.get_arg('audit_email_account')
    events_url = f"{graph_url}/users/{mailbox}/events"

    log_info(helper, "Fetching calendar events", **build_log_context(helper, mailbox=mailbox))
    events = []

    while events_url:
        response = send_request_with_retry(helper, events_url, "GET", headers=headers, timeout=(15.0, 90.0))
        if response.status_code == 200:
            data = response.json()
            events.extend(data.get('value', []))
            events_url = data.get('@odata.nextLink')  # Handle pagination
        else:
            log_error(helper, "Failed to retrieve calendar events", **build_log_context(helper, mailbox=mailbox, status_code=response.status_code, response_text=response.text))
            break

    log_info(helper, "Retrieved calendar events", **build_log_context(helper, mailbox=mailbox, event_count=len(events)))
    return events

def purge_calendar_event(helper, graph_url, headers, event_id):
    """
    Purge a specific calendar event by deleting it permanently.
    """
    mailbox = helper.get_arg('audit_email_account')
    delete_url = f"{graph_url}/users/{mailbox}/events/{event_id}"

    response = send_request_with_retry(helper, delete_url, "DELETE", headers=headers, timeout=(15.0, 90.0))

    if response.status_code == 204:
        get_run_stats(helper)["calendar_events_deleted"] += 1
        log_info(helper, "Deleted calendar event", **build_log_context(helper, mailbox=mailbox, event_id=event_id))
    else:
        log_error(helper, "Failed to delete calendar event", **build_log_context(helper, mailbox=mailbox, event_id=event_id, status_code=response.status_code, response_text=response.text))

def purge_calendar_events(helper, graph_url, headers):
    """
    Fetch and purge all calendar events for the specified mailbox.
    """
    # Get calendar events
    events = get_calendar_events(helper, graph_url, headers)
    if not events:
        log_info(helper, "No calendar events found to delete", **build_log_context(helper))
        return

    # Loop through events and delete
    log_info(helper, "Purging calendar events", **build_log_context(helper, event_count=len(events)))
    for event in events:
        event_id = event.get('id')
        event_subject = event.get('subject', 'No Subject')
        start_time = event.get('start', {}).get('dateTime', 'Unknown Start Time')

        if is_debug_enabled(helper):
            log_debug(helper, "Deleting calendar event", **build_log_context(helper, event_subject=event_subject, start_time=start_time, event_id=event_id))
        purge_calendar_event(helper, graph_url, headers, event_id)
    log_info(helper, "Finished purging calendar events", **build_log_context(helper))

#Function to ingest messages to splunk
def ingest_messages_to_splunk(helper, ew, messages):
    try:
        if messages:
            log_info(helper, "Writing messages to Splunk", **build_log_context(helper, event_count=len(messages)))
            _write_events(helper, ew, messages=messages)
        else:
            log_info(helper, "Nothing to write to Splunk", **build_log_context(helper))
    except Exception as e:
        log_error(helper, "Error while ingesting messages to Splunk", **build_log_context(helper, error=str(e)))
        log_debug(helper, traceback.format_exc(), **build_log_context(helper))

#URL IOC extraction function.
def extract_urls(helper,data):
    urls = itertools.chain(
        url_re.finditer(data)
    )
    for url in urls:
        url = url.group(0)
        yield url

#Domain IOC extraction function.
def extract_domains(helper,data):
    domains = itertools.chain(
        domain_re.finditer(data)
    )
    for domain in domains:
        domain = domain.group(0)
        yield domain

#IPv4 IOC extraction function.
def extract_ipv4(helper,data):
    ipv4s = itertools.chain(
        ipv4_re.finditer(data)
    )
    for ip in ipv4s:
        ip = ip.group(0)
        yield ip

#IPv6 IOC extraction function.
def extract_ipv6(helper,data):
    ipv6s = itertools.chain(
        ipv6_re.finditer(data)
    )
    for ip in ipv6s:
        ip = ip.group(0)
        yield ip

#Function to check if returned url is secure
def is_https(url):
    if url.startswith("https://"):
        return True
    else:
        return False

#Function to process Internet message headers
def process_internet_message_headers(item, message_items, helper):
    internet_message_headers = item.get('internetMessageHeaders', [])
    message_path = []

    if 'internetMessageHeaders' in item:
        # Message path calculations
        path_item = {}

        for item in internet_message_headers:
            if item['name'] == "Received":
                path_item = item
                message_path.append(path_item)

        if message_path:
            src_line = str(message_path[-1])
            dest_line = str(message_path[0])

            re_by = re.compile(r'(?<=\bby\s)(\S+)')
            re_from = re.compile(r'(?<=\bfrom\s)(\S+)')

            dest = re_by.search(dest_line)
            src = None

            if re_from.search(src_line):
                src = re_from.search(src_line)
            elif re_by.search(src_line):
                src = re_by.search(src_line)

            try:
                message_items['src'] = str(src[0])
            except (TypeError, IndexError):
                message_items['src'] = "no source mta found"

            try:
                message_items['dest'] = str(dest[0])
            except (TypeError, IndexError):
                message_items['dest'] = "no destination mta found"
        else:
            message_items['src'] = "no source mta found"
            message_items['dest'] = "no destination mta found"

    return internet_message_headers, message_path, message_items

def process_macro_attachments(helper, attachment):
    if 'contentType' in attachment and helper.get_arg('get_attachment_info') and helper.get_arg('macro_analysis'):
        filename = attachment['name']

        try:
            if attachment['@odata.mediaContentType'] in macro_file_types:
                filedata_encoded = attachment['contentBytes'].encode()
                file_bytes = base64.b64decode(filedata_encoded)
                return analyze_macro_content(helper, filename, file_bytes)
        except KeyError:
            log_debug(helper, "Attachment missing @odata.mediaContentType; skipping macro check", **build_log_context(helper, attachment_name=filename))

    return {
        'macros_exist': None,
        'macro_analysis': None,
        'attention': None
    }

#Function to collect IOCs from message body
def ingest_iocs_from_body(helper, message_body):
    ioc_data = {}

    ipv4_extract = extract_ipv4(helper, message_body)
    ipv4_iocs = list(set(ipv4_extract))
    if ipv4_iocs:
        ioc_data['ipv4_iocs'] = ipv4_iocs

    ipv6_extract = extract_ipv6(helper, message_body)
    ipv6_iocs = list(set(ipv6_extract))
    if ipv6_iocs:
        ioc_data['ipv6_iocs'] = ipv6_iocs

    url_extract = extract_urls(helper, message_body)
    url_iocs = list(set(url_extract))
    if url_iocs:
        ioc_data['url_iocs'] = url_iocs

    domain_extract = extract_domains(helper, message_body)
    domain_iocs = list(set(domain_extract))
    if domain_iocs:
        ioc_data['domain_iocs'] = domain_iocs

    return ioc_data

#Function to format message body as defined by the user in the TA setup
def format_message_body(message_body, body_type):
    if body_type == "text":
        h2t = html2text.HTML2Text()
        h2t.ignore_links = True
        h2t.ignore_images = True
        return h2t.handle(message_body)
    else:  # body_type == "html"
        return message_body

#zip file attachment processing function
def process_zip_file(helper, attachment, message_body):
    zip_data = {
        'zip_files': [],
        'zip_hashes': [],
        'attention': None
    }

    if 'contentType' in attachment and attachment['contentType'] in ('application/zip', 'application/x-zip-compressed', 'application/zip-compressed', 'multipart/x-zip', 'application/x-compressed-zip'):
        filedata_encoded = attachment['contentBytes'].encode()
        file_bytes = base64.b64decode(filedata_encoded)
        zipbytes = io.BytesIO(file_bytes)

        try:
            zipfile = ZipFile(zipbytes)
            zipmembers = zipfile.namelist()

            # Extract words from the email body
            words = set(message_body.split())

            def try_extract(password):
                for word in words:
                    try:
                        with zipfile.open(file, pwd=bytes(word, 'utf-8')) as zfile:
                            return zfile.read()
                    except RuntimeError:
                        continue
                return None

            for file in zipmembers:
                zip_read = None
                try:
                    zip_read = zipfile.read(file)
                except RuntimeError:
                    if helper.get_arg('try_zip_password'):
                        zip_read = try_extract(file)

                if zip_read is None:
                    zip_data['attention'] = 'could not extract the zip file, may be protected with an unknown password'
                    break

                zip_hash = get_hash_hexdigest(zip_read, helper.get_arg('file_hash_algorithm'))

                if not file in zip_data['zip_files']:
                    zip_data['zip_files'].append(file)
                    zip_data['zip_hashes'].append(zip_hash)

        except BadZipFile:
            zip_data['attention'] = 'could not extract the zip file, it may be corrupted'

    return zip_data

def extract_certificate_data(helper, content):
    content_info = ContentInfo.load(content)
    signed_data = content_info['content']
    certificates = signed_data['certificates']
    cert_data_list = []

    for cert_choice in certificates:
        try:
            # Check if the choice is an X.509 Certificate
            if isinstance(cert_choice.chosen, Certificate):
                cert = cert_choice.chosen
                subject = cert.subject.native
                common_name = subject.get('common_name')
                email_address = None
                if common_name and '@' in common_name:
                    email_address = common_name

                # Additional certificate info
                not_before = cert['tbs_certificate']['validity']['not_before'].native
                not_after = cert['tbs_certificate']['validity']['not_after'].native
                issuer = cert.issuer.native
                serial_number = cert.serial_number

                cert_data = {
                    'email_address': email_address,
                    'not_before': not_before.isoformat(),
                    'not_after': not_after.isoformat(),
                    'issuer': issuer,
                    'serial_number': serial_number,
                }
                cert_data_list.append(cert_data)

        except KeyError as e:
            log_error(helper, "Error extracting certificate data", **build_log_context(helper, error=str(e)))

    return cert_data_list

def handle_smime_data(helper, attachment_content, message_body):

    smime_attachments = []
    smime_data = {}

    # Decode the base64 contentBytes
    decoded_bytes = base64.b64decode(attachment_content)

    # Parse the decoded bytes
    msg = BytesParser().parsebytes(decoded_bytes)

    # Iterate through the message parts and get the attachments' information
    for part in msg.walk():
        content_disposition = part.get("Content-Disposition", "").strip()
        if content_disposition.startswith("inline") or content_disposition.startswith("attachment"):
            # Get the filename and content
            filename = part.get_filename()
            content = part.get_payload(decode=True)
            content_type = part.get_content_type()

            # Calculate the size and file hash
            size = len(content)
            hash_algorithm = helper.get_arg('file_hash_algorithm')
            try:
                file_hash = get_hash_hexdigest(content, hash_algorithm)
            except ValueError as e:
                log_error(helper, "Unknown file hash algorithm for S/MIME attachment", **build_log_context(helper, error=str(e)))
                continue

            smime_attachment_info = {
                "filename": filename,
                "content_type": content_type,
                "size": size,
                "file_hash": file_hash,
            }

            if helper.get_arg('get_attachment_info') and helper.get_arg('read_zip_files') and content_type in ('application/zip', 'application/x-zip-compressed', 'application/zip-compressed', 'multipart/x-zip', 'application/x-compressed-zip'):
                zip_data = {
                    'zip_files': [],
                    'zip_hashes': [],
                    'attention': None
                }

                zipbytes = io.BytesIO(content)

                try:
                    zipfile = ZipFile(zipbytes)
                    zipmembers = zipfile.namelist()

                    # Extract words from the email body
                    words = set(message_body.split())

                    def try_extract(password):
                        for word in words:
                            try:
                                with zipfile.open(file, pwd=bytes(word, 'utf-8')) as zfile:
                                    return zfile.read()
                            except RuntimeError:
                                continue
                        return None

                    for file in zipmembers:
                        zip_read = None
                        try:
                            zip_read = zipfile.read(file)
                        except RuntimeError:
                            if helper.get_arg('try_zip_password'):
                                zip_read = try_extract(file)

                        if zip_read is None:
                            zip_data['attention'] = 'could not extract the zip file, may be protected with an unknown password'
                            break

                        zip_hash = get_hash_hexdigest(zip_read, helper.get_arg('file_hash_algorithm'))

                        if not file in zip_data['zip_files']:
                            zip_data['zip_files'].append(file)
                            zip_data['zip_hashes'].append(zip_hash)

                except BadZipFile:
                    zip_data['attention'] = 'could not extract the zip file, it may be corrupted'

                smime_attachment_info.update(zip_data)

            if helper.get_arg('get_attachment_info') and helper.get_arg('macro_analysis') and content_type in macro_file_types:
                macro_data = analyze_macro_content(helper, filename, content)
                smime_attachment_info.update(macro_data)

            if helper.get_arg('analyze_attachment_risk') or helper.get_arg('analyze_message_risk'):
                smime_attachment_info.update(classify_attachment_risk(smime_attachment_info))

            # Check if the attachment is an smime.p7s
            if helper.get_arg('get_s_mime_info') and filename.lower().endswith("smime.p7s"):
                cert_data_list = extract_certificate_data(helper, content)
                if cert_data_list:
                    smime_data["certificates"] = cert_data_list
                else:
                    log_debug(helper, "No certificate data found in signed attachment", **build_log_context(helper, attachment_name=filename))

            smime_attachments.append(smime_attachment_info)

    return smime_attachments, smime_data

def get_attachment_info(helper, attachment, message_body):
    attach_data = []

    # Looks for itemAttachment type, which is a contact, event, or message that's attached.
    if attachment["@odata.type"] == "#microsoft.graph.itemAttachment":

        my_added_data = {}
            
        my_added_data['name'] = attachment['name']
        my_added_data['odata_type'] = attachment['@odata.type']
        my_added_data['id'] = attachment['id']
        my_added_data['contentType'] = attachment['contentType']
        my_added_data['size'] = attachment['size']
        if helper.get_arg('analyze_attachment_risk') or helper.get_arg('analyze_message_risk'):
            my_added_data.update(classify_attachment_risk(my_added_data))

        attach_data.append(my_added_data)
    
    # Looks for referenceAttachment type, which is a link to a file on OneDrive or other supported storage location
    if attachment["@odata.type"] == "#microsoft.graph.referenceAttachment":

        my_added_data = {}

        my_added_data['name'] = attachment['name']
        my_added_data['odata_type'] = attachment['@odata.type']
        my_added_data['id'] = attachment['id']
        my_added_data['contentType'] = attachment['contentType']
        my_added_data['size'] = attachment['size']
        if helper.get_arg('analyze_attachment_risk') or helper.get_arg('analyze_message_risk'):
            my_added_data.update(classify_attachment_risk(my_added_data))

        attach_data.append(my_added_data)
    
    # Looks for fileAttachment type, which is a standard email attachment.
    if attachment["@odata.type"] == "#microsoft.graph.fileAttachment":

        my_added_data = {}

        attach_b64decode = base64.b64decode(attachment['contentBytes'])

        att_hash = get_hash_hexdigest(attach_b64decode, helper.get_arg('file_hash_algorithm'))

        my_added_data['name'] = attachment['name']
        my_added_data['odata_type'] = attachment['@odata.type']
        my_added_data['id'] = attachment['id']
        my_added_data['contentType'] = attachment['contentType']
        my_added_data['size'] = attachment['size']
        my_added_data['file_hash'] = att_hash

        if helper.get_arg('get_attachment_info') and helper.get_arg('read_zip_files'):
            zip_info = process_zip_file(helper, attachment, message_body)
            my_added_data.update(zip_info)

        if helper.get_arg('get_attachment_info') and helper.get_arg('macro_analysis'):
            macro_info = process_macro_attachments(helper, attachment)
            my_added_data.update(macro_info)

        if helper.get_arg('analyze_attachment_risk') or helper.get_arg('analyze_message_risk'):
            my_added_data.update(classify_attachment_risk(my_added_data))

        attach_data.append(my_added_data)

    return attach_data

def process_message_attachments(helper, attachments, message_body, message_items):
    attach_data = []
    smime_attachment_entries = []

    for attachment in attachments:
        if attachment['contentType'] == 'multipart/signed':
            attachment_content = attachment['contentBytes']
            smime_attachments, signature_data = handle_smime_data(helper, attachment_content, message_body)
            message_items['smime_data'] = signature_data

            if helper.get_arg('get_attachment_info'):
                message_items['smime_attachments'] = smime_attachments
            smime_attachment_entries.extend(smime_attachments)
        else:
            my_added_data = get_attachment_info(helper, attachment, message_body)
            attach_data.extend(my_added_data)

    if helper.get_arg('get_attachment_info') and attach_data:
        message_items['attachments'] = attach_data

    if helper.get_arg('analyze_attachment_risk') or helper.get_arg('analyze_message_risk'):
        risk_summary = summarize_attachment_risks(attach_data + smime_attachment_entries)
        if risk_summary:
            message_items.update(risk_summary)

def get_graph_base_url(helper):
    if helper.get_arg('endpoint') == 'worldwide':
        return 'https://graph.microsoft.com/v1.0'
    elif helper.get_arg('endpoint') == 'gcchigh':
        return 'https://graph.microsoft.us/v1.0'
    raise ValueError("Unsupported endpoint: {}".format(helper.get_arg('endpoint')))

def build_request_headers(access_token):
    return {
        "Authorization": "Bearer " + access_token,
        "User-Agent": "MicrosoftGraphEmail-Splunk/",
    }


def should_request_attachments(helper):
    return any(
        (
            helper.get_arg('get_attachment_info'),
            helper.get_arg('analyze_attachment_risk'),
            helper.get_arg('analyze_message_risk'),
            helper.get_arg('get_s_mime_info'),
            helper.get_arg('macro_analysis'),
            helper.get_arg('read_zip_files'),
        )
    )


def should_request_internet_headers(helper):
    return any(
        (
            helper.get_arg('get_internet_headers'),
            helper.get_arg('get_message_path'),
            helper.get_arg('get_auth_results'),
            helper.get_arg('get_arc_results'),
            helper.get_arg('get_spf_results'),
            helper.get_arg('get_dkim_signature'),
            helper.get_arg('get_x_headers'),
            helper.get_arg('normalize_auth_results'),
            helper.get_arg('analyze_message_risk'),
        )
    )


def should_request_body(helper):
    return any(
        (
            helper.get_arg('get_body'),
            helper.get_arg('extract_body_iocs'),
            helper.get_arg('get_tracking_pixel'),
            helper.get_arg('try_zip_password'),
            helper.get_arg('analyze_link_mismatch'),
            helper.get_arg('analyze_url_risk'),
            helper.get_arg('analyze_html_risk'),
            helper.get_arg('analyze_encoded_content'),
            helper.get_arg('decode_encoded_content'),
            helper.get_arg('analyze_message_risk'),
        )
    )


def should_request_body_preview(helper):
    return helper.get_arg('get_body_preview')


def build_messages_endpoint(helper):
    expands = ["SingleValueExtendedProperties($filter=Id eq 'LONG 0x0E08')"]
    if should_request_attachments(helper):
        expands.append("attachments")

    selects = [
        "receivedDateTime",
        "subject",
        "sender",
        "from",
        "hasAttachments",
        "internetMessageId",
        "toRecipients",
        "ccRecipients",
        "bccRecipients",
        "replyTo",
        "isReadReceiptRequested",
        "isDeliveryReceiptRequested",
    ]
    if should_request_internet_headers(helper):
        selects.append("internetMessageHeaders")
    if should_request_body(helper):
        selects.append("body")
    if should_request_body_preview(helper):
        selects.append("bodyPreview")

    endpoint = "/users/" + helper.get_arg('audit_email_account')
    endpoint += "/mailFolders/" + helper.get_arg('folder') + "/messages/"
    endpoint += "?$expand=" + ",".join(expands)
    endpoint += "&$select=" + ",".join(selects)
    endpoint += "&$top=" + helper.get_arg('message_num')
    endpoint += "&$orderby=receivedDateTime"
    endpoint += "&$count=true"
    return endpoint

def log_retrieved_message_count(helper, response, prefix="Retrieving"):
    count = response.get('@odata.count', 0)
    message_num = int(helper.get_arg('message_num'))
    if count < message_num:
        log_info(helper, "{} messages retrieved".format(prefix), **build_log_context(helper, count=count))
    else:
        log_info(helper, "{} messages retrieved".format(prefix), **build_log_context(helper, retrieved=helper.get_arg('message_num'), total=count))

def fetch_json(helper, url, headers, timeout=(15.0, 90.0)):
    return send_request_with_retry(helper, url, "GET", headers=headers, parameters=None, timeout=timeout).json()

def fetch_message_pages(helper, graph_url, headers):
    endpoint = build_messages_endpoint(helper)
    messages_response = fetch_json(helper, graph_url + endpoint, headers)
    log_retrieved_message_count(helper, messages_response)

    messages = [messages_response['value']]
    stats = get_run_stats(helper)
    stats["pages_fetched"] += 1
    stats["messages_fetched"] += len(messages_response.get('value', []))
    interval_in_seconds = int(helper.get_arg('interval'))
    page_limit = max((interval_in_seconds // 60) * 4, 1)

    url_count = 0
    while ("@odata.nextLink" in messages_response) and is_https(messages_response["@odata.nextLink"]):
        if url_count >= page_limit:
            log_warning(
                helper,
                "Reached page safety limit for this run; remaining mail will be fetched next interval",
                **build_log_context(helper, page_limit=page_limit + 1)
            )
            break

        nextlinkurl = messages_response["@odata.nextLink"]
        messages_response = fetch_json(helper, nextlinkurl, headers)
        log_retrieved_message_count(helper, messages_response, prefix="Retrieving another")
        url_count += 1
        stats["pages_fetched"] += 1
        stats["messages_fetched"] += len(messages_response.get('value', []))
        messages.append(messages_response['value'])

    return messages

def build_message_items(item):
    message_items = {}
    message_items['DateTime'] = item.get('receivedDateTime')
    message_items['hasAttachments'] = item.get('hasAttachments')
    message_items['internetMessageId'] = item.get('internetMessageId')
    message_items['id'] = item.get('id')
    message_items['to'] = extract_email_addresses(item.get('toRecipients'))
    message_items['ccRecipients'] = extract_email_addresses(item.get('ccRecipients'))
    message_items['bccRecipients'] = extract_email_addresses(item.get('bccRecipients'))
    message_items['from'] = extract_email_address(item.get('from'))
    message_items['replyTo'] = extract_email_addresses(item.get('replyTo'))
    message_items['sender'] = extract_email_address(item.get('sender'))
    message_items['subject'] = item.get('subject')
    return message_items

def should_use_permanent_delete(helper):
    return helper.get_arg('endpoint') == 'worldwide'


def move_message_to_purges(helper, message_url, headers):
    purge_folder_payload = {
        "destinationId": "recoverableitemspurges"
    }
    return send_request_with_retry(
        helper,
        message_url + "/move",
        "POST",
        headers=headers,
        payload=purge_folder_payload,
        timeout=(15.0, 90.0),
    )


def permanently_delete_message(helper, message_url, headers):
    return send_request_with_retry(
        helper,
        message_url + "/permanentDelete",
        "POST",
        headers=headers,
        timeout=(15.0, 90.0),
    )


def purge_message(helper, graph_url, headers, item):
    disable_rr_payload = {
         "singleValueExtendedProperties": [
             {
             "id": "Boolean 0x0C06",
             "value": "false"
             },
             {
             "id": "Boolean 0x0029",
             "value": "false"
             }
         ]
         }
    message_id = item["id"]
    message_url = graph_url + "/users/" + helper.get_arg('audit_email_account') + "/messages/" + message_id

    if item["isReadReceiptRequested"]:
        log_info(helper, "Removing read receipts before deletion", **build_log_context(helper, message_id=message_id))
        remove_receipt_response = send_request_with_retry(
            helper,
            message_url,
            "PATCH",
            headers=headers,
            payload=disable_rr_payload,
            timeout=(15.0, 90.0),
        )
        if remove_receipt_response.status_code != 200:
            log_warning(helper, "Couldn't remove read receipt; not purging", **build_log_context(helper, message_id=message_id, status_code=remove_receipt_response.status_code))
            return None

    if should_use_permanent_delete(helper):
        log_info(helper, "Permanently deleting message", **build_log_context(helper, message_id=message_id, purge_strategy="permanentDelete"))
        permanent_delete_response = permanently_delete_message(helper, message_url, headers)
        if permanent_delete_response.status_code in PURGE_SUCCESS_STATUS_CODES:
            return permanent_delete_response
        if permanent_delete_response.status_code in PERMANENT_DELETE_FALLBACK_STATUS_CODES:
            log_warning(
                helper,
                "Graph permanentDelete unavailable; falling back to move-to-Purges purge strategy",
                **build_log_context(helper, message_id=message_id, status_code=permanent_delete_response.status_code, purge_strategy="permanentDelete")
            )
        else:
            return permanent_delete_response

    log_info(helper, "Moving message to Purges folder", **build_log_context(helper, message_id=message_id, purge_strategy="move"))
    return move_message_to_purges(helper, message_url, headers)

#Main function for gathering emails.
def collect_events(helper, ew):
    start_time = time.time()
    get_run_stats(helper)
    graph_url = get_graph_base_url(helper)
    access_token = _get_access_token(helper)
    headers = build_request_headers(access_token)

    if is_debug_enabled(helper):
        log_debug(
            helper,
            "Starting email collection run",
            **build_log_context(
                helper,
                message_num=helper.get_arg('message_num'),
                interval=helper.get_arg('interval'),
                request_attachments=should_request_attachments(helper),
                request_internet_headers=should_request_internet_headers(helper),
                request_body=should_request_body(helper),
                request_body_preview=should_request_body_preview(helper),
                analyze_link_mismatch=helper.get_arg('analyze_link_mismatch'),
                analyze_url_risk=helper.get_arg('analyze_url_risk'),
                analyze_html_risk=helper.get_arg('analyze_html_risk'),
                analyze_attachment_risk=helper.get_arg('analyze_attachment_risk'),
                analyze_message_risk=helper.get_arg('analyze_message_risk'),
                analyze_sender_impersonation=helper.get_arg('analyze_sender_impersonation'),
                normalize_auth_results=helper.get_arg('normalize_auth_results'),
                debug_sample_limit=get_debug_sample_limit(helper),
                debug_message_id=get_debug_message_id(helper),
            )
        )
    if not should_use_permanent_delete(helper):
        log_info(
            helper,
            "Using move-to-Purges purge strategy because Graph permanentDelete is not used for this endpoint",
            **build_log_context(helper, purge_strategy="move")
        )

    # Purge calendar events before message processing
    purge_calendar_events(helper, graph_url, headers)

    try:
        messages = fetch_message_pages(helper, graph_url, headers)
    except Exception as e:
        log_error(helper, "Initial message retrieval failed", **build_log_context(helper, error=str(e)))
        log_debug(helper, traceback.format_exc(), **build_log_context(helper))
        log_run_summary(helper, time.time() - start_time)
        return

    for message in messages:
        message_data = []

        for item in message:
            stats = get_run_stats(helper)
            stats["messages_processed"] += 1
            try:
                message_items = build_message_items(item)
                message_body = item.get('body', {}).get('content', '')
                message_body_content_type = item.get('body', {}).get('contentType', '')
                body_preview = item.get('bodyPreview', '')
                attachments = item.get('attachments', [])
                single_value_properties = item.get('singleValueExtendedProperties', [])

                internet_message_headers, message_path, message_items = process_internet_message_headers(item, message_items, helper)

                if helper.get_arg('get_internet_headers'):
                    message_items['Internet-Headers'] = internet_message_headers

                if helper.get_arg('get_message_path'):
                    message_items['message_path'] = list(map(lambda x: x['value'], message_path))

                if helper.get_arg('get_x_headers'):
                    x_headers = [x_header for x_header in internet_message_headers if "X-" in x_header['name']]
                    message_items['X-Headers'] = x_headers

                if helper.get_arg('get_auth_results'):
                    auth_results = [auth_result for auth_result in internet_message_headers if "Authentication-Results" in auth_result['name']]
                    message_items['Authentication-Results'] = list(map(lambda x: x['value'], auth_results))

                if helper.get_arg('get_arc_results'):
                    arc_headers = [
                        arc_header
                        for arc_header in internet_message_headers
                        if arc_header.get('name') in ("ARC-Seal", "ARC-Message-Signature", "ARC-Authentication-Results")
                    ]
                    if arc_headers:
                        message_items['ARC-Headers'] = arc_headers

                if helper.get_arg('get_spf_results'):
                    spf_results = [spf_result for spf_result in internet_message_headers if "Received-SPF" in spf_result['name']]
                    message_items['Received-SPF'] = list(map(lambda x: x['value'], spf_results))

                if helper.get_arg('get_dkim_signature'):
                    dkim_sig = [dkim_sig for dkim_sig in internet_message_headers if "DKIM-Signature" in dkim_sig['name']]
                    message_items['DKIM-Signature'] = dkim_sig

                if helper.get_arg('normalize_auth_results') or helper.get_arg('analyze_message_risk'):
                    normalized_auth = normalize_auth_results(helper, internet_message_headers, message_items.get('from'))
                    for key in ('spf_result', 'dkim_result', 'dmarc_result', 'arc_result', 'dmarc_aligned', 'auth_summary'):
                        if normalized_auth.get(key) is not None:
                            message_items[key] = normalized_auth[key]

                if helper.get_arg('get_tracking_pixel') and pixeltrack_re.search(message_body):
                    pixel_data = pixeltrack_re.search(message_body)
                    message_items['tracking_pixel'] = "true"
                    message_items['tracking_pixel_data'] = pixel_data.group(0)

                for prop in single_value_properties:
                    if prop['id'] == "Long 0xe08":
                        message_items['size'] = prop['value']

                body_type = helper.get_arg('body_type')

                if helper.get_arg('get_body'):
                    formatted_body = format_message_body(message_body, body_type)
                    message_items['body'] = formatted_body

                if helper.get_arg('get_body_preview'):
                    formatted_body_preview = format_message_body(body_preview, body_type)
                    message_items['bodyPreview'] = formatted_body_preview

                if helper.get_arg('extract_body_iocs'):
                    ioc_data = ingest_iocs_from_body(helper, message_body)
                    message_items.update(ioc_data)

                if (helper.get_arg('analyze_link_mismatch') or helper.get_arg('analyze_message_risk')) and (message_body_content_type == 'html' or '<a' in message_body.lower()):
                    suspicious_links = analyze_link_mismatches(message_body)
                    if suspicious_links:
                        message_items['link_analysis'] = suspicious_links
                        message_items['link_mismatch_detected'] = True
                        message_items['link_mismatch_count'] = len(suspicious_links)

                if helper.get_arg('analyze_url_risk') or helper.get_arg('analyze_message_risk'):
                    risky_urls = analyze_url_risks(message_body)
                    if risky_urls:
                        message_items['url_risk_analysis'] = risky_urls
                        message_items['url_risk_detected'] = True
                        message_items['url_risk_count'] = len(risky_urls)
                        for field_name, indicator_name in (
                            ('url_shortener_detected', 'shortener_domain'),
                            ('url_redirect_detected', 'redirect_parameter_present'),
                            ('url_ip_literal_detected', 'ip_literal_host'),
                            ('url_punycode_detected', 'punycode_domain'),
                            ('url_credential_harvest_detected', 'credential_harvest_terms'),
                            ('url_brand_keyword_mismatch_detected', 'brand_keyword_mismatch'),
                        ):
                            if any(indicator_name in url_item.get('indicators', []) for url_item in risky_urls):
                                message_items[field_name] = True

                if helper.get_arg('analyze_html_risk') or helper.get_arg('analyze_message_risk'):
                    html_analysis = analyze_html_risks(message_body)
                    if html_analysis:
                        message_items['html_risk_analysis'] = html_analysis
                        message_items['html_risk_detected'] = True
                        message_items['html_form_detected'] = html_analysis['contains_form']
                        message_items['html_hidden_text_detected'] = html_analysis['hidden_text_detected']
                        message_items['html_remote_image_detected'] = html_analysis['remote_image_count'] > 0
                        message_items['html_suspicious_css_detected'] = html_analysis['suspicious_css_detected']
                        message_items['html_tracking_indicator_count'] = html_analysis['tiny_image_count']

                if helper.get_arg('analyze_encoded_content') or helper.get_arg('decode_encoded_content') or helper.get_arg('analyze_message_risk'):
                    encoded_content = analyze_encoded_content(helper, message_body)
                    if encoded_content:
                        message_items['encoded_content_analysis'] = encoded_content['encoded_content_analysis']
                        message_items['encoded_content_detected'] = True
                        message_items['encoded_content_count'] = encoded_content['encoded_content_count']
                        message_items['encoded_content_types'] = encoded_content['encoded_content_types']
                        message_items['encoded_content_indicators'] = encoded_content['encoded_content_indicators']
                        message_items['encoded_content_risk_detected'] = encoded_content['encoded_content_risk_detected']
                        for field_name, indicator_name in (
                            ('encoded_html_payload_detected', 'embedded_html_payload'),
                            ('encoded_javascript_payload_detected', 'embedded_javascript_payload'),
                            ('encoded_url_payload_detected', 'embedded_url_payload'),
                            ('encoded_ip_payload_detected', 'decoded_text_contains_ip'),
                            ('encoded_domain_payload_detected', 'decoded_text_contains_domain'),
                            ('encoded_command_payload_detected', 'decoded_text_contains_command'),
                            ('encoded_credential_payload_detected', 'decoded_text_contains_credential_term'),
                            ('encoded_zip_payload_detected', 'zip_magic_bytes'),
                            ('encoded_binary_payload_detected', 'binary_payload'),
                        ):
                            if indicator_name in encoded_content['encoded_content_indicators']:
                                message_items[field_name] = True

                if helper.get_arg('analyze_sender_impersonation') or helper.get_arg('analyze_message_risk'):
                    sender_analysis = analyze_sender_impersonation(helper, item, message_items)
                    if sender_analysis:
                        message_items['sender_analysis'] = sender_analysis
                        message_items['sender_impersonation_suspected'] = True

                if attachments:
                    process_message_attachments(helper, attachments, message_body, message_items)

                if helper.get_arg('analyze_message_risk'):
                    message_items.update(calculate_message_risk(message_items))
                log_message_debug(helper, "Processed message payload", item=item, message_items=message_items)
            except Exception as e:
                stats["messages_processing_failed"] += 1
                log_error(helper, "Error processing message", **build_log_context(helper, message_id=item.get("id"), error=str(e), item_summary=sanitize_value({
                    "subject": item.get("subject"),
                    "hasAttachments": item.get("hasAttachments"),
                    "keys": sorted(item.keys()),
                })))
                log_debug(helper, traceback.format_exc(), **build_log_context(helper, message_id=item.get("id")))
                continue

            try:
                purge_response = purge_message(helper, graph_url, headers, item)
                if purge_response is None:
                    stats["messages_skipped_pre_purge"] += 1
                    log_warning(helper, "Skipping ingest because purge prerequisites failed", **build_log_context(helper, message_id=message_items["id"]))
                    continue
                if purge_response.status_code not in PURGE_SUCCESS_STATUS_CODES:
                    stats["messages_purge_failed"] += 1
                    log_warning(helper, "Couldn't purge message", **build_log_context(helper, message_id=message_items["id"], status_code=purge_response.status_code, response_text=purge_response.text))
                else:
                    stats["messages_ingested"] += 1
                    log_info(helper, "Ingesting message", **build_log_context(helper, message_id=message_items["id"]))
                    message_data.append(message_items)
            except Exception as e:
                stats["messages_purge_failed"] += 1
                log_error(helper, "Error handling purge response", **build_log_context(helper, message_id=message_items["id"], error=str(e)))
                log_debug(helper, traceback.format_exc(), **build_log_context(helper, message_id=message_items["id"]))

        #ingest messages to splunk
        ingest_messages_to_splunk(helper, ew, message_data)

    log_run_summary(helper, time.time() - start_time)
