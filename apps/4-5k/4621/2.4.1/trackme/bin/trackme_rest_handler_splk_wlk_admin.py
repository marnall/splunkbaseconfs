#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_dsm.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import uuid
import hashlib
import json

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_wlk_admin",
    "trackme_rest_api_splk_wlk_admin.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_audit_event,
    trackme_create_report,
    trackme_delete_tenant_object_summary,
    trackme_getloglevel,
    trackme_idx_for_tenant,
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_send_to_tcm,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, sanitize_spl_input

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkWlkAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkWlkAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_wlk(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_wlk/admin",
            "resource_group_desc": "Endpoints specific to the splk-wlk TrackMe component (Splunk Workload, admin operations)",
        }

        return {"payload": response, "status": 200}

    # Return and execute simulation searches
    def post_wlk_tracker_simulation(self, request_info, **kwargs):
        # init
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # run simulation
                try:
                    run_simulation = resp_dict["run_simulation"]
                    if run_simulation in ("true", "false"):
                        if run_simulation == "true":
                            run_simulation = True
                        elif run_simulation == "false":
                            run_simulation = False
                except Exception as e:
                    run_simulation = True

                # tracker type: valid options are: introspection, scheduler, splunkcloud_svc
                tracker_type = resp_dict["tracker_type"]

                if tracker_type not in (
                    "introspection",
                    "scheduler",
                    "splunkcloud_svc",
                    "notable",
                ):
                    logger.error(
                        f'invalid tracker_type="{tracker_type}", valid options are: main, introspection, scheduler, splunkcloud_svc, notable'
                    )
                    return {
                        "payload": f'invalid tracker_type="{tracker_type}", valid options are: main, introspection, scheduler, splunkcloud_svc, notable',
                        "status": 500,
                    }

                # tracker_name
                # include a random UUID
                tracker_name = str(tracker_type) + "_" + uuid.uuid4().hex[:15]
                # report name len is 100 chars max, as we include a prefix and suffix, limit to 50 chars here
                tracker_type = tracker_type[:50]

                # tenant
                tenant_id = resp_dict["tenant_id"]

                # get account
                account = resp_dict["account"]

                #
                # optional args
                #

                try:
                    root_constraint = sanitize_spl_input(resp_dict["root_constraint"])
                except Exception as e:
                    root_constraint = "(host=* splunk_server=*)"

                # define time quantifiers
                if tracker_type in ("scheduler", "introspection"):
                    earliest_time = "-20m"
                    latest_time = "now"

                elif tracker_type in ("splunkcloud_svc"):
                    earliest_time = "-3h"
                    latest_time = "now"

                elif tracker_type in ("notable"):
                    earliest_time = "-24h"
                    latest_time = "now"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns and executes simulation searches, it requires a POST call with the following information:",
                "resource_desc": "Return and execute hybrid tracker search for simulation purposes",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_wlk/admin/wlk_tracker_simulation\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'component': 'wlk', 'account': 'local', 'tracker_type': 'introspection', 'earliest_time': '-5m', 'latest_time': 'now'}",
                "options": [
                    {
                        "run_simulation": "Optional, Execute the simulation search or simply return the search syntax and other information, valid options are: true | false (default to true)",
                        "tracker_type": "The type of tracker to be simulated, valid options are: introspection, scheduler, splunkcloud_svc, notable",
                        "account": "Splunk deployment, either local or a configured remote account",
                        "root_constraint": "An optional search filter, defaults to (host=* splunk_server=*)",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # proceed
        try:
            # init
            response = {
                "run_simulation": run_simulation,
                "tracker_type": tracker_type,
                "account": account,
                "root_constraint": root_constraint,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
            }

            # Define the search
            if tracker_type == "introspection":
                tracker_search = f"""\
                    (index=_introspection sourcetype=splunk_resource_usage) component=PerProcess data.process_type="search" data.search_props.user="*" data.search_props.app="*" data.search_props.label="*" {root_constraint}
                    | bucket _time span=1m
                    | stats sum(data.pct_cpu) as pct_cpu sum(data.pct_memory) as pct_memory, sum(data.fd_used) as fd_used, sum(data.page_faults) as page_faults, sum(data.read_mb) as read_mb, sum(data.written_mb) as written_mb latest(data.elapsed) as elapsed, latest("data.search_props.*") as "data.search_props.*" by _time, data.pid, data.process, data.process_type
                    | rename data.search_props.app as app, data.search_props.user as user, data.search_props.type as type, data.pid as pid
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    | eval object = app . ":" . user . ":" . 'data.search_props.label', savedsearch_name = 'data.search_props.label'
                    | stats max(_time) as last_time, avg(elapsed) as elapsed, avg(pct_cpu) as pct_cpu, avg(pct_memory) as pct_memory, sum(data.search_props.scan_count) as scan_count, latest(type) as type, latest(user) as user by object, app, savedsearch_name
                    | eval group = app
                    | eval pct_cpu=if(isnum(pct_cpu), round(pct_cpu, 5), 0), elapsed=if(isnum(elapsed), round(elapsed, 3), 0), pct_memory=if(isnum(pct_memory), round(pct_memory, 3), 0), scan_count=if(isnum(scan_count), round(scan_count, 0), 0)
                    | fields object app savedsearch_name last_time elapsed pct_cpu pct_memory scan_count type user group
                    """

            elif tracker_type == "scheduler":
                tracker_search = f"""\
                    (index=_internal sourcetype=scheduler)
                    | eval alert_actions=if((isnull(alert_actions) OR (alert_actions == "")), "none", alert_actions)
                    ``` in some error cases, we need to manage extractions and status ```
                    | rex field=savedsearch_id "^(?<user>[^\\;]*)\\;(?<app>[^\\;]*)\\;(?<savedsearch_name>.*)"
                    | eval user=coalesce(user, user_alt), app=coalesce(app, app_alt), savedsearch_name=coalesce(savedsearch_name, savedsearch_name_alt)
                    | search {root_constraint}
                    | eval errmsg=case(len(errmsg)>0, errmsg, match(log_level, "(?i)error") AND len(message)>0, message)                    
                    | eval status=case(((status == "success") OR (status == "completed")),"completed",(status == "skipped"),"skipped",(status == "continued"),"deferred",len(errmsg)>0 OR status == "delegated_remote_error","error")
                    | search (status="completed" OR status="deferred" OR status="skipped" OR status="error")
                    | stats count(eval(status=="completed")) as count_completed, count(eval(status=="skipped")) as count_skipped, count(eval(status=="error")) as count_errors, count as count_execution by app, user, savedsearch_name
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    """

            elif tracker_type == "notable":
                tracker_search = f"""\
                    | tstats count as count_ess_notable where index=notable source="*Rule" by source
                    | rename source as savedsearch_name
                    """

            elif tracker_type == "splunkcloud_svc":
                tracker_search = f"""\
                    ((index=_cmc_summary OR index=summary) source="splunk-svc-search-attribution") (search_type!="ad-hoc") svc_usage=* svc_consumer=search search_label=* {root_constraint}
                    | fields _time svc_usage svc_consumer svc_consumption_score search_type search_app search_label search_user search_head_names unified_sid process_type
                    | fillnull value="" svc_consumer process_type search_provenances search_type search_app search_label search_user unified_sid search_modes labels search_head_names usage_source
                    | stats max(svc_usage) as svc_usage by _time svc_consumer search_type search_app search_label search_user search_head_names unified_sid process_type
                    | stats sum(svc_usage) as svc_usage by _time, search_app, search_label, search_user
                    | rename search_label as savedsearch_name, search_app as app, search_user as user
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    | eval object = app . ":" . user . ":" . savedsearch_name, object_id=sha256(object)
                    | eval group = app
                    | fields app,group,object,savedsearch_name,user,svc_usage
                    """

            # If account is remote, does not apply to the main tracker which always look at locally generated metrics
            if account != "local" and tracker_type != "main":
                tracker_search = tracker_search.replace('"', '\\"')
                tracker_search = remove_leading_spaces(tracker_search)
                tracker_search = f"""\
                    | splunkremotesearch account="{account}" search="{tracker_search}" earliest="{earliest_time}" latest="{latest_time}"
                    tenant_id="{tenant_id}" register_component="False" component="splk-wlk" report="trackme_wlk_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
                    """
            logger.info("tracker_search={}" + tracker_search)

            # finish the search
            if tracker_type == "introspection":
                tracker_search = f""" \
                    {tracker_search}
                    | trackmegenjsonmetrics fields="avg_pct_cpu,avg_pct_memory,avg_elapsed,avg_scan_count"
                    | eval tracker_type = "{tracker_type}"
                    | trackmesplkwlkparse tenant_id="{tenant_id}" context="simulation"
                    """

            elif tracker_type == "scheduler":
                tracker_search = f"""\
                    {tracker_search}
                    ``` In some circumstances, the scheduler logs may lack a user and app context which could lead to the creation of new entities in case of execution errors ```
                    ``` Althrough the following can potentially be wrong, in a majority of use cases, we can lookup the collection and use already known user and app context as a last chance choice ```
                    ``` This needs to happen at the last step of the tracker execution to handle remote executions ```
                    | lookup trackme_wlk_tenant_{tenant_id} savedsearch_name OUTPUT app as collection_app, user as collection_user
                    | foreach collection_user, collection_app [ eval <<FIELD>> = mvindex('<<FIELD>>', 0) ]
                    | foreach user, app [ eval <<FIELD>> = if(user=="system" AND isnotnull(collection_user) AND user!=collection_user, collection_<<FIELD>>, <<FIELD>>) ]
                    | fields - collection_app, collection_user
                    ``` perform a second verification for the user owner, dynamically query the owner from the savedsearch_name if still unknown ```
                    | trackmesplkwlkgetreportowner account="{account}"
                    | eval object = app . ":" . user . ":" . savedsearch_name, object_id=sha256(object)
                    | eval group = app                    
                    ``` finalize ```
                    | trackmegenjsonmetrics fields="count_completed,count_execution,count_skipped,count_errors"
                    | eval tracker_type = "{tracker_type}"
                    | trackmesplkwlkparse tenant_id="{tenant_id}" context="simulation"
                """

            elif tracker_type == "notable":
                tracker_search = f"""\
                    {tracker_search}
                    ``` Lookup app and user from savedsearch_name ```
                    | lookup trackme_wlk_tenant_{tenant_id} savedsearch_name OUTPUT object, app, user, group
                    | where isnotnull(object)
                    ``` ensure we always have a single value, if we have multiple entries for the same search, we could end up with mv fields ```
                    | foreach object, app, user, group [ eval <<FIELD>> = mvindex('<<FIELD>>', 0) ]
                    | fields app, user, savedsearch_name, count_ess_notable, group, object, object_id
                    | trackmegenjsonmetrics fields="count_ess_notable"
                    | eval tracker_type = "{tracker_type}"
                    | trackmesplkwlkparse tenant_id="{tenant_id}" context="simulation"
                """

            elif tracker_type == "splunkcloud_svc":
                tracker_search = f"""\
                    {tracker_search}
                    | trackmegenjsonmetrics fields="avg_svc_usage"
                    | eval tracker_type = "{tracker_type}"
                    | trackmesplkwlkparse tenant_id="{tenant_id}" context="simulation"
                """

            # add to response
            response["tracker_simulation_search"] = remove_leading_spaces(
                tracker_search
            )

            # render response
            return {"payload": response, "status": 200}

        except Exception as e:
            # render response
            msg = f'An exception was encountered while processing hybrid tracker simulation, exception="{str(e)}"'
            logger.error(msg)
            return {
                "payload": {
                    "action": "failure",
                    "response": msg,
                },
                "status": 500,
            }

    # Create a wlk tracker
    def post_wlk_tracker_create(self, request_info, **kwargs):
        # args
        account = None
        tenant_id = None
        tracker_type = None
        tracker_name = None
        root_constraint = None
        overgroup = None
        owner = None
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            # gets args
            if not describe:
                #
                # mandatory args
                #

                # tenant
                tenant_id = resp_dict["tenant_id"]

                # component
                component = "wlk"

                # remote account
                account = resp_dict["account"]

                # overgroup, optional
                overgroup = resp_dict.get("overgroup", None)
                # if overgroup equals to app which is the default set by the UI, we do not need to define it
                if overgroup == "app":
                    overgroup = None

                # tracker type: valid options are: introspection, scheduler, metadata
                tracker_type = resp_dict["tracker_type"]

                if tracker_type not in (
                    "main",
                    "introspection",
                    "scheduler",
                    "metadata",
                    "orphan",
                    "inactive_entities",
                    "splunkcloud_svc",
                    "notable",
                ):
                    logger.error(
                        f'invalid tracker_type="{tracker_type}", valid options are: main, introspection, scheduler, metadata, orphan, inactive_entities, splunkcloud_svc'
                    )
                    return {
                        "payload": f'invalid tracker_type="{tracker_type}", valid options are: main, introspection, scheduler, metadata, orphan, inactive_entities, splunkcloud_svc',
                        "status": 500,
                    }

                # tracker_name
                # include a random UUID
                tracker_name = str(tracker_type) + "_" + uuid.uuid4().hex[:15]
                # report name len is 100 chars max, as we include a prefix and suffix, limit to 50 chars here
                tracker_type = tracker_type[:50]

                #
                # optional args
                #

                try:
                    environment_type = resp_dict["environment_type"]
                except Exception as e:
                    environment_type = "splunk_enterprise"

                try:
                    root_constraint = sanitize_spl_input(resp_dict["root_constraint"])
                except Exception as e:
                    root_constraint = "(host=* splunk_server=*)"

                try:
                    owner = resp_dict["owner"]
                except Exception as e:
                    owner = None

                try:
                    inactive_entities_max_age_days = resp_dict[
                        "inactive_entities_max_age_days"
                    ]
                except Exception as e:
                    inactive_entities_max_age_days = "7"

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

                # Optional: burn_test, temporary create the abstract, perform a burn test, report the run time performance, delete and report
                try:
                    burn_test = resp_dict["burn_test"]
                    if burn_test == "True":
                        burn_test = True
                    elif burn_test == "False":
                        burn_test = False
                except Exception as e:
                    burn_test = False

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating an hybrid tracker for the Splunk Workload component, it requires a POST call with the following information:",
                "resource_desc": "Create a new Hybrid tracker",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_wlk/admin/wlk_tracker_create\" body=\"{'tenant_id': 'mytenant', 'account': 'local', 'tracker_type': 'introspection'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_type": "The type of tracker to be created, valid options are: main, introspection, scheduler, metadata, orphan, inactive_entities, splunkcloud_svc, notable",
                        "environment_type": "The type of Splunk environment, valid options are: splunk_enterprise | splunk_cloud",
                        "account": "name of remote Splunk deployment account as configured in TrackMe",
                        "root_constraint": "An optional search filter, defaults to (host=* splunk_server=*), relevant for introspection and scheduler trackers",
                        "inactive_entities_max_age_days": "relevant for the inactive_entities tracker, the max days before an inactive entity will be purged",
                        "overgroup": "Optional, the overgroup can be used to override grouping entities by application",
                        "owner": "Optional, the Splunk user owning the objects to be created, defaults to the owner set for the tenant",
                        "burn_test": "Optional, create the abstract report, run a performance test, delete the report and report the performance results, valid options are: True | False (default: False)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # run creation
        else:
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

            # get TrackMe conf
            trackme_conf = trackme_reqinfo(
                request_info.system_authtoken, request_info.server_rest_uri
            )
            logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')

            # TrackMe sharing level
            trackme_default_sharing = trackme_conf["trackme_conf"]["trackme_general"][
                "trackme_default_sharing"
            ]

            # Retrieve the virtual tenant record to access acl
            collection_vtenants_name = "kv_trackme_virtual_tenants"
            collection_vtenants = service.kvstore[collection_vtenants_name]

            # Define the KV query search string
            query_string = {
                "tenant_id": tenant_id,
            }

            # Get the tenant
            try:
                vtenant_record = collection_vtenants.data.query(
                    query=json.dumps(query_string)
                )[0]
                vtenant_key = vtenant_record.get("_key")

            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", failed to retrieve the tenant record, exception="{str(e)}"'
                )
                return {
                    "payload": f'tenant_id="{tenant_id}", failed to retrieve the tenant record, exception="{str(e)}"',
                    "status": 500,
                }

            # check license state
            try:
                check_license = trackme_check_license(
                    request_info.server_rest_uri,
                    request_info.session_key,
                    request_info.system_authtoken,
                )
                license_is_valid = check_license.get("license_is_valid")
                license_subscription_class = check_license.get("license_subscription_class")
                license_read_only = check_license.get("license_read_only", False)
                license_active_wlk_trackers = int(
                    check_license.get("license_active_wlk_trackers")
                )
                logger.debug(
                    f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
                )

            except Exception as e:
                license_is_valid = 0
                license_subscription_class = "free"
                license_read_only = False
                license_active_wlk_trackers = 16
                logger.error(f'function check_license exception="{str(e)}"')

            if license_read_only:
                return {
                    "payload": "I'm afraid I can't do that, this instance is currently in read-only mode and cannot create new trackers.",
                    "status": 402,
                }

            if license_subscription_class == "foundation":
                audit_record = {
                    "action": "failure",
                    "change_type": "add new WLK tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, the Foundation edition does not allow creating WLK trackers.",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            if license_active_wlk_trackers >= 16 and (
                license_is_valid != 1 or license_subscription_class == "foundation"
            ):
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new WLK tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, the maximum number of 16 allowed trackers has been reached, there are {license_active_wlk_trackers} active trackers currently for this component",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            # verify the owner
            if not owner:
                owner = vtenant_record.get("tenant_owner")

            # check if TCM is enabled in receiver mode
            enable_conf_manager_receiver = int(
                trackme_conf["trackme_conf"]["trackme_general"][
                    "enable_conf_manager_receiver"
                ]
            )

            if enable_conf_manager_receiver == 1:
                try:
                    tcm_response = trackme_send_to_tcm(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        resp_dict,
                        "post",
                        "/services/trackme/v2/splk_wlk/admin/wlk_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            #
            # step 1: define the search
            #

            # define time quantifiers and cron schedule
            if tracker_type in ("main"):
                # run every 5 minutes over last 24h (super mstats fast search) - main does not use indexed time quantifiers
                cron_schedule = "*/5 * * * *"
                earliest_time = "-24h"
                latest_time = "now"

            elif tracker_type in ("scheduler", "introspection", "notable"):
                # run every 5 minutes over last 20 minutes and 20 minutes of indexed data with builtin dedup
                cron_schedule = "*/5 * * * *"
                earliest_time = "-20m"
                latest_time = "now"
                index_earliest_time = "-20m"
                index_latest_time = "now"

            elif tracker_type in ("metadata"):
                # run every 30 minutes, other time quantifiers are not relevant here
                cron_schedule = "*/15 * * * *"
                earliest_time = "-5m"
                latest_time = "now"

            elif tracker_type in ("orphan"):
                # run every 15 minutes, other time quantifiers are not relevant here
                cron_schedule = "*/15 * * * *"
                earliest_time = "-5m"
                latest_time = "now"

            elif tracker_type in ("inactive_entities"):
                # run every 60 minutes, other time quantifiers are not relevant here
                cron_schedule = "*/60 * * * *"
                earliest_time = "-5m"
                latest_time = "now"

            elif tracker_type in ("splunkcloud_svc"):
                # run every 15 minutes over last 3 hours and 3 hours of indexed data
                cron_schedule = "*/15 * * * *"
                earliest_time = "-3h"
                latest_time = "now"
                index_earliest_time = "-3h"
                index_latest_time = "now"

            # Define the search
            if tracker_type == "main":
                tenant_id_str = str(tenant_id)

                # Resolve metric index for this tenant
                tenant_indexes = trackme_idx_for_tenant(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                )
                tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

                trackme_metrics_idx = f'index="{tenant_trackme_metric_idx}"'
                tenant_id_clause = f'tenant_id="{tenant_id_str}"'

                # init the mstats search string
                mstats_searchstring = f"""\
                    | mstats sum(trackme.splk.wlk.count_completed) as count_completed, sum(trackme.splk.wlk.count_execution) as count_execution,
                    sum(trackme.splk.wlk.count_skipped) as count_skipped, sum(trackme.splk.wlk.count_errors) as count_errors, avg(trackme.splk.wlk.elapsed) as avg_elapsed,
                    avg(trackme.splk.wlk.pct_cpu) as avg_pct_cpu, avg(trackme.splk.wlk.pct_memory) as avg_pct_memory, avg(trackme.splk.wlk.scan_count) as avg_scan_count,
                    sum(trackme.splk.wlk.count_ess_notable) as count_ess_notable
                    """

                # handle Splunk Cloud SVC
                if environment_type == "splunk_cloud":
                    mstats_searchstring = f"{mstats_searchstring}, avg(trackme.splk.wlk.svc_usage) as avg_svc_usage"

                # breakby statement
                breakby_statement = None
                if overgroup:
                    breakby_statement = "tenant_id, object_category, account, overgroup, app, user, object_id, object, savedsearch_name"
                else:
                    breakby_statement = "tenant_id, object_category, account, app, user, object_id, object, savedsearch_name"

                # set the final search
                tracker_search = f"""\
                    {mstats_searchstring}
                    where {trackme_metrics_idx} {tenant_id_clause} object_category="splk-wlk" object="*" earliest="-24h" latest="now" by {breakby_statement}
                    | join type=outer object_id [ | mstats count where {trackme_metrics_idx} {tenant_id_clause} object_category="splk-wlk" object_id=* (metric_name=trackme.splk.wlk.count_execution OR metric_name=trackme.splk.wlk.count_errors) earliest="-24h" latest="now" by tenant_id, object_id span=1m
                    | stats max(_time) as last_seen by object_id ]
                    | where (count_execution>0 OR count_errors>0)
                    ``` rename according to the time period ```
                    | foreach count_completed,count_execution,count_skipped,count_errors,avg_elapsed,avg_pct_cpu,avg_pct_memory,avg_scan_count,skipped_pct,count_ess_notable,avg_svc_usage [ rename <<FIELD>> as <<FIELD>>_last_24h ]
                    ``` get and join metrics from past 4 hours ```
                    | join {breakby_statement} type=outer [ 
                    {mstats_searchstring}
                    where {trackme_metrics_idx} {tenant_id_clause} object_category="splk-wlk" object="*" earliest="-4h" latest="now"  by {breakby_statement}
                    | where (count_execution>0 OR count_errors>0)
                    ``` rename according to the time period ```
                    | foreach count_completed,count_execution,count_skipped,count_errors,avg_elapsed,avg_pct_cpu,avg_pct_memory,avg_scan_count,skipped_pct,count_ess_notable,avg_svc_usage [ rename <<FIELD>> as <<FIELD>>_last_4h ]
                    ]
                    ``` get and join metrics from past hour ```
                    | join {breakby_statement} type=outer [ 
                    {mstats_searchstring}
                    where {trackme_metrics_idx} {tenant_id_clause} object_category="splk-wlk" object="*" earliest="-1h" latest="now"  by {breakby_statement}
                    | where (count_execution>0 OR count_errors>0)
                    ``` rename according to the time period ```
                    | foreach count_completed,count_execution,count_skipped,count_errors,avg_elapsed,avg_pct_cpu,avg_pct_memory,avg_scan_count,skipped_pct,count_ess_notable,avg_svc_usage [ rename <<FIELD>> as <<FIELD>>_last_60m ]
                    ]
                    ``` Call the metric eval logic ```
                    | `trackme_wlk_eval_metrics_v2`
                    ``` Call the tenant specific set status macro ```
                    | `trackme_wlk_set_status_tenant_{tenant_id}`
                    ``` grouping definition ```
                    | eval group = app
                    ``` Generate the metrics JSON objects - keep metrics as the last 24 metrics```
                    | trackmegenjsonmetrics fields="count_completed_last_24h,count_execution_last_24h,count_skipped_last_24h,count_errors_last_24h,avg_elapsed_last_24h,avg_pct_cpu_last_24h,avg_pct_memory_last_24h,avg_scan_count_last_24h,skipped_pct_last_24h,count_ess_notable_last_24h,avg_svc_usage_last_24h" target="metrics" suppress_suffix="last_24h"
                    | trackmegenjsonmetrics fields="count_completed_last_24h,count_execution_last_24h,count_skipped_last_24h,count_errors_last_24h,avg_elapsed_last_24h,avg_pct_cpu_last_24h,avg_pct_memory_last_24h,avg_scan_count_last_24h,skipped_pct_last_24h,count_ess_notable_last_24h,avg_svc_usage_last_24h" add_root_label="last_24h" target="metrics_last_24h"
                    | trackmegenjsonmetrics fields="count_completed_last_4h,count_execution_last_4h,count_skipped_last_4h,count_errors_last_4h,avg_elapsed_last_4h,avg_pct_cpu_last_4h,avg_pct_memory_last_4h,avg_scan_count_last_4h,skipped_pct_last_4h,count_ess_notable_last_4h,avg_svc_usage_last_4h" add_root_label="last_4h" target="metrics_last_4h"
                    | trackmegenjsonmetrics fields="count_completed_last_60m,count_execution_last_60m,count_skipped_last_60m,count_errors_last_60m,avg_elapsed_last_60m,avg_pct_cpu_last_60m,avg_pct_memory_last_60m,avg_scan_count_last_60m,skipped_pct_last_60m,count_ess_notable_last_60m,avg_svc_usage_last_60m" add_root_label="last_60m" target="metrics_last_60m"
                    ``` If we have no activity for that period ```
                    | `trackme_wlk_null_metrics_json`
                    ``` make all that pretty ```
                    | trackmeprettyjson fields="metrics" remove_nonpositive_num="True" remove_null="True"
                    | trackmeprettyjson fields="metrics_last_24h,metrics_last_4h,metrics_last_60m" remove_nonpositive_num="True" remove_null="True" merge="True" merge_field_target="metrics_extended"
                    ``` finalize ```
                    | fields tenant_id, object_category, account, object_id, object, savedsearch_name, app, user, overgroup, group, status, status_description, metrics*, last_seen, *
                    ``` handle outliers ```
                    | `trackme_wlk_set_outliers_metrics_tenant_{tenant_id}`
                    | trackmesplkoutlierssetrules tenant_id="{tenant_id}" component="wlk"
                    """

            elif tracker_type == "introspection":
                tracker_search = f"""\
                    (index=_introspection sourcetype=splunk_resource_usage) component=PerProcess data.process_type="search" data.search_props.user="*" data.search_props.app="*" data.search_props.label="*" {root_constraint} _index_earliest="{index_earliest_time}" _index_latest="{index_latest_time}"
                    | bucket _time span=1m
                    | stats sum(data.pct_cpu) as pct_cpu sum(data.pct_memory) as pct_memory, sum(data.fd_used) as fd_used, sum(data.page_faults) as page_faults, sum(data.read_mb) as read_mb, sum(data.written_mb) as written_mb latest(data.elapsed) as elapsed, latest("data.search_props.*") as "data.search_props.*" by _time, data.pid, data.process, data.process_type
                    | rename data.search_props.app as app, data.search_props.user as user, data.search_props.type as type, data.pid as pid
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    | eval object = app . ":" . user . ":" . 'data.search_props.label', savedsearch_name = 'data.search_props.label'
                    | eval orig_time=_time | bucket orig_time span=5m
                    | stats max(_time) as _time, avg(elapsed) as elapsed, avg(pct_cpu) as pct_cpu, avg(pct_memory) as pct_memory, sum(data.search_props.scan_count) as scan_count, latest(type) as type, latest(user) as user by orig_time, object, app, savedsearch_name
                    | eval group = app
                    | eval pct_cpu=if(isnum(pct_cpu), round(pct_cpu, 5), 0), elapsed=if(isnum(elapsed), round(elapsed, 3), 0), pct_memory=if(isnum(pct_memory), round(pct_memory, 3), 0), scan_count=if(isnum(scan_count), round(scan_count, 0), 0)
                    | eval object_id=sha256(object)
                    | fields _time, object, object_id, app, savedsearch_name, last_seen, elapsed, pct_cpu, pct_memory, scan_count, type, user, group
                    """

            elif tracker_type == "scheduler":
                tracker_search = f"""\
                    (index=_internal sourcetype=scheduler) _index_earliest="{index_earliest_time}" _index_latest="{index_latest_time}"
                    | eval orig_time=_time | bucket _time span=5m
                    | eval alert_actions=if((isnull(alert_actions) OR (alert_actions == "")), "none", alert_actions)
                    ``` in some error cases, we need to manage extractions and status ```
                    | rex field=savedsearch_id "^(?<user_alt>[^\\;]*)\\;(?<app_alt>[^\\;]*)\\;(?<savedsearch_name_alt>.*)"
                    | eval user=coalesce(user, user_alt), app=coalesce(app, app_alt), savedsearch_name=coalesce(savedsearch_name, savedsearch_name_alt)
                    | search {root_constraint}
                    | eval errmsg=case(len(errmsg)>0, errmsg, match(log_level, "(?i)error") AND len(message)>0, message)
                    | eval status=case(((status == "success") OR (status == "completed")),"completed",(status == "skipped"),"skipped",(status == "continued"),"deferred",len(errmsg)>0 OR status == "delegated_remote_error","error")
                    | search (status="completed" OR status="deferred" OR status="skipped" OR status="error")
                    | stats max(_time) as _time, count(eval(status=="completed")) as count_completed, count(eval(status=="skipped")) as count_skipped, count(eval(status=="error")) as count_errors, count as count_execution by orig_time, app, user, savedsearch_name
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    """

            elif tracker_type == "notable":
                tracker_search = f"""\
                    | tstats count as count_ess_notable where index=notable source="*Rule" _index_earliest="{index_earliest_time}" _index_latest="{index_latest_time}" by _time, source span=5m
                    | rename source as savedsearch_name
                    """

            elif tracker_type == "splunkcloud_svc":
                tracker_search = f"""\
                    ((index=_cmc_summary OR index=summary) source="splunk-svc-search-attribution") (search_type!="ad-hoc") svc_usage=* svc_consumer=search search_label=* {root_constraint} _index_earliest="{index_earliest_time}" _index_latest="{index_latest_time}"
                    | fields _time svc_usage svc_consumer svc_consumption_score search_type search_app search_label search_user search_head_names unified_sid process_type
                    | fillnull value="" svc_consumer process_type search_provenances search_type search_app search_label search_user unified_sid search_modes labels search_head_names usage_source
                    | stats max(svc_usage) as svc_usage by _time svc_consumer search_type search_app search_label search_user search_head_names unified_sid process_type
                    | stats sum(svc_usage) as svc_usage by _time, search_app, search_label, search_user
                    | rename search_label as savedsearch_name, search_app as app, search_user as user
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    | eval object = app . ":" . user . ":" . savedsearch_name, object_id=sha256(object)
                    | eval group = app
                    | fields _time, app, group, object, object_id, savedsearch_name, user, svc_usage
                    """

            elif tracker_type == "metadata":
                tracker_search = f"""\
                    | inputlookup trackme_wlk_tenant_{tenant_id} | eval object_id=_key | where NOT match(object, "_ACCELERATE") | where last_seen>=relative_time(now(), "-90m")
                    | fields tenant_id, account, app, user, savedsearch_name, object, object_id, metrics
                    | lookup local=t trackme_wlk_apps_enablement_tenant_{tenant_id} app OUTPUT enabled as app_is_enabled | where NOT app_is_enabled="False"
                    ``` order by date of last inspection ```
                    | lookup trackme_wlk_versioning_tenant_{tenant_id} _key as object_id OUTPUT mtime as last_inspection | fillnull value=0 last_inspection
                    | sort limit=0 last_inspection
                    ``` Call the inspector backend ```
                    | trackmesplkwlkgetreportsdefstream tenant_id="{tenant_id}" context="live" register_component="True" report="trackme_wlk_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}" max_runtime_sec="900" filters_get_last_updates="host=*"
                    | where json_data!="None"
                    ``` you can uncomment the next command for troubleshooting and investigation purposes, it is otherwise not required for the processing purposes ```
                    ```| trackmeprettyjson fields="json_data"```
                    """

            elif tracker_type == "orphan":
                tracker_search = f"""\
                    | rest timeout=1800 splunk_server=local /servicesNS/-/-/saved/searches add_orphan_field=yes count=0 
                    | rename title as object, eai:acl.owner AS user, eai:acl.app AS app
                    | fields object, user, app, orphan
                    | eval mtime=now()
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    | eval object = app . ":" . user . ":" . object, key=sha256(object)
                    | table key, object, app, user, mtime, orphan
                    """

                if account != "local":
                    tracker_search = tracker_search.replace('"', '\\"')
                    tracker_search = f"""\
                        | splunkremotesearch account="{account}" search="{tracker_search}"
                        earliest="{earliest_time}" latest="{latest_time}"
                        tenant_id="{tenant_id}" register_component="True"
                        component="splk-wlk" report="trackme_wlk_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
                        | table key, object, app, user, mtime, orphan
                        | outputlookup trackme_wlk_orphan_status_tenant_{tenant_id} append=t key_field=key
                        """
                else:
                    tracker_search = f"""\
                        {tracker_search}
                        | outputlookup trackme_wlk_orphan_status_tenant_{tenant_id} append=t key_field=key
                        """

            elif tracker_type == "inactive_entities":
                tracker_search = f"""\
                    | trackmesplkwlkinactiveinspector tenant_id="{tenant_id}" max_days_since_inactivity="{inactive_entities_max_age_days}"
                    """

            # If account is remote, does not apply to the main tracker which always look at locally generated metrics, as well as the versioning tracker
            if account != "local" and not tracker_type in (
                "main",
                "metadata",
                "orphan",
                "inactive_entities",
            ):
                # manage remote call
                tracker_search = tracker_search.replace('"', '\\"')
                tracker_search = remove_leading_spaces(tracker_search)
                tracker_search = f"""\
                    | splunkremotesearch account="{account}" search="{tracker_search}"
                    earliest="{earliest_time}" latest="{latest_time}"
                    tenant_id="{tenant_id}" register_component="True"
                    component="splk-wlk" report="trackme_wlk_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
                    | lookup local=t trackme_wlk_apps_enablement_tenant_{tenant_id} app OUTPUT enabled as app_is_enabled | where NOT app_is_enabled="False"
                    """

            # log
            logger.info(f"tracker_search={tracker_search}")

            # finish the search
            if tracker_type not in ("main", "metadata", "orphan", "inactive_entities"):
                # manage extra options for deduplication
                if tracker_type in (
                    "introspection",
                    "scheduler",
                    "notable",
                    "splunkcloud_svc",
                ):
                    wklparse_extra_options = f"check_last_seen=True check_last_seen_field=last_seen_{tracker_type}"
                else:
                    wklparse_extra_options = f"check_last_seen=False"

                if overgroup:
                    tracker_search_extension = f"""\
                        | eval tracker_type = "{tracker_type}"
                        | eval account = "{account}"
                        | `trackme_wlk_lookup_metadata_version_id({tenant_id})`
                        | trackmesplkwlkparse tenant_id="{tenant_id}" context="live" overgroup="{overgroup}" {wklparse_extra_options}
                        """
                else:
                    tracker_search_extension = f"""\
                        | eval tracker_type = "{tracker_type}"
                        | eval account = "{account}"
                        | `trackme_wlk_lookup_metadata_version_id({tenant_id})`
                        | trackmesplkwlkparse tenant_id="{tenant_id}" context="live" {wklparse_extra_options}
                        """

            if tracker_type == "introspection":
                tracker_search = f"""\
                    {tracker_search}
                    | trackmegenjsonmetrics fields="pct_cpu,pct_memory,elapsed,scan_count"
                    {tracker_search_extension}"""

            elif tracker_type == "scheduler":
                tracker_search = f"""\
                    {tracker_search}
                    ``` In some circumstances, the scheduler logs may lack a user and app context which could lead to the creation of new entities in case of execution errors ```
                    ``` Althrough the following can potentially be wrong, in a majority of use cases, we can lookup the collection and use already known user and app context as a last chance choice ```
                    ``` This needs to happen at the last step of the tracker execution to handle remote executions ```
                    | lookup trackme_wlk_tenant_{tenant_id} savedsearch_name OUTPUT app as collection_app, user as collection_user
                    | foreach collection_user, collection_app [ eval <<FIELD>> = mvindex('<<FIELD>>', 0) ]
                    | foreach user, app [ eval <<FIELD>> = if(user=="system" AND isnotnull(collection_user) AND user!=collection_user, collection_<<FIELD>>, <<FIELD>>) ]
                    | fields - collection_app, collection_user
                    ``` perform a second verification for the user owner, dynamically query the owner from the savedsearch_name if still unknown ```
                    | trackmesplkwlkgetreportowner account="{account}"
                    | eval object = app . ":" . user . ":" . savedsearch_name, object_id=sha256(object)
                    | eval group = app
                    | fields _time, app, user, savedsearch_name, count_completed, count_skipped, count_execution, count_errors, group, object, object_id                    
                    ``` finalize ```
                    | trackmegenjsonmetrics fields="count_completed,count_execution,count_skipped,count_errors"
                    {tracker_search_extension}"""

            elif tracker_type == "notable":
                tracker_search = f"""\
                    {tracker_search}
                    ``` Lookup app and user from savedsearch_name ```
                    | lookup trackme_wlk_tenant_{tenant_id} savedsearch_name OUTPUT object, app, user, group
                    | where isnotnull(object)
                    ``` ensure we always have a single value, if we have multiple entries for the same search, we could end up with mv fields ```
                    | foreach object, app, user, group [ eval <<FIELD>> = mvindex('<<FIELD>>', 0) ]
                    | fields _time, app, user, savedsearch_name, count_ess_notable, group, object, object_id
                    | trackmegenjsonmetrics fields="count_ess_notable"
                    {tracker_search_extension}"""

            elif tracker_type == "splunkcloud_svc":
                tracker_search = f"""\
                    {tracker_search}
                    | trackmegenjsonmetrics fields="svc_usage"
                    {tracker_search_extension}"""

            #
            # burn test: execute the search directly and report the run time performance
            #

            if burn_test:
                burn_test_search = remove_leading_spaces(tracker_search)

                logger.info(
                    f'tenant_id="{tenant_id}", burn test was requested, starting burn test now'
                )

                burn_test_kwargs = {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "search_mode": "normal",
                    "preview": False,
                    "time_format": "%s",
                    "output_mode": "json",
                    "count": 0,
                }

                burn_test_start_time = time.time()
                burn_test_results_counter = 0

                try:
                    reader = run_splunk_search(
                        service,
                        burn_test_search,
                        burn_test_kwargs,
                        24,
                        5,
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            burn_test_results_counter += 1

                    burn_test_results_record = {
                        "tenant_id": tenant_id,
                        "run_time": round((time.time() - burn_test_start_time), 3),
                        "results_count": burn_test_results_counter,
                        "search": burn_test_search,
                        "burn_test_success": True,
                    }

                    logger.info(
                        f'tenant_id="{tenant_id}", burn test, results="{json.dumps(burn_test_results_record, indent=2)}"'
                    )
                    return {"payload": burn_test_results_record, "status": 200}

                except Exception as e:
                    burn_test_results_record = {
                        "tenant_id": tenant_id,
                        "run_time": round((time.time() - burn_test_start_time), 3),
                        "results_count": burn_test_results_counter,
                        "search": burn_test_search,
                        "burn_test_success": False,
                        "exception": f'search failed with exception="{str(e)}"',
                    }

                    logger.error(json.dumps(burn_test_results_record, indent=2))
                    return {
                        "payload": burn_test_results_record,
                        "status": 200,
                    }

            #
            # step 2: create the wrapper
            #

            report_name = (
                f"trackme_wlk_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
            )

            if tracker_type == "main":
                report_search = f"""\
                    {tracker_search}
                    | eval tracker_runtime=now()
                    | `trackme_wlk_tracker_abstract({tenant_id})`
                    | `trackme_collect_state("current_state_tracking:splk-wlk:{tenant_id}", "object", "{tenant_id}")`
                    | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-wlk"
                    | `set_splk_outliers_rules({tenant_id}, wlk)`
                    | `trackme_outputlookup(trackme_wlk_tenant_{tenant_id}, key)`
                    | stats count as report_entities_count, values(object) as report_objects_list by tenant_id
                    | `register_tenant_component_summary_wlk({tenant_id}, wlk)`"""

            elif tracker_type in ("metadata", "orphan", "inactive_entities"):
                report_search = f"""\
                    {tracker_search}
                    """

            else:
                report_search = f"""\
                    {tracker_search}
                    | eval tenant_id="{tenant_id}"
                    | stats count as report_entities_count, values(object) as report_objects_list by tenant_id
                    | `register_tenant_component_summary_wlk({tenant_id}, wlk)`"""

            # Create a new report
            report_properties = {
                "description": "TrackMe hybrid wrapper",
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
                "is_scheduled": False,
            }

            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }

            wrapper_create_report = trackme_create_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
                remove_leading_spaces(report_search),
                report_properties,
                report_acl,
            )

            # sleep
            time.sleep(5)

            #
            # step 3: create the tracker
            #

            report_name = (
                f"trackme_{component}_hybrid_{tracker_name}_tracker_tenant_{tenant_id}"
            )
            report_search = f"""\
                | trackmetrackerexecutor tenant_id="{tenant_id}" component="splk-{component}" report="trackme_{component}_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}" alert_no_results=True"""

            # Create a new report
            report_properties = {
                "description": "TrackMe hybrid tracker",
                "is_scheduled": True,
                "schedule_window": "5",
                "cron_schedule": str(cron_schedule),
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
            }

            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }

            tracker_create_report = trackme_create_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
                remove_leading_spaces(report_search),
                report_properties,
                report_acl,
            )

            # sleep
            time.sleep(5)

        #
        # END
        #

        audit_record = {
            "account": str(account),
            "wrapper_report": wrapper_create_report.get("report_name"),
            "tracker_report": tracker_create_report.get("report_name"),
            "root_constraint": str(root_constraint),
            "tracker_name": str(tracker_name),
            "tracker_search": remove_leading_spaces(tracker_search),
            "earliest": str(earliest_time),
            "latest": str(latest_time),
            "cron_schedule": tracker_create_report.get("cron_schedule"),
            "action": "success",
        }

        # Register the new components in the vtenant collection
        collection_vtenants_name = "kv_trackme_virtual_tenants"
        collection_vtenants = service.kvstore[collection_vtenants_name]

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # Get the tenant
        try:
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps(query_string)
            )[0]
            vtenant_key = vtenant_record.get("_key")

        except Exception as e:
            vtenant_key = None

        # We can only proceed with a valid tenant record
        if vtenant_key:
            # Try to get the current definition
            try:
                tenant_hybrid_objects = vtenant_record.get("tenant_wlk_hybrid_objects")

                # logger.debug
                logger.debug(f'tenant_hybrid_objects="{tenant_hybrid_objects}"')
            except Exception as e:
                tenant_hybrid_objects = None

            # add to existing disct
            if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                vtenant_dict = json.loads(tenant_hybrid_objects)
                logger.info(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')

                report1 = wrapper_create_report.get("report_name")
                report2 = tracker_create_report.get("report_name")

                reports = vtenant_dict["reports"]
                reports.append(str(report1))
                reports.append(str(report2))
                vtenant_dict = dict(
                    [
                        ("reports", reports),
                    ]
                )

            # empty dict
            else:
                report1 = wrapper_create_report.get("report_name")
                report2 = tracker_create_report.get("report_name")

                reports = []
                reports.append(str(report1))
                reports.append(str(report2))

                vtenant_dict = dict(
                    [
                        ("reports", reports),
                    ]
                )

            try:
                vtenant_record["tenant_wlk_hybrid_objects"] = json.dumps(
                    vtenant_dict, indent=1
                )
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )
            except Exception as e:
                logger.error(
                    f'Failure while trying to update the vtenant KVstore record, exception="{e}"'
                )
                return {
                    "payload": f"Warn: exception encountered: {e}",  # Payload of the request.
                }

            # Record the new hybrid component in the hybrid collection
            collection_hybrid_name = (
                "kv_trackme_"
                + str(component)
                + "_hybrid_trackers_tenant_"
                + str(tenant_id)
            )
            collection_hybrid = service.kvstore[collection_hybrid_name]

            reports = []
            reports.append(str(report1))
            reports.append(str(report2))

            properties = []
            properties_dict = {
                "tracker_type": str(tracker_type),
                "account": str(account),
                "root_constraint": str(root_constraint),
                "earliest": str(earliest_time),
                "latest": str(latest_time),
                "cron_schedule": tracker_create_report.get("cron_schedule"),
            }

            properties.append(properties_dict)

            hybrid_dict = dict(
                [
                    ("reports", reports),
                    ("properties", properties),
                ]
            )

            try:
                collection_hybrid.data.insert(
                    json.dumps(
                        {
                            "_key": hashlib.sha256(
                                tracker_name.encode("utf-8")
                            ).hexdigest(),
                            "tracker_type": tracker_type,
                            "tracker_name": tracker_name,
                            "knowledge_objects": json.dumps(hybrid_dict, indent=1),
                        }
                    )
                )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{e}"'
                )

        # Record an audit change
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "add hybrid tracker",
                f"trackme_{component}_hybrid_{tracker_name}",
                "hybrid_tracker",
                str(audit_record),
                "The hybrid tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{e}"')

        # final return
        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Remove an hybrid tracker and associated objects
    def post_wlk_tracker_delete(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_wlk/admin/wlk_tracker_delete" body="{'tenant_id': 'mytenant', 'hybrid_trackers_list': 'test:001,test:002'}"
        """

        # By tracker_name
        tenant_id = None
        hybrid_trackers_list = None
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
                tenant_id = resp_dict["tenant_id"]
                hybrid_trackers_list = resp_dict["hybrid_trackers_list"]
                # Handle as a CSV list of keys, it not already a list
                if not isinstance(hybrid_trackers_list, list):
                    hybrid_trackers_list = [x.strip() for x in hybrid_trackers_list.split(",") if x.strip()]
                else:
                    # Filter out empty strings from existing list
                    hybrid_trackers_list = [x.strip() if isinstance(x, str) else x for x in hybrid_trackers_list if (x.strip() if isinstance(x, str) else bool(x))]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs the deletion of an hybrid tracker and associated objects, it requires a POST call with the following information:",
                "resource_desc": "Delete an hybrid tracker and associated objects",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_wlk/admin/wlk_tracker_delete\" body=\"{'tenant_id': 'mytenant', 'hybrid_trackers_list': 'test:001,test:002'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "hybrid_trackers_list": "comma separated list of hybrid entities to be deleted, for each submitted entity, all related objects will be purged",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

        # Loop through the list of entities to be handled
        for hybrid_tracker in hybrid_trackers_list:
            # this operation will be considered to be successful only no failures were encountered
            # any failure encountered will be added to the record summary for that entity
            sub_failures_count = 0

            # Define the KV query
            query_string = {
                "tracker_name": hybrid_tracker,
            }

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

            # get TrackMe conf
            trackme_conf = trackme_reqinfo(
                request_info.system_authtoken, request_info.server_rest_uri
            )
            logger.debug(f'trackme_conf="{json.dumps(trackme_conf, indent=2)}"')

            try:
                # Data collection
                collection_name = "kv_trackme_wlk_hybrid_trackers_tenant_" + str(
                    tenant_id
                )
                collection = service.kvstore[collection_name]

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

                try:
                    hybrid_record = collection.data.query(
                        query=json.dumps(query_string)
                    )[0]
                    key = hybrid_record.get("_key")

                except Exception as e:
                    key = None

                # Render result
                if key:
                    # check if TCM is enabled in receiver mode
                    enable_conf_manager_receiver = int(
                        trackme_conf["trackme_conf"]["trackme_general"][
                            "enable_conf_manager_receiver"
                        ]
                    )

                    if enable_conf_manager_receiver == 1:
                        try:
                            tcm_response = trackme_send_to_tcm(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                resp_dict,
                                "post",
                                "/services/trackme/v2/splk_wlk/admin/wlk_tracker_delete",
                            )
                            logger.info(
                                f"trackme_send_to_tcm was successfully executed"
                            )
                        except Exception as e:
                            logger.error(
                                f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                            )

                    # load the knowledge object dict
                    tenant_hybrid_objects = json.loads(
                        hybrid_record.get("knowledge_objects")
                    )
                    logger.debug(
                        f'tenant_hybrid_objects="{json.dumps(tenant_hybrid_objects, indent=1)}"'
                    )

                    # Step 1: delete knowledge objects
                    reports_list = tenant_hybrid_objects["reports"]
                    logger.debug(f'reports_list="{reports_list}"')

                    # Delete all reports
                    for report_name in reports_list:
                        logger.info(
                            f'tenant_id="{tenant_id}", attempting removal of report="{report_name}"'
                        )
                        try:
                            service.saved_searches.delete(str(report_name))
                            logger.info(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", action="success", the report was successfully removed, report_name="{report_name}"'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", failed to remove the report, report_name="{report_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "hybrid_tracker": hybrid_tracker,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", failed to remove the report, report_name="{report_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                    # Step 2: delete the KVstore record

                    # Remove the record
                    try:
                        collection.data.delete(json.dumps({"_key": key}))

                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"'
                        )
                        sub_failures_count += 1
                        result = {
                            "tracker_name": hybrid_tracker,
                            "action": "delete",
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"',
                        }
                        records.append(result)

                    # Step 3: delete the hybrid knowledge from the tenant

                    # Register the new components in the vtenant collection
                    collection_vtenants_name = "kv_trackme_virtual_tenants"
                    collection_vtenants = service.kvstore[collection_vtenants_name]

                    # Define the KV query search string
                    query_string = {
                        "tenant_id": tenant_id,
                    }

                    # Get the tenant
                    try:
                        vtenant_record = collection_vtenants.data.query(
                            query=json.dumps(query_string)
                        )[0]
                        vtenant_key = vtenant_record.get("_key")

                    except Exception as e:
                        vtenant_key = None

                    # We can only proceed with a valid tenant record
                    if vtenant_key:
                        # Try to get the current definition
                        try:
                            tenant_hybrid_objects = vtenant_record.get(
                                "tenant_wlk_hybrid_objects"
                            )
                            # logger.debug
                            logger.debug(
                                f'tenant_hybrid_objects="{tenant_hybrid_objects}"'
                            )
                        except Exception as e:
                            tenant_hybrid_objects = None

                        # remove from the dict
                        if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                            vtenant_dict = json.loads(tenant_hybrid_objects)
                            logger.debug(
                                f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"'
                            )

                            report1 = (
                                "trackme_wlk_hybrid_"
                                + str(hybrid_tracker)
                                + "_wrapper"
                                + "_tenant_"
                                + str(tenant_id)
                            )
                            report2 = (
                                "trackme_wlk_hybrid_"
                                + str(hybrid_tracker)
                                + "_tracker"
                                + "_tenant_"
                                + str(tenant_id)
                            )

                            reports = vtenant_dict["reports"]
                            try:
                                reports.remove(str(report1))
                            except ValueError:
                                logger.warning(
                                    f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", report="{report1}" not found in tenant_wlk_hybrid_objects, skipping removal'
                                )
                            try:
                                reports.remove(str(report2))
                            except ValueError:
                                logger.warning(
                                    f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", report="{report2}" not found in tenant_wlk_hybrid_objects, skipping removal'
                                )

                            vtenant_dict = dict(
                                [
                                    ("reports", reports),
                                ]
                            )

                            # Update the KVstore
                            try:
                                vtenant_record["tenant_wlk_hybrid_objects"] = (
                                    json.dumps(vtenant_dict, indent=2)
                                )
                                collection_vtenants.data.update(
                                    str(vtenant_key), json.dumps(vtenant_record)
                                )

                            except Exception as e:
                                logger.error(
                                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                                )
                                return {
                                    "payload": "Warn: exception encountered: "
                                    + str(e)  # Payload of the request.
                                }

                    # Step 4: purge the register summary object
                    try:
                        delete_register_summary = trackme_delete_tenant_object_summary(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            "splk-wlk",
                            "trackme_wlk_hybrid_"
                            + str(hybrid_tracker)
                            + "_wrapper"
                            + "_tenant_"
                            + str(tenant_id),
                        )
                    except Exception as e:
                        logger.error(
                            f'exception encountered while calling function trackme_delete_tenant_object_summary, exception="{str(e)}"'
                        )

                    # Record an audit change
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "remove hybrid tracker",
                            str(hybrid_tracker),
                            "hybrid_tracker",
                            str(json.dumps(hybrid_record, indent=2)),
                            "The Hybrid tracker and its associated objects were successfully deleted",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    logger.info(
                        f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", The hybrid tracker and its associated objects were successfully deleted'
                    )

                    # Handle the sub operation results
                    if sub_failures_count == 0:
                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # append for summary
                        result = {
                            "tracker_name": hybrid_tracker,
                            "action": "delete",
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", The hybrid tracker and its associated objects were successfully deleted',
                        }
                        records.append(result)

                else:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    logger.error(
                        f'tenant_id="{tenant_id}", tracker_name="{hybrid_tracker}", the resource was not found or the request is incorrect'
                    )

                    # append for summary
                    result = {
                        "tracker_name": hybrid_tracker,
                        "action": "delete",
                        "result": "failure",
                        "exception": "HTTP 404 NOT FOUND",
                    }
                    records.append(result)

            # raise any exception
            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                logger.error(
                    f'tenant_id="{tenant_id}", exception encountered, exception="{str(e)}"'
                )

                # append for summary
                result = {
                    "tracker_name": hybrid_tracker,
                    "action": "delete",
                    "result": "failure",
                    "exception": str(e),
                }

                records.append(result)

        # render HTTP status and summary

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
