
# encoding = utf-8

import sys
import hashlib

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    base_url = getHttpsBaseUrl(helper)
    token_name = helper.get_arg('token_name')
    auth_token = helper.get_arg('auth_token')

    helper.log_info(f'Collecting BigID Audit Logs from: {str(base_url)}')
    
    try:
        helper.log_info(f'Refreshing token on {base_url} with token (secret) length: {str(len(auth_token))}')
        r_rt = refresh_token(helper, base_url, auth_token)
        helper.log_info('Token refreshed. Now retrieving audit logs...')
        
        r_al = get_audit_logs(helper, base_url, r_rt)
        helper.log_info('Audit logs successfully retrieved.')
        
        audit_dumps = r_al.splitlines()
        total_audit_dumps = len(audit_dumps)
        
        helper.log_info(f'Audit logs retrieved. A total of {str(total_audit_dumps)} lines. Now working on checkpoint matching...')
        
        
        # Retrieve checkpoint 
        checkpoint = helper.get_check_point(f'{base_url}_last_line_ingested')
        
        index_to_start = -1
        if checkpoint is None:
            helper.log_info('Checkpoint is empty. All audit logs will be indexed.')
        else:
            helper.log_info('Checkpoint is not empty. Starting with new events only. Searching audit dumps for a checkpoint match...')
            for ad in audit_dumps:
                index_to_start = index_to_start + 1
                ad_line_hash = get_hexdigest_from_string(ad)
                if checkpoint == ad_line_hash: 
                    helper.log_info(f'Checkpoint found. Starting at line: {str(index_to_start + 1)}.')
                    break
            helper.log_info(f'Checkpoint engine report: {str(index_to_start + 1)}/{total_audit_dumps}.')
        
        if index_to_start + 1 != total_audit_dumps:
            new_audit_logs = audit_dumps[index_to_start + 1:]
            for line in new_audit_logs:
                cleaned_line = remove_null_bytes(line)
                if not cleaned_line:
                    continue
                event = helper.new_event(data=cleaned_line, sourcetype="bigid:audit:logs", source=helper.get_input_stanza_names(), done=True, unbroken=True)
                ew.write_event(event)
            helper.log_info('New audit logs ingested successfully')
            
            # Write checkpoint 
            helper.save_check_point(f'{base_url}_last_line_ingested', get_hexdigest_from_string(new_audit_logs[-1]))
            helper.log_info('Checkpoint saved successfully')
        else:
            helper.log_info('All audit logs available have already been ingested')
            
    except Exception as e:
        helper.log_error(f'Error streaming events: {str(e)}')

def getHttpsBaseUrl(helper):
    if not helper.get_arg('bigid_base_url').lower().startswith('https://'):
        if helper.get_arg('bigid_base_url').lower().startswith('http://'):
            _base_url = helper.get_arg('bigid_base_url').replace('http://', 'https://', 1)
            helper.log_warning('Base URL modified to use HTTPS.')
            return _base_url
        else:
            helper.log_error('Insecure base URL provided. HTTPS is required.')
            sys.exit(1)
    return helper.get_arg('bigid_base_url')
    
def refresh_token(helper, _base_url, _auth_token):
    base_url = _base_url + '/api/v1'
    endpoint_refresh = '/refresh-access-token'
    url = base_url + endpoint_refresh
    
    headers = {
        'Authorization': _auth_token,
        'Content-Type': 'application/json'
    }
    
    r = helper.send_http_request(url, 'GET', parameters=None, payload=None, headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)
    
    try:
        if r.status_code != 200:
            helper.log_error(f'Unsuccessful HTTP request for BigID Refresh Token endpoint. status_code={str(r.status_code)}')
            sys.exit(1)
        
        return r.json()["systemToken"]
    except Exception as e:
        helper.log_error(f'Error getting audit logs: {str(e)}')
        sys.exit(1)

def get_audit_logs(helper, _base_url, _auth_token):
    
    base_url = _base_url + '/api/v1'
    endpoint_auditlogs = '/audit-log'
    url = base_url + endpoint_auditlogs
    
    headers = {
        'Authorization': _auth_token,
        'Content-Type': 'application/json'
    }
    
    try:
        r = helper.send_http_request(url, 'GET', parameters=None, payload=None, headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)
    
        if r.status_code != 200:
            helper.log_error(f'Unsuccessful HTTP request for BigID Audit Log endpoint. status_code={str(r.status_code)}')
            sys.exit(1)
        
        return r.text
    
    except Exception as e:
        helper.log_error(f'Error getting audit logs: {str(e)}')
        sys.exit(1)

def get_hexdigest_from_string(line):
    line_hash = hashlib.sha256(line.strip().encode())
    return line_hash.hexdigest()

def remove_null_bytes(data):
    # If it's bytes, decode to string
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='ignore')
    # Remove null bytes from string
    return data.replace('\x00', '').replace('\\x00', '')
