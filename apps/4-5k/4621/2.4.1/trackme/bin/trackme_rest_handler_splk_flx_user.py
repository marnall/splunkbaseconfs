#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_flx.py"
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
import time
import requests
from collections import OrderedDict

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_flx_user", "trackme_rest_api_splk_flx_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, trackme_getloglevel, trackme_idx_for_tenant, trackme_parse_describe_flag

# import TrackMe splk-flx libs
from trackme_libs_splk_flx import splk_flx_return_searches

# import TrackMe converging helpers (parse the canonical command string)
from trackme_libs_flx_converging import parse_converging_command

# import trackme libs utils
from trackme_libs_utils import decode_unicode

# import trackme decision maker
from trackme_libs_decisionmaker import convert_epoch_to_datetime

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkFlxTrackingRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkFlxTrackingRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_flx(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_flx",
            "resource_group_desc": "Endpoints specific to the splk-flx TrackMe component (Splunk Flex objects tracking, read-only operations).",
        }

        return {"payload": response, "status": 200}

    # get the component table
    def post_flx_get_table(self, request_info, **kwargs):
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
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }

                try:
                    key_id = resp_dict["key_id"]
                    if key_id == "*":
                        key_id = None
                except Exception as e:
                    key_id = None

                try:
                    object = resp_dict["object"]
                    if object == "*":
                        object = None
                except Exception as e:
                    object = None

                # only key_id or object can be specified
                if key_id and object:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "only key_id or object can be specified, not both",
                        },
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the component table. It requires a POST call with the following options:",
                "resource_desc": "Get the entity table",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_get_table\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'key_id': '*', 'object': '*'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "key_id": "(Optional) The key ID. Do not specify this to match all entities",
                        "object": "(Optional) The entity name. Do not specify this to match all entities",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # url
        url = f"{request_info.server_rest_uri}/services/trackme/v2/component/load_component_data"

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {request_info.system_authtoken}",
            "Content-Type": "application/json",
        }

        params = {
            "tenant_id": tenant_id,
            "component": "flx",
            "page": 1,
            "size": 0,
        }

        if key_id:
            params["filter_key"] = key_id
        elif object:
            params["object_key"] = object

        data_records = []

        # Proceed
        try:
            response = requests.get(
                url,
                headers=header,
                params=params,
                verify=False,
                timeout=600,
            )

            if response.status_code not in (200, 201, 204):
                msg = f'get component has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                return {"payload": msg, "status": 500}

            else:
                response_json = response.json()
                data = response_json.get("data", [])

                # add the data to the data_records
                for record in data:
                    data_records.append(record)

                # return
                return {"payload": data_records, "status": 200}

        except Exception as e:
            msg = f'get component has failed, exception="{str(e)}"'
            logger.error(msg)
            return {"payload": msg, "status": 500}

    # get all records
    def post_flx_tracker_show(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_flx/flx_tracker_show" body="{'tenant_id': 'mytenant'}"
        """

        # Declare
        tenant_id = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]

                # show_search, defaults to False
                show_search = resp_dict.get("show_search", False)
                if show_search in ("true", "True"):
                    show_search = True
                else:
                    show_search = False

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all records for the hybrid tracker collection. It requires a POST call with the following information:",
                "resource_desc": "Get hybrid trackers",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/flx_tracker_show\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "show_search": "Show the search definition for the tracker, in large environments and/or with many trackers this can cause UI performance issues. Defaults to False.",
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

        # Declare
        trackers_list = []
        seen_tracker_ids = set()  # Track seen tracker_ids for deduplication

        try:
            # Data collection
            collection_name = "kv_trackme_flx_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            for entity in collection.data.query():
                tracker_id = entity.get("tracker_id")
                
                # Skip if we've already seen this tracker_id
                if tracker_id in seen_tracker_ids:
                    continue
                
                # Add tracker_id to seen set
                seen_tracker_ids.add(tracker_id)
                tracker_name = entity.get("tracker_name")
                knowledge_objects = entity.get("knowledge_objects")
                # try to load as a json
                try:
                    knowledge_objects = json.loads(knowledge_objects)
                except Exception as e:
                    knowledge_objects = {}

                # get the live definition
                ko_json = {}
                ko_json["reports"] = []
                ko_json["properties"] = {}

                # Tracker type — derived from the _wrapper report's live search:
                # a wrapper that runs the `trackmesplkflxconverging` command is a
                # converging tracker, anything else is a use case tracker. Defaults
                # to use_case if the wrapper can't be read.
                tracker_type = "use_case"

                if knowledge_objects:
                    reports_list = knowledge_objects.get("reports", [])
                    ko_json["reports"] = reports_list
                    for report_name in reports_list:

                        # _tracker only
                        if "_tracker" in report_name:
                            try:
                                savedsearch = service.saved_searches[report_name]
                                search_cron_schedule = savedsearch.content[
                                    "cron_schedule"
                                ]
                                search_earliest = savedsearch.content[
                                    "dispatch.earliest_time"
                                ]
                                search_latest = savedsearch.content[
                                    "dispatch.latest_time"
                                ]
                                ko_json["properties"][
                                    "cron_schedule"
                                ] = search_cron_schedule
                                ko_json["properties"]["earliest"] = search_earliest
                                ko_json["properties"]["latest"] = search_latest
                            except Exception as e:
                                logger.error(
                                    f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                )

                        # _wrapper: read the live search to (1) detect the tracker
                        # type (converging vs use_case) and (2) optionally expose
                        # the search string when show_search is requested.
                        if "_wrapper" in report_name:
                            try:
                                savedsearch = service.saved_searches[report_name]
                                savedsearch_definition = savedsearch.content[
                                    "search"
                                ]
                                if "trackmesplkflxconverging" in str(savedsearch_definition).lower():
                                    tracker_type = "converging"
                                else:
                                    tracker_type = "use_case"
                                if show_search:
                                    ko_json["properties"][
                                        "search"
                                    ] = savedsearch_definition
                            except Exception as e:
                                logger.error(
                                    f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                )

                # add to the list
                trackers_list.append(
                    {
                        "tracker_id": tracker_id,
                        "tracker_name": tracker_name,
                        "type": tracker_type,
                        "knowledge_objects": ko_json,
                    }
                )

            return {"payload": trackers_list, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"response": error_msg}, "status": 500}

    # Get the parsed configuration of a converging tracker (for the edit modal)
    def post_flx_converging_tracker_get(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_flx/flx_converging_tracker_get" body="{'tenant_id': 'mytenant', 'object': '01-Service-Availability:service-availability-001'}"

        Returns the editable configuration of a converging Flex tracker by
        parsing the canonical command string stored in the hybrid-tracker KV
        registry (knowledge_objects.properties[0].root_constraint). This feeds
        the UI-driven "Modify converging tracker" modal so it can pre-fill the
        current values without the frontend having to parse SPL.

        Resolution: the caller passes the entity `object` (preferred — it maps
        1:1 to a single converging tracker via the KV key, which is robust even
        when a row carries a merged/sorted multi-tracker_name array) and/or the
        `tracker_name`. When `object` is given the handler authoritatively
        resolves the owning tracker by matching the parsed command's
        group:object against the entity object, and returns the resolved
        `tracker_name` so the modal can drive the in-place update.
        """

        tenant_id = None
        tracker_name = None
        object_value = None
        describe = False

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id")
                tracker_name = resp_dict.get("tracker_name")
                object_value = resp_dict.get("object")
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the editable configuration of a converging Flex Object tracker, parsed from its canonical command definition. It requires a POST call with the following information:",
                "resource_desc": "Get a converging Flex Object tracker configuration",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/flx_converging_tracker_get\" body=\"{'tenant_id': 'mytenant', 'object': '01-Service-Availability:service-availability-001'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "PREFERRED. The entity object (group:object) — resolves the owning converging tracker authoritatively (1:1 via the KV key)",
                        "tracker_name": "OPTIONAL. The tracker identifier (tracker_id). Used when object is not provided; verified against object when both are given",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if not tenant_id:
            return {"payload": {"response": "tenant_id is required"}, "status": 500}
        if not tracker_name and not object_value:
            return {"payload": {"response": "one of object or tracker_name is required"}, "status": 500}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            collection_name = "kv_trackme_flx_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            record = None

            # 1) Preferred: resolve by object — scan the registry and match the
            #    parsed command's group:object (or bare object) against the
            #    entity object. This is authoritative even when a row carries a
            #    merged/sorted multi-tracker_name array (concurrent trackers).
            if object_value:
                for candidate in collection.data.query():
                    try:
                        ko = json.loads(candidate.get("knowledge_objects"))
                    except Exception:
                        continue
                    props = ko.get("properties") or []
                    if not props:
                        continue
                    parsed_c = parse_converging_command(props[0].get("root_constraint", ""))
                    c_obj = parsed_c.get("object") or ""
                    c_grp = parsed_c.get("group") or ""
                    full = f"{c_grp}:{c_obj}" if c_grp else c_obj
                    if object_value in (full, c_obj):
                        record = candidate
                        break

            # 2) Fallback: resolve by tracker_name (tracker_id) when object did
            #    not match or was not provided.
            if record is None and tracker_name:
                by_name = collection.data.query(
                    query=json.dumps({"tracker_id": tracker_name})
                )
                if by_name:
                    record = by_name[0]

            if record is None:
                return {
                    "payload": {
                        "response": f'tenant_id="{tenant_id}", no converging tracker matched object="{object_value}" / tracker_name="{tracker_name}"'
                    },
                    "status": 404,
                }

            resolved_tracker_name = record.get("tracker_id") or record.get("tracker_name")
            knowledge_objects = record.get("knowledge_objects")
            try:
                knowledge_objects = json.loads(knowledge_objects)
            except Exception:
                knowledge_objects = {}

            properties = knowledge_objects.get("properties") or []
            properties_dict = properties[0] if properties else {}
            root_constraint_cmd = properties_dict.get("root_constraint", "")

            # Parse the canonical command into the editable fields
            parsed = parse_converging_command(root_constraint_cmd)

            payload = {
                "tenant_id": tenant_id,
                "tracker_name": resolved_tracker_name,
                "tenants_scope": parsed["tenants_scope"],
                "object": parsed["object"],
                "group": parsed["group"],
                "object_description": parsed["object_description"],
                "root_constraint": parsed["root_constraint"],
                "consider_orange_as_up": parsed["consider_orange_as_up"],
                "min_pct_for_green": parsed["min_pct_for_green"],
                "cron_schedule": properties_dict.get("cron_schedule"),
                "earliest": properties_dict.get("earliest"),
                "latest": properties_dict.get("latest"),
                "enable_zero_kpis_when_inactive": record.get(
                    "enable_zero_kpis_when_inactive"
                ),
            }
            return {"payload": payload, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", object="{object_value}", tracker_name="{tracker_name}", an exception was encountered="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"response": error_msg}, "status": 500}

    # Get entity info
    def post_flx_entity_info(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/splk_flx/flx_entity_info" mode="post" body="{'tenant_id': 'mytenant', 'object': 'Okta:Splunk_TA_okta_identity_cloud:okta_logs'}"
        """

        # init
        object_id = None
        object_value = None
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
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }
                # object or object_id must be provided, but not both
                try:
                    object_value = resp_dict["object"]
                except Exception as e:
                    object_value = None
                try:
                    object_id = resp_dict["object_id"]
                except Exception as e:
                    object_id = None
                if object_value and object_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "only object or object_id can be specified, not both",
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns various information related to the entity, it requires a POST call with the following information:",
                "resource_desc": "Return the entity main information, these normalized information are used to build dynamically the various queries through the user interfaces",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_entity_info\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object': 'remote|account:lab|firewall.pan.amer.design.node1'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "The entity identifier, you can specify the object or the object_id, but not both",
                        "object_id": "The entity key identifier, you can specify the object or the object_id, but not both",
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

        # Data collection
        collection_name = "kv_trackme_flx_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # Define the KV query
        query_string = {}

        if object_value:
            query_string["object"] = object_value
        elif object_id:
            query_string["_key"] = object_id

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        try:
            kvrecord = collection.data.query(query=json.dumps(query_string))[0]
            key = kvrecord.get("_key")
            if not object_value:
                object_value = kvrecord.get("object")

        except Exception as e:
            key = None

            if not object_value:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'the entity with identifier="{object_id}" was not found',
                    },
                    "status": 404,
                }

            else:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'the entity with identifier="{object_value}" was not found',
                    },
                    "status": 404,
                }

        # proceed
        if key:
            # init
            response = {}

            try:
                # entity_info
                entity_info = {}

                # get tenant metric index
                tenant_indexes = trackme_idx_for_tenant(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                )
                tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

                # get entity searches
                entity_searches = splk_flx_return_searches(tenant_id, kvrecord, tenant_trackme_metric_idx=tenant_trackme_metric_idx)

                # log debug
                logger.debug(
                    f'function splk_flx_return_searches, entity_searches="{json.dumps(entity_searches, indent=2)}"'
                )

                # add
                entity_info["splk_flx_mctalog_search"] = entity_searches.get(
                    "splk_flx_mctalog_search"
                )
                entity_info["splk_flx_mctalog_search_litsearch"] = entity_searches.get(
                    "splk_flx_mctalog_search_litsearch"
                )
                entity_info["splk_flx_metrics_report"] = entity_searches.get(
                    "splk_flx_metrics_report"
                )
                entity_info["splk_flx_metrics_report_litsearch"] = entity_searches.get(
                    "splk_flx_metrics_report_litsearch"
                )
                entity_info["splk_flx_mpreview"] = entity_searches.get(
                    "splk_flx_mpreview"
                )
                entity_info["splk_flx_mpreview_litsearch"] = entity_searches.get(
                    "splk_flx_mpreview_litsearch"
                )
                entity_info["splk_flx_metrics_populate_search"] = entity_searches.get(
                    "splk_flx_metrics_populate_search"
                )

                # add object and key
                entity_info["object"] = object_value
                entity_info["key"] = key

                # render response
                return {"payload": entity_info, "status": 200}

            except Exception as e:
                # render response
                msg = f'An exception was encountered while processing entity get info, exception="{str(e)}"'
                logger.error(msg)
                return {
                    "payload": {
                        "action": "failure",
                        "response": msg,
                    },
                    "status": 500,
                }

    # get thresholds
    def post_flx_get_thresholds(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]

                # handle object_list / keys_list
                object_list = resp_dict.get("object_list", None)
                if object_list:
                    if not isinstance(object_list, list):
                        object_list = object_list.split(",")

                keys_list = extract_keys_list(resp_dict)
                if keys_list:
                    if not isinstance(keys_list, list):
                        keys_list = keys_list.split(",")

                if not object_list and not keys_list:
                    return {
                        "payload": {
                            "error": "either object_list or keys_list must be provided"
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves thresholds for a given list of entities, it requires a POST call with the following information:",
                "resource_desc": "Retrieve thresholds for a given list of entities",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_get_thresholds\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_list': 'entity1,entity2'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_list": "List of object entities, provided as a comma separated list of fields, you can provide object_list or keys_list",
                        "keys_list": "List of key entities, provided as a comma separated list of fields, you can provide object_list or keys_list",
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

        # Data collection
        collection_name = "kv_trackme_flx_thresholds_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # loop and proceed
        return_records = []

        if object_list:
            keys_list = []
            for object in object_list:
                try:
                    kvrecord = collection.data.query(
                        query=json.dumps({"object": object})
                    )[0]
                    key = kvrecord.get("_key")
                    keys_list.append(key)
                except Exception as e:
                    key = None

        for key in keys_list:
            try:
                kvrecords = collection.data.query(query=json.dumps({"object_id": key}))
                for kvrecord in kvrecords:

                    mtime = kvrecord.get("mtime")
                    if mtime:
                        mtime = convert_epoch_to_datetime(mtime)
                    else:
                        mtime = "N/A"

                    # Get score, default to 100 if not present (for backward compatibility)
                    score = kvrecord.get("score")
                    if score is None:
                        score = 100
                    else:
                        try:
                            score = int(score)
                        except (TypeError, ValueError):
                            score = 100
                    
                    return_records.append(
                        {
                            "_key": kvrecord.get("_key"),
                            "object_id": kvrecord.get("object_id"),
                            "metric_name": kvrecord.get("metric_name"),
                            "value": kvrecord.get("value"),
                            "operator": kvrecord.get("operator"),
                            "condition_true": kvrecord.get("condition_true"),
                            "mtime": mtime,
                            "comment": kvrecord.get("comment"),
                            "score": score,
                            "variable_threshold_enabled": kvrecord.get("variable_threshold_enabled", "false"),
                            "variable_threshold_default": kvrecord.get("variable_threshold_default"),
                            "variable_threshold_slots": kvrecord.get("variable_threshold_slots"),
                        }
                    )
            except:
                pass

        # render
        return {"payload": return_records, "status": 200}


    # get drilldown search for a given tracker
    def post_flx_get_drilldown_search_for_tracker(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # tracker_name
                try:
                    tracker_name = resp_dict["tracker_name"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The tracker_name is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the drilldown search definition for a given tracker, it requires a POST call with the following information:",
                "resource_desc": "Retrieve the drilldown search definition for a given tracker",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_get_drilldown_search_for_tracker\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'mytracker'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_name": "The name of the tracker",
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

        # Data collection
        collection_name = f"kv_trackme_flx_drilldown_searches_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # iterate through the collection
        drilldown_search_record = None
        for record in collection.data.query():
            if record.get("tracker_name") == tracker_name:
                return {
                    "payload": {
                        "tracker_name": tracker_name,
                        "drilldown_search": record.get("drilldown_search"),
                        "drilldown_search_earliest": record.get("drilldown_search_earliest"),
                        "drilldown_search_latest": record.get("drilldown_search_latest"),
                    },
                    "status": 200,
                }

        # not found, return an empty record
        if not drilldown_search_record:
            return {
                "payload": {
                    "tracker_name": tracker_name,
                    "drilldown_search": None,
                    "drilldown_search_earliest": None,
                    "drilldown_search_latest": None,
                },
                "status": 200,
            }

    # get all drilldown searches as a list of records for a given tenant
    def post_flx_get_all_drilldown_searches_for_tenant(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all drilldown search definitions for a given tenant, it requires a POST call with the following information:",
                "resource_desc": "Retrieve all drilldown search definitions for a given tenant",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_get_all_drilldown_searches_for_tenant\" mode=\"post\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
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

        # Data collection
        collection_name = f"kv_trackme_flx_drilldown_searches_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # iterate through the collection
        drilldown_search_records = []
        for record in collection.data.query():
            drilldown_search_records.append(record)
            
        # render
        return {"payload": drilldown_search_records, "status": 200}

    # get default metric for a given tracker
    def post_flx_get_default_metric_for_tracker(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # tracker_name
                try:
                    tracker_name = resp_dict["tracker_name"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The tracker_name is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the default metric definition for a given tracker, it requires a POST call with the following information:",
                "resource_desc": "Retrieve the default metric definition for a given tracker",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_get_default_metric_for_tracker\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'mytracker'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_name": "The name of the tracker",
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

        # Data collection
        collection_name = f"kv_trackme_flx_default_metric_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # iterate through the collection
        default_metric_record = None
        for record in collection.data.query():
            if record.get("tracker_name") == tracker_name:
                return {
                    "payload": {
                        "tracker_name": tracker_name,
                        "metric_name": record.get("metric_name"),
                    },
                    "status": 200,
                }

        # not found, return an empty record
        if not default_metric_record:
            return {
                "payload": {
                    "tracker_name": tracker_name,
                    "metric_name": None,
                },
                "status": 200,
            }

    # get all default metrics as a list of records for a given tenant
    def post_flx_get_all_default_metrics_for_tenant(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all default metric definitions for a given tenant, it requires a POST call with the following information:",
                "resource_desc": "Retrieve all default metric definitions for a given tenant",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/flx_get_all_default_metrics_for_tenant\" mode=\"post\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
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

        # Data collection
        collection_name = f"kv_trackme_flx_default_metric_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # iterate through the collection
        default_metric_records = []
        for record in collection.data.query():
            default_metric_records.append(record)
            
        # render
        return {"payload": default_metric_records, "status": 200}
