import ta_expanse_declare
import ipaddress
import json
import re
from datetime import datetime

from six.moves.urllib.parse import quote
from solnlib.splunkenv import get_splunkd_uri

from constants import ALERTS_TIME_FORMAT
from splunk_client import SplunkClient


class KVStore(object):
    """Class to connect to splunk KV store
    Methods:
        update_index - Updates CIDR lookup index
        get_index - Returns data in index
        update_asset_data - Updates IP asset data in KV store
        get_asset_data - Returns IP asset data in KV store
    """

    KV_KEY_PATH = '_key'

    # This is set by Splunk in a conf file
    max_batch_save_size = 1000
    max_batch_data_size = 50 * 1024 * 1024
    max_single_record_size = 16 * 1024 * 1024

    def __init__(self, username, password, splunk_uri=None, input_name='xpanse', splunk_client=None):
        """
        Arguments:
            username {str} -- Username of splunk account
            password {str} -- Password of splunk account

        Keyword Arguments:
            collection {str} -- Name of the KV store collection
                                (default: {None})
        """
        self.__base_url = SplunkClient.get_splunk_base_url(splunk_uri)
        self.__host, self.__port, self.owner, self.__app_name = SplunkClient.parseAppNameFromUrl(self.__base_url)
        self.__splunk_service = splunk_client or SplunkClient(username=username, password=password)
        self.__input_name = input_name

    def create_collection(self, collection):
        """ Create collection if not already present"""
        kvstore_list = self.__splunk_service.list(owner=self.owner, app=self.__app_name)
        collections = [collection.name for collection in kvstore_list]
        if collection not in collections:
            self.__splunk_service.create(collection, owner=self.owner, app=self.__app_name)

    @staticmethod
    def cidr_to_str(cidr):
        """Converts CIDR IP range to string and replaces . with - and / with _

        Arguments:
            cidr {IPRange} -- IPRange object

        Returns:
            str -- string version for CIDR
        """
        return str(cidr).replace('.', '-').replace('/', '_').strip()

    @staticmethod
    def str_to_cidr(string):
        """Converts CIDR string with - and _ to proper notation

        Arguments:
            string {str} -- cidr string with - and _

        Returns:
            str -- string in proper CIDR format
        """
        return string.replace('-', '.').replace('_', '/').strip()

    @staticmethod
    def chunk_data(helper, data, chunk_size, max_data_size, max_single_record_size):
        """Chunks inputs into multiple lists of size {chunk_size} as a generator
            inputs can be lists or generators

        Arguments:
            helper {smi.Script} -- A helper object that controls logging and state
            data {list} -- the list to be chunked
            chunk_size {int} -- the size of each chunk
            max_data_size {int} -- the max size in bytes per chunk
            max_single_record_size {int} -- the max size in bytes per record

        yields:
            lists of the original input in chunk sizes that match the data limits
        """
        chunk_size = int(chunk_size)
        processed_chunks = []
        chunk_len = 0
        for entry in data:
            data_len = len(json.dumps(entry).encode('utf-8'))
            if data_len >= max_single_record_size:
                helper.log_error("One record is larger than the max allowed single record size, unable to chunk")
                continue
            elif data_len + chunk_len > max_data_size:
                yield processed_chunks
                processed_chunks = [entry]
                chunk_len = data_len
            elif len(processed_chunks) == chunk_size:
                yield processed_chunks
                processed_chunks = [entry]
                chunk_len = data_len
            else:
                processed_chunks.append(entry)
                chunk_len = len(json.dumps(processed_chunks).encode('utf-8'))
        if processed_chunks:
            yield processed_chunks

    def trim_registration_info(self, helper, registration_info):
        helper.log_debug("Trimming registration information {}".format(registration_info))
        keys_to_keep = ['handle', 'startAddress', 'endAddress', 'country', 'name', 'updatedDate']
        trimmed_info = []
        for info in registration_info:
            trimmed_info.append({k: v for k, v in info.items() if k in keys_to_keep})
        return trimmed_info

    def update_kv_store_data(self, collection, kv_data, helper):
        """Generic function to update the KV Store for any kind of data it needs

        Arguments:
            collection {str} -- the collection to update
            kv_data {list} -- the data to be inserted into the KV Store
            helper {smi.Script} -- A helper object that controls logging and state

        Returns:
            lists -- save data responses
        """
        chunked_data = self.chunk_data(helper, kv_data, self.max_batch_save_size, self.max_batch_data_size,
                                       self.max_single_record_size)

        responses = []

        collection = self.__splunk_service.get_collection(collection)
        for data in chunked_data:
            items = collection.data.batch_save(*data)
            responses.append(items)

        return responses

    def clear_collection(self, helper, collection, input_name):
        """Deletes the contents of a KV Store collection

        Arguments:
            helper {smi.Script} -- A helper object that controls logging and state
            collection {str} -- The name of the collection to delete
        """

        helper.log_info("About to delete {}".format(collection))
        query = '{"input_name":"' + input_name + '"}'
        response = self.__splunk_service.delete(collection=collection, query=query)
        helper.log_debug("Deleting contents of collection {} For input {}. "
                         "This is generally done before repopulating with updated data".format(collection, input_name))
        if response.status == 200:
            helper.log_debug("Collection {} deleted successfully for input {}".format(collection, input_name))
        else:
            helper.log_warning("Error deleting collection {} on input {}. Status code: {}".format(collection,
                                                                                                  input_name,
                                                                                                  response.status_code))

    @staticmethod
    def get_kv_store_query(input_name):
        return quote('{"input_name":"' + input_name + '"}')

    @staticmethod
    def flatten_json(y):
        out = {}

        def flatten(x, name='', isArray=False):
            # If the Nested key-value
            # pair is of dict type
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_', isArray)

            # If the Nested key-value
            # pair is of list type
            elif type(x) is list:
                for a in x:
                    flatten(a, name, True)
            else:
                key = name[:-1]
                # format all fields relating to time to be in a human readable timestamp
                if type(x) is int and re.search(r'(date|time|after|before|time|observed)', key, flags=re.IGNORECASE):
                    x = datetime.fromtimestamp(x / 1000).strftime(ALERTS_TIME_FORMAT)
                # format all ipv4 fields into a human readable format if they're int
                if type(x) is int and re.search((r'recent_ips_ip'), key, flags=re.IGNORECASE):
                    x = ".".join(map(str, [(x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF]))
                if type(x) is int and re.search(r'ipv6', key, flags=re.IGNORECASE):
                    x = str(ipaddress.IPv6Address(x))
                if isArray:
                    x = [x]
                    if key in out:
                        x = out[key] + x
                out[key] = x

        flatten(y)
        return out
