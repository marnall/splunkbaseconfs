
import os
import sys
import time
import json
import re
import requests
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
bin_dir = os.path.basename(__file__)

from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi
from falconpy import APIHarnessV2
from datetime import datetime, timedelta

# Base URL mapping for CrowdStrike cloud environments
CS_BASE_URLS = {
    'us_commercial': 'https://api.crowdstrike.com',
    'us_commercial2': 'https://api.us-2.crowdstrike.com',
    'eucloud': 'https://api.eu-1.crowdstrike.com',
    'govcloud': 'https://api.laggar.gcw.crowdstrike.com',
    'govcloud2': 'https://api.us-gov-2.crowdstrike.mil',
}


class ModInputcrowdstrike_event_streams(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputcrowdstrike_event_streams, self).__init__("ta_crowdstrike_falcon_event_streams", "crowdstrike_event_streams", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputcrowdstrike_event_streams, self).get_scheme()
        scheme.title = ("CrowdStrike Event Streams")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        scheme.add_argument(smi.Argument("cloud_environment", title="Select Cloud Environment",
                                         description="Select the appropriate cloud environment for the Falcon Instance",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("account", title="API Credential",
                                         description="This is an OAuth2 based API credential with Event Streams scope",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("app_id", title="Application ID",
                                         description="Application IDs must be a unique value per CrowdStrike instance",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("event_types", title="Event Types",
                                         description="Select specific event type(s) to collect using this input",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("initial_start", title="Initial Starting Point",
                                         description="Select an event collection starting point option (only used on the initial collection)",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-crowdstrike-falcon-event-streams"

    def validate_input(helper, definition):
        #Validate the Application ID
        application_name = definition.parameters.get('app_id')
    
        if len(application_name) > 30:
            raise ValueError('Application ID cannot exceed 30 characters.')
        elif ' ' in application_name:
            raise ValueError('Application ID cannot contain blank spaces')

        event_type_val = definition.parameters.get('event_types')
        event_type_list = list(event_type_val.split("~"))
        
        if 'All' in event_type_val:
            if len(event_type_list) > 1:
                raise ValueError('Event Types selection cannot contain both specific Event Types and "All"')


    def collect_events(helper, ew):
    
        ta_title = 'CrowdStrike Event Streams TA'
    
        #get and set log level
        loglevel = helper.get_log_level()
        helper.set_log_level(loglevel)
        
        #get the stanza name
        stanza_name = str(helper.get_input_stanza_names())
    
        #get TA version
        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "..", "app.manifest"))
        
        with open(filepath, 'r') as manifest:
            manifest_file = json.load(manifest)
            version = str(manifest_file['info']['id']['version'])
        user_agent = 'Splunk_TA_Event_Streams_v%s' % str(version)
    
        #construct log tags
        event_streams_title = f'{ta_title} {version} {stanza_name} :'
    
        #get index info
        index_info = helper.get_output_index()
    
        #get credentials
        global_account = helper.get_arg('account')
        clientid = global_account['username']
        secret= global_account['password']   
        
        #proxy server info
        proxy = helper.get_proxy()
    
        if proxy:
            proxy_details = 'Proxy Type: ' + str(proxy['proxy_type']) + ' Proxy URL: ' + str(proxy['proxy_url']) + ' Proxy Port: ' + str(proxy['proxy_port'])
            
            if proxy['proxy_username']:
                #proxy enabled with authentication - craft appropriate URL
                proxy_auth = 'Proxy is configured with authentication.'
                proxy_string = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_username']) + ':' + str(proxy['proxy_password']) +'@' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port']))
                redacted_proxy = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_username']) + ':***@' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port']))
                proxy_settings = {'http':proxy_string, 'https':proxy_string}
    
            else:
                #proxy enabled without authentication - craft appropriate URL
                proxy_auth = 'Proxy is configured without authentication'
                proxy_string = (str(proxy['proxy_type']) + '://' + str(proxy['proxy_url']) + ':' + str(proxy['proxy_port'])) 
                proxy_settings = {'http':proxy_string, 'https':proxy_string}
    
            proxy_config = True
            redacted_proxy_str = redacted_proxy if proxy['proxy_username'] else proxy_string
            proxy_info = 'Proxy set: ' + str(proxy_config) + '    ' + proxy_auth + '   ' + proxy_details + '   Proxy URL: ' + redacted_proxy_str
    
        else:
            proxy_config = False
            proxy_info = 'Proxy set: ' + str(proxy_config)
        
        #get the API endpoint selection
        api_endpoint = helper.get_arg('cloud_environment')
        
        #get the customer app_id 
        app_id = helper.get_arg('app_id')

        event_types = helper.get_arg('event_types')
        if len(event_types) == 0:
            event_types = ['All']
            helper.log_info(event_streams_title + ' This appears to be a converted input, setting event_types to ALL')
        
        initial_start = helper.get_arg('initial_start')
    
        #Log Configuration Information for support
        helper.log_info(event_streams_title + ' CONFIGURATION LOG LEVEL: ' + str(loglevel))
        helper.log_info(event_streams_title + ' CONFIGURATION  VERSION: ' + str(version))
        helper.log_info(event_streams_title + ' CONFIGURATION CS ENVIRONMENT: ' + str(api_endpoint))
        helper.log_info(event_streams_title + ' CONFIGURATION PROXY CONFIG: ' + str(proxy_info) )
        helper.log_info(event_streams_title + ' CONFIGURATION INPUT: ' + str(stanza_name))
        helper.log_info(event_streams_title + ' CONFIGURATION APP ID: ' + str(app_id))
        helper.log_info(event_streams_title + ' CONFIGURATION INDEX INFO: ' + str(index_info))
        helper.log_info(event_streams_title + ' CONFIGURATION EVENT TYPES: ' + str(event_types))
        helper.log_info(event_streams_title + ' CONFIGURATION Initial Start: ' + str(initial_start))
    
        def stream_event(data, timestamp, num_feeds, streaming_endpoint, api_endpoint, stanza):
            
            #initial test to determine multiple feeds
            if num_feeds > 1:
                multi_feed  = 'True'
            else:
                multi_feed = 'False'
    
            #get datafeed URL information
            regex = (r"datafeed/v\d(\W(\d))")
            multi_feed_data = re.search(regex, streaming_endpoint)
            matches = multi_feed_data.group(2)
    
            #preventive assignment incase of a single feed reconnection
            if int(matches) > 0:
                multi_feed = 'True'

            #create custom ta_data section for the events
            ta_data = {}
            ta_data ['ta_data'] = {}
            ta_data ['ta_data']['Feed_id'] = matches
            ta_data ['ta_data']['Multiple_feeds'] = multi_feed
            ta_data ['ta_data']['Cloud_environment'] = api_endpoint
            ta_data ['ta_data']['TA_version'] = version
            ta_data ['ta_data']['Input'] = stanza
            ta_data ['ta_data']['App_id'] = str(app_id)
            ta_data ['ta_data']['Event_types'] = str(event_types)
            ta_data ['ta_data']['Initial_start'] = initial_start
    
            data.update(ta_data)
    
            updated_data = json.dumps(data)
    
            event_timestamp = "%.3f" %timestamp
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=updated_data, time=event_timestamp)
            try:
                ew.write_event(event)
                return 'successful'
    
            except Exception as e:
                helper.log_error(event_streams_title + ' WRITE ERROR:    Failed to write event to Splunk: ' + str(type(e).__name__) + ': ' + str(e))
                return 'failed'
    
        #Connect to data stream URL with auth token, stream output to Splunk
        def stream_data(**kwargs):
            active_feeds = threading.active_count()
            helper.log_debug(event_streams_title + '  Number of active feeds: ' + str(active_feeds))
            offset_data_present = kwargs.get('offset_data_present')
            offset_val = int(kwargs.get('offset_val'))
            num_feeds = int(kwargs.get('num_feeds'))
            helper.log_debug(event_streams_title + ' Offset value: ' + str(offset_val))
            token_expire = kwargs.get('token_expire')
            input_name = kwargs.get('stanza_name')
            event_types = kwargs.get('event_types')
            initial_start = kwargs.get('initial_start')
            
    
            helper.log_debug(event_streams_title + ' Event Types: ' + str(event_types))
            helper.log_debug(event_streams_title + ' Initial Start: ' + str(initial_start))
    
            if offset_val > 0:
                offset_val = offset_val + 1
                url_formed = kwargs.get('url')+'&offset='+ str(offset_val)
            
            elif offset_val == 0:
                if initial_start == 'historic':
                    whence_val=0
                elif initial_start == 'current':
                    whence_val=2
                else:
                    helper.log_warning(event_streams_title + ' CONFIGURATION WARNING:    initial_start value "' + str(initial_start) + '" not recognized. Defaulting to historic (whence=0).')
                    whence_val=0
                url_formed = kwargs.get('url')+'&whence='+ str(whence_val)
    
            if 'All' not in event_types:
                event_type_list = event_types.split("~") if isinstance(event_types, str) else event_types
                helper.log_debug(event_streams_title + ' Event Filtering Configured: ' + str(event_type_list))
                events_string = ",".join(event_type_list)
                url_events = "&eventType="+ events_string
                helper.log_debug(event_streams_title + ' URL Filter: ' + str(url_events))
                url_formed = url_formed + url_events
    
            max_retries = 5
            retry_delay = 5
            headers = {'Authorization': 'Token %s' % kwargs.get('token'), 'Connection': 'Keep-Alive', 'X-INTEGRATION':'%s' % app_id, 'User-Agent': user_agent}

            for attempt in range(1, max_retries + 1):
                try:
                    if proxy:
                        helper.log_debug(event_streams_title + ' Attempting to connect input ' + str(input_name) + ' to Event Streams via proxy (attempt ' + str(attempt) + '/' + str(max_retries) + ').')
                        response = requests.get(url_formed, headers=headers, timeout=(30, 300), stream=True, proxies=proxy_settings)
                        response.raise_for_status()
                    else:
                        helper.log_debug(event_streams_title + ' Attempting to connect input ' + str(input_name) + ' to Event Streams without proxy (attempt ' + str(attempt) + '/' + str(max_retries) + ').')
                        response = requests.get(url_formed, headers=headers, timeout=(30, 300), stream=True)
                        response.raise_for_status()

                    response_code = response.status_code
                    helper.log_info(event_streams_title + ' CONNECTION RESULTS:    Streaming Data Module: Event Streams connection response code for input: ' + str(input_name) + ' : ' + str(response_code))
                    break

                except requests.exceptions.Timeout:
                    helper.log_error(event_streams_title + ' ERROR:     A timeout occurred or no heartbeat was detected for input: ' + str(input_name))
                    return

                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response is not None else 0
                    helper.log_error(event_streams_title + ' ERROR:     Streaming Data Module received HTTP ' + str(status) + ' for input: ' + str(input_name) + ' (attempt ' + str(attempt) + '/' + str(max_retries) + ')')
                    if 400 <= status < 500:
                        helper.log_error(event_streams_title + ' ERROR:     Client error (HTTP ' + str(status) + ') - session token may be invalid. Thread exiting for reconnect.')
                        return
                    if attempt < max_retries:
                        helper.log_info(event_streams_title + ' RETRY:     Retrying in ' + str(retry_delay) + ' seconds...')
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)
                    else:
                        helper.log_error(event_streams_title + ' ERROR:     All ' + str(max_retries) + ' connection attempts failed. Thread exiting.')
                        return

                except requests.exceptions.RequestException as e:
                    helper.log_error(event_streams_title + ' ERROR:     Streaming Data Module failed to connect to the API for input: ' + str(input_name) + ' (attempt ' + str(attempt) + '/' + str(max_retries) + ')')
                    helper.log_error(event_streams_title + ' ERROR:     ' + str(type(e).__name__) + ': ' + str(e))
                    if attempt < max_retries:
                        helper.log_info(event_streams_title + ' RETRY:     Retrying in ' + str(retry_delay) + ' seconds...')
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)
                    else:
                        helper.log_error(event_streams_title + ' ERROR:     All ' + str(max_retries) + ' connection attempts failed. Thread exiting.')
                        return
                
    
            try:
                for line in response.iter_lines():

                    helper.log_debug(event_streams_title + ' Looking or waiting for events to process for input: ' + str(input_name) + '. Current token will expire at: ' + str(token_expire))

                    #Check to see if the token needs to be refreshed
                    current_time = datetime.now()
                    if current_time > token_expire:
                        helper.log_debug(event_streams_title + ' TOKEN REFRESH:     Token refresh process has started for input: ' + str(input_name) + ' for feed number: ' + kwargs.get('feed_num_kv'))

                        #refresh the stream session using falcon bearer token
                        falcon = kwargs.get('falcon')
                        falcon.authenticate()
                        if not falcon.authenticated():
                            helper.log_error(event_streams_title + ' TOKEN REFRESH:    OAuth token re-authentication failed for input: ' + str(input_name) + ' for feed number: ' + kwargs.get('feed_num_kv') + '   Token status: ' + str(falcon.token_status))
                            return

                        refresh_url = kwargs.get('refresh_url')
                        refresh_headers = {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + falcon.token_value,
                            'User-Agent': user_agent
                        }

                        try:
                            refresh_response = requests.post(refresh_url, headers=refresh_headers, timeout=(30, 30), proxies=proxy_settings if proxy else None)
                            refresh_status = str(refresh_response.status_code)

                            if refresh_status.startswith('20'):
                                token_expire = datetime.now() + timedelta(minutes=20)
                                helper.log_info(event_streams_title + ' TOKEN REFRESH:     Stream session was successfully refreshed for input: ' + str(input_name) + ' for feed number: ' + kwargs.get('feed_num_kv') + '   The session now expires at: ' + str(token_expire))
                            else:
                                helper.log_warning(event_streams_title + ' TOKEN REFRESH:    Stream session refresh returned non-success status for input: ' + str(input_name) + ' for feed number: ' + kwargs.get('feed_num_kv') + '   Status code: ' + refresh_status + '   Continuing to consume stream.')
                                token_expire = datetime.now() + timedelta(minutes=5)

                        except Exception as e:
                            helper.log_warning(event_streams_title + ' TOKEN REFRESH:    Exception during stream session refresh for input: ' + str(input_name) + ' for feed number: ' + kwargs.get('feed_num_kv') + '   Error: ' + str(e) + '   Continuing to consume stream.')
                            token_expire = datetime.now() + timedelta(minutes=5)


                    if line:
                        decoded_line = line.decode('utf-8')
                        try:
                            line_json = json.loads(decoded_line)
                            offset_num = line_json['metadata']['offset']
                        except (json.JSONDecodeError, KeyError, TypeError) as e:
                            helper.log_warning(event_streams_title + ' PARSE WARNING:    Skipping malformed stream line for input: ' + str(input_name) + ' Error: ' + str(type(e).__name__) + ': ' + str(e))
                            continue

                        # Skip metadata-only events (null event field)
                        if line_json.get('event') is None:
                            helper.log_debug(event_streams_title + ' Skipping metadata-only event at offset: ' + str(offset_num) + ' for input: ' + str(input_name))
                            try:
                                checkpoint_key = kwargs.get('url')
                                checkpoint = {checkpoint_key: offset_num}
                                kv_record = kwargs.get('kv_entry')
                                helper.save_check_point(kv_record, checkpoint)
                            except Exception as e:
                                helper.log_error(event_streams_title + ' OFFSET KV STORE:    Offset failed to record to KV Store: ' + str(stanza_name) + ' Error: ' + str(type(e).__name__) + ': ' + str(e))
                            continue

                        try:
                            metadata = line_json['metadata']
                            event_creation_time = metadata.get('eventCreationTime')
                            if event_creation_time is None:
                                helper.log_warning(event_streams_title + ' PARSE WARNING:    Event missing eventCreationTime for input: ' + str(input_name) + ' offset: ' + str(offset_num) + ' - using current time')
                                timestamp = time.time()
                            else:
                                timestamp = (event_creation_time / 1000)
                            write_event = stream_event(line_json, timestamp, num_feeds, kwargs.get('url'), kwargs.get('api_endpoint'), input_name)

                            if write_event == 'successful':
                                helper.log_debug(event_streams_title + ' SPLUNK EVENT:    Event number ' + str(kwargs.get('url')) + ' ' + str(offset_num) +' was successfully sent to Splunk for indexing to: ' + str(index_info))

                                try:
                                    helper.log_debug(event_streams_title + ' Saving Offset to KV Store ' + str(offset_num))
                                    checkpoint_key = kwargs.get('url')
                                    offset_num = line_json ['metadata']['offset']
                                    checkpoint={checkpoint_key:offset_num}
                                    kv_record = kwargs.get('kv_entry')
                                    helper.save_check_point(kv_record, checkpoint)
                                    helper.log_debug(event_streams_title + ' OFFSET KV STORE:     Offset recorded to KV Store: ' +  str(kv_record) + ' ' + str(checkpoint))

                                except Exception as e:
                                    helper.log_error(event_streams_title + ' OFFSET KV STORE:    Offset failed to record to KV Store: ' + str(stanza_name) + ' to KV store. Error: ' + str(type(e).__name__) + ': ' + str(e))

                            else:
                                helper.log_warning(event_streams_title + ' SPLUNK EVENT:    Event number ' + str(kwargs.get('url')) + ' ' + str(offset_num) +' was not successfully sent to Splunk for indexing to: ' + str(index_info) + ' - checkpoint NOT advanced')

                        except Exception as e:
                            helper.log_error(event_streams_title + '  EVENT ERROR:    Error processing event at offset ' + str(offset_num) + ' for input: ' + str(input_name) + ' Error: ' + str(type(e).__name__) + ': ' + str(e))
                            continue

                else:
                    helper.log_info(event_streams_title + ' STREAM CLOSED:    Stream connection closed by server for input: ' + str(input_name) + ' for feed number: ' + kwargs.get('feed_num_kv') + ' - Thread exiting for reconnect.')
                    return

            except requests.exceptions.ReadTimeout:
                helper.log_error(event_streams_title + ' TIMEOUT:    No data or heartbeat received for 5 minutes for input: ' + str(input_name) + ' feed: ' + kwargs.get('feed_num_kv') + ' - Thread exiting for reconnect.')
                return
            except requests.exceptions.ChunkedEncodingError as e:
                helper.log_error(event_streams_title + ' CONNECTION LOST:    Stream connection broken for input: ' + str(input_name) + ' feed: ' + kwargs.get('feed_num_kv') + ' Error: ' + str(e))
                return
                        
        #Connect to discover stream URL, get auth token, connect to data stream URL
        def crowdstrike_client():
            threads = []    
            streams = {}

            #Authenticate via FalconPy Uber Class
            base_url = CS_BASE_URLS.get(api_endpoint)
            if not base_url:
                helper.log_error(event_streams_title + ' ERROR: Unknown cloud environment: ' + str(api_endpoint) + '. Valid options: ' + str(list(CS_BASE_URLS.keys())))
                raise SystemExit()

            falcon = APIHarnessV2(
                client_id=clientid,
                client_secret=secret,
                base_url=base_url,
                proxy=proxy_settings if proxy else None,
                user_agent=user_agent,
                timeout=(30, 600)
            )
            falcon.authenticate()

            if falcon.authenticated():
                helper.log_info(event_streams_title + ' TOKEN REQUEST:     OAuth2 Token was successfully retrieved for input: ' + str(stanza_name))
            else:
                helper.log_error(event_streams_title + ' TOKEN REQUEST ERROR:     Failed to retrieve OAuth2 API token for input:    ' + str(stanza_name))
                helper.log_error(event_streams_title + f' Error returned:      token_status={falcon.token_status}')
                raise SystemExit()

            #Discover available streams via Uber Class
            streams_response = falcon.command("listAvailableStreamsOAuth2", appId=app_id)
            streams_status = streams_response.get('status_code', 0)

            if str(streams_status).startswith('20'):
                helper.log_info(event_streams_title + ' CONNECTION: Successfully connected to the Event Streams API.')
                response = streams_response.get('body', {})
            else:
                errors = streams_response.get('body', {}).get('errors', [])
                error_msg = errors[0].get('message', 'Unknown error') if errors else 'No error details'
                error_code = errors[0].get('code', 0) if errors else 0
                trace_id = streams_response.get('headers', {}).get('X-Cs-Traceid', 'Not provided')
                helper.log_error(event_streams_title + ' CONNECTION ERROR:    Failed to connect to the Event Streams API.    Status: ' + str(streams_status) + '    Code: ' + str(error_code) + '    Message: ' + str(error_msg) + '    TraceID: ' + str(trace_id))
                if streams_status in (401, 403):
                    helper.log_error(event_streams_title + ' CONNECTION ERROR:    Permission or scope error - verify API client has Event Streams read scope.')
                    raise SystemExit()
                return
    
            #determine the number of feeds present in the Streaming API and check of App ID collision
            if response['resources'] is not None:
                num_feeds = len(response['resources'])
            elif response['resources'] is None:
                helper.log_error(event_streams_title + ' ERROR: The Event Streams API responded correctly but there were no DataFeed URLs identified for collection. Ensure that the Application ID is unique for this Falcon instance.')
                raise SystemExit()
            count = num_feeds
            while count > 0: helper.log_debug(event_streams_title + ' CONNECTION DATA: DataFeed URL identified: ' + str(response['resources'][count-1]['dataFeedURL'])); count = count - 1
    
    
            #if there's no feeds there's no reason to process
            if num_feeds == 0:
                helper.log_error(event_streams_title + " ERROR: No feeds were found in the response from the Event Streams API - Exiting.")
                raise SystemExit()
    
            #if there are feeds detected
            #generate a timestamp 20 minutes from now
            #pull the data URL and the resources response data for processing
            elif num_feeds == 1:
                helper.log_info(event_streams_title + ' CS EVENT STREAMS FEEDS:    Identified: 1 stream for data collection.')
                generated_time = datetime.now()
                #configures the token to expire in 20 minutes
                expire_time = generated_time + timedelta(minutes=20)
                data_url = response['resources'][0]['dataFeedURL']
                url_check = str(data_url)
                if url_check.startswith('https'):
                        helper.log_debug(event_streams_title + ' Splunk https URL check satisfied')
                else:
                        helper.log_debug(event_streams_title + ' Splunk https URL check not satisfied - exiting TA')
                        raise SystemExit()
                streaming_data = response['resources'][0]
                streaming_data.update( {'expire': expire_time} )
                streams[data_url]=streaming_data
                
            elif num_feeds > 1:
                feed = 0
                helper.log_info(event_streams_title + 'FEEDS:     Identified: ' + str(num_feeds) + ' streams for data collection.')
                while num_feeds > feed:
                    generated_time = datetime.now()
                    #configures the token to expire in 20 minutes
                    expire_time = generated_time + timedelta(minutes=20)
                    data_url = response['resources'][feed]['dataFeedURL']
                    url_check = str(data_url)
                    if url_check.startswith('https'):
                        helper.log_debug(event_streams_title + ' Splunk https URL check satisfied')
                    else:
                        helper.log_debug(event_streams_title + ' Splunk https URL check not satisfied - exiting TA')
                        raise SystemExit()
                    streaming_data = response['resources'][feed]
                    streaming_data.update( {'expire': expire_time} )
                    streams[data_url]=streaming_data
                    feed += 1
    
            #process the streaming data and create child threads for each stream
            try:
                for key, val in list(streams.items()):
                    url = key
                    #pulling out the feed num from the URL to retrieve KV store entry
                    regex = (r"datafeed/v\d(\W(\d+))")
                    feed_num_raw = re.search(regex, url)
                    feed_num_kv = feed_num_raw.group(2)
                    kv_entry = stanza_name + '_feed_num_' + str(feed_num_kv)
    
                    #Check for offset value in KVStore
                    try:
                        offset_kv_store = helper.get_check_point(kv_entry)

                        if offset_kv_store and len(offset_kv_store) > 0:
                            kv_offset = offset_kv_store[url]
                            kv_offset_entry = ' KV Store offset entry found: '  + str(offset_kv_store)
                            offset_data_present = True

                        else:
                            kv_offset_entry = ' No specific KV Store offset entry found for: '  + str(kv_entry)
                            kv_offset = 0
                            offset_data_present = False

                    except Exception as e:
                        kv_offset_entry = 'No Splunk KV Store offset entry found for: '  + str(kv_entry)
                        helper.log_error(event_streams_title + ' CHECKPOINT READ ERROR:    Failed to read checkpoint for: ' + str(kv_entry) + '   Error: ' + str(type(e).__name__) + ': ' + str(e))
                        kv_offset = 0
                        offset_data_present = False
    
                    helper.log_info(event_streams_title + ' KV INFO:    ' + kv_offset_entry + '   Initial KV Value is: ' + str(kv_offset))
                    
                    offset_val = kv_offset
                    
                    token = val['sessionToken']['token'] 
                    refresh_url = val['refreshActiveSessionURL'] 
                    token_expire = val['expire']
                    thread_args={'url':url, 'token':token, 'refresh_url':refresh_url, 'app_id':app_id, 'offset_val':offset_val, 'offset_data_present':offset_data_present, 'token_expire':token_expire, 'falcon':falcon, 'api_endpoint':api_endpoint, 'proxy':proxy, 'num_feeds':num_feeds, 'stanza_name':stanza_name, 'feed_num_kv':feed_num_kv, 'kv_entry':kv_entry, 'event_types':event_types, 'initial_start':initial_start}
                    helper.log_debug(event_streams_title + ' Starting threads')
                    threads.append(threading.Thread(target=stream_data, kwargs=thread_args))
                    threads[-1].start()
                    time.sleep(5)
        
                while any(t.is_alive() for t in threads):
                    for t in threads:
                        t.join(timeout=60)
                    active_feeds = sum(1 for t in threads if t.is_alive())
                    if active_feeds < num_feeds and active_feeds > 0:
                        helper.log_error(event_streams_title + ' THREADING ERROR:    A thread appears to have failed. Active: ' + str(active_feeds) + '/' + str(num_feeds) + '. Restarting input.')
                        return
    
            except ValueError:
                helper.log_error (event_streams_title + " Unable to process the streaming data and create child threads for each stream.")
                helper.log_error (event_streams_title + " The TA is now shutting down.")
                raise SystemExit()
                
    
        reconnect_delay = 5
        while True:
            try:
                client_start = time.time()
                crowdstrike_client()
                # If crowdstrike_client returns normally, a reconnection is needed
                client_duration = time.time() - client_start
                if client_duration > 120:
                    reconnect_delay = 5
                helper.log_info(event_streams_title + ' RECONNECT:    Restarting client in ' + str(reconnect_delay) + ' seconds... (ran for ' + str(int(client_duration)) + 's)')
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 120)
            except SystemExit:
                helper.log_error(event_streams_title + ' SHUTDOWN:    Fatal error encountered. Input stopping.')
                break

    def get_account_fields(self):
        account_fields = []
        account_fields.append("account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

if __name__ == "__main__":
    exitcode = ModInputcrowdstrike_event_streams().run(sys.argv)
    sys.exit(exitcode)
