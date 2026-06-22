# encoding = utf-8

import json
import time
import datetime


def validate_input(helper, definition):
    """
    Validate input parameters only.
    """
    p = definition.parameters

    if not p.get("guardium_url"):
        raise ValueError("guardium_url is required")

    if not p.get("guardium_url").startswith(("http://", "https://")):
        raise ValueError("guardium_url must start with http:// or https://")

    if not p.get("report_name"):
        raise ValueError("report_name is required")

    if not p.get("initial_from"):
        raise ValueError("initial_from is required (YYYY-MM-DD HH:MM:SS)")

    try:
        datetime.datetime.strptime(p.get("initial_from"), "%Y-%m-%d %H:%M:%S")
    except Exception:
        raise ValueError("initial_from must be in format YYYY-MM-DD HH:MM:SS")


def collect_events(helper, ew):
    """
    FINAL Guardium collector.
    - Local time only
    - Explicit source naming
    - Per-input checkpoint
    - Retry + backoff
    - AOB-safe
    """

    # -------- GLOBAL SETTINGS --------
    auth_token = helper.get_global_setting("auth_token")
    if not auth_token:
        helper.log_error("auth_token not configured in TA setup")
        return

    verify_ssl = str(helper.get_global_setting("verify_ssl") or "0").lower() in (
        "1", "true", "yes", "on"
    )

    # -------- INPUT ARGS --------
    guardium_url = helper.get_arg("guardium_url").strip()
    report_name = helper.get_arg("report_name").strip()
    initial_from = helper.get_arg("initial_from").strip()
    fetch_size = int(helper.get_arg("fetch_size") or "5000")
    reset_checkpoint = str(helper.get_arg("reset_checkpoint") or "false").lower()
    source_suffix = helper.get_arg("source_suffix").strip()

    # -------- SOURCE --------
    input_type = helper.get_input_type()
    source = f"{input_type}://{source_suffix}"
    logp = f"[source={source}]"

    # -------- CHECKPOINT --------
    checkpoint_key = f"guardium::{source_suffix}::checkpoint"

    if reset_checkpoint == "true":
        helper.log_warning(f"{logp} Reset checkpoint requested")
        helper.delete_check_point(checkpoint_key)
        checkpoint = None
    else:
        checkpoint = helper.get_check_point(checkpoint_key)

    if checkpoint and checkpoint.get("last_time"):
        query_from = checkpoint["last_time"]
        helper.log_info(f"{logp} Resuming from checkpoint {query_from}")
    else:
        query_from = initial_from
        helper.log_info(f"{logp} First run, using initial_from={query_from}")

    now = datetime.datetime.now()
    query_to = now.strftime("%Y-%m-%d %H:%M:%S")

    helper.log_info(f"{logp} Querying Guardium from {query_from} to {query_to}")

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    def parse_ts(ts):
        return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    max_ts = None
    page_index_from = 1
    retries = 3

    while True:
        payload = {
            "reportName": report_name,
            "indexFrom": str(page_index_from),
            "fetchSize": fetch_size,
            "reportParameter": {
                "QUERY_FROM_DATE": query_from,
                "QUERY_TO_DATE": query_to,
                "ServerIP": "%",
                "DBUserName": "%",
                "OSUser": "%",
                "DBName": "%",
                "DBUser": "%",
                "SHOW_ALIASES": "true",
                "REMOTE_SOURCE": "%",
                "SourceApp": "%",
                "FullSQL": "%"
            }
        }

        attempt = 0
        response = None

        while attempt < retries:
            try:
                response = helper.send_http_request(
                    url=guardium_url,
                    method="POST",
                    headers=headers,
                    payload=json.dumps(payload),
                    verify=verify_ssl,
                    timeout=180,
                )
                response.raise_for_status()
                break
            except Exception as e:
                attempt += 1
                helper.log_warning(
                    f"{logp} Guardium request failed (attempt {attempt}/{retries}): {e}"
                )
                time.sleep(5 * attempt)

        if not response:
            helper.log_error(f"{logp} Guardium API unreachable after retries")
            break

        try:
            rows = response.json()
        except Exception as e:
            helper.log_error(f"{logp} JSON parse failed: {e}")
            break

        if isinstance(rows, dict):
            helper.log_info(f"{logp} No data returned")
            break

        if not rows:
            break

        last_ts = parse_ts(query_from)

        for row in rows:
            ts_str = row.get("Timestamp")
            if not ts_str:
                continue

            try:
                row_ts = parse_ts(ts_str)
            except Exception:
                continue

            if row_ts <= last_ts:
                continue

            if not max_ts or row_ts > max_ts:
                max_ts = row_ts

            event = helper.new_event(
                data=json.dumps(row, ensure_ascii=False),
                time=time.mktime(row_ts.timetuple()),
                index=helper.get_output_index(),
                source=source,
                sourcetype=helper.get_sourcetype(),
            )
            ew.write_event(event)

        if len(rows) < fetch_size:
            break

        page_index_from += fetch_size

    if max_ts is None:
        max_ts = datetime.datetime.strptime(query_to, "%Y-%m-%d %H:%M:%S")

    helper.save_check_point(
        checkpoint_key,
        {"last_time": max_ts.strftime("%Y-%m-%d %H:%M:%S")}
    )

    helper.log_info(f"{logp} Checkpoint updated to {max_ts}")