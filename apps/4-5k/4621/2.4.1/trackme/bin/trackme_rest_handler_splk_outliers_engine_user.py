#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_dhm.py"
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
import requests
import time

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_outliers_engine_user",
    "trackme_rest_api_splk_outliers_engine_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import run_splunk_search, trackme_getloglevel, trackme_parse_describe_flag, trackme_reqinfo
from trackme_libs_mloutliers import get_outliers_rules, get_outliers_data

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkOutliersEngineRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkOutliersEngineRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_outliers_engine(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_outliers_engine",
            "resource_group_desc": "Endpoints related to the management of the Machine Learning Outliers detection (read only operations)",
        }

        return {"payload": response, "status": 200}

    # get Machine Learning models and rules
    def post_outliers_get_rules(self, request_info, **kwargs):

        describe = False
        object_id_value = None  # Initialize at function scope

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
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }
                
                # Support both object and object_id, prefer object_id if both provided
                object_value = None
                object_id_value = resp_dict.get("object_id")
                object_param = resp_dict.get("object")
                
                if object_id_value:
                    # object_id provided - will look up object value later
                    object_value = None  # Will be resolved after service connection
                elif object_param:
                    # object provided
                    object_value = object_param
                else:
                    return {
                        "payload": {
                            "response": "object or object_id is required",
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "component is required",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the Machine Learning outliers models and rules, it requires a POST call with the following options:",
                "resource_desc": "Get Machine Learning outliers models and rules",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/outliers_get_rules\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Use a wildcard '*' to match all entities. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative). The entity KV record _key. Either object or object_id must be provided",
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

        # Get reqinfo for configuration
        try:
            reqinfo = trackme_reqinfo(
                request_info.session_key, request_info.server_rest_uri
            )
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'Failed to retrieve request info, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

        # If object_id was provided, look up the object value from KV store
        if object_id_value and not object_value:
            try:
                # Try to get object from rules collection first (both collections should have the same object)
                collection_rules_name = (
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                )
                collection_rule = service.kvstore[collection_rules_name]
                
                # Query by _key (object_id)
                query_string = {"_key": object_id_value}
                records = collection_rule.data.query(query=json.dumps(query_string))
                
                # Try rules collection first
                if records and len(records) > 0:
                    object_value = records[0].get("object")
                
                # If not found in rules collection, try data collection as fallback
                if not object_value:
                    collection_data_name = (
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
                    )
                    collection_data = service.kvstore[collection_data_name]
                    records_data = collection_data.data.query(query=json.dumps(query_string))
                    if records_data and len(records_data) > 0:
                        object_value = records_data[0].get("object")
                
                if not object_value:
                    return {
                        "payload": {
                            "response": f'object_id="{object_id_value}" not found in KV store',
                        },
                        "status": 500,
                    }
            except Exception as e:
                response = {
                    "action": "failure",
                    "response": f'Failed to look up object from object_id, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

        # Call helper function directly instead of using Splunk search
        try:
            query_results = get_outliers_rules(
                service, tenant_id, component, object_value, reqinfo, logger
            )
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # get Machine Learning outliers data
    def post_outliers_get_data(self, request_info, **kwargs):

        describe = False
        object_id_value = None  # Initialize at function scope

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
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }
                
                # Support both object and object_id, prefer object_id if both provided
                object_value = None
                object_id_value = resp_dict.get("object_id")
                object_param = resp_dict.get("object")
                
                if object_id_value:
                    # object_id provided - will look up object value later
                    object_value = None  # Will be resolved after service connection
                elif object_param:
                    # object provided
                    object_value = object_param
                else:
                    return {
                        "payload": {
                            "response": "object or object_id is required",
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "component is required",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the Machine Learning outliers data, it requires a POST call with the following options:",
                "resource_desc": "Get Machine Learning outliers data",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/outliers_get_data\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Use a wildcard '*' to match all entities. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative). The entity KV record _key. Either object or object_id must be provided",
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

        # Get reqinfo for configuration
        try:
            reqinfo = trackme_reqinfo(
                request_info.session_key, request_info.server_rest_uri
            )
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'Failed to retrieve request info, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

        # If object_id was provided, look up the object value from KV store
        if object_id_value and not object_value:
            try:
                # Try to get object from rules collection first (both collections should have the same object)
                collection_rules_name = (
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                )
                collection_rule = service.kvstore[collection_rules_name]
                
                # Query by _key (object_id)
                query_string = {"_key": object_id_value}
                records = collection_rule.data.query(query=json.dumps(query_string))
                
                # Try rules collection first
                if records and len(records) > 0:
                    object_value = records[0].get("object")
                
                # If not found in rules collection, try data collection as fallback
                if not object_value:
                    collection_data_name = (
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
                    )
                    collection_data = service.kvstore[collection_data_name]
                    records_data = collection_data.data.query(query=json.dumps(query_string))
                    if records_data and len(records_data) > 0:
                        object_value = records_data[0].get("object")
                
                if not object_value:
                    return {
                        "payload": {
                            "response": f'object_id="{object_id_value}" not found in KV store',
                        },
                        "status": 500,
                    }
            except Exception as e:
                response = {
                    "action": "failure",
                    "response": f'Failed to look up object from object_id, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

        # Call helper function directly instead of using Splunk search
        try:
            query_results = get_outliers_data(
                service, tenant_id, component, object_value, reqinfo, logger
            )
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # get Machine Learning outliers summary (rules + data merged by model_id)
    def post_outliers_get_summary(self, request_info, **kwargs):

        describe = False
        object_id_value = None  # Initialize at function scope

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
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }
                
                # Support both object and object_id, prefer object_id if both provided
                object_value = None
                object_id_value = resp_dict.get("object_id")
                object_param = resp_dict.get("object")
                
                if object_id_value:
                    # object_id provided - will look up object value later
                    object_value = None  # Will be resolved after service connection
                elif object_param:
                    # object provided
                    object_value = object_param
                else:
                    return {
                        "payload": {
                            "response": "object or object_id is required",
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "component is required",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the Machine Learning outliers summary (rules and data merged by model_id), it requires a POST call with the following options:",
                "resource_desc": "Get Machine Learning outliers summary (rules + data)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/outliers_get_summary\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Use a wildcard '*' to match all entities. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative). The entity KV record _key. Either object or object_id must be provided",
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

        # Get reqinfo for configuration
        try:
            reqinfo = trackme_reqinfo(
                request_info.session_key, request_info.server_rest_uri
            )
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'Failed to retrieve request info, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

        # If object_id was provided, look up the object value from KV store
        if object_id_value and not object_value:
            try:
                # Try to get object from rules collection first (both collections should have the same object)
                collection_rules_name = (
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                )
                collection_rule = service.kvstore[collection_rules_name]
                
                # Query by _key (object_id)
                query_string = {"_key": object_id_value}
                records = collection_rule.data.query(query=json.dumps(query_string))
                
                # Try rules collection first
                if records and len(records) > 0:
                    object_value = records[0].get("object")
                
                # If not found in rules collection, try data collection as fallback
                if not object_value:
                    collection_data_name = (
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
                    )
                    collection_data = service.kvstore[collection_data_name]
                    records_data = collection_data.data.query(query=json.dumps(query_string))
                    if records_data and len(records_data) > 0:
                        object_value = records_data[0].get("object")
                
                if not object_value:
                    return {
                        "payload": {
                            "response": f'object_id="{object_id_value}" not found in KV store',
                        },
                        "status": 500,
                    }
            except Exception as e:
                response = {
                    "action": "failure",
                    "response": f'Failed to look up object from object_id, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

        # Call both helper functions and merge results by model_id
        try:
            # Get rules
            rules_results = get_outliers_rules(
                service, tenant_id, component, object_value, reqinfo, logger
            )

            # Get data
            data_results = get_outliers_data(
                service, tenant_id, component, object_value, reqinfo, logger
            )

            # Merge results by model_id
            # Structure: List of dictionaries, each containing model_id as key with rules and data
            summary_results = []

            # Create a dictionary to group rules by model_id
            rules_by_model = {}
            for rule in rules_results:
                model_id = rule.get("model_id")
                if model_id:
                    if model_id not in rules_by_model:
                        rules_by_model[model_id] = []
                    rules_by_model[model_id].append(rule)

            # Create a dictionary to group data by object (data doesn't have model_id directly)
            # We'll match data to rules by object and object_category
            data_by_object = {}
            for data_item in data_results:
                obj_key = f"{data_item.get('object_category')}:{data_item.get('object')}"
                if obj_key not in data_by_object:
                    data_by_object[obj_key] = []
                data_by_object[obj_key].append(data_item)

            # Build summary: for each model_id, create an entry with rules and matching data
            for model_id, rules_list in rules_by_model.items():
                # Get the object and object_category from the first rule (they should be the same for all rules of the same model)
                if rules_list:
                    first_rule = rules_list[0]
                    obj_key = f"{first_rule.get('object_category')}:{first_rule.get('object')}"
                    
                    # Find matching data
                    matching_data = data_by_object.get(obj_key, [])

                    # Create summary entry
                    summary_entry = {
                        model_id: {
                            "rules": rules_list,
                            "data": matching_data
                        }
                    }
                    summary_results.append(summary_entry)

            return {"payload": summary_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # get Machine Learning list of models for a given object
    def post_outliers_get_models(self, request_info, **kwargs):

        describe = False
        object_id_value = None  # Initialize at function scope

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
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }
                
                # Support both object and object_id, prefer object_id if both provided
                object_value = None
                object_id_value = resp_dict.get("object_id")
                object_param = resp_dict.get("object")
                
                if object_id_value:
                    # object_id provided - will look up object value later
                    object_value = None  # Will be resolved after service connection
                elif object_param:
                    # object provided
                    object_value = object_param
                else:
                    return {
                        "payload": {
                            "response": "object or object_id is required",
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "component is required",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the Machine Learning outliers models, it requires a POST call with the following options:",
                "resource_desc": "Get Machine Learning outliers list of models for a given entity",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/outliers_get_models\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'myobject'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Use a wildcard '*' to match all entities. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative). The entity KV record _key. Either object or object_id must be provided",
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

        # If object_id was provided, look up the object value from KV store
        if object_id_value and not object_value:
            try:
                # Try to get object from rules collection first (both collections should have the same object)
                collection_rules_name = (
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                )
                collection_rule = service.kvstore[collection_rules_name]
                
                # Query by _key (object_id)
                query_string = {"_key": object_id_value}
                records = collection_rule.data.query(query=json.dumps(query_string))
                
                # Try rules collection first
                if records and len(records) > 0:
                    object_value = records[0].get("object")
                
                # If not found in rules collection, try data collection as fallback
                if not object_value:
                    collection_data_name = (
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
                    )
                    collection_data = service.kvstore[collection_data_name]
                    records_data = collection_data.data.query(query=json.dumps(query_string))
                    if records_data and len(records_data) > 0:
                        object_value = records_data[0].get("object")
                
                if not object_value:
                    return {
                        "payload": {
                            "response": f'object_id="{object_id_value}" not found in KV store',
                        },
                        "status": 500,
                    }
            except Exception as e:
                response = {
                    "action": "failure",
                    "response": f'Failed to look up object from object_id, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        searchquery = f'| trackmesplkoutliersgetrules tenant_id="{tenant_id}" component="{component}" object="{object_value}"'

        models_list = []
        try:
            # spawn the search and get the results
            reader = run_splunk_search(
                service,
                searchquery,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    model_id = item.get("model_id")
                    if model_id:
                        models_list.append(model_id)
            return {"payload": {"models": models_list}, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # render ML entity model
    def post_outliers_render_entity_model(self, request_info, **kwargs):
        describe = False
        object_id_value = None  # Initialize at function scope

        logger.debug(f"Starting function post_outliers_render_entity_model")

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
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }

                # Support both object and object_id, prefer object_id if both provided
                object_value = None
                object_id_value = resp_dict.get("object_id")
                object_param = resp_dict.get("object")
                
                if object_id_value:
                    # object_id provided - will look up object value later
                    object_value = None  # Will be resolved after service connection
                elif object_param:
                    # object provided
                    object_value = object_param
                else:
                    return {
                        "payload": {
                            "response": "object or object_id is required",
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "component is required",
                        },
                        "status": 500,
                    }

                try:
                    mode = resp_dict["mode"]
                    # valid options are: live, simulation
                    if mode not in ("live", "simulation"):
                        return {
                            "payload": {
                                "response": "mode must be either live or simulation",
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "mode is required",
                        },
                        "status": 500,
                    }

                try:
                    model_id = resp_dict["model_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "model_id is required",
                        },
                        "status": 500,
                    }

                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "earliest_time is required",
                        },
                        "status": 500,
                    }

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "latest_time is required",
                        },
                        "status": 500,
                    }

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint renders ML for a given entity, it requires a POST call with the following options:",
                "resource_desc": "Renders ML Outliers for a given entity, this endpoint is used by the backend to render the ML model for a given entity.",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/outliers_render_entity_model\" body=\"{'tenant_id':'mytenant','component':'dsm','object':'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative). The entity KV record _key. Either object or object_id must be provided",
                        "mode": "(required) rendering mode, valid options: live, simulation",
                        "model_id": "(required) model identifier",
                        "earliest_time": "(required) earliest time",
                        "latest_time": "(required) latest time",
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
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # If object_id was provided, look up the object value from KV store
        if object_id_value and not object_value:
            try:
                # Try to get object from rules collection first (both collections should have the same object)
                collection_rules_name_temp = (
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                )
                collection_rule_temp = service.kvstore[collection_rules_name_temp]
                
                # Query by _key (object_id)
                query_string = {"_key": object_id_value}
                records = collection_rule_temp.data.query(query=json.dumps(query_string))
                
                # Try rules collection first
                if records and len(records) > 0:
                    object_value = records[0].get("object")
                
                # If not found in rules collection, try data collection as fallback
                if not object_value:
                    collection_data_name = (
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
                    )
                    collection_data = service.kvstore[collection_data_name]
                    records_data = collection_data.data.query(query=json.dumps(query_string))
                    if records_data and len(records_data) > 0:
                        object_value = records_data[0].get("object")
                
                if not object_value:
                    return {
                        "payload": {
                            "response": f'object_id="{object_id_value}" not found in KV store',
                        },
                        "status": 500,
                    }
            except Exception as e:
                response = {
                    "action": "failure",
                    "response": f'Failed to look up object from object_id, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

        # start time
        start_time = time.time()

        # Outliers rules storage collection
        collection_rules_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_rule = service.kvstore[collection_rules_name]

        # Vtenants storage collection
        vtenants_collection_name = "kv_trackme_virtual_tenants"
        vtenants_collection = service.kvstore[vtenants_collection_name]

        #
        # First, get the full vtenant definition
        #

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # get
        try:
            vtenant_record = vtenants_collection.data.query(
                query=json.dumps(query_string)
            )
            vtenant_key = vtenant_record[0].get("_key")
        except Exception as e:
            error_msg = (
                f'tenant_id="{tenant_id}" could not be found in the vtenants collection'
            )
            logger.error(error_msg)
            return {
                "payload": {
                    "response": error_msg,
                },
                "status": 500,
            }

        #
        # Get the Outliers rules
        #

        # Define the KV query
        query_string_filter = {
            "object_category": f"splk-{component}",
            "object": object_value,
        }

        query_string = {"$and": [query_string_filter]}

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        key = None

        try:
            records_outliers_rules = collection_rule.data.query(
                query=json.dumps(query_string)
            )
            record_outliers_rules = records_outliers_rules[0]
            key = record_outliers_rules.get("_key")

        except Exception as e:
            key = None

        # if no records
        if not key:
            msg = f'tenant_id="{tenant_id}", component="{component}", object="{object_value}" outliers rules record cannot be found or are not yet available for this entity.'
            logger.error(msg)
            return {
                "payload": {"response": msg},
                "status": 500,
            }

        # log debug
        logger.debug(f'record_outliers_rules="{record_outliers_rules}"')

        # Get the JSON outliers rules object
        entities_outliers = record_outliers_rules.get("entities_outliers")

        # Load as a dict
        try:
            entities_outliers = json.loads(
                record_outliers_rules.get("entities_outliers")
            )
        except Exception as e:
            msg = f'Failed to load entities_outliers with exception="{str(e)}"'

        # log debug
        logger.debug(f'entities_outliers="{entities_outliers}"')

        # Extract as a dict
        entity_outlier_dict = entities_outliers[model_id]

        # log debug
        logger.debug(f'entity_outlier_dict="{entity_outlier_dict}"')

        # Extract the render search
        if mode == "simulation":
            ml_model_render_search = entity_outlier_dict[
                "ml_model_simulation_render_search"
            ]
        elif mode == "live":
            ml_model_render_search = entity_outlier_dict["ml_model_render_search"]
        logger.debug(f'ml_model_simulation_render_search="{ml_model_render_search}"')

        # set kwargs
        kwargs_oneshot = {
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "search_mode": "normal",
            "preview": False,
            "time_format": "%s",
            "count": 0,
            "output_mode": "json",
        }

        # run search
        search_results = []
        try:
            reader = run_splunk_search(
                service,
                ml_model_render_search,
                kwargs_oneshot,
                24,
                5,
            )

            # loop through the reader results
            for item in reader:
                if isinstance(item, dict):
                    search_results.append(item)

            # return
            logger.info(
                f"function post_outliers_render_entity_model successfully executed in {round(time.time() - start_time, 3)} seconds"
            )
            return {
                "payload": {
                    "search_results": search_results,
                },
                "status": 200,
            }

        except Exception as e:
            return {
                "payload": {
                    "response": f'Failed to run the search with exception="{str(e)}"',
                },
                "status": 500,
            }

    # check model
    def post_outliers_check_model(self, request_info, **kwargs):

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:

                # get model_id
                try:
                    model_id = resp_dict["model_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "model_id is required",
                        },
                        "status": 500,
                    }

                # get model_storage and tenant_id for native KVstore models
                model_storage = resp_dict.get("model_storage", "file")
                tenant_id = resp_dict.get("tenant_id", None)

                # tenant_id is required when model_storage is kvstore
                if model_storage == "kvstore" and not tenant_id:
                    return {
                        "payload": {
                            "response": "tenant_id is required when model_storage is kvstore",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint checks a specific ML model, it requires a POST call with the following options:",
                "resource_desc": "Check TrackMe Machine Learning model",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/outliers_check_model\" body=\"{'model_id': 'model_178709885414488'}\"",
                "options": [
                    {
                        "model_id": "(required) model identifier",
                        "model_storage": "(optional) model storage backend: 'kvstore' or 'file' (default: 'file')",
                        "tenant_id": "(required for kvstore) tenant identifier for KVstore model lookup",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.system_authtoken,
            "Content-Type": "application/json",
        }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # create an object response_final
        response_final = {}

        # Check model existence based on storage type
        if model_storage == "kvstore" and tenant_id:
            # Native KVstore model: check in the native ML models collection
            try:
                collection_name = f"kv_trackme_native_ml_models_tenant_{tenant_id}"
                service = client.connect(
                    owner="nobody",
                    app="trackme",
                    port=request_info.server_rest_port,
                    token=request_info.session_key,
                    timeout=600,
                )
                collection = service.kvstore[collection_name]
                records = collection.data.query(query=json.dumps({"_key": model_id}))
                if records and len(records) > 0:
                    response_final["model_exists"] = True
                    response_final["model_storage"] = "kvstore"
                    response_final["collection_name"] = collection_name
                    # include model metadata
                    for key, value in records[0].items():
                        if key != "model_data":  # exclude large model data blob
                            response_final[key] = value
                else:
                    response_final["model_exists"] = False
                    response_final["model_storage"] = "kvstore"
                    response_final["collection_name"] = collection_name
                    response_final["response"] = f"Model '{model_id}' not found in KVstore collection '{collection_name}'"
            except Exception as e:
                error_msg = f'Failed to check KVstore model existence with exception="{str(e)}"'
                response_final["model_exists"] = False
                response_final["model_storage"] = "kvstore"
                response_final["response"] = error_msg
                logger.error(f"{error_msg}")
        else:
            # File-based model (both MLTK and native): uses __mlspl_ naming convention
            # Native file-based models reuse the MLTK naming format for SHC replication
            # and cluster bundle exclusion compatibility
            rest_url = f"{request_info.server_rest_uri}/servicesNS/splunk-system-user/trackme/data/lookup-table-files/__mlspl_{model_id}.mlmodel"

            try:
                response = requests.get(
                    rest_url,
                    params={"output_mode": "json", "count": 0},
                    headers=header,
                    timeout=600,
                    verify=False,
                )

                if response.status_code not in (200, 201, 204):
                    error_msg = f'Failed to get the model with status_code="{response.status_code}", response.text="{response.text}"'
                    response_final["model_exists"] = False
                    response_final["rest_url"] = rest_url
                    response_final["response"] = error_msg

                else:
                    response_final["model_exists"] = True
                    response_final["rest_url"] = rest_url
                    response_json = response.json()
                    # for fields in response_json, add to the response_final
                    for key, value in response_json.items():
                        response_final[key] = value

            except Exception as e:
                error_msg = f'Failed to get the model with exception="{str(e)}"'
                response_final["model_exists"] = False
                response_final["response"] = error_msg
                response_final["rest_url"] = rest_url
                logger.error(f"{error_msg}")

        # return the payload
        return {
            "payload": response_final,
            "status": 200,
        }
