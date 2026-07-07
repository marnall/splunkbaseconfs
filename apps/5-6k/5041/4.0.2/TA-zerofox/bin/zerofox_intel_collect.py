"""CTI collection orchestration (Splunk-agnostic; helper adapts I/O to splunklib)."""

from __future__ import annotations

import datetime
import json
import os
from collections.abc import Callable, Mapping
from typing import Any

from zerofox_checkpoints import get_last_checked_intel, save_checkpoint_intel
from zerofox_epoch import epoch_for_parser
from zerofox_intel_client import ZeroFoxIntelClient, absolutize_url
from zerofox_intel_sources import IntelRegistry

EmitFn = Callable[[str, str, float, str], None]  # raw_json, sourcetype, epoch, stanza


def _default_start_iso(spec: Mapping[str, Any]) -> str:
    # ZFOX_DEV_LOOKBACK_DAYS overrides all per-feed defaults for local dev / QA.
    # The var is never set in production, so the per-feed YAML values always win there.
    dev_days = os.environ.get("ZFOX_DEV_LOOKBACK_DAYS")
    now = datetime.datetime.now(datetime.timezone.utc)
    if dev_days:
        start = now - datetime.timedelta(days=int(dev_days))
    else:
        lb = spec["default_lookback"]
        if "hours" in lb:
            start = now - datetime.timedelta(hours=int(lb["hours"]))
        else:
            start = now - datetime.timedelta(days=int(lb["days"]))
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat().replace("+00:00", "Z")


def _merge_query_params(
    spec: Mapping[str, Any],
    last_checked: str,
    optional_args: Mapping[str, str],
) -> dict[str, str]:
    params: dict[str, str] = {str(spec["date_param"]): last_checked}
    filters = spec.get("filters") or {}
    for input_key, api_param in filters.items():
        val = optional_args.get(str(input_key), "") or ""
        val = str(val).strip()
        if val:
            params[str(api_param)] = val
    extra = spec.get("extra_query_params") or {}
    for k, v in extra.items():
        params[str(k)] = str(v)
    return params


def collect_intel_for_stanza(
    *,
    registry: IntelRegistry,
    intel_source: str,
    splunk_stanza: str,
    checkpoint_dir: str,
    api_base_url: str,
    username: str,
    password: str,
    optional_args: Mapping[str, str],
    emit: EmitFn,
    log_error: Callable[[str], None],
    log_debug: Callable[[str], None],
    proxies: dict[str, str] | None = None,
    legacy_checkpoint_stanzas: list[str] | None = None,
    client: ZeroFoxIntelClient | None = None,
) -> int:
    spec = registry.require(intel_source)
    client = client or ZeroFoxIntelClient(api_base_url, username, password, proxies=proxies)

    last_checked = get_last_checked_intel(
        checkpoint_dir,
        intel_source,
        splunk_stanza,
        legacy_stanzas=legacy_checkpoint_stanzas,
    )
    if not last_checked:
        last_checked = _default_start_iso(spec)

    params = _merge_query_params(spec, last_checked, optional_args)
    path = str(spec["path"])
    if not path.startswith("/"):
        msg = f"invalid path in spec: {path!r}"
        raise ValueError(msg)
    first_url = absolutize_url(api_base_url, path[1:])

    date_field = str(spec["date_field"])
    epoch_parser = str(spec["epoch_parser"])
    sourcetype = str(spec["sourcetype"])

    total = 0
    for batch in client.iter_cti_pages(first_url, params):
        batch_checkpoint: str | None = None
        for indicator in batch:
            raw_ts = indicator.get(date_field)
            if raw_ts is None:
                log_error(f"missing date field {date_field!r} in indicator")
                continue
            ts_str = str(raw_ts)
            try:
                epoch = epoch_for_parser(epoch_parser, ts_str)
            except (ValueError, TypeError) as err:
                log_error(f"epoch parse failed for {ts_str!r}: {err}")
                continue
            payload = json.dumps(indicator)
            emit(payload, sourcetype, epoch, splunk_stanza)
            # Track the latest timestamp seen in this batch; checkpoint once after
            # all indicators are emitted rather than on every write.
            if batch_checkpoint is None or ts_str > batch_checkpoint:
                batch_checkpoint = ts_str
            total += 1
        if batch_checkpoint:
            save_checkpoint_intel(checkpoint_dir, intel_source, splunk_stanza, batch_checkpoint)

    log_debug(f"zerofox_intel {intel_source} stanza={splunk_stanza!r}: collected {total} events")
    return total
