# encoding = utf-8

import os
import sys
import time
import datetime
import json
import urllib.parse
import re
from elasticsearch import Elasticsearch
import ipaddress
import warnings

# ── Constants (v1.2.3) ───────────────────────────────────────────────────
_APP_NAME = "TA-ensign_elasticsearch_add-on--Modular_input"
MIN_INTERVAL_SECONDS = 15

# SECURITY FIX (VULN-03): Only suppress specific known warnings,
# not ALL warnings. Global suppression hides security-critical alerts
# like InsecureRequestWarning.
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

# ==========================================
# COLLECTION STATE MANAGER
# ==========================================
# Manages the dedicated "collection" directory that sits at the TA root level,
# next to the bin/ folder. This is the most practical location for Heavy
# Forwarder (HF) deployments — always writeable, co-located with the add-on,
# and survives Splunk restarts (though NOT TA reinstalls/upgrades, zip/unzip
# overwrites do not touch this folder because it is not part of the package).
#
# Directory structure created on first deploy:
#
#   $SPLUNK_HOME/etc/apps/TA-ensign_elasticsearch.../
#   ├── bin/
#   │   └── input_module_elasticsearch_source.py
#   └── collection/                          ← created here on first run
#       └── <stanza_name>/                   ← one sub-folder per input stanza
#           ├── scroll_state.json            ← active scroll_id (crash recovery)
#           ├── last_bookmark.txt            ← timestamp of last successful run
#           └── seen_ids.txt                 ← per-stanza rolling dedup guard

class CollectionStateManager:
    """
    Manages a dedicated persistent directory for all checkpoint data
    specific to one modular input stanza. Provides three protection layers:

      1. Timestamp bookmark  → defines gte boundary for the next query
      2. Scroll ID recovery  → resumes paging after a crash mid-scroll
      3. Seen-IDs dedup guard → blocks duplicates in overlapping time windows
                                (one seen_ids.txt FILE PER STANZA)
    """

    def __init__(self, stanza_name, helper):
        self.helper      = helper
        self.stanza_name = stanza_name

        # ── Resolve the "collection" directory next to bin/ ──────────────────
        # __file__ → .../TA-.../bin/input_module_elasticsearch_source.py
        # bin_dir  → .../TA-.../bin/
        # ta_root  → .../TA-.../
        bin_dir = os.path.dirname(os.path.abspath(__file__))
        ta_root = os.path.dirname(bin_dir)

        # collection/<stanza_name>/  ← per-stanza sub-directory
        self.collection_dir = os.path.join(ta_root, "collection", stanza_name)
        self._ensure_collection_dir()

        # ── File paths (all scoped to this stanza's sub-folder) ──────────────
        self.scroll_state_file = os.path.join(self.collection_dir, "scroll_state.json")
        self.bookmark_file     = os.path.join(self.collection_dir, "last_bookmark.txt")
        # seen_ids.txt is per-stanza by design (lives inside <stanza_name>/)
        self.seen_ids_file     = os.path.join(self.collection_dir, "seen_ids.txt")

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _ensure_collection_dir(self):
        """Create the stanza's collection sub-directory on first deploy."""
        if not os.path.exists(self.collection_dir):
            try:
                os.makedirs(self.collection_dir, exist_ok=True)
                self.helper.log_info(
                    f"[+] Collection directory initialized for stanza "
                    f"'{self.stanza_name}': {self.collection_dir}"
                )
            except OSError as e:
                self.helper.log_error(
                    f"[-] Failed to create collection directory "
                    f"'{self.collection_dir}': {str(e)}"
                )
                raise

    # ── Bookmark (Timestamp) ──────────────────────────────────────────────────

    def load_bookmark(self, fallback):
        """
        Read the last-run timestamp bookmark for this stanza.
        Returns fallback (e.g. 'now-1h') if no bookmark file exists yet.
        """
        if os.path.exists(self.bookmark_file):
            try:
                with open(self.bookmark_file, "r") as f:
                    val = f.read().strip()
                    if val:
                        return val
            except OSError:
                pass
        return fallback

    def save_bookmark(self, timestamp_iso):
        """Persist the current run UTC timestamp as the next run's gte boundary."""
        try:
            with open(self.bookmark_file, "w") as f:
                f.write(timestamp_iso)
        except OSError as e:
            self.helper.log_error(f"[-] Failed to save bookmark: {str(e)}")

    # ── Scroll State (Crash Recovery) ─────────────────────────────────────────

    def save_scroll_state(self, scroll_id, query_bookmark):
        """
        Persist the active Elasticsearch scroll context.
        If Splunk kills the process mid-scroll the NEXT scheduled run will
        attempt to resume from this cursor rather than issuing a fresh search
        (which would re-ingest already-processed pages).
        """
        state = {
            "scroll_id":      scroll_id,
            "query_bookmark": query_bookmark,
            "saved_at":       datetime.datetime.utcnow().isoformat() + "Z"
        }
        try:
            with open(self.scroll_state_file, "w") as f:
                json.dump(state, f)
        except OSError as e:
            self.helper.log_error(f"[-] Failed to save scroll state: {str(e)}")

    def load_scroll_state(self):
        """
        Load a previously saved scroll state for this stanza.
        Returns None if no state file exists.
        """
        if not os.path.exists(self.scroll_state_file):
            return None
        try:
            with open(self.scroll_state_file, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def clear_scroll_state(self):
        """Remove the scroll state file after a clean, complete collection run."""
        if os.path.exists(self.scroll_state_file):
            try:
                os.remove(self.scroll_state_file)
            except OSError:
                pass

    # ── Seen-IDs Deduplication Guard (per-stanza) ─────────────────────────────
    # Prevents ingesting the same Elasticsearch document twice when the time
    # windows of consecutive runs overlap at boundary edges.
    # Each stanza has its OWN seen_ids.txt under its own collection sub-folder.
    # A rolling cap of MAX_SEEN_IDS entries bounds the file size.

    MAX_SEEN_IDS = 50_000

    def load_seen_ids(self):
        """Load this stanza's set of already-ingested document IDs."""
        if not os.path.exists(self.seen_ids_file):
            return set()
        try:
            with open(self.seen_ids_file, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except OSError:
            return set()

    def append_seen_ids(self, new_ids):
        """
        Append newly ingested doc IDs to this stanza's guard file.
        Prunes oldest entries when total exceeds MAX_SEEN_IDS.
        """
        if not new_ids:
            return
        try:
            existing = []
            if os.path.exists(self.seen_ids_file):
                with open(self.seen_ids_file, "r") as f:
                    existing = [line.strip() for line in f if line.strip()]

            combined = existing + list(new_ids)

            # Prune: keep only the latest MAX_SEEN_IDS entries
            if len(combined) > self.MAX_SEEN_IDS:
                combined = combined[-self.MAX_SEEN_IDS:]

            with open(self.seen_ids_file, "w") as f:
                f.write("\n".join(combined) + "\n")
        except OSError as e:
            self.helper.log_error(f"[-] Failed to update seen_ids guard: {str(e)}")


# ==========================================
# KVSTORE STATE MANAGER (v1.2.3)
# ==========================================
class KVStoreStateManager:
    """
    Checkpoint storage using Splunk KVStore collections.
    SHC-native: checkpoints are automatically replicated across SHC members.
    Uses REST API to read/write to es_checkpoint_store and es_seen_ids_store.
    """

    MAX_SEEN_IDS = 50_000

    def __init__(self, stanza_name, helper):
        self.helper = helper
        self.stanza_name = stanza_name
        self._server_uri = helper.context_meta.get('server_uri')
        self._session_key = helper.context_meta.get('session_key')
        self._headers = {
            "Authorization": f"Splunk {self._session_key}",
            "Content-Type": "application/json",
        }
        self._ckpt_endpoint = (
            f"{self._server_uri}/servicesNS/nobody/{_APP_NAME}"
            f"/storage/collections/data/es_checkpoint_store"
        )
        self._seen_endpoint = (
            f"{self._server_uri}/servicesNS/nobody/{_APP_NAME}"
            f"/storage/collections/data/es_seen_ids_store"
        )

    def _kvstore_get(self, endpoint, key):
        """GET a single record from KVStore by _key."""
        uri = f"{endpoint}/{urllib.parse.quote(key)}?output_mode=json"
        try:
            resp = self.helper.send_http_request(
                uri, "GET", parameters=None, payload=None,
                headers=self._headers, cookies=None,
                verify=True, cert=None, timeout=15, use_proxy=False
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def _kvstore_upsert(self, endpoint, key, data):
        """Insert or update a record in KVStore."""
        data["_key"] = key
        uri = f"{endpoint}/{urllib.parse.quote(key)}?output_mode=json"
        try:
            resp = self.helper.send_http_request(
                uri, "POST", parameters=None,
                payload=json.dumps(data),
                headers=self._headers, cookies=None,
                verify=True, cert=None, timeout=15, use_proxy=False
            )
            if resp.status_code in (200, 201, 409):
                return True
        except Exception as e:
            self.helper.log_error(f"[-] KVStore upsert failed: {str(e)}")
        return False

    def load_bookmark(self, fallback):
        record = self._kvstore_get(self._ckpt_endpoint, self.stanza_name)
        if record and record.get("last_bookmark"):
            return record["last_bookmark"]
        return fallback

    def get_bookmark_timestamp(self):
        """Return the updated_at timestamp for comparison."""
        record = self._kvstore_get(self._ckpt_endpoint, self.stanza_name)
        if record and record.get("updated_at"):
            return record["updated_at"]
        return None

    def save_bookmark(self, timestamp_iso):
        self._kvstore_upsert(self._ckpt_endpoint, self.stanza_name, {
            "stanza_name": self.stanza_name,
            "last_bookmark": timestamp_iso,
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        })

    def save_scroll_state(self, scroll_id, query_bookmark):
        state = json.dumps({
            "scroll_id": scroll_id,
            "query_bookmark": query_bookmark,
            "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
        })
        record = self._kvstore_get(self._ckpt_endpoint, self.stanza_name)
        data = {
            "stanza_name": self.stanza_name,
            "last_bookmark": record.get("last_bookmark", "") if record else "",
            "scroll_state": state,
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        self._kvstore_upsert(self._ckpt_endpoint, self.stanza_name, data)

    def load_scroll_state(self):
        record = self._kvstore_get(self._ckpt_endpoint, self.stanza_name)
        if record and record.get("scroll_state"):
            try:
                return json.loads(record["scroll_state"])
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def clear_scroll_state(self):
        record = self._kvstore_get(self._ckpt_endpoint, self.stanza_name)
        if record:
            data = {
                "stanza_name": self.stanza_name,
                "last_bookmark": record.get("last_bookmark", ""),
                "scroll_state": "",
                "updated_at": record.get("updated_at", ""),
            }
            self._kvstore_upsert(self._ckpt_endpoint, self.stanza_name, data)

    def load_seen_ids(self):
        record = self._kvstore_get(self._seen_endpoint, self.stanza_name)
        if record and record.get("seen_ids"):
            try:
                return set(json.loads(record["seen_ids"]))
            except (json.JSONDecodeError, TypeError):
                pass
        return set()

    def append_seen_ids(self, new_ids):
        if not new_ids:
            return
        existing = list(self.load_seen_ids())
        combined = existing + list(new_ids)
        if len(combined) > self.MAX_SEEN_IDS:
            combined = combined[-self.MAX_SEEN_IDS:]
        self._kvstore_upsert(self._seen_endpoint, self.stanza_name, {
            "stanza_name": self.stanza_name,
            "seen_ids": json.dumps(combined),
            "count": len(combined),
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        })


# ==========================================
# SMART FALLBACK MANAGER (v1.2.3)
# ==========================================
class SmartFallbackManager:
    """
    Wraps both file-based and KVStore state managers.
    On load_bookmark: reads BOTH backends, returns the most recent.
    On write operations: writes ONLY to the active backend.
    Seen IDs are NOT cross-referenced between backends.
    """

    def __init__(self, active_mode, file_mgr, kvstore_mgr, helper):
        self.active_mode = active_mode  # 'file' or 'kvstore'
        self.file_mgr = file_mgr
        self.kvstore_mgr = kvstore_mgr
        self.helper = helper
        self._active = kvstore_mgr if active_mode == "kvstore" else file_mgr

    def load_bookmark(self, fallback):
        """Smart Fallback: read BOTH backends, return the newest bookmark."""
        file_bookmark = self.file_mgr.load_bookmark(None)
        kv_bookmark = None
        try:
            kv_bookmark = self.kvstore_mgr.load_bookmark(None)
        except Exception:
            pass

        if file_bookmark and kv_bookmark:
            # Compare ISO timestamps — lexicographic comparison works for ISO 8601
            if kv_bookmark > file_bookmark:
                self.helper.log_info(
                    f"[*] Smart Fallback: KVStore bookmark ({kv_bookmark}) is newer "
                    f"than file bookmark ({file_bookmark}). Using KVStore."
                )
                return kv_bookmark
            else:
                self.helper.log_info(
                    f"[*] Smart Fallback: File bookmark ({file_bookmark}) is newer "
                    f"than or equal to KVStore ({kv_bookmark}). Using file."
                )
                return file_bookmark
        elif file_bookmark:
            return file_bookmark
        elif kv_bookmark:
            return kv_bookmark
        return fallback

    def save_bookmark(self, timestamp_iso):
        self._active.save_bookmark(timestamp_iso)

    def save_scroll_state(self, scroll_id, query_bookmark):
        self._active.save_scroll_state(scroll_id, query_bookmark)

    def load_scroll_state(self):
        return self._active.load_scroll_state()

    def clear_scroll_state(self):
        self._active.clear_scroll_state()

    def load_seen_ids(self):
        return self._active.load_seen_ids()

    def append_seen_ids(self, new_ids):
        self._active.append_seen_ids(new_ids)

    @property
    def collection_dir(self):
        """For logging compatibility — returns file manager's dir."""
        return self.file_mgr.collection_dir


# ==========================================
# CHECKPOINT SETTINGS READER (v1.2.3)
# ==========================================
def _read_checkpoint_setting(helper):
    """Read checkpoint_storage setting from settings REST endpoint."""
    try:
        uri = (
            f"{helper.context_meta.get('server_uri')}/servicesNS/nobody/"
            f"{_APP_NAME}/"
            f"TA_ensign_elasticsearch_add_on__Modular_input_settings/"
            f"checkpoint?output_mode=json"
        )
        headers = {
            "Authorization": f"Splunk {helper.context_meta.get('session_key')}"
        }
        resp = helper.send_http_request(
            uri, "GET", parameters=None, payload=None,
            headers=headers, cookies=None,
            verify=True, cert=None, timeout=15, use_proxy=False
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get('entry', [{}])[0].get('content', {})
            return content.get('checkpoint_storage', 'file').strip().lower()
    except Exception as e:
        helper.log_info(f"[!] Could not read checkpoint setting, defaulting to file: {str(e)}")
    return 'file'


def create_state_manager(helper, safe_stanza_name):
    """Factory: create the appropriate state manager based on settings."""
    mode = _read_checkpoint_setting(helper)
    file_mgr = CollectionStateManager(safe_stanza_name, helper)
    kvstore_mgr = KVStoreStateManager(safe_stanza_name, helper)

    helper.log_info(f"[*] Checkpoint storage mode: {mode}")
    return SmartFallbackManager(mode, file_mgr, kvstore_mgr, helper)


# ==========================================
# INPUT VALIDATION BEFORE SAVING
# ==========================================
def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""

    # ── NEW (v1.2.3): Minimum interval enforcement ───────────────────────
    interval_raw = definition.parameters.get('interval', None)
    if interval_raw is not None:
        try:
            interval_val = int(interval_raw)
            if interval_val < MIN_INTERVAL_SECONDS:
                raise ValueError(
                    f"[-] Interval Error: Minimum polling interval is "
                    f"{MIN_INTERVAL_SECONDS} seconds. Current value: "
                    f"{interval_val}s. Please update your inputs.conf "
                    f"to set interval >= {MIN_INTERVAL_SECONDS}."
                )
        except ValueError as ve:
            if "Interval Error" in str(ve):
                raise
            raise ValueError(
                f"[-] Interval must be a positive integer (seconds). "
                f"Got: '{interval_raw}'"
            )

    time_preset = definition.parameters.get('time_preset', None)
    if time_preset:
        preset_str = str(time_preset).strip()
        is_date_math_es  = re.match(r'^\d+[smhdwMy]$', preset_str)
        is_iso_timestamp = re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', preset_str)

        if not (is_date_math_es or is_iso_timestamp):
            err_msg = (
                f"[-] Save Failed! Invalid Fetch Range format.\n"
                f"Please use ES date math notation (e.g., '15m', '1h', '3d')\n"
                f"or a raw ISO 8601 timestamp (e.g., '2023-12-31T23:59:59Z')."
            )
            raise ValueError(err_msg)

    opt_enable_filter = definition.parameters.get('enable_filter', None)
    is_filter_enabled = str(opt_enable_filter).lower() in ["true", "1", "yes"]
    if is_filter_enabled:
        filter_key = definition.parameters.get('filter_key', None)
        filter_val = definition.parameters.get('filter_val', None)
        if not filter_key or not str(filter_key).strip():
            raise ValueError(
                "[-] Validation Error: 'Enable Custom Filter' is checked. "
                "The 'Filter Key' field is required and cannot be empty."
            )
        if not filter_val or not str(filter_val).strip():
            raise ValueError(
                "[-] Validation Error: 'Enable Custom Filter' is checked. "
                "The 'Filter Value' field is required and cannot be empty."
            )

    opt_enable_srctype = definition.parameters.get('enable_srctype', None)
    is_srctype_enabled = str(opt_enable_srctype).lower() in ["true", "1", "yes"]
    if is_srctype_enabled:
        custom_src = definition.parameters.get('custom_srctype', None)
        if not custom_src or not str(custom_src).strip():
            raise ValueError(
                "[-] Validation Error: 'Enable Custom Sourcetype' is checked. "
                "The 'Custom Sourcetype' field is required and cannot be empty."
            )


# ==========================================
# HELPER:  PARSE HOSTS (CLUSTER-AWARE)
# ==========================================
# SECURITY FIX (VULN-06): Block internal/metadata IPs to prevent SSRF
_BLOCKED_HOSTS = {'localhost', '0.0.0.0', '169.254.169.254', 'metadata.google.internal'}

def _validate_host(host):
    """
    Validate that a hostname is not pointing to an internal service.
    Prevents SSRF attacks targeting cloud metadata endpoints,
    loopback interfaces, or link-local addresses.
    """
    if host.lower() in _BLOCKED_HOSTS:
        raise ValueError(f"Blocked host: '{host}' — internal/metadata addresses are not allowed.")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            raise ValueError(f"Blocked loopback IP: {host}")
        if ip.is_link_local:
            raise ValueError(f"Blocked link-local IP: {host}")
    except ValueError as ve:
        if "Blocked" in str(ve):
            raise
        # Not a valid IP literal → treat as hostname (acceptable)
    return host


def _parse_hosts(host_string, port, scheme="https"):
    """
    Parse a single or comma-separated host string into the list-of-dicts
    format accepted by the ``elasticsearch-py`` client.

    Supports the following patterns::

        "192.168.1.10"                       → single node
        "192.168.1.10, 192.168.1.11"         → multi-node (comma-separated)
        "es-node-1.local,es-node-2.local"    → multi-node (DNS names)

    Returns a list of ``{"host": ..., "port": ..., "scheme": ...}`` dicts.

    Raises ValueError if any host fails SSRF validation.
    """
    hosts = []
    for h in str(host_string).split(","):
        h = h.strip()
        if h:
            _validate_host(h)  # SECURITY: SSRF check
            hosts.append({"host": h, "port": int(port), "scheme": scheme})
    return hosts if hosts else [{"host": _validate_host(str(host_string).strip()), "port": int(port), "scheme": scheme}]


# ==========================================
# DATA COLLECTION ROUTINE (SCHEDULER / WORKER)
# ==========================================
def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # ── 1. READ DATA INPUT IDENTITY ──────────────────────────────────────────
    opt_es_cluster_target = helper.get_arg('es_cluster_target')
    opt_es_index          = helper.get_arg('es_index')
    opt_date_field        = helper.get_arg('date_field') or "@timestamp"
    opt_time_preset       = helper.get_arg('time_preset') or "1h"

    time_preset_str = str(opt_time_preset).strip()
    if re.match(r'^\d+[smhdwMy]$', time_preset_str):
        fallback_time = f"now-{time_preset_str}"
    else:
        fallback_time = time_preset_str

    opt_enable_filter  = helper.get_arg('enable_filter')
    is_filter_enabled  = str(opt_enable_filter).lower() in ["true", "1", "yes"]
    opt_filter_key     = helper.get_arg('filter_key')
    opt_filter_val     = helper.get_arg('filter_val')

    opt_enable_srctype = helper.get_arg('enable_srctype')
    is_srctype_enabled = str(opt_enable_srctype).lower() in ["true", "1", "yes"]
    opt_custom_srctype = helper.get_arg('custom_srctype')

    stanza_name_dict = helper.get_input_stanza()
    stanza_name_raw  = list(stanza_name_dict.keys())[0] if stanza_name_dict else opt_es_index
    stanza_name      = stanza_name_raw.split("://")[-1] if "://" in stanza_name_raw else stanza_name_raw

    # Sanitize stanza_name so it is safe to use as a directory name
    safe_stanza_name = re.sub(r'[<>:"/\\|?*]', '_', stanza_name)

    # SECURITY FIX (VULN-04): Sanitize for log injection — strip control chars
    safe_log_name = re.sub(r'[\n\r\t\x00-\x1f]', '', stanza_name)

    # ── 2. INITIALIZE STATE MANAGER (v1.2.3 — Smart Fallback) ─────────────────
    # Creates both file-based and KVStore managers, wraps them in
    # SmartFallbackManager that selects the newest bookmark on load.
    try:
        state = create_state_manager(helper, safe_stanza_name)
    except Exception as e:
        helper.log_error(
            f"[-] FATAL: Cannot initialize state manager for '{stanza_name}': {str(e)}"
        )
        return

    # ── 3. RESOLVE GLOBAL CONFIGURATION VIA INTERNAL REST API ────────────────
    try:
        uri = (
            f"{helper.context_meta.get('server_uri')}/servicesNS/nobody/"
            f"TA-ensign_elasticsearch_add-on--Modular_input/"
            f"TA_ensign_elasticsearch_add_on__Modular_input_es_clusters/"
            f"{urllib.parse.quote(opt_es_cluster_target)}?output_mode=json&--cred--=1"
        )
        splunk_headers = {
            "Authorization": f"Splunk {helper.context_meta.get('session_key')}"
        }
        # FIX (v1.2.5): verify=False for internal splunkd REST call.
        # Splunkd uses a self-signed certificate by default on the management
        # port (8089). verify=True causes SSL_CERTIFICATE_VERIFY_FAILED fatal
        # exception on every input cycle. Session-key authentication provides
        # sufficient security for this localhost-only request.
        response = helper.send_http_request(
            uri, "GET",
            parameters=None, payload=None,
            headers=splunk_headers, cookies=None,
            verify=False, cert=None, timeout=30, use_proxy=False
        )

        if response.status_code != 200:
            helper.log_error(
                f"[-] FATAL: Failed to read ES Cluster profile '{opt_es_cluster_target}'. "
                f"HTTP Status: {response.status_code}"
            )
            return

        cluster_data = response.json().get('entry', [])[0].get('content', {})

        # CHECK DISABLED STATUS
        is_disabled = str(cluster_data.get('disabled', '0')).lower() in ['1', 'true', 'yes']
        if is_disabled:
            helper.log_error(
                f"[-] BLOCKED: ES Cluster profile '{opt_es_cluster_target}' is DISABLED. "
                f"Data collection aborted for '{stanza_name}'."
            )
            return

        opt_es_host         = cluster_data.get('es_host')
        opt_es_port         = int(cluster_data.get('es_port', 9200))
        opt_es_user         = cluster_data.get('es_user')
        opt_es_pass         = cluster_data.get('es_pass')

        # SSL/TLS
        opt_verify_cert_raw = cluster_data.get('verify_cert', '0')
        is_verify_cert      = str(opt_verify_cert_raw).lower() in ['1', 'true', 'yes']
        opt_cert_location   = cluster_data.get('cert_location', '').strip()

        # ── CLUSTER-AWARE SETTINGS (v1.2.0) ──────────────────────────────────
        opt_enable_sniffing_raw = cluster_data.get('enable_sniffing', '0')
        is_sniffing_enabled     = str(opt_enable_sniffing_raw).lower() in ['1', 'true', 'yes']

        opt_max_retries         = int(cluster_data.get('max_retries', 3))
        opt_retry_on_timeout_raw = cluster_data.get('retry_on_timeout', '1')
        is_retry_on_timeout     = str(opt_retry_on_timeout_raw).lower() in ['1', 'true', 'yes']

        opt_conn_timeout        = int(cluster_data.get('connection_timeout', 30))

    except Exception as e:
        helper.log_error(
            f"[-] FATAL: System error while accessing ES Cluster profile "
            f"'{opt_es_cluster_target}': {str(e)}"
        )
        return

    # ── 4. LOAD CHECKPOINT STATE ──────────────────────────────────────────────
    # Primary  : file-based bookmark in collection/<stanza>/last_bookmark.txt
    # Secondary: Splunk-native helper.get_check_point() (legacy compat)
    # Fallback  : configured time_preset (e.g. "now-1h")

    splunk_native_bookmark = helper.get_check_point(f"last_elastic_query_{safe_stanza_name}")
    last_run_bookmark      = state.load_bookmark(splunk_native_bookmark or fallback_time)

    helper.log_info(
        f"[*] Stanza '{safe_log_name}' | "
        f"Collection dir: {state.collection_dir} | "
        f"Query window gte: {last_run_bookmark}"
    )

    # ── OPERATIONAL LOGGING (v1.2.5) ─────────────────────────────────────────
    # Input config
    helper.log_info(
        f"[*] Input Config: cluster={opt_es_cluster_target}, "
        f"es_index={opt_es_index}, date_field={opt_date_field}, "
        f"fetch_range={opt_time_preset}, interval={helper.get_arg('interval')}s"
    )

    # Filter config
    if is_filter_enabled:
        helper.log_info(
            f"[*] Filter Config: ENABLED | "
            f"key='{opt_filter_key}', val='{opt_filter_val}'"
        )
    else:
        helper.log_info("[*] Filter Config: DISABLED (no custom DSL filter applied)")

    # Sourcetype config
    if is_srctype_enabled and opt_custom_srctype:
        helper.log_info(f"[*] Sourcetype: CUSTOM → '{opt_custom_srctype}'")
    else:
        helper.log_info(f"[*] Sourcetype: DEFAULT → '{helper.get_sourcetype()}'")

    # ── 5. GLOBAL PROXY CHECK ─────────────────────────────────────────────────
    proxy_settings = helper.get_proxy()
    if proxy_settings:
        proxy_url  = proxy_settings.get("proxy_url")
        proxy_port = proxy_settings.get("proxy_port", "8080")
        if proxy_url:
            proxy_user = proxy_settings.get("proxy_username", "")
            proxy_pass = proxy_settings.get("proxy_password", "")
            proxy_type = proxy_settings.get("proxy_type", "http").lower()

            auth_str = ""
            if proxy_user and proxy_pass:
                safe_user = urllib.parse.quote(proxy_user)
                safe_pass = urllib.parse.quote(proxy_pass)
                auth_str  = f"{safe_user}:{safe_pass}@"

            proxy_str = f"{proxy_type}://{auth_str}{proxy_url}:{proxy_port}"
            os.environ['HTTP_PROXY']  = proxy_str
            os.environ['HTTPS_PROXY'] = proxy_str

    # SECURITY FIX (VULN-02): Flag for env var cleanup after client creation
    _proxy_env_set = bool(proxy_settings and proxy_settings.get('proxy_url'))

    # ── 6. EXECUTE DATA COLLECTION FROM ELASTICSEARCH ────────────────────────
    try:
        # ── Build Elasticsearch Client (CLUSTER-AWARE v1.2.0) ─────────────
        # Parse comma-separated hosts for multi-node cluster support.
        # Example: "node1.es.local, node2.es.local, node3.es.local"
        hosts_list = _parse_hosts(opt_es_host, opt_es_port, scheme="https")

        es_kwargs = {
            "hosts":            hosts_list,
            "headers":          {"Content-Type": "application/json"},
            "basic_auth":       (opt_es_user, opt_es_pass),
            "request_timeout":  opt_conn_timeout,
            "max_retries":      opt_max_retries,
            "retry_on_timeout": is_retry_on_timeout,
        }

        # SSL/TLS configuration — SECURITY FIX (VULN-01, VULN-05)
        if is_verify_cert:
            es_kwargs["verify_certs"] = True
            if opt_cert_location:
                # SECURITY FIX (v1.2.5): Use cert_path.py for hardened validation
                try:
                    from cert_path import validate_cert_path
                    validated = validate_cert_path(opt_cert_location)
                    es_kwargs["ca_certs"] = validated
                except (ValueError, ImportError) as cert_err:
                    helper.log_error(
                        f"[-] SECURITY: cert_location rejected: {cert_err}. "
                        f"Falling back to system CA bundle."
                    )
            # If no cert_location specified, elasticsearch-py uses system CA (certifi)
        else:
            es_kwargs["verify_certs"] = False
            # SECURITY FIX (VULN-01): Explicit warning when TLS verification disabled
            helper.log_warning(
                f"[!] SECURITY WARNING: SSL certificate verification is DISABLED "
                f"for stanza '{safe_log_name}'. Credentials are vulnerable to "
                f"Man-in-the-Middle (MitM) interception. Enable 'Verify SSL/TLS "
                f"Certificate' in ES Cluster configuration for production use."
            )

        # Node Sniffing — auto-discover all nodes in the ES cluster
        if is_sniffing_enabled:
            es_kwargs["sniff_on_start"]        = True
            es_kwargs["sniff_on_node_failure"]  = True
            es_kwargs["sniff_before_requests"]  = True
            es_kwargs["sniff_timeout"]          = 5
            es_kwargs["min_delay_between_sniffing"] = 60

        # Multi-node load balancing (round-robin across discovered nodes)
        if len(hosts_list) > 1:
            es_kwargs["randomize_nodes_in_pool"] = True

        client = Elasticsearch(**es_kwargs)

        # SECURITY FIX (VULN-02): Clean proxy credentials from env vars
        # immediately after client creation to minimize exposure window.
        if _proxy_env_set:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)

        # Proxy status log (v1.2.5)
        if _proxy_env_set:
            helper.log_info(
                f"[*] Proxy: ENABLED | host={proxy_settings.get('proxy_url')}, "
                f"port={proxy_settings.get('proxy_port', '8080')}, "
                f"auth={'YES' if proxy_settings.get('proxy_username') else 'NO'}"
            )
        else:
            helper.log_info("[*] Proxy: NOT configured")

        # ES Client config log (v1.2.5)
        helper.log_info(
            f"[*] ES Client: hosts={len(hosts_list)}, max_retries={opt_max_retries}, "
            f"timeout={opt_conn_timeout}s, sniffing={'ON' if is_sniffing_enabled else 'OFF'}, "
            f"tls_verify={'ON' if is_verify_cert else 'OFF'}, "
            f"pool={'multi-node' if len(hosts_list) > 1 else 'single-node'}"
        )

        # ── Cluster Health Preflight Check (v1.2.0) ───────────────────────
        # If connected to a cluster, perform a lightweight health check
        # to detect RED status before starting data collection.
        try:
            health = client.cluster.health(timeout="10s")
            cluster_status = health.get("status", "unknown")
            cluster_name   = health.get("cluster_name", "unknown")
            node_count     = health.get("number_of_nodes", "?")

            helper.log_info(
                f"[*] ES Cluster Health: status={cluster_status}, "
                f"cluster={cluster_name}, nodes={node_count}, "
                f"hosts_configured={len(hosts_list)}, "
                f"sniffing={'ON' if is_sniffing_enabled else 'OFF'}, "
                f"tls_verify={'ON' if is_verify_cert else 'OFF'}"
            )

            if cluster_status == "red":
                helper.log_error(
                    f"[-] WARNING: ES Cluster '{cluster_name}' status is RED. "
                    f"Data collection may be incomplete or unreliable. "
                    f"Proceeding with caution for stanza '{safe_log_name}'."
                )
                # NOTE: We proceed despite RED status because some indices
                # may still be available. The operator should be alerted
                # via Splunk internal logs.

        except Exception as health_ex:
            # Health check is best-effort; don't block collection if it fails
            helper.log_info(
                f"[!] Cluster health check skipped (non-fatal): {str(health_ex)}"
            )

        # ── Scroll State Recovery ─────────────────────────────────────────
        # If a previous run left a scroll state (crash mid-scroll), try to
        # resume. ES scroll contexts survive ~5 min after last access, so
        # this only helps when the scheduler interval is shorter than that.
        scroll_id   = None
        hits        = []
        saved_state = state.load_scroll_state()

        if saved_state and saved_state.get("scroll_id"):
            try:
                helper.log_info(
                    f"[*] Attempting scroll recovery for '{safe_log_name}' "
                    f"(saved at {saved_state.get('saved_at', '?')})"
                )
                resume_resp = client.scroll(
                    scroll_id=saved_state["scroll_id"],
                    scroll="5m"
                )
                scroll_id = resume_resp.get("_scroll_id")
                hits      = resume_resp.get("hits", {}).get("hits", [])
                helper.log_info(
                    f"[+] Scroll context resumed successfully for '{safe_log_name}'."
                )
            except Exception as scroll_ex:
                # Context has expired on the ES cluster — start fresh
                helper.log_info(
                    f"[!] Saved scroll context expired for '{safe_log_name}', "
                    f"issuing fresh search. Detail: {str(scroll_ex)}"
                )
                state.clear_scroll_state()
                saved_state = None

        if not saved_state:
            # ── Fresh Search ──────────────────────────────────────────────
            must_conditions = [
                {"range": {opt_date_field: {"gte": last_run_bookmark, "lte": "now"}}}
            ]
            if is_filter_enabled:
                must_conditions.append({"term": {opt_filter_key: opt_filter_val}})

            search_query = {"bool": {"must": must_conditions}}

            # Query DSL log (v1.2.5)
            helper.log_info(
                f"[*] ES Query DSL: {json.dumps(search_query, ensure_ascii=False)}"
            )

            response  = client.search(
                index=opt_es_index,
                query=search_query,
                size=1000,
                scroll="5m"
            )
            scroll_id = response.get("_scroll_id")
            hits      = response.get("hits", {}).get("hits", [])

            # ES Response summary log (v1.2.5)
            total_hits = response.get('hits', {}).get('total', {}).get('value', '?')
            helper.log_info(
                f"[*] ES Response: total_hits={total_hits}, "
                f"first_page={len(hits)}, scroll_id={'present' if scroll_id else 'none'}"
            )

            # Persist scroll state right after fresh search so that a crash
            # during processing of the very first page is also recoverable.
            if scroll_id:
                state.save_scroll_state(scroll_id, last_run_bookmark)

        # ── Deduplication Guard ───────────────────────────────────────────
        # seen_ids.txt is scoped per-stanza (inside collection/<stanza_name>/)
        seen_ids       = state.load_seen_ids()
        newly_seen_ids = []
        total_ingested = 0
        total_skipped  = 0

        # Sourcetype resolution
        final_sourcetype = (
            opt_custom_srctype
            if (is_srctype_enabled and opt_custom_srctype)
            else helper.get_sourcetype()
        )

        # ── Main Scroll Loop ──────────────────────────────────────────────
        while len(hits) > 0:
            for doc in hits:
                doc_id      = doc.get("_id", "")
                source_data = doc.get("_source", {})

                # Skip docs already ingested in a previous overlapping run
                if doc_id and doc_id in seen_ids:
                    total_skipped += 1
                    continue

                event = helper.new_event(
                    source=f"elasticsearch_api://{opt_es_index}",
                    index=helper.get_output_index(),
                    sourcetype=final_sourcetype,
                    data=json.dumps(source_data, ensure_ascii=False)
                )
                ew.write_event(event)
                total_ingested += 1

                if doc_id:
                    newly_seen_ids.append(doc_id)

            # Update scroll_state after each page — always point to latest cursor
            if scroll_id:
                state.save_scroll_state(scroll_id, last_run_bookmark)

            response  = client.scroll(scroll_id=scroll_id, scroll="5m")
            scroll_id = response.get("_scroll_id")
            hits      = response.get("hits", {}).get("hits", [])

        # ── Finalize: Persist All State ───────────────────────────────────
        current_time_utc = datetime.datetime.utcnow().isoformat() + "Z"

        # 1. Update file-based timestamp bookmark (primary)
        state.save_bookmark(current_time_utc)

        # 2. Update Splunk-native checkpoint (secondary / legacy compat)
        helper.save_check_point(f"last_elastic_query_{safe_stanza_name}", current_time_utc)

        # 3. Append newly seen doc IDs to this stanza's per-stanza dedup guard
        state.append_seen_ids(newly_seen_ids)

        # 4. Clear scroll state — full collection completed without error
        state.clear_scroll_state()

        helper.log_info(
            f"[+] Task '{safe_log_name}' completed | "
            f"Ingested: {total_ingested} events | "
            f"Skipped (dup): {total_skipped} | "
            f"ES Hosts: {opt_es_host} | "
            f"Collection dir: {state.collection_dir}"
        )

    except Exception as e:
        helper.log_error(
            f"[-] FATAL: Data collection error for '{safe_log_name}': {str(e)}"
        )
        # NOTE: scroll_state.json is intentionally NOT cleared on exception
        # so the next scheduled run can attempt scroll context recovery.
    finally:
        # SECURITY FIX (v1.2.5): Guaranteed proxy credential cleanup
        # Ensures HTTP_PROXY/HTTPS_PROXY are scrubbed even on exception
        if _proxy_env_set:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
