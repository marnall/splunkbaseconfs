import os
import io
from six.moves import configparser
import json
import time
from datetime import datetime, timedelta
import calendar
from requests.compat import quote_plus


from splunk.clilib.bundle_paths import make_splunkhome_path

input_stanza = None
input_name = None
credential_compromise_list = []
ioc_id_list = []
MAPPING_SOURCETYPE = {
    'incidents':'ds:search:alerts',
    'intel_incidents': 'ds:search:intel:incidents',
    'credential:compromise': 'ds:search:credentials',
    'risk_pipeline': 'ds:search:riskpipeline',
    'intel_ioc_incidents': 'ds:search:intel:iocs',
    'verbose': 'verbose'
}

# List of dictionaries of incidents and it's types
all_incident_types = [
    {"type": "DATA_LEAKAGE",
     "subTypes": ["CREDENTIAL_COMPROMISE", "CUSTOMER_DETAILS", "INTELLECTUAL_PROPERTY", "INTERNALLY_MARKED_DOCUMENT",
                  "LEGACY_MARKED_DOCUMENT", "PROTECTIVELY_MARKED_DOCUMENT", "TECHNICAL_LEAKAGE", "UNMARKED_DOCUMENT"]},
    {"type": "BRAND_PROTECTION",
     "subTypes": ["BRAND_MISUSE", "DEFAMATION", "MOBILE_APPLICATION", "NEGATIVE_PUBLICITY", "SPOOF_PROFILE",
                  "PHISHING_ATTEMPT"]},
    {"type": "INFRASTRUCTURE", "subTypes": ["DOMAIN_CERTIFICATE_ISSUE", "EXPOSED_PORT", "CVE"]},
    {"type": "INFRASTRUCTURE", "subTypes": ["DOMAIN_CERTIFICATE_ISSUE", "EXPOSED_PORT", "CVE"]},
    {"type": "PHYSICAL_SECURITY", "subTypes": ["COMPANY_THREAT", "EMPLOYEE_THREAT", "PERSONAL_INFORMATION"]},
    {"type": "SOCIAL_MEDIA_COMPLIANCE",
     "subTypes": ["CORPORATE_INFORMATION", "PERSONAL_INFORMATION", "TECHNICAL_INFORMATION"]},
    {"type": "CYBER_THREAT", "subTypes": []}
]


def get_time(time_ip, helper):
    """ This method returns the epoch time for given time format
        :param time_ip: The time in the format of mentioned pattern
        :param helper:
        :return: integer with epoch value or None
    """
    # date_time = '1970-07-16T06:16:23.777000Z'
    try:
        pattern = '%Y-%m-%dT%H:%M:%S.%fZ'
        epoch = int(calendar.timegm(time.strptime(time_ip, pattern)))
        return epoch
    except Exception as e:
        helper.log_error('Exception while getting the time' + str(e))
        return None


def get_intel_incidents_header(types, date_range, offset):
    """ This method returns the request body payload for intel incidents
        :param types The types of the incidents which needs to be fetched
        :param date_range: The range of the date
        :param offset: The starting number for the incidents
        :return: dictionary of the request body payload
    """
    return {
        "filter": {
            "severities": [],
            "tags": [],
            "tagOperator": "AND",
            "dateRange": date_range,
            "dateRangeField": "modified",
            "types": [] if types is None else types,
            "withFeedback": "true",
            "withoutFeedback": "true"
        },
        "sort": {
            "property": "date",
            "direction": "ASCENDING"
        },
        "pagination": {
            "size": 50,
            "offset": offset
        }
    }


def handle_verbose(content):
    """ This method updates the list for fetching verbose information of Credential Compromise incidents
        :param content: The json data containing info of one incident
        :return: None
    """
    if content.get('subType') != "CREDENTIAL_COMPROMISE":
        return
    elif content['entitySummary'].get("dataBreach") is None:
        return

    global credential_compromise_list
    id = content['entitySummary']["dataBreach"].get("id")
    credential_compromise_list.append(id)


def handle_intel_ioc(content):
    """ This method updates the list for fetching ioc information of Intel incidents
                 :param content: The json data containing info of one incident
                 :return: None
    """
    try:
        if content.get('indicatorOfCompromiseCount',0) > 0:
            global ioc_id_list
            ioc_id = content.get("id")
            ioc_id_list.append(ioc_id)
    except Exception as e:
        return


def write_to_splunk(helper, r_json, ew, incident_private_intel):
    """ This method writes the incidents to Splunk
        :param helper:
        :param r_json: response content
        :param ew:
        :param incident_private_intel: Whether writing to private or intel incident
        :return: None
    """
    try:
        # Extract the last incident for checkpoint mechanism
        checkpoint_event = r_json[-1]

        # Write every incident to Splunk
        if input_stanza[input_name]['verbose'] == '1' and incident_private_intel == 'incidents':
            for content in r_json:
                handle_verbose(content)
                event = helper.new_event(data=json.dumps(content), time=None,
                                     host=None, index=input_stanza[input_name]['index'], source='radark_app',
                                     sourcetype=MAPPING_SOURCETYPE[incident_private_intel], done=True, unbroken=True)
                ew.write_event(event)
        elif incident_private_intel == "intel_incidents":
            for content in r_json:
                handle_intel_ioc(content)
                event = helper.new_event(data=json.dumps(content), time=None,
                                     host=None, index=input_stanza[input_name]['index'], source='radark_app',
                                     sourcetype=MAPPING_SOURCETYPE[incident_private_intel], done=True, unbroken=True)
                ew.write_event(event)
        elif incident_private_intel == "intel_ioc_incidents":
            for content in r_json:
                if content.get("source"):
                    content["ioc_source"] = content.pop("source")
                event = helper.new_event(data=json.dumps(content), time=None,
                                     host=None, index=input_stanza[input_name]['index'], source='radark_app',
                                     sourcetype=MAPPING_SOURCETYPE[incident_private_intel], done=True, unbroken=True)
                ew.write_event(event)
            helper.log_debug('Successfully created splunk events of type:' + MAPPING_SOURCETYPE[incident_private_intel])
            return
        else:
            for content in r_json:
                event = helper.new_event(data=json.dumps(content), time=None,
                                     host=None, index=input_stanza[input_name]['index'], source='radark_app',
                                     sourcetype=MAPPING_SOURCETYPE[incident_private_intel], done=True, unbroken=True)
                ew.write_event(event)

        # Update checkpoint after the events have been written successfully
        checkpoint = helper.get_check_point(input_name) or dict()
        if incident_private_intel == 'incidents':
            checkpoint["private_incident"] = checkpoint_event["modified"]
            helper.save_check_point(input_name, checkpoint)
        else:
            checkpoint["intel_incident"] = checkpoint_event["modified"]
            helper.save_check_point(input_name, checkpoint)
        helper.log_debug('Successfully created splunk events of type:' + MAPPING_SOURCETYPE[incident_private_intel])
    except Exception as e:
        helper.log_error('Exception while writing to splunk of type:' + MAPPING_SOURCETYPE[incident_private_intel] + 'With error:' + str(e))
        raise


def write_verbose(helper, r_json, ew, cc_id):
    """ This method writes the verbose incidents to Splunk
        :param helper:
        :param r_json: response content
        :param ew:
        :return:None
    """
    try:
        # Write every incident to Splunk
        for content in r_json:
            content['dataBreachId'] = str(cc_id)
            event = helper.new_event(data=json.dumps(content), time=None,
                                     host=None, index=input_stanza[input_name]['index'], source='radark_app',
                                     sourcetype=MAPPING_SOURCETYPE['credential:compromise'], done=True, unbroken=True)
            ew.write_event(event)
        helper.log_debug('Successfully created splunk events of type:' + MAPPING_SOURCETYPE['credential:compromise'])
    except Exception as e:
        helper.log_error('Exception while writing to splunk of type:' + MAPPING_SOURCETYPE['credential:compromise'] + 'With error:' + str(e))
        raise


def scroll_incidents(helper, proxy, ew, info, incident_private_intel, cc_id=None):
    """ This method fetches the incidents in batch
        :param helper:
        :param proxy: Decides if the proxy is enabled or not
        :param ew:
        :param info: Dictionary with headers, payload and url
        :param incident_private_intel: Decides the type of incidents that needs to be collected
        :param cc_id: The id of credential compromise
        :return: None
    """
    try:
        helper.log_debug('Collecting Events for: ' + MAPPING_SOURCETYPE[incident_private_intel])

        # This loop will fetch the events in batch until all of them are fetched and written to Splunk
        while True:
            response = helper.send_http_request(info['url'], method="POST", parameters=None,
                                                payload=info['payload'],
                                                headers=info['headers'], cookies=None, verify=True, cert=None,
                                                timeout=60.0, use_proxy=proxy)
            if response.status_code == 200:
                r_json = response.json()
                offset = r_json["currentPage"]["offset"]
                size = r_json["currentPage"]["size"]
                total = r_json["total"]

                if total == 0:
                    pass
                else:
                    if incident_private_intel == 'verbose':
                        time.sleep(0.4)
                        write_verbose(helper,r_json['content'], ew, cc_id)
                    else:
                        write_to_splunk(helper, r_json['content'], ew, incident_private_intel)

                helper.log_debug(" Offset " + str(offset) +
                                " Size " + str(size) +
                                " Total " + str(total))

                # Stop the fetching of events if all of them have been fetched
                if offset + size < total:
                    info['payload']['pagination']['offset'] = offset + r_json["currentPage"]["size"]
                else:
                    break
            elif response.status_code == 429:
                r_json = response.json()
                retryAfter = r_json['retryAfter']
                retryAfter = get_time(retryAfter, helper)
                if not retryAfter:
                    helper.log_error('Rate limit exceeded...Cannot parse retryAfter field')
                    raise Exception('Rate limit exceeded...Cannot parse retryAfter field')
                current = int(calendar.timegm(time.gmtime()))
                wait_time = retryAfter - current
                if wait_time > 300:
                    helper.log_error('Rate limit exceeded...Wait time too high. Hence, exiting from this '
                                     'round of data collection and will retry in next invocation.')
                    raise Exception('Rate limit exceeded...Wait time too high. Hence, exiting from this '
                                    'round of data collection and will retry in next invocation.')
                elif wait_time < 0:
                    pass
                else:
                    helper.log_info('Rate limit exceeded... Will retry in {} seconds'.format(wait_time))
                    time.sleep(wait_time)
            else:
                helper.log_error("For {} status code-------- {}".format(info['url'], str(response.status_code)))
                break
    except Exception as e:
        helper.log_error('Exception while scrolling private incidents' + str(e))
        raise


def get_incidents_header(types, daterange, offset):
    """ This method returns the request body payload for private incidents
        :param types The types of the incidents which needs to be fetched
        :param daterange: The range of the date
        :param offset: The starting number for the incidents
        :return: Dictionary containing the request body payload
    """

    return {
        "filter": {
            "severities": [],
            "tags": [],
            "tagOperator": "AND",
            "dateRange": daterange,
            "dateRangeField": "modified",
            "types": [] if types is None else types,
            "withFeedback": 'true',
            "withoutFeedback": 'true',
            "alerted": 'false',
            "withTakedown": 'true',
            "withoutTakedown": 'true',
            "withContentRemoved": 'true',
            "withoutContentRemoved": 'true',
            "statuses": [
                "UNREAD",
                "READ",
                "CLOSED"
            ],
            "repostedCredentials": []
        },
        "sort": {
            "property": "date",
            "direction": "ASCENDING"
        },
        "pagination": {
            "size": 50,
            "offset": offset
        },
        "subscribed": 'false'
    }


def set_input(stanza, name):
    """ This method sets two global parameters
        :param stanza: The input stanza with information
        :param name: Name of input stanza
        :return: None
    """
    global input_stanza, input_name
    input_stanza = stanza
    input_name = name


def get_verbose_header():
    """ This method returns the request payload boady for verbose
        :return: Dictionary of request body payload
    """
    return {
      "filter": {
        "published": "ALL",
        "domainNames": [],
        "reviewStatuses": []
      },
      "sort": {
        "property": "username",
        "direction": "ASCENDING"
      },
      "pagination": {
        "size": 50,
        "offset": 0
      }
    }


def get_intel_ioc_header():
    """ This method returns the request payload boady for verbose
        :return: Dictionary of request body payload
    """
    return {
        "filter": {},
        "sort": {
            "property": "value",
            "direction": "ASCENDING"
            }
        }


def get_types(helper):
    """ This method is used to return the incident types for data collection
        :param helper:
        :return: dictionary extracting the types of incidents to be fetched
    """
    try:
        if input_stanza[input_name]['incident_types'] == '':
            return None
        types = input_stanza[input_name]['incident_types']
        if 'all' in types:
            return None
        list_types = []
        for type_incident in types:
            for each_type in all_incident_types:
                if each_type["type"] == type_incident:
                    list_types.append(each_type)
        return list_types
    except Exception as e:
        helper.log_error('Exception while retrieving types' + str(e) + 'Returning None')
        return None


def get_request_parameters(incident_private_intel, authorization, helper, finaltime):
    """ This method returns the dictionary of the necessary information for making api call for collection
        of events
        :param helper:
        :param authorization: auth param
        :param finaltime: time of indexing
        :param incident_private_intel: Whether writing to private or intel incident
        :return: dictionary of the necessary information for making api call for collection
        of events
    """

    try:
        info = dict()

        info['headers'] = {"Content-Type": "application/vnd.polaris-v36+json", "Accept": "application/vnd.polaris-v36+json",
                       "Authorization": "Basic " + str(authorization)}

        since = input_stanza[input_name].get('since','1970-01-01T00:00:00.000')
        checkpoint = helper.get_check_point(input_name)
        if incident_private_intel == 'intel_incidents':
            if checkpoint and checkpoint.get('intel_incident'):
                helper.log_debug('Checkpoint is present:' + str(checkpoint))
                date = checkpoint.get('intel_incident') + '/' + finaltime
            else:
                helper.log_debug('Checkpoint not present, Starting Time:' + str(since))
                date = since + 'Z' + '/' + finaltime
            info['payload'] = get_intel_incidents_header(get_types(helper), date, '0')
            info['url'] = 'https://' + str(input_stanza[input_name]['global_account']['address']).rstrip('/') + '/api/intel-incidents/find'
        elif incident_private_intel == 'incidents':
            if checkpoint and checkpoint.get('private_incident'):
                helper.log_debug('Checkpoint is present:' + str(checkpoint))
                date = checkpoint.get('private_incident') + '/' + finaltime
            else:
                helper.log_debug('Checkpoint not present, Starting Time:' + str(since))
                date = since + 'Z' + '/' + finaltime
            info['payload'] = get_incidents_header(get_types(helper), date, '0')
            info['url'] = 'https://' + str(input_stanza[input_name]['global_account']['address']).rstrip('/') + '/api/incidents/find'
        return info
    except Exception as e:
        helper.log_error("Exception while getting request parameters:" + str(e))
        raise


def retrieve_verbose_incidents(helper, authorization, proxy, ew):
    """ This method retrieves the verbose incidents for credential compromise
        :param helper:
        :param authorization: auth param
        :param proxy: Decides if the proxy is enabled or not
        :param ew:
        :return: None
    """
    try:
        info = dict()
        info['headers'] = {"Content-Type": "application/vnd.polaris-v36+json",
                           "Accept": "application/vnd.polaris-v36+json",
                           "Authorization": "Basic " + str(authorization)}
        info['payload'] = get_verbose_header()
        global credential_compromise_list
        for cc_id in credential_compromise_list:
            helper.log_debug('fetching info for id:' + str(cc_id))
            info['url'] = 'https://' + str(input_stanza[input_name]['global_account']['address']).rstrip('/') \
                          + '/api/data-breach/' + str(cc_id) + '/records'
            scroll_incidents(helper, proxy, ew, info, 'verbose',cc_id)
    except Exception as e:
        helper.log_error('Exception while retrieving verbose incidents' + str(e))
        raise


def retrieve_intel_ioc(helper, authorization, proxy, ew):
    """ This method retrieves the ioc details for intel incidents
        :param helper:
        :param authorization: auth param
        :param proxy: Decides if the proxy is enabled or not
        :param ew:
        :return: None
    """
    try:
        info = dict()
        info['headers'] = {"Content-Type": "application/vnd.polaris-v36+json",
                           "Accept": "application/vnd.polaris-v36+json",
                           "Authorization": "Basic " + str(authorization)}
        info['payload'] = get_intel_ioc_header()
        global ioc_id_list
        for ioc_id in ioc_id_list:
            helper.log_debug('fetching iocs for id:' + str(ioc_id))
            info['url'] = 'https://' + str(input_stanza[input_name]['global_account']['address']).rstrip('/') \
                          + '/api/intel-incidents/' + str(ioc_id) + '/iocs'
            get_intel_ioc_incidents(helper, proxy, ew, info, range=str(ioc_id))
            time.sleep(1.1)
    except Exception as e:
        helper.log_error('Exception while retrieving ioc for intel incidents' + str(e))
        raise


def get_intel_ioc_incidents(helper, proxy, ew, info, range):
    """ This method retrives and write incidents to splunk
        of events
        :param helper:
        :param proxy:
        :param ew:
        :param info: Information header for request
        :param range: The date range
        :return: None
    """
    type = "intel_ioc_incidents"
    try:
        while True:
            response = helper.send_http_request(info['url'], method="POST", parameters=None,
                                                payload=info['payload'],
                                                headers=info['headers'], cookies=None, verify=True, cert=None,
                                                timeout=60.0, use_proxy=proxy)
            if response.status_code == 200:
                r_json = response.json()
                if r_json['total'] != 0:
                    # adding intel_incident_id for linking IOC to its belonging intel incident
                    for content in r_json['content']:
                        content["intel_incident_id"] = range
                    write_to_splunk(helper, r_json['content'], ew, type)
                    helper.log_debug("Created ioc events for id: {}".format(range))
                break
            elif response.status_code == 429:
                r_json = response.json()
                retryAfter = r_json['retryAfter']
                retryAfter = get_time(retryAfter, helper)
                if not retryAfter:
                    helper.log_error('Rate limit exceeded...Cannot parse retryAfter field')
                    raise Exception('Rate limit exceeded...Cannot parse retryAfter field')
                current = int(calendar.timegm(time.gmtime()))
                wait_time = retryAfter - current
                if wait_time > 300:
                    helper.log_error('Rate limit exceeded...Wait time too high. Hence, exiting from this '
                                     'round of data collection and will retry in next invocation.')
                    raise Exception('Rate limit exceeded...Wait time too high. Hence, exiting from this '
                                    'round of data collection and will retry in next invocation.')
                elif wait_time < 0:
                    pass
                else:
                    helper.log_info('Rate limit exceeded... Will retry in {} seconds'.format(wait_time))
                    time.sleep(wait_time)
            else:
                helper.log_error("For {} status code-------- {}".format(info['url'], str(response.status_code)))
                break
    except Exception as e:
        helper.log_error('Exception in get_intel_ioc_incidents:' + str(e))
        raise

def get_risk_pipeline_body(date_range):
    """ This method returns the dictionary of the request body payload
        of events
        :param date_range: The range of the date
        :return: dictionary of the request body payload
    """
    return {
        "filter": {
            "timeRange": date_range
        }
    }
    
def write_risk_pipeline_to_splunk(data, type, range, helper, ew):
    """This method write risk pipeline data into the splunk
        :param data: dict of particular risl_pipekine data
        :param type: type of the risk
        :param range: The date range
        :return: None
    """
    risk_pipeline_json = data
    risk_pipeline_json['date_range'] = range
    risk_pipeline_json['type'] = type
    event = helper.new_event(data=json.dumps(risk_pipeline_json), time=None,
                                    host=None, index=input_stanza[input_name]['index'],
                                    source='radark_app',
                                    sourcetype=MAPPING_SOURCETYPE['risk_pipeline'], done=True, unbroken=True)
    ew.write_event(event)
    

def get_risk_pipeline(helper, proxy, ew, info, range="LAST_90_DAYS"):
    """ This method retrives and write incidents to splunk for pipeline data
        of events
        :param helper:
        :param proxy:
        :param ew:
        :param type: type of the event
        :param info: Information header for request
        :param range: The date range
        :return: None
    """
    try:
        while True:
            response = helper.send_http_request(info['url'], method="POST", parameters=None,
                                                payload=info['payload'],
                                                headers=info['headers'], cookies=None, verify=True, cert=None,
                                                timeout=60.0, use_proxy=proxy)
            if response.status_code == 200:
                r_json = response.json()
                dict_risk_pipeline = {"coverageCounts": "coverage", "footprintCounts":"footprint","alertAndIncidentCounts":"alertsAndIncidents"} 
                for key in dict_risk_pipeline.keys():
                    write_risk_pipeline_to_splunk(r_json[key], dict_risk_pipeline[key], range, helper, ew)
                break
            elif response.status_code == 429:
                r_json = response.json()
                retryAfter = r_json['retryAfter']
                retryAfter = get_time(retryAfter, helper)
                if not retryAfter:
                    helper.log_error('Rate limit exceeded...Cannot parse retryAfter field')
                    raise Exception('Rate limit exceeded...Cannot parse retryAfter field')
                current = int(calendar.timegm(time.gmtime()))
                wait_time = retryAfter - current
                if wait_time > 300:
                    helper.log_error('Rate limit exceeded...Wait time too high. Hence, exiting from this '
                                     'round of data collection and will retry in next invocation.')
                    raise Exception('Rate limit exceeded...Wait time too high. Hence, exiting from this '
                                    'round of data collection and will retry in next invocation.')
                elif wait_time < 0:
                    pass
                else:
                    helper.log_info('Rate limit exceeded... Will retry in {} seconds'.format(wait_time))
                    time.sleep(wait_time)
            else:
                helper.log_error("For {} status code-------- {}".format(info['url'], str(response.status_code)))
                break
    except Exception as e:
        helper.log_error('Exception in get_risk_pipeline:' + str(e))
        raise

def retrieve_risk_pipeline(helper, authorization, proxy, ew):
    """ This method acts as base for retrieving pipeline incidents
        of events
        :param helper:
        :param authorization: The simple auth credentials
        :param proxy:
        :param ew:
        :return: None
    """
    try:
        info = dict()
        info['headers'] = {"Content-Type": "application/vnd.polaris-v39+json",
                           "Accept": "application/vnd.polaris-v39+json",
                           "Authorization": "Basic " + str(authorization)}
        info['url'] = 'https://' + str(input_stanza[input_name]['global_account']['address']).rstrip('/') \
                      + '/api/risk-detection-pipeline/counts'
        # Pipeline ranges for 30 days, 2 weeks and 1 year
        range_time = []

        range_time_dict = dict()
        range_time_dict['code'] = 'P1D'
        range_time_dict['value'] = 'LAST_24_HOURS'
        range_time.append(range_time_dict)

        range_time_dict = dict()
        range_time_dict['code'] = 'P1W'
        range_time_dict['value'] = 'LAST_7_DAYS'
        range_time.append(range_time_dict)

        range_time_dict = dict()
        range_time_dict['code'] = 'P30D'
        range_time_dict['value'] = 'LAST_30_DAYS'
        range_time.append(range_time_dict)

        range_time_dict = dict()
        range_time_dict['code'] = 'P90D'
        range_time_dict['value'] = 'LAST_90_DAYS'
        range_time.append(range_time_dict)

        for range_item in range_time:
            info['payload'] = get_risk_pipeline_body(range_item['code'])
            get_risk_pipeline(helper, proxy, ew, info, range_item['value'])
    except Exception as e:
        helper.log_error('Exception while retrieving risk pipeline' + str(e))
        raise


def getProxySettings(my_app, entities):
    """ Form Proxy URI
        :param my_app: name of app
        :param entities: dict which will have clear password
        :return: proxy settings
    """
    config = configparser.ConfigParser()
    proxy_settings_conf = os.path.join(
        make_splunkhome_path(["etc", "apps", my_app, "local", "radark_app_settings.conf"]))
    proxies = {}
    if os.path.isfile(proxy_settings_conf):
        with io.open(proxy_settings_conf, 'r', encoding='utf_8_sig') as inputconffp:
            config.readfp(inputconffp)
        proxy_settings = {}
        if config.has_section('proxy'):
            proxy_enabled = int(config.get('proxy', 'proxy_enabled'))
            if proxy_enabled:
                proxy_settings['proxy_port'] = config.get('proxy', 'proxy_port')
                proxy_settings['proxy_url'] = config.get('proxy', 'proxy_url')
                proxy_settings['proxy_type'] = config.get('proxy', 'proxy_type')
                try:
                    proxy_settings['proxy_username'] = config.get('proxy', 'proxy_username')
                    for ent, value in list(entities.items()):
                        if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):
                            cred = json.loads(value.get('clear_password', '{}'))
                            proxy_settings['proxy_password'] = cred.get('proxy_password', '')
                            break
                except:
                    pass
        uri = None
        if proxy_settings and proxy_settings.get('proxy_url') and proxy_settings.get('proxy_type'):
            uri = proxy_settings['proxy_url']
            if proxy_settings.get('proxy_port'):
                uri = '{}:{}'.format(uri, proxy_settings.get('proxy_port'))
            if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
                uri = '{}://{}:{}@{}/'.format(proxy_settings['proxy_type'], quote_plus(proxy_settings['proxy_username']),
                                              quote_plus(proxy_settings['proxy_password']), uri)
            else:
                uri = '{}://{}'.format(proxy_settings['proxy_type'], uri)

        proxies = {
            'http': uri,
            'https': uri
        }

        return proxies
