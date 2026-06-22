import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
import ta_nutanix_declare
import sys
import json
import time
from datetime import datetime
import pytz_deprecation_shim as pytz
import tzlocal
import requests
import uuid
import re
import base64
from urllib.request import Request, urlopen

requests.packages.urllib3.disable_warnings



class NutanixApiProcessor:

    URL_TEMPLATES = {
        "clusters": "clustermgmt/{version}/config/clusters",
        "hosts": "clustermgmt/{version}/config/hosts",
        "vms": "vmm/{version}/ahv/config/vms",
        "disks": "clustermgmt/{version}/config/disks",
        "storage-containers": "clustermgmt/{version}/config/storage-containers",
        "volume-groups": "volumes/{version}/config/volume-groups",
        "file-servers": "files/{version}/config/file-servers",
        "alerts": "monitoring/{version}/serviceability/alerts",
        "events": "monitoring/{version}/serviceability/events",
        "host_nics": "clustermgmt/v4.1/config/host-nics",

        "cluster_performance": "clustermgmt/{version}/stats/clusters/{ext_id}",
        "host_performance": "clustermgmt/{version}/stats/clusters/{cl_ext_id}/hosts/{ext_id}",
        "disk_performance": "clustermgmt/{version}/stats/disks/{ext_id}",
        "vm_performance": "vmm/{version}/ahv/stats/vms/{ext_id}", 
        "volume_groups_stats": "volumes/v4.1/stats/volume-groups/{ext_id}"
    }

    def __init__(self, endpoint, username, password, logger):
        context = self.create_custom_context()
        # Set the security protocol to use like TLSv1, TLSv1.1, and TLSv1.2 so on
        context.options |= ssl.OP_ALL
        # Replace the default HTTPS context with your custom context
        ssl._create_default_https_context = lambda: context
        self.endpoint = endpoint
        self.logger = logger
        self.auth_header = f"Basic {base64.b64encode(f'{username}:{password}'.encode('ascii')).decode('ascii')}"
    
    def make_api_call(self, url, param=None, retries=5, backoff_factor=2):    
        """
        The method called to fetch data from REST API with retry on 429 errors.
        
        :param url: URL to make GET request
        :param param: dict of query parameters
        :param retries: number of retries before failing
        :param backoff_factor: multiplier for sleep time (exponential backoff)
        """
        try:
            if param:
                query_string = urlencode(param, safe=":.-")
                url = f"{url}?{query_string}"
                url = url.replace('%5B', '').replace('%5D', '').replace('%27', "")

            for attempt in range(retries):
                try:
                    request = Request(url)
                    request.headers.update({'Content-Type': 'application/json; charset=utf-8'})
                    request.add_header("Authorization", self.auth_header)

                    with urlopen(request) as response:
                        dataset = json.load(response)
                        if dataset:
                            return dataset
                        else:
                            self.logger.error('Splunk was unable to retrieve data from the API: {}'.format(url))
                            return None

                except HTTPError as e:
                    if e.code == 429 and attempt < retries - 1:
                        wait_time = backoff_factor ** attempt
                        self.logger.info(f"429 Too Many Requests. Retrying in {wait_time}s (attempt {attempt+1}/{retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"HTTPError {e.code} when calling {url}: {e}")
                        return None

                except URLError as e:
                    self.logger.error(f"URLError when calling {url}: {e}")
                    return None

            self.logger.error(f"Failed to fetch data after {retries} retries: {url}")
            return None

        except Exception as e:
            self.logger.error('Splunk was unable to retrieve data from the API: {}, Error: {}'.format(url, e))
            return None

    def get_url(self, entity, ext_id=None, cl_ext_id=None):
        """
        Build a REST API endpoint URL dynamically from templates.
        """
        if entity not in self.URL_TEMPLATES:
            raise ValueError(f"Unknown entity: {entity}")

        template = self.URL_TEMPLATES[entity]
        endpoint = self.endpoint.rstrip("/")
        version = "v4.0"

        try:
            path = template.format(version=version, ext_id=ext_id, cl_ext_id=cl_ext_id)
        except KeyError as e:
            raise ValueError(f"Missing required parameter for {entity}: {e}")

        return f"{endpoint}/{path}"     
        
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
        try:
            if self.validate_uuid(unique_id):
                endpoint_val = "{0}{1}/".format(self.get_url(entity_type), unique_id)
                if cluster_metadata["IS_PC-PE"]:
                    param = {"proxyClusterUuid":cluster_metadata["cluster_uuid"]}
                    rest_result = self.make_api_call(endpoint_val, param)
                else:
                    rest_result = self.make_api_call(endpoint_val)

            if rest_result is None:
                return rest_result
            elif entity_type == "disk":
                return rest_result["mount_path"].split('/')[-1]
            else:
                return rest_result["name"]
        except Exception as e:
            self.logger.error('Splunk was unable to retrieve data from the Nutanix Prism API: {}, API request failed after retries: {}'.format(url,e))
            return None

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
            dataset = self.fetch_with_retry(request)
            if (dataset):
                return dataset
            else:
                self.logger.error('Splunk was unable to retrieve data from the Nutanix Prism API: {}'.format(url))
                return None
        except Exception as e:
            self.logger.error('Splunk was unable to retrieve data from the Nutanix Prism API: {}, API request failed after retries: {}'.format(url,e))
            return None
