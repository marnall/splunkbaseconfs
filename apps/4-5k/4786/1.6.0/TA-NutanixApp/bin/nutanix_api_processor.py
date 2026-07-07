import sys
import json
import time
from datetime import datetime
import pytz
import tzlocal
import requests
import re
requests.packages.urllib3.disable_warnings

class NutanixApiProcessor:

    def __init__(self, endpoint, username, password, ew):
        self.endpoint = endpoint
        self.ew = ew
        self.request = requests.Session()
        self.request.auth = (username, password)
        self.request.headers.update({'Content-Type': 'application/json; charset=utf-8'})
        
    def make_api_call(self, url, param={}):    
        """The method called to fetch data from rest api
            :param url: url to make get request call
            """

        dataset = self.request.get(url, params=param, verify=False)
        if dataset.status_code == 200:
            return dataset.json()
        elif dataset.status_code == 401 or dataset.status_code == 403:
            self.ew.log('ERROR',
                'The Nutanix Prism API username and/password is incorrect or unauthorized for API access. A status code of %s was returned.' % dataset.status_code)
        else:
            self.ew.log('ERROR', 'Splunk was unable to retrieve data from the Nutanix Prism API: %s' % url)
            self.ew.log('ERROR', 'A status code of %s was returned. Message: %s' % (dataset.status_code , dataset.json()["message"]))
        
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
            "vg": endpoint + version2 + "/volume_groups/"
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
            """
            
        affected_entities = {}
        for affected_entity in entities:
            entity_type = affected_entity["entity_type"]
            if entity_type == "cluster" and cluster_metadata["IS_PC-PE"] == False:
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



        