#!/usr/bin/env python
# encoding = utf-8

def status_code_errors(response, api_endpoint, log_label, helper):
    if isinstance(response, int):
        status_code = response
    elif isinstance(response, dict):
        status_code = response.get('status_code', 0)
    else:
        helper.log_error(f'{log_label} Unexpected response type from {api_endpoint}: {type(response)}')
        raise RuntimeError(f'Unexpected response type from {api_endpoint}: {type(response)}')

    if status_code == 0:
        helper.log_error(f'{log_label} No HTTP response received from {api_endpoint} — possible network or connection error')
        raise RuntimeError(f'API error from {api_endpoint}: no HTTP response received (status_code=0)')

    if 200 <= status_code <= 299:
        helper.log_debug(f'{log_label} Successful API call to {api_endpoint} — HTTP {status_code}')
        return

    body = response.get('body', {}) if isinstance(response, dict) else {}
    cs_traceid = body.get('meta', {}).get('trace_id', 'No TraceID available')
    errors = body.get('errors', [])
    cs_error_msg = errors[0].get('message', 'No error message available') if errors else 'No error message available'
    headers = response.get('headers', {}) if isinstance(response, dict) else {}
    header_traceid = headers.get('X-Cs-Traceid', None)
    effective_traceid = cs_traceid if cs_traceid != 'No TraceID available' else header_traceid or 'No TraceID available'

    if 400 <= status_code <= 499:
        helper.log_error(f'{log_label} CrowdStrike Intel Indicators API error for {api_endpoint} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')
    elif 500 <= status_code <= 599:
        helper.log_error(f'{log_label} CrowdStrike Intel Indicators API server error for {api_endpoint} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')
    else:
        helper.log_error(f'{log_label} CrowdStrike Intel Indicators API unexpected status for {api_endpoint} — HTTP {status_code}: {cs_error_msg}, TraceID: {effective_traceid}')

    raise RuntimeError(f'API error from {api_endpoint}: {status_code} - {cs_error_msg}')
