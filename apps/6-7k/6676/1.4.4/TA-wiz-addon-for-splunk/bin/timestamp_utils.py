import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

DATE_PATTERN = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_PATTERN2 = "%Y-%m-%dT%H:%M:%SZ"

POLLING = "polling"
SYNC = "sync"
CURSOR = "cursor"


# Polling and sync share file/field; distinct KVStore keys come from the `kind` prefix.
@dataclass(frozen=True)
class _KindStorage:
    field: str
    filename: str


_KIND_STORAGE = {
    POLLING: _KindStorage("timestamp", "timestamp.txt"),
    SYNC:    _KindStorage("timestamp", "timestamp.txt"),
    CURSOR:  _KindStorage("cursor",    "cursor.txt"),
}

CHECKPOINT_STORAGE_KVSTORE = "KVStore"
CHECKPOINT_STORAGE_FILE = "file"
CHECKPOINT_STORAGE_BOTH = "KVStore and file"

# Anything outside this set is treated as ready — fail-open on unknown statuses.
_KVSTORE_NOT_READY_STATUSES = frozenset({'starting', 'failed'})

# Process-wide. Cluster mode never changes; readiness only flips False -> True.
_cluster_mode_cache = None
_kvstore_ready_cache = None


def _reset_caches_for_tests():
    global _cluster_mode_cache, _kvstore_ready_cache
    _cluster_mode_cache = None
    _kvstore_ready_cache = None


class KVStoreUnavailableError(Exception):
    pass


def _sanitize_source(source):
    """Replace non-[a-zA-Z0-9_-] with '_' to prevent path traversal."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', str(source))


def _get_session_key(helper):
    return helper.context_meta.get('session_key', '')


def _strip_z(value):
    if not isinstance(value, str):
        return value
    return value[:-1] if value.endswith('Z') else value


def _splunk_rest_get(session_key, endpoint):
    """Parsed JSON entry content or None on non-2xx / empty body / parse error.

    Network errors propagate so callers can decide whether to cache or retry.
    """
    import json
    import splunk.rest as rest
    response, content = rest.simpleRequest(
        endpoint, sessionKey=session_key,
        getargs={'output_mode': 'json'}, raiseAllErrors=False,
    )
    if not (200 <= response.status < 300):
        return None
    if not content:
        return None
    try:
        entries = json.loads(content).get('entry', [])
    except (ValueError, TypeError):
        return None
    return entries[0].get('content', {}) if entries else None


def _detect_cluster_mode(helper):
    # Never cache False on exception or missing content: an unknown answer would
    # permanently degrade an SHC member to standalone for the process lifetime.
    global _cluster_mode_cache
    if _cluster_mode_cache is not None:
        return _cluster_mode_cache
    try:
        content = _splunk_rest_get(_get_session_key(helper), '/services/shcluster/config')
    except Exception as e:
        helper.log_debug(f"Failed to detect cluster mode (will retry next poll): {e}")
        return False
    if content is None:
        helper.log_debug("SHC config unavailable during cluster-mode detection; will retry next poll")
        return False
    _cluster_mode_cache = content.get('mode', 'disabled') != 'disabled'
    return _cluster_mode_cache


def is_cluster_mode(helper):
    """Public wrapper around _detect_cluster_mode for callers outside the cursor path."""
    return _detect_cluster_mode(helper)


def _is_shc_captain(helper, session_key):
    content = _splunk_rest_get(session_key, '/services/server/info')
    if content is None:
        helper.log_warning("Cannot determine captain status, skipping to prevent duplicates")
        return False
    return 'shc_captain' in content.get('server_roles', [])


def should_run_in_shc(helper):
    """True for standalone or SHC captain; False otherwise (fail-safe on error)."""
    try:
        session_key = _get_session_key(helper)
        content = _splunk_rest_get(session_key, '/services/shcluster/config')
        if content is None:
            helper.log_debug("SHC config not available, assuming standalone mode")
            return True
        if content.get('mode', 'disabled') == 'disabled':
            return True
        is_captain = _is_shc_captain(helper, session_key)
        helper.log_info("Running on SHC captain") if is_captain else helper.log_debug("Skipping non-captain SHC member")
        return is_captain
    except Exception as e:
        helper.log_warning(f"Error checking SHC status: {e}. Skipping to prevent duplicates.")
        return False


def _extract_field(state, field):
    if not state:
        return None
    return state.get(field) if isinstance(state, dict) else state


class CheckpointManager:
    """Per-input polling timestamp, sync timestamp, and cursor.

    Standalone Splunk: KVStore with on-disk file fallback (fail-safe).
    SHC member: KVStore-only; unavailability raises KVStoreUnavailableError so
    the caller skips the poll instead of diverging across cluster members.
    """

    def __init__(self, helper, source, log_location, host, dir_name,
                 sync_host=None, sync_dir_name=None):
        self.helper = helper
        self.source = source
        self.log_location = log_location
        self.host = host
        self.dir_name = dir_name
        self.sync_host = sync_host or host
        self.sync_dir_name = sync_dir_name or dir_name
        self._is_cluster = _detect_cluster_mode(helper)

    @property
    def is_cluster_mode(self):
        return self._is_cluster

    def _build_key(self, kind):
        return f"{_sanitize_source(self.source)}_{kind}"

    def _file_host(self, kind):
        if kind == SYNC:
            return self.sync_host, self.sync_dir_name
        return self.host, self.dir_name

    def _read_file_fallback(self, kind):
        host, dir_name = self._file_host(kind)
        return get_latest_cursor(self.log_location, self.source, host, dir_name,
                                 filename=_KIND_STORAGE[kind].filename)

    def _legacy_file_path(self, kind):
        host, dir_name = self._file_host(kind)
        safe_source = _sanitize_source(self.source)
        return os.path.join(self.log_location, dir_name, host + safe_source,
                            _KIND_STORAGE[kind].filename)

    def _archive_file_fallback(self, kind):
        # Rename to .migrated so the file is never re-read; KVStore is authoritative post-migration.
        filepath = self._legacy_file_path(kind)
        if not os.path.exists(filepath):
            return
        archived = filepath + ".migrated"
        try:
            os.replace(filepath, archived)
            self.helper.log_info(f"Source {self.source}: archived legacy {filepath} -> {archived}")
        except OSError as e:
            self.helper.log_warning(f"Source {self.source}: archive of {filepath} failed: {e}")

    def _is_unmigrated_legacy_state(self, kind):
        # File-fallback gate: customer has a pre-WZ-99491 file AND has never
        # successfully migrated. Once .migrated exists, KVStore is the sole truth.
        legacy = self._legacy_file_path(kind)
        return os.path.exists(legacy) and not os.path.exists(legacy + ".migrated")

    def _write_file_fallback(self, kind, value):
        host, dir_name = self._file_host(kind)
        set_latest_cursor(self.helper, self.log_location, self.source, value, host, dir_name,
                          filename=_KIND_STORAGE[kind].filename)

    def _is_kvstore_ready(self):
        """Fail-open: only block on explicitly-bad statuses so unknown values
        from new Splunk builds don't silently skip every poll.
        """
        global _kvstore_ready_cache
        if _kvstore_ready_cache is True:
            return True
        content = _splunk_rest_get(_get_session_key(self.helper), '/services/kvstore/status')
        status = (content or {}).get('current', {}).get('status', 'unknown')
        if status in _KVSTORE_NOT_READY_STATUSES:
            self.helper.log_debug(f"KVStore status: {status}")
            return False
        if status == 'ready':
            _kvstore_ready_cache = True
        return True

    def _require_kvstore_ready(self, field):
        try:
            ready = self._is_kvstore_ready()
        except Exception as e:
            raise KVStoreUnavailableError(f"KVStore readiness check failed for {field}: {e}")
        if not ready:
            self.helper.log_debug(f"Source {self.source}: KVStore not ready for {field}, skipping poll")
            raise KVStoreUnavailableError(f"KVStore not ready for {field}; skipping poll")

    def _save(self, key, field, normalized_value):
        self.helper.save_check_point(key, {
            field: normalized_value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        self.helper.log_debug(
            f"Source {self.source}: checkpoint saved to KVStore "
            f"(key={key}, {field}={normalized_value})"
        )

    def _save_migrated(self, key, field, file_value):
        self.helper.save_check_point(key, {
            field: file_value,
            "migrated_from_file": True,
            "migration_date": datetime.now(timezone.utc).isoformat(),
        })
        self.helper.log_info(f"Source {self.source}: Migrated {field} to KVStore: {file_value}")

    def _validated_timestamp(self, raw):
        """Corrupt stored timestamp == first-run, not a permanent stall."""
        if raw is None:
            return None
        if not isinstance(raw, str):
            self.helper.log_warning(
                f"Source {self.source}: stored timestamp is {type(raw).__name__} not str; "
                "treating as first-run. Next poll will overwrite it."
            )
            return None
        # Storage strips trailing Z; try_parse_wiz_timestamp requires it.
        if try_parse_wiz_timestamp(raw + 'Z') is None:
            self.helper.log_warning(
                f"Source {self.source}: stored timestamp {raw!r} is unparseable; "
                "treating as first-run. Next poll will overwrite it."
            )
            return None
        return raw

    def _read(self, kind):
        field = _KIND_STORAGE[kind].field
        key = self._build_key(kind)
        normalize = (lambda v: v) if kind == CURSOR else _strip_z

        try:
            self._require_kvstore_ready(field)
            try:
                state = self.helper.get_check_point(key)
            except Exception as e:
                raise KVStoreUnavailableError(f"KVStore unavailable for {field}: {e}")

            value = _extract_field(state, field)
            if value:
                return normalize(value)

            if self._is_cluster:
                return None

            # One-time pre-WZ-99491 file migration. Migration failure is non-fatal
            # — the legacy gate stays open and the next poll retries.
            file_value = normalize(self._read_file_fallback(kind))
            if file_value:
                try:
                    self._save_migrated(key, field, file_value)
                    self._archive_file_fallback(kind)
                except Exception:
                    pass
            return file_value
        except KVStoreUnavailableError:
            if not self._is_cluster and self._is_unmigrated_legacy_state(kind):
                return normalize(self._read_file_fallback(kind))
            raise

    def _write(self, kind, value):
        field = _KIND_STORAGE[kind].field
        key = self._build_key(kind)
        normalized = value if kind == CURSOR else _strip_z(value)

        try:
            self._require_kvstore_ready(field)
            try:
                self._save(key, field, normalized)
            except Exception as e:
                raise KVStoreUnavailableError(f"Failed to save to KVStore: {e}")
            if not self._is_cluster and self._is_unmigrated_legacy_state(kind):
                self._write_file_fallback(kind, value)
                return CHECKPOINT_STORAGE_BOTH
            return CHECKPOINT_STORAGE_KVSTORE
        except KVStoreUnavailableError:
            if not self._is_cluster and self._is_unmigrated_legacy_state(kind):
                self._write_file_fallback(kind, value)
                return CHECKPOINT_STORAGE_FILE
            raise

    def get_timestamp(self):
        return self._validated_timestamp(self._read(POLLING))

    def set_timestamp(self, value):
        # Lex compare == chrono compare only because ASCII '.' < '0'.
        # Validated read so corrupt values self-heal; KVStore errors propagate
        # rather than bypass the guard and let a backward write through.
        current = self._validated_timestamp(self._read(POLLING))
        if current:
            new_normalized = _strip_z(value)
            if new_normalized is not None and new_normalized <= current:
                self.helper.log_warning(
                    f"Source {self.source}: rewind blocked: tried to set "
                    f"polling={new_normalized} but current={current}"
                )
                return None
        return self._write(POLLING, value)

    def get_sync_timestamp(self, frequency_days):
        """None when sync is disabled or no timestamp exists; re-appends the 'Z' suffix."""
        if frequency_days == 0:
            return None
        timestamp = self._validated_timestamp(self._read(SYNC))
        return timestamp + 'Z' if timestamp else None

    def set_sync_timestamp(self, value):
        return self._write(SYNC, value)

    def get_cursor(self):
        return self._read(CURSOR)

    def set_cursor(self, value):
        return self._write(CURSOR, value)


def get_latest_cursor(log_location, source, host, dir_name, filename="cursor.txt"):
    # Read-only: don't create the legacy directory; post-WZ-99491 nobody writes here.
    safe_source = _sanitize_source(source)
    filepath = os.path.join(log_location, dir_name, host + safe_source, filename)
    if not os.path.exists(filepath) or os.stat(filepath).st_size == 0:
        return None
    with open(filepath, "r") as f:
        return f.read()


def set_latest_cursor(helper, log_location, source, value, host, dir_name, filename="cursor.txt"):
    # Atomic write via tmp + os.replace so a mid-write crash can't corrupt the cursor.
    safe_source = _sanitize_source(source)
    dirpath = os.path.join(log_location, dir_name, host + safe_source)
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, filename)
    tmp = filepath + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(value))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, filepath)
    helper.log_warning(
        f"Source {source}: checkpoint written to file fallback {filepath}"
    )




# strptime %f maxes at 6 digits; Wiz can emit 7+ (re-assessed issues).
_SUBMICRO_FRACTION_RE = re.compile(r'(\.\d{6})\d+(Z?)$')


def try_parse_wiz_timestamp(date_str, nudge=True):
    """Try Wiz's 2 timestamp formats; return parsed datetime or None.

    nudge=True (default) bumps the result forward by 1us/1s so a subsequent
    `after:` filter excludes events already pulled. nudge=False for raw
    arithmetic that would compound the nudge.
    """
    if isinstance(date_str, str):
        date_str = _SUBMICRO_FRACTION_RE.sub(r'\1\2', date_str)
    try:
        parsed = datetime.strptime(date_str, DATE_PATTERN)
        return parsed + timedelta(microseconds=1) if nudge else parsed
    except Exception:
        try:
            parsed = datetime.strptime(date_str, DATE_PATTERN2)
            return parsed + timedelta(seconds=1) if nudge else parsed
        except Exception:
            return None


def should_trigger_full_sync(latest_sync, frequency_days):
    if not latest_sync:
        return False
    threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=frequency_days)
    return try_parse_wiz_timestamp(latest_sync) <= threshold


def get_latest_sync(frequency_days, log_location, source, host, dir_name):
    if frequency_days == 0:
        return None
    latest_sync = get_latest_cursor(log_location, source, host, dir_name, filename="timestamp.txt")
    return latest_sync + 'Z' if latest_sync else None


def with_overlap_buffer(time_str):
    """Subtract 1 hour to overlap windows, absorbing late-arriving data without gaps."""
    dt = try_parse_wiz_timestamp(time_str)
    return (dt - timedelta(hours=1)).strftime(DATE_PATTERN) if dt else None
