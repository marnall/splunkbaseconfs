import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Union, List

import util
import requests
import itertools
import re
from dynatrace_types_37 import *
# from dynatrace_types import *


def prepare_and_get_data(api_type, tenant, token, params, session, helper):
    request_info = util.prepare_dynatrace_params(api_type, token, tenant)
    helper.log_debug(f"Request Info: {request_info}")
    data = util.get_dynatrace_data(session, request_info, opt_helper=helper)

    if data is None:
        helper.log_error(f"Failed to fetch data for request: {request_info}")
        # Handle the error as needed: retry, return early, raise exception, etc.

    return data


def parse_series_collection(series_collection: MetricSeriesCollection) -> List[MetricSeries]:
    """Parse a MetricSeriesCollection into a list of MetricSeries.

    Args:
        series_collection (MetricSeriesCollection): A MetricSeriesCollection.

    Returns:
        list[MetricSeries]: A list of MetricSeries.
    """
    return series_collection['data']


def parse_series(series: MetricSeries) -> List[DataPoint]:
    """Parse a MetricSeries into a list of DataPoints.

    Args:
        series (MetricSeries): A MetricSeries.

    Returns:
        list[DataPoint]: A list of DataPoints.
    """
    return series['data']


def flatten_and_zip_timeseries(timeseries_data: MetricData):
    series_collection: MetricSeriesCollection
    series: MetricSeries
    dimension_map_dict: DimensionMap
    item: DataPoint
    resolution: str = timeseries_data['resolution']

    for series_collection in timeseries_data['result']:
        for series in series_collection['data']:
            timestamps_list = series['timestamps']
            values_list = series['values']
            dimension_map_dict = series['dimensionMap']

            # Iterate over each timestamp-value pair
            for timestamp, value in zip(timestamps_list, values_list):
                # Create a new dictionary merging the 'dimension_map', 'timestamp', and 'value'
                data_point = {
                    **dimension_map_dict,
                    'timestamp': timestamp,
                    'value': value,
                    'resolution': resolution
                }

                yield data_point


def build_event_data(item: DataPoint, metric_descriptor: MetricDescriptor, opt_dynatrace_tenant: Tenant, metric_selector: MetricSelector):
    event_data = {
        **item,
        **{'metric_name': metric_descriptor['metricId'],
           'value': item['value'],
           'dynatraceTenant': opt_dynatrace_tenant,
           'metric_selector_used': metric_selector},
        **({'unit': metric_descriptor['unit']} if 'unit' in metric_descriptor else {})}
    return event_data


def get_dynatrace_metrics_descriptors(tenant, api_token, metric_selector, time=None, page_size=100, verify=True):
    """Get Dynatrace metrics descriptors from the API v2.

    Args:
        tenant (str): Dynatrace
        api_token (str): Dynatrace API token
        metric_selector (str): Metric selector.
        time (str): Time range for the problems. Defaults to None.
        page_size (int): Number of problems to return. Defaults to 100.

    Returns:
        json: JSON response from the API.
    """
    # Set the headers
    headers = {
        'Authorization': 'Api-Token {}'.format(api_token),
        'version': 'Splunk_TA_Dynatrace'
    }
    # Set the parameters
    if time is None:
        parameters = {
            'metricSelector': metric_selector,
            'pageSize': page_size
        }
    else:
        parameters = {
            'metricSelector': metric_selector,
            'from': time,
            'pageSize': page_size
        }
    # Set the URL
    url = tenant + '/api/v2/metrics/query/descriptors'
    # Get the problems
    response = requests.get(url, headers=headers, params=parameters, verify=verify)
    # Return the response
    return response.json()


def parse_metric_selector(metric_selectors: List[str]) -> MetricSelector:
    """Parse a list of metric selectors into a string for the API call.

    Args:
        metric_selectors (list): A list of metric selectors.

    Returns:
        MetricSelector: A string of metric selectors.
    """
    metric_selector_str = ''
    for selector in metric_selectors:
        metric_selector_str += selector + '\n'

    metric_selector = MetricSelector(metric_selector_str[:-1])

    return metric_selector


def parse_metric_selectors_from_file(file_path: Path):
    with open(file_path, 'r') as f:
        file_content = f.read()

    return parse_metric_selectors_text_area(file_content)


def parse_metric_selectors_text_area(textarea_input: str) -> List[MetricSelector]:
    """Scan line by line, if there is leading whitespace or tabs, it's a continuation of the previous line.
    Strip them and append them to the previous selector.
    @param textarea_input: The text area input
    @return: A list of metric selectors
    """

    # Combine the lines that are continuations of the previous line
    joined_sub_expressions = re.sub(re.compile(r'\n\s+:'), ':', textarea_input)

    # Split the lines into a list
    parsed_metric_selectors_str = joined_sub_expressions.splitlines()

    # Convert each string in the list to a MetricSelector
    parsed_metric_selectors = [MetricSelector(selector) for selector in parsed_metric_selectors_str]

    return parsed_metric_selectors

