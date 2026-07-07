
# encoding = utf-8

import os
import sys
import time
import datetime
from solnlib.server_info import ServerInfo

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
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # retrive_data_from = definition.parameters.get('retrive_data_from', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    input_name = helper.get_input_stanza_names()
    checkpoint_pooling_key = f"{input_name}_pooling_key"
    
    # Check if a previous execution is still running
    pooling_status = helper.get_check_point(checkpoint_pooling_key)
    
    if pooling_status == 1:
        helper.log_info(f"Asset Input '{input_name}' is still running from a previous interval. Skipping this run.")
        return
    try:
        # Set status to 1 (Running)
        helper.save_check_point(checkpoint_pooling_key, 1)
        helper.log_info(f"Starting Assets input run for '{input_name}'. Setting pooling status to 1.")

        account = helper.get_arg('global_account')
        if (not account):
            return helper.log_error("No Account selected for the input for Asset")
        opt_retrive_data_from = account.get("retrive_data_from")
        opt_organization_route = account.get("organization_route")
        opt_scadafence_server = account.get("scadafence_server")
        opt_page_size = account.get("page_size_asset")
        page_size = int(account.get("page_size_asset") or 1000)
        retry_count = int(account.get("api_retry_interval") or 60)

        opt_site_id = account.get("site_id")
        opt_api_key = account.get("api_key")
        opt_api_secret = account.get("api_secret")
    
        opt_ssl_certification_enabled = account.get("ssl_certification_enabled")

        opt_ssl_certification_enabled = True if (opt_ssl_certification_enabled or ServerInfo(helper.context_meta["session_key"]).is_cloud_instance()) else False
        endpoint_for_platfrom = "/externalApi/assets"
        endpoint_for_multi_site = "/gateway/api/assets"

        # Define checkpoint key
        checkpoint_key = f"scadafence_assets_last_run_{input_name}"    
        last_run_time = helper.get_check_point(checkpoint_key)
    
        if not last_run_time:
            last_run_time = "1970-01-01T00:00:00.000Z"
            helper.log_info(f"First run: Initializing full pull from {last_run_time}")
        else:
            helper.log_info(f"Subsequent run: Fetching updates since {last_run_time}")

        # This variable will track the newest 'lastSeen' found in the data. We start it with the current checkpoint value
        newest_checkpoint = last_run_time

        if(opt_retrive_data_from == "platform"):
            endpoint = endpoint_for_platfrom
        else:
            endpoint = endpoint_for_multi_site

        opt_scadafence_server = opt_scadafence_server + endpoint
    
        opt_page = 1
        opt_size = page_size
        helper.log_info(f"Initialized with page_size: {opt_size}")
        final_assets = []

        # --- Configuration ---
        max_retries = 4
        retry_delay = retry_count

        while True:

            url = opt_scadafence_server

            # Normalize format: strip the milliseconds/Z to match YYYY-MM-DDTHH:mm:ss for api call "2025-11-21T09:43:49.000Z" -> "2025-11-21T09:43:49"
            normalized_last_run_time = last_run_time.split('.')[0].replace('Z', '')

            parameters = {
                "page": opt_page, 
                "size": opt_size, 
                "from_last_seen": normalized_last_run_time
            }
        
            headers = {
                "x-api-key": opt_api_key,
                "x-api-secret": opt_api_secret,
                "accept": "application/json"
            }

            if(opt_retrive_data_from == "multi_site"):
                parameters["site_id"] = opt_site_id
                parameters["order"] = "ip"
                parameters["sort"] = "asc"
                headers['x-org'] = opt_organization_route

            # --- Retry Logic Loop ---
            attempt = 0
            success = False

            while attempt < max_retries:
                try:
                    response = helper.send_http_request(
                        url, "GET", parameters=parameters, payload=None,
                        headers=headers, cookies=None, verify=opt_ssl_certification_enabled,
                        timeout=None, use_proxy=False
                    )
            
                    if response.status_code == 200:
                        success = True
                        break
                    elif response.status_code in [429, 500, 502, 503, 504]:
                        # Retryable errors: Rate limited or Server issues
                        attempt += 1
                        wait = retry_delay * (2 ** (attempt - 1)) # Exponential backoff: 60s, 120s, 180s
                        helper.log_info(f"Request failed ({response.status_code}). Retry {attempt}/{max_retries} in {wait}s...")
                        time.sleep(wait)
                    else:
                        # Critical errors (401, 403, 404): No point in retrying
                        helper.log_error(f"Critical API Error: {response.status_code} - {response.text}")
                        response.raise_for_status()
                        break
                except Exception as e:
                    attempt += 1
                    helper.log_error(f"Connection error: {e}. Retry {attempt}/{max_retries}...")
                    time.sleep(retry_delay)

            if not success:
                helper.log_error("Failed to fetch data after maximum retries. Exiting loop.")
                break

            # response = helper.send_http_request(url, "GET", parameters=parameters, payload=None,
            #                                     headers=headers, cookies=None, verify=opt_ssl_certification_enabled, cert=None,
            #                                     timeout=None, use_proxy=False)

            # r_status = response.status_code
            # if r_status != 200:
            #     response.raise_for_status()
            #     break

            r_json = response.json()
            if len(r_json) == 0:
                helper.log_debug(f"No assets in page number {opt_page}")
                break

            for asset in r_json:
                asset_time_str = asset.get("lastSeen")

                # Only process and save the asset if it is strictly NEWER than our last run
                if asset_time_str and asset_time_str > last_run_time:
                    final_assets.append(asset)

                    # Update our tracker for the next checkpoint
                    if asset_time_str > newest_checkpoint:
                        newest_checkpoint = asset_time_str
                else:
                    # This log is optional, but helps you see it working in debug mode
                    helper.log_debug(f"Skipping duplicate asset: {asset.get('ip')} lastSeen: {asset_time_str}")

            opt_page = opt_page + 1
    
        # Write events to Splunk
        for asset in final_assets:
            single_event = ""
            for key, val in asset.items():
                single_event += key + "=" + str(val) + "\t"
            single_event += "site id=" + str(opt_site_id) + "\t"
            event = helper.new_event(single_event, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
            ew.write_event(event)

        # Save the higher lastSeen mark found during the run
        if newest_checkpoint > last_run_time:
            helper.save_check_point(checkpoint_key, newest_checkpoint)
            helper.log_info(f"Successfully saved checkpoint to most recent lastSeen: {newest_checkpoint}")
        else:
            helper.log_info("No newer records found; checkpoint not updated.")

    except Exception as e:
        helper.log_error(f"Unexpected error in CVE collection for {input_name}: {e}")

    finally:
        helper.save_check_point(checkpoint_pooling_key, 0)
        helper.log_info(f"CVE Run completed for '{input_name}'. Pooling status reset to 0.")