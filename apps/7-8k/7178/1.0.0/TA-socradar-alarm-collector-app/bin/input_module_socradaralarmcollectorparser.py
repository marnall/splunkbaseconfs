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
    opt_api_key = helper.get_arg('api_key')
    opt_company_id = helper.get_arg('company_id')

    url =f"https://platform.socradar.com/api/company/{opt_company_id}/incidents/v3?limit=30"
    headers = {'Content-Type': 'application/json','Api-Key': opt_api_key}
    
    payload = {'Api-Key': opt_api_key}
    
    response = helper.send_http_request(url, 'GET', parameters=None, payload=json.dumps(payload), headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)
    
    final_result=[]
    r_json = response.json()
    r_status = response.status_code
    if r_status !=200:
        response.raise_for_status()
    for alarm in r_json["data"]:
        alarm_send={}
        alarm_send["alarm_id"]=alarm.get("consolidated_alarm_id")
        alarm_send["alarm_type"]=alarm.get("alarm_type_details",{}).get("alarm_main_type","")
        alarm_send["alarm_assets"]=alarm.get("alarm_assets",'')[:9999]
        alarm_send["title"]=alarm.get("alarm_notification_texts",{}).get("alarm_title","").replace('"','')
        alarm_send["severity"]=alarm.get("alarm_risk_level")
        alarm_send["description"]=alarm.get("alarm_notification_texts",{}).get("alarm_text","").replace('"','')[:9999]        
        alarm_send["mitigation"]=alarm.get("alarm_notification_texts",{}).get("alarm_mitigation_plan","").replace('"','')[:9999]
        alarm_send["alarm_sub_type"]=alarm.get("alarm_type_details",{}).get("alarm_sub_type","")
        alarm_send["tags"]=alarm.get("tags","").replace('"','')[:9999]
        alarm_send["insert_date"]=alarm.get("insert_date")
        alarm_send["is_resolved"]=alarm.get("is_resolved")
        alarm_send["is_false_positive"]=alarm.get("is_false_positive")
        state = helper.get_check_point(str(alarm["consolidated_alarm_id"]))
        #helper.delete_check_point(str(alarm["consolidated_alarm_id"]))
        if state is None:
            helper.save_check_point(str(alarm["consolidated_alarm_id"]), "Indexed")
            if alarm_send:
                event = helper.new_event(json.dumps(alarm_send), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)