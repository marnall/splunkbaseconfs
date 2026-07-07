#!/opt/clearsky/bin/python2.7
#
# ClearSky Data Modular Input Script
# Modular script can be configured to pull monitoring data from ClearSky data service
#
# Copyright (c) 2016 ClearSky Data, Inc.
# All Rights Reserved.
#
# NOTICE: All information contained herein is, and remains the property of
# ClearSky Data, Inc. and its suppliers, if any.  The intellectual and
# technical concepts contained herein are proprietary to ClearSky Data, Inc.
# and its suppliers and may be covered by U.S. and Foreign Patents, patents in
# process, and are protected by trade secret or copyright law.  Dissemination
# of this information or reproduction of this material is strictly forbidden
# unless prior written permission is obtained from ClearSky Data, Inc.
#

import sys,os,time,logging,re
import xml.dom.minidom
import requests
import json
from datetime import datetime

from pprint import pprint
from httplib import UNAUTHORIZED, OK

SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
SPLUNK_PORT = 8089
STANZA = None
SESSION_TOKEN = None
DELIMITER = ','

#dynamically load in any eggs 
EGG_DIR = SPLUNK_HOME + '/etc/apps/csdmonitor/bin/'
for filename in os.listdir(EGG_DIR):
    if filename.endswith('.egg'):
        sys.path.append(EGG_DIR + filename) 
       
from splunklib.client import connect
from splunklib.client import Service
from splunklib.results import ResultsReader
from splunklib.results import Message
           
# enable  debug logging
try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client
#http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger('requests.packages.urllib3')
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

SCHEME = """<scheme>
    <title>ClearSky Event Collector</title>
    <description>Collect monitoring data from ClearSky Data service</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>ClearSky input name</title>
                <description>Name of this ClearSky input</description>
            </arg>
            <arg name="client_ip">
                <title>Edge cache IP</title>
                <description>Edge cache virtual IP (client IP)</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="customer_id">
                <title>ClearSky customer ID</title>
                <description>ClearSky customer ID</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="auth_user">
                <title>Authentication User</title>
                <description>Authentication user. It is recommended to use Stats-API account</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="auth_password">
                <title>Authentication Password</title>
                <description>Authentication password</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="polling_interval">
                <title>Polling Interval</title>
                <description>Interval time in seconds to poll the data</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="backoff_time">
                <title>Backoff Time</title>
                <description>Time in seconds to wait for retry after error or timeout</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

# print usage
def print_usage():
    print 'Usage: %s [--scheme|--validate-arguments]'
 
# introspection mode
def do_scheme():
    print SCHEME

# validation mode
def do_validate():
    config = get_validation_config() 
    #TODO
    #if error , print_validation_error & sys.exit(2) 
 
# execution mode    
def do_run(request_list):
    
    #setup globals
    global config
    global SPLUNK_PORT
    global STANZA
    global SESSION_TOKEN 

    config = get_input_config()

    server_uri = config.get('server_uri')
    SPLUNK_PORT = server_uri[18:]
    STANZA = config.get('name')
    SESSION_TOKEN = config.get('session_key')

    # configure management endpoint
    client_ip = config.get('client_ip')
    customer_id = config.get('customer_id','')
    endpoint = '{}/{}/{}'.format(client_ip, customer_id, 'api/v1')

    logging.error('Started input script %s for endpoint %s' % (config['name'], endpoint))
    
    # authentication params
    auth_user = config.get('auth_user')
    auth_password = config.get('auth_password')
    
    http_header_propertys={}
    # http_header_propertys_str=config.get('http_header_propertys')
    # if not http_header_propertys_str is None:
    #     http_header_propertys = dict((k.strip(), v.strip()) for k,v in 
    #           (item.split('=',1) for item in http_header_propertys_str.split(DELIMITER)))
        
    http_proxy=config.get('http_proxy')
    https_proxy=config.get('https_proxy')
    
    proxies={}
    if not http_proxy is None:
        proxies['http'] = http_proxy   
    if not https_proxy is None:
        proxies['https'] = https_proxy 
        
    request_timeout = int(config.get('request_timeout', 120))
    polling_interval = config.get('polling_interval', 60)
    backoff_time = int(config.get('backoff_time', 60))

    verify_cert = bool(config.get('verify_cert', False))
        
    try: 
        req_args = {'verify' : False , 'stream' : False, 'timeout' : float(request_timeout)}
        if http_header_propertys:
            req_args['headers']= http_header_propertys
        if proxies:
            req_args['proxies']= proxies

        # now log in
        session = requests.session()
        url = 'https://{}/login'.format(endpoint)
        result = session.post(url, data={'username': auth_user, 'password': auth_password}, verify=verify_cert)
        if result.status_code != OK:
            terminate_script('Failed to login to URL %s (status code %s)' % (url, result.status_code))
    
        # unlimited request loop                    
        while True:
             
            # Update group stats
            groups = perform_get_request(session, 'https://{}/groups'.format(endpoint), req_args)
            if groups is None:
                time.sleep(float(backoff_time))
                continue
            else:  
                push_data(groups, None)
                # fix group's objectRef that starts from /groups   
                group_ref = groups[0].get('objectRef')
                if group_ref.startswith('/groups'):
                    group_ref = group_ref[7:]

            # Now, get datacenters 
            dcs = perform_get_request(session, 'https://{}{}/dcs'.format(endpoint, group_ref), req_args)
            if dcs is None:
                time.sleep(float(backoff_time))
                continue
            else:    
                push_data(dcs, None)
                for dc in dcs:
                    # retrieve datacenter interfaces
                    dc_ref = dcs[0].get('objectRef')
                    intf = perform_get_request(session, 'https://{}{}/netconfig/interfaces'.format(endpoint, dc_ref), req_args)
                    push_data(intf, None)
   
            # Start processing pod-wide requests
            for request in request_list:      
                # build URL and parameter dictionary          
                resource = request.get('resource')
                url = 'https://{}{}/{}'.format(endpoint, group_ref, resource)
                params = {} 
                params_str = request.get('params')
                if not params_str is None:
                    params = dict((k.strip(), v.strip()) for k,v in 
                        (item.split('=',1) for item in params_str.split(DELIMITER)))
                req_args['params']= params

                # HPA: eventtype is not currently used here except for debugging
                eventtype = request.get('eventtype','unknown')
                timefield = request.get('timefield')

                # do GET request now
                data = perform_get_request(session, url, req_args)
                if data is None:
                    time.sleep(float(backoff_time))
                    continue

                # get request's checkpoint; value will be 0 if there are no checkpoints
                checkpoint = get_checkpoint(request)

                # push events to Splunk 
                logging.debug('Processing %d events of type %s; checkpoint = %s' % (len(data), eventtype, checkpoint)) 
                new_checkpoint = checkpoint
                pushed = 0
                for event in data:
                    try:
                        if timefield is not None:
                            # only push new event if timestamp (rounded to milliseconds) is greater than the last indexed one
                            timestamp = long(event[timefield])
                            new_checkpoint = max(timestamp, new_checkpoint)    
                            if timestamp > checkpoint:
                                push_event(event, long(timestamp / 1000))   # round to seconds
                                pushed += 1
                        else:
                            # timefield not defined, index with system time      
                            push_event(event, None)
                            continue
                    except Exception,e:
                        logging.error('Failed to stream event: %s' % str(e))  

                # update checkpoint
                request['checkpoint'] = new_checkpoint
                logging.debug('Pushed %d events of type %s; new checkpoint = %s' % (pushed, eventtype, new_checkpoint))   
                
            # sleep now
            time.sleep(float(polling_interval))

    except RuntimeError,e:
        terminate_spript('Runtime error: %s' % str(e))

# perform GET request to the ClearSky endpoint
def perform_get_request(session, url, req_args):
    try:
        result = session.get(url, **req_args)
    except requests.exceptions.Timeout,e:
        logging.error('HTTP Request Timeout error: %s' % str(e))
        return None
    except Exception as e:
        logging.error('Exception performing request: %s' % str(e))
        return None
    
    # check HTTP status
    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError,e:
        error_output = result.text
        error_http_code = result.status_code
        logging.error('HTTP Request error: %s' % str(e))
        return None

    # returns parsed data
    try:
        data = json.loads(result.text)
        return data 
    except RuntimeError,e:
        logging.error('Error parsing GET response output: %s' % str(e))
        return None 

# parse and push data to the stream with the same timestamp (optional)
def push_data(data, timestamp):
    # process JSON data and stream events
    for event in data:
        push_event(event, timestamp)
 
# parse and push single event to the stream
# function returns the timestamp of the latest pushed event
def push_event(event, timestamp):
    # process JSON data and stream events
        # extract event time and convert to seconds 
        try:
            # set host property to match the endpoint
            print_xml_event(json.dumps(event), timestamp)
            logging.debug('Pushed event with timestamp %s' % (timestamp)) 
        except RuntimeError,e:
            logging.error('Failed to stream event: %s' % str(e))          

# exit script
def terminate_script(error_str):
    # no need to logout because we will be here only if lost connection 
    #try:
    #   result = session.post('https://{}/logout'.format(endpoint))
    #except RuntimeError,e:
    #    logging.error('Error handling the response output: %s' % str(e))
    logging.error('Terminated input script %s with error: %s' % (config['name'], error_str))
    if error_str is not None:
        sys.exit(error_str)
    else:
        sys.exit(0)        
        
# generate checkpoint file name
# HPA: file based checkpointing in not currently used
# def get_checkpoint_file(request):
#     # encode the URL (simply to make the file name recognizable)
#     #Applications/Splunk/var/lib/splunk/modinputs/csd
#     endpoint = config.get('endpoint')
#     resource = request['resource']
#     name = endpoint.replace('/','_') + '_' + resource.replace('/','_')
#     return os.path.join(config["checkpoint_dir"], name)

# simply creates a checkpoint file indicating that the URL was checkpointed
# HPA: file based checkpointing in not currently used
# def save_checkpoint_file(url):
#     chk_file = get_checkpoint_file(config, url)
#     # just create an empty file name
#     logging.info("Checkpointing url=%s file=%s", url, chk_file)
#     f = open(chk_file, "w")
#     f.close()

# get checkpint for the request type, rounded to milliseconds
def get_checkpoint(request):
    # if it was cached already, just return cached value
    checkpoint = request.get('checkpoint', 0L)
    if checkpoint > 0:
        return checkpoint

    # data object timefield and query must be defined 
    timefield = request.get('timefield')
    query = request.get('query')
    if timefield is None or query is None:
        return 0L

    # execute the search query
    try:
        last_event = get_last_indexed_event(query)
        if last_event is not None:
            checkpoint = long(last_event[timefield])
    except RuntimeError,e:
        logging.error('Failed to extract time from indexed event = %s: %s' % (last_event,str(e)))

    return checkpoint

# execute query to Splunk to retrieve last event data in JSON format
# method returns None if there are no events found 
def get_last_indexed_event(query): 
    try:
        args = {'host': 'localhost', 'port': SPLUNK_PORT, 'token': SESSION_TOKEN}
        service = Service(**args)   

        # Run a one-shot search and parse XML results using the results reader
        full_query = 'search index="clearskydata" ' + query
        results = service.jobs.oneshot(full_query, sort_dir='desc', count=1)

        event = None
        reader = ResultsReader(results)
        for result in reader:
            if isinstance(result, Message):
                # Diagnostic messages may be returned in the results
                logging.debug('Query diagnostics Message = %s: %s' % (result.type, result.message))
            elif isinstance(result, dict):
                # Normal events are returned as dicts
                # HPA: we could use standard _time field to get time in milliseconds but it is returned as a string in 
                # search results and must be parsed from the UNIX time string (like '2016-04-04T15:33:19.951-04:00') 
                # Instead, we will retrieve the original timestamp field value from the raw data object (expressed in ms)
                raw_data = result.get('_raw')
                event = json.loads(raw_data)

        logging.debug('Executed query = %s; event data = %s' % (full_query,event)) 
        return event

    except Exception,e:
        logging.error('Failed to execute Splunk query = %s: %s' % (full_query,str(e)))
        return None

# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print '<error><message>%s</message></error>' % encode_xml_text(s)
    
# prints single XML event with a time tag to be consumed by Splunk
def print_xml_event(s, timestamp):
    time_tag = '' 
    if timestamp is not None:
        time_tag = '<time>' + str(timestamp) + '</time>'
    # override host property with CSD input name
    input_name = config['input_name']
    print '<stream><event><data>%s</data><host>%s</host>%s</event></stream>' % (encode_xml_text(s), input_name, time_tag)

# prints XML stream with unbroken events
def print_xml_stream(s):
    print '<stream><event unbroken=\'1\'><data>%s</data><done/></event></stream>' % encode_xml_text(s)

# prints simple stream
def print_simple(s):
    print '%s\n' % s

# encode text for XML output
def encode_xml_text(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_input_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        
        session_key_node = root.getElementsByTagName('session_key')[0]
        if session_key_node and session_key_node.firstChild and session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:
            data = session_key_node.firstChild.data
            config['session_key'] = data 
            
        server_uri_node = root.getElementsByTagName('server_uri')[0]
        if server_uri_node and server_uri_node.firstChild and server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
            data = server_uri_node.firstChild.data
            config['server_uri'] = data   
            
        conf_node = root.getElementsByTagName('configuration')[0]
        if conf_node:
            logging.debug('XML: found configuration')
            stanza = conf_node.getElementsByTagName('stanza')[0]
            if stanza:
                stanza_name = stanza.getAttribute('name')
                if stanza_name:
                    logging.debug('XML: found stanza ' + stanza_name)
                    config['name'] = stanza_name
                    config['input_name'] = re.match('csd://(.+)', stanza_name).group(1)

                    params = stanza.getElementsByTagName('param')
                    for param in params:
                        param_name = param.getAttribute('name')
                        logging.debug('XML: found param %s' % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug('XML: %s -> %s' % (param_name, data))

        checkpnt_node = root.getElementsByTagName('checkpoint_dir')[0]
        if checkpnt_node and checkpnt_node.firstChild and \
            checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
                config['checkpoint_dir'] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, 'Invalid configuration received from Splunk.'
        
    except Exception, e:
        raise Exception, 'Error getting Splunk configuration via STDIN: %s' % str(e)

    return config

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logging.debug('XML: found items')
    item_node = root.getElementsByTagName('item')[0]
    if item_node:
        logging.debug('XML: found item')

        name = item_node.getAttribute('name')
        val_data['stanza'] = name

        params_node = item_node.getElementsByTagName('param')
        for param in params_node:
            name = param.getAttribute('name')
            logging.debug('Found param %s' % name)
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data

# main 
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scheme':           
            do_scheme()
        elif sys.argv[1] == '--validate-arguments':
            do_validate()
        else:
            print_usage()
    else:
        # collected data set
        # HPA: temporary limit events to 10 to minimize duplications
        events = {'resource':'events', 'params':'limit=100', 'timefield':'timestamp', 'eventtype':'csd-event', 'query':'eventID' } 
        alerts = {'resource':'alerts', 'timefield':'firstTriggered', 'eventtype':'csd-alert', 'query':'alertID'} 
        sessions = {'resource':'sessions', 'timefield':'connectTime', 'eventtype':'csd-session', 'query':'sessionID'}    
        request_list = [events, alerts, sessions]

        do_run(request_list)        
        
    sys.exit(0)
