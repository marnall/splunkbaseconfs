#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_fqm.py"
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
import threading
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
    "trackme.rest.splk_fqm_admin", "trackme_rest_api_splk_fqm_admin.log"
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
    trackme_register_tenant_component_summary,
    trackme_reqinfo,
    trackme_send_to_tcm,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license

# import trackme libs croniter
from trackme_libs_croniter import validate_cron_schedule, add_minutes_to_cron

# import Splunk libs
import splunklib.client as client

# import trackme
import croniter

class TrackMeHandlerSplkFqmTrackingAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkFqmTrackingAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_fqm(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_fqm/admin",
            "resource_group_desc": "Endpoints specific to the splk-fqm TrackMe component (Splunk Flex objects tracking, admin operations)",
        }

        return {"payload": response, "status": 200}

    def register_component_summary_async(
        self, session_key, splunkd_uri, tenant_id, component
    ):
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logger.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logger.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    # Return and execute simulation searches
    def post_fqm_collect_job_simulation(self, request_info, **kwargs):

        # Helper function to handle double quote escaping for remote accounts
        def escape_double_quotes_for_remote(search_str):
            # replace any double quotes already escaped with a single backslash with triple escaped double quotes
            search_str = re.sub(r'(?<=\\)"', r'\\\\"', search_str)
            # replace any remaining standalone double quotes with escaped double quotes
            search_str = re.sub(r'(?<!\\)"', r'\\"', search_str)
            # replace any double quotes already escaped with a single backslash with triple escaped double quotes
            search_str = search_str.replace(r"\\\\\"", r"\\\"")
            return search_str

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
                    tracker_name = "fqm_" + uuid.uuid4().hex[:5]

                else:
                    # sanitize tracker name
                    tracker_name = (
                        tracker_name.lower().replace(" ", "-").replace(":", "-")[:40]
                    )
                    tracker_name = tracker_name + "_" + uuid.uuid4().hex[:5]

                # get account
                account = resp_dict["account"]

                # get search
                search_constraint = resp_dict["search_constraint"]

                # datamodel (must not be empty)
                try:
                    datamodel = resp_dict["datamodel"]
                    if not datamodel or len(datamodel) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for datamodel="{datamodel}", valid choices are: numeric',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'Invalid option for datamodel="{datamodel}", valid choices are: numeric',
                        },
                        "status": 500,
                    }
                
                # nodename (must not be empty)
                try:
                    nodename = resp_dict["nodename"]
                    if not nodename or len(nodename) == 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for nodename="{nodename}", valid choices are: numeric',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'Invalid option for nodename="{nodename}", valid choices are: numeric',
                        },
                        "status": 500,
                    }

                # search_type (raw or generating)
                try:
                    search_type = resp_dict["search_type"]
                    if search_type not in ("raw", "generating"):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for search_type="{search_type}", valid choices are: raw | generating',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'Invalid option for search_type="{search_type}", valid choices are: raw | generating',
                        },
                        "status": 500,
                    }
                
                # event limit (numeric)
                try:
                    event_limit = resp_dict["event_limit"]
                    if not event_limit.isdigit():
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for event_limit="{event_limit}", valid choices are: numeric',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    event_limit = 10000

                # sample hard limit (numeric)
                try:
                    raw_sample_hard_limit = resp_dict.get("sample_hard_limit", None)
                    if raw_sample_hard_limit is None:
                        sample_hard_limit = 10000
                    else:
                        if isinstance(raw_sample_hard_limit, str):
                            raw_sample_hard_limit = raw_sample_hard_limit.strip()
                        try:
                            sample_hard_limit = int(raw_sample_hard_limit)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for sample_hard_limit="{raw_sample_hard_limit}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                        if sample_hard_limit < 0:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for sample_hard_limit="{sample_hard_limit}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                except Exception as e:
                    sample_hard_limit = 10000

                # default fields success threshold for the simulation only
                try:
                    default_fields_success_threshold = resp_dict["default_fields_success_threshold"]
                    # if is string attempt to convert to numeric
                    if isinstance(default_fields_success_threshold, str):
                        try:
                            default_fields_success_threshold = float(default_fields_success_threshold)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for default_fields_success_threshold="{default_fields_success_threshold}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                    # must between 0 and 100
                    if default_fields_success_threshold < 0 or default_fields_success_threshold > 100:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for default_fields_success_threshold="{default_fields_success_threshold}", valid choices are: numeric',
                            },
                            "status": 500,
                        }
                    # convert to int if possible
                    if default_fields_success_threshold == int(default_fields_success_threshold):
                        default_fields_success_threshold = int(default_fields_success_threshold)
                except Exception as e:
                    default_fields_success_threshold = 85

                # recommended_fields (True/False)
                try:
                    recommended_fields = resp_dict["recommended_fields"]
                    if not isinstance(recommended_fields, bool):
                        if recommended_fields not in ("true", "True", "false", "False"):
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for recommended_fields="{recommended_fields}", valid choices are: true | false',
                                },
                                "status": 500,
                            }
                        if recommended_fields in ("true", "True"):
                            recommended_fields = True
                        elif recommended_fields in ("false", "False"):
                            recommended_fields = False
                except Exception as e:
                    recommended_fields = False

                # allow_unknown (True/False)
                try:
                    allow_unknown = resp_dict["allow_unknown"]
                    if not isinstance(allow_unknown, bool):
                        if allow_unknown not in ("true", "True", "false", "False"):
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for allow_unknown="{allow_unknown}", valid choices are: true | false',
                                },
                                "status": 500,
                            }
                        if allow_unknown in ("true", "True"):
                            allow_unknown = True
                        elif allow_unknown in ("false", "False"):
                            allow_unknown = False
                except Exception as e:
                    allow_unknown = False

                # allow_empty_or_missing (True/False)
                try:
                    allow_empty_or_missing = resp_dict["allow_empty_or_missing"]
                    if not isinstance(allow_empty_or_missing, bool):
                        if allow_empty_or_missing not in ("true", "True", "false", "False"):
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for allow_empty_or_missing="{allow_empty_or_missing}", valid choices are: true | false',
                                },
                                "status": 500,
                            }
                        if allow_empty_or_missing in ("true", "True"):
                            allow_empty_or_missing = True
                        elif allow_empty_or_missing in ("false", "False"):
                            allow_empty_or_missing = False
                except Exception as e:
                    allow_empty_or_missing = False

                # fields_to_check_search_command, can be specified to handle the generation of the dictionary
                try:
                    fields_to_check_search_command = resp_dict["fields_to_check_search_command"]
                except Exception as e:
                    fields_to_check_search_command = None
                
                if not fields_to_check_search_command:
                    fields_to_check_search_command = f"| trackmefieldsqualitygendict datamodel={datamodel} show_only_recommended_fields={recommended_fields} allow_unknown={allow_unknown} allow_empty_or_missing={allow_empty_or_missing}"

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

                # object_metadata_list, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname
                # object_metadata_list defines the list of fields used to generate the object value, in their order of precedence
                try:
                    object_metadata_list = resp_dict["object_metadata_list"]
                    # ensure not empty if specified
                    if not len(object_metadata_list) > 0:
                        object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"
                    # if is a list, convert to a comma separated string
                    if isinstance(object_metadata_list, list):
                        object_metadata_list = ",".join(object_metadata_list)
                except Exception as e:
                    object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns and executes simulation searches, it requires a POST call with the following information:",
                "resource_desc": "Return and execute hybrid tracker search for simulation purposes",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/admin/fqm_collect_job_simulation\" mode=\"post\" body=\"{'component': 'fqm', 'account': 'local', 'search_mode': 'tstats', 'earliest_time': '-4h', 'latest_time': '+4h', 'search_constraint': 'splunk_server=* sourcetype!=stash sourcetype!=*too_small sourcetype!=modular_alerts:trackme* sourcetype!=trackme:*'\"}",
                "options": [
                    {
                        "run_simulation": "Optional, Execute the simulation search or simply return the search syntax and other information, valid options are: true | false (default to true)",
                        "tracker_name": "The name of tracker, this value will prefix all entities under the format value:<entity>",
                        "account": "Splunk deployment, either local or a configured remote account",
                        "datamodel": "The datamodel to be used for the simulation, this value will be used to generate the recommended fields",
                        "object_metadata_list": "Optional, the list of fields used to generate the object value, in their order of precedence, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname",
                        "nodename": "The nodename to be used for the simulation, this value will be used to generate the recommended fields",
                        "search_constraint": "Splunk root search constraint, if using tstats mode all fields need to be indexed time fields",
                        "search_type": "The type of search, valid options are: raw | generating (default to raw)",
                        "event_limit": "The maximum number of events to retrieve, valid options are: numeric (default to 10000)",
                        "sample_hard_limit": "A hard limit of events that can be returned when using sampling mode, valid options are: numeric (default to 10000)",
                        "recommended_fields": "Optional, if true only recommended fields will be returned, if false all fields will be returned. Unused if fields_to_check_search_command is specified",
                        "default_fields_success_threshold": "Optional, the default threshold value for fields, defaults to 85. (integer or float value, from 0 to 100)",
                        "allow_unknown": "Optional, if true unknown field values will be allowed, if false unknown field values will be considered as failures. Unused if fields_to_check_search_command is specified",
                        "allow_empty_or_missing": "Optional, if true empty or missing field values will be allowed, if false empty or missing field values will be considered as failures. Unused if fields_to_check_search_command is specified",
                        "fields_to_check_search_command": "Optional, the search command to be used to generate the dictionary, if not specified the default command will be used",
                        "earliest_time": "The earliest time quantifier",
                        "latest_time": "The latest time quantifier",
                        "cron_schedule": "Optional, the cron schedule, if submitted in the context of simulation its validity will be verified.",
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

        # init
        tracker_simulation_search = None
        tracker_simulation_search_sample = None
        tracker_simulation_search_head = None

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
            root_search = f"{search_constraint}"
            tracker_simulation_search_sample_replaceme = f"{search_constraint} | head replace_sample_hard_limit | fields * | sort 0 _time"
            tracker_simulation_search_head = f"{search_constraint} | head {event_limit} | fields * | sort 0 _time"
            tracker_simulation_search_head_replaceme = f"{search_constraint} | head replace_head_limit | fields * | sort 0 _time"

            # If account is remote
            if account != "local":
                root_search = escape_double_quotes_for_remote(root_search)
                # set search
                tracker_simulation_search_sample_replaceme = f"| splunkremotesearch account=\"{account}\" search=\"{root_search} | head replace_sample_hard_limit | fields * | sort 0 _time\" earliest=\"{earliest_time}\" latest=\"{latest_time}\" sample_ratio=replace_sample_ratio"
                tracker_simulation_search_head = f"| splunkremotesearch account=\"{account}\" search=\"{root_search} | head {event_limit} | fields * | sort 0 _time\" earliest=\"{earliest_time}\" latest=\"{latest_time}\""
                tracker_simulation_search_head_replaceme = f"| splunkremotesearch account=\"{account}\" search=\"{root_search} | head replace_head_limit | fields * | sort 0 _time\" earliest=\"{earliest_time}\" latest=\"{latest_time}\""

            # handle the metadata fields value based on object_metadata_list:
            # 1 - turn the csv list into a list
            # 2 - for each item in the list, remove the prefix metadata.
            # 3 - remove index, sourcetype and fieldname which are not needed explicitly
            # 4 - convert the list into a csv string

            object_metadata_list_for_collect = object_metadata_list
            object_metadata_list_for_collect = object_metadata_list_for_collect.split(",")
            object_metadata_list_for_collect = [item.replace("metadata.", "") for item in object_metadata_list_for_collect]
            object_metadata_list_for_collect = [item for item in object_metadata_list_for_collect if item not in ["index", "sourcetype", "fieldname"]]
            object_metadata_list_for_collect = ",".join(object_metadata_list_for_collect)
            logger.debug(f"object_metadata_list_for_collect={object_metadata_list_for_collect}, object_metadata_list={object_metadata_list}")

            # basesearch
            base_search = remove_leading_spaces(f"""
                {tracker_simulation_search_head}
                | eval datamodel="{datamodel}", nodename="{nodename}"
                | trackmefieldsquality fields_to_check_search_command="{fields_to_check_search_command}" output_mode=json metadata_fields="{object_metadata_list_for_collect}" include_field_values=True
                | table _time, _raw
                ``` This prevents null bytes from reaching the extract command ```
                | where NOT match(_raw, "\\x00")
                | trackmefieldsqualityextract
                | `trackme_fqm_get_description_extended`
                | stats values(description) as description, count as count_total, count(eval(status=="success")) as count_success, count(eval(status=="failure")) as count_failure by {object_metadata_list}
                | eval percentage_success=round(count_success/count_total*100, 2)
                ``` set the threshold per field, this defines if the field is considered as passed or failed globally, this threshold has to be part of the SPL logic ```
                | eval threshold={default_fields_success_threshold}
                ``` flag field ```
                | eval fieldstatus=if(percentage_success>=threshold, "success", "failure")
                ``` join field summary ```                
                """).strip()
            
            join_root_search = None
            if search_type == "raw" and account == "local":
                join_root_search = f'search {tracker_simulation_search_head}'
            elif search_type == "generating" or account != "local":
                join_root_search = f'{tracker_simulation_search_head}'
            
            join_search = remove_leading_spaces(f"""
                | join type=outer {object_metadata_list} 
                [ {join_root_search}
                | eval datamodel="{datamodel}", nodename="{nodename}"
                | trackmefieldsquality fields_to_check_search_command="{fields_to_check_search_command}" output_mode=json metadata_fields="{object_metadata_list_for_collect}" include_field_values=True
                | table _time, _raw
                ``` This prevents null bytes from reaching the extract command ```
                | where NOT match(_raw, "\\x00")
                | trackmefieldsqualityextract
                | table _time, {object_metadata_list}, value, regex_expression
                ``` sort is mandatory to force all records to be retrieved before we call the gen summary command ```
                | sort 0 _time
                | trackmefieldsqualitygensummary maxvals=15 fieldvalues_format=csv groupby_metadata_fields="{object_metadata_list}"
                | fields {object_metadata_list}, total_events, distinct_value_count, percent_coverage, field_values, regex_expression | fields - _time, _raw ]
            """).strip()

            end_search = remove_leading_spaces(f"""
                ``` end join ```
                ``` set as an mvfield ```
                | eval field_values=split(field_values, ",")
                """).strip()

            # tracker_simulation_search
            tracker_simulation_search = remove_leading_spaces(f"""
                {base_search}
                {join_search}
                {end_search}
                """).strip()

            logger.debug(f'tracker_simulation_search="{tracker_simulation_search}"')

            # simulation breaby_statement, defaults to index, sourcetype
            # if the object_metadata_list differs from the default, extract each non-default field, remove "metadata." prefix
            # and add to the simulation_breakby_statement (ex: index, sourcetype, myfield)
            simulation_breakby_statement = "index, sourcetype"
            if object_metadata_list != "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname":
                for field in object_metadata_list.split(","):
                    if field != "metadata.datamodel" and field != "metadata.nodename" and field != "metadata.index" and field != "metadata.sourcetype" and field != "fieldname":
                        simulation_breakby_statement += ", " + field.replace("metadata.", "")

            # add to response
            response["tracker_simulation_search"] = remove_leading_spaces(
                tracker_simulation_search
            )
            response["tracker_simulation_search_sample_replaceme"] = remove_leading_spaces(
                tracker_simulation_search_sample_replaceme
            )
            response["tracker_simulation_search_head_replaceme"] = remove_leading_spaces(
                tracker_simulation_search_head_replaceme
            )
            response["simulation_breakby_statement"] = simulation_breakby_statement

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

    # Return and execute simulation searches (monitor phase only)
    def post_fqm_collect_job_monitor_only_simulation(self, request_info, **kwargs):

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
                    tracker_name = "fqm_" + uuid.uuid4().hex[:5]

                else:
                    # sanitize tracker name
                    tracker_name = (
                        tracker_name.lower().replace(" ", "-").replace(":", "-")[:40]
                    )
                    tracker_name = tracker_name + "_" + uuid.uuid4().hex[:5]

                # get search
                search_constraint = resp_dict["search_constraint"]

                # default fields success threshold for the simulation only
                try:
                    default_fields_success_threshold = resp_dict["default_fields_success_threshold"]
                    # if is string attempt to convert to numeric
                    if isinstance(default_fields_success_threshold, str):
                        try:
                            default_fields_success_threshold = float(default_fields_success_threshold)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for default_fields_success_threshold="{default_fields_success_threshold}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                    # must between 0 and 100
                    if default_fields_success_threshold < 0 or default_fields_success_threshold > 100:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'Invalid option for default_fields_success_threshold="{default_fields_success_threshold}", valid choices are: numeric',
                            },
                            "status": 500,
                        }
                    # convert to int if possible
                    if default_fields_success_threshold == int(default_fields_success_threshold):
                        default_fields_success_threshold = int(default_fields_success_threshold)
                except Exception as e:
                    default_fields_success_threshold = 85

                # sample hard limit (numeric)
                try:
                    raw_sample_hard_limit = resp_dict.get("sample_hard_limit", None)
                    if raw_sample_hard_limit is None:
                        sample_hard_limit = 10000
                    else:
                        if isinstance(raw_sample_hard_limit, str):
                            raw_sample_hard_limit = raw_sample_hard_limit.strip()
                        try:
                            sample_hard_limit = int(raw_sample_hard_limit)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for sample_hard_limit="{raw_sample_hard_limit}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                        if sample_hard_limit < 0:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for sample_hard_limit="{sample_hard_limit}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                except Exception as e:
                    sample_hard_limit = 10000

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

                # object_metadata_list, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname
                # object_metadata_list defines the list of fields used to generate the object value, in their order of precedence
                try:
                    object_metadata_list = resp_dict["object_metadata_list"]
                    # ensure not empty if specified
                    if not len(object_metadata_list) > 0:
                        object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"
                    # if is a list, convert to a comma separated string
                    if isinstance(object_metadata_list, list):
                        object_metadata_list = ",".join(object_metadata_list)
                except Exception as e:
                    object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns and executes simulation searches for a monitor phase only job, it requires a POST call with the following information:",
                "resource_desc": "Return and execute hybrid tracker search for simulation purposes",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_fqm/admin/fqm_collect_job_monitor_only_simulation\" mode=\"post\" body=\"{'component': 'fqm', 'account': 'local', 'search_mode': 'tstats', 'earliest_time': '-4h', 'latest_time': '+4h', 'search_constraint': 'splunk_server=* sourcetype!=stash sourcetype!=*too_small sourcetype!=modular_alerts:trackme* sourcetype!=trackme:*'\"}",
                "options": [
                    {
                        "run_simulation": "Optional, Execute the simulation search or simply return the search syntax and other information, valid options are: true | false (default to true)",
                        "tracker_name": "The name of tracker, this value will prefix all entities under the format value:<entity>",
                        "object_metadata_list": "Optional, the list of fields used to generate the object value, in their order of precedence, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname",
                        "search_constraint": "Splunk root search constraint, if using tstats mode all fields need to be indexed time fields",
                        "sample_hard_limit": "A hard limit of events that can be returned when using sampling mode, valid options are: numeric (default to 10000)",
                        "default_fields_success_threshold": "Optional, the default threshold value for fields, defaults to 85. (integer or float value, from 0 to 100)",
                        "earliest_time": "The earliest time quantifier",
                        "latest_time": "The latest time quantifier",
                        "cron_schedule": "Optional, the cron schedule, if submitted in the context of simulation its validity will be verified.",
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

        # init
        tracker_simulation_search = None

        # proceed
        try:
            # init
            response = {
                "run_simulation": run_simulation,
                "tracker_name": tracker_name,
                "search_constraint": search_constraint,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
            }         

            # tracker_simulation_search
            tracker_simulation_search = remove_leading_spaces(f"""
                {search_constraint} | fields * | sort 0 _time
                | trackmefieldsqualityextract
                | `trackme_fqm_get_description_extended`
                | stats values(description) as description, count as count_total, count(eval(status=="success")) as count_success, count(eval(status=="failure")) as count_failure by {object_metadata_list}
                | eval percentage_success=round(count_success/count_total*100, 2)
                ``` set the threshold per field, this defines if the field is considered as passed or failed globally, this threshold has to be part of the SPL logic ```
                | eval threshold={default_fields_success_threshold}
                ``` flag field ```
                | eval fieldstatus=if(percentage_success>=threshold, "success", "failure")
                ``` join field summary ```
                | join type=outer {object_metadata_list}
                [ search {search_constraint} | fields * | sort 0 _time
                | trackmefieldsqualityextract
                | table _time, {object_metadata_list}, value, regex_expression
                ``` sort is mandatory to force all records to be retrieved before we call the gen summary command ```
                | sort 0 _time
                | trackmefieldsqualitygensummary maxvals=15 fieldvalues_format=csv groupby_metadata_fields="{object_metadata_list}"
                | fields {object_metadata_list}, total_events, distinct_value_count, percent_coverage, field_values, regex_expression | fields - _time, _raw ]
                ``` end join ```
                ``` set as an mvfield ```
                | eval field_values=split(field_values, ",")
                """).strip()

            logger.debug(f'tracker_simulation_search="{tracker_simulation_search}"')

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

    # Create a collect job
    def post_fqm_collect_job_create(self, request_info, **kwargs):
        describe = False

        # Helper function to handle double quote escaping for remote accounts
        def escape_double_quotes_for_remote(search_str):
            # replace any double quotes already escaped with a single backslash with triple escaped double quotes
            search_str = re.sub(r'(?<=\\)"', r'\\\\"', search_str)
            # replace any remaining standalone double quotes with escaped double quotes
            search_str = re.sub(r'(?<!\\)"', r'\\"', search_str)
            # replace any double quotes already escaped with a single backslash with triple escaped double quotes
            search_str = search_str.replace(r"\\\\\"", r"\\\"")
            return search_str

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
                try:
                    tenant_id = resp_dict["tenant_id"]
                    # ensure not empty
                    if not len(tenant_id) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'tenant_id is required and cannot be empty',
                            },
                            "status": 500
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'tenant_id is required',
                        },
                        "status": 500,
                    }

                # component (static)
                component = "fqm"

                # tracker name
                try:
                    tracker_name = resp_dict["tracker_name"]                    
                except Exception as e:
                    tracker_name = None

                if not tracker_name or len(tracker_name) == 0:
                    # generate a random tracker name
                    tracker_name = "fqm_" + uuid.uuid4().hex[:5]

                else:
                    # sanitize tracker name
                    tracker_name = (
                        tracker_name.lower().replace(" ", "-").replace(":", "-")[:40]
                    )
                    tracker_name = tracker_name + "_" + uuid.uuid4().hex[:5]

                # remote account
                account = resp_dict["account"]

                # get search constraint
                try:
                    search_constraint = resp_dict["search_constraint"]
                    # ensure not empty
                    if not len(search_constraint) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'search_constraint is required and cannot be empty',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'search_constraint is required',
                        },
                        "status": 500,
                    }
                
                # collect strategy
                try:
                    collect_strategy = resp_dict["collect_strategy"]
                    if collect_strategy not in ("head", "sampling"):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'collect_strategy is required and must be either "head" or "sampling"',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'collect_strategy is required, valid options are: head | sampling',
                        },
                        "status": 500,
                    }

                # collect limiter
                try:
                    collect_limiter = int(resp_dict["collect_limiter"])
                    if not collect_limiter > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'collect_limiter is required and must be greater than 0',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'collect_limiter is required, must be a positive numeric value',
                        },
                        "status": 500,
                    }

                # sample hard limit (numeric)
                try:
                    raw_sample_hard_limit = resp_dict.get("sample_hard_limit", None)
                    if raw_sample_hard_limit is None:
                        sample_hard_limit = 10000
                    else:
                        if isinstance(raw_sample_hard_limit, str):
                            raw_sample_hard_limit = raw_sample_hard_limit.strip()
                        try:
                            sample_hard_limit = int(raw_sample_hard_limit)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for sample_hard_limit="{raw_sample_hard_limit}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                        if sample_hard_limit < 0:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'Invalid option for sample_hard_limit="{sample_hard_limit}", valid choices are: numeric',
                                },
                                "status": 500,
                            }
                except Exception as e:
                    sample_hard_limit = 10000
                
                # datamodel
                try:
                    datamodel = resp_dict["datamodel"]
                    # ensure not empty
                    if not len(datamodel) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'datamodel is required and cannot be empty',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'datamodel is required',
                        },
                        "status": 500,
                    }
                
                # nodename
                try:
                    nodename = resp_dict["nodename"]
                    # ensure not empty
                    if not len(nodename) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'nodename is required and cannot be empty',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'nodename is required',
                        },
                        "status": 500,
                    }
                
                # dictionary_create_new (boolean)
                try:
                    dictionary_create_new = resp_dict["dictionary_create_new"]
                    if isinstance(dictionary_create_new, str):
                        # check and convert to boolean
                        if dictionary_create_new.lower() in ("true", "1"):
                            dictionary_create_new = True
                        else:
                            dictionary_create_new = False
                    else:
                        dictionary_create_new = bool(dictionary_create_new)
                    if not isinstance(dictionary_create_new, bool):
                        dictionary_create_new = False
                except Exception as e:
                    dictionary_create_new = False

                # dictionary_name
                try:
                    dictionary_name = resp_dict["dictionary_name"]
                    # ensure not empty
                    if not len(dictionary_name) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'dictionary_name is required and cannot be empty, set to new to create a new dictionary',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'dictionary_name is required',
                        },
                        "status": 500,
                    }
                
                # dictionary_json, used and required if dictionary_create_new is True
                dictionary_json = None
                if dictionary_create_new:
                    try:
                        dictionary_json = resp_dict["dictionary_json"]
                        if not len(dictionary_json) > 0:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'dictionary_json is required and cannot be empty if creating a new dictionary',
                                },
                                "status": 500,
                            }
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'dictionary_json is required if creating a new dictionary',
                            },
                            "status": 500,
                        }
                    
                    # check and load as a JSON if not already an object
                    if isinstance(dictionary_json, str):
                        try:
                            dictionary_json = json.loads(dictionary_json)
                        except Exception as e:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'dictionary_json is not a valid JSON object',
                                },
                                "status": 500,
                            }
                    else:
                        dictionary_json = None
    
                #
                # optional args
                #

                # object_metadata_list, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname
                # object_metadata_list defines the list of fields used to generate the object value, in their order of precedence
                try:
                    object_metadata_list = resp_dict["object_metadata_list"]
                    # ensure not empty if specified
                    if not len(object_metadata_list) > 0:
                        object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"
                    # if is a list, convert to a comma separated string
                    if isinstance(object_metadata_list, list):
                        object_metadata_list = ",".join(object_metadata_list)
                except Exception as e:
                    object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"

                # default_threshold_fields, defaults to 99 (must be a numeric value)
                try:
                    default_threshold_fields = resp_dict["default_threshold_fields"]
                    try:
                        default_threshold_fields = float(default_threshold_fields)
                        if default_threshold_fields < 0 or default_threshold_fields > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_threshold_fields is required and must be a numeric value between 0 and 100',
                                },
                                "status": 500,
                            }
                        # round to an integer if possible
                        if default_threshold_fields == int(default_threshold_fields):
                            default_threshold_fields = int(default_threshold_fields)
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_threshold_fields is required and must be a numeric value',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'default_threshold_fields is required and must be a numeric value',
                        },
                        "status": 500,
                    }
                    
                # default_threshold_global, defaults to 100 (must be a numeric value)
                try:
                    default_threshold_global = resp_dict["default_threshold_global"]
                    try:
                        default_threshold_global = float(default_threshold_global)
                        if default_threshold_global < 0 or default_threshold_global > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_threshold_global is required and must be a numeric value between 0 and 100',
                                },
                                "status": 500,
                            }
                        # round to an integer if possible
                        if default_threshold_global == int(default_threshold_global):
                            default_threshold_global = int(default_threshold_global)
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_threshold_global is required and must be a numeric value',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'default_threshold_global is required and must be a numeric value',
                        },
                        "status": 500,
                    }

                # default_score_fields, defaults to 100 (must be an integer between 0 and 100)
                try:
                    default_score_fields = resp_dict.get("default_score_fields", 100)
                    try:
                        default_score_fields = int(default_score_fields)
                        if default_score_fields < 0 or default_score_fields > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_score_fields must be an integer between 0 and 100',
                                },
                                "status": 500,
                            }
                    except (ValueError, TypeError):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_score_fields must be an integer between 0 and 100',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    default_score_fields = 100
                
                # default_score_global, defaults to 100 (must be an integer between 0 and 100)
                try:
                    default_score_global = resp_dict.get("default_score_global", 100)
                    try:
                        default_score_global = int(default_score_global)
                        if default_score_global < 0 or default_score_global > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_score_global must be an integer between 0 and 100',
                                },
                                "status": 500,
                            }
                    except (ValueError, TypeError):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_score_global must be an integer between 0 and 100',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    default_score_global = 100

                # summary_index (defaults to summary if not specified)
                try:
                    summary_index = resp_dict["summary_index"]
                    # ensure not empty if specified
                    if not len(summary_index) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'summary_index is required and cannot be empty',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    summary_index = "summary"

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "10 2 * * *"

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

                # earliest_time and latest_time for the tracker, if not specified, defaults to -5m / +4h for fqm|dhm and -5m/+5m for fqm
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-24h"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "now"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a new Quality Fields Collect Job, it requires a POST call with the following information:",
                "resource_desc": "Create a new Quality Fields Collect Job",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/admin/fqm_collect_job_create\" body=\"{<TBD>}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "tracker_name": "The name of tracker, this value will prefix all entities under the format value:<entity>",
                        "account": "name of remote Splunk deployment account as configured in TrackMe",
                        "default_threshold_fields": "The default threshold for fields, must be a numeric value between 0 and 100",
                        "default_threshold_global": "The default threshold for the global entity, must be a numeric value between 0 and 100",
                        "object_metadata_list": "Optional, the list of fields used to generate the object value, in their order of precedence, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname",
                        "search_constraint": "The search constraint to be used for the collect job",
                        "collect_strategy": "The collect strategy to be used for the collect job, valid options are: head | sampling",
                        "collect_limiter": "The collect limiter to be used for the collect job, must be a positive numeric value",
                        "sample_hard_limit": "A hard limit of events that can be returned when using sampling mode, valid options are: numeric (default to 10000)",
                        "datamodel": "The datamodel to be used for the collect job",
                        "nodename": "The nodename to be used for the collect job",
                        "dictionary_create_new": "Whether to create a new dictionary, if True, dictionary_name and dictionary_json are required",
                        "dictionary_name": "The name of the dictionary to be used for the collect job, required if dictionary is new",
                        "dictionary_json": "The JSON object to be used for the dictionary collect job, required if dictionary is new",
                        "owner": "Optional, the Splunk user owning the objects to be created, defaults to the owner set for the tenant",
                        "cron_schedule": "Optional, the cron schedule, defaults to every 5 minutes",
                        "earliest_time": "Optional, the earliest time value for the tracker, defaults to -5m for fqm|dhm and -5m for fqm",
                        "latest_time": "Optional, the latest time value for the tracker, defaults to +4h for fqm|dhm and +5m for fqm",
                        "summary_index": "Optional, the index to be used for the summary, defaults to summary",
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
                    "change_type": "add new FQM tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, the Foundation edition does not allow creating FQM trackers.",
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
                        "/services/trackme/v2/splk_fqm/admin/fqm_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # connect to the dictionary KVstore collection
            collection_dictionaries_name = "kv_trackme_fqm_data_dictionary_tenant_" + str(tenant_id)
            collection_dictionaries = service.kvstore[collection_dictionaries_name]

            #
            # step 1: handle the dictionary
            #

            # if dictionary_create_new is True, verify first if an existing dictionary with the same name exists, raise an error if it does
            if dictionary_create_new:
                try:
                    dictionary_record = collection_dictionaries.data.query(
                        query=json.dumps({"dictionary_name": dictionary_name})
                    )[0]
                except Exception as e:
                    dictionary_record = None

                if dictionary_record:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'dictionary_name="{dictionary_name}" already exists, cannot create a new dictionary with the same name',
                        },
                        "status": 500,
                    }
                
                else:

                    # create a new dictionary
                    try:
                        record = {
                            "name": dictionary_name,
                            "json_dict": json.dumps(dictionary_json, indent=2),
                            "mtime": time.time(),
                        }
                        dictionary_record = collection_dictionaries.data.insert(json.dumps(record))
                        logger.info(f'tenant_id="{tenant_id}", dictionary_name="{dictionary_name}" created successfully, collection_dictionaries_name="{collection_dictionaries_name}"')
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'failed to create the dictionary, exception="{str(e)}"',
                            },
                            "status": 500,
                        }

            # set the value for fields_to_check_search_command
            fields_to_check_search_command = f'| inputlookup trackme_fqm_data_dictionary_tenant_{tenant_id} where name=\"{dictionary_name}\" | head 1 | table json_dict'

            #
            # step 2: define the search
            #

            # basesearch
            base_search = None

            if account == "local":
                if collect_strategy == "head":
                    base_search = f"{search_constraint} | head {collect_limiter}"
                elif collect_strategy == "sampling":
                    base_search = f"{search_constraint} | head {sample_hard_limit} | fields * | sort 0 _time"

            else:
                base_search = escape_double_quotes_for_remote(search_constraint)

                if collect_strategy == "head":
                    base_search = f"{search_constraint} | head {collect_limiter} | fields * | sort 0 _time"
                    base_search = f"""
                    | splunkremotesearch account="{account}" search="{base_search}"
                    earliest="{earliest_time}" latest="{latest_time}" tenant_id="{tenant_id}"
                    register_component="True" component="splk-fqm" report="trackme_fqm_collect_{tracker_name}_wrapper_tenant_{tenant_id}"
                    """.strip()

                elif collect_strategy == "sampling":
                    base_search = f"{search_constraint} | head {sample_hard_limit} | fields * | sort 0 _time"
                    base_search = f"""
                    | splunkremotesearch account="{account}" search="{base_search}"
                    earliest="{earliest_time}" latest="{latest_time}" sample_ratio={collect_limiter} tenant_id="{tenant_id}"
                    register_component="True" component="splk-fqm" report="trackme_fqm_collect_{tracker_name}_wrapper_tenant_{tenant_id}"
                    """.strip()

            logger.debug(f"tenant_id={tenant_id}, base_search={base_search}")

            # add the rest of the query

            # handle the metadata fields value based on object_metadata_list:
            # 1 - turn the csv list into a list
            # 2 - for each item in the list, remove the prefix metadata.
            # 3 - remove index, sourcetype and fieldname which are not needed explicitly
            # 4 - convert the list into a csv string

            object_metadata_list_for_collect = object_metadata_list
            object_metadata_list_for_collect = object_metadata_list_for_collect.split(",")
            object_metadata_list_for_collect = [item.replace("metadata.", "") for item in object_metadata_list_for_collect]
            object_metadata_list_for_collect = [item for item in object_metadata_list_for_collect if item not in ["index", "sourcetype", "fieldname"]]
            object_metadata_list_for_collect = ",".join(object_metadata_list_for_collect)
            logger.debug(f"tenant_id={tenant_id}, object_metadata_list_for_collect={object_metadata_list_for_collect}, object_metadata_list={object_metadata_list}")

            base_search = f"""
                {base_search}
                | eval datamodel="{datamodel}", nodename="{nodename}"
                | trackmefieldsquality fields_to_check_search_command="{fields_to_check_search_command}" output_mode=json metadata_fields="{object_metadata_list_for_collect}" include_field_values=True
                | collect index={summary_index} sourcetype=trackme:fields_quality source=\"trackme:quality:{tracker_name}\"
                """

            #
            # step 3: create the wrapper for the collect job
            #

            report_name = (
                f"trackme_fqm_collect_{tracker_name}_wrapper_tenant_{tenant_id}"
            )
            report_search = f"""
            {base_search}
            | stats count as report_results_count
            | `register_tenant_component_summary_fqm_collect_job({tenant_id}, fqm)`
            """.strip()

            # create a new report
            report_properties = {
                "description": "TrackMe Fields Quality collect job wrapper",
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
                "is_scheduled": False,
            }

            # sample ratio management, only for account=local and if collect_strategy=sampling
            if account == "local" and collect_strategy == "sampling":
                report_properties["dispatch.sample_ratio"] = collect_limiter

            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            collect_wrapper_create_report = trackme_create_report(
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
            # step 4: create the tracker for the collect job
            #

            report_name = (
                f"trackme_{component}_collect_{tracker_name}_tracker_tenant_{tenant_id}"
            )
            report_search = f"""
            | trackmetrackerexecutor tenant_id="{tenant_id}" component="splk-{component}" 
            report="trackme_{component}_collect_{tracker_name}_wrapper_tenant_{tenant_id}" 
            alert_no_results=True
            """.strip()

            # create a new report
            report_properties = {
                "description": "TrackMe Fields Quality collect job tracker",
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
            collect_tracker_create_report = trackme_create_report(
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
            # step 5: create the wrapper for the monitor job
            #

            report_name = (
                f"trackme_{component}_monitor_{tracker_name}_wrapper_tenant_{tenant_id}"
            )
            report_search = f"""
                index={summary_index} sourcetype=trackme:fields_quality source=\"trackme:quality:{tracker_name}\" | fields * | sort 0 _time
                | trackmefieldsqualityextract
                | `trackme_fqm_get_description_extended`
                | stats values(description) as description, count as count_total, count(eval(status=="success")) as count_success, count(eval(status=="failure")) as count_failure by {object_metadata_list}
                | eval percentage_success=round(count_success/count_total*100, 2)
                ``` flag field ```
                | eval fieldstatus=if(percentage_success>=threshold, "success", "failure")
                ``` join field summary ```
                | join type=outer {object_metadata_list} 
                [ search index={summary_index} sourcetype=trackme:fields_quality source=\"trackme:quality:{tracker_name}\" | fields * | sort 0 _time
                | trackmefieldsqualityextract
                | table _time, {object_metadata_list}, value, regex_expression
                ``` sort is mandatory to force all records to be retrieved before we call the gen summary command ```
                | sort 0 _time
                | trackmefieldsqualitygensummary maxvals=15 fieldvalues_format=csv groupby_metadata_fields="{object_metadata_list}"
                | fields {object_metadata_list}, total_events, distinct_value_count, percent_coverage, field_values, regex_expression | fields - _time, _raw ]
                | eval field_values=split(field_values, ",")
                ``` set account ```
                | eval account="{account}"
                ``` call the command trackmesplkfqmparse ```
                | trackmesplkfqmparse tenant_id={tenant_id} object_metadata_list="{object_metadata_list}" default_threshold_fields={default_threshold_fields} default_threshold_global={default_threshold_global} default_score_fields={default_score_fields} default_score_global={default_score_global} context="live" max_sec_inactive=604800 tracker_name="{tracker_name}" tracker_index={summary_index}
                ``` call the streaming decision maker command ```
                | trackmedecisionmaker tenant_id={tenant_id} component=fqm
                ``` abstract macro ```
                | `trackme_fqm_tracker_abstract({tenant_id})`
                ``` collects latest collection state into the summary index ```
                | `trackme_collect_state("current_state_tracking:splk-fqm:{tenant_id}", "object", "{tenant_id}")`
                ``` output flipping change status if changes ```
                | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-fqm"
                ``` call final logics ```
                | `trackme_outputlookup(trackme_fqm_tenant_{tenant_id}, key)`
                | stats count as report_entities_count, values(object) as report_objects_list by tenant_id
                | `register_tenant_component_summary_nofilter({tenant_id}, fqm)`
            """.strip()

            # create a new report
            report_properties = {
                "description": "TrackMe Fields Quality monitor job wrapper",
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
            monitor_wrapper_create_report = trackme_create_report(
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
            # step 6: create the tracker for the monitor job
            #

            report_name = (
                f"trackme_{component}_monitor_{tracker_name}_tracker_tenant_{tenant_id}"
            )
            report_search = f"""
            | trackmetrackerexecutor tenant_id="{tenant_id}" component="splk-{component}" 
            report="trackme_{component}_monitor_{tracker_name}_wrapper_tenant_{tenant_id}" 
            alert_no_results=True
            """.strip()

            # create a new report
            monitor_cron_schedule = add_minutes_to_cron(str(cron_schedule), 10)
            report_properties = {
                "description": "TrackMe Fields Quality monitor job tracker",
                "is_scheduled": True,
                "schedule_window": "5",
                "cron_schedule": monitor_cron_schedule,
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
            }
            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            monitor_tracker_create_report = trackme_create_report(
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
            "collect_wrapper_report": collect_wrapper_create_report.get("report_name"),
            "collect_tracker_report": collect_tracker_create_report.get("report_name"),
            "monitor_wrapper_report": monitor_wrapper_create_report.get("report_name"),
            "monitor_tracker_report": monitor_tracker_create_report.get("report_name"),
            "collect_search_constraint": collect_wrapper_create_report.get("report_search"),
            "monitor_search_constraint": monitor_wrapper_create_report.get("report_search"),
            "tracker_name": str(tracker_name),
            "earliest": str(earliest_time),
            "latest": str(latest_time),
            "collect_cron_schedule": collect_tracker_create_report.get("cron_schedule"),
            "monitor_cron_schedule": monitor_tracker_create_report.get("cron_schedule"),
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
                tenant_hybrid_objects = vtenant_record.get("tenant_fqm_hybrid_objects")

                # logger.debug
                logger.debug(f'tenant_hybrid_objects="{tenant_hybrid_objects}"')
            except Exception as e:
                tenant_hybrid_objects = None

            # add to existing disct
            if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                vtenant_dict = json.loads(tenant_hybrid_objects)
                logger.info(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')

                report1 = collect_wrapper_create_report.get("report_name")
                report2 = collect_tracker_create_report.get("report_name")
                report3 = monitor_wrapper_create_report.get("report_name")
                report4 = monitor_tracker_create_report.get("report_name")

                reports = vtenant_dict["reports"]
                reports.append(str(report1))
                reports.append(str(report2))
                reports.append(str(report3))
                reports.append(str(report4))
                vtenant_dict = dict(
                    [
                        ("reports", reports),
                    ]
                )

            # empty dict
            else:
                report1 = collect_wrapper_create_report.get("report_name")
                report2 = collect_tracker_create_report.get("report_name")
                report3 = monitor_wrapper_create_report.get("report_name")
                report4 = monitor_tracker_create_report.get("report_name")

                reports = []
                reports.append(str(report1))
                reports.append(str(report2))
                reports.append(str(report3))
                reports.append(str(report4))

                vtenant_dict = dict(
                    [
                        ("reports", reports),
                    ]
                )

            try:
                vtenant_record["tenant_fqm_hybrid_objects"] = json.dumps(
                    vtenant_dict, indent=1
                )
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )

            except Exception as e:
                error_message = f'tenant_id="{tenant_id}", failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                logger.error(error_message)
                return {
                    "payload": error_message,
                    "status": 500,
                }

            # Record the new hybrid component in the hybrid collection
            collection_hybrid_name = f"kv_trackme_{component}_hybrid_trackers_tenant_{tenant_id}"
            collection_hybrid = service.kvstore[collection_hybrid_name]

            reports = []
            reports.append(str(report1))
            reports.append(str(report2))
            reports.append(str(report3))
            reports.append(str(report4))

            properties = []
            properties_dict = {
                collect_wrapper_create_report.get("report_name"): {
                    "search_constraint": collect_wrapper_create_report.get("report_search"),
                    "earliest": collect_wrapper_create_report.get("dispatch.earliest_time"),
                    "latest": collect_wrapper_create_report.get("dispatch.latest_time"),
                    "cron_schedule": collect_tracker_create_report.get("cron_schedule"),
                },
                monitor_wrapper_create_report.get("report_name"): {
                    "search_constraint": monitor_wrapper_create_report.get("report_search"),
                    "earliest": monitor_wrapper_create_report.get("dispatch.earliest_time"),
                    "latest": monitor_tracker_create_report.get("dispatch.latest_time"),
                    "cron_schedule": monitor_tracker_create_report.get("cron_schedule"),
                }
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
                            "knowledge_objects": json.dumps(hybrid_dict, indent=1),
                        }
                    )
                )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{str(e)}"'
                )

        # Record audit changes
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "add collect tracker",
                f"trackme_{component}_collect_{tracker_name}",
                "hybrid_tracker",
                str(audit_record),
                "The quality collect tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "add monitor tracker",
                f"trackme_{component}_monitor_{tracker_name}",
                "hybrid_tracker",
                str(audit_record),
                "The quality monitor tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        # final return
        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Create a collect job (monitor phase only)
    def post_fqm_collect_job_monitor_only_create(self, request_info, **kwargs):
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
                try:
                    tenant_id = resp_dict["tenant_id"]
                    # ensure not empty
                    if not len(tenant_id) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'tenant_id is required and cannot be empty',
                            },
                            "status": 500
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'tenant_id is required',
                        },
                        "status": 500,
                    }

                # component (static)
                component = "fqm"

                # tracker name
                try:
                    tracker_name = resp_dict["tracker_name"]                    
                except Exception as e:
                    tracker_name = None

                if not tracker_name or len(tracker_name) == 0:
                    # generate a random tracker name
                    tracker_name = "fqm_" + uuid.uuid4().hex[:5]

                else:
                    # sanitize tracker name
                    tracker_name = (
                        tracker_name.lower().replace(" ", "-").replace(":", "-")[:40]
                    )
                    tracker_name = tracker_name + "_" + uuid.uuid4().hex[:5]

                # get search constraint
                try:
                    search_constraint = resp_dict["search_constraint"]
                    # ensure not empty
                    if not len(search_constraint) > 0:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'search_constraint is required and cannot be empty',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'search_constraint is required',
                        },
                        "status": 500,
                    }

                #
                # optional args
                #

                # object_metadata_list, defaults to metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname
                # object_metadata_list defines the list of fields used to generate the object value, in their order of precedence
                try:
                    object_metadata_list = resp_dict["object_metadata_list"]
                    # ensure not empty if specified
                    if not len(object_metadata_list) > 0:
                        object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"
                    # if is a list, convert to a comma separated string
                    if isinstance(object_metadata_list, list):
                        object_metadata_list = ",".join(object_metadata_list)
                except Exception as e:
                    object_metadata_list = "metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"

                # default_threshold_fields, defaults to 99 (must be a numeric value)
                try:
                    default_threshold_fields = resp_dict["default_threshold_fields"]
                    try:
                        default_threshold_fields = float(default_threshold_fields)
                        if default_threshold_fields < 0 or default_threshold_fields > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_threshold_fields is required and must be a numeric value between 0 and 100',
                                },
                                "status": 500,
                            }
                        # round to an integer if possible
                        if default_threshold_fields == int(default_threshold_fields):
                            default_threshold_fields = int(default_threshold_fields)
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_threshold_fields is required and must be a numeric value',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'default_threshold_fields is required and must be a numeric value',
                        },
                        "status": 500,
                    }
                    
                # default_threshold_global, defaults to 100 (must be a numeric value)
                try:
                    default_threshold_global = resp_dict["default_threshold_global"]
                    try:
                        default_threshold_global = float(default_threshold_global)
                        if default_threshold_global < 0 or default_threshold_global > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_threshold_global is required and must be a numeric value between 0 and 100',
                                },
                                "status": 500,
                            }
                        # round to an integer if possible
                        if default_threshold_global == int(default_threshold_global):
                            default_threshold_global = int(default_threshold_global)
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_threshold_global is required and must be a numeric value',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'default_threshold_global is required and must be a numeric value',
                        },
                        "status": 500,
                    }

                # default_score_fields, defaults to 100 (must be an integer between 0 and 100)
                try:
                    default_score_fields = resp_dict.get("default_score_fields", 100)
                    try:
                        default_score_fields = int(default_score_fields)
                        if default_score_fields < 0 or default_score_fields > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_score_fields must be an integer between 0 and 100',
                                },
                                "status": 500,
                            }
                    except (ValueError, TypeError):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_score_fields must be an integer between 0 and 100',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    default_score_fields = 100
                
                # default_score_global, defaults to 100 (must be an integer between 0 and 100)
                try:
                    default_score_global = resp_dict.get("default_score_global", 100)
                    try:
                        default_score_global = int(default_score_global)
                        if default_score_global < 0 or default_score_global > 100:
                            return {
                                "payload": {
                                    "action": "failure",
                                    "response": f'default_score_global must be an integer between 0 and 100',
                                },
                                "status": 500,
                            }
                    except (ValueError, TypeError):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f'default_score_global must be an integer between 0 and 100',
                            },
                            "status": 500,
                        }
                except Exception as e:
                    default_score_global = 100

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "10 2 * * *"

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

                # earliest_time and latest_time for the tracker, if not specified, defaults to -5m / +4h for fqm|dhm and -5m/+5m for fqm
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-24h"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "now"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint creates a new Field Quality Monitoring (FQM) Collect Job in monitor-only phase. Monitor-only mode skips the historical data backfill step and starts collecting from now forward — useful when seeding a new tracker against high-volume sources where backfill would be expensive. It requires a POST call with the following information:",
                "resource_desc": "Create a new FQM Collect Job in monitor-only phase (no historical backfill)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/admin/fqm_collect_job_monitor_only_create\" body=\"{'tenant_id': 'mytenant', 'tracker_name': 'mytracker', 'search_constraint': 'index=_internal sourcetype=splunkd', 'default_threshold_fields': '99', 'default_threshold_global': '99'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "search_constraint": "REQUIRED. The Splunk search constraint to scope the collect job (e.g. 'index=foo sourcetype=bar')",
                        "default_threshold_fields": "REQUIRED. The default per-field quality threshold. Numeric value 0-100 representing the percentage of events that must match the field-quality model",
                        "default_threshold_global": "REQUIRED. The default global-entity quality threshold. Numeric value 0-100",
                        "tracker_name": "OPTIONAL. The name of the tracker — value will prefix all entities under the format value:<entity>. Defaults to a randomly-generated name when omitted",
                        "object_metadata_list": "OPTIONAL. Comma-separated list of fields used to generate the object value, in order of precedence. Defaults to 'metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname'",
                        "owner": "OPTIONAL. The Splunk user owning the objects to be created. Defaults to the owner set for the tenant",
                        "cron_schedule": "OPTIONAL. The cron schedule for the tracker. Defaults to every 5 minutes ('*/5 * * * *')",
                        "earliest_time": "OPTIONAL. The earliest time value for the tracker. Defaults to '-5m'",
                        "latest_time": "OPTIONAL. The latest time value for the tracker. Defaults to 'now'",
                        "summary_index": "OPTIONAL. The Splunk index to write the summary results to. Defaults to the tenant's configured summary index",
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
                    "change_type": "add new FQM tracker",
                    "tenant_id": str(tenant_id),
                    "result": "I'm afraid I can't do that, the Foundation edition does not allow creating FQM trackers.",
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
                        "/services/trackme/v2/splk_fqm/admin/fqm_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            #
            # step 1: create the wrapper for the monitor job
            #

            report_name = (
                f"trackme_{component}_monitor_{tracker_name}_wrapper_tenant_{tenant_id}"
            )
            report_search = f"""
                {search_constraint} | fields * | sort 0 _time
                | trackmefieldsqualityextract
                | `trackme_fqm_get_description_extended`
                | stats values(description) as description, count as count_total, count(eval(status=="success")) as count_success, count(eval(status=="failure")) as count_failure by {object_metadata_list}
                | eval percentage_success=round(count_success/count_total*100, 2)
                ``` flag field ```
                | eval fieldstatus=if(percentage_success>=threshold, "success", "failure")
                ``` join field summary ```
                | join type=outer {object_metadata_list} 
                [ search {search_constraint} | fields * | sort 0 _time
                | trackmefieldsqualityextract
                | table _time, {object_metadata_list}, value, regex_expression
                ``` sort is mandatory to force all records to be retrieved before we call the gen summary command ```
                | sort 0 _time
                | trackmefieldsqualitygensummary maxvals=15 fieldvalues_format=csv groupby_metadata_fields="{object_metadata_list}"
                | fields {object_metadata_list}, total_events, distinct_value_count, percent_coverage, field_values, regex_expression | fields - _time, _raw ]
                | eval field_values=split(field_values, ",")
                ``` set account to local```
                | eval account="local"
                ``` call the command trackmesplkfqmparse ```
                | trackmesplkfqmparse tenant_id={tenant_id} object_metadata_list="{object_metadata_list}" default_threshold_fields={default_threshold_fields} default_threshold_global={default_threshold_global} default_score_fields={default_score_fields} default_score_global={default_score_global} context="live" max_sec_inactive=604800 tracker_name="{tracker_name}"
                ``` call the streaming decision maker command ```
                | trackmedecisionmaker tenant_id={tenant_id} component=fqm
                ``` abstract macro ```
                | `trackme_fqm_tracker_abstract({tenant_id})`
                ``` collects latest collection state into the summary index ```
                | `trackme_collect_state("current_state_tracking:splk-fqm:{tenant_id}", "object", "{tenant_id}")`
                ``` output flipping change status if changes ```
                | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-fqm"
                ``` call final logics ```
                | `trackme_outputlookup(trackme_fqm_tenant_{tenant_id}, key)`
                | stats count as report_entities_count, values(object) as report_objects_list by tenant_id
                | `register_tenant_component_summary_nofilter({tenant_id}, fqm)`
            """.strip()

            # create a new report
            report_properties = {
                "description": "TrackMe Fields Quality monitor job wrapper",
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
            monitor_wrapper_create_report = trackme_create_report(
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
            # step 2: create the tracker for the monitor job
            #

            report_name = (
                f"trackme_{component}_monitor_{tracker_name}_tracker_tenant_{tenant_id}"
            )
            report_search = f"""
            | trackmetrackerexecutor tenant_id="{tenant_id}" component="splk-{component}" 
            report="trackme_{component}_monitor_{tracker_name}_wrapper_tenant_{tenant_id}" 
            alert_no_results=True
            """.strip()

            # create a new report
            monitor_cron_schedule = add_minutes_to_cron(str(cron_schedule), 10)
            report_properties = {
                "description": "TrackMe Fields Quality monitor job tracker",
                "is_scheduled": True,
                "schedule_window": "5",
                "cron_schedule": monitor_cron_schedule,
                "dispatch.earliest_time": str(earliest_time),
                "dispatch.latest_time": str(latest_time),
            }
            report_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            monitor_tracker_create_report = trackme_create_report(
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
            "monitor_wrapper_report": monitor_wrapper_create_report.get("report_name"),
            "monitor_tracker_report": monitor_tracker_create_report.get("report_name"),
            "monitor_search_constraint": monitor_wrapper_create_report.get("report_search"),
            "tracker_name": str(tracker_name),
            "earliest": str(earliest_time),
            "latest": str(latest_time),
            "monitor_cron_schedule": monitor_tracker_create_report.get("cron_schedule"),
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
                tenant_hybrid_objects = vtenant_record.get("tenant_fqm_hybrid_objects")

                # logger.debug
                logger.debug(f'tenant_hybrid_objects="{tenant_hybrid_objects}"')
            except Exception as e:
                tenant_hybrid_objects = None

            # add to existing disct
            if tenant_hybrid_objects and tenant_hybrid_objects != "None":
                vtenant_dict = json.loads(tenant_hybrid_objects)
                logger.info(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')

                report1 = monitor_wrapper_create_report.get("report_name")
                report2 = monitor_tracker_create_report.get("report_name")

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
                report1 = monitor_wrapper_create_report.get("report_name")
                report2 = monitor_tracker_create_report.get("report_name")

                reports = []
                reports.append(str(report1))
                reports.append(str(report2))

                vtenant_dict = dict(
                    [
                        ("reports", reports),
                    ]
                )

            try:
                vtenant_record["tenant_fqm_hybrid_objects"] = json.dumps(
                    vtenant_dict, indent=1
                )
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )

            except Exception as e:
                error_message = f'tenant_id="{tenant_id}", failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                logger.error(error_message)
                return {
                    "payload": error_message,
                    "status": 500,
                }

            # Record the new hybrid component in the hybrid collection
            collection_hybrid_name = f"kv_trackme_{component}_hybrid_trackers_tenant_{tenant_id}"
            collection_hybrid = service.kvstore[collection_hybrid_name]

            reports = []
            reports.append(str(report1))
            reports.append(str(report2))

            properties = []
            properties_dict = {
                monitor_wrapper_create_report.get("report_name"): {
                    "search_constraint": monitor_wrapper_create_report.get("report_search"),
                    "earliest": monitor_wrapper_create_report.get("dispatch.earliest_time"),
                    "latest": monitor_tracker_create_report.get("dispatch.latest_time"),
                    "cron_schedule": monitor_tracker_create_report.get("cron_schedule"),
                }
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
                            "knowledge_objects": json.dumps(hybrid_dict, indent=1),
                        }
                    )
                )
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the hybrid KVstore record, exception="{str(e)}"'
                )

        # Record audit changes
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "add collect tracker",
                f"trackme_{component}_collect_{tracker_name}",
                "hybrid_tracker",
                str(audit_record),
                "The quality collect tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "add monitor tracker",
                f"trackme_{component}_monitor_{tracker_name}",
                "hybrid_tracker",
                str(audit_record),
                "The quality monitor tracker was created successfully",
                str(update_comment),
            )
        except Exception as e:
            logger.error(f'failed to generate an audit event with exception="{str(e)}"')

        # final return
        logger.info(json.dumps(audit_record, indent=2))
        return {"payload": audit_record, "status": 200}

    # Remove an hybrid tracker and associated objects
    def post_fqm_tracker_delete(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/splk_fqm/admin/fqm_tracker_delete" body="{'tenant_id': 'mytenant', 'hybrid_trackers_list': 'test:001,test:002'}"
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
                # Handle as a CSV list of keys, if not a list already
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
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_fqm/admin/fqm_tracker_delete\" body=\"{'tenant_id': 'mytenant', 'hybrid_trackers_list': 'test:001,test:002'}\"",
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
                            "/services/trackme/v2/splk_fqm/admin/fqm_tracker_delete",
                        )
                        logger.info(f"trackme_send_to_tcm was successfully executed")
                    except Exception as e:
                        logger.error(
                            f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                        )

                # Data collection
                collection_name = "kv_trackme_fqm_hybrid_trackers_tenant_" + str(
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
                                "tenant_fqm_hybrid_objects"
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

                            report1 = f"trackme_fqm_collect_{hybrid_tracker}_wrapper_tenant_{tenant_id}"
                            report2 = f"trackme_fqm_collect_{hybrid_tracker}_tracker_tenant_{tenant_id}"
                            report3 = f"trackme_fqm_monitor_{hybrid_tracker}_wrapper_tenant_{tenant_id}"
                            report4 = f"trackme_fqm_monitor_{hybrid_tracker}_tracker_tenant_{tenant_id}"

                            reports = vtenant_dict["reports"]
                            for report in [str(report1), str(report2), str(report3), str(report4)]:
                                if report in reports:
                                    reports.remove(report)

                            vtenant_dict = dict(
                                [
                                    ("reports", reports),
                                ]
                            )

                            # Update the KVstore
                            try:
                                vtenant_record["tenant_fqm_hybrid_objects"] = (
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
                            "splk-fqm",
                            f"trackme_fqm_collect_{hybrid_tracker}_wrapper_tenant_{tenant_id}",
                        )
                    except Exception as e:
                        logger.error(
                            f'exception encountered while calling function trackme_delete_tenant_object_summary, exception="{str(e)}"'
                        )

                    try:
                        delete_register_summary = trackme_delete_tenant_object_summary(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            "splk-fqm",
                            f"trackme_fqm_monitor_{hybrid_tracker}_wrapper_tenant_{tenant_id}",
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
