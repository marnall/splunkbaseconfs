import Status_Code_Errors as handle_Errors
import CrowdStrike_Constants as const
import time
import random

def _command_with_retry(falcon, command, log_label, helper, **kwargs):
    """Execute a FalconPy command with rate-limit retry and token expiry handling.

    Must be called before status_code_errors() — by the time
    status_code_errors sees a 429, retries are already exhausted
    and the error is genuinely fatal.
    """
    for attempt in range(const.rate_limit_retries + 1):
        response = falcon.command(command, **kwargs)
        status_code = response.get('status_code', 0) if isinstance(response, dict) else 0

        # Handle token expiry — attempt re-authentication once
        if status_code == 401 and attempt == 0:
            helper.log_warning(f'{log_label} Token expired (401) on {command}, attempting re-authentication')
            try:
                falcon.authenticate()
                if falcon.authenticated():
                    helper.log_info(f'{log_label} Re-authentication successful, retrying {command}')
                    continue
                else:
                    helper.log_error(f'{log_label} Re-authentication failed for {command}')
            except Exception as e:
                helper.log_error(f'{log_label} Re-authentication exception during {command}: {type(e).__name__}: {e}')
            return response

        # Handle rate limiting and server errors
        if status_code == 429 or status_code >= 500:
            if attempt < const.rate_limit_retries:
                wait = const.rate_limit_backoff * (2 ** attempt) + random.uniform(0, 1)
                helper.log_warning(f'{log_label} Retryable error ({status_code}) on {command}, retrying in {wait:.1f}s (attempt {attempt + 1}/{const.rate_limit_retries})')
                time.sleep(wait)
                continue
            else:
                helper.log_error(f'{log_label} All {const.rate_limit_retries} retries exhausted for {command}, final status {status_code}')
                return response

        if attempt > 0 and 200 <= status_code <= 299:
            helper.log_info(f'{log_label} {command} succeeded after {attempt} retries')

        return response

def getExecutions(falcon, ids, checkpoint, limit, collection_option, log_label, helper):

    helper.log_info(f'{log_label} Preparing to collect the execution IDs')
    report_id = ids[0].replace("'", "\\'")
    exec_filter = f"scheduled_report_id:'{report_id}'+result_metadata.report_finish:>'{checkpoint}'+status:'DONE'"

    if collection_option == 'standard':
        exec_sort = 'last_updated_on.desc'
    else:
        exec_sort = 'last_updated_on.asc'

    helper.log_info(f'{log_label} Execution query — filter: {exec_filter}, sort: {exec_sort}')
    exec_response = _command_with_retry(falcon, "report_executions_query", log_label, helper, filter=exec_filter, sort=exec_sort, limit=limit)
    handle_Errors.status_code_errors(exec_response, 'Get Executions IDs', log_label, helper)
    body = exec_response.get('body', {})
    total = body.get('meta', {}).get('pagination', {}).get('total', 0)
    exec_ids = body.get('resources', []) or []
    result_count = len(exec_ids)
    query_counter = 1

    #only return the first collection of IDs if it is not historic
    if collection_option == 'standard':
        return exec_ids

    #if not then determine if pagination is required to collect all the data
    while total > result_count:
        helper.log_info(f'{log_label} Pagination required to collect additional execution IDs (page {query_counter})')
        offset_val= query_counter * limit
        pag_exec_response = _command_with_retry(falcon, "report_executions_query", log_label, helper, filter=exec_filter, limit=limit, offset=offset_val, sort=exec_sort)
        handle_Errors.status_code_errors(pag_exec_response, 'Get Executions IDs - Pagination', log_label, helper)
        pag_exec_ids = pag_exec_response.get('body', {}).get('resources', []) or []
        if len(pag_exec_ids) == 0:
            helper.log_warning(f'{log_label} Pagination returned empty page at offset {offset_val}, stopping')
            break
        exec_ids.extend(pag_exec_ids)
        result_count = len(exec_ids)
        query_counter += 1

    helper.log_info(f'{log_label} Successfully collected {result_count} execution IDs')

    return exec_ids

def getExecDetails(falcon, ids, log_label, helper):
    helper.log_info(f'{log_label} Preparing to collect the execution ID details for {len(ids)}')
    exec_data = []
    id_groups = []
    size = 1000  # Verified via live API testing — batch sizes up to 1000 accepted

    if len(ids) > size:
        helper.log_debug(f'{log_label} The number of execution IDs exceeded the API limit, IDs will be grouped for collection.')
    for i in range(0, len(ids), size):
        group = ids[i:i + size]
        id_groups.append(group)

    num_groups = len(id_groups)
    helper.log_debug(f'{log_label} Calculated {num_groups} number of execution ID groups for collection.')

    #collect the details for the execution IDs:
    for i in range(0, num_groups):
        helper.log_info(f'{log_label} Collecting details for execution ID group: {i + 1} of {num_groups}')
        exec_details_response = _command_with_retry(falcon, "report_executions_get", log_label, helper, ids=id_groups[i], limit=size)
        handle_Errors.status_code_errors(exec_details_response, 'Get Executions Details', log_label, helper)
        exec_data.extend(exec_details_response.get('body', {}).get('resources', []) or [])
    helper.log_info(f'{log_label} Successfully collected the execution ID group details, {len(exec_data)} in total')
    if len(exec_data) != len(ids):
        helper.log_warning(f'{log_label} Execution detail count mismatch: requested {len(ids)} IDs but received {len(exec_data)} details')
    return exec_data

def getReportFile(falcon, exe_id, log_label, helper):
    helper.log_info(f'{log_label} Downloading report file for execution {exe_id}')
    report_file_response = _command_with_retry(falcon, "report_executions_download_get", log_label, helper, ids=exe_id)

    # Bytes response means raw file content (CSV or other) — return directly for caller to handle
    if isinstance(report_file_response, bytes):
        if len(report_file_response) == 0:
            helper.log_warning(f'{log_label} Execution {exe_id}: no report data was returned from download')
        else:
            helper.log_info(f'{log_label} Execution {exe_id}: downloaded report file ({len(report_file_response):,} bytes)')
        return report_file_response

    # Dict response — validate and return resources
    handle_Errors.status_code_errors(report_file_response, 'Report File Collection', log_label, helper)
    resources = report_file_response.get('body', {}).get('resources', [])
    if len(resources) == 0:
        helper.log_warning(f'{log_label} Execution {exe_id}: report response contained no resources')
    return resources
