import datetime
import json
import os
import re
import sys
import time
from urllib.parse import parse_qs

from splunk.persistconn.application import PersistentServerConnectionApplication

APP_BIN = os.path.dirname(os.path.abspath(__file__))
if APP_BIN not in sys.path:
    sys.path.insert(0, APP_BIN)

from dv_ioc_intelligence_lib import audit
from dv_ioc_intelligence_lib.engine import EnrichmentEngine
from dv_ioc_intelligence_lib.ioc import MATCH_TYPES, TYPES, normalize_exclusion
from dv_ioc_intelligence_lib.providers import validate_api_url, validate_proxy_url
from dv_ioc_intelligence_lib.splunk_api import SplunkAPI
from dv_ioc_intelligence_lib.store import Store, valid_email_list


EDIT_CAPABILITY = "edit_dv_ioc_intelligence"
PROVIDERS = ("virustotal", "abuseipdb", "misp", "otx")
SEVERITIES = ("informational", "low", "medium", "high", "critical")
SAFE_KEY_FIELDS = (
    "provider", "key_id", "label", "ending", "minute_used", "daily_count",
    "daily_window", "blocked_until", "block_reason", "last_used_at", "last_status",
)


def _pairs(value):
    if isinstance(value, dict):
        return {key: item[-1] if isinstance(item, list) and item else item for key, item in value.items()}
    output = {}
    for item in value or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            output[item[0]] = item[1]
        elif isinstance(item, dict) and "name" in item:
            output[item["name"]] = item.get("value", "")
    return output


def _json_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _request_data(request):
    data = {}
    data.update(_json_object(request.get("payload")))

    body = request.get("body") or ""
    body_data = _json_object(body)
    data.update(body_data)
    if isinstance(body, str) and body and not body_data:
        encoded = parse_qs(body, keep_blank_values=True)
        encoded = {key: values[-1] for key, values in encoded.items() if values}
        data.update(_json_object(encoded.get("payload")))
        data.update({key: value for key, value in encoded.items() if key != "payload"})

    form = _pairs(request.get("form"))
    data.update(_json_object(form.get("payload")))
    data.update({key: value for key, value in form.items() if key != "payload"})
    return data


def _int(value, name, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s must be an integer" % name) from exc
    if number < minimum or number > maximum:
        raise ValueError("%s is outside the allowed range" % name)
    return str(number)


def _truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class DVIOCIntelligenceRestHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            session = request.get("session", {})
            if not isinstance(session, dict):
                session = {}
            token = session.get("authtoken")
            user = session.get("user", "unknown")
            server = request.get("server", {})
            server_uri = server.get("rest_uri") if isinstance(server, dict) else ""
            server_uri = server_uri or request.get("server_uri") or "https://127.0.0.1:8089"
            store = Store(SplunkAPI(token, server_uri))
            query = _pairs(request.get("query"))
            data = _request_data(request)
            action = data.get("action") or query.get("action") or "bootstrap"
            method = str(request.get("method", "GET")).upper()

            if method != "GET":
                self._require_edit(store)

            if method == "GET" and action in ("bootstrap", "setup_bootstrap"):
                return self._response(200, self._bootstrap(store, setup=action == "setup_bootstrap"))
            if method == "GET" and action == "activity":
                return self._response(200, self._activity(store))
            if method == "GET" and action == "health":
                return self._response(200, self._health(store))
            if method == "POST" and action == "save_settings":
                settings = self._validate_settings(data.get("settings", {}))
                for provider in PROVIDERS:
                    if settings[provider]["enabled"] == "1" and not store.list_keys(provider):
                        raise ValueError("Add at least one %s API key before enabling the provider" % provider)
                store.save_settings(settings)
                for provider in PROVIDERS:
                    if settings[provider]["enabled"] == "1" and settings[provider]["verify_tls"] == "0":
                        audit.write(
                            "provider_tls_verification_disabled",
                            level="WARNING",
                            provider=provider,
                        )
                store.set_replay_window(settings["general"]["replay_window_hours"])
                if data.get("complete_setup"):
                    store.complete_setup()
                    store.reload_app()
                return self._response(200, {"ok": True})
            if method == "POST" and action == "add_key":
                provider = data.get("provider", "")
                secret = str(data.get("secret", "")).strip()
                label = str(data.get("label", ""))[:80]
                if provider not in PROVIDERS or not secret or len(secret) > 2048:
                    raise ValueError("Invalid API key")
                key_id = store.add_key(provider, secret, label)
                return self._response(201, {"ok": True, "key_id": key_id})
            if method in ("POST", "DELETE") and action == "delete_key":
                provider = data.get("provider", "")
                key_id = data.get("key_id", "")
                if provider not in PROVIDERS or not re.fullmatch(r"[a-z]+_[a-f0-9]{12}", key_id):
                    raise ValueError("Invalid API key reference")
                provider_settings = store.settings().get(provider, {})
                if provider_settings.get("enabled") == "1" and len(store.list_keys(provider)) <= 1:
                    raise ValueError("Disable %s before removing its last API key" % provider)
                store.delete_key(provider, key_id)
                return self._response(200, {"ok": True})
            if method == "POST" and action == "add_exclusion":
                ioc_type = data.get("ioc_type", "")
                match_type = str(data.get("match_type", "exact")).lower()
                if ioc_type not in TYPES:
                    raise ValueError("Invalid IOC type")
                if match_type not in MATCH_TYPES:
                    raise ValueError("Invalid exclusion match type")
                value = normalize_exclusion(ioc_type, data.get("ioc", ""), match_type)
                key = store.add_exclusion(
                    ioc_type, value, match_type, str(data.get("reason", ""))[:300], user
                )
                return self._response(201, {"ok": True, "key": key, "ioc": value, "match_type": match_type})
            if method in ("POST", "DELETE") and action == "delete_exclusion":
                key = str(data.get("key", ""))
                if not re.fullmatch(r"[a-f0-9]{64}", key):
                    raise ValueError("Invalid exclusion reference")
                store.kv_delete("exclusions", key)
                return self._response(200, {"ok": True})
            if method == "POST" and action == "clear_cache":
                store.clear_cache()
                return self._response(200, {"ok": True})
            if method == "POST" and action == "test_email":
                general = store.settings().get("general", {})
                recipients = str(general.get("email_to", "")).strip()
                if not recipients or not valid_email_list(recipients):
                    raise ValueError("Configure a valid email recipient and save settings first")
                subject = "[TEST] " + str(general.get("email_subject", "DV IOC Enrichment"))[:190]
                try:
                    store.send_email(
                        recipients,
                        subject,
                        "DV IOC Enrichment email delivery test. Splunk SMTP and configured recipients are working.",
                        fields={
                            "Application": "DV IOC Enrichment",
                            "Status": "SMTP DELIVERY TEST SUCCESSFUL",
                            "Generated At": datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                            "Recipients": recipients,
                        },
                    )
                    audit.write("email_test_sent")
                except Exception as exc:
                    audit.write("email_test_failed", level="ERROR", error=str(exc))
                    raise
                return self._response(200, {"ok": True})
            if method == "POST" and action == "test_provider":
                provider = str(data.get("provider", ""))
                if provider not in PROVIDERS:
                    raise ValueError("Invalid provider")
                outcome = EnrichmentEngine(store).test_provider(provider)
                audit.write(
                    "provider_test_succeeded", provider=provider, verdict=outcome.get("verdict"),
                    confidence=outcome.get("confidence"), malicious_count=outcome.get("malicious"),
                    suspicious_count=outcome.get("suspicious"),
                )
                return self._response(200, {"ok": True, "result": outcome})
            return self._response(404, {"ok": False, "error": "Unknown action"})
        except ValueError as exc:
            return self._response(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            return self._response(500, {"ok": False, "error": str(exc)})

    @staticmethod
    def _require_edit(store):
        capabilities = store.capabilities()
        if EDIT_CAPABILITY not in capabilities and "admin_all_objects" not in capabilities:
            raise ValueError("User is not authorized to edit DV IOC Enrichment settings")

    @staticmethod
    def _bootstrap(store, setup=False):
        warnings = []

        def load(name, callback, fallback):
            try:
                return callback()
            except Exception as exc:
                warnings.append({"component": name, "error": str(exc)})
                return fallback

        settings = load("settings", store.settings, {})
        keys = load("api_keys", store.list_keys, [])
        if setup:
            return {
                "ok": True,
                "settings": settings,
                "keys": [{name: item.get(name) for name in SAFE_KEY_FIELDS} for item in keys],
                "exclusions": [],
                "stats": {},
                "warnings": warnings,
            }
        exclusions = load("exclusions", lambda: store.kv_list("exclusions"), [])
        stats = load("stats", store.stats, {
            "cache_count": 0, "exclusion_count": len(exclusions), "provider_state": [],
            "pending_count": 0, "failed_count": 0, "last_success_at": 0,
        })
        return {
            "ok": True,
            "settings": settings,
            "keys": [{name: item.get(name) for name in SAFE_KEY_FIELDS} for item in keys],
            "exclusions": sorted(exclusions, key=lambda item: item.get("created_at", 0), reverse=True),
            "stats": stats,
            "warnings": warnings,
        }

    @staticmethod
    def _activity(store):
        search = " | ".join([
            'search index=_internal source="*/dv_ioc_intelligence.log"',
            'spath input=_raw path=event output=log_event',
            'spath input=_raw path=event_id output=log_event_id',
            'spath input=_raw path=ioc output=log_ioc',
            'spath input=_raw path=ioc_type output=log_ioc_type',
            'spath input=_raw path=provider output=log_provider',
            'spath input=_raw path=verdict output=log_verdict',
            'spath input=_raw path=confidence output=log_confidence',
            'spath input=_raw path=confidence_threshold output=log_confidence_threshold',
            'spath input=_raw path=malicious_count output=log_malicious_count',
            'spath input=_raw path=malicious_threshold output=log_malicious_threshold',
            'spath input=_raw path=suspicious_count output=log_suspicious_count',
            'spath input=_raw path=suspicious_threshold output=log_suspicious_threshold',
            'spath input=_raw path=match_count output=log_match_count',
            'spath input=_raw path=match_threshold output=log_match_threshold',
            'spath input=_raw path=event_count output=log_event_count',
            'spath input=_raw path=misp_event_ids output=log_misp_event_ids',
            'spath input=_raw path=latest_timestamp output=log_latest_timestamp',
            'spath input=_raw path=harmless_count output=log_harmless_count',
            'spath input=_raw path=undetected_count output=log_undetected_count',
            'spath input=_raw path=reports output=log_reports',
            'spath input=_raw path=last_reported_at output=log_last_reported_at',
            'spath input=_raw path=pulse_count output=log_pulse_count',
            'spath input=_raw path=pulse_threshold output=log_pulse_threshold',
            'spath input=_raw path=reputation output=log_reputation',
            'spath input=_raw path=latest_pulse_at output=log_latest_pulse_at',
            'spath input=_raw path=pulse_ids output=log_pulse_ids',
            'spath input=_raw path=pulse_names output=log_pulse_names',
            'spath input=_raw path=field output=log_field',
            'spath input=_raw path=status output=log_status',
            'spath input=_raw path=lookup_source output=log_source',
            'spath input=_raw path=stage output=log_stage',
            'search log_event="ioc_enrichment_result" OR log_event="ioc_enrichment_error"',
            'sort 0 - _time',
            'dedup log_event_id log_provider log_ioc',
            'eval log_verdict=if(log_event="ioc_enrichment_error","unknown",log_verdict)',
            'eventstats dc(eval(if(log_verdict="malicious",log_ioc,null()))) AS malicious_ioc_count',
            'eval score=case(log_event="ioc_enrichment_error","-",log_provider="abuseipdb",log_confidence."%",log_provider="virustotal","M: ".log_malicious_count." / S: ".log_suspicious_count,log_provider="misp","Matches: ".log_match_count." / Events: ".log_event_count,log_provider="otx","Pulses: ".log_pulse_count." / Rep: ".log_reputation,true(),"-")',
            'eval threshold=case(log_event="ioc_enrichment_error","-",log_provider="abuseipdb",log_confidence_threshold."%",log_provider="virustotal","M: ".log_malicious_threshold." / S: ".log_suspicious_threshold,log_provider="misp",log_match_threshold,log_provider="otx",log_pulse_threshold,true(),"-")',
            'eval result_status=if(log_event="ioc_enrichment_error",coalesce(log_stage,"error"),coalesce(log_status,"enriched"))',
            'eval log_source=if(log_event="ioc_enrichment_error","provider error",coalesce(log_source,"api"))',
            'eval display_time=strftime(_time,"%Y-%m-%d %H:%M:%S")',
            'head 50',
            'table display_time log_event_id log_ioc log_ioc_type log_provider score threshold log_verdict result_status log_source log_field log_confidence log_confidence_threshold log_reports log_last_reported_at log_malicious_count log_malicious_threshold log_suspicious_count log_suspicious_threshold log_harmless_count log_undetected_count log_match_count log_match_threshold log_event_count log_misp_event_ids log_latest_timestamp log_pulse_count log_pulse_threshold log_reputation log_latest_pulse_at log_pulse_ids log_pulse_names log_stage malicious_ioc_count',
        ])
        results = store.search_oneshot(
            search,
            earliest_time="-24h",
            latest_time="now",
            enable_lookups=False,
            ignore_lookup_errors=True,
        )
        count = results[0].get("malicious_ioc_count", 0) if results else 0
        return {"ok": True, "results": results, "malicious_ioc_count": count}

    @staticmethod
    def _health(store):
        checks = []

        def add(check_id, name, category, status, detail, metadata=None):
            checks.append({
                "id": check_id,
                "name": name,
                "category": category,
                "status": status,
                "detail": str(detail),
                "metadata": metadata or {},
            })

        settings = {}
        try:
            settings = store.settings()
            add("configuration", "Application configuration", "Configuration", "healthy", "Configuration stanzas are readable.")
        except Exception as exc:
            add("configuration", "Application configuration", "Configuration", "failed", str(exc))

        general = settings.get("general", {})
        if settings:
            if _truthy(general.get("enabled", "1")):
                add("automation", "Automatic enrichment", "Configuration", "healthy", "Automation is enabled.")
            else:
                add("automation", "Automatic enrichment", "Configuration", "warning", "Automation is disabled in Settings.")

            if _truthy(general.get("email_enabled")):
                recipients = str(general.get("email_to", "")).strip()
                if recipients and valid_email_list(recipients):
                    add("email", "Email notification", "Configuration", "healthy", "Email notification is enabled and recipients are valid.")
                else:
                    add("email", "Email notification", "Configuration", "failed", "Email is enabled but no valid recipient is configured.")
            else:
                add("email", "Email notification", "Configuration", "healthy", "Optional email notification is disabled.")

        keys = []
        keys_loaded = False
        try:
            keys = store.list_keys()
            keys_loaded = True
        except Exception as exc:
            add("credentials", "Encrypted credentials", "Providers", "failed", str(exc))

        provider_states = []
        try:
            provider_states = store.kv_list("provider_state", fields="_key,provider,exhausted,next_retry_at", limit=20)
        except Exception:
            provider_states = []

        if settings and keys_loaded:
            now = time.time()
            for provider, label in (("virustotal", "VirusTotal"), ("abuseipdb", "AbuseIPDB"), ("misp", "MISP"), ("otx", "AlienVault OTX")):
                provider_settings = settings.get(provider, {})
                provider_keys = [item for item in keys if item.get("provider") == provider]
                if not _truthy(provider_settings.get("enabled")):
                    add("provider_" + provider, label, "Providers", "healthy", "Provider is intentionally disabled.", {"key_count": len(provider_keys)})
                    continue
                if not provider_keys:
                    add("provider_" + provider, label, "Providers", "failed", "Provider is enabled but no API key is configured.", {"key_count": 0})
                    continue
                state = next((item for item in provider_states if item.get("provider") == provider), {})
                blocked = [item for item in provider_keys if float(item.get("blocked_until", 0) or 0) > now]
                if _truthy(state.get("exhausted")) or len(blocked) == len(provider_keys):
                    retry_at = float(state.get("next_retry_at", 0) or 0)
                    detail = "All configured keys are temporarily unavailable."
                    if retry_at > now:
                        detail += " Next retry is scheduled after %s." % datetime.datetime.fromtimestamp(retry_at).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
                    add("provider_" + provider, label, "Providers", "warning", detail, {"key_count": len(provider_keys), "blocked_key_count": len(blocked)})
                elif not _truthy(provider_settings.get("verify_tls", "1")):
                    add(
                        "provider_" + provider,
                        label,
                        "Providers",
                        "warning",
                        "%d encrypted key(s) configured and available, but TLS certificate verification is disabled." % len(provider_keys),
                        {"key_count": len(provider_keys), "blocked_key_count": len(blocked), "verify_tls": False},
                    )
                else:
                    add(
                        "provider_" + provider,
                        label,
                        "Providers",
                        "healthy",
                        "%d encrypted key(s) configured; %d currently available." % (len(provider_keys), len(provider_keys) - len(blocked)),
                        {"key_count": len(provider_keys), "blocked_key_count": len(blocked)},
                    )

        collection_labels = (
            ("cache", "Enrichment cache"),
            ("exclusions", "IOC exclusions"),
            ("key_state", "API key quota state"),
            ("provider_state", "Provider quota state"),
            ("processed", "Processed event checkpoints"),
            ("locks", "Concurrency leases"),
            ("app_state", "Application state"),
        )
        unavailable_collections = []
        for collection, label in collection_labels:
            try:
                store.kv_list(collection, fields="_key", limit=1)
            except Exception as exc:
                unavailable_collections.append("%s: %s" % (label, exc))
        if unavailable_collections:
            add("kv_store", "KV Store collections", "Storage", "failed", "; ".join(unavailable_collections))
        else:
            add("kv_store", "KV Store collections", "Storage", "healthy", "All seven application collections are readable.")

        try:
            saved_search = store.saved_search_status("DV IOC Enrichment - Process New Notables")
            if saved_search.get("enabled"):
                add(
                    "scheduled_search",
                    "Notable processing search",
                    "Splunk",
                    "healthy",
                    "Scheduled with cron %s and lookback %s." % (
                        saved_search.get("cron_schedule") or "not reported",
                        saved_search.get("earliest_time") or "not reported",
                    ),
                    saved_search,
                )
            else:
                add("scheduled_search", "Notable processing search", "Splunk", "failed", "The scheduled search is disabled.", saved_search)
        except Exception as exc:
            add("scheduled_search", "Notable processing search", "Splunk", "failed", str(exc))

        try:
            notable_results = store.search_oneshot(
                "search index=notable (event_id=* OR source_event_id=*) | stats count AS event_count latest(_time) AS latest_time",
                earliest_time="-24h",
                latest_time="now",
                enable_lookups=False,
                ignore_lookup_errors=True,
            )
            notable_count = int((notable_results[0] if notable_results else {}).get("event_count", 0) or 0)
            if notable_count:
                add("notable_index", "Notable event access", "Splunk", "healthy", "%d notable event(s) are readable from the last 24 hours." % notable_count, {"event_count": notable_count})
            else:
                add("notable_index", "Notable event access", "Splunk", "warning", "The notable index is readable, but no events were found in the last 24 hours.", {"event_count": 0})
        except Exception as exc:
            add("notable_index", "Notable event access", "Splunk", "failed", str(exc))

        try:
            log_results = store.search_oneshot(
                'search index=_internal source="*/dv_ioc_intelligence.log" | stats count AS log_count latest(_time) AS latest_time',
                earliest_time="-24h",
                latest_time="now",
                enable_lookups=False,
                ignore_lookup_errors=True,
            )
            log_count = int((log_results[0] if log_results else {}).get("log_count", 0) or 0)
            if log_count:
                add("internal_log", "Operational log ingestion", "Splunk", "healthy", "%d app log event(s) are searchable from the last 24 hours." % log_count, {"event_count": log_count})
            else:
                add("internal_log", "Operational log ingestion", "Splunk", "warning", "No app log events were found in the last 24 hours.", {"event_count": 0})
        except Exception as exc:
            add("internal_log", "Operational log ingestion", "Splunk", "failed", str(exc))

        summary = {
            "healthy": len([item for item in checks if item["status"] == "healthy"]),
            "warning": len([item for item in checks if item["status"] == "warning"]),
            "failed": len([item for item in checks if item["status"] == "failed"]),
            "total": len(checks),
        }
        summary["status"] = "failed" if summary["failed"] else ("warning" if summary["warning"] else "healthy")
        return {"ok": True, "generated_at": time.time(), "summary": summary, "checks": checks}

    @staticmethod
    def _validate_settings(settings):
        general_in = settings.get("general", {})
        vt_in = settings.get("virustotal", {})
        abuse_in = settings.get("abuseipdb", {})
        misp_in = settings.get("misp", {})
        otx_in = settings.get("otx", {})
        severity = general_in.get("severity_when_malicious", "high")
        if severity not in SEVERITIES:
            raise ValueError("Invalid severity")
        email_to = str(general_in.get("email_to", "")).strip()
        email_enabled = str(general_in.get("email_enabled", "0")).lower() in ("1", "true", "on")
        if not valid_email_list(email_to):
            raise ValueError("Invalid email recipient list")
        if email_enabled and not email_to:
            raise ValueError("Email recipients are required when email notifications are enabled")

        general = {
            "enabled": "1" if str(general_in.get("enabled", "1")).lower() in ("1", "true", "on") else "0",
            "skip_private_ips": "1" if str(general_in.get("skip_private_ips", "1")).lower() in ("1", "true", "on") else "0",
            "severity_when_malicious": severity,
            "email_enabled": "1" if email_enabled else "0",
            "email_to": email_to,
            "email_subject": str(general_in.get("email_subject", "Malicious IOC detected by DV IOC Enrichment"))[:200],
            "proxy_url": validate_proxy_url(general_in.get("proxy_url", "")),
            "processed_retention_days": _int(
                general_in.get("processed_retention_days", 90), "Processed event retention", 1, 3650
            ),
            "max_iocs_per_event": _int(
                general_in.get("max_iocs_per_event", 20), "Maximum IOCs per event", 1, 100
            ),
            "replay_window_hours": _int(
                general_in.get("replay_window_hours", 24), "Retry window", 1, 720
            ),
        }
        ca_bundle = str(general_in.get("ca_bundle", "")).strip()
        expanded_ca = ca_bundle
        if expanded_ca.startswith("$SPLUNK_HOME"):
            expanded_ca = os.environ.get("SPLUNK_HOME", "") + expanded_ca[len("$SPLUNK_HOME"):]
        if ca_bundle and (
            len(ca_bundle) > 500
            or not os.path.isabs(expanded_ca)
            or not os.path.isfile(expanded_ca)
            or not os.access(expanded_ca, os.R_OK)
        ):
            raise ValueError("CA bundle must be an existing absolute file readable by Splunk")
        general["ca_bundle"] = ca_bundle
        for field_name in ("ip_fields", "domain_fields", "url_fields", "hash_fields"):
            value = str(general_in.get(field_name, ""))
            if not re.fullmatch(r"[A-Za-z0-9_,.:-]*", value):
                raise ValueError("Invalid field mapping")
            general[field_name] = value

        vt = {
            "enabled": "1" if str(vt_in.get("enabled", "0")).lower() in ("1", "true", "on") else "0",
            "verify_tls": "1" if _truthy(vt_in.get("verify_tls", "1")) else "0",
            "api_url": validate_api_url(vt_in.get("api_url", "https://www.virustotal.com/api/v3")),
            "malicious_threshold": _int(vt_in.get("malicious_threshold", 3), "VirusTotal malicious threshold", 1, 100),
            "suspicious_threshold": _int(vt_in.get("suspicious_threshold", 2), "VirusTotal suspicious threshold", 1, 100),
            "cache_ttl_hours": _int(vt_in.get("cache_ttl_hours", 24), "VirusTotal cache TTL", 1, 8760),
            "minute_limit": _int(vt_in.get("minute_limit", 4), "VirusTotal minute limit", 1, 4),
            "daily_limit": _int(vt_in.get("daily_limit", 500), "VirusTotal daily limit", 1, 100000000),
        }
        abuse_api_url = validate_api_url(abuse_in.get("api_url", "https://api.abuseipdb.com/api/v2"))
        if abuse_api_url.lower().endswith("/check"):
            abuse_api_url = abuse_api_url[:-6].rstrip("/")
        abuse = {
            "enabled": "1" if str(abuse_in.get("enabled", "0")).lower() in ("1", "true", "on") else "0",
            "verify_tls": "1" if _truthy(abuse_in.get("verify_tls", "1")) else "0",
            "api_url": abuse_api_url,
            "confidence_threshold": _int(abuse_in.get("confidence_threshold", 40), "AbuseIPDB confidence threshold", 1, 100),
            "cache_ttl_hours": _int(abuse_in.get("cache_ttl_hours", 24), "AbuseIPDB cache TTL", 1, 8760),
            "daily_limit": _int(abuse_in.get("daily_limit", 1000), "AbuseIPDB daily limit", 1, 100000000),
            "max_age_days": _int(abuse_in.get("max_age_days", 90), "AbuseIPDB max age", 1, 365),
        }
        misp = {
            "enabled": "1" if str(misp_in.get("enabled", "0")).lower() in ("1", "true", "on") else "0",
            "verify_tls": "1" if _truthy(misp_in.get("verify_tls", "1")) else "0",
            "api_url": validate_api_url(misp_in.get("api_url", "https://misp.example.com")),
            "match_threshold": _int(misp_in.get("match_threshold", 1), "MISP match threshold", 1, 100),
            "cache_ttl_hours": _int(misp_in.get("cache_ttl_hours", 24), "MISP cache TTL", 1, 8760),
            "minute_limit": _int(misp_in.get("minute_limit", 60), "MISP minute limit", 1, 1000000),
            "daily_limit": _int(misp_in.get("daily_limit", 10000), "MISP daily limit", 1, 100000000),
            "published_only": "1" if _truthy(misp_in.get("published_only", "1")) else "0",
            "to_ids_only": "1" if _truthy(misp_in.get("to_ids_only", "1")) else "0",
            "enforce_warninglist": "1" if _truthy(misp_in.get("enforce_warninglist", "1")) else "0",
        }
        otx = {
            "enabled": "1" if str(otx_in.get("enabled", "0")).lower() in ("1", "true", "on") else "0",
            "verify_tls": "1" if _truthy(otx_in.get("verify_tls", "1")) else "0",
            "api_url": validate_api_url(otx_in.get("api_url", "https://otx.alienvault.com/api/v1")),
            "pulse_threshold": _int(otx_in.get("pulse_threshold", 1), "OTX pulse threshold", 1, 1000),
            "max_pulse_age_days": _int(otx_in.get("max_pulse_age_days", 365), "OTX maximum pulse age", 1, 3650),
            "cache_ttl_hours": _int(otx_in.get("cache_ttl_hours", 24), "OTX cache TTL", 1, 8760),
            "minute_limit": _int(otx_in.get("minute_limit", 60), "OTX minute limit", 1, 1000000),
            "daily_limit": _int(otx_in.get("daily_limit", 10000), "OTX daily limit", 1, 100000000),
        }
        return {"general": general, "virustotal": vt, "abuseipdb": abuse, "misp": misp, "otx": otx}

    @staticmethod
    def _response(status, payload):
        return {"payload": payload, "status": status}

    def handleStream(self, handle, in_string):
        raise NotImplementedError()

    def done(self):
        pass
