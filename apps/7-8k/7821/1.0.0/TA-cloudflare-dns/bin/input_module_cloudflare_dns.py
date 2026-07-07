
# encoding = utf-8

import requests
import json
import random
import time

def validate_input(helper, definition):
    pass

def get_all_zones(helper, ew, base_url, token):
    
    zones = []
    page = 1
    
    BASE_URL = base_url
    API_TOKEN = token
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    while True:
        
        if random.random() < 0.01:
            helper.log_info("Still collecting Zone Records...")
        
        response = requests.get(
            f"{BASE_URL}/zones?page={page}&per_page=100",
            headers=headers
        )
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            time.sleep(retry_after)
            continue
        
        response.raise_for_status()
        data = response.json()

        if not data['success']:
            not_success_msg = f"Failed to fetch zones: {data}'"
            helper.log_error(not_success_msg)
            raise Exception(not_success_msg)

        zones_data_result = data['result']
        zones.extend(zones_data_result)
        
        # Write Zone as a separate event data
        for z in zones_data_result:
            
            zone_data_event = json.dumps(z, separators=(",", ":"))
            
            zone_event = helper.new_event(source="cloudflare_zone_dns_collector", index=helper.get_output_index(), sourcetype='cloudflare:zone', data=zone_data_event)
            
            ew.write_event(zone_event)

        if page >= data['result_info']['total_pages']:
            break

        page += 1

    return zones

def get_all_dns_for_zone(helper, base_url, token, zone_id):
    records = []
    page = 1
    
    BASE_URL = base_url
    API_TOKEN = token
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    while True:
        
        if random.random() < 0.01:
            helper.log_info("Still collecting DNS Records. This part of the collection takes most of the time...")
        
        response = requests.get(
            f"{BASE_URL}/zones/{zone_id}/dns_records?page={page}&per_page=100",
            headers=headers
        )
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            time.sleep(retry_after)
            continue
        
        response.raise_for_status()
        data = response.json()

        if not data['success']:
            not_success_msg = f"Failed to fetch DNS for zone {zone_id}: {data}"
            helper.log_error(not_success_msg)
            raise Exception(not_success_msg)
            
        records.extend(data['result'])

        if page >= data['result_info']['total_pages']:
            break

        page += 1

    return records

def collect_events(helper, ew):
    
    BASE_URL = helper.get_arg('base_url')
    BEARER_TOKEN = helper.get_arg('api_bearer_token')
    
    log_level = helper.get_log_level()
    
    helper.set_log_level(log_level)
    
    helper.log_info(f"Cloudflare DNS collection starts here. Starting with Zones...")
    helper.log_info(f"Logging level is set to: {log_level}")
    
    try:
        
        zones = get_all_zones(helper, ew, BASE_URL, BEARER_TOKEN)
        
        helper.log_info(f"All Zones indexed. Now querying DNS Records API Endpoint. Multi-page enabled. Record per page is set to: 100. This will take time.")
    
        dns_ctr = 0
        
        for z in zones:
            
            # Get all DNS from Zones
            zone_id = z['id']
            zone_name = z['name']
            
            try:
            
                dns_records = get_all_dns_for_zone(helper, BASE_URL, BEARER_TOKEN, zone_id)
            
                for d in dns_records:
                    
                    d['zone_info'] = {
                        "zone_name": z['name'],
                        "zone_id": z['id']
                    }
                    
                    # Write DNS as events
                    
                    dns_data_event = json.dumps(d, separators=(",", ":"))
                    
                    dns_event = helper.new_event(source="cloudflare_zone_dns_collector", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=dns_data_event)
                    
                    dns_ctr = dns_ctr + 1
                    
                    ew.write_event(dns_event)
            
            except Exception as e:
                helper.log_error(f"Cloudflare DNS collection ended with error: {e}")
        
        helper.log_info(f"Total Zones data event written: {len(zones)}")     
        helper.log_info(f"Total DNS data event written: {dns_ctr}")
        helper.log_info("Cloudflare DNS collection ends here.")
        
    except Exception as e:
        helper.log_error(f"Cloudflare DNS collection ended with error: {e}")
    