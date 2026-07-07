
# encoding = utf-8

import json
from input_module_powerflex_common import PowerFlexCommonDataCollector
from input_module_powerflex_common import timer

class PowerFlexInstanceCollector(PowerFlexCommonDataCollector):
    # Input type
    DELTA_INPUT, INSTANCE_INPUT = range(2) 
    RETRY = 3
    MAX_COLLECT_COUNT = 1000

    def __init__(self, helper, event_writer):
        """
        Data Collector class.
        :param helper: instance of ModInputpowerflex_os_instance
        :param event_writer: class instance to write the events
        """
        super(PowerFlexInstanceCollector, self).__init__(helper, event_writer, 'ta_dell_powerflex_powerflex_os_instance')

        self.instances_rest_endpoint = helper.get_arg('instances_rest_endpoint')
        self.request_method = self.helper.get_arg('method')

        # Delta Endpoint or not
        self.system_id = None
        self.input_type = self.parse_input_type()
        self.input_ckpt_key = "{}_{}".format(self.powerflex_account_obj.name, self.input_name)

        # Instance specific parameters
        self.is_completed = False
        self.retry = 0
        self.call_count = 0
        self.is_data_dirty = False

    def parse_input_type(self):
        """
        Return whether the endpoint is of type delta or not. Verify using the request paramaters i.e. system_id, session_tag & last_version
        """
        try:
            if all(("system id" in self.instances_rest_endpoint, "last version" in self.instances_rest_endpoint, "session tag" in self.instances_rest_endpoint)):
                # Replace the parameters with variable name so that we can use format in future.
                self.instances_rest_endpoint = self.instances_rest_endpoint.replace("system id", "system_id").replace("last version", "last_version").replace("session tag", "session_tag")
                return self.DELTA_INPUT
            else:
                # sdc_to_sds_disconnection endpoint handling
                if r"System::{id}" in self.instances_rest_endpoint:
                    self.logger.debug(r"Updating System::{id} endpoint with system_id")
                    self.instances_rest_endpoint = self.instances_rest_endpoint.replace(r"System::{id}", "System::{}".format(self.get_system_id()))

                return self.INSTANCE_INPUT
        except:
            self.logger.exception("Error while initializing the input.")
            raise

    @timer
    def collect_events(self):
        """
        Collect & Ingest Dell PowerFlex Instance events into Splunk
        """
        try:
            self.state = self.get_state()
            while self.is_not_completed():
                response = self.request(self.state)
                self.state = self.update_state(response)
                self.parse_and_write_events(response)
        except:
            self.logger.exception("Error while collecting instance data.")

        return self.system_id


    def get_state(self):
        """
        Update the self.state using the checkpoint file.
        """
        if self.input_type != self.DELTA_INPUT:
            return None

        state = None
        try:
            self.logger.debug("Getting the checkpoint for ckpt_name={}".format(self.input_ckpt_key))
            state = self.helper.get_check_point(self.input_ckpt_key)
            if state:
                self.logger.debug("Got the checkpoint state: {}".format(",".join("{}={}".format(key, value) for key, value in state.items())))
            else:
                self.logger.info('No checkpoint found.')
        except Exception as e:
            self.logger.info('No checkpoint found. msg="{}"'.format(str(e)))

        if not state:
            state = {
                "last_version": 0,
                "session_tag": 0
            }
        return state


    def is_not_completed(self):
        """
        Determine whether the data collection is completed or not, based on the state.
        """
        if self.is_completed:
            self.logger.debug("Completed the collection loop is_completed=true call_count={}".format(self.call_count))
            return False
        self.call_count += 1
        if self.call_count >= self.MAX_COLLECT_COUNT:
            self.logger.warning("Max Collect Count exceeded. Stopping the data collection. call_count={}".format(self.call_count))
            return False
        self.logger.debug("Iterating through for loop with is_completed=false call_count={}".format(self.call_count))
        return True

    def get_response_value(self, response, *key_list, **kwargs):
        """
        Iterate through the response elements and return the required one.
        :param response: the dictionary object from which the key should be searched
        :param *key_list: the keywords which should be searched from a dictionary-key.
        :param except: provide a keyword if any key should be discarded.
        """
        self.logger.debug('Finding key="{}",except_key={} from response'.format("+".join(key_list), kwargs.get("except_key")))
        for each_element in response:
            if all([bool(each_key.lower() in each_element.lower()) for each_key in key_list]):
                if kwargs.get("except_key") and kwargs.get("except_key") in each_element:
                    self.logger.debug('Skipping the response for key="{}" because of except_key={}'.format("+".join(key_list), kwargs.get("except_key")))
                    continue
                self.logger.debug('Found the response for key="{}"'.format("+".join(key_list)))
                if kwargs.get("return_key"):
                    return each_element
                return response[each_element]
        else:
            self.logger.warning("Could not find the element for key={},except_key={} from response".format("+".join(key_list), kwargs.get("except_key")))

    def update_state(self, response):
        """
        Update self.state & the checkpoint using the response
        """

        self.logger.debug("Updating the state")
        if self.input_type != self.DELTA_INPUT:
            self.is_completed = True
            return

        if response.get("isDirty", None):
            self.is_data_dirty = True
            self.logger.info("Got isDirty=true response from endpoint. will try again try_count={}.".format(self.retry))
            # Try again.!
            self.retry += 1
            if self.retry >= self.RETRY:
                raise Exception("Got isDirty=true response more than 3 times.")
            return self.state
        # Reset the retries
        self.retry = 0

        is_partial = self.get_response_value(response, "isPartial")
        if not is_partial:
            self.logger.debug("Got isPartial=false.")
            self.is_completed = True

        state = {
            "last_version": self.get_response_value(response, "last", "Version") or 0,
            "session_tag": response["sessionTag"] or 0
        }

        if state == self.state:
            self.logger.info("No delta found. Skipping the data ingestion.")
            self.is_data_dirty = True

        return state


    def parse_and_write_events(self, response):
        """
        Write events
        """
        if self.is_data_dirty:
            self.logger.debug("Skipping event ingestion for the data.")
            self.is_data_dirty = False
            return

        self.logger.debug("Ingesting the events collected")
        if self.input_type == self.DELTA_INPUT:

            # Get require key from response & log message
            response_list_key = self.get_response_value(response, "List", except_key="deleted", return_key=True)
            response_deleted_list_key = self.get_response_value(response, "deleted", "Id" ,"List", return_key=True)
            self.logger.info("Ingesting the delta events for last_version={}, list_count={}, delete_count={}".format(
                        self.state["last_version"],
                        len(response.get(response_list_key) or list()),
                        len(response.get(response_deleted_list_key) or list())
                ))

            # Ingest List
            for each_list_element in (response.get(response_list_key) or list()):
                each_list_element["systemId"] = self.get_system_id()
                each_list_element["lastVersion"] = self.state["last_version"]

                each_event = self.helper.new_event(json.dumps(each_list_element), time=None, host=self.host, index=self.index, source=self.source, sourcetype=self.sourcetype, done=True, unbroken=True)
                self.event_writer.write_event(each_event)

            #Ingest DeletedEvents
            if response.get(response_deleted_list_key):
                deleted_id_response = dict()
                deleted_id_response["systemId"] = self.get_system_id()
                deleted_id_response["lastVersion"] = self.state["last_version"]
                deleted_id_response[response_deleted_list_key] = response.get(response_deleted_list_key)

                deleted_id_event = self.helper.new_event(json.dumps(deleted_id_response), time=None, host=self.host, index=self.index, source=self.source, sourcetype=self.sourcetype, done=True, unbroken=True)
                self.event_writer.write_event(deleted_id_event)

            # Update Checkpoint for delta type of endpoints
            self.logger.debug("Storing checkpoint ckpt_name={}, {}".format(self.input_ckpt_key, ",".join("{}={}".format(key, value) for key, value in self.state.items())))
            self.helper.save_check_point(self.input_ckpt_key, self.state)

        else:
            if isinstance(response, list):
                self.logger.info("Ingesting the instance events. type=list, event_count={}".format(len(response)))
                for each_element in response:
                    # Ingest events
                    each_element["systemId"] = self.get_system_id()
                    each_event = self.helper.new_event(json.dumps(each_element), time=None, host=self.host, index=self.index, source=self.source, sourcetype=self.sourcetype, done=True, unbroken=True)
                    self.event_writer.write_event(each_event)
            elif isinstance(response, dict):
                # for POST response, like SDC_disconnection, mdm_cluster
                response["systemId"] = self.get_system_id()
                self.logger.info("Ingesting an instance event. type=dictionary, event_count=1")
                event = self.helper.new_event(json.dumps(response), time=None, host=self.host, index=self.index, source=self.source, sourcetype=self.sourcetype, done=True, unbroken=True)
                self.event_writer.write_event(event)
            else:
                raise Exception("Unsupported type of response. type={}".format(str(type(response))))
        self.logger.debug("Ingested the events successfully")


    def request(self, state):
        """
        Request to the Dell Powerflex Rest endpoint
        """
        request_url = self.instances_rest_endpoint.format(system_id=self.get_system_id(), **state) if state else self.instances_rest_endpoint
        self.logger.info("Requesting to the instance endpoint. endpoint={}".format(request_url))
        return self.session_obj.request(url=request_url, method=self.request_method)
