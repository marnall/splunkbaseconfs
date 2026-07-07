# encoding = utf-8

import app_common as utils

import json
import requests
import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
from dateutil.parser import parse as date_parse

APP_VERSION = utils.get_version()


def log_formater(helper, obj):
    formater = {
        'access': access_format,
        # 'activity': activity_format,
        # 'category': category_format,
        'result': result_format,
        'user': user_format,
        'role': role_format,
        # 'loggedTime': iso_format,
        # 'details': details_format,
    }
    try:
        for handle in formater.values():
            handle(helper, obj)
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] audit log format error: %s" % str(e))


def iso_format(helper, obj):
    try:
        if 'loggedTime' in obj:
            obj['loggedTime'] = date_parse(obj['loggedTime']).isoformat()
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] loggedTime field format error: %s" % str(e))


def result_format(helper, obj):
    try:
        if 'result' in obj:
            obj['result'] = 'Successful' if obj['result'] else 'Unsuccessful'
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] result field format error: %s" % str(e))


def user_format(helper, obj):
    try:
        if len(obj.get('user', '').strip()) == 0:
            obj['user'] = 'Root Account'
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] user field format error: %s" % str(e))


def role_format(helper, obj):
    try:
        if len(obj.get('role', '').strip()) == 0:
            obj['role'] = 'Master Administrator'
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] role field format error: %s" % str(e))


def details_format(helper, obj):
    try:
        mapping = {
            'ipAddr': 'IP address',
            'user': 'User account',
            'role': 'Role',
            'accessLevel': 'Access level',
            'product': 'Product',
            'tmAccount': 'Trend Micro Account',
            'hostName': 'Host name',
            'modelName': 'Model name',
            'workbenchId': 'Workbench ID',
            'status': 'Status',
            'fileName': 'File name',
            'messageId': 'Message ID',
            'mailbox': 'Mailbox',
            'packageId': 'Package ID',
            'domain': 'Domain',
            'url': 'URL',
            'port': 'Port',
            'sha1': 'SHA1',
            'sha256': 'SHA256',
            'filterId': 'Filter ID',
            'fieldName': 'Field name',
            'matchType': 'Match type',
            'value': 'Value',
            'description': 'Description',
            'clpAccountId': 'CLP account ID',
            'errorCode': 'Error code',
            'ac': 'AC',
            'deviceId': 'Device ID',
            'description': 'Description',
            'mailBox': 'Mailbox',
            'productCode': 'Product code',
            'requestId': 'Request ID',
            'account': 'Account Name',
            'cltIPAddr': 'Endpoint IP address',
            'devIPAddr': 'Appliance IP address',
            'devIPv6Addr': 'Appliance IPv6 address',
            'devName': 'Appliance name',
            'devPrimDNS': 'Appliance primary DNS server',
            'devSecDNS': 'Appliance secondary DNS server',
            'devProxyAddr': 'Appliance proxy address',
            'devProxyType': 'Appliance proxy Type',
            'devNTPAddr': 'Appliance NTP address',
            'devFWVer': 'Appliance firmware version',
            'spsStatus': 'Smart Protection Services',
            'tpiStatus': 'Third-Party Integration',
            'auStatus': 'Scheduled update',
            'auInterval': 'Scheduled update interval',
            'autoUpgStatus': 'Automatic update',
            'autoUpgSched': 'Automatic update schedule',
            'certIssuedBy': 'Certificate issued by',
            'certIssuedTo': 'Certificate issued to',
            'certValidity': 'Certificate validity',
            'downloadSpeed': 'Download speed',
            'soClass': 'VASO/UDSO type',
            'source': 'Source',
            'originalIncidentId': 'Original Incident ID',
            'targetIncidentId': 'Target Incident ID',
            'serverAddress': 'Server address',
            'port': 'Port',
            'secureConnection': 'Secure connection',
            'objectType': 'Object type',
            'action': 'Action',
            'frequencyMin': 'Frequency (minutes)',
            'applicationName': 'Application name',
            'batchSize': 'Batch size',
            'timeoutMin': 'Timeout (minutes)',
            'riskLevel': 'Risk level',
            'urlParameters': 'URL parameters',
            'httpEnable': 'Enabled HTTP',
            'request': 'Request',
            'lauStatus': 'ActiveUpdate',
            'sosStatus': 'Suspicious Object List synchronization',
            'lauList': 'ActiveUpdate URL or product list',
            'apiKey': 'New API key'
        }
        if 'details' in obj and isinstance(obj['details'], dict):
            output_str = ''
            for field in obj['details']:
                if field in mapping:
                    output_str += '{}: {}; '.format(
                        mapping[field], obj['details'][field])
                else:
                    output_str += '{}: {}; '.format(field,
                                                    obj['details'][field])
            obj['details'] = output_str
        elif 'details' in obj and isinstance(obj['details'], list):
            output_str = ''
            for inx, item in enumerate(obj['details']):
                output_str += '{}: {}; '.format(
                    inx,
                    json.dumps(item, separators=(',', ':'))
                )
            obj['details'] = output_str
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] details field format error: %s" % str(e))


def access_format(helper, obj):
    try:
        mapping = {
            0: 'Console',
            1: 'API',
            9: 'All',
        }
        if 'access' in obj:
            obj['access'] = mapping.get(int(obj['access']), 'Unknown')
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] access field format error: %s" % str(e))


def activity_format(helper, obj):
    try:
        mapping = {
            '01': {
                '01': 'Log on',
                '02': 'Log off'
            },
            '02': {
                '01': 'Enable single sign-on',
                '02': 'Disable single sign-on'
            },
            '03': {
                '01': 'Add user account',
                '02': 'Delete user account',
                '03': 'Enable user account',
                '04': 'Disable user account',
                '05': 'Reset password',
                '06': 'Change role',
                '07': 'Change access level'
            },
            '04': {
                '01': 'Connect product',
                '02': 'Unregister product'
            },
            '05': {
                '01': 'Copy SIEM authentication token',
                '02': 'Add email notifications\' recipient',
                '03': 'Send test message'
            },
            '06': {
                '01': 'Enable detection model',
                '02': 'Disable detection model',
                '03': 'Remove exception'
            },
            '07': {
                '01': 'Modify alert details',
                '02': 'Add exception'
            },
            '08': {
                '01': 'Create task: Isolate endpoint',
                '02': 'Create task: Restore connection',
                '03': 'Create task: Allow traffic',
                '04': 'Create task: Terminate',
                '05': 'Create task: Add to Block List',
                '06': 'Create task: Remove from Block List',
                '07': 'Create task: Collect file',
                '08': 'Create task: Quarantine message',
                '09': 'Create task: Delete message',
                '0a': 'Create task: Run Trend Micro Investigation Kit',
                '0b': 'Download file',
                '10': 'Remote shell',
                '11': 'Custom Script'
            },
            '09': {
                '01': 'RCA Generated',
                '02': 'RCA Deleted'
            },
            '0b': {
                '01': 'Enable Managed XDR',
                '02': 'Disable Managed XDR',
                '03': 'Enable automatic response approval',
                '04': 'Disable automatic response approval',
                '05': 'Specify notification recipient',
                '06': 'Create response action request',
                '07': 'Approve response action request (auto)',
                '08': 'Approve response action request (manual)',
                '09': 'Reject response action request',
                '0a': 'Remove entitlement',
                '0b': 'Create Managed XDR account token',
                '0c': 'Renew Managed XDR account token',
                '0d': 'Revoke Managed XDR account token'
            },
            '0c': {
                '01': 'Invite user',
                '02': 'Remove enrollment',
                '03': 'Invite Azure AD group',
                '04': 'Delete Azure AD group',
                '05': 'Enroll device',
                '06': 'Unenroll device',
                '07': 'Create policy',
                '08': 'Replicate policy',
                '09': 'Modify policy',
                '0a': 'Delete policy'
            },
            '0d': {
                '01': 'Disconnect network sensor',
                '02': 'Select product',
                '03': 'Reset Network Inventory',
                '05': 'Import Domain Exceptions list',
                '06': 'Import Priority Watch List',
                '07': 'Import Registered Services list',
                '08': 'Import Trusted Internal Network list'
            },
            '11': {
                '01': 'Add intelligence feed',
                '02': 'Modify intelligence feed',
                '03': 'Delete intelligence feed',
                '11': 'Configure Check Point Open Platform for Security',
                '12': 'Reset Check Point Open Platform for Security',
                '21': 'Configure Palo Alto Panorama',
                '22': 'Reset Palo Alto Panorama',
                '31': 'Configure ProxySG and Advanced Secure Gateway',
                '32': 'Reset ProxySG and Advanced Secure Gateway',
                '41': 'Configure QRadar on Cloud STIX-Shifter connector'
            },
            '13': {
                '01': 'Log on',
                '02': 'Log off',
                '03': 'Register',
                '04': 'Unregister',
                '05': 'Configure IP address',
                '06': 'Configure appliance name',
                '07': 'Configure DNS',
                '08': 'Configure proxy',
                '09': 'Configure NTP',
                '0a': 'Change password',
                '0b': 'Shut down',
                '0c': 'Restart',
                '51': 'Download Service Gateway Virtual Appliance',
                '52': 'Configure Service Gateway',
                '53': 'Disconnect Service Gateway',
                '54': 'Start manual update',
                '55': 'Change API key'
            },
            '14': {
                '01': 'Add suspicious object / Edit suspicious object',
                '02': 'Delete suspicious object',
                '03': 'Import file',
                '05': 'Edit default settings',
                '06': 'Add to exception list',
                '07': 'Delete exception',
                '10': 'Download STIX intelligence report',
                '14': 'Trigger manual sweeping'
            },
            '1c': {
                '21': 'Group activated',
                '22': 'Group created',
                '23': 'Group deleted'
            },
            '1d': {
                '01': 'Endpoint security settings saved'
            }
        }
        if 'category' in obj and 'activity' in obj:
            if obj['category'] in mapping:
                category = mapping[obj['category']]
                obj['activity'] = category.get(obj['activity'], 'Unknown')
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] activity field format error: %s" % str(e))


def category_format(helper, obj):
    try:
        mapping = {
            '01': 'Logon',
            '02': 'Single Sign-On',
            '03': 'Account Management',
            '04': 'Product Connector',
            '05': 'SIEM Connector',
            '06': 'Detection Model Management',
            '07': 'Workbench',
            '08': 'Response',
            '09': 'Search',
            '10': 'Flywheel',
            '0b': 'Managed XDR',
            '0c': 'Mobile Security',
            '0d': 'Network Inventory',
            '11': 'Third-party Integration',
            '13': 'Service Gateway Inventory',
            '14': 'Threat Intelligence',
            '19': 'Identity and Risk Insights App',
            '1a': 'Cloud App Visibility',
            '1b': 'ZTSA Zero Trust Secure Access App',
            '1c': 'Endpoint Inventory',
            '1d': 'Security Configuration',
        }
        if 'category' in obj:
            obj['category'] = mapping.get(obj['category'], 'Unknown')
    except Exception as e:
        helper.log_error(
            "[TrendMicro Audit] category field format error: %s" % str(e))


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    try:
        interval = definition.parameters.get('interval', None)
        if interval is not None and int(interval) < 10:
            raise ValueError(
                "The minimum public API access interval cannot be less than 10 seconds.")
    except ValueError as e:
        # Re-raise with same message but cleaner presentation
        raise ValueError(str(e))
    except Exception as e:
        # Log the actual error for debugging
        helper.log_error(f"Validation error: {str(e)}")
        raise ValueError("Validation failed. Please check input configuration.")

def collect_events_for_one_consumer(helper, ew, endpoint, token):
    cid = utils.extractCID(token)
    STANZA = helper.get_input_stanza_names()
    helper.log_info("[TrendMicro Audit] <%s> get stanza names: %s" % (cid, STANZA))
    polling = helper.get_arg('interval')
    helper.log_info("[TrendMicro Audit] <%s> get interval: %s" % (cid, polling))
    backoff_time = float(helper.get_global_setting("backoff_time") or 10)
    helper.log_info("[TrendMicro Audit] <%s> get backoff_time: %d" % (cid,backoff_time))
    https_proxy = str(helper.get_global_setting("https_proxy")).strip()

    parse_url = urlparse(endpoint)
    endpoint = "{}://{}".format(parse_url.scheme, parse_url.netloc)
    helper.log_info("[TrendMicro Audit] <%s> get endpoint: %s" % (cid, endpoint))

    url_path = '/v3.0/xdr/portal/auditLog/search'

    nowTime = utils.format_iso_time()

    file_context = utils.fetch_context(STANZA, cid, {
        'startTime': utils.format_iso_time(delta_sec=30)
    })

    query_params = {
        'dateTimeTarget': 'ingestedDateTime',
        'pageIndex': 1,
        'pageSize': 100,
        'period': 30,
        'categories': '',
        'detail': '',
        'accessType': 9,
    }
    query_params["endTime"] = nowTime

    query_params["startTime"] = file_context.get('startTime', nowTime)

    # query_params = {
    #     'pageIndex': 1,
    #     'pageSize': 100,
    #     'period': 30,
    #     'categories': '',
    #     'detail': '',
    #     'accessType': 9,
    #     'startTime': '2021-05-06T00:00:00.000Z',
    #     'endTime': '2021-05-07T12:00:00.000Z'
    # }
    proxies = {}

    if https_proxy != None and https_proxy.lower() != "none":
        proxies["https"] = https_proxy

    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json;charset=utf-8',
        "User-Agent": "TMXDRSplunkAddon/" + str(APP_VERSION)
    }

    # Skip API call if start and end time are the same to avoid errors
    if query_params["startTime"] == query_params["endTime"]:
        helper.log_info(
            "[TrendMicro Audit] <%s> startTime equals endTime, skipping API call" % cid)
        utils.update_context(STANZA, cid, 'startTime', nowTime)
        return 0

    helper.log_info("[TrendMicro Audit] <%s> request params: %s" %
                    (cid, str(query_params)))

    request_help = utils.request_help(2, backoff_time)

    try:
        res = request_help(
            url=endpoint + url_path,
            method="GET",
            parameters=query_params,
            headers=headers,
            proxies=proxies
        )
        res.raise_for_status()
        data = res.json()["data"]
        helper.log_info("[TrendMicro Audit] <%s> response page %d: %s" %
                        (cid, query_params['pageIndex'], str(data)))
        cursor = len(data["items"])
        audit_logs = data["items"]
        total_counts = data['totalCounts']

        while cursor < total_counts:
            query_params['pageIndex'] += 1
            res = request_help(
                url=endpoint + url_path,
                method="GET",
                parameters=query_params,
                headers=headers,
                proxies=proxies
            )
            res.raise_for_status()
            data = res.json()["data"]
            if len(data["items"]) == 0:
                break
            cursor += len(data["items"])
            helper.log_info("[TrendMicro Audit] <%s> response page %d: %s" % (
                cid, query_params['pageIndex'], str(data)))
            audit_logs.extend(data["items"])
    except requests.exceptions.Timeout as e:
        helper.log_error(
            "[TrendMicro Audit] <%s> audit log request timeout error: %s" % (cid, str(e)))
        return 1
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            "[TrendMicro Audit] <%s> audit log request error: %s %s" % (cid, str(e), str(endpoint)))
        return 1
    except Exception as e:
        helper.log_error("[TrendMicro Audit] <%s> audit log exception: %s" % (cid, str(e)))
        return 1

    helper.log_info("[TrendMicro Audit] <%s> get totalCount: %d" % (cid, total_counts))

    helper.log_info(f"[TrendMicro Audit] <{cid}> events start writing...")
    write_count = 0
    for audit in audit_logs:
        log_formater(helper, audit)
        audit['customerID'] = cid
        event = helper.new_event(source=helper.get_input_type(), time=datetime.datetime.now(),
                                 host=None, index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), data=json.dumps(audit),
                                 done=True, unbroken=True)
        ew.write_event(event)
        write_count += 1
        if not write_count % 2000:
            helper.log_info(f"[TrendMicro Audit] <{cid}> {write_count} events has been written")
    if write_count % 2000:
        helper.log_info(f"[TrendMicro Audit] <{cid}> {write_count} events has been written")


    utils.update_context(STANZA,cid,  'startTime', nowTime)
    # utils.update_tpc_metrics(endpoint, headers, proxies)
    helper.log_info(f"[TrendMicro Audit] <{cid}> events writing completed")
    return 0

def collect_events(helper, ew):
    endpoint = helper.get_arg('global_account')['endpoint']
    tokens = helper.get_arg('global_account')['token']
    if (not endpoint) or (not tokens):
        helper.log_info("[TrendMicro Audit] no valid config, will pass")
        return 0
    tokens = utils.split_token(tokens)
    return_status = 0
    for token in tokens:
        return_status = return_status | collect_events_for_one_consumer(helper, ew, endpoint, token)
    return return_status

    