"""Pull Wiz vulnerability findings and write them to Splunk."""
import time

from queries import VULNS_QUERY
from query_builders import (
    ALL_VULN_STATUSES,
    INITIAL_VULN_STATUSES,
    build_vulnerability_query_variables,
)
from wiz_api import VULNS, request_wiz_api_token, resolve_request_timeout
from wiz_pager import query_wiz_api_and_write_to_splunk


def get_vulnerabilities(helper, ew, latest_polling_timestamp=None, trigger_full_sync_bool=False):
    start_time = time.time()
    source_name = helper.get_arg('name')

    if trigger_full_sync_bool:
        pull_mode, status_list = 'full_sync', ALL_VULN_STATUSES
    elif latest_polling_timestamp:
        pull_mode, status_list = 'incremental', INITIAL_VULN_STATUSES
    else:
        pull_mode, status_list = 'initial', INITIAL_VULN_STATUSES

    helper.log_info(f'Source name = {source_name}. Starting to pull: {pull_mode} ')

    variables = build_vulnerability_query_variables(helper, status_list, latest_polling_timestamp)
    token = request_wiz_api_token(helper)
    total = query_wiz_api_and_write_to_splunk(
        helper, VULNS, token, VULNS_QUERY, variables, ew,
        requests_timeout=resolve_request_timeout(helper),
    )

    execution_time = time.time() - start_time
    helper.log_info(
        f'Source name = {source_name}. Pull mode = {pull_mode}. Fetched {total} vulnerabilities. '
        f'Events written to Splunk: {total}. Execution time: {execution_time:.2f} seconds. Variables = {variables}'
    )
    return total
