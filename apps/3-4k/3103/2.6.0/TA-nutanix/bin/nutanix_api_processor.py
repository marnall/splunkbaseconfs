import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
import ta_nutanix_declare
import sys
import json
import time
from datetime import datetime
import pytz
import tzlocal
import requests
import uuid
import re
import base64
from urllib.request import Request, urlopen

requests.packages.urllib3.disable_warnings

class NutanixApiProcessor:

    def __init__(self, endpoint, username, password, logger):
        context = self.create_custom_context()
        # Set the security protocol to use like TLSv1, TLSv1.1, and TLSv1.2 so on
        context.options |= ssl.OP_ALL
        # Replace the default HTTPS context with your custom context
        ssl._create_default_https_context = lambda: context
        self.endpoint = endpoint
        self.logger = logger
        self.auth_header = f"Basic {base64.b64encode(f'{username}:{password}'.encode('ascii')).decode('ascii')}"


        
    def make_api_call(self, url, param=None):    
        """The method called to fetch data from rest api
            :param url: url to make get request call
        """
        if (param):
            query_string = urlencode(param)
            url = f"{url}?{query_string}"
            url = url.replace('%5B','').replace('%5D','').replace('%27',"")
        
        request = Request(url)
        request.headers.update({'Content-Type': 'application/json; charset=utf-8'})
        request.add_header("Authorization", self.auth_header)
        dataset = json.load(urlopen(request))
        if dataset:
            return dataset
        else:
            self.logger.error('Splunk was unable to retrieve data from the Nutanix Prism API: {}'.format(url))
            #self.logger.error('A status code of {} was returned.'.format(dataset.status))
        
        
    def get_url(self, entity):
        """The method called to get rest api endpoint of entity
            :param entity: name of entity
            """

        endpoint = self.endpoint
        version1 = "v1"
        version2 = "v2.0"
        nutanix_endpoints = {
            "alerts": endpoint + version2 + "/alerts/",
            "events": endpoint + version2 + "/events/",
            "cluster": endpoint + version2 + "/cluster/",
			"clusters": endpoint + version2 + "/clusters/",
            "node": endpoint + version1 + "/hosts/",
            "host": endpoint + version1 + "/hosts/",
            "storage_pool": endpoint + version1 + "/storage_pools/",
            "protection_domain": endpoint + version2 + "/protection_domains/",
            "container": endpoint + version2 + "/storage_containers/",
            "file_server": endpoint + version1 + "/vfilers/",
            "vm": endpoint + version2 + "/vms/",
            "remote_site": endpoint + version2 + "/remote_sites/",
            "disk": endpoint + version2 + "/disks/",
            "vg": endpoint + version2 + "/volume_groups/",
            "vm_health": endpoint + version1 + "/vms/health_check_summary/",
            "host_health": endpoint + version1 + "/hosts/health_check_summary",
            "disk_health": endpoint + version1 + "/disks/health_check_summary",
            "vm_v1": endpoint + version1 + "/vms/",
            "disk_v1": endpoint + version1 + "/disks/",
            "cluster_v1": endpoint + version1 + "/cluster/",
            "fault_tolerance": endpoint + version1 + "/cluster/domain_fault_tolerance_status/",
            "cluster_stats": endpoint + version1 + "/cluster/stats/"
        }
        return nutanix_endpoints[entity] 
        
    def convert_timestamp_to_dateTime_format(self, timestamp):
        
        """The method called to convert timestamp into isoformat
            :param timestamp : time stamp in usecs
            """
        if timestamp==0 or timestamp is None:
            return timestamp
        else:
            data_time = pytz.utc.localize(datetime.utcfromtimestamp(timestamp * 0.000001))
            data_time = data_time.astimezone(tzlocal.get_localzone())
            return data_time.replace(microsecond=0).isoformat()
            
    def get_affected_entities_name(self, entities, cluster_metadata):

        """The method called to get name of affected entities
            :param entities : Dict containing affected_entity dataset
            :param cluster_metadata : cluster details 
            """
            
        affected_entities = {}
        for affected_entity in entities:
            entity_type = affected_entity["entity_type"]
            if entity_type == "cluster":
                affected_entities.update({entity_type: cluster_metadata["cluster_name"]})

            elif entity_type == "remote_site" or entity_type == "protection_domain":
                affected_entities.update({entity_type: affected_entity["uuid"]})

            else:
                entity_name = self.get_affected_entity_name(affected_entity,cluster_metadata)
                affected_entities.update({entity_type: entity_name})
                
        return affected_entities
        
    def get_affected_entity_name(self, affected_entity, cluster_metadata):

        """The method called to get alert entity name
            :param affected_entity: Dict containing affected_entity dataset
            """

        entity_type = affected_entity["entity_type"]
        if affected_entity["entity_name"]:
            return affected_entity["entity_name"]

        elif affected_entity["uuid"]:
            return self.get_entity_name_from_uniqueID(entity_type, affected_entity["uuid"], cluster_metadata)

        else:
            return self.get_entity_name_from_uniqueID(entity_type, affected_entity["id"], cluster_metadata)

    def get_entity_name_from_uniqueID(self, entity_type, unique_id, cluster_metadata):

        """The method called to get alert entity name with Unique entity Id
            :param entity_type: entity_type
            :param unique_id : unique id of the entity
            """
        rest_result= None
        if self.validate_uuid(unique_id):
            endpoint_val = "{0}{1}/".format(self.get_url(entity_type), unique_id)
            if cluster_metadata["IS_PC-PE"]:
                param = {"proxyClusterUuid":cluster_metadata["cluster_uuid"]}
                rest_result = self.make_api_call(endpoint_val, param)
            else:
                rest_result = self.make_api_call(endpoint_val)

        if rest_result is None:
            return None
        elif entity_type == "disk":
            return rest_result["mount_path"].split('/')[-1]
        else:
            return rest_result["name"]

    def validate_uuid(self, uuid_string):
        """The method called to validate if a string is a valid uuid string
            :param uuid_string: uuid of the entity
            """
        try:
            pattern = re.compile(r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')
            return pattern.match(uuid_string)
        except Exception as e:
            return False
    
    def create_custom_context(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    
    def fetch_with_retry(self, request, retries=3, delay=5):
        """
            Fetch data from the API with retry logic.
            
            Args:
                request: The API request object.
                retries: Number of retry attempts.
                delay: Delay (in seconds) between retries.
            
            Returns:
                The parsed JSON dataset.
            
            Raises:
                Exception: If all retries fail.
        """
        for attempt in range(retries):
            try:
                # Attempt to fetch the data
                response = urlopen(request)
                return json.load(response)
            except (URLError, HTTPError) as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)  # Wait before retrying
                else:
                    raise  # Raise the exception if all retries fail
   
    def make_api_call_with_retries(self, url, param=None):    
        """The method called to fetch data from rest api
            :param url: url to make get request call
            """
        if (param):
            query_string = urlencode(param)
            url = f"{url}?{query_string}"
            url = url.replace('%5B','').replace('%5D','').replace('%27',"")
        
        request = Request(url)
        request.headers.update({'Content-Type': 'application/json; charset=utf-8'})
        request.add_header("Authorization", self.auth_header)
        try:
            dataset = self.fetch_with_retry(request, 3, 5)
            if (dataset):
                return dataset
            else:
                self.logger.error('Splunk was unable to retrieve data from the Nutanix Prism API: {}'.format(url))
                return None
        except Exception as e:
            self.logger.error('Splunk was unable to retrieve data from the Nutanix Prism API: {}, API request failed after retries: {}'.format(url,e))


        
     

        
