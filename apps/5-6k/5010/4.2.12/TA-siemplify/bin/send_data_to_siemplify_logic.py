import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.error import HTTPError
import copy
import requests
import traceback
from ta_siemplify_splunkquery import splunkquery
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
# CONSTS
APP_NAME = 'TA-siemplify'
ENCODING_UTF_8 = "utf-8"
PAYLOAD = """{{
    "Cases": [{{
            "Events": [{{
                    "_fields": {{
                        "BaseEventIds": [],
                        "ParentEventId": -1,
                        "DeviceProduct": "Windows:AccessDisabledAccounts",
                        "DeviceVendor": "Windows:AccessDisabledAccounts",
                        "StartTime": "1522318978039",
                        "EndTime": "1522318978039"
                    }},
                    "_rawDataFields": {{

                    }},
                    "Environment": "{environment}",
                    "SourceSystemName": "Splunk"
                }}
            ],
            "Environment": "{environment}",
            "SourceSystemName": "Splunk",
            "TicketId": "{ticket_id}",
            "Description": "{description}",
            "DisplayId": "{display_id}",
            "Reason": "{reason}",
            "Name": "{alert_name}",
            "DeviceVendor": "{device_vendor}",
            "DeviceProduct": "{device_product}",
            "StartTime": "{start_time}",
            "EndTime": "{end_time}",
            "IsTestCase": false,
            "Priority": "{priority}",
            "RuleGenerator": "{rule_generator}",
            "PlaybookTriggerKeywords": [],
            "Extensions": []
        }}
    ],
    "IsTestCase": false
}}"""

PRIORITY = {
    'info': -1,
    'low': 40,
    'medium': 60,
    'high': 80,
    'critical': 100
    }

MAX_RETRY = 3
MAX_EVENTS = "10"


class alert_config:
    """
    Getting alert parameters from Splunk Helper.
    """

    def __init__(self, helper):
        """

        :param helper:
        """
        self.title = helper.get_param("alert_name")
        helper.log_debug(f"alert_name={self.title}")

        self.category = helper.get_param("category")
        helper.log_debug(f"category={self.category}")

        self.priority = helper.get_param("case_priority")
        helper.log_debug(f"case_priority={self.priority}")

        self.env = helper.get_param("environment")
        helper.log_debug(f"environment={self.env}")

        self.device_product = helper.get_param("device_product")
        helper.log_debug(f"device_product={self.device_product}")

        self.device_vendor = helper.get_param("device_vendor")
        helper.log_debug(f"device_vendor={self.device_vendor}")

        self.expand_mv = helper.get_param("expand_multivalue_fields")
        helper.log_debug(f"expand_mv={self.expand_mv}")

        self.trigger_per_result = helper.get_param("trigger_per_result")
        helper.log_debug(f"trigger_per_result={self.trigger_per_result}")

        self.mode = helper.get_global_setting("mode")
        helper.log_debug(f"mode={self.mode}")

        self.uri = helper.get_global_setting("siemplify_api_uri")
        self.token = helper.get_global_setting("api_key")
        
        self.uri_secondary = helper.get_global_setting("siemplify_api_uri_secondary")
        self.token_secondary = helper.get_global_setting("api_key_secondary")

        if self.mode == 'push':
            if self.env is None:
                self.env = ''

            if self.uri:
                helper.log_debug(f"URI={self.uri}")
                if not self.uri.startswith("https:"):
                    helper.log_error("URI is not HTTPS, Failing.")
                    raise ValueError('URI is not HTTPS')
            else:
                helper.log_error("URI hasn't defined.")
                raise ValueError("URI has not been defined")

            if not self.token:
                helper.log_error("API Token has not been setup")
                raise ValueError("API Token has not been setup")

            if self.uri_secondary:
                if not self.uri_secondary.startswith("https:"):
                    helper.log_error("Secondary URI is not HTTPS, Failing.")
                    raise ValueError('Secondary URI is not HTTPS')


def extract_splunk_event_data(event, vendor_field='', product_field='[sourcetype]', time_field='_indextime',
                              environment=None, source_system_name=None, event_type_field='', category=None,
                              helper=None):
    FORMAT = {"_fields":{}, "_rawDataFields": {}, "Environment": 'place_holder', "SourceSystemName": "Splunk",
              "Category": 'place_holder'}

    FORMAT["_fields"]['BaseEventIds'] = []
    FORMAT["_fields"]['ParentEventId'] = -1

    if product_field and product_field[0] == '[' and product_field[-1] == ']':
        FORMAT["_fields"]['DeviceProduct'] = event.get(product_field[1:-1], 'Default Product')
    else:
        FORMAT["_fields"]['DeviceProduct'] = product_field

    if event_type_field and event_type_field[0] == '[' and event_type_field[-1] == ']':
        FORMAT["_fields"]['DeviceEventClassId'] = event.get(event_type_field[1:-1], '')
    else:
        FORMAT["_fields"]['DeviceEventClassId'] = event_type_field

    FORMAT["_fields"]['DeviceVendor'] = event.get(vendor_field, 'Default Vendor')

    time_value = str(event.get(time_field, str(int(round(time.time() * 1000)))))
    time_value = str(convert_timestamp(helper, time_value))
    if len(time_value) < 13:
        time_value = str(time_value) + '000'

    FORMAT["_fields"]['StartTime'] = time_value
    FORMAT["_fields"]['EndTime'] = time_value

    FORMAT["_rawDataFields"] = event

    FORMAT["Environment"] = environment
    FORMAT["Category"] = category
    FORMAT['SourceSystemName'] = source_system_name if source_system_name else FORMAT['SourceSystemName']

    return FORMAT

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def validate_string(string, convert_none = False, ignore_non_str = False):
    """
    Validates string encoding, in case of unicode the string will be encoded and returned as a string object
    :param string:  {Basestring}
    :return: {str}
    """

    if convert_none is True and string is None:
        return str(None)

    if isinstance(string, str):
        return string.encode(ENCODING_UTF_8)
    elif isinstance(string, str):
        return string
    elif ignore_non_str:
        return string
    else:
        raise Exception("validate string error: Given object in not any basestring type")

def dict_to_flat(target_dict):
    """
    Receives nested dictionary and returns it as a flat dictionary.
    :param target_dict: {dict}
    :return: Flat dict : {dict}
    """
    target_dict = copy.deepcopy(target_dict)

    def expand(raw_key, raw_value):
        key = validate_string(raw_key, convert_none=True, ignore_non_str=True)
        value = validate_string(raw_value, convert_none=True, ignore_non_str=True)
        """
        :param key: {string}
        :param value: {string}
        :return: Recursive function.
        """
        if not value:
            return [(key, "")]
        elif isinstance(value, dict):
            # Handle dict type value
            return [("{}_{}".format(key,
                                      validate_string(sub_key, convert_none=True, ignore_non_str=True)),
                     validate_string(sub_value, convert_none=True, ignore_non_str=True))
                    for sub_key, sub_value in list(dict_to_flat(value).items())]
        elif isinstance(value, list):
            # Handle list type value
            count = 1
            l = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    # Handle nested dict in list
                    l.extend([("{}_{}_{}".format(validate_string(key, convert_none=True, ignore_non_str=True),
                                                    str(count),
                                                    validate_string(sub_key, convert_none=True, ignore_non_str=True)),
                               sub_value)
                              for sub_key, sub_value in list(dict_to_flat(value_item).items())])
                    items_to_remove.append(value_item)
                    count += 1
                elif isinstance(value_item, list):
                    l.extend(expand(str(key) + '_' + str(count), value_item))
                    count += 1
                    items_to_remove.append(value_item)

            for value_item in items_to_remove:
                value.remove(value_item)

            for value_item in value:
                l.extend([(str(key) + '_' + str(count), value_item)])
                count += 1
            return l
        else:
            return [(key, value)]

    items = [item for sub_key, sub_value in list(target_dict.items()) for item in
             expand(sub_key, sub_value)]
    return dict(items)

def expand_mv_events(helper, event, search_query):
    # This function takes an event that has multivalue source or destination fields and breaks the event up into multiple events.
    helper.log_debug("Expand MV Events")
    evts = []
    event_added = 0
    if 'group_by_fields' in search_query:
        for attr_name in event:
            if isinstance(event[attr_name], list):
                helper.log_debug(f'got multivalue : {attr_name}')
                vals = event[attr_name]
                in_group_by = 0
                if attr_name.startswith('src') or attr_name.startswith('dest'):
                    helper.log_debug(f'found src or dest: {event[attr_name]}')
                    for group_by_field in search_query['group_by_fields']:
                        if group_by_field['field'] == attr_name:
                            event[group_by_field['field']] = group_by_field['value']
                            in_group_by = 1
                    if in_group_by == 0:
                        for val in vals:
                            event_new = copy.deepcopy(event)
                            event_new[attr_name] = val
                            evts.append(event_new)
                            event_added = 1
    if event_added == 0:
        helper.log_debug(event)
        evts.append(event)
    return evts

def expand_mv(helper, events):
    helper.log_debug("Epand_MV---")
    evts = []
    for event in events:
        mv_fields = {}
        for attr in event:
            if re.match('^__mv_', attr) is not None:
                vals = event[attr].split(';')
                attr_name_re = re.search('__mv_(.*)', attr)
                attr_name = attr_name_re.group(1)
                for idx, val in enumerate(vals):
                    attr_idx = f"{attr_name}_{idx}"
                    mv_fields[attr_idx] = val.strip("$")
        expanded_event = merge_two_dicts(mv_fields, event)
        evts.append(expanded_event)
    helper.log_debug("End ExpandMV--")
    return evts

def getEventProps(helper, config, event):
    props = {}
    try:
        if '[' in config.title and ']' in config.title:
            alertnamekey = config.title[1:-1]
            if alertnamekey in list(event.keys()):
                config.title = event[alertnamekey]
    except Exception as e:
        pass
    props['alertname'] = config.title



    try:
        if '[' in config.env and ']' in config.env:
            config.env = config.env[1:-1]
            if config.env in list(event.keys()):
                config.env = event[config.env]
            else:
                config.env = ''
    except Exception as e:
        config.env = ''
    props['environment'] = config.env

    case_product = ''
    try:
        if '[' in config.device_product and ']' in config.device_product:
            case_product = config.device_product[1:-1]
            if case_product in list(event.keys()):
                case_product = event[case_product]
            else:
                case_product = 'MissingProduct'
        else:
            case_product = config.device_product
    except Exception as e:
        case_product = 'MissingProduct'

    props['product'] = case_product
    case_vendor = ''
    try:
        if '[' in config.device_vendor and ']' in config.device_vendor:
            case_vendor = config.device_vendor[1:-1]
            if case_vendor in list(event.keys()):
                case_vendor = event[case_vendor]
            else:
                case_vendor = 'MissingVendor'
        else:
            case_vendor = config.device_vendor
    except Exception as e:
        case_vendor = 'MissingVendor'

    props['vendor'] = case_vendor

    case_priority = 'info'
    try:
        if '[' in config.priority and ']' in config.priority:
            case_priority = config.priority[1:-1]
            if case_priority in list(event.keys()):
                case_priority = event[case_priority]
            else:
                case_priority = 'info'
        else:
            case_priority = config.priority
    except Exception as e:
        case_priority = 'info'

    props['priority'] = case_priority

    return props

def send_message(helper, *args, **kwargs):
    """

    :param helper: Splunk built-in object. Pay attention many things aren't documented into Splunk Documents.
    :param args: Left for consistent.
    :param kwargs: Left for consistent.
    :return: Not used.
    """

    config = alert_config(helper)
    headers = {"AppKey": config.token, 'Content-Type': 'application/json'}
    try:
        alert_time = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
        helper.log_debug(f"alert_time={alert_time}")

        session_key = helper.session_key

        search_params = get_search_params(helper)
        helper.log_debug(f"expand_mv = {config.expand_mv}")
        helper.log_debug(f'Send Message Module: Alert Params are {str(search_params)}')

        alert_search = search_params['_search']
        events = helper.get_events()
        events = [event for event in events]
        helper.log_debug(f"Events from helper: {events}")
        bring_all_events_data_txt = helper.get_param("bring_all_events_data")
        helper.log_debug(f'bring_all_events_data_txt value is: {str(bring_all_events_data_txt)}.')

        kv_mgr = splunkquery(sessionkey=session_key, helper=helper)
        job_summary = kv_mgr.getJobSummary(search_params['_sid'])
        helper.log_debug(f"job summary: {job_summary}")
        kv_record = {
            "_key": helper.sid,
            "_time":str(int(round(time.time()))),
            "app": helper.app,
            "alert_name": helper.search_name,
            "siemplify_alert_name": helper._alert_name,
            "sid": helper.sid,
            "category": helper.get_param("category"),
            "event_type": helper.get_param("event_type"),
            "time_field": helper.get_param("time_field"),
            "retry_count": 0
        }

        try:
            events_part = {}
            first_event = {}
            if bring_all_events_data_txt and bring_all_events_data_txt != '0' and job_summary['eventAvailableCount'] == '0' and 'eventSearch' in job_summary:
                helper.log_debug("inside if")
                try:
                    alert_events = getRawEventsFromSplunk(helper, session_key, search_params, job_summary, events)
                    for events_part in alert_events:
                        helper.log_info(events_part)
                        if not events_part["events"]:
                            helper.log_info(f"Couldn't find events for alert {helper._alert_name}")
                            continue
                        first_event = events_part['events'][0]
                        props = getEventProps(helper, config, first_event)
                        kv_record['environment'] = props['environment']
                        kv_record['product'] = props['product']
                        kv_record['vendor'] = props['vendor']
                        kv_record['priority'] = props['priority']
                        kv_record['alertname'] = props['alertname']
                        event_list = []
                        for e in events_part['events']:
                            expand_src_dest = 1
                            if expand_src_dest:
                                expanded_events = expand_mv_events(helper, e, events_part['search_query'])
                                event_list.extend(expanded_events)
                        events_flat = []
                        for e in event_list:
                            e_flat = dict_to_flat(e)
                            events_flat.append(e_flat)
                        events_part['events'] = events_flat


                        alert_header = buildAlertHeader(config)
                        case = dict(alert_header, **events_part)
                        post_case(helper, kv_mgr, config, props, case, kv_record)
                except Exception as e:
                    helper.log_error(f"Exception: {e}")
                    if config.expand_mv and config.expand_mv != 0:
                        events = expand_mv(helper, events)
                    events_part = {'events': [{k: v for k, v in list(event.items()) if v} for event in events]}

            else:
                if config.trigger_per_result and config.trigger_per_result != 0:
                    if config.expand_mv and config.expand_mv != 0:
                        events = expand_mv(helper, events)
                    #events_part = {'events': [dict((k, v) for k, v in event.iteritems() if v) for event in events]}
                    for event in events:
                        events_part = {'events': [{k: v for k, v in list(event.items()) if v}] }
                        if not events_part["events"]:
                            helper.log_info(f"Couldn't find events for alert {helper._alert_name}")
                            continue
                        first_event = events_part['events'][0]
                        props = getEventProps(helper, config, first_event)
                        kv_record['environment'] = props['environment']
                        kv_record['product'] = props['product']
                        kv_record['vendor'] = props['vendor']
                        kv_record['priority'] = props['priority']
                        kv_record['alertname'] = props['alertname']

                        alert_header = buildAlertHeader(config)
                        case = dict(alert_header, **events_part)
                        post_case(helper, kv_mgr, config, props, case, kv_record)
                else:
                    if config.expand_mv and config.expand_mv != 0:
                        events = expand_mv(helper, events)
                    events_part = {'events': [{k: v for k, v in list(event.items()) if v} for event in events]}
                    if not events_part["events"]:
                        helper.log_info(f"Couldn't find events for alert {helper._alert_name}")
                        retry_failed_alerts(helper, config, headers)
                        return
                    first_event = events_part['events'][0]
                    props = getEventProps(helper, config, first_event)
                    kv_record['environment'] = props['environment']
                    kv_record['product'] = props['product']
                    kv_record['vendor'] = props['vendor']
                    kv_record['priority'] = props['priority']
                    kv_record['alertname'] = props['alertname']

                    alert_header = buildAlertHeader(config)
                    case = dict(alert_header, **events_part)
                    post_case(helper, kv_mgr, config, props, case, kv_record)

        except Exception as err:
            helper.log_debug("")
            helper.log_debug(f"Error Getting Events:\n{str(err)}\n\n{traceback.format_exc()}")
    except Exception as err:
        helper.log_debug(f'General Error:\n{str(err)}\n\n{traceback.format_exc()}')

    retry_failed_alerts(helper, config, headers)

def convert_timestamp(helper, time_value):
    time_format = helper.get_param("time_format")
    if not time_format:
        return time_value
    try:
        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time_value)))
        helper.log_debug(f'Time is epoch: "{time_value}"')
        return time_value
    except:
        helper.log_info(f'Provided time({time_value}) is not epoch. Converting...')
    try:
        converted_value = str(int(time.mktime(time.strptime(time_value, time_format))))
        helper.log_debug(f'Successfully converted from {time_value} to "{converted_value}" using format {time_format}')
        return converted_value
    except Exception as e:
        helper.log_error(f'Unable to convert "{time_value}" from format "{time_format}". Error is: {e}')
    return time_value

def post_case(helper, kv_mgr, config, props, case, kv_record):
    record_created = False
    try:
        splunk_payload = case
        kv_record['siemplify_alert_name'] = splunk_payload.get('alertname', 'Undefined Alert Name'),
        headers = {"AppKey": config.token, 'Content-Type': 'application/json'}
        events = []
        for event in splunk_payload['events']:
            event_props = getEventProps(helper, config, event)
            events.append(extract_splunk_event_data(event, product_field=event_props['product'],
                                                    environment=splunk_payload['environment'],
                                                    vendor_field=event_props['vendor'],
                                                    event_type_field=helper.get_param("event_type"),
                                                    time_field=helper.get_param("time_field"),
                                                    category=helper.get_param("category"),
                                                    helper=helper))

        # id = hash_first_event_with_alert_data(splunk_payload, events, helper)
        id = str(uuid.uuid4())
        kv_record['_key'] = id
        payload = PAYLOAD.format(device_product=props['product'],
                                 ticket_id=id,
                                 alert_name=props.get('alertname', 'Undefined Alert Name'),
                                 environment=splunk_payload['environment'],
                                 description=props.get('alertname', 'Undefined Alert'),
                                 display_id=id,
                                 reason='No ',
                                 device_vendor=props['vendor'],
                                 start_time=events[0]["_fields"]['StartTime'],
                                 end_time=events[0]["_fields"]['StartTime'],
                                 #start_time=splunk_payload['start_time'],
                                 #start_time=str(int(round(time.time() * 1000))),
                                 #end_time=str(int(round(time.time() * 1000))),
                                 rule_generator=props.get('alertname', 'Unknown Event'),
                                 priority=PRIORITY.get(props['priority'].lower()))

        json_payload = json.loads(payload)
        events2=[]
        for i in events:
            tmp=i
            new={}
            for j in list(i['_rawDataFields'].keys()):
                try:
                    key = j.decode('utf-8')
                except:
                    key = j
                try:
                    value = i['_rawDataFields'][j].decode('utf-8')
                except:
                    value = i['_rawDataFields'][j]
                new[key] = value
            tmp['_rawDataFields'] = new
            events2.append(tmp)
        events=events2
        json_payload['Cases'][0]['Events'] = events
        kv_record['case_data'] = json.dumps(json_payload)
        
        kv_record['status'] = "pending"
        kv_record['return_msg'] = "Pending Sent Alert"
        kv_record['last_send_attempt'] = str(int(round(time.time())))
        
        try:
            data = kv_mgr.addToKVStore("siemplify_alerts", kv_record)
            record_created = True
        except Exception as e:
            helper.log_error(f"Failed to add to KVStore: {e}")
            raise e
        if config.mode == 'push':
            res = requests.post(config.uri + "/api/external/v1/cases/CreateCase", headers=headers,
                        json=json_payload)
            res.raise_for_status()
        kv_record['alert_sent'] = str(int(round(time.time())))

        helper.log_info(f"Success sending id: {id} to Siemplify")
        kv_record['status'] = "success"
        kv_record['return_msg'] = "Sent Alert"
        if record_created:
            try:
                kv_mgr.updateKVStoreRecord("siemplify_alerts", kv_record['_key'], kv_record)
            except Exception as e:
                current_time = int(round(time.time()))
                interval = current_time - int(kv_record.get('last_send_attempt', current_time))
                helper.log_error(f"updateKVStoreRecord failed for success status after {interval} seconds from add. Error: {e}")
        if config.mode == 'push':
            try:
                helper.log_info(f"Sending to secondary: {config.uri_secondary}")
                headers_secondary = {"AppKey": config.token_secondary, 'Content-Type': 'application/json'}
                res = requests.post(config.uri_secondary + "/api/external/v1/cases/CreateCase", headers=headers_secondary,
                            json=json_payload)
            except Exception as e:
                helper.log_debug("Secondary server not configured")


    except Exception as err:
        helper.log_debug(f'Error in REST part\n{str(err)}\n\n{traceback.format_exc()}')
        helper.log_info("Error connecting to Siemplify.  Retrying id: {}".format(kv_record['_key']))
        kv_record['status'] = "retrying"
        kv_record['error_msg'] =f'{str(err)}'
        kv_record['return_msg'] = "Error connecting to Siemplify.  Retrying"
        if record_created:
            try:
                kv_mgr.updateKVStoreRecord("siemplify_alerts", kv_record['_key'], kv_record)
            except Exception as e:
                current_time = int(round(time.time()))
                interval = current_time - int(kv_record.get('last_send_attempt', current_time))
                helper.log_error(f"updateKVStoreRecord failed for retry status after {interval} seconds from add. Error: {e}")

def retry_failed_alerts(helper, config, headers):

        session_key = helper.session_key
        failed_alert = {}
        helper.log_debug("Retrying any queued failed alerts")
        kv_mgr = splunkquery(sessionkey=session_key, helper=helper)
        try:
            failed_alerts = kv_mgr.getKVStoreRecordbyKey("siemplify_alerts", "status", "retrying")
            
            try:
                pending_alerts = kv_mgr.getKVStoreRecordbyKey("siemplify_alerts", "status", "pending")
                current_time = int(round(time.time()))
                # Filter for pending alerts that are older than 5 minutes (300 seconds)
                stuck_pending = [
                    alert for alert in pending_alerts 
                    if current_time - int(alert.get('last_send_attempt', 0)) > 300
                ]
                helper.log_debug(f"Found {len(stuck_pending)} stuck pending alerts.")
                failed_alerts.extend(stuck_pending)
            except Exception as e:
                helper.log_debug(f"Error checking for pending alerts: {e}")
                
            helper.log_debug(f"found {len(failed_alerts)} messages needing to be retryed.")
            for failedalert in failed_alerts:
                try:
                    failed_alert = failedalert
                    helper.log_debug(failed_alert)
                    if failed_alert['retry_count'] < MAX_RETRY:
                        helper.log_debug("Retrying ID: {}".format(failed_alert['_key']))
                        failed_alert['last_send_attempt'] = str(int(round(time.time())))
                        if config.mode == 'push':
                            res = requests.post(config.uri + "/api/external/v1/cases/CreateCase", headers=headers,
                                             json=json.loads(failed_alert['case_data']), timeout=(2,5))
                            res.raise_for_status()
                        failed_alert['alert_sent'] = str(int(round(time.time())))
                        failed_alert['status'] = "success"
                        failed_alert['return_msg'] = "Sent Alert"
                        helper.log_debug("Successfully sent retry for id: {}".format(failed_alert['_key']))
                        helper.log_info("Success sending id: {} to Siemplify".format(failed_alert['_key']))
                        kv_mgr.updateKVStoreRecord("siemplify_alerts", failed_alert['_key'], failed_alert)
                    else:
                        failed_alert['return_msg'] = 'Too many retries'
                        failed_alert['status'] = 'failed'
                        helper.log_debug('Failing alert due to too many retries id: {}'.format(failed_alert['_key']))
                        helper.log_error("Failed to connect to Siemplify. Failing alert sid: {}"
                                         .format(failed_alert['sid']))
                        kv_mgr.updateKVStoreRecord("siemplify_alerts", failed_alert['_key'], failed_alert)
                except Exception as err:
                    helper.log_error(f"Error: {str(err)}\n{traceback.format_exc()}")
                    if failed_alert['retry_count'] < MAX_RETRY:
                        failed_alert['retry_count'] = failed_alert['retry_count'] + 1
                        failed_alert['error_msg'] = f"{str(err)}"
                        failed_alert['return_msg'] = "Failed to connect, retrying"
                        helper.log_info('Updating retry count for id: {}'.format(failed_alert['_key']))
                        helper.log_info("Failed to connect to Siemplify.  Retrying alert id: {}"
                                        .format(failed_alert['_key']))
                        kv_mgr.updateKVStoreRecord("siemplify_alerts", failed_alert['_key'], failed_alert)
                    else:
                        failed_alert['error_msg'] = f"{str(err)}"
                        failed_alert['return_msg'] = "Too many retries."
                        failed_alert['status'] = 'failed'
                        helper.log_error('setting alert to failed due to too many retries id: {}'
                                         .format(failed_alert['_key']))
                        kv_mgr.updateKVStoreRecord("siemplify_alerts", failed_alert['_key'], failed_alert)
        except Exception as err:
            helper.log_error(f"Failed. {str(err)}\n{traceback.format_exc()}")

def get_search_params(helper):
    """
    Get alert search parameters from info.csv file. Usually it is stored into dispatch/searchname_tempvalue
    :param helper: Splunk Helper
    :return: Search Params
    """

    try:
        info_file = helper.info_file

        # If per result alert is selected - then the path given by splunk of the info file might be wrong
        # But the actual info file can be in the following path:
        # /opt/splunk/var/run/splunk/dispatch/scheduler__admin__search__RMD5e94c3e24a8d563a5_at_1528897080_68/info.csv
        # So check if the path is correct and replace if necessary.
        if not os.path.exists(info_file):
            info_file = os.path.join(os.path.dirname(os.path.dirname(info_file)), os.path.basename(info_file))
        with open(info_file) as info:
            info_data = info.read()

        helper.log_debug(f'info.csv is placed {info_file}')

        info_data_json = extract_csv(info_data)[0]
        #helper.log_debug("info data is : {}".format(json.dumps(info_data_json)))
        required_params = ['_search', '_startTime', '_endTime', '_sid', 'eventSearch', 'fieldMetadataStatic', 'field_metadata' ]
        return dict([i for i in iter(list(info_data_json.items())) if i[0] in required_params])
    except Exception as err:
        helper.log_debug(f'get_search_params {err}\n\n{traceback.format_exc()}')

def extract_csv(stats_data):
    data_reader = csv.DictReader(stats_data.split('\n'), delimiter=',', quotechar='\"')
    return [row for row in data_reader]

def buildAlertHeader(config):
    return {
        "alertname": config.title,
        "category": config.category,
        "priority": config.priority,
        "environment": config.env,
    }

def getRawDataFromSplunk(helper, sessionkey, search_params, job_summary, events):
    sq = splunkquery(sessionkey=sessionkey, helper=helper)
    helper.log_debug('Created Splunk Query object.')
    start_time = turnEpochTimeToISO(search_params['_startTime'])
    end_time = turnEpochTimeToISO(search_params['_endTime'])
    try:
        helper.log_debug("======= Inside getRawDataFromSplunk ======")
        helper.log_debug("raw search is: {}".format(job_summary['eventSearch']))
        filtered_searches = _buildFilteredSearch(helper, job_summary, events)
        helper.log_debug(f"filtered searches are: {filtered_searches}")
        results = []
        for filtered_search in filtered_searches:
            data = sq.runSearchGetEvents(searchQuery=filtered_search['query'],
                                         head=MAX_EVENTS,
                                         earliestTime=start_time,
                                         latestTime=end_time)
            results.append({"events": json.loads(data),
                            "start_time": start_time,
                            "end_time": end_time,
                            "search_query": filtered_search})
        return results
    except Exception as e:
        helper.log_error("Failed to get data")
        helper.log_error(e)

def getRawEventsFromSplunk(helper, sessionkey, search_params, job_summary, alert_events):
    """

    :param helper:
    :param sessionkey:
    :param search_request:
    :param search_params:
    :return:
    """
    sq = splunkquery(sessionkey=sessionkey, helper=helper)
    helper.log_debug('Created Splunk Query object.')

    start_time = turnEpochTimeToISO(search_params['_startTime'])
    end_time = turnEpochTimeToISO(search_params['_endTime'])

    try:
        data = sq.getEvents(search_params['_sid'])
        helper.log_debug('Get events from Splunk for {}'.format(search_params['_search']))
        if data == "[]":
            events = getRawDataFromSplunk(helper, sessionkey, search_params, job_summary, alert_events)
            if events:
                return events
        return {"events": json.loads(data),
                "start_time": start_time,
                "end_time": end_time }

    except Exception as err:
        helper.log_error(f'Error getting data from Splunk {err}')

def turnEpochTimeToISO(utc_datetime):
# This is a Fedex specific fix.
#    utc_datetime = datetime.utcfromtimestamp(float(utc_datetime))
#    cst_datetime = utc_datetime - timedelta(hours=5)
#    return cst_datetime.isoformat()

    utc_datetime = datetime.utcfromtimestamp(float(utc_datetime))
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    required_datetime = utc_datetime + offset
    return required_datetime.isoformat()

def _buildFilteredSearch(helper, job_summary, stats_data):
    helper.log_debug("Initial raw search is: {}".format(job_summary['eventSearch']))
    filtered_search = ''
    search_queries = []
    helper.log_debug(f"job_summary: {job_summary}")
    if 'fieldMetadataStatic' in job_summary:
        for data in stats_data:
            search_query = {}
            search_query['group_by_fields'] = []
            params = ''
            for group_by_field in job_summary['fieldMetadataStatic']:
                if group_by_field in data and 'groupby_rank' in job_summary['fieldMetadataStatic'][group_by_field]:
                    helper.log_debug(group_by_field)
                    group_by = {}
                    if not params:
                        params = group_by_field + '=\"' + data[group_by_field].replace('"', '\\"')  + '\"'
                    else:
                        params += ' AND '
                        params = params + group_by_field + '=\"' + data[group_by_field].replace('"', '\\"') + '\"'
                    group_by['field'] = group_by_field
                    group_by['value'] = data[group_by_field]
                    search_query['group_by_fields'].append(group_by)
            params = job_summary['eventSearch'] + ' | where ' + params
            search_query['query'] = params
            search_queries.append(search_query)
    else:
        search_query = {}
        search_query['group_by_fields'] = []
        search_query['query'] = job_summary['eventSearch']
        search_queries.append(search_query)
    return search_queries

