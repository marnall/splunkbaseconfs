#!/usr/bin/env python3
"""
PhishIQPlus modular input for Splunk.
Deploy on Heavy Forwarder: enriches events with PhishIQPlus API (batch or single).
Architecture: Heavy Forwarder -> PhishIQPlus API -> forward enriched data to Splunk Cloud.
"""

from __future__ import absolute_import, print_function

import gzip
import json
import logging
import sys
import os
import time
import glob
import re
import hashlib
import math
from urllib.parse import urlsplit, urlunsplit

# Ensure bin/ is on path when run by Splunk or standalone
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

# App-root lib/ (vendored splunk-sdk) must load before splunklib imports (dynamic mode uses jobs.oneshot).
_app_root = os.path.abspath(os.path.join(bin_dir, ".."))
_app_lib = os.path.join(_app_root, "lib")
if os.path.isdir(_app_lib) and _app_lib not in sys.path:
    sys.path.insert(0, _app_lib)

def _import_splunk_modularinput():
    """
    Import splunklib.modularinput with resilient path discovery.
    Some Splunk installs do not expose splunklib on sys.path for custom apps.
    """
    try:
        import splunklib.modularinput as _smi

        return _smi
    except Exception:
        pass

    splunk_home = os.environ.get("SPLUNK_HOME", "/Applications/Splunk")
    candidate_dirs = []

    # Common locations used by Splunk apps shipping splunklib.
    candidate_dirs.extend(glob.glob(os.path.join(splunk_home, "etc", "apps", "*", "lib")))
    candidate_dirs.extend(glob.glob(os.path.join(splunk_home, "etc", "apps", "*", "libs")))
    candidate_dirs.extend(glob.glob(os.path.join(splunk_home, "etc", "apps", "*", "bin")))

    for d in candidate_dirs:
        if d and os.path.isdir(d) and d not in sys.path:
            sys.path.insert(0, d)
        try:
            import splunklib.modularinput as _smi

            return _smi
        except Exception:
            continue
    return None


# Splunk SDK is required for modular input runtime.
smi = _import_splunk_modularinput()

from phishiq_client import PhishIQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "https://phishiq-api-371323850079.us-central1.run.app"
DEFAULT_INDEX = "main"
DEFAULT_SOURCETYPE = "phishiq_enriched"
PASSWORD_REALM = "phishiq"
DEFAULT_INTERNAL_INDEX = "phishiqplus_internal"
DEFAULT_INTERNAL_SOURCETYPE = "phishiqplus:internal"


def _str_param(params, name, default=""):
    v = params.get(name)
    if v is None:
        return default
    return str(v).strip()


def get_scheme():
    """Return the scheme for the PhishIQPlus modular input (Setup UI)."""
    scheme = smi.Scheme("phishiqplus_enrichment")
    scheme.title = "PhishIQPlus URL Enrichment"
    scheme.description = "Enrich events with PhishIQPlus phishing prediction. Deploy on Heavy Forwarder."
    # Validate on save (acts like a built-in Test Connection)
    scheme.use_external_validation = True
    scheme.use_single_instance = False

    # API Key is required for onboarding.
    scheme.add_argument(
        smi.Argument(
            "api_key",
            title="API Key",
            description="API key from PhishIQPlus (required)",
            data_type=smi.Argument.data_type_string,
            required_on_create=True,
        )
    )
    scheme.add_argument(
        smi.Argument(
            "api_base_url",
            title="API Base URL (advanced)",
            description="Optional override. Default points to PhishIQPlus production API.",
            data_type=smi.Argument.data_type_string,
            required_on_create=False,
        )
    )
    scheme.add_argument(smi.Argument("api_key_name", title="API Key Name", description="Optional license label from PhishIQPlus (e.g. Enterprise 1M)", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("request_timeout_seconds", title="Request Timeout (sec)", description="Timeout for API calls", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("rate_limit_mode", title="Rate Limit Mode", description="Low / Standard / High", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("ssl_verify", title="SSL Verify", description="Verify SSL certificate", data_type=smi.Argument.data_type_boolean, required_on_create=False))
    scheme.add_argument(smi.Argument("mode", title="Mode", description="batch or realtime", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search", title="Source Search (dynamic)", description="Splunk search query used in dynamic mode", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("source_url_field", title="Source URL Field (dynamic)", description="Field name containing URL in dynamic mode", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search_limit", title="Source Search Limit (dynamic)", description="Maximum events read per run in dynamic mode", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search_earliest", title="Source Search Earliest (dynamic)", description="Earliest time for dynamic mode search (default: -15m)", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search_latest", title="Source Search Latest (dynamic)", description="Latest time for dynamic mode search (default: now)", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search_overlap_seconds", title="Source Search Overlap (dynamic)", description="Checkpoint overlap in seconds to prevent misses (default: 30)", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search_batch_size", title="Source Search Batch Size (dynamic)", description="Maximum URLs per API batch in dynamic mode (default: 100)", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("source_search_max_urls", title="Source Search Max URLs (dynamic)", description="Hard cap for total URLs processed per dynamic run (default: 1000)", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("dynamic_sleep_ms_between_batches", title="Dynamic Sleep Between Batches (ms)", description="Throttle delay between dynamic API batches", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("url_field", title="URL Field", description="Field name containing URL in events", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("emit_original_event_context", title="Emit Original URL Context", description="Include original URL input as phishiq_original_url in events", data_type=smi.Argument.data_type_boolean, required_on_create=False))
    scheme.add_argument(smi.Argument("emit_source_event_context", title="Emit Source Event Context", description="Include source event metadata and correlation hash in dynamic mode", data_type=smi.Argument.data_type_boolean, required_on_create=False))
    scheme.add_argument(smi.Argument("cache_enabled", title="Cache Enabled", description="Use local cache for API responses", data_type=smi.Argument.data_type_boolean, required_on_create=False))
    scheme.add_argument(smi.Argument("cache_ttl_seconds", title="Cache TTL (sec)", description="Cache entry TTL", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("cache_max_entries", title="Cache Max Entries", description="Max cache size", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("cache_clear_on_start", title="Clear Cache on Start", description="Clear local cache at the start of each run (useful for troubleshooting)", data_type=smi.Argument.data_type_boolean, required_on_create=False))
    scheme.add_argument(smi.Argument("url_list", title="URL List (batch)", description="One URL per line for batch mode", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("retry_max_attempts", title="Retry Attempts", description="Max retry attempts for transient errors (5xx/timeouts)", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("retry_base_delay_ms", title="Retry Base Delay (ms)", description="Base delay for exponential backoff", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("retry_max_delay_ms", title="Retry Max Delay (ms)", description="Max delay for exponential backoff", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("circuit_breaker_failures", title="Circuit Breaker Failures", description="Open circuit after N consecutive failures", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("circuit_breaker_reset_seconds", title="Circuit Breaker Reset (sec)", description="How long to pause calls after circuit opens", data_type=smi.Argument.data_type_number, required_on_create=False))
    scheme.add_argument(smi.Argument("degraded_mode", title="Degraded Mode", description="What to do when API is unavailable: emit_error_event | skip_event", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("telemetry_enabled", title="Telemetry Enabled", description="Emit internal health/metrics events into Splunk", data_type=smi.Argument.data_type_boolean, required_on_create=False))
    scheme.add_argument(smi.Argument("internal_index", title="Internal Index", description="Index for internal telemetry (recommended: phishiqplus_internal)", data_type=smi.Argument.data_type_string, required_on_create=False))
    scheme.add_argument(smi.Argument("internal_sourcetype", title="Internal Sourcetype", description="Sourcetype for internal telemetry (recommended: phishiqplus:internal)", data_type=smi.Argument.data_type_string, required_on_create=False))

    return scheme


def _bool_param(params, name, default=False):
    v = params.get(name)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes")


def _int_param(params, name, default=None):
    v = params.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _extract_urls_from_text(raw_text):
    if not raw_text:
        return []
    pattern = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
    return pattern.findall(str(raw_text))


def _normalize_url(raw_url):
    if raw_url is None:
        return None
    candidate = str(raw_url).strip()
    if not candidate:
        return None
    parts = urlsplit(candidate)
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https"):
        return None
    hostname = (parts.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        return None

    port = parts.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = hostname
    elif port:
        netloc = "{}:{}".format(hostname, port)
    else:
        netloc = hostname

    path = parts.path or "/"
    normalized = urlunsplit((scheme, netloc, path, parts.query, ""))
    return normalized


def _source_event_hash(context, normalized_url):
    c = context or {}
    base = "{}|{}|{}|{}|{}".format(
        str(c.get("_time", "")).strip(),
        str(c.get("host", "")).strip(),
        str(c.get("source", "")).strip(),
        str(c.get("sourcetype", "")).strip(),
        str(normalized_url or "").strip(),
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _unique_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _read_http_body_fully(stream):
    """Read a splunklib response body; some stacks require more than one .read()."""
    if stream is None:
        return b""
    if isinstance(stream, (bytes, bytearray, memoryview)):
        return bytes(stream)
    chunks = []
    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            chunks.append(chunk)
    except Exception:
        if chunks:
            return b"".join(chunks)
        return b""
    return b"".join(chunks)


def _maybe_decompress_splunk_body(body):
    if not body or len(body) < 3:
        return body
    if body[0] == 0x1F and body[1] == 0x8B:
        try:
            return gzip.decompress(body)
        except Exception:
            return body
    return body


def _normalize_spl_query(query):
    """Strip BOM/invisible prefix so leading '|' tests and REST behavior match the UI."""
    if query is None:
        return ""
    s = str(query).replace("\ufeff", "").replace("\u200b", "").strip()
    for bad, good in (
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u201e", '"'),
        ("\u201f", '"'),
    ):
        s = s.replace(bad, good)
    # Entire value sometimes arrives wrapped in ASCII double quotes; then startswith('|') fails and
    # earliest/latest get applied to generating searches -> zero rows.
    while len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].strip()
    # Modular inputs sometimes receive inputs.conf-style \" sequences literally (backslash + quote).
    # That breaks SPL (e.g. eval url=\"https://...\") and Splunk returns results=null with FATAL messages.
    if '\\"' in s:
        s = s.replace('\\"', '"')
    return s


def _splunk_json_fatal_preview(body, max_len=600):
    """First FATAL/ERROR message text from a search/jobs JSON body, or empty string."""
    if not body:
        return ""
    try:
        if isinstance(body, bytes):
            t = body.decode("utf-8", errors="replace").strip()
        else:
            t = str(body).strip()
        if not t.startswith("{"):
            return ""
        doc = json.loads(t)
        if not isinstance(doc, dict):
            return ""
        for msg in doc.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            mtype = (msg.get("type") or "").upper()
            if mtype not in ("FATAL", "ERROR"):
                continue
            text = (msg.get("text") or "").strip()
            if text:
                return text[:max_len]
    except Exception:
        return ""
    return ""


def _splunk_json_messages_summary(body, max_len=900):
    """Concatenate Splunk search JSON messages (any type) for diagnostics."""
    if not body:
        return ""
    try:
        if isinstance(body, bytes):
            t = body.decode("utf-8", errors="replace").strip()
        else:
            t = str(body).strip()
        if not t.startswith("{"):
            return ""
        doc = json.loads(t)
        if not isinstance(doc, dict):
            return ""
        parts = []
        for msg in doc.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            mtype = (msg.get("type") or "").strip()
            text = (msg.get("text") or "").strip()
            if text:
                parts.append("[{}] {}".format(mtype, text))
        out = " | ".join(parts)
        return out[:max_len] if out else ""
    except Exception:
        return ""


def _warn_splunk_search_json_errors(body, context):
    """Log FATAL/ERROR messages from search/jobs JSON when results are empty."""
    if not body:
        return
    try:
        if isinstance(body, bytes):
            t = body.decode("utf-8", errors="replace").strip()
        else:
            t = str(body).strip()
        if not t.startswith("{"):
            return
        doc = json.loads(t)
        if not isinstance(doc, dict):
            return
        for msg in doc.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            mtype = (msg.get("type") or "").upper()
            text = msg.get("text") or ""
            if mtype in ("FATAL", "ERROR") and text:
                logger.warning(
                    "phishiqplus_enrichment: source_search %s Splunk [%s]: %s",
                    context,
                    mtype,
                    text,
                )
    except Exception:
        return


def _oneshot_skip_time_window(search_query):
    """
    Splunk REST oneshot with earliest/latest can return zero rows for generating
    commands (makeresults, inputlookup, gentimes) even when the same SPL works in UI.
    """
    s = _normalize_spl_query(search_query).lower()
    if not s.startswith("|"):
        return False
    head = s[:800]
    return (
        "makeresults" in head
        or "inputlookup" in head
        or "gentimes" in head
    )


def _result_dict_field(record, name):
    """Case-insensitive field lookup for JSON search rows; unwrap single-element lists."""
    if not record or not isinstance(record, dict):
        return ""
    want = (name or "").strip().lower()
    for k, v in record.items():
        if k is None:
            continue
        kn = str(k).lstrip("\ufeff").strip().lower()
        if kn != want:
            continue
        if v is None:
            return ""
        if isinstance(v, list):
            if not v:
                return ""
            v = v[0]
        return str(v)
    return ""


def _iter_splunk_json_result_dicts(body):
    """
    Yield one dict per result row from Splunk oneshot/export JSON.

    Splunk v2 oneshot often returns a single JSON object with a top-level
    "results" array. JSONResultsReader expects newline-delimited JSON; using it
    alone on multi-line or wrapped payloads yields zero rows.
    """
    if body is None:
        return
    if isinstance(body, bytes):
        text = body.decode("utf-8", errors="replace").strip()
    else:
        text = str(body).strip()
    if not text:
        return
    if text.startswith("<?xml") or text.lstrip().startswith("<"):
        return

    try:
        doc = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        doc = None

    if isinstance(doc, dict):
        res = doc.get("results")
        if isinstance(res, list) and len(res) > 0:
            yielded_any = False
            for row in res:
                if isinstance(row, dict):
                    yield row
                    yielded_any = True
            if yielded_any:
                return
        one = doc.get("result")
        if isinstance(one, dict):
            yield one
            return
        # results=[] or missing: body may be NDJSON or multi-doc; fall through

    try:
        import io

        import splunklib.results as splunk_results
    except Exception:
        return

    try:
        stream = io.BytesIO(text.encode("utf-8"))
        for item in splunk_results.JSONResultsReader(stream):
            if isinstance(item, dict):
                yield item
    except Exception:
        return


def _urls_from_splunk_result_dicts(result_dicts, url_field):
    out = []
    field = (url_field or "url").strip()
    for item in result_dicts:
        if not isinstance(item, dict):
            continue
        context = {
            "_time": _result_dict_field(item, "_time"),
            "host": _result_dict_field(item, "host"),
            "source": _result_dict_field(item, "source"),
            "sourcetype": _result_dict_field(item, "sourcetype"),
        }
        direct = _result_dict_field(item, field)
        if direct and str(direct).strip():
            out.append({"url": str(direct).strip(), "context": context})
            continue
        raw_val = _result_dict_field(item, "_raw")
        for extracted in _extract_urls_from_text(raw_val):
            out.append({"url": extracted, "context": context})
    return out


def _collect_urls_from_search(service, query, url_field, limit, earliest_time=None, latest_time=None):
    """
    Returns (url_rows, diagnostics_dict). diagnostics help explain empty results in telemetry.
    """
    diag = {}
    if service is None or not query:
        diag["rest_error"] = "no_service_or_empty_query"
        return [], diag

    search_query = _normalize_spl_query(query)
    if not search_query:
        diag["rest_error"] = "blank_after_normalize"
        return [], diag
    if not search_query.lower().startswith(("search ", "|")):
        search_query = "search {}".format(search_query)

    kwargs = {"output_mode": "json", "count": max(1, int(limit))}
    skip_time = _oneshot_skip_time_window(search_query)
    diag["skip_time_window"] = bool(skip_time)
    diag["rest_query_head"] = search_query[:240] + ("..." if len(search_query) > 240 else "")
    if earliest_time and not skip_time:
        kwargs["earliest_time"] = earliest_time
    if latest_time and not skip_time:
        kwargs["latest_time"] = latest_time

    field = (url_field or "url").strip()

    try:
        response = service.jobs.oneshot(search_query, **kwargs)
        body = _maybe_decompress_splunk_body(_read_http_body_fully(response))
        diag["response_byte_len_oneshot"] = len(body)
        rows_out = _urls_from_splunk_result_dicts(_iter_splunk_json_result_dicts(body), field)
        if rows_out:
            return rows_out, diag
        err = _splunk_json_fatal_preview(body)
        if err:
            diag["splunk_search_error"] = err
        msg_sum = _splunk_json_messages_summary(body)
        if msg_sum:
            diag["splunk_messages_summary"] = msg_sum
        _warn_splunk_search_json_errors(body, "oneshot")
        stream = service.jobs.export(search_query, **kwargs)
        body2 = _maybe_decompress_splunk_body(_read_http_body_fully(stream))
        diag["response_byte_len_export"] = len(body2)
        rows_out = _urls_from_splunk_result_dicts(_iter_splunk_json_result_dicts(body2), field)
        if not rows_out:
            err2 = _splunk_json_fatal_preview(body2)
            if err2 and not diag.get("splunk_search_error"):
                diag["splunk_search_error"] = err2
            msg_sum2 = _splunk_json_messages_summary(body2)
            if msg_sum2 and not diag.get("splunk_messages_summary"):
                diag["splunk_messages_summary"] = msg_sum2
            _warn_splunk_search_json_errors(body2, "export")
        return rows_out, diag
    except Exception as e:
        logger.warning("phishiqplus_enrichment: source_search failed: %s", e)
        diag["rest_error"] = "exception"
        diag["exception_message"] = str(e)[:400]
        return [], diag


def _checkpoint_file(metadata, stanza_name):
    checkpoint_dir = (metadata or {}).get("checkpoint_dir", "")
    if not checkpoint_dir:
        return None
    try:
        if not os.path.isdir(checkpoint_dir):
            os.makedirs(checkpoint_dir)
    except Exception:
        return None
    digest = hashlib.sha256((stanza_name or "default").encode("utf-8")).hexdigest()[:16]
    return os.path.join(checkpoint_dir, "phishiqplus_{}.json".format(digest))


def _read_dynamic_checkpoint(metadata, stanza_name):
    path = _checkpoint_file(metadata, stanza_name)
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        value = data.get("last_run_epoch")
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _write_dynamic_checkpoint(metadata, stanza_name, run_epoch):
    path = _checkpoint_file(metadata, stanza_name)
    if not path:
        return
    payload = {"last_run_epoch": int(run_epoch)}
    tmp = "{}.tmp".format(path)
    try:
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _lock_file(metadata, stanza_name):
    checkpoint_dir = (metadata or {}).get("checkpoint_dir", "")
    if not checkpoint_dir:
        return None
    try:
        if not os.path.isdir(checkpoint_dir):
            os.makedirs(checkpoint_dir)
    except Exception:
        return None
    digest = hashlib.sha256((stanza_name or "default").encode("utf-8")).hexdigest()[:16]
    return os.path.join(checkpoint_dir, "phishiqplus_{}.lock".format(digest))


def _acquire_run_lock(metadata, stanza_name, stale_seconds=3600):
    path = _lock_file(metadata, stanza_name)
    if not path:
        return None
    now = int(time.time())
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(str(now))
        return path
    except OSError:
        try:
            mtime = int(os.path.getmtime(path))
            if now - mtime > max(1, int(stale_seconds)):
                os.remove(path)
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as f:
                    f.write(str(now))
                return path
        except Exception:
            return None
    except Exception:
        return None
    return None


def _release_run_lock(lock_path):
    if not lock_path:
        return
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception:
        pass


def _splunk_app_name_for_rest():
    """
    Namespace for REST searches from this script. Must match the installed app id so
    inputlookup / knowledge objects in this app (e.g. lookups/) resolve. Using app=search
    breaks TA-local lookups while makeresults/index searches still work.
    """
    # Modular input: SPLUNK_ARG_0 is the script path (reliable when __file__ is not under etc/apps).
    for path in (
        os.environ.get("SPLUNK_ARG_0", ""),
        os.path.abspath(__file__),
    ):
        if not path:
            continue
        norm = path.replace("\\", "/")
        if "/apps/" in norm:
            try:
                after = norm.split("/apps/", 1)[1]
                app_name = after.split("/", 1)[0]
                if app_name and app_name not in ("bin", "etc", "apps", ""):
                    return app_name
            except Exception:
                continue
    direct = (os.environ.get("SPLUNK_ARG_APP") or os.environ.get("SPLUNK_APP_NAME") or "").strip()
    if direct:
        return direct
    return "phishiq_ta"


def _connect_splunk_service(server_uri, session_key):
    """
    Create a Splunk service object using Splunk SDK.
    server_uri example: https://127.0.0.1:8089
    """
    try:
        import splunklib.client as client
    except Exception:
        return None

    server_uri = (server_uri or "").strip()
    session_key = (session_key or "").strip()
    if not server_uri or not session_key:
        return None

    # server_uri includes scheme://host:port
    try:
        scheme, rest = server_uri.split("://", 1)
        host, port = rest.split(":", 1)
        host = host.strip()
        port = str(port).strip()
        rest_app = _splunk_app_name_for_rest()
        return client.connect(
            host=host,
            port=int(port),
            scheme=scheme,
            token=session_key,
            verify=False,
            owner="nobody",
            app=rest_app,
            sharing="app",
        )
    except Exception:
        return None


def _password_store_key(input_name):
    # Unique per input stanza
    return "api_key:{}".format(input_name)


def _save_api_key_to_password_store(service, input_name, api_key):
    """
    Save API key into Splunk's encrypted credential store (storage/passwords).
    """
    if service is None:
        raise ValueError("Splunk service unavailable; cannot access credential store.")
    if not api_key:
        raise ValueError("API Key is required.")

    username = _password_store_key(input_name)
    realm = PASSWORD_REALM

    # Delete existing if present (idempotent update)
    try:
        for c in service.storage_passwords:
            if c.content.get("realm") == realm and c.content.get("username") == username:
                c.delete()
                break
    except Exception:
        # Continue to create new
        pass

    try:
        service.storage_passwords.create(api_key, username=username, realm=realm)
    except Exception as e:
        raise ValueError("Failed to save API Key to Splunk credential store: {}".format(e))


def _load_api_key_from_password_store(service, input_name):
    """
    Load API key from Splunk's encrypted credential store.
    Returns None if not found.
    """
    if service is None:
        return None
    username = _password_store_key(input_name)
    realm = PASSWORD_REALM
    try:
        for c in service.storage_passwords:
            if c.content.get("realm") == realm and c.content.get("username") == username:
                return c.content.get("clear_password")
    except Exception:
        return None
    return None


class PhishIQModularInput(smi.Script):
    def get_scheme(self):
        return get_scheme()

    def validate_input(self, validation_definition):
        params = validation_definition.parameters
        api_key = _str_param(params, "api_key", "")
        if not api_key:
            raise ValueError("API Key is required.")
        # Store API key in Splunk credential store (encrypted)
        meta = getattr(validation_definition, "metadata", {}) or {}
        service = _connect_splunk_service(meta.get("server_uri"), meta.get("session_key"))
        input_name = meta.get("name") or "phishiqplus_enrichment"
        _save_api_key_to_password_store(service, input_name, api_key)

        api_base_url = _str_param(params, "api_base_url", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
        timeout = _int_param(params, "request_timeout_seconds", 30)
        ssl_verify = _bool_param(params, "ssl_verify", True)

        client = PhishIQClient(
            base_url=api_base_url,
            api_key=api_key,
            timeout_seconds=timeout,
            ssl_verify=ssl_verify,
            cache_enabled=False,
            retry_max_attempts=_int_param(params, "retry_max_attempts", 3),
            retry_base_delay_ms=_int_param(params, "retry_base_delay_ms", 250),
            retry_max_delay_ms=_int_param(params, "retry_max_delay_ms", 5000),
            circuit_breaker_failures=_int_param(params, "circuit_breaker_failures", 5),
            circuit_breaker_reset_seconds=_int_param(params, "circuit_breaker_reset_seconds", 60),
        )
        ok, msg = client.test_connection()
        if not ok:
            raise ValueError("Test Connection failed: {}".format(msg))

    def stream_events(self, inputs, ew):
        meta = getattr(inputs, "metadata", {}) or {}
        service = _connect_splunk_service(meta.get("server_uri"), meta.get("session_key"))

        for name, input_item in inputs.inputs.items():
            run_started = time.time()
            params = input_item
            lock_path = _acquire_run_lock(meta, name, stale_seconds=3600)
            if not lock_path:
                ew.log("INFO", "phishiqplus_enrichment: skipped stanza {} (lock held by another run)".format(name))
                continue

            try:
                # Security: read API key from credential store. If not present, fall back to stanza value.
                api_key = _load_api_key_from_password_store(service, name) or _str_param(params, "api_key", "")
                if not api_key:
                    ew.log(
                        "ERROR",
                        "phishiqplus_enrichment: API Key not found in credential store. Please re-save the input to store it securely.",
                    )
                    continue
                api_base_url = _str_param(params, "api_base_url", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
                timeout = _int_param(params, "request_timeout_seconds", 30)
                ssl_verify = _bool_param(params, "ssl_verify", True)
                cache_enabled = _bool_param(params, "cache_enabled", True)
                cache_ttl = _int_param(params, "cache_ttl_seconds", 86400)
                cache_max = _int_param(params, "cache_max_entries", 10000)
                cache_clear_on_start = _bool_param(params, "cache_clear_on_start", False)
                index = _str_param(params, "index", DEFAULT_INDEX) or DEFAULT_INDEX
                sourcetype = _str_param(params, "sourcetype", DEFAULT_SOURCETYPE) or DEFAULT_SOURCETYPE
                mode = _str_param(params, "mode", "batch").lower() or "batch"
                degraded_mode = _str_param(params, "degraded_mode", "emit_error_event") or "emit_error_event"
                telemetry_enabled = _bool_param(params, "telemetry_enabled", True)
                internal_index = _str_param(params, "internal_index", DEFAULT_INTERNAL_INDEX) or DEFAULT_INTERNAL_INDEX
                internal_sourcetype = _str_param(params, "internal_sourcetype", DEFAULT_INTERNAL_SOURCETYPE) or DEFAULT_INTERNAL_SOURCETYPE
                emit_original_event_context = _bool_param(params, "emit_original_event_context", False)
                emit_source_event_context = _bool_param(params, "emit_source_event_context", True)

                client = PhishIQClient(
                    base_url=api_base_url,
                    api_key=api_key,
                    timeout_seconds=timeout,
                    ssl_verify=ssl_verify,
                    cache_enabled=cache_enabled,
                    cache_ttl_seconds=cache_ttl,
                    cache_max_entries=cache_max,
                    retry_max_attempts=_int_param(params, "retry_max_attempts", 3),
                    retry_base_delay_ms=_int_param(params, "retry_base_delay_ms", 250),
                    retry_max_delay_ms=_int_param(params, "retry_max_delay_ms", 5000),
                    circuit_breaker_failures=_int_param(params, "circuit_breaker_failures", 5),
                    circuit_breaker_reset_seconds=_int_param(params, "circuit_breaker_reset_seconds", 60),
                    degraded_mode=degraded_mode,
                )

                if cache_clear_on_start:
                    client.clear_cache()

                checkpoint_used = False
                effective_earliest = ""
                effective_latest = ""
                source_search_limit = 0
                pre_dedupe_count = 0
                url_rows = []
                dynamic_search_diag = {}
                if mode == "dynamic":
                    source_search = _normalize_spl_query(_str_param(params, "source_search", ""))
                    source_url_field = _str_param(params, "source_url_field", "url") or "url"
                    source_search_limit = _int_param(params, "source_search_limit", 500)
                    source_search_earliest = _str_param(params, "source_search_earliest", "-15m") or "-15m"
                    source_search_latest = _str_param(params, "source_search_latest", "now") or "now"
                    source_search_overlap_seconds = _int_param(params, "source_search_overlap_seconds", 30)
                    checkpoint_epoch = _read_dynamic_checkpoint(meta, name)
                    if checkpoint_epoch is not None:
                        checkpoint_used = True
                        safe_overlap = max(0, source_search_overlap_seconds or 0)
                        effective_earliest = str(max(0, checkpoint_epoch - safe_overlap))
                        effective_latest = "now"
                    else:
                        effective_earliest = source_search_earliest
                        effective_latest = source_search_latest
                    url_rows, dynamic_search_diag = _collect_urls_from_search(
                        service,
                        source_search,
                        source_url_field,
                        source_search_limit,
                        earliest_time=effective_earliest,
                        latest_time=effective_latest,
                    )
                else:
                    url_list_raw = params.get("url_list") or params.get("urls")
                    if url_list_raw:
                        if isinstance(url_list_raw, (list, tuple)):
                            url_rows = [{"url": u.strip(), "context": {}} for u in url_list_raw if u and isinstance(u, str) and u.strip()]
                        else:
                            url_rows = [{"url": u.strip(), "context": {}} for u in str(url_list_raw).splitlines() if u.strip()]

                pre_dedupe_count = len(url_rows)
                prepared = []
                seen_norm = set()
                urls_invalid = 0
                urls_normalized_changed = 0
                for row in url_rows:
                    raw_url = row.get("url", "")
                    source_context = row.get("context", {}) or {}
                    normalized_url = _normalize_url(raw_url)
                    if not normalized_url:
                        urls_invalid += 1
                        continue
                    if normalized_url != raw_url:
                        urls_normalized_changed += 1
                    if normalized_url in seen_norm:
                        continue
                    seen_norm.add(normalized_url)
                    prepared.append({"original": raw_url, "normalized": normalized_url, "source_context": source_context})

                dynamic_max_urls = _int_param(params, "source_search_max_urls", 1000)
                if mode == "dynamic" and dynamic_max_urls and dynamic_max_urls > 0 and len(prepared) > dynamic_max_urls:
                    prepared = prepared[:dynamic_max_urls]

                if not prepared:
                    ew.log(
                        "INFO",
                        "phishiqplus_enrichment: no valid URLs found after normalization/filters.",
                    )
                    if mode == "dynamic":
                        if service is None:
                            fail_reason = "splunk_service_unavailable"
                        elif not source_search:
                            fail_reason = "source_search_empty"
                        elif pre_dedupe_count == 0:
                            fail_reason = "no_rows_from_source_search"
                        else:
                            fail_reason = "urls_failed_validation"
                    else:
                        fail_reason = "no_urls_found"
                    if telemetry_enabled:
                        summary_payload = {
                            "event_type": "run_summary",
                            "stanza": name,
                            "api_base_url": api_base_url,
                            "urls_total": 0,
                            "urls_success": 0,
                            "urls_failed": 0,
                            "cache_hits": 0,
                            "duration_ms": int((time.time() - run_started) * 1000),
                            "reason": fail_reason,
                            "mode": mode,
                            "checkpoint_used": checkpoint_used,
                            "effective_earliest": effective_earliest,
                            "effective_latest": effective_latest,
                            "source_search_limit": source_search_limit,
                            "urls_deduped": max(0, pre_dedupe_count - len(prepared)),
                            "urls_invalid": urls_invalid,
                            "urls_normalized_changed": urls_normalized_changed,
                        }
                        if mode == "dynamic":
                            summary_payload["rest_namespace_app"] = _splunk_app_name_for_rest()
                        if mode == "dynamic" and dynamic_search_diag:
                            summary_payload["dynamic_rest_query_head"] = dynamic_search_diag.get("rest_query_head", "")
                            summary_payload["dynamic_skip_time_window"] = dynamic_search_diag.get("skip_time_window")
                            if dynamic_search_diag.get("splunk_search_error"):
                                summary_payload["dynamic_splunk_error"] = dynamic_search_diag.get("splunk_search_error")
                            if dynamic_search_diag.get("splunk_messages_summary"):
                                summary_payload["dynamic_splunk_messages"] = dynamic_search_diag.get("splunk_messages_summary")
                            if dynamic_search_diag.get("response_byte_len_oneshot") is not None:
                                summary_payload["dynamic_response_bytes_oneshot"] = dynamic_search_diag.get(
                                    "response_byte_len_oneshot"
                                )
                            if dynamic_search_diag.get("response_byte_len_export") is not None:
                                summary_payload["dynamic_response_bytes_export"] = dynamic_search_diag.get(
                                    "response_byte_len_export"
                                )
                            if dynamic_search_diag.get("rest_error"):
                                summary_payload["dynamic_rest_error"] = dynamic_search_diag.get("rest_error")
                            if dynamic_search_diag.get("exception_message"):
                                summary_payload["dynamic_exception"] = dynamic_search_diag.get("exception_message")
                        ew.write_event(
                            smi.Event(
                                data=json.dumps(summary_payload),
                                source="phishiqplus_enrichment",
                                index=internal_index,
                                sourcetype=internal_sourcetype,
                            )
                        )
                    continue

                batch_size = _int_param(params, "source_search_batch_size", 100)
                if not batch_size or batch_size <= 0:
                    batch_size = 100
                batch_size = min(batch_size, 100)
                sleep_ms = _int_param(params, "dynamic_sleep_ms_between_batches", 0)
                if sleep_ms is None or sleep_ms < 0:
                    sleep_ms = 0

                url_success = 0
                url_failed = 0
                cache_hits = 0
                batches_total = int(math.ceil(float(len(prepared)) / float(batch_size)))

                for batch_idx in range(batches_total):
                    start = batch_idx * batch_size
                    end = start + batch_size
                    batch_items = prepared[start:end]
                    batch_urls = [item["normalized"] for item in batch_items]
                    results = client.predict_batch(batch_urls, fast_mode=False)
                    for i, item in enumerate(batch_items):
                        normalized_url = item["normalized"]
                        original_url = item["original"]
                        source_context = item.get("source_context", {}) or {}
                        pred = results[i] if i < len(results) else None
                        if pred is None:
                            url_failed += 1
                            if degraded_mode == "skip_event":
                                continue
                            event_data = {
                                "url": normalized_url,
                                "phishiq_error": "no_response",
                                "phishiq_risk_level": "UNKNOWN",
                                "phishiq_degraded_mode": degraded_mode,
                            }
                        else:
                            url_success += 1
                            event_data = {
                                "url": normalized_url,
                                "phishiq_prediction": pred.get("prediction"),
                                "phishiq_source": pred.get("source", ""),
                                "phishiq_confidence": pred.get("confidence"),
                                "phishiq_risk_level": pred.get("risk_level", ""),
                                "phishiq_cached": pred.get("cached", False),
                            }
                            if pred.get("cached", False):
                                cache_hits += 1
                            details = pred.get("details")
                            if isinstance(details, dict):
                                event_data["phishiq_domain"] = details.get("domain")
                                event_data["phishiq_analysis_time"] = details.get("analysis_time")
                        if emit_original_event_context:
                            event_data["phishiq_original_url"] = original_url
                        if mode == "dynamic" and emit_source_event_context:
                            event_data["phishiq_source_event_time"] = source_context.get("_time", "")
                            event_data["phishiq_source_event_host"] = source_context.get("host", "")
                            event_data["phishiq_source_event_source"] = source_context.get("source", "")
                            event_data["phishiq_source_event_sourcetype"] = source_context.get("sourcetype", "")
                            event_data["phishiq_source_event_hash"] = _source_event_hash(source_context, normalized_url)

                        ew.write_event(
                            smi.Event(
                                data=json.dumps(event_data),
                                source=normalized_url[:255],
                                index=index,
                                sourcetype=sourcetype,
                            )
                        )
                    if sleep_ms > 0 and batch_idx < batches_total - 1:
                        time.sleep(float(sleep_ms) / 1000.0)

                ew.log("INFO", "phishiqplus_enrichment: processed {} URLs for stanza {}".format(len(prepared), name))

                if telemetry_enabled:
                    ok_summary = {
                        "event_type": "run_summary",
                        "stanza": name,
                        "api_base_url": api_base_url,
                        "urls_total": len(prepared),
                        "urls_success": url_success,
                        "urls_failed": url_failed,
                        "cache_hits": cache_hits,
                        "duration_ms": int((time.time() - run_started) * 1000),
                        "client_metrics": client.get_and_reset_metrics(),
                        "cache": {
                            "enabled": cache_enabled,
                            "ttl_seconds": cache_ttl,
                            "max_entries": cache_max,
                            "cleared_on_start": cache_clear_on_start,
                            "stats": client.cache_stats(),
                        },
                        "degraded_mode": degraded_mode,
                        "mode": mode,
                        "checkpoint_used": checkpoint_used,
                        "effective_earliest": effective_earliest,
                        "effective_latest": effective_latest,
                        "source_search_limit": source_search_limit,
                        "urls_deduped": max(0, pre_dedupe_count - len(prepared)),
                        "urls_invalid": urls_invalid,
                        "urls_normalized_changed": urls_normalized_changed,
                        "batch_size": batch_size,
                        "batches_total": batches_total,
                    }
                    if mode == "dynamic":
                        ok_summary["rest_namespace_app"] = _splunk_app_name_for_rest()
                    ew.write_event(
                        smi.Event(
                            data=json.dumps(ok_summary),
                            source="phishiqplus_enrichment",
                            index=internal_index,
                            sourcetype=internal_sourcetype,
                        )
                    )

                if mode == "dynamic":
                    _write_dynamic_checkpoint(meta, name, int(time.time()))
            finally:
                _release_run_lock(lock_path)


def main():
    if smi is None:
        logger.error("splunklib not available; run inside Splunk or install splunk-sdk")
        sys.exit(1)
    PhishIQModularInput().run(sys.argv)


if __name__ == "__main__":
    main()
