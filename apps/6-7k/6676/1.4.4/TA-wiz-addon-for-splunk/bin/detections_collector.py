"""Pull Wiz detections and write them to Splunk.

Detections flush per page so the cursor is checkpointed after every page —
mid-poll timeouts don't lose pages that already wrote events.
"""
from queries import DETECTIONS_QUERY
from query_builders import build_detections_query_variables
from wiz_api import DETECTIONS, request_wiz_api_token, resolve_request_timeout
from wiz_pager import query_wiz_api_and_write_to_splunk

DEFAULT_DETECTIONS_POLL_BUDGET_SECONDS = 300


def get_detections(helper, ew, days_back, latest_polling_cursor=None, save_cursor_callback=None) -> int:
    source_name = helper.get_arg('name')

    variables = build_detections_query_variables(helper, days_back)
    if latest_polling_cursor:
        variables['after'] = latest_polling_cursor

    token = request_wiz_api_token(helper)

    def save_cursor(page_info):
        if not page_info:
            return
        last_cursor = page_info.get('endCursor')
        if last_cursor and save_cursor_callback:
            save_cursor_callback(last_cursor)

    requests_timeout = resolve_request_timeout(helper)

    total = query_wiz_api_and_write_to_splunk(
        helper, DETECTIONS, token, DETECTIONS_QUERY, variables, ew,
        post_write_callback=save_cursor,
        requests_timeout=requests_timeout,
        total_query_timeout=DEFAULT_DETECTIONS_POLL_BUDGET_SECONDS,
    )
    helper.log_info(f'Source name = {source_name}. Fetched {total} detections. Variables = {variables}')
    return total
