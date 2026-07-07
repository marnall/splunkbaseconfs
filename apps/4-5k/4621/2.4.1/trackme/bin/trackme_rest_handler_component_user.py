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
import logging
import os
import sys
import time
import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.component_user", "trackme_rest_api_component_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_getloglevel_from_service,
    trackme_idx_for_tenant,
    trackme_parse_describe_flag,
    trackme_reqinfo_from_service,
    trackme_vtenant_account_from_service,
)

# import shadow copy libs
from trackme_libs_shadow import (
    should_use_shadow,
)

# import trackme libs utils
from trackme_libs_utils import replace_encoded_backslashes, get_uuid

# import Splunk libs
import splunklib.client as client

# import TrackMe get data libs
from trackme_libs_get_data import (
    search_kv_collection,
    get_target_from_kv_collection,
    get_sampling_kv_collection,
    get_collection_documents_count,
    get_wlk_apps_enablement_kv_collection,
    get_feeds_datagen_kv_collection,
    search_kv_collection_restmode,
    search_kv_collection_searchmode,
    search_kv_collection_sdkmode,    
)

# import TrackMe decision maker libs
from trackme_libs_decisionmaker import (
    pre_filter_records,
    filter_records,
    convert_epoch_to_datetime,
    get_monitoring_time_status,
    get_outliers_status,
    get_data_sampling_status,
    get_future_status,
    get_future_metrics_status,
    get_is_under_dcount_host,
    get_logical_groups_collection_records,
    get_dsm_latency_status,
    get_dsm_delay_status,
    set_dsm_status,
    set_dhm_status,
    set_mhm_status,
    set_flx_status,
    set_fqm_status,
    set_wlk_status,
    ack_check,
    define_state_icon_code,
    outliers_readiness,
    logical_group_lookup,
    set_feeds_lag_summary,
    set_feeds_thresholds_duration,
    dsm_sampling_lookup,
    outliers_data_lookup,
    sampling_anomaly_status,
    get_coll_docs_ref,
    docs_ref_lookup,
    wlk_disabled_apps_lookup,
    wlk_versioning_lookup,
    wlk_orphan_lookup,
    apply_blocklist,
    dsm_check_default_thresholds,
    dhm_check_default_thresholds,
    dynamic_priority_lookup,
    dynamic_tags_lookup,
    dynamic_labels_lookup,
    dynamic_sla_class_lookup,
    get_sla_timer,
    flx_thresholds_lookup,
    wlk_thresholds_lookup,
    fqm_thresholds_lookup,
    flx_check_dynamic_thresholds,
    fqm_check_dynamic_thresholds,
    flx_drilldown_searches_lookup,
    flx_default_metrics_lookup,
    calculate_score,
    resolve_variable_delay_threshold,
    resolve_lagging_class_threshold,
)

# import threshold intent-lock predicates (real-time display must honour pins)
from trackme_libs_threshold_intent import (
    is_delay_threshold_locked,
    is_lag_threshold_locked,
)

# import trackme libs disruption queue
from trackme_libs_disruption_queue import (
    disruption_queue_lookup,
    disruption_queue_update,
    disruption_queue_get_duration,
)
from trackme_libs_entity_maintenance import (
    entity_maintenance_lookup,
    apply_entity_maintenance_override,
    clear_entity_maintenance_fields,
)

# import chart generation functions from stateful alert helper
from modalert_trackme_stateful_alert_helper import (
    get_chart_search,
    get_mlmodels_from_kvstore,
    flx_get_metrics_catalog_for_object_id,
    fqm_get_metrics_catalog_for_object_id,
    wlk_get_metrics_catalog_for_object_id,
    remove_leading_spaces,
)


class TrackMeHandlerComponentRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerComponentRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_component(self, request_info, **kwargs):
        response = {
            "resource_group_name": "component",
            "resource_group_desc": "Endpoints specific to TrackMe's components data offload (read only operations)",
        }

        return {"payload": response, "status": 200}

    # Get the component data with pagination and progressive load capabilities
    def get_load_component_data(self, request_info, **kwargs):
        describe = False

        try:
            params_dict = request_info.raw_args["query_parameters"]
        except Exception as e:
            params_dict = None

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        # Generate a unique request ID for this specific REST endpoint call
        request_id = get_uuid()
        
        # Extract request metadata for debugging duplicate calls
        try:
            request_path = getattr(request_info, 'path', 'unknown')
            request_method = getattr(request_info, 'method', 'unknown')
            connection_src_ip = getattr(request_info, 'connection_src_ip', 'unknown')
            user = getattr(request_info, 'user', 'unknown')
            caller_param = params_dict.get("caller", "none") if params_dict else "none"
        except Exception as e:
            request_path = 'unknown'
            request_method = 'unknown'
            connection_src_ip = 'unknown'
            user = 'unknown'
            caller_param = 'none'
        
        logger.info(
            f'function get_load_component_data called, request_id="{request_id}", method="{request_method}", path="{request_path}", user="{user}", src_ip="{connection_src_ip}", caller="{caller_param}", params_dict="{params_dict}"'
        )
        
        logger.debug(
            f'get_load_component_data request_id="{request_id}", instance_id="{getattr(self, "instance_id", "not_set")}", params_dict="{params_dict}"'
        )

        # Start performance counter
        start = time.time()        

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        if not params_dict and not resp_dict:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves a TrackMe's component table data, it requires a GET call using params and the following options:",
                "resource_desc": "Get TrackMe's component data",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/component/load_component_data\" mode=\"get\" params=\"{'tenant_id': 'mytenant', 'component': 'flx', 'page': 1, 'size': 100}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) component identifier, valid options are: flx, dsm, dhm, mhm, wlk, fqm",
                        "filter_object": "(optional) target a specific TrackMe object record, do not specify this for no filtering",
                        "filter_key": "(optional) target a specific TrackMe key record, do not specify this for no filtering",
                        "filter_objects": "(optional) comma-separated list of TrackMe object records to filter on, do not specify this for no filtering",
                        "filter_keys": "(optional) comma-separated list of TrackMe key records to filter on, do not specify this for no filtering",
                        "pagination_mode": "(optional) set to true to enable pagination, valid options are: local, remote. Defaults to remote.",
                        "page": "(optional) page number, specific the page to be retrieved, defaults to page 1",
                        "size": "(optional) number of records to retrieve, set to 0 with page: 1 to retrieve all records in a single operation",
                        "mode_view": "(optional) for splk-mhm/splk-wlk, the view mode, defaults to minimal, valid options are: minimal, compact, full. For splk-dhm, views are always generated on-demand (minimal for sourcetype_summary, full for UI expansion).",
                        "load_charts_resources": "(optional) set to true to load the charts resources, defaults to false",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if params_dict is not None:

            # tenant_id
            try:
                tenant_id = params_dict["tenant_id"]
            except Exception as e:
                return {
                    "payload": {
                        "action": "failure",
                        "response": "the tenant_id is required",
                    },
                    "status": 400,
                }

            # component
            try:
                component = params_dict["component"]
            except Exception as e:
                return {
                    "payload": {
                        "action": "failure",
                        "response": "the component is required",
                    },
                    "status": 400,
                }

            # pagination_mode, optional and defaults to False if not specified
            try:
                pagination_mode = params_dict["pagination_mode"]
                if pagination_mode not in ("local", "remote"):
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the pagination_mode is invalid",
                        },
                        "status": 400,
                    }
            except Exception as e:
                pagination_mode = "remote"

            # filter_object, optional and defaults to None if not specified
            try:
                filter_object = params_dict["filter_object"]
            except Exception as e:
                filter_object = None

            # filter_key, optional and defaults to None if not specified
            try:
                filter_key = params_dict["filter_key"]
            except Exception as e:
                filter_key = None

            # filter_objects, optional and defaults to None if not specified
            try:
                filter_objects = params_dict["filter_objects"]
                if filter_objects:
                    filter_objects = [obj.strip() for obj in filter_objects.split(",")]
            except Exception as e:
                filter_objects = None

            # filter_keys, optional and defaults to None if not specified
            try:
                filter_keys = params_dict["filter_keys"]
                if filter_keys:
                    filter_keys = [key.strip() for key in filter_keys.split(",")]
            except Exception as e:
                filter_keys = None

            # page, if not submitted, default to 1
            try:
                page = int(params_dict["page"])
            except Exception as e:
                page = 1

            # size, if not submitted, default to 0
            try:
                size = int(params_dict["size"])
            except Exception as e:
                size = 0

            # caller, optional - identifies the caller (e.g., "trackmestateful", "trackme_rest_handler_component_power")
            # Used to build accurate provenance for logging
            try:
                caller = params_dict.get("caller", None)
            except Exception as e:
                caller = None

            # mode_view
            try:
                mode_view = params_dict["mode_view"]
            except Exception as e:
                mode_view = "minimal"
            logger.debug(f'mode_view="{mode_view}"')

            # load_charts_resources (accepts boolean, true or false as strings, 0 or 1 as integers or strings)
            try:
                load_charts_resources = params_dict["load_charts_resources"]
                if isinstance(load_charts_resources, str):
                    if load_charts_resources in ("true", "True", "1"):
                        load_charts_resources = True
                    elif load_charts_resources in ("false", "False", "0"):
                        load_charts_resources = False
                elif isinstance(load_charts_resources, int):
                    if load_charts_resources == 1:
                        load_charts_resources = True
                    elif load_charts_resources == 0:
                        load_charts_resources = False
            except Exception as e:
                load_charts_resources = False

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service (user-level, used for KVstore queries and searches)
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # Get system-level service (elevated privileges for conf reads)
        # This single connection replaces what were previously 3 separate connections/REST calls:
        # - trackme_getloglevel (created its own client.connect)
        # - trackme_reqinfo (HTTP roundtrip to /services/trackme/v2/configuration/request_info)
        # - trackme_vtenant_account (HTTP roundtrip to /services/trackme/v2/vtenants/vtenants_accounts)
        service_system = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel - reuse system service connection instead of creating a new one
        loglevel = trackme_getloglevel_from_service(service_system)
        logger.setLevel(loglevel)

        # set instance_id
        self.instance_id = get_uuid()

        # Get trackmeconf - direct conf read instead of REST loopback
        trackme_conf = trackme_reqinfo_from_service(service_system)["trackme_conf"]

        # Get virtual tenant account - direct conf read instead of REST loopback
        vtenant_conf = trackme_vtenant_account_from_service(service_system, tenant_id)

        #
        # System level settings
        #

        system_future_tolerance = float(
            trackme_conf["splk_general"]["splk_general_feeds_future_tolerance"]
        )

        #
        # System level default minimal disruption period
        #

        default_disruption_min_time_sec = int(
            vtenant_conf["default_disruption_min_time_sec"]
        )

        #
        # Tenant level default monitoring time policy
        #

        try:
            default_monitoring_time_policy = vtenant_conf["monitoring_time_policy"]
        except Exception as e:
            default_monitoring_time_policy = "all_time"

        #
        # SLA timer
        #

        sla_classes = {}
        sla_default_class = None

        sla_classes = trackme_conf["sla"]["sla_classes"]
        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
            sla_default_class = trackme_conf["sla"]["sla_default_class"]
            if not len(sla_default_class) > 0 or sla_default_class not in sla_classes:
                sla_default_class = "silver"
                logger.error(
                    f'instance_id={self.instance_id}, Invalid sla_default_class="{sla_default_class}", this SLA class is not part of the SLA classes, applying fallback configuration'
                )

        except:
            logger.error(
                f'instance_id={self.instance_id}, Error loading sla_classes JSON, please check the configuration, the JSON is not valid JSON, applying fallback configuration, exception="{str(e)}"'
            )
            sla_classes = json.loads(
                '{"platinum": {"sla_threshold": 14400, "rank": 3}, "gold": {"sla_threshold": 86400, "rank": 2}, "silver": {"sla_threshold": 172800, "rank": 1}}'
            )
            sla_default_class = "silver"

        # retrieve the tenant metric index
        tenant_indexes = trackme_idx_for_tenant(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
        )
        tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

        # retrieve the score for the tenant and component
        scores_dict = calculate_score(service, tenant_id, component, tenant_trackme_metric_idx=tenant_trackme_metric_idx)
        logger.debug(
            f'instance_id={self.instance_id}, tenant_id="{tenant_id}", component="{component}", scores_dict="{json.dumps(scores_dict, indent=2)}"'
        )

        # Global docs references - applies to all components
        # Priority: tenant-level override > system-wide default
        # Initialize defaults
        docs_is_global = "False"
        docs_note_global = "N/A"
        docs_link_global = "N/A"

        # First, check for tenant-level override
        tenant_docs_note_global = vtenant_conf.get("docs_note_global", "")
        tenant_docs_link_global = vtenant_conf.get("docs_link_global", "")

        # If tenant-level values are set, use them
        if tenant_docs_note_global and tenant_docs_link_global:
            docs_note_global = tenant_docs_note_global
            docs_link_global = tenant_docs_link_global
            docs_is_global = "True"
        else:
            # Fall back to system-wide configuration
            # Note: field names contain "dsm" for historical reasons but are
            # system-wide settings in the shared [splk_general] stanza,
            # applicable to all components.
            try:
                docs_note_global = trackme_conf["splk_general"][
                    "splk_general_dsm_docs_note_global"
                ]
                if not docs_note_global:
                    docs_note_global = "N/A"
            except Exception:
                docs_note_global = "N/A"

            try:
                docs_link_global = trackme_conf["splk_general"][
                    "splk_general_dsm_docs_link_global"
                ]
                if not docs_link_global:
                    docs_link_global = "N/A"
            except Exception:
                docs_link_global = "N/A"

            # both should be defined to be enabled
            if docs_note_global == "N/A" or docs_link_global == "N/A":
                docs_note_global = "N/A"
                docs_link_global = "N/A"
            else:
                docs_is_global = "True"

        # dsm specific
        if component == "dsm":

            # Data sampling
            sampling_collection_name = (
                f"kv_trackme_dsm_data_sampling_tenant_{tenant_id}"
            )
            sampling_collection = service.kvstore[sampling_collection_name]
            sampling_records, sampling_collection_keys, sampling_collection_dict = (
                get_sampling_kv_collection(
                    sampling_collection, sampling_collection_name
                )
            )

            # Docs reference
            docs_collection_name = f"kv_trackme_dsm_knowledge_tenant_{tenant_id}"
            docs_collection = service.kvstore[docs_collection_name]
            (
                docs_collection_records,
                docs_collection_records_dict,
                docs_collection_members_list,
                docs_collection_members_dict,
            ) = get_coll_docs_ref(docs_collection, docs_collection_name)

            logger.debug(
                f'instance_id={self.instance_id}, docs_collection_dict="{json.dumps(docs_collection_members_dict, indent=2)}"'
            )
        else:
            # For non-DSM components, initialize empty docs collection variables
            docs_collection_records = []
            docs_collection_records_dict = {}
            docs_collection_members_list = []
            docs_collection_members_dict = {}

        # dhm specific
        if component == "dhm":
            macro_name = f"trackme_dhm_default_splk_dhm_alert_policy_tenant_{tenant_id}"
            macro_current = service.confs["macros"][macro_name]
            default_splk_dhm_alerting_policy = macro_current.content.get("definition")
            # remove double quotes from default_splk_dhm_alerting_policy
            default_splk_dhm_alerting_policy = default_splk_dhm_alerting_policy.replace(
                '"', ""
            )

            logger.debug(
                f'instance_id={self.instance_id}, default_splk_dhm_alerting_policy="{default_splk_dhm_alerting_policy}"'
            )

        #
        # splk-flx specific collections
        #

        # Initialize thresholds_collection_dict as safe default for all components;
        # component-specific blocks (flx, fqm, wlk) will overwrite with actual data.
        thresholds_collection_dict = {}

        if component == "flx":

            # Thresholds
            thresholds_collection_name = f"kv_trackme_flx_thresholds_tenant_{tenant_id}"
            thresholds_collection = service.kvstore[thresholds_collection_name]
            (
                thresholds_records,
                thresholds_collection_keys,
                thresholds_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, thresholds_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logger.debug(
                f'instance_id={self.instance_id}, thresholds_collection_dict="{json.dumps(thresholds_collection_dict, indent=2)}"'
            )

            # Drilldown searches
            drilldown_searches_collection_name = f"kv_trackme_flx_drilldown_searches_tenant_{tenant_id}"
            try:
                drilldown_searches_collection = service.kvstore[drilldown_searches_collection_name]
                (
                    drilldown_searches_records,
                    drilldown_searches_collection_keys,
                    drilldown_searches_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logger, service, drilldown_searches_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception as e:
                logger.debug(f"instance_id={self.instance_id}, Drilldown searches collection not found or accessible: {str(e)}")
                drilldown_searches_records = []
                drilldown_searches_collection_keys = []
                drilldown_searches_collection_dict = {}

            logger.debug(
                f'instance_id={self.instance_id}, drilldown_searches_collection_dict="{json.dumps(drilldown_searches_collection_dict, indent=2)}"'
            )

            # Default metrics
            default_metrics_collection_name = f"kv_trackme_flx_default_metric_tenant_{tenant_id}"
            try:
                default_metrics_collection = service.kvstore[default_metrics_collection_name]
                (
                    default_metrics_records,
                    default_metrics_collection_keys,
                    default_metrics_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logger, service, default_metrics_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception as e:
                logger.debug(f"instance_id={self.instance_id}, Default metrics collection not found or accessible: {str(e)}")
                default_metrics_records = []
                default_metrics_collection_keys = []
                default_metrics_collection_dict = {}

            logger.debug(
                f'instance_id={self.instance_id}, default_metrics_collection_dict="{json.dumps(default_metrics_collection_dict, indent=2)}"'
            )

        #
        # splk-fqm specific collections
        #

        if component == "fqm":

            # Thresholds
            thresholds_collection_name = f"kv_trackme_fqm_thresholds_tenant_{tenant_id}"
            thresholds_collection = service.kvstore[thresholds_collection_name]
            (
                thresholds_records,
                thresholds_collection_keys,
                thresholds_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, thresholds_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logger.debug(
                f'instance_id={self.instance_id}, thresholds_collection_dict="{json.dumps(thresholds_collection_dict, indent=2)}"'
            )

        #
        # Virtual tenant account settings
        #

        # outliers tenant level settings (deprecated - kept for backward compatibility)
        # These are no longer used with score-based approach, but kept for backward compatibility
        tenant_outliers_set_state = int(vtenant_conf.get("outliers_set_state", 1))
        tenant_data_sampling_set_state = int(vtenant_conf.get("data_sampling_set_state", 1))

        #
        # Logical groups collection records
        #

        logical_group_coll = service.kvstore[
            f"kv_trackme_common_logical_group_tenant_{tenant_id}"
        ]

        (
            logical_coll_records,
            logical_coll_dict,
            logical_coll_members_list,
            logical_coll_members_dict,
            logical_coll_count,
        ) = get_logical_groups_collection_records(logical_group_coll)

        # log debug
        logger.debug(
            f'instance_id={self.instance_id}, function get_logical_groups_collection_records, logical_coll_dict="{json.dumps(logical_coll_dict, indent=2)}", logical_coll_count="{logical_coll_count}"'
        )

        # entities KV collection
        data_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        data_collection = service.kvstore[data_collection_name]

        # detect if we have multiple filters, if we do, set size to 0 as we need to retrieve all records
        multiple_filters = False
        query_parameters = request_info.raw_args["query_parameters"]
        if params_dict:

            # Loop through all query parameters
            for key, value in query_parameters.items():
                if "filter[" in key:
                    if key == "filter[1][field]":
                        multiple_filters = True

        if multiple_filters:
            size = 0

        if (
            not filter_object
            and not filter_key
            and not filter_objects
            and not filter_keys
        ):

            # Get kvcollection mode from configuration with error handling (once, shared for both branches)
            try:
                kvcollection_mode = trackme_conf["trackme_general"].get(
                    "central_kvcollection_mode", "search_mode"
                )
            except Exception as e:
                logger.debug(
                    f"instance_id={self.instance_id}, failed to retrieve kvcollection_mode, defaulting to search_mode, exception={str(e)}"
                )
                kvcollection_mode = "search_mode"
            
            # Build provenance string for logging (once, shared for both branches)
            # Include caller information if provided (e.g., when called from custom commands)
            if caller:
                provenance = f"trackme_rest_handler_component_user(called_by={caller}):{component}:tenant_{tenant_id}"
            else:
                provenance = f"trackme_rest_handler_component_user:{component}:tenant_{tenant_id}"

            # get records
            # NOTE: The two call sites below are intentionally in mutually exclusive branches
            # (if size == 0 vs else), ensuring search_kv_collection is called exactly once per request.
            # The control flow itself guarantees single execution - no safeguard flag needed.
            if size == 0:

                func_start = time.time()
                logger.debug(
                    f'get_load_component_data CALL_SITE_1 (size==0), request_id="{request_id}", instance_id="{self.instance_id}", collection="{data_collection_name}", page=1, page_count=0, kvcollection_mode="{kvcollection_mode}"'
                )
                data_records, data_collection_keys, data_collection_dict, last_page = (
                    search_kv_collection(
                        service,
                        data_collection_name,
                        page=1,
                        page_count=0,
                        kvcollection_mode=kvcollection_mode,
                        provenance=provenance,
                        logger=logger,
                        instance_id=self.instance_id,
                    )
                )
                last_page = 1

                logger.info(
                    f"instance_id={self.instance_id}, function search_kv_collection took {round(time.time() - func_start, 2)} seconds, records_count={len(data_records)}"
                )

            else:

                func_start = time.time()
                logger.debug(
                    f'get_load_component_data CALL_SITE_2 (size={size}), request_id="{request_id}", instance_id="{self.instance_id}", collection="{data_collection_name}", page={page}, page_count={size}, kvcollection_mode="{kvcollection_mode}"'
                )
                data_records, data_collection_keys, data_collection_dict, last_page = (
                    search_kv_collection(
                        service,
                        data_collection_name,
                        page=page,
                        page_count=size,
                        kvcollection_mode=kvcollection_mode,
                        provenance=provenance,
                        logger=logger,
                        instance_id=self.instance_id,
                    )
                )

                logger.info(
                    f"instance_id={self.instance_id}, function search_kv_collection took {round(time.time() - func_start, 2)} seconds, records_count={len(data_records)}"
                )

        elif filter_object:  # filter on a given object
            data_records, data_collection_keys, data_collection_dict = (
                get_target_from_kv_collection(
                    "object", filter_object, data_collection, data_collection_name
                )
            )
            last_page = 1
            total_record_count = len(data_records)

        elif filter_key:  # filter on a given key
            data_records, data_collection_keys, data_collection_dict = (
                get_target_from_kv_collection(
                    "_key", filter_key, data_collection, data_collection_name
                )
            )
            last_page = 1
            total_record_count = len(data_records)

        elif filter_objects:  # filter on multiple objects
            data_records, data_collection_keys, data_collection_dict = (
                get_target_from_kv_collection(
                    "object", filter_objects, data_collection, data_collection_name
                )
            )
            last_page = 1
            total_record_count = len(data_records)

        elif filter_keys:  # filter on multiple keys
            data_records, data_collection_keys, data_collection_dict = (
                get_target_from_kv_collection(
                    "_key", filter_keys, data_collection, data_collection_name
                )
            )
            last_page = 1
            total_record_count = len(data_records)

        # for later usage
        total_record_count = len(data_records)

        # get Ack collection
        ack_collection_name = f"kv_trackme_common_alerts_ack_tenant_{tenant_id}"
        ack_collection = service.kvstore[ack_collection_name]
        (
            ack_records,
            ack_collection_keys,
            ack_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logger, service, ack_collection_name, page=1, page_count=0, orderby="object"
        )

        # get priority collection
        priority_collection_name = f"kv_trackme_{component}_priority_tenant_{tenant_id}"
        priority_collection = service.kvstore[priority_collection_name]
        (
            priority_records,
            priority_collection_keys,
            priority_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logger, service, priority_collection_name, page=1, page_count=0, orderby="keyid"
        )

        # get tags collection
        tags_collection_name = f"kv_trackme_{component}_tags_tenant_{tenant_id}"
        tags_collection = service.kvstore[tags_collection_name]
        (
            tags_records,
            tags_collection_keys,
            tags_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logger, service, tags_collection_name, page=1, page_count=0, orderby="keyid"
        )

        # get sla collection
        sla_collection_name = f"kv_trackme_{component}_sla_tenant_{tenant_id}"
        sla_collection = service.kvstore[sla_collection_name]
        (
            sla_records,
            sla_collection_keys,
            sla_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logger, service, sla_collection_name, page=1, page_count=0, orderby="keyid"
        )

        # get disruption queue collection
        disruption_queue_collection_name = (
            f"kv_trackme_common_disruption_queue_tenant_{tenant_id}"
        )
        disruption_queue_collection = service.kvstore[disruption_queue_collection_name]
        (
            disruption_queue_records,
            disruption_queue_collection_keys,
            disruption_queue_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logger, service, disruption_queue_collection_name, page=1, page_count=0, orderby="keyid"
        )

        logger.debug(
            f'instance_id={self.instance_id}, disruption_queue_collection_dict="{json.dumps(disruption_queue_collection_dict, indent=2)}"'
        )

        # get per-entity maintenance collection. A missing collection (older
        # tenant not yet backfilled by the general health manager) is expected
        # and degrades to empty; a genuine read failure (auth/session) must NOT
        # silently disable maintenance, so only a MISSING collection is treated
        # as empty and real read errors propagate.
        entity_maintenance_collection_name = (
            f"kv_trackme_common_entity_maintenance_tenant_{tenant_id}"
        )
        if entity_maintenance_collection_name in service.kvstore:
            (
                _entity_maintenance_records,
                entity_maintenance_collection_keys,
                entity_maintenance_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, entity_maintenance_collection_name, page=1, page_count=0, orderby="keyid"
            )
        else:
            logger.info(
                f'instance_id={self.instance_id}, maintenance collection="{entity_maintenance_collection_name}" not present yet; skipping maintenance override'
            )
            entity_maintenance_collection_keys = []
            entity_maintenance_collection_dict = {}

        # get labels definitions
        labels_def_collection_name = f"kv_trackme_labels_tenant_{tenant_id}"
        try:
            (
                labels_def_records,
                labels_def_collection_keys,
                labels_def_collection_dict,
                labels_def_last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, labels_def_collection_name, page=1, page_count=0, orderby="keyid"
            )
        except Exception:
            labels_def_records, labels_def_collection_keys, labels_def_collection_dict = [], [], {}

        # get labels assignments
        labels_assign_collection_name = f"kv_trackme_label_assignments_tenant_{tenant_id}"
        try:
            (
                labels_assign_records,
                labels_assign_collection_keys,
                labels_assign_collection_dict,
                labels_assign_last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, labels_assign_collection_name, page=1, page_count=0, orderby="keyid"
            )
        except Exception:
            labels_assign_records, labels_assign_collection_keys, labels_assign_collection_dict = [], [], {}

        # get notes counts per object_id (shared across components — notes are keyed by entity _key)
        notes_count_by_object = {}
        notes_collection_name = f"kv_trackme_notes_tenant_{tenant_id}"
        try:
            (
                notes_records,
                notes_collection_keys,
                notes_collection_dict,
                notes_last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, notes_collection_name, page=1, page_count=0, orderby="keyid"
            )
            for note_rec in notes_records or []:
                note_object_id = note_rec.get("object_id")
                if note_object_id:
                    notes_count_by_object[note_object_id] = notes_count_by_object.get(note_object_id, 0) + 1
        except Exception:
            notes_count_by_object = {}

        # get outliers data (all components except mhm)
        if component not in ["mhm"]:

            # data collection
            outliers_data_collection_name = (
                f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
            )
            outliers_data_collection = service.kvstore[outliers_data_collection_name]
            (
                outliers_data_records,
                outliers_data_collection_keys,
                outliers_data_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, outliers_data_collection_name, page=1, page_count=0, orderby="keyid"
            )

            # rules collection
            outliers_rules_collection_name = (
                f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
            )
            outliers_rules_collection = service.kvstore[outliers_rules_collection_name]
            (
                outliers_rules_records,
                outliers_rules_collection_keys,
                outliers_rules_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, outliers_rules_collection_name, page=1, page_count=0, orderby="keyid"
            )

        #
        # component specific collections
        #

        if component in ["dsm", "dhm", "mhm", "flx", "fqm", "wlk"]:

            # datagen
            datagen_collection_name = (
                f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
            )
            datagen_collection = service.kvstore[datagen_collection_name]
            (
                datagen_records,
                datagen_collection_keys,
                datagen_collection_dict,
                datagen_collection_blocklist_not_regex_dict,
                datagen_collection_blocklist_regex_dict,
            ) = get_feeds_datagen_kv_collection(
                datagen_collection, datagen_collection_name, component
            )

            logger.debug(
                f'instance_id={self.instance_id}, datagen_collection_dict="{json.dumps(datagen_collection_dict, indent=2)}"'
            )

            logger.debug(
                f'instance_id={self.instance_id}, datagen_collection_blocklist_not_regex_dict="{json.dumps(datagen_collection_blocklist_not_regex_dict, indent=2)}"'
            )

            logger.debug(
                f'instance_id={self.instance_id}, datagen_collection_blocklist_regex_dict="{json.dumps(datagen_collection_blocklist_regex_dict, indent=2)}"'
            )


        #
        # splk-wlk specific collections
        #

        if component == "wlk":

            # apps_disabled
            apps_enablement_collection_name = (
                f"kv_trackme_wlk_apps_enablement_tenant_{tenant_id}"
            )
            apps_enablement_collection = service.kvstore[
                apps_enablement_collection_name
            ]
            (
                apps_enablement_records,
                apps_enablement_collection_keys,
                apps_enablement_collection_dict,
            ) = get_wlk_apps_enablement_kv_collection(
                apps_enablement_collection, apps_enablement_collection_name
            )

            logger.debug(
                f'instance_id={self.instance_id}, apps_enablement_collection_dict="{json.dumps(apps_enablement_collection_dict, indent=2)}"'
            )

            # versioning
            versioning_collection_name = f"kv_trackme_wlk_versioning_tenant_{tenant_id}"
            versioning_collection = service.kvstore[versioning_collection_name]
            (
                versioning_records,
                versioning_collection_keys,
                versioning_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, versioning_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logger.debug(
                f'instance_id={self.instance_id}, versioning_collection_dict="{json.dumps(versioning_collection_dict, indent=2)}"'
            )

            # orphan
            orphan_collection_name = f"kv_trackme_wlk_orphan_status_tenant_{tenant_id}"
            orphan_collection = service.kvstore[orphan_collection_name]
            (
                orphan_records,
                orphan_collection_keys,
                orphan_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logger, service, orphan_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logger.debug(
                f'instance_id={self.instance_id}, orphan_collection_dict="{json.dumps(orphan_collection_dict, indent=2)}"'
            )

            # Thresholds
            thresholds_collection_name = f"kv_trackme_wlk_thresholds_tenant_{tenant_id}"
            try:
                thresholds_collection = service.kvstore[thresholds_collection_name]
                (
                    thresholds_records,
                    thresholds_collection_keys,
                    thresholds_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logger, service, thresholds_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception:
                thresholds_collection_dict = {}

            logger.debug(
                f'instance_id={self.instance_id}, thresholds_collection_dict="{json.dumps(thresholds_collection_dict, indent=2)}"'
            )

        #
        # variable delay collection (DSM and DHM only)
        #

        variable_delay_collection_dict = {}
        if component in ["dsm", "dhm"]:
            variable_delay_collection_name = (
                f"kv_trackme_{component}_variable_delay_tenant_{tenant_id}"
            )
            try:
                (
                    variable_delay_records,
                    variable_delay_collection_keys,
                    variable_delay_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logger, service, variable_delay_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception as e:
                logger.warning(
                    f'instance_id={self.instance_id}, failed to load variable delay collection="{variable_delay_collection_name}", exception="{str(e)}", variable delay will not be applied'
                )
                variable_delay_collection_dict = {}

            logger.debug(
                f'instance_id={self.instance_id}, variable_delay_collection_dict has {len(variable_delay_collection_dict)} records'
            )

        #
        # lagging classes collection (DSM and DHM)
        #

        lagging_classes_records = []
        if component in ["dsm", "dhm"]:
            lagging_classes_collection_name = (
                f"kv_trackme_{component}_lagging_classes_tenant_{tenant_id}"
            )
            try:
                (
                    lagging_classes_records,
                    lagging_classes_collection_keys,
                    lagging_classes_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logger, service, lagging_classes_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception as e:
                logger.warning(
                    f'instance_id={self.instance_id}, failed to load lagging classes collection="{lagging_classes_collection_name}", exception="{str(e)}", lagging classes will not be applied'
                )
                lagging_classes_records = []

            logger.debug(
                f'instance_id={self.instance_id}, lagging_classes_records has {len(lagging_classes_records)} records'
            )

        # A list to store processed records
        processed_records = []

        # Process records through TrackMe's decision maker workflow
        records_count = 0

        # filter records - server side filters not working for now
        query_parameters_json = request_info.raw_args["query_parameters"]
        logger.info(
            f'instance_id={self.instance_id}, tenant_id="{tenant_id}", component="{component}", received query_parameters_json="{json.dumps(query_parameters_json, indent=2)}"'
        )

        # pre-filtered records
        prefiltered_records = pre_filter_records(data_records, query_parameters_json)

        # Pre-compute debug flag once to avoid expensive f-string evaluation
        # at 40k+ records when log level is INFO or higher
        _debug = logger.isEnabledFor(logging.DEBUG)

        # loop
        for record in prefiltered_records:

            records_count += 1
            try:

                if _debug:
                    logger.debug(f"instance_id={self.instance_id}, processing record")

                # Safeguard: ensure tenant_id is populated on every record.
                # The KVStore collection is tenant-specific so the record belongs
                # to this tenant, but the field may be missing due to an edge case
                # during tracker execution.  (refs #625)
                if not record.get("tenant_id"):
                    record["tenant_id"] = tenant_id

                # append_record boolean, True by default unless specific use cases
                append_record = True

                # get object_value and key
                object_value = record.get("object", None)
                if _debug:
                    logger.debug(
                        f'instance_id={self.instance_id}, object="{object_value}", record="{json.dumps(record, indent=2)}"'
                    )

                # save the current value of object_state in the record as kvcurrent_object_state, we manipulate real state calculations
                # and we need the original state in some conditions (sla)
                record["kvcurrent_object_state"] = record.get("object_state", "N/A")

                # get the KVsotre unique key and add to the record as keyid
                key_value = record.get("_key", None)
                record["keyid"] = key_value

                # get the score for the object and add to the record
                try:
                    score = int(scores_dict.get(key_value, {}).get("score", 0))
                except:
                    score = 0
                try:
                    score_outliers = int(scores_dict.get(key_value, {}).get("score_outliers", 0))
                except:
                    score_outliers = 0
                record["score_outliers"] = score_outliers
                try:
                    score_source = scores_dict.get(key_value, {}).get("score_source", [])
                except:
                    score_source = []
                record["score"] = score
                record["score_source"] = score_source

                # ensure alias has not encoded backslashes
                record["alias"] = replace_encoded_backslashes(record.get("alias", ""))

                #
                # logical group lookup
                #

                if component not in ["wlk"]:
                    logical_group_lookup(
                        object_value,
                        logical_coll_members_list,
                        logical_coll_members_dict,
                        record,
                    )

                #
                # some safety checks for feeds (dsm/dhm)
                #

                if component in ["dsm"]:
                    dsm_check_default_thresholds(record, trackme_conf)
                elif component in ["dhm"]:
                    dhm_check_default_thresholds(record, trackme_conf)

                #
                # Check Ack
                #

                # Call ack_check function
                ack_check(
                    object_value,
                    ack_collection_keys,
                    ack_collection_dict,
                    record,
                )

                #
                # Dynamic priority
                #

                dynamic_priority_lookup(
                    key_value,
                    priority_collection_keys,
                    priority_collection_dict,
                    record,
                )

                #
                # Dynamic tags
                #

                dynamic_tags_lookup(
                    key_value,
                    tags_collection_keys,
                    tags_collection_dict,
                    record,
                )

                #
                # Labels
                #

                dynamic_labels_lookup(
                    key_value,
                    component,
                    labels_def_collection_dict,
                    labels_assign_collection_dict,
                    record,
                )

                #
                # Notes count (per entity)
                #

                record["notes_count"] = notes_count_by_object.get(key_value, 0)

                #
                # Dynamic sla_class
                #

                dynamic_sla_class_lookup(
                    key_value,
                    sla_collection_keys,
                    sla_collection_dict,
                    record,
                )

                #
                # Disruption queue
                #
                
                # Aggregate disruption_min_time_sec: take maximum value across all trackers
                aggregated_disruption_min_time_sec = default_disruption_min_time_sec
                if "disruption_min_time_sec" in record:
                    try:
                        disruption_min_time_value = record.get("disruption_min_time_sec")
                        if disruption_min_time_value:
                            disruption_times_by_tracker = None
                            
                            # Parse if it's a JSON string
                            if isinstance(disruption_min_time_value, str):
                                try:
                                    disruption_times_by_tracker = json.loads(disruption_min_time_value)
                                except (json.JSONDecodeError, TypeError):
                                    # If parsing fails, might be old format numeric value
                                    try:
                                        aggregated_disruption_min_time_sec = max(
                                            default_disruption_min_time_sec,
                                            int(float(disruption_min_time_value))
                                        )
                                    except (ValueError, TypeError):
                                        pass
                            elif isinstance(disruption_min_time_value, dict):
                                disruption_times_by_tracker = disruption_min_time_value
                            else:
                                # Numeric value (old format)
                                try:
                                    aggregated_disruption_min_time_sec = max(
                                        default_disruption_min_time_sec,
                                        int(float(disruption_min_time_value))
                                    )
                                except (ValueError, TypeError):
                                    pass
                            
                            # If tracker-keyed format, take maximum across all trackers
                            if disruption_times_by_tracker and isinstance(disruption_times_by_tracker, dict):
                                max_disruption_time = max(
                                    int(float(v)) for v in disruption_times_by_tracker.values()
                                )
                                aggregated_disruption_min_time_sec = max(
                                    default_disruption_min_time_sec,
                                    max_disruption_time
                                )
                    except Exception as e:
                        logger.error(
                            f'instance_id={self.instance_id}, failed to aggregate disruption_min_time_sec for object="{object_value}", '
                            f'exception="{str(e)}"'
                        )

                disruption_queue_record = disruption_queue_lookup(
                    key_value,
                    disruption_queue_collection_keys,
                    disruption_queue_collection_dict,
                    aggregated_disruption_min_time_sec,
                )

                #
                # Outliers status (all components except mhm)
                #

                if component not in ["mhm"]:
                    outliers_data_lookup(
                        key_value,
                        outliers_data_collection_keys,
                        outliers_data_collection_dict,
                        outliers_rules_collection_keys,
                        outliers_rules_collection_dict,
                        record,
                    )

                #
                # Outliers readiness
                #

                outliers_readiness(record)

                #
                # Human time fields context
                #

                record["latest_flip_time (translated)"] = convert_epoch_to_datetime(
                    record.get("latest_flip_time", "0")
                )
                record["tracker_runtime (translated)"] = convert_epoch_to_datetime(
                    record.get("tracker_runtime", "0")
                )

                #
                # tags field, if not existing in record, set to "N/A"
                #
                tags_auto = record.get("tags_auto", [])
                tags_manual = record.get("tags_manual", [])

                if tags_auto:
                    # if tags_auto is a string, convert to a list
                    if isinstance(tags_auto, str):
                        tags_auto = tags_auto.split(",")
                else:
                    tags_auto = []
                # add to record
                record["tags_auto"] = tags_auto

                if tags_manual:
                    # if tags_manual is a string, convert to a list
                    if isinstance(tags_manual, str):
                        tags_manual = tags_manual.split(",")
                else:
                    tags_manual = []
                # add to record
                record["tags_manual"] = tags_manual

                # merge tags_auto and tags_manual into tags
                tags = sorted(
                    list(set([x.lower() for x in tags_auto + tags_manual if x]))
                )

                # finally, set the tags field if not existing
                if not tags:
                    record["tags"] = "N/A"
                else:
                    record["tags"] = tags

                #
                # splk-dsm
                #

                # get record fields depending on the component
                if component == "dsm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # refresh data_last_lag_seen in the record
                        try:
                            record["data_last_lag_seen"] = time.time() - float(
                                record.get("data_last_time_seen", 0)
                            )
                        except:
                            record["data_last_lag_seen"] = 0

                        # get outliers and data sampling
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        try:
                            isAnomaly = int(record.get("isAnomaly", 0))
                        except:
                            isAnomaly = 0

                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", isAnomaly="{isAnomaly}"'
                            )

                        # get future_tolerance
                        future_tolerance = record.get("future_tolerance", 0)
                        try:
                            future_tolerance = float(future_tolerance)
                        except:
                            future_tolerance = 0

                        # get actual primary KPI values
                        data_last_ingestion_lag_seen = record.get(
                            "data_last_ingestion_lag_seen", 0
                        )
                        if data_last_ingestion_lag_seen == "":
                            data_last_ingestion_lag_seen = 0
                        try:
                            data_last_ingestion_lag_seen = float(
                                data_last_ingestion_lag_seen
                            )
                        except:
                            data_last_ingestion_lag_seen = 0
                        data_last_lag_seen = record.get("data_last_lag_seen", 0)

                        # get per entity thresholds
                        data_max_lag_allowed = float(
                            record.get("data_max_lag_allowed", 0)
                        )
                        data_max_delay_allowed = float(
                            record.get("data_max_delay_allowed", 0)
                        )

                        # resolve lagging class threshold (overrides entity thresholds if matched)
                        lc_matched = False
                        lc_delay_mode = None
                        lc_resolved_delay = None
                        lc_active_slot = None
                        if lagging_classes_records:
                            (
                                lc_matched,
                                lc_override_lag,
                                lc_override_delay,
                                lc_delay_mode,
                                lc_resolved_delay,
                                lc_active_slot,
                                lc_match_info,
                            ) = resolve_lagging_class_threshold(
                                record, lagging_classes_records
                            )
                            if lc_matched:
                                # Threshold intent lock — a pinned threshold is
                                # not overridden by a lagging class (real-time
                                # display + state must match the persisted pin).
                                if lc_override_lag is not None and not is_lag_threshold_locked(
                                    record
                                ):
                                    data_max_lag_allowed = lc_override_lag
                                    record["data_max_lag_allowed"] = lc_override_lag
                                if (
                                    lc_delay_mode == "static"
                                    and lc_override_delay is not None
                                    and not is_delay_threshold_locked(record)
                                ):
                                    data_max_delay_allowed = lc_override_delay
                                    record["data_max_delay_allowed"] = lc_override_delay
                                # populate transient lagging class fields on the record for UI visibility
                                record["lagging_class_matched"] = "true"
                                record["lagging_class_name"] = str(lc_match_info.get("name", ""))
                                record["lagging_class_level"] = str(lc_match_info.get("level", ""))
                                record["lagging_class_match_mode"] = str(lc_match_info.get("match_mode", ""))
                                record["lagging_class_delay_mode"] = str(lc_delay_mode) if lc_delay_mode else ""
                                record["lagging_class_key"] = str(lc_match_info.get("_key", ""))
                        if not lc_matched:
                            record["lagging_class_matched"] = "false"
                            record["lagging_class_name"] = ""
                            record["lagging_class_level"] = ""
                            record["lagging_class_match_mode"] = ""
                            record["lagging_class_delay_mode"] = ""
                            record["lagging_class_key"] = ""

                        min_dcount_threshold = record.get("min_dcount_threshold", 0)
                        try:
                            min_dcount_threshold = float(min_dcount_threshold)
                        except:
                            min_dcount_threshold = 0

                        # get dcount host related information
                        min_dcount_host = record.get("min_dcount_host", "any")
                        try:
                            min_dcount_host = float(min_dcount_host)
                        except:
                            pass
                        min_dcount_field = record.get("min_dcount_field", None)

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # get data_last_ingest, data_last_time_seen, data_last_time_seen_idx (epochtime)
                        data_last_ingest = record.get("data_last_ingest", 0)
                        try:
                            data_last_ingest = float(data_last_ingest)
                        except:
                            pass
                        data_last_time_seen = record.get("data_last_time_seen", 0)
                        if data_last_time_seen == "":
                            data_last_time_seen = 0
                        try:
                            data_last_time_seen = float(data_last_time_seen)
                        except:
                            data_last_time_seen = 0
                        data_last_time_seen_idx = record.get(
                            "data_last_time_seen_idx", 0
                        )
                        try:
                            data_last_time_seen_idx = float(data_last_time_seen_idx)
                        except:
                            pass

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 921-933)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                            )

                        #
                        # DSM Sampling
                        #

                        # call function dsm_sampling_lookup
                        dsm_sampling_lookup(
                            object_value,
                            sampling_collection_keys,
                            sampling_collection_dict,
                            record,
                        )

                        # call get_data_sampling_status and define isAnomaly
                        isAnomaly = get_data_sampling_status(
                            record.get("data_sample_status_colour"),
                            record.get("data_sample_feature"),
                            tenant_data_sampling_set_state,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isAnomaly="{isAnomaly}", tenant_data_sampling_set_state="{tenant_data_sampling_set_state}"'
                            )

                        # call get_future_status and define isFuture
                        (
                            isFuture,
                            isFutureMsg,
                            merged_future_tolerance,
                        ) = get_future_status(
                            future_tolerance,
                            system_future_tolerance,
                            data_last_lag_seen,
                            data_last_ingestion_lag_seen,
                            data_last_time_seen,
                            data_last_ingest,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isFuture="{isFuture}", future_tolerance="{future_tolerance}", system_future_tolerance="{system_future_tolerance}", merged_future_tolerance="{merged_future_tolerance}", data_last_lag_seen="{data_last_lag_seen}", isFutureMsg="{isFutureMsg}"'
                            )

                        # call get_is_under_dcount_host and define isUnderDcountHost
                        (
                            isUnderDcountHost,
                            isUnderDcountHostMsg,
                        ) = get_is_under_dcount_host(
                            min_dcount_host, min_dcount_threshold, min_dcount_field
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderDcountHost="{isUnderDcountHost}", isUnderDcountHostMsg="{isUnderDcountHostMsg}", min_dcount_host="{min_dcount_host}", min_dcount_threshold="{min_dcount_threshold}"'
                            )

                        # call get_dsm_latency_status and define isUnderLatencyAlert and isUnderLatencyMessage
                        (
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                        ) = get_dsm_latency_status(
                            data_last_ingestion_lag_seen,
                            data_max_lag_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderLatencyAlert="{isUnderLatencyAlert}", isUnderLatencyMessage="{isUnderLatencyMessage}", data_last_ingestion_lag_seen="{data_last_ingestion_lag_seen}", data_max_lag_allowed="{data_max_lag_allowed}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                            )

                        # resolve variable delay threshold
                        # Lagging class variable delay takes precedence over entity-level variable delay
                        # Lagging class static delay is authoritative and skips entity-level variable delay
                        if lc_matched and lc_delay_mode == "variable":
                            # Use lagging class variable delay
                            resolved_threshold = lc_resolved_delay
                            active_slot_name = lc_active_slot
                            is_variable = True
                        elif lc_matched and lc_delay_mode == "static":
                            # Lagging class static delay is authoritative, do not allow
                            # entity-level variable delay to override it
                            resolved_threshold = None
                            active_slot_name = None
                            is_variable = False
                        else:
                            # No lagging class match, fall through to entity-level variable delay
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # Threshold intent lock — a pinned delay threshold must
                        # govern the (real-time) decision/display path and IGNORE
                        # lagging classes. But a locked VARIABLE-policy entity must
                        # keep evaluating against its OWN slots (time-aware), not
                        # collapse to a flat static value. Re-resolve from the
                        # entity's own variable-delay record: variable entities keep
                        # their slots, static entities resolve to is_variable=False
                        # and use the pinned data_max_delay_allowed.
                        if is_delay_threshold_locked(record):
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # populate transient variable delay fields on the record
                        if is_variable:
                            record["variable_delay_active_slot"] = str(active_slot_name) if active_slot_name else ""
                            record["variable_delay_active_threshold"] = str(int(round(resolved_threshold, 0)))
                            # Override data_max_delay_allowed with the effective variable threshold
                            # (transient override for response only — component handler is read-only)
                            record["data_max_delay_allowed"] = resolved_threshold
                        else:
                            record["variable_delay_active_slot"] = ""
                            record["variable_delay_active_threshold"] = ""

                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", variable_delay_policy="{record.get("variable_delay_policy", "static")}", is_variable="{is_variable}", active_slot_name="{active_slot_name}", resolved_threshold="{resolved_threshold}", lc_matched="{lc_matched}", lc_delay_mode="{lc_delay_mode}"'
                            )

                        # call get_dsm_delay_status and define isUnderDelayAlert and isUnderDelayMessage
                        (
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                        ) = get_dsm_delay_status(
                            data_last_lag_seen,
                            data_max_delay_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                            resolved_max_delay_allowed=resolved_threshold if is_variable else None,
                            variable_delay_slot_name=active_slot_name if is_variable else None,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderDelayAlert="{isUnderDelayAlert}", isUnderDelayMessage="{isUnderDelayMessage}", data_last_lag_seen="{data_last_lag_seen}", data_max_delay_allowed="{data_max_delay_allowed}", resolved_threshold="{resolved_threshold}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                            )

                        # Initialize threshold_scores for DSM (DSM doesn't use dynamic thresholds, so this is always empty)
                        threshold_scores = []

                        # call set_dsm_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_dsm_status(
                            logger,
                            request_info.server_rest_uri,
                            request_info.system_authtoken,
                            tenant_id,
                            record,
                            isOutlier,
                            isAnomaly,
                            isFuture,
                            isFutureMsg,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            isUnderDcountHost,
                            isUnderDcountHostMsg,
                            object_logical_group_dict,
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="rest_handler",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                            delay_is_variable=is_variable,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, set_dsm_status, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                            )

                        # insert our main fields
                        record["object_state"] = object_state
                        record["status_message"] = " | ".join(status_message)
                        record["status_message_json"] = status_message_json
                        record["anomaly_reason"] = "|".join(anomaly_reason)

                        # generate charts resources for this entity
                        if load_charts_resources:
                            try:
                                charts_resources = generate_charts_resources(
                                    tenant_id=tenant_id,
                                    component="dsm",
                                    object=object_value,
                                    keyid=key_value,
                                    anomaly_reason=anomaly_reason,
                                    vtenant_conf=vtenant_conf,
                                    service=service,
                                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                                )
                                record["charts_resources"] = charts_resources
                            except Exception as e:
                                logger.warning(f"Failed to generate charts for DSM entity {key_value}: {str(e)}")
                                record["charts_resources"] = []

                        # sampling status
                        sampling_anomaly_status(record)

                        # future tolerance
                        try:
                            record["future_tolerance"] = int(
                                round(merged_future_tolerance, 0)
                            )
                        except:
                            record["future_tolerance"] = -600

                        # convert data_last_time_seen to last_time from epoch
                        last_time = convert_epoch_to_datetime(data_last_time_seen)
                        record["last_time"] = last_time

                        # convert data_last_ingest to last_ingest from epoch
                        last_ingest = convert_epoch_to_datetime(data_last_ingest)
                        record["last_ingest"] = last_ingest

                        # convert data_last_time_seen_idx to last_time_idx from epoch
                        last_time_idx = convert_epoch_to_datetime(data_last_time_seen)
                        record["last_time_idx"] = last_time_idx

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        record["latest_flip_time_human"] = convert_epoch_to_datetime(
                            latest_flip_time_human
                        )

                        # set lag_summary field
                        record["lag_summary"] = set_feeds_lag_summary(record, component)

                        # get and set thresholds_duration
                        (
                            data_max_delay_allowed_duration,
                            data_max_lag_allowed_duration,
                        ) = set_feeds_thresholds_duration(record)
                        record["data_max_delay_allowed_duration"] = (
                            data_max_delay_allowed_duration
                        )
                        record["data_max_lag_allowed_duration"] = (
                            data_max_lag_allowed_duration
                        )

                        # Documentation note
                        docs_ref_lookup(
                            docs_is_global,
                            docs_note_global,
                            docs_link_global,
                            object_value,
                            docs_collection_members_list,
                            docs_collection_members_dict,
                            record,
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-dhm
                #

                elif component == "dhm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # refresh data_last_lag_seen in the record
                        try:
                            record["data_last_lag_seen"] = time.time() - float(
                                record.get("data_last_time_seen", 0)
                            )
                        except:
                            record["data_last_lag_seen"] = 0

                        # get splk_dhm_st_summary
                        splk_dhm_st_summary = record.get("splk_dhm_st_summary", None)
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", splk_dhm_st_summary="{splk_dhm_st_summary}"'
                            )

                        # get outliers and data sampling
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        try:
                            isAnomaly = int(record.get("isAnomaly", 0))
                        except:
                            isAnomaly = 0

                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", isAnomaly="{isAnomaly}"'
                            )

                        # get future_tolerance
                        future_tolerance = record.get("future_tolerance", 0)
                        try:
                            future_tolerance = float(future_tolerance)
                        except:
                            future_tolerance = 0

                        # get actual primary KPI values
                        data_last_ingestion_lag_seen = record.get(
                            "data_last_ingestion_lag_seen", 0
                        )
                        if data_last_ingestion_lag_seen == "":
                            data_last_ingestion_lag_seen = 0
                        try:
                            data_last_ingestion_lag_seen = float(
                                data_last_ingestion_lag_seen
                            )
                        except:
                            data_last_ingestion_lag_seen = 0
                        data_last_lag_seen = record.get("data_last_lag_seen", 0)

                        # get per entity thresholds
                        data_max_lag_allowed = float(
                            record.get("data_max_lag_allowed", 0)
                        )
                        data_max_delay_allowed = float(
                            record.get("data_max_delay_allowed", 0)
                        )

                        # resolve lagging class threshold (overrides entity thresholds if matched)
                        lc_matched = False
                        lc_delay_mode = None
                        lc_resolved_delay = None
                        lc_active_slot = None
                        if lagging_classes_records:
                            (
                                lc_matched,
                                lc_override_lag,
                                lc_override_delay,
                                lc_delay_mode,
                                lc_resolved_delay,
                                lc_active_slot,
                                lc_match_info,
                            ) = resolve_lagging_class_threshold(
                                record, lagging_classes_records
                            )
                            if lc_matched:
                                # Threshold intent lock — a pinned threshold is
                                # not overridden by a lagging class (real-time
                                # display + state must match the persisted pin).
                                if lc_override_lag is not None and not is_lag_threshold_locked(
                                    record
                                ):
                                    data_max_lag_allowed = lc_override_lag
                                    record["data_max_lag_allowed"] = lc_override_lag
                                if (
                                    lc_delay_mode == "static"
                                    and lc_override_delay is not None
                                    and not is_delay_threshold_locked(record)
                                ):
                                    data_max_delay_allowed = lc_override_delay
                                    record["data_max_delay_allowed"] = lc_override_delay
                                # populate transient lagging class fields on the record for UI visibility
                                record["lagging_class_matched"] = "true"
                                record["lagging_class_name"] = str(lc_match_info.get("name", ""))
                                record["lagging_class_level"] = str(lc_match_info.get("level", ""))
                                record["lagging_class_match_mode"] = str(lc_match_info.get("match_mode", ""))
                                record["lagging_class_delay_mode"] = str(lc_delay_mode) if lc_delay_mode else ""
                                record["lagging_class_key"] = str(lc_match_info.get("_key", ""))
                        if not lc_matched:
                            record["lagging_class_matched"] = "false"
                            record["lagging_class_name"] = ""
                            record["lagging_class_level"] = ""
                            record["lagging_class_match_mode"] = ""
                            record["lagging_class_delay_mode"] = ""
                            record["lagging_class_key"] = ""

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # get data_last_ingest, data_last_time_seen, data_last_time_seen_idx (epochtime)
                        data_last_ingest = record.get("data_last_ingest", 0)
                        try:
                            data_last_ingest = float(data_last_ingest)
                        except:
                            pass
                        data_last_time_seen = record.get("data_last_time_seen", 0)
                        if data_last_time_seen == "":
                            data_last_time_seen = 0
                        try:
                            data_last_time_seen = float(data_last_time_seen)
                        except:
                            data_last_time_seen = 0
                        data_last_time_seen_idx = record.get(
                            "data_last_time_seen_idx", 0
                        )
                        try:
                            data_last_time_seen_idx = float(data_last_time_seen_idx)
                        except:
                            pass

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 920-923)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                            )

                        # call get_future_status and define isFuture
                        (
                            isFuture,
                            isFutureMsg,
                            merged_future_tolerance,
                        ) = get_future_status(
                            future_tolerance,
                            system_future_tolerance,
                            data_last_lag_seen,
                            data_last_ingestion_lag_seen,
                            data_last_time_seen,
                            data_last_ingest,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isFuture="{isFuture}", future_tolerance="{future_tolerance}", system_future_tolerance="{system_future_tolerance}", merged_future_tolerance="{merged_future_tolerance}", data_last_lag_seen="{data_last_lag_seen}", isFutureMsg="{isFutureMsg}"'
                            )

                        # call get_dsm_latency_status and define isUnderLatencyAlert and isUnderLatencyMessage
                        (
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                        ) = get_dsm_latency_status(
                            data_last_ingestion_lag_seen,
                            data_max_lag_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderLatencyAlert="{isUnderLatencyAlert}", isUnderLatencyMessage="{isUnderLatencyMessage}", data_last_ingestion_lag_seen="{data_last_ingestion_lag_seen}", data_max_lag_allowed="{data_max_lag_allowed}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                            )

                        # resolve variable delay threshold
                        # Lagging class variable delay takes precedence over entity-level variable delay
                        # Lagging class static delay is authoritative and skips entity-level variable delay
                        if lc_matched and lc_delay_mode == "variable":
                            # Use lagging class variable delay
                            resolved_threshold = lc_resolved_delay
                            active_slot_name = lc_active_slot
                            is_variable = True
                        elif lc_matched and lc_delay_mode == "static":
                            # Lagging class static delay is authoritative, do not allow
                            # entity-level variable delay to override it
                            resolved_threshold = None
                            active_slot_name = None
                            is_variable = False
                        else:
                            # No lagging class match, fall through to entity-level variable delay
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # Threshold intent lock — a pinned delay threshold must
                        # govern the (real-time) decision/display path and IGNORE
                        # lagging classes. But a locked VARIABLE-policy entity must
                        # keep evaluating against its OWN slots (time-aware), not
                        # collapse to a flat static value. Re-resolve from the
                        # entity's own variable-delay record: variable entities keep
                        # their slots, static entities resolve to is_variable=False
                        # and use the pinned data_max_delay_allowed.
                        if is_delay_threshold_locked(record):
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # populate transient variable delay fields on the record
                        if is_variable:
                            record["variable_delay_active_slot"] = str(active_slot_name) if active_slot_name else ""
                            record["variable_delay_active_threshold"] = str(int(round(resolved_threshold, 0)))
                            # Override data_max_delay_allowed with the effective variable threshold
                            # (transient override for response only — component handler is read-only)
                            record["data_max_delay_allowed"] = resolved_threshold
                        else:
                            record["variable_delay_active_slot"] = ""
                            record["variable_delay_active_threshold"] = ""

                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", variable_delay_policy="{record.get("variable_delay_policy", "static")}", is_variable="{is_variable}", active_slot_name="{active_slot_name}", resolved_threshold="{resolved_threshold}", lc_matched="{lc_matched}", lc_delay_mode="{lc_delay_mode}"'
                            )

                        # call get_dsm_delay_status and define isUnderDelayAlert and isUnderDelayMessage
                        (
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                        ) = get_dsm_delay_status(
                            data_last_lag_seen,
                            data_max_delay_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                            resolved_max_delay_allowed=resolved_threshold if is_variable else None,
                            variable_delay_slot_name=active_slot_name if is_variable else None,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderDelayAlert="{isUnderDelayAlert}", isUnderDelayMessage="{isUnderDelayMessage}", data_last_lag_seen="{data_last_lag_seen}", data_max_delay_allowed="{data_max_delay_allowed}", resolved_threshold="{resolved_threshold}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                            )

                        # Initialize threshold_scores for DHM (DHM doesn't use dynamic thresholds, so this is always empty)
                        threshold_scores = []

                        # call set_dhm_status and define object_state and anomaly_reason (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 921-933)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                            splk_dhm_alerting_policy,
                        ) = set_dhm_status(
                            logger,
                            request_info.server_rest_uri,
                            request_info.system_authtoken,
                            tenant_id,
                            record,
                            isOutlier,
                            isFuture,
                            isFutureMsg,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                            default_splk_dhm_alerting_policy,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="rest_handler",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                            delay_is_variable=is_variable,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                            )

                        # insert our main fields
                        record["object_state"] = object_state
                        record["status_message"] = " | ".join(status_message)
                        record["status_message_json"] = status_message_json
                        record["anomaly_reason"] = "|".join(anomaly_reason)

                        # generate charts resources for this entity
                        if load_charts_resources:
                            try:
                                charts_resources = generate_charts_resources(
                                    tenant_id=tenant_id,
                                    component="dhm",
                                    object=object_value,
                                    keyid=key_value,
                                    anomaly_reason=anomaly_reason,
                                    vtenant_conf=vtenant_conf,
                                    service=service,
                                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                                )
                                record["charts_resources"] = charts_resources
                            except Exception as e:
                                logger.warning(f"Failed to generate charts for DHM entity {key_value}: {str(e)}")
                                record["charts_resources"] = []

                        # future tolerance
                        try:
                            record["future_tolerance"] = int(
                                round(merged_future_tolerance, 0)
                            )
                        except:
                            record["future_tolerance"] = -600

                        # specific for dhm
                        record["splk_dhm_alerting_policy"] = splk_dhm_alerting_policy

                        # convert data_last_time_seen to last_time from epoch
                        last_time = convert_epoch_to_datetime(data_last_time_seen)
                        record["last_time"] = last_time

                        # convert data_last_ingest to last_ingest from epoch
                        last_ingest = convert_epoch_to_datetime(data_last_ingest)
                        record["last_ingest"] = last_ingest

                        # convert data_last_time_seen_idx to last_time_idx from epoch
                        last_time_idx = convert_epoch_to_datetime(data_last_time_seen)
                        record["last_time_idx"] = last_time_idx

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        record["latest_flip_time_human"] = convert_epoch_to_datetime(
                            latest_flip_time_human
                        )

                        # set lag_summary field
                        record["lag_summary"] = set_feeds_lag_summary(record, component)

                        # get and set thresholds_duration
                        (
                            data_max_delay_allowed_duration,
                            data_max_lag_allowed_duration,
                        ) = set_feeds_thresholds_duration(record)
                        record["data_max_delay_allowed_duration"] = (
                            data_max_delay_allowed_duration
                        )
                        record["data_max_lag_allowed_duration"] = (
                            data_max_lag_allowed_duration
                        )

                        # sourcetype summary: generated on-demand from raw splk_dhm_st_summary
                        # Only the raw summary is stored in KV; display views are computed here
                        dhm_views = generate_dhm_summary_views(
                            record.get("splk_dhm_st_summary", "{}")
                        )
                        record["sourcetype_summary"] = dhm_views["minimal"]
                        record["splk_dhm_st_summary_full"] = dhm_views["full"]

                        # Documentation note
                        docs_ref_lookup(
                            docs_is_global,
                            docs_note_global,
                            docs_link_global,
                            object_value,
                            docs_collection_members_list,
                            docs_collection_members_dict,
                            record,
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-mhm
                #

                elif component == "mhm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # refresh data_last_lag_seen in the record
                        try:
                            record["last_lag_seen"] = time.time() - float(
                                record.get("metric_last_time_seen", 0)
                            )
                        except:
                            record["last_lag_seen"] = 0

                        # get metric_details
                        metric_details = record.get("metric_details", None)
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", metric_details="{metric_details}"'
                            )

                        # metric_details summary replacements
                        record["metric_details"] = record.get(
                            f"metric_details_{mode_view}", "{}"
                        )
                        # remove metric_details_* for optimization purposes
                        del record["metric_details_minimal"]
                        del record["metric_details_compact"]
                        # metric_details_full cannot be removed for UI expansion purposes

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # get metric_last_time_seen (epochtime)
                        metric_last_time_seen = record.get("metric_last_time_seen", 0)
                        try:
                            metric_last_time_seen = float(metric_last_time_seen)
                        except:
                            pass

                        # call get_future_metrics_status and define isFuture
                        isFuture, isFutureMsg = get_future_metrics_status(
                            system_future_tolerance,
                            metric_last_time_seen,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isFuture="{isFuture}", system_future_tolerance="{system_future_tolerance}", metric_last_time_seen="{metric_last_time_seen}", isFutureMsg="{isFutureMsg}"'
                            )

                        # get monitoring time policy and rules
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # call set_mhm_status and define object_state and anomaly_reason (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 921-933)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_mhm_status(
                            logger,
                            request_info.server_rest_uri,
                            request_info.system_authtoken,
                            tenant_id,
                            record,
                            metric_details,
                            isFuture,
                            isFutureMsg,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="rest_handler",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                            )

                        # insert our main fields
                        record["object_state"] = object_state
                        record["status_message"] = " | ".join(status_message)
                        record["status_message_json"] = status_message_json
                        record["anomaly_reason"] = "|".join(anomaly_reason)

                        # generate charts resources for this entity
                        if load_charts_resources:
                            try:
                                charts_resources = generate_charts_resources(
                                    tenant_id=tenant_id,
                                    component="mhm",
                                    object=object_value,
                                    keyid=key_value,
                                    anomaly_reason=anomaly_reason,
                                    vtenant_conf=vtenant_conf,
                                    service=service,
                                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                                )
                                record["charts_resources"] = charts_resources
                            except Exception as e:
                                logger.warning(f"Failed to generate charts for MHM entity {key_value}: {str(e)}")
                                record["charts_resources"] = []

                        # convert metric_last_time_seen to last_time from epoch
                        last_time = convert_epoch_to_datetime(metric_last_time_seen)
                        record["last_time"] = last_time

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        record["latest_flip_time_human"] = convert_epoch_to_datetime(
                            latest_flip_time_human
                        )

                        # set lag_summary field
                        record["lag_summary"] = set_feeds_lag_summary(record, component)

                        # Documentation note
                        docs_ref_lookup(
                            docs_is_global,
                            docs_note_global,
                            docs_link_global,
                            object_value,
                            docs_collection_members_list,
                            docs_collection_members_dict,
                            record,
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-flx
                #

                # get record fields depending on the component
                elif component == "flx":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get outliers
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}"'
                            )

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 920-923)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                            )

                        # Aggregate tracker-keyed JSON fields for concurrent trackers support (same logic as decision maker)
                        # Aggregate metrics: merge all trackers' metrics into a single dict
                        # This must be done BEFORE flx_check_dynamic_thresholds which expects aggregated metrics
                        if "metrics" in record:
                            try:
                                metrics_value = record.get("metrics")
                                if metrics_value:
                                    metrics_by_tracker = None
                                    
                                    # Parse if it's a JSON string
                                    if isinstance(metrics_value, str):
                                        try:
                                            metrics_by_tracker = json.loads(metrics_value)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format, skip aggregation
                                            pass
                                    elif isinstance(metrics_value, dict):
                                        metrics_by_tracker = metrics_value
                                    
                                    if metrics_by_tracker and isinstance(metrics_by_tracker, dict):
                                        # Check if it's tracker-keyed format (values are dicts) or old format (direct metrics dict)
                                        aggregated_metrics = {}
                                        is_tracker_keyed = False
                                        
                                        for key, value in metrics_by_tracker.items():
                                            if isinstance(value, dict):
                                                # Check if value looks like metrics (has numeric/string values) or tracker data
                                                # If all values in the nested dict are simple types, it's likely metrics
                                                if all(isinstance(v, (int, float, str, bool)) or v is None for v in value.values()):
                                                    # This is tracker-keyed format, merge all trackers' metrics
                                                    aggregated_metrics.update(value)
                                                    is_tracker_keyed = True
                                                else:
                                                    # Nested structure, might be tracker data
                                                    is_tracker_keyed = True
                                                    aggregated_metrics.update(value)
                                            else:
                                                # Simple value, old format
                                                break
                                        
                                        if is_tracker_keyed:
                                            # Remove internal "status" field from aggregated metrics (not a user metric)
                                            if "status" in aggregated_metrics:
                                                del aggregated_metrics["status"]
                                            
                                            # Update record with aggregated metrics as dict (for backward compatibility)
                                            # Handle empty aggregated_metrics case (e.g., {"tracker1": {}})
                                            record["metrics"] = aggregated_metrics
                                        elif not is_tracker_keyed:
                                            # Old format (already aggregated flat dict), remove status field
                                            if isinstance(metrics_value, str):
                                                try:
                                                    old_metrics = json.loads(metrics_value)
                                                    if isinstance(old_metrics, dict):
                                                        if "status" in old_metrics:
                                                            old_metrics = old_metrics.copy()
                                                            del old_metrics["status"]
                                                        record["metrics"] = old_metrics
                                                    else:
                                                        record["metrics"] = {}
                                                except:
                                                    record["metrics"] = {}
                                            else:
                                                # metrics_by_tracker is already the parsed dict
                                                if isinstance(metrics_by_tracker, dict):
                                                    if "status" in metrics_by_tracker:
                                                        metrics_by_tracker = metrics_by_tracker.copy()
                                                        del metrics_by_tracker["status"]
                                                    record["metrics"] = metrics_by_tracker
                                                else:
                                                    record["metrics"] = {}
                            except Exception as e:
                                logger.error(
                                    f'instance_id={self.instance_id}, failed to aggregate metrics for object="{object_value}", '
                                    f'exception="{str(e)}"'
                                )

                        # flx thresholds lookup
                        flx_thresholds_lookup(
                            object_value,
                            key_value,
                            record,
                            thresholds_collection_dict,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}"'
                            )

                        # flx check dynamic thresholds
                        threshold_alert, threshold_messages, threshold_scores = (
                            flx_check_dynamic_thresholds(
                                logger,
                                record.get("dynamic_thresholds", {}),
                                record.get("metrics", {}),
                            )
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, result function flx_check_dynamic_thresholds object_value="{object_value}", key_value="{key_value}", threshold_alert="{threshold_alert}", threshold_messages="{threshold_messages}", dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}", metrics_record="{json.dumps(record.get("metrics", {}), indent=2)}"'
                            )

                        # flx drilldown searches lookup
                        try:
                            flx_drilldown_searches_lookup(
                                tenant_id,
                                record.get("tracker_name", ""),
                                record.get("account", "local"),
                                record,
                                drilldown_searches_collection_dict,
                            )
                            if _debug:
                                logger.debug(
                                    f'instance_id={self.instance_id}, drilldown_search="{record.get("drilldown_search", "")}", drilldown_search_earliest="{record.get("drilldown_search_earliest", "")}", drilldown_search_latest="{record.get("drilldown_search_latest", "")}", drilldown_searches="{json.dumps(record.get("drilldown_searches", []), indent=2)}"'
                                )
                        except Exception as e:
                            logger.error(f"instance_id={self.instance_id}, Error in flx_drilldown_searches_lookup: {str(e)}")

                        # flx default metrics lookup
                        try:
                            flx_default_metrics_lookup(
                                tenant_id,
                                record.get("tracker_name", ""),
                                record,
                                default_metrics_collection_dict,
                            )
                            if _debug:
                                logger.debug(
                                    f'instance_id={self.instance_id}, default_metric="{record.get("default_metric", "")}"'
                                )
                        except Exception as e:
                            logger.error(f"instance_id={self.instance_id}, Error in flx_default_metrics_lookup: {str(e)}")

                        # Determine number of trackers to decide if we need prefix
                        num_trackers = 1
                        if "tracker_name" in record:
                            try:
                                tracker_name_value = record.get("tracker_name")
                                if tracker_name_value:
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list):
                                                num_trackers = len(tracker_names)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be comma-separated string
                                            if "," in tracker_name_value:
                                                num_trackers = len([t.strip() for t in tracker_name_value.split(",")])
                                    elif isinstance(tracker_name_value, list):
                                        num_trackers = len(tracker_name_value)
                            except Exception:
                                pass
                        
                        # Aggregate status_description: concatenate all trackers' descriptions
                        if "status_description" in record:
                            try:
                                status_desc_value = record.get("status_description")
                                if status_desc_value:
                                    status_desc_by_tracker = None
                                    
                                    if isinstance(status_desc_value, str):
                                        try:
                                            status_desc_by_tracker = json.loads(status_desc_value)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, keep as-is
                                            pass
                                    elif isinstance(status_desc_value, dict):
                                        status_desc_by_tracker = status_desc_value
                                    
                                    if status_desc_by_tracker and isinstance(status_desc_by_tracker, dict):
                                        # Check if it's tracker-keyed format (all values are strings) or old format
                                        status_descriptions = []
                                        is_tracker_keyed = False
                                        
                                        for tracker_name, desc in status_desc_by_tracker.items():
                                            if isinstance(desc, str):
                                                # Tracker-keyed format
                                                if desc:
                                                    # Only add prefix if multiple trackers
                                                    if num_trackers > 1:
                                                        status_descriptions.append(f"{tracker_name}: {desc}")
                                                    else:
                                                        status_descriptions.append(desc)
                                                    is_tracker_keyed = True
                                            else:
                                                # Not tracker-keyed format
                                                break
                                        
                                        if is_tracker_keyed and status_descriptions:
                                            # Update record with aggregated status_description
                                            record["status_description"] = " | ".join(status_descriptions)
                            except Exception as e:
                                logger.error(
                                    f'instance_id={self.instance_id}, failed to aggregate status_description for object="{object_value}", '
                                    f'exception="{str(e)}"'
                                )
                        
                        # Aggregate status_description_short: concatenate all trackers' descriptions
                        if "status_description_short" in record:
                            try:
                                status_desc_short_value = record.get("status_description_short")
                                if status_desc_short_value:
                                    status_desc_short_by_tracker = None

                                    if isinstance(status_desc_short_value, str):
                                        try:
                                            status_desc_short_by_tracker = json.loads(status_desc_short_value)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, keep as-is
                                            pass
                                    elif isinstance(status_desc_short_value, dict):
                                        status_desc_short_by_tracker = status_desc_short_value

                                    if status_desc_short_by_tracker and isinstance(status_desc_short_by_tracker, dict):
                                        # Check if it's tracker-keyed format
                                        status_descriptions_short = []
                                        is_tracker_keyed = False

                                        for tracker_name, desc in status_desc_short_by_tracker.items():
                                            if isinstance(desc, str):
                                                # Tracker-keyed format
                                                if desc:
                                                    # Only add prefix if multiple trackers
                                                    if num_trackers > 1:
                                                        status_descriptions_short.append(f"{tracker_name}: {desc}")
                                                    else:
                                                        status_descriptions_short.append(desc)
                                                    is_tracker_keyed = True
                                            else:
                                                # Not tracker-keyed format
                                                break

                                        if is_tracker_keyed and status_descriptions_short:
                                            # Update record with aggregated status_description_short
                                            record["status_description_short"] = " | ".join(status_descriptions_short)
                            except Exception as e:
                                logger.error(
                                    f'instance_id={self.instance_id}, failed to aggregate status_description_short for object="{object_value}", '
                                    f'exception="{str(e)}"'
                                )

                        # Aggregate tracker_name: convert JSON array to comma-separated string for display
                        if "tracker_name" in record:
                            try:
                                tracker_name_value = record.get("tracker_name")
                                if tracker_name_value:
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list):
                                                # Convert array to comma-separated string
                                                record["tracker_name"] = ", ".join(tracker_names)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, keep as-is
                                            pass
                                    elif isinstance(tracker_name_value, list):
                                        # Already a list, convert to comma-separated string
                                        record["tracker_name"] = ", ".join(tracker_name_value)
                            except Exception as e:
                                logger.error(
                                    f'instance_id={self.instance_id}, failed to aggregate tracker_name for object="{object_value}", '
                                    f'exception="{str(e)}"'
                                )
                        
                        # Aggregate object_description: concatenate all trackers' descriptions
                        if "object_description" in record:
                            try:
                                object_desc_value = record.get("object_description")
                                if object_desc_value:
                                    object_desc_by_tracker = None

                                    if isinstance(object_desc_value, str):
                                        try:
                                            object_desc_by_tracker = json.loads(object_desc_value)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, keep as-is
                                            pass
                                    elif isinstance(object_desc_value, dict):
                                        object_desc_by_tracker = object_desc_value

                                    if object_desc_by_tracker and isinstance(object_desc_by_tracker, dict):
                                        # Check if it's tracker-keyed format (all values are strings) or old format
                                        object_descriptions = []
                                        is_tracker_keyed = False

                                        for tracker_name, desc in object_desc_by_tracker.items():
                                            if isinstance(desc, str):
                                                # Tracker-keyed format
                                                if desc:
                                                    # Only add prefix if multiple trackers
                                                    if num_trackers > 1:
                                                        object_descriptions.append(f"{tracker_name}: {desc}")
                                                    else:
                                                        object_descriptions.append(desc)
                                                    is_tracker_keyed = True
                                            else:
                                                # Not tracker-keyed format
                                                break

                                        if is_tracker_keyed and object_descriptions:
                                            # Update record with aggregated object_description
                                            record["object_description"] = " | ".join(object_descriptions)
                            except Exception as e:
                                logger.error(
                                    f'instance_id={self.instance_id}, failed to aggregate object_description for object="{object_value}", '
                                    f'exception="{str(e)}"'
                                )

                        # call set_flx_status and define object_state and anomaly_reason (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 921-933)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_flx_status(
                            logger,
                            request_info.server_rest_uri,
                            request_info.system_authtoken,
                            tenant_id,
                            record,
                            isOutlier,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            threshold_alert,
                            threshold_messages,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="rest_handler",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            threshold_scores=threshold_scores,
                            vtenant_account=vtenant_conf,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                            )

                        # insert our main fields
                        record["object_state"] = object_state
                        record["status_message"] = " | ".join(status_message)
                        record["status_message_json"] = status_message_json
                        record["anomaly_reason"] = "|".join(anomaly_reason)

                        # generate charts resources for this entity
                        if load_charts_resources:
                            try:
                                charts_resources = generate_charts_resources(
                                    tenant_id=tenant_id,
                                    component="flx",
                                    object=object_value,
                                    keyid=key_value,
                                    anomaly_reason=anomaly_reason,
                                    vtenant_conf=vtenant_conf,
                                    service=service,
                                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                                )
                                record["charts_resources"] = charts_resources
                            except Exception as e:
                                logger.warning(f"Failed to generate charts for FLX entity {key_value}: {str(e)}")
                                record["charts_resources"] = []

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        record["latest_flip_time_human"] = convert_epoch_to_datetime(
                            latest_flip_time_human
                        )

                        # Documentation note
                        docs_ref_lookup(
                            docs_is_global,
                            docs_note_global,
                            docs_link_global,
                            object_value,
                            docs_collection_members_list,
                            docs_collection_members_dict,
                            record,
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-fqm
                #

                # get record fields depending on the component
                elif component == "fqm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get outliers
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}"'
                            )

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 920-923)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                            )

                        # fqm thresholds lookup
                        fqm_thresholds_lookup(
                            object_value,
                            key_value,
                            record,
                            thresholds_collection_dict,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}"'
                            )

                        # fqm check dynamic thresholds
                        threshold_alert, threshold_messages, threshold_scores = (
                            fqm_check_dynamic_thresholds(
                                logger,
                                record.get("dynamic_thresholds", {}),
                                record.get("metrics", {}),
                            )
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, result function fqm_check_dynamic_thresholds object_value="{object_value}", key_value="{key_value}", threshold_alert="{threshold_alert}", threshold_messages="{threshold_messages}", dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}", metrics_record="{json.dumps(record.get("metrics", {}), indent=2)}"'
                            )

                        # call set_fqm_status and define object_state and anomaly_reason (with hybrid scoring)
                        # Note: score and score_outliers are already extracted from scores_dict above (lines 921-933)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_fqm_status(
                            logger,
                            request_info.server_rest_uri,
                            request_info.system_authtoken,
                            tenant_id,
                            record,
                            isOutlier,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            threshold_alert,
                            threshold_messages,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="rest_handler",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            threshold_scores=threshold_scores,
                            vtenant_account=vtenant_conf,
                        )
                        if _debug:
                            logger.debug(
                                f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                            )

                        # insert our main fields
                        record["object_state"] = object_state
                        record["status_message"] = " | ".join(status_message)
                        record["status_message_json"] = status_message_json
                        record["anomaly_reason"] = "|".join(anomaly_reason)

                        # generate charts resources for this entity
                        if load_charts_resources:
                            try:
                                charts_resources = generate_charts_resources(
                                    tenant_id=tenant_id,
                                    component="fqm",
                                    object=object_value,
                                    keyid=key_value,
                                    anomaly_reason=anomaly_reason,
                                    vtenant_conf=vtenant_conf,
                                    service=service,
                                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                                )
                                record["charts_resources"] = charts_resources
                            except Exception as e:
                                logger.warning(f"Failed to generate charts for FQM entity {key_value}: {str(e)}")
                                record["charts_resources"] = []

                        # custom breakby fields support:
                        # 1 - try to load the content of fields_quality_summary (JSON as string)
                        # 2 - iterate over the JSON and look for fields metadata.* except the default metadata fields (datamodel, nodename, index, sourcetype)
                        # 3 - if one or more additional metadata fields are found, add them to the record as metadata_<fieldname> (instead of metadata.<fieldname>)
                        if "fields_quality_summary" in record:
                            try:
                                fields_quality_summary = json.loads(record["fields_quality_summary"])
                                for field in fields_quality_summary:
                                    if field.startswith("metadata."):
                                        if field not in ["metadata.datamodel", "metadata.nodename", "metadata.index", "metadata.sourcetype"]:
                                            newfield_name = field.replace("metadata.", "metadata_")
                                            record[f"{newfield_name}"] = fields_quality_summary[field]
                            except:
                                pass

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        record["latest_flip_time_human"] = convert_epoch_to_datetime(
                            latest_flip_time_human
                        )

                        # Documentation note
                        docs_ref_lookup(
                            docs_is_global,
                            docs_note_global,
                            docs_link_global,
                            object_value,
                            docs_collection_members_list,
                            docs_collection_members_dict,
                            record,
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-wlk
                #

                # get record fields depending on the component
                elif component == "wlk":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # set overgroup, if not existing, overgroup is the value of group
                        if "overgroup" not in record:
                            record["overgroup"] = record.get("group")

                        # lookup app enablement
                        wlk_disabled_apps_lookup(
                            record.get("app"),
                            apps_enablement_collection_keys,
                            apps_enablement_collection_dict,
                            record,
                        )

                        # lookup versioning
                        wlk_versioning_lookup(
                            key_value,
                            versioning_collection_keys,
                            versioning_collection_dict,
                            record,
                        )

                        # lookup orphan
                        wlk_orphan_lookup(
                            key_value,
                            orphan_collection_keys,
                            orphan_collection_dict,
                            record,
                        )

                        # Only process if needed
                        if record.get("app_is_enabled") == "False":
                            append_record = False

                        else:
                            # if mode_view is full, replace metrics with metrics_extended and remove metrics_extended
                            if mode_view == "full":
                                record["metrics"] = record.get("metrics_extended", "{}")
                            if "metrics_extended" in record:
                                del record["metrics_extended"]

                            # get outliers
                            try:
                                isOutlier = int(record.get("isOutlier", 0))
                            except:
                                isOutlier = 0

                            try:
                                OutliersDisabled = int(
                                    record.get("OutliersDisabled", 0)
                                )
                            except:
                                OutliersDisabled = 0

                            if _debug:
                                logger.debug(
                                    f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}"'
                                )

                            # get monitoring time policy and rules (new fields)
                            monitoring_time_policy = record.get("monitoring_time_policy", None)
                            # if unset yet, use the tenant level and add to the record
                            if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                                monitoring_time_policy = default_monitoring_time_policy
                                record["monitoring_time_policy"] = default_monitoring_time_policy
                            monitoring_time_rules = record.get("monitoring_time_rules", None)

                            # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                            # Falls back to legacy fields if new fields are not set
                            (
                                isUnderMonitoring,
                                monitoring_anomaly_reason,
                                isUnderMonitoringMsg,
                            ) = get_monitoring_time_status(
                                monitoring_time_policy,
                                monitoring_time_rules,
                            )

                            # call get_outliers_status and define isOutlier (with hybrid scoring)
                            # Note: score and score_outliers are already extracted from scores_dict above (lines 921-933)
                            isOutlier = get_outliers_status(
                                isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                            )
                            if _debug:
                                logger.debug(
                                    f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                                )

                            # wlk thresholds lookup
                            wlk_thresholds_lookup(
                                object_value,
                                key_value,
                                record,
                                thresholds_collection_dict,
                            )

                            # call set_wlk_status and define object_state and anomaly_reason (with hybrid scoring)
                            (
                                object_state,
                                status_message,
                                status_message_json,
                                anomaly_reason,
                            ) = set_wlk_status(
                                logger,
                                request_info.server_rest_uri,
                                request_info.system_authtoken,
                                tenant_id,
                                record,
                                isOutlier,
                                isUnderMonitoring,
                                isUnderMonitoringMsg,
                                disruption_queue_collection,
                                disruption_queue_record,
                                source_handler="rest_handler",
                                monitoring_anomaly_reason=monitoring_anomaly_reason,
                                score=score,
                                score_outliers=score_outliers,
                                vtenant_account=vtenant_conf,
                                dynamic_thresholds=record.get("dynamic_thresholds", {}),
                            )
                            if _debug:
                                logger.debug(
                                    f'instance_id={self.instance_id}, tenant_id="{tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                                )

                            # insert our main fields
                            record["object_state"] = object_state
                            record["status_message"] = " | ".join(status_message)
                            record["status_message_json"] = status_message_json
                            record["anomaly_reason"] = "|".join(anomaly_reason)

                            # generate charts resources for this entity
                            if load_charts_resources:
                                try:
                                    charts_resources = generate_charts_resources(
                                        tenant_id=tenant_id,
                                        component="wlk",
                                        object=object_value,
                                        keyid=key_value,
                                        anomaly_reason=anomaly_reason,
                                        vtenant_conf=vtenant_conf,
                                        service=service,
                                        tenant_trackme_metric_idx=tenant_trackme_metric_idx
                                    )
                                    record["charts_resources"] = charts_resources
                                except Exception as e:
                                    logger.warning(f"Failed to generate charts for WLK entity {key_value}: {str(e)}")
                                    record["charts_resources"] = []

                            # get and convert latest_flip_time from epoch
                            latest_flip_time_human = record.get("latest_flip_time", 0)
                            try:
                                latest_flip_time_human = float(latest_flip_time_human)
                            except:
                                latest_flip_time_human = 0
                            record["latest_flip_time_human"] = (
                                convert_epoch_to_datetime(latest_flip_time_human)
                            )

                            # convert last_time_seen from epoch
                            last_seen = convert_epoch_to_datetime(
                                record.get("last_seen", 0)
                            )
                            record["last_seen_human"] = last_seen

                            # Documentation note
                            docs_ref_lookup(
                                docs_is_global,
                                docs_note_global,
                                docs_link_global,
                                object_value,
                                docs_collection_members_list,
                                docs_collection_members_dict,
                                record,
                            )

                            # sla_timer
                            get_sla_timer(record, sla_classes, sla_default_class)

                if append_record:

                    #
                    # if we do not have a value for object_state or object_state is empty, define to red
                    #

                    if not record.get("object_state", None):
                        record["object_state"] = "red"

                    #
                    # per-entity maintenance override (TOP precedence) — applied
                    # as the FINAL state mutation so it wins over the computed
                    # state and every other blue/protection layer (ACK,
                    # disruption grace, logical group). Inert once the window
                    # expires.
                    #

                    maintenance_record = entity_maintenance_lookup(
                        key_value,
                        entity_maintenance_collection_keys,
                        entity_maintenance_collection_dict,
                    )
                    if maintenance_record:
                        apply_entity_maintenance_override(record, maintenance_record)
                    else:
                        # No active window — strip any stale maintenance metadata
                        # a prior (now-expired) window may have persisted.
                        clear_entity_maintenance_fields(record)

                    #
                    # state icon code
                    #

                    record["state_icon_code"] = define_state_icon_code(record)

                    #
                    # End, add to the processed_records list
                    #
                    processed_records.append(record)

                    # log debug only
                    if _debug:
                        logger.debug(f'instance_id={self.instance_id}, record="{json.dumps(record, indent=2)}"')

            #
            # End per component processing
            #

            except Exception as e:
                logger.error(
                    f'instance_id={self.instance_id}, tenant_id="{tenant_id}", component="{component}", Error processing record, record="{json.dumps(record, indent=2)}", exception="{str(e)}"'
                )
                continue  # Proceed with next record

        try:

            logger.info(
                f'instance_id={self.instance_id}, collection_name="{data_collection_name}", page="{page}", size="{size}", collection_count="{total_record_count}", last_page="{last_page}"'
            )

            filtered_records = filter_records(processed_records, query_parameters_json)
            """
            for dev debug only
            if len(filtered_records) > 0:
                for record in filtered_records[:10]:
                    logger.debug(f'record="{json.dumps(record, indent=2)}"')
            else:
                logger.debug(f"no results found")
            """

            # For replica tenants: swap tenant_id with tenant_parent so downstream
            # searches and charts reference the source tenant where metrics/events live.
            # The original replica tenant ID is preserved in tenant_replica_id.
            for record in filtered_records:
                tenant_parent = record.get("tenant_parent")
                if tenant_parent and str(tenant_parent) not in ("", "None"):
                    record["tenant_replica_id"] = record.get("tenant_id", "")
                    record["tenant_id"] = tenant_parent

            # log info
            logger.info(
                f'instance_id="{self.instance_id}", trackme_rest_handler_component_user has terminated, run_time="{round((time.time() - start), 3)}"'
            )

            if pagination_mode == "remote":
                return {
                    "payload": {
                        "last_page": last_page,
                        "data": filtered_records,
                    },
                    "status": 200,
                }
            elif pagination_mode == "local":
                return {
                    "payload": filtered_records,
                    "status": 200,
                }

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(f"instance_id={self.instance_id}, {json.dumps(response)}")
            return {"payload": response, "status": 500}

    # ─── Shadow copy availability check ───
    # Lightweight GET endpoint: checks if a shadow copy is available for a tenant/component.
    # The frontend calls this before loading data — if shadow is available, it reads
    # directly via SearchJob `| inputlookup` (~7s for 100k records). Otherwise it
    # falls back to the synchronous load_component_data endpoint.

    def get_check_shadow(self, request_info, **kwargs):
        """Check if a shadow copy is available for this tenant/component."""

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint reports whether a shadow lookup transform "
                    "is currently available for the given tenant and "
                    "component, and if so returns the lookup name the UI "
                    "should query instead of the live KV collection. Shadow "
                    "copies are a performance optimisation: when a tenant "
                    "exceeds the configured shadow_entity_threshold the "
                    "decision maker periodically writes a flat lookup that "
                    "the UI can scan in a fraction of the time of a KV-store "
                    "query. This endpoint is consulted by the entity-grid "
                    "loader on every page render to decide which data source "
                    "to pull from. Returns shadow_available=false if the "
                    "tenant is below threshold, shadow is disabled in "
                    "tenant config, or the shadow file is stale/missing."
                ),
                "resource_desc": "Report whether a shadow lookup is available for a given tenant/component pair",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/component/check_shadow?tenant_id=mytenant&component=dsm"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier. Passed as a query-string parameter",
                        "component": "REQUIRED. The component code (one of: dsm, dhm, mhm, flx, fqm, wlk). Passed as a query-string parameter",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        try:
            params_dict = request_info.raw_args.get("query_parameters", {})
        except Exception:
            params_dict = {}

        tenant_id = params_dict.get("tenant_id")
        component_name = params_dict.get("component")
        if not tenant_id or not component_name:
            return {
                "payload": {"error": "tenant_id and component are required"},
                "status": 400,
            }

        try:
            service = client.connect(
                token=request_info.system_authtoken,
                owner="nobody",
                app="trackme",
                host=request_info.server_rest_host,
                port=request_info.server_rest_port,
                timeout=120,
            )

            # Check tenant config for shadow threshold
            vtenant_conf = trackme_vtenant_account_from_service(service, tenant_id)
            shadow_threshold = int(vtenant_conf.get("shadow_entity_threshold", 1000))
            shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))

            if shadow_threshold > 0 and should_use_shadow(
                service, tenant_id, component_name, shadow_threshold, False, shadow_enabled=shadow_enabled
            ):
                shadow_transform = f"trackme_{component_name}_shadow_tenant_{tenant_id}"
                return {
                    "payload": {
                        "shadow_available": True,
                        "shadow_transform": shadow_transform,
                    },
                    "status": 200,
                }
            else:
                return {
                    "payload": {
                        "shadow_available": False,
                    },
                    "status": 200,
                }

        except Exception as e:
            logger.warning(f"Shadow check failed for tenant={tenant_id}, component={component_name}: {e}")
            return {
                "payload": {
                    "shadow_available": False,
                },
                "status": 200,
            }

    # Get the component data with pagination and progressive load capabilities
    def post_load_component_data_full(self, request_info, **kwargs):
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
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves and returns the full component data with pagination and multithreading, it calls the load_component_data endpoint accordingly, it requires a POST call using data and the following options:",
                "resource_desc": "Retrieve the full component data with pagination and multithreading",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/component/load_component_data_full\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'component': 'flx'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "component identifier, valid options are: flx, dsm, dhm, mhm, wlk, fqm",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # set loglevel - create a lightweight system service for conf read instead of full connection
        splunkd_port = request_info.server_rest_port
        service_system = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        loglevel = trackme_getloglevel_from_service(service_system)
        logger.setLevel(loglevel)

        # performance counter
        start = time.time()

        params = {
            "tenant_id": tenant_id,
            "component": component,
            "page": 1,
            "size": 0,
            "caller": "trackme_rest_handler_component_user_internal",  # Identify this as an internal REST handler call
        }

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {request_info.system_authtoken}",
            "Content-Type": "application/json",
        }

        # Add the vtenant account
        url = f"{request_info.server_rest_uri}/services/trackme/v2/component/load_component_data"

        # results_records list
        results_records = []

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
                raise Exception(msg)

            else:
                response_json = response.json()
                last_page = response_json.get("last_page", 1)
                data = response_json.get("data", [])

                # add the data to the data_records
                for record in data:
                    results_records.append(record)

                logger.info(
                    f"retrieved page 1 with {len(data)} records, last_page={last_page}"
                )

        except Exception as e:
            msg = f'get component has failed, exception="{str(e)}"'
            logger.error(msg)
            return {"payload": {"response": msg}, "status": 500}

        # run_time
        run_time = round((time.time() - start), 3)

        # return the response
        logger.info(
            f'context="perf", no_records="{len(results_records)}", run_time="{run_time}", tenant_id="{tenant_id}", component="{component}"'
        )

        return {
            "payload": {
                "data": results_records,
                "entities": len(results_records),
                "run_time": run_time,
            },
            "status": 200,
        }


def generate_dhm_summary_views(raw_summary_str):
    """
    Generate DHM sourcetype summary display views on-demand from the raw splk_dhm_st_summary.

    Only the raw splk_dhm_st_summary (JSON format) is stored in KV.
    This function generates:
    - 'minimal': green/red combo counts (used as sourcetype_summary in the API response)
    - 'full': detailed JSON with human-readable timestamps (used by frontend for combo expansion)

    Args:
        raw_summary_str: The raw splk_dhm_st_summary string (JSON or legacy Python dict format) or dict.

    Returns:
        dict with 'minimal' (JSON string) and 'full' (JSON string) keys.
    """

    result = {"minimal": "{}", "full": "{}"}

    try:
        if not raw_summary_str or raw_summary_str == "{}":
            return result

        # Parse the raw summary — try JSON first (fast), fall back to ast.literal_eval (legacy)
        if isinstance(raw_summary_str, str):
            try:
                raw_dict = json.loads(raw_summary_str)
            except (json.JSONDecodeError, ValueError):
                import ast
                raw_dict = ast.literal_eval(raw_summary_str)
        elif isinstance(raw_summary_str, dict):
            raw_dict = raw_summary_str
        else:
            return result

        count_green = 0
        count_red = 0
        full_view = {}

        def _fmt_time(epoch):
            if epoch and epoch > 0:
                return time.strftime(
                    "%d %b %Y %H:%M:%S", time.localtime(int(epoch))
                )
            return "N/A"

        for combo_id, combo_info in raw_dict.items():
            try:
                state = str(combo_info.get("state", "unknown"))
                if state == "green":
                    count_green += 1
                else:
                    count_red += 1

                # Build full view entry with human-readable timestamps
                first_time = float(combo_info.get("first_time", 0))
                last_time = float(combo_info.get("last_time", 0))
                time_measure = float(combo_info.get("time_measure", 0))
                last_ingest = float(combo_info.get("last_ingest", 0))

                full_entry = {
                    "summary_idx": str(combo_info.get("idx", "")),
                    "summary_st": str(combo_info.get("st", "")),
                    "summary_first_time": _fmt_time(first_time),
                    "summary_last_time": _fmt_time(last_time),
                    "summary_last_ingest_lag": str(
                        combo_info.get("last_ingest_lag", "0")
                    ),
                    "summary_last_event_lag": str(
                        combo_info.get("last_event_lag", "0")
                    ),
                    "summary_time_measure": _fmt_time(time_measure),
                    "summary_last_ingest": _fmt_time(last_ingest),
                    "summary_last_eventcount": str(
                        combo_info.get("last_eventcount", "0")
                    ),
                    "summary_max_lag_allowed": str(
                        combo_info.get("max_lag_allowed", "0")
                    ),
                    "summary_max_delay_allowed": str(
                        combo_info.get("max_delay_allowed", "0")
                    ),
                    "state": state,
                }
                # Extras-aware trackers (breakby_extra_fields) attach a
                # per-combo dict mapping field name → value. Surface it on
                # the full view as `summary_extras` so the entity inspector
                # modal and the UI donut charts can label each extra by its
                # source field. Empty / absent on trackers that don't opt
                # in — the existing _full view stays byte-identical.
                extras_dict = combo_info.get("extras")
                if isinstance(extras_dict, dict) and extras_dict:
                    full_entry["summary_extras"] = {
                        str(k): str(v) for k, v in extras_dict.items()
                    }
                full_view[combo_id] = full_entry
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Skipping corrupt DHM combo entry combo_id={combo_id}: {e}")
                continue

        result["minimal"] = json.dumps(
            {"green": count_green, "red": count_red}
        )
        result["full"] = json.dumps(full_view)

    except Exception as e:
        logger.warning(f"Failed to generate DHM summary views: {e}")

    return result


def get_chart_labels_and_descriptions():
    """
    Function to get chart labels and descriptions mapping
    
    Returns:
        Dictionary mapping chart types to their labels, descriptions, and chart types
    """
    return {
        "latency": {
            "label": "Event Latency",
            "description": "Event latency over time showing data ingestion delays",
            "chart_type": "line"
        },
        "delay": {
            "label": "Event Delay", 
            "description": "Event delay over time showing time between event occurrence and ingestion",
            "chart_type": "line"
        },
        "volume": {
            "label": "Event Volume",
            "description": "Event volume over time showing the number of events",
            "chart_type": "line"
        },
        "hosts_dcount": {
            "label": "Hosts Count",
            "description": "Distinct host count over time",
            "chart_type": "line"
        },
        "data_sampling_anomaly": {
            "label": "Data Sampling Anomaly",
            "description": "Data sampling model match percentage over time",
            "chart_type": "bar"
        },
        "flx_status": {
            "label": "FLX Status",
            "description": "FLX entity status over time",
            "chart_type": "line"
        },
        "incidents_events": {
            "label": "Incident Events",
            "description": "Stateful alert incidents timeline",
            "chart_type": "bar"
        },
        "flipping_events": {
            "label": "State Flipping Events",
            "description": "Entity state changes over time",
            "chart_type": "bar"
        },
        "state_events": {
            "label": "State Events",
            "description": "Entity state distribution over time",
            "chart_type": "bar"
        }
    }


def generate_charts_resources(tenant_id, component, object, keyid, anomaly_reason, vtenant_conf, service, tenant_trackme_metric_idx="trackme_metrics"):
    """
    Function to generate chart resources for an entity based on component type and anomaly reasons
    
    Args:
        tenant_id: The tenant ID
        component: The component type (dsm, dhm, mhm, flx, fqm, wlk)
        object: The object name
        keyid: The object key ID
        anomaly_reason: List of anomaly reasons
        vtenant_conf: Virtual tenant configuration
        service: Splunk service object
        
    Returns:
        List of chart dictionaries with chart_label, chart_description, and chart_search
    """
    charts = []
    chart_labels = get_chart_labels_and_descriptions()
    
    try:
        # Parse anomaly_reason if it's a string
        if isinstance(anomaly_reason, str):
            anomaly_reason = anomaly_reason.split("|") if anomaly_reason else []
        elif not isinstance(anomaly_reason, list):
            anomaly_reason = []
            
        # Normalize anomaly_reason (remove empty strings)
        anomaly_reason = [reason for reason in anomaly_reason if reason and reason.strip()]
        
        # Create object_category for chart search
        object_category = f"splk-{component}"
        
        # Check tenant-level feature enablement
        try:
            outliers_enabled = int(vtenant_conf.get(f'mloutliers_{component}', 1)) == 1
        except Exception as e:
            outliers_enabled = False
        try:
            sampling_enabled = int(vtenant_conf.get('sampling', 1)) == 1
        except Exception as e:
            sampling_enabled = False
        
        # Component-specific chart logic
        if component in ("dsm", "dhm"):
            # Always include basic charts for DSM/DHM
            for chart_type in ["latency", "delay", "volume"]:
                chart_search = get_chart_search(
                    chart_type=chart_type,
                    tenant_id=tenant_id,
                    object_category=object_category,
                    object=object,
                    keyid=keyid,
                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )
                if chart_search:
                    chart_info = chart_labels.get(chart_type, {})
                    charts.append({
                        "chart_label": chart_info.get("label", chart_type),
                        "chart_description": chart_info.get("description", f"{chart_type} chart"),
                        "chart_search": chart_search,
                        "chart_type": chart_info.get("chart_type", "line")
                    })
            
            # DSM-specific charts
            if component == "dsm":
                # hosts_dcount chart
                chart_search = get_chart_search(
                    chart_type="hosts_dcount",
                    tenant_id=tenant_id,
                    object_category=object_category,
                    object=object,
                    keyid=keyid,
                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )
                if chart_search:
                    chart_info = chart_labels.get("hosts_dcount", {})
                    charts.append({
                        "chart_label": chart_info.get("label", "Hosts Count"),
                        "chart_description": chart_info.get("description", "Distinct host count over time"),
                        "chart_search": chart_search,
                        "chart_type": chart_info.get("chart_type", "line")
                    })
                
                # data_sampling_anomaly chart (if anomaly present and sampling enabled)
                if "data_sampling_anomaly" in anomaly_reason and sampling_enabled:
                    chart_search = get_chart_search(
                        chart_type="data_sampling_anomaly",
                        tenant_id=tenant_id,
                        object_category=object_category,
                        object=object,
                        keyid=keyid,
                        tenant_trackme_metric_idx=tenant_trackme_metric_idx
                    )
                    if chart_search:
                        chart_info = chart_labels.get("data_sampling_anomaly", {})
                        charts.append({
                            "chart_label": chart_info.get("label", "Data Sampling Anomaly"),
                            "chart_description": chart_info.get("description", "Data sampling model match percentage over time"),
                            "chart_search": chart_search,
                            "chart_type": chart_info.get("chart_type", "bar")
                        })
        
        elif component == "flx":
            # FLX status chart
            chart_search = get_chart_search(
                chart_type="flx_status",
                tenant_id=tenant_id,
                object_category=object_category,
                object=object,
                keyid=keyid,
                tenant_trackme_metric_idx=tenant_trackme_metric_idx
            )
            if chart_search:
                chart_info = chart_labels.get("flx_status", {})
                charts.append({
                    "chart_label": chart_info.get("label", "FLX Status"),
                    "chart_description": chart_info.get("description", "FLX entity status over time"),
                    "chart_search": chart_search,
                    "chart_type": chart_info.get("chart_type", "line")
                })
            
            # Dynamic FLX metrics
            try:
                flx_metrics = flx_get_metrics_catalog_for_object_id(
                    None, service, tenant_id, keyid, timerange_charts="24h",
                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )
                if flx_metrics:
                    for flx_metric in flx_metrics:
                        chart_search = get_chart_search(
                            chart_type="flx_metric_group",
                            tenant_id=tenant_id,
                            object_category=object_category,
                            object=object,
                            keyid=keyid,
                            metric_list=[flx_metric],
                            tenant_trackme_metric_idx=tenant_trackme_metric_idx
                        )
                        if chart_search:
                            # Determine chart type based on metrics (bar if any metric contains "count", otherwise line)
                            chart_type = "bar" if "count" in flx_metric.lower() else "line"
                            charts.append({
                                "chart_label": f"FLX Metric: {flx_metric}",
                                "chart_description": f"FLX metrics over time for {flx_metric}",
                                "chart_search": chart_search,
                                "chart_type": chart_type
                            })
            except Exception as e:
                logger.debug(f"Failed to get FLX metrics for {keyid}: {str(e)}")
        
        elif component == "fqm":
            # Dynamic FQM metrics
            try:
                fqm_metrics = fqm_get_metrics_catalog_for_object_id(
                    None, service, tenant_id, keyid, timerange_charts="24h",
                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )
                if fqm_metrics:
                    for fqm_metric in fqm_metrics:
                        chart_search = get_chart_search(
                            chart_type="fqm_metric_group",
                            tenant_id=tenant_id,
                            object_category=object_category,
                            object=object,
                            keyid=keyid,
                            metric_list=[fqm_metric],
                            tenant_trackme_metric_idx=tenant_trackme_metric_idx
                        )
                        if chart_search:
                            # Determine chart type based on metrics (bar if any metric contains "count", otherwise line)
                            chart_type = "bar" if "count" in fqm_metric.lower() else "line"
                            charts.append({
                                "chart_label": f"FQM Metric: {fqm_metric}",
                                "chart_description": f"FQM metrics over time for {fqm_metric}",
                                "chart_search": chart_search,
                                "chart_type": chart_type
                            })
            except Exception as e:
                logger.debug(f"Failed to get FQM metrics for {keyid}: {str(e)}")
        
        elif component == "wlk":
            # Dynamic WLK metrics
            try:
                wlk_metrics = wlk_get_metrics_catalog_for_object_id(
                    None, service, tenant_id, keyid, timerange_charts="24h",
                    tenant_trackme_metric_idx=tenant_trackme_metric_idx
                )
                if wlk_metrics:
                    for wlk_metric in wlk_metrics:
                        chart_search = get_chart_search(
                            chart_type="wlk_metric_group",
                            tenant_id=tenant_id,
                            object_category=object_category,
                            object=object,
                            keyid=keyid,
                            metric_list=[wlk_metric],
                            tenant_trackme_metric_idx=tenant_trackme_metric_idx
                        )
                        if chart_search:
                            # Determine chart type based on metrics (bar if any metric contains "count", otherwise line)
                            chart_type = "bar" if "count" in wlk_metric.lower() else "line"
                            charts.append({
                                "chart_label": f"WLK Metric: {wlk_metric}",
                                "chart_description": f"WLK metrics over time for {wlk_metric}",
                                "chart_search": chart_search,
                                "chart_type": chart_type
                            })
            except Exception as e:
                logger.debug(f"Failed to get WLK metrics for {keyid}: {str(e)}")
        
        # ML Outliers charts (for applicable components)
        if component in ("dsm", "dhm", "flx", "fqm", "wlk") and outliers_enabled:
            logger.debug(f'handling mloutliers_detection for {component} entity {keyid}, outliers_enabled={outliers_enabled}')
            try:
                class _HelperAdapter:
                    def __init__(self, base_logger):
                        self._logger = base_logger
                    def log_debug(self, message):
                        self._logger.debug(message)
                    def log_info(self, message):
                        self._logger.info(message)
                    def log_error(self, message):
                        self._logger.error(message)

                helper_adapter = _HelperAdapter(logger)

                ml_models = get_mlmodels_from_kvstore(
                    helper_adapter, service, tenant_id, component, object, keyid
                )
                if ml_models:
                    for model_id in ml_models:
                        chart_search = get_chart_search(
                            chart_type="ml_outliers",
                            tenant_id=tenant_id,
                            object_category=object_category,
                            object=object,
                            keyid=keyid,
                            model_id=model_id,
                            tenant_trackme_metric_idx=tenant_trackme_metric_idx
                        )
                        if chart_search:
                            charts.append({
                                "chart_label": f"ML Outliers: {model_id}",
                                "chart_description": f"Machine learning outliers detection for model {model_id}",
                                "chart_search": chart_search,
                                "chart_type": "line"
                            })
            except Exception as e:
                logger.error(f"Failed to get ML models for {keyid}: {str(e)}")
        
        # Common charts for all components
        for chart_type in ["incidents_events", "flipping_events", "state_events"]:
            chart_search = get_chart_search(
                chart_type=chart_type,
                tenant_id=tenant_id,
                object_category=object_category,
                object=object,
                keyid=keyid,
                tenant_trackme_metric_idx=tenant_trackme_metric_idx
            )
            if chart_search:
                chart_info = chart_labels.get(chart_type, {})
                charts.append({
                    "chart_label": chart_info.get("label", chart_type),
                    "chart_description": chart_info.get("description", f"{chart_type} chart"),
                    "chart_search": chart_search,
                    "chart_type": chart_info.get("chart_type", "line")
                })
        
    except Exception as e:
        logger.error(f"Error generating charts for {component} entity {keyid}: {str(e)}")
        # Return empty list on error to not break the main response
        return []
    
    return charts
