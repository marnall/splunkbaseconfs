import sys
import os
import time
import datetime
import json
import platform

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from splunklib.client import *


import dragoslib.logger
import dragoslib.indicator_api
import dragoslib.utils
import dragoslib.dragos_api_credential_manager
import dragoslib.ioc_cache_tracker
import dragoslib.splunk_collections
import dragoslib.ioc_inactive_list


class DragosIOCs(Script):

    LOOP_SLEEP_TIME = 15

    def __init__(self):
        super(DragosIOCs, self).__init__()
        self._service_with_app = None
        self._num_ingested = 0
        self._logger = dragoslib.logger.create_logger("mod_input")
        self._logger.info("Module input class initialized")

        
    def __debug(self):
        sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
        import splunk_debug as dbg
        dbg.enable_debugging(timeout=120, port=5988)
        dbg.set_breakpoint()

    def get_scheme(self):
        scheme = Scheme("Dragos IOCs")
        scheme.description = "This input pulls Indicators of Compromise (IOCs) from the Dragos WorldView portal. The name of this input must be set to 'dragos_iocs'"
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
    
    def validate_input(self, validation_definition):
        #
        # Note that we have to be quick in this function. splunk will timeout
        # the validation request if we don't return withinin 30 seconds
        #

        # Validate that there is only one active instance of this modular input
        #
        # We do this by forcing the name of the input to be 'dragos_iocs'. We then
        # throw an error if the name doesn't match this. Since splunk requires input
        # names to be unique this accomplishes our goal of having only once instance
        input_name = validation_definition.metadata['name']
        if input_name != 'dragos_iocs':
            raise ValueError("You must name this input 'dragos_iocs'. The name '%s' is not allowed." % input_name)
        
        # Validate that the API credentials they have provided allow them to access
        # the Dragos WorldView API
        # unless the credentials are masked
        api_access_token = validation_definition.parameters['api_access_token']
        api_secret_key   = validation_definition.parameters['api_secret_key']
        masked           = dragoslib.dragos_api_credential_manager.DragosAPICredentialManager.MASKED_CREDENTIAL
        if api_access_token == masked and api_secret_key == masked:
            pass
        elif ((api_access_token == masked and api_secret_key != masked) or 
            (api_access_token != masked and api_secret_key == masked)):
            raise ValueError("If you are updating the Dragos WorldView API credentials please update both the API access token and secret key at the same time.")
        else:
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
        
        # Validate the interval that we check for new IOCs
        poll_interval = validation_definition.parameters['poll_interval']
        if poll_interval[0:6] == '-99900':
            pass
        else:
            if not poll_interval.isdigit():
                raise ValueError("Invalid poll interval. Value must be a positive integer >= 1")
            if int(poll_interval) < 1:
                raise ValueError("Invalid poll interval. Must be >= 1")

        # Validate the interval that we perform a full IOC replacement
        full_replace_interval = validation_definition.parameters['full_replace_interval']
        if full_replace_interval[0:6] == '-99900':
            pass
        else:
            if not full_replace_interval.isdigit():
                raise ValueError("Invalid full replacement interval. Value must be a positive integer >= 1")
            if int(full_replace_interval) < 1:
                raise ValueError("Invalid full replacement interval. Must be >= 1")

        if 'output_to_index' in validation_definition.parameters:
            output_to_index = validation_definition.parameters['output_to_index']
            if output_to_index:
                if output_to_index.lower() == 'true':
                    pass
                elif output_to_index.lower() == 'false':
                    pass
                elif output_to_index.lower() == 'none':
                    pass
                else:
                    raise ValueError("Invalid value for the output_to_index field. The value specified was '%s' but it must either be 'true'/'false' (without quotes) or left empty" % output_to_index)
    
    def stream_events(self, inputs, ew):
        self._logger.info("Starting stream_events method")
        self._logger.info("Python version %s" % platform.python_version())
        #
        # Initialize things and make sure the credentials are placed in secure storage
        #
        try:
            service_with_app = dragoslib.utils.create_app_specific_service(service=self.service, owner='nobody')
            api_creds_manager = dragoslib.dragos_api_credential_manager.DragosAPICredentialManager(service_with_app)
        except Exception as e:
            self._logger.error("Error initializing modular input run")
            self._logger.exception(e)
            return

        # If there aren't any inputs configured, the bail
        if dragoslib.utils.INPUT_NAME not in inputs.inputs:
            self._logger.info("No inputs configured. Leaving")
            return
        #
        # Initialize things so we can go into our poll loop
        #
        try:
            input_parameters = inputs.inputs[dragoslib.utils.INPUT_NAME]
            dragos_api = dragoslib.indicator_api.IndicatorApi(api_creds_manager.access_token, api_creds_manager.secret_key, service_with_app)

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
                # something weird has happened default to 7 day days
                full_replace_interval = 86400 * 7
            
            output_to_index = ""
            if 'output_to_index' in input_parameters:
                output_to_index = input_parameters['output_to_index'] if input_parameters['output_to_index'] else ""
            output_to_index = True if output_to_index.lower() == 'true' else False

            self._logger.info("Starting to poll for new IOCs from Dragos API, sleep_time=%d, interval=%d" % 
                (self.LOOP_SLEEP_TIME, poll_interval))

            ioc_cache_tracker = dragoslib.ioc_cache_tracker.IOCCacheTracker(service_with_app)
            ioc_inactive_list = dragoslib.ioc_inactive_list.IOCInactiveList(service_with_app, self._logger)

            # this should be created via the default collections.conf but create it here just to be safe
            if dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE not in service_with_app.kvstore:
                service_with_app.kvstore.create(dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE)
            
        except Exception as e:
            self._logger.error("Error initializing modular input run")
            self._logger.exception(e)
            try:
                ioc_cache_tracker.record_new_ioc_pull(datetime.datetime.now(), 0, "Error initializing modular input runtime. Check dragos_ta_threat_intel_mod_input.log for more details.")
            except Exception:
                # eat the exception
                pass
            return

        
        #
        # Loop and poll for new IOCs
        #
        while True:
            try:
                time.sleep(self.LOOP_SLEEP_TIME)

                ioc_cache_tracker.update_last_mod_input_run_time()

                if ioc_cache_tracker.should_perform_full_ioc_replacement(full_replace_interval):
                    ioc_cache_tracker.update_cache_for_full_replacement()
                    service_with_app.kvstore[dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE].data.delete()

                if ioc_cache_tracker.should_pull_new_iocs(poll_interval):
                    
                    ingest_timestamp = datetime.datetime.now()
                    self._num_ingested = 0

                    def process_iocs_helper(ioc_list):
                        self.process_list_of_iocs(ioc_list, service_with_app.kvstore[dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE], ingest_timestamp, ioc_inactive_list, output_to_index, ew)

                    dragos_api.get_iocs(ioc_cache_tracker.last_ioc_pull, process_iocs_helper)

                    # clean up any IOCs that may have accidentally been added
                    # due to a race condition with the inactive managemet page
                    ioc_inactive_list.remove_all_inactive_from_ioc_list()

                    ioc_cache_tracker.record_new_ioc_pull(ingest_timestamp, self._num_ingested)
            except Exception as e:
                self._logger.error("Catching error on API poll loop")
                self._logger.exception(e)
                try:
                    ioc_cache_tracker.record_new_ioc_pull(datetime.datetime.now(), 0, "Error while updating list of IOCs. " + str(e))
                except Exception:
                    # eat the exception if we cant record the failed IOC pull
                    pass
                
            
                
        
    def process_list_of_iocs(self, list_of_iocs, ioc_kvstore, ingest_timestamp, ioc_inactive_list, output_to_index, event_writer):
        # do a single pass through the list to add the _key value that is required
        # by the splunk kv store

        if len(list_of_iocs) > 0:
            for ioc in list_of_iocs:
                ioc["_key"] = ioc["uuid"]
                ioc["ingested_at"] = dragoslib.utils.format_datetime(ingest_timestamp)

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

            inactive_ids = ioc_inactive_list.get_inactive_ids()
            pruned_list_of_iocs = [ioc for ioc in list_of_iocs if ioc["id"] not in inactive_ids]

            ioc_kvstore.data.batch_save(*pruned_list_of_iocs)

            if output_to_index:
                for ioc in pruned_list_of_iocs:
                    import json

                    event = Event()
                    event.data = json.dumps(ioc)
                    event.sourcetype = "dragos_ioc"
                    event.time = datetime.datetime.strptime(ioc["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime('%s')
                    event.index = "main"
                    event_writer.write_event(event)
        
        self._num_ingested += len(list_of_iocs)

       

if __name__ == "__main__":
    sys.exit(DragosIOCs().run(sys.argv))
