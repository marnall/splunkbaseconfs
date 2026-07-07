import ta_nutanix_declare
import json
import requests
from splunklib.modularinput import *
import sys
import traceback
import splunklib.client as client
from nutanix_splunk_client import NutanixSplunkClient
import logger.log as log
from nutanix_api_processor import NutanixApiProcessor

requests.packages.urllib3.disable_warnings()

_LOGGER = log.Logs().get_logger("health")

class NutanixHEALTH(NutanixSplunkClient):
    
    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Nutanix Prism API Health')
        scheme.description = 'Streams data about the Health of a cluster.'
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
        return scheme
    


    def stream_events(self,inputs,ew):
        # Taken from Splunk's event writer module.
    
    
        """The method called to stream events into Splunk. It should do all of its output via EventWriter rather than assuming that there is a console attached.:param ew: An object with methods to write events and log messages to Splunk.
        """
        try:
            _LOGGER.info('Obtaining Username, Password, Console IP, and Port Number from inputs.conf.')
            for input_name, input_item in list(inputs.inputs.items()):
                Username = input_item['username']
                Password = input_item['password']
                IP = input_item['ip']
                Port = input_item['port']
            
            #Create session and mask password if hasn't done already
            session_key = self._input_definition.metadata["session_key"]
            Module_Name, _ = inputs.inputs.popitem()
            service = client.connect(**{'token': session_key})
            realm = "%s-%s" %(Module_Name, IP) #Unique password storage key
            if Password != self.MASK:
                self.save_password(service, Username, Password, realm, _LOGGER)
                self.mask_password(service, Username, Module_Name, _LOGGER)
            else:
                Password = self.get_password(service, Username, realm, _LOGGER)
            # Creating a session
            _LOGGER.info('Accessing Nutanix Rest API for health data using Username:{},IP:{},Ports:{}'.format(Username, IP, Port))
            endpoint = 'https://%s:%s/PrismGateway/services/rest/' %(IP, Port)

             #create nutanix api processor object
            api_processor = NutanixApiProcessor(endpoint, Username, Password, _LOGGER,)
           
            cluster_dataset = api_processor.make_api_call(api_processor.get_url("cluster"))
            if cluster_dataset:
                version = cluster_dataset['version']
                if "pc" not in version.lower():
                    # Obtaining data on VM Health
                    _LOGGER.info("Obtaining data about the health of all VMs.")
                    dataset = api_processor.make_api_call(api_processor.get_url("vm_health"))
                    if dataset:
                        event = Event()
                        event.stanza = input_name
                        event.source = 'nutanix:health'
                        event.host = api_processor.get_url("vm_health")
                        event.data = json.dumps(dataset)
                        event.sourcetype = 'nutanix_health'
                        ew.write_event(event)

            # Obtaining data on Host Health
            _LOGGER.info("Obtaining data about the health of all hosts.")
            dataset = api_processor.make_api_call(api_processor.get_url("host_health"))
            if dataset:
                event = Event()
                event.stanza = input_name
                event.source = 'nutanix:health'
                event.host = api_processor.get_url("host_health")
                event.data = json.dumps(dataset)
                event.sourcetype = 'nutanix_health'
                ew.write_event(event)

            # Obtaining data on Disk Health
            _LOGGER.info('Obtaining data about the health of all disks.')
            dataset = api_processor.make_api_call(api_processor.get_url("disk_health"))
            if dataset:
                event = Event()
                event.stanza = input_name
                event.source = 'nutanix:health'
                event.host = api_processor.get_url("disk_health")
                event.data = json.dumps(dataset)
                event.sourcetype = 'nutanix_health'
                ew.write_event(event)
            _LOGGER.info('Completed fetching Healths data')

        except Exception as e:
            type_, value_, traceback_ = sys.exc_info()
            err_msg = '\n'.join(traceback.format_exception(type_, value_, traceback_))
            _LOGGER.error("Splunk was unable to retrieve data from the Nutanix Prism API. The following error was encountered when accessing the Nutanix API Endpoint to obtain cluster data: [[{}]]".format(err_msg))

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
                Module_Name = "nutanix_health://" + definition.metadata.get('name')

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
    sys.exit(NutanixHEALTH().run(sys.argv))
