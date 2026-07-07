# encoding = utf-8

import os
import sys
import time
import datetime
import csv
import tempfile
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
  
    pass

def collect_events(helper, ew):
    # Get the unique input name
    input_name = helper.get_input_stanza_names()
    checkpoint_pooling_key = f"{input_name}_pooling_key"
    
    # Check if a previous execution is still running
    pooling_status = helper.get_check_point(checkpoint_pooling_key)
    
    if pooling_status == 1:
        helper.log_info(f"CVE Input '{input_name}' is still running from a previous interval. Skipping this run.")
        return

    try:
        # Set status to 1 (Running)
        helper.save_check_point(checkpoint_pooling_key, 1)
        helper.log_info(f"Starting CVE input run for '{input_name}'. Setting pooling status to 1.")
    
        account = helper.get_arg('global_account')
        if (not account):
            return helper.log_error(f"No Account selected for the input: {input_name}")
    
        opt_retrive_data_from = account.get("retrive_data_from")
        opt_organization_route = account.get("organization_route")
        opt_scadafence_server = account.get("scadafence_server")
        opt_site_id = account.get("site_id")
        opt_api_key = account.get("api_key")
        opt_api_secret = account.get("api_secret")

        opt_page_size = account.get("page_size_cves")
        page_size = int(account.get("page_size_cves") or 1000)
        retry_count = int(account.get("api_retry_interval") or 60)

        opt_ssl_certification_enabled = account.get("ssl_certification_enabled")
    
        opt_ssl_certification_enabled = True if (opt_ssl_certification_enabled or ServerInfo(helper.context_meta["session_key"]).is_cloud_instance()) else False
    
        endpoint_for_platfrom = "/externalApi/cve/assets"
        endpoint_for_multi_site = "/gateway/api/cve/assets"

        if(opt_retrive_data_from == "platform"):
            endpoint = endpoint_for_platfrom
        else:
            endpoint = endpoint_for_multi_site
    
        opt_scadafence_server = opt_scadafence_server + endpoint
    
        opt_page = 1
        opt_size = page_size
        helper.log_info(f"Initialized with page_size: {opt_size}")
        final_cves = []

        # --- Configuration ---
        max_retries = 4
        retry_delay = retry_count

        # --- DATA COLLECTION PHASE ---
        while True:

            url = opt_scadafence_server
            parameters = {"page": opt_page, "size": opt_size}
            headers = {
                "x-api-key": opt_api_key,
                "x-api-secret": opt_api_secret,
                "accept": "application/json"
            }

            if(opt_retrive_data_from == "multi_site"):
                parameters["site_id"] = opt_site_id
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
            
            r_json = response.json()
            if not r_json or len(r_json) == 0:
                break

            for cve in r_json:
                cve['site_id'] = opt_site_id
                final_cves.append(cve)
            
            opt_page = opt_page + 1

        # --- BACKEND LOOKUP UPDATE PHASE ---
        if final_cves:
            try:
                # Setup Directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                lookup_dir = os.path.join(os.path.dirname(current_dir), "lookups")
        
                if not os.path.exists(lookup_dir):
                    os.makedirs(lookup_dir)

                for cve in final_cves:
                    # Extract Date for Filename (e.g., 2026-05-12)
                    raw_published = str(cve.get("published_on", "unknown_date"))
                    published_date = raw_published[:10] if len(raw_published) >= 10 else "unknown_date"

                    ip = str(cve.get("ip", "no_ip"))
                    cve_id = str(cve.get("cve_id", "no_cve"))
                    status = str(cve.get("status", "no_status"))
            
                    # Create the unique record format: ip--cve_id--status
                    unique_record = f"{ip}--{cve_id}--{status}"

                    filename = f"cve_data_{published_date}.csv"
                    file_path = os.path.join(lookup_dir, filename)
            
                    is_duplicate = False

                    # Search line-by-line for the unique record
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f_search:
                            for line in f_search:
                                # strip() removes the newline character for an exact match check
                                if unique_record == line.strip():
                                    is_duplicate = True
                                    break

                    # If not present, add to file and create Splunk event
                    if not is_duplicate:
                        # Append the unique key to the file on a new line
                        with open(file_path, 'a', encoding='utf-8') as f_out:
                            f_out.write(unique_record + "\n")
                            helper.log_info(f"Ingested new unique ID: {unique_record}")

                        single_event = ""
                        for key, val in cve.items():
                            single_event += key + "=" + str(val) + "\t"
                            #helper.log_info(single_event)
                        single_event+="site id="+opt_site_id+"\t"
                        #helper.log_info(single_event)
                        event = helper.new_event(single_event, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                        ew.write_event(event)

            except Exception as e:
                helper.log_error(f"Error in unique tracking logic: {str(e)}")

    except Exception as e:
        helper.log_error(f"Unexpected error in CVE collection for {input_name}: {e}")

    finally:
        helper.save_check_point(checkpoint_pooling_key, 0)
        helper.log_info(f"CVE Run completed for '{input_name}'. Pooling status reset to 0.")