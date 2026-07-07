# encoding = utf-8

"""
Cyera Collector -- Centralized orchestrator input that collects from all
enabled Cyera API endpoints using a single JWT and shared rate limit tracker.

This eliminates cross-process rate limit competition that occurs when running
multiple individual inputs simultaneously.
"""

import datetime
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from cyera_utils import (
    validate_input,
    get_jwt,
    get_data,
    get_checkpoint,
    save_checkpoint,
    DEFAULT_DAYS_TO_LOOK_BACK,
)
from input_module_cyera_audit import get_audit_logs


# Thread-safe rate limit tracker shared across concurrent endpoint collections
class RateLimitTracker:
    """Thread-safe wrapper around rate_state for use with ThreadPoolExecutor."""
    
    def __init__(self, count_limit=300, window_seconds=300):
        self._lock = threading.Lock()
        self._count = 0
        self._start_time = time.time()
        self.count_limit = count_limit
        self.window_seconds = window_seconds
    
    def get_state(self):
        """Return a rate_state dict that references this tracker's shared counters."""
        with self._lock:
            return {"count": self._count, "start_time": self._start_time}
    
    def update_state(self, rate_state):
        """Update the shared counters from a rate_state dict returned by handle_request."""
        with self._lock:
            self._count = rate_state["count"]
            self._start_time = rate_state["start_time"]


def _is_checkbox_enabled(value):
    """Properly check Splunk checkbox values (string '0' is truthy in Python)."""
    if value is None:
        return False
    return str(value).strip() == '1' or value is True


def _get_account_credentials(helper):
    """Extract account credentials from input configuration."""
    cyera_account = helper.get_arg('cyera_account') or helper.get_arg('account')
    
    if cyera_account:
        if isinstance(cyera_account, dict):
            helper.log_debug("Using input-specific account (dict)")
            return (
                cyera_account.get('name'),
                cyera_account.get('username'),
                cyera_account.get('password'),
            )
        # Could be a legacy global account identifier
        helper.log_debug(f"Using global account identifier: {cyera_account}")
        try:
            account_details = helper.get_user_credential_by_id(cyera_account)
            if not account_details:
                helper.log_error(f"Account '{cyera_account}' not found in credential store.")
                return None, None, None
            return (
                cyera_account,
                account_details.get('username'),
                account_details.get('password'),
            )
        except Exception as e:
            helper.log_error(f"Error retrieving account details: {str(e)}")
            return None, None, None

    helper.log_error(
        "Neither input-specific nor global account is set. "
        "Please configure the account in the input parameters or add-on setup."
    )
    return None, None, None


def _get_days_to_look_back(helper):
    """Retrieve and validate the days_to_look_back global setting."""
    days_to_look_back = helper.get_global_setting('days_to_look_back')
    helper.log_debug(f"Retrieved days_to_look_back from global settings: {days_to_look_back}")
    
    if not days_to_look_back:
        helper.log_warning(
            "The 'days_to_look_back' setting is not set in global additional parameters. "
            "Using default value of 365 days."
        )
        return DEFAULT_DAYS_TO_LOOK_BACK
    
    try:
        return int(days_to_look_back)
    except ValueError:
        helper.log_error(
            f"Invalid value for 'days_to_look_back': {days_to_look_back}. "
            "Using default value of 365 days."
        )
        return DEFAULT_DAYS_TO_LOOK_BACK


def _compute_created_date(helper, endpoint, days_to_look_back, retrieve_all_data=False):
    """Compute the created_date filter for an endpoint based on checkpoints."""
    date_format = "%Y-%m-%dT%H:%M:%S.000Z" if endpoint == "events" else "%Y-%m-%d"
    
    if retrieve_all_data:
        helper.log_info(f"[{endpoint}] Retrieve all data mode: no date filter")
        return None
    
    last_run_timestamp = get_checkpoint(helper, f"{endpoint}_last_run")
    original_days_to_look_back = get_checkpoint(helper, f"{endpoint}_original_days_to_look_back")
    
    if not last_run_timestamp:
        created_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).strftime(date_format)
        helper.log_info(f"[{endpoint}] No last run timestamp found. Using created_date: {created_date}")
        save_checkpoint(helper, f"{endpoint}_original_days_to_look_back", days_to_look_back)
        return created_date
    
    if original_days_to_look_back != days_to_look_back:
        created_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).strftime(date_format)
        helper.log_info(f"[{endpoint}] Days to look back changed. Using created_date: {created_date}")
        save_checkpoint(helper, f"{endpoint}_original_days_to_look_back", days_to_look_back)
        return created_date
    
    try:
        if endpoint == "events":
            created_date = last_run_timestamp
        else:
            created_date = datetime.datetime.fromisoformat(last_run_timestamp).strftime(date_format)
        helper.log_info(f"[{endpoint}] Using last run timestamp as created_date: {created_date}")
        return created_date
    except ValueError:
        helper.log_error(f"[{endpoint}] Invalid last run timestamp format: {last_run_timestamp}. Using days_to_look_back.")
        created_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).strftime(date_format)
        return created_date


def _get_endpoint_interval(helper, endpoint_name):
    """
    Get the per-endpoint interval. Returns seconds as int, or None to use base interval.
    """
    raw = helper.get_arg(f'interval_{endpoint_name}')
    if raw is None or str(raw).strip() == '':
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        helper.log_warning(f"[{endpoint_name}] Invalid interval value '{raw}', using base interval.")
        return None


def _get_endpoint_index(helper, endpoint_name):
    """
    Get the per-endpoint index override. Returns index name, or None to use base index.
    """
    raw = helper.get_arg(f'index_{endpoint_name}')
    if raw is None or str(raw).strip() == '':
        return None
    return str(raw).strip()


def _should_run_endpoint(helper, endpoint_name, endpoint_interval):
    """
    Check whether an endpoint should run based on its per-endpoint interval
    and last checkpoint timestamp. Returns True if enough time has elapsed.
    If no per-endpoint interval is set, always returns True (use base interval).
    """
    if endpoint_interval is None:
        return True
    
    # Use the appropriate checkpoint key
    checkpoint_key = "audit_logs_last_run" if endpoint_name == "audit" else f"{endpoint_name}_last_run"
    last_run = get_checkpoint(helper, checkpoint_key)
    
    if not last_run:
        helper.log_info(f"[{endpoint_name}] No previous run found, will collect.")
        return True
    
    try:
        last_run_dt = datetime.datetime.fromisoformat(last_run)
        elapsed = (datetime.datetime.now() - last_run_dt).total_seconds()
        if elapsed >= endpoint_interval:
            helper.log_info(f"[{endpoint_name}] {elapsed:.0f}s since last run (interval: {endpoint_interval}s), will collect.")
            return True
        else:
            helper.log_info(f"[{endpoint_name}] {elapsed:.0f}s since last run (interval: {endpoint_interval}s), skipping.")
            return False
    except (ValueError, TypeError) as e:
        helper.log_warning(f"[{endpoint_name}] Error parsing last run timestamp: {e}. Will collect.")
        return True


def _collect_standard_endpoint(helper, endpoint, sourcetype, jwt, days_to_look_back, rate_state, retrieve_all_data=False):
    """
    Collect data from a standard Cyera API endpoint (events, issues, datastores, classifications).
    Returns (data_list, sourcetype, index_override) tuple for main-thread event writing.
    """
    helper.log_info(f"[{endpoint}] Starting collection")
    
    created_date = _compute_created_date(helper, endpoint, days_to_look_back, retrieve_all_data)
    data = get_data(helper, endpoint, jwt, limit=None, created_date=created_date, rate_state=rate_state)
    
    index_override = _get_endpoint_index(helper, endpoint)
    
    if data:
        new_checkpoint = datetime.datetime.now().isoformat()
        save_checkpoint(helper, f"{endpoint}_last_run", new_checkpoint)
        helper.log_info(f"[{endpoint}] Collected {len(data)} items. Checkpoint saved: {new_checkpoint}")
    else:
        helper.log_info(f"[{endpoint}] No data retrieved, checkpoint not updated.")
    
    return data, sourcetype, index_override


def _collect_audit_endpoint(helper, jwt, days_to_look_back):
    """
    Collect data from the audit logs endpoint (uses a different API).
    Returns (data_list, sourcetype, index_override) tuple for main-thread event writing.
    """
    helper.log_info("[audit] Starting collection")
    
    last_run_timestamp = get_checkpoint(helper, "audit_logs_last_run")
    
    if not last_run_timestamp:
        created_from = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).isoformat()
    else:
        created_from = last_run_timestamp
    
    helper.log_info(f"[audit] Fetching audit logs from: {created_from}")
    
    data = get_audit_logs(helper, jwt, limit=200, created_from=created_from)
    
    index_override = _get_endpoint_index(helper, "audit")
    
    if data:
        new_checkpoint = datetime.datetime.now().isoformat()
        save_checkpoint(helper, "audit_logs_last_run", new_checkpoint)
        helper.log_info(f"[audit] Collected {len(data)} items. Checkpoint saved: {new_checkpoint}")
    else:
        helper.log_info("[audit] No audit log data retrieved, checkpoint not updated.")
    
    return data, "cyera:audit", index_override


def _write_events(helper, ew, data, sourcetype, index_override=None):
    """
    Write events to Splunk, optionally overriding the index per-endpoint.
    Falls back to the input's default index when no override is set.
    """
    if not data:
        return 0
    
    helper.log_info(f"Processing {len(data)} items for sourcetype: {sourcetype}" +
                    (f" (index: {index_override})" if index_override else ""))
    
    target_index = index_override or helper.get_output_index()
    count = 0
    
    for i, item in enumerate(data):
        try:
            event_data = json.dumps(item)
            event = helper.new_event(data=event_data, index=target_index, sourcetype=sourcetype)
            ew.write_event(event)
            count += 1
            
            if (i + 1) % 100 == 0:
                helper.log_info(f"Processed {i + 1}/{len(data)} items for {sourcetype}")
        except Exception as e:
            helper.log_error(f"Error processing item {i} for {sourcetype}: {str(e)}")
            helper.log_debug(f"Problematic item: {json.dumps(item)}")
    
    helper.log_info(f"Completed processing {count} items for {sourcetype}")
    return count


def collect_events(helper, ew):
    """
    Orchestrator: collect all enabled Cyera endpoints with a single JWT,
    shared rate limit tracking, and controlled parallelism (max_workers=2).
    
    Each endpoint can have its own collection interval and target index,
    independent of the base input interval.
    """
    helper.session_key = helper.context_meta['session_key']
    
    # --- Authenticate once ---
    account_name, client_id, secret = _get_account_credentials(helper)
    if not account_name or not client_id or not secret:
        helper.log_error("Account name, client ID, or secret is missing. Aborting collection.")
        return
    
    helper.log_debug(f"Successfully retrieved account details. Account name: {account_name}")
    
    jwt = get_jwt(helper, client_id, secret)
    if not jwt:
        helper.log_error("Failed to authenticate with API. Aborting collection.")
        return
    
    helper.log_info("Successfully authenticated. Starting orchestrated collection.")
    
    # --- Global settings ---
    days_to_look_back = _get_days_to_look_back(helper)
    retrieve_all_datastores = _is_checkbox_enabled(helper.get_arg('retrieve_all_datastores'))
    
    # --- Build list of enabled endpoints that are due for collection ---
    tasks = []
    
    # Shared rate state for centralized tracking across all endpoints
    rate_state = {"count": 0, "start_time": time.time()}
    
    # Endpoint definitions: (name, enabled_flag, task_factory)
    endpoint_defs = [
        ("events", 'enable_events', lambda: _collect_standard_endpoint(
            helper, "events", "cyera:events", jwt, days_to_look_back, rate_state
        )),
        ("issues", 'enable_issues', lambda: _collect_standard_endpoint(
            helper, "issues", "cyera:issues", jwt, days_to_look_back, rate_state
        )),
        ("datastores", 'enable_datastores', lambda: _collect_standard_endpoint(
            helper, "datastores", "cyera:datastores", jwt, days_to_look_back, rate_state,
            retrieve_all_data=retrieve_all_datastores
        )),
        ("classifications", 'enable_classifications', lambda: _collect_standard_endpoint(
            helper, "classifications", "cyera:classifications", jwt, days_to_look_back, rate_state
        )),
        ("audit", 'enable_audit', lambda: _collect_audit_endpoint(
            helper, jwt, days_to_look_back
        )),
    ]
    for ep_name, enable_flag, task_fn in endpoint_defs:
        if not _is_checkbox_enabled(helper.get_arg(enable_flag)):
            continue
        
        ep_interval = _get_endpoint_interval(helper, ep_name)
        if not _should_run_endpoint(helper, ep_name, ep_interval):
            continue
        
        tasks.append((ep_name, task_fn))
    
    if not tasks:
        helper.log_info("No endpoints are due for collection this cycle.")
        return
    
    helper.log_info(f"Collecting from {len(tasks)} endpoints this cycle: {[t[0] for t in tasks]}")
    
    # --- Collect with controlled parallelism (max 2 concurrent) ---
    # I/O threads collect data; event writing happens on the main thread afterward.
    results = []
    
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(task_fn): endpoint_name
            for endpoint_name, task_fn in tasks
        }
        
        for future in as_completed(futures):
            endpoint_name = futures[future]
            try:
                data, sourcetype, index_override = future.result()
                if data:
                    results.append((data, sourcetype, index_override))
                    helper.log_info(f"[{endpoint_name}] Collection complete: {len(data)} items")
                else:
                    helper.log_info(f"[{endpoint_name}] Collection complete: no data")
            except Exception as e:
                helper.log_error(f"[{endpoint_name}] Collection failed: {str(e)}")
    
    # --- Write all events from main thread (EventWriter is not thread-safe) ---
    total_events = 0
    for data, sourcetype, index_override in results:
        total_events += _write_events(helper, ew, data, sourcetype, index_override)
    
    helper.log_info(f"Orchestrated collection complete. Total events written: {total_events}")


def main(helper, ew):
    """Main entry point for the module."""
    collect_events(helper, ew)
