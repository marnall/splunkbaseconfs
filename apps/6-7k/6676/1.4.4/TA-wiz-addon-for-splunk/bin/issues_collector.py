"""Pull Wiz issues. Branch order: UPDATED > FULL_SYNC > INCREMENTAL > INITIAL."""
from queries import ISSUES_QUERY, ISSUES_QUERY_WITH_SECURITY_FRAMEWORKS
from query_builders import (
    ISSUES_DATE_FIELD,
    ISSUES_DATE_RESOLVED_FIELD,
    build_issues_query_variables,
    filter_updated_at_issues,
)
from wiz_api import ISSUES, get_wiz_url, request_wiz_api_token, resolve_request_timeout
from wiz_pager import query_wiz_api_and_write_to_splunk

ACTIVE_STATUSES = ['OPEN', 'IN_PROGRESS', 'REJECTED']


def _build_url_enricher(helper):
    """Return a callable that stamps sourceURL onto each issue, or None if URL unavailable."""
    wiz_url = get_wiz_url(helper)

    def enrich(batch):
        for item in batch:
            if 'id' in item:
                item['sourceURL'] = f"{wiz_url}/issues#~(issue~'{item['id']})"
        return batch

    return enrich


def _filter_then_enrich(helper, after, before):
    """Compose the updated-mode filter with the URL enricher into one prepare_batch fn."""
    enrich = _build_url_enricher(helper)

    def prepare(batch):
        return enrich(filter_updated_at_issues(batch, after, before, helper))

    return prepare


def get_issues(helper, trigger_full_sync_bool, latest_full_sync_time, ew,
               before_timestamp, latest_polling_timestamp=False):
    source_name = helper.get_arg('name')
    re_assessed = helper.get_arg('re_assessed_issues')
    query = ISSUES_QUERY_WITH_SECURITY_FRAMEWORKS if helper.get_arg('include_security_categories') else ISSUES_QUERY
    before_z = before_timestamp + 'Z'
    token = request_wiz_api_token(helper)

    requests_timeout = resolve_request_timeout(helper)

    def fetch(variables, *, prepare_batch=None):
        return query_wiz_api_and_write_to_splunk(
            helper, ISSUES, token, query, variables, ew, prepare_batch=prepare_batch,
            requests_timeout=requests_timeout,
        )

    # Updated mode: re-assessment opt-in. Active sweep filtered by updatedAt + resolved window.
    if not trigger_full_sync_bool and re_assessed and latest_polling_timestamp:
        helper.log_info(f'Source name = {source_name}. Doing incrementally polling of issues using updatedAt field')

        updated_vars = build_issues_query_variables(helper, status=ACTIVE_STATUSES)
        updated_count = fetch(
            updated_vars,
            prepare_batch=_filter_then_enrich(helper, latest_polling_timestamp, before_z),
        )
        helper.log_info(
            f'Source name = {source_name}. Fetched {updated_count} new updated issues. '
            f'updatedAt range: before: {before_z}, after: {latest_polling_timestamp}. Variables = {updated_vars}'
        )

        resolved_vars = build_issues_query_variables(
            helper, status=['RESOLVED'],
            extra_filter={ISSUES_DATE_FIELD: {'after': latest_polling_timestamp, 'before': before_z}},
        )
        resolved_count = fetch(resolved_vars, prepare_batch=_build_url_enricher(helper))
        helper.log_info(
            f'Source name = {source_name}. Fetched {resolved_count} resolved issues. Variables = {resolved_vars}'
        )
        return updated_count + resolved_count

    # Full sync: all active issues + resolved window since last sync.
    if trigger_full_sync_bool:
        helper.log_info(f"Source name = {source_name}. Doing full sync polling of issues")
        active_vars = build_issues_query_variables(helper, status=ACTIVE_STATUSES)
        active_count = fetch(active_vars, prepare_batch=_build_url_enricher(helper))
        helper.log_info(f'Source name = {source_name}. Fetched {active_count} issues. Variables = {active_vars}')

        resolved_vars = build_issues_query_variables(
            helper, status=['RESOLVED'],
            extra_filter={ISSUES_DATE_RESOLVED_FIELD: {'after': latest_full_sync_time, 'before': before_z}},
        )
        resolved_count = fetch(resolved_vars, prepare_batch=_build_url_enricher(helper))
        helper.log_info(
            f'Source name = {source_name}. Fetched {resolved_count} resolved issues. Variables = {resolved_vars}'
        )
        return active_count + resolved_count

    # Incremental: status-change sweep since last poll.
    if latest_polling_timestamp:
        helper.log_info(f"Source name = {source_name}. Doing incrementally polling of issues")
        variables = build_issues_query_variables(helper)
        variables['filterBy'][ISSUES_DATE_FIELD] = {'after': latest_polling_timestamp, 'before': before_z}
        total = fetch(variables, prepare_batch=_build_url_enricher(helper))
        helper.log_info(f'Source name = {source_name}. Fetched {total} issues. Variables = {variables}')
        return total

    # Initial: OPEN/IN_PROGRESS first-time pull.
    helper.log_info(f"Source name = {source_name}. Doing initially polling of issues")
    variables = build_issues_query_variables(helper, status=['OPEN', 'IN_PROGRESS'])
    total = fetch(variables, prepare_batch=_build_url_enricher(helper))
    helper.log_info(f'Source name = {source_name}. Fetched {total} issues. Variables = {variables}')
    return total
