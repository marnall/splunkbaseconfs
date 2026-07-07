# encoding = utf-8
from utils.definitions import InputFilterInfo, IntervalParams
from utils.general_utils import init_interval_params, run_interval, get_site_name_by_id
from constants import LOOKUP_EXACT, SITES_FILTER_KEY, SITE_ID_QUERY_FILTER_ATTRIBUTE, API_ENDPOINTS, Sourcetype, SITE_ID_KEY

BASELINES_QUERY_FILTERS = []
API_ENDPOINT = API_ENDPOINTS[Sourcetype.eBaselines]
ASSETS_API_ENDPOINT = API_ENDPOINTS[Sourcetype.eAssets]
BASELINES_INPUT_FILTERS_INFO = [
    InputFilterInfo(input_name=SITES_FILTER_KEY, filter_name=SITE_ID_QUERY_FILTER_ATTRIBUTE, lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="baseline_category", filter_name="category", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="baseline_protocol", filter_name="protocol", lookup=LOOKUP_EXACT)
    ]


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    interval_params = init_interval_params(
        helper = helper,
        ew = ew,
        api_endpoint = API_ENDPOINT,
        query_filters = BASELINES_QUERY_FILTERS
        )
    run_interval(interval_params, BASELINES_INPUT_FILTERS_INFO, extend_baseline)

def extend_baseline(interval_params: IntervalParams, baseline: dict, sites_ids_to_names_map: dict):
    baseline["site_name"] = get_site_name_by_id(baseline.get(SITE_ID_KEY), sites_ids_to_names_map)

    return baseline
