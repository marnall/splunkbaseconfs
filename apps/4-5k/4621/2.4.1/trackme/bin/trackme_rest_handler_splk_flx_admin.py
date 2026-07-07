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
import hashlib
import json
import os
import re
import sys
import time
import uuid
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
    "trackme.rest.splk_flx_admin", "trackme_rest_api_splk_flx_admin.log"
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
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_send_to_tcm,
)

# import trackme libs utils
from trackme_libs_utils import (
    remove_leading_spaces,
    sanitize_flx_tracker_name_prefix,
    sanitize_spl_input,
)

# import TrackMe converging helpers (single source of truth for the
# converging command string — keeps create and in-place update identical)
from trackme_libs_flx_converging import (
    build_converging_command,
    parse_converging_command,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license

# import trackme libs croniter
from trackme_libs_croniter import validate_cron_schedule

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkFlxTrackingAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkFlxTrackingAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_flx(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_flx/admin",
            "resource_group_desc": "Endpoints specific to the splk-flx TrackMe component (Splunk Flex objects tracking, admin operations)",
        }

        return {"payload": response, "status": 200}

    # Return a use case from the library
    def post_flx_load_uc(self, request_info, **kwargs):
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
                uc_ref = resp_dict["uc_ref"]
                tenant_id = resp_dict["tenant_id"]
                group = resp_dict["group"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a use case from the Flex library, it requires a POST call with the following information:",
                "resource_desc": "Return a Flex use case",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_flx/admin/flx_load_uc" mode="post" body="{\'uc_ref\': \'splk_dma\'"}',
                "options": [
                    {
                        "tenant_id": "The target tenant identifier, in some cases replacements are needed in the search logic",
                        "group": "The group target, in some cases replacements are needed in the search logic",
                        "uc_ref": "The use case reference identifier",
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
        uc_lib_json = f"{uc_ref}.json"
        uc_json = os.path.join(
            splunkhome, "etc", "apps", "trackme", "lib", "flx_library", uc_lib_json
        )

        if not os.path.isfile(uc_json):
            # render response
            msg = f"The uc_ref={uc_ref} could not be found in the use case library, expected file {uc_json} was not found."
            logger.error(msg)
            return {
                "payload": {
                    "action": "failure",
                    "response": msg,
                },
                "status": 500,
            }

        else:
            try:
                with open(uc_json, "r") as f:
                    uc_json_def = json.load(f)

                # perform tenant_id replacement
                uc_search = uc_json_def.get("uc_search")
                uc_search = uc_search.replace("mytenant", tenant_id)
                uc_search = uc_search.replace("mygroup", group)
                uc_json_def["uc_search"] = uc_search

                return {
                    "payload": {
                        "response": uc_json_def,
                    },
                    "status": 200,
                }

            except Exception as e:
                # render response
                msg = f'An exception was encountered, uc_file={uc_json}, exception="{str(e)}"'
                logger.error(msg)
                return {
                    "payload": {
                        "action": "failure",
                        "response": msg,
                    },
                    "status": 500,
                }

    # Return and execute simulation searches
    def post_flx_tracker_simulation(self, request_info, **kwargs):
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
                try:
                    run_simulation = resp_dict["run_simulation"]
                except Exception as e:
                    if run_simulation in ("true", "false"):
                        if run_simulation == "true":
                            run_simulation = True
                        elif run_simulation == "false":
                            run_simulation = False
                    else:
                        msg = f'Invalid option for run_simulation="{run_simulation}", valid choices are: true | false'
                        logger.error(msg)
                        return {
                            "payload": {
                                "action": "failure",
                                "response": msg,
                            },
                            "status": 500,
                        }

                # tracker name
                try:
                    tracker_name = resp_dict["tracker_name"]
                except Exception as e:
                    tracker_name = None

                if not tracker_name or len(tracker_name) == 0:
                    # generate a random tracker name
                    tracker_name = "flx_" + uuid.uuid4().hex[:5]

                else:
                    # Sanitize the user-supplied prefix (lowercase + space/colon→hyphen
                    # + strip SPL metacharacters), then append the uuid suffix.
                    # Falls back to "flx" if the prefix collapses to empty after
                    # sanitization (e.g. user supplied only metacharacters).
                    sanitized = sanitize_flx_tracker_name_prefix(tracker_name)
                    tracker_name = (sanitized or "flx") + "_" + uuid.uuid4().hex[:5]

                # tenant
                tenant_id = resp_dict["tenant_id"]

                # get account
                account = resp_dict["account"]

                # get search
                search_constraint = resp_dict["search_constraint"]

                # Substitute the `__flx_tracker_placeholder__` token with the
                # finalized tracker_name. Mirrors the `mytenant` / `mygroup`
                # substitution done in `post_flx_load_uc`, but cannot run there
                # because the tracker_name is only generated at simulation /
                # create time.
                #
                # The placeholder is deliberately distinctive (double-underscore
                # padded, 28 chars) so it cannot collide with substrings of
                # user-authored SPL — unlike a natural-language token like
                # `mytracker` would (see issue #1698). The substitution runs
                # against arbitrary user-submitted SPL here, so the token MUST
                # be one that a user would never accidentally type.
                #
                # Use-case templates reference the placeholder in their SPL
                # (e.g. to extract the tracker-keyed entry from
                # `object_description` via
                # `spath path="__flx_tracker_placeholder__"`).
                if isinstance(search_constraint, str) and tracker_name:
                    search_constraint = search_constraint.replace(
                        "__flx_tracker_placeholder__", tracker_name
                    )

                # get time range quantifiers
                earliest_time = resp_dict["earliest_time"]
                latest_time = resp_dict["latest_time"]

                # cron_schedule, if submitted in the context of simulation will be verified
                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = None

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "*/5 * * * *"

                # verify the cron schedule validity, if submitted
                if cron_schedule:
                    try:
                        validate_cron_schedule(cron_schedule)
                    except Exception as e:
                        logger.error(str(e))
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns and (optionally) executes a simulation search for a Flex Object tracker. It is used by the Flex tracker creation wizard to preview the search syntax and entity counts before committing the tracker. It requires a POST call with the following information:",
                "resource_desc": "Return (and optionally execute) the simulation search for a candidate Flex Object tracker",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_flx/admin/flx_tracker_simulation\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'account': 'local', 'tracker_name': 'mytracker', 'search_constraint': 'index=_internal sourcetype=splunkd', 'earliest_time': '-4h', 'latest_time': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "account": "REQUIRED. Splunk deployment to run the simulation against — either 'local' or the name of a configured remote account",
                        "search_constraint": "REQUIRED. Splunk root search constraint. When using tstats mode, all referenced fields must be indexed time fields",
                        "earliest_time": "REQUIRED. The earliest time quantifier (e.g. '-4h', '-24h@h')",
                        "latest_time": "REQUIRED. The latest time quantifier (e.g. 'now', '+5m')",
                        "tracker_name": "OPTIONAL. The name of the tracker — value will prefix all entities under the format value:<entity>. Defaults to a randomly-generated name when omitted",
                        "run_simulation": "OPTIONAL. Execute the simulation search or simply return the search syntax. Valid options are 'true' / 'false' (defaults to 'true')",
                        "cron_schedule": "OPTIONAL. The cron schedule. When submitted in the simulation context, the value is validated for syntax",
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

        # proceed
        try:
            # init
            response = {
                "run_simulation": run_simulation,
                "tracker_name": tracker_name,
                "account": account,
                "search_constraint": search_constraint,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
            }

            # Define the search
            tracker_simulation_search = search_constraint

            # If account is remote
            if account != "local":
                # replace any double quotes already escaped with a single backslash with triple escaped double quotes
                tracker_simulation_search = re.sub(
                    r'(?<=\\)"', r'\\\\"', tracker_simulation_search
                )
                # replace any remaining standalone double quotes with escaped double quotes
                tracker_simulation_search = re.sub(
                    r'(?<!\\)"', r'\\"', tracker_simulation_search
                )
                # replace any double quotes already escaped with a single backslash with triple escaped double quotes
                tracker_simulation_search = tracker_simulation_search.replace(
                    r"\\\\\"", r"\\\""
                )

                # set search
                tracker_simulation_search = f"""
                | splunkremotesearch account="{account}" search="{tracker_simulation_search}"
                earliest="{earliest_time}" latest="{latest_time}"
                """.strip()

            logger.debug(f'tracker_simulation_search="{tracker_simulation_search}"')

            tracker_simulation_search = f"""
            {tracker_simulation_search}
            | eval tracker_name = "{tracker_name}"
            | trackmesplkflxparse tenant_id="{tenant_id}" context="simulation"
            """.strip()

            # add to response
            response["tracker_simulation_search"] = remove_leading_spaces(
                tracker_simulation_search
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

    # Create a use case flx tracker
    def post_flx_tracker_create(self, request_info, **kwargs):
        # args
        account = None
        tenant_id = None
        tracker_name = None
        root_constraint = None
        cron_schedule = None
        owner = None
        earliest_time = None
        latest_time = None
        flx_type = None
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
                component = "flx"

                # tracker name
                try:
                    tracker_name = resp_dict["tracker_name"]
                except Exception as e:
                    tracker_name = None

                if not tracker_name or len(tracker_name) == 0:
                    # generate a random tracker name
                    tracker_name = "flx_" + uuid.uuid4().hex[:5]

                else:
                    # Sanitize the user-supplied prefix (lowercase + space/colon→hyphen
                    # + strip SPL metacharacters), then append the uuid suffix.
                    # Falls back to "flx" if the prefix collapses to empty after
                    # sanitization (e.g. user supplied only metacharacters).
                    sanitized = sanitize_flx_tracker_name_prefix(tracker_name)
                    tracker_name = (sanitized or "flx") + "_" + uuid.uuid4().hex[:5]

                # remote account
                account = resp_dict["account"]

                # the root constraint of the tracker
                root_constraint = sanitize_spl_input(resp_dict["root_constraint"])

                # Substitute the `__flx_tracker_placeholder__` token with the
                # finalized tracker_name (see post_flx_tracker_simulation for
                # the rationale on the distinctive placeholder and the
                # user-SPL-collision risk it avoids — issue #1698).
                if isinstance(root_constraint, str) and tracker_name:
                    root_constraint = root_constraint.replace(
                        "__flx_tracker_placeholder__", tracker_name
                    )

                #
                # optional args
                #

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "*/5 * * * *"

                # verify the cron schedule validity, if submitted
                if cron_schedule:
                    try:
                        validate_cron_schedule(cron_schedule)
                    except Exception as e:
                        logger.error(str(e))
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

                try:
                    owner = resp_dict["owner"]
                except Exception as e:
                    owner = None

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

                # earliest_time and latest_time for the tracker, if not specified, defaults to -5m / +4h for flx|dhm and -5m/+5m for flx
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-5m"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "now"

                # Optional: burn_test, temporary create the abstract, perform a burn test, report the run time performance, delete and report
                try:
                    burn_test = resp_dict["burn_test"]
                    if burn_test == "True":
                        burn_test = True
                    elif burn_test == "False":
                        burn_test = False
                except Exception as e:
                    burn_test = False

                # Optional: flx_type, the type of flx tracker, do not set if not specified
                try:
                    flx_type = resp_dict["flx_type"]
                    if flx_type not in ("use_case", "converging"):
                        return {
                            "payload": {
                                "response": f'Invalid flx_type="{flx_type}", valid options are: use_case | converging',
                                "status": 500,
                            },
                        }
                except Exception as e:
                    flx_type = None

                # Optional: enable_zero_kpis_when_inactive
                # When enabled (default), the FLX inactive entities tracker emits a 0 value for every
                # numeric KPI in the entity's last-seen metrics dict (status stays = 2). This keeps the
                # Outliers Anomaly Detection chart continuous through inactivity windows.
                try:
                    enable_zero_kpis_when_inactive = (
                        1 if int(resp_dict.get("enable_zero_kpis_when_inactive", 1)) else 0
                    )
                except (TypeError, ValueError):
                    enable_zero_kpis_when_inactive = 1

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating an hybrid tracker for Flex Objects tracking, it requires a POST call with the following information:",
                "resource_desc": "Create a new Hybrid tracker",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/admin/flx_tracker_create\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'test:001', 'account': 'local', 'root_constraint': '', 'earliest_time': '-5m', 'latest_time': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_name": "The name of tracker, this value will prefix all entities under the format value:<entity>",
                        "account": "name of remote Splunk deployment account as configured in TrackMe",
                        "root_constraint": "the Splunk magic search",
                        "owner": "Optional, the Splunk user owning the objects to be created, defaults to the owner set for the tenant",
                        "cron_schedule": "Optional, the cron schedule, defaults to every 5 minutes",
                        "earliest_time": "Optional, the earliest time value for the tracker, defaults to -5m for flx|dhm and -5m for flx",
                        "latest_time": "Optional, the latest time value for the tracker, defaults to +4h for flx|dhm and +5m for flx",
                        "burn_test": "Optional, create the abstract report, run a performance test, delete the report and report the performance results, valid options are: True | False (default: False)",
                        "flx_type": "Optional, the type of flx tracker, valid options are: use_case | converging",
                        "enable_zero_kpis_when_inactive": "Optional, 0 or 1 (default: 1). When enabled, the FLX inactive entities tracker emits a 0 value for every numeric KPI in the entity's last-seen metrics dict (status stays = 2), keeping the Outliers Anomaly Detection chart continuous through inactivity windows.",
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
                license_active_flex_trackers = int(
                    check_license.get("license_active_flex_trackers")
                )
                logger.debug(
                    f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
                )

            except Exception as e:
                license_is_valid = 0
                license_subscription_class = "free"
                license_read_only = False
                license_active_flex_trackers = 32
                logger.error(f'function check_license exception="{str(e)}"')

            if license_read_only:
                return {
                    "payload": "I'm afraid I can't do that, this instance is currently in read-only mode and cannot create new trackers.",
                    "status": 402,
                }

            if license_subscription_class == "foundation":
                audit_record = {
                    "action": "failure",
                    "change_type": "add new Flex tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, the Foundation edition does not allow creating Flex trackers.",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            if license_active_flex_trackers >= 32 and (
                license_is_valid != 1 or license_subscription_class == "foundation"
            ):
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new CIM tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, the maximum number of 32 allowed trackers has been reached, there are {license_active_flex_trackers} active trackers currently for this component",
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
                        "/services/trackme/v2/splk_flx/admin/flx_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            #
            # step 1: define the search
            #

            # Define the search
            tracker_simulation_search = root_constraint

            # If account is remote
            if account != "local":
                # replace any double quotes already escaped with a single backslash with triple escaped double quotes
                tracker_simulation_search = re.sub(
                    r'(?<=\\)"', r'\\\\"', tracker_simulation_search
                )
                # replace any remaining standalone double quotes with escaped double quotes
                tracker_simulation_search = re.sub(
                    r'(?<!\\)"', r'\\"', tracker_simulation_search
                )
                # replace any double quotes already escaped with a single backslash with triple escaped double quotes
                tracker_simulation_search = tracker_simulation_search.replace(
                    r"\\\\\"", r"\\\""
                )

                tracker_simulation_search = f"""
                | splunkremotesearch account="{account}" search="{tracker_simulation_search}"
                earliest="{earliest_time}" latest="{latest_time}" tenant_id="{tenant_id}"
                register_component="True" component="splk-flx" report="trackme_flx_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
                """.strip()

            logger.info(f"tracker_simulation_search={tracker_simulation_search}")

            if not flx_type:
                tracker_simulation_search = f"""
                {tracker_simulation_search}
                | eval tracker_name = "{tracker_name}"
                | trackmesplkflxparse tenant_id="{tenant_id}" context="live"
                """.strip()
            else:
                tracker_simulation_search = f"""
                {tracker_simulation_search}
                | eval tracker_name = "{tracker_name}"
                | trackmesplkflxparse tenant_id="{tenant_id}" context="live" flx_type="{flx_type}"
                """.strip()

            #
            # burn test: execute the search directly and report the run time performance
            #

            if burn_test:
                burn_test_search = remove_leading_spaces(
                    tracker_simulation_search
                )

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
                f"trackme_flx_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
            )
            report_search = f"""
            {tracker_simulation_search}
            ``` set the table ```
            | eval time=if(isnull(_time), now(), _time)
            | table _time, group, object, alias, object_category, object_description, status, status_description, metrics, outliers_metrics, *
            | eval tracker_name="trackme_flx_hybrid_{tracker_name}_tracker_tenant_{tenant_id}"
            | eval account="{account}"
            | eval tracker_runtime=now()
            ``` abstract macro ```
            | `trackme_flx_tracker_abstract({tenant_id})`
            ``` collects latest collection state into the summary index ```
            | `trackme_collect_state("current_state_tracking:splk-flx:{tenant_id}", "object", "{tenant_id}")`
            ``` output flipping change status if changes ```
            | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-flx"
            ```Generate splk outliers rules```
            | `set_splk_outliers_rules({tenant_id}, flx)`
            | `trackme_outputlookup(trackme_flx_tenant_{tenant_id}, key)`
            | stats count as report_entities_count, values(object) as report_objects_list by tenant_id
            | `register_tenant_component_summary_nofilter({tenant_id}, flx)`
            """.strip()

            # create a new report
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
            report_search = f"""
            | trackmetrackerexecutor tenant_id="{tenant_id}" component="splk-{component}" 
            report="trackme_{component}_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}" 
            alert_no_results=True
            """.strip()

            # create a new report
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
                tenant_hybrid_objects = vtenant_record.get("tenant_flx_hybrid_objects")

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
                vtenant_record["tenant_flx_hybrid_objects"] = json.dumps(
                    vtenant_dict, indent=1
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
                            "tracker_id": tracker_name,
                            "tracker_name": tracker_name,
                            "enable_zero_kpis_when_inactive": enable_zero_kpis_when_inactive,
                            "knowledge_objects": json.dumps(hybrid_dict, indent=1),
                        }
                    )
                )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{str(e)}"'
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
                "trackme_" + str(component) + "_hybrid_" + str(tracker_name),
                "hybrid_tracker",
                str(audit_record),
                "The hybrid tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        # final return
        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Create a converging flx tracker
    def post_flx_converging_tracker_create(self, request_info, **kwargs):
        # args
        tenant_id = None
        tracker_name = None
        root_constraint = None
        cron_schedule = None
        owner = None
        earliest_time = None
        latest_time = None
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
                component = "flx"

                # tracker name
                try:
                    tracker_name = resp_dict["tracker_name"]
                except Exception as e:
                    tracker_name = None

                if not tracker_name or len(tracker_name) == 0:
                    # generate a random tracker name
                    tracker_name = "flx_" + uuid.uuid4().hex[:5]

                else:
                    # Sanitize the user-supplied prefix (lowercase + space/colon→hyphen
                    # + strip SPL metacharacters), then append the uuid suffix.
                    # Falls back to "flx" if the prefix collapses to empty after
                    # sanitization (e.g. user supplied only metacharacters).
                    sanitized = sanitize_flx_tracker_name_prefix(tracker_name)
                    tracker_name = (sanitized or "flx") + "_" + uuid.uuid4().hex[:5]

                # the root constraint of the tracker
                root_constraint = sanitize_spl_input(resp_dict["root_constraint"])

                # Substitute the `__flx_tracker_placeholder__` token with the
                # finalized tracker_name (see post_flx_tracker_simulation for
                # the rationale on the distinctive placeholder and the
                # user-SPL-collision risk it avoids — issue #1698).
                if isinstance(root_constraint, str) and tracker_name:
                    root_constraint = root_constraint.replace(
                        "__flx_tracker_placeholder__", tracker_name
                    )

                #
                # optional args
                #

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "*/5 * * * *"

                # verify the cron schedule validity, if submitted
                if cron_schedule:
                    try:
                        validate_cron_schedule(cron_schedule)
                    except Exception as e:
                        logger.error(str(e))
                        return {
                            "payload": {
                                "action": "failure",
                                "response": str(e),
                            },
                            "status": 500,
                        }

                try:
                    owner = resp_dict["owner"]
                except Exception as e:
                    owner = None

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

                # earliest_time and latest_time for the tracker, if not specified, defaults to -5m / +4h for flx|dhm and -5m/+5m for flx
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-5m"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "now"

                # Optional: burn_test, temporary create the abstract, perform a burn test, report the run time performance, delete and report
                try:
                    burn_test = resp_dict["burn_test"]
                    if burn_test == "True":
                        burn_test = True
                    elif burn_test == "False":
                        burn_test = False
                except Exception as e:
                    burn_test = False

                # Optional: enable_zero_kpis_when_inactive (see post_flx_tracker_create for semantics)
                try:
                    enable_zero_kpis_when_inactive = (
                        1 if int(resp_dict.get("enable_zero_kpis_when_inactive", 1)) else 0
                    )
                except (TypeError, ValueError):
                    enable_zero_kpis_when_inactive = 1

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint creates a new converging Flex Object tracker. Converging Flex trackers are correlated multi-KPI Flex trackers — a single tracker definition that drives multiple downstream KPI sub-trackers and aggregates their state. It requires a POST call with the following information:",
                "resource_desc": "Create a new converging Flex Object tracker (correlated multi-KPI tracker)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/admin/flx_converging_tracker_create\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'test:001', 'root_constraint': 'index=_internal sourcetype=splunkd', 'earliest_time': '-5m', 'latest_time': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "root_constraint": "REQUIRED. The Splunk root search constraint that defines the entity universe for this tracker",
                        "tracker_name": "OPTIONAL. The name of the tracker — value will prefix all entities under the format value:<entity>. Defaults to a randomly-generated name when omitted",
                        "owner": "OPTIONAL. The Splunk user owning the objects to be created. Defaults to the owner set for the tenant",
                        "cron_schedule": "OPTIONAL. The cron schedule for the tracker. Defaults to every 5 minutes ('*/5 * * * *')",
                        "earliest_time": "OPTIONAL. The earliest time value for the tracker. Defaults to '-5m'",
                        "latest_time": "OPTIONAL. The latest time value for the tracker. Defaults to 'now'",
                        "burn_test": "OPTIONAL. Create the report, run a performance test, then delete the report and return the performance results. Valid options are 'True' / 'False' (defaults to 'False')",
                        "enable_zero_kpis_when_inactive": "OPTIONAL. 0 or 1 (default: 1). When enabled, the FLX inactive entities tracker emits a 0 value for every numeric KPI in the entity's last-seen metrics dict (status stays = 2), keeping the Outliers Anomaly Detection chart continuous through inactivity windows.",
                        "update_comment": "OPTIONAL. Comment recorded in the audit log for this change. Defaults to 'API update' when omitted",
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
                license_active_flex_trackers = int(
                    check_license.get("license_active_flex_trackers")
                )
                logger.debug(
                    f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
                )

            except Exception as e:
                license_is_valid = 0
                license_subscription_class = "free"
                license_read_only = False
                license_active_flex_trackers = 32
                logger.error(f'function check_license exception="{str(e)}"')

            if license_read_only:
                return {
                    "payload": "I'm afraid I can't do that, this instance is currently in read-only mode and cannot create new trackers.",
                    "status": 402,
                }

            if license_subscription_class == "foundation":
                audit_record = {
                    "action": "failure",
                    "change_type": "add new Flex tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, the Foundation edition does not allow creating Flex trackers.",
                }

                logger.error(str(audit_record))
                return {"payload": audit_record, "status": 402}

            if license_active_flex_trackers >= 32 and (
                license_is_valid != 1 or license_subscription_class == "foundation"
            ):
                # Licensing restrictions reached
                audit_record = {
                    "action": "failure",
                    "change_type": "add new CIM tracker",
                    "tenant_id": str(tenant_id),
                    "result": f"I'm afraid I can't do that, the maximum number of 32 allowed trackers has been reached, there are {license_active_flex_trackers} active trackers currently for this component",
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
                        "/services/trackme/v2/splk_flx/admin/flx_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            #
            # step 1: define the search
            #

            # Define the search
            tracker_simulation_search = root_constraint

            logger.info(f"tracker_simulation_search={tracker_simulation_search}")

            tracker_simulation_search = f"""
            {tracker_simulation_search}
            | eval tracker_name = "{tracker_name}"
            | trackmesplkflxparse tenant_id="{tenant_id}" context="live"
            """.strip()
            #
            # burn test: execute the search directly and report the run time performance
            #

            if burn_test:
                burn_test_search = remove_leading_spaces(
                    tracker_simulation_search
                )

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
                f"trackme_flx_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
            )
            report_search = f"""
            {tracker_simulation_search}
            ``` set the table ```
            | eval time=if(isnull(_time), now(), _time)
            | table _time, group, object, alias, object_category, object_description, status, status_description, metrics, outliers_metrics, *
            | eval tracker_name="trackme_flx_hybrid_{tracker_name}_tracker_tenant_{tenant_id}"
            | eval tracker_runtime=now()
            ``` abstract macro ```
            | `trackme_flx_tracker_abstract({tenant_id})`
            ``` collects latest collection state into the summary index ```
            | `trackme_collect_state("current_state_tracking:splk-flx:{tenant_id}", "object", "{tenant_id}")`
            ``` output flipping change status if changes ```
            | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-flx"
            ```Generate splk outliers rules```
            | `set_splk_outliers_rules({tenant_id}, flx)`
            | `trackme_outputlookup(trackme_flx_tenant_{tenant_id}, key)`
            | stats count as report_entities_count, values(object) as report_objects_list by tenant_id
            | `register_tenant_component_summary_nofilter({tenant_id}, flx)`
            """.strip()

            # create a new report
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
            report_search = f"""
            | trackmetrackerexecutor tenant_id="{tenant_id}" component="splk-{component}" 
            report="trackme_{component}_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}" 
            alert_no_results=True
            """.strip()

            # create a new report
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
            "wrapper_report": wrapper_create_report.get("report_name"),
            "tracker_report": tracker_create_report.get("report_name"),
            "root_constraint": str(root_constraint),
            "tracker_name": str(tracker_name),
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
                tenant_hybrid_objects = vtenant_record.get("tenant_flx_hybrid_objects")

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
                vtenant_record["tenant_flx_hybrid_objects"] = json.dumps(
                    vtenant_dict, indent=1
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
                            "tracker_id": tracker_name,
                            "tracker_name": tracker_name,
                            "enable_zero_kpis_when_inactive": enable_zero_kpis_when_inactive,
                            "knowledge_objects": json.dumps(hybrid_dict, indent=1),
                        }
                    )
                )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{str(e)}"'
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
                "trackme_" + str(component) + "_hybrid_" + str(tracker_name),
                "hybrid_tracker",
                str(audit_record),
                "The hybrid tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        # final return
        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Update (in-place) an existing converging flx tracker
    def post_flx_converging_tracker_update(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_flx/admin/flx_converging_tracker_update" body="{'tenant_id': 'mytenant', 'tracker_name': 'mytracker', 'tenants_scope': 't1:dsm,t1:dhm', 'root_constraint': 'priority=high', 'consider_orange_as_up': True, 'min_pct_for_green': 100}"

        In-place modify of a converging Flex tracker: rebuilds the
        `trackmesplkflxconverging` command from the (current) fixed
        object/group/description plus the new editable fields, rewrites the
        wrapper saved-search SPL (preserving everything after the
        `| eval tracker_name = "..."` boundary) and updates the canonical
        command stored in the hybrid-tracker KV registry. The tracker_name,
        object, group and the wrapper/tracker reports stay unchanged so the
        entity keeps its history, outlier models and KV state.
        """

        tenant_id = None
        tracker_name = None
        describe = False
        update_comment = "API update"

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id")
                tracker_name = resp_dict.get("tracker_name")
                update_comment = resp_dict.get("update_comment", "API update")
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs an in-place modification of an existing converging Flex Object tracker. The tracker_name, object and group are fixed (use create+delete to change them); only the membership scope, member filter, orange-as-up and min-green-% are editable. It requires a POST call with the following information:",
                "resource_desc": "Update a converging Flex Object tracker in place",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/admin/flx_converging_tracker_update\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'mytracker', 'tenants_scope': 't1:dsm,t1:dhm', 'root_constraint': 'priority=high', 'consider_orange_as_up': True, 'min_pct_for_green': 100}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_name": "REQUIRED. The tracker identifier (tracker_id)",
                        "tenants_scope": "OPTIONAL. New tenants/components scope (CSV of tenant_id:component pairs). Defaults to the current value when omitted",
                        "root_constraint": "OPTIONAL. New member filter expression (TrackMe filter DSL). Empty string clears the filter. Defaults to the current value when omitted",
                        "consider_orange_as_up": "OPTIONAL. Whether orange members count as up. Defaults to the current value when omitted",
                        "min_pct_for_green": "OPTIONAL. Minimum availability %% for green. Defaults to the current value when omitted",
                        "update_comment": "OPTIONAL. Comment recorded in the audit log. Defaults to 'API update'",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if not tenant_id:
            return {"payload": {"action": "failure", "response": "tenant_id is required"}, "status": 500}
        if not tracker_name:
            return {"payload": {"action": "failure", "response": "tracker_name is required"}, "status": 500}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # check license state (same gating as create, minus the tracker-count
        # cap — an in-place update does not add a tracker)
        try:
            check_license = trackme_check_license(
                request_info.server_rest_uri,
                request_info.session_key,
                request_info.system_authtoken,
            )
            license_subscription_class = check_license.get("license_subscription_class")
            license_read_only = check_license.get("license_read_only", False)
        except Exception as e:
            license_subscription_class = "free"
            license_read_only = False
            logger.error(f'function check_license exception="{str(e)}"')

        if license_read_only:
            return {
                "payload": "I'm afraid I can't do that, this instance is currently in read-only mode and cannot modify trackers.",
                "status": 402,
            }
        if license_subscription_class == "foundation":
            return {
                "payload": {
                    "action": "failure",
                    "change_type": "modify converging Flex tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, the Foundation edition does not allow Flex trackers.",
                },
                "status": 402,
            }

        # Step 1: read the current canonical command from the KV registry
        try:
            collection_name = "kv_trackme_flx_hybrid_trackers_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]
            records = collection.data.query(
                query=json.dumps({"tracker_id": tracker_name})
            )
        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to query the hybrid tracker collection, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "response": error_msg}, "status": 500}

        if not records:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'tenant_id="{tenant_id}", tracker_name="{tracker_name}" was not found',
                },
                "status": 404,
            }

        record = records[0]
        record_key = record.get("_key")
        try:
            knowledge_objects = json.loads(record.get("knowledge_objects"))
        except Exception:
            knowledge_objects = {}

        properties = knowledge_objects.get("properties") or []
        properties_dict = properties[0] if properties else {}
        current_command = properties_dict.get("root_constraint", "")
        current = parse_converging_command(current_command)

        # Step 2: resolve the final editable values (provided value wins, else current).
        # object / group / object_description stay FIXED (from the current command).
        final_scope = resp_dict.get("tenants_scope")
        if final_scope is None:
            final_scope = current["tenants_scope"]

        final_filter = resp_dict.get("root_constraint")
        if final_filter is None:
            final_filter = current["root_constraint"]
        # the filter is user input embedded in SPL — strip injection metacharacters
        final_filter = sanitize_spl_input(final_filter) if final_filter else ""

        final_orange = resp_dict.get("consider_orange_as_up")
        if final_orange is None:
            final_orange = current["consider_orange_as_up"]

        final_min = resp_dict.get("min_pct_for_green")
        if final_min is None:
            final_min = current["min_pct_for_green"]

        # Step 3: rebuild the canonical command (shared builder → byte-identical to create)
        new_command = build_converging_command(
            tenants_scope=final_scope,
            object_name=current["object"],
            group=current["group"],
            root_constraint=final_filter,
            consider_orange_as_up=final_orange,
            min_pct_for_green=final_min,
            object_description=current["object_description"],
        )

        # Step 4: rewrite the wrapper saved-search SPL, preserving everything from
        # the `| eval tracker_name = "<tracker_name>"` boundary onward
        wrapper_name = f"trackme_flx_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
        try:
            wrapper_object = service.saved_searches[wrapper_name]
        except Exception:
            wrapper_object = None

        if not wrapper_object:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to retrieve the wrapper report, expected_report_name="{wrapper_name}"',
                },
                "status": 500,
            }

        wrapper_search = wrapper_object.content.get("search") or ""
        wrapper_earliest = wrapper_object.content.get("dispatch.earliest_time")
        wrapper_latest = wrapper_object.content.get("dispatch.latest_time")
        wrapper_schedule_window = wrapper_object.content.get("schedule_window")

        # locate the boundary marker (flexible on whitespace around '=')
        marker = re.search(
            r'\|\s*eval\s+tracker_name\s*=\s*"' + re.escape(tracker_name) + r'"',
            wrapper_search,
        )
        if not marker:
            return {
                "payload": {
                    "action": "failure",
                    "response": f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", could not locate the converging-command boundary in the wrapper search; refusing to rewrite to avoid corruption',
                },
                "status": 500,
            }

        new_wrapper_search = new_command + "\n" + wrapper_search[marker.start():]

        url = f"{request_info.server_rest_uri}/services/trackme/v2/configuration/admin/update_report"
        data = {
            "tenant_id": tenant_id,
            "report_name": wrapper_name,
            "report_search": new_wrapper_search,
            "earliest_time": wrapper_earliest,
            "latest_time": wrapper_latest,
            "schedule_window": wrapper_schedule_window,
        }
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Splunk {request_info.session_key}"},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to update the wrapper report, status={response.status_code}, response={response.text}'
                logger.error(error_msg)
                return {
                    "payload": {"action": "failure", "response": error_msg},
                    "status": 500,
                }
        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", exception updating the wrapper report, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"action": "failure", "response": error_msg}, "status": 500}

        # Step 5: persist the new canonical command into the KV registry
        try:
            if properties:
                properties[0]["root_constraint"] = new_command
            else:
                properties = [{"root_constraint": new_command}]
            knowledge_objects["properties"] = properties
            record["knowledge_objects"] = json.dumps(knowledge_objects, indent=1)
            collection.data.update(str(record_key), json.dumps(record))
        except Exception as e:
            logger.error(
                f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", wrapper SPL updated but failed to update the KV registry, exception="{str(e)}"'
            )

        # Step 6: audit
        audit_record = {
            "action": "success",
            "change_type": "modify converging Flex tracker",
            "tracker_name": str(tracker_name),
            "wrapper_report": wrapper_name,
            "old_root_constraint": str(current_command),
            "new_root_constraint": str(new_command),
        }
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "modify converging Flex tracker",
                "trackme_flx_hybrid_" + str(tracker_name),
                "hybrid_tracker",
                str(audit_record),
                "The converging Flex tracker was updated successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Remove an hybrid tracker and associated objects
    def post_flx_tracker_delete(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_flx/admin/flx_tracker_delete" body="{'tenant_id': 'mytenant', 'hybrid_trackers_list': 'test:001,test:002'}"
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
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/admin/flx_tracker_delete\" body=\"{'tenant_id': 'mytenant', 'hybrid_trackers_list': 'test:001,test:002'}\"",
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
                            "/services/trackme/v2/splk_flx/admin/flx_tracker_delete",
                        )
                        logger.info(f"trackme_send_to_tcm was successfully executed")
                    except Exception as e:
                        logger.error(
                            f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                        )

                # Data collection
                collection_name = "kv_trackme_flx_hybrid_trackers_tenant_" + str(
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
                                "tenant_flx_hybrid_objects"
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
                                "trackme_flx_hybrid_"
                                + str(hybrid_tracker)
                                + "_wrapper"
                                + "_tenant_"
                                + str(tenant_id)
                            )
                            report2 = (
                                "trackme_flx_hybrid_"
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
                                    f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", report="{report1}" not found in tenant_flx_hybrid_objects, skipping removal'
                                )
                            try:
                                reports.remove(str(report2))
                            except ValueError:
                                logger.warning(
                                    f'tenant_id="{tenant_id}", hybrid_tracker="{hybrid_tracker}", report="{report2}" not found in tenant_flx_hybrid_objects, skipping removal'
                                )

                            vtenant_dict = dict(
                                [
                                    ("reports", reports),
                                ]
                            )

                            # Update the KVstore
                            try:
                                vtenant_record["tenant_flx_hybrid_objects"] = (
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
                                    "payload": f"Warn: exception encountered: {str(e)}"
                                }

                    # Step 4: purge the register summary object
                    try:
                        delete_register_summary = trackme_delete_tenant_object_summary(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            "splk-flx",
                            "trackme_flx_hybrid_"
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

    # Rename a Flex Object group
    def post_flx_tracker_rename_group(self, request_info, **kwargs):

        # By tracker_name
        tenant_id = None
        tracker_name = None
        group_new_value = None
        metrics_migrate_earliest = None
        purge_entities = True
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
                    if not len(tenant_id) > 0:
                        return {
                            "payload": "tenant_id is required",
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "tenant_id is required",
                        "status": 500,
                    }

                try:
                    tracker_name = resp_dict["tracker_name"]
                    if not len(tracker_name) > 0:
                        return {
                            "payload": "tracker_name is required",
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "tracker_name is required",
                        "status": 500,
                    }

                try:
                    group_new_value = resp_dict["group_new_value"]
                    if not len(group_new_value) > 0:
                        return {
                            "payload": "group_new_value is required",
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "group_new_value is required",
                        "status": 500,
                    }

                try:
                    metrics_migrate_earliest = resp_dict["metrics_migrate_earliest"]
                    if not len(metrics_migrate_earliest) > 0:
                        metrics_migrate_earliest = "-90d"
                    else:
                        # check that this is a valid time relative format
                        if not re.match(r"^-\d*[smhdwy]$", metrics_migrate_earliest):
                            return {
                                "payload": "metrics_migrate_earliest is not in a valid time relative format, it should be expressed as -<any digit><s|m|h|d|w>, default is set to -90d",
                                "status": 500,
                            }
                except Exception as e:
                    metrics_migrate_earliest = "-90d"

                try:
                    purge_entities = resp_dict["purge_entities"]

                    # accept 0, 1, True, False (boolean) or true, false (string case insensitive), turn into boolean
                    if isinstance(purge_entities, str):
                        purge_entities = purge_entities.lower()
                        if purge_entities in ("true", "1"):
                            purge_entities = True
                        elif purge_entities in ("false", "0"):
                            purge_entities = False
                        else:
                            purge_entities = True
                    elif isinstance(purge_entities, int):
                        purge_entities = bool(purge_entities)
                    else:
                        purge_entities = True

                except Exception as e:
                    purge_entities = True  # default is True

                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs the renaming of a Flex object group and handle tasks associated this, it requires a POST call with the following information:",
                "resource_desc": "Rename a Flex object group",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_flx/admin/flx_tracker_rename_group\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'mytracker1', 'group_new_value': 'new_value', 'metrics_migrate_earliest': '-90d'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_name": "The name of the tracker, this should be the short name of the tracker, which come before _wrapper_<tenant_id>/_tracker_<tenant_id>",
                        "group_new_value": 'New group value, if the group is a string, it must be enclosed in double quotes such as "my_new_group", if the group is an eval expression, do not enclose in double quotes, it can also be a mix of both such as "my_new_group:" + myeval',
                        "metrics_migrate_earliest": "OPTIONAL: earliest time for the migration of the metrics, default is set to -90d",
                        "purge_entities": "OPTIONAL: boolean, if set to True, all entities associated with the group will be purged, default is set to True",
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

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # init actions_records
        actions_records = []

        ######################################
        # Step 1: identify the tracker objects
        ######################################

        # construct the full tracker name
        tracker_main_name = (
            f"trackme_flx_hybrid_{tracker_name}_tracker_tenant_{tenant_id}"
        )
        tracker_wrapper_name = (
            f"trackme_flx_hybrid_{tracker_name}_wrapper_tenant_{tenant_id}"
        )

        # for each, get the object
        try:
            tracker_main_object = service.saved_searches[tracker_main_name]
        except Exception as e:
            tracker_main_object = None

        try:
            tracker_wrapper_object = service.saved_searches[tracker_wrapper_name]
        except Exception as e:
            tracker_wrapper_object = None

        # if either object is missing, return
        if not tracker_main_object:
            return {
                "payload": f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to retrieve the tracker main object, expected_report_name="{tracker_main_name}"',
                "status": 500,
            }
        elif not tracker_wrapper_object:
            return {
                "payload": f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to retrieve the tracker wrapper object, expected_report_name="{tracker_wrapper_name}"',
                "status": 500,
            }

        # get the definition of the tracker
        tracker_wrapper_search = tracker_wrapper_object.content.get("search")
        tracker_wrapper_earliest_time = tracker_wrapper_object.content.get(
            "dispatch.earliest_time"
        )
        tracker_wrapper_latest_time = tracker_wrapper_object.content.get(
            "dispatch.latest_time"
        )
        tracker_wrapper_schedule_window = tracker_wrapper_object.content.get(
            "schedule_window"
        )

        # check that we have a group using regex, otherwise return an error
        logger.info(
            f'tenant_id="{tenant_id}", Checking for group definition in tracker wrapper search'
        )

        # Improved regex pattern to match various group definition formats
        group_pattern = r'(?i)(?:group\s*=\s*)(?:"[^"]*"|[^,\s\|]+)(?:\s*[\.\+\s\w]*)?(?=(?:,\s*\w+\s*=|\s*\|\s*\w+\s*=|\||$))'

        if not re.search(group_pattern, tracker_wrapper_search):
            error_msg = f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", Failed to identify the group in the tracker wrapper search, verify that the group is defined in the tracker wrapper search, expected_group_definition="group = <group_definition>"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": "identify_group_current_value",
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "tracker_name": tracker_name,
                    "message": error_msg,
                },
                "status": 500,
            }

        logger.info(
            f'tenant_id="{tenant_id}", Successfully identified group definition in tracker wrapper search'
        )

        ##########################################################################
        # Step 2: identify the current expended group associated with this tracker
        ##########################################################################

        # set task
        task = "identify_group_current_value"

        # init
        group_current_value = None

        # run a search to retrieve and build our entities dict
        search = f'| trackmegetcoll tenant_id={tenant_id} component=flx | where tracker_name="{tracker_main_name}" | stats count by group | fields group | head 1'
        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        logger.info(f'tenant_id="{tenant_id}", Attempting to execute search="{search}"')
        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs_oneshot,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):

                    # get the group value
                    group_current_value = item.get("group")

                    # log
                    msg = f'tenant_id="{tenant_id}", task={task}, execution was successful, group_current_value="{group_current_value}"'
                    logger.info(msg)
                    processed_count += 1
                    succcess_count += 1
                    actions_records.append(
                        {
                            "task": task,
                            "action": "success",
                            "tenant_id": tenant_id,
                            "search": search,
                            "message": f"task was executed successful",
                            "results": f'group_current_value="{group_current_value}"',
                        }
                    )

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", task={task}, group current value identification, failed to execute the search, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": f'failed to execute the search, exception="{str(e)}"',
                    "results": None,
                },
                "status": 500,
            }

        # if we failed to identify the group value, return
        if not group_current_value:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to identify the current group value, search="{search}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "result": "failed to identify the current group value",
                    "search": search,
                },
                "status": 500,
            }

        #######################################
        # Step 3: Update the tracker definition
        #######################################

        # set task
        task = "update_tracker_definition"

        # update the search definition, replace group = <anything> with group = <new_value>, take into account empty space surrounding the equal sign
        # the existing group definition can something likeL
        # group="mygroup"
        # group = "mygroup: " . myeval
        # group = myeval
        # group = "mygroup: " + myeval
        # group = "myeval:" . mygroup, myotherfield = "myotherfield"

        # we also need to take into account that double quotes can be escaped, and preserve them as escaped double quotes

        def update_group(tracker_current_search, group_new_value):

            search_is_remote = False
            # if the search contains "| splunkremotesearch", it is a remote search
            if re.search(r"\| splunkremotesearch", tracker_current_search):
                search_is_remote = True

            # Normalize group_new_value: determine if it's a plain string, quoted string, or eval expression
            group_new_value_normalized = group_new_value.strip()
            
            # Check if it's already a quoted string (starts and ends with double quotes)
            # Examples: "mygroup" (fully quoted string)
            is_fully_quoted = (
                len(group_new_value_normalized) >= 2 and
                group_new_value_normalized.startswith('"') and
                group_new_value_normalized.endswith('"')
            )
            
            # Check if it's an eval expression (contains concatenation operators)
            # Examples: "mygroup:" + myeval, "prefix:" . suffix, myeval
            # If it contains + or . operators, it's definitely an eval expression
            has_concatenation_operator = '+' in group_new_value_normalized or '.' in group_new_value_normalized
            
            # Determine if we need to add quotes
            # Rule 1: If already fully quoted, keep as-is
            # Rule 2: If it has concatenation operators, it's an eval expression - keep as-is
            # Rule 3: If it's a single unquoted word/identifier (like "cpu", "myeval"), it could be:
            #   - A plain string value that needs quotes: "cpu"
            #   - A field reference in eval: myeval (but this would typically be part of an expression)
            #   Since the user provides it as a standalone value, treat it as a plain string
            # Rule 4: If it contains spaces or special characters without quotes, it's likely a string that needs quotes
            
            needs_quotes = False
            if is_fully_quoted:
                # Already quoted, keep as-is
                needs_quotes = False
            elif has_concatenation_operator:
                # Eval expression with operators, keep as-is
                needs_quotes = False
            else:
                # Plain string value - needs quotes
                needs_quotes = True
            
            # Apply quotes if needed
            if needs_quotes:
                group_new_value_normalized = f'"{group_new_value_normalized}"'
            
            # If the search is remote, escape double quotes in the normalized value
            if search_is_remote:
                # Escape double quotes for remote search
                # First, unescape any existing escaped quotes to avoid double-escaping
                group_new_value_normalized = group_new_value_normalized.replace('\\"', '"')
                # Then escape all double quotes
                group_new_value_normalized = re.sub(r'"', r'\\"', group_new_value_normalized)

            # Replace the group value in the search
            # Match: group= followed by quoted string OR unquoted value, optionally followed by operators
            tracker_new_search = re.sub(
                r'(?i)(group\s*=\s*)(".*?"|\S+)(\s*[\.\+\s\w]*)?(?=(?:,\s*\w+\s*=|\s*\|\s*\w+\s*=|\||$))',
                rf"\1{group_new_value_normalized}",
                tracker_current_search,
            )

            # Restore newline if the replacement was at the end of a line
            tracker_new_search = re.sub(
                r"(\| eval group=.*?)(?=\||\Z)",  # Lookahead for next eval OR end of text
                r"\1\n",  # Ensure newline is kept
                tracker_new_search,
            )

            return tracker_new_search

        tracker_wrapper_new_search = update_group(
            tracker_wrapper_search, group_new_value
        )
        # update the search definition
        url = f"{request_info.server_rest_uri}/services/trackme/v2/configuration/admin/update_report"
        data = {
            "tenant_id": tenant_id,
            "report_name": tracker_wrapper_name,
            "report_search": tracker_wrapper_new_search,
            "earliest_time": tracker_wrapper_earliest_time,
            "latest_time": tracker_wrapper_latest_time,
            "schedule_window": tracker_wrapper_schedule_window,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Splunk {request_info.session_key}"},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'tenant_id="{tenant_id}", task={task}, failed to update the report definition, report={tracker_wrapper_name}, status={response.status_code}, response={response.text}'
                logger.error(error_msg)
                return {
                    "payload": {
                        "task": task,
                        "action": "failure",
                        "tenant_id": tenant_id,
                        "report_name": tracker_wrapper_name,
                        "search": tracker_wrapper_new_search,
                        "message": error_msg,
                    },
                    "status": 500,
                }

            else:
                processed_count += 1
                succcess_count += 1
                msg = f'tenant_id="{tenant_id}", task={task}, report="{tracker_wrapper_name}", group_new_value="{group_new_value}", action="success", the report definition was successfully updated'
                logger.info(msg)
                actions_records.append(
                    {
                        "task": task,
                        "action": "success",
                        "tenant_id": tenant_id,
                        "report_name": tracker_wrapper_name,
                        "search": tracker_wrapper_new_search,
                        "message": msg,
                    }
                )
                # sleep 5 seconds
                time.sleep(5)

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to update the report definition, report={tracker_wrapper_name}, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "report_name": tracker_wrapper_name,
                    "search": tracker_wrapper_new_search,
                    "message": error_msg,
                },
                "status": 500,
            }

        ######################################################################
        # Step 3: identify the new expended group associated with this tracker
        #######################################################################

        # set task
        task = "identify_group_new_value"

        def execute_tracker():

            # set task
            task = "execute_tracker"

            tracker_search = f"| savedsearch {tracker_main_name}"
            tracker_main_earliest_time = tracker_main_object.content.get(
                "dispatch.earliest_time"
            )
            tracker_main_latest_time = tracker_main_object.content.get(
                "dispatch.latest_time"
            )

            try:
                reader = run_splunk_search(
                    service,
                    tracker_search,
                    {
                        "earliest_time": tracker_main_earliest_time,
                        "latest_time": tracker_main_latest_time,
                        "output_mode": "json",
                        "count": 0,
                    },
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        msg = f'tenant_id="{tenant_id}", task={task}, tracker="{tracker_main_name}", execution was successful, results="{json.dumps(json.loads(item.get("_raw")), indent=2)}"'
                        logger.info(msg)
                        processed_count += 1
                        succcess_count += 1
                        actions_records.append(
                            {
                                "task": task,
                                "action": "success",
                                "tenant_id": tenant_id,
                                "tracker_name": tracker_main_name,
                                "search": tracker_search,
                                "message": msg,
                            }
                        )
                        # sleep 5 seconds
                        time.sleep(5)

            except Exception as e:
                error_msg = f'tenant_id="{tenant_id}", task={task}, tracker="{tracker_main_name}", failed to execute the tracker, search="{tracker_search}", exception="{str(e)}"'
                logger.error(error_msg)
                return {
                    "payload": {
                        "task": task,
                        "action": "failure",
                        "tenant_id": tenant_id,
                        "tracker_name": tracker_main_name,
                        "search": tracker_search,
                        "message": error_msg,
                    },
                    "status": 500,
                }

        # init
        group_new_expanded_value = None

        # run a search to retrieve and build our entities dict
        search = f'| trackmegetcoll tenant_id={tenant_id} component=flx | where tracker_name="{tracker_main_name}" | where group!="{group_current_value}" | stats count by group | fields group | head 1'
        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        # attempt to execute the tracker search and identify the new group, if failed, we will re-attempt 10 times waiting 5 seconds between each attempt
        for i in range(10):

            logger.info(
                f'tenant_id="{tenant_id}", Attempting to execute search="{search}"'
            )
            try:
                reader = run_splunk_search(
                    service,
                    search,
                    kwargs_oneshot,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):

                        # get the group value
                        group_new_expanded_value = item.get("group")

                        # log
                        msg = f'tenant_id="{tenant_id}", task={task}, execution was successful, group_new_expanded_value="{group_new_expanded_value}"'
                        logger.info(msg)
                        processed_count += 1
                        succcess_count += 1
                        actions_records.append(
                            {
                                "task": task,
                                "action": "success",
                                "tenant_id": tenant_id,
                                "search": search,
                                "message": f"task was executed successful",
                                "results": f'group_new_expanded_value="{group_new_expanded_value}"',
                            }
                        )

            except Exception as e:
                error_msg = f'tenant_id="{tenant_id}", task={task}, group current value identification, failed to execute the search, exception="{str(e)}"'
                logger.error(error_msg)
                return {
                    "payload": {
                        "task": task,
                        "action": "failure",
                        "tenant_id": tenant_id,
                        "search": search,
                        "message": f'failed to execute the search, exception="{str(e)}"',
                        "results": None,
                    },
                    "status": 500,
                }

            # if we failed to identify the group value, re-attempt
            if not group_new_expanded_value:
                time.sleep(5)
                execute_tracker()
                continue

            # if we have a value, break the loop
            break

        # if we failed to identify the group value, return
        if not group_new_expanded_value:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to identify the new expended group value, search="{search}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "result": "failed to identify the new expended group value",
                    "search": search,
                },
                "status": 500,
            }

        ##########################
        # Step 4: migrate entities
        ##########################

        # set task
        task = "migrate_entities"

        search = remove_leading_spaces(
            f"""\
                | mstats max(_value) as value where index=trackme_metrics tenant_id={tenant_id} metric_name="trackme.splk.flx.*" object="{group_current_value}*" by tenant_id, metric_name, object_category, object span=1m

                ``` replace the old group by the new group in object ```
                | rex field=object mode=sed "s/{group_current_value}/{group_new_value}/g"

                ``` lookup the new object_id in the KVstore ```
                | lookup trackme_flx_tenant_{tenant_id} object OUTPUT _key as object_id
                | where isnotnull(object_id) AND object_id!=""

                ``` convert metrics into fields ```
                | eval {{metric_name}}=value
                | fields - metric_name, value

                ``` call mcollect ```
                | mcollect index=trackme_metrics split=t tenant_id, object_category, object, object_id
            """
        )
        kwargs_oneshot = {
            "earliest_time": metrics_migrate_earliest,
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs_oneshot,
                24,
                5,
            )

            msg = f'tenant_id="{tenant_id}", task={task}, execution was successful'
            logger.info(msg)
            processed_count += 1
            succcess_count += 1
            actions_records.append(
                {
                    "task": task,
                    "action": "success",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": msg,
                }
            )

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to execute the search, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": error_msg,
                },
                "status": 500,
            }

        #############################
        # Step 5: migrate sla metrics
        #############################

        # set task
        task = "migrate_sla_metrics"

        search = remove_leading_spaces(
            f"""\
                | mstats max(_value) as value where index=trackme_metrics tenant_id={tenant_id} metric_name="trackme.sla.object_state" object="{group_current_value}*" by tenant_id, metric_name, object_category, object, alias, priority span=1m

                ``` replace the old group by the new group in object ```
                | rex field=object mode=sed "s/{group_current_value}/{group_new_value}/g"

                ``` lookup the new object_id in the KVstore ```
                | lookup trackme_flx_tenant_{tenant_id} object OUTPUT _key as object_id
                | where isnotnull(object_id) AND object_id!=""

                ``` convert metrics into fields ```
                | eval {{metric_name}}=value
                | fields - metric_name, value

                ``` call mcollect ```
                | mcollect index=trackme_metrics split=t tenant_id, object_category, object, object_id, alias, priority
            """
        )
        kwargs_oneshot = {
            "earliest_time": metrics_migrate_earliest,
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs_oneshot,
                24,
                5,
            )

            msg = f'tenant_id="{tenant_id}", task={task}, execution was successful'
            logger.info(msg)
            processed_count += 1
            succcess_count += 1
            actions_records.append(
                {
                    "task": task,
                    "action": "success",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": msg,
                }
            )

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to execute the search, search="{search}", exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": error_msg,
                },
                "status": 500,
            }

        ###################################
        # Step 7: migrate entities metadata
        ###################################

        # set task
        task = "migrate_entities_metadata"

        search = remove_leading_spaces(
            f"""\
                | inputlookup trackme_flx_tenant_{tenant_id} | eval keyid=_key | where group="{group_new_expanded_value}"

                ``` replace the old group by the new group in object ```
                | eval old_object=object
                | rex field=old_object mode=sed "s/{group_new_expanded_value}/{group_current_value}/g"

                ``` lookup the new object_id in the KVstore ```
                | lookup trackme_flx_tenant_{tenant_id} object as old_object OUTPUT ctime as orig_ctime, priority as orig_priority, tags as orig_tags, tags_manual as orig_tags_manual, sla_class as orig_sla_class
                | where isnotnull(orig_ctime) AND orig_ctime!=""

                ``` handle fields ```
                | eval priority=if(isnotnull(orig_priority) AND orig_priority!="", orig_priority, priority), ctime=if(isnotnull(orig_ctime) AND orig_ctime!="", orig_ctime, ctime), tags=if(isnotnull(orig_tags) AND orig_tags!="", orig_tags, tags), tags_manual=if(isnotnull(orig_tags_manual) AND orig_tags_manual!="", orig_tags_manual, tags_manual), sla_class=if(isnotnull(orig_sla_class) AND orig_sla_class!="", orig_sla_class, sla_class)
                | fields - orig_ctime, orig_priority, old_object, orig_tags, orig_tags_manual, orig_sla_class

                ``` call outputlookup ```
                | outputlookup trackme_flx_tenant_{tenant_id} append=t key_field=keyid
            """
        )

        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs_oneshot,
                24,
                5,
            )

            msg = f'tenant_id="{tenant_id}", task={task}, execution was successful'
            logger.info(msg)
            processed_count += 1
            succcess_count += 1
            actions_records.append(
                {
                    "task": task,
                    "action": "success",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": msg,
                }
            )

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to execute the search, search="{search}", exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": error_msg,
                },
                "status": 500,
            }

        ################################
        # Step 8: migrate outliers rules
        ################################

        # set task
        task = "migrate_outliers_rules"

        search = remove_leading_spaces(
            f"""\
                | inputlookup trackme_flx_outliers_entity_rules_tenant_{tenant_id}

                ``` replace the old group by the new group in object ```
                | rex field=object mode=sed "s/{group_current_value}/{group_new_value}/g"

                ``` lookup the new object_id in the KVstore ```
                | lookup trackme_flx_outliers_entity_rules_tenant_{tenant_id} object OUTPUT _key as object_id
                | where isnotnull(object_id) AND object_id!=""
                | fields - object_id

                ``` call outputlookup ```
                | outputlookup trackme_flx_outliers_entity_rules_tenant_{tenant_id} append=t
            """
        )

        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(
                service,
                search,
                kwargs_oneshot,
                24,
                5,
            )

            msg = f'tenant_id="{tenant_id}", task={task}, execution was successful'
            logger.info(msg)
            processed_count += 1
            succcess_count += 1
            actions_records.append(
                {
                    "task": task,
                    "action": "success",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": msg,
                }
            )

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", task={task}, failed to execute the search, search="{search}", exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "task": task,
                    "action": "failure",
                    "tenant_id": tenant_id,
                    "search": search,
                    "message": error_msg,
                },
                "status": 500,
            }

        ########################
        # Step 9: purge entities
        ########################

        if purge_entities:

            # set task
            task = "purge_entities"

            def get_collection_records(collection, group_current_value):

                collection_records = []
                collection_records_keys = set()
                collection_dict = {}

                end = False
                skip_tracker = 0
                while end == False:
                    process_collection_records = collection.data.query(
                        skip=skip_tracker
                    )
                    if len(process_collection_records) != 0:
                        for item in process_collection_records:
                            if (
                                item.get("_key") not in collection_records_keys
                                and item.get("group") == group_current_value
                            ):
                                collection_records.append(item)
                                collection_records_keys.add(item.get("_key"))
                                collection_dict[item.get("_key")] = item
                        skip_tracker += len(process_collection_records)
                    else:
                        end = True

                return collection_records, collection_records_keys, collection_dict

            # Connect to the KVstore
            collection_name = f"kv_trackme_flx_tenant_{tenant_id}"
            collection = service.kvstore[collection_name]

            # Get the records
            collection_records, collection_records_keys, collection_dict = (
                get_collection_records(collection, group_current_value)
            )

            # Call the endpoint /services/trackme/v2/splk_flx/write/flx_delete in post

            # turn collection_records_keys into a csv list
            keys_to_deleted = ",".join(collection_records_keys)

            url = f"{request_info.server_rest_uri}/services/trackme/v2/splk_flx/write/flx_delete"
            data = {
                "tenant_id": tenant_id,
                "report_name": tracker_wrapper_name,
                "keys_list": keys_to_deleted,
                "deletion_type": "temporary",
                "update_comment": update_comment,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f"Splunk {request_info.session_key}"},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 204):
                    error_msg = f'tenant_id="{tenant_id}", task={task}, failed to execute the deletion, status={response.status_code}, response="{response.text}"'
                    logger.error(error_msg)
                    return {
                        "payload": {
                            "task": task,
                            "action": "failure",
                            "tenant_id": tenant_id,
                            "message": error_msg,
                        },
                        "status": 500,
                    }

                else:
                    processed_count += 1
                    succcess_count += 1
                    msg = f'tenant_id="{tenant_id}", task={task}, action="success", the deletion was successfully executed'
                    logger.info(msg)
                    actions_records.append(
                        {
                            "task": task,
                            "action": "success",
                            "tenant_id": tenant_id,
                            "message": msg,
                        }
                    )

            except Exception as e:
                error_msg = f'tenant_id="{tenant_id}", task={task}, failed to execute the deletion, exception="{str(e)}"'
                logger.error(error_msg)
                return {
                    "payload": {
                        "task": task,
                        "action": "failure",
                        "tenant_id": tenant_id,
                        "message": error_msg,
                    },
                    "status": 500,
                }

        #
        # render results
        #

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "actions_records": actions_records,
        }

        if processed_count > 0 and processed_count == succcess_count:

            # Record an audit change
            try:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "rename Flex object group name",
                    f"new group={group_new_value}",
                    "flex_group_name",
                    actions_records,
                    f"The Flex object group name was successfully renamed to {group_new_value}",
                    str(update_comment),
                )
            except Exception as e:
                logger.error(
                    f'failed to generate an audit event with exception="{str(e)}"'
                )
            return {"payload": req_summary, "status": 200}

        else:
            # Record an audit change
            try:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "failure",
                    "rename Flex object group name",
                    f"new group={group_new_value}",
                    "flex_group_name",
                    actions_records,
                    f"The Flex object group name renaming was requested with new group={group_new_value} but errors were reported",
                    str(update_comment),
                )
            except Exception as e:
                logger.error(
                    f'failed to generate an audit event with exception="{str(e)}"'
                )
            return {"payload": req_summary, "status": 500}
