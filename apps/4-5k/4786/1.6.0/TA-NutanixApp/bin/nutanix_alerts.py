import json
import time
from splunklib.modularinput import *
import sys
import traceback
import splunklib.client as client
from nutanix_splunk_client import NutanixSplunkClient
from nutanix_api_processor import NutanixApiProcessor

class NutanixALERTS(NutanixSplunkClient):

    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Nutanix Prism API Alerts')
        scheme.description = 'Streams data about the Alerts in a cluster into Splunk for indexing.'
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
        start_argument.description = 'Start Time is necessary in determining how far back to get alerts. This number should be in seconds.'
        start_argument.required_on_create = True
        scheme.add_argument(start_argument)
        return scheme

    def stream_events(self, inputs, ew):
        # Taken from Splunk's event writer module.

        """The method called to stream events into Splunk. It should do all of its output via
            EventWriter rather than assuming that there is a console attached.
            :param ew: An object with methods to write events and log messages to Splunk.
            """

        ew.log('INFO', 'Obtaining Username, Password, Console IP, and Port Number from inputs.conf.')
        for input_name, input_item in inputs.inputs.iteritems():
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
            self.encrypt_password(service, Username, Password, realm, ew)
            self.mask_password(service, Username, Module_Name, ew)
        else:
            Password = self.get_password(service, Username, realm, ew)
        ew.log('INFO',
               'Accessing Nutanix Rest API for alert data using Username:%s,IP:%s,Ports:%s' % (Username, IP, Port))

        # Creating a session
        endpoint = 'https://%s:%s/PrismGateway/services/rest/' % (IP, Port)

        # Fetching the current time in microseconds
        now = lambda: int(time.time() * 1000000)
        # converting user input to microseconds. User input must be in seconds. If set to 0, will get current.
        past = int(now() - (Start_Time * 1000000))
        param = {'start_time_in_usecs': past, 'end_time_in_usecs': now()}

        #create nutanix api processor object
        api_processor = NutanixApiProcessor(endpoint, Username, Password, ew)
        # Obtaining data on Alerts.
        ew.log('INFO', 'Obtaining data about the alerts in a cluster.')
        dataset = api_processor.make_api_call(api_processor.get_url("alerts"), param=param)
        if dataset:
            cluster_dataset = api_processor.make_api_call(api_processor.get_url("cluster"))
            for item in dataset['entities']:
                try:
                    event = Event()
                    event.stanza = input_name
                    event.source = 'nutanix:alerts'
                    event.host = endpoint + 'v2.0/alerts/'
                    #ew.log('INFO', 'Inside the alerts for loop %s' %item)
                    data = self.get_alert_data(item, cluster_dataset, api_processor, IP)
                    event.data = json.dumps(data)
                    event.sourcetype = 'nutanix_alerts'
                    ew.write_event(event)
                except Exception as e:
                    type_, value_, traceback_ = sys.exc_info()
                    err_msg = '\n'.join(traceback.format_exception(type_, value_, traceback_))
                    ew.log('ERROR',
                           'Splunk was unable to retrieve alert data. The following error was encountered  : [[%s]]' % err_msg)
                    continue
            ew.log('INFO', 'Completed fetching Alerts data')           
    def get_alert_data(self, dataset, cluster_dataset, api_processor, IP):

        """The method called to process alert data
        :param dataset: dict containing alert data
        :param cluster_dataset: Dict containing cluster data
        :param ew: An object with methods to write events and log messages to Splunk.
        """
        
        contextDict = {key: value for key, value in zip(dataset["context_types"], dataset["context_values"])}
        cluster_metadata = {"IS_PC-PE": False,
                            "cluster_uuid":dataset["cluster_uuid"],
                            "cluster_name":cluster_dataset['name']}
        
        #For PC Support: For PC Alert use cluster name from cluster dataset otherwise fetch cluster name using uuid       
        if cluster_dataset["cluster_uuid"] == dataset["cluster_uuid"]:
            cluster_name = cluster_dataset["name"]
            cluster_metadata.update({"cluster_uuid":dataset["cluster_uuid"]})
        else:
            cluster_metadata.update({"IS_PC-PE":True})
            cluster_name = api_processor.get_entity_name_from_uniqueID("clusters", dataset["cluster_uuid"], cluster_metadata)

        #Incase of wrong uuid is coming from api
        if api_processor.validate_uuid(dataset["node_uuid"]):   
            node_name = api_processor.get_entity_name_from_uniqueID("node", dataset["node_uuid"],cluster_metadata)
        else:
            node_name = None

        #Context Types and message placeholders do not match
        try:
            message = dataset["message"].format(**contextDict)            
        except Exception as e:
            message = dataset["message"]

        alert_dataset = {
            "alert_title": dataset["alert_title"].format(**contextDict),
            "message": message,
            "cluster_name": cluster_name,
            "alert_type_uuid":dataset["alert_type_uuid"],
            "resolved": dataset["resolved"],
            "auto_resolved": dataset["auto_resolved"],
            "acknowledged": dataset["acknowledged"],
            "classifications": dataset["classifications"],
            "impact_types": dataset["impact_types"],
            "detailed_message": dataset["detailed_message"],
            "alert_details": dataset["alert_details"],
            "severity": dataset["severity"],
            "cluster_uuid": dataset["cluster_uuid"],
            "node_uuid": dataset["node_uuid"],
            "node_name": node_name,
            "affected_entities": api_processor.get_affected_entities_name(dataset["affected_entities"],cluster_metadata),
            "id":dataset["id"],
            "created_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["created_time_stamp_in_usecs"]),
            "last_occurrence_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["last_occurrence_time_stamp_in_usecs"]),
            "acknowledged_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["acknowledged_time_stamp_in_usecs"]),
            "resolved_time_stamp": api_processor.convert_timestamp_to_dateTime_format(dataset["resolved_time_stamp_in_usecs"])
        }
        return alert_dataset
        
if __name__ == '__main__':
    sys.exit(NutanixALERTS().run(sys.argv))
