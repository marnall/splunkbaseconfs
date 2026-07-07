import sys
import os
import time
import datetime
import time
import json
import platform
import socket
import requests
from io import open
from contextlib import contextmanager
from socket import error as ConnectionRefusedError # Covers case where exception is not defined in python2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from splunklib.client import *
from splunklib.six.moves.urllib.parse import urlsplit
from splunklib.binding import *

from six.moves.urllib.parse import urlencode

import dragoslib.logger
import dragoslib.indicator_api
import dragoslib.utils
import dragoslib.dragos_api_credential_manager
import dragoslib.ioc_cache_tracker
import dragoslib.splunk_collections
import dragoslib.ioc_inactive_list
import dragoslib.app_config

# disable ssl warnings about not verifying cert
try:
    requests.packages.urllib3.disable_warnings() 
except:
    pass


class DragosIOCs(Script):

    LOOP_SLEEP_TIME = 15

    IOC_DEST_KV_STORE = 'ioc-dest-kvstore'
    IOC_DEST_SPLUNK_ES = 'ios-dest-splunkes'

    def __init__(self):
        super(DragosIOCs, self).__init__()
        self._service_with_app = None
        self._num_ingested = 0
        self._logger = dragoslib.logger.create_logger("mod_input")

    def get_scheme(self):
        self._logger.info("Entering get_scheme method")

        scheme = Scheme("Dragos IOCs")
        scheme.description = "This input pulls Indicators of Compromise (IOCs) from the Dragos WorldView portal."
        scheme.use_external_validation = True
        scheme.use_single_instance = True
        scheme.streaming_mode = Scheme.streaming_mode_xml
        
        access_token_argument = Argument(
            name="api_access_token",
            title="API Access Token",
            description="API Access Token (from Dragos WorldView User Profile page).",
            data_type=Argument.data_type_string,
            required_on_edit=True,
            required_on_create=True
        )
        scheme.add_argument(access_token_argument)
        
        secret_key_argument = Argument(
            name="api_secret_key",
            title="API Secret Key",
            description="API Secret Key (from Dragos WorldView User Profile page).",
            data_type=Argument.data_type_string,
            required_on_edit=True,
            required_on_create=True
        )
        scheme.add_argument(secret_key_argument)
        
        poll_interval_argument = Argument(
            name="poll_interval",
            title="Poll Interval (in days)",
            description="How often should we pull IOCs from the Dragos WorldView API?. The shortest poll interval we allow is a single day and this field just be a whole integer >=1.",
            data_type=Argument.data_type_number,
            required_on_edit=True,
            required_on_create=True
        )
        scheme.add_argument(poll_interval_argument)
        
        full_replace_argument = Argument(
            name="full_replace_interval",
            title="IOC Full Replacement Interval (in days)",
            description="In order to keep the list of IOCs update to date, this input will periodically do a full replacement of all IOCs. The smallest value we allow is 7 days and this field must be a whole integer. This value must also be greater than the poll interval.",
            data_type=Argument.data_type_number,
            required_on_edit=True,
            required_on_create=True
        )
        scheme.add_argument(full_replace_argument)

        ioc_destination_config = Argument(
            name="ioc_destination_config",
            title="IOC Destination Configuraiton",
            description="Will the IOCs be stored locally,  sent to a remote search head cluster, or sent to Splunk Enterprise Security?",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(ioc_destination_config)
        
        remote_search_head_location = Argument(
            name="remote_search_head_location",
            title="Remote Search Head Location",
            description="The URL of the Rest API located on the remote search head. Typically this is listening on port 8089.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(remote_search_head_location)

        remote_search_head_api_username = Argument(
            name="remote_search_head_api_username",
            title="Username",
            description="Username that can be used to access the Rest API.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(remote_search_head_api_username)

        remote_search_head_api_password = Argument(
            name="remote_search_head_api_password",
            title="Password",
            description="Password that can be used to access the Rest API.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(remote_search_head_api_password)

        splunkes_location = Argument(
            name="splunkes_location",
            title="Remote Search Head Location",
            description="The URL of the Rest API located on the Splunk Enterprise Security instance. Typically this is listening on port 8089.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(splunkes_location)

        splunkes_api_username = Argument(
            name="splunkes_api_username",
            title="Username",
            description="Username that can be used to access the Rest API.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(splunkes_api_username)

        splunkes_api_password = Argument(
            name="splunkes_api_password",
            title="Password",
            description="Password that can be used to access the Rest API.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(splunkes_api_password)

        splunkes_intel_feed_name = Argument(
            name="splunkes_intel_feed_name",
            title="Itel Feed Name",
            description="The name of the threat intel feed that has been configured to store Dragos IOCs.",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False
        )
        scheme.add_argument(splunkes_intel_feed_name)
        
        output_iocs_to_index = Argument(
            name="output_to_index",
            title="Output IOCs to an Index",
            description="By default all IOCs are placed in a KV store which is then used to to enrich events. If you would like you can also configure the input to output IOCs to the index specified in this input. By default we reccomend you don't use this feature. If you want to enable it write the string 'true' (without quotes) in this field",
            data_type=Argument.data_type_string,
            required_on_edit=False,
            required_on_create=False  
        )
        scheme.add_argument(output_iocs_to_index)
        
        return scheme

    def log_input_parameters(self, params):
        params_to_print = {}
        for key in params:
            params_to_print[key] = params[key]

            if key in ['api_access_token', 'api_secret_key', 'remote_search_head_api_username', 'remote_search_head_api_password']:
                if key != None:
                    params_to_print[key] = dragoslib.dragos_api_credential_manager.DragosCredentialManager.MASKED_CREDENTIAL

        self._logger.info("Input Parameters: " + json.dumps(params_to_print))

    def verify_input_parameters(self, actual_params, assign_defaults=False):
        assigned_default = False

        expected_params = {
            'api_access_token':                'default-access-token',
            'api_secret_key':                  'default-secret-key',
            'poll_interval':                   1,
            'full_replace_interval':           7,
            'ioc_destination_config':          'localSearchHead',
        }

        for expected in expected_params:
            if not expected in actual_params:
                if assign_defaults:
                    self._logger.warn("Input parameter %s not present, initializing with default value" % expected)
                    actual_params[expected] = expected_params[expected]
                    assigned_default = True
                else:
                    raise RuntimeError('Input parameter %s not present' % expected)
        
        if assign_defaults:
            if not 'output_to_index' in actual_params:
                actual_params['output_to_index'] = False

        if assigned_default:
            self.log_input_parameters(actual_params)
    
    def validate_input(self, validation_definition):
        self._logger.info("Validating Input")
        #
        # Note that we have to be quick in this function. splunk will timeout
        # the validation request if we don't return withinin 30 seconds
        #

        try:

            # Validate that there is only one active instance of this modular input
            #
            # We do this by forcing the name of the input to be 'dragos_iocs'. We then
            # throw an error if the name doesn't match this. Since splunk requires input
            # names to be unique this accomplishes our goal of having only once instance
            input_name = validation_definition.metadata['name']
            self._logger.info("Input name = %s" % input_name)
            if input_name != 'dragos_iocs':
                raise ValueError("You must name this input 'dragos_iocs'. The name '%s' is not allowed." % input_name)
            
            self.log_input_parameters(validation_definition.parameters)
            self.verify_input_parameters(validation_definition.parameters)
            
            # Validate that the API credentials they have provided allow them to access
            # the Dragos WorldView API
            # unless the credentials are masked
            api_access_token = validation_definition.parameters['api_access_token']
            api_secret_key   = validation_definition.parameters['api_secret_key']
            masked           = dragoslib.dragos_api_credential_manager.DragosAPICredentialManager.MASKED_CREDENTIAL
            if api_access_token == masked and api_secret_key == masked:
                self._logger.info("API creds haven't changed. Skipping validation")
            elif ((api_access_token == masked and api_secret_key != masked) or 
                (api_access_token != masked and api_secret_key == masked)):
                raise ValueError("If you are updating the Dragos WorldView API credentials please update both the API access token and secret key at the same time.")
            else:
                self._logger.info("API creds have been updated, validating")
                service_with_app = dragoslib.utils.create_app_specific_service(
                    splunk_url=validation_definition.metadata["server_uri"], 
                    session_key=validation_definition.metadata["session_key"],
                    owner='nobody')
                dragos_api = dragoslib.indicator_api.IndicatorApi(
                    validation_definition.parameters['api_access_token'],
                    validation_definition.parameters['api_secret_key'],
                    service_with_app)
                
                are_creds_valid, msg = dragos_api.verify_api_connectivity()
                
                if not are_creds_valid:
                    raise ValueError(msg)
                else:
                    self._logger.info("Dragos API credentials are valid")
            
            # Validate the interval that we check for new IOCs
            poll_interval = validation_definition.parameters['poll_interval']
            self._logger.info("Poll Interval = %s" % poll_interval)
            if poll_interval[0:6] == '-99900':
                pass
            else:
                if not poll_interval.isdigit():
                    raise ValueError("Invalid poll interval. Value must be a positive integer >= 1")
                if int(poll_interval) < 1:
                    raise ValueError("Invalid poll interval. Must be >= 1")
            
            # Validate the interval that we perform a full IOC replacement
            full_replace_interval = validation_definition.parameters['full_replace_interval']
            self._logger.info("Full Replace Interval = %s" % full_replace_interval)
            if full_replace_interval[0:6] == '-99900':
                pass
            else:
                if not full_replace_interval.isdigit():
                    raise ValueError("Invalid full replacement interval %s. Value must be a positive integer >= 1" % str(full_replace_interval))
                if int(full_replace_interval) < 1:
                    raise ValueError("Invalid full replacement interval %s. Must be >= 1" % str(full_replace_interval))
                if int(full_replace_interval) <= int(poll_interval):
                    raise ValueError("invalid full replacement interval (%s), must be greater than poll interval (%s)" % (str(full_replace_interval), str(poll_interval)))

            ioc_destination_config = validation_definition.parameters['ioc_destination_config']
            self._logger.info("Search Head Configuration = %s" % ioc_destination_config)
            if ioc_destination_config == 'localSearchHead':
                # Nothing to validate
                pass
            elif ioc_destination_config == 'remoteSearchHead':
                location = validation_definition.parameters['remote_search_head_location']
                username = validation_definition.parameters['remote_search_head_api_username']
                password = validation_definition.parameters['remote_search_head_api_password']

                self.verify_api_connectivity('remote search head API', location, username, password)
            elif ioc_destination_config == 'splunkES':
                location = validation_definition.parameters['splunkes_location']
                username = validation_definition.parameters['splunkes_api_username']
                password = validation_definition.parameters['splunkes_api_password']
                
                self.verify_api_connectivity('splunk enterprise security API', location, username, password)

                if not 'splunkes_intel_feed_name' in validation_definition.parameters:
                    raise ValueError("Name of intel feed used to store Dragos IOCs not found.")
                elif validation_definition.parameters['splunkes_intel_feed_name'] == '':
                    raise ValueError("Name of intel feed used to store Dragos IOCs is empty.")
            else:
                raise ValueError("Invalid IOC destination config '%s'. Must be 'localSearchHead', 'remoteSearchHead', or 'splunkES'" % ioc_destination_config)
            
            if 'sourcetype' in validation_definition.parameters:
                if validation_definition.parameters['sourcetype'] != None:
                    raise ValueError("sourcetype was set to '%s' but it must be set to 'Automatic'" % validation_definition.parameters['sourcetype'])
            
            if 'output_to_index' in validation_definition.parameters:
                output_to_index = validation_definition.parameters['output_to_index']
                self._logger.info("Output To Index = %s" % output_to_index)
                if output_to_index:
                    if output_to_index.lower() == 'true':
                        pass
                    elif output_to_index.lower() == 'false':
                        pass
                    elif output_to_index.lower() == '0':
                        pass
                    elif output_to_index.lower() == '1':
                        pass
                    elif output_to_index.lower() == 'none':
                        pass
                    else:
                        raise ValueError("Invalid value for the output_to_index field. The value specified was '%s' but it must either be 'true'/'false' (without quotes) or left empty" % output_to_index)
            
            self._logger.info("Input definition valid")
        except Exception as e:
            self._logger.error("Input definition not valid or error validating")
            self._logger.exception(e)
            raise

    def stream_events(self, inputs, ew):
        self._logger.info("Entering stream_events method. Splunk Version %s, Python version %s, PID %d" % ('.'.join(str(i) for i in self.service.splunk_version), platform.python_version(), os.getpid()))

        # Set the local service to auto logon to be more fault tolerant
        self.service.autologin = True

        #
        # Initialize things and make sure the credentials are placed in secure storage
        #
        try:
            # load internal app config values
            internal_app_config = dragoslib.app_config.AppConfig()

            # Sometimes the modular input can get started before the kv store is ready
            # wait for the kv store
            self._wait_for_kv_store(self.service)

            local_service_with_app = dragoslib.utils.create_app_specific_service(service=self.service, owner='nobody')
            api_creds_manager = dragoslib.dragos_api_credential_manager.DragosAPICredentialManager(local_service_with_app)
            search_head_creds_manager = dragoslib.dragos_api_credential_manager.DragosSearchHeadCredentialManager(local_service_with_app)
            splunkes_creds_manager = dragoslib.dragos_api_credential_manager.DragosSplunkESCredentialManager(local_service_with_app)
            local_ioc_cache_tracker = dragoslib.ioc_cache_tracker.IOCCacheTracker(local_service_with_app)

            ioc_cache_trackers = [local_ioc_cache_tracker]
            primary_ioc_cache_tracker = local_ioc_cache_tracker

            search_head_service_with_app = local_service_with_app

            remote_service_with_app = None
            ioc_dest_context = None

            # by default send IOCs to the kv store
            ioc_destination_config = self.IOC_DEST_KV_STORE

            if dragoslib.utils.INPUT_NAME in inputs.inputs:
                ioc_input = inputs.inputs[dragoslib.utils.INPUT_NAME]

                # If the user has upgraded the app there may be an outdated input and fields may be missing
                # Therefore quickly verify the input parameters and assign defaults so that the app doesn't
                # die after an upgrade 
                self.verify_input_parameters(ioc_input, assign_defaults=True)
                
                if 'ioc_destination_config' in ioc_input and ioc_input['ioc_destination_config'] == 'remoteSearchHead':
                    splunkd = urlsplit(ioc_input['remote_search_head_location'], allow_fragments=False)

                    remote_service_with_app =  Service(
                        handler=dragoslib.utils.splunk_request_handler,
                        scheme=splunkd.scheme,
                        host=splunkd.hostname,
                        port=splunkd.port,
                        username=search_head_creds_manager.username,
                        password=search_head_creds_manager.password,
                        app=dragoslib.utils.APP_NAME,
                        owner='nobody',
                        autologin=True
                    )

                    self._wait_for_kv_store(remote_service_with_app)

                    remote_ioc_cache_tracker = dragoslib.ioc_cache_tracker.IOCCacheTracker(remote_service_with_app)
                    ioc_cache_trackers.append(remote_ioc_cache_tracker)
                    primary_ioc_cache_tracker = remote_ioc_cache_tracker
                    search_head_service_with_app = remote_service_with_app

                elif 'ioc_destination_config' in ioc_input and ioc_input['ioc_destination_config'] == 'splunkES':
                    splunkd = urlsplit(ioc_input['splunkes_location'], allow_fragments=False)

                    splunk_es_service =  Service(
                        handler=dragoslib.utils.splunk_request_handler,
                        scheme=splunkd.scheme,
                        host=splunkd.hostname,
                        port=splunkd.port,
                        username=splunkes_creds_manager.username,
                        password=splunkes_creds_manager.password,
                        autologin=True
                    )

                    ioc_dest_context = [splunk_es_service, ioc_input['splunkes_intel_feed_name']]

                    ioc_destination_config = self.IOC_DEST_SPLUNK_ES
                

            ioc_inactive_list = dragoslib.ioc_inactive_list.IOCInactiveList(search_head_service_with_app, self._logger)

            if ioc_destination_config != self.IOC_DEST_SPLUNK_ES:
                # this should be created via the default collections.conf but create it here just to be safe
                if dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE not in search_head_service_with_app.kvstore:
                    search_head_service_with_app.kvstore.create(dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE)
                ioc_dest_context = search_head_service_with_app.kvstore[dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE]

        except Exception as e:
            self._logger.error("Error initializing modular input run")
            self._logger.exception(e)
            return
        
        #
        # Do we have any initial IOCs that should be loaded?
        #
        try:
            initial_iocs_file_name = os.path.join(os.path.dirname(__file__), "..", "bin", 'initial_iocs.json')
            if os.path.isfile(initial_iocs_file_name):

                self._logger.info("Initial demo IOC file detected.")
                if ((dragoslib.splunk_collections.COLLECTION_NAME_INITIAL_IOCS_LOADED not in search_head_service_with_app.kvstore) or (ioc_destination_config == self.IOC_DEST_SPLUNK_ES)): 
                    with open(initial_iocs_file_name) as initial_iocs_json_file:
                        timestamp = datetime.datetime.now().isoformat()[0:-3] + 'Z'
                        raw_json = initial_iocs_json_file.read()
                        raw_json = raw_json.replace("REPLACE_WITH_TIMESTAMP", timestamp)
                        initial_iocs = json.loads(raw_json)["indicators"]
                        ingest_timestamp = datetime.datetime.now()
                        
                        self.process_list_of_iocs(initial_iocs, ioc_destination_config, ioc_dest_context, ingest_timestamp, ioc_inactive_list, False, None, None, ew, internal_app_config)

                        # clean up any IOCs that may have accidentally been added
                        # due to a race condition with the inactive managemet page
                        ioc_inactive_list.remove_all_inactive_from_ioc_list()
                        
                        # update the cache trackers and then ensure they are reset so that main ioc
                        # ingest doesn't get messed up
                        for tracker in ioc_cache_trackers:
                            tracker.record_new_ioc_pull(ingest_timestamp, len(initial_iocs))
                            tracker.update_cache_for_full_replacement()
                            
                        if ioc_destination_config != self.IOC_DEST_SPLUNK_ES:
                            search_head_service_with_app.kvstore.create(dragoslib.splunk_collections.COLLECTION_NAME_INITIAL_IOCS_LOADED)
                        
        except Exception as e:
            self._logger.error("Error loading initial IOCs")
            self._logger.exception(e)
            return
        

        # If there aren't any inputs configured, then bail (assuming we aren't in demo mode)
        if dragoslib.utils.INPUT_NAME not in inputs.inputs:
            self._logger.info("No inputs configured. Leaving")
            return
        
        #
        # Initialize things so we can then poll for new IOCs
        #
        try:
            input_parameters = inputs.inputs[dragoslib.utils.INPUT_NAME]
            dragos_api = dragoslib.indicator_api.IndicatorApi(api_creds_manager.username, api_creds_manager.password, local_service_with_app, suppress_url_log=True)

            poll_interval = int(input_parameters['poll_interval'])
            # need to convert from days to seconds
            if poll_interval >= 1:
                poll_interval = poll_interval * 86400 # seconds in a day
            elif poll_interval <= -99900:
                # for debug use. value will be specified in seconds once we remove the prefix
                poll_interval = int(str(poll_interval)[6:])
            else:
                # something weird has happened default to 1 day
                poll_interval = 86400
            
            full_replace_interval = int(input_parameters['full_replace_interval'])
            # need to convert from days to seconds
            if full_replace_interval >= 1:
                full_replace_interval = full_replace_interval * 86400 # seconds in a day
            elif full_replace_interval <= -99900:
                # for debug use. value will be specified in seconds once we remove the prefix
                full_replace_interval = int(str(full_replace_interval)[6:])
            else:
                # something weird has happened default to 7 days
                full_replace_interval = 86400 * 7
            
            output_to_index = ""
            if 'output_to_index' in input_parameters:
                output_to_index = input_parameters['output_to_index'] if input_parameters['output_to_index'] else ""
            output_to_index = True if (output_to_index.lower() == 'true' or output_to_index.lower() == '1') else False

            index = None
            if 'index' in input_parameters:
                index = input_parameters['index']

            host = None
            if 'host' in input_parameters:
                host = input_parameters['host']
                if host.lower() == '$decideonstartup':
                    host = None
                
            
        except Exception as e:
            self._logger.error("Error initializing modular input run")
            self._logger.exception(e)
            try:
                for tracker in ioc_cache_trackers:
                    tracker.record_new_ioc_pull(datetime.datetime.now(), 0, "Error initializing modular input runtime. Check dragos_ta_threat_intel_mod_input.log for more details.")
            except Exception:
                # eat the exception
                pass
            return

        #
        # Poll for new IOCs
        #
        try:
            for tracker in ioc_cache_trackers:
                tracker.update_last_mod_input_run_time()
                
            if primary_ioc_cache_tracker.should_pull_new_iocs(poll_interval):

                self._logger.info("Hit poll for new IOCs from Dragos API, interval=%d" % (poll_interval))
                
                # should we perform a full replace?
                if primary_ioc_cache_tracker.should_perform_full_ioc_replacement(full_replace_interval):
                    for tracker in ioc_cache_trackers:
                        tracker.update_cache_for_full_replacement()
                    # only able to perform full replacement when using kv store as a destination
                    if ioc_destination_config == self.IOC_DEST_KV_STORE:
                        search_head_service_with_app.kvstore[dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE].data.delete()
                
                ingest_timestamp = datetime.datetime.now()
                self._num_ingested = 0

                def process_iocs_helper(ioc_list):
                    self.process_list_of_iocs(ioc_list, ioc_destination_config, ioc_dest_context, ingest_timestamp, ioc_inactive_list, output_to_index, index, host, ew, internal_app_config)
                
                dragos_api.get_iocs(primary_ioc_cache_tracker.last_ioc_pull, process_iocs_helper)

                # only able to perform advanced inactive management when using the kv store as a destination
                if ioc_destination_config == self.IOC_DEST_KV_STORE:
                    # clean up any IOCs that may have accidentally been added
                    # due to a race condition with the inactive managemet page
                    ioc_inactive_list.remove_all_inactive_from_ioc_list()

                for tracker in ioc_cache_trackers:
                    tracker.record_new_ioc_pull(ingest_timestamp, self._num_ingested)
        except Exception as e:
            self._logger.error("Catching error on API poll loop")
            self._logger.exception(e)
            try:
                for tracker in ioc_cache_trackers:
                    tracker.record_new_ioc_pull(datetime.datetime.now(), 0, "Error while updating list of IOCs:" + str(e) + ". Check dragos_ta_threat_intel_mod_input.log for more details.")
            except Exception:
                # eat the exception if we cant record the failed IOC pull
                pass
    
    def process_list_of_iocs_dest_kv_store(self, list_of_iocs, ioc_kvstore, ingest_timestamp, ioc_inactive_list, internal_app_config):
        if len(list_of_iocs) > 0:
            for ioc in list_of_iocs:
                ioc["_key"] = ioc["uuid"]
                ioc["ingested_at"] = dragoslib.utils.format_datetime(ingest_timestamp)
                if "first_seen" in ioc:
                    if ioc["first_seen"] == None or ioc["first_seen"] == "":
                        ioc["first_seen"] = dragoslib.utils.format_datetime(ingest_timestamp)
                if "last_seen" in ioc:
                    if ioc["last_seen"] == None or ioc["last_seen"] == "":
                        ioc["last_seen"] = dragoslib.utils.format_datetime(ingest_timestamp)
                
                # Its too complex using simplexml dashboards to link to multipe serials
                # so if there is more than one just pick the first one
                product_serial = None
                if "products" in ioc:
                    if isinstance(ioc["products"], list):
                        for product in ioc["products"]:
                            if "serial" in product:
                                product_serial = product["serial"]
                ioc["primary_product_serial"] = product_serial

                ioc["value_wildcard"] = ioc["value"]
                if ioc["indicator_type"] == "domain":
                    split_parts = ioc["value"].split(".")      
                    split_parts.reverse()
                    reversed_domain = ".".join(split_parts)
                    if reversed_domain[-1] != ".":
                        reversed_domain += "."
                    reversed_domain += "*"
                    ioc["value_wildcard"] = reversed_domain

            ioc_kvstore.data.batch_save(*list_of_iocs)


    def send_iocs_to_splunk_es_intel_collection(self, splunk_es_service, http_method, intel_collection, ioc_data, key_fields):
        validated_ioc_data = []
        invalid_ioc_data = []

        for ioc in ioc_data:
            if ( (len(set(key_fields).intersection(ioc.keys())) > 0) and ('threat_key' in ioc) ):
                validated_ioc_data.append(ioc)
            else:
                self._logger.warning("Invalid IOC, missing at least 1 key field of %s or threat_key field. IOC removed prior to sending to Splunk ES" % key_fields)
                self._logger.warning("Raw IOC = " +  json.dumps(ioc))
                invalid_ioc_data.append(ioc)

        self._logger.info("Final IOC count prior to http %s: valid=%d, invalid and not sent=%d" % (http_method, len(validated_ioc_data), len(invalid_ioc_data)))

        if len(validated_ioc_data) > 0:
            try:
                http_body = urlencode({"item": json.dumps(validated_ioc_data)})
                resp = None
                
                if http_method == 'POST':
                    resp = splunk_es_service.post('/services/data/threat_intel/item/' + intel_collection, body=http_body)
                elif http_method == 'PUT':
                    resp = splunk_es_service.put('/services/data/threat_intel/item/' + intel_collection, body=http_body)

                if not (200 <= resp.status and resp.status < 300):
                    raise RuntimeError("Unable to send IOCs to Splunk ES at %s. Response code %d" % (splunk_es_service.authority, resp.status))
            except:
                # Just log the http request info...error info will be logged elsewhere
                self._logger.info("HTTP Method: %s" % http_method)
                self._logger.info("HTTP Body: %s" % http_body)
                raise



    def check_iocs_in_splunk_es_intel_collection(self, splunk_es_service, intel_collection, ioc_data, key_fields):
        existing_iocs = []
        new_iocs = ioc_data

        try:
            resp = splunk_es_service.get('/services/data/threat_intel/item/' + intel_collection, item=json.dumps(ioc_data))

            # API returns 400 if there aren't any IOCs to update, so just silently accept all
            if (200 <= resp.status and resp.status < 300):
                resp_body = json.load(resp.body)
                if 'message' in resp_body:
                    existing_iocs = resp_body['message']
            else:
                new_iocs = ioc_data

            if len(existing_iocs) > 0:
                new_iocs = []

                # trim our existing IOCs to remove fields we don't care about
                # and then identify the IOCs that already exist and therefore aren't
                # condidered 'new'
                existing_iocs_values = []
                for ioc in existing_iocs:
                    ioc.pop('time')
                    ioc.pop('_user')
                    existing_iocs_values = existing_iocs_values + [ioc[k] for k in ioc.keys() if k in key_fields]

                for ioc in ioc_data:
                    # If we can't find the ioc in the existing values, then add it to
                    # the list of new iocs
                    if not next((i for i in ioc.values() if i in existing_iocs_values), None):
                        new_iocs.append(ioc)
        except Exception as e:
            # If no IOCs are present then the API returns a 400. This is not an error
            if type(e) == HTTPError and e.status == 400:
                pass
            else:
                raise
                

        return [new_iocs, existing_iocs]

    
    def send_iocs_to_splunk_es_with_retry(self, splunk_es_service, intel_collection, threat_key, ioc_data, key_fields, internal_app_config):
        if len(ioc_data) > 0:
            attempts = 0
            
            # If we fail in the middle of adding IOCs to Splunk, then restart the whole upload processes
            # This is because a failure in the middle of an add may have resulted in some but not all of the IOCs being 
            # uploaded. In this event we then want to restart by querying splunk to see which IOCs are already present
            # so that we don't add a duplicate.
            while attempts < internal_app_config.splunk_es_max_retries():
                try:
                    attempts = attempts + 1
                    
                    iocs_to_add, iocs_to_update = self.check_iocs_in_splunk_es_intel_collection(splunk_es_service, intel_collection, ioc_data, key_fields)
                    self._logger.info("Sending %d IOCs to Splunk ES %s collection '%s' (num_to_add=%d, num_to_update=%d)" % (len(ioc_data), intel_collection, threat_key, len(iocs_to_add), len(iocs_to_update)))
                    self.send_iocs_to_splunk_es_intel_collection(splunk_es_service, 'POST', intel_collection, iocs_to_add, key_fields)
                    self.send_iocs_to_splunk_es_intel_collection(splunk_es_service, 'PUT', intel_collection, iocs_to_update, key_fields)

                    # if we've gotten this far then we successfully sent the iocs so terminate the retry loop
                    attempts = internal_app_config.splunk_es_max_retries()
                except Exception as e:
                    if attempts < internal_app_config.splunk_es_max_retries():
                        self._logger.info("Error communicating with Splunk ES API, trying again. Attempt %d of %d. Error: %s" % (attempts, internal_app_config.splunk_es_max_retries(), repr(e)))
                        time.sleep(internal_app_config.splunk_es_wait_seconds_before_retry())
                    else:
                        self._logger.error("Error communicating with Splunk ES API, max retries exceeded")
                        self._logger.exception(e)
                        raise
    

    def process_list_of_iocs_dest_splunk_es(self, list_of_iocs, splunk_es_service, threat_key, ingest_timestamp, ioc_inactive_list, internal_app_config):
        if len(list_of_iocs) > 0:
            # break the array into smaller chunks so we don't overload the splunk API
            # by querying/uploading too many IOCs in a single API request
            batch_size = internal_app_config.splunk_es_batch_size()
            ioc_batches = [list_of_iocs[i:i + batch_size] for i in range(0, len(list_of_iocs), batch_size)] 

            counter = 1

            for batch in ioc_batches:
                self._logger.info("Sending batch of %d IOCs (%d-%d out of %d) to Splunk ES" % (len(batch), counter, counter+len(batch)-1, len(list_of_iocs)))
                counter = counter + len(batch)

                ip_intel = []
                file_intel = []

                for ioc in batch:
                    if ioc["value"] != None and ioc["value"] != "":
                        if ioc["indicator_type"] == "ip":
                            ip_intel.append({ "ip": ioc["value"], "threat_key": threat_key })
                        elif ioc["indicator_type"] == "domain":
                            ip_intel.append({ "domain": ioc["value"], "threat_key": threat_key })
                        elif ioc["indicator_type"] == "hostname":
                            ip_intel.append({ "domain": ioc["value"], "threat_key": threat_key })
                        elif ioc["indicator_type"] == "md5" or ioc["indicator_type"] == "sha1" or ioc["indicator_type"] == "sha256":
                            file_intel.append( {"file_hash": ioc["value"], "threat_key": threat_key })
                        elif ioc["indicator_type"] == "filename":
                            file_intel.append( {"file_name": ioc["value"], "threat_key": threat_key })
                
                self.send_iocs_to_splunk_es_with_retry(splunk_es_service, "ip_intel", threat_key, ip_intel, ["ip", "domain"], internal_app_config)
                self.send_iocs_to_splunk_es_with_retry(splunk_es_service, "file_intel", threat_key, file_intel, ["file_hash", "file_name"], internal_app_config)
    

    def process_list_of_iocs(self, list_of_iocs, ioc_destination_config, ioc_dest, ingest_timestamp, ioc_inactive_list, output_to_index, index_name, host, event_writer, internal_app_config):
        # remove any IOCs in the inactive list prior to sending them to their destination
        inactive_ids = ioc_inactive_list.get_inactive_ids()
        pruned_list_of_iocs = [ioc for ioc in list_of_iocs if "id" in ioc and ioc["id"] not in inactive_ids]

        if ioc_destination_config == self.IOC_DEST_KV_STORE:
            self.process_list_of_iocs_dest_kv_store(pruned_list_of_iocs, ioc_dest, ingest_timestamp, ioc_inactive_list, internal_app_config)
        elif ioc_destination_config == self.IOC_DEST_SPLUNK_ES:
            self.process_list_of_iocs_dest_splunk_es(pruned_list_of_iocs, ioc_dest[0], ioc_dest[1], ingest_timestamp, ioc_inactive_list, internal_app_config) 

        try:
            if output_to_index:
                for ioc in pruned_list_of_iocs:
                    import json
                    event = Event()
                    event.data = json.dumps(ioc)
                    event.sourceType = "dragos_ioc"
                    parsed_timestamp = datetime.datetime.strptime(ioc["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                    event.time = int(time.mktime(parsed_timestamp.timetuple()))
                    if index_name:
                        event.index = index_name
                    if host:
                        event.host = host
                    event_writer.write_event(event)
        except Exception as e:
            try:
                self._logger.error("Error outputting IOC with uuid %s to index" % ioc["uuid"])
                self._logger.exception(e)
            except Exception as e:
                self._logger.error("Error logging IOC to index error")
                self._logger.exception(e)
        
        self._num_ingested += len(list_of_iocs)

    def _setup_remote_search_head_service_object(self, search_head_location, username, password):
        splunkd = urlsplit(search_head_location, allow_fragments=False)
        
        port = splunkd.port
        if splunkd.port == None:
            if splunkd.scheme == 'https':
                port = 443
            else:
                port = 80

        remote_service_with_app = Service(
            scheme=splunkd.scheme,
            host=splunkd.hostname,
            port=port,
            username=username,
            password=password,
            app=dragoslib.utils.APP_NAME,
            owner='nobody',
            autologin=True
        )

        return remote_service_with_app

    def _wait_for_kv_store(self, service, sleep_seconds=10, times_to_try=12):
        kv_store_ready = False
        x = 0
        while x < times_to_try:
            try:
                if service.info['kvStoreStatus'].lower() == 'ready':
                    x = times_to_try
                    kv_store_ready = True
                else:
                    time.sleep(sleep_seconds)
                    x = x + 1
            except:
                time.sleep(sleep_seconds)
                x = x + 1


        if not kv_store_ready:
            raise RuntimeError("Splunk KV store at %s is not ready after %d seconds" % (str(service.authority), sleep_seconds * times_to_try))
    

    def verify_api_connectivity(self, label, location, username, password):
        try:
            masked = dragoslib.dragos_api_credential_manager.DragosAPICredentialManager.MASKED_CREDENTIAL

            self._logger.info("%s Location = %s" % (label, location))
            self._logger.info("Verifying connectivity to %s" % location)
            self._logger.info("If there are no further log statements indicating the connection was successful, then please verify connectivity " +
                            "to the %s outside of Splunk. Also verify there are no firewall or other network restrictions " % label               +
                            "preventing communciations. After verifying connectivity please retry creating the input.")

            # verify we can connect to splunk by issuing a get request
            # we are simply trying to make a connection and want to ignore any complaints about a self
            # signed cert that may be present in a client's environment.
            # By default splunklib doesn't perform ssl certification so we don't do it also
            r = requests.get(location, verify=False)

            if r.status_code != requests.codes.ok:
                raise ValueError("A connection was made to the %s %s but an unknown HTTP error (code=%s, error=\"%s\") occurred." % (label, location, r.status_code, r.content))
            
            # if the password has been updated then check to see if the creds are valid
            if password != masked:
                remote_service = self._setup_remote_search_head_service_object(location, username, password)
                remote_service.login()

            self._logger.info("Successfully validated connection and/or credentials to %s %s" % (label, location))
        except requests.exceptions.ConnectionError as e:
            raise ValueError("There was an error connecting to the %s %s. Please verify connectivity. Error: %s" % (label, location, repr(e)))
        except requests.exceptions.Timeout as e:
            raise ValueError("The connection to the %s %s timed out. Error: " % (label, location, repr(e)))
        except requests.exceptions.ProxyError as e:
            raise ValueError("There was a proxy error when connecting to the %s %s. Error: %s" % (label, location, repr(e)))
        except requests.exceptions.SSLError as e:
            raise ValueError("A SSL error occurred when connecting to the %s %s. Error: %s" % (label, location, repr(e)))
        except requests.exceptions.TooManyRedirects as e:
            raise ValueError("Too many redirects when connecting to the %s %s. Error: %s" % (label, location, repr(e)))
        except requests.exceptions.ChunkedEncodingError as e:
            raise ValueError("The remote search headr declared chunked encoding but sent an invalid chunk. Error: " + repr(e))
        except requests.exceptions.ContentDecodingError as e:
            raise ValueError("Failed to decode response content from the remote search head. Error: " + repr(e))
        except AuthenticationError as e:
            raise ValueError("A connection was made to the %s %s, but the username '%s' was unknown or the password was incorrect. Error: %s" % (label, location, username, repr(e)))
        except HTTPError as e:
            raise ValueError("A connection was made to the %s %s, but it returned returned an HTTP error. Error: %s" % (label, location, repr(e)))
        except socket.gaierror as e:
            raise ValueError("Unable to resolve %s %s Please verify URL. Error: %s" % (label, location, repr(e)))
        except ConnectionRefusedError as e:
            raise ValueError("Connection to %s at %s was refused. Please verify URL. Error: %s" % (label, location, repr(e)))
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError("Unkown error when attempting to connect to %s. Please verify location, credentials, and connectivity. Error: %s" % (label, repr(e)))
       

if __name__ == "__main__":
    sys.exit(DragosIOCs().run(sys.argv))
