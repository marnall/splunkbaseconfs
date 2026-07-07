# encoding = utf-8
from constants import SITE_ID_KEY, ALERT_ID_KEY, TYPE_QUERY_FILTER_KEY, LOOKUP_EXACT, SITES_FILTER_KEY, SITE_ID_QUERY_FILTER_ATTRIBUTE, API_ENDPOINTS, Sourcetype, QUERY_FILTER_MULTIPLE_VALUES_SEPARATOR
from utils.definitions import IntervalParams, InputFilterInfo
from utils.general_utils import send_request, get_assets_src_dest_ips, init_interval_params, run_interval, get_assets_src_dest_types, get_site_name_by_id

Alerts = {}
EVENTS_QUERY_FILTERS = []
API_ENDPOINT = API_ENDPOINTS[Sourcetype.eEvents]
ALERTS_API_ENDPOINT = API_ENDPOINTS[Sourcetype.eAlerts]

EVENTS_INPUT_FILTERS_INFO = [
    InputFilterInfo(input_name=SITES_FILTER_KEY, filter_name=SITE_ID_QUERY_FILTER_ATTRIBUTE, lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="event_type", filter_name=TYPE_QUERY_FILTER_KEY, lookup=LOOKUP_EXACT)
    ]

def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    Alerts.clear()
    interval_params = init_interval_params(
        helper = helper,
        ew = ew,
        api_endpoint = API_ENDPOINT,
        query_filters = EVENTS_QUERY_FILTERS
        )
    run_interval(interval_params, EVENTS_INPUT_FILTERS_INFO, get_related_alert_severity)


def get_related_alert_severity(interval_params: IntervalParams, event: dict, sites_ids_to_names_map: dict) -> dict:
    raw_alert_id = event.get(ALERT_ID_KEY)
    raw_site_id = event.get(SITE_ID_KEY)

    if raw_alert_id is None or raw_site_id is None:
        interval_params.helper.log_debug(f"Event is missing alert_id or site_id, skipping alert enrichment.")
        return event

    alert_id = f"{raw_alert_id}-{raw_site_id}"
    if not Alerts.get(alert_id):
        url = build_get_alert_severity_and_assets_url(interval_params, alert_id)
        res_as_json = send_request(url, interval_params)
        src_ips, dest_ips = get_assets_src_dest_ips(res_as_json)
        src_types, dest_types = get_assets_src_dest_types(res_as_json)
        Alerts[alert_id] = {
            "severity": res_as_json.get("severity"),
            "severity__": res_as_json.get("severity__"),
            "src": src_ips,
            "dest": dest_ips,
            "src_types": src_types,
            "dest_types": dest_types,
            "site_name": get_site_name_by_id(event.get(SITE_ID_KEY), sites_ids_to_names_map)
            }

    alert = Alerts.get(alert_id, {})
    event = {**event, **alert}

    return event


def build_get_alert_severity_and_assets_url(interval_params: IntervalParams, alert_id: str) -> str:
    return f"https://{interval_params.hostname}{ALERTS_API_ENDPOINT}/{alert_id}?fields=severity{QUERY_FILTER_MULTIPLE_VALUES_SEPARATOR}actionable_assets"
