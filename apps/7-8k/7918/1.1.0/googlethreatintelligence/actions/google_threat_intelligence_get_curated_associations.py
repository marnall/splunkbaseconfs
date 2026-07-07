# File: google_threat_intelligence_get_curated_associations.py
#
# Copyright 2025-2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from urllib.parse import urlencode

import phantom.app as phantom

import google_threat_intelligence_consts as consts
from actions import BaseAction


class GetCuratedAssociations(BaseAction):
    """Class to handle get curated associations action."""

    def execute(self):
        """Execute get curated threat intelligence action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("get_curated_threat_intelligence"))

        query_params = self.__get_query_params()
        entity = self._param["entity"]
        password = self._param.get("password")
        entity_type = self._connector.util.get_data_type(entity)

        self._connector.debug_print(f"Running action {self._connector.get_action_identifier()} with {entity} and entity type {entity_type}.")

        if entity_type == consts.IP_ADDRESS or entity_type == consts.DOMAIN:
            endpoint, method = (
                consts.GET_CURATED_THREAT_INTELLIGENCE_ENDPOINT.format(entity_type=entity_type, entity=entity),
                "get",
            )

        elif entity_type == consts.URL:
            ret_val, url_id = self._connector.util.submit_url_for_analysis(self._action_result, entity)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            endpoint, method = (
                consts.GET_CURATED_THREAT_INTELLIGENCE_ENDPOINT.format(entity_type=entity_type, entity=url_id),
                "get",
            )

        elif entity_type == consts.FILE:
            ret_val, file_id = self._connector.util.get_file_hash_from_input(self._action_result, entity, password)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            endpoint, method = (
                consts.GET_CURATED_THREAT_INTELLIGENCE_ENDPOINT.format(entity_type=entity_type, entity=file_id),
                "get",
            )

        else:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MESSAGE_INVALID_ENTITY)

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self.__check_for_pagination(response, method, entity, entity_type)

        return self.__handle_response(ret_val, response)

    def __check_for_pagination(self, response, method, entity, entity_type):
        """
        Check if pagination is required for a particular relationship and fetch all the data via pagination.

        Args:
            response (dict): The response of the API call.
            endpoint (str): The endpoint of the API call.
            method (str): The HTTP method of the API call.
            entity (str): The entity for which the API call is made.
            entity_type (str): The type of the entity.

        Returns:
            None
        """
        for relationship in ["malware_families", "related_threat_actors", "campaigns", "reports"]:
            # Paginate if cursor exists
            if response.get("data", {}).get("relationships", {}).get(relationship, {}).get("meta", {}).get("cursor", ""):
                # Get query params for particular relationship
                query_params = self.__get_query_params(name=relationship)

                # Fetch all the relationships via pagination
                endpoint = consts.GET_RELATIONSHIP_ENDPOINT.format(entity_type=entity_type, entity=entity, relationship=relationship)
                ret_val, response_relationships = self.__make_rest_call(url=endpoint, method=method, param=query_params, pagination=True)

                if phantom.is_fail(ret_val):
                    return self._action_result.get_status()

                # Replace the data of particular relationship with all the data fetched
                response["data"]["relationships"][relationship]["data"] = response_relationships

    def __get_query_params(self, name=None):
        """
        Get query parameters for the API call.

        Args:
            name (str, optional): The name of the relationship to fetch query parameters for. Defaults to None.

        Returns:
            dict: The query parameters to be sent in the request.
        """
        all_relationships = {
            "malware_families": (
                "name,id,collection_type,description,origin,source_regions_hierarchy,targeted_industries_tree,targeted_regions_hierarchy"
            ),
            "related_threat_actors": (
                "name,id,collection_type,description,origin,source_regions_hierarchy,targeted_industries_tree,targeted_regions_hierarchy"
            ),
            "campaigns": (
                "name,id,collection_type,description,origin,source_regions_hierarchy,targeted_industries_tree,targeted_regions_hierarchy"
            ),
            "reports": ("name,id,collection_type,origin,source_regions_hierarchy,targeted_industries_tree,targeted_regions_hierarchy"),
        }

        if name:
            return {"attributes": all_relationships[name]}

        # Default: return all
        query_params = {"relationships": ",".join(all_relationships.keys())}
        query_params.update({f"relationship_attributes[{key}]": value for key, value in all_relationships.items()})
        return query_params

    def __make_rest_call(self, url, method, headers=None, param=None, body=None, pagination=False):
        """
        Make a REST call to the API.

        Args:
            url (str): The endpoint to make the REST call to.
            method (str): The method to use for the REST call.
            headers (dict, optional): The headers to be sent in the request. Defaults to {}.
            param (dict, optional): The query parameters to be sent in the request. Defaults to {}.
            body (dict, optional): The request body to be sent in the request. Defaults to {}.
            pagination (bool, optional): If True, use the paginator to fetch all entities. Defaults to False.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {},
        }

        if param:
            param = urlencode(param)
            # Decode square brackets after encoding
            custom_param = param.replace("%5B", "[").replace("%5D", "]").replace("%2C", ",")
            args["endpoint"] = f"{args['endpoint']}?{custom_param}"

        self._connector.debug_print(f"args endpoint: {args['endpoint']}")

        if body:
            args["json"] = body
        if pagination:
            return self._connector.util._paginator(**args)
        else:
            return self._connector.util.make_rest_call(**args)

    def __handle_response(self, ret_val, response):
        """
        Process response received from the third party API

        Args:
            ret_val (bool): The return value of the API call
            response (list or dict): The response object from the API call

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                self._action_result.add_data(item)
        else:
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_GET_CURATED_THREAT_INTELLIGENCE_SUCCESS_RESPONSE,
        )
