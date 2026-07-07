# encoding = utf-8
from __future__ import print_function

import sys
import math
import json
import time
from datetime import datetime
from pytz import timezone
from os.path import dirname, abspath
import os
sys.path.append(dirname(abspath(__file__)))
import os
import splunk.rest as rest
import splunk
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from exceptions import ReportingAPIClientException, PrivateResourcesAPIClientException
from enums import PrivateResourcesEndpoints
from reporting_api_client import ReportingAPIClient
from service.app_kvstore_service import KVStoreService
from typing import Dict, List
from global_org_client import GlobalOrgClient

sys.path.append(dirname(abspath(__file__)))

class PrivateResourcesAPIClient(PersistentServerConnectionApplication):
    """The class responsible for handling HTTP requests for the private resources dashboard."""

    def __init__(self, command_line, command_arg):
        """
        Initializes the PrivateResourcesAPIClient class.

        Args:
            command_line (str): Command line arguments.
            command_arg (str): Command arguments.
        """
        PersistentServerConnectionApplication.__init__(self)
        self.reporting_api_client = None
        self.session_token = None
        self.org_id = None

    def handle(self, in_string):
        """
        Handles the components of the private resources dashboard.

        This method processes requests for different components of the private resources dashboard.
        The components are determined by the `request_for` query parameter.

        Args:
            in_string (str): The input string containing the request details.

        Returns:
            dict: The appropriate response based on the `request_for` parameter.

        Raises:
            ValueError: If the `request_for` parameter is missing or invalid.
            ReportingAPIClientException: If an error occurs in the reporting API client.
            Exception: For any other unexpected errors.
        """

        try:
            params = Common().parse_in_string(in_string)
            self.session_token = params["session"]["authtoken"]
            self.org_id = params.get("query", {}).get("orgId") or GlobalOrgClient(
                self.session_token
            ).global_org
            self.reporting_api_client = ReportingAPIClient(self.session_token, org_id=self.org_id)
            request_for = params.get("query", {}).get("request_for", "")
            if not request_for:
                raise ValueError("Missing 'request_for' parameter")
            query = params.get("query")
            if request_for == "panel":
                return self._process_panel_request(query)
            elif request_for == "table":
                return self._process_table_request(query)
            elif request_for == "modal":
                return self._process_modal_request(query)
            else:
                raise ValueError("Invalid 'request_for' value")

        except ReportingAPIClientException as e:
            Logger().error(
                "PrivateResourcesAPIClient: handle: reporting_api_client, Exception: {0}".format(
                    str(e)
                )
            )
            if e.error_code == 429:
                error_msg = 'Please Click on the Refresh Button to Retry this Request.'
                return {"payload": {"error_msg": error_msg}, "status": e.error_code}
            Logger().error("API: reporting_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            Logger().error(
                "PrivateResourcesAPIClient: handle: Exception: {0}".format(str(e))
            )
            return {"payload": {"error_msg": str(e)}, "status": 500}

    def _process_panel_request(self, request_query: Dict) -> Dict:
        """
        Processes requests for the general overview panel.

        Args:
            request_query (Dict): The query parameters for the request.

        Returns:
            Dict: The response payload for the panel request.

        Raises:
            PrivateResourcesAPIClientException: If required query parameters are missing.
        """
        from_timestamp = request_query.get("from", "")
        to_timestamp = request_query.get("to", "")
        if not from_timestamp:
            raise PrivateResourcesAPIClientException(
                error_code=400, error_msg="'from' query parameter is required"
            )
        if not to_timestamp:
            raise PrivateResourcesAPIClientException(
                error_code=400, error_msg="'to' query parameter is required"
            )
        response = {}
        tz = self._fetch_timezone()
        timerange_header = {
            "timerange": self._get_timerange_header_value(from_timestamp, to_timestamp)
        }
        applications_accessed = self._get_applications_accessed(
            from_timestamp, to_timestamp, tz, timerange_header
        )
        # user_indentities_accessed = self._get_user_identities_accessed(
        #     from_timestamp, to_timestamp, tz, timerange_header
        # )
        timerange_data = self._get_timerange_data(
            from_timestamp, to_timestamp, tz, timerange_header
        )
        response.update(
            {
                "prapplications": applications_accessed,
                #"prusers": user_indentities_accessed,
                "prtimelinechart": timerange_data.get("timerange", [{}]),
                "prallowed": timerange_data.get("allowed", 0),
                "prblocked": timerange_data.get("blocked", 0),
            }
        )
        return {"status": 200, "payload": response}

    def _get_applications_accessed(self, from_timestamp: str, to_timestamp: str, timezone: str, timerange_header: Dict):
        """
        Retrieves the count of unique applications accessed within the specified time range.

        Args:
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            timezone (str): The timezone for the request.
            timerange_header (Dict): Additional headers for the request.

        Returns:
            int: The count of unique applications accessed.
        """
        request_path = PrivateResourcesEndpoints.UNIQUE_RESOURCES.value.format(
            from_timestamp, to_timestamp, timezone
        )
        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )        
        result = response.json()        
        return result.get("data", {}).get("count", 0)

    def _get_top_resource_accessed(self, from_timestamp: str, to_timestamp: str, limit: int, offset: int, timezone: str, timerange_header: Dict):
        """
        Retrieves the top resources accessed within the specified time range.

        Args:
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            limit (int): The maximum number of results to retrieve.
            offset (int): The offset for pagination.
            timezone (str): The timezone for the request.
            timerange_header (Dict): Additional headers for the request.

        Returns:
            list: A list of dictionaries containing resource details.
        """
        request_path = PrivateResourcesEndpoints.TOP_RESOURCES.value.format(
            from_timestamp, to_timestamp, limit, offset, timezone
        )

        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )

        top_resource_res = response.json()
        top_res = []

        for item in top_resource_res.get("data",[]):
            top_res_dict = { }
            application = item.get("application", {})
            if "id" in application and "label" in application:
                top_res_dict.update({
                    "privateresourceid": application.get("id", 0),
                    "name": application.get("label","")
                })
                top_res.append(top_res_dict)
        return top_res

    def _get_user_identities_accessed(self, from_timestamp: str, to_timestamp: str, timezone: str, timerange_header: Dict):
        """
        Retrieves the count of unique user identities accessed within the specified time range.

        Args:
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            timezone (str): The timezone for the request.
            timerange_header (Dict): Additional headers for the request.

        Returns:
            int: The count of unique user identities accessed.
        """
        request_path = PrivateResourcesEndpoints.UNIQUE_IDENTITIES.value.format(
            from_timestamp, to_timestamp, timezone
        )
        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )
        result = response.json()
        return result.get("data", {}).get("count", 0)

    def _get_summary_status_accessed(self, top_resource_response: Dict, from_timestamp: str, to_timestamp: str, limit: int, offset: int, timezone: str, timerange_header: Dict):
        """
        Retrieves summary status information for the top resources accessed.

        Args:
            top_resource_response (Dict): The response containing top resource details.
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            limit (int): The maximum number of results to retrieve.
            offset (int): The offset for pagination.
            timezone (str): The timezone for the request.
            timerange_header (Dict): Additional headers for the request.

        Returns:
            list: A list of dictionaries containing summary status details.
        """
        resp = []
        # Extract privateresourceid values and convert them to strings
        privateresource_id_values = [str(item["privateresourceid"]) for item in top_resource_response]
        # Join the values with a comma and a space
        private_resource_ids = ",".join(privateresource_id_values)
        request_params = {
            "privateresourceids": private_resource_ids
        }      
        request_path = PrivateResourcesEndpoints.SUMMARY_STATS.value.format(
            from_timestamp, to_timestamp, limit, offset, timezone
        )        
        response = self._send_request(
            path=request_path, additional_headers=timerange_header, params=request_params
        )
        result = response.json()
        resp = result.get("data",[])
        return resp

    def _get_timerange_data(self, from_timestamp: str, to_timestamp: str, timezone: str, timerange_header: Dict):
        """
        Retrieves data for requests grouped by time range.

        Args:
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            timezone (str): The timezone for the request.
            timerange_header (Dict): Additional headers for the request.

        Returns:
            dict: A dictionary containing allowed and blocked request counts and timerange data.
        """
        request_path = PrivateResourcesEndpoints.REQUESTS_BY_TIME_RANGE.value.format(
            from_timestamp, to_timestamp, timezone
        )
        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )

        result = response.json()
        output = {}
        data = result.get("data", [{}])
        allowed_requests = self._calculate_total_requests(data, key="allowedrequests")
        blocked_requests = self._calculate_total_requests(data, key="blockedrequests")

        timerange_data = []
        for item in data:
            timerange_data.append(
                {
                    "label": item["date"] + " " + item["time"],
                    "value1": item["counts"]["allowedrequests"],
                    "value2": item["counts"]["blockedrequests"],
                }
            )

        output.update({
            "allowed": allowed_requests,
            "blocked": blocked_requests,
            "timerange": timerange_data
        })        
        return output

    def _get_detailed_status_timerange_accessed(self, top_resource_response: Dict, from_timestamp: str, to_timestamp: str, timezone: str, timerange_header: Dict):
        """
        Retrieves detailed status information for resources accessed within the specified time range.

        Args:
            top_resource_response (Dict): The response containing top resource details.
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            timezone (str): The timezone for the request.
            timerange_header (Dict): Additional headers for the request.

        Returns:
            list: A list of dictionaries containing detailed status information.
        """

        resp = []
        privateresourceids = [item.get("privateresourceid",0) for item in top_resource_response] 
        for privateresourceid in privateresourceids:
            if privateresourceid:
                new_json={}
                request_path = PrivateResourcesEndpoints.DETAILED_STATS_TIMERANGE.value.format(
                    from_timestamp, to_timestamp, privateresourceid, timezone
                )

                response = self._send_request(
                    path=request_path, additional_headers=timerange_header
                )
                result = response.json()
                # Extract the desired data
                privateresourceid = result.get("data",{}).get("privateresourceid",0)
                totalHitsCount = result.get("data",{}).get("totalHitsCount",0)

                # Create a new JSON object with the extracted data
                new_json.update({"privateresourceid": privateresourceid, "totalHitsCount": totalHitsCount})
                resp.append(new_json) 
        return resp

    def _get_private_resource_table_response(self, top_resource_response, summary_status_response, detailed_status_timerange_response):
        """
        Combines data from multiple sources to create a response for the private resource table.

        Args:
            top_resource_response (list): The top resource details.
            summary_status_response (list): The summary status details.
            detailed_status_timerange_response (list): The detailed status details.

        Returns:
            list: A list of dictionaries containing the combined data for the table.
        """
        response = []
        # Create a dictionary for easy lookup of detailed status
        detailed_status_lookup = {item['privateresourceid']: item['totalHitsCount'] for item in detailed_status_timerange_response}

        # Create a dictionary for easy lookup of summary status
        summary_status_lookup = {item['privateresourceid']: item for item in summary_status_response}

        # Combine the data
        for resource in top_resource_response:
            resource_id = resource['privateresourceid']
            name = resource['name']  
            detailed_status = detailed_status_lookup.get(resource_id, {})
            summary_status = summary_status_lookup.get(resource_id, {})

            response.append({
                'name': name,
                'success': detailed_status.get('success', 0),
                'blocked': detailed_status.get('blocked', 0),
                'accessed': summary_status.get('idscount', 0),
                'total': detailed_status.get('total', 0),
                'id': resource_id
            })
        return response

    def _process_table_request(self, request_query: Dict):
        """
        Processes requests for table data.

        Args:
            request_query (Dict): The query parameters for the request.

        Returns:
            dict: The response payload for the table request.

        Raises:
            PrivateResourcesAPIClientException: If required query parameters are missing or no data is available.
        """

        get_request = request_query.get("query", "")
        response = {}
        from_timestamp = request_query.get("from", "")
        to_timestamp = request_query.get("to", "")

        if not from_timestamp:
            raise PrivateResourcesAPIClientException(
                error_code=400, error_msg="'from' query parameter is required"
            )
        if not to_timestamp:
            raise PrivateResourcesAPIClientException(
                error_code=400, error_msg="'to' query parameter is required"
            )
        timerange_header = {
                "timerange": self._get_timerange_header_value(from_timestamp, to_timestamp)
            }
        tz = self._fetch_timezone()

        if get_request == "getRecCount":
            response = self.get_top_res_count(
                from_timestamp, to_timestamp, timerange_header, tz)
            return {"status": 200, "payload": response}

        elif get_request == "getTableData":
            limit, offset = self._get_pagination_params(request_query)
            response = {}
            top_resource_response = self._get_top_resource_accessed(
                from_timestamp, to_timestamp, limit, offset, tz, timerange_header
            )
            if not top_resource_response:
                raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")

            response = self._call_private_resources_response(top_resource_response,
                from_timestamp, to_timestamp, limit, offset, tz, timerange_header)

        elif get_request == "getSearchData":
            resource_name = request_query.get("resource_name", "")
            limit, offset = self._get_pagination_params(request_query)

            if not resource_name:
                raise PrivateResourcesAPIClientException(
                error_code=400, error_msg="'resource_name' query parameter is required"
            )

            job_result = self._call_create_search_job_data(from_timestamp, to_timestamp, resource_name, request_query)

            if not job_result:
                raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")

            top_resource_resp = [{'privateresourceid': int(item['id']), 'name': item['name']} for item in job_result]
            response = self._call_private_resources_response(top_resource_resp,
                from_timestamp, to_timestamp, limit, offset, tz, timerange_header)

        elif get_request == "getSearchDataCount":
            resource_name = request_query.get("resource_name", "")
            if not resource_name:
                raise PrivateResourcesAPIClientException(
                error_code=400, error_msg="'resource_name' query parameter is required"
            )
            job_result = self._call_create_search_job_data(from_timestamp, to_timestamp, resource_name, request_query)
            if not job_result:
                raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")
            result = job_result[-1].get("value", 0)
            if int(result) == 0:
                raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")
            response = {
                "count": result
            }

        return {"status": 200, "payload": response}

    def _call_create_search_job_data(self, from_timestamp, to_timestamp, resource_name, request_query):
        """
        Creates a search job for retrieving data.

        Args:
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            resource_name (str): The name of the resource.
            request_query (dict): The query parameters for the request.

        Returns:
            dict: The result of the search job.
        """
        get_request = request_query.get("query", "")
        limit, offset = self._get_pagination_params(request_query)
        if get_request == "getSearchDataCount":
            data = {
            "data": {
                    "from" : from_timestamp,
                    "query" : "privateresourceidscount",
                    "search_param" : f"name={resource_name}",
                    "to" : to_timestamp,
                    "sort":""
                }
            }
        elif get_request == "getSearchData":
            data = {
            "data": {
                    "from" : from_timestamp,
                    "query" : "privateresourceids",
                    "search_param" : f"name={resource_name}",
                    "to" : to_timestamp,
                    "limit": limit,
                    "page_no": offset,
                    "sort":""
                }
            }
        else:
            pass
        job_result = self._call_create_search_job_response_data(data)

        return job_result

    def _call_private_resources_response(self, top_resource_response, from_timestamp, to_timestamp, limit, offset, tz, timerange_header):
        """
        Combines data from multiple sources to create a response for private resources.

        Args:
            top_resource_response (list): The top resource details.
            from_timestamp (str): The start timestamp.
            to_timestamp (str): The end timestamp.
            limit (int): The maximum number of results to retrieve.
            offset (int): The offset for pagination.
            tz (str): The timezone for the request.
            timerange_header (dict): Additional headers for the request.

        Returns:
            dict: The combined response data.
        """
        summary_status_response = self._get_summary_status_accessed(top_resource_response,
                from_timestamp, to_timestamp, limit, offset, tz, timerange_header
            )
        detailed_status_timerange_response = self._get_detailed_status_timerange_accessed(top_resource_response,
            from_timestamp, to_timestamp, tz, timerange_header
        )
        response = self._get_private_resource_table_response(top_resource_response,
            summary_status_response,detailed_status_timerange_response
        )

        return response

    def _call_create_search_job(self, data):
        """
        Creates a search job by sending a POST request to the 'create_search_job' endpoint.

        Args:
            data (dict): The payload containing parameters required to create the search job.

        Returns:
            dict: The response from the Splunk endpoint after creating the search job.
        """
        endpoint = "create_search_job"
        return self._call_splunk_endpoint(endpoint, "POST", data)

    def _call_fetch_search_job_status(self, job_id):
        """
        Fetches the status of a search job by its job ID.

        Args:
            job_id (str): The unique identifier of the search job.

        Returns:
            dict: The result of the search job status fetched from the Splunk endpoint.

        Raises:
            PrivateResourcesAPIClientException: If an internal server error occurs while fetching the job status.
        """
        endpoint = f"fetch_search_job_status?s_id={job_id}"
        try:
            result = self._call_splunk_endpoint(endpoint)
        except splunk.InternalServerError as e:
            raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"Something went wrong. Please try your request again")
        return result

    def _call_fetch_search_job_results(self, job_id):
        """
        Fetches the results of a search job from the Splunk endpoint.

        Args:
            job_id (str): The unique identifier of the search job.

        Returns:
            dict: The results returned by the Splunk endpoint for the specified search job.

        Raises:
            Exception: If the request to the Splunk endpoint fails or returns an error.
        """
        endpoint = f"fetch_search_job_results?s_id={job_id}"
        return self._call_splunk_endpoint(endpoint)

    def _call_create_search_job_response_data(self, data):
        """
        Creates a search job, monitors its status, and retrieves the job results.
        This method initiates a search job using the provided data, checks the job's status,
        waits for its completion if necessary, and finally fetches the results. If the job fails,
        is paused, or does not complete successfully, an exception is raised.
        Args:
            data (dict): The data required to create the search job.
        Returns:
            dict: The results of the completed search job.
        Raises:
            PrivateResourcesAPIClientException: If the job cannot be created, fails, is paused,
                or does not complete successfully.
        """
        job_id = self._call_create_search_job(data)
        if not job_id:
            raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")

        job_status = self._call_fetch_search_job_status(job_id)
        if job_status.get("isFailed","") == "1" or job_status.get("isPaused","") == "1":
            raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")
        if job_status.get("isDone","") == "0":
            is_job_completed = self._wait_for_job(job_id)
            if not is_job_completed:
                raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")
        job_result = self._call_fetch_search_job_results(job_id)

        return job_result

    def _wait_for_job(self, job_id: str, wait_interval: float = 0.2, max_wait_time: int = 120):
        """
        Waits for a job to complete by polling its status at regular intervals.

        Args:
            job_id (str): The unique identifier of the job to monitor.
            wait_interval (float, optional): Time in seconds to wait between status checks. Defaults to 0.2.
            max_wait_time (int, optional): Maximum total time in seconds to wait for job completion. Defaults to 120.

        Returns:
            bool: True if the job completes successfully, False if the job fails, is paused, or the maximum wait time is exceeded.
        """
        max_retries = int(max_wait_time / wait_interval)
        retries = 0

        while retries < max_retries:
            status = self._call_fetch_search_job_status(job_id)
            if status['isDone'] == '1':
                return True
            elif status['isFailed'] == '1':
                return False
            elif status['isPaused'] == '1':
                return False
            retries += 1
            time.sleep(wait_interval)

        return False

    def _get_pagination_params(self, request_query, default_limit=20, default_page=0):
        """
        Extracts pagination parameters from a request query.

        Args:
            request_query (dict): Dictionary containing query parameters, typically from a request.
            default_limit (int, optional): Default number of items per page if not specified in the query. Defaults to 20.
            default_page (int, optional): Default page number if not specified in the query. Defaults to 0.

        Returns:
            tuple: A tuple containing:
                - limit (int): The number of items per page.
                - offset (int): The calculated offset based on the page and limit.
        """
        limit = int(request_query.get("limit", default_limit))
        page = int(request_query.get("page", default_page))
        offset = (page - 1) * limit if page > 0 else 0

        return limit, offset

    def _process_modal_request(self, request_query: Dict):
        """
        Processes modal API requests based on the specified endpoint in the request query.
        Supported endpoints:
            - "getResource": Retrieves a private resource by its application ID.
            - "getPrivateAppIdentities": Retrieves identities associated with a private application within a specified time range, with pagination support.
            - "getPrivateAppIdentitiesCount": Retrieves the count of identities associated with a private application within a specified time range.
            - "getPrivateResourceGroup": Retrieves the resource group for a given private application ID.
        Args:
            request_query (Dict): Dictionary containing request parameters, including the "end_point" key to specify the operation.
        Returns:
            dict: A dictionary with "status" (HTTP status code) and "payload" (JSON-encoded response or error message).
        Raises:
            PrivateResourcesAPIClientException: If required query parameters are missing or invalid.
        """
        end_point = request_query.get("end_point", "")

        if end_point == "getResource":
            app_id = int(request_query.get("privateAppId", ""))
            response = self._get_private_resource(app_id)
            json_response = json.dumps(response)
            return {"status": 200, "payload": json_response}

        elif end_point == "getPrivateAppIdentities":
            app_id = request_query.get("privateAppId", "")
            page = int(request_query.get("page", ""))
            from_timestamp = request_query.get("from_timestamp", "")
            to_timestamp = request_query.get("to_timestamp", "")
            limit = int(request_query.get("limit", ""))
            offset = (page-1) * limit
            if not from_timestamp:
                raise PrivateResourcesAPIClientException(
                    error_code=400, error_msg="'from' query parameter is required"
                )
            if not to_timestamp:
                raise PrivateResourcesAPIClientException(
                    error_code=400, error_msg="'to' query parameter is required"
                )
            tz = 'UTC'
            # return {"status": 200, "payload": "json_response"}
            response = self._get_private_app_identities(app_id,
            from_timestamp, to_timestamp, tz, limit, offset
                    )

            final_response = {}
            # count = len(response["data"]["identities"])
            id = response["data"]["privateresourceid"]
            response = response["data"]["identities"]
            final_response.update({"data": response,  "Id": id})
            json_response = json.dumps(final_response)
            return {"status": 200, "payload": json_response}

        elif end_point == "getPrivateAppIdentitiesCount":
            app_id = request_query.get("privateAppId", "")
            page = int(request_query.get("page", ""))
            from_timestamp = request_query.get("from_timestamp", "")
            to_timestamp = request_query.get("to_timestamp", "")
            # limit = int(request_query.get("limit", ""))
            limit = 100
            # offset = (page-1) * limit
            offset = 0
            if not from_timestamp:
                raise PrivateResourcesAPIClientException(
                    error_code=400, error_msg="'from' query parameter is required"
                )
            if not to_timestamp:
                raise PrivateResourcesAPIClientException(
                    error_code=400, error_msg="'to' query parameter is required"
                )
            tz = 'UTC'
            # return {"status": 200, "payload": "json_response"}
            response = self._get_private_app_identities_count(app_id,
            from_timestamp, to_timestamp, tz, limit, offset
                    )

            final_response = {}
            count = len(response["data"]["identities"])
            id = response["data"]["privateresourceid"]
            # response = response["data"]["identities"][offset: offset+limit]
            final_response.update({"count": count, "Id": id})
            json_response = json.dumps(final_response)
            return {"status": 200, "payload": json_response}

        elif end_point == "getPrivateResourceGroup":
            app_id = int(request_query.get("privateAppId", ""))
            response = {}
            response = self._get_private_group_resource(app_id)
            response.update({"app_id": app_id})
            json_response = json.dumps(response)
            return {"status": 200, "payload": json_response}
        return {"status": 404, "payload": {"message": "Endpoint not found"}}

    def _get_private_resource(self, app_id):
        """
        Retrieve a private resource for the specified application ID.

        Args:
            app_id (str): The unique identifier of the application whose private resource is to be retrieved.

        Returns:
            dict: The JSON-decoded response containing the private resource details.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            ValueError: If the response cannot be decoded as JSON.
        """
        request_path = PrivateResourcesEndpoints.PRIVATE_RESOURCE.value.format(app_id)
        response = self._send_request(
            path=request_path
        )
        result = response.json()
        return result

    def _get_private_app_identities(self, app_id, from_timestamp, to_timestamp, tz, limit, offset):
        """
        Retrieves detailed identity statistics for a private app within a specified time range.

        Args:
            app_id (str): The unique identifier of the private app.
            from_timestamp (str): The start of the time range (ISO 8601 format or epoch).
            to_timestamp (str): The end of the time range (ISO 8601 format or epoch).
            tz (str): The timezone to use for the query.
            limit (int): The maximum number of records to return.
            offset (int): The number of records to skip for pagination.

        Returns:
            dict: The JSON response containing detailed identity statistics for the specified app and time range.
        """
        request_path = PrivateResourcesEndpoints.DETAILED_STATS_IDENTITIES.value.format(
            from_timestamp, to_timestamp, app_id, limit, offset, tz
            )
        timerange_header = {
            "timerange": self._get_timerange_header_value(from_timestamp, to_timestamp)
        }
        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )
        result = response.json()
        return result

    def _get_private_app_identities_count(self, app_id, from_timestamp, to_timestamp, tz, limit, offset):
        """
        Retrieves the count of private app identities for a specified application within a given time range.

        Args:
            app_id (str): The unique identifier of the application.
            from_timestamp (str): The start timestamp for the query (ISO 8601 format).
            to_timestamp (str): The end timestamp for the query (ISO 8601 format).
            tz (str): The timezone to be used for the query.
            limit (int): The maximum number of records to return.
            offset (int): The offset for pagination.

        Returns:
            dict: The JSON response containing the count and details of private app identities.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            ValueError: If the response cannot be parsed as JSON.
        """
        request_path = PrivateResourcesEndpoints.DETAILED_STATS_IDENTITIES.value.format(
            from_timestamp, to_timestamp, app_id, limit, offset, tz
            )
        timerange_header = {
            "timerange": self._get_timerange_header_value(from_timestamp, to_timestamp)
        }
        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )
        result = response.json()
        return result

    def _get_private_group_resource(self, app_id):
        """
        Retrieves the private group resource for a given application ID.

        Args:
            app_id (str): The unique identifier of the application whose private group resource is to be fetched.

        Returns:
            dict: The JSON-decoded response containing the private group resource details.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            ValueError: If the response cannot be decoded as JSON.
        """
        request_path = PrivateResourcesEndpoints.PRIVATE_RESOURCE_GROUP.value.format(app_id)
        response = self._send_request(
            path=request_path
        )
        result = response.json()
        return result

    def _get_timerange_header_value(self, from_timestamp: str, to_timestamp: str) -> str:
        """
        Determines the appropriate time range header value based on the difference between two timestamps.

        Args:
            from_timestamp (str): The starting timestamp in milliseconds since epoch, as a string.
            to_timestamp (str): The ending timestamp in milliseconds since epoch, as a string.

        Returns:
            str: Returns "day" if the time range is greater than 24 hours (86400000 ms),
                 "minute" if the time range is less than or equal to 1 hour (3600000 ms),
                 otherwise returns "hour".
        """
        if (int(to_timestamp) - int(from_timestamp)) > 86400000:
            return "day"
        elif (int(to_timestamp) - int(from_timestamp)) <= 3600000:
            return "minute"
        return "hour"

    def _calculate_total_requests(self, data: List[Dict], key: str) -> int:
        """
        Calculates the total number of requests for a specified key from a list of data entries.

        Args:
            data (List[Dict]): A list of dictionaries, each potentially containing a "counts" dictionary.
            key (str): The key within the "counts" dictionary whose values should be summed.

        Returns:
            int: The total sum of the values associated with the specified key across all entries.
        """
        total_requests = sum(entry.get("counts", {}).get(key, 0) for entry in data)
        return total_requests

    def _send_request(self, path, additional_headers=None, params=None):
        """
        Sends a request to the reporting API using the reporting API client.

        Args:
            path (str): The API endpoint path.
            additional_headers (dict, optional): Additional headers for the request.
            params (dict, optional): Query parameters for the request.

        Returns:
            Response: The response object from the API.
        """
        # Default headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CiscoCloudSecurityAppForSplunk/python-requests/3x",
        }

        # If additional headers are provided, merge them with the default headers
        if additional_headers:
            headers.update(additional_headers)

        return self.reporting_api_client.send_request(path, "get", headers=headers, params=params)

    def _fetch_timezone(self):
        """
        Fetches the timezone from the KV store.

        Returns:
            str: The timezone string.
        """
        tz = "UTC"
        oauth_settings = KVStoreService("oauth_settings", self.session_token)
        oauth_settings = json.loads(
            oauth_settings.query_items(
                "oauth_settings",
                self.session_token,
                query_conditions={"status": "active", "orgId": self.org_id},
            )
        )
        if len(oauth_settings) == 0:
            Logger().error("timezone setting not found!")
        else:
            oauth_settings = oauth_settings[-1]
            tz = oauth_settings["timezone"]

        return tz

    def get_top_res_count(self, from_timestamp: str, to_timestamp: str, timerange_header, tz: str):
        """
        Retrieves the count of top resources within a specified time range.
        Args:
            from_timestamp (str): The start timestamp for the query (ISO 8601 format).
            to_timestamp (str): The end timestamp for the query (ISO 8601 format).
            timerange_header: Additional headers to include in the request, typically for time range specification.
            tz (str): Timezone identifier (e.g., 'UTC', 'America/Los_Angeles').
        Returns:
            dict: A dictionary containing the count of top resources, e.g., {"count": 42}.
        Raises:
            PrivateResourcesAPIClientException: If no data is available or an error occurs during the request.
        """
        limit = 5000
        offset = 0
        request_path = PrivateResourcesEndpoints.TOP_RESOURCES.value.format(
            from_timestamp, to_timestamp, limit, offset, tz
        )

        response = self._send_request(
            path=request_path, additional_headers=timerange_header
        )
        resp = response.json()
        value = len(resp.get("data",[]))
        if value == 0:
            raise PrivateResourcesAPIClientException(error_code=500, error_msg=f"No Data Available")
        response = {"count": value} 

        return response

    def _call_splunk_endpoint(self, endpoint, method="GET", data=None):
        """
        Makes a REST API call to a specified Splunk endpoint within the 'cisco-cloud-security' app namespace.

        Args:
            endpoint (str): The relative endpoint path to call within the Splunk app.
            method (str, optional): The HTTP method to use for the request (default is "GET").
            data (dict, optional): The data payload to send with the request, if any.

        Returns:
            dict: The JSON-decoded response content from the Splunk endpoint.

        Raises:
            Any exception raised by rest.simpleRequest when raiseAllErrors is True.
        """
        request_url = f"/servicesNS/nobody/cisco-cloud-security/{endpoint}"
        data = json.dumps(data) if data else None
        _, content = rest.simpleRequest(
            request_url, sessionKey=self.session_token, method=method, raiseAllErrors=True, jsonargs=data
        )
        return json.loads(content)
