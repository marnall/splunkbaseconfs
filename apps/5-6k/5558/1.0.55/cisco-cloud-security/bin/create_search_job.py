# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath, join
sys.path.append(dirname(abspath(__file__)))

import json
import splunklib.client as client
from splunk.persistconn.application import PersistentServerConnectionApplication
if sys.version_info.major == 3:
    from six.moves.configparser import RawConfigParser
else:
    from configparser import RawConfigParser    
from logger import Logger
from validator import cummulative_validator, get_host
from common import Common
from string import Template
from datetime import datetime, timedelta
from service.app_kvstore_service import KVStoreService
from global_org_client import GlobalOrgClient

s3_indexes = None
appdiscovery_index = None
investigate_settings = None
cloudlock_index = None
dict_to_be_replaced ={}

class CreateSearchJob(PersistentServerConnectionApplication):
    """
    Handles the creation of search jobs for various queries in the Cisco Cloud Security application.
    """

    def __init__(self, command_line, command_arg):
        """
        Initializes the CreateSearchJob class.

        Args:
            command_line (str): Command line arguments.
            command_arg (str): Command arguments.
        """
        PersistentServerConnectionApplication.__init__(self)
        self.global_org_client = None

    def spl_dict(self, query):
        """
        Retrieves a dictionary of queries from the configuration file.

        Args:
            query (str): The query key to retrieve.

        Returns:
            dict: A dictionary containing the query configuration.
        """
        config = RawConfigParser()
        config.read(join(Common().ini_path, "splunkspls.ini"))
        return (dict(config.items("queries")))[query]
    
    def format_query(self, data, in_index, index_name, session_token):
        """
        Formats and dispatches a query based on the provided data and index configuration.

        Args:
            data (dict): Dictionary containing query parameters, including the 'query' key.
            in_index (str): The internal index identifier to be resolved.
            index_name (str): The name of the index to be used (e.g., 'RAVPN', 'DLP', 'PrivateResource').
            session_token (str): Session token for authentication and authorization.

        Returns:
            str: The formatted query string or the result of the corresponding handler method.

        Raises:
            Exception: If the index is not configured or if an error occurs during query formatting.
        """
        try:
            query = data['query']
            in_index_value = self.get_index(in_index, session_token)
            
            if  not in_index_value:
                raise Exception(f'{index_name} index is not configured')
                     
            if index_name=='RAVPN':
                if query == 'totalravpneventcount':
                    return self.handle_total_event_count(query, data, in_index_value)
                elif query == 'ravpneventpaginated':
                    return self.handle_event_paginated(query, data, in_index_value)
            elif index_name=='DLP':
                if query == 'totaldlpeventcount':
                    return self.handle_total_event_count(query, data, in_index_value)
                elif query == 'dlpeventpaginated':
                    return self.handle_event_paginated(query, data, in_index_value) 
            elif index_name=='PrivateResource':
                if query == 'privateresourceidscount':
                    return self.handle_total_event_count(query, data, in_index_value)
                elif query == 'privateresourceids':
                    return self.handle_event_paginated(query, data, in_index_value)
        except Exception as e:
            Logger().info("API: create_search_job, Exception : {0}".format(str(e)))
            raise Exception(e)
     
    def get_index(self, index, session_token):
        """
        Retrieves the latest record for a given index from either an S3 index or a standard KV store collection.

        Args:
            index (str): The name of the index or KV store collection to query.
            session_token (str): The session token used for authentication with the KV store service.

        Returns:
            dict or None: The latest record associated with the specified index, or None if no records are found.
        """
        global s3_indexes
        if self._is_s3_index(index):
            if s3_indexes is None:
                s3_indexes= KVStoreService('s3_indexes', session_token)
            s3_indexes_lastRecord = json.loads(s3_indexes.query_items('s3_indexes', session_token))
            if len(s3_indexes_lastRecord) == 0:
                return None
            if s3_indexes_lastRecord[-1].get(index) is not None:
                return s3_indexes_lastRecord[-1].get(index)
        else: 
            records_service = KVStoreService(index, session_token)
            collection_records = json.loads(records_service.query_items(index, session_token))
            return collection_records[-1].get('index')
        return None

    def handle_total_event_count(self, query, data, index_value):
        """
        Constructs and formats a search query for retrieving the total event count.

        Args:
            query (str): The query template string containing placeholders for substitution.
            data (dict): A dictionary containing search parameters, specifically the 'search_param' key.
            index_value (str): The value to substitute for the 'index_val' placeholder in the query.

        Returns:
            str: The formatted search query with substituted values.

        Raises:
            Exception: If the provided query is empty or None.
        """
        global dict_to_be_replaced
        search_query = 'search'
        if data['search_param']:
            search_query = self.build_search_query(data['search_param'])
        query_name = query  # Store the original query name
        query = self.spl_dict(query)
        if not query:
            raise Exception('Query does not exist')
        s = Template(query)
        dict_to_be_replaced = {'index_val': index_value, 'search_query': search_query}
        if query_name in ("privateresourceidscount", "totalravpneventcount", "totaldlpeventcount"):
            dict_to_be_replaced.update({
                "org_id": self.global_org_client.global_org
            })
        formatted_query = s.substitute(dict_to_be_replaced)
        return formatted_query

    def handle_event_paginated(self, query, data, index_value):
        """
        Constructs and formats a paginated search query.

        Args:
            query (str): The query template string containing placeholders for substitution.
            data (dict): A dictionary containing search parameters, including pagination details.
            index_value (str): The value to substitute for the 'index_val' placeholder in the query.

        Returns:
            str: The formatted paginated search query.
        """
        global dict_to_be_replaced
        sort_field, search_query, limit, page_no = self.initialize_paginated_query(data)
        event_upto = limit * page_no
        event_from = event_upto - limit
        query_name = query  # Store the original query name
        query = self.spl_dict(query)
        s = Template(query)
        dict_to_be_replaced = {
            'index_val': index_value,
            'event_from': event_from,
            'event_upto': event_upto,
            'search_query': search_query,
        } 
        if query != "privateresourceids":
            dict_to_be_replaced['sort_field'] = sort_field
        if query_name in ("privateresourceids", "ravpneventpaginated", "dlpeventpaginated"):
            dict_to_be_replaced.update({
                "org_id": self.global_org_client.global_org
            })
        formatted_query = s.substitute(dict_to_be_replaced)
        return formatted_query

    def initialize_paginated_query(self, data):
        """
        Initializes parameters for a paginated query.

        Args:
            data (dict): A dictionary containing pagination details.

        Returns:
            tuple: A tuple containing sort_field, search_query, limit, and page_no.
        """
        sort_field = 'sort -Timestamp'
        search_query = 'search'
        limit = 20
        page_no = 1

        if data['search_param']:
            search_query = self.build_search_query(data['search_param']) 
        if data['sort']:
            sort_field = self.determine_sort_field(data['sort'])
        if data['limit']:
            limit = data['limit']
        if data['page_no']:
            page_no = data['page_no']
        return sort_field, search_query, limit, page_no
    
    def build_search_query(self, search_param):
        """
        Builds a search query string based on the provided search parameters.

        Args:
            search_param (str): The search parameter string.

        Returns:
            str: The constructed search query string.
        """
        search_terms = search_param.split('=')
        search_value = search_terms[1] + '*'
        search_param = f'{search_terms[0]}="{search_value}"'
        search_query = f'search {search_param}'
        return search_query
    
    def determine_sort_field(self, sort_option):
        """
        Determines the sort field based on the provided sort option.

        Args:
            sort_option (str): The sort option string.

        Returns:
            str: The sort field string.
        """
        if sort_option == 'event_type':
            return 'eval severity_rank = case(event_type == "CONNECTED", 1, event_type == "DISCONNECTED", 2, event_type == "FAILED", 3) | sort severity_rank'
        elif sort_option == '-event_type':
            return 'eval severity_rank = case(event_type == "CONNECTED", 1, event_type == "DISCONNECTED", 2, event_type == "FAILED", 3) | sort -severity_rank'
        elif sort_option == 'severity':
            return  'eval severity_rank = case(severity == "CRITICAL", 1, severity == "WARNING", 2, severity == "INFO", 3) | sort severity_rank'
        elif sort_option == '-severity':
            return 'eval severity_rank = case(severity == "CRITICAL", 1, severity == "WARNING", 2, severity == "INFO", 3) | sort -severity_rank'
        else:
            return f'sort {sort_option}'
        
    def query_formatter(self, q1, date1, date2):
        """
        Formats a query with date and time placeholders.

        Args:
            q1 (str): The query template string.
            date1 (str): The start date in ISO format.
            date2 (str): The end date in ISO format.

        Returns:
            str: The formatted query string.
        """
        dt_obj1 = datetime.strptime(date1, "%Y-%m-%dT%H:%M:%S")
        dt_obj2 = datetime.strptime(date2, "%Y-%m-%dT%H:%M:%S")
        diff = dt_obj2 - dt_obj1
        diff_in_seconds = int(diff.total_seconds())
        if 'tail' not in q1:
            diff_in_seconds = diff_in_seconds//10
        dt_obj0 = dt_obj1 - timedelta(days=diff.days,seconds=diff.seconds)
        dt_str0 = datetime.strftime(dt_obj0, "%m/%d/%Y:%H:%M:%S")
        second_earliest_value = datetime.strftime(datetime.strptime(date1, "%Y-%m-%dT%H:%M:%S"), "%m/%d/%Y:%H:%M:%S")
        second_latest_value = datetime.strftime(datetime.strptime(date2, "%Y-%m-%dT%H:%M:%S"), "%m/%d/%Y:%H:%M:%S")
        dict_value_replaced = {}
        dict_value_replaced.update(
            {'first_earliest_value': dt_str0, 'first_latest_value': second_earliest_value,
             'second_earliest_value': second_earliest_value, 'second_latest_value': second_latest_value,
             'index_val': '$index_val','span':str(diff_in_seconds)+'s'})
        if "$org_id" in q1:
            dict_value_replaced.update({'org_id': self.global_org_client.global_org})
        s = Template(q1)
        q2 = s.substitute(dict_value_replaced)
        return q2
    
    def sourcetype_getter(self, query):
        """
        Extracts sourcetypes from a query string.

        Args:
            query (str): The query string.

        Returns:
            list: A list of sourcetypes extracted from the query.
        """
        import re
        list_req = []
        match = re.findall('sourcetype=(\S+)', query)
        for m in match:
            list_req.append(m.split(':')[-1])
        return list_req

    def index_source_type_embedder(self, query, session_token):
        """
        Embeds index and sourcetype information into a query.

        Args:
            query (str): The query string.
            session_token (str): The session token for authentication.

        Returns:
            str: The query string with embedded index and sourcetype information.
        """
        list_sourcetypes = [str(i) for i in self.sourcetype_getter(query)]
        list_ind = []
        dict_to_be_replaced = {}
        index_string = 'index='
        index_val = None
        for st in list_sourcetypes:
            if st=='incident':
                continue
            elif st=='cloudlock':
                global cloudlock_index
                if cloudlock_index is None:
                    cloudlock_index = KVStoreService('cloudlock_index', session_token)
                cloudlock_index_data = json.loads(cloudlock_index.query_items('cloudlock_index', session_token))
                if len(cloudlock_index_data) != 0:
                    cloudlock_index_lastRecord = cloudlock_index_data[-1]
                    index_val = cloudlock_index_lastRecord['index']

            elif st=='appdiscovery':
                global appdiscovery_index
                if appdiscovery_index is None:
                    appdiscovery_index = KVStoreService('appdiscovery_index', session_token)
                appdiscovery_index_data = json.loads(appdiscovery_index.query_items('appdiscovery_index', session_token, {
                    "orgId": self.global_org_client.global_org
                }))
                if len(appdiscovery_index_data) != 0:
                    appdiscovery_index_lastRecord = appdiscovery_index_data[-1]
                    index_val = appdiscovery_index_lastRecord['index']
                else:
                    raise Exception("Index for app discovery is not configured.")

            elif st=='investigated':
                global investigate_settings
                if investigate_settings is None:
                    investigate_settings = KVStoreService('investigate_settings', session_token)
                investigate_settings_data = json.loads(
                    investigate_settings.query_items('investigate_settings', session_token, {
                    "orgId": self.global_org_client.global_org
                }))
                if len(investigate_settings_data) == 0:
                    raise Exception('Investigate index is not configured')
                for obj in investigate_settings_data:
                    if obj['status'] == 'active':
                        index_val = obj['index']
                        break
                if not index_val:
                    raise Exception('Investigate index is not configured')
            else:
                global s3_indexes
                if not s3_indexes:
                    s3_indexes = KVStoreService('s3_indexes', session_token)
                s3_indexes_lastRecord = json.loads(s3_indexes.query_items('s3_indexes', session_token, {
                    "orgId": self.global_org_client.global_org
                }))
                if not s3_indexes_lastRecord:
                    raise Exception('S3 indexes not configured')
                s3_indexes_lastRecord = s3_indexes_lastRecord[-1]
                index_val = s3_indexes_lastRecord[st+'_index']

            if index_val not in list_ind:
                if index_val is None:
                    raise Exception('Index is not selected for sourcetype {0}'.format(index_val))
                index_string = index_string + index_val + ' OR index='
                list_ind.append(index_val)

        val = index_string.rsplit(' ', 2)
        
        dict_to_be_replaced.update({'index_val': val[0]})
        s = Template(query)
        formatted_query = s.substitute(dict_to_be_replaced)
        return formatted_query
    
    def _validate_timestamps(self, from_timestamp: str, to_timestamp: str) -> bool:
        """
        Validates that both timestamps are provided and not empty.

        Args:
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.

        Returns:
            bool: True if both timestamps are valid, False otherwise.
        """
        return bool(from_timestamp and to_timestamp)
    
    def _convert_timestamp(self, timestamp: str) -> str:
        """
        Converts a timestamp from milliseconds to seconds.

        Args:
            timestamp (str): The timestamp in milliseconds.

        Returns:
            str: The timestamp in seconds.
        """
        return str(int(timestamp) / 1000)

    def _is_s3_index(self, index: str) -> bool:
        """
        Checks if the given index is an S3 index.

        Args:
            index (str): The index name.

        Returns:
            bool: True if the index is an S3 index, False otherwise.
        """
        return index in ["dns_index", "proxy_index", "firewall_index", "dlp_index", "ravpn_index"]
    
    def handle(self, in_string):
        """
        Handles the incoming request and processes the query.

        Args:
            in_string (str): The input string containing request parameters.

        Returns:
            dict: A dictionary containing the response payload and status.
        """
        try:
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            Logger().info(f"API: create_search_job, Host: {host}")
            self.global_org_client = GlobalOrgClient(session_token)
            service = client.connect(host=host,
                                     token=session_token,
                                     app="cisco-cloud-security")
            data = json.loads(params['payload'])['data']
            if data['query'] == 'totaldlpeventcount' or data['query'] == 'dlpeventpaginated':
                from_timestamp = data.get("from", "")
                to_timestamp = data.get("to", "")
                if not self._validate_timestamps(from_timestamp, to_timestamp):
                    raise Exception(f"Both 'from' and 'to' timestamps must be provided and cannot be empty.")
                formatted_query = self.format_query(data, 'dlp_index', 'DLP', session_token)
                kwargs = {"search_mode": "normal", "exec_mode": "normal", "earliest_time": self._convert_timestamp(from_timestamp), "latest_time": self._convert_timestamp(to_timestamp)}
                Logger().info(f"API: create_search_job, Formatted Query : {formatted_query}")
                Logger().info(f"API: create_search_job, Kwargs : {kwargs}")
                job = service.jobs.create(formatted_query,**kwargs)
                return {'payload': job.sid, 'status': 200}
            elif data['query'] == 'totalravpneventcount' or data['query'] == 'ravpneventpaginated':
                from_timestamp = data.get("from", "")
                to_timestamp = data.get("to", "")
                if not self._validate_timestamps(from_timestamp, to_timestamp):
                    raise Exception(f"Both 'from' and 'to' timestamps must be provided and cannot be empty.")
                formatted_query = self.format_query(data, 'ravpn_index', 'RAVPN', session_token)
                kwargs = {"search_mode": "normal", "exec_mode": "normal", "earliest_time": self._convert_timestamp(from_timestamp), "latest_time": self._convert_timestamp(to_timestamp)}
                Logger().info(f"API: create_search_job, Formatted Query : {formatted_query}")
                Logger().info(f"API: create_search_job, Kwargs : {kwargs}")
                job = service.jobs.create(formatted_query,**kwargs)
                return {'payload': job.sid, 'status': 200}
            elif data['query'] == 'privateresourceidscount' or data['query'] == 'privateresourceids':
                from_timestamp = data.get("from", "")
                to_timestamp = data.get("to", "")
                if not self._validate_timestamps(from_timestamp, to_timestamp):
                    raise Exception(f"Both 'from' and 'to' timestamps must be provided and cannot be empty.")
                formatted_query = self.format_query(data, 'privateapp_index', 'PrivateResource', session_token)
                kwargs = {"search_mode": "normal", "exec_mode": "normal", "earliest_time": self._convert_timestamp(from_timestamp), "latest_time": self._convert_timestamp(to_timestamp)}
                Logger().info(f"API: create_search_job, Formatted Query : {formatted_query}")
                Logger().info(f"API: create_search_job, Kwargs : {kwargs}")
                job = service.jobs.create(formatted_query,**kwargs)
                return {'payload': job.sid, 'status': 200}
            query = self.spl_dict(data['query'])
            if not query:
                raise Exception('Query does not exists')
            if not cummulative_validator(data['query']):
                raise Exception('Query name validation failed')
            if not cummulative_validator(data['earliest_time']):
                raise Exception('Earliest time validation failed')
            if not cummulative_validator(data['latest_time']):
                raise Exception('Latest time validation failed')
            date1 = data['earliest_time']#.replace('Z','')
            date2 = data['latest_time']#.replace('Z','')
            query_formatted = self.query_formatter(query,date1,date2)
            query_formatted2 = self.index_source_type_embedder(query_formatted, session_token)
            Logger().info(f"API: create_search_job, Formatted Query : {query_formatted2}")
            job = service.jobs.create(query_formatted2,**{"search_mode": "normal", "exec_mode": "normal"})
            return {'payload': job.sid, 'status': 200}
        except Exception as e:
            Logger().error("API: create_search_job, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
