import Status_Code_Errors as handle_Errors
from Scheduled_Reports_Get_Executions import _command_with_retry

def _escape_fql_value(value):
    """Escape FQL metacharacters in field values."""
    value = value.replace('\\', '\\\\')
    value = value.replace("'", "\\'")
    value = value.replace('+', '\\+')
    value = value.replace('*', '\\*')
    return value

def getIDS(falcon, report_name, report_limit, log_label,  helper):
    helper.log_info(f'{log_label} Preparing to collect Report ID for report name: {report_name}')
    escaped_name = _escape_fql_value(report_name)
    query_filter = f"name:'{escaped_name}'"
    #Takes the report name and identifies that associated report ID
    id_response = _command_with_retry(falcon, "scheduled_reports_query", log_label, helper, filter=query_filter, limit=report_limit)
    handle_Errors.status_code_errors(id_response, 'Get Report IDs ' + report_name, log_label, helper)
    report_ids = id_response.get('body', {}).get('resources', []) or []

    if len(report_ids) == 0:
        helper.log_error(f'{log_label} There was no id returned for a report named {report_name} - Please validate the report name, the TA will now exit')
        raise RuntimeError(f'No report ID found for report name: {report_name}')

    if len(report_ids) > 1:
        helper.log_warning(f'{log_label} Multiple report IDs ({len(report_ids)}) found for report name: {report_name}, only the first will be used')

    helper.log_info(f'{log_label} Successfully collected report ID for report name: {report_name}')
    return report_ids

def getReports(falcon, ids, log_label, helper):
    helper.log_info(f'{log_label} Preparing to get the report details for the Report ID')
    report_response = _command_with_retry(falcon, "scheduled_reports_get", log_label, helper, ids=ids)
    handle_Errors.status_code_errors(report_response, 'Get Reports', log_label, helper)
    report_data = report_response.get('body', {}).get('resources', [])
    if len(report_data) == 0:
        helper.log_error(f'{log_label} There are no reports that match the provided ID - please validate the report name, the TA will now exit')
        raise RuntimeError('No report data found for the provided report ID')
    helper.log_info(f'{log_label} Successfully collected the report details for the Report ID')
    report_format = report_data[0].get('report_params', {}).get('format', 'unknown')
    helper.log_info(f'{log_label} Format of the search results is {report_format}')
    return report_data[0]
