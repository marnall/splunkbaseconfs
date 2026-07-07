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
import re
import json
import os
import random
import sys
import time
import threading
from datetime import datetime
import hashlib
import requests
import urllib.parse

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_outliers_engine_power",
    "trackme_rest_api_splk_outliers_engine_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    run_splunk_search,
    trackme_audit_event,
    trackme_gen_state,
    trackme_getloglevel,
    trackme_idx_for_tenant,
    trackme_parse_describe_flag,
    trackme_refresh_component_summary_async,
    trackme_reqinfo,
    trackme_vtenant_account_from_service,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import trackme libs mloutliers
from trackme_libs_mloutliers import (
    train_mlmodel,
    parse_user_datetime,
    get_training_window_cutoff_epoch,
)

# import trackme libs scoring
from trackme_libs_scoring import trackme_scoring_gen_metrics, generate_score_id, write_score_cache

# import shadow libs
from trackme_libs_shadow import refresh_shadow_after_score_change

# import Splunk libs
import splunklib.client as client

# Numeric type definitions for outlier model fields
# Used by REST handlers to coerce string values from the frontend to proper types
OUTLIER_FLOAT_FIELDS = {
    "density_lowerthreshold",
    "density_upperthreshold",
    "perc_min_lowerbound_deviation",
    "perc_min_upperbound_deviation",
    "min_value_for_lowerbound_breached",
    "min_value_for_upperbound_breached",
    "static_lower_threshold",
    "static_upper_threshold",
}
OUTLIER_INT_FIELDS = {
    "alert_lower_breached",
    "alert_upper_breached",
    "auto_correct",
    "is_disabled",
    "score",
    "ai_mladvisor_disabled",
}


class TrackMeHandlerSplkOutliersEngineWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkOutliersEngineWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_outliers_engine(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_outliers_engine/write",
            "resource_group_desc": "Endpoints related to the management of the Machine Learning Outliers detection (power operations)",
        }

        return {"payload": response, "status": 200}

    # Add a new ML model to a given entity
    def post_outliers_add_model(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                # Accept either object_id or object (prefer object_id)
                object_id = resp_dict.get("object_id", None)
                object_value = resp_dict.get("object", None)
                if not object_id and not object_value:
                    return {"payload": "either object_id or object is required", "status": 500}
                try:
                    model_json = resp_dict["model_json"]
                except Exception as e:
                    return {"payload": "model_json is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "resource_desc": "Add a new Machine Learning outliers model",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_outliers_engine/write/outliers_add_model" body="{\'tenant_id\':\'mytenant\',\'component\':\'dsm\',\'object\':\'netscreen:netscreen:firewall\',\'model_json\':\'{\\\\\\"kpi_metric\\\\\\":\\\\\\"splk.feeds.perc95_eventcount_5m\\\\\\",\\\\\\"kpi_span\\\\\\":\\\\\\"10m\\\\\\",\\\\\\"method_calculation\\\\\\":\\\\\\"avg\\\\\\",\\\\\\"density_lowerthreshold\\\\\\":\\\\\\"0.005\\\\\\",\\\\\\"density_upperthreshold\\\\\\":\\\\\\"0.005\\\\\\",\\\\\\"alert_lower_breached\\\\\\":\\\\\\"1\\\\\\",\\\\\\"alert_upper_breached\\\\\\":\\\\\\"1\\\\\\",\\\\\\"period_calculation\\\\\\":\\\\\\"-30d\\\\\\",\\\\\\"time_factor\\\\\\":\\\\\\"%25H\\\\\\",\\\\\\"perc_min_lowerbound_deviation\\\\\\":\\\\\\"5.0\\\\\\",\\\\\\"perc_min_upperbound_deviation\\\\\\":\\\\\\"5.0\\\\\\"}\'}"',
                "describe": "This endpoint adds a new ML model to a given entity, it requires a POST call with the following options:",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "REQUIRED. The component category (one of: dsm, dhm, mhm, flx, fqm, wlk)",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative — preferred when known). The entity KV record _key. Either object or object_id must be provided",
                        "model_json": "REQUIRED. The new ML model JSON definition",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Component collection
        collection_component_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        collection_component = service.kvstore[collection_component_name]

        # Data collection_rules
        collection_rules_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_rules = service.kvstore[collection_rules_name]

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Try to load the model JSON definition, if loading fails, stop here
        if not isinstance(model_json, dict):
            try:
                new_model_definition = json.loads(model_json)
                logger.info(
                    f'Successfully loaded model_json="{json.dumps(new_model_definition, indent=4)}"'
                )
            except Exception as e:
                msg = f'Failed to load the model_json="{model_json}" as a properly formatted JSON object with exception="{str(e)}"'
                logger.error(msg)
                return {"payload": msg, "status": 500}
        else:
            new_model_definition = model_json

        # records summary
        records = []

        # Use object_id if provided, otherwise query by object to get the key
        key = None
        if object_id:
            # Use object_id directly
            key = object_id
            # Get object_value from KVstore for logging/response purposes
            # Try component collection first (for entities without outliers rules yet),
            # then fall back to outliers rules collection
            if not object_value:
                try:
                    # Try component collection first (main entity collection)
                    component_record = collection_component.data.query_by_id(object_id)
                    object_value = component_record.get("object", "")
                except Exception as e:
                    # Fall back to outliers rules collection if component collection query fails
                    try:
                        entity_rules_record = collection_rules.data.query_by_id(object_id)
                        object_value = entity_rules_record.get("object", "")
                    except Exception as e2:
                        object_value = ""
        else:
            # Get the component current record
            try:
                # Define the KV query
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "object": object_value,
                        }
                    ]
                }
                component_record = collection_component.data.query(
                    query=json.dumps(query_string)
                )[0]
                key = component_record.get("_key")

            except Exception as e:
                key = None

        # Get the current entity_rules record, if any

        # init
        entity_rules = {}
        entities_outliers = {}
        entity_has_rules = False

        try:
            # Define the KV query - use object_id if available, otherwise object
            if object_id:
                # Query by object_id (_key)
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "_key": object_id,
                        }
                    ]
                }
            else:
                # Query by object
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "object": object_value,
                        }
                    ]
                }

            entity_rules = collection_rules.data.query(query=json.dumps(query_string))[
                0
            ]
        except Exception as e:
            pass

        if entity_rules:
            entity_has_rules = True

        #
        # main
        #

        if (
            not key
        ):  # cannot continue if the object is not found in the component collection
            error_msg = {
                "payload": "object not found",
                "query": query_string,
                "collection": collection_component_name,
                "status": 404,
            }
            logger.error(json.dumps(error_msg))
            return {"payload": error_msg, "status": 404}

        else:
            # Load as a dict
            if entity_rules:
                try:
                    entities_outliers = json.loads(
                        entity_rules.get("entities_outliers")
                    )
                except Exception as e:
                    entities_outliers = {}

            # log debug
            logger.debug(
                f'entities_outliers="{json.dumps(entities_outliers, indent=4)}"'
            )

            # For each expected key, try to retrieve the value
            try:
                score = new_model_definition.get("score", 36)
                
                # Validate score (must be integer between 0 and 100, default 36)
                try:
                    score = int(score)
                    if score < 0 or score > 100:
                        return {
                            "payload": {
                                "error": "score must be an integer between 0 and 100"
                            },
                            "status": 500,
                        }
                except (ValueError, TypeError):
                    return {
                        "payload": {
                            "error": "score must be an integer between 0 and 100"
                        },
                        "status": 500,
                    }
                
                kpi_metric = new_model_definition.get("kpi_metric")
                kpi_span = new_model_definition.get("kpi_span")
                method_calculation = new_model_definition.get("method_calculation")
                density_lowerthreshold = new_model_definition.get(
                    "density_lowerthreshold"
                )
                density_upperthreshold = new_model_definition.get(
                    "density_upperthreshold"
                )
                alert_lower_breached = new_model_definition.get("alert_lower_breached")
                alert_upper_breached = new_model_definition.get("alert_upper_breached")
                period_calculation = new_model_definition.get("period_calculation")
                # optional period_calculation_latest
                period_calculation_latest = new_model_definition.get(
                    "period_calculation_latest", "now"
                )
                time_factor = urllib.parse.unquote(
                    new_model_definition.get("time_factor")
                )
                min_value_for_lowerbound_breached = new_model_definition.get(
                    "min_value_for_lowerbound_breached", 0
                )
                min_value_for_upperbound_breached = new_model_definition.get(
                    "min_value_for_upperbound_breached", 0
                )
                static_lower_threshold = new_model_definition.get(
                    "static_lower_threshold", None
                )
                static_upper_threshold = new_model_definition.get(
                    "static_upper_threshold", None
                )
                auto_correct = new_model_definition.get("auto_correct")
                perc_min_lowerbound_deviation = new_model_definition.get(
                    "perc_min_lowerbound_deviation"
                )
                perc_min_upperbound_deviation = new_model_definition.get(
                    "perc_min_upperbound_deviation"
                )

            except Exception as e:
                msg = f'Failed to retrieve expected key from model_json with exception="{str(e)}"'
                logger.error(msg)
                return {"payload": msg, "status": 500}

            # Set the model identifier
            model = f"model_{random.getrandbits(48)}"

            # Set the final model definition
            final_model_definition = {
                "is_disabled": 0,
                "score": score,
                "kpi_metric": kpi_metric,
                "kpi_span": kpi_span,
                "method_calculation": method_calculation,
                "density_lowerthreshold": density_lowerthreshold,
                "density_upperthreshold": density_upperthreshold,
                "alert_lower_breached": alert_lower_breached,
                "alert_upper_breached": alert_upper_breached,
                "period_calculation": period_calculation,
                "period_calculation_latest": period_calculation_latest,
                "time_factor": time_factor,
                "auto_correct": auto_correct,
                "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                "static_lower_threshold": static_lower_threshold,
                "static_upper_threshold": static_upper_threshold,
                "period_exclusions": [],
                "ml_model_gen_search": "pending",
                "ml_model_render_search": "pending",
                "ml_model_summary_search": "pending",
                "rules_access_search": "pending",
                "ml_model_filename": "pending",
                "ml_model_filesize": "pending",
                "ml_model_lookup_share": "pending",
                "ml_model_lookup_owner": "pending",
                "last_exec": "pending",
            }

            # Coerce string values from the frontend to proper numeric types
            for field, val in final_model_definition.items():
                if val is not None:
                    try:
                        if field in OUTLIER_FLOAT_FIELDS:
                            final_model_definition[field] = float(val)
                        elif field in OUTLIER_INT_FIELDS:
                            final_model_definition[field] = int(float(val))
                    except (ValueError, TypeError):
                        pass  # keep original if conversion fails

            # Add the new model to the dict
            entities_outliers[model] = final_model_definition

            # log debug
            logger.debug(
                f'final model_dict="{json.dumps(entities_outliers, indent=4)}"'
            )

            try:
                # Update the record
                entity_rules["entities_outliers"] = json.dumps(
                    entities_outliers, indent=4
                )
                entity_rules["mtime"] = time.time()

                # Insert or update
                if entity_has_rules:
                    collection_rules.data.update(str(key), json.dumps(entity_rules))
                else:
                    new_kvrecord = {
                        "_key": key,
                        "object_category": f"splk-{component}",
                        "object": object_value,
                        "confidence": "pending",
                        "confidence_reason": "pending",
                        "is_disabled": 0,
                        "mtime": time.time(),
                        "entities_outliers": json.dumps(entities_outliers, indent=4),
                    }
                    collection_rules.data.insert(json.dumps(new_kvrecord))

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "action": "add",
                    "result": "success",
                    "model_definition": {
                        "score": score,
                        "kpi_metric": kpi_metric,
                        "kpi_span": kpi_span,
                        "method_calculation": method_calculation,
                        "density_lowerthreshold": density_lowerthreshold,
                        "density_upperthreshold": density_upperthreshold,
                        "alert_lower_breached": alert_lower_breached,
                        "alert_upper_breached": alert_upper_breached,
                        "period_calculation": period_calculation,
                        "period_calculation_latest": period_calculation_latest,
                        "time_factor": time_factor,
                        "auto_correct": auto_correct,
                        "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                        "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                        "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                        "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                        "static_lower_threshold": static_lower_threshold,
                        "static_upper_threshold": static_upper_threshold,
                    },
                    "message": f'the model="{model}" was successfully added to the outliers rules',
                }
                records.append(result)

            except Exception as e:
                logger.error(
                    f'failed to add the new model to the dictionary with exception="{str(e)}"'
                )

                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                result = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "action": "add",
                    "result": "failure",
                    "model_definition": {
                        "score": score,
                        "kpi_metric": kpi_metric,
                        "kpi_span": kpi_span,
                        "method_calculation": method_calculation,
                        "density_lowerthreshold": density_lowerthreshold,
                        "density_upperthreshold": density_upperthreshold,
                        "alert_lower_breached": alert_lower_breached,
                        "alert_upper_breached": alert_upper_breached,
                        "period_calculation": period_calculation,
                        "period_calculation_latest": period_calculation_latest,
                        "time_factor": time_factor,
                        "auto_correct": auto_correct,
                        "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                        "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                        "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                        "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                        "static_lower_threshold": static_lower_threshold,
                        "static_upper_threshold": static_upper_threshold,
                    },
                    "exception": f'failed to add the new model to the dictionary with exception="{str(e)}"',
                }
                records.append(result)

            # log debug
            logger.debug(
                f'final dict, entity_rules="{json.dumps(entities_outliers, indent=4)}"'
            )

            # render HTTP status and summary

            req_summary = {
                "process_count": processed_count,
                "success_count": succcess_count,
                "failures_count": failures_count,
                "records": records,
            }

            if processed_count > 0 and processed_count == succcess_count:
                # log
                logger.info(
                    f'ML model was added successfully, summary="{json.dumps(req_summary, indent=4)}"'
                )

                # audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "add ML models",
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(req_summary, indent=1)),
                        "ML model was added successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                return {"payload": req_summary, "status": 200}

            else:
                # log
                logger.error(
                    f'ML model could not be added, summary="{json.dumps(req_summary, indent=4)}"'
                )

                # audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "add ML models",
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(req_summary, indent=1)),
                        "ML model could not be added",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                return {"payload": req_summary, "status": 500}

    # delete one or more ML models
    def post_outliers_delete_models(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                # Accept either object_id or object (prefer object_id)
                object_id = resp_dict.get("object_id", None)
                object_value = resp_dict.get("object", None)
                if not object_id and not object_value:
                    return {"payload": "either object_id or object is required", "status": 500}
                try:
                    models_list = resp_dict["models_list"]
                    # if not a list already, convert to a list from comma separated string
                    if not isinstance(models_list, list):
                        models_list = models_list.split(",")
                except Exception as e:
                    return {"payload": "models_list is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint deletes or more existing ML models, it requires a POST call with the following options:",
                "resource_desc": "Delete a Machine Learning outliers model",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_delete_models\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'object': 'netscreen:netscreen:firewall', 'models_list': 'model_xxxxxxxxxx'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "(optional) entity name",
                        "object_id": "(optional) entity identifier (preferred over object)",
                        "models_list": "(required) Comma separated list of models identifiers to be deleted",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Data collection
        collection_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection = service.kvstore[collection_name]

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        key = None
        try:
            # Define the KV query - use object_id if available, otherwise object
            if object_id:
                # Query by object_id (_key)
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "_key": object_id,
                        }
                    ]
                }
            else:
                # Query by object
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "object": object_value,
                        }
                    ]
                }

            entity_rules = collection.data.query(query=json.dumps(query_string))[0]
            key = entity_rules.get("_key")
            # Get object_value from KVstore if object_id was used
            if object_id and not object_value:
                object_value = entity_rules.get("object", "")

        except Exception as e:
            key = None

        # Render result
        if key:
            logger.debug(entity_rules)

            # Load as a dict
            try:
                entities_outliers = json.loads(entity_rules.get("entities_outliers"))
            except Exception as e:
                msg = f'Failed to load entities_outliers with exception="{str(e)}"'
                logger.error(msg)
                return {"payload": msg, "status": 500}

            # log debug
            logger.debug(
                f'entities_outliers="{json.dumps(entities_outliers, indent=4)}"'
            )

            # loop through the models
            for model in models_list:
                try:
                    model_dict = entities_outliers[model]

                    # log debug
                    logger.debug(f'model_dict="{json.dumps(model_dict, indent=4)}"')

                    # delete from the dict
                    del entities_outliers[model]

                    # if the last model from the rules was deleted, Ml is not ready any longer
                    if not len(entities_outliers) > 2:
                        last_exec = "pending"
                    else:
                        last_exec = entity_rules.get("last_exec")

                    # Update the record
                    entity_rules["entities_outliers"] = json.dumps(
                        entities_outliers, indent=4
                    )
                    entity_rules["mtime"] = time.time()
                    entity_rules["last_exec"] = last_exec
                    collection.data.update(str(key), json.dumps(entity_rules))

                    # increment counter
                    processed_count += 1
                    succcess_count += 1
                    failures_count += 0

                    # append for summary
                    result = {
                        "tenant_id": tenant_id,
                        "object_category": f"splk-{component}",
                        "object": object_value,
                        "action": "delete",
                        "result": "success",
                        "message": f'the model="{model}" was successfully deleted from the outliers rules',
                    }
                    records.append(result)

                except Exception as e:
                    logger.error(
                        f'model="{model}" could not be found in the entity_rules="{json.dumps(entities_outliers, indent=4)}"'
                    )

                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    result = {
                        "tenant_id": tenant_id,
                        "object_category": f"splk-{component}",
                        "object": object_value,
                        "action": "delete",
                        "result": "failure",
                        "exception": f'the model="{model}" could not be found in the outliers rules',
                    }
                    records.append(result)

            # log debug
            logger.debug(
                f'final dict, entity_rules="{json.dumps(entities_outliers, indent=4)}"'
            )

            # render HTTP status and summary

            req_summary = {
                "process_count": processed_count,
                "success_count": succcess_count,
                "failures_count": failures_count,
                "records": records,
            }

            if processed_count > 0 and processed_count == succcess_count:
                # log
                logger.info(
                    f'ML models were deleted successfully, summary="{json.dumps(req_summary, indent=4)}"'
                )

                # audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "delete ML models",
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(req_summary, indent=1)),
                        "ML models were deleted successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                return {"payload": req_summary, "status": 200}

            else:
                # log
                logger.error(
                    f'ML models could not be deleted, summary="{json.dumps(req_summary, indent=4)}"'
                )

                # audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "delete ML models",
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(req_summary, indent=1)),
                        "ML models could not be deleted",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                return {"payload": req_summary, "status": 500}

        else:
            msg = f'No record found for this object, query_string="{json.dumps(query_string, indent=2)}", collection="{collection_name}"'
            logger.error(msg)
            return {"payload": {"response": msg}, "status": 404}

    # update one or more ML models
    def post_outliers_update_models(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                # Accept either object_id or object (prefer object_id)
                object_id = resp_dict.get("object_id", None)
                object_value = resp_dict.get("object", None)
                if not object_id and not object_value:
                    return {"payload": "either object_id or object is required", "status": 500}
                try:
                    outliers_rules = resp_dict["outliers_rules"]
                except Exception as e:
                    return {"payload": "outliers_rules is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint updates existing ML models rules, it requires a POST call with the following options:",
                "resource_desc": "Update a Machine Learning outliers model",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_update_models\" body=\"{'tenant_id':'mytenant','component':'dsm','object':'netscreen:netscreen:firewall','outliers_rules':'<redacted_json_dict>'}",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "(optional) entity name",
                        "object_id": "(optional) entity identifier (preferred over object)",
                        "outliers_rules": "(required) The JSON array object containing the outliers rules",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Data collection
        collection_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection = service.kvstore[collection_name]

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        key = None
        try:
            # Define the KV query - use object_id if available, otherwise object
            if object_id:
                # Query by object_id (_key)
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "_key": object_id,
                        }
                    ]
                }
            else:
                # Query by object
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "object": object_value,
                        }
                    ]
                }

            entity_rules = collection.data.query(query=json.dumps(query_string))[0]
            key = entity_rules.get("_key")
            # Get object_value from KVstore if object_id was used
            if object_id and not object_value:
                object_value = entity_rules.get("object", "")

        except Exception as e:
            key = None

        # Render result
        if key:
            logger.debug(entity_rules)

            # Load as a dict
            try:
                entities_outliers = json.loads(entity_rules.get("entities_outliers"))
            except Exception as e:
                msg = f'Failed to load entities_outliers with exception="{str(e)}"'
                logger.error(msg)
                return {"payload": msg, "status": 500}

            # log debug
            logger.debug(
                f'before update, entities_outliers="{json.dumps(entities_outliers, indent=4)}"'
            )

            #
            # Process update
            #

            # load the JSON update as a dict
            logger.debug(f'outliers_rules="{outliers_rules}"')

            # Per-call diff accumulator. Layer 2 of the May 2026
            # ML-Advisor-loop fix: the AI Advisor and any other caller
            # needs a definitive "what actually changed on disk" answer
            # so it can detect ineffective writes (sparse update payloads,
            # values identical to current state, etc.) without re-reading
            # the model. Returned alongside ``entities_outliers`` in the
            # success payload at the bottom of this method.
            per_model_diffs = {}

            for outliers_rule in outliers_rules:
                # log debug
                logger.debug(f'outliers_rule_update="{outliers_rule}"')

                # get the model_id
                model_id = outliers_rule.get("model_id")

                # log debug
                logger.debug(f'Handling model_id="{model_id}"')

                # Snapshot the model's pre-update state for the diff
                # report. Shallow copy is sufficient — every field in
                # ``fields_list`` is a scalar (str / int / float / bool /
                # None); the only nested structure on these records is
                # ``period_exclusions`` which this method does not touch.
                pre_update_snapshot = dict(entities_outliers.get(model_id, {}))

                # Update the main dict
                fields_list = [
                    "score",
                    "kpi_metric",
                    "kpi_span",
                    "method_calculation",
                    "period_calculation",
                    "period_calculation_latest",
                    "time_factor",
                    "density_lowerthreshold",
                    "density_upperthreshold",
                    "alert_lower_breached",
                    "alert_upper_breached",
                    "auto_correct",
                    "perc_min_lowerbound_deviation",
                    "perc_min_upperbound_deviation",
                    "min_value_for_lowerbound_breached",
                    "min_value_for_upperbound_breached",
                    "static_lower_threshold",
                    "static_upper_threshold",
                    "algorithm",
                    "boundaries_extraction_macro",
                    "fit_extra_parameters",
                    "apply_extra_parameters",
                    "is_disabled",
                    "ai_mladvisor_disabled",
                ]
                for field in fields_list:
                    if field in ("time_factor"):
                        entities_outliers[model_id][field] = urllib.parse.unquote(
                            outliers_rule.get(field)
                        )
                    elif field in (
                        "min_value_for_lowerbound_breached",
                        "min_value_for_upperbound_breached",
                    ):
                        entities_outliers[model_id][field] = outliers_rule.get(field, 0)
                    # fields fit_extra_parameters and apply_extra_parameters are optional
                    elif field in ("fit_extra_parameters", "apply_extra_parameters"):
                        if field in outliers_rule:
                            entities_outliers[model_id][field] = outliers_rule.get(
                                field
                            )
                    else:
                        entities_outliers[model_id][field] = outliers_rule.get(field)

                # Coerce string values from the frontend to proper numeric types
                for field in fields_list:
                    val = entities_outliers[model_id].get(field)
                    if val is not None:
                        try:
                            if field in OUTLIER_FLOAT_FIELDS:
                                entities_outliers[model_id][field] = float(val)
                            elif field in OUTLIER_INT_FIELDS:
                                # Use int(float(val)) to handle float-formatted strings like "1.0"
                                entities_outliers[model_id][field] = int(float(val))
                        except (ValueError, TypeError):
                            pass  # keep original if conversion fails (e.g. sentinel strings)

                # Diff: compare pre/post snapshots for every field in
                # ``fields_list`` and record what actually moved. Compare
                # via str() to absorb the int/float/bool round-trip
                # through urllib unquoting and Splunk KV serialisation.
                # ``changed_fields`` is the source of truth for callers
                # that need to detect ineffective writes; ``unchanged_in_request``
                # surfaces the subset of fields the caller named but
                # whose values matched current state (a hint that the
                # caller's payload was a no-op for that field).
                post_update_snapshot = entities_outliers.get(model_id, {})
                changed_fields = {}
                unchanged_in_request = []
                for field in fields_list:
                    pre_v = pre_update_snapshot.get(field)
                    post_v = post_update_snapshot.get(field)
                    if str(pre_v) != str(post_v):
                        changed_fields[field] = {"from": pre_v, "to": post_v}
                    elif field in outliers_rule:
                        unchanged_in_request.append(field)
                per_model_diffs[model_id] = {
                    "changed_fields": changed_fields,
                    "unchanged_in_request": unchanged_in_request,
                }

            # log debug
            logger.debug(
                f'after update, entities_outliers="{json.dumps(entities_outliers, indent=4)}"'
            )

            # Finally, update the KVstore record
            try:
                # Update the record
                entity_rules["entities_outliers"] = json.dumps(
                    entities_outliers, indent=4
                )
                collection.data.update(str(key), json.dumps(entity_rules))

                # Aggregate "did anything actually change" across every
                # model in this batch. ``any_changes_applied`` is the
                # single boolean callers like the AI Advisor's
                # ``update_model_rules`` tool use to detect ineffective
                # writes without parsing the per-model diff.
                any_changes_applied = any(
                    bool(d.get("changed_fields"))
                    for d in per_model_diffs.values()
                )

                # final
                result_record = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "results": "ML models were successfully updated",
                    "failures_count": 0,
                    "entities_outliers": entities_outliers,
                    "per_model_diffs": per_model_diffs,
                    "any_changes_applied": any_changes_applied,
                }

                # log
                logger.info(json.dumps(result_record, indent=4))

                # audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "update ML models",
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(result_record, indent=1)),
                        "ML models were updated successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                return {"payload": result_record, "status": 200}

            except Exception as e:
                result_record = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "results": "Failed to update the KVstore record",
                    "failures_count": 1,
                    "exception": str(e),
                }
                logger.error(json.dumps(result_record, indent=4))
                return {"payload": result_record, "status": 500}

        else:
            msg = "No record found for this object"
            logger.error(msg)
            return {"payload": msg, "status": 404}

    # Add an exclusion period to the ML model
    def post_outliers_manage_model_period_exclusion(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # required in all cases
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                # Accept either object_id or object (prefer object_id)
                object_id = resp_dict.get("object_id", None)
                object_value = resp_dict.get("object", None)
                if not object_id and not object_value:
                    return {"payload": "either object_id or object is required", "status": 500}
                try:
                    model_id = resp_dict["model_id"]
                except Exception as e:
                    return {
                        "payload": "model_id is required, use all or * to match all models from this object",
                        "status": 500,
                    }

                action = resp_dict["action"]
                # action value can be add or delete
                if not action in ("add", "delete", "show"):
                    msg = f'action="{action}" is not valid, it must be either "add", "delete" or "show"'
                    logger.error(msg)
                    return {"payload": msg, "status": 500}

                # required for delete, this can be given as a list of comma separated values, check if it is a list and otherwise turn it as a proper list
                period_exclusion_id = resp_dict.get("period_exclusion_id", None)
                if period_exclusion_id:
                    if not isinstance(period_exclusion_id, list):
                        period_exclusion_id = period_exclusion_id.split(",")

                # required for addition
                earliest = resp_dict.get("earliest", None)
                latest = resp_dict.get("latest", None)

                # if action is delete, the period_exclude_id is required
                if action == "delete":
                    if not period_exclusion_id:
                        msg = f'action="{action}" requires period_exclusion_id to be defined'
                        logger.error(msg)
                        return {"payload": msg, "status": 500}

                # if action is add, earliest and latest are required
                if action == "add":
                    if not earliest or not latest:
                        msg = f'action="{action}" requires earliest and latest to be defined'
                        logger.error(msg)
                        return {"payload": msg, "status": 500}
                    # earliest and latest accept several forms (see parse_user_datetime
                    # for the canonical list): epoch seconds, ISO date strings, "now",
                    # or relative tokens like "-30d". The preferred LLM-facing form is
                    # an ISO date string — see add_period_exclusion in
                    # trackme_ai_agent_tools.py for why.
                    try:
                        earliest = parse_user_datetime(earliest)
                    except ValueError as e:
                        msg = f'action="{action}" earliest is invalid: {e}'
                        logger.error(msg)
                        return {"payload": msg, "status": 400}
                    try:
                        latest = parse_user_datetime(latest)
                    except ValueError as e:
                        msg = f'action="{action}" latest is invalid: {e}'
                        logger.error(msg)
                        return {"payload": msg, "status": 400}

                    # also verify that earliest is not lower than latest, the earliest epochtime cannot be before the latest epochtime
                    if not earliest < latest:
                        msg = f'action="{action}" requires earliest to be before latest, earliest="{earliest}", latest="{latest}"'
                        logger.error(msg)
                        return {"payload": msg, "status": 400}

                    # Reject windows that lie in the future — an exclusion can only
                    # refer to data that already exists.  Both edges of the window
                    # must be in the past: gating only ``earliest`` would let
                    # ``earliest=-1d, latest=now+1d`` slip through and contradict
                    # the describe-string contract ("Future-dated windows are
                    # rejected").
                    now_epoch = int(time.time())
                    if earliest > now_epoch:
                        msg = (
                            f'action="{action}" requires earliest to be in the past, '
                            f'earliest={earliest} (now={now_epoch})'
                        )
                        logger.error(msg)
                        return {"payload": msg, "status": 400}
                    if latest > now_epoch:
                        msg = (
                            f'action="{action}" requires latest to be in the past, '
                            f'latest={latest} (now={now_epoch})'
                        )
                        logger.error(msg)
                        return {"payload": msg, "status": 400}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint manages period-of-exclusion entries for a given ML model — used to mask known-bad windows (deployments, incidents, maintenance) so the model's training set ignores them. Three actions are supported: 'add' (create a new exclusion window), 'delete' (remove existing windows by period_exclusion_id), and 'show' (return the current exclusions). Future-dated windows are rejected — exclusions can only refer to data that already exists.",
                "resource_desc": "Add, delete, or list period-of-exclusion entries for a given ML model",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_manage_model_period_exclusion\" body=\"{'tenant_id':'mytenant','component':'dsm','object':'netscreen:netscreen:firewall','model_id':'<model_id>','action':'add','earliest':'2026-01-01T00:00','latest':'2026-01-02T00:00'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "REQUIRED. The component category (one of: dsm, dhm, mhm, flx, fqm, wlk)",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative — preferred when known). The entity KV record _key. Either object or object_id must be provided",
                        "action": "REQUIRED. One of: add, delete, show",
                        "model_id": "REQUIRED. The model identifier. Use 'all' or '*' to match every model on this entity",
                        "earliest": "REQUIRED when action=add. The earliest time of the window to exclude. Accepted forms: epoch seconds (e.g. 1769644800), ISO 'YYYY-MM-DD' / 'YYYY-MM-DDTHH:MM' / 'YYYY-MM-DDTHH:MM:SS' (interpreted as local-time naive), the literal 'now', or relative tokens '-Ns' / '-Nm' / '-Nh' / '-Nd' / '-Nw' (e.g. '-30d'). The preferred LLM-facing form is an ISO date string",
                        "latest": "REQUIRED when action=add. The latest time of the window to exclude. Same accepted forms as 'earliest'. Must be strictly greater than 'earliest', and the window must not extend into the future",
                        "period_exclusion_id": "REQUIRED when action=delete. The period exclusion identifier(s) to delete. Can be provided as a single value or as a comma-separated list",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Data collection
        collection_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection = service.kvstore[collection_name]

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        key = None
        try:
            # Define the KV query - use object_id if available, otherwise object
            if object_id:
                # Query by object_id (_key)
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "_key": object_id,
                        }
                    ]
                }
            else:
                # Query by object
                query_string = {
                    "$and": [
                        {
                            "object_category": f"splk-{component}",
                            "object": object_value,
                        }
                    ]
                }

            object_rules_definition = collection.data.query(
                query=json.dumps(query_string)
            )[0]
            key = object_rules_definition.get("_key")
            # Get object_value from KVstore if object_id was used
            if object_id and not object_value:
                object_value = object_rules_definition.get("object", "")

        except Exception as e:
            key = None

        # Render result
        if key:
            logger.debug(object_rules_definition)

            # Load as a dict
            try:
                entities_outliers = json.loads(
                    object_rules_definition.get("entities_outliers")
                )
            except Exception as e:
                msg = f'Failed to load entities_outliers with exception="{str(e)}"'
                logger.error(msg)
                return {"payload": msg, "status": 500}

            # log debug
            logger.debug(
                f'before update, entities_outliers="{json.dumps(entities_outliers, indent=4)}"'
            )

            #
            # Process update
            #

            # load the JSON update as a dict
            logger.debug(
                f'entities_outliers="{json.dumps(entities_outliers, indent=2)}"'
            )

            # boolean to check if model_id exists
            model_id_exists = False

            for entity_model_id in entities_outliers:
                logger.debug(f'model_id="{entity_model_id}"')

                entity_rules = entities_outliers[entity_model_id]
                logger.debug(f'entity_rules="{json.dumps(entity_rules, indent=2)}"')

                # if the model_id does not match, break
                if entity_model_id != model_id and not model_id in ("all", "*"):
                    continue
                else:
                    model_id_exists = True

                # log debug
                logger.debug(f'Handling model_id="{entity_model_id}"')

                # Get the current period_exclusions record (list)
                period_exclusions = entity_rules.get("period_exclusions", [])

                # if action is add
                if action == "add":
                    # Validate the requested window against this model's training
                    # horizon — otherwise the trainer will silently drop the
                    # exclusion at next run (see train_mlmodel rejection branch).
                    # Surface a 4xx so the caller (REST client or AI agent tool)
                    # can correct the window instead of getting a false-success.
                    period_calculation = entity_rules.get("period_calculation", "-30d")
                    cutoff_epoch = get_training_window_cutoff_epoch(period_calculation)
                    if int(latest) < cutoff_epoch:
                        msg = (
                            f'action="add" rejected: latest={latest} '
                            f'({time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(int(latest)))}) '
                            f'is older than this model\'s training-window cutoff '
                            f'{cutoff_epoch} '
                            f'({time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(cutoff_epoch))}). '
                            f'period_calculation="{period_calculation}" — exclusions whose latest '
                            f'falls before the cutoff would be silently dropped at training time. '
                            f'Provide a window whose latest is after the cutoff.'
                        )
                        logger.error(
                            f'tenant_id="{tenant_id}", component="{component}", '
                            f'object="{object_value}", model_id="{entity_model_id}": {msg}'
                        )
                        return {"payload": msg, "status": 400}

                    # add our object to the list

                    # period_exclusion_id, generate the sha256 hash of earliest:latest, use this to detect if the period was excluded already
                    period_exclusion_id = hashlib.sha256(
                        f"{earliest}:{latest}".encode()
                    ).hexdigest()

                    # boolean
                    period_exclusion_id_exists = False

                    if len(period_exclusions) > 0:
                        for period_exclusion in period_exclusions:
                            if (
                                period_exclusion["period_exclusion_id"]
                                == period_exclusion_id
                            ):
                                period_exclusion_id_exists = True
                                logger.info(
                                    f'period_exclusion_id="{period_exclusion_id}" already exists, skipping'
                                )
                                continue

                    if not period_exclusion_id_exists:
                        # add the new period
                        period_exclusions.append(
                            {
                                "period_exclusion_id": period_exclusion_id,
                                "earliest": earliest,
                                "earliest_human": time.strftime(
                                    "%c", time.localtime(float(earliest))
                                ),
                                "latest": latest,
                                "latest_human": time.strftime(
                                    "%c", time.localtime(float(latest))
                                ),
                                "ctime": str(round(time.time(), 0)),
                            }
                        )

                # if action is delete, verify the period_exclusion_id exists in the list, if so delete it
                elif action == "delete":
                    # delete the period_exclusion_id from the list
                    for item in period_exclusion_id:
                        logger.debug(f'checking item: "{item}"')
                        # Create a list of items to remove to avoid modifying during iteration
                        items_to_remove = []
                        for period_exclusion in period_exclusions:
                            if period_exclusion["period_exclusion_id"] == item.strip():
                                logger.debug(f'deleting item: "{item}"')
                                items_to_remove.append(period_exclusion)

                        # Remove the collected items
                        for item_to_remove in items_to_remove:
                            period_exclusions.remove(item_to_remove)

                # if action is show, return the period_exclusions list
                elif action == "show":
                    response_list = []
                    # loop through the period_exclusions, add each as a dict to the response_list (model_id, period_exclusion_id, earliest, latest))
                    for period_exclusion in period_exclusions:
                        response_list.append(
                            {
                                "model_id": model_id,
                                "period_exclusion_id": period_exclusion.get(
                                    "period_exclusion_id"
                                ),
                                "earliest": period_exclusion.get("earliest"),
                                "earliest_human": period_exclusion.get(
                                    "earliest_human"
                                ),
                                "latest": period_exclusion.get("latest"),
                                "latest_human": period_exclusion.get("latest_human"),
                                "ctime": period_exclusion.get("ctime"),
                                "ctime_human": time.strftime(
                                    "%c",
                                    time.localtime(
                                        float(period_exclusion.get("ctime"))
                                    ),
                                ),
                            }
                        )
                    return {
                        "payload": response_list,
                        "status": 200,
                    }

                # update the entity_rule record
                entity_rules["period_exclusions"] = period_exclusions

                # update the entities_outliers dict
                entities_outliers[entity_model_id] = entity_rules

                # log
                logger.debug(
                    f'post update entities_outliers="{json.dumps(entities_outliers, indent=2)}"'
                )

            # if model_id does not exist, return a 500 payload
            if not model_id_exists and not model_id in ("all", "*"):
                error_msg = (
                    f'The model_id="{model_id}" does not exist in the outliers rules'
                )
                logger.error(error_msg)
                return {"payload": error_msg, "status": 500}

            # log debug
            logger.debug(
                f'after update, entities_outliers="{json.dumps(entities_outliers, indent=4)}"'
            )

            # update the object record
            object_rules_definition["entities_outliers"] = json.dumps(
                entities_outliers, indent=2
            )

            # Finally, update the KVstore record
            try:
                # Update the record
                collection.data.update(str(key), json.dumps(object_rules_definition))

                # final
                if action == "add":
                    msg = "Exclusion period for ML model was successfully added"
                    msg_audit_title = "add ML model exclusion period"
                elif action == "delete":
                    msg = "Exclusion period for ML model was successfully deleted"
                    msg_audit_title = "delete ML model exclusion period"

                result_record = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "results": msg,
                    "failures_count": 0,
                    "entities_outliers": entities_outliers,
                }

                # log
                logger.info(json.dumps(result_record, indent=4))

                # audit

                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        msg_audit_title,
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(result_record, indent=1)),
                        "ML models were updated successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                return {"payload": result_record, "status": 200}

            except Exception as e:
                result_record = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "results": "Failed to update the KVstore record",
                    "failures_count": 1,
                    "exception": str(e),
                }
                logger.error(json.dumps(result_record, indent=4))
                return {"payload": result_record, "status": 500}

        else:
            msg = "No record found for this object"
            logger.error(msg)
            return {"payload": msg, "status": 404}

    # reset ML models
    def post_outliers_reset_models(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}
                # Accept either object_id or object (prefer object_id)
                object_id = resp_dict.get("object_id", None)
                object_param = resp_dict.get("object", None)
                object_value = None  # Initialize to None, will be set based on preference
                
                if object_id:
                    # object_id provided - will look up object value later (preferred method)
                    object_value = None  # Will be resolved after service connection
                elif object_param:
                    # object provided (fallback)
                    object_value = object_param
                else:
                    return {"payload": "either object_id or object is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint resets ML models rules, it requires a POST call with the following options:",
                "resource_desc": "Reset all ML outliers models for a given entity",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_reset_models\" body=\"{'tenant_id':'mytenant','component':'dsm','object':'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "REQUIRED. The component category (one of: dsm, dhm, mhm, flx, fqm, wlk)",
                        "object": "REQUIRED (with object_id as alternative). The entity name. Either object or object_id must be provided",
                        "object_id": "REQUIRED (with object as alternative — preferred when known). The entity KV record _key. Either object or object_id must be provided",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # If object_id was provided, look up the object value from KV store
        if object_id and not object_value:
            try:
                # Try to get object from rules collection first (both collections should have the same object)
                collection_rules_name_temp = (
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                )
                collection_rule_temp = service.kvstore[collection_rules_name_temp]
                
                # Query by _key (object_id)
                query_string_temp = {"_key": object_id}
                records = collection_rule_temp.data.query(query=json.dumps(query_string_temp))
                
                # Try rules collection first
                if records and len(records) > 0:
                    object_value = records[0].get("object")
                
                # If not found in rules collection, try data collection as fallback
                if not object_value:
                    collection_data_name = (
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
                    )
                    collection_data = service.kvstore[collection_data_name]
                    records_data = collection_data.data.query(query=json.dumps(query_string_temp))
                    if records_data and len(records_data) > 0:
                        object_value = records_data[0].get("object")
                
                if not object_value:
                    return {
                        "payload": f'object_id="{object_id}" not found in KV store',
                        "status": 500,
                    }
            except Exception as e:
                return {
                    "payload": f'Failed to look up object from object_id, exception="{str(e)}"',
                    "status": 500,
                }

        # entity rules collection
        collection_entity_rules_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_entity_rules = service.kvstore[collection_entity_rules_name]

        # data rules collection
        collection_entity_data_name = (
            f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
        )
        collection_entity_data = service.kvstore[collection_entity_data_name]

        # Define the KV query
        query_string = {
            "$and": [
                {
                    "object_category": f"splk-{component}",
                    "object": object_value,
                }
            ]
        }

        # get the entity_rules record
        try:
            kvrecord_entity_rules = collection_entity_rules.data.query(
                query=json.dumps(query_string)
            )[0]
            kvrecord_entity_rules_key = kvrecord_entity_rules.get("_key")
        except Exception as e:
            kvrecord_entity_rules_key = None

        # get the entity_data record
        try:
            kvrecord_entity_data = collection_entity_data.data.query(
                query=json.dumps(query_string)
            )[0]
            kvrecord_entity_data_key = kvrecord_entity_data.get("_key")
        except Exception as e:
            kvrecord_entity_data_key = None

        #
        # proceed
        #

        # first, reset the entity_data record, if any
        kvrecord_entity_data_deleted = False
        if kvrecord_entity_data_key:
            try:
                collection_entity_data.data.delete(
                    json.dumps({"_key": kvrecord_entity_data_key})
                )
                logger.info(
                    f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", collection="{collection_entity_rules_name}", deleted key="{kvrecord_entity_data_key}"'
                )
                kvrecord_entity_data_deleted = True
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", collection="{collection_entity_rules_name}", failed to deleted key="{kvrecord_entity_data_key}" with exception="{str(e)}"'
                )

        # secondly, purge and re-generate ML models
        kvrecord_entity_rules_deleted = False
        if kvrecord_entity_rules_key:
            #
            # Process reset
            #

            try:
                collection_entity_rules.data.delete(
                    json.dumps({"_key": kvrecord_entity_rules_key})
                )
                logger.info(
                    f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", collection="{collection_entity_data_name}", deleted key="{kvrecord_entity_rules_key}"'
                )
                kvrecord_entity_rules_deleted = True
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", collection="{collection_entity_data_name}", failed to deleted key="{kvrecord_entity_rules_key}" with exception="{str(e)}"'
                )
                kvrecord_entity_rules_deleted = False

                result_record = {
                    "tenant_id": tenant_id,
                    "object_category": f"splk-{component}",
                    "object": object_value,
                    "results": "Failed to delete the KVstore record this entity, cannot proceed to reset",
                    "failures_count": 1,
                    "exception": str(e),
                }
                logger.error(json.dumps(result_record, indent=4))
                return {"payload": result_record, "status": 500}

        else:
            logger.info(
                f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", no KVstore record was found to be deleted'
            )

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        # Search query reset
        searchquery_reset = remove_leading_spaces(
            f"""\
            | makeresults | head 1
            | eval tenant_id="{tenant_id}", object_category="splk-{component}", object="{object_value}", key="{kvrecord_entity_rules_key}"
            | trackmesplkoutlierssetrules tenant_id="{tenant_id}" component="{component}"
            """
        )

        # log debug
        logger.debug(
            f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", searchquery_reset="{searchquery_reset}"'
        )

        # run search
        reset_results = []
        try:
            # spawn the search and get the results
            reader = run_splunk_search(
                service,
                searchquery_reset,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    reset_results.append(item)

            # final
            result_record = {
                "tenant_id": tenant_id,
                "object_category": f"splk-{component}",
                "object": object_value,
                "results": "ML models were successfully reset",
                "failures_count": 0,
                "reset_results": reset_results,
                "searchquery_reset": searchquery_reset,
                "entity_rules_deleted": kvrecord_entity_rules_deleted,
                "entity_data_deleted": kvrecord_entity_data_deleted,
            }

            # log
            logger.info(json.dumps(result_record, indent=4))

            # audit
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "reset ML models",
                str(object_value),
                f"splk-{component}",
                str(json.dumps(result_record, indent=1)),
                "ML models were reset successfully",
                str(update_comment),
            )

            return {"payload": result_record, "status": 200}

        except Exception as e:
            # permanent failure
            result_record = {
                "tenant_id": tenant_id,
                "object_category": f"splk-{component}",
                "object": object_value,
                "results": "Failed to reset ML models for this entity",
                "failures_count": 1,
                "entity_rules_deleted": kvrecord_entity_rules_deleted,
                "entity_data_deleted": kvrecord_entity_data_deleted,
                "exception": str(e),
            }
            logger.error(json.dumps(result_record, indent=4))
            return {"payload": result_record, "status": 500}

    # train ML models
    def post_outliers_train_models(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                # Accept object_list or object_id_list (lists only)
                object_list = resp_dict.get("object_list", None)
                object_id_list = resp_dict.get("object_id_list", None)
                
                # Handle list conversion if string is provided
                if object_list and not isinstance(object_list, list):
                    if isinstance(object_list, str):
                        object_list = object_list.split(",") if object_list else None
                    else:
                        return {"payload": f"object_list must be a list or comma-separated string, got {type(object_list).__name__}", "status": 500}
                if object_id_list and not isinstance(object_id_list, list):
                    if isinstance(object_id_list, str):
                        object_id_list = object_id_list.split(",") if object_id_list else None
                    else:
                        return {"payload": f"object_id_list must be a list or comma-separated string, got {type(object_id_list).__name__}", "status": 500}
                
                if not object_list and not object_id_list:
                    return {"payload": "either object_list or object_id_list is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint trains ML models rules for a list of entities, it requires a POST call with the following options:",
                "resource_desc": "Train all ML outliers models for a given list of entities (processed sequentially)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_train_models\" body=\"{'tenant_id':'mytenant','component':'dsm','object_list':['entity1','entity2']}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object_list": "(required unless using object_id_list) list of entity names",
                        "object_id_list": "(required unless using object_list) list of entity identifiers",
                        "update_comment": "(optional) comment for audit trail",
                    }
                ],
                "note": "Entities are processed sequentially (one after another) in a background thread. This is a fire-and-forget operation.",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Define background worker function for sequential processing
        def background_train_worker(
            tenant_id,
            component,
            object_list,
            object_id_list,
            service,
            request_info,
            update_comment,
        ):
            """Background worker function for sequential ML training"""
            try:
                processed_count = 0
                success_count = 0
                failures_count = 0
                results_summary = []

                # Build list of entities to process
                entities_to_process = []
                if object_id_list:
                    # Use object_id_list, resolve object names from KVstore
                    collection_name = (
                        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                    )
                    collection = service.kvstore[collection_name]
                    
                    for object_id in object_id_list:
                        try:
                            entity_rules = collection.data.query_by_id(object_id)
                            object_value = entity_rules.get("object", "")
                            entities_to_process.append({
                                "object_id": object_id,
                                "object": object_value,
                            })
                        except Exception as e:
                            logger.warning(f"Could not resolve object_id={object_id}, using as-is: {str(e)}")
                            entities_to_process.append({
                                "object_id": object_id,
                                "object": "",
                            })
                elif object_list:
                    # Use object_list, resolve object_ids from KVstore
                    collection_name = (
                        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                    )
                    collection = service.kvstore[collection_name]
                    
                    for object_value in object_list:
                        try:
                            query_string = {
                                "$and": [
                                    {
                                        "object_category": f"splk-{component}",
                                        "object": object_value,
                                    }
                                ]
                            }
                            entity_rules = collection.data.query(query=json.dumps(query_string))
                            if entity_rules and len(entity_rules) > 0:
                                key = entity_rules[0].get("_key")
                                entities_to_process.append({
                                    "object_id": key,
                                    "object": object_value,
                                })
                            else:
                                entities_to_process.append({
                                    "object_id": None,
                                    "object": object_value,
                                })
                        except Exception as e:
                            logger.warning(f"Could not resolve object={object_value}, using as-is: {str(e)}")
                            entities_to_process.append({
                                "object_id": None,
                                "object": object_value,
                            })

                # Process entities sequentially
                for entity in entities_to_process:
                    object_value = entity.get("object", "")
                    object_id = entity.get("object_id", None)
                    processed_count += 1

                    try:
                        # Determine object_param for SPL query
                        if object_id:
                            object_param = f'object_id="{object_id}"'
                        else:
                            object_param = f'object="{object_value}"'

                        # Define the SPL query
                        kwargs_search = {
                            "app": "trackme",
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        }
                        searchquery = f'| trackmesplkoutlierstrain tenant_id="{tenant_id}" component="{component}" {object_param}'
                        
                        log_object_ref = f'object_id="{object_id}"' if object_id else f'object="{object_value}"'
                        logger.debug(
                            f'Processing ML train: tenant_id="{tenant_id}", component="{component}", {log_object_ref}, searchquery="{searchquery}"'
                        )

                        query_results = []
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
                                query_results.append(item)

                        # Get object value from KVstore if object_id was used and object_value is empty
                        if object_id and not object_value:
                            try:
                                collection_name = (
                                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                                )
                                collection = service.kvstore[collection_name]
                                entity_rules = collection.data.query_by_id(object_id)
                                object_value = entity_rules.get("object", "")
                            except Exception as e:
                                object_value = ""

                        result_record = {
                            "tenant_id": tenant_id,
                            "object_category": f"splk-{component}",
                            "object": object_value,
                            "object_id": object_id,
                            "results": "ML models were successfully trained",
                            "failures_count": 0,
                            "query_results": query_results,
                        }

                        logger.info(json.dumps(result_record, indent=4))
                        results_summary.append(result_record)
                        success_count += 1

                        # audit
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "success",
                                "train ML models",
                                str(object_value),
                                f"splk-{component}",
                                str(json.dumps(result_record, indent=1)),
                                "ML models were trained successfully",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )

                    except Exception as e:
                        failures_count += 1
                        result_record = {
                            "tenant_id": tenant_id,
                            "object_category": f"splk-{component}",
                            "object": object_value,
                            "object_id": object_id,
                            "results": "Failed to train ML models for this entity",
                            "failures_count": 1,
                            "exception": str(e),
                        }
                        logger.error(json.dumps(result_record, indent=4))
                        results_summary.append(result_record)

                        # audit failure
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "failure",
                                "train ML models",
                                str(object_value),
                                f"splk-{component}",
                                f"Failed to train ML models: {str(e)}",
                                "ML models training failed",
                                str(update_comment),
                            )
                        except Exception as audit_e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(audit_e)}"'
                            )

                # Log final summary
                logger.info(
                    f"Sequential ML train processing completed: processed={processed_count}, success={success_count}, failures={failures_count}"
                )

            except Exception as e:
                # Top-level exception handler to prevent silent failures
                logger.error(
                    f'Background ML train worker failed with top-level exception: {str(e)}. '
                    f'tenant_id="{tenant_id}", component="{component}", '
                    f'object_list_count={len(object_list) if object_list else 0}, '
                    f'object_id_list_count={len(object_id_list) if object_id_list else 0}'
                )
                # Attempt to log audit event for the failure
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "train ML models",
                        "bulk operation",
                        f"splk-{component}",
                        f"Background ML train worker failed with exception: {str(e)}",
                        "ML models training worker failed",
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.error(
                        f'failed to generate audit event for worker failure with exception="{str(audit_e)}"'
                    )

        # Spawn background thread for fire-and-forget behavior
        thread = threading.Thread(
            target=background_train_worker,
            args=(
                tenant_id,
                component,
                object_list,
                object_id_list,
                service,
                request_info,
                update_comment,
            ),
            daemon=True,
        )
        thread.start()

        # Return immediately
        total_entities = len(object_id_list) if object_id_list else len(object_list) if object_list else 0
        return {
            "payload": {
                "action": "success",
                "message": f"ML train processing started for {total_entities} entities. Processing sequentially in background.",
                "note": "This is a fire-and-forget operation. Check logs for individual entity results.",
                "entities_count": total_entities,
            },
            "status": 200,
        }

    # train entity ML model
    def post_outliers_train_entity_model(self, request_info, **kwargs):
        describe = False

        logger.debug(f"Starting function post_outliers_train_entity_model")

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

                # Accept either object_id or object (prefer object_id)
                object_id = resp_dict.get("object_id", None)
                object_value = resp_dict.get("object", None)
                if not object_id and not object_value:
                    return {
                        "payload": {
                            "response": "either object_id or object is required",
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
                    # valid options are live, simulation
                    if mode not in ("live", "simulation"):
                        return {
                            "payload": {
                                "response": "mode is invalid, valid options are live, simulation",
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
                    entity_outlier = resp_dict["entity_outlier"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "entity_outlier is required",
                        },
                        "status": 500,
                    }

                try:
                    entity_outlier_dict = resp_dict["entity_outlier_dict"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "entity_outlier_dict is required",
                        },
                        "status": 500,
                    }

                model_json_def = resp_dict.get("model_json_def", {})
                # if mode is simulation, model_json_def is required
                if mode == "simulation" and not model_json_def:
                    return {
                        "payload": {
                            "response": "model_json_def is required for simulation mode",
                        },
                        "status": 500,
                    }

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint trains ML for a given entity, it requires a POST call with the following options:",
                "resource_desc": "Programmatically train ML models for a given entity, this endpoints is designed to be called by the backend for the purpose of training ML models",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_train_entity_model\" body=\"{'tenant_id':'mytenant','component':'dsm','object':'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category",
                        "object": "(optional) entity name",
                        "object_id": "(optional) entity identifier (preferred over object)",
                        "mode": "(required) train mode, valid options: live, simulation",
                        "entity_outlier": "(required) entity outlier",
                        "entity_outlier_dict": "(required) entity outlier dict",
                        "model_json_def": "(required for simulation only) model json definition",
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

        # Get request info and set logger.level
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )

        # trackme_idx_for_tenant
        tenant_indexes = trackme_idx_for_tenant(
            request_info.system_authtoken, request_info.server_rest_uri, tenant_id
        )

        # set the tenant_trackme_metric_idx
        tenant_trackme_metric_idx = tenant_indexes.get(
            "trackme_metric_idx", "trackme_metrics"
        )

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

        # Define the KV query - use object_id if available, otherwise object
        key = None
        record_outliers_rules = None
        if object_id:
            # Query by object_id (_key)
            try:
                record_outliers_rules = collection_rule.data.query_by_id(object_id)
                key = record_outliers_rules.get("_key")
                # Get object_value from KVstore for logging/response purposes
                if not object_value:
                    object_value = record_outliers_rules.get("object", "")
            except Exception as e:
                # Record not found or query failed
                key = None
                record_outliers_rules = None
        else:
            # Query by object
            query_string_filter = {
                "object_category": f"splk-{component}",
                "object": object_value,
            }
            query_string = {"$and": [query_string_filter]}

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
            try:
                records_outliers_rules = collection_rule.data.query(
                    query=json.dumps(query_string)
                )
                record_outliers_rules = records_outliers_rules[0]
                key = record_outliers_rules.get("_key")
            except Exception as e:
                key = None
                record_outliers_rules = None

        # if no records
        if not key or not record_outliers_rules:
            object_ref = f'object_id="{object_id}"' if object_id else f'object="{object_value}"'
            msg = f'tenant_id="{tenant_id}", component="{component}", {object_ref} outliers rules record cannot be found or are not yet available for this entity.'
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

        # Load the general enablement
        try:
            outliers_is_disabled = int(record_outliers_rules.get("is_disabled"))
            logger.debug(f'is_disabled="{outliers_is_disabled}"')

        except Exception as e:
            msg = f'Failed to extract one or more expected settings from the entity, is this record corrupted? Exception="{str(e)}"'
            logger.error(msg)
            return {
                "payload": {"response": msg},
                "status": 500,
            }

        # proceed
        if outliers_is_disabled == 1:
            msg = f"Outliers detection are disabled at the global level for this entity, nothing to do."
            logger.info(msg)
            return {
                "payload": msg,
                "status": 200,
            }

        else:

            logger.debug(
                f"calling function train_mlmodel with arguments: {tenant_id}, {component}, {object_value}, {key}, {tenant_trackme_metric_idx}, {mode}, {entities_outliers}, {entity_outlier}, {entity_outlier_dict}, {model_json_def}"
            )

            entities_outliers, entity_outlier, entity_outlier_dict = train_mlmodel(
                service,
                request_info.server_rest_uri,
                request_info.system_authtoken,
                request_info.user,
                tenant_id,
                component,
                object_value,
                key,
                tenant_trackme_metric_idx,
                mode,
                entities_outliers,
                entity_outlier,
                entity_outlier_dict,
                model_json_def,
            )

            # temp
            return {
                "payload": {
                    "entities_outliers": entities_outliers,
                    "entity_outlier": entity_outlier,
                    "entity_outlier_dict": entity_outlier_dict,
                },
                "status": 200,
            }

    # Force mlmonitor execution for a given object
    def post_outliers_mlmonitor_models(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                # Accept object_list or object_id_list (lists only)
                object_list = resp_dict.get("object_list", None)
                object_id_list = resp_dict.get("object_id_list", None)
                
                # Handle list conversion if string is provided
                if object_list and not isinstance(object_list, list):
                    if isinstance(object_list, str):
                        object_list = object_list.split(",") if object_list else None
                    else:
                        return {"payload": f"object_list must be a list or comma-separated string, got {type(object_list).__name__}", "status": 500}
                if object_id_list and not isinstance(object_id_list, list):
                    if isinstance(object_id_list, str):
                        object_id_list = object_id_list.split(",") if object_id_list else None
                    else:
                        return {"payload": f"object_id_list must be a list or comma-separated string, got {type(object_id_list).__name__}", "status": 500}
                
                if not object_list and not object_id_list:
                    return {"payload": "either object_list or object_id_list is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint runs the execution of the ML monitor backend process for a list of entities, it requires a POST call with the following options:",
                "resource_desc": "Runs Machine Learning Outliers monitor process for a given list of entities (processed sequentially)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_mlmonitor_models\" body=\"{'tenant_id':'mytenant','component':'dsm','object_list':['entity1','entity2']}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) the component, valid options for this endpoint are: dsm|dhm|flx|fqm|wlk",
                        "object_list": "(required unless using object_id_list) list of entity names",
                        "object_id_list": "(required unless using object_list) list of entity identifiers",
                        "update_comment": "(optional) comment for audit trail",
                    }
                ],
                "note": "Entities are processed sequentially (one after another) in a background thread. This is a fire-and-forget operation.",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Define background worker function for sequential processing
        def background_monitor_worker(
            tenant_id,
            component,
            object_list,
            object_id_list,
            service,
            request_info,
            update_comment,
        ):
            """Background worker function for sequential ML monitoring"""
            try:
                processed_count = 0
                success_count = 0
                failures_count = 0
                results_summary = []

                # Build list of entities to process
                entities_to_process = []
                if object_id_list:
                    # Use object_id_list, resolve object names from KVstore
                    collection_name = (
                        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                    )
                    collection = service.kvstore[collection_name]
                    
                    for object_id in object_id_list:
                        try:
                            entity_rules = collection.data.query_by_id(object_id)
                            object_value = entity_rules.get("object", "")
                            entities_to_process.append({
                                "object_id": object_id,
                                "object": object_value,
                            })
                        except Exception as e:
                            logger.warning(f"Could not resolve object_id={object_id}, using as-is: {str(e)}")
                            entities_to_process.append({
                                "object_id": object_id,
                                "object": "",
                            })
                elif object_list:
                    # Use object_list, resolve object_ids from KVstore
                    collection_name = (
                        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                    )
                    collection = service.kvstore[collection_name]
                    
                    for object_value in object_list:
                        try:
                            query_string = {
                                "$and": [
                                    {
                                        "object_category": f"splk-{component}",
                                        "object": object_value,
                                    }
                                ]
                            }
                            entity_rules = collection.data.query(query=json.dumps(query_string))
                            if entity_rules and len(entity_rules) > 0:
                                key = entity_rules[0].get("_key")
                                entities_to_process.append({
                                    "object_id": key,
                                    "object": object_value,
                                })
                            else:
                                entities_to_process.append({
                                    "object_id": None,
                                    "object": object_value,
                                })
                        except Exception as e:
                            logger.warning(f"Could not resolve object={object_value}, using as-is: {str(e)}")
                            entities_to_process.append({
                                "object_id": None,
                                "object": object_value,
                            })

                # Process entities sequentially
                for entity in entities_to_process:
                    object_value = entity.get("object", "")
                    object_id = entity.get("object_id", None)
                    processed_count += 1
                    start_time = time.time()

                    try:
                        # Determine object_param for SPL query
                        if object_id:
                            object_param = f'object_id="{object_id}"'
                        else:
                            object_param = f'object="{object_value}"'

                        # Define the SPL query
                        kwargs_search = {
                            "app": "trackme",
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        }
                        searchquery = f'| trackmesplkoutlierstrackerhelper tenant_id="{tenant_id}" component="{component}" {object_param} force_run="True"'
                        
                        log_object_ref = f'object_id="{object_id}"' if object_id else f'object="{object_value}"'
                        logger.debug(
                            f'Processing ML monitor: tenant_id="{tenant_id}", component="{component}", {log_object_ref}, searchquery="{searchquery}"'
                        )

                        query_results = []
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
                                query_results.append(item)

                        # Get object value from KVstore if object_id was used and object_value is empty
                        if object_id and not object_value:
                            try:
                                collection_name = (
                                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                                )
                                collection = service.kvstore[collection_name]
                                entity_rules = collection.data.query_by_id(object_id)
                                object_value = entity_rules.get("object", "")
                            except Exception as e:
                                object_value = ""

                        if len(query_results) > 0:
                            execution_time = round(time.time() - start_time, 3)
                            logger.info(
                                f"ML monitor successfully executed for {log_object_ref} in {execution_time} seconds"
                            )
                            result_record = {
                                "action": "success",
                                "tenant_id": tenant_id,
                                "object_category": f"splk-{component}",
                                "object": object_value,
                                "object_id": object_id,
                                "upstream_query": searchquery,
                                "query_results": query_results,
                                "execution_time_seconds": execution_time,
                            }
                            results_summary.append(result_record)
                            success_count += 1

                            # audit
                            try:
                                trackme_audit_event(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    request_info.user,
                                    "success",
                                    "ML monitor",
                                    str(object_value),
                                    f"splk-{component}",
                                    f"ML monitor executed successfully in {execution_time} seconds",
                                    "ML monitor executed successfully",
                                    str(update_comment),
                                )
                            except Exception as e:
                                logger.error(
                                    f'failed to generate an audit event with exception="{str(e)}"'
                                )
                        else:
                            result_record = {
                                "action": "failure",
                                "tenant_id": tenant_id,
                                "object_category": f"splk-{component}",
                                "object": object_value,
                                "object_id": object_id,
                                "upstream_query": searchquery,
                                "query_results": "The search was executed successfully, but no results were returned.",
                            }
                            logger.warning(json.dumps(result_record, indent=4))
                            results_summary.append(result_record)
                            failures_count += 1

                            # audit failure
                            try:
                                trackme_audit_event(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    request_info.user,
                                    "failure",
                                    "ML monitor",
                                    str(object_value),
                                    f"splk-{component}",
                                    "The search was executed successfully, but no results were returned.",
                                    "ML monitor returned no results",
                                    str(update_comment),
                                )
                            except Exception as audit_e:
                                logger.error(
                                    f'failed to generate an audit event with exception="{str(audit_e)}"'
                                )

                    except Exception as e:
                        failures_count += 1
                        result_record = {
                            "action": "failure",
                            "tenant_id": tenant_id,
                            "object_category": f"splk-{component}",
                            "object": object_value,
                            "object_id": object_id,
                            "response": f'an exception was encountered, exception="{str(e)}"',
                        }
                        logger.error(json.dumps(result_record, indent=4))
                        results_summary.append(result_record)

                        # audit failure
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "failure",
                                "ML monitor",
                                str(object_value),
                                f"splk-{component}",
                                f"ML monitor failed with exception: {str(e)}",
                                "ML monitor execution failed",
                                str(update_comment),
                            )
                        except Exception as audit_e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(audit_e)}"'
                            )

                # Log final summary
                logger.info(
                    f"Sequential ML monitor processing completed: processed={processed_count}, success={success_count}, failures={failures_count}"
                )

            except Exception as e:
                # Top-level exception handler to prevent silent failures
                logger.error(
                    f'Background ML monitor worker failed with top-level exception: {str(e)}. '
                    f'tenant_id="{tenant_id}", component="{component}", '
                    f'object_list_count={len(object_list) if object_list else 0}, '
                    f'object_id_list_count={len(object_id_list) if object_id_list else 0}'
                )
                # Attempt to log audit event for the failure
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "ML monitor",
                        "bulk operation",
                        f"splk-{component}",
                        f"Background ML monitor worker failed with exception: {str(e)}",
                        "ML monitor worker failed",
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.error(
                        f'failed to generate audit event for worker failure with exception="{str(audit_e)}"'
                    )

        # Spawn background thread for fire-and-forget behavior
        thread = threading.Thread(
            target=background_monitor_worker,
            args=(
                tenant_id,
                component,
                object_list,
                object_id_list,
                service,
                request_info,
                update_comment,
            ),
            daemon=True,
        )
        thread.start()

        # Return immediately
        total_entities = len(object_id_list) if object_id_list else len(object_list) if object_list else 0
        return {
            "payload": {
                "action": "success",
                "message": f"ML monitor processing started for {total_entities} entities. Processing sequentially in background.",
                "note": "This is a fire-and-forget operation. Check logs for individual entity results.",
                "entities_count": total_entities,
            },
            "status": 200,
        }

    # Run Bulk mlmonitor or mltrain
    def post_outliers_bulk_action(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}

                # handle object_list / keys_list
                object_list = resp_dict.get("object_list", None)
                if object_list:
                    if not isinstance(object_list, list):
                        if isinstance(object_list, str):
                            object_list = object_list.split(",")
                        else:
                            return {"payload": f"object_list must be a list or comma-separated string, got {type(object_list).__name__}", "status": 500}

                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")

                if object_list and keys_list:
                    return {
                        "payload": {
                            "error": "object_list and keys_list are mutually exclusive, provide one or the other but not both"
                        },
                        "status": 400,
                    }

                if not object_list and not keys_list:
                    return {
                        "payload": {
                            "error": "either object_list or keys_list must be provided"
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                    # valid components are dsm/dhm/flx/fqm/wlk
                    if component not in ("dsm", "dhm", "flx", "fqm", "wlk"):
                        return {
                            "payload": f"component {component} is invalid, must be either dsm, dhm, flx, fqm or wlk",
                            "status": 500,
                        }
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                try:
                    action = resp_dict["action"]
                    if action not in (
                        "enable",
                        "disable",
                        "mlmonitor",
                        "mltrain",
                        "reset_status",
                    ):
                        return {
                            "payload": f"action {action} is invalid, must be either enable, disable, mlmonitor, mltrain, or reset_status",
                            "status": 500,
                        }
                except Exception as e:
                    return {"payload": "action is required", "status": 500}

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows performing bulk actions for a given list of entities, it requires a POST call with the following options:",
                "resource_desc": "Run bulk actions for a given list of entities (fire and forget for mlmonitor/mltrain)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_bulk_action\" body=\"{'tenant_id':'mytenant','component':'dsm','object_list':'entity1,entity2', 'action': 'enable'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category, valid options: dsm/dhm/flx/fqm/wlk",
                        "object_list": "(required unless using keys_list) comma separated list of entities",
                        "keys_list": "(required unless using object_list) comma separated list of keys",
                        "action": "(required) enable, disable, mlmonitor, mltrain, reset_status",
                    }
                ],
                "note": "mlmonitor and mltrain actions are executed sequentially in background (fire and forget), while enable/disable/reset_status are executed synchronously",
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

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.session_key,
            "Content-Type": "application/json",
        }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # entity main collection
        collection_main_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        collection_main = service.kvstore[collection_main_name]

        # entity rules collection
        collection_rules_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_rules = service.kvstore[collection_rules_name]

        # entity data collection
        collection_data_name = (
            f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
        )
        collection_data = service.kvstore[collection_data_name]

        #
        # proceed
        #

        # Retrieve the list object values and object_ids if keys_list is provided
        object_id_map = {}  # Map object_value to object_id for later use
        if keys_list:
            object_list = []
            for key_value in keys_list:
                kvrecords = collection_main.data.query(
                    query=json.dumps({"_key": key_value})
                )
                for kvrecord in kvrecords:
                    object = kvrecord.get("object", None)
                    if object:
                        object_list.append(object)
                        object_id_map[object] = key_value  # Store mapping

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

        # For mlmonitor and mltrain actions, call endpoints directly with lists
        if action in ("mlmonitor", "mltrain"):
            logger.info(
                f"Calling {action} endpoint directly for {len(object_list)} objects (sequential processing)"
            )

            # Build object_id_list from object_id_map
            object_id_list = []
            for object_value in object_list:
                object_id_value = object_id_map.get(object_value, None)
                if object_id_value:
                    object_id_list.append(object_id_value)

            # Define background worker to call endpoint with lists
            def background_endpoint_caller(
                action,
                tenant_id,
                component,
                object_list,
                object_id_list,
                header,
                request_info,
                update_comment,
            ):
                """Background worker to call ML endpoints with lists"""
                try:
                    if action == "mlmonitor":
                        rest_url = f"{request_info.server_rest_uri}/services/trackme/v2/splk_outliers_engine/write/outliers_mlmonitor_models"
                    elif action == "mltrain":
                        rest_url = f"{request_info.server_rest_uri}/services/trackme/v2/splk_outliers_engine/write/outliers_train_models"
                    else:
                        logger.error(f"Invalid action for endpoint caller: {action}")
                        return

                    post_data = {
                        "tenant_id": tenant_id,
                        "component": component,
                        "update_comment": update_comment,
                    }
                    # Prefer object_id_list if available and non-empty, otherwise use object_list
                    if object_id_list and len(object_id_list) > 0:
                        post_data["object_id_list"] = object_id_list
                    if object_list and len(object_list) > 0:
                        post_data["object_list"] = object_list
                    # Ensure at least one list is provided
                    if "object_id_list" not in post_data and "object_list" not in post_data:
                        logger.error("Both object_list and object_id_list are empty")
                        return

                    response = requests.post(
                        rest_url,
                        headers=header,
                        data=json.dumps(post_data),
                        verify=False,
                        timeout=600,
                    )

                    if response.status_code == 200:
                        logger.info(
                            f'Bulk {action} endpoint called successfully for {len(object_list)} objects'
                        )
                    else:
                        logger.error(
                            f'Bulk {action} endpoint call failed, status_code="{response.status_code}", response="{response.text}"'
                        )

                except Exception as e:
                    logger.error(
                        f'Bulk {action} endpoint call failed with exception="{str(e)}"'
                    )

            # Spawn background thread to call endpoint (maintains fire-and-forget behavior)
            thread = threading.Thread(
                target=background_endpoint_caller,
                args=(
                    action,
                    tenant_id,
                    component,
                    object_list,
                    object_id_list if object_id_list and len(object_id_list) > 0 else None,
                    header,
                    request_info,
                    update_comment,
                ),
                daemon=True,
            )
            thread.start()
            processed_count = len(object_list)
            succcess_count = processed_count  # Count as success since endpoint call was initiated for all entities

            # Return immediately for fire and forget behavior
            req_summary = {
                "process_count": processed_count,
                "success_count": succcess_count,
                "failures_count": failures_count,
                "action": action,
                "message": f"Bulk {action} action initiated for {processed_count} objects. Entities will be processed sequentially in background.",
                "note": "This is a fire and forget operation. Entities are processed sequentially (one after another). Check logs for individual entity results.",
            }

            logger.info(
                f"Bulk edit Fire and forget, action={action} endpoint called for objects_count={processed_count}"
            )
            return {"payload": req_summary, "status": 200}

        # For synchronous actions (enable, disable, reset_status), process normally
        else:
            logger.info(
                f"Processing synchronous {action} actions for {len(object_list)} objects"
            )

            # Check if collections exist and have data
            try:
                rules_count = len(collection_rules.data.query())
                data_count = len(collection_data.data.query())
                logger.info(
                    f"Collection stats: rules_count={rules_count}, data_count={data_count}"
                )
            except Exception as e:
                logger.error(f"Failed to check collection stats: {str(e)}")

            # Loop through objects for synchronous processing
            for object_value in object_list:
                try:
                    logger.debug(
                        f"Processing object: {object_value} for action: {action}"
                    )
                    #
                    # Enable / Disable, we need to update the value of is_disabled in the rules collection for each matching object
                    #

                    if action in ("enable", "disable"):
                        logger.debug(
                            f"Processing enable/disable action for object: {object_value}"
                        )
                        # Get all matching records
                        kvrecords = collection_rules.data.query(
                            query=json.dumps({"object": object_value})
                        )
                        logger.debug(
                            f"Found {len(kvrecords)} records for object: {object_value}"
                        )

                        if len(kvrecords) == 0:
                            logger.warning(
                                f"No records found for object: {object_value} in collection: {collection_rules_name}"
                            )
                            # Still count as processed but mark as failure
                            processed_count += 1
                            succcess_count += 0
                            failures_count += 1
                            result = {
                                "object": object_value,
                                "action": "update",
                                "result": "failure",
                                "exception": f'No records found for object="{object_value}" in collection="{collection_rules_name}"',
                            }
                            records.append(result)
                            continue

                        for kvrecord in kvrecords:
                            # Update the record
                            current_object_value = kvrecord.get("object")
                            current_key_value = kvrecord.get("_key")
                            if action == "enable":
                                kvrecord["is_disabled"] = 0
                            elif action == "disable":
                                kvrecord["is_disabled"] = 1
                            kvrecord["mtime"] = time.time()

                            # Update the record
                            try:
                                collection_rules.data.update(
                                    current_key_value, json.dumps(kvrecord)
                                )

                                # increment counter
                                processed_count += 1
                                succcess_count += 1
                                failures_count += 0

                                result = {
                                    "object": current_object_value,
                                    "action": "update",
                                    "result": "success",
                                    "message": f'tenant_id="{tenant_id}", object="{current_object_value}" was successfully updated',
                                }
                                records.append(result)

                                try:
                                    trackme_audit_event(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        request_info.user,
                                        "success",
                                        f"Oultiers detection bulk action {action}",
                                        str(object_value),
                                        f"splk-{component}",
                                        str(
                                            json.dumps(
                                                collection_main.data.query(
                                                    query=json.dumps(
                                                        {"object": object_value}
                                                    )
                                                ),
                                                indent=1,
                                            )
                                        ),
                                        f"The Outliers detection bulk action {action} was performed successfully",
                                        str(update_comment),
                                    )
                                except Exception as e:
                                    logger.error(
                                        f'failed to generate an audit event with exception="{str(e)}"'
                                    )

                            except Exception as e:
                                # increment counter
                                processed_count += 1
                                succcess_count += 0
                                failures_count += 1

                                result = {
                                    "object": object_value,
                                    "action": "update",
                                    "result": "failure",
                                    "exception": f'tenant_id="{tenant_id}", object="{current_object_value}" failed to be updated, exception="{str(e)}"',
                                }
                                records.append(result)

                                try:
                                    trackme_audit_event(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        request_info.user,
                                        "failure",
                                        f"Oultiers detection bulk action {action}",
                                        str(object_value),
                                        f"splk-{component}",
                                        str(
                                            json.dumps(
                                                collection_main.data.query(
                                                    query=json.dumps(
                                                        {"object": object_value}
                                                    )
                                                ),
                                                indent=1,
                                            )
                                        ),
                                        f"The Outliers detection bulk action {action} has failed",
                                        str(update_comment),
                                    )
                                except Exception as e:
                                    logger.error(
                                        f'failed to generate an audit event with exception="{str(e)}"'
                                    )

                    #
                    # Reset status
                    #

                    # for reset_status, we need to delete the record in the data collection for each matching object

                    elif action in ("reset_status"):
                        logger.debug(
                            f"Processing reset_status action for object: {object_value}"
                        )
                        # Get all matching records
                        kvrecords = collection_rules.data.query(
                            query=json.dumps({"object": object_value})
                        )
                        logger.debug(
                            f"Found {len(kvrecords)} records for object: {object_value}"
                        )

                        if len(kvrecords) == 0:
                            logger.warning(
                                f"No records found for object: {object_value} in collection: {collection_rules_name}"
                            )
                            # Still count as processed but mark as failure
                            processed_count += 1
                            succcess_count += 0
                            failures_count += 1
                            result = {
                                "object": object_value,
                                "action": "update",
                                "result": "failure",
                                "exception": f'No records found for object="{object_value}" in collection="{collection_rules_name}"',
                            }
                            records.append(result)
                            continue

                        for kvrecord in kvrecords:
                            current_object_value = kvrecord.get("object")
                            current_key_value = kvrecord.get("_key")

                            try:
                                collection_data.data.delete(
                                    json.dumps({"_key": current_key_value})
                                )

                                # increment counter
                                processed_count += 1
                                succcess_count += 1
                                failures_count += 0

                                result = {
                                    "object": current_object_value,
                                    "action": "update",
                                    "result": "success",
                                    "message": f'tenant_id="{tenant_id}", object="{current_object_value}" was successfully updated',
                                }
                                records.append(result)

                                try:
                                    trackme_audit_event(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        request_info.user,
                                        "success",
                                        f"Oultiers detection bulk action {action}",
                                        str(object_value),
                                        f"splk-{component}",
                                        str(
                                            json.dumps(
                                                collection_main.data.query(
                                                    query=json.dumps(
                                                        {"object": object_value}
                                                    )
                                                ),
                                                indent=1,
                                            )
                                        ),
                                        f"The Outliers detection bulk action {action} was performed successfully",
                                        str(update_comment),
                                    )
                                except Exception as e:
                                    logger.error(
                                        f'failed to generate an audit event with exception="{str(e)}"'
                                    )

                            except Exception as e:
                                # increment counter
                                processed_count += 1
                                succcess_count += 0
                                failures_count += 1

                                result = {
                                    "object": object_value,
                                    "action": "update",
                                    "result": "failure",
                                    "exception": f'tenant_id="{tenant_id}", object="{current_object_value}" failed to be updated, exception="{str(e)}"',
                                }
                                records.append(result)

                                try:
                                    trackme_audit_event(
                                        request_info.system_authtoken,
                                        request_info.server_rest_uri,
                                        tenant_id,
                                        request_info.user,
                                        "failure",
                                        f"Oultiers detection bulk action {action}",
                                        str(object_value),
                                        f"splk-{component}",
                                        str(
                                            json.dumps(
                                                collection_main.data.query(
                                                    query=json.dumps(
                                                        {"object": object_value}
                                                    )
                                                ),
                                                indent=1,
                                            )
                                        ),
                                        f"The Outliers detection bulk action {action} has failed",
                                        str(update_comment),
                                    )
                                except Exception as e:
                                    logger.error(
                                        f'failed to generate an audit event with exception="{str(e)}"'
                                    )

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    result = {
                        "object": object_value,
                        "action": "update",
                        "result": "failure",
                        "exception": f'tenant_id="{tenant_id}", object="{object_value}", failed to execute action="{action}", exception="{str(e)}"',
                    }
                    records.append(result)

            logger.info(
                f"Synchronous processing completed: processed={processed_count}, success={succcess_count}, failures={failures_count}"
            )
            # render HTTP status and summary for synchronous actions

            req_summary = {
                "process_count": processed_count,
                "success_count": succcess_count,
                "failures_count": failures_count,
                "records": records,
            }

            if processed_count > 0 and processed_count == succcess_count:
                return {"payload": req_summary, "status": 200}

            else:
                return {"payload": req_summary, "status": 500}

    def post_outliers_bulk_rules_update(self, request_info, **kwargs):
        describe = False

        # Validation rules mapping
        FIELD_VALIDATION_RULES = {
            # kpi_span, span notation such as 10m
            "kpi_span": (
                r"^\d+[m|h|d]$",
                "Must be an integer followed by one of: `m`, `h`, `d`.",
            ),
            # method_calculation, one of stdev, avg, max, min, sum, perc95, latest
            "method_calculation": (
                r"^(stdev|avg|max|min|sum|perc95|latest)$",
                "Must be one of: `stdev`, `avg`, `max`, `min`, `sum`, `perc95`, `latest`.",
            ),
            # period_calculation, now or a relative time notation such as -30d
            "period_calculation": (
                r"^-?\d+[m|h|d]$",
                "Must be an integer followed by one of: `m`, `h`, `d`.",
            ),
            # period_calculation_latest, now or a relative time notation such as -1d
            "period_calculation_latest": (
                r"^(now|-\d+[m|h|d])$",
                "Must be `latest`, `now` or a relative time notation such as `-1d`.",
            ),
            # time_factor, one of %H, %H%M, %w%H, %w%H%M, %w, none
            "time_factor": (
                r"^(%H|%H%M|%w%H|%w%H%M|%w|none)$",
                "Must be one of: `%H`, `%H%M`, `%w%H`, `%w%H%M`, `%w`, `none`.",
            ),
            # density_lowerthreshold, a decimal or integer
            "density_lowerthreshold": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # density_upperthreshold, a decimal or integer
            "density_upperthreshold": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # alert_lower_breached, 0 or 1
            "alert_lower_breached": (r"^(1|0)$", "Must be `1` (True) or `0` (False)."),
            # alert_upper_breached, 0 or 1
            "alert_upper_breached": (r"^(1|0)$", "Must be `1` (True) or `0` (False)."),
            # auto_correct, 1 or 0
            "auto_correct": (r"^(1|0)$", "Must be `1` (True) or `0` (False)."),
            # perc_min_lowerbound_deviation, a decimal or integer
            "perc_min_lowerbound_deviation": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # perc_min_upperbound_deviation, a decimal or integer
            "perc_min_upperbound_deviation": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # min_value_for_lowerbound_breached, a decimal or integer
            "min_value_for_lowerbound_breached": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # min_value_for_upperbound_breached, a decimal or integer
            "min_value_for_upperbound_breached": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # static_lower_threshold, a decimal or integer
            "static_lower_threshold": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # static_upper_threshold, a decimal or integer
            "static_upper_threshold": (
                r"^[\d|\.]*$",
                "Must be an integer or decimal.",
            ),
            # is_disabled, 0 or 1
            "is_disabled": (r"^(1|0)$", "Must be `1` (True) or `0` (False)."),
            # ai_mladvisor_disabled, 0 or 1 — opt-out from automated ML Advisor batch
            "ai_mladvisor_disabled": (r"^(1|0)$", "Must be `1` (True) or `0` (False)."),
            # score, an integer
            "score": (r"^\d*$", "Must be an integer."),
        }

        def validate_update_fields(update_fields):
            """Validates update fields based on predefined rules."""
            invalid_fields = {}
            for field, value in update_fields.items():
                if field in FIELD_VALIDATION_RULES:
                    pattern, error_message = FIELD_VALIDATION_RULES[field]
                    if not re.match(pattern, str(value)):
                        invalid_fields[field] = error_message
                    # Special validation for score field: must be between 0 and 100
                    if field == "score":
                        try:
                            score_int = int(value)
                            if score_int < 0 or score_int > 100:
                                invalid_fields[field] = "score must be an integer between 0 and 100"
                        except (ValueError, TypeError):
                            invalid_fields[field] = "score must be an integer between 0 and 100"

            return invalid_fields

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = resp_dict.get("describe", False) in ("true", "True")

            if not describe:
                tenant_id = resp_dict.get("tenant_id")
                if not tenant_id:
                    return {"payload": "tenant_id is required", "status": 500}

                object_list = resp_dict.get("object_list", [])
                if isinstance(object_list, str):
                    object_list = object_list.split(",")

                keys_list = extract_keys_list(resp_dict, default=[])
                if isinstance(keys_list, str):
                    keys_list = keys_list.split(",")

                if object_list and keys_list:
                    return {
                        "payload": {
                            "error": "object_list and keys_list are mutually exclusive, provide one or the other but not both"
                        },
                        "status": 400,
                    }

                if not object_list and not keys_list:
                    return {
                        "payload": "Either object_list or keys_list must be provided",
                        "status": 500,
                    }

                component = resp_dict.get("component")
                if component not in ("dsm", "dhm", "flx", "fqm", "wlk"):
                    return {"payload": f"Invalid component {component}", "status": 500}

                # Update comment is optional and used for audit changes
                update_comment = resp_dict.get("update_comment") or "API update"

                update_fields = {
                    k: v
                    for k, v in resp_dict.items()
                    if k
                    not in (
                        "tenant_id",
                        "component",
                        "object_list",
                        "keys_list",
                        "update_comment",
                        "describe",
                    )
                }

                if not update_fields:
                    return {
                        "payload": "At least one field to update must be provided",
                        "status": 500,
                    }

                # Ensure values are not empty or null
                invalid_fields = [
                    k for k, v in update_fields.items() if v in (None, "")
                ]
                if invalid_fields:
                    return {
                        "payload": f"Invalid values for fields: {', '.join(invalid_fields)}",
                        "status": 500,
                    }

                # Validate input fields
                validation_errors = validate_update_fields(update_fields)
                if validation_errors:
                    return {
                        "payload": f"Invalid values: {validation_errors}",
                        "status": 500,
                    }

                # if we have a field kpi_metric, ensure it does not contain "splk.flx.replaceme" which is specific for
                # splk-flx and preset in the UI, users are required to change this
                if "kpi_metric" in update_fields:
                    if "splk.flx.replaceme" in update_fields["kpi_metric"]:
                        return {
                            "payload": "kpi_metric must be changed from 'splk.flx.replaceme'",
                            "status": 500,
                        }

                # prevents an update from the UI for custom update without care
                # if we have a field called field_name, and/or a value with value equal to field_value, raise an error
                # field_name: field_value is forbidden
                # <something>: field_value is forbidden
                # field_name: <something> is forbidden
                for field, value in update_fields.items():
                    if field in ("field_name", "field_value") or value in (
                        "field_name",
                        "field_value",
                    ):
                        return {
                            "payload": "field_name and field_value are forbidden",
                            "status": 500,
                        }

        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint allows performing bulk updates on outlier detection rules for a given list of entities.",
                "resource_desc": "Bulk update rules for outlier detection",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_bulk_rules_update\" body=\"{'tenant_id':'mytenant','component':'dsm','object_list':'entity1,entity2', 'kpi_span': '10m'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category, valid options: dsm/dhm/flx/fqm/wlk",
                        "object_list": "(required unless using keys_list) Comma separated list of entities",
                        "keys_list": "(required unless using object_list) Comma separated list of keys",
                        "update_fields": "(optional) Fields to update within the rules, only specified fields will be modified",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        collection_rules_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_rules = service.kvstore[collection_rules_name]

        processed_count = 0
        success_count = 0
        failures_count = 0
        records = []

        if "*" in object_list:
            kvrecords = collection_rules.data.query()
            object_list = [kvrecord.get("object") for kvrecord in kvrecords]

        if keys_list:
            kvrecords = collection_rules.data.query(
                query=json.dumps({"_key": {"$in": keys_list}})
            )
            object_list.extend([kvrecord.get("object") for kvrecord in kvrecords])

        for object_value in object_list:
            try:
                kvrecords = collection_rules.data.query(
                    query=json.dumps({"object": object_value})
                )
                for kvrecord in kvrecords:
                    current_key_value = kvrecord.get("_key")
                    entities_outliers = kvrecord.get("entities_outliers", "{}")

                    if isinstance(entities_outliers, str):
                        try:
                            entities_outliers = json.loads(entities_outliers)
                        except json.JSONDecodeError:
                            failures_count += 1
                            records.append(
                                {
                                    "object": object_value,
                                    "status": "failure",
                                    "error": "Invalid JSON structure in entities_outliers",
                                }
                            )
                            continue

                    # Fields that can be added to models even if they don't exist yet
                    ADDABLE_FIELDS = {"ai_mladvisor_disabled"}

                    for model_key, model_data in entities_outliers.items():
                        if isinstance(model_data, dict):
                            for field, value in update_fields.items():
                                if field in model_data or field in ADDABLE_FIELDS:
                                    # Coerce to proper numeric type
                                    try:
                                        if field in OUTLIER_FLOAT_FIELDS:
                                            model_data[field] = float(value)
                                        elif field in OUTLIER_INT_FIELDS:
                                            # Use int(float(val)) to handle float-formatted strings like "1.0"
                                            model_data[field] = int(float(value))
                                        else:
                                            model_data[field] = value
                                    except (ValueError, TypeError):
                                        model_data[field] = value

                    kvrecord["entities_outliers"] = json.dumps(
                        entities_outliers, indent=2
                    )
                    kvrecord["mtime"] = time.time()

                    try:
                        collection_rules.data.update(
                            current_key_value, json.dumps(kvrecord)
                        )
                        success_count += 1
                        records.append({"object": object_value, "status": "success"})

                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "success",
                                "bulk update outlier rules",
                                str(object_value),
                                f"splk-{component}",
                                str(json.dumps(update_fields, indent=1)),
                                "Outlier rules were updated successfully",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )

                    except Exception as e:
                        failures_count += 1
                        records.append(
                            {
                                "object": object_value,
                                "status": "failure",
                                "error": str(e),
                            }
                        )

                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "failure",
                                "bulk update outlier rules",
                                str(object_value),
                                f"splk-{component}",
                                str(json.dumps(update_fields, indent=1)),
                                f'Outlier rules update has failed, exception="{str(e)}"',
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )

            except Exception as e:
                failures_count += 1
                records.append(
                    {"object": object_value, "status": "failure", "error": str(e)}
                )

                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "bulk update outlier rules",
                        str(object_value),
                        f"splk-{component}",
                        str(json.dumps(update_fields, indent=1)),
                        f'Outlier rules update has failed, exception="{str(e)}"',
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

            processed_count += 1

        summary = {
            "processed_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "records": records,
        }

        return {"payload": summary, "status": 200 if failures_count == 0 else 500}

    #
    # Bulk period exclusion
    #

    def post_outliers_bulk_period_exclusion(self, request_info, **kwargs):
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
                    return {"payload": "tenant_id is required", "status": 500}

                # handle object_list / keys_list
                object_list = resp_dict.get("object_list", None)
                if object_list:
                    if not isinstance(object_list, list):
                        if isinstance(object_list, str):
                            object_list = object_list.split(",")
                        else:
                            return {"payload": f"object_list must be a list or comma-separated string, got {type(object_list).__name__}", "status": 500}

                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")

                if object_list and keys_list:
                    return {
                        "payload": {
                            "error": "object_list and keys_list are mutually exclusive, provide one or the other but not both"
                        },
                        "status": 400,
                    }

                if not object_list and not keys_list:
                    return {
                        "payload": {
                            "error": "either object_list or keys_list must be provided"
                        },
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                    # valid components are dsm/dhm/flx/fqm/wlk
                    if component not in ("dsm", "dhm", "flx", "fqm", "wlk"):
                        return {
                            "payload": f"component {component} is invalid, must be either dsm, dhm, flx, fqm or wlk",
                            "status": 500,
                        }
                except Exception as e:
                    return {"payload": "component is required", "status": 500}

                # required for addition
                earliest = resp_dict.get("earliest", None)
                latest = resp_dict.get("latest", None)

                # if action is add, earliest and latest are required
                if not earliest or not latest:
                    msg = "earliest and latest are required"
                    logger.error(msg)
                    return {"payload": msg, "status": 500}

                # earliest and latest can be provided as epochtime, or date string in the format %Y-%m-%dT%H:%M, check if provided
                # as epochtime or date string, if dat string attempt to convert to epochtime using datetime.datetime.strptime
                try:
                    earliest = int(earliest)
                except Exception as e:
                    try:
                        logger.debug(
                            f'trying to parse as datetime, earliest="{earliest}"'
                        )
                        earliest_dt = datetime.strptime(
                            str(earliest), "%Y-%m-%dT%H:%M"
                        )
                        earliest = int(round(float(earliest_dt.timestamp())))
                    except Exception as e:
                        msg = f'earliest must be defined as epochtime or date string in the format %Y-%m-%dT%H:%M, parsing as date failed with exception={str(e)}'
                        logger.error(msg)
                        return {"payload": msg, "status": 500}
                try:
                    latest = int(latest)
                except Exception as e:
                    try:
                        logger.debug(
                            f'trying to parse as datetime, latest="{latest}"'
                        )
                        latest_dt = datetime.strptime(str(latest), "%Y-%m-%dT%H:%M")
                        latest = int(round(float(latest_dt.timestamp())))
                    except Exception as e:
                        msg = f'latest must be defined as epochtime or date string in the format %Y-%m-%dT%H:%M, parsing as date failed with exception={str(e)}'
                        logger.error(msg)
                        return {"payload": msg, "status": 500}

                # also verify that earliest is not lower than latest, the earliest epochtime cannot be before the latest epochtime
                if not earliest < latest:
                    msg = f'earliest must be before latest, earliest="{earliest}", latest="{latest}"'
                    logger.error(msg)
                    return {"payload": msg, "status": 500}

        else:
            # body is not required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint adds a period of exclusion for multiple entities and their ML models, it requires a POST call with the following options:",
                "resource_desc": "Add an exclusion period to multiple entities and their ML models",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_outliers_engine/write/outliers_bulk_period_exclusion\" body=\"{'tenant_id':'mytenant','component':'dsm','keys_list':'key1,key2', 'earliest': '<epoch earliest', 'latest': '<epoch latest>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category, valid options: dsm/dhm/flx/fqm/wlk",
                        "object_list": "(required unless using keys_list) comma separated list of entities",
                        "keys_list": "(required unless using object_list) comma separated list of keys",
                        "earliest": "(required) The earliest time to be excluded, in epochtime or date string in the format %Y-%m-%dT%H:%M",
                        "latest": "(required) The latest time to be excluded, in epochtime or date string in the format %Y-%m-%dT%H:%M",
                        "update_comment": "(optional) Comment for audit trail",
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

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # entity main collection
        collection_main_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        collection_main = service.kvstore[collection_main_name]

        # entity rules collection
        collection_rules_name = (
            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
        )
        collection_rules = service.kvstore[collection_rules_name]

        # Retrieve the list object values and object_ids if keys_list is provided
        object_id_map = {}  # Map object_value to object_id for later use
        if keys_list:
            object_list = []
            for key_value in keys_list:
                kvrecords = collection_main.data.query(
                    query=json.dumps({"_key": key_value})
                )
                for kvrecord in kvrecords:
                    object = kvrecord.get("object", None)
                    if object:
                        object_list.append(object)
                        object_id_map[object] = key_value  # Store mapping

        # counters
        processed_count = 0
        success_count = 0
        failures_count = 0

        # records summary
        records = []

        # Loop through objects
        for object_value in object_list:
            try:
                logger.debug(
                    f"Processing period exclusion for object: {object_value}"
                )

                # Define the KV query - use object_id if available, otherwise object
                object_id = object_id_map.get(object_value, None)
                if object_id:
                    # Query by object_id (_key)
                    query_string = {
                        "$and": [
                            {
                                "object_category": f"splk-{component}",
                                "_key": object_id,
                            }
                        ]
                    }
                else:
                    # Query by object
                    query_string = {
                        "$and": [
                            {
                                "object_category": f"splk-{component}",
                                "object": object_value,
                            }
                        ]
                    }

                try:
                    object_rules_definition = collection_rules.data.query(
                        query=json.dumps(query_string)
                    )[0]
                    key = object_rules_definition.get("_key")
                    # Get object_value from KVstore if object_id was used
                    if object_id and not object_value:
                        object_value = object_rules_definition.get("object", "")

                except Exception as e:
                    logger.warning(
                        f'No rules found for object="{object_value}", skipping'
                    )
                    processed_count += 1
                    failures_count += 1
                    records.append(
                        {
                            "object": object_value,
                            "status": "failure",
                            "error": f"No rules found for object",
                        }
                    )
                    continue

                # Load as a dict
                try:
                    entities_outliers = json.loads(
                        object_rules_definition.get("entities_outliers")
                    )
                except Exception as e:
                    msg = f'Failed to load entities_outliers with exception="{str(e)}"'
                    logger.error(msg)
                    processed_count += 1
                    failures_count += 1
                    records.append(
                        {
                            "object": object_value,
                            "status": "failure",
                            "error": msg,
                        }
                    )
                    continue

                # Process all models (model_id='all')
                model_id = "all"
                model_id_exists = False
                models_updated = 0

                for entity_model_id in entities_outliers:
                    logger.debug(f'model_id="{entity_model_id}"')

                    entity_rules = entities_outliers[entity_model_id]
                    logger.debug(f'entity_rules="{json.dumps(entity_rules, indent=2)}"')

                    # if the model_id does not match, skip
                    if entity_model_id != model_id and not model_id in ("all", "*"):
                        continue
                    else:
                        model_id_exists = True

                    # log debug
                    logger.debug(f'Handling model_id="{entity_model_id}"')

                    # Get the current period_exclusions record (list)
                    period_exclusions = entity_rules.get("period_exclusions", [])

                    # period_exclusion_id, generate the sha256 hash of earliest:latest, use this to detect if the period was excluded already
                    period_exclusion_id = hashlib.sha256(
                        f"{earliest}:{latest}".encode()
                    ).hexdigest()

                    # boolean
                    period_exclusion_id_exists = False

                    if len(period_exclusions) > 0:
                        for period_exclusion in period_exclusions:
                            if (
                                period_exclusion["period_exclusion_id"]
                                == period_exclusion_id
                            ):
                                period_exclusion_id_exists = True
                                logger.info(
                                    f'period_exclusion_id="{period_exclusion_id}" already exists for model="{entity_model_id}", skipping'
                                )
                                continue

                    if not period_exclusion_id_exists:
                        # add the new period
                        period_exclusions.append(
                            {
                                "period_exclusion_id": period_exclusion_id,
                                "earliest": earliest,
                                "earliest_human": time.strftime(
                                    "%c", time.localtime(float(earliest))
                                ),
                                "latest": latest,
                                "latest_human": time.strftime(
                                    "%c", time.localtime(float(latest))
                                ),
                                "ctime": str(round(time.time(), 0)),
                            }
                        )
                        models_updated += 1

                    # Persist the updated period_exclusions back to entity_rules
                    entity_rules["period_exclusions"] = period_exclusions
                    # Update the entities_outliers dict with the modified entity_rules
                    entities_outliers[entity_model_id] = entity_rules

                # Update the record if any models were updated
                if model_id_exists and models_updated > 0:
                    object_rules_definition["entities_outliers"] = json.dumps(
                        entities_outliers, indent=2
                    )
                    object_rules_definition["mtime"] = time.time()

                    try:
                        collection_rules.data.update(
                            key, json.dumps(object_rules_definition)
                        )

                        # Audit event
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "success",
                                "bulk add outlier period exclusion",
                                str(object_value),
                                f"splk-{component}",
                                str(
                                    json.dumps(
                                        {
                                            "models_updated": models_updated,
                                            "earliest": earliest,
                                            "latest": latest,
                                        },
                                        indent=1,
                                    )
                                ),
                                f"Period exclusion was added successfully for {models_updated} model(s)",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.warning(
                                f'Failed to create audit event, exception="{str(e)}"'
                            )

                        processed_count += 1
                        success_count += 1
                        records.append(
                            {
                                "object": object_value,
                                "status": "success",
                                "message": f'Added period exclusion to {models_updated} model(s)',
                            }
                        )

                    except Exception as e:
                        msg = f'Failed to update record, exception="{str(e)}"'
                        logger.error(msg)
                        processed_count += 1
                        failures_count += 1
                        records.append(
                            {
                                "object": object_value,
                                "status": "failure",
                                "error": msg,
                            }
                        )
                elif not model_id_exists:
                    processed_count += 1
                    failures_count += 1
                    records.append(
                        {
                            "object": object_value,
                            "status": "failure",
                            "error": "No ML models found for this entity",
                        }
                    )
                else:
                    # No models were updated (period already exists)
                    processed_count += 1
                    success_count += 1
                    records.append(
                        {
                            "object": object_value,
                            "status": "skipped",
                            "message": "Period exclusion already exists for all models",
                        }
                    )

            except Exception as e:
                processed_count += 1
                failures_count += 1
                records.append(
                    {"object": object_value, "status": "failure", "error": str(e)}
                )

        summary = {
            "processed_count": processed_count,
            "success_count": success_count,
            "failures_count": failures_count,
            "records": records,
        }

        return {"payload": summary, "status": 200 if failures_count == 0 else 500}

    #
    # Set as false positive
    #

    def post_outliers_set_false_positive(self, request_info, **kwargs):
        """
        | trackme url=/services/trackme/v2/splk_outliers_engine/write/outliers_set_false_positive mode=post body="{ 'tenant_id': 'mytenant', 'component': 'dsm', 'object_id': 'abc123' }"
        """

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
                    return {"payload": "tenant_id is required", "status": 500}
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                try:
                    object_id = resp_dict["object_id"]
                except Exception as e:
                    return {"payload": "object_id is required", "status": 500}
                # Optional: object name for better logging
                object_value = resp_dict.get("object", None)

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "resource_desc": "Set outliers as false positive by generating negative score",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_outliers_engine/write/outliers_set_false_positive" body="{\'tenant_id\':\'mytenant\',\'component\':\'dsm\',\'object_id\':\'abc123\'}"',
                "describe": "This endpoint sets outliers as false positive by calculating the current outliers score and generating a negative score event to suppress the alert, it requires a POST call with the following options:",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category (dsm, dhm, mhm, flx, fqm, wlk)",
                        "object_id": "(required) entity identifier",
                        "object": "(optional) entity name for logging purposes",
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

        # Get TrackMe conf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')

        # Get tenant indexes
        tenant_indexes = trackme_idx_for_tenant(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
        )

        metrics_idx = tenant_indexes.get("trackme_metric_idx")
        if not metrics_idx:
            error_msg = f'tenant_id="{tenant_id}", metrics index not found'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}

        # Calculate current outliers score
        search_query = remove_leading_spaces(
            f"""
            | mstats sum(trackme.scoring.score) as score where index="{metrics_idx}"
            tenant_id="{tenant_id}" (score_source="lowerbound_outlier*" OR score_source="upperbound_outlier*" OR score_source="false_positive_outlier")
            object_id="{object_id}"
            | append [ | makeresults | eval score=0 | fields - _time ]
            | head 1
            """
        )

        try:
            # Prepare search parameters
            kwargs_search = {
                "earliest_time": "-24h",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            reader = run_splunk_search(
                service,
                search_query,
                kwargs_search,
                24,
                5,
            )

            current_score = 0
            # Read results from the reader
            search_results = []
            for item in reader:
                if isinstance(item, dict):
                    search_results.append(item)

            if search_results and len(search_results) > 0:
                try:
                    current_score = float(search_results[0].get("score", 0))
                except (ValueError, TypeError):
                    current_score = 0

            logger.info(
                f'tenant_id="{tenant_id}", component="{component}", object_id="{object_id}", current_score={current_score}, search_query="{search_query}"'
            )

            # If score is not positive, return early
            if current_score <= 0:
                return {
                    "payload": {
                        "message": f"Current outliers score is {current_score}, no action needed",
                        "current_score": current_score,
                    },
                    "status": 200,
                }

            # Generate negative score event to suppress the alert
            # Use a score_source that indicates false positive
            negative_score = -abs(current_score)

            # Get object name if not provided
            if not object_value:
                # Try to get object name from KVstore
                try:
                    collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
                    collection = service.kvstore[collection_name]
                    query_string = {"object_id": object_id}
                    results = collection.data.query(query=json.dumps(query_string))
                    if results and len(results) > 0:
                        object_value = results[0].get("object", object_id)
                    else:
                        object_value = object_id
                except Exception as e:
                    logger.warning(
                        f'Failed to get object name for object_id="{object_id}", exception={str(e)}'
                    )
                    object_value = object_id

            # Generate score_id for traceability between cache and metrics event
            score_id_ctime = time.time()
            score_id = generate_score_id(tenant_id, object_id, component, "false_positive_outlier", negative_score, score_id_ctime)

            # Create scoring record
            scoring_record = {
                "tenant_id": tenant_id,
                "object_id": object_id,
                "object": object_value,
                "object_category": component,
                "score_source": "false_positive_outlier",
                "metrics_event": {
                    "score_id": score_id,
                    "score": negative_score,
                    "original_score": current_score,
                    "reason": "User marked as false positive",
                },
            }

            # Generate the scoring metrics
            try:
                scoring_result = trackme_scoring_gen_metrics(
                    tenant_id=tenant_id,
                    metrics_idx=metrics_idx,
                    records=[scoring_record],
                )

                if scoring_result:
                    # Create audit event
                    try:
                        trackme_audit_event(
                            session_key=request_info.system_authtoken,
                            splunkd_uri=request_info.server_rest_uri,
                            tenant_id=tenant_id,
                            user=request_info.user,
                            action="success",
                            change_type="set outliers as false positive",
                            object_name=str(object_value),
                            object_category=component,
                            object_attrs=json.dumps({"object_id": object_id}),
                            result=json.dumps(
                                {
                                    "original_score": current_score,
                                    "negative_score": negative_score,
                                }
                            ),
                            comment="Outliers marked as false positive",
                            object_id=object_id,
                        )
                    except Exception as e:
                        logger.warning(
                            f'Failed to create audit event, exception={str(e)}'
                        )

                    # also generate events for the score
                    for score_event in [scoring_record]:
                        try:
                            trackme_gen_state(
                                index=tenant_indexes.get("trackme_summary_idx"),
                                sourcetype="trackme:score",
                                source=f"/services/trackme/v2/splk_outliers_engine/write/outliers_set_false_positive",
                                event=score_event,
                            )
                        except Exception as e:
                            logger.warning(
                                f'Failed to generate score state event, exception={str(e)}'
                            )

                    # Write to score cache for immediate visibility (no need to wait for metrics indexing)
                    try:
                        write_score_cache(
                            service, tenant_id, object_id, object_value,
                            component, "false_positive_outlier", negative_score,
                            score_id=score_id, ctime=score_id_ctime,
                        )
                        logger.info(
                            f'Score cache written, score_id="{score_id}", tenant_id="{tenant_id}", '
                            f'component="{component}", object_id="{object_id}", score={negative_score}'
                        )
                    except Exception as e:
                        logger.warning(
                            f'Failed to write score cache, exception={str(e)}'
                        )

                    # Retrieve shadow_enabled for shadow refresh
                    try:
                        vtenant_conf = trackme_vtenant_account_from_service(service, tenant_id)
                        shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))
                    except Exception:
                        shadow_enabled = None

                    # Refresh shadow record in background (non-blocking)
                    t = threading.Thread(
                        target=refresh_shadow_after_score_change,
                        args=(service, request_info.server_rest_uri, request_info.system_authtoken,
                              tenant_id, component, object_id),
                        kwargs={
                            "shadow_enabled": shadow_enabled,
                            "splunkd_port": request_info.server_rest_port,
                        },
                        daemon=True,
                    )
                    t.start()

                    # Refresh tenant component summary cache (drives the
                    # Single Value cards on Tenant Home). Score-only
                    # mutations don't touch entity KV records, so the
                    # cached <component>_extended_stats blob stays stale
                    # until the next scheduled tracker fires unless we
                    # refresh it here.
                    trackme_refresh_component_summary_async(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        component,
                        object_id=object_id,
                        logger_=logger,
                    )

                    return {
                        "payload": {
                            "message": "False positive score generated successfully",
                            "original_score": current_score,
                            "negative_score": negative_score,
                        },
                        "status": 200,
                    }
                else:
                    error_msg = "Failed to generate scoring metrics"
                    logger.error(error_msg)
                    return {"payload": {"error": error_msg}, "status": 500}

            except Exception as e:
                error_msg = f'Failed to generate scoring metrics, exception="{str(e)}", scoring_record="{json.dumps(scoring_record, indent=2)}"'
                logger.error(error_msg)
                return {"payload": {"error": error_msg}, "status": 500}

        except Exception as e:
            error_msg = f'Failed to calculate current score, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}
