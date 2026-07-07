#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_component.py"
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
import hashlib
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
    "trackme.rest.component_power", "trackme_rest_api_component_power.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    get_splunkd_timeout,
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

# import trackme libs scoring
from trackme_libs_scoring import trackme_scoring_gen_metrics, generate_score_id, write_score_cache

# import the in-process decision-maker engine (used by some endpoints
# below to avoid an HTTP loopback into load_component_data — see
# ai-context/backend/decision-maker-engine.md).
from trackme_libs_decisionmaker_engine import DecisionMakerEngine

# import shadow libs
import threading
from trackme_libs_shadow import refresh_shadow_after_score_change

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerComponentPower_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerComponentPower_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_component(self, request_info, **kwargs):
        response = {
            "resource_group_name": "component/write",
            "resource_group_desc": "Endpoints specific to TrackMe's components data offload (write operations)",
        }

        return {"payload": response, "status": 200}

    # Update the component summary
    def post_component_summary_update(self, request_info, **kwargs):
        describe = False

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:
                # tenant_id
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {"error": "tenant_id is required"},
                        "status": 500,
                    }

                # component
                try:
                    component = resp_dict["component"]
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "flx",
                        "fqm",
                        "wlk",
                    ):
                        return {
                            "payload": {"error": "component is invalid"},
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {"error": "component is required"},
                        "status": 500,
                    }

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint updates the component summary collection which contains high level summary information used in the Virtual Tenant UI for the tenant and component, this endpoint is called automatically by TrackMe to maintain these information, it requires a POST call using data and the following options:",
                "resource_desc": "Update the component summary",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/component/write/component_summary_update\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'component': 'flx'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "component identifier, valid options are: dsm, dhm, mhm, flx, wlk, fqm",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        ))

        # Get service
        # Wrapped in try-except to handle connection errors gracefully and return
        # user-friendly JSON error responses instead of unhandled exceptions
        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=splunkd_timeout,
            )
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            error_msg = f'Failed to connect to local splunkd, connection error="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}
        except Exception as e:
            error_msg = f'Failed to connect to local splunkd, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}

        # summary KVstore collection
        summary_collection_name = f"kv_trackme_virtual_tenants_entities_summary"
        summary_collection = service.kvstore[summary_collection_name]

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # performance counter
        start = time.time()

        def count_records(record, stats):
            """
            Update the stats based on the properties of the record.

            :param record: A dictionary representing a single record.
            :param stats: A dictionary holding the count of various statistics.
            """
            # Increase the total entities count
            if record.get("monitored_state") == "enabled":
                stats["entities"] += 1

            # Check if the object_state is red and increment the appropriate priority counter
            if (
                record.get("object_state") == "red"
                and record.get("monitored_state") == "enabled"
            ):
                priority = record.get("priority")
                if priority == "low":
                    stats["low_red_priority"] += 1
                elif priority == "medium":
                    stats["medium_red_priority"] += 1
                elif priority == "high":
                    stats["high_red_priority"] += 1
                elif priority == "critical":
                    stats["critical_red_priority"] += 1

            # Update the last_exec with the maximum tracker_runtime value
            try:
                tracker_runtime = float(record.get("tracker_runtime", 0))
            except Exception as e:
                tracker_runtime = 0
            if tracker_runtime > stats.get("last_exec", 0):
                stats["last_exec"] = tracker_runtime

        def extended_count_records(record, extended_stats):
            """
            Update the extended_stats based on the properties of the record.

            :param record: A dictionary representing a single record.
            :param extended_stats: A dictionary holding the count of various statistics.
            """
            if record.get("monitored_state") == "enabled":
                extended_stats["count_total"] += 1
            if record.get("monitored_state") == "disabled":
                extended_stats["count_total_disabled"] += 1
            if (
                record.get("object_state") == "red"
                and record.get("monitored_state") == "enabled"
            ):
                extended_stats["count_total_in_alert"] += 1
            if (
                record.get("object_state") == "red"
                and record.get("priority") == "high"
                and record.get("monitored_state") == "enabled"
            ):
                extended_stats["count_total_high_priority_red"] += 1
            if (
                record.get("object_state") == "red"
                and record.get("priority") == "critical"
                and record.get("monitored_state") == "enabled"
            ):
                extended_stats["count_total_critical_priority_red"] += 1
            if record.get("monitored_state") == "enabled":
                if record.get("priority") == "low":
                    extended_stats["count_low_enabled"] += 1
                if record.get("priority") == "medium":
                    extended_stats["count_medium_enabled"] += 1
                if record.get("priority") == "high":
                    extended_stats["count_high_enabled"] += 1
                if record.get("priority") == "critical":
                    extended_stats["count_critical_enabled"] += 1
                if record.get("priority") == "pending":
                    extended_stats["count_pending_enabled"] += 1
                if record.get("object_state") == "green":
                    extended_stats["count_green_enabled"] += 1
                if record.get("object_state") == "blue":
                    extended_stats["count_blue_enabled"] += 1
                if record.get("object_state") == "orange":
                    extended_stats["count_orange_enabled"] += 1
                if (
                    record.get("object_state") == "red"
                    and record.get("priority") == "low"
                ):
                    extended_stats["count_red_low_priority_enabled"] += 1
                if (
                    record.get("object_state") == "red"
                    and record.get("priority") == "medium"
                ):
                    extended_stats["count_red_medium_priority_enabled"] += 1
                if (
                    record.get("object_state") == "red"
                    and record.get("priority") == "high"
                ):
                    extended_stats["count_red_high_priority_enabled"] += 1
                if (
                    record.get("object_state") == "red"
                    and record.get("priority") == "critical"
                ):
                    extended_stats["count_red_critical_priority_enabled"] += 1
                if (
                    record.get("object_state") == "red"
                    and record.get("priority") != "high"
                    and record.get("priority") != "critical"
                ):
                    extended_stats["count_red_other_priority_enabled"] += 1
            extended_stats["mtime"] = time.time()
            extended_stats["human_mtime"] = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.gmtime(extended_stats["mtime"])
            )

        # Initialize the stats dictionary with the new structure
        stats = {
            "entities": 0,
            "low_red_priority": 0,
            "medium_red_priority": 0,
            "high_red_priority": 0,
            "critical_red_priority": 0,
            "last_exec": 0,  # Assuming tracker_runtime is an epoch time, initialize with 0
        }

        # extended stats
        extended_stats = {
            "count_total": 0,
            "count_total_disabled": 0,
            "count_total_in_alert": 0,
            "count_total_high_priority_red": 0,
            "count_total_critical_priority_red": 0,
            "count_low_enabled": 0,
            "count_medium_enabled": 0,
            "count_high_enabled": 0,
            "count_critical_enabled": 0,
            "count_pending_enabled": 0,
            "count_blue_enabled": 0,
            "count_orange_enabled": 0,
            "count_green_enabled": 0,
            "count_red_low_priority_enabled": 0,
            "count_red_medium_priority_enabled": 0,
            "count_red_high_priority_enabled": 0,
            "count_red_critical_priority_enabled": 0,
            "count_red_other_priority_enabled": 0,
            "mtime": 0,
            "human_mtime": 0,
        }

        params = {
            "tenant_id": tenant_id,
            "component": component,
            "page": 1,
            "size": 0,
            "caller": "trackme_rest_handler_component_power",  # Identify this as a REST handler call
        }

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {request_info.system_authtoken}",
            "Content-Type": "application/json",
        }

        # Add the vtenant account
        url = f"{request_info.server_rest_uri}/services/trackme/v2/component/load_component_data"

        # Proceed
        try:
            logger.info(f'calling api url="{url}", params="{params}"')

            response = requests.get(
                url,
                headers=header,
                params=params,
                verify=False,
                timeout=splunkd_timeout,
            )

            if response.status_code not in (200, 201, 204):
                msg = f'get component has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(msg)

            else:
                response_json = response.json()
                last_page = response_json.get("last_page", 1)
                data = response_json.get("data", [])

                # add the data to the data_records
                for record in data:
                    # count the records
                    count_records(record, stats)
                    extended_count_records(record, extended_stats)

        except Exception as e:
            msg = f'get component has failed, exception="{str(e)}"'
            logger.error(msg)
            # Use "error" key to maintain consistency with other error responses in this file
            return {"payload": {"error": msg}, "status": 500}

        # Get the summary record
        try:
            vtenant_record = summary_collection.data.query(
                query=json.dumps({"tenant_id": tenant_id})
            )[0]
            vtenant_key = vtenant_record.get("_key")
            logger.debug(
                f'tenant_id="{tenant_id}", vtenant_key="{vtenant_key}", vtenant_report="{json.dumps(vtenant_record)}"'
            )
        except Exception as e:
            vtenant_record = {}
            vtenant_key = None

        # update the summary record
        vtenant_record[f"{component}_entities"] = stats.get("entities")
        vtenant_record[f"{component}_low_red_priority"] = stats.get("low_red_priority")
        vtenant_record[f"{component}_medium_red_priority"] = stats.get(
            "medium_red_priority"
        )
        vtenant_record[f"{component}_high_red_priority"] = stats.get(
            "high_red_priority"
        )
        vtenant_record[f"{component}_critical_red_priority"] = stats.get(
            "critical_red_priority"
        )
        vtenant_record[f"{component}_last_exec"] = stats.get("last_exec")
        vtenant_record[f"{component}_summary_stats"] = json.dumps(stats, indent=2)
        vtenant_record[f"{component}_extended_stats"] = json.dumps(
            extended_stats, indent=2
        )

        try:
            if vtenant_key:
                summary_collection.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )
            else:
                vtenant_record["tenant_id"] = tenant_id
                # add _key as the sha256 of the tenant_id
                vtenant_record["_key"] = hashlib.sha256(
                    f"{tenant_id}".encode()
                ).hexdigest()
                summary_collection.data.insert(json.dumps(vtenant_record))

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}" cannot be updated or created, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": error_msg,
                },
                "status": 500,
            }

        # run_time
        run_time = round((time.time() - start), 3)
        stats["run_time"] = run_time

        # return the response
        logger.info(
            f'context="perf", no_records="{stats.get("entities")}", run_time="{run_time}", tenant_id="{tenant_id}", component="{component}"'
        )

        return {
            "payload": {
                "response": "component summary has been updated",
                "stats": stats,
                "extended_stats": extended_stats,
                "vtenant_summary_record": vtenant_record,
            },
            "status": 200,
        }

    def post_set_false_positive(self, request_info, **kwargs):
        """
        | trackme url=/services/trackme/v2/component/write/set_false_positive mode=post body="{ 'tenant_id': 'mytenant', 'component': 'dsm', 'object_id': 'abc123' }"
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
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "flx",
                        "fqm",
                        "wlk",
                    ):
                        return {"payload": "component is invalid, must be one of: dsm, dhm, mhm, flx, fqm, wlk", "status": 500}
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
                "resource_desc": "Set entity as false positive by generating negative score",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/component/write/set_false_positive" body="{\'tenant_id\':\'mytenant\',\'component\':\'dsm\',\'object_id\':\'abc123\'}"',
                "describe": "This endpoint sets an entity as false positive by calculating the current global impact score and generating a negative score event to suppress the alert, it requires a POST call with the following options:",
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

        # Get TrackMe conf and configurable splunkd timeout
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')
        splunkd_timeout = get_splunkd_timeout(reqinfo=trackme_conf)

        # Get service
        # Wrapped in try-except to handle connection errors gracefully and return
        # user-friendly JSON error responses instead of unhandled exceptions
        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.system_authtoken,
                timeout=splunkd_timeout,
            )
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            error_msg = f'Failed to connect to local splunkd, connection error="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}
        except Exception as e:
            error_msg = f'Failed to connect to local splunkd, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

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

        # Initialize scoring_record to None to prevent NameError if exception occurs before it's defined
        scoring_record = None

        # Get current global impact score from the decision maker.
        # Uses the in-process DecisionMakerEngine instead of an HTTP loopback
        # to /trackme/v2/component/load_component_data — same library code
        # (set_*_status / scoring helpers), no JSON serialization or REST
        # round-trip overhead.
        try:
            engine = DecisionMakerEngine(
                session_key=request_info.session_key,
                splunkd_uri=request_info.server_rest_uri,
                tenant_id=tenant_id,
                component=component,
                system_authtoken=request_info.system_authtoken,
                splunkd_port=request_info.server_rest_port,
                logger=logger,
            )
            engine.load()
            evaluated = engine.evaluate_object_full(object_id)

            # Validate entity exists before processing — covers both "missing"
            # and "filtered by blocklist" (engine surfaces both as None,
            # matching the previous load_component_data empty-data behaviour).
            if evaluated is None:
                error_msg = f'Entity with object_id="{object_id}" does not exist for tenant_id="{tenant_id}" and component="{component}"'
                logger.error(error_msg)
                return {"payload": {"error": error_msg}, "status": 404}

            current_score = 0
            try:
                score_value = evaluated.get("score", 0)
                if score_value is not None:
                    current_score = float(score_value)
                else:
                    current_score = 0
            except (ValueError, TypeError) as e:
                logger.warning(
                    f'Failed to parse score from engine output, score_value="{evaluated.get("score")}", exception="{str(e)}"'
                )
                current_score = 0

            logger.info(
                f'tenant_id="{tenant_id}", component="{component}", object_id="{object_id}", current_score={current_score}'
            )

            # If score is not positive, return early
            if current_score <= 0:
                return {
                    "payload": {
                        "message": f"Current impact score is {current_score}, no action needed",
                        "current_score": current_score,
                    },
                    "status": 200,
                }

            # Generate negative score event to suppress the alert
            # Use a score_source that indicates false positive
            negative_score = -abs(current_score)

            # Get object name if not provided
            if not object_value:
                # Try to get object name from KVstore (_key is object_id)
                try:
                    collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
                    collection = service.kvstore[collection_name]
                    query_string = {"_key": object_id}
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
            score_id = generate_score_id(tenant_id, object_id, component, "false_positive", negative_score, score_id_ctime)

            # Create scoring record
            scoring_record = {
                "tenant_id": tenant_id,
                "object_id": object_id,
                "object": object_value,
                "object_category": component,
                "score_source": "false_positive",
                "metrics_event": {
                    "score_id": score_id,
                    "score": negative_score,
                    "original_score": current_score,
                    "reason": f"Entity marked as false positive by {request_info.user}",
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
                            change_type="set entity as false positive",
                            object_name=str(object_value),
                            object_category=f"splk-{component}",
                            object_attrs=json.dumps({"object_id": object_id}),
                            result=json.dumps(
                                {
                                    "original_score": current_score,
                                    "negative_score": negative_score,
                                }
                            ),
                            comment="Entity marked as false positive",
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
                                source=f"/services/trackme/v2/component/write/set_false_positive",
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
                            component, "false_positive", negative_score,
                            score_id=score_id, ctime=score_id_ctime,
                        )
                        logger.info(
                            f'Score cache written, score_id="{score_id}", tenant_id="{tenant_id}", '
                            f'component="{component}", object_id="{object_id}", score={negative_score}'
                        )
                    except Exception as e:
                        logger.warning(
                            f'Failed to write score cache, tenant_id="{tenant_id}", '
                            f'object_id="{object_id}", exception="{str(e)}"'
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
                              tenant_id, component, object_id, splunkd_timeout),
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
                scoring_record_str = json.dumps(scoring_record, indent=2) if scoring_record is not None else "None"
                error_msg = f'Failed to generate scoring metrics, exception="{str(e)}", scoring_record="{scoring_record_str}"'
                logger.error(error_msg)
                return {"payload": {"error": error_msg}, "status": 500}

        except Exception as e:
            error_msg = f'Failed to load current score from component data, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}

    def post_manual_score_influence(self, request_info, **kwargs):
        """
        | trackme url=/services/trackme/v2/component/write/manual_score_influence mode=post body="{ 'tenant_id': 'mytenant', 'component': 'dsm', 'object_id': 'abc123', 'score_type': 'add', 'score_value': 10 }"
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
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "flx",
                        "fqm",
                        "wlk",
                    ):
                        return {"payload": "component is invalid, must be one of: dsm, dhm, mhm, flx, fqm, wlk", "status": 500}
                except Exception as e:
                    return {"payload": "component is required", "status": 500}
                try:
                    object_id = resp_dict["object_id"]
                except Exception as e:
                    return {"payload": "object_id is required", "status": 500}
                try:
                    score_type = resp_dict["score_type"]
                    if score_type not in ("add", "subtract"):
                        return {"payload": "score_type must be 'add' or 'subtract'", "status": 500}
                except Exception as e:
                    return {"payload": "score_type is required (must be 'add' or 'subtract')", "status": 500}
                try:
                    score_value = int(resp_dict["score_value"])
                    if score_value <= 0:
                        return {"payload": "score_value must be a positive integer", "status": 500}
                except (ValueError, TypeError, KeyError) as e:
                    return {"payload": "score_value is required and must be a positive integer", "status": 500}
                # Optional: object name for better logging
                object_value = resp_dict.get("object", None)
                # Optional: comment for score event context
                comment = resp_dict.get("comment", None)

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "resource_desc": "Manually influence entity score by adding or subtracting a value",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/component/write/manual_score_influence" body="{\'tenant_id\':\'mytenant\',\'component\':\'dsm\',\'object_id\':\'abc123\',\'score_type\':\'add\',\'score_value\':10}"',
                "describe": "This endpoint allows manually influencing the impact score of an entity by adding or subtracting a specific value, it requires a POST call with the following options:",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component category (dsm, dhm, mhm, flx, fqm, wlk)",
                        "object_id": "(required) entity identifier",
                        "score_type": "(required) Operation type: 'add' to increase score, 'subtract' to decrease score",
                        "score_value": "(required) Positive integer value to add or subtract",
                        "object": "(optional) entity name for logging purposes",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get TrackMe conf and configurable splunkd timeout
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')
        splunkd_timeout = get_splunkd_timeout(reqinfo=trackme_conf)

        # Get service
        # Wrapped in try-except to handle connection errors gracefully and return
        # user-friendly JSON error responses instead of unhandled exceptions
        try:
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.system_authtoken,
                timeout=splunkd_timeout,
            )
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            error_msg = f'Failed to connect to local splunkd, connection error="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}
        except Exception as e:
            error_msg = f'Failed to connect to local splunkd, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

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

        # Validate entity existence by querying KVstore directly (_key is object_id)
        try:
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            collection = service.kvstore[collection_name]
            query_string = {"_key": object_id}
            results = collection.data.query(query=json.dumps(query_string))

            # Validate entity exists
            if not results or len(results) == 0:
                error_msg = f'Entity with object_id="{object_id}" does not exist for tenant_id="{tenant_id}" and component="{component}"'
                logger.error(error_msg)
                return {"payload": {"error": error_msg}, "status": 404}

            # Entity exists, get object name if not provided
            if not object_value:
                object_value = results[0].get("object", object_id)

        except Exception as e:
            error_msg = f'Failed to validate entity existence for object_id="{object_id}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"error": error_msg}, "status": 500}

        # Calculate the score to apply (positive for add, negative for subtract)
        applied_score = score_value if score_type == "add" else -score_value

        # Generate score_id for traceability between cache and metrics event
        score_id_ctime = time.time()
        score_id = generate_score_id(tenant_id, object_id, component, "manual_score", applied_score, score_id_ctime)

        # Create scoring record
        metrics_event = {
            "score_id": score_id,
            "score": applied_score,
            "score_type": score_type,
            "score_value": score_value,
            "reason": f"Manual score influence ({score_type} {score_value}) by {request_info.user}",
        }
        # Add comment to metrics_event if provided
        if comment:
            metrics_event["comment"] = comment

        scoring_record = {
            "tenant_id": tenant_id,
            "object_id": object_id,
            "object": object_value,
            "object_category": component,
            "score_source": "manual_score",
            "metrics_event": metrics_event,
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
                        change_type="manual score influence",
                        object_name=str(object_value),
                        object_category=f"splk-{component}",
                        object_attrs=json.dumps({"object_id": object_id}),
                        result=json.dumps(
                            {
                                "score_type": score_type,
                                "score_value": score_value,
                                "applied_score": applied_score,
                            }
                        ),
                        comment=f"Manual score influence: {score_type} {score_value}" + (f" - {comment}" if comment else ""),
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
                            source=f"/services/trackme/v2/component/write/manual_score_influence",
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
                        component, "manual_score", applied_score,
                        score_id=score_id, ctime=score_id_ctime,
                    )
                    logger.info(
                        f'Score cache written, score_id="{score_id}", tenant_id="{tenant_id}", '
                        f'component="{component}", object_id="{object_id}", score={applied_score}'
                    )
                except Exception as e:
                    logger.warning(
                        f'Failed to write score cache, tenant_id="{tenant_id}", '
                        f'object_id="{object_id}", exception="{str(e)}"'
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
                          tenant_id, component, object_id, splunkd_timeout),
                    kwargs={
                        "shadow_enabled": shadow_enabled,
                        "splunkd_port": request_info.server_rest_port,
                    },
                    daemon=True,
                )
                t.start()

                # Refresh tenant component summary cache (drives the
                # Single Value cards on Tenant Home). Score-only
                # mutations don't touch entity KV records, so the cached
                # <component>_extended_stats blob stays stale until the
                # next scheduled tracker fires unless we refresh it here.
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
                        "message": f"Manual score influence applied successfully ({score_type} {score_value})",
                        "applied_score": applied_score,
                        "score_type": score_type,
                        "score_value": score_value,
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
