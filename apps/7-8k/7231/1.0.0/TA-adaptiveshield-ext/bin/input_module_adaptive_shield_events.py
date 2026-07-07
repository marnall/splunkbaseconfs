# encoding = utf-8
import os
import sys
import time
import datetime
from datetime import datetime
import calendar
import json
from functools import wraps
from urllib.parse import quote_plus


def validate_input(helper, definition):
    from_date = helper.get_arg("from_date")
    to_date = helper.get_arg("to_date")
    if from_date:
        try:
            datetime.strptime(from_date, "yyyy-MM-ddTHH:mm:ssZ")
        except ValueError:
            raise ValueError("Incorrect data format, should be yyyy-MM-ddTHH:mm:ssZ")
    if to_date:
        try:
            datetime.strptime(to_date, "yyyy-MM-ddTHH:mm:ssZ")
        except ValueError:
            raise ValueError("Incorrect data format, should be yyyy-MM-ddTHH:mm:ssZ")
    pass

def retry(exception_to_check, tries=5, delay=3, backoff=2):
    # retry decorator
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check as e:
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry

    return deco_retry


@retry(Exception)
def get(url, helper, params=None, headers=None):
    if not params:
        params = {}
    if not headers:
        headers = {}
    res = helper.send_http_request(url, "get", parameters=params, headers=headers, use_proxy=True, timeout=15.0)
    res.raise_for_status()
    return res



def collect_events(helper, ew):
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    TIME_FORMAT_ISO = '%Y-%m-%d %H:%M:%S'
    
    event_time_fields = {
        "activity_monitor": "activity_time",
        "user_audit": "event_time",
        "api_audit": "event_time",
        "system_logs": "event_time"
    }

    api_suffixes = {
        "activity_monitor": "activity_monitor",
        "user_audit": "user_audit",
        "api_audit": "api_audit",
        "system_logs": "system_logs"
    }

    sourcetypes = {
        "activity_monitor": "as:activity:monitor",
        "user_audit": "as:user:audit",
        "api_audit": "as:api:audit",
        "system_logs": "as:system:logs"
    }    

    def getSourceType(input_type):
        return sourcetypes[input_type]

    global_api_key = helper.get_global_setting("api_key")
    main_account_id = helper.get_global_setting("account_id")
    log_debug(helper,"----------------------------------------------")
    headers = {"Authorization": f"token {global_api_key}"}
    account_id = main_account_id
    api_base_url = "https://api.adaptive-shield.com/api/v1"
    input_type = helper.get_arg("input_type")
    event_time_field = event_time_fields[input_type]
    api_suffix = api_suffixes[input_type]
    log_info(helper, "Fetching {input_type}")    
    events_url = f"{api_base_url}/accounts/{account_id}/{api_suffix}"
    params = {}
    if(input_type == "activity_monitor"):
        days_ago = helper.get_arg("days_ago")
        sensitivity = helper.get_arg("sensitivity")
        params = {"days_ago": days_ago, "sensitivity": sensitivity}
        if not sensitivity:
            params = {"days_ago": days_ago}
    else:
        from_date = helper.get_arg("from_date")
        if from_date:
            params["from_date"] = from_date
        to_date = helper.get_arg("to_date")
        if to_date:
            params["to_date"] = to_date        
        total_count = helper.get_arg("total_count")
        if total_count:
            params["total_count"] = total_count               
    log_info(helper, f'input_type - {input_type}, events_url - {events_url}, params - "{params}"')
    events_res = get(events_url, helper, headers=headers, params=params)
    events = events_res.json()["data"]
    next_page_uri = events_res.json().get("next_page_uri", None)

    def create_event(event_log):
        #st = helper.get_sourcetype()
        st = getSourceType(input_type)
        '''if(helper.get_arg("sourcetype_override")):
            st = helper.get_arg("sourcetype_override")'''
        event_pers = helper.new_event(source=helper.get_input_type() + ":" + helper.get_input_stanza_names(), index=helper.get_output_index(), sourcetype=st, data=json.dumps(event_log))
        ew.write_event(event_pers)

    page = 0
    total_num_of_events = len(events)
    log_info(helper,f"num of events - {len(events)}")
    #lastIndexedTime, oldest_event_time = readCheckPoint(helper)
    oldest_event_time = readCheckPointKV(helper, "last_event_time")
    log_info(helper,f"From KVStore oldest_event_time - {oldest_event_time}")
    
    if events:    
        last_event_time = convertStringToEpoch(events[0][event_time_field], TIME_FORMAT)

    #if(lastIndexedTime==""):
    #    lastIndexedTime = 1672531200
        
    if(oldest_event_time==""):
        oldest_event_time = 1672531200

    events_created = 0

    for event in events:
        curr_event_time=convertStringToEpoch(event[event_time_field],TIME_FORMAT)
        if curr_event_time > last_event_time:
            last_event_time = curr_event_time
        timenow = convertDateTimeToEpoch(datetime.now(), TIME_FORMAT_ISO)
        #since_last_index = (timenow-lastIndexedTime)
        if((curr_event_time>oldest_event_time)):
            log_debug(helper,f"creating event")
            create_event(event)
            events_created += 1
 
    if events:
        indexedTime = convertDateTimeToEpoch(datetime.now(), TIME_FORMAT_ISO)
        #writeCheckPoint(helper, str(indexedTime), str(last_event_time))
        writeCheckPointKV(helper, "last_event_time" ,str(last_event_time))
       
    while next_page_uri:
        page += 1
        if page >= 20:
            break
        events_res = get(next_page_uri, helper, headers=headers)
        events = events_res.json()["data"]
        total_num_of_events += len(events)
        log_info(helper,f"num of events - {len(events)}")
        next_page_uri = events_res.json().get("next_page_uri", None)
        log_info(helper,f"next_page_uri - {next_page_uri}")
        for event in events:
            curr_event_time=convertStringToEpoch(event[event_time_field],TIME_FORMAT)
            if curr_event_time > last_event_time:
                last_event_time = curr_event_time
            timenow = convertDateTimeToEpoch(datetime.now(), TIME_FORMAT_ISO)
            #since_last_index = (timenow-lastIndexedTime)
            if((curr_event_time>oldest_event_time)):
                log_debug(helper,f"creating event")
                create_event(event)
                events_created += 1

    indexedTime = convertDateTimeToEpoch(datetime.now(), TIME_FORMAT_ISO)   
    #writeCheckPoint(helper, str(indexedTime), str(last_event_time))  
    if(events):
        writeCheckPointKV(helper, "last_event_time" ,str(last_event_time))
    log_info(helper,f"Total number of events retrieved - {total_num_of_events}, Events created - {events_created}")
    log_info(helper,f"Finished with {account_id}")

def convertDateTimeToEpoch(dtObject, timeFormat):
    dtEPOCH = int(time.mktime(dtObject.timetuple()))
    return dtEPOCH

def convertDateTimeToString(dtObject, timeFormat):
    dtString = dtObject.strftime(timeFormat)
    return dtString

def convertEpochToDateTime(dtEpoch):
    dtObject = datetime.fromtimestamp(dtEpoch)
    return dtObject

def convertStringToEpoch(dtString, timeFormat):
    dtObject = datetime.strptime(dtString, timeFormat)
    dtEPOCH = calendar.timegm(dtObject.timetuple())
    return dtEPOCH

def convertDateTimeFormat(dtObject, timeFormatTarget):
    dtObjectTarget = dtObject.strftime(timeFormatTarget)
    return dtObjectTarget

def generate_checkpoint_key(helper, account_id):
    stanza_name = str(helper.get_input_stanza_names())
    input_stanza = helper.get_input_stanza(input_stanza_name=stanza_name)
    print(input_stanza)
    key = '|'.join(["ACTIVITY-", account_id, stanza_name])
    return quote_plus(key)

def writeCheckPointKV(helper, key, value):
    key = helper.get_input_stanza_names() + "_" + key
    log_info(helper,f"Writing checkpoint key - {key}, value - {value}")
    helper.save_check_point(key, value)

def readCheckPointKV(helper, key):
    key = helper.get_input_stanza_names() + "_" + key
    value = helper.get_check_point(key)
    if(value): 
        value = int(value)
        log_info(helper,f"Reading checkpoint key - {key}, value - {value}")    
        return int(value)
    else: 
        log_info(helper,f"Reading checkpoint key - {key}, got No Value")  
        return ""

def getLogContext(helper):
    mod_input = helper.get_input_type()
    input_type = helper.get_arg("input_type")
    stanza_name = str(helper.get_input_stanza_names())
    index_name = helper.get_output_index()
    context = f"ModInput={mod_input}, InputType={input_type}, StanzaName={stanza_name}, index={index_name}"
    return context

def log_info(helper, msg):
    logContext = getLogContext(helper)
    msg = f"{logContext} , {msg}"
    helper.log_info(str(msg))

def log_debug(helper, msg):
    logContext = getLogContext(helper)
    msg = f"{logContext} , {msg}"
    helper.log_debug(str(msg))

def log_error(helper, msg):
    logContext = getLogContext(helper)
    msg = f"{logContext} , {msg}"
    helper.log_error(str(msg))

def log_warning(helper, msg):
    logContext = getLogContext(helper)
    msg = f"{logContext} , {msg}"    
    helper.log_warning(str(msg))

def log_critical(helper, msg):
    logContext = getLogContext(helper)
    msg = f"{logContext} , {msg}"    
    helper.log_critical(str(msg))