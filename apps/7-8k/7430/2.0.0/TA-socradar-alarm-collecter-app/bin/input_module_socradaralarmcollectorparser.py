# encoding = utf-8
import os
import sys
import json
from datetime import datetime, timedelta


def validate_input(helper, definition):
    """
    Validation for modular input configurations
    """
    pass


def build_proxies(proxy_settings):
    """
    Build proxy configuration for HTTP requests
    """
    if proxy_settings:
        proxy_url = proxy_settings.get('proxy_url')
        proxy_port = proxy_settings.get('proxy_port')
        proxy_username = proxy_settings.get('proxy_username')
        proxy_password = proxy_settings.get('proxy_password')
        if proxy_username and proxy_password:
            return {
                'http': f"http://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}",
                'https': f"https://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
            }
        return {
            'http': f"http://{proxy_url}:{proxy_port}",
            'https': f"https://{proxy_url}:{proxy_port}"
        }
    return None


def clean_text(text, max_length=1000):
    """
    Clean and truncate text to prevent Splunk ingestion errors
    """
    if not text:
        return ""
    # Remove harmful characters and truncate long text
    text = text.replace(",", "").replace('"', '').replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    return text[:max_length] + " [DATA TRUNCATED]" if len(text) > max_length else text


def build_alarm_event(alarm, api_key, company_id):
    """
    Build a structured alarm event from SOC Radar data
    """
    return {
        "alarm_id": alarm.get("alarm_id"),
        "alarm_main_type": alarm.get("alarm_type_details", {}).get("alarm_main_type", ""),
        "alarm_sub_type": alarm.get("alarm_type_details", {}).get("alarm_sub_type", ""),
        "alarm_asset": alarm.get("alarm_asset", "")[:9999],
        "title": clean_text(alarm.get("alarm_type_details", {}).get("alarm_generic_title", "")),
        "severity": alarm.get("alarm_risk_level"),
        "description": clean_text(alarm.get("alarm_text", "")),
        "mitigation": clean_text(alarm.get("alarm_type_details", {}).get("alarm_default_mitigation_plan", "")),
        "tags": ",".join(str(tag) for tag in alarm.get("tags", [])),
        "insert_date": alarm.get("date"),
        "status": alarm.get("status"),
        "alarm_link": f"https://platform.socradar.com/app/company/{company_id}/alarm-management?tab=approved&alarmId={alarm.get('alarm_id')}"
    }


def fetch_alarms(helper, api_key, company_id, proxies):
    """
    Fetch alarms from SOC Radar API
    """
    url = f"https://platform.socradar.com/api/company/{company_id}/incidents/v4?key={api_key}&limit=100"
    headers = {'Content-Type': 'application/json', 'Api-Key': api_key}

    response = helper.send_http_request(
        url,
        'GET',
        parameters=None,
        payload=None,
        headers=headers,
        cookies=None,
        verify=True,
        cert=None,
        timeout=30,
        use_proxy=bool(proxies)
    )

    if response.status_code != 200:
        helper.log_error(f"Failed to fetch alarms: {response.status_code} - {response.text}")
        response.raise_for_status()

    return response.json().get("data", [])


def change_alarm_status(helper, alarm_id, status, comments, api_key, company_id, proxies):
    """
    Change the status of an alarm using SOC Radar API
    """
    url = f"https://platform.socradar.com/api/company/{company_id}/alarms/status/change"
    headers = {'Content-Type': 'application/json', 'Api-Key': api_key}
    payload = {
        "status": status,
        "alarm_ids": [alarm_id],
        "comments": comments
    }

    response = helper.send_http_request(
        url,
        'POST',
        parameters=None,
        payload=json.dumps(payload),
        headers=headers,
        cookies=None,
        verify=True,
        cert=None,
        timeout=30,
        use_proxy=bool(proxies)
    )

    if response.status_code == 200:
        helper.log_info(f"Successfully changed status of alarm {alarm_id} to {status}")
        return True
    else:
        helper.log_error(f"Failed to change status of alarm {alarm_id}. HTTP {response.status_code}: {response.text}")
        return False


def collect_events(helper, ew):
    """
    Collect and process SOC Radar alarms for Splunk
    """
    proxy_settings = helper.get_proxy()
    proxies = build_proxies(proxy_settings)

    opt_api_key = helper.get_arg('your_company_api_key')
    opt_company_id = helper.get_arg('company_id')

    try:
        alarms = fetch_alarms(helper, opt_api_key, opt_company_id, proxies)
        for alarm in alarms:
            alarm_event = build_alarm_event(alarm, opt_api_key, opt_company_id)
            state = helper.get_check_point(str(alarm_event["alarm_id"]))
            if state is None:
                helper.save_check_point(str(alarm_event["alarm_id"]), "Indexed")
                try:
                    event = helper.new_event(
                        json.dumps(alarm_event),
                        time=None,
                        host=None,
                        index=None,
                        source=None,
                        sourcetype=None,
                        done=True,
                        unbroken=True
                    )
                    ew.write_event(event)

                    # Example: Auto-close low severity alarms
                    if alarm_event["severity"].lower() == "low":
                        change_alarm_status(helper, alarm_event["alarm_id"], "2", "Automatically resolved by Splunk",
                                            opt_api_key, opt_company_id, proxies)
                except Exception as e:
                    helper.log_error(f"Error writing event to Splunk: {str(e)}")
    except Exception as e:
        helper.log_error(f"Error processing alarms: {str(e)}")



"""


# encoding = utf-8
import os
import sys
import time
import datetime
import json
from datetime import datetime, timedelta

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
        # Splunk proxy ayarlarını al
    proxy_settings = helper.get_proxy()

    # Proxy kullanılıyor mu kontrol et
    if proxy_settings:
        # Proxy bilgilerini al
        proxy_url = proxy_settings.get('proxy_url')
        proxy_port = proxy_settings.get('proxy_port')
        proxy_username = proxy_settings.get('proxy_username')
        proxy_password = proxy_settings.get('proxy_password')

        # Proxy string oluşturma (kullanıcı adı/şifre varsa)
        if proxy_username and proxy_password:
            proxy = f"http://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
        else:
            proxy = f"http://{proxy_url}:{proxy_port}"

    # Proxy ayarlarını HTTP isteğinde kullan
    proxies = {
        'http': proxy,
        'https': proxy
    } if proxy_settings else None
    
    opt_api_key = helper.get_arg('your_company_api_key')
    opt_company_id = helper.get_arg('company_id')
    url =f"https://platform.socradar.com/api/company/{opt_company_id}/incidents/v4?key={opt_api_key}"
    headers = {'Content-Type': 'application/json','Api-Key': opt_api_key}
    
    payload = {'Api-Key': opt_api_key}
    
    response = helper.send_http_request(url, 'GET', parameters=None, payload=json.dumps(payload), headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=proxy_settings)
    
    final_result=[]
    r_json = response.json()
    r_status = response.status_code
    if r_status !=200:
        response.raise_for_status()
    for alarm in r_json["data"]:
        alarm_send={}
        alarm_send["alarm_id"]=alarm.get("alarm_id")
        alarm_send["alarm_type"]=alarm.get("alarm_type_details",{}).get("alarm_main_type","")
        alarm_send["alarm_assets"]=alarm.get("alarm_assets",'')[:9999]
        alarm_send["title"]=alarm.get("alarm_notification_texts",{}).get("alarm_generic_title","").replace('"','')
        alarm_send["severity"]=alarm.get("alarm_risk_level")
        alarm_send["description"]=alarm.get("alarm_text","").replace('"','')[:9999]        
        alarm_send["mitigation"]=alarm.get("alarm_type_details",{}).get("alarm_default_mitigation_plan","").replace('"','')[:9999]
        alarm_send["alarm_sub_type"]=alarm.get("alarm_type_details",{}).get("alarm_sub_type","")
        my_tags = ",".join(str(element) for element in alarm.get("tags"))
        alarm_send["tags"]=my_tags
        alarm_send["insert_date"]=alarm.get("date")
        alarm_send["status"]=alarm.get("status")
        alarm_id_forlink=alarm.get("alarm_id")
        alarm_send["alarm_link"]=f"https://platform.socradar.com/app/company/{opt_company_id}/alarm-management?tab=approved&alarmId={alarm_id_forlink}"
        state = helper.get_check_point(str(alarm["alarm_id"]))
        #helper.delete_check_point(str(alarm["alarm_id"]))
        if state is None:
            helper.save_check_point(str(alarm["alarm_id"]), "Indexed")
            if alarm_send:
                event = helper.new_event(json.dumps(alarm_send), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
"""