# encoding = utf-8
from constants import SITES_FILTER_KEY, SITE_ID_QUERY_FILTER_ATTRIBUTE, LOOKUP_EXACT, API_ENDPOINTS, Sourcetype
from utils.definitions import Filter, InputFilterInfo
from utils.general_utils import init_interval_params, run_interval

ASSETS_QUERY_FILTERS = [
    Filter(name="valid", lookup="exact", values=["true"]),
    Filter(name="special_hint", lookup="exact", values=["0"]),
    Filter(name="ghost", lookup="exact", values=["false"]),
    Filter(name="format", values=["asset_list"])
    ]
API_ENDPOINT = API_ENDPOINTS[Sourcetype.eAssets]
ASSETS_INPUT_FILTERS_INFO = [
    InputFilterInfo(input_name=SITES_FILTER_KEY, filter_name=SITE_ID_QUERY_FILTER_ATTRIBUTE, lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="asset_class", filter_name="class_type", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="asset_type", filter_name="asset_type", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="asset_criticality", filter_name="criticality", lookup=LOOKUP_EXACT),
    InputFilterInfo(input_name="asset_vendor", filter_name="vendor", lookup=LOOKUP_EXACT),
]


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    interval_params = init_interval_params(
        helper = helper,
        ew = ew,
        api_endpoint = API_ENDPOINT,
        query_filters = ASSETS_QUERY_FILTERS
        )
    
    run_interval(interval_params, ASSETS_INPUT_FILTERS_INFO)
