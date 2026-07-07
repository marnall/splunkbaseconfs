#!/usr/bin/env python
# encoding = utf-8

def status_code_errors(response, api_call, log_label, helper):
    #handles status codes that aren't 200 level responses

    if isinstance(response, int):
        status_code = response
    elif isinstance(response, dict):
        status_code = response.get('status_code', 0)
    else:
        helper.log_error(f'{log_label} Unexpected response type from {api_call}: {type(response)}')
        raise RuntimeError(f'Unexpected response type from {api_call}: {type(response)}')

    if status_code == 0:
        helper.log_error(f'{log_label} No HTTP response received from {api_call} — possible network or connection error')
        raise RuntimeError(f'API error from {api_call}: no HTTP response received (status_code=0)')

    if 200 <= status_code <= 299:
        helper.log_debug(f'{log_label} Successful API call to {api_call} Status Code: {status_code}')
        return

    # Extract trace ID and error message safely for all error paths
    body = response.get('body', {}) if isinstance(response, dict) else {}
    cs_traceid = body.get('meta', {}).get('trace_id', 'No TraceID available')
    errors = body.get('errors', [])
    cs_error_msg = errors[0].get('message', 'No error message available') if errors else 'No error message available'
    headers = response.get('headers', {}) if isinstance(response, dict) else {}

    # Resolve effective TraceID with header fallback
    header_traceid = headers.get('X-Cs-Traceid', None)
    effective_traceid = cs_traceid if cs_traceid != 'No TraceID available' else header_traceid or 'No TraceID available'

    if status_code == 429:
        helper.log_error(f'{log_label} Rate limit exhausted for {api_call} after retries — HTTP {status_code}, TraceID: {effective_traceid}')
    elif 400 <= status_code <= 499:
        helper.log_error(f'{log_label} CrowdStrike API error for {api_call} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')
    elif 500 <= status_code <= 599:
        helper.log_error(f'{log_label} CrowdStrike API server error for {api_call} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')
    else:
        helper.log_error(f'{log_label} CrowdStrike API unexpected status for {api_call} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')

    raise RuntimeError(f'API error from {api_call}: {status_code} - {cs_error_msg}')
