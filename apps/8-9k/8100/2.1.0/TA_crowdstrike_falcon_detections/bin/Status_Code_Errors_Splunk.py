#!/usr/bin/env python
# encoding = utf-8

def status_code_errors(response, api_endpoint, log_label, helper):
    """Handle non-2xx API responses with safe key extraction."""
    status_code = response.get('status_code', 0) if isinstance(response, dict) else 0

    # Log raw response for debugging when status_code is 0 or response is non-dict
    if status_code == 0 or not isinstance(response, dict):
        helper.log_debug(f'{log_label} Raw API response object: {response}')

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
        helper.log_error(f'{log_label} Rate limit exhausted for {api_endpoint} — HTTP {status_code}, TraceID: {effective_traceid}')
    elif 400 <= status_code <= 499:
        helper.log_error(f'{log_label} CrowdStrike API error for {api_endpoint} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')
    elif 500 <= status_code <= 599:
        helper.log_error(f'{log_label} CrowdStrike API server error for {api_endpoint} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')
    else:
        helper.log_error(f'{log_label} CrowdStrike API unexpected status for {api_endpoint} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')

    raise RuntimeError(f'CrowdStrike API error on {api_endpoint}: HTTP {status_code} - {cs_error_msg}')
