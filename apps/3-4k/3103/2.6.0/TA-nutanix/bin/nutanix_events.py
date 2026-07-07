import ta_nutanix_declare
import json
from splunklib.modularinput import *
import time
import sys
import traceback
from six.moves import zip
import splunklib.client as client
from nutanix_splunk_client import NutanixSplunkClient
from nutanix_api_processor import NutanixApiProcessor
import logger.log as log
import urllib3
urllib3.disable_warnings()

_LOGGER = log.Logs().get_logger("events")
class NutanixEVENTS(NutanixSplunkClient):
    
    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Nutanix Prism API Events')
        scheme.description = 'Streams data about the events in a cluster into Splunk for indexing.'
        scheme.use_external_validation = True
        
        # About the username located in inputs.conf.spec
        username_argument = Argument('username')
        username_argument.data_type = Argument.data_type_string
        username_argument.description = 'Username is necessary to authenticate with the Nutanix Prism Rest API.'
        username_argument.required_on_create = True
        scheme.add_argument(username_argument)
        
        # About the password located in inputs.conf.spec
        password_argument = Argument('password')
        password_argument.data_type = Argument.data_type_string
        password_argument.description = 'Password is necessary to authenticate with the Nutanix Prism Rest API.'
        password_argument.required_on_create = True
        scheme.add_argument(password_argument)
        
        
        # About the IP/Hostname located in inputs.conf.spec
        ip_argument = Argument('ip')
        ip_argument.data_type = Argument.data_type_string
        ip_argument.description = 'IP or Hostname is necessary to access the Nutanix Prism Rest API.'
        ip_argument.required_on_create = True
        scheme.add_argument(ip_argument)
        
        
        # About the port located in inputs.conf.spec
        port_argument = Argument('port')
        port_argument.data_type = Argument.data_type_string
        port_argument.description = 'Port is necessary to access the Nutanix Prism Rest API.'
        port_argument.required_on_create = True
        scheme.add_argument(port_argument)
        
        # About the start_time located in inputs.conf.spec
        start_argument = Argument('start_time')
        start_argument.data_type = Argument.data_type_string
        start_argument.description = 'Start_Time is necessary in determining how far back to get events. This number should be in seconds.'
        start_argument.required_on_create = True
        scheme.add_argument(start_argument)
        return scheme
    
    
    def stream_events(self, inputs, ew):
        # Taken from Splunk's event writer module.

        """The method called to stream events into Splunk. It should do all of its output via
            EventWriter rather than assuming that there is a console attached.
            :param ew: An object with methods to write events and log messages to Splunk.
            """
        try:
            _LOGGER.info('Obtaining Username, Password, Console IP, and Port Number from inputs.conf.')
            for input_name, input_item in list(inputs.inputs.items()):
                Username = input_item['username']
                Password = input_item['password']
                IP = input_item['ip']
                Port = input_item['port']
                Start_Time = int(input_item['start_time'])

            # Create session and mask password if hasn't done already
            session_key = self._input_definition.metadata["session_key"]
            Module_Name, _ = inputs.inputs.popitem()
            service = client.connect(**{'token': session_key})
            realm = "%s-%s" % (Module_Name, IP)  # Unique password storage key
            if Password != self.MASK:
                self.save_password(service, Username, Password, realm, _LOGGER)
                self.mask_password(service, Username, Module_Name, _LOGGER)
            else:
                Password = self.get_password(service, Username, realm, _LOGGER)
            _LOGGER.info('Accessing Nutanix Rest API for event data using Username:{},IP:{},Ports:{}'.format(Username, IP, Port))
            # Creating a session
            endpoint = 'https://%s:%s/PrismGateway/services/rest/' % (IP, Port)

            # Fetching the current time in microseconds
            now = lambda: int(time.time() * 1000000)
            # converting user input to microseconds. User input must be in seconds. If set to 0, will get current.
            past = int(now() - (Start_Time * 1000000))
            param = {'start_time_in_usecs': past, 'end_time_in_usecs': now()}

            # create nutanix api processor object
            api_processor = NutanixApiProcessor(endpoint, Username, Password, _LOGGER)

            # Obtaining data on Events.
            _LOGGER.info('Obtaining data about the events in a cluster.')
            dataset = api_processor.make_api_call(api_processor.get_url("events"))
            if dataset:
                cluster_dataset = api_processor.make_api_call(api_processor.get_url("cluster"))
                for item in dataset['entities']:
                    try:
                        event = Event()
                        event.stanza = input_name
                        event.source = 'nutanix:events'
                        event.host = endpoint + 'v2.0/events/'
                        data = self.get_event_data(item, cluster_dataset, api_processor)
                        event.data = json.dumps(data)
                        event.sourcetype = 'nutanix_events'
                        ew.write_event(event)
                    except Exception as e:
                        type_, value_, traceback_ = sys.exc_info()
                        err_msg = '\n'.join(traceback.format_exception(type_, value_, traceback_))
                        _LOGGER.error('Splunk was unable to retrieve event data. The following error was encountered  : [[{}]]'.format(err_msg))
                        continue
                _LOGGER.info('Completed fetching Events data')
        except Exception as e:
                type_, value_, traceback_ = sys.exc_info()
                err_msg = '\n'.join(traceback.format_exception(type_, value_, traceback_))
                _LOGGER.error('Splunk was unable to retrieve event data. The following error was encountered  : [[{}]]'.format(err_msg))
 
          
    def get_event_data(self, dataset, cluster_dataset, api_processor):

        """The method called to process Event information.
                    :param dataset: A dict containing event information.
                    :param cluster_dataset : A dict containing cluster information.
                    """
        dictionary = {key: value for key, value in zip(dataset["context_types"], dataset["context_values"])}
        cluster_metadata = {"IS_PC-PE": False,
                            "cluster_uuid":dataset["cluster_uuid"],
                            "cluster_name":cluster_dataset['name']}
        
        #For PC Support: For PC event use cluster name from cluster dataset otherwise fetch cluster name using uuid       
        if cluster_dataset["cluster_uuid"] == dataset["cluster_uuid"]:
            cluster_name = cluster_dataset["name"]
            cluster_metadata.update({"cluster_uuid":dataset["cluster_uuid"]})
        else:
            cluster_metadata.update({"IS_PC-PE":True})
            cluster_name = api_processor.get_entity_name_from_uniqueID("clusters", dataset["cluster_uuid"], cluster_metadata)

        entity_name = api_processor.get_affected_entities_name(dataset["affected_entities"], cluster_metadata=cluster_metadata)

        #Incase of wrong uuid is coming from api
        if api_processor.validate_uuid(dataset["node_uuid"]):   
            node_name = api_processor.get_entity_name_from_uniqueID("node", dataset["node_uuid"],cluster_metadata)
        else:
            node_name = None

        #Context Types and message placeholders do not match
        try:
            message = dataset["message"].format(**dictionary)            
        except Exception as e:
            message = dataset["message"]        
			
        event_dataset = {
            "id":dataset["id"],
            "alert_title": dataset["alert_title"].format(**dictionary),
            "message": message,
            "cluster_name" : cluster_name,
            "resolved" : dataset["resolved"],
            "auto_resolved" : dataset["auto_resolved"],
            "acknowledged" : dataset["acknowledged"],
            "classifications" : dataset["classifications"],
            "impact_types" : dataset["impact_types"],
            "detailed_message" : dataset["detailed_message"],
            "alert_details" : dataset["alert_details"],
            "severity": dataset["severity"],
            "cluster_uuid" : dataset["cluster_uuid"],
            "created_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["created_time_stamp_in_usecs"]),
            "last_occurrence_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["last_occurrence_time_stamp_in_usecs"]),
            "acknowledged_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["acknowledged_time_stamp_in_usecs"]),
            "resolved_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["resolved_time_stamp_in_usecs"]),
            "alert_type_uuid" : dataset["alert_type_uuid"],
            "affected_entities": entity_name,
            "node_uuid": dataset["node_uuid"],
            "node_name": node_name
                     
        }
        return event_dataset

    def validate_input(self, definition):
        try:
            username = definition.parameters.get('username')
            password = definition.parameters.get('password')
            ip = definition.parameters.get('ip')
            port = definition.parameters.get('port')
                
            _LOGGER.info('Validating user input')

            if ip and port:
                # Create session and mask password if hasn't done already
                session_key = definition.metadata.get('session_key')
                Module_Name = "nutanix_events://" + definition.metadata.get('name')

                service = client.connect(**{'token': session_key})
                if service:
                    realm = "%s-%s" % (Module_Name, ip)  # Unique password storage key
                    if password != self.MASK:
                        self.save_password(service, username, password, realm, _LOGGER)
                    else:
                        password = self.get_password(service, username, realm, _LOGGER)
                    
                    # Creating a session
                    endpoint = 'https://%s:%s/PrismGateway/services/rest/' % (ip, port)

                    #create nutanix api processor object
                    api_processor = NutanixApiProcessor(endpoint, username, password, _LOGGER,)

                    # Checking connectivity of cluster using provided parameter.
                    _LOGGER.info('Checking connectivity using provided parameter')
                    dataset = api_processor.make_api_call(api_processor.get_url("cluster"))
                    if dataset:
                        _LOGGER.info('Connection details validated successfully.')
                    else:
                        _LOGGER.error('The Nutanix Prism API username and/password is incorrect or unauthorized for API access.')    
                        raise Exception('The Nutanix Prism API username and/password is incorrect or unauthorized for API access.')    

        except Exception as e:
            type_, value_, traceback_ = sys.exc_info()
            err_msg = '\n'.join(traceback.format_exception(type_, value_, traceback_))
            _LOGGER.error('The Nutanix Prism API username and/password is incorrect or unauthorized for API access"  : [[{}]]'.format(err_msg))
            sys.exit(1)

if __name__ == '__main__':
    sys.exit(NutanixEVENTS().run(sys.argv))
