# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

# encoding = utf-8

import os
import sys
import time
import datetime
import requests
from xml.sax.saxutils import escape

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
    api_url = definition.parameters.get('api_url', None)
    api_key = definition.parameters.get('api_key', None)
    account_name = definition.parameters.get('account_name', None)
    hec_url = definition.parameters.get('hec_url', None)
    hec_token = definition.parameters.get('hec_token', None)
    anchore_verify_ssl = definition.parameters.get('anchore_verify_ssl', None)
    hec_verify_ssl = definition.parameters.get('hec_verify_ssl', None)

    # --- Validation Logic ---

    # First, check if the parameter is missing entirely
    if anchore_verify_ssl is None :
        raise ValueError("'Anchore Verify SSL' parameter must be provided (e.g., True or False).")

    if hec_verify_ssl is None :
        raise ValueError("'HEC Verify SSL' parameter must be provided (e.g., True or False).")
        
    # --- THE FIX: Convert the input to a strict boolean ---
    # bool(1) becomes True, bool(0) becomes False, bool(True) stays True.
    # is_anchore_ssl_verify_enabled = bool(anchore_verify_ssl)
    # is_hec_ssl_verify_enabled = bool(hec_verify_ssl)

    is_anchore_ssl_verify_enabled = str(anchore_verify_ssl).lower() in ['1', 'true']
    is_hec_ssl_verify_enabled = str(hec_verify_ssl).lower() in ['1', 'true']
    
    # --- Phase 2: Perform Anchore API Connection Test ---
    try:
        # Construct the full URL for the status endpoint
        status_url = api_url.strip().rstrip('/') + '/health'
        
        headers = {
            'accept': 'application/json'
        }
        
        helper.log_info(f"Validating connection and authentication to {status_url}")

        # Make the GET request, now including authentication and the new timeout
        # For Anchore API, the username is the key and the password is an empty string.
        response = requests.get(
            status_url,
            headers=headers,
            verify=is_hec_ssl_verify_enabled,
            timeout=30  # <-- Timeout updated to 30 seconds as requested
        )
        # Proxy is not supoorted inside validation, hence used requests
        # response = helper.send_http_request(
        #     status_url,
        #     'GET',
        #     parameters=None,
        #     payload=None,
        #     headers=headers,
        #     cookies=None,
        #     verify=is_anchore_ssl_verify_enabled,
        #     cert=None,
        #     timeout=30,
        #     use_proxy=True
        # )

    #     # --- RESTRUCTURED AND CORRECTED ERROR HANDLING ---
    #     if response.status_code == 200:
    #         # Success Path: Verify the body is valid JSON as expected.
    #         response.json()
    #         helper.log_info("Anchore API validation successful.")
        
    #     elif response.status_code == 401:
    #         # Specific Failure Path for 401: Raise a clear, direct error.
    #         raise ValueError(f"Anchore API validation failed: 401 Unauthorized. The API Key is invalid or lacks permissions. {response.text}")
            
    #     else:
    #         # All Other Failure Paths (e.g., 500, 404): Try to get a detailed message from the body.
    #         try:
    #             error_json = response.json()
    #             error_message = error_json.get('message', response.text)
    #             raise ValueError(f"Anchore API validation failed. Status: {response.status_code}. Message: '{error_message}'")
    #         except requests.exceptions.JSONDecodeError:
    #             # If the body isn't JSON, just show the raw text.
    #             raise ValueError(f"Anchore API validation failed. Status: {response.status_code}. Response: {response.text}")

    # except requests.exceptions.RequestException as e:
    #     raise ValueError(f"Anchore API connection failed. Error: {e}")
    # except Exception as e:
    #     # This will now only catch truly unexpected errors, not our custom ValueErrors.
    #     raise ValueError(f"An unexpected error occurred during Anchore API validation: {e}")


        # Check for non-200 status codes (401 for bad key, 404 for bad URL, etc.)
        # --- Enhanced Error Handling Block ---
        if response.status_code != 200:
            raise ValueError(f"Anchore API URL test failed. Status: {response.status_code}. Response: {escape(response.text)}. Please check the API URL.")
        
        helper.log_info("Anchore API URL and connectivity validation successful.")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Anchore API connection failed. Could not connect to host. Error: {escape(str(e))}")



    # --- Phase 3: Perform Splunk HEC Token and Endpoint Validation ---
    try:
        # Use the main collector endpoint for token validation
        hec_health_url = hec_url.strip().rstrip('/') + '/health'
        helper.log_info(f"Validating HEC URL and connectivity to {hec_health_url}.")

        # Make a simple GET request without any authentication headers.
        hec_response = requests.get(
            hec_health_url,
            verify=is_hec_ssl_verify_enabled,
            timeout=30
        )

        # A 200 status code is all we need to confirm the endpoint is reachable.
        if hec_response.status_code != 200:
            raise ValueError(f"HEC URL test failed. Status: {hec_response.status_code}. Response: {escape(hec_response.text)}. Please check the HEC URL.")
        
        # Optional: Check the response body to be thorough.
        hec_response.json()
        helper.log_info("HEC URL and connectivity validation successful.")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"HEC connection failed. Could not connect to host. Error: {escape(str(e))}")

    # If the function completes without raising an exception, the validation is successful.

import json
import base64
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timezone

# Thread-safe logging and shared session
log_lock = threading.Lock()
session_lock = threading.Lock()
hec_session = None

def thread_safe_print(helper, message, level='info'):
    """Thread-safe logging function"""
    with log_lock:
        if level == 'info':
            helper.log_info(message)
        elif level == 'error':
            helper.log_error(message)
        elif level == 'warning':
            helper.log_warning(message)

def get_hec_session(helper):
    """Get or create a shared HTTP session with connection pooling"""
    global hec_session
    with session_lock:
        if hec_session is None:
            helper.log_info("Creating new HEC session with connection pooling and retries.")
            hec_session = requests.Session()
            
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"]
            )
            
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=20,
                pool_maxsize=20
            )
            
            hec_session.mount("http://", adapter)
            hec_session.mount("https://", adapter)
            
        return hec_session

def get_all_images(helper, api_url, api_key, account_name, verify_ssl):
    """Get list of all active images from Anchore, handling pagination."""
    url = f"{api_url.strip().rstrip('/')}/images"
    
    # Create Basic Auth header to match curl -u '_api_key:YOUR_API_KEY'
    auth_str = f"_api_key:{api_key}"
    encoded_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    
    headers = {
        'x-anchore-account': account_name,
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_auth}'
    }
    
    all_images = []
    page = 1
    
    while True:
        try:
            params = {'image_status': 'active', 'page': page, 'limit': 500}
            thread_safe_print(helper, f"Fetching images page {page} from {url}")
            response = helper.send_http_request(url, 'GET', parameters=params, payload=None, headers=headers, cookies=None, verify=verify_ssl, cert=None, timeout=60, use_proxy=True)
            response.raise_for_status()
            data = response.json()
            
            images = data.get("items", [])
            all_images.extend(images)

            # If the number of returned images is less than the limit, it's the last page.
            if not images or len(images) < 500:
                break  # No more images
            
            page += 1
            

        except requests.exceptions.RequestException as e:
            thread_safe_print(helper, f"ERROR: Failed to get images: {e}", 'error')
            break # Return what we have so far
            
    return all_images

def get_image_vulnerabilities(helper, api_url, api_key, account_name, image_digest, verify_ssl):
    """Get vulnerabilities for a specific image"""
    url = f"{api_url.strip().rstrip('/')}/images/{image_digest}/vuln/all"

    # Create Basic Auth header to match curl -u '_api_key:YOUR_API_KEY'
    auth_str = f"_api_key:{api_key}"
    encoded_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    headers = {
        'x-anchore-account': account_name,
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_auth}'
    }
    
    try:
        response = helper.send_http_request(url, 'GET', parameters=None, payload=None, headers=headers, cookies=None, verify=verify_ssl, cert=None, timeout=60, use_proxy=True)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        thread_safe_print(helper, f"ERROR: Failed to get vulnerabilities for {image_digest}: {e}", 'error')
        return None

def format_vulnerability_events(image_info, vuln_data, api_url, account_name):
    """Format vulnerability data as multiple Splunk HEC events - one per vulnerability"""
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    event_time = int(datetime.now(timezone.utc).timestamp())
    
    api_base_url = '/'.join(api_url.rstrip('/').split('/')[:-1]) if api_url else ""
    
    image_detail = image_info.get("image_detail", [{}])[0] if image_info.get("image_detail") else {}
    
    base_image_data = {
        "timestamp": timestamp,
        "api_url": api_base_url,
        "account_name": account_name,
        "image_digest": image_info.get("image_digest"),
        "image_id": image_info.get("image_id"),
        "analysis_status": image_info.get("analysis_status"),
        "image_type": image_info.get("image_type"),
        "analyzed_at": image_info.get("analyzed_at"),
        "created_at": image_info.get("created_at"),
        "last_updated": image_info.get("last_updated"),
        "repo": image_detail.get("repo"),
        "registry": image_detail.get("registry"),
        "tag": image_detail.get("tag"),
        "full_tag": image_detail.get("full_tag"),
        "tags": image_detail.get("tags", [])
    }
    
    events = []
    vulnerabilities = vuln_data.get("vulnerabilities", [])
    
    if not vulnerabilities:
        event_data = base_image_data.copy()
        event_data.update({
            "vulnerability_found": False,
            "vulnerability_count": 0
        })
        
        hec_event = {
            "time": event_time,
            "source": "anchore_api",
            "sourcetype": "anchore:vulnerabilities",
            "event": event_data
        }
        events.append(hec_event)
    else:
        for vuln in vulnerabilities:
            event_data = base_image_data.copy()
            event_data.update({
                "vulnerability_found": True,
                "vulnerability_count": len(vulnerabilities),
                "vuln_id": vuln.get("vuln"),
                "package": vuln.get("package"),
                "package_name": vuln.get("package_name"),
                "package_version": vuln.get("package_version"),
                "package_type": vuln.get("package_type"),
                "severity": vuln.get("severity"),
                "fix": vuln.get("fix"),
                "url": vuln.get("url"),
                "nvd_data": vuln.get("nvd_data", []),
                "vendor_data": vuln.get("vendor_data", [])
            })
            
            hec_event = {
                "time": event_time,
                "source": "anchore_api", 
                "sourcetype": "anchore:vulnerabilities",
                "event": event_data
            }
            events.append(hec_event)
    
    return events

def send_events_to_hec_batch(helper, hec_url, hec_token, events, verify_ssl=False):
    """Send multiple events to Splunk HEC in a single request"""
    if not events:
        return True, 0, 0
    
    headers = {
        "Authorization": f"Splunk {hec_token}",
        "Content-Type": "application/json"
    }
    
    batch_data = '\n'.join(json.dumps(event) for event in events)
    
    try:
        session = get_hec_session(helper)
        response = session.post(
            hec_url,
            headers=headers,
            data=batch_data,
            verify=verify_ssl,
            timeout=30
        )
        response.raise_for_status()
        return True, len(events), 0
    except requests.exceptions.RequestException as e:
        thread_safe_print(helper, f"ERROR: Failed to send batch to HEC: {e}", 'error')
        return False, 0, len(events)

def process_image_vulnerabilities(helper, image, api_url, api_key, account_name, hec_url, hec_token, anchore_verify_ssl, hec_verify_ssl, target_index):
    """Process vulnerabilities for a single image in a thread"""
    image_digest = image.get('image_digest')
    if not image_digest:
        return {"success": False, "error": "No image_digest"}
    
    image_detail = image.get("image_detail", [{}])[0] if image.get("image_detail") else {}
    repo_tag = f"{image_detail.get('repo', 'unknown')}:{image_detail.get('tag', 'unknown')}"
    
    try:
        vuln_data = get_image_vulnerabilities(helper, api_url, api_key, account_name, image_digest, anchore_verify_ssl)
        
        if vuln_data is None:
            return {"success": False, "error": "API error", "repo_tag": repo_tag}
            
        if not isinstance(vuln_data, dict):
            return {"success": False, "error": f"Invalid data type: {type(vuln_data)}", "repo_tag": repo_tag}
            
        events = format_vulnerability_events(image, vuln_data, api_url, account_name)
        
        for event in events:
            event["index"] = target_index
        
        success, successful_events, failed_events = send_events_to_hec_batch(
            helper, hec_url, hec_token, events, hec_verify_ssl
        )
        
        return {
            "success": True,
            "repo_tag": repo_tag,
            "total_events": len(events),
            "successful_events": successful_events,
            "failed_events": failed_events
        }
        
    except Exception as e:
        return {"success": False, "error": str(e), "repo_tag": repo_tag}

def collect_events(helper, ew):
    """This function connects to the Anchore API, fetches data, and then forwards that data to a specified Splunk HEC endpoint."""
    try:
        # --- Step 1: Get All Configuration Parameters ---
        api_url = helper.get_arg('api_url')
        api_key = helper.get_arg('api_key')
        account_name = helper.get_arg('account_name') # Default to 'admin' if not provided
        hec_url = helper.get_arg('hec_url')
        hec_token = helper.get_arg('hec_token')
        anchore_verify_ssl = helper.get_arg('anchore_verify_ssl')
        hec_verify_ssl = helper.get_arg('hec_verify_ssl')
        target_index = helper.get_output_index()
        
        thread_safe_print(helper, f"Starting Anchore vulnerability collection at {datetime.now(timezone.utc)}")

        # --- Step 2: Get all images ---
        images = get_all_images(helper, api_url, api_key, account_name, anchore_verify_ssl)
        
        if not images:
            thread_safe_print(helper, "WARNING: No images found or API call failed", 'warning')
            return
        
        thread_safe_print(helper, f"INFO: Found {len(images)} images to process")
        
        # --- Step 3: Process images in parallel ---
        max_workers = min(10, len(images) if len(images) > 0 else 1)
        thread_safe_print(helper, f"INFO: Using {max_workers} worker threads for parallel processing")
        
        total_processed = 0
        total_events_sent = 0
        total_events_failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_image = {
                executor.submit(
                    process_image_vulnerabilities, 
                    helper, image, api_url, api_key, account_name, 
                    hec_url, hec_token, anchore_verify_ssl, hec_verify_ssl, target_index
                ): (i, image) for i, image in enumerate(images)
            }
            
            for future in as_completed(future_to_image):
                i, image = future_to_image[future]
                
                try:
                    result = future.result()
                    total_processed += 1
                    
                    if result["success"]:
                        total_events_sent += result["successful_events"]
                        total_events_failed += result["failed_events"]
                        
                        if result["failed_events"] == 0:
                            thread_safe_print(helper, f"INFO: Sent {result['total_events']} events for image {i+1}/{len(images)} ({result['repo_tag']})")
                        else:
                            thread_safe_print(helper, f"WARNING: Sent {result['successful_events']}/{result['total_events']} events for image {i+1}/{len(images)} ({result['repo_tag']}) - {result['failed_events']} failed", 'warning')
                    else:
                        thread_safe_print(helper, f"ERROR: Failed to process image {i+1}/{len(images)} ({result.get('repo_tag', 'unknown')}): {result.get('error', 'Unknown error')}", 'error')
                    
                    if total_processed % 10 == 0:
                        thread_safe_print(helper, f"PROGRESS: Completed {total_processed}/{len(images)} images, sent {total_events_sent} events, {total_events_failed} failed")
                        
                except Exception as e:
                    thread_safe_print(helper, f"ERROR: Thread exception for image {i+1}/{len(images)}: {e}", 'error')
        
        thread_safe_print(helper, f"INFO: Completed vulnerability collection at {datetime.now(timezone.utc)}")
        thread_safe_print(helper, f"SUMMARY: Processed {total_processed}/{len(images)} images, sent {total_events_sent} events, {total_events_failed} failed")
        
    except Exception as e:
        thread_safe_print(helper, f"FATAL: Collection failed entirely: {e}", 'error')
