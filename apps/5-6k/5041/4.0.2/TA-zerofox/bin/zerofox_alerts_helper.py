"""UCC input helper for ZeroFox Alerts (splunklib modular input)."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from solnlib import conf_manager
from splunklib import modularinput as smi
from splunklib.modularinput import Event
from zerofox_checkpoints import read_text_checkpoint, write_text_checkpoint
from zerofox_proxy import build_proxies

_SOURCETYPE = "zfox"
_CHECKPOINT_PREFIX = "zerofox_alerts::"
# Dev overrides: set ZFOX_DEV_API_BASE / ZFOX_DEV_LOOKBACK_DAYS in the container
# environment (.env → docker-compose) to point at QA and shorten the initial window.
# Both vars are absent in production — defaults are always used there.
_API_BASE = os.environ.get("ZFOX_DEV_API_BASE", "https://api.zerofox.com")
_LOOKBACK_INITIAL_DAYS = int(os.environ.get("ZFOX_DEV_LOOKBACK_DAYS", "365"))
_LOOKBACK_INCREMENTAL_DAYS = 90


def _ucc_conf_stanzas(bin_dir: Path) -> tuple[str, str, str]:
    """Read addon_name, account_conf, settings_conf from the packaged globalConfig.json."""
    gc_path = bin_dir.parent / "appserver" / "static" / "js" / "build" / "globalConfig.json"
    gc = json.loads(gc_path.read_text(encoding="utf-8"))
    meta = gc["meta"]
    addon_name = str(meta["name"])
    rest_root = str(meta["restRoot"])
    tail = rest_root[3:] if rest_root.startswith("TA_") else rest_root
    suffix = tail.lower()
    return addon_name, f"ta_{suffix}_account", f"ta_{suffix}_settings"


def _account_credentials(
    session_key: str,
    addon_name: str,
    account_conf: str,
    account_name: str,
) -> tuple[str, str]:
    realm = f"__REST_CREDENTIAL__#{addon_name}#configs/conf-{account_conf}"
    cfm = conf_manager.ConfManager(session_key, addon_name, realm=realm)
    stanza = cfm.get_conf(account_conf).get(account_name)
    user = stanza.get("username")
    pwd = stanza.get("password")
    if not user or not pwd:
        msg = f"Account {account_name!r} is missing username or password"
        raise ValueError(msg)
    return str(user), str(pwd)


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------


def _alerts_checkpoint_key(instance: str) -> str:
    return f"{_CHECKPOINT_PREFIX}{instance}"


def _read_legacy_checkpoint(checkpoint_dir: str, stanza: str) -> str | None:
    """Migrate the old AoB md5-based checkpoint written by the legacy modular input."""
    cp_dir = os.path.join(checkpoint_dir, hashlib.md5(stanza.encode()).hexdigest())
    cp_file = os.path.join(cp_dir, hashlib.md5("splunk_alert_idcache".encode()).hexdigest())
    try:
        with open(cp_file, encoding="utf-8") as fh:
            alert_ids = fh.read().split(",")
        last_entry = alert_ids[-1]
        if last_entry and last_entry[0] == ":":
            last_update = last_entry[1:].strip()
            ts = datetime.datetime.utcfromtimestamp(int(last_update)).strftime("%Y-%m-%dT%H:%M:%SZ")
            shutil.rmtree(cp_dir, ignore_errors=True)
            return ts
    except Exception:
        pass
    return None


def _get_last_checked(checkpoint_dir: str, instance: str, legacy_stanza: str) -> str | None:
    """Return the most-recent checkpoint for this input; migrate legacy format on first run."""
    key = _alerts_checkpoint_key(instance)
    found = read_text_checkpoint(checkpoint_dir, key)
    if found:
        return found
    legacy = _read_legacy_checkpoint(checkpoint_dir, legacy_stanza)
    if legacy:
        write_text_checkpoint(checkpoint_dir, key, legacy)
        return legacy
    return None


def _save_checkpoint(checkpoint_dir: str, instance: str, value: str) -> None:
    write_text_checkpoint(checkpoint_dir, _alerts_checkpoint_key(instance), value)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _build_initial_params(last_checked: str | None, alert_filter: str) -> dict[str, str]:
    now = datetime.datetime.utcnow()
    params: dict[str, str] = {
        "sort_direction": "asc",
        "sort_field": "last_modified",
    }
    if last_checked:
        last_dt = datetime.datetime.strptime(last_checked, "%Y-%m-%dT%H:%M:%SZ")
        min_d = last_dt + datetime.timedelta(seconds=1)
        params["last_modified_min_date"] = min_d.strftime("%Y-%m-%d %H:%M:%S")
        historic = now - datetime.timedelta(days=_LOOKBACK_INCREMENTAL_DAYS)
        params["min_timestamp"] = historic.isoformat()
    else:
        historic = now - datetime.timedelta(days=_LOOKBACK_INITIAL_DAYS)
        params["min_timestamp"] = historic.isoformat()
    if alert_filter == "escalated":
        params["escalated"] = "true"
    return params


def _sanitize_offending_url(url: str) -> str:
    """Strip the 'entity' query param that can contain PII."""
    parsed = urlsplit(url)
    filtered = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "entity"]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(filtered, doseq=True), parsed.fragment))


def _enrich_alert_logs(alert: dict[str, Any]) -> dict[str, Any]:
    """Promote takedown/escalation timestamps from the logs list to top-level fields."""
    for log in alert.get("logs") or []:
        if not log.get("timestamp"):
            continue
        dt = datetime.datetime.strptime(log["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        ts = (dt if dt.utcoffset() else dt.replace(tzinfo=datetime.timezone.utc)).isoformat()
        action = log.get("action", "")
        if action == "request takedown":
            alert["takedown_requestor"] = log.get("actor")
            alert["timestamp_takedown_requested"] = ts
        elif action == "accept takedown":
            alert["timestamp_takedown_accepted"] = ts
        elif action == "deny takedown":
            alert["timestamp_takedown_denied"] = ts
        elif action == "modify notes":
            alert["timestamp_modify_notes"] = ts
        elif action == "modify tags":
            alert["timestamp_modify_tags"] = ts
        elif action == "escalate":
            alert["timestamp_escalated"] = ts
        elif action == "review":
            alert["timestamp_reviewed"] = ts
        elif action == "require evidence takedown":
            alert["timestamp_takedown_evidence_required"] = ts
        elif action == "down on arrival takedown":
            alert["timestamp_takedown_down_on_arrival"] = ts
        elif action == "withdraw from review takedown":
            alert["timestamp_takedown_withdraw_from_review"] = ts
        elif action == "submit for review takedown":
            alert["timestamp_takedown_submit_from_review"] = ts
    return alert


def _parse_epoch(last_modified: str) -> float:
    dt = datetime.datetime.strptime(last_modified, "%Y-%m-%dT%H:%M:%S%z")
    return dt.timestamp()


# ---------------------------------------------------------------------------
# UCC entry points
# ---------------------------------------------------------------------------


def validate_input(definition: Any) -> None:
    params = getattr(definition, "parameters", None) or {}
    if not (params.get("account") or "").strip():
        raise ValueError("Account is required")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    bin_dir = Path(__file__).resolve().parent
    addon_name, account_conf, settings_conf = _ucc_conf_stanzas(bin_dir)
    session_key = inputs.metadata["session_key"]
    checkpoint_dir = str(inputs.metadata.get("checkpoint_dir") or "")
    proxies = build_proxies(session_key, addon_name, settings_conf)

    for input_name, input_item in inputs.inputs.items():
        p = {str(k): v for k, v in dict(input_item).items()}
        account_name = (p.get("account") or "").strip()
        if not account_name:
            event_writer.log(event_writer.ERROR, f"{input_name}: account is required")
            continue

        # Configure log level from settings if possible
        try:
            logger = __import__("logging").getLogger(__name__)
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=addon_name,
                conf_name=settings_conf,
            )
            logger.setLevel(log_level)
        except Exception:
            pass

        try:
            _username, api_token = _account_credentials(session_key, addon_name, account_conf, account_name)
        except Exception as err:
            event_writer.log(event_writer.ERROR, f"{input_name}: credential error: {err}")
            continue

        api_base = _API_BASE
        alert_filter = str(p.get("alert_filter") or "all").strip()
        stanza_str = str(input_name)

        # For checkpoint keying: use the instance part of "scheme://instance"
        # For legacy migration: use the bare stanza name (how AoB wrote it)
        if "://" in stanza_str:
            _, _, instance = stanza_str.partition("://")
            checkpoint_instance = instance or stanza_str
        else:
            checkpoint_instance = stanza_str

        last_checked = _get_last_checked(checkpoint_dir, checkpoint_instance, stanza_str)
        params: dict[str, str] | None = _build_initial_params(last_checked, alert_filter)

        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
            "zf-source": "Splunk",
        }

        url: str | None = f"{api_base}/1.0/alerts/"
        cnt = 0

        event_writer.log(
            event_writer.DEBUG,
            f"{input_name}: collecting alerts " f"(filter={alert_filter!r}, last_checked={last_checked!r})",
        )

        try:
            while url:
                if not url.startswith("https"):
                    event_writer.log(
                        event_writer.ERROR,
                        f'{input_name}: alert API URL must start with "https" — aborting.',
                    )
                    break

                resp = requests.get(url, params=params, headers=headers, proxies=proxies or None, timeout=60)
                if not resp.ok:
                    body_snippet = " ".join(resp.text[:300].split())
                    event_writer.log(
                        event_writer.ERROR,
                        f"{input_name}: HTTP {resp.status_code}: {body_snippet}",
                    )
                    resp.raise_for_status()

                body = resp.json()
                for alert in body.get("alerts") or []:
                    try:
                        # Parse metadata JSON string into a dict if present
                        if isinstance(alert.get("metadata"), str):
                            try:
                                alert["metadata"] = json.loads(alert["metadata"])
                            except (ValueError, TypeError):
                                pass

                        alert = _enrich_alert_logs(alert)

                        if offending := alert.get("offending_content_url"):
                            alert["offending_content_url"] = _sanitize_offending_url(offending)

                        epoch = _parse_epoch(alert["last_modified"])
                        ev = Event(
                            data=json.dumps(alert),
                            stanza=f"zerofox_alerts://{checkpoint_instance}",
                            source=f"zfox://{checkpoint_instance}",
                            time="%.3f" % epoch,
                            sourcetype=_SOURCETYPE,
                            index=p.get("index"),
                            done=True,
                        )
                        event_writer.write_event(ev)
                        _save_checkpoint(checkpoint_dir, checkpoint_instance, alert["last_modified"])
                        cnt += 1
                    except Exception as alert_err:
                        event_writer.log(
                            event_writer.ERROR,
                            f"{input_name}: error processing alert {alert.get('id')!r}: {alert_err}",
                        )

                next_url = body.get("next")
                url = next_url.replace("http://", "https://", 1) if next_url else None
                params = None  # params embedded in next URL; don't double-send

        except Exception as err:
            event_writer.log(event_writer.ERROR, f"{input_name}: collection failed: {err}")

        event_writer.log(event_writer.DEBUG, f"{input_name}: collected {cnt} alerts")
