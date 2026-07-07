import os
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple, Union
import pickle
from uuid import UUID
import urllib3
from pathlib import Path
import shutil
import filecmp
import math
import requests
from enum import Enum
from dataclasses import dataclass
from urllib.parse import quote_plus
from requests import Response, Request, PreparedRequest, Session
import re
import string
from dynatrace_types_37 import *

# from dynatrace_types import *
import json
import certifi
from string import Formatter

# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""util.py: This module contains utility functions for the package. These functions are used by the package's scripts.

    Functions:
        get_dynatrace_tenant: Get the Dynatrace tenant from the input.
        get_dynatrace_api_token: Get the Dynatrace API token from the input.
        get_dynatrace_collection_interval: Get the Dynatrace collection interval from the input.
        get_dynatrace_entity_cursor: Get the Dynatrace entity cursor from the input.
        get_dynatrace_entity_end"""

__author__ = "David Connett"
__version__ = "2.1.6"
__maintainer__ = "David Connett"
__email__ = "dconnett@splunk.com"
__status__ = "Development"
__license__ = "Splunk General Terms"

script_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(script_dir)

dynatrace_managed_uri_v2 = "https://{your-domain}/e/{your-environment-id}/api/v2"
dynatrace_saas_uri_v2 = "https://{your-enviroment-id}.live.dynatrace.com/api/v2"
dynatrace_environment_active_gate_v2 = (
    "https://{your-domain}/e/{your-environment-id}/api/v2"
)


@dataclass
class EndpointInfo:
    url: URL
    selector: ResponseSelector
    params: Optional[Params]
    url_path_param: Optional[PathParam]
    extra_params: Optional[List[str]] = None


class Endpoint(Enum):
    METRICS = EndpointInfo(
        URL("/api/v2/metrics"),
        ResponseSelector("metrics"),
        Params({"writtenSince": "{time}", "fields": "unit,aggregationTypes"}),
        None,
    )
    METRICS_QUERY = EndpointInfo(
        URL("/api/v2/metrics/query"),
        ResponseSelector("result"),
        Params({"from": "{time}", "metricSelector": "{metricSelector}"}),
        None,
    )
    METRIC_DESCRIPTORS = EndpointInfo(
        URL("/api/v2/metrics/{metricKey}"),
        ResponseSelector("metricId"),
        None,
        PathParam("metricKey"),
    )
    ENTITIES = EndpointInfo(
        URL("/api/v2/entities"),
        ResponseSelector("entities"),
        Params({"entitySelector": 'type("{entitySelector}")', "from": "{time}"}),
        None,
        [
            "HOST",
            "PROCESS_GROUP_INSTANCE",
            "PROCESS_GROUP",
            "APPLICATION",
            "SERVICE",
            "SYNTHETIC_TEST",
            "SYNTHETIC_TEST_STEP",
            "KUBERNETES_CLUSTER",
            "KUBERNETES_NODE",
            "CLOUD_APPLICATION_NAMESPACE",
            "CLOUD_APPLICATION",
            "CLOUD_APPLICATION_INSTANCE",
            "CONTAINER_GROUP_INSTANCE",
        ],
    )
    ENTITY = EndpointInfo(
        URL("/api/v2/entities/{entityId}"),
        ResponseSelector("entityId"),
        Params({"from": "{time}"}),
        PathParam("entityId"),
    )
    ENTITY_TYPES = EndpointInfo(
        URL("/api/v2/entityTypes/{entityType}"), None, None, PathParam("entityType")
    )
    ENTITY_TYPES_LIST = EndpointInfo(
        URL("/api/v2/entityTypes"),
        ResponseSelector("types"),
        None,
        None,
    )
    PROBLEM = EndpointInfo(
        URL("/api/v2/problems/{problemId}"),
        ResponseSelector("problemId"),
        None,
        PathParam("problemId"),
    )
    PROBLEMS = EndpointInfo(
        URL("/api/v2/problems"),
        ResponseSelector("problems"),
        Params({"from": "{time}"}),
        None,
    )
    EVENTS = EndpointInfo(
        URL("/api/v2/events"),
        ResponseSelector("events"),
        Params({"from": "{time}"}),
        None,
    )
    SYNTHETIC_LOCATIONS = EndpointInfo(
        URL("/api/v2/synthetic/locations"), ResponseSelector("locations"), None, None
    )
    SYNTHETIC_TESTS_ON_DEMAND = EndpointInfo(
        URL("/api/v2/synthetic/executions"),
        ResponseSelector("executions"),
        Params({"schedulingFrom": "{time}"}),
        None,
    )
    SYNTHETIC_TEST_ON_DEMAND = EndpointInfo(
        URL("/api/v2/synthetic/executions/{executionId}/fullReport"),
        ResponseSelector("entityId"),
        None,
        PathParam("executionId"),
    )
    SYNTHETIC_MONITORS_HTTP = EndpointInfo(
        URL("/api/v1/synthetic/monitors"), ResponseSelector("monitors"), None, None
    )
    SYNTHETIC_MONITOR_HTTP = EndpointInfo(
        URL("/api/v1/synthetic/monitors/{entityId}"),
        ResponseSelector("entityId"),
        None,
        PathParam("entityId"),
    )
    SYNTHETIC_MONITOR_HTTP_V2 = EndpointInfo(
        URL("/api/v2/synthetic/execution/{monitorId}"),
        ResponseSelector("monitorId"),
        None,
        PathParam("monitorId"),
        ["SUCCESS", "FAILED"],
    )
    # This is a hack because SYNTHETIC_MONITORS_HTTP returns entityIds and others return monitorIds
    SYNTHETIC_MONITOR_ENTITY_V2 = EndpointInfo(
        URL("/api/v2/synthetic/execution/{entityId}"),
        ResponseSelector("entityId"),
        None,
        PathParam("entityId"),
        ["SUCCESS", "FAILED"],
    )
    SYNTHETIC_TESTS_RESULTS = EndpointInfo(
        URL("/api/v2/synthetic/tests/results"), ResponseSelector("results"), None, None
    )

    @property
    def url(self):
        return self.value.url if isinstance(self.value, EndpointInfo) else self.value

    @property
    def selector(self):
        return self.value.selector if isinstance(self.value, EndpointInfo) else None

    @property
    def params(self):
        return self.value.params if isinstance(self.value, EndpointInfo) else None

    @property
    def url_path_param(self):
        return (
            self.value.url_path_param if isinstance(self.value, EndpointInfo) else None
        )

    @property
    def extra_params(self):
        return self.value.extra_params

    @classmethod
    def get_endpoint(cls, endpoint_value):
        try:
            return cls[endpoint_value]
        except KeyError:
            return None


def get_current_working_directory():
    """Get the current working directory.

    Returns:
        str: Current working directory.
    """
    return os.getcwd()


def get_dynatrace_managed_uri(domain, environment_id):
    """Create a managed URI given the domain and environment ID.

    Args:
        domain (str): Dynatrace domain.
        environment_id (str): Dynatrace environment ID.

    Returns:
        str: Managed URI.
    """
    return dynatrace_managed_uri_v2.format(
        your_domain=domain, your_environment_id=environment_id
    )


def get_dynatrace_saas_uri(environment_id):
    """Create a SaaS URI given the environment ID.

    Args:
        environment_id (str): Dynatrace environment ID.

    Returns:
        str: SaaS URI.
    """
    return dynatrace_saas_uri_v2.format(your_environment_id=environment_id)


def get_dynatrace_environment_active_gate_uri(domain, environment_id):
    """Create an environment active gate URI given the domain and environment ID.

    Args:
        domain (str): Dynatrace domain.
        environment_id (str): Dynatrace environment ID.

    Returns:
        str: Environment active gate URI.
    """
    return dynatrace_environment_active_gate_v2.format(
        your_domain=domain, your_environment_id=environment_id
    )


def endpoint_enum_lookup(url: str) -> Optional[EndpointInfo]:
    """Match a URL to an EndpointInfo object."""
    for endpoint in Endpoint:
        endpoint_url_regex = re.escape(endpoint.value.url).replace(r"\{id\}", r"[^/]+")
        # Ensure endpoint.url is at the end of url
        endpoint_url_regex = r".*{}$".format(endpoint_url_regex)
        if re.search(endpoint_url_regex, url):
            return Optional[endpoint]
    return None


def parse_url(url):
    if not url.startswith("https://"):
        if url.startswith("http://"):
            return url.replace("http://", "https://")
        else:
            return "https://" + url
    return url


# Parse secrets.env file
def parse_secrets_env():
    """Parse the secrets.env file. Only used for testing, and running the scripts locally.

    Returns:
        dict: Dictionary of secrets from the secrets.env file.
    """
    # Create the secrets dictionary
    secrets = {}
    print("Current working dir:", get_current_working_directory())
    # Check if the secrets.env file exists
    # Get the path to the current script

    # Construct a path relative to the script directory
    secrets_file = os.path.join(package_dir, "secrets.env")
    print("Secrets file:", secrets_file)
    if os.path.exists(secrets_file):
        with open(secrets_file) as f:
            for line in f:
                if not line.startswith("#"):
                    (key, val) = line.split("=")
                    secrets[key] = val.strip()
    return secrets


# Get dynatrace Problems from apiv2
# https://www.dynatrace.com/support/help/dynatrace-api/environment-api/problems/problems-get/


def default_time() -> WrittenSinceParam:
    written_since = (datetime.now() - timedelta(minutes=1)).timestamp()
    last_hour: WrittenSinceParam = WrittenSinceParam(
        {"written_since": f"{written_since}"}
    )
    return last_hour


def get_from_time(minutes: CollectionInterval = 60) -> int:
    """Calculate unix stamp n minutes ago. Return unix epoch time in milliseconds with no decimals"""
    from_time_float = (datetime.now() - timedelta(minutes=minutes)).timestamp()

    # Round to nearest millisecond
    from_time: int = math.floor(from_time_float * 1000)

    # Return the time
    return from_time


def calculate_utc_start_timestamp(minutes: Optional[int] = 60) -> StartTime:
    """Calculate unix timestamp n minutes ago in UTC"""
    now: datetime = datetime.utcnow()
    time_range: timedelta = timedelta(minutes=minutes)
    start_time: datetime = now - time_range
    timestamp: StartTime = StartTime(math.floor(start_time.timestamp() * 1000))

    return timestamp


def get_from_time_utc(minutes: Optional[int] = 60) -> int:
    """Calculate unix stamp n minutes ago in UTC. Return unix epoch time in milliseconds with no decimals"""
    from_time = calculate_utc_start_timestamp(minutes)

    # Return the time
    return from_time


def default_time_utc_written_since() -> WrittenSinceParam:
    """Return the current time in UTC minus 1 hour
    in unix epoch time in milliseconds with no decimals with the key written_since.
    This is for certain endpoints that require a time parameter in UTC"""
    last_hour: StartTime = calculate_utc_start_timestamp(60)
    written_since = WrittenSinceParam({"written_since": f"{last_hour}"})
    return written_since


def create_session(tenant, api_token, verify=True) -> requests.Session:
    session = requests.Session()
    session.verify = verify
    session.headers = {"Authorization": f"Api-Token {api_token}"}
    session.base_url = tenant
    return session


def find_format_key(value: str) -> Optional[str]:
    """Find the key to be formatted from a given string value."""
    format_keys = [tup[1] for tup in Formatter().parse(value) if tup[1] is not None]
    return format_keys[0] if format_keys else None


def get_formatted_key_value_pair(
    key: str, value: str, params: Params
) -> Tuple[str, Any]:
    """Return the key-value pair after formatting."""
    replaced_key = find_format_key(value)
    if replaced_key and replaced_key in params:
        formatted_value = value.format(**{replaced_key: params[replaced_key]})
        return key, formatted_value
    return key, value


def format_url_and_pop_path_params(
    endpoint: Endpoint, url: URL, params: Params
) -> Tuple[URL, Params]:
    """Format the URL and pop the URL Path parameter from the params dictionary."""
    # print('format_url_and_pop_path_params: {}'.format(endpoint)
    #         + ' url: {}'.format(url)
    #         + ' params: {}'.format(params))
    if endpoint.url_path_param:
        endpoint_path_key = endpoint.url_path_param
        if endpoint_path_key in params:
            formatted_url = URL(
                url.format(**{endpoint_path_key: params[endpoint_path_key]})
            )
            new_params = Params(
                {k: v for k, v in params.items() if k != endpoint_path_key}
            )
            # print('format_url_and_pop_path_params: {}'.format(formatted_url)
            #         + ' new_params: {}'.format(new_params))
            return formatted_url, new_params
    return url, params


def format_params(endpoint: Endpoint, params: Params) -> Params:
    """Format and inject parameters according to the Endpoint Enum.
    Injects default parameters from V2Endpoints Enum,
                Params Input: {}
                -> {'fields': 'unit,aggregationTypes'} for METRICS,
    Formats default parameters from V2Endpoints Enum (if it exists)
                Params Input: {'entitySelector': 'HOST'}
                V2Endpoint Input: {'entitySelector': 'type(\"{entitySelector}\")'}
                -> {'entitySelector': 'type('HOST')'},
    Renames parameters with the same meaning from the V2Endpoints Enum,
                Params Input: {'time': 1234}
                V2Endpoints Input: {'writtenSince': '{time}'}
                 -> {'writtenSince': '1234'}

    Why? Different API endpoints need specific inputs, but many are actually the same data and just need to be renamed,
    or some endpoints always need the same inputs all the time.

    Cleaner idea: defining functions or classes for each endpoint would probably be a better idea,
    but this design was chosen because of the evolution of the code over time. This is a hack, but it works... for now.

    Important to know:
        1. If you pass a parameter that changes names, the old one will be removed {time} -> {writtenSince}
        2. Parameters that have a format string will be formatted with the input params of the same key name
            {'entitySelector': 'HOST'}
            {'entitySelector': 'type(\"{entitySelector}\")'}
                -> {'entitySelector': 'type(\"HOST\")'}

    """
    formatted_params = params.copy()
    if endpoint.params:
        for key, value in endpoint.params.items():
            # If the value contains a format string
            if "{" in value:
                format_key = find_format_key(value)
                if format_key and format_key in formatted_params:
                    new_key, new_value = get_formatted_key_value_pair(
                        key, value, formatted_params
                    )
                    formatted_params[new_key] = new_value
                    # If the key has changed, remove the original key
                    if new_key != key:
                        formatted_params.pop(key)
                    # If the formatted value uses a parameter, consume that parameter
                    if format_key != key:
                        formatted_params.pop(format_key)
            else:
                formatted_params[key] = value
    return Params(formatted_params)


def build_url(endpoint: Endpoint, tenant: Tenant, params: Params) -> URL:
    url = URL(tenant + endpoint.url)
    url, params = format_url_and_pop_path_params(endpoint, url, params)
    return URL(url)


def prepare_dynatrace_headers(api_token, extra_headers=None):
    headers = {
        "Authorization": f"Api-Token {api_token}",
        "version": f"Splunk_TA_Dynatrace {__version__}",
    }
    return {**headers, **extra_headers} if extra_headers else headers


def prepare_dynatrace_params(base_url, endpoint: Endpoint, params, extra_params=None):
    """Prepare a Dynatrace request for the given endpoint and parameters.
    Params that are expected:
        time

    """
    endpoint_url = endpoint.url
    url = base_url + endpoint_url
    url, prepared_params = format_url_and_pop_path_params(endpoint, url, params)

    if endpoint == Endpoint.ENTITIES and extra_params:
        for entity_type in extra_params:
            prepared_params["entitySelector"] = entity_type
            yield url, format_params(endpoint, prepared_params), endpoint
    elif endpoint == Endpoint.METRICS_QUERY and extra_params:
        for metric_selector in extra_params:
            prepared_params["metricSelector"] = metric_selector
            yield url, format_params(endpoint, prepared_params), endpoint
    elif endpoint == Endpoint.METRICS and extra_params:
        # {'metricSelector': 'builtin:host.cpu.usage:merge(0):avg, metricselector2, etc...'}
        prepared_params["metricSelector"] = ",".join(extra_params)
        yield url, format_params(endpoint, prepared_params), endpoint
    elif endpoint == Endpoint.SYNTHETIC_MONITOR_HTTP_V2 and endpoint.extra_params:
        for extra_param in endpoint.extra_params:  # loop through ["SUCCESS", "FAILURE"]
            result_url = url + "/" + extra_param  # Append the suffix
            yield result_url, format_params(endpoint, params), endpoint
    elif endpoint == Endpoint.SYNTHETIC_MONITOR_ENTITY_V2 and endpoint.extra_params:
        for extra_param in endpoint.extra_params:  # loop through ["SUCCESS", "FAILURE"]
            result_url = url + "/" + extra_param  # Append the suffix
            yield result_url, format_params(endpoint, params), endpoint
    else:
        yield url, format_params(endpoint, params), endpoint


def prepare_dynatrace_request(session: Session, url: URL, params: Params):
    session.url = url
    session.params = params
    return session.prepare_request(Request("GET", url, params=params))


def remove_sensitive_info_recursive(data, keys_to_remove):
    if isinstance(data, dict):
        data = {
            key: remove_sensitive_info_recursive(value, keys_to_remove)
            for key, value in data.items()
            if key not in keys_to_remove
        }
    elif isinstance(data, list):
        data = [remove_sensitive_info_recursive(item, keys_to_remove) for item in data]
    return data


def fetch_entity_properties(session, tenant, result, extra_params):
    entity_properties = []
    if result and result[0].get("type"):
        prepared_params_list = prepare_dynatrace_params(
            tenant,
            Endpoint.ENTITY_TYPES,
            {"entityType": result[0].get("type")},
            extra_params,
        )
        for details in get_dynatrace_data(session, prepared_params_list):
            entity_properties.append(details["properties"])
    return entity_properties


def prepare_entity_property_params(entity_properties):
    flattened_properties = entity_properties[0]
    url_entity_property_params = [
        f'+properties.{prop["id"]}' for prop in flattened_properties
    ]
    return "fields=" + ",".join(url_entity_property_params)


def execute_session(
    endpoints: Union[Endpoint, Tuple[Endpoint, Endpoint]],
    tenant,
    api_token,
    params,
    extra_params=None,
    proxy_uri=None,
    verify=None,
    opt_helper=None,
):
    params = Params(params)

    with requests.Session() as session:
        session.headers.update(prepare_dynatrace_headers(api_token))

        main_endpoint, detail_endpoints = parse_endpoints(endpoints)
        extra_params = (
            main_endpoint.extra_params
            if main_endpoint.extra_params and extra_params is None
            else extra_params
        )
        prepared_params_list = prepare_dynatrace_params(
            tenant, main_endpoint, params, extra_params
        )

        counter = initialize_counter()
        for result in get_dynatrace_data(
            session,
            prepared_params_list,
            opt_helper,
            proxy_uri=proxy_uri,
            verify=verify,
        ):
            counter["session_loop_count"] += 1
            if not detail_endpoints:
                yield from process_main_results(result, counter)
            else:
                yield from process_detail_endpoints(
                    result,
                    detail_endpoints,
                    tenant,
                    extra_params,
                    counter,
                    session,
                    opt_helper=opt_helper,
                    proxy_uri=proxy_uri,
                    verify=verify,
                )
        log_counters(opt_helper, counter)


def parse_endpoints(endpoints):
    if isinstance(endpoints, tuple):
        return endpoints[0], endpoints[1:]
    return endpoints, []


def initialize_counter():
    return {
        "session_loop_count": 0,
        "item_count": 0,
        "result_count": 0,
        "detail_count": 0,
        "item_size": 0,
        "result_size": 0,
        "detail_size": 0,
    }


def process_main_results(result, counter):
    if isinstance(result, list):
        for item in result:
            counter["item_count"] += 1
            counter["item_size"] += len(json.dumps(item))
            yield item
    else:
        counter["result_count"] += 1
        counter["result_size"] += len(json.dumps(result))
        yield result


def process_detail_endpoints(
    result,
    detail_endpoints,
    tenant,
    extra_params,
    counter,
    session,
    opt_helper=None,
    proxy_uri=None,
    verify=None,
):
    if result:
        entity_properties, url_entity_property_params_string = (
            get_entity_properties_if_needed(
                detail_endpoints,
                result,
                tenant,
                extra_params,
                session,
                opt_helper=opt_helper,
                proxy_uri=proxy_uri,
                verify=verify,
            )
        )
        for record in result:
            counter["detail_count"] += 1
            counter["detail_size"] += len(json.dumps(record))
            id = record[detail_endpoints[0].selector]
            params = Params(
                {"time": get_from_time(), detail_endpoints[0].url_path_param: id}
            )
            if url_entity_property_params_string:
                params["url_params"] = url_entity_property_params_string
            prepared_params_list = prepare_dynatrace_params(
                tenant, detail_endpoints[0], params, extra_params
            )
            for details in get_dynatrace_data(
                session,
                prepared_params_list,
                opt_helper,
                proxy_uri=proxy_uri,
                verify=verify,
            ):
                yield details


def get_entity_properties_if_needed(
    detail_endpoints,
    result,
    tenant,
    extra_params,
    session,
    opt_helper=None,
    proxy_uri=None,
    verify=None,
):
    entity_properties = []
    url_entity_property_params_string = None
    if detail_endpoints[0] == Endpoint.ENTITY and result[0].get("type"):
        prepared_params_list = prepare_dynatrace_params(
            tenant,
            Endpoint.ENTITY_TYPES,
            {"entityType": result[0].get("type")},
            extra_params,
        )
        for details in get_dynatrace_data(
            session,
            prepared_params_list,
            opt_helper,
            proxy_uri=proxy_uri,
            verify=verify,
        ):
            entity_properties.append(details["properties"])
        flattened_properties = entity_properties[0]
        url_entity_property_params = [
            f'+properties.{prop["id"]}' for prop in flattened_properties
        ]
        url_entity_property_params_string = "fields=" + ",".join(
            url_entity_property_params
        )
    return entity_properties, url_entity_property_params_string


def log_counters(opt_helper, counter):
    if opt_helper:
        opt_helper.log_info(
            f"correlation_id: {opt_helper.correlation_id}, session_counters: {counter}"
        )


def list_dynatrace_entity_types(
    tenant,
    api_token,
    proxy_uri=None,
    verify=None,
    opt_helper=None,
):
    entity_types = []
    seen_entity_types = set()
    for item in execute_session(
        Endpoint.ENTITY_TYPES_LIST,
        tenant,
        api_token,
        {"pageSize": 500},
        proxy_uri=proxy_uri,
        verify=verify,
        opt_helper=opt_helper,
    ):
        entity_type = item.get("type") if isinstance(item, dict) else None
        if entity_type and entity_type not in seen_entity_types:
            seen_entity_types.add(entity_type)
            entity_types.append(entity_type)
    return entity_types


def get_dynatrace_data(
    session: Session,
    prepared_params_list,
    opt_helper=None,
    proxy_uri=None,
    verify=None,
):
    for url, params, endpoint in prepared_params_list:

        prepared_request = prepare_dynatrace_request(session, url, params)
        effective_proxy_uri = proxy_uri
        if effective_proxy_uri is None and opt_helper:
            effective_proxy_uri = opt_helper._get_proxy_uri()

        proxies = {}
        if effective_proxy_uri:
            proxies = {"http": effective_proxy_uri, "https": effective_proxy_uri}

        effective_verify = (
            verify if verify is not None else get_ssl_certificate_verification(opt_helper)
        )

        settings = session.merge_environment_settings(
            prepared_request.url,
            proxies,
            None,
            effective_verify,
            None,
        )
        # print('prepared_request: {}'.format(prepared_request))
        # print('prepared_request.url: {}'.format(prepared_request.url))
        # print('params: {}'.format(params))
        # print('settings: {}'.format(settings))

        if opt_helper:
            opt_helper.log_debug(
                f"Prepared Request: {prepared_request} {prepared_request.url} {prepared_request.body}"
            )
            opt_helper.log_debug(f"url: {url}")
            opt_helper.log_debug(f"headers: {prepared_request.headers}")
            opt_helper.log_debug(f"params: {params}")
            opt_helper.log_debug(f"Settings: {settings}")

        for response_json in _get_dynatrace_data(
            session, prepared_request, settings, opt_helper
        ):
            parsed_response = parse_dynatrace_response(response_json, endpoint)

            if opt_helper:
                opt_helper.log_debug(f"Parsed Response: {parsed_response}")

            if parsed_response:
                yield parsed_response


def _get_dynatrace_data(
    session, prepared_request: PreparedRequest, settings: dict, opt_helper
) -> json:
    base_url = prepared_request.url.replace(prepared_request.path_url, "")
    while True:
        try:
            response: Response = session.send(prepared_request, **settings)
            response.raise_for_status()  # raise HTTPError if status >=400

            if opt_helper:
                opt_helper.log_debug(f"Response: {response.text}")

            response_json: json = response.json()

            if opt_helper:
                opt_helper.log_debug(f"Parsed response: {response_json}")

                # If totalCount is in the response, log it
                if "totalCount" in response_json:
                    opt_helper.log_info(
                        f"correlation_id: {opt_helper.correlation_id}, "
                        f'dynatrace_json_response_size: {response_json["totalCount"]}'
                    )

            yield response_json

            if (
                "nextPageKey" not in response_json
                or response_json["nextPageKey"] is None
            ):
                break

            # Remove all params except for nextPageKey
            next_url = prepared_request.url.split("?")[0]
            prepared_request.prepare_url(
                next_url, {"nextPageKey": response_json["nextPageKey"]}
            )

        except requests.exceptions.HTTPError as err:
            if opt_helper:
                # Log the status code and error message
                opt_helper.log_error(
                    f"correlation_id: {opt_helper.correlation_id}, HTTP Error: {err}"
                )

                # If the server sent a response, log the response body
                if err.response is not None:
                    opt_helper.log_error(f"Details: {err.response.text}")
            break

        except Exception as e:
            if opt_helper:
                opt_helper.log_error(
                    f"Unexpected error: {e}, correlation_id {opt_helper.correlation_id}"
                )
            break


def parse_dynatrace_response(response: json, endpoint: Endpoint):
    resolution = None
    unit = None
    selector = endpoint.selector
    # Check if the response has an entityId, if so, return early, this is for entities endpoint
    if endpoint == Endpoint.ENTITIES and isinstance(response, dict):
        return response.get(selector, response)
    # Check if monitorId is a top level key, return immediately if so this is for synthetic endpoint
    elif endpoint == Endpoint.SYNTHETIC_MONITOR_HTTP_V2 and isinstance(response, dict):
        return response
    # elif endpoint == Endpoint.SYNTHETIC_MONITORS_HTTP_V2:
    #     return SyntheticOnDemandExecution(**response)
    elif endpoint == Endpoint.METRIC_DESCRIPTORS and isinstance(response, dict):
        return MetricDescriptor(**response)
    elif endpoint == Endpoint.ENTITY and isinstance(response, dict):
        return Entity(**response)
    elif endpoint == Endpoint.PROBLEM and isinstance(response, dict):
        return Problem(**response)
    elif endpoint == Endpoint.METRICS_QUERY and isinstance(response, dict):
        return MetricData(**response)
    elif endpoint == Endpoint.METRICS and isinstance(response, dict):
        return MetricDescriptorCollection(**response)

    # This next line grabs a specific key from the response, if it doesn't exist, it returns the response
    parsed_response = response.get(selector, response)

    # Add resolution to parsed response if it exists: this is metric specific code
    # parsed response is a list and resolution is a string
    # Probably don't need this anymore
    if (
        endpoint == Endpoint.METRICS_QUERY
        and isinstance(parsed_response, list)
        and parsed_response
    ):
        parsed_response: MetricData = MetricData(**response)
        return parsed_response

    # Check if the parsed response is a list, if so, return early
    if isinstance(parsed_response, list):
        return parsed_response

    return response


def write_certificate_to_file(cert_file, certificate, helper=None):
    try:
        with open(cert_file, "w") as f:
            f.write(certificate)
        if helper:
            helper.log_debug("Certificate written successfully")
        return True
    except Exception as e:
        if helper:
            helper.log_error(f"Failed to write certificate: {e}")
        return False


def get_ssl_certificate_verification(helper=None, user_certificate=None):
    local_dir = os.path.abspath(
        os.path.join(Path(__file__).resolve().parent.parent, "local")
    )
    os.makedirs(local_dir, exist_ok=True)
    cert_file = os.path.join(local_dir, "cert.pem")

    user_uploaded_certificate = user_certificate
    if user_uploaded_certificate is None and helper:
        user_uploaded_certificate = helper.get_global_setting("user_certificate")

    # Update the certificate on disk if it doesn't exist or if the user uploaded a new certificate
    if not os.path.isfile(cert_file) or (
        user_uploaded_certificate
        and open(cert_file, "r").read() != user_uploaded_certificate
    ):
        if user_uploaded_certificate:
            if not write_certificate_to_file(
                cert_file, user_uploaded_certificate, helper
            ):
                return cert_file

    return cert_file if os.path.isfile(cert_file) else certifi.where()
