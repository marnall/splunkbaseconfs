import json
import re
import traceback
from urllib.parse import urlencode
import requests
from datetime import datetime, timezone
from utils import raise_web_message, get_proxy_kwargs, get_version, convert_ts, extract_path


def validate_input(helper, definition):
    '''Implement your own validation logic to validate the input stanza configurations'''
    pass


def adapt_breach_alert(breach_alert):
    victim = extract_path(breach_alert, "victims")[0]
    titan_breach_alert = {
        "activity": {
                "first": convert_ts(extract_path(breach_alert, "creation_ts")),
                "last": convert_ts(extract_path(breach_alert, "last_updated_ts")),
              },
        "last_updated": convert_ts(extract_path(breach_alert, "last_updated_ts")),
        "uid": extract_path(breach_alert, "id"),
        "data": {
                "breach_alert": {
                  "title": extract_path(breach_alert, "title"),
                  "summary":  extract_path(breach_alert, "body"),
                  "date_of_information": convert_ts(extract_path(breach_alert, "information_ts")),
                  "released_at": convert_ts(extract_path(breach_alert, "released_ts")),
                  "confidence": extract_path(breach_alert, "confidence"),
                  "actor_or_group": extract_path(breach_alert, "actor_or_group"),
                  "victim": {
                    "name": extract_path(victim, "name"),
                    "urls": [extract_path(url, "external.href") for url in extract_path(victim, "links")],
                    "industries": extract_path(victim, "industries"),
                    "revenue": extract_path(victim, "revenue"),
                    "region": extract_path(victim, "region"),
                    "country": extract_path(victim, "country"),
                  },
                  "sources": [
                    {
                      "type": source["type"],
                      "url": extract_path(source, "links.verity_portal.href"),
                      "title": source["title"],
                      "date": convert_ts(source["last_updated_ts"]),
                      "source_type": source["source_type"]
                    } for source in extract_path(breach_alert, "sources")
                  ],
                  "intel_requirements": [
                    gir["path"] for gir in extract_path(breach_alert, "classification.girs")
                  ]
                },
                "entities": extract_path(breach_alert, "entities"),
              }
    }
    return titan_breach_alert


def make_api_request(session, api_url):
    """Make API request and return parsed response."""
    resp = session.get(api_url)
    resp.raise_for_status()
    return resp.json()


def process_breach_alert(breach_alerts, helper,ew):
    """Process credentials and write events."""
    backend = helper.get_arg("backend")
    alert_count = 0
    for alert in breach_alerts:
        alert = adapt_breach_alert(alert) if backend == "verity" else alert
        alert_data = alert.get("data", {}).get("breach_alert", {})
        if alert_data:
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype="intel471:breachdata:source",
                data=json.dumps(alert),
            )
            ew.write_event(event)
            alert_count = 0
    return alert_count


def handle_api_error(e, helper):
    helper.log_warning(f'API request exception: {str(e)}')
    msg = "Intel 471 Breach Alerts Add-on Data input failed to connect to the API. " \
          "This could be either due to use of invalid credentials in Add-on Configuration " \
          f"or connectivity issues. {str(e)}"
    raise_web_message(helper, msg)


def handle_general_error(e, helper):
    helper.log_error(f'Collecting events failed: {str(e)}')
    helper.log_error(traceback.format_exc())
    raise_web_message(helper, "Intel 471 Breach Alerts Add-on Data input failed. "
                              "Refer to the logs for more details")


def parse_created_after_date(helper, created_after_arg, checkpoint_key):
    """Parse and validate the created_after date parameter."""
    created_after = helper.get_check_point(checkpoint_key)
    if not created_after:
        created_after = (created_after_arg or "").strip()
        if re.match(r"^\d{13}$", created_after):
            created_after = int(created_after)
        else:
            created_after = int(datetime.now(timezone.utc).timestamp() * 1000)
        helper.save_check_point(checkpoint_key, created_after)

    helper.log_info("Starting collection of Breach Alerts from "
                    f"{datetime.fromtimestamp(created_after / 1000).isoformat()} ({created_after}).")
    return created_after


def setup_session(global_account, proxy_settings):
    """Setup authenticated session with proxy configuration."""
    session = requests.Session()
    session.proxies.update(get_proxy_kwargs(proxy_settings))
    session.auth = (global_account["username"], global_account["password"])
    return session


def collect_events(helper, ew):
    helper.set_log_level(helper.get_log_level())
    backend = helper.get_arg("backend")
    if backend == "verity":
        alert_count, request_count =collect_events_verity(helper, ew)
    else:
        alert_count, request_count =collect_events_titan(helper, ew)
    helper.log_info(f'Collected {alert_count} breach alerts using {request_count} API calls.')


def collect_events_verity(helper, ew):
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    account_name = input_stanza[input_name]['global_account']['name']
    CHECKPOINT_CURSOR_KEY = f'i471_breach_alerts_cursor_{input_name}_{account_name}verity'
    CHECKPOINT_INITIAL_DATE=f'i471_breach_alerts_initial_date_{input_name}_{account_name}verity'

    # Get API configuration
    base_url = "https://api.intel471.cloud/integrations/intel-report/v1/reports/breach-alert/stream"
    headers = {"User-agent": f"Intel 471 - Breach Alerts - Splunk App {get_version()}"}

    global_account = helper.get_arg('global_account')
    session = setup_session(global_account, helper.get_proxy())
    session.headers = headers

    cursor = helper.get_check_point(CHECKPOINT_CURSOR_KEY)
    if cursor:
        helper.log_info("Starting from cursor stored in checkpoint")
        api_query = {"cursor": cursor, "size": 1000}
    else:
        helper.log_info("Starting from initial timestamp")
        created_after = parse_created_after_date(helper, helper.get_arg("created_after"), CHECKPOINT_INITIAL_DATE)
        api_query = {"from": created_after, "size": 1000}

    helper.log_debug(f"source: '{helper.get_input_type()}' index: '{helper.get_output_index()}'")

    alert_count = 0
    request_count = 0
    while True:
        try:
            if cursor:
                api_query["cursor"] = cursor
                api_query.pop("from", None)
            api_url = f"{base_url}?{urlencode(api_query)}"
            helper.log_debug(f"API URL is {api_url}.")
            resp = session.get(api_url)
            request_count += 1
            resp.raise_for_status()
            alerts = resp.json().get("reports", [])
            if len(alerts) == 0:
                helper.log_debug("No alerts for given query.")
                break
            helper.log_debug(f"Got {len(alerts)} alerts for given query.")
            cursor = resp.json().get("cursor_next")
            helper.log_debug(f"Saving the cursor value {cursor} to the Splunk KV store.")
            helper.save_check_point(CHECKPOINT_CURSOR_KEY, cursor)
            for alert in alerts:
                alert_id = alert.get("id", {})
                if alert_id:
                    alert=adapt_breach_alert(alert)
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype="intel471:breachdata:source",
                        data=json.dumps(alert),
                    )
                    ew.write_event(event)
                    alert_count += 1
            break
        except requests.RequestException as e:
            handle_api_error(e, helper)
            break
        except Exception as e:
            handle_general_error(e, helper)
            break
    return alert_count, request_count


def collect_events_titan(helper, ew):
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    account_name = input_stanza[input_name]['global_account']['name']
    CHECKPOINT_CURSOR_KEY = f'i471_breach_alerts_cursor_{input_name}_{account_name}'
    checkpoint_value = helper.get_check_point(CHECKPOINT_CURSOR_KEY)
    if checkpoint_value:
        helper.log_info("Starting from timestamp stored in checkpoint")
        cursor = checkpoint_value
    else:
        helper.log_info("Starting from initial timestamp")
        created_after = (helper.get_arg("created_after") or "").strip()
        if re.match(r"^\d{13}$", created_after):
            cursor = int(created_after)
        else:
            cursor = int(datetime.now().timestamp()) * 1000
    helper.log_info("Starting collection of Breach Alerts from "
                    f"{datetime.fromtimestamp(cursor/1000).isoformat()} ({cursor}).")
    helper.log_debug(f"source: '{helper.get_input_type()}' index: '{helper.get_output_index()}'")
    base_url = "https://api.intel471.com/v1/breachAlerts"
    global_account = helper.get_arg("global_account")
    session = requests.Session()
    session.headers = {"User-agent": f"Intel 471 - Breach Alerts - Splunk App {get_version()}"}
    session.proxies.update(get_proxy_kwargs(helper.get_proxy()))
    session.auth = (global_account["username"], global_account["password"])
    alert_count = 0
    request_count = 0
    while True:
        try:
            api_query = {"breachAlert": "*", "from": cursor, "count": 100, "sort": "earliest"}
            api_url = f"{base_url}?{urlencode(api_query)}"
            helper.log_debug(f"API URL is {api_url}.")
            resp = session.get(api_url)
            request_count += 1
            resp.raise_for_status()
            alerts = resp.json().get("breach_alerts", [])
            if len(alerts) == 0:
                helper.log_debug("No alerts for given query.")
                break
            helper.log_debug(f"Got {len(alerts)} alerts for given query.")
            cursor = alerts[-1]["activity"]["first"] + 1
            helper.log_debug(f"Saving the cursor value {cursor} to the Splunk KV store.")
            helper.save_check_point(CHECKPOINT_CURSOR_KEY, cursor)
            for alert in alerts:
                alert_data = alert.get("data", {}).get("breach_alert", {})
                if alert_data:
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype="intel471:breachdata:source",
                        data=json.dumps(alert),
                    )
                    ew.write_event(event)
                    alert_count += 1
        except requests.RequestException as e:
            handle_api_error(e, helper)
            break
        except Exception as e:
            handle_general_error(e, helper)
            break
    return alert_count, request_count

