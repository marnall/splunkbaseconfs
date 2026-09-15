# encoding = utf-8
"""Invicti Platform — vulnerabilities modular input.

Pulls `/api/inventory/v1/vulnerabilities` page by page and writes each
vulnerability JSON object as a separate Splunk event. A per-stanza
checkpoint stores the most recent `lastSeen` timestamp seen so far, and is
used as `lastSeen=<value>&lastSeenOperator=after` on subsequent runs.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

import import_declare_test  # noqa: F401  -- must be first; sets up sys.path

from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi


ADDON_NAME = "TA-invicti-platform"
INPUT_NAME = "invicti_vulnerabilities"
ACCOUNT_CONF = "ta_invicti_platform_account"
SETTINGS_CONF = "ta_invicti_platform_settings"

# Match the Invicti Platform API contract.
VULN_PATH = "/api/inventory/v1/vulnerabilities"
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
HTTP_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5

# Conservative cap so a single run cannot loop indefinitely on a runaway API.
MAX_PAGES_PER_RUN = 1000


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _logger(session_key: str, input_name: str):
    """Return a logger configured with the user-selected log level."""
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{SETTINGS_CONF}",
        )
        loglevel = (
            cfm.get_conf(SETTINGS_CONF)
            .get("logging")
            .get("loglevel", "INFO")
        )
    except Exception:
        loglevel = "INFO"
    logger = log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")
    log.Logs().set_level(loglevel)
    return logger


def _get_account(session_key: str, account_name: str) -> Dict[str, str]:
    """Read the selected account stanza, including the decrypted api_token."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ACCOUNT_CONF}",
    )
    account_conf = cfm.get_conf(ACCOUNT_CONF).get(account_name)
    return {
        "base_url": (account_conf.get("base_url") or "https://platform.invicti.com").rstrip("/"),
        "api_token": account_conf.get("api_token") or "",
    }


def _get_proxy(session_key: str) -> Optional[Dict[str, str]]:
    """Build a `requests`-style proxies dict if proxy is enabled, else None."""
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{SETTINGS_CONF}",
        )
        proxy = cfm.get_conf(SETTINGS_CONF).get("proxy", {})
    except Exception:
        return None

    enabled = str(proxy.get("proxy_enabled", "0")).lower() in ("1", "true")
    if not enabled:
        return None
    host = proxy.get("proxy_url")
    port = proxy.get("proxy_port")
    if not host or not port:
        return None
    scheme = proxy.get("proxy_type", "http")
    user = proxy.get("proxy_username")
    pwd = proxy.get("proxy_password")
    auth = f"{user}:{pwd}@" if user else ""
    proxy_url = f"{scheme}://{auth}{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def _build_query(
    page_size: int,
    page_number: int,
    last_seen: Optional[str],
    asset_id: Optional[str],
    origin_id: Optional[str],
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "pageSize": page_size,
        "pageNumber": page_number,
    }
    if last_seen:
        params["lastSeen"] = last_seen
        params["lastSeenOperator"] = "after"
    if asset_id:
        params["assetId"] = asset_id
    if origin_id:
        params["originId"] = origin_id
    return params


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    # API returns ISO-8601 with trailing Z, e.g. 2026-03-18T11:36:24.268412Z
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# HTTP                                                                        #
# --------------------------------------------------------------------------- #
def _request_page(
    session,  # requests.Session
    url: str,
    params: Dict[str, Any],
    headers: Dict[str, str],
    proxies: Optional[Dict[str, str]],
    logger,
    run_id: str,
) -> Dict[str, Any]:
    """GET one page with simple exponential-style backoff for 429/5xx."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                url,
                params=params,
                headers=headers,
                timeout=HTTP_TIMEOUT,
                proxies=proxies,
            )
        except Exception as exc:  # network error, connection reset, etc.
            last_exc = exc
            logger.warning(
                "PROCID=%s | MsgID=HTTP_NET_ERROR | Attempt=%d | Err=%s",
                run_id, attempt, exc,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
            retry_after = int(resp.headers.get("Retry-After", "0") or 0)
            sleep_for = max(retry_after, RETRY_BACKOFF_SECONDS * attempt)
            logger.warning(
                "PROCID=%s | MsgID=HTTP_RETRYABLE | Status=%d | Sleep=%ds | Attempt=%d",
                run_id, resp.status_code, sleep_for, attempt,
            )
            time.sleep(sleep_for)
            continue

        # Non-retryable, surface the error with body for diagnostics.
        body = resp.text[:500] if resp.text else ""
        raise RuntimeError(
            f"Invicti API error status={resp.status_code} body={body!r}"
        )

    raise RuntimeError(f"Invicti API request failed after retries: {last_exc!r}")


# --------------------------------------------------------------------------- #
# Modular input                                                               #
# --------------------------------------------------------------------------- #
class InvictiVulnerabilities(smi.Script):
    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("Invicti Vulnerabilities")
        scheme.description = "Pulls vulnerabilities from the Invicti Platform Inventory API."
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.streaming_mode_xml = True

        for arg_name in ("account", "asset_id", "origin_id", "page_size"):
            arg = smi.Argument(
                name=arg_name,
                data_type=smi.Argument.data_type_string,
                required_on_create=arg_name == "account",
                required_on_edit=False,
            )
            scheme.add_argument(arg)
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition) -> None:
        page_size = definition.parameters.get("page_size") or DEFAULT_PAGE_SIZE
        try:
            ps = int(page_size)
        except (TypeError, ValueError):
            raise ValueError("page_size must be an integer.")
        if ps < 1 or ps > MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

    def stream_events(
        self, inputs: smi.InputDefinition, ew: smi.EventWriter
    ) -> None:
        # Lazy import so import_declare_test can adjust sys.path first.
        import requests

        session_key = self._input_definition.metadata["session_key"]

        for full_stanza, params in inputs.inputs.items():
            # full_stanza looks like "invicti_vulnerabilities://my_input"
            input_name = full_stanza.split("://", 1)[1] if "://" in full_stanza else full_stanza
            logger = _logger(session_key, input_name)
            run_id = str(uuid.uuid4())

            try:
                logger.info(
                    "PROCID=%s | MsgID=BEGIN | Input=%s", run_id, input_name,
                )

                # Resolve account + settings.
                account_name = params.get("account")
                if not account_name:
                    raise ValueError("Input is missing the 'account' field.")
                account = _get_account(session_key, account_name)
                if not account["api_token"]:
                    raise ValueError(
                        f"Account '{account_name}' has no API token configured."
                    )

                proxies = _get_proxy(session_key)

                page_size = int(params.get("page_size") or DEFAULT_PAGE_SIZE)
                asset_id = (params.get("asset_id") or "").strip() or None
                origin_id = (params.get("origin_id") or "").strip() or None
                index = params.get("index") or "default"
                sourcetype = "invicti:platform:vulnerability"
                source = f"invicti_vulnerabilities://{input_name}"

                # Per-input checkpoint (KV file under $SPLUNK_HOME/var/lib/splunk/modinputs).
                ckpt = checkpointer.KVStoreCheckpointer(
                    f"{ADDON_NAME.lower()}_{INPUT_NAME}_ckpt",
                    session_key,
                    ADDON_NAME,
                )
                state = ckpt.get(input_name) or {}
                last_seen: Optional[str] = state.get("last_seen")

                logger.info(
                    "PROCID=%s | MsgID=INITVARS | BaseUrl=%s | LastSeen=%s | "
                    "PageSize=%d | AssetId=%s | OriginId=%s",
                    run_id, account["base_url"], last_seen,
                    page_size, asset_id, origin_id,
                )

                http = requests.Session()
                headers = {
                    "Accept": "application/json",
                    "X-Auth": account["api_token"],
                    "User-Agent": f"{ADDON_NAME}/1.0.0",
                }
                url = account["base_url"] + VULN_PATH

                # Tracks the maximum lastSeen we observe in this run.
                max_seen_dt: Optional[datetime] = _parse_iso(last_seen)
                max_seen_str: Optional[str] = last_seen

                page_number = 1
                total_events = 0

                while page_number <= MAX_PAGES_PER_RUN:
                    query = _build_query(
                        page_size, page_number, last_seen, asset_id, origin_id,
                    )
                    logger.debug(
                        "PROCID=%s | MsgID=REQUEST | Page=%d | Query=%s",
                        run_id, page_number, query,
                    )
                    payload = _request_page(
                        http, url, query, headers, proxies, logger, run_id,
                    )

                    items: Iterable[Dict[str, Any]] = payload.get("items") or []
                    page_info = payload.get("pageInfo") or {}
                    total_pages = int(page_info.get("totalPages") or 0)

                    for item in items:
                        try:
                            ts = item.get("lastSeen")
                            ts_dt = _parse_iso(ts)
                            if ts_dt and (max_seen_dt is None or ts_dt > max_seen_dt):
                                max_seen_dt = ts_dt
                                max_seen_str = ts

                            event = smi.Event(
                                data=json.dumps(item, ensure_ascii=False),
                                index=index,
                                source=source,
                                sourcetype=sourcetype,
                                time=ts_dt.timestamp() if ts_dt else None,
                            )
                            ew.write_event(event)
                            total_events += 1
                        except Exception:
                            logger.error(
                                "PROCID=%s | MsgID=EVENT_WRITE_ERROR | Trace=%s",
                                run_id, traceback.format_exc(),
                            )

                    # Stop when we've drained the current snapshot.
                    if not items or (total_pages and page_number >= total_pages):
                        break
                    page_number += 1

                # Persist new checkpoint only if we observed something newer.
                if max_seen_str and max_seen_str != last_seen:
                    ckpt.update(input_name, {"last_seen": max_seen_str})
                    logger.info(
                        "PROCID=%s | MsgID=CHECKPOINT | LastSeen=%s",
                        run_id, max_seen_str,
                    )

                logger.info(
                    "PROCID=%s | MsgID=END | Pages=%d | Events=%d",
                    run_id, page_number, total_events,
                )

            except Exception as exc:
                logger.error(
                    "PROCID=%s | MsgID=GENERAL_ERROR | Input=%s | Err=%s | Trace=%s",
                    run_id, input_name, exc, traceback.format_exc(),
                )


if __name__ == "__main__":
    sys.exit(InvictiVulnerabilities().run(sys.argv))
