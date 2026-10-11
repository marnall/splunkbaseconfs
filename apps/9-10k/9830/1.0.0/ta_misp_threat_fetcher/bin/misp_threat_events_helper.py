import json
import os
from datetime import datetime, timedelta

import import_declare_test
from solnlib import conf_manager, log
from solnlib.credentials import CredentialManager
from splunklib import modularinput as smi

from rest_client import (
    get_attributes, load_state, save_state,
    build_proxy_dict, test_connection, lean_attribute,
)

ADDON_NAME = "ta_misp_threat_fetcher"
LOG_LOCATION = None

SOURCETYPE_IOC = "MISP:IOC"
SOURCETYPE_ERROR = "MISP:Error"


def _get_log_location():
    global LOG_LOCATION
    if LOG_LOCATION is None:
        splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
        LOG_LOCATION = os.path.join(splunk_home, "var", "log", "splunk", "MISPThreatFetcher")
    return LOG_LOCATION


def _load_env_file():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        return env
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            env[key.strip()] = val.strip()
    return env


def _get_encrypted_fields(session_key, realm, user):
    try:
        mgr = CredentialManager(
            session_key=session_key,
            app=ADDON_NAME,
            owner="nobody",
            realm=realm,
        )
        return json.loads(mgr.get_password(user=user))
    except Exception:
        return {}


def _get_misp_config(session_key, input_name, input_item):
    encrypted = _get_encrypted_fields(
        session_key,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#data/inputs/misp_threat_events",
        user=input_name,
    )
    env = _load_env_file()
    return {
        "url": input_item.get("misp_url", ""),
        "api_key": encrypted.get("misp_api_key", ""),
        "verify_ssl": env.get("MISP_VERIFY_SSL", "false").lower() == "true",
        "page_size": int(env.get("MISP_PAGE_SIZE", "100")),
        "published_only": env.get("MISP_PUBLISHED_ONLY", "true").lower() == "true",
        "tag_filter": env.get("MISP_TAG_FILTER", ""),
    }


def _get_proxy_settings(session_key):
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME}_settings",
        )
        settings = cfm.get_conf(f"{ADDON_NAME}_settings")
        return settings.get("proxy", {})
    except Exception:
        return {}


def _write_error(ew, input_name, function, error):
    ew.write_event(smi.Event(
        data=json.dumps({
            "timestamp": datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            "function": function,
            "input_name": input_name,
            "error": str(error)
        }),
        index="_internal",
        sourcetype=SOURCETYPE_ERROR,
        source="MISP_Threat_Fetcher"
    ))


def validate_input(definition: smi.ValidationDefinition):
    params = definition.parameters
    days = int(params.get("historical_polling_days", 30))
    if days < 1 or days > 365:
        raise ValueError("historical_polling_days must be between 1 and 365")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_name = input_name.split("/")[-1]
        logger = log.Logs().get_logger(f"{ADDON_NAME}_{normalized_name}")

        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger, session_key=session_key,
                app_name=ADDON_NAME, conf_name=f"{ADDON_NAME}_settings",
            )
            logger.setLevel(log_level)

            misp_cfg = _get_misp_config(session_key, normalized_name, input_item)
            misp_url = misp_cfg["url"]
            api_key = misp_cfg["api_key"]
            verify_ssl = misp_cfg["verify_ssl"]
            page_size = misp_cfg["page_size"]
            published_only = misp_cfg["published_only"]
            tag_filter = misp_cfg["tag_filter"]

            if not misp_url:
                logger.error("MISP URL not set for input=%s", normalized_name)
                _write_error(event_writer, normalized_name, "config", "MISP URL not set")
                return

            if not api_key:
                logger.error("MISP API Key not set for input=%s", normalized_name)
                _write_error(event_writer, normalized_name, "config", "MISP API Key not set")
                return

            historical_days = int(input_item.get("historical_polling_days", 30))
            index = input_item.get("index", "default")

            if not verify_ssl:
                logger.warning("verify_ssl=disabled input=%s", normalized_name)

            headers = {
                "Authorization": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            proxy_dict = build_proxy_dict(_get_proxy_settings(session_key))
            log_location = _get_log_location()

            if not test_connection(logger, misp_url, headers, verify_ssl, proxy_dict):
                _write_error(event_writer, normalized_name, "test_connection", "MISP unreachable")
                return

            state = load_state(log_location, normalized_name, logger)
            seen_uuids = set(state.get("seen_uuids", [])) if state else set()
            page = 1
            end_ts = int(datetime.utcnow().timestamp())

            if state is None:
                start_ts = int((datetime.utcnow() - timedelta(days=historical_days)).timestamp())
                logger.info("First run, polling from %d", start_ts)
            elif state.get("isComplete") is False:
                start_ts = state["lastModStartTimestamp"]
                end_ts = state["lastModEndTimestamp"]
                page = state.get("currentPage", 1)
                logger.info("Resuming from page %d", page)
            else:
                start_ts = state["lastModEndTimestamp"]
                logger.info("Incremental poll from %d", start_ts)

            total_written = 0
            total_skipped = 0

            while True:
                result = get_attributes(
                    logger, misp_url, start_ts, end_ts, page, page_size,
                    headers, tag_filter, published_only, verify_ssl, proxy_dict
                )

                if isinstance(result, dict) and result.get("error"):
                    logger.error("API error: %s", result.get("reason"))
                    _write_error(event_writer, normalized_name, "get_attributes", result.get("reason"))
                    save_state({
                        "lastModStartTimestamp": start_ts,
                        "lastModEndTimestamp": end_ts,
                        "seen_uuids": list(seen_uuids)[-1000:],
                        "currentPage": page,
                        "isComplete": False
                    }, log_location, normalized_name, logger)
                    return

                attributes = result
                if not attributes:
                    break

                for attr in attributes:
                    attr_uuid = attr.get("uuid", "")
                    if attr_uuid in seen_uuids:
                        total_skipped += 1
                        continue

                    ioc = lean_attribute(attr)
                    event_writer.write_event(smi.Event(
                        data=json.dumps(ioc, ensure_ascii=False),
                        index=index,
                        sourcetype=SOURCETYPE_IOC,
                        source=normalized_name
                    ))
                    total_written += 1

                    if attr_uuid:
                        seen_uuids.add(attr_uuid)

                save_state({
                    "lastModStartTimestamp": start_ts,
                    "lastModEndTimestamp": end_ts,
                    "seen_uuids": list(seen_uuids)[-1000:],
                    "currentPage": page,
                    "isComplete": False
                }, log_location, normalized_name, logger)

                if len(attributes) < page_size:
                    break
                page += 1

            save_state({
                "lastModStartTimestamp": start_ts,
                "lastModEndTimestamp": end_ts,
                "seen_uuids": list(seen_uuids)[-1000:],
                "currentPage": 1,
                "isComplete": True
            }, log_location, normalized_name, logger)

            logger.info("Complete. Written=%d, Skipped=%d, Pages=%d",
                        total_written, total_skipped, page)

        except Exception as e:
            logger.error("Unhandled exception: %s", e)
            _write_error(event_writer, normalized_name, "stream_events", str(e))
