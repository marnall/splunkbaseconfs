import json
import logging
from datetime import datetime, timezone
from urllib import error, request

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi


ADDON_NAME = "cloudflare_status"
STATUS_URL = "https://www.cloudflarestatus.com/api/v2/status.json"
INCIDENTS_URL = "https://www.cloudflarestatus.com/api/v2/incidents.json"
USER_AGENT = "cloudflare-status-addon/1.0"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def fetch_json(logger: logging.Logger, url: str) -> dict:
    """Fetch JSON from the Cloudflare status API."""
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    logger.debug("Requesting Cloudflare data", extra={"url": url})
    with request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Unexpected response status {resp.status} from {url}")
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def build_status_event(payload: dict) -> dict:
    """Shape a concise event from the Cloudflare status payload."""
    status = payload.get("status") or {}
    page = payload.get("page") or {}
    return {
        "feed": "status",
        "status_indicator": status.get("indicator"),
        "status_description": status.get("description"),
        "page": {k: page.get(k) for k in ("id", "name", "url", "updated_at")},
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "raw": payload,
    }


def build_incident_events(payload: dict) -> list[dict]:
    """Flatten incidents list into individual events."""
    incidents = payload.get("incidents") or []
    events = []
    for inc in incidents:
        events.append(
            {
                "feed": "incidents",
                "id": inc.get("id"),
                "name": inc.get("name"),
                "status": inc.get("status"),
                "impact": inc.get("impact"),
                "shortlink": inc.get("shortlink"),
                "started_at": inc.get("started_at"),
                "updated_at": inc.get("updated_at"),
                "resolved_at": inc.get("resolved_at"),
                "raw": inc,
            }
        )
    return events


def validate_input(definition: smi.ValidationDefinition):
    feed = (definition.parameters.get("feed") or "status").lower()
    if feed not in {"status", "incidents"}:
        raise ValueError("Feed must be either 'status' or 'incidents'.")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="cloudflare_status_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            feed = (input_item.get("feed") or "status").lower()
            if feed == "incidents":
                payload = fetch_json(logger, INCIDENTS_URL)
                events = build_incident_events(payload)
                sourcetype = "cloudflare:incident"
            else:
                payload = fetch_json(logger, STATUS_URL)
                events = [build_status_event(payload)]
                sourcetype = "cloudflare:status"

            for event in events:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(event, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                    )
                )

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(events),
                input_item.get("index"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except error.URLError as err:
            log.log_exception(logger, err, "cloudflare_status_http_error", msg_before="HTTP error while fetching Cloudflare status: ")
        except Exception as e:
            log.log_exception(logger, e, "cloudflare_status_error", msg_before="Exception raised while ingesting Cloudflare status: ")
