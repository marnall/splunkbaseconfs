
import sys
import requests
import traceback
from nutanix_splunk_client import NutanixSplunkClient
from nutanix_api_processor import NutanixApiProcessor
import ta_nutanix_declare
import logger.log as log
from datetime import datetime, timedelta, timezone
import splunklib.client as client
from splunklib.modularinput import *
from pc_performance_fetchers import (
    ClusterPerformanceFetcher,
    HostPerformanceFetcher,
    DiskPerformanceFetcher,
    VMPerformanceFetcher,
    VolumeGroupsStatsFetcher
)


requests.packages.urllib3.disable_warnings()

_LOGGER = log.Logs().get_logger("PCPerformance")
class NutanixPrismCentralPerformance(NutanixSplunkClient):
    
    def build_time_params(self, start_time: int):
        """
        :param start_time: user input in seconds (how far back from now).
                        if 0 -> current time
        :return: dict with startTime and endTime in ISO 8601 UTC format
        """

        # Current UTC time
        now = datetime.now(timezone.utc)

        # Calculate past time
        if start_time > 0:
            past = now - timedelta(seconds=start_time)
        else:
            past = now

        # Convert to ISO 8601 with milliseconds + Z
        def to_iso8601(dt: datetime) -> str:
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        return {
            "$startTime": to_iso8601(past),
            "$endTime": to_iso8601(now),
        }

    def get_scheme(self):
        scheme = Scheme("Nutanix Prism Central Performance")
        scheme.description = "Get the statistics of the Nutanix Prism Central entities and index it into Splunk."
        scheme.use_external_validation = True
        scheme.add_argument(Argument("pc_ip", title="Prism Central IP", required_on_create=True))
        scheme.add_argument(Argument("username", title="Username", required_on_create=True))
        scheme.add_argument(Argument("password", title="Password", ))
        scheme.add_argument(Argument('start_time', title="Start Time", 
                                     description='Start Time is necessary in determining how far back to get the stats.', 
                                     required_on_create=True))
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
                Module_Name = "Nutanix_PrismCentral_Performance://" + definition.metadata.get('name')

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
                    cluster_performance = ClusterPerformanceFetcher(api_processor, None, input_name, service)
                    dataset = cluster_performance.get_clusters_list()
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
            start_Time = int(input_item['start_time'])

            _LOGGER.info(f"Nutanix PC Stream event started: {ip},{username},{password},{input_name},{port}")
            try:
                #Create session and mask password if hasn't done already
                session_key = self._input_definition.metadata["session_key"]
                module_Name, _ = inputs.inputs.popitem()
                service = client.connect(**{'token': session_key})
                realm = "%s-%s" %(module_Name, ip) #Unique password storage key
                if password != self.MASK:
                    self.save_password(service, username, password, realm, _LOGGER)
                    self.mask_password(service, username, module_Name, _LOGGER)
                else:
                    password = self.get_password(service, username, realm, _LOGGER)
                _LOGGER.info('Accessing Nutanix Rest API for cluster data using Username:{},IP:{},Ports:{}'.format(username, ip, port))

                param = self.build_time_params(start_Time)
                _LOGGER.info(f'Performance params: {param}')

                # Creating a session
                endpoint = 'https://%s:%s/api/' % (ip, port)
                
                #create nutanix api processor object
                api_processor = NutanixApiProcessor(endpoint, username, password, _LOGGER,)

                cluster_performance = ClusterPerformanceFetcher(api_processor, ew, input_name, service)
                for cluster in cluster_performance.get_clusters_list():
                    cluster_performance.fetch_and_write_event(ext_id=cluster, param=param)

                hosts_performance = HostPerformanceFetcher(api_processor, ew, input_name, service)
                for ext_id, cl_ext_id  in hosts_performance.get_hosts_data():
                    hosts_performance.fetch_and_write_event(cl_ext_id=cl_ext_id, ext_id=ext_id, param=param)
                
                disks_performance = DiskPerformanceFetcher(api_processor, ew, input_name, service)
                for disk in disks_performance.get_disks_list():
                    disks_performance.fetch_and_write_event(ext_id=disk, param=param)

                vvms_performance = VMPerformanceFetcher(api_processor, ew, input_name, service)
                for vvm in vvms_performance.get_vvms_list():
                    vm_param = dict(param)
                    vm_param.update({
                        "$samplingInterval": 60,
                        "$statType": "AVG",
                        "$select": "*",
                    })
                    vvms_performance.fetch_and_write_event(ext_id=vvm, param=vm_param)

                volume_groups_stats = VolumeGroupsStatsFetcher(api_processor, ew, input_name, service)
                for ext_id in volume_groups_stats.get_volume_groups_data():
                    volume_groups_stats.fetch_and_write_event(ext_id=ext_id, param=param)

            except Exception as e:
                _LOGGER.error( f"Failed to fetch data from Nutanix Prism Central: {str(e)}")

if __name__ == "__main__":
    sys.exit(NutanixPrismCentralPerformance().run(sys.argv))