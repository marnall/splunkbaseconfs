#!/usr/bin/env python3
"""
Legacy external search command for Splunk:
| phishiqplus [url_field=<field>] [url=<single_url>] [api_key=<key>] [api_base_url=<url>]
"""

from __future__ import absolute_import, print_function

import configparser
import json
import os
import ssl
import sys
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import splunk.Intersplunk as intersplunk

from phishiq_client import PhishIQClient


DEFAULT_API_BASE_URL = "https://phishiq-api-371323850079.us-central1.run.app"
PASSWORD_REALM = "phishiq"


def _parse_args(argv):
    args = {}
    for token in argv[1:]:
        if "=" not in token:
            continue
        k, v = token.split("=", 1)
        args[k.strip()] = v.strip()
    return args


def _load_default_stanza():
    """
    Read defaults from app inputs.conf.
    local/inputs.conf overrides default/inputs.conf when present.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.dirname(script_dir)
    local_inputs = os.path.join(app_root, "local", "inputs.conf")
    default_inputs = os.path.join(app_root, "default", "inputs.conf")
    stanza = "phishiqplus_enrichment://default"

    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read([default_inputs, local_inputs])
    if parser.has_section(stanza):
        return dict(parser.items(stanza))
    return {}


def _ensure_input_rows(results, single_url):
    if results:
        return results
    if single_url:
        return [{"url": single_url}]
    return []


def _connect_splunk_service(settings):
    try:
        bin_dir = os.path.dirname(os.path.abspath(__file__))
        app_lib = os.path.join(os.path.dirname(bin_dir), "lib")
        if os.path.isdir(app_lib) and app_lib not in sys.path:
            sys.path.insert(0, app_lib)
        import splunklib.client as client
    except Exception:
        return None

    token = (settings.get("sessionKey") or settings.get("session_key") or "").strip()
    server_uri = (settings.get("server_uri") or settings.get("splunkd_uri") or "https://127.0.0.1:8089").strip()
    if not token:
        return None

    try:
        parsed = urlparse(server_uri)
        host = parsed.hostname or "127.0.0.1"
        port = int(parsed.port or 8089)
        scheme = parsed.scheme or "https"
        # Local splunkd commonly uses a self-signed cert; verify=True breaks connect/submit.
        return client.connect(host=host, port=port, scheme=scheme, token=token, verify=False)
    except Exception:
        return None


def _load_api_key_from_password_store(service, input_name):
    if service is None:
        return None
    username = "api_key:{}".format(input_name)
    try:
        for c in service.storage_passwords:
            if c.content.get("realm") == PASSWORD_REALM and c.content.get("username") == username:
                return c.content.get("clear_password")
    except Exception:
        return None
    return None


def _emit_internal_summary(service, index_name, sourcetype, payload):
    if service is None:
        return False
    try:
        service.indexes[index_name].submit(
            json.dumps(payload),
            sourcetype=sourcetype,
            source="phishiqplus_search_command",
        )
        return True
    except Exception:
        return False


def _emit_internal_summary_via_rest(settings, index_name, sourcetype, payload):
    """
    Fallback telemetry writer that does not require splunklib.
    Uses Splunk's simple receiver endpoint with the current session key.
    """
    token = settings.get("sessionKey") or settings.get("session_key")
    server_uri = settings.get("server_uri") or settings.get("splunkd_uri") or "https://127.0.0.1:8089"
    if not token:
        return False

    try:
        parsed = urlparse(server_uri)
        scheme = parsed.scheme or "https"
        host = parsed.hostname or "127.0.0.1"
        port = int(parsed.port or 8089)
        query = urlencode(
            {
                "index": index_name,
                "sourcetype": sourcetype,
                "source": "phishiqplus_search_command",
                "host": "search",
            }
        )
        endpoint = "{}://{}:{}/services/receivers/simple?{}".format(scheme, host, port, query)
        req = Request(
            endpoint,
            data=(json.dumps(payload) + "\n").encode("utf-8"),
            headers={
                "Authorization": "Splunk {}".format(token.strip()),
                "Content-Type": "text/plain",
            },
            method="POST",
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(req, timeout=5, context=ctx):
            return True
    except Exception:
        return False


def _enrich_row(client, row, url_field):
    url = str(row.get(url_field, "")).strip()
    if not url:
        row["phishiq_error"] = "missing_url"
        return row

    pred = client.predict_single(url)
    if pred is None:
        row["phishiq_error"] = "no_response"
        row["phishiq_risk_level"] = "UNKNOWN"
        return row

    row["phishiq_prediction"] = pred.get("prediction")
    row["phishiq_source"] = pred.get("source", "")
    row["phishiq_confidence"] = pred.get("confidence")
    row["phishiq_risk_level"] = pred.get("risk_level", "")
    row["phishiq_cached"] = pred.get("cached", False)
    details = pred.get("details")
    if isinstance(details, dict):
        row["phishiq_domain"] = details.get("domain")
        row["phishiq_analysis_time"] = details.get("analysis_time")
    return row


def main():
    try:
        started = time.time()
        args = _parse_args(sys.argv)
        defaults = _load_default_stanza()
        results, dummy, settings = intersplunk.getOrganizedResults()

        url_field = args.get("url_field", "url")
        single_url = args.get("url", "")
        api_base_url = args.get("api_base_url") or defaults.get("api_base_url", DEFAULT_API_BASE_URL)
        service = _connect_splunk_service(settings)
        api_key = (
            args.get("api_key")
            or _load_api_key_from_password_store(service, "phishiqplus_enrichment://default")
            or defaults.get("api_key")
            or os.environ.get("PHISHIQPLUS_API_KEY", "")
        )
        timeout = int(args.get("request_timeout_seconds") or defaults.get("request_timeout_seconds", "30"))
        ssl_verify = (args.get("ssl_verify") or defaults.get("ssl_verify", "1")).lower() in ("1", "true", "yes")
        telemetry_enabled = (args.get("telemetry_enabled") or defaults.get("telemetry_enabled", "1")).lower() in ("1", "true", "yes")
        internal_index = args.get("internal_index") or defaults.get("internal_index", "phishiqplus_internal")
        internal_sourcetype = args.get("internal_sourcetype") or defaults.get("internal_sourcetype", "phishiqplus:internal")

        if not api_key:
            raise ValueError("API key is required. Use api_key=<key> or configure and save the modular input.")

        rows = _ensure_input_rows(results, single_url)
        client = PhishIQClient(
            base_url=api_base_url,
            api_key=api_key,
            timeout_seconds=timeout,
            ssl_verify=ssl_verify,
            cache_enabled=True,
        )
        out = [_enrich_row(client, row, url_field) for row in rows]
        urls_total = len(out)
        urls_success = sum(1 for row in out if row.get("phishiq_error") in (None, ""))
        urls_failed = max(0, urls_total - urls_success)
        cache_hits = sum(1 for row in out if bool(row.get("phishiq_cached", False)))
        if telemetry_enabled:
            summary_payload = {
                "event_type": "run_summary",
                "stanza": "phishiqplus_search_command",
                "mode": "manual_search_command",
                "api_base_url": api_base_url,
                "urls_total": urls_total,
                "urls_success": urls_success,
                "urls_failed": urls_failed,
                "cache_hits": cache_hits,
                "duration_ms": int((time.time() - started) * 1000),
                "degraded_mode": "n/a_manual",
                "client_metrics": client.get_and_reset_metrics(),
            }
            wrote = _emit_internal_summary(service, internal_index, internal_sourcetype, summary_payload)
            if not wrote:
                _emit_internal_summary_via_rest(settings, internal_index, internal_sourcetype, summary_payload)
        intersplunk.outputResults(out)
    except Exception as e:
        intersplunk.generateErrorResults("phishiqplus command failed: {}".format(e))


if __name__ == "__main__":
    main()
