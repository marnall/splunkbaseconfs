#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_priority_policies.py"
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
    "trackme.rest.splk_priority_policies_power",
    "trackme_rest_api_splk_priority_policies_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    get_kv_collection,
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
)
from trackme_libs_policies import (
    collect_all_fields,
    validate_lookup_name,
    load_lookup_content,
    match_entity_to_lookup_row,
    resolve_lookup_priority,
    validate_search_query,
    execute_search_content,
    resolve_service_for_account,
    preload_lookup_cache,
    preload_search_cache,
    MULTI_VALUE_FIELDS,
    PRIORITY_DICT,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkPriorityPoliciesWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkPriorityPoliciesWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_priority_policies(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_priority_policies/write",
            "resource_group_desc": "Endpoints related to the management of priorities (power operations)",
        }

        return {"payload": response, "status": 200}

    # Add new policy
    def post_priority_policies_add(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        component = None
        priority_policy_id = None
        priority_policy_type = "regex"
        priority_policy_value = None
        priority_policy_regex = None
        priority_policy_regex_match_field = "object"
        # Lookup-specific fields
        priority_policy_lookup_name = ""
        priority_policy_lookup_field_mappings = ""
        priority_policy_lookup_priority_field = ""
        priority_policy_lookup_priority_mappings = ""
        priority_policy_lookup_match_mode = "exact"
        # Search-specific fields
        priority_policy_search_query = ""
        priority_policy_search_earliest = "-5m"
        priority_policy_search_latest = "now"
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
                    priority_policy_id = resp_dict["priority_policy_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The priority_policy_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # Get policy type (defaults to "regex" for backward compatibility)
                priority_policy_type = resp_dict.get("priority_policy_type", "regex")
                if priority_policy_type not in ("regex", "lookup", "search"):
                    return {
                        "payload": {
                            "response": "The priority_policy_type is not valid, valid options are: regex, lookup, search",
                            "status": 400,
                        },
                        "status": 400,
                    }

                if priority_policy_type == "regex":
                    # Regex mode: require value and regex
                    try:
                        priority_policy_value = resp_dict["priority_policy_value"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_value is required for regex policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # if priority_policy_value is a string, make it lower case
                    if isinstance(priority_policy_value, str):
                        priority_policy_value = priority_policy_value.lower()
                        if priority_policy_value not in (
                            "low",
                            "medium",
                            "high",
                            "critical",
                            "pending",
                        ):
                            return {
                                "payload": {
                                    "response": "The priority_policy_value is not a valid value, valid options are: low, medium, high, critical, pending",
                                },
                                "status": 400,
                            }
                    else:
                        return {
                            "payload": {
                                "response": "The priority_policy_value should be a string",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        priority_policy_regex = resp_dict["priority_policy_regex"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_regex is required for regex policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # verify that the regex is valid
                    try:
                        re.compile(priority_policy_regex)
                    except re.error:
                        return {
                            "payload": {
                                "response": "The priority_policy_regex is not a valid regular expression",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional: field to match the regex against (default: "object")
                    priority_policy_regex_match_field = resp_dict.get("priority_policy_regex_match_field", "object")
                    if not isinstance(priority_policy_regex_match_field, str) or not priority_policy_regex_match_field.strip():
                        priority_policy_regex_match_field = "object"

                elif priority_policy_type == "lookup":
                    # Lookup mode: require lookup-specific fields
                    priority_policy_value = "from_lookup"
                    priority_policy_regex = ""

                    try:
                        priority_policy_lookup_name = resp_dict["priority_policy_lookup_name"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_name is required for lookup policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate lookup name before any Splunk API access
                    try:
                        validate_lookup_name(priority_policy_lookup_name)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        priority_policy_lookup_field_mappings = resp_dict["priority_policy_lookup_field_mappings"]
                        # Validate JSON and ensure it's a non-empty dict
                        if isinstance(priority_policy_lookup_field_mappings, str):
                            parsed = json.loads(priority_policy_lookup_field_mappings)
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                return {
                                    "payload": {
                                        "response": "The priority_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        elif isinstance(priority_policy_lookup_field_mappings, dict):
                            if len(priority_policy_lookup_field_mappings) == 0:
                                return {
                                    "payload": {
                                        "response": "The priority_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                            priority_policy_lookup_field_mappings = json.dumps(priority_policy_lookup_field_mappings)
                        else:
                            return {
                                "payload": {
                                    "response": "The priority_policy_lookup_field_mappings must be a JSON string or object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, ValueError):
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_field_mappings is required for lookup policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        priority_policy_lookup_priority_field = resp_dict["priority_policy_lookup_priority_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_priority_field is required for lookup policies",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    if not priority_policy_lookup_priority_field:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_priority_field must not be empty",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional fields
                    priority_policy_lookup_priority_mappings = resp_dict.get("priority_policy_lookup_priority_mappings", "")
                    if priority_policy_lookup_priority_mappings:
                        if isinstance(priority_policy_lookup_priority_mappings, dict):
                            priority_policy_lookup_priority_mappings = json.dumps(priority_policy_lookup_priority_mappings)
                        elif isinstance(priority_policy_lookup_priority_mappings, str):
                            try:
                                parsed_mappings = json.loads(priority_policy_lookup_priority_mappings)
                                if not isinstance(parsed_mappings, dict):
                                    return {
                                        "payload": {
                                            "response": "The priority_policy_lookup_priority_mappings must be a JSON object (dict), not an array or other type",
                                            "status": 400,
                                        },
                                        "status": 400,
                                    }
                            except (json.JSONDecodeError, ValueError):
                                return {
                                    "payload": {
                                        "response": "The priority_policy_lookup_priority_mappings is not valid JSON",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        else:
                            return {
                                "payload": {
                                    "response": "The priority_policy_lookup_priority_mappings must be a JSON string or object (dict)",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    priority_policy_lookup_match_mode = resp_dict.get("priority_policy_lookup_match_mode", "exact")
                    if priority_policy_lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_match_mode is not valid, valid options are: exact, wildcard",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif priority_policy_type == "search":
                    # Search mode: require search query, reuse lookup field mappings
                    priority_policy_value = "from_search"
                    priority_policy_regex = ""
                    priority_policy_lookup_name = ""

                    # Search query (required)
                    priority_policy_search_query = resp_dict.get("priority_policy_search_query", "")
                    if not priority_policy_search_query:
                        return {
                            "payload": {
                                "response": "The priority_policy_search_query is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate search query
                    try:
                        validate_search_query(priority_policy_search_query)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Search time range (optional)
                    priority_policy_search_earliest = resp_dict.get("priority_policy_search_earliest", "-5m")
                    priority_policy_search_latest = resp_dict.get("priority_policy_search_latest", "now")

                    # Field mappings (required, same as lookup)
                    try:
                        priority_policy_lookup_field_mappings = resp_dict["priority_policy_lookup_field_mappings"]
                        # Validate JSON and ensure it's a non-empty dict
                        if isinstance(priority_policy_lookup_field_mappings, str):
                            parsed = json.loads(priority_policy_lookup_field_mappings)
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                return {
                                    "payload": {
                                        "response": "The priority_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        elif isinstance(priority_policy_lookup_field_mappings, dict):
                            if len(priority_policy_lookup_field_mappings) == 0:
                                return {
                                    "payload": {
                                        "response": "The priority_policy_lookup_field_mappings must be a non-empty JSON object",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                            priority_policy_lookup_field_mappings = json.dumps(priority_policy_lookup_field_mappings)
                        else:
                            return {
                                "payload": {
                                    "response": "The priority_policy_lookup_field_mappings must be a JSON string or object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, ValueError):
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_field_mappings is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Priority field (required)
                    try:
                        priority_policy_lookup_priority_field = resp_dict["priority_policy_lookup_priority_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_priority_field is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    if not priority_policy_lookup_priority_field:
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_priority_field must not be empty",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Priority mappings (optional)
                    priority_policy_lookup_priority_mappings = resp_dict.get("priority_policy_lookup_priority_mappings", "")
                    if priority_policy_lookup_priority_mappings:
                        if isinstance(priority_policy_lookup_priority_mappings, dict):
                            priority_policy_lookup_priority_mappings = json.dumps(priority_policy_lookup_priority_mappings)
                        elif isinstance(priority_policy_lookup_priority_mappings, str):
                            try:
                                parsed_mappings = json.loads(priority_policy_lookup_priority_mappings)
                                if not isinstance(parsed_mappings, dict):
                                    return {
                                        "payload": {
                                            "response": "The priority_policy_lookup_priority_mappings must be a JSON object (dict), not an array or other type",
                                            "status": 400,
                                        },
                                        "status": 400,
                                    }
                            except (json.JSONDecodeError, ValueError):
                                return {
                                    "payload": {
                                        "response": "The priority_policy_lookup_priority_mappings is not valid JSON",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                        else:
                            return {
                                "payload": {
                                    "response": "The priority_policy_lookup_priority_mappings must be a JSON string or object (dict)",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    # Match mode (optional)
                    priority_policy_lookup_match_mode = resp_dict.get("priority_policy_lookup_match_mode", "exact")
                    if priority_policy_lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "The priority_policy_lookup_match_mode is not valid, valid options are: exact, wildcard",
                                "status": 400,
                            },
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new priority policy or updates a policy if it exists already, it requires a POST call with the following data:",
                "resource_desc": "Add or update a priority policy (supports regex, lookup and search modes)",
                "resource_spl_example": r"| trackme mode=post url=\"/services/trackme/v2/splk_priority_policies/write/priority_policies_add\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'priority_policy_id': 'linux_secure', 'priority_policy_value': 'high', 'priority_policy_regex': '\:linux_secure$'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "priority_policy_id": "(required) ID of the priority policy",
                        "priority_policy_type": "(optional) Policy type: 'regex' (default), 'lookup' or 'search'",
                        "priority_policy_regex": "(required for regex) The regular expression to be used by the priority policy",
                        "priority_policy_regex_match_field": "(optional for regex, default: object) The entity field to match the regex against (e.g., object, alias, data_index, data_sourcetype)",
                        "priority_policy_value": "(required for regex) priority value (low/medium/high/critical/pending) to be applied",
                        "priority_policy_lookup_name": "(required for lookup) The Splunk lookup transform name",
                        "priority_policy_lookup_field_mappings": "(required for lookup/search) JSON mapping of lookup/search result fields to entity fields",
                        "priority_policy_lookup_priority_field": "(required for lookup/search) The field in the lookup/search results containing priority values",
                        "priority_policy_lookup_priority_mappings": "(optional for lookup/search) JSON mapping of foreign priority values to TrackMe format",
                        "priority_policy_lookup_match_mode": "(optional for lookup/search) Match mode: 'exact' (default, case-insensitive) or 'wildcard'",
                        "priority_policy_search_query": "(required for search) The SPL search query to execute",
                        "priority_policy_search_earliest": "(optional for search, default: -5m) The earliest time for the search",
                        "priority_policy_search_latest": "(optional for search, default: now) The latest time for the search",
                        "account": "(optional) The remote Splunk deployment account name, defaults to local",
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

        # optional account (for remote Splunk deployment)
        account = resp_dict.get("account", "local") if resp_dict else "local"

        # Define the KV query
        query_string = {
            "priority_policy_id": priority_policy_id,
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

        # For lookup and search policies, resolve remote account upfront to validate connectivity
        if priority_policy_type in ("lookup", "search"):
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
            if priority_policy_type == "lookup":
                try:
                    target_service.confs["transforms"][priority_policy_lookup_name]
                except Exception as e:
                    return {
                        "payload": {
                            "response": f'The lookup transform "{priority_policy_lookup_name}" was not found in Splunk',
                            "status": 400,
                        },
                        "status": 400,
                    }

        # Data collection
        collection_name = f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Get the current record
        try:
            record = collection.data.query(query=json.dumps(query_string))
            key = record[0].get("_key")

        except Exception as e:
            key = None

        # Build the record data (common for both insert and update)
        record_data = {
            "priority_policy_id": priority_policy_id,
            "priority_policy_type": priority_policy_type,
            "priority_policy_value": priority_policy_value,
            "priority_policy_regex": priority_policy_regex if priority_policy_regex else "",
            "priority_policy_regex_match_field": priority_policy_regex_match_field,
            "priority_policy_lookup_name": priority_policy_lookup_name,
            "priority_policy_lookup_field_mappings": priority_policy_lookup_field_mappings,
            "priority_policy_lookup_priority_field": priority_policy_lookup_priority_field,
            "priority_policy_lookup_priority_mappings": priority_policy_lookup_priority_mappings,
            "priority_policy_lookup_match_mode": priority_policy_lookup_match_mode,
            "priority_policy_search_query": priority_policy_search_query,
            "priority_policy_search_earliest": priority_policy_search_earliest,
            "priority_policy_search_latest": priority_policy_search_latest,
            "mtime": time.time(),
            "account": account,
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
                        "update priority policy",
                        str(priority_policy_id),
                        f"splk-{component}",
                        collection.data.query(query=json.dumps(query_string)),
                        "The priority policy was updated successfully",
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
                        "add priority policy",
                        str(priority_policy_id),
                        f"splk-{component}",
                        collection.data.query(query=json.dumps(query_string)),
                        "The priority policy was added successfully",
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
                "response": f'the priority policy priority_policy_id="{priority_policy_id}" was {action_desc} successfully',
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
    def post_priority_policies_del(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
        priority_policy_id_list = None
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
                    priority_policy_id_list = resp_dict["priority_policy_id_list"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The priority_policy_id_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # if priority_policy_id_list is a string, turn into a list
                if isinstance(priority_policy_id_list, str):
                    priority_policy_id_list = priority_policy_id_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes priority policies, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more priority policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_priority_policies/write/priority_policies_del\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'priority_policy_id': 'linux_secure,linux_sec'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
                        "priority_policy_id_list": "(required) Comma separated list of priority policies",
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
        collection_name = f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # entities KV collection
        priority_collection_name = f"kv_trackme_{component}_priority_tenant_{tenant_id}"
        priority_collection = service.kvstore[priority_collection_name]

        # records summary
        records = []

        # loop
        for item in priority_policy_id_list:

            # Define the KV query
            query_string = {
                "priority_policy_id": item,
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
                            "delete priority policy",
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

                    #
                    # clean up the priority collection
                    #

                    # Define the KV query
                    query_string = {
                        "priority_reason": item,
                    }

                    # Get records
                    priority_records = priority_collection.data.query(
                        query=json.dumps(query_string)
                    )

                    for priority_record in priority_records:
                        priority_record_key = priority_record.get("_key")

                        # silently remove the record
                        try:
                            priority_collection.data.delete(
                                json.dumps({"_key": priority_record_key})
                            )
                        except:
                            pass

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
                            "delete priority policy",
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
                        "delete priority policy",
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
    def post_priority_policies_update(self, request_info, **kwargs):
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
                "resource_desc": "Update one or more priority policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_priority_policies/write/priority_policies_update\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'records_list': '<redacted_json_records>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
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

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
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
                    "priority_policy_id": item.get("priority_policy_id"),
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
                    item_policy_type = item.get("priority_policy_type", "regex")
                    if item_policy_type not in ("regex", "lookup", "search"):
                        processed_count += 1
                        failures_count += 1
                        result = {
                            "action": "update",
                            "result": "failure",
                            "record": item,
                            "exception": f"Invalid priority_policy_type '{item_policy_type}', valid options are: regex, lookup, search",
                        }
                        records.append(result)
                        continue

                    # Update the record
                    priority_policy_value = item.get("priority_policy_value")

                    if item_policy_type == "regex":
                        # Regex mode: validate priority value
                        if isinstance(priority_policy_value, str):
                            priority_policy_value = priority_policy_value.lower()
                            if priority_policy_value not in (
                                "low",
                                "medium",
                                "high",
                                "critical",
                                "pending",
                            ):
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "The priority_policy_value is not a valid value, valid options are: low, medium, high, critical, pending",
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
                                "exception": "The priority_policy_value should be a string",
                            }
                            records.append(result)
                            continue

                        # Validate regex is present and valid
                        priority_regex = item.get("priority_policy_regex", "")
                        if not priority_regex:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_regex is required for regex policies",
                            }
                            records.append(result)
                            continue
                        try:
                            re.compile(priority_regex)
                        except re.error:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_regex is not a valid regular expression",
                            }
                            records.append(result)
                            continue

                    elif item_policy_type == "lookup":
                        # Lookup mode: accept "from_lookup" as value
                        priority_policy_value = "from_lookup"

                        # Validate required lookup fields
                        lookup_name = item.get("priority_policy_lookup_name", "")
                        if not lookup_name:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_name is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        try:
                            validate_lookup_name(lookup_name)
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

                        lookup_field_mappings = item.get("priority_policy_lookup_field_mappings", "")
                        if not lookup_field_mappings:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_field_mappings is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        try:
                            parsed = json.loads(lookup_field_mappings) if isinstance(lookup_field_mappings, str) else lookup_field_mappings
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "priority_policy_lookup_field_mappings must be a non-empty JSON object",
                                }
                                records.append(result)
                                continue
                        except (json.JSONDecodeError, TypeError):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_field_mappings is not valid JSON",
                            }
                            records.append(result)
                            continue

                        priority_field = item.get("priority_policy_lookup_priority_field", "")
                        if not priority_field:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_priority_field is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        # Validate match mode
                        lookup_match_mode = item.get("priority_policy_lookup_match_mode", "exact")
                        if lookup_match_mode not in ("exact", "wildcard"):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                            }
                            records.append(result)
                            continue

                        # Validate priority mappings if provided
                        priority_mappings_raw = item.get("priority_policy_lookup_priority_mappings", "")
                        if priority_mappings_raw:
                            try:
                                if isinstance(priority_mappings_raw, str):
                                    parsed = json.loads(priority_mappings_raw)
                                elif isinstance(priority_mappings_raw, dict):
                                    parsed = priority_mappings_raw
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
                                    "exception": "priority_policy_lookup_priority_mappings must be a valid JSON object (dict)",
                                }
                                records.append(result)
                                continue

                    elif item_policy_type == "search":
                        # Search mode: accept "from_search" as value
                        priority_policy_value = "from_search"

                        # Validate search query
                        search_query = item.get("priority_policy_search_query", "")
                        if not search_query:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_search_query is required for search policies",
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
                        lookup_field_mappings = item.get("priority_policy_lookup_field_mappings", "")
                        if not lookup_field_mappings:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_field_mappings is required for search policies",
                            }
                            records.append(result)
                            continue

                        try:
                            parsed = json.loads(lookup_field_mappings) if isinstance(lookup_field_mappings, str) else lookup_field_mappings
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "priority_policy_lookup_field_mappings must be a non-empty JSON object",
                                }
                                records.append(result)
                                continue
                        except (json.JSONDecodeError, TypeError):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_field_mappings is not valid JSON",
                            }
                            records.append(result)
                            continue

                        priority_field = item.get("priority_policy_lookup_priority_field", "")
                        if not priority_field:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_priority_field is required for search policies",
                            }
                            records.append(result)
                            continue

                        # Validate match mode
                        lookup_match_mode = item.get("priority_policy_lookup_match_mode", "exact")
                        if lookup_match_mode not in ("exact", "wildcard"):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "priority_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                            }
                            records.append(result)
                            continue

                        # Validate priority mappings if provided
                        priority_mappings_raw = item.get("priority_policy_lookup_priority_mappings", "")
                        if priority_mappings_raw:
                            try:
                                if isinstance(priority_mappings_raw, str):
                                    parsed = json.loads(priority_mappings_raw)
                                elif isinstance(priority_mappings_raw, dict):
                                    parsed = priority_mappings_raw
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
                                    "exception": "priority_policy_lookup_priority_mappings must be a valid JSON object (dict)",
                                }
                                records.append(result)
                                continue

                    # Normalize dict values to JSON strings for consistent KVstore storage
                    _field_mappings = item.get("priority_policy_lookup_field_mappings", "")
                    if isinstance(_field_mappings, dict):
                        _field_mappings = json.dumps(_field_mappings)
                    _priority_mappings = item.get("priority_policy_lookup_priority_mappings", "")
                    if isinstance(_priority_mappings, dict):
                        _priority_mappings = json.dumps(_priority_mappings)

                    # Build update record with all fields
                    update_data = {
                        "priority_policy_id": item.get("priority_policy_id"),
                        "priority_policy_type": item_policy_type,
                        "priority_policy_value": priority_policy_value,
                        "priority_policy_regex": item.get("priority_policy_regex", ""),
                        "priority_policy_regex_match_field": item.get("priority_policy_regex_match_field", "object"),
                        "priority_policy_lookup_name": item.get("priority_policy_lookup_name", ""),
                        "priority_policy_lookup_field_mappings": _field_mappings,
                        "priority_policy_lookup_priority_field": item.get("priority_policy_lookup_priority_field", ""),
                        "priority_policy_lookup_priority_mappings": _priority_mappings,
                        "priority_policy_lookup_match_mode": item.get("priority_policy_lookup_match_mode", "exact"),
                        "priority_policy_search_query": item.get("priority_policy_search_query", ""),
                        "priority_policy_search_earliest": item.get("priority_policy_search_earliest", "-5m"),
                        "priority_policy_search_latest": item.get("priority_policy_search_latest", "now"),
                        "mtime": time.time(),
                        "account": item.get("account", "local"),
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
                            "update priority policies",
                            str(item),
                            "dsm",
                            record,
                            "The priority policy was updated successfully",
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
                            "update priority policies",
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
                        "update priority policies",
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

    # Simulate priority
    def post_priority_policies_simulate(self, request_info, **kwargs):
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

                # Get policy type (default: regex for backward compatibility)
                priority_policy_type = resp_dict.get("priority_policy_type", "regex")
                if priority_policy_type not in ("regex", "lookup", "search"):
                    return {
                        "payload": {
                            "response": "The priority_policy_type must be 'regex', 'lookup' or 'search'",
                            "status": 400,
                        },
                        "status": 400,
                    }

                if priority_policy_type == "regex":
                    # Regex mode: require regex_value and priority
                    try:
                        regex_value = resp_dict["regex_value"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument regex_value is required for regex simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        priority = resp_dict["priority"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument priority is required for regex simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    # priority should be a string, valid options: low, medium, high, critical, pending
                    if isinstance(priority, str):
                        priority = priority.lower()
                        if priority not in ("low", "medium", "high", "critical", "pending"):
                            return {
                                "payload": {
                                    "response": "The priority is not a valid value, valid options are: low, medium, high, critical, pending",
                                },
                                "status": 400,
                            }
                    else:
                        return {
                            "payload": {
                                "response": "The priority should be a string",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional: field to match the regex against (default: "object")
                    regex_match_field = resp_dict.get("regex_match_field", "object")
                    if not isinstance(regex_match_field, str) or not regex_match_field.strip():
                        regex_match_field = "object"

                elif priority_policy_type == "lookup":
                    # Lookup mode: require lookup_name, field_mappings, priority_field
                    try:
                        lookup_name = resp_dict["lookup_name"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument lookup_name is required for lookup simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate lookup name before any Splunk API access
                    try:
                        validate_lookup_name(lookup_name)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        field_mappings_raw = resp_dict["field_mappings"]
                        if isinstance(field_mappings_raw, str):
                            field_mappings = json.loads(field_mappings_raw)
                        else:
                            field_mappings = field_mappings_raw
                        if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "field_mappings must be a non-empty JSON object mapping lookup fields to entity fields",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, TypeError, KeyError):
                        return {
                            "payload": {
                                "response": "field_mappings is required and must be valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    try:
                        priority_field = resp_dict["priority_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument priority_field is required for lookup simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional: priority_mappings and match_mode
                    priority_mappings_raw = resp_dict.get("priority_mappings", "")
                    priority_mappings = {}
                    if priority_mappings_raw:
                        try:
                            if isinstance(priority_mappings_raw, str):
                                parsed_mappings = json.loads(priority_mappings_raw)
                            else:
                                parsed_mappings = priority_mappings_raw
                            if not isinstance(parsed_mappings, dict):
                                return {
                                    "payload": {
                                        "response": "priority_mappings must be a JSON object (dict), not an array or other type",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                            priority_mappings = parsed_mappings
                        except (json.JSONDecodeError, TypeError):
                            return {
                                "payload": {
                                    "response": "priority_mappings must be valid JSON",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    match_mode = resp_dict.get("match_mode", "exact")
                    if match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "match_mode must be 'exact' or 'wildcard'",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif priority_policy_type == "search":
                    # Search mode: require search_query, field_mappings, priority_field
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
                        field_mappings_raw = resp_dict["field_mappings"]
                        if isinstance(field_mappings_raw, str):
                            field_mappings = json.loads(field_mappings_raw)
                        else:
                            field_mappings = field_mappings_raw
                        if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "field_mappings must be a non-empty JSON object mapping search result fields to entity fields",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, TypeError, KeyError):
                        return {
                            "payload": {
                                "response": "field_mappings is required and must be valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Priority field (required)
                    try:
                        priority_field = resp_dict["priority_field"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument priority_field is required for search simulation",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional: priority_mappings and match_mode
                    priority_mappings_raw = resp_dict.get("priority_mappings", "")
                    priority_mappings = {}
                    if priority_mappings_raw:
                        try:
                            if isinstance(priority_mappings_raw, str):
                                parsed_mappings = json.loads(priority_mappings_raw)
                            else:
                                parsed_mappings = priority_mappings_raw
                            if not isinstance(parsed_mappings, dict):
                                return {
                                    "payload": {
                                        "response": "priority_mappings must be a JSON object (dict), not an array or other type",
                                        "status": 400,
                                    },
                                    "status": 400,
                                }
                            priority_mappings = parsed_mappings
                        except (json.JSONDecodeError, TypeError):
                            return {
                                "payload": {
                                    "response": "priority_mappings must be valid JSON",
                                    "status": 400,
                                },
                                "status": 400,
                            }

                    match_mode = resp_dict.get("match_mode", "exact")
                    if match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "match_mode must be 'exact' or 'wildcard'",
                                "status": 400,
                            },
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint simulates a priority policy, it requires a POST call with the following information:",
                "resource_desc": "Simulates a priority policy (supports regex, lookup and search modes)",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_priority_policies/write/priority_policies_simulate" body="{\'tenant_id\': \'mytenant\', \'regex_value\': \'^org_eu.*\', \'priority\': \'high\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "REQUIRED. The component (one of: dsm, dhm, mhm, wlk, flx, fqm)",
                        "priority_policy_type": "OPTIONAL. The policy type — one of: regex, lookup, search (defaults to 'regex'). Subsequent fields are conditionally required based on this value",
                        "account": "OPTIONAL. The remote Splunk deployment account name to use for lookup/search operations (defaults to 'local')",
                        "regex_value": "REQUIRED when priority_policy_type=regex. The regex to be used for the simulation",
                        "priority": "REQUIRED when priority_policy_type=regex. The priority value to assign to matching entities — one of: low, medium, high, critical, pending",
                        "regex_match_field": "OPTIONAL when priority_policy_type=regex. The entity field to match the regex against (defaults to 'object'). Other valid options: alias, data_index, data_sourcetype",
                        "lookup_name": "REQUIRED when priority_policy_type=lookup. The Splunk lookup transform name",
                        "field_mappings": 'REQUIRED when priority_policy_type=lookup OR priority_policy_type=search. JSON mapping of lookup/search-result fields to entity fields, e.g. {"index": "data_index"}',
                        "priority_field": "REQUIRED when priority_policy_type=lookup OR priority_policy_type=search. The field in the lookup/search results containing priority values",
                        "priority_mappings": 'OPTIONAL when priority_policy_type=lookup OR priority_policy_type=search. JSON mapping of foreign priority values to TrackMe priorities, e.g. {"P1": "critical"}',
                        "match_mode": "OPTIONAL when priority_policy_type=lookup OR priority_policy_type=search. Match mode — one of: exact (case-insensitive, default) or wildcard (supports * and ?)",
                        "search_query": "REQUIRED when priority_policy_type=search. The SPL search query to execute",
                        "earliest": "OPTIONAL when priority_policy_type=search. The earliest time for the search (defaults to '-5m')",
                        "latest": "OPTIONAL when priority_policy_type=search. The latest time for the search (defaults to 'now')",
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

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

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

        #
        # Simulate based on policy type
        #

        if priority_policy_type == "regex":
            #
            # Regex simulation (existing behavior)
            #

            priority_policies_records = [
                {
                    "priority_policy_regex": regex_value,
                    "priority_policy_value": priority,
                }
            ]

            # Counters and error list
            entities_failures_count = 0
            entities_exceptions_list = []
            entities_matched = []

            # only proceed if we have entities
            if len(data_records) > 0:

                # loop through records and apply policies
                for entity_record in data_records:

                    entity_key = entity_record["_key"]
                    entity_object = entity_record["object"]

                    # apply policies
                    if len(priority_policies_records) > 0:
                        for policy_record in priority_policies_records:

                            # check that the regex expression is a valid regex expression
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
                                # apply regex
                                regex = policy_record["priority_policy_regex"]
                                value = policy_record["priority_policy_value"]

                                # make it lower case
                                if isinstance(value, str):
                                    value = value.lower()

                                # Use configurable match field (from simulate request param)
                                target_value = str(entity_record.get(regex_match_field, ""))
                                # For multi-value fields (e.g. DHM data_index/data_sourcetype),
                                # split on comma and match against each individual value
                                if regex_match_field in MULTI_VALUE_FIELDS:
                                    target_values = [v.strip() for v in target_value.split(",") if v.strip()]
                                else:
                                    target_values = [target_value]
                                if any(re.match(regex, v) for v in target_values):
                                    logger.info(
                                        f'tenant_id="{tenant_id}", object="{entity_object}", regex has matched this entity on field="{regex_match_field}", regex="{regex}", value="{value}"'
                                    )

                                    # append to our list
                                    if not entity_object in entities_matched:
                                        entities_matched.append(entity_object)

                                else:
                                    logger.info(
                                        f'tenant_id="{tenant_id}", object="{entity_object}", regex has not matched this entity on field="{regex_match_field}", regex="{regex}", value="{value}"'
                                    )

                            except Exception as e:
                                logger.error(
                                    f'context="exception", failed to apply policy, exception="{str(e)}"'
                                )

            # set action
            if entities_failures_count == 0:
                action = "success"
            else:
                action = "failure"

            # get run_time
            run_time = round((time.time() - main_start), 3)

            # create a result summary
            if len(entities_matched) > 0:
                result_summary = f"The regex has matched {len(entities_matched)} entities."
            else:
                result_summary = "The regex has not matched any entities, verify your inputs and try again."

            # request summary
            req_summary = {
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
                "regex_is_valid": "true",
            }

            # render response
            if action == "success":
                logger.info(
                    f'priority simulation operation has terminated, action="{action}", tenant_id="{tenant_id}", run_time="{run_time}"'
                )
                return {"payload": req_summary, "status": 200}

            else:
                logger.error(
                    f'priority simulation operation has failed, action="{action}", tenant_id="{tenant_id}", req_summary="{json.dumps(req_summary, indent=2)}"'
                )
                return {"payload": req_summary, "status": 500}

        elif priority_policy_type == "lookup":
            #
            # Lookup simulation
            #

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

            # Validate the lookup transform exists (prevents SPL injection)
            try:
                target_service.confs["transforms"][lookup_name]
            except Exception:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'The lookup transform "{lookup_name}" does not exist',
                    },
                    "status": 404,
                }

            # Load lookup content
            try:
                lookup_rows = load_lookup_content(target_service, lookup_name, max_rows=50000)
            except Exception as e:
                logger.error(
                    f'tenant_id="{tenant_id}", failed to load lookup "{lookup_name}", exception="{str(e)}"'
                )
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'Failed to load lookup "{lookup_name}": {str(e)}',
                    },
                    "status": 500,
                }

            if len(lookup_rows) == 0:
                return {
                    "payload": {
                        "lookup_rows_count": 0,
                        "entities_matched_count": 0,
                        "entities_matched": [],
                        "priority_distribution": {},
                        "result_summary": f'The lookup "{lookup_name}" is empty or could not be loaded.',
                    },
                    "status": 200,
                }

            # Validate that priority_field exists in lookup
            lookup_fields = collect_all_fields(lookup_rows)
            if priority_field not in lookup_fields:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'The priority_field "{priority_field}" was not found in the lookup fields: {lookup_fields}',
                    },
                    "status": 400,
                }

            # Validate that field_mappings keys exist in lookup
            for lk_field in field_mappings.keys():
                if lk_field not in lookup_fields:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'The lookup field "{lk_field}" in field_mappings was not found in the lookup fields: {lookup_fields}',
                        },
                        "status": 400,
                    }

            # Counters
            entities_matched = []
            priority_distribution = {}

            # only proceed if we have entities
            if len(data_records) > 0:

                for entity_record in data_records:

                    entity_object = entity_record.get("object", "")
                    entity_matched = False
                    entity_resolved_priority = None

                    # Try each lookup row
                    for row in lookup_rows:

                        if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):

                            # Resolve priority from the lookup row
                            raw_priority = row.get(priority_field, "")
                            resolved = resolve_lookup_priority(raw_priority, priority_mappings)

                            if resolved is None:
                                # Could not resolve priority for this row, skip
                                continue

                            # If entity already matched with a lower priority, upgrade
                            if entity_resolved_priority is None:
                                entity_resolved_priority = resolved
                            else:
                                if PRIORITY_DICT.get(resolved, 0) > PRIORITY_DICT.get(entity_resolved_priority, 0):
                                    entity_resolved_priority = resolved

                            entity_matched = True

                    if entity_matched and entity_resolved_priority:
                        entities_matched.append({
                            "object": entity_object,
                            "resolved_priority": entity_resolved_priority,
                        })

                        # Update priority distribution
                        priority_distribution[entity_resolved_priority] = priority_distribution.get(entity_resolved_priority, 0) + 1

            # get run_time
            run_time = round((time.time() - main_start), 3)

            # create result summary
            if len(entities_matched) > 0:
                result_summary = f'The lookup "{lookup_name}" matched {len(entities_matched)} entities out of {len(data_records)} total entities.'
            else:
                result_summary = f'The lookup "{lookup_name}" did not match any entities. Verify your field mappings and lookup content.'

            req_summary = {
                "lookup_name": lookup_name,
                "lookup_rows_count": len(lookup_rows),
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "priority_distribution": priority_distribution,
                "field_mappings": field_mappings,
                "priority_field": priority_field,
                "priority_mappings": priority_mappings,
                "match_mode": match_mode,
                "result_summary": result_summary,
            }

            logger.info(
                f'priority lookup simulation has terminated, tenant_id="{tenant_id}", lookup="{lookup_name}", '
                f'matched={len(entities_matched)}/{len(data_records)}, run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}

        elif priority_policy_type == "search":
            #
            # Search simulation
            #

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
                        "priority_distribution": {},
                        "result_summary": "The search query returned no results.",
                    },
                    "status": 200,
                }

            # Validate that priority_field exists in search results
            search_fields = collect_all_fields(search_rows)
            if priority_field not in search_fields:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'The priority_field "{priority_field}" was not found in the search result fields: {search_fields}',
                    },
                    "status": 400,
                }

            # Validate that field_mappings keys exist in search results
            for sr_field in field_mappings.keys():
                if sr_field not in search_fields:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'The search result field "{sr_field}" in field_mappings was not found in the search result fields: {search_fields}',
                        },
                        "status": 400,
                    }

            # Counters
            entities_matched = []
            priority_distribution = {}

            # only proceed if we have entities
            if len(data_records) > 0:

                for entity_record in data_records:

                    entity_object = entity_record.get("object", "")
                    entity_matched = False
                    entity_resolved_priority = None

                    # Try each search result row
                    for row in search_rows:

                        if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):

                            # Resolve priority from the search result row
                            raw_priority = row.get(priority_field, "")
                            resolved = resolve_lookup_priority(raw_priority, priority_mappings)

                            if resolved is None:
                                # Could not resolve priority for this row, skip
                                continue

                            # If entity already matched with a lower priority, upgrade
                            if entity_resolved_priority is None:
                                entity_resolved_priority = resolved
                            else:
                                if PRIORITY_DICT.get(resolved, 0) > PRIORITY_DICT.get(entity_resolved_priority, 0):
                                    entity_resolved_priority = resolved

                            entity_matched = True

                    if entity_matched and entity_resolved_priority:
                        entities_matched.append({
                            "object": entity_object,
                            "resolved_priority": entity_resolved_priority,
                        })

                        # Update priority distribution
                        priority_distribution[entity_resolved_priority] = priority_distribution.get(entity_resolved_priority, 0) + 1

            # get run_time
            run_time = round((time.time() - main_start), 3)

            # create result summary
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
                "priority_distribution": priority_distribution,
                "field_mappings": field_mappings,
                "priority_field": priority_field,
                "priority_mappings": priority_mappings,
                "match_mode": match_mode,
                "result_summary": result_summary,
            }

            logger.info(
                f'priority search simulation has terminated, tenant_id="{tenant_id}", '
                f'matched={len(entities_matched)}/{len(data_records)}, run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}

    # Apply priority
    def post_priority_policies_apply(self, request_info, **kwargs):
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
                "describe": "This endpoint applies priority policies, it requires a POST call with the following information:",
                "resource_desc": "Immediately apply and update priority policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_priority_policies/write/priority_policies_apply\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component identifier, valid values are: dsm/dhm/mhm/wlk/flx/fqm",
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

        # start
        main_start = time.time()

        #
        # KV priority policies
        #

        # priority policies KV collection
        priority_policies_collection_name = (
            f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
        )
        priority_policies_collection = service.kvstore[
            priority_policies_collection_name
        ]

        # get records
        (
            priority_policies_records,
            priority_collection_keys,
            priority_collection_dict,
        ) = get_kv_collection(
            priority_policies_collection, priority_policies_collection_name
        )

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
        # KV priority
        #

        # entities KV collection
        priority_collection_name = f"kv_trackme_{component}_priority_tenant_{tenant_id}"
        priority_collection = service.kvstore[priority_collection_name]

        # get records
        priority_records, priority_collection_keys, priority_collection_dict = (
            get_kv_collection(priority_collection, priority_collection_name)
        )

        #
        # Handle policies
        #

        # Separate policies by type: regex vs lookup vs search
        regex_policies = []
        lookup_policies = []
        search_policies = []
        for policy_record in priority_policies_records:
            policy_type = policy_record.get("priority_policy_type", "regex")
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
            lookup_policies, "priority_policy_lookup_name",
            remote_services_cache, service, request_info, tenant_id, logger
        )

        # Pre-parse lookup policy JSON fields once (outside entity loop)
        parsed_lookup_policies = []
        for policy_record in lookup_policies:
            lk_name = policy_record.get("priority_policy_lookup_name", "")
            policy_account = policy_record.get("account", "local")
            lk_rows = lookup_cache.get((policy_account, lk_name), [])
            if not lk_rows:
                continue

            field_mappings_raw = policy_record.get("priority_policy_lookup_field_mappings", "{}")
            try:
                if isinstance(field_mappings_raw, str):
                    field_mappings = json.loads(field_mappings_raw)
                else:
                    field_mappings = field_mappings_raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                continue

            priority_field = policy_record.get("priority_policy_lookup_priority_field", "")
            if not priority_field:
                continue

            priority_mappings_raw = policy_record.get("priority_policy_lookup_priority_mappings", "")
            priority_mappings = {}
            if priority_mappings_raw:
                try:
                    if isinstance(priority_mappings_raw, str):
                        priority_mappings = json.loads(priority_mappings_raw)
                    else:
                        priority_mappings = priority_mappings_raw
                except (json.JSONDecodeError, TypeError):
                    priority_mappings = {}

            match_mode = policy_record.get("priority_policy_lookup_match_mode", "exact")

            parsed_lookup_policies.append({
                "policy_record": policy_record,
                "lk_rows": lk_rows,
                "field_mappings": field_mappings,
                "priority_field": priority_field,
                "priority_mappings": priority_mappings,
                "match_mode": match_mode,
            })

        # Pre-execute search queries once per unique (account, query, earliest, latest)
        search_cache = preload_search_cache(
            search_policies, "priority_policy_search_query",
            "priority_policy_search_earliest", "priority_policy_search_latest",
            remote_services_cache, service, request_info, tenant_id, logger
        )

        # Pre-parse search policy JSON fields once (outside entity loop)
        parsed_search_policies = []
        for policy_record in search_policies:
            sq = policy_record.get("priority_policy_search_query", "")
            se = policy_record.get("priority_policy_search_earliest", "-5m")
            sl = policy_record.get("priority_policy_search_latest", "now")
            policy_account = policy_record.get("account", "local")
            cache_key = (policy_account, sq, se, sl)
            sr_rows = search_cache.get(cache_key, [])
            if not sr_rows:
                continue

            field_mappings_raw = policy_record.get("priority_policy_lookup_field_mappings", "{}")
            try:
                if isinstance(field_mappings_raw, str):
                    field_mappings = json.loads(field_mappings_raw)
                else:
                    field_mappings = field_mappings_raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                continue

            priority_field = policy_record.get("priority_policy_lookup_priority_field", "")
            if not priority_field:
                continue

            priority_mappings_raw = policy_record.get("priority_policy_lookup_priority_mappings", "")
            priority_mappings = {}
            if priority_mappings_raw:
                try:
                    if isinstance(priority_mappings_raw, str):
                        priority_mappings = json.loads(priority_mappings_raw)
                    else:
                        priority_mappings = priority_mappings_raw
                except (json.JSONDecodeError, TypeError):
                    priority_mappings = {}

            match_mode = policy_record.get("priority_policy_lookup_match_mode", "exact")

            parsed_search_policies.append({
                "policy_record": policy_record,
                "sr_rows": sr_rows,
                "field_mappings": field_mappings,
                "priority_field": priority_field,
                "priority_mappings": priority_mappings,
                "match_mode": match_mode,
            })

        # Counters and error list
        entities_updated_count = 0
        entities_failures_count = 0
        entities_deleted_count = 0
        entities_exceptions_list = []

        updated_records = []  # we will store the updated records here

        # only proceed if we have entities
        if len(data_records) > 0:

            # loop through records and apply policies
            for entity_record in data_records:

                entity_key = entity_record["_key"]
                entity_object = entity_record["object"]
                priority = None
                priority_reason = None
                policy_matched = False

                # Apply regex policies
                if len(regex_policies) > 0:
                    for policy_record in regex_policies:
                        try:
                            regex = policy_record["priority_policy_regex"]
                            value = policy_record["priority_policy_value"].lower()
                            match_field = policy_record.get("priority_policy_regex_match_field", "object")
                            target_value = str(entity_record.get(match_field, ""))

                            # For multi-value fields (e.g. DHM data_index/data_sourcetype),
                            # split on comma and match against each individual value
                            if match_field in MULTI_VALUE_FIELDS:
                                target_values = [v.strip() for v in target_value.split(",") if v.strip()]
                            else:
                                target_values = [target_value]

                            if any(re.match(regex, v) for v in target_values):
                                logger.info(
                                    f'tenant_id="{tenant_id}", object="{entity_object}", policy="{policy_record["priority_policy_id"]}" has matched this entity on field="{match_field}", regex="{regex}", value="{value}"'
                                )

                                # Check if a priority was already matched
                                if policy_matched:
                                    priority_matched_num = PRIORITY_DICT.get(
                                        priority, -1
                                    )
                                    priority_current_num = PRIORITY_DICT.get(value, -1)

                                    # Update if the new priority value is higher
                                    if priority_current_num > priority_matched_num:
                                        priority = value
                                        priority_reason = policy_record[
                                            "priority_policy_id"
                                        ]
                                else:
                                    priority = value
                                    priority_reason = policy_record[
                                        "priority_policy_id"
                                    ]
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
                            priority_field = parsed_policy["priority_field"]
                            priority_mappings = parsed_policy["priority_mappings"]
                            match_mode = parsed_policy["match_mode"]

                            # Try each lookup row for this entity
                            for row in lk_rows:
                                if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                    raw_priority = row.get(priority_field, "")
                                    resolved = resolve_lookup_priority(raw_priority, priority_mappings)
                                    if resolved is None:
                                        continue

                                    # Compare with current best priority (across all policies)
                                    if policy_matched:
                                        priority_matched_num = PRIORITY_DICT.get(priority, -1)
                                        priority_current_num = PRIORITY_DICT.get(resolved, -1)
                                        if priority_current_num > priority_matched_num:
                                            priority = resolved
                                            priority_reason = policy_record["priority_policy_id"]
                                    else:
                                        priority = resolved
                                        priority_reason = policy_record["priority_policy_id"]
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
                            priority_field = parsed_policy["priority_field"]
                            priority_mappings = parsed_policy["priority_mappings"]
                            match_mode = parsed_policy["match_mode"]

                            # Try each search result row for this entity
                            for row in sr_rows:
                                if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                    raw_priority = row.get(priority_field, "")
                                    resolved = resolve_lookup_priority(raw_priority, priority_mappings)
                                    if resolved is None:
                                        continue

                                    # Compare with current best priority (across all policies)
                                    if policy_matched:
                                        priority_matched_num = PRIORITY_DICT.get(priority, -1)
                                        priority_current_num = PRIORITY_DICT.get(resolved, -1)
                                        if priority_current_num > priority_matched_num:
                                            priority = resolved
                                            priority_reason = policy_record["priority_policy_id"]
                                    else:
                                        priority = resolved
                                        priority_reason = policy_record["priority_policy_id"]
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
                            "priority": priority,
                            "priority_reason": priority_reason,
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
                    priority_collection.data.batch_save(*chunk)
                    entities_updated_count += len(chunk)
                except Exception as e:
                    entities_failures_count += len(chunk)
                    msg = f'KVstore batch save failed with exception="{str(e)}"'
                    logger.error(msg)
                    entities_exceptions_list.append(msg)

            # for record in priority_records, if the key of the record does not exist in data_collection_keys, delete it
            for record in priority_records:
                if record["_key"] not in data_collection_keys:
                    try:
                        priority_collection.data.delete(
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
            priority_records, priority_collection_keys, priority_collection_dict = (
                get_kv_collection(priority_collection, priority_collection_name)
            )

            # immediately apply priority on the data collection
            # Use data_collection_dict for O(1) key lookups instead of nested loop over all entities
            updated_data_records = []

            for priority_record in priority_records:
                entity_key = priority_record["_key"]
                entity_record = data_collection_dict.get(entity_key)
                if not entity_record:
                    continue

                # Respect manual priority overrides: if priority_updated is set to 1,
                # the user has manually overridden the priority and we must not overwrite it
                try:
                    entity_priority_updated = int(
                        entity_record.get("priority_updated", 0)
                    )
                except (ValueError, TypeError):
                    entity_priority_updated = 0

                if entity_priority_updated == 1:
                    logger.info(
                        f'tenant_id="{tenant_id}", object="{entity_record.get("object")}", '
                        f'priority_updated is set to 1 (manual override), skipping immediate '
                        f'priority apply from policy="{priority_record.get("priority_reason", "unknown")}"'
                    )
                    continue

                # get the current priority value, we will only update the KVstore record if the final priority field has changed
                current_priority = entity_record.get("priority", None)

                # set the priority
                entity_record["priority"] = priority_record["priority"]

                # get the policy id from priority_reason field, set to unknown if not found
                priority_policy_id = priority_record.get(
                    "priority_reason", "unknown"
                )

                # compare current_priority and priority, if they are different, add the record to the updated_data_records list
                if current_priority:
                    if current_priority != priority_record["priority"]:
                        entity_record["mtime"] = time.time()
                        entity_record["priority_reason"] = (
                            f"priority_policy_id: {priority_policy_id}"
                        )
                        updated_data_records.append(entity_record)

                else:  # we have no current priority, we need to update the record
                    entity_record["mtime"] = time.time()
                    entity_record["priority_reason"] = (
                        f"priority_policy_id: {priority_policy_id}"
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
                            f'tenant_id="{tenant_id}", applied priority to {len(chunk)} entities in data collection'
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
            "kvstore_lookup_collection": f"trackme_{component}_priority_tenant_{tenant_id}",
            "priority_policies_no_records": len(priority_policies_records),
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
                "apply priority policies",
                "priority_policies",
                f"splk-{component}",
                json.dumps(req_summary, default=str),
                f'Priority policies applied for component="{component}" '
                f'(updated={entities_updated_count}, failed={entities_failures_count}, '
                f'deleted={entities_deleted_count})',
                str(update_comment),
            )
        except Exception as audit_e:
            logger.warning(
                f'function=post_priority_policies_apply, tenant_id="{tenant_id}", '
                f'step="audit", exception="{str(audit_e)}"'
            )

        # render response
        if action == "success":
            logger.info(
                f'priority apply operation has terminated, action="{action}", tenant_id="{tenant_id}", run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}

        else:
            logger.error(
                f'priority apply operation has failed, action="{action}", tenant_id="{tenant_id}", req_summary="{json.dumps(req_summary, indent=2)}"'
            )
            return {"payload": req_summary, "status": 500}
