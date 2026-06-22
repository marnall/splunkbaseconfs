#!/usr/bin/env python3

import sys
import os
import json
import ssl
import gzip
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timezone

# vh_http is the single source of truth for outbound HTTP — proxy config,
# explicit env-var-proxy disablement on splunkd loopback, etc.  Imported
# from the same bin/ directory.
import vh_http

try:
    import pytz as _pytz
    _PYTZ_AVAILABLE = True
except ImportError:
    _PYTZ_AVAILABLE = False


class StopIngestionError(Exception):
    """Raised when a user-initiated stop request is detected during ingestion.
    Not a RuntimeError subclass so it propagates cleanly through the generic
    exception handlers in run_ingestion without being re-wrapped.
    """


APP_NAME = "vh_enrichment_app"
DATA_COLLECTION = "vh_enrichment_kv_collection_app"
CONTROL_COLLECTION = "vh_enrichment_control_state"
CONTROL_KEY = "state"
SPLUNKD_BASE = "https://127.0.0.1:8089"
BATCH_SIZE = 250
BATCH_SLEEP = 0.1  # seconds between batch inserts to reduce KV Store pressure


def normalize_record(record):
    try:
        ip = str(record.get("ip", "")).strip()
        if not ip:
            return None

        raw_tags = record.get("risk_tags", "[]")
        try:
            risk_tags = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
            if not isinstance(risk_tags, list):
                risk_tags = []
        except Exception:
            risk_tags = []

        scanner_name = str(record.get("scanner_name", ""))
        if scanner_name == "null":
            scanner_name = ""

        return {
            "_key": ip,
            "ip": ip,
            "risk_score": str(record.get("risk_score", "")),
            "risk_tags": json.dumps(risk_tags),
            "is_scanner": str(record.get("is_scanner", "")),
            "scanner_name": scanner_name,
            "is_anonymizer": str(record.get("is_anonymizer", "")),
            "is_commercial_vpn": str(record.get("is_commercial_vpn", "")),
            "is_residential_proxy": str(record.get("is_residential_proxy", "")),
            "longitude": str(record.get("longitude", "")),
            "latitude": str(record.get("latitude", "")),
        }

    except Exception:
        return None


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def print_scheme():
    # The modular input takes no per-stanza args.  The canonical API base
    # URL is resolved at runtime from the KV settings doc via
    # vh_http.load_api_base; ingestion semantics are always full-refresh.
    print("""<scheme>
  <title>VH Enrichment Loader</title>
  <description>Loads enrichment data into KV Store via the VisionHeight API.</description>
  <use_external_validation>true</use_external_validation>
  <use_single_instance>false</use_single_instance>
  <streaming_mode>simple</streaming_mode>

  <endpoint>
    <args>
    </args>
  </endpoint>
</scheme>""")


def get_text(parent, path, default=""):
    node = parent.find(path)
    return node.text if node is not None and node.text is not None else default


def validate_arguments():
    # No args to validate; Splunk still invokes the script with --validate-arguments
    # at enable time, so the entry point must exist and exit cleanly.
    sys.stdin.read()


def splunkd_request(session_key, method, path, data=None, retries=10, retry_sleep=3, timeout=60):
    url = f"{SPLUNKD_BASE}{path}"
    headers = {
        "Authorization": f"Splunk {session_key}",
    }

    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    context = ssl.create_default_context()
    context.load_verify_locations(cafile=os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem"))
    context.check_hostname = False
    last_error = None

    for attempt in range(retries):
        try:
            request = urllib.request.Request(
                url=url,
                headers=headers,
                data=payload,
                method=method,
            )

            # splunkd loopback — explicitly bypass any configured corporate
            # proxy AND any HTTP_PROXY/HTTPS_PROXY env vars by passing
            # proxy_cfg=None to vh_http.urlopen.
            with vh_http.urlopen(request, context=context, timeout=timeout, proxy_cfg=None) as response:
                return response.read().decode("utf-8")

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            last_error = e

            print(
                f"Splunk REST error: method={method}, path={path}, "
                f"status={e.code}, body={error_body}",
                file=sys.stderr,
            )

            if e.code == 503 and attempt < retries - 1:
                print(
                    f"splunkd not ready yet (503), retry {attempt + 1}/{retries}",
                    file=sys.stderr,
                )
                time.sleep(retry_sleep)
                continue

            raise

        except Exception as e:
            last_error = e
            print(
                f"Splunk REST request failed: method={method}, path={path}, error={e}",
                file=sys.stderr,
            )

            if attempt < retries - 1:
                time.sleep(retry_sleep)
                continue

            raise

    raise last_error


def get_api_key(session_key):
    # Wildcard owner (-) finds the credential regardless of who created it.
    # output_mode=json is required — storage/passwords returns Atom XML by default.
    path = (
        f"/servicesNS/-/{APP_NAME}/storage/passwords/"
        f"{APP_NAME}:api_key:?output_mode=json"
    )
    try:
        body = splunkd_request(session_key, "GET", path, retries=1, retry_sleep=0)
        data = json.loads(body)
        entries = data.get("entry", [])
        if not entries:
            print(f"get_api_key: response had no entries for path {path}", file=sys.stderr)
            return None
        return entries[0]["content"].get("clear_password")
    except urllib.error.HTTPError as e:
        print(f"get_api_key: HTTP {e.code} — credential not found at path {path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"get_api_key: unexpected error: {e}", file=sys.stderr)
        return None


def batch_save_records(session_key, records):
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{DATA_COLLECTION}/batch_save"
    )
    splunkd_request(session_key, "POST", path, records, retries=3, retry_sleep=5)


def get_control_state(session_key):
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{CONTROL_COLLECTION}/{CONTROL_KEY}"
    )
    try:
        body = splunkd_request(session_key, "GET", path)
        return json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"_key": CONTROL_KEY, "run_requested": False}
        raise


def save_control_state(session_key, state_doc):
    state_doc["_key"] = CONTROL_KEY
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{CONTROL_COLLECTION}/batch_save"
    )
    splunkd_request(session_key, "POST", path, [state_doc], retries=3, retry_sleep=5)


def _merge_and_save(session_key, updates, retries=3, retry_sleep=1):
    """Re-read live KV state, apply only `updates` fields, and write back.

    Only the keys present in `updates` are changed.  All other fields —
    run_requested, schedule_enabled, scheduled_time_hhmm,
    last_scheduled_run_date, etc. — are preserved from the document
    currently in KV Store.  This prevents a long-running ingestion process
    from clobbering concurrent writes made by the scheduler or a Run Now
    request.
    """
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{CONTROL_COLLECTION}/{CONTROL_KEY}"
    )
    try:
        body = splunkd_request(session_key, "GET", path, retries=retries, retry_sleep=retry_sleep)
        live = json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            live = {"_key": CONTROL_KEY}
        else:
            raise
    live.update(updates)
    save_control_state(session_key, live)
    return live


def _check_scheduled_run(state):
    """Return today's date string (in the schedule's timezone) if a scheduled run should
    trigger now, else None.

    Fires when schedule_enabled=True, the current time in schedule_tz matches
    scheduled_time_hhmm, and the run hasn't already been triggered today
    (last_scheduled_run_date != today in that timezone).

    schedule_tz must be a valid IANA timezone name (e.g. "America/New_York").
    Defaults to "UTC" for backward compatibility with schedules saved before
    timezone support was added.
    """
    if not state.get("schedule_enabled"):
        return None
    scheduled_hhmm = state.get("scheduled_time_hhmm", "").strip()
    if not scheduled_hhmm:
        return None

    tz_name = state.get("schedule_tz", "UTC").strip() or "UTC"

    if _PYTZ_AVAILABLE:
        try:
            tz = _pytz.timezone(tz_name)
        except Exception:
            print(
                f"_check_scheduled_run: unknown timezone {tz_name!r}, falling back to UTC",
                file=sys.stderr,
            )
            tz = _pytz.utc
            tz_name = "UTC"
        now_local = datetime.now(timezone.utc).astimezone(tz)
    else:
        # pytz not available — behave as UTC so the scheduler still works
        print(
            "_check_scheduled_run: pytz not available, using UTC",
            file=sys.stderr,
        )
        now_local = datetime.now(timezone.utc)

    if now_local.strftime("%H:%M") != scheduled_hhmm:
        return None

    # Dedup key is the LOCAL calendar date so "once per day" means once per
    # local day (avoids double-fire or missed-fire around midnight).
    today = now_local.strftime("%Y-%m-%d")
    if state.get("last_scheduled_run_date", "") == today:
        return None
    return today


def parse_input_definition():
    xml_data = sys.stdin.read()
    root = ET.fromstring(xml_data)

    session_key = ""
    metadata_session = root.find(".//session_key")
    if metadata_session is not None and metadata_session.text:
        session_key = metadata_session.text

    inputs = []
    for stanza in root.findall(".//configuration/stanza"):
        name = stanza.get("name", "")
        params = {}
        for param in stanza.findall("./param"):
            params[param.get("name")] = param.text or ""
        inputs.append((name, params))

    return session_key, inputs


def run_ingestion(session_key, api_base,
                  progress_callback=None, stop_check_fn=None):
    """Execute a single ingestion pass. Raises RuntimeError on failure.

    `api_base` is a vh_http.ApiBase resolved by the caller from the
    Setup-UI value (KV settings doc).  This function never reads any
    other source for the base URL, so changing the Setup field is
    enough to redirect the next ingestion cycle.

    Upsert-only: records are written via KV batch_save keyed on _key=ip,
    so existing rows are updated in place and new rows are added.  This
    function never deletes records — emptying the collection is reserved
    for the user-initiated "Clear KV Store" action in the dashboard.
    Stale ips that drop out of the upstream snapshot therefore linger in
    KV until the user explicitly clears.

    progress_callback(phase, records_inserted) is called at key points
    so the caller can write observable state to KV Store without coupling
    this module to the control state schema.

    stop_check_fn() is called once before the insert phase and again
    before each batch.  If it returns True, StopIngestionError is raised
    and any records already inserted are preserved.
    """
    def _progress(phase, records_inserted=None):
        if progress_callback:
            try:
                progress_callback(phase=phase, records_inserted=records_inserted)
            except StopIngestionError:
                raise  # let stop signals propagate out of progress callbacks
            except Exception:
                pass  # never let ordinary progress reporting kill the ingestion

    api_key = get_api_key(session_key)
    if not api_key:
        raise RuntimeError("API key not found in storage/passwords. Please complete setup.")

    if not api_base or not api_base.url:
        raise RuntimeError(
            "API base URL is not configured. Please complete setup."
        )

    # Outbound TLS trust:
    #   * Stock default = secure public-CA verification — works for Splunk
    #     Cloud and for on-prem hosts with direct public-internet access.
    #   * When the operator has configured a `ca_bundle_path` in Setup
    #     (vh_enrichment_app_settings.ca_bundle_path), that PEM bundle is
    #     ADDED to the default trust store so TLS-inspection proxies and
    #     private internal CAs are trusted too.  Verification is never
    #     disabled and hostname checks stay on — see vh_http.build_outbound_ssl_context.
    _tls_loader_ctx = ssl.create_default_context()
    _tls_loader_ctx.load_verify_locations(cafile=os.path.join(
        os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem"))
    _tls_loader_ctx.check_hostname = False
    tls_settings = vh_http.load_outbound_tls_settings(
        session_key=session_key,
        splunkd_base=SPLUNKD_BASE,
        ssl_context=_tls_loader_ctx,
        app_name=APP_NAME,
        logger=lambda m: print("vh ingestion: " + m, file=sys.stderr),
    )
    print("vh ingestion: " + tls_settings.debug_repr(), file=sys.stderr)
    context = vh_http.build_outbound_ssl_context(
        tls_settings,
        logger=lambda m: print("vh ingestion: " + m, file=sys.stderr),
    )

    # urllib's `timeout=` is a SOCKET-LEVEL read timeout: it triggers when
    # no bytes flow for that many seconds, not when the overall transfer
    # is slow.  Without it, a half-open TCP socket (slow corporate proxy
    # stalling mid-stream, dead NAT translation, broken HTTPS-inspection
    # appliance) hangs this process forever, holding the "running" slot
    # until manual intervention.
    #   PRESIGNED_URL_TIMEOUT — small JSON GET, must complete promptly
    #   DOWNLOAD_TIMEOUT      — applies to each read of the gzip stream;
    #                          120s of zero bytes flowing = real stall
    PRESIGNED_URL_TIMEOUT_SEC = 30
    DOWNLOAD_TIMEOUT_SEC      = 120

    # Load outbound-proxy config once per ingestion run.  Uses its own
    # splunkd-CA-pinned SSL context (matches splunkd_request).  Any failure
    # degrades to "no proxy" with a logged warning — see vh_http.load_proxy_config.
    proxy_ctx = ssl.create_default_context()
    proxy_ctx.load_verify_locations(cafile=os.path.join(
        os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem"))
    proxy_ctx.check_hostname = False
    proxy_cfg = vh_http.load_proxy_config(
        session_key=session_key,
        splunkd_base=SPLUNKD_BASE,
        ssl_context=proxy_ctx,
        app_name=APP_NAME,
    )
    print("vh ingestion: " + proxy_cfg.debug_repr(), file=sys.stderr)

    # 1. Get presigned URL
    _progress("fetching_url")
    try:
        request = urllib.request.Request(
            url=f"{api_base.url}/splunk/enrichment/file",
            headers={"x-api-key": api_key},
            method="GET",
        )
        with vh_http.urlopen(request, context=context, proxy_cfg=proxy_cfg,
                             timeout=PRESIGNED_URL_TIMEOUT_SEC) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            presigned_url = data.get("url") or data.get("presignedUrl")

            if not presigned_url:
                raise RuntimeError("No presigned URL returned")

            print("Got presigned URL successfully", file=sys.stderr)

    except RuntimeError:
        raise
    except Exception as e:
        # Map SSL handshake failures to an actionable message that names
        # the API host (not a secret) and points the operator at the CA
        # bundle setting.  Hostname comes from the Request URL so the
        # UI's run_error reads cleanly without echoing the full URL.
        _api_host = urllib.parse.urlsplit(api_base.url).hostname
        tls_msg = vh_http.classify_outbound_tls_error(e, host=_api_host)
        if tls_msg is not None:
            raise RuntimeError(tls_msg) from e
        raise RuntimeError(f"API call failed: {e}") from e

    # 2. Download + parse + normalize into memory first
    _progress("downloading")
    prepared_batches = []
    current_batch = []
    total_prepared = 0

    try:
        download_req = urllib.request.Request(presigned_url, method="GET")
        with vh_http.urlopen(download_req, context=context, proxy_cfg=proxy_cfg,
                             timeout=DOWNLOAD_TIMEOUT_SEC) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for line in gz:
                    try:
                        record = json.loads(line.decode("utf-8"))
                        normalized = normalize_record(record)

                        if not normalized:
                            continue

                        current_batch.append(normalized)

                        if len(current_batch) >= BATCH_SIZE:
                            prepared_batches.append(current_batch)
                            total_prepared += len(current_batch)
                            current_batch = []

                    except Exception:
                        continue

        if current_batch:
            prepared_batches.append(current_batch)
            total_prepared += len(current_batch)

        print(f"Finished download/parse. Total prepared={total_prepared}", file=sys.stderr)

    except StopIngestionError:
        raise
    except RuntimeError:
        raise
    except Exception as e:
        # TLS failure on the S3 hop is the other place enterprise CA
        # misconfiguration shows up.  Only the host portion of the
        # presigned URL is surfaced — never the signed query string.
        _s3_host = urllib.parse.urlsplit(presigned_url).hostname
        tls_msg = vh_http.classify_outbound_tls_error(e, host=_s3_host)
        if tls_msg is not None:
            raise RuntimeError(tls_msg) from e
        raise RuntimeError(f"Download/processing failed: {e}") from e

    # Last clean-abort point before any KV writes — Stop here leaves the
    # collection exactly as it was when this run started.
    if stop_check_fn and stop_check_fn():
        raise StopIngestionError("Stop requested before KV insert")

    # 3. Upsert prepared batches — progress updated after every batch.
    # batch_save is idempotent on _key=ip, so existing records are updated
    # in place and new records are appended.  Nothing is deleted here.
    _progress("inserting", records_inserted=0)
    total_inserted = 0
    total_batches  = len(prepared_batches)

    try:
        for batch_index, batch in enumerate(prepared_batches):
            # Check for stop request before each batch so the user gets a
            # timely response.  stop_check_fn is throttled internally.
            if stop_check_fn and stop_check_fn():
                raise StopIngestionError(
                    f"Stop requested at batch {batch_index + 1}/{total_batches} "
                    f"after {total_inserted} records"
                )
            if batch_index == 0 or (batch_index + 1) % 500 == 0 or batch_index + 1 == total_batches:
                print(
                    f"Inserting batch {batch_index + 1}/{total_batches}, "
                    f"total_inserted={total_inserted}",
                    file=sys.stderr,
                )
            batch_save_records(session_key, batch)
            total_inserted += len(batch)
            _progress("inserting", records_inserted=total_inserted)
            time.sleep(BATCH_SLEEP)

        print(f"Finished ingestion. Total records inserted={total_inserted}", file=sys.stderr)

    except StopIngestionError:
        raise  # propagate without re-wrapping as RuntimeError
    except Exception as e:
        raise RuntimeError(
            f"KV Store insert failed at batch {batch_index + 1}/{total_batches} "
            f"after {total_inserted} records: {e}"
        ) from e

    return total_inserted


def run():
    session_key, inputs = parse_input_definition()

    if not session_key:
        print("No session_key found in modular input definition", file=sys.stderr)
        return

    try:
        state = get_control_state(session_key)
    except Exception as e:
        print(f"Failed to read control state: {e}", file=sys.stderr)
        return

    # No KV "ingestion_enabled" gate — the single source of truth for whether
    # the modular input runs is `disabled` in [vh_enrichment_modinput://default]
    # in inputs.conf, controlled by the Setup UI "Enable Ingestion" checkbox.
    # splunkd does not spawn this script at all when disabled=1, so any KV-side
    # gate would either be redundant (always-true) or unreachable.

    # Auto-trigger if the configured daily schedule time (in schedule_tz) matches right now.
    # Only runs once per day (guarded by last_scheduled_run_date) and only when
    # no manual run is already queued, so Run Now is never disrupted.
    if not state.get("run_requested"):
        trigger_date = _check_scheduled_run(state)
        if trigger_date is not None:
            _tz_label = state.get("schedule_tz", "UTC") or "UTC"
            if state.get("run_status") == "running":
                # Ingestion is already active — the in-progress run counts as
                # today's daily refresh.  Mark the day as handled (so the check
                # does not re-fire every minute for the rest of the hour) but do
                # NOT set run_requested=True, which would queue a redundant run.
                # Use _merge_and_save so we only touch last_scheduled_run_date
                # and do not disturb any other concurrent state.
                print(
                    f"Scheduled time {state.get('scheduled_time_hhmm')} {_tz_label} reached "
                    f"but ingestion already running; marking today ({trigger_date}) as handled.",
                    file=sys.stderr,
                )
                try:
                    _merge_and_save(session_key, {"last_scheduled_run_date": trigger_date})
                except Exception as e:
                    print(f"Failed to save scheduled-skip state: {e}", file=sys.stderr)
                return

            print(
                f"Scheduled run triggered at {state.get('scheduled_time_hhmm')} {_tz_label}",
                file=sys.stderr,
            )
            state["run_requested"] = True  # keep local dict in sync for line 561 check
            try:
                _merge_and_save(session_key, {
                    "run_requested": True,
                    "last_scheduled_run_date": trigger_date,
                })
            except Exception as e:
                print(f"Failed to save scheduled trigger state: {e}", file=sys.stderr)

    run_requested = state.get("run_requested") in (True, "true", "True")

    if not run_requested:
        print("No action needed (run_requested=false).", file=sys.stderr)
        return

    # Guard: another modular input invocation may already be running.
    if state.get("run_status") == "running":
        print("Ingestion already running in another invocation; skipping.", file=sys.stderr)
        return

    # Resolve the canonical API base URL via the shared loader so the
    # modular input and the `vhipmetadata` search command go through one
    # source of truth (KV settings doc, written by the Setup UI).
    _api_ctx = ssl.create_default_context()
    _api_ctx.load_verify_locations(cafile=os.path.join(
        os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem"))
    _api_ctx.check_hostname = False
    api_base = vh_http.load_api_base(
        session_key=session_key,
        splunkd_base=SPLUNKD_BASE,
        ssl_context=_api_ctx,
        app_name=APP_NAME,
    )
    print("vh ingestion: " + api_base.debug_repr(), file=sys.stderr)
    if not api_base.url:
        print("API base URL not configured; cannot run ingestion.",
              file=sys.stderr)
        return

    print("Starting ingestion", file=sys.stderr)

    _started_at = utc_now()
    state["run_requested"] = False       # keep local dict in sync for progress_callback
    state["run_status"] = "running"
    state["run_started_at"] = _started_at
    state["run_completed_at"] = ""
    state["run_error"] = ""
    state["current_phase"] = "starting"
    state["records_inserted_so_far"] = ""
    state["last_heartbeat_at"] = _started_at

    try:
        _merge_and_save(session_key, {
            "run_requested":           False,
            "run_status":              "running",
            "run_started_at":          _started_at,
            "run_completed_at":        "",
            "run_error":               "",
            "current_phase":           "starting",
            "records_inserted_so_far": "",
            "last_heartbeat_at":       _started_at,
        })
    except Exception as e:
        print(f"Failed to save initial running state: {e}", file=sys.stderr)

    _last_progress_save = [time.time()]

    def progress_callback(phase=None, records_inserted=None):
        now = time.time()
        phase_changed = phase is not None and phase != state.get("current_phase")
        if not phase_changed and (now - _last_progress_save[0]) < 10:
            return
        try:
            if phase is not None:
                state["current_phase"] = phase
            if records_inserted is not None:
                state["records_inserted_so_far"] = str(records_inserted)
            state["last_heartbeat_at"] = utc_now()
            # Write only the fields this callback owns.  Re-reading live KV state
            # before writing ensures run_requested and schedule fields are
            # never overwritten by the stale local dict.
            live = _merge_and_save(session_key, {
                "run_status": "running",
                "current_phase": state["current_phase"],
                "records_inserted_so_far": state.get("records_inserted_so_far", ""),
                "last_heartbeat_at": state["last_heartbeat_at"],
            })
            _last_progress_save[0] = now
            # If a stop was written to KV while we were inserting, signal it.
            if live and live.get("stop_requested") in (True, "true", "True"):
                raise StopIngestionError("Stop requested detected in progress callback")
        except StopIngestionError:
            raise
        except Exception as cb_err:
            print(f"progress_callback error: {cb_err}", file=sys.stderr)

    # Throttled KV poll for stop_requested — reads KV at most once every 5 s.
    # Between reads it returns _stop_detected[0] (set True on first detection).
    _stop_detected = [False]
    _last_stop_check_ts = [0.0]
    _STOP_CHECK_INTERVAL = 5

    def _should_stop():
        if _stop_detected[0]:
            return True
        now = time.time()
        if now - _last_stop_check_ts[0] < _STOP_CHECK_INTERVAL:
            return False
        _last_stop_check_ts[0] = now
        try:
            live = get_control_state(session_key)
            if live.get("stop_requested") in (True, "true", "True"):
                _stop_detected[0] = True
                return True
        except Exception:
            pass
        return False

    try:
        total_inserted = run_ingestion(
            session_key,
            api_base,
            progress_callback=progress_callback,
            stop_check_fn=_should_stop,
        )
        _completed_at = utc_now()
        _merge_and_save(session_key, {
            "run_status": "done",
            "run_completed_at": _completed_at,
            "run_error": "",
            "current_phase": "done",
            "records_inserted_so_far": str(total_inserted),
            "last_record_count": str(total_inserted),
            "last_heartbeat_at": _completed_at,
        })
        print(f"Ingestion completed. total_inserted={total_inserted}", file=sys.stderr)

    except StopIngestionError:
        _stopped_so_far = state.get("records_inserted_so_far", "0") or "0"
        print(
            f"Ingestion stopped by user request. records_inserted_so_far={_stopped_so_far}",
            file=sys.stderr,
        )
        _stopped_at = utc_now()
        _stop_fields = {
            "run_status": "stopped",
            "run_completed_at": _stopped_at,
            "run_error": "",
            "current_phase": "stopped",
            "records_inserted_so_far": _stopped_so_far,
            "last_heartbeat_at": _stopped_at,
            "stop_requested": False,
        }
        for attempt in range(5):
            try:
                _merge_and_save(session_key, _stop_fields, retries=2, retry_sleep=2)
                print(f"Stopped state written (attempt {attempt + 1})", file=sys.stderr)
                break
            except Exception as write_err:
                print(
                    f"Could not write stopped state (attempt {attempt + 1}/5): {write_err}",
                    file=sys.stderr,
                )
                if attempt < 4:
                    time.sleep(5)

    except Exception as e:
        print(f"Ingestion failed: {e}", file=sys.stderr)
        _failed_at = utc_now()
        _failure_fields = {
            "run_status": "failed",
            "run_completed_at": _failed_at,
            "run_error": str(e),
            "last_heartbeat_at": _failed_at,
        }
        for attempt in range(5):
            try:
                _merge_and_save(session_key, _failure_fields, retries=2, retry_sleep=2)
                print(f"Failure state written (attempt {attempt + 1})", file=sys.stderr)
                break
            except Exception as write_err:
                print(
                    f"Could not write failure state (attempt {attempt + 1}/5): {write_err}",
                    file=sys.stderr,
                )
                if attempt < 4:
                    time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scheme":
        print_scheme()
    elif len(sys.argv) > 1 and sys.argv[1] == "--validate-arguments":
        validate_arguments()
    else:
        run()
