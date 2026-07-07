
# encoding = utf-8

import json
import requests
import base64
import hashlib
import time
import hmac
import uuid
import datetime
import random
import gc

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    pass

def get_campaigns(helper, _grid_url, _access_key, _secret_key, _app_id, _app_key):

    base_url = _grid_url
    uri = "/api/awareness-training/phishing/campaign/get-campaign"
    url = base_url + uri
    access_key = _access_key
    secret_key = _secret_key
    app_id = _app_id
    app_key = _app_key

    request_id = str(uuid.uuid4())
    hdr_date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") + " UTC"
    dataToSign = ':'.join([hdr_date, request_id, uri, app_key])
    hmac_sha1 = hmac.new(base64.b64decode(secret_key), dataToSign.encode(), digestmod=hashlib.sha1).digest()
    sig = base64.b64encode(hmac_sha1).rstrip()

    headers = {
        'Authorization': 'MC ' + access_key + ':' + sig.decode(),
        'x-mc-app-id': app_id,
        'x-mc-date': hdr_date,
        'x-mc-req-id': request_id,
        'Content-Type': 'application/json'
    }

    payload = {
        "data": []
    }
    
    all_results = []
    page = 1
    max_retries = 10
    retry_count = 0
    
    while url and retry_count < max_retries: 
        
        response = requests.post(url=url, headers=headers, data=str(payload))
        
        if response.status_code == 200:
            
            all_results = response.json()
            url = None
            retry_count = 0
            
        elif response.status_code > 499:
            
            retry_count += 1
            if retry_count < max_retries:
                # Sleep for 10 seconds and then retry the request
                helper.log_warning(f'API query failed due to http_status={response.status_code} error (Mimecast server error). Will retry for a maximum of 10x.')
                time.sleep(10)
            else:
                helper.log_error(f'Failed after {max_retries} retries. Status code: {response.status_code}')
                break
            
        else:
            helper.log_error(f'Failed to retrieve campaigns summary data. Status code: {response.status_code}')
            break
    
    return all_results
    
def get_userdata(helper, _grid_url, _access_key, _secret_key, _app_id, _app_key, _campaignId, _pageToken):

        base_url = _grid_url
        uri = "/api/awareness-training/phishing/campaign/get-user-data"
        url = base_url + uri
        access_key = _access_key
        secret_key = _secret_key
        app_id = _app_id
        app_key = _app_key

        request_id = str(uuid.uuid4())
        hdr_date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") + " UTC"
        dataToSign = ':'.join([hdr_date, request_id, uri, app_key])
        hmac_sha1 = hmac.new(base64.b64decode(secret_key), dataToSign.encode(), digestmod=hashlib.sha1).digest()
        sig = base64.b64encode(hmac_sha1).rstrip()

        headers = {
            'Authorization': 'MC ' + access_key + ':' + sig.decode(),
            'x-mc-app-id': app_id,
            'x-mc-date': hdr_date,
            'x-mc-req-id': request_id,
            'Content-Type': 'application/json'
        }

        payload = {
            'meta': {
                "pagination": {
                    "pageSize": 100,
                    "pageToken": _pageToken
                }
            },
            'data': [
                {
                    "id": _campaignId,
                }
            ]
        }
        
        all_results = []
        page = 1
        max_retries = 10
        retry_count = 0
        
        while url and retry_count < max_retries: 
            
            response = requests.post(url=url, headers=headers, data=str(payload))
            
            if response.status_code == 200:
                
                all_results = response.json()
                url = None
                retry_count = 0
                
            elif response.status_code > 499:
                
                retry_count += 1
                if retry_count < max_retries:
                    # Sleep for 10 seconds and then retry the request
                    helper.log_warning(f'API query failed due to http_status={response.status_code} error (Mimecast server error). Will retry for a maximum of 10x.')
                    time.sleep(10)
                else:
                    helper.log_error(f'Failed after {max_retries} retries. Status code: {response.status_code}')
                    break
                
            else:
                helper.log_error(f'Failed to retrieve user data. Status code: {response.status_code}')
                break
        
        return all_results
        
def parse_campaign_dates(helper, date_str, ret_zero_if_err):
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError as e:
        helper.log_error(f'Date parsing encountered an error: {e}')
        
        if ret_zero_if_err:
            return 0
        else:
            return None

def collect_events(helper, ew):
    
    stanzaname = helper.get_input_stanza_names()
    grid_url = helper.get_arg('grid_url')
    access_key = helper.get_arg('access_key')
    secret_key = helper.get_arg('secret_key')
    app_id = helper.get_arg('app_id')
    app_key = helper.get_arg('app_key')
    campaign_parent_name = helper.get_arg('campaign_parent_name')
    campaign_launched_date = helper.get_arg('campaign_launched_date')
    campaign_end_date = helper.get_arg('campaign_end_date')
    include_all_user_data = helper.get_arg('include_all_user_data')
    
    # Phase 1: Date validation and parsing
    
    ld_epoch = parse_campaign_dates(helper, campaign_launched_date, False)
    
    if ld_epoch is None:
        helper.log_warning(f'Failed to parse the configured Campaign Launched Date "{campaign_launched_date}". Revisit the Inputs configuration and double-check the format to have exactly: YYYY-mm-ddTHH:MM:SS+0000. This collection will not continue')
        return 0
    
    ced_epoch = parse_campaign_dates(helper, campaign_end_date, False)
    
    if ced_epoch is None:
        helper.log_warning(f'Failed to parse the configured Campaign End Date "{campaign_end_date}". Revisit the Inputs configuration and double-check the format to have exactly: YYYY-mm-ddTHH:MM:SS+0000. This collection will not continue')
        return 0
    
    if ld_epoch > ced_epoch:
        helper.log_error(f'Launched Date cannot be after the End Date. Skipping this scheduled collection.')
        return 0
    
    # Phase 2: Phishing Campaign Summary and Result
    
    campaign_summary = get_campaigns(helper, grid_url, access_key, secret_key, app_id, app_key)
    
    if len(campaign_summary)==0 or campaign_summary is None:
        helper.log_warning(f'No Phishing Campaigns data was retrieved. Exiting.')
        return 0
    
    cs_err = ""
    
    if campaign_summary.get('fail', []):
        cs_err = campaign_summary['fail'][0]['errors'][0]['message']
    
    if cs_err:
        helper.log_error(f'Retrieving Campaigns Summary resulted to an error: {cs_err}. Exiting this collection.')
        return 0
    
    helper.log_info(f'Retrieving Phishing Campaigns result/summary data.')
    
    ld_epoch_simple = datetime.datetime.strftime(ld_epoch, '%Y-%m-%d')
    ed_epoch_simple = datetime.datetime.strftime(ced_epoch, '%Y-%m-%d')
    
    helper.log_info(f'Configuration: campaign_name="{campaign_parent_name}" between launch_date={ld_epoch_simple} and end_date={ed_epoch_simple} all_users={include_all_user_data}')
    
    cs = campaign_summary.get('data')
    
    helper.log_info(f'A total of {len(cs)} Phishing Campaign summary results were retrieved.')
    helper.log_info(f'Looping through all Phishing Campaigns to get user data. This may take some time...')
    helper.log_info(f'Skipping campaigns outside of CLD and CED.')
    
    skip_ctr_campaigns = 0
    skip_ctr_userdata = 0
    
    meta_source = f'mimecast_phishing_campaigns://{stanzaname}'
    
    for c in cs:
        
        this_c_name = c.get('name')
        this_c_id = c.get('id')
        this_c_launch_date = c.get('launchDate')
        
        this_c_launch_date_epoch = parse_campaign_dates(helper, this_c_launch_date, False)
        
        if this_c_launch_date_epoch is None:
            helper.log_info(f'Skipping {this_c_name} because of failure to retrieve its launchDate property.')
            skip_ctr_campaigns = skip_ctr_campaigns + 1
            continue
        
        if this_c_launch_date_epoch < ld_epoch or this_c_launch_date_epoch > ced_epoch:
            skip_ctr_campaigns = skip_ctr_campaigns + 1
            continue
        
        data = json.dumps(c, separators=(',', ':'))
        event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype='mc:at:phishcampaigns:summary', data=data)
        ew.write_event(event)
        
        # Phase 3: Phishing Campaign User Data and Results
        
        next_page = ""

        while next_page != "n/a":

            user_data_result = get_userdata(helper, grid_url, access_key, secret_key, app_id, app_key, this_c_id, next_page)
            
            if len(user_data_result)==0 or user_data_result is None:
                helper.log_info(f'No user data were retrieved from "{this_c_name}".')
                continue
            
            if "next" in user_data_result.get('meta', {}).get('pagination', {}):
                next_page = user_data_result.get('meta', {}).get('pagination', {}).get('next', 'n/a')
            else:
                next_page = "n/a"
                
            # Rather than collecting all user data in one JSON heap-resourced variable, we are
            # ingesting every user data for every iteration to free up memory
            
            if random.random() < 0.03:
                helper.log_info(f'TA-mimecastcampaigns is alive and is still collecting User Data...')
            
            for user_data in user_data_result["data"]:
                
                for u in user_data["items"]:
                    
                    zero_epoch = "1970-01-01T00:00:00+0000"
                    
                    time_clicked = parse_campaign_dates(helper, u.get('timeClicked', zero_epoch), True)
                    time_opened = parse_campaign_dates(helper, u.get('timeOpened', zero_epoch), True)
                    time_reported = parse_campaign_dates(helper, u.get('timeReported', zero_epoch), True)
                    time_submitted = parse_campaign_dates(helper, u.get('timeSubmitted', zero_epoch), True)
                    
                    activity_timestamp = max(time_clicked, time_opened, time_reported, time_submitted, this_c_launch_date_epoch)
                    
                    if not include_all_user_data:
                        if activity_timestamp > ced_epoch:
                            skip_ctr_userdata = skip_ctr_userdata + 1
                            continue
                        
                    outside_campaign_period = "True" if activity_timestamp > ced_epoch else "False"
                        
                    u["campaignId"] = this_c_id
                    u["campaignName"] = this_c_name
                    u["campaign"] = campaign_parent_name
                    u["launchDate"] = this_c_launch_date
                    u["campaignEndDate"] = campaign_end_date
                    u["activityTimestamp"] = datetime.datetime.strftime(activity_timestamp, '%Y-%m-%dT%H:%M:%S%z')
                    u["isOutsideCampaignPeriod"] = outside_campaign_period
                    
                    data = json.dumps(u, separators=(',', ':'))
                    event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                    ew.write_event(event)
            
            user_data_result = None
            gc.collect()
                    
    
    helper.log_info(f'Skipped a total of {skip_ctr_campaigns} campaigns outside the configured launched and end date.')
    
    if not include_all_user_data:
        helper.log_info(f'Skipped a total of {skip_ctr_userdata} user activities because the action (e.g. Click Time, Reported Time) date is beyond this Input\'s configured Campaign End Date.')
    
    helper.log_info('End of collection. Reaching this part means a successful data collection.')
    
    