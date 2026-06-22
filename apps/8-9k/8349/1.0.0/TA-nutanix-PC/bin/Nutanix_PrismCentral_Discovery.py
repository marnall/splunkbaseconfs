
import sys
import json
import requests
import traceback
from nutanix_splunk_client import NutanixSplunkClient
from nutanix_api_processor import NutanixApiProcessor
import ta_nutanix_declare
import logger.log as log
import splunklib.client as client
from splunklib.modularinput import *
from pc_discovery_fetchers import (
    ClustersFetcher,
    PrismCentralsFetcher,
    HostsFetcher,
    VMsFetcher,
    DisksFetcher,
    StorageContainersFetcher,
    VolumeGroupsFetcher,
    FileServersFetcher,
    AlertsFetcher,
    EventsFetcher,
    HostNICsFetcher
)



requests.packages.urllib3.disable_warnings()

_LOGGER = log.Logs().get_logger("PCDiscovery")
class NutanixPrismCentralDiscovery(NutanixSplunkClient):
    def get_scheme(self):
        scheme = Scheme("Nutanix Prism Central Discovery")
        scheme.description = "Discover Nutanix Prism Central data and index it into Splunk."
        scheme.use_external_validation = True
        scheme.add_argument(Argument("pc_ip", title="Prism Central IP", required_on_create=True))
        scheme.add_argument(Argument("username", title="Username", required_on_create=True))
        scheme.add_argument(Argument("password", title="Password", required_on_create=True))

        return scheme

    def validate_input(self, definition):
        try:
            username = definition.parameters.get('username')
            password = definition.parameters.get('password')
            ip = definition.parameters.get('pc_ip')
            port = definition.parameters.get('port')
            input_name = definition.parameters.get('input_name') 
            _LOGGER.info(f"Validating user input:{ip},{username},{password},{port},{input_name}")

            if ip and port:
                # Create session and mask password if hasn't done already
                session_key = definition.metadata.get('session_key')
                Module_Name = "Nutanix_PrismCentral_Discovery://" + definition.metadata.get('name')

                service = client.connect(**{'token': session_key})
                if service:
                    realm = "%s-%s" % (Module_Name, ip)  # Unique password storage key
                    if password != self.MASK:
                        self.save_password(service, username, password, realm, _LOGGER)
                    else:
                        password = self.get_password(service, username, realm, _LOGGER)
                    
                    endpoint = 'https://%s:%s/api/' % (ip, port)
                    api_processor = NutanixApiProcessor(endpoint, username, password, _LOGGER,)
                    
                    _LOGGER.info('Checking connectivity using provided parameter')
                    dataset, _ = ClustersFetcher(api_processor, None, input_name, service).collect_event_data()
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


    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            ip = input_item["pc_ip"]
            username = input_item["username"]
            password = input_item["password"]
            port = input_item["port"]
            interval = input_item["interval"]

            _LOGGER.info(f"Nutanix PC Stream event started: {ip},{username},{password},{input_name},{port}")
            try:
                #Create session and mask password if hasn't done already
                session_key = self._input_definition.metadata["session_key"]
                module_Name, _ = inputs.inputs.popitem()
                service = client.connect(**{'token': session_key})
                realm = "%s-%s" %(module_Name, ip) #Unique password storage key
                _LOGGER.info(f"password: {password}")
                if password != self.MASK:
                    self.save_password(service, username, password, realm, _LOGGER)
                    self.mask_password(service, username, module_Name, _LOGGER)
                else:
                    password = self.get_password(service, username, realm, _LOGGER)
                _LOGGER.info('Accessing Nutanix Rest API for cluster data using Username:{},IP:{},Ports:{}'.format(username, ip, port))


                # Creating a session
                endpoint = 'https://%s:%s/api/' % (ip, port)
                
                #create nutanix api processor object
                api_processor = NutanixApiProcessor(endpoint, username, password, _LOGGER,)

                fetchers = [
                    ClustersFetcher,
                    PrismCentralsFetcher,
                    HostsFetcher,
                    VMsFetcher,
                    DisksFetcher,
                    StorageContainersFetcher,
                    VolumeGroupsFetcher,
                    FileServersFetcher,
                    HostNICsFetcher
                ]

                AlertsFetcher(api_processor, ew, input_name, service, interval, ip).fetch_and_write_event()
                EventsFetcher(api_processor, ew, input_name, service, interval, ip).fetch_and_write_event()

                for fetcher_cls in fetchers:
                    fetcher_cls(api_processor, ew, input_name, service, ip).fetch_and_write_event()

            except Exception as e:
                _LOGGER.error( f"Failed to fetch data from Nutanix Prism Central: {str(e)}")

if __name__ == "__main__":
    sys.exit(NutanixPrismCentralDiscovery().run(sys.argv))