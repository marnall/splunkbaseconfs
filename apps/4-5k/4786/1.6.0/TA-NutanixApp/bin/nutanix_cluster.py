import json
import requests
from splunklib.modularinput import *
import time
import sys
from cluster_transforms import clusterstatistics
import traceback
import splunklib.client as client
from nutanix_splunk_client import NutanixSplunkClient

requests.packages.urllib3.disable_warnings()

class NutanixCLUSTER(NutanixSplunkClient):
    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Nutanix Prism API Cluster')
        scheme.description = 'Streams data about the cluster.'
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
        start_argument.description = 'Start Time is necessary in determining how far back to get the stats.'
        start_argument.required_on_create = True
        scheme.add_argument(start_argument)
        return scheme
    
    
    def stream_events(self,inputs,ew):
        # Taken from Splunk's event writer module.
        
        """The method called to stream events into Splunk. It should do all of its output via
            EventWriter rather than assuming that there is a console attached.
            :param ew: An object with methods to write events and log messages to Splunk.
            """
        try:
            ew.log('INFO','Obtaining Username, Password, Console IP, and Port Number from inputs.conf.')
            for input_name, input_item in inputs.inputs.iteritems():
                Username = input_item['username']
                Password = input_item['password']
                IP = input_item['ip']
                Port = input_item['port']
                Start_Time = int(input_item['start_time'])

            #Create session and mask password if hasn't done already
            session_key = self._input_definition.metadata["session_key"]
	    Module_Name, _ = inputs.inputs.popitem()
            service = client.connect(**{'token': session_key})
            realm = "%s-%s" %(Module_Name, IP) #Unique password storage key
	    if Password != self.MASK:
	      self.encrypt_password(service, Username, Password, realm, ew)
	      self.mask_password(service, Username, Module_Name, ew)
            else:
              Password = self.get_password(service, Username, realm, ew)
            ew.log('INFO', 'Accessing Nutanix Rest API for cluster data using Username:%s,IP:%s,Ports:%s' %(Username, IP, Port))
            # Fetching the current time in microseconds
            now = lambda: int(time.time() * 1000000)
            # Converting user input to microseconds. User input must be in seconds. If set to 0, will get current.
            past = int(now()-(Start_Time * 1000000))
            
            # Creating a session
            endpoint = 'https://%s:%s/PrismGateway/services/rest/v1/' %(IP, Port)
            req = requests.Session()
            req.auth = (Username, Password)
            req.headers.update({'Content-Type': 'application/json; charset=utf-8'})
            stats = ['controller_num_iops','controller_io_bandwidth_kBps','controller_avg_io_latency_usecs']
            # Obtaining data on the cluster. Returning data in intervals of a minute
            param = {'metrics':stats,'startTimeInUsecs':past,'endTimeInUsecs':now(),'intervalInSecs':60}
            ew.log('INFO','Obtaining stats data about the cluster.')
            dataset = req.get(endpoint+'cluster/stats/',params=param,verify=False)
            if dataset.status_code == 200:
                ew.log('INFO','Parsing data for Splunk ingestion.')
                for item in clusterstatistics(starttime=past,json_data=dataset.json()['statsSpecificResponses']):
                    for cluster_event in item:
                        event = Event()
                        event.stanza = input_name
                        event.source = 'nutanix:cluster'
                        event.host = endpoint+'cluster/stats/'
                        event.data = json.dumps(cluster_event)
                        event.sourcetype = 'nutanix_cluster'
                        ew.write_event(event)
        
            elif dataset.status_code == 401 or dataset.status_code == 403:
                ew.log('ERROR','The Nutanix Prism API username and/password is incorrect or unauthorized for API access. A status code of %s was returned.' %dataset.status_code)
            
            else:
                ew.log('ERROR','A status code of %s was returned. Splunk was unable to retrieve data from the Nutanix Prism API.' %dataset.status_code)

        except Exception as e:
            type_, value_, traceback_ = sys.exc_info()
            err_msg = '\n'.join(traceback.format_exception(type_, value_, traceback_))
            ew.log('ERROR','Splunk was unable to retrieve data from the Nutanix Prism API. The following error was encountered when accessing Nutanix API Endpoint to obtain stats data about the cluster: [[%s]]' %err_msg)


if __name__ == '__main__':
    sys.exit(NutanixCLUSTER().run(sys.argv))
