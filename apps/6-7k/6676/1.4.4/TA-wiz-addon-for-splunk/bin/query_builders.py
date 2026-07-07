"""Build GraphQL `variables` payloads for the Wiz API."""
import re

from timestamp_utils import try_parse_wiz_timestamp, with_overlap_buffer

ISSUES_DATE_FIELD = 'statusChangedAt'
ISSUES_DATE_RESOLVED_FIELD = 'resolvedAt'
AUDIT_DATE_FIELD = 'timestamp'
DETECTION_DATE_FIELD = 'createdAt'
DETECTION_ORDER_BY = 'CREATED_AT'

ALL_VULN_STATUSES = ["OPEN", "IN_PROGRESS", "REJECTED", "RESOLVED"]
INITIAL_VULN_STATUSES = ["OPEN", "IN_PROGRESS", "REJECTED"]

ISSUES_PAGE_SIZE = 500
VULNS_PAGE_SIZE = 5000
AUDIT_PAGE_SIZE = 500
DETECTIONS_PAGE_SIZE_FULL = 500
DETECTIONS_PAGE_SIZE_WITH_TRIGGERS = 50  # triggers inflate payload; smaller pages

# Splunk multi-select args arrive in many shapes; this split feeds GraphQL a clean list.
_LIST_ARG_SPLIT = re.compile(r"[,~\[\]'\"\s]+")
_WIZ_TIMESTAMP_SORT_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z$')


def _parse_list_arg(value):
    """Normalize Splunk multi-select args (str/list/stringified) to flat list[str] or None."""
    if not value:
        return None
    if isinstance(value, list):
        flat = ",".join(str(item) for item in value)
    elif isinstance(value, str):
        flat = value
    else:
        return None
    tokens = [t for t in _LIST_ARG_SPLIT.split(flat) if t]
    return tokens or None


def _project_filter(helper, field, *, wrap_equals=False):
    """filterBy fragment for project_id. wrap_equals=True for fields that take {equals: [...]}."""
    ids = _parse_list_arg(helper.get_arg('project_id'))
    if not ids:
        return {}
    return {field: {'equals': ids} if wrap_equals else ids}


def _timestamp_sort_key(value):
    if not isinstance(value, str) or try_parse_wiz_timestamp(value) is None:
        return None
    match = _WIZ_TIMESTAMP_SORT_RE.match(value)
    if not match:
        return None
    seconds, fraction = match.groups()
    fraction = (fraction or "").ljust(9, "0")[:9]
    return f"{seconds}.{fraction}Z"


def filter_updated_at_issues(entries, latest_polling_timestamp, before_timestamp, helper=None):
    """Keep issues whose updatedAt falls in (after, before] — exclusive after, inclusive before."""
    after = _timestamp_sort_key(latest_polling_timestamp)
    before = _timestamp_sort_key(before_timestamp)
    # Raise (not return []) so the caller doesn't advance the checkpoint past unread data.
    if after is None or before is None:
        raise ValueError(f"Invalid polling window: after={latest_polling_timestamp!r}, before={before_timestamp!r}")
    res = []
    for issue in entries:
        raw = issue.get('updatedAt')
        updated = _timestamp_sort_key(raw)
        if updated is None:
            if helper is not None:
                helper.log_warning(
                    f"Skipping issue with unparseable updatedAt: id={issue.get('id')!r}, updatedAt={raw!r}"
                )
            continue
        # `<= before`: edge-stamped issues are lost if the cursor advances past them.
        if after < updated <= before:
            res.append(issue)
    return res


def build_issues_query_variables(helper, *, status=None, extra_filter=None):
    filter_by = {**_project_filter(helper, 'project')}
    severity = _parse_list_arg(helper.get_arg('severity'))
    if severity:
        filter_by['severity'] = severity
    if status:
        filter_by['status'] = status
    if extra_filter:
        filter_by.update(extra_filter)
    return {'first': ISSUES_PAGE_SIZE, 'filterBy': filter_by}


def build_vulnerability_query_variables(helper, status_list, latest_polling_timestamp=None):
    filter_by = {
        **_project_filter(helper, 'projectIdV2', wrap_equals=True),
        'assetType': _parse_list_arg(helper.get_arg('asset_type')),
        'vendorSeverity': _parse_list_arg(helper.get_arg('severity')),
        'status': status_list,
    }

    related = _parse_list_arg(helper.get_arg('related_issue_severity'))
    if related:
        filter_by['relatedIssueSeverity'] = related

    if latest_polling_timestamp:
        adjusted = with_overlap_buffer(latest_polling_timestamp)
        if adjusted is None:
            # Don't send `after: null` — Wiz errors or silently full-refetches.
            helper.log_warning(
                f"Unparseable latest_polling_timestamp {latest_polling_timestamp!r}; "
                "falling back to initial pull."
            )
        else:
            filter_by[helper.get_arg('daily_update_by')] = {'after': adjusted}

    return {'first': VULNS_PAGE_SIZE, 'filterBy': filter_by}


def build_detections_query_variables(helper, days_back):
    include_triggering_events = bool(helper.get_arg('include_triggering_events'))
    page_size = DETECTIONS_PAGE_SIZE_WITH_TRIGGERS if include_triggering_events else DETECTIONS_PAGE_SIZE_FULL

    filter_by = {
        **_project_filter(helper, 'projectId'),
        'severity': {'equals': _parse_list_arg(helper.get_arg('severity'))},
        DETECTION_DATE_FIELD: {'inLast': {'amount': days_back, 'unit': 'DurationFilterValueUnitDays'}},
    }
    return {
        'first': page_size,
        'filterBy': filter_by,
        'includeTriggeringEvents': include_triggering_events,
        'orderBy': {'field': DETECTION_ORDER_BY, 'direction': 'ASC'},
    }
