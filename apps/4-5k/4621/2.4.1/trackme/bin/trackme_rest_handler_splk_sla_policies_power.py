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
import re
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
    "trackme.rest.splk_sla_policies_power",
    "trackme_rest_api_splk_sla_policies_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    get_kv_collection,
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
)
from trackme_libs_policies import (
    collect_all_fields,
    validate_lookup_name,
    load_lookup_content,
    match_entity_to_lookup_row,
    resolve_lookup_sla,
    validate_search_query,
    execute_search_content,
    resolve_service_for_account,
    preload_lookup_cache,
    preload_search_cache,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkSlaPoliciesWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkSlaPoliciesWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_sla_policies(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_sla_policies/write",
            "resource_group_desc": "Endpoints related to the management of priorities (power operations)",
        }

        return {"payload": response, "status": 200}

    # Add new policy
    def post_sla_policies_add(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        component = None
        sla_policy_id = None
        sla_policy_type = "regex"
        sla_policy_value = None
        sla_policy_regex = None
        # Lookup-specific fields
        sla_policy_lookup_name = ""
        sla_policy_lookup_field_mappings = ""
        sla_policy_lookup_sla_field = ""
        sla_policy_lookup_sla_mappings = ""
        sla_policy_lookup_match_mode = "exact"
        # Search-specific fields
        sla_policy_search_query = ""
        sla_policy_search_earliest = "-5m"
        sla_policy_search_latest = "now"
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
                            "response": "The tenant_id is required",
                            "status": 400,
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
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    sla_policy_id = resp_dict["sla_policy_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The sla_policy_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # Get policy type (defaults to "regex" for backward compatibility)
                sla_policy_type = resp_dict.get("sla_policy_type", "regex")
                if sla_policy_type not in ("regex", "lookup", "search"):
                    return {
                        "payload": {
                            "response": "The sla_policy_type is not valid, valid options are: regex, lookup, search",
                            "status": 400,
                        },
                        "status": 400,
                    }

                if sla_policy_type == "regex":
                    # Regex mode: require value and regex
                    try:
                        sla_policy_value = resp_dict["sla_policy_value"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_value is required for regex policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # if sla_policy_value is a string, make it lower case
                    if isinstance(sla_policy_value, str):
                        if not len(sla_policy_value) > 0:
                            return {
                                "payload": {
                                    "response": "The sla_policy_value should not be empty",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                        else:
                            sla_policy_value = sla_policy_value.lower()
                    else:
                        return {
                            "payload": {
                                "response": "The sla_policy_value should be a string",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        sla_policy_regex = resp_dict["sla_policy_regex"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_regex is required for regex policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # verify that the regex is valid
                    try:
                        re.compile(sla_policy_regex)
                    except re.error:
                        return {
                            "payload": {
                                "response": "The sla_policy_regex is not a valid regular expression",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif sla_policy_type == "lookup":
                    # Lookup mode: require lookup-specific fields
                    sla_policy_value = "from_lookup"
                    sla_policy_regex = ""

                    try:
                        sla_policy_lookup_name = resp_dict["sla_policy_lookup_name"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_name is required for lookup policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate lookup name before any Splunk API access
                    try:
                        validate_lookup_name(sla_policy_lookup_name)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        sla_policy_lookup_field_mappings = resp_dict["sla_policy_lookup_field_mappings"]
                        # Validate JSON and ensure it's a non-empty dict
                        if isinstance(sla_policy_lookup_field_mappings, str):
                            parsed = json.loads(sla_policy_lookup_field_mappings)
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                return {
                                    "payload": {
                                        "response": "The sla_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        elif isinstance(sla_policy_lookup_field_mappings, dict):
                            if len(sla_policy_lookup_field_mappings) == 0:
                                return {
                                    "payload": {
                                        "response": "The sla_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                            sla_policy_lookup_field_mappings = json.dumps(sla_policy_lookup_field_mappings)
                        else:
                            return {
                                "payload": {
                                    "response": "The sla_policy_lookup_field_mappings must be a JSON string or object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, ValueError):
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_field_mappings is required for lookup policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        sla_policy_lookup_sla_field = resp_dict["sla_policy_lookup_sla_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_sla_field is required for lookup policies",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    if not sla_policy_lookup_sla_field:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_sla_field must not be empty",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional fields
                    sla_policy_lookup_sla_mappings = resp_dict.get("sla_policy_lookup_sla_mappings", "")
                    if sla_policy_lookup_sla_mappings:
                        if isinstance(sla_policy_lookup_sla_mappings, dict):
                            sla_policy_lookup_sla_mappings = json.dumps(sla_policy_lookup_sla_mappings)
                        elif isinstance(sla_policy_lookup_sla_mappings, str):
                            try:
                                parsed_mappings = json.loads(sla_policy_lookup_sla_mappings)
                                if not isinstance(parsed_mappings, dict):
                                    return {
                                        "payload": {
                                            "response": "The sla_policy_lookup_sla_mappings must be a JSON object (dict), not an array or other type",
                                            "status": 400,
                                        },
                                        "status": 400,
                                    }
                            except (json.JSONDecodeError, ValueError):
                                return {
                                    "payload": {
                                        "response": "The sla_policy_lookup_sla_mappings is not valid JSON",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        else:
                            return {
                                "payload": {
                                    "response": "The sla_policy_lookup_sla_mappings must be a JSON string or object (dict)",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    sla_policy_lookup_match_mode = resp_dict.get("sla_policy_lookup_match_mode", "exact")
                    if sla_policy_lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_match_mode is not valid, valid options are: exact, wildcard",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif sla_policy_type == "search":
                    # Search mode: require search query, reuse lookup field mappings
                    sla_policy_value = "from_search"
                    sla_policy_regex = ""
                    sla_policy_lookup_name = ""

                    # Search query (required)
                    sla_policy_search_query = resp_dict.get("sla_policy_search_query", "")
                    if not sla_policy_search_query:
                        return {
                            "payload": {
                                "response": "The sla_policy_search_query is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate search query
                    try:
                        validate_search_query(sla_policy_search_query)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Search time range (optional)
                    sla_policy_search_earliest = resp_dict.get("sla_policy_search_earliest", "-5m")
                    sla_policy_search_latest = resp_dict.get("sla_policy_search_latest", "now")

                    # Field mappings (required, same as lookup)
                    try:
                        sla_policy_lookup_field_mappings = resp_dict["sla_policy_lookup_field_mappings"]
                        # Validate JSON and ensure it's a non-empty dict
                        if isinstance(sla_policy_lookup_field_mappings, str):
                            parsed = json.loads(sla_policy_lookup_field_mappings)
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                return {
                                    "payload": {
                                        "response": "The sla_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        elif isinstance(sla_policy_lookup_field_mappings, dict):
                            if len(sla_policy_lookup_field_mappings) == 0:
                                return {
                                    "payload": {
                                        "response": "The sla_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                            sla_policy_lookup_field_mappings = json.dumps(sla_policy_lookup_field_mappings)
                        else:
                            return {
                                "payload": {
                                    "response": "The sla_policy_lookup_field_mappings must be a JSON string or object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, ValueError):
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_field_mappings is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # SLA field (required)
                    try:
                        sla_policy_lookup_sla_field = resp_dict["sla_policy_lookup_sla_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_sla_field is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    if not sla_policy_lookup_sla_field:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_sla_field must not be empty",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # SLA mappings (optional)
                    sla_policy_lookup_sla_mappings = resp_dict.get("sla_policy_lookup_sla_mappings", "")
                    if sla_policy_lookup_sla_mappings:
                        if isinstance(sla_policy_lookup_sla_mappings, dict):
                            sla_policy_lookup_sla_mappings = json.dumps(sla_policy_lookup_sla_mappings)
                        elif isinstance(sla_policy_lookup_sla_mappings, str):
                            try:
                                parsed_mappings = json.loads(sla_policy_lookup_sla_mappings)
                                if not isinstance(parsed_mappings, dict):
                                    return {
                                        "payload": {
                                            "response": "The sla_policy_lookup_sla_mappings must be a JSON object (dict), not an array or other type",
                                            "status": 400,
                                        },
                                        "status": 400,
                                    }
                            except (json.JSONDecodeError, ValueError):
                                return {
                                    "payload": {
                                        "response": "The sla_policy_lookup_sla_mappings is not valid JSON",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        else:
                            return {
                                "payload": {
                                    "response": "The sla_policy_lookup_sla_mappings must be a JSON string or object (dict)",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    sla_policy_lookup_match_mode = resp_dict.get("sla_policy_lookup_match_mode", "exact")
                    if sla_policy_lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_match_mode is not valid, valid options are: exact, wildcard",
                                "status": 400,
                            },
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new sla class policy or updates a policy if it exists already, it requires a POST call with the following data:",
                "resource_desc": "Add or update a sla class policy (supports regex, lookup and search modes)",
                "resource_spl_example": r"| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/write/sla_policies_add\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'sla_policy_id': 'linux_secure', 'sla_policy_value': 'gold', 'sla_policy_regex': '\:linux_secure$'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "sla_policy_id": "(required) ID of the sla class policy",
                        "sla_policy_type": "(optional) Policy type: 'regex' (default), 'lookup' or 'search'",
                        "sla_policy_regex": "(required for regex) The regular expression to be used by the sla class policy, special characters should be escaped.",
                        "sla_policy_value": "(required for regex) SLA class to be applied.",
                        "sla_policy_lookup_name": "(required for lookup) The Splunk lookup transform name",
                        "sla_policy_lookup_field_mappings": "(required for lookup/search) JSON mapping of lookup/search result fields to entity fields",
                        "sla_policy_lookup_sla_field": "(required for lookup/search) The field in the lookup/search results containing SLA class values",
                        "sla_policy_lookup_sla_mappings": "(optional for lookup/search) JSON mapping of foreign SLA values to TrackMe format",
                        "sla_policy_lookup_match_mode": "(optional for lookup/search) Match mode: 'exact' (default, case-insensitive) or 'wildcard'",
                        "sla_policy_search_query": "(required for search) The SPL search query to execute",
                        "sla_policy_search_earliest": "(optional for search, default: -5m) The earliest time for the search",
                        "sla_policy_search_latest": "(optional for search, default: now) The latest time for the search",
                        "account": "(optional) The remote Splunk deployment account name to use for lookup/search operations, default: local",
                        "update_comment": "(optional) Comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Define the KV query
        query_string = {
            "sla_policy_id": sla_policy_id,
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

        # Resolve account for remote Splunk deployment support
        account = resp_dict.get("account", "local") if resp_dict else "local"

        # For lookup and search policies, resolve remote account upfront to validate connectivity
        if sla_policy_type in ("lookup", "search"):
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
            # For lookup policies, also validate that the lookup transform exists
            if sla_policy_type == "lookup":
                try:
                    target_service.confs["transforms"][sla_policy_lookup_name]
                except Exception as e:
                    return {
                        "payload": {
                            "response": f'The lookup transform "{sla_policy_lookup_name}" was not found in Splunk',
                            "status": 400,
                        },
                        "status": 400,
                    }

        # Get trackmeconf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )["trackme_conf"]

        # Get SLA classes conf
        sla_classes = trackme_conf["sla"]["sla_classes"]

        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
            # For regex policies, validate the SLA class value
            if sla_policy_type == "regex" and sla_policy_value not in sla_classes:
                error_msg = f"The SLA class {sla_policy_value} is not available currently in TrackMe's configuration, available classes: {json.dumps(sla_classes, 0)}"
                logger.error(error_msg)
                return {
                    "payload": {
                        "response": f"{error_msg}",
                        "status": 500,
                    },
                    "status": 500,
                }

        except Exception as e:
            error_msg = f'Error loading sla_classes JSON, please check the configuration, the JSON is not valid JSON, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": f"{error_msg}",
                    "status": 500,
                },
                "status": 500,
            }

        # Data collection
        collection_name = f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Get the current record
        try:
            record = collection.data.query(query=json.dumps(query_string))
            key = record[0].get("_key")
        except Exception as e:
            key = None

        # Build the record data (common for both insert and update)
        record_data = {
            "sla_policy_id": sla_policy_id,
            "sla_policy_type": sla_policy_type,
            "sla_policy_value": sla_policy_value,
            "sla_policy_regex": sla_policy_regex if sla_policy_regex else "",
            "sla_policy_lookup_name": sla_policy_lookup_name,
            "sla_policy_lookup_field_mappings": sla_policy_lookup_field_mappings,
            "sla_policy_lookup_sla_field": sla_policy_lookup_sla_field,
            "sla_policy_lookup_sla_mappings": sla_policy_lookup_sla_mappings,
            "sla_policy_lookup_match_mode": sla_policy_lookup_match_mode,
            "sla_policy_search_query": sla_policy_search_query,
            "sla_policy_search_earliest": sla_policy_search_earliest,
            "sla_policy_search_latest": sla_policy_search_latest,
            "account": account,
            "mtime": time.time(),
        }

        # proceed
        if key:
            action_desc = "updated"
        else:
            action_desc = "created"

        try:
            if key:
                # Update the record
                collection.data.update(
                    str(key),
                    json.dumps(record_data),
                )

                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "update sla class policy",
                        str(sla_policy_id),
                        f"splk-{component}",
                        collection.data.query(query=json.dumps(query_string)),
                        "The sla class policy was updated successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

            else:
                # Insert the record
                collection.data.insert(
                    json.dumps(record_data)
                )

                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "add sla class policy",
                        str(sla_policy_id),
                        f"splk-{component}",
                        collection.data.query(query=json.dumps(query_string)),
                        "The sla class policy was added successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

            # render response
            response = {
                "action": "success",
                "action_desc": action_desc,
                "response": f'the sla class policy sla_policy_id="{sla_policy_id}" was {action_desc} successfully',
                "record": collection.data.query(query=json.dumps(query_string)),
            }

            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Delete records from the collection
    def post_sla_policies_del(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
        sla_policy_id_list = None
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
                            "response": "The tenant_id is required",
                            "status": 400,
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
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    sla_policy_id_list = resp_dict["sla_policy_id_list"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The sla_policy_id_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # if sla_policy_id_list is a string, turn into a list
                if isinstance(sla_policy_id_list, str):
                    sla_policy_id_list = sla_policy_id_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes sla policies, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more sla policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/write/sla_policies_del\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'sla_policy_id': 'linux_secure,linux_sec'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "sla_policy_id_list": "(required) Comma separated list of sla policies",
                        "update_comment": "(optional) Comment for the update, comments are added to the audit record, if unset will be defined to: API update",
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

        # Data collection
        collection_name = f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop
        for item in sla_policy_id_list:
            # Define the KV query
            query_string = {
                "sla_policy_id": item,
            }

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # Remove and audit
                try:
                    # Remove the record
                    collection.data.delete(json.dumps({"_key": key}))

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "delete sla class policy",
                            str(item),
                            "all",
                            record,
                            "The lagging class was deleted successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "delete",
                        "result": "success",
                        "record": record,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "failure",
                            "delete sla class policy",
                            str(item),
                            "all",
                            record,
                            str(e),
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "delete",
                        "result": "failure",
                        "record": record,
                        "exception": e,
                    }

                    # append to records
                    records.append(result)

                    # log
                    logger.error(json.dumps(result, indent=0))

            else:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # audit record
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "delete sla class policy",
                        str(item),
                        "all",
                        record,
                        "HTTP 404 NOT FOUND",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                result = {
                    "action": "delete",
                    "result": "failure",
                    "record": item,
                    "exception": "HTTP 404 NOT FOUND",
                }

                # append to records
                records.append(result)

                # log
                logger.error(json.dumps(result, indent=0))

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

    # Update records
    def post_sla_policies_update(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
        records_list = None
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
                            "response": "The tenant_id is required",
                            "status": 400,
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
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    records_list = resp_dict["records_list"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The records_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    records_list = json.loads(records_list)
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The records_list is not a valid JSON",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates records, it requires a POST call with the following information:",
                "resource_desc": "Update one or more sla policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/write/sla_policies_update\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'records_list': '<redacted_json_records>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "records_list": "(required) JSON records to be updated",
                        "update_comment": "(option) Comment for the update, comments are added to the audit record, if unset will be defined to: API update",
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

        # Get trackmeconf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )["trackme_conf"]

        # Get SLA classes conf
        sla_classes = trackme_conf["sla"]["sla_classes"]

        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
        except Exception as e:
            error_msg = f'Error loading sla_classes JSON, please check the configuration, the JSON is not valid JSON, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": f"{error_msg}",
                    "status": 500,
                },
                "status": 500,
            }

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # debug
        logger.info(f'records_list="{json.dumps(records_list, indent=0)}"')

        # loop
        for item in records_list:
            # debug
            logger.info(f'item="{item}"')

            # check if we have the _key, otherwise search for it
            if item.get("_key"):
                key = item.get("_key")

            else:
                # Define the KV query
                query_string = {
                    "sla_policy_id": item.get("sla_policy_id"),
                }

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
                try:
                    record = collection.data.query(query=json.dumps(query_string))
                    key = record[0].get("_key")

                except Exception as e:
                    key = None

            # Render result
            if key:
                # This record exists already

                # Store the record for audit purposes
                record = str(json.dumps(collection.data.query_by_id(key), indent=1))

                # Update and audit
                try:
                    # Determine policy type
                    item_policy_type = item.get("sla_policy_type", "regex")
                    if item_policy_type not in ("regex", "lookup", "search"):
                        processed_count += 1
                        failures_count += 1
                        result = {
                            "action": "update",
                            "result": "failure",
                            "record": item,
                            "exception": f"Invalid sla_policy_type '{item_policy_type}', valid options are: regex, lookup, search",
                        }
                        records.append(result)
                        continue

                    # Update the record
                    sla_policy_value = item.get("sla_policy_value")

                    if item_policy_type == "regex":
                        # Regex mode: validate SLA class value
                        if isinstance(sla_policy_value, str):
                            if not len(sla_policy_value) > 0:
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "The sla_policy_value should not be empty",
                                }
                                records.append(result)
                                continue
                            else:
                                sla_policy_value = sla_policy_value.lower()
                                if sla_policy_value not in sla_classes:
                                    processed_count += 1
                                    failures_count += 1
                                    result = {
                                        "action": "update",
                                        "result": "failure",
                                        "record": item,
                                        "exception": f"The SLA class {sla_policy_value} is not available currently in TrackMe's configuration, available classes: {json.dumps(sla_classes, 0)}",
                                    }
                                    records.append(result)
                                    continue
                        else:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "The sla_policy_value should be a string",
                            }
                            records.append(result)
                            continue

                        # Validate regex is provided and valid for regex mode
                        sla_regex = item.get("sla_policy_regex", "")
                        if not sla_regex:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_regex is required for regex policies",
                            }
                            records.append(result)
                            continue
                        try:
                            re.compile(sla_regex)
                        except re.error:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_regex is not a valid regular expression",
                            }
                            records.append(result)
                            continue

                    elif item_policy_type == "lookup":
                        # Lookup mode: accept "from_lookup" as value
                        sla_policy_value = "from_lookup"

                        # Validate required lookup fields
                        lookup_name = item.get("sla_policy_lookup_name", "")
                        if not lookup_name:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_name is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        try:
                            validate_lookup_name(lookup_name)
                        except ValueError:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": f"Invalid lookup name: {lookup_name}",
                            }
                            records.append(result)
                            continue

                        lookup_field_mappings = item.get("sla_policy_lookup_field_mappings", "")
                        if not lookup_field_mappings:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_field_mappings is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        try:
                            parsed = json.loads(lookup_field_mappings) if isinstance(lookup_field_mappings, str) else lookup_field_mappings
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                raise ValueError("empty")
                        except (json.JSONDecodeError, TypeError, ValueError):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_field_mappings must be a non-empty JSON object or is not valid JSON",
                            }
                            records.append(result)
                            continue

                        sla_field = item.get("sla_policy_lookup_sla_field", "")
                        if not sla_field:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_sla_field is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        # Validate match mode
                        lookup_match_mode = item.get("sla_policy_lookup_match_mode", "exact")
                        if lookup_match_mode not in ("exact", "wildcard"):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                            }
                            records.append(result)
                            continue

                        # Validate SLA mappings if provided
                        sla_mappings_raw = item.get("sla_policy_lookup_sla_mappings", "")
                        if sla_mappings_raw:
                            try:
                                if isinstance(sla_mappings_raw, str):
                                    parsed = json.loads(sla_mappings_raw)
                                elif isinstance(sla_mappings_raw, dict):
                                    parsed = sla_mappings_raw
                                else:
                                    raise ValueError("not a string or dict")
                                if not isinstance(parsed, dict):
                                    raise ValueError("not a dict")
                            except (json.JSONDecodeError, TypeError, ValueError):
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "sla_policy_lookup_sla_mappings must be a valid JSON object (dict)",
                                }
                                records.append(result)
                                continue

                    elif item_policy_type == "search":
                        # Search mode: accept "from_search" as value
                        sla_policy_value = "from_search"

                        # Validate search query
                        search_query = item.get("sla_policy_search_query", "")
                        if not search_query:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_search_query is required for search policies",
                            }
                            records.append(result)
                            continue

                        try:
                            validate_search_query(search_query)
                        except ValueError as e:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": str(e),
                            }
                            records.append(result)
                            continue

                        # Validate required field mappings
                        lookup_field_mappings = item.get("sla_policy_lookup_field_mappings", "")
                        if not lookup_field_mappings:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_field_mappings is required for search policies",
                            }
                            records.append(result)
                            continue

                        try:
                            parsed = json.loads(lookup_field_mappings) if isinstance(lookup_field_mappings, str) else lookup_field_mappings
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                raise ValueError("empty")
                        except (json.JSONDecodeError, TypeError, ValueError):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_field_mappings must be a non-empty JSON object or is not valid JSON",
                            }
                            records.append(result)
                            continue

                        sla_field = item.get("sla_policy_lookup_sla_field", "")
                        if not sla_field:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_sla_field is required for search policies",
                            }
                            records.append(result)
                            continue

                        # Validate match mode
                        lookup_match_mode = item.get("sla_policy_lookup_match_mode", "exact")
                        if lookup_match_mode not in ("exact", "wildcard"):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "sla_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                            }
                            records.append(result)
                            continue

                        # Validate SLA mappings if provided
                        sla_mappings_raw = item.get("sla_policy_lookup_sla_mappings", "")
                        if sla_mappings_raw:
                            try:
                                if isinstance(sla_mappings_raw, str):
                                    parsed = json.loads(sla_mappings_raw)
                                elif isinstance(sla_mappings_raw, dict):
                                    parsed = sla_mappings_raw
                                else:
                                    raise ValueError("not a string or dict")
                                if not isinstance(parsed, dict):
                                    raise ValueError("not a dict")
                            except (json.JSONDecodeError, TypeError, ValueError):
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "sla_policy_lookup_sla_mappings must be a valid JSON object (dict)",
                                }
                                records.append(result)
                                continue

                    # Normalize dict values to JSON strings for consistent KVstore storage
                    _field_mappings = item.get("sla_policy_lookup_field_mappings", "")
                    if isinstance(_field_mappings, dict):
                        _field_mappings = json.dumps(_field_mappings)
                    _sla_mappings = item.get("sla_policy_lookup_sla_mappings", "")
                    if isinstance(_sla_mappings, dict):
                        _sla_mappings = json.dumps(_sla_mappings)

                    # Build update record with all fields
                    update_data = {
                        "sla_policy_id": item.get("sla_policy_id"),
                        "sla_policy_type": item_policy_type,
                        "sla_policy_value": sla_policy_value,
                        "sla_policy_regex": item.get("sla_policy_regex", ""),
                        "sla_policy_lookup_name": item.get("sla_policy_lookup_name", ""),
                        "sla_policy_lookup_field_mappings": _field_mappings,
                        "sla_policy_lookup_sla_field": item.get("sla_policy_lookup_sla_field", ""),
                        "sla_policy_lookup_sla_mappings": _sla_mappings,
                        "sla_policy_lookup_match_mode": item.get("sla_policy_lookup_match_mode", "exact"),
                        "sla_policy_search_query": item.get("sla_policy_search_query", ""),
                        "sla_policy_search_earliest": item.get("sla_policy_search_earliest", "-5m"),
                        "sla_policy_search_latest": item.get("sla_policy_search_latest", "now"),
                        "account": item.get("account", "local"),
                        "mtime": time.time(),
                    }

                    collection.data.update(
                        str(key),
                        json.dumps(update_data),
                    )

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "update sla policies",
                            str(item),
                            "dsm",
                            record,
                            "The sla policy was updated successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "delete",
                        "result": "success",
                        "record": record,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "failure",
                            "update sla policies",
                            str(item),
                            "dsm",
                            record,
                            str(e),
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "delete",
                        "result": "failure",
                        "record": record,
                        "exception": e,
                    }

                    # append to records
                    records.append(result)

                    # log
                    logger.error(json.dumps(result, indent=0))

            else:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # audit record
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "update sla policies",
                        str(item),
                        "dsm",
                        record,
                        "HTTP 404 NOT FOUND",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                result = {
                    "action": "delete",
                    "result": "failure",
                    "record": item,
                    "exception": "HTTP 404 NOT FOUND",
                }

                # append to records
                records.append(result)

                # log
                logger.error(json.dumps(result, indent=0))

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

    # Simulate sla_class
    def post_sla_policies_simulate(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
        sla_policy_type = "regex"
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
                            "response": "The tenant_id is required",
                            "status": 400,
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
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # Get policy type
                sla_policy_type = resp_dict.get("sla_policy_type", "regex")
                if sla_policy_type not in ("regex", "lookup", "search"):
                    return {
                        "payload": {
                            "response": "The sla_policy_type must be 'regex', 'lookup' or 'search'",
                            "status": 400,
                        },
                        "status": 400,
                    }

                if sla_policy_type == "regex":
                    try:
                        regex_value = resp_dict["regex_value"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument regex_value is required",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        sla_class = resp_dict["sla_class"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument sla_class is required",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    # sla_class should be a string
                    if isinstance(sla_class, str):
                        if not len(sla_class) > 0:
                            return {
                                "payload": {
                                    "response": "The sla_class should not be empty",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                        else:
                            sla_class = sla_class.lower()
                    else:
                        return {
                            "payload": {
                                "response": "The sla_class should be a string",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif sla_policy_type == "lookup":
                    # Lookup mode parameters
                    try:
                        lookup_name = resp_dict["sla_policy_lookup_name"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The sla_policy_lookup_name is required for lookup simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        validate_lookup_name(lookup_name)
                    except ValueError as e:
                        return {
                            "payload": {"response": str(e), "status": 400},
                            "status": 400,
                        }

                    try:
                        lookup_field_mappings_raw = resp_dict["sla_policy_lookup_field_mappings"]
                        if isinstance(lookup_field_mappings_raw, str):
                            lookup_field_mappings = json.loads(lookup_field_mappings_raw)
                        elif isinstance(lookup_field_mappings_raw, dict):
                            lookup_field_mappings = lookup_field_mappings_raw
                        else:
                            return {
                                "payload": {
                                    "response": "sla_policy_lookup_field_mappings must be a JSON string or object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                        if not isinstance(lookup_field_mappings, dict) or len(lookup_field_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "sla_policy_lookup_field_mappings must be a non-empty JSON object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, ValueError):
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_field_mappings is required for lookup simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        lookup_sla_field = resp_dict["sla_policy_lookup_sla_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_sla_field is required for lookup simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    if not lookup_sla_field:
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_sla_field must not be empty",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    lookup_sla_mappings_raw = resp_dict.get("sla_policy_lookup_sla_mappings", "")
                    lookup_sla_mappings = {}
                    if lookup_sla_mappings_raw:
                        try:
                            if isinstance(lookup_sla_mappings_raw, str):
                                parsed = json.loads(lookup_sla_mappings_raw)
                                if not isinstance(parsed, dict):
                                    return {
                                        "payload": {
                                            "response": "sla_policy_lookup_sla_mappings must be a JSON object (dict), not an array or other type",
                                            "status": 400,
                                        },
                                        "status": 400,
                                    }
                                lookup_sla_mappings = parsed
                            elif isinstance(lookup_sla_mappings_raw, dict):
                                lookup_sla_mappings = lookup_sla_mappings_raw
                            else:
                                return {
                                    "payload": {
                                        "response": "sla_policy_lookup_sla_mappings must be a JSON string or object (dict)",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        except (json.JSONDecodeError, ValueError):
                            return {
                                "payload": {
                                    "response": "sla_policy_lookup_sla_mappings is not valid JSON",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    lookup_match_mode = resp_dict.get("sla_policy_lookup_match_mode", "exact")
                    if lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif sla_policy_type == "search":
                    # Search mode: require search_query, field_mappings, sla_field
                    search_query = resp_dict.get("search_query", "")
                    if not search_query:
                        return {
                            "payload": {
                                "response": "The argument search_query is required for search simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate search query
                    try:
                        validate_search_query(search_query)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Search time range (optional)
                    earliest = resp_dict.get("earliest", "-5m")
                    latest = resp_dict.get("latest", "now")

                    # Field mappings (required)
                    try:
                        lookup_field_mappings_raw = resp_dict["sla_policy_lookup_field_mappings"]
                        if isinstance(lookup_field_mappings_raw, str):
                            lookup_field_mappings = json.loads(lookup_field_mappings_raw)
                        elif isinstance(lookup_field_mappings_raw, dict):
                            lookup_field_mappings = lookup_field_mappings_raw
                        else:
                            return {
                                "payload": {
                                    "response": "sla_policy_lookup_field_mappings must be a JSON string or object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                        if not isinstance(lookup_field_mappings, dict) or len(lookup_field_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "sla_policy_lookup_field_mappings must be a non-empty JSON object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, ValueError):
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_field_mappings is required for search simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # SLA field (required)
                    try:
                        lookup_sla_field = resp_dict["sla_policy_lookup_sla_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_sla_field is required for search simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    if not lookup_sla_field:
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_sla_field must not be empty",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    lookup_sla_mappings_raw = resp_dict.get("sla_policy_lookup_sla_mappings", "")
                    lookup_sla_mappings = {}
                    if lookup_sla_mappings_raw:
                        try:
                            if isinstance(lookup_sla_mappings_raw, str):
                                parsed = json.loads(lookup_sla_mappings_raw)
                                if not isinstance(parsed, dict):
                                    return {
                                        "payload": {
                                            "response": "sla_policy_lookup_sla_mappings must be a JSON object (dict), not an array or other type",
                                            "status": 400,
                                        },
                                        "status": 400,
                                    }
                                lookup_sla_mappings = parsed
                            elif isinstance(lookup_sla_mappings_raw, dict):
                                lookup_sla_mappings = lookup_sla_mappings_raw
                            else:
                                return {
                                    "payload": {
                                        "response": "sla_policy_lookup_sla_mappings must be a JSON string or object (dict)",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        except (json.JSONDecodeError, ValueError):
                            return {
                                "payload": {
                                    "response": "sla_policy_lookup_sla_mappings is not valid JSON",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    lookup_match_mode = resp_dict.get("sla_policy_lookup_match_mode", "exact")
                    if lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "sla_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                                "status": 400,
                            },
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint simulates a sla class policy, it requires a POST call with the following information:",
                "resource_desc": "Simulates a sla class policy (supports regex, lookup and search modes)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/write/sla_policies_simulate\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'regex_value': '^org_eu.*', 'sla_class': 'gold'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier",
                        "sla_policy_type": "(optional) Policy type: 'regex' (default), 'lookup' or 'search'",
                        "regex_value": "(required for regex) The regex to be used for the simulation",
                        "sla_class": "(required for regex) The sla_class value",
                        "sla_policy_lookup_name": "(required for lookup) The Splunk lookup transform name",
                        "sla_policy_lookup_field_mappings": "(required for lookup/search) JSON mapping of lookup/search result fields to entity fields",
                        "sla_policy_lookup_sla_field": "(required for lookup/search) The field in the lookup/search results containing SLA class values",
                        "sla_policy_lookup_sla_mappings": "(optional for lookup/search) JSON mapping of foreign SLA values to TrackMe format",
                        "sla_policy_lookup_match_mode": "(optional for lookup/search) Match mode: 'exact' or 'wildcard'",
                        "search_query": "(required for search) The SPL search query to execute",
                        "earliest": "(optional for search, default: -5m) The earliest time for the search",
                        "latest": "(optional for search, default: now) The latest time for the search",
                        "account": "(optional) The remote Splunk deployment account name to use for lookup/search operations, default: local",
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

        # Resolve account for remote Splunk deployment support
        account = resp_dict.get("account", "local") if resp_dict else "local"

        # Get trackmeconf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )["trackme_conf"]

        # Get SLA classes conf
        sla_classes = trackme_conf["sla"]["sla_classes"]

        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
        except Exception as e:
            return {
                "payload": {
                    "response": "The sla_classes configuration is not a valid JSON",
                    "status": 400,
                },
                "status": 400,
            }

        # Build SLA class rank dict
        sla_class_rank_dict = {}
        for sc in sla_classes:
            sla_class_rank_dict[sc] = sla_classes[sc].get("rank", 0)

        # start
        main_start = time.time()

        #
        # KV entities
        #

        # entities KV collection
        data_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        data_collection = service.kvstore[data_collection_name]

        # get records
        data_records, data_collection_keys, data_collection_dict = get_kv_collection(
            data_collection, data_collection_name
        )

        # Counters and error list
        entities_failures_count = 0
        entities_exceptions_list = []
        entities_matched = []

        if sla_policy_type == "regex":
            # Check requested sla class
            if sla_class not in sla_classes:
                return {
                    "payload": {
                        "response": f"The SLA class {sla_class} is not available currently in TrackMe's configuration, available classes: {json.dumps(sla_classes, 0)}",
                        "status": 400,
                    },
                    "status": 400,
                }

            # Regex simulation
            sla_policies_records = [
                {
                    "sla_policy_regex": regex_value,
                    "sla_policy_value": sla_class,
                }
            ]

            if len(data_records) > 0:
                for entity_record in data_records:
                    entity_object = entity_record["object"]

                    for policy_record in sla_policies_records:
                        try:
                            re.compile(regex_value)
                        except re.error:
                            req_summary = {
                                "entities_matched_count": len(entities_matched),
                                "result_summary": "The regex_value is not a valid regular expression, review this expression and try again.",
                                "regex_value": regex_value,
                                "regex_is_valid": "false",
                            }
                            return {"payload": req_summary, "status": 200}

                        try:
                            regex = policy_record["sla_policy_regex"]
                            value = policy_record["sla_policy_value"]
                            if isinstance(value, str):
                                value = value.lower()

                            if re.match(regex, entity_record["object"]):
                                if entity_object not in entities_matched:
                                    entities_matched.append(entity_object)

                        except Exception as e:
                            logger.error(
                                f'context="exception", failed to apply policy, exception="{str(e)}"'
                            )

            run_time = round((time.time() - main_start), 3)

            if len(entities_matched) > 0:
                result_summary = f"The regex has matched {len(entities_matched)} entities."
            else:
                result_summary = "The regex has not matched any entities, verify your inputs and try again."

            req_summary = {
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
                "regex_is_valid": "true",
            }

        elif sla_policy_type == "lookup":
            # Lookup simulation - resolve remote account
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
            try:
                target_service.confs["transforms"][lookup_name]
            except Exception as e:
                return {
                    "payload": {
                        "response": f'The lookup transform "{lookup_name}" was not found in Splunk',
                        "status": 400,
                    },
                    "status": 400,
                }

            try:
                lookup_rows = load_lookup_content(target_service, lookup_name)
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Failed to load lookup content: {str(e)}',
                        "status": 500,
                    },
                    "status": 500,
                }

            # Validate that the SLA field exists in lookup rows
            if lookup_rows:
                lookup_fields = collect_all_fields(lookup_rows)
                if lookup_sla_field not in lookup_fields:
                    return {
                        "payload": {
                            "response": f'The sla field "{lookup_sla_field}" was not found in the lookup. Available fields: {lookup_fields}',
                            "status": 400,
                        },
                        "status": 400,
                    }

            sla_distribution = {}

            # Build valid SLA classes dict for lookup resolver
            valid_sla_classes = {k: True for k in sla_classes}

            if len(data_records) > 0:
                for entity_record in data_records:
                    entity_object = entity_record["object"]
                    best_sla = None
                    best_rank = -1

                    for row in lookup_rows:
                        try:
                            if match_entity_to_lookup_row(entity_record, row, lookup_field_mappings, lookup_match_mode):
                                raw_sla = row.get(lookup_sla_field, "")
                                resolved = resolve_lookup_sla(raw_sla, lookup_sla_mappings, valid_sla_classes)
                                if resolved:
                                    resolved_rank = sla_class_rank_dict.get(resolved, 0)
                                    if resolved_rank > best_rank:
                                        best_sla = resolved
                                        best_rank = resolved_rank
                        except Exception as e:
                            msg = f'Failed to process lookup row for entity="{entity_object}", exception="{str(e)}"'
                            logger.error(msg)
                            if msg not in entities_exceptions_list:
                                entities_exceptions_list.append(msg)

                    if best_sla:
                        entities_matched.append({
                            "object": entity_object,
                            "resolved_sla_class": best_sla,
                        })
                        sla_distribution[best_sla] = sla_distribution.get(best_sla, 0) + 1

            run_time = round((time.time() - main_start), 3)

            if len(entities_matched) > 0:
                result_summary = f"The lookup has matched {len(entities_matched)} entities."
            else:
                result_summary = "The lookup has not matched any entities, verify your field mappings and try again."

            req_summary = {
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "sla_distribution": sla_distribution,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
            }

        elif sla_policy_type == "search":
            #
            # Search simulation
            #

            # Resolve remote account
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

            # Execute search query
            try:
                search_rows = execute_search_content(target_service, search_query, earliest, latest)
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", failed to execute search query, exception="{str(e)}"'
                )
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'Failed to execute search query: {str(e)}',
                    },
                    "status": 500,
                }

            if len(search_rows) == 0:
                return {
                    "payload": {
                        "search_rows_count": 0,
                        "entities_matched_count": 0,
                        "entities_matched": [],
                        "sla_distribution": {},
                        "result_summary": "The search query returned no results.",
                    },
                    "status": 200,
                }

            # Validate that sla_field exists in search results
            search_fields = collect_all_fields(search_rows)
            if lookup_sla_field not in search_fields:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'The sla field "{lookup_sla_field}" was not found in the search result fields: {search_fields}',
                    },
                    "status": 400,
                }

            # Validate that field_mappings keys exist in search results
            for sr_field in lookup_field_mappings.keys():
                if sr_field not in search_fields:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'The search result field "{sr_field}" in field_mappings was not found in the search result fields: {search_fields}',
                        },
                        "status": 400,
                    }

            sla_distribution = {}

            # Build valid SLA classes dict for resolver
            valid_sla_classes = {k: True for k in sla_classes}

            if len(data_records) > 0:
                for entity_record in data_records:
                    entity_object = entity_record["object"]
                    best_sla = None
                    best_rank = -1

                    for row in search_rows:
                        try:
                            if match_entity_to_lookup_row(entity_record, row, lookup_field_mappings, lookup_match_mode):
                                raw_sla = row.get(lookup_sla_field, "")
                                resolved = resolve_lookup_sla(raw_sla, lookup_sla_mappings, valid_sla_classes)
                                if resolved:
                                    resolved_rank = sla_class_rank_dict.get(resolved, 0)
                                    if resolved_rank > best_rank:
                                        best_sla = resolved
                                        best_rank = resolved_rank
                        except Exception as e:
                            msg = f'Failed to process search result row for entity="{entity_object}", exception="{str(e)}"'
                            logger.error(msg)
                            if msg not in entities_exceptions_list:
                                entities_exceptions_list.append(msg)

                    if best_sla:
                        entities_matched.append({
                            "object": entity_object,
                            "resolved_sla_class": best_sla,
                        })
                        sla_distribution[best_sla] = sla_distribution.get(best_sla, 0) + 1

            run_time = round((time.time() - main_start), 3)

            if len(entities_matched) > 0:
                result_summary = f'The search query matched {len(entities_matched)} entities out of {len(data_records)} total entities.'
            else:
                result_summary = "The search query did not match any entities. Verify your field mappings and search query."

            req_summary = {
                "search_query": search_query,
                "search_rows_count": len(search_rows),
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "sla_distribution": sla_distribution,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
            }

        # render response
        if entities_failures_count == 0:
            logger.info(
                f'sla_class simulation operation has terminated, action="success", tenant_id="{tenant_id}", run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}
        else:
            logger.error(
                f'sla_class simulation operation has failed, action="failure", tenant_id="{tenant_id}", req_summary="{json.dumps(req_summary, indent=2)}"'
            )
            return {"payload": req_summary, "status": 500}

    # Apply sla_class
    def post_sla_policies_apply(self, request_info, **kwargs):
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
                            "response": "The tenant_id is required",
                            "status": 400,
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
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint applies sla policies, it requires a POST call with the following information:",
                "resource_desc": "Immediately apply and update sla policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_sla_policies/write/sla_policies_apply\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        update_comment = resp_dict.get("update_comment") or "API update"

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

        # Get trackmeconf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )["trackme_conf"]

        # Get SLA classes conf
        sla_classes = trackme_conf["sla"]["sla_classes"]

        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)

        except Exception as e:
            return {
                "payload": {
                    "response": "The sla_classes configuration is not a valid JSON",
                    "status": 400,
                },
                "status": 400,
            }

        # start
        main_start = time.time()

        #
        # KV sla policies
        #

        # sla policies KV collection
        sla_policies_collection_name = (
            f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
        )
        sla_policies_collection = service.kvstore[sla_policies_collection_name]

        # get records
        (
            sla_policies_records,
            sla_class_collection_keys,
            sla_class_collection_dict,
        ) = get_kv_collection(sla_policies_collection, sla_policies_collection_name)

        #
        # KV entities
        #

        # entities KV collection
        data_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        data_collection = service.kvstore[data_collection_name]

        # get records
        data_records, data_collection_keys, data_collection_dict = get_kv_collection(
            data_collection, data_collection_name
        )

        #
        # KV sla_class
        #

        # entities KV collection
        sla_class_collection_name = f"kv_trackme_{component}_sla_tenant_{tenant_id}"
        sla_class_collection = service.kvstore[sla_class_collection_name]

        # get records
        sla_class_records, sla_class_collection_keys, sla_class_collection_dict = (
            get_kv_collection(sla_class_collection, sla_class_collection_name)
        )

        #
        # Handle policies
        #

        # Separate policies by type: regex vs lookup vs search
        regex_policies = []
        lookup_policies = []
        search_policies = []
        for policy_record in sla_policies_records:
            policy_type = policy_record.get("sla_policy_type", "regex")
            if policy_type == "lookup":
                lookup_policies.append(policy_record)
            elif policy_type == "search":
                search_policies.append(policy_record)
            else:
                regex_policies.append(policy_record)

        # Cache for remote service connections (avoid reconnecting per policy)
        remote_services_cache = {}

        # Pre-load lookup contents once per unique (account, lookup_name)
        lookup_cache = preload_lookup_cache(
            lookup_policies, "sla_policy_lookup_name",
            remote_services_cache, service, request_info, tenant_id, logger
        )

        # Pre-parse lookup policy JSON fields once (outside entity loop)
        parsed_lookup_policies = []
        for policy_record in lookup_policies:
            lk_name = policy_record.get("sla_policy_lookup_name", "")
            policy_account = policy_record.get("account", "local")
            lk_rows = lookup_cache.get((policy_account, lk_name), [])
            if not lk_rows:
                continue

            field_mappings_raw = policy_record.get("sla_policy_lookup_field_mappings", "{}")
            try:
                if isinstance(field_mappings_raw, str):
                    field_mappings = json.loads(field_mappings_raw)
                else:
                    field_mappings = field_mappings_raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                continue

            sla_field = policy_record.get("sla_policy_lookup_sla_field", "")
            if not sla_field:
                continue

            sla_mappings_raw = policy_record.get("sla_policy_lookup_sla_mappings", "")
            sla_mappings = {}
            if sla_mappings_raw:
                try:
                    if isinstance(sla_mappings_raw, str):
                        sla_mappings = json.loads(sla_mappings_raw)
                    else:
                        sla_mappings = sla_mappings_raw
                except (json.JSONDecodeError, TypeError):
                    sla_mappings = {}

            match_mode = policy_record.get("sla_policy_lookup_match_mode", "exact")

            parsed_lookup_policies.append({
                "policy_record": policy_record,
                "lk_rows": lk_rows,
                "field_mappings": field_mappings,
                "sla_field": sla_field,
                "sla_mappings": sla_mappings,
                "match_mode": match_mode,
            })

        # Pre-execute search queries once per unique (account, query, earliest, latest)
        search_cache = preload_search_cache(
            search_policies, "sla_policy_search_query",
            "sla_policy_search_earliest", "sla_policy_search_latest",
            remote_services_cache, service, request_info, tenant_id, logger
        )

        # Pre-parse search policy JSON fields once (outside entity loop)
        parsed_search_policies = []
        for policy_record in search_policies:
            sq = policy_record.get("sla_policy_search_query", "")
            se = policy_record.get("sla_policy_search_earliest", "-5m")
            sl = policy_record.get("sla_policy_search_latest", "now")
            policy_account = policy_record.get("account", "local")
            cache_key = (policy_account, sq, se, sl)
            sr_rows = search_cache.get(cache_key, [])
            if not sr_rows:
                continue

            field_mappings_raw = policy_record.get("sla_policy_lookup_field_mappings", "{}")
            try:
                if isinstance(field_mappings_raw, str):
                    field_mappings = json.loads(field_mappings_raw)
                else:
                    field_mappings = field_mappings_raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                continue

            sla_field = policy_record.get("sla_policy_lookup_sla_field", "")
            if not sla_field:
                continue

            sla_mappings_raw = policy_record.get("sla_policy_lookup_sla_mappings", "")
            sla_mappings = {}
            if sla_mappings_raw:
                try:
                    if isinstance(sla_mappings_raw, str):
                        sla_mappings = json.loads(sla_mappings_raw)
                    else:
                        sla_mappings = sla_mappings_raw
                except (json.JSONDecodeError, TypeError):
                    sla_mappings = {}

            match_mode = policy_record.get("sla_policy_lookup_match_mode", "exact")

            parsed_search_policies.append({
                "policy_record": policy_record,
                "sr_rows": sr_rows,
                "field_mappings": field_mappings,
                "sla_field": sla_field,
                "sla_mappings": sla_mappings,
                "match_mode": match_mode,
            })

        # Counters and error list
        entities_updated_count = 0
        entities_failures_count = 0
        entities_deleted_count = 0
        entities_exceptions_list = []

        updated_records = []  # we will store the updated records here

        # each sla class in sla_classes has a rank field which defines its numerical value, loop through the records and apply the sla_class
        sla_class_rank_dict = {}
        for sla_class in sla_classes:
            sla_class_rank = sla_classes[sla_class].get("rank", 0)
            sla_class_rank_dict[sla_class] = sla_class_rank

        # Build valid SLA classes dict for lookup resolver
        valid_sla_classes = {k: True for k in sla_classes}

        # only proceed if we have entities
        if len(data_records) > 0:

            # loop through records and apply policies
            for entity_record in data_records:

                entity_key = entity_record["_key"]
                entity_object = entity_record["object"]
                sla_class = None
                sla_class_reason = None
                policy_matched = False

                # Apply regex policies
                if len(regex_policies) > 0:
                    for policy_record in regex_policies:
                        try:
                            regex = policy_record["sla_policy_regex"]
                            value = policy_record["sla_policy_value"].lower()

                            if re.match(regex, entity_record["object"]):
                                logger.info(
                                    f'tenant_id="{tenant_id}", object="{entity_object}", policy="{policy_record["sla_policy_id"]}" has matched this entity, regex="{regex}", value="{value}"'
                                )

                                # Check if a sla_class was already matched
                                if policy_matched:
                                    sla_class_matched_num = sla_class_rank_dict.get(
                                        sla_class, -1
                                    )
                                    sla_class_current_num = sla_class_rank_dict.get(
                                        value, -1
                                    )

                                    # Update if the new sla_class value is higher
                                    if sla_class_current_num > sla_class_matched_num:
                                        sla_class = value
                                        sla_class_reason = policy_record[
                                            "sla_policy_id"
                                        ]
                                else:
                                    sla_class = value
                                    sla_class_reason = policy_record["sla_policy_id"]
                                    policy_matched = True

                        except Exception as e:
                            logger.error(
                                f'context="exception", failed to apply regex policy, exception="{str(e)}"'
                            )

                # Apply lookup policies (using pre-parsed data)
                if len(parsed_lookup_policies) > 0:
                    for parsed_policy in parsed_lookup_policies:
                        try:
                            policy_record = parsed_policy["policy_record"]
                            lk_rows = parsed_policy["lk_rows"]
                            field_mappings = parsed_policy["field_mappings"]
                            sla_field = parsed_policy["sla_field"]
                            sla_mappings = parsed_policy["sla_mappings"]
                            match_mode = parsed_policy["match_mode"]

                            # Try each lookup row for this entity
                            for row in lk_rows:
                                if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                    raw_sla = row.get(sla_field, "")
                                    resolved = resolve_lookup_sla(raw_sla, sla_mappings, valid_sla_classes)
                                    if resolved is None:
                                        continue

                                    # Compare with current best sla_class (across all policies)
                                    if policy_matched:
                                        sla_class_matched_num = sla_class_rank_dict.get(sla_class, -1)
                                        sla_class_current_num = sla_class_rank_dict.get(resolved, -1)
                                        if sla_class_current_num > sla_class_matched_num:
                                            sla_class = resolved
                                            sla_class_reason = policy_record["sla_policy_id"]
                                    else:
                                        sla_class = resolved
                                        sla_class_reason = policy_record["sla_policy_id"]
                                        policy_matched = True

                        except Exception as e:
                            logger.error(
                                f'context="exception", failed to apply lookup policy, exception="{str(e)}"'
                            )

                # Apply search policies (using pre-parsed data)
                if len(parsed_search_policies) > 0:
                    for parsed_policy in parsed_search_policies:
                        try:
                            policy_record = parsed_policy["policy_record"]
                            sr_rows = parsed_policy["sr_rows"]
                            field_mappings = parsed_policy["field_mappings"]
                            sla_field = parsed_policy["sla_field"]
                            sla_mappings = parsed_policy["sla_mappings"]
                            match_mode = parsed_policy["match_mode"]

                            # Try each search result row for this entity
                            for row in sr_rows:
                                if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                    raw_sla = row.get(sla_field, "")
                                    resolved = resolve_lookup_sla(raw_sla, sla_mappings, valid_sla_classes)
                                    if resolved is None:
                                        continue

                                    # Compare with current best sla_class (across all policies)
                                    if policy_matched:
                                        sla_class_matched_num = sla_class_rank_dict.get(sla_class, -1)
                                        sla_class_current_num = sla_class_rank_dict.get(resolved, -1)
                                        if sla_class_current_num > sla_class_matched_num:
                                            sla_class = resolved
                                            sla_class_reason = policy_record["sla_policy_id"]
                                    else:
                                        sla_class = resolved
                                        sla_class_reason = policy_record["sla_policy_id"]
                                        policy_matched = True

                        except Exception as e:
                            logger.error(
                                f'context="exception", failed to apply search policy, exception="{str(e)}"'
                            )

                # Add if matched
                if policy_matched:

                    # add to updated_records
                    updated_records.append(
                        {
                            "_key": entity_key,
                            "object": entity_object,
                            "sla_class": sla_class,
                            "sla_class_reason": sla_class_reason,
                            "mtime": time.time(),
                        }
                    )

            # Update records in batches
            chunks = [
                updated_records[i : i + 500]
                for i in range(0, len(updated_records), 500)
            ]
            for chunk in chunks:
                try:
                    sla_class_collection.data.batch_save(*chunk)
                    entities_updated_count += len(chunk)
                except Exception as e:
                    entities_failures_count += len(chunk)
                    msg = f'KVstore batch save failed with exception="{str(e)}"'
                    logger.error(msg)
                    entities_exceptions_list.append(msg)

            # for record in sla_class_records, if the key of the record does not exist in data_collection_keys, delete it
            for record in sla_class_records:
                if record["_key"] not in data_collection_keys:
                    try:
                        sla_class_collection.data.delete(
                            json.dumps({"_key": record["_key"]})
                        )
                        # counter deleted
                        entities_deleted_count += 1

                    except Exception as e:
                        # counter failure
                        entities_failures_count += 1
                        msg = f'KVstore delete failed for key="{record["_key"]}", exception="{str(e)}"'
                        logger.error(msg)
                        entities_exceptions_list.append(msg)

            # refresh knowledge
            sla_class_records, sla_class_collection_keys, sla_class_collection_dict = (
                get_kv_collection(sla_class_collection, sla_class_collection_name)
            )

            # immediately apply sla_class on the data collection
            # Use data_collection_dict for O(1) key lookups instead of nested loop over all entities
            updated_data_records = []

            for sla_class_record in sla_class_records:
                entity_key = sla_class_record["_key"]
                entity_record = data_collection_dict.get(entity_key)
                if not entity_record:
                    continue

                # get the current sla_class value, we will only update the KVstore record if the final sla_class field has changed
                current_sla_class = entity_record.get("sla_class", None)

                entity_record["sla_class"] = sla_class_record["sla_class"]

                # get the policy id from sla_class_reason field, set to unknown if not found
                sla_policy_id = sla_class_record.get(
                    "sla_class_reason", "unknown"
                )

                # compare current_sla_class and sla_class, if they are different, add the record to the updated_data_records list
                if current_sla_class:
                    if current_sla_class != sla_class_record["sla_class"]:
                        entity_record["mtime"] = time.time()
                        entity_record["sla_updated"] = 1
                        entity_record["sla_class_reason"] = (
                            f"sla_policy_id: {sla_policy_id}"
                        )
                        updated_data_records.append(entity_record)

                else:  # we have no current sla_class, we need to update the record
                    entity_record["mtime"] = time.time()
                    entity_record["sla_updated"] = 1
                    entity_record["sla_class_reason"] = (
                        f"sla_policy_id: {sla_policy_id}"
                    )
                    updated_data_records.append(entity_record)

            # Batch save updated entity records to data collection
            if updated_data_records:
                data_chunks = [
                    updated_data_records[i : i + 500]
                    for i in range(0, len(updated_data_records), 500)
                ]
                for chunk in data_chunks:
                    try:
                        data_collection.data.batch_save(*chunk)
                        logger.info(
                            f'tenant_id="{tenant_id}", applied sla_class to {len(chunk)} entities in data collection'
                        )
                    except Exception as e:
                        msg = f'Data collection batch save failed with exception="{str(e)}"'
                        logger.error(msg)
                        entities_failures_count += len(chunk)
                        entities_exceptions_list.append(msg)

        # set action
        if entities_failures_count == 0:
            action = "success"
        else:
            action = "failure"

        # get run_time
        run_time = round((time.time() - main_start), 3)

        # request summary
        req_summary = {
            "tenant_id": tenant_id,
            "action": action,
            "run_time": run_time,
            "kvstore_lookup_collection": f"trackme_{component}_sla_tenant_{tenant_id}",
            "sla_policies_no_records": len(sla_policies_records),
            "regex_policies_count": len(regex_policies),
            "lookup_policies_count": len(lookup_policies),
            "search_policies_count": len(search_policies),
            "kvstore_collection_entities_count": len(data_records),
            "entities_updated_count": entities_updated_count,
            "entities_failures_count": entities_failures_count,
            "entities_deleted_count": entities_deleted_count,
            "error_messages": entities_exceptions_list,
        }

        # Audit
        try:
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                action,
                "apply sla policies",
                "sla_policies",
                f"splk-{component}",
                json.dumps(req_summary, default=str),
                f'SLA policies applied for component="{component}" '
                f'(updated={entities_updated_count}, failed={entities_failures_count}, '
                f'deleted={entities_deleted_count})',
                str(update_comment),
            )
        except Exception as audit_e:
            logger.warning(
                f'function=post_sla_policies_apply, tenant_id="{tenant_id}", '
                f'step="audit", exception="{str(audit_e)}"'
            )

        # render response
        if action == "success":
            logger.info(
                f'sla_class apply operation has terminated, action="{action}", tenant_id="{tenant_id}", run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}

        else:
            logger.error(
                f'sla_class apply operation has failed, action="{action}", tenant_id="{tenant_id}", req_summary="{json.dumps(req_summary, indent=2)}"'
            )
            return {"payload": req_summary, "status": 500}
