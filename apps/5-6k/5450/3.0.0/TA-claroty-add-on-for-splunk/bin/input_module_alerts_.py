# encoding = utf-8
from utils.definitions import Filter, IntervalParams, InputFilterInfo
from utils.general_utils import get_assets_src_dest_ips, init_interval_params, run_interval, get_assets_src_dest_types, get_site_name_by_id
from constants import TYPE_QUERY_FILTER_KEY, LOOKUP_EXACT, SITES_FILTER_KEY, SITE_ID_QUERY_FILTER_ATTRIBUTE, API_ENDPOINTS, Sourcetype, ASSIGNED_TO_KEY, MITRE_TECHNIQUES_KEY, MITRE_ID_KEY, SITE_ID_KEY

ALERTS_QUERY_FILTERS = [
    Filter(name="is_qualified", lookup=LOOKUP_EXACT, values=["true"]),
    Filter(name="format", values=["alert_list"])
    ]
API_ENDPOINT = API_ENDPOINTS[Sourcetype.eAlerts]
ALERTS_INPUT_FILTERS_INFO = [
    InputFilterInfo(input_name=SITES_FILTER_KEY, filter_name=SITE_ID_QUERY_FILTER_ATTRIBUTE, lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="alert_severity", filter_name="severity", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="alert_category", filter_name="category", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="alert_status", filter_name="resolved", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="alert_type", filter_name=TYPE_QUERY_FILTER_KEY, lookup=LOOKUP_EXACT)
    ]


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    interval_params = init_interval_params(
        helper = helper,
        ew = ew,
        api_endpoint = API_ENDPOINT,
        query_filters = ALERTS_QUERY_FILTERS
        )
    run_interval(interval_params, ALERTS_INPUT_FILTERS_INFO, extend_alert)


def extend_alert(interval_params: IntervalParams, alert: dict, sites_ids_to_names_map: dict):
    src_ip, dest_ip = get_assets_src_dest_ips(alert)
    src_types, dest_types = get_assets_src_dest_types(alert)
    mitre_techniques = alert.get(MITRE_TECHNIQUES_KEY, [])
    alert["src"] = src_ip
    alert["dest"] = dest_ip
    alert["src_types"] = src_types
    alert["dest_types"] = dest_types
    alert["site_name"] = get_site_name_by_id(alert.get(SITE_ID_KEY), sites_ids_to_names_map)
    alert["mitre_technique_ids"] = [technique.get(MITRE_ID_KEY) for technique in mitre_techniques if technique.get(MITRE_ID_KEY) is not None]
    assigned_to = alert.get(ASSIGNED_TO_KEY)
    alert["assigned_to_user_id"] = assigned_to.get("user_id") if isinstance(assigned_to, dict) else None

    return alert
