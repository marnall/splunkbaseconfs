"""Pull Wiz user audit logs and write them to Splunk."""
from queries import AUDIT_LOGS_QUERY
from query_builders import AUDIT_DATE_FIELD, AUDIT_PAGE_SIZE
from wiz_api import AUDIT, request_wiz_api_token, resolve_request_timeout
from wiz_pager import query_wiz_api_and_write_to_splunk


def get_user_audit_logs(helper, latest_polling_timestamp, ew, before_timestamp):
    source_name = helper.get_arg('name')
    before_z = before_timestamp + 'Z'
    variables = {
        'first': AUDIT_PAGE_SIZE,
        'filterBy': {
            AUDIT_DATE_FIELD: {
                'after': latest_polling_timestamp,
                'before': before_z,
            },
        },
    }
    helper.log_info(f'Source name = {source_name}. Going to pull Audit logs. Variables ={variables}')
    token = request_wiz_api_token(helper)
    return query_wiz_api_and_write_to_splunk(
        helper, AUDIT, token, AUDIT_LOGS_QUERY, variables, ew,
        requests_timeout=resolve_request_timeout(helper),
    )
