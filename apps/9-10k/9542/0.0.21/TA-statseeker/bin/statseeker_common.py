import hashlib
import json
import logging
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from solnlib import conf_manager, log
from urllib3.util.retry import Retry


ADDON_NAME = "TA-statseeker"

FIELD_ALIASES = {
    "cdt_device.name": "deviceName",
    "cdt_device.ipaddress": "deviceIp",
    "cdt_device.vendor": "deviceVendor",
    "cdt_device.sysLocation": "deviceLocation",
    "cdt_device.sysName": "deviceSysName",
    "cdt_device.sysDescr": "deviceSysDescr",
    "cdt_device.sysObjectID": "deviceSysObjectId",
    "ipaddress": "deviceIp",
    "vendor": "deviceVendor",
    "sysLocation": "deviceLocation",
    "sysName": "deviceSysName",
    "sysDescr": "deviceSysDescr",
    "sysObjectID": "deviceSysObjectId",
    "snmp_state": "snmpState",
    "ping_state": "pingState",
    "snmp_poll": "snmpPoll",
    "ping_poll": "pingPoll",
    "memorySize": "deviceMemorySize",
}


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger("{0}_{1}".format(ADDON_NAME.lower(), input_name))


def sanitize_log_value(value) -> str:
    normalized = str(value or "")
    normalized = normalized.replace("\\", "\\\\").replace('"', '\\"')
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def log_collection_exception(logger, exc: Exception, input_name: str, resource: str, action: str = "input_failed"):
    logger.error(
        'statseeker_ta_action=%s input_name=%s resource=%s exception_type=%s exception_message="%s"',
        action,
        sanitize_log_value(input_name),
        sanitize_log_value(resource),
        exc.__class__.__name__,
        sanitize_log_value(exc),
    )


def extract_timeseries_samples_with_reason(metric_block: dict, sample_interval: int) -> Tuple[List[Tuple[float, float]], str]:
    if not isinstance(metric_block, dict):
        return [], "metric_block_not_dict"

    values = metric_block.get("vals")
    if not isinstance(values, list):
        return [], "vals_missing_or_not_list"

    if not values:
        return [], "vals_empty"

    if isinstance(values[0], (list, tuple)):
        samples = []
        skipped_null = 0
        skipped_unparseable = 0
        skipped_shape = 0
        for sample in values:
            if not isinstance(sample, (list, tuple)) or len(sample) < 2:
                skipped_shape += 1
                continue
            timestamp, value = sample[0], sample[1]
            if value is None:
                skipped_null += 1
                continue
            try:
                samples.append((float(timestamp), float(value)))
            except (TypeError, ValueError):
                skipped_unparseable += 1
        if samples:
            return samples, "ok"
        if skipped_unparseable:
            return [], "vals_nested_unparseable"
        if skipped_shape:
            return [], "vals_nested_invalid_shape"
        if skipped_null:
            return [], "vals_nested_all_null"
        return [], "vals_nested_no_samples"

    timestamps = metric_block.get("value_time")
    derived_timestamps = False
    if not isinstance(timestamps, list) or len(timestamps) != len(values):
        start_time = metric_block.get("start_time")
        if isinstance(start_time, (int, float)):
            timestamps = [float(start_time) + (sample_interval * idx) for idx in range(len(values))]
            derived_timestamps = True
        else:
            return [], "timestamps_missing"

    samples = []
    skipped_null = 0
    skipped_unparseable = 0
    for timestamp, value in zip(timestamps, values):
        if value is None:
            skipped_null += 1
            continue
        try:
            samples.append((float(timestamp), float(value)))
        except (TypeError, ValueError):
            skipped_unparseable += 1

    if samples:
        return samples, "ok_derived_timestamps" if derived_timestamps else "ok"
    if skipped_unparseable:
        return [], "vals_unparseable"
    if skipped_null:
        return [], "vals_all_null"
    return [], "vals_no_samples"


def sanitize_metric_part(value: str) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def to_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("0", "false", "f", "no", "off", "")


def to_int(value, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def parse_csv(value: str) -> List[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def normalize_optional_field(value) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    if normalized.lower() == "none":
        return ""
    return normalized


def merge_fields(*field_groups: List[str]) -> List[str]:
    merged = []
    seen = set()
    for field_group in field_groups:
        for field_name in field_group:
            normalized = str(field_name or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def add_scalar_field(target: dict, field_name: str, field_value, include_raw: bool = True):
    if field_value is None or isinstance(field_value, (dict, list)):
        return
    if include_raw:
        target[field_name] = field_value
    alias = FIELD_ALIASES.get(field_name)
    if alias:
        target[alias] = field_value


def get_account_config(session_key: str, account_name: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm="__REST_CREDENTIAL__#{0}#configs/conf-ta-statseeker_account".format(ADDON_NAME),
    )
    account_conf_file = cfm.get_conf("ta-statseeker_account")
    return dict(account_conf_file.get(account_name))


def build_session(verify_ssl: bool) -> requests.Session:
    session = requests.Session()
    session.verify = verify_ssl
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class StatseekerClient:
    def __init__(self, session: requests.Session, base_url: str, username: str, password: str, auth_mode: str):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.auth_mode = (auth_mode or "auto").strip().lower()
        self._bearer_token = None
        self._use_basic = self.auth_mode == "basic"

    def authenticate(self):
        if self._use_basic:
            return

        response = self.session.post(
            "{0}/ss-auth".format(self.base_url),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"user": self.username, "password": self.password},
            timeout=30,
        )
        if response.status_code == 200:
            payload = response.json()
            self._bearer_token = payload.get("access_token")
            if self._bearer_token:
                return
        if self.auth_mode == "token":
            response.raise_for_status()
            raise ValueError("Statseeker token authentication succeeded but no access token was returned.")
        self._use_basic = True

    def request(self, method: str, path: str, *, params: Optional[dict] = None) -> requests.Response:
        if self._bearer_token is None and not self._use_basic:
            self.authenticate()

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth = None
        if self._use_basic:
            auth = (self.username, self.password)
        else:
            headers["Authorization"] = "Bearer {0}".format(self._bearer_token)

        response = self.session.request(
            method=method,
            url="{0}{1}".format(self.base_url, path),
            params=params,
            headers=headers,
            auth=auth,
            timeout=60,
        )

        if response.status_code == 401 and not self._use_basic:
            if self.auth_mode == "auto":
                self._use_basic = True
                return self.request(method, path, params=params)
            self._bearer_token = None
            self.authenticate()
            headers["Authorization"] = "Bearer {0}".format(self._bearer_token)
            response = self.session.request(
                method=method,
                url="{0}{1}".format(self.base_url, path),
                params=params,
                headers=headers,
                timeout=60,
            )

        response.raise_for_status()
        return response


def build_query_string(params: dict) -> str:
    parts = []
    for key, value in params.items():
        if value is None or value == "":
            continue
        safe = ""
        if key == "fields":
            safe = ",._"
        elif key in {"formats", "group_by", "time_sort"} or key.endswith("_formats") or key.endswith("_states"):
            safe = ",._{}"
        elif key.endswith("_filter") or key.endswith("_timefilter") or key == "timefilter":
            safe = "=(),\"- _.%"
        elif key in {"value_time", "links"}:
            safe = "_"
        encoded_value = quote(str(value), safe=safe)
        parts.append("{0}={1}".format(key, encoded_value))
    return "&".join(parts)


def extract_resource_objects(payload: dict, resource_name: str) -> List[dict]:
    wrapper = payload.get("data", {}) if isinstance(payload, dict) else {}
    objects = wrapper.get("objects", []) if isinstance(wrapper, dict) else []
    for item in objects:
        if item.get("type") == resource_name:
            return item.get("data", []) or []
    return []


def fetch_paged_resource(
    client: StatseekerClient,
    resource_name: str,
    base_params: dict,
    page_size: int,
    response_type: Optional[str] = None,
) -> Iterable[dict]:
    offset = 0
    expected_type = response_type or resource_name
    while True:
        params = dict(base_params)
        params["limit"] = str(page_size)
        params["offset"] = str(offset)
        params["links"] = "none"
        response = client.request(
            "GET",
            "/api/v2.1/{0}/?{1}".format(resource_name, build_query_string(params)),
        )
        objects = extract_resource_objects(response.json(), expected_type)
        if not objects:
            break
        for item in objects:
            yield item
        if len(objects) < page_size:
            break
        offset += page_size


def checkpoint_file_path(checkpoint_dir: Optional[str], input_name: str, prefix: str) -> Optional[str]:
    if not checkpoint_dir:
        return None
    digest = hashlib.sha1(input_name.encode("utf-8")).hexdigest()
    return os.path.join(checkpoint_dir, "{0}_{1}.json".format(prefix, digest))


def load_checkpoint(path: Optional[str]) -> dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError, TypeError):
        return {}
    return {}


def save_checkpoint(path: Optional[str], checkpoint: dict):
    if not path:
        return
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, sort_keys=True)