#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_sla_policies.py"
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
    "trackme.rest.splk_sla_policies_user",
    "trackme_rest_api_splk_sla_policies_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag, trackme_reqinfo
from trackme_libs_policies import (
    list_available_transforms,
    get_lookup_fields,
    get_entity_fields,
    get_search_fields,
    resolve_service_for_account,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkSlaPoliciesRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkSlaPoliciesRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_sla_policies(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_sla_policies",
            "resource_group_desc": "Endpoints related to the management of SLA classes through policies (read only operations)",
        }

        return {"payload": response, "status": 200}

    # get SLA classes definition
    def get_sla_classes_show(self, request_info, **kwargs):

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
            describe = False

        if describe:
            response = {
                "describe": "This endpoint shows current SLA classes definitions, it requires a GET call:",
                "resource_desc": "Get SLA classes definitions",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/splk_sla_policies/sla_classes_show"',
                "options": [],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get trackmeconf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )["trackme_conf"]

        # Get SLA classes conf
        sla_classes = trackme_conf["sla"]["sla_classes"]

        # A list of SLA classes
        sla_classes_list = []

        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
            for sla_class in sla_classes:
                sla_classes_list.append(sla_class)

            # Sort by rank descending (most important first)
            sla_classes_list.sort(
                key=lambda c: sla_classes[c].get("rank", 0), reverse=True
            )

            # render response
            return {
                "payload": {
                    "response": {
                        "sla_classes": sla_classes_list,
                        "sla_classes_definitions": sla_classes,
                    },
                    "status": 200,
                },
                "status": 200,
            }

        except:
            error_msg = f'Error loading sla_classes JSON, please check the configuration, the JSON is not valid JSON, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": f"{error_msg}",
                    "status": 500,
                },
                "status": 500,
            }

    # get SLA classes definition
    def get_sla_classes_show_list(self, request_info, **kwargs):

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
            describe = False

        if describe:
            response = {
                "describe": "This endpoint returns the list of currently-defined SLA class names, sorted by rank in descending order (most important first). The class definitions themselves are stored in the [sla] stanza of trackme_settings.conf as a JSON object keyed by class name. It requires a GET call with no parameters.",
                "resource_desc": "Return the list of currently-defined SLA class names (sorted by rank, most important first)",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/splk_sla_policies/sla_classes_show_list"',
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get trackmeconf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )["trackme_conf"]

        # Get SLA classes conf
        sla_classes = trackme_conf["sla"]["sla_classes"]

        # A list of SLA classes
        sla_classes_list = []

        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
            for sla_class in sla_classes:
                sla_classes_list.append(sla_class)

            # Sort by rank descending (most important first)
            sla_classes_list.sort(
                key=lambda c: sla_classes[c].get("rank", 0), reverse=True
            )

            # render response
            return {
                "payload": sla_classes_list,
                "status": 200,
            }

        except:
            error_msg = f'Error loading sla_classes JSON, please check the configuration, the JSON is not valid JSON, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": f"{error_msg}",
                    "status": 500,
                },
                "status": 500,
            }

    # get all records
    def post_sla_policies_show(self, request_info, **kwargs):

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
                "describe": "This endpoint retrieves all records for the SLA classes policies collection, it requires a POST call with the following information:",
                "resource_desc": "Get SLA classes policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/sla_policies_show\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
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
            collection_name = f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
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
    def post_sla_policies_by_id(self, request_info, **kwargs):

        # By id
        tenant_id = None
        component = None
        sla_class_policy_id = None

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
                    sla_class_policy_id = resp_dict["sla_class_policy_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "sla_class_policy_id is required",
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
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/sla_policies_by_id\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'sla_class_policy_id': 'pan:traffic'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "sla_class_policy_id": "(required) ID of the sla policy",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Define the KV query
        query_string = {
            "sla_class_policy_id": sla_class_policy_id,
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
            collection_name = f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
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
                    "response": f'sla_class_policy_id="{sla_class_policy_id}" not found',
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
    def post_sla_policies_list_transforms(self, request_info, **kwargs):

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
                "describe": "This endpoint lists Splunk lookup transforms available to the calling user (or to a configured remote Splunk deployment account), used by the SLA policy configuration UI to populate the lookup-name picker.",
                "resource_desc": "List available Splunk lookup transforms (local or remote) for SLA policy configuration",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_sla_policies/sla_policies_list_transforms" body="{\'filter\': \'sla\', \'account\': \'local\'}"',
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
    def post_sla_policies_get_lookup_fields(self, request_info, **kwargs):

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
                "resource_desc": "Get fields from a lookup transform for SLA policy field mapping",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_sla_policies/sla_policies_get_lookup_fields" body="{\'lookup_name\': \'my_asset_lookup\'}"',
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
    def post_sla_policies_get_entity_fields(self, request_info, **kwargs):

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
                "describe": "This endpoint returns the available entity fields for mapping in lookup-based SLA policies, it requires a POST call with the following information:",
                "resource_desc": "Get available entity fields per component for SLA policy lookup field mapping",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_sla_policies/sla_policies_get_entity_fields" body="{\'component\': \'dsm\'}"',
                "options": [
                    {
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        return get_entity_fields(component)

    # Execute a Splunk search and return fields for search-based SLA policies
    def post_sla_policies_execute_search(self, request_info, **kwargs):

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
                "describe": "This endpoint executes a Splunk SPL search and returns fields and sample rows for search-based SLA policy configuration, it requires a POST call with the following information:",
                "resource_desc": "Execute a Splunk SPL search and return fields and sample rows for search-based SLA policy configuration",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_sla_policies/sla_policies_execute_search" body="{\'tenant_id\': \'mytenant\', \'component\': \'dsm\', \'search_query\': \'| inputlookup my_asset_lookup\', \'earliest\': \'-5m\', \'latest\': \'now\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
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
