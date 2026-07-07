#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_priority_policies.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_priority_policies_user",
    "trackme_rest_api_splk_priority_policies_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag
from trackme_libs_policies import (
    list_available_transforms,
    get_lookup_fields,
    get_entity_fields,
    get_search_fields,
    resolve_service_for_account,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkPriorityPoliciesRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkPriorityPoliciesRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_priority_policies(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_priority_policies",
            "resource_group_desc": "Endpoints related to the management of priorities (read only operations)",
        }

        return {"payload": response, "status": 200}

    # get all records
    def post_priority_policies_show(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        component = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "tenant_id is required",
                        },
                        "status": 400,
                    }
                try:
                    component = resp_dict["component"]
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "wlk",
                        "flx",
                        "fqm",
                    ):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"invalid component {component}, valid options are: dsm/dhm/mhm/wlk/flx/fqm",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "component is required",
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all records for the priority policies collection, it requires a POST call with the following information:",
                "resource_desc": "Get priority policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_priority_policies/priority_policies_show\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', }\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            # Data collection
            collection_name = (
                f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
            )
            collection = service.kvstore[collection_name]

            return {"payload": collection.data.query(), "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Get model
    def post_priority_policies_by_id(self, request_info, **kwargs):

        # By id
        tenant_id = None
        component = None
        priority_policy_id = None

        # query_string to find records
        query_string = None

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "tenant_id is required",
                        },
                        "status": 400,
                    }
                try:
                    component = resp_dict["component"]
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "wlk",
                        "flx",
                        "fqm",
                    ):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"invalid component {component}, valid options are: dsm/dhm/mhm/wlk/flx/fqm",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "component is required",
                        },
                        "status": 400,
                    }
                try:
                    priority_policy_id = resp_dict["priority_policy_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "priority_policy_id is required",
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves a tag policy by its id, it requires a GET call with the following data:",
                "resource_desc": "Get a given tag policy",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_priority_policies/priority_policies_by_id\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'priority_policy_id': 'pan:traffic'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "priority_policy_id": "ID of the priority policy",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Define the KV query
        query_string = {
            "priority_policy_id": priority_policy_id,
        }

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            collection_name = (
                f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
            )
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                return {"payload": collection.data.query_by_id(key), "status": 200}

            else:
                response = {
                    "action": "failure",
                    "response": f'priority_policy_id="{priority_policy_id}" not found',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 404}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # List available Splunk lookup transforms
    def post_priority_policies_list_transforms(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint lists Splunk lookup transforms available to the calling user (or to a configured remote Splunk deployment account), used by the priority policy configuration UI to populate the lookup-name picker.",
                "resource_desc": "List available Splunk lookup transforms (local or remote) for priority policy configuration",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_priority_policies/priority_policies_list_transforms" body="{\'filter\': \'priority\', \'account\': \'local\'}"',
                "options": [
                    {
                        "filter": "OPTIONAL. A substring filter to match against transform names — only transforms whose name contains this substring are returned",
                        "account": "OPTIONAL. The remote Splunk deployment account name to enumerate transforms from (defaults to 'local')",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional filter
        name_filter = None
        if resp_dict:
            name_filter = resp_dict.get("filter", None)

        # optional account (for remote Splunk deployment)
        account = resp_dict.get("account", "local") if resp_dict else "local"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # Resolve target service (local or remote)
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        return list_available_transforms(target_service, logger, name_filter)

    # Get fields from a specific lookup transform
    def post_priority_policies_get_lookup_fields(self, request_info, **kwargs):

        # Declare
        lookup_name = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    lookup_name = resp_dict["lookup_name"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "lookup_name is required",
                        },
                        "status": 400,
                    }
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the fields from a Splunk lookup transform, it requires a POST call with the following information:",
                "resource_desc": "Get fields from a lookup transform for priority policy field mapping",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_priority_policies/priority_policies_get_lookup_fields" body="{\'lookup_name\': \'my_asset_lookup\'}"',
                "options": [
                    {
                        "lookup_name": "(required) The name of the lookup transform",
                        "account": "(optional) The remote Splunk deployment account name, defaults to local",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional account (for remote Splunk deployment)
        account = resp_dict.get("account", "local") if resp_dict else "local"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # Resolve target service (local or remote)
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        return get_lookup_fields(target_service, logger, lookup_name)

    # Get available entity fields for a given component
    def post_priority_policies_get_entity_fields(self, request_info, **kwargs):

        # Declare
        component = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    component = resp_dict["component"]
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "wlk",
                        "flx",
                        "fqm",
                    ):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"invalid component {component}, valid options are: dsm/dhm/mhm/wlk/flx/fqm",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "component is required",
                        },
                        "status": 400,
                    }
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the available entity fields for mapping in lookup-based priority policies, it requires a POST call with the following information:",
                "resource_desc": "Get available entity fields per component for priority policy lookup field mapping",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_priority_policies/priority_policies_get_entity_fields" body="{\'component\': \'dsm\'}"',
                "options": [
                    {
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        return get_entity_fields(component)

    # Execute a Splunk search and return fields for search-based priority policies
    def post_priority_policies_execute_search(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        component = None
        search_query = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "tenant_id is required",
                        },
                        "status": 400,
                    }
                try:
                    component = resp_dict["component"]
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "wlk",
                        "flx",
                        "fqm",
                    ):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"invalid component {component}, valid options are: dsm/dhm/mhm/wlk/flx/fqm",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "component is required",
                        },
                        "status": 400,
                    }
                search_query = resp_dict.get("search_query", "")
                if not search_query:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "search_query is required",
                        },
                        "status": 400,
                    }
                earliest = resp_dict.get("earliest", "-5m")
                latest = resp_dict.get("latest", "now")
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint executes a Splunk SPL search and returns fields and sample rows for search-based priority policy configuration, it requires a POST call with the following information:",
                "resource_desc": "Execute a Splunk SPL search and return fields and sample rows for search-based priority policy configuration",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_priority_policies/priority_policies_execute_search" body="{\'tenant_id\': \'mytenant\', \'component\': \'dsm\', \'search_query\': \'| inputlookup my_asset_lookup\', \'earliest\': \'-5m\', \'latest\': \'now\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "search_query": "(required) The SPL search query to execute",
                        "earliest": "(optional) The earliest time for the search, defaults to -5m",
                        "latest": "(optional) The latest time for the search, defaults to now",
                        "account": "(optional) The remote Splunk deployment account name, defaults to local",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # optional account (for remote Splunk deployment)
        account = resp_dict.get("account", "local") if resp_dict else "local"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # Resolve target service (local or remote)
        try:
            target_service = resolve_service_for_account(service, request_info, account, logger)
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'Failed to connect to remote account "{account}": {str(e)}',
                },
                "status": 503,
            }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        return get_search_fields(target_service, logger, search_query, earliest, latest)
