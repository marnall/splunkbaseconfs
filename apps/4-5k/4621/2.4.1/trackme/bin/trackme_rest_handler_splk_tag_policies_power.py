#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_tag_policies.py"
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
    "trackme.rest.splk_tag_policies_power",
    "trackme_rest_api_splk_tag_policies_power.log",
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
    resolve_lookup_tags,
    validate_search_query,
    execute_search_content,
    resolve_service_for_account,
    preload_lookup_cache,
    preload_search_cache,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkTagPoliciesWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkTagPoliciesWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_tag_policies(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_tag_policies/write",
            "resource_group_desc": "Endpoints related to the management of tags (power operations)",
        }

        return {"payload": response, "status": 200}

    # Add new policy
    def post_tag_policies_add(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        component = None
        tags_policy_id = None
        tags_policy_type = "regex"
        tags_policy_value = None
        tags_policy_regex = None
        # Lookup-specific fields
        tags_policy_lookup_name = ""
        tags_policy_lookup_field_mappings = ""
        tags_policy_lookup_tags_field = ""
        tags_policy_lookup_tags_separator = ","
        tags_policy_lookup_match_mode = "exact"
        # Search-specific fields
        tags_policy_search_query = ""
        tags_policy_search_earliest = "-5m"
        tags_policy_search_latest = "now"
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
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                # value must be either: dsm,dhm,mhm,wlk,flx,fqm
                if component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "response": "The component must be either: dsm,dhm,mhm,wlk,flx,fqm",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # Get policy type (default: regex)
                tags_policy_type = resp_dict.get("tags_policy_type", "regex")
                if tags_policy_type not in ("regex", "lookup", "search"):
                    return {
                        "payload": {
                            "response": f"Invalid tags_policy_type: {tags_policy_type}, valid options are: regex, lookup, search",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    tags_policy_id = resp_dict["tags_policy_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The tags_policy_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                if tags_policy_type == "regex":
                    # Regex mode: require tags_policy_value and tags_policy_regex
                    try:
                        tags_policy_value = resp_dict["tags_policy_value"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The tags_policy_value is required for regex mode",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # if tags_policy_value is a string, turn into a list and make it lower case
                    if isinstance(tags_policy_value, str):
                        tags_policy_value = tags_policy_value.lower()
                        tags_policy_value = tags_policy_value.split(",")
                    else:
                        tags_policy_value = [x.lower() for x in tags_policy_value]

                    try:
                        tags_policy_regex = resp_dict["tags_policy_regex"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The tags_policy_regex is required for regex mode",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # verify that the regex is valid
                    try:
                        re.compile(tags_policy_regex)
                    except re.error:
                        return {
                            "payload": {
                                "response": "The tags_policy_regex is not a valid regular expression",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif tags_policy_type == "lookup":
                    # Lookup mode
                    tags_policy_value = ["from_lookup"]
                    tags_policy_regex = ""

                    # Validate lookup name
                    tags_policy_lookup_name = resp_dict.get("tags_policy_lookup_name", "")
                    if not tags_policy_lookup_name:
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_name is required for lookup mode",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate lookup name for SPL injection
                    try:
                        validate_lookup_name(tags_policy_lookup_name)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate field mappings
                    tags_policy_lookup_field_mappings = resp_dict.get("tags_policy_lookup_field_mappings", "")
                    if not tags_policy_lookup_field_mappings:
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_field_mappings is required for lookup mode",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    try:
                        if isinstance(tags_policy_lookup_field_mappings, str):
                            parsed_mappings = json.loads(tags_policy_lookup_field_mappings)
                        else:
                            parsed_mappings = tags_policy_lookup_field_mappings
                            tags_policy_lookup_field_mappings = json.dumps(parsed_mappings)
                        if not isinstance(parsed_mappings, dict) or len(parsed_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "The tags_policy_lookup_field_mappings must be a non-empty JSON object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, TypeError):
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate tags field
                    tags_policy_lookup_tags_field = resp_dict.get("tags_policy_lookup_tags_field", "")
                    if not tags_policy_lookup_tags_field:
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_tags_field is required for lookup mode",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional separator (default: comma), guard against empty string
                    tags_policy_lookup_tags_separator = resp_dict.get("tags_policy_lookup_tags_separator", ",")
                    if not tags_policy_lookup_tags_separator:
                        tags_policy_lookup_tags_separator = ","

                    # Optional match mode
                    tags_policy_lookup_match_mode = resp_dict.get("tags_policy_lookup_match_mode", "exact")
                    if tags_policy_lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_match_mode is not valid, valid options are: exact, wildcard",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif tags_policy_type == "search":
                    # Search mode: require search query, reuse lookup field mappings
                    tags_policy_value = ["from_search"]
                    tags_policy_regex = ""
                    tags_policy_lookup_name = ""

                    # Search query (required)
                    tags_policy_search_query = resp_dict.get("tags_policy_search_query", "")
                    if not tags_policy_search_query:
                        return {
                            "payload": {
                                "response": "The tags_policy_search_query is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Validate search query
                    try:
                        validate_search_query(tags_policy_search_query)
                    except ValueError as e:
                        return {
                            "payload": {
                                "response": str(e),
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Search time range (optional)
                    tags_policy_search_earliest = resp_dict.get("tags_policy_search_earliest", "-5m")
                    tags_policy_search_latest = resp_dict.get("tags_policy_search_latest", "now")

                    # Field mappings (required, same as lookup)
                    tags_policy_lookup_field_mappings = resp_dict.get("tags_policy_lookup_field_mappings", "")
                    if not tags_policy_lookup_field_mappings:
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_field_mappings is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    try:
                        if isinstance(tags_policy_lookup_field_mappings, str):
                            parsed_mappings = json.loads(tags_policy_lookup_field_mappings)
                        else:
                            parsed_mappings = tags_policy_lookup_field_mappings
                            tags_policy_lookup_field_mappings = json.dumps(parsed_mappings)
                        if not isinstance(parsed_mappings, dict) or len(parsed_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "The tags_policy_lookup_field_mappings must be a non-empty JSON object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, TypeError):
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Tags field (required)
                    tags_policy_lookup_tags_field = resp_dict.get("tags_policy_lookup_tags_field", "")
                    if not tags_policy_lookup_tags_field:
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_tags_field is required for search policies",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Optional separator (default: comma), guard against empty string
                    tags_policy_lookup_tags_separator = resp_dict.get("tags_policy_lookup_tags_separator", ",")
                    if not tags_policy_lookup_tags_separator:
                        tags_policy_lookup_tags_separator = ","

                    # Optional match mode
                    tags_policy_lookup_match_mode = resp_dict.get("tags_policy_lookup_match_mode", "exact")
                    if tags_policy_lookup_match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "The tags_policy_lookup_match_mode is not valid, valid options are: exact, wildcard",
                                "status": 400,
                            },
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new tag policy or updates a policy if it exists already, it requires a POST call with the following data:",
                "resource_desc": "Add or update a tag policy (supports regex, lookup and search modes)",
                "resource_spl_example": r"| trackme mode=post url=\"/services/trackme/v2/splk_tag_policies/write/tag_policies_add\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'tags_policy_id': 'linux_secure', 'tags_policy_type': 'regex', 'tags_policy_value': 'Linux,OS,CIM', 'tags_policy_regex': '\:linux_secure$'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, must be either: dsm,dhm,mhm,wlk,flx,fqm",
                        "tags_policy_id": "(required) ID of the tag policy",
                        "tags_policy_type": "(optional) Policy type: 'regex' (default), 'lookup' or 'search'",
                        "tags_policy_regex": "(required for regex mode) The regular expression to be used by the tags policy, special characters should be escaped.",
                        "tags_policy_value": "(required for regex mode) A comma separated list of tags",
                        "tags_policy_lookup_name": "(required for lookup mode) The name of the Splunk lookup transform",
                        "tags_policy_lookup_field_mappings": "(required for lookup/search mode) JSON object mapping lookup/search result fields to entity fields",
                        "tags_policy_lookup_tags_field": "(required for lookup/search mode) The field in the lookup/search results containing tag values",
                        "tags_policy_lookup_tags_separator": "(optional for lookup/search mode) Separator for tag values in lookup/search result field, default: comma",
                        "tags_policy_lookup_match_mode": "(optional for lookup/search mode) Match mode: 'exact' (default) or 'wildcard'",
                        "tags_policy_search_query": "(required for search mode) The SPL search query to execute",
                        "tags_policy_search_earliest": "(optional for search mode, default: -5m) The earliest time for the search",
                        "tags_policy_search_latest": "(optional for search mode, default: now) The latest time for the search",
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
            "tags_policy_id": tags_policy_id,
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
        account = resp_dict.get("account", "local") if resp_dict else "local"
        if tags_policy_type in ("lookup", "search"):
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
            if tags_policy_type == "lookup":
                try:
                    target_service.confs["transforms"][tags_policy_lookup_name]
                except Exception as e:
                    return {
                        "payload": {
                            "response": f'The lookup transform "{tags_policy_lookup_name}" was not found in Splunk',
                            "status": 400,
                        },
                        "status": 400,
                    }

        # Data collection
        collection_name = f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        try:
            record = collection.data.query(query=json.dumps(query_string))
            key = record[0].get("_key")

        except Exception as e:
            key = None

        # proceed

        # this policy exists already, it will be updated to include any missing tags from the list
        if key:
            # set an action_desc
            action_desc = "updated"

            # create a new list
            tags_new = []

            # add existing members
            for tag in record[0].get("tags_policy_value"):
                tags_new.append(tag)

            # add tags, if not in there already
            for tag in tags_policy_value:
                if tag not in tags_new:
                    tags_new.append(tag)

        else:
            # set an action_desc
            action_desc = "created"

        # proceed
        try:
            # Build the record data with all fields
            # Use merged tags_new on update (includes existing + incoming), raw tags_policy_value on create
            record_data = {
                "tags_policy_id": tags_policy_id,
                "tags_policy_type": tags_policy_type,
                "tags_policy_value": tags_new if key else tags_policy_value,
                "tags_policy_regex": tags_policy_regex,
                "tags_policy_lookup_name": tags_policy_lookup_name,
                "tags_policy_lookup_field_mappings": tags_policy_lookup_field_mappings,
                "tags_policy_lookup_tags_field": tags_policy_lookup_tags_field,
                "tags_policy_lookup_tags_separator": tags_policy_lookup_tags_separator,
                "tags_policy_lookup_match_mode": tags_policy_lookup_match_mode,
                "tags_policy_search_query": tags_policy_search_query,
                "tags_policy_search_earliest": tags_policy_search_earliest,
                "tags_policy_search_latest": tags_policy_search_latest,
                "account": account,
                "mtime": time.time(),
            }

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
                        "update tags policy",
                        str(tags_policy_id),
                        f"splk-{component}",
                        collection.data.query(query=json.dumps(query_string)),
                        "The tag policy was updated successfully",
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
                        "add tags policy",
                        str(tags_policy_id),
                        f"splk-{component}",
                        collection.data.query(query=json.dumps(query_string)),
                        "The tag policy was added successfully",
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
                "response": f'the tag policy tags_policy_id="{tags_policy_id}" was {action_desc} successfully',
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
    def post_tag_policies_del(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
        tags_policy_id_list = None
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
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                # value must be either: dsm,dhm,mhm,wlk,flx,fqm
                if component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "response": "The component must be either: dsm,dhm,mhm,wlk,flx,fqm",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    tags_policy_id_list = resp_dict["tags_policy_id_list"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The tags_policy_id_list is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # if tags_policy_id_list is a string, turn into a list
                if isinstance(tags_policy_id_list, str):
                    tags_policy_id_list = tags_policy_id_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes tag policies, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more tag policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_tag_policies/write/tag_policies_del\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'tags_policy_id': 'linux_secure,linux_sec'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, must be either: dsm,dhm,mhm,wlk,flx,fqm",
                        "tags_policy_id_list": "(required) Comma separated list of tag policies",
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
        collection_name = f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop
        for item in tags_policy_id_list:
            # Define the KV query
            query_string = {
                "tags_policy_id": item,
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
                            "delete tag policy",
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
                            "delete tag policy",
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
                        "delete tag policy",
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
    def post_tag_policies_update(self, request_info, **kwargs):
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
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                # value must be either: dsm,dhm,mhm,wlk,flx,fqm
                if component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "response": "The component must be either: dsm,dhm,mhm,wlk,flx,fqm",
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
                "resource_desc": "Update one or more tag policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_tag_policies/write/tag_policies_update\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'records_list': '<redacted_json_records>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, must be either: dsm,dhm,mhm,wlk,flx,fqm",
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
        collection_name = f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
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
                    "tags_policy_id": item.get("tags_policy_id"),
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
                    # Get the policy type
                    item_policy_type = item.get("tags_policy_type", "regex")

                    # Validate policy type
                    if item_policy_type not in ("regex", "lookup", "search"):
                        processed_count += 1
                        failures_count += 1
                        result = {
                            "action": "update",
                            "result": "failure",
                            "record": item,
                            "exception": f"Invalid tags_policy_type: {item_policy_type}, valid options are: regex, lookup, search",
                        }
                        records.append(result)
                        continue

                    tags_policy_value = item.get("tags_policy_value")

                    if item_policy_type == "regex":
                        # if tags_policy_value is a string, turn into a list and make it lower case
                        if isinstance(tags_policy_value, str):
                            tags_policy_value = tags_policy_value.lower()
                            tags_policy_value = tags_policy_value.split(",")
                        else:
                            tags_policy_value = [x.lower() for x in tags_policy_value]

                        # Validate regex is provided and valid for regex mode
                        tags_regex = item.get("tags_policy_regex", "")
                        if not tags_regex:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_regex is required for regex policies",
                            }
                            records.append(result)
                            continue
                        try:
                            re.compile(tags_regex)
                        except re.error:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_regex is not a valid regular expression",
                            }
                            records.append(result)
                            continue
                    elif item_policy_type == "lookup":
                        # Lookup mode - validate lookup fields
                        lk_name = item.get("tags_policy_lookup_name", "")
                        if not lk_name:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_name is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        try:
                            validate_lookup_name(lk_name)
                        except ValueError:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": f"Invalid lookup name: {lk_name}",
                            }
                            records.append(result)
                            continue

                        field_mappings_raw = item.get("tags_policy_lookup_field_mappings", "")
                        if not field_mappings_raw:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_field_mappings is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        if field_mappings_raw:
                            try:
                                if isinstance(field_mappings_raw, str):
                                    parsed = json.loads(field_mappings_raw)
                                else:
                                    parsed = field_mappings_raw
                                if not isinstance(parsed, dict) or len(parsed) == 0:
                                    raise ValueError("empty")
                            except (json.JSONDecodeError, TypeError, ValueError):
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "Invalid field_mappings",
                                }
                                records.append(result)
                                continue

                        tags_field = item.get("tags_policy_lookup_tags_field", "")
                        if not tags_field:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_tags_field is required for lookup policies",
                            }
                            records.append(result)
                            continue

                        tags_policy_value = item.get("tags_policy_value", ["from_lookup"])

                        # Validate match mode
                        lookup_match_mode = item.get("tags_policy_lookup_match_mode", "exact")
                        if lookup_match_mode not in ("exact", "wildcard"):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                            }
                            records.append(result)
                            continue

                    elif item_policy_type == "search":
                        # Search mode - accept "from_search" as value
                        tags_policy_value = item.get("tags_policy_value", ["from_search"])

                        # Validate search query
                        search_query = item.get("tags_policy_search_query", "")
                        if not search_query:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_search_query is required for search policies",
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
                        field_mappings_raw = item.get("tags_policy_lookup_field_mappings", "")
                        if not field_mappings_raw:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_field_mappings is required for search policies",
                            }
                            records.append(result)
                            continue

                        try:
                            parsed = json.loads(field_mappings_raw) if isinstance(field_mappings_raw, str) else field_mappings_raw
                            if not isinstance(parsed, dict) or len(parsed) == 0:
                                processed_count += 1
                                failures_count += 1
                                result = {
                                    "action": "update",
                                    "result": "failure",
                                    "record": item,
                                    "exception": "tags_policy_lookup_field_mappings must be a non-empty JSON object",
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
                                "exception": "tags_policy_lookup_field_mappings is not valid JSON",
                            }
                            records.append(result)
                            continue

                        # Tags field (required)
                        tags_field = item.get("tags_policy_lookup_tags_field", "")
                        if not tags_field:
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_tags_field is required for search policies",
                            }
                            records.append(result)
                            continue

                        # Validate match mode
                        lookup_match_mode = item.get("tags_policy_lookup_match_mode", "exact")
                        if lookup_match_mode not in ("exact", "wildcard"):
                            processed_count += 1
                            failures_count += 1
                            result = {
                                "action": "update",
                                "result": "failure",
                                "record": item,
                                "exception": "tags_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                            }
                            records.append(result)
                            continue

                    # Normalize dict values to JSON strings for consistent KVstore storage
                    _field_mappings = item.get("tags_policy_lookup_field_mappings", "")
                    if isinstance(_field_mappings, dict):
                        _field_mappings = json.dumps(_field_mappings)

                    update_data = {
                        "tags_policy_id": item.get("tags_policy_id"),
                        "tags_policy_type": item_policy_type,
                        "tags_policy_value": tags_policy_value,
                        "tags_policy_regex": item.get("tags_policy_regex", ""),
                        "tags_policy_lookup_name": item.get("tags_policy_lookup_name", ""),
                        "tags_policy_lookup_field_mappings": _field_mappings,
                        "tags_policy_lookup_tags_field": item.get("tags_policy_lookup_tags_field", ""),
                        "tags_policy_lookup_tags_separator": item.get("tags_policy_lookup_tags_separator", ",") or ",",
                        "tags_policy_lookup_match_mode": item.get("tags_policy_lookup_match_mode", "exact"),
                        "tags_policy_search_query": item.get("tags_policy_search_query", ""),
                        "tags_policy_search_earliest": item.get("tags_policy_search_earliest", "-5m"),
                        "tags_policy_search_latest": item.get("tags_policy_search_latest", "now"),
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
                            "update tag policies",
                            str(item),
                            component,
                            record,
                            "The tag policy was updated successfully",
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
                            "update tag policies",
                            str(item),
                            component,
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
                        "update tag policies",
                        str(item),
                        component,
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

    # Simulate tags
    def post_tag_policies_simulate(self, request_info, **kwargs):
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
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                # value must be either: dsm,dhm,mhm,wlk,flx,fqm
                if component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "response": "The component must be either: dsm,dhm,mhm,wlk,flx,fqm",
                            "status": 400,
                        },
                        "status": 400,
                    }

                # Get policy type (default: regex)
                tags_policy_type = resp_dict.get("tags_policy_type", "regex")
                if tags_policy_type not in ("regex", "lookup", "search"):
                    return {
                        "payload": {
                            "response": f"Invalid tags_policy_type: {tags_policy_type}, valid options are: regex, lookup, search",
                            "status": 400,
                        },
                        "status": 400,
                    }

                if tags_policy_type == "regex":
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
                        tags_list = resp_dict["tags_list"]
                    except Exception as e:
                        return {
                            "payload": {
                                "response": "The argument tags_list is required",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    # if tags_list is not a list, turn it into a list from comma separated values
                    if isinstance(tags_list, str):
                        tags_list = tags_list.split(",")

                elif tags_policy_type == "lookup":
                    # Lookup mode params
                    regex_value = None
                    tags_list = None

                    lookup_name = resp_dict.get("tags_policy_lookup_name", "")
                    if not lookup_name:
                        return {
                            "payload": {
                                "response": "The argument tags_policy_lookup_name is required for lookup mode",
                                "status": 400,
                            },
                            "status": 400,
                        }
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

                    field_mappings_raw = resp_dict.get("tags_policy_lookup_field_mappings", "")
                    if not field_mappings_raw:
                        return {
                            "payload": {
                                "response": "The argument tags_policy_lookup_field_mappings is required for lookup mode",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    try:
                        if isinstance(field_mappings_raw, str):
                            field_mappings = json.loads(field_mappings_raw)
                        else:
                            field_mappings = field_mappings_raw
                        if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "tags_policy_lookup_field_mappings must be a non-empty JSON object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, TypeError):
                        return {
                            "payload": {
                                "response": "tags_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    tags_field = resp_dict.get("tags_policy_lookup_tags_field", "")
                    if not tags_field:
                        return {
                            "payload": {
                                "response": "The argument tags_policy_lookup_tags_field is required for lookup mode",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    tags_separator = resp_dict.get("tags_policy_lookup_tags_separator", ",") or ","
                    match_mode = resp_dict.get("tags_policy_lookup_match_mode", "exact")
                    if match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "tags_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                                "status": 400,
                            },
                            "status": 400,
                        }

                elif tags_policy_type == "search":
                    # Search mode params
                    regex_value = None
                    tags_list = None

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
                    field_mappings_raw = resp_dict.get("tags_policy_lookup_field_mappings", "")
                    if not field_mappings_raw:
                        return {
                            "payload": {
                                "response": "The argument tags_policy_lookup_field_mappings is required for search mode",
                                "status": 400,
                            },
                            "status": 400,
                        }
                    try:
                        if isinstance(field_mappings_raw, str):
                            field_mappings = json.loads(field_mappings_raw)
                        else:
                            field_mappings = field_mappings_raw
                        if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                            return {
                                "payload": {
                                    "response": "tags_policy_lookup_field_mappings must be a non-empty JSON object",
                                    "status": 400,
                                },
                                "status": 400,
                            }
                    except (json.JSONDecodeError, TypeError):
                        return {
                            "payload": {
                                "response": "tags_policy_lookup_field_mappings is not valid JSON",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    # Tags field (required)
                    tags_field = resp_dict.get("tags_policy_lookup_tags_field", "")
                    if not tags_field:
                        return {
                            "payload": {
                                "response": "The argument tags_policy_lookup_tags_field is required for search mode",
                                "status": 400,
                            },
                            "status": 400,
                        }

                    tags_separator = resp_dict.get("tags_policy_lookup_tags_separator", ",") or ","
                    match_mode = resp_dict.get("tags_policy_lookup_match_mode", "exact")
                    if match_mode not in ("exact", "wildcard"):
                        return {
                            "payload": {
                                "response": "tags_policy_lookup_match_mode must be 'exact' or 'wildcard'",
                                "status": 400,
                            },
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint simulates a tags policy, it requires a POST call with the following information:",
                "resource_desc": "Simulates a tags policy (supports regex, lookup and search modes)",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_tag_policies/write/tag_policies_simulate\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'tags_policy_type': 'regex', 'regex_value': '^org_eu.*', 'tags_list': 'edr,eu,gdpr'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, must be either: dsm,dhm,mhm,wlk,flx,fqm",
                        "tags_policy_type": "(optional) Policy type: 'regex' (default), 'lookup' or 'search'",
                        "regex_value": "(required for regex mode) The regex to be used for the simulation",
                        "tags_list": "(required for regex mode) A comma separated list of tags",
                        "tags_policy_lookup_name": "(required for lookup mode) The name of the Splunk lookup transform",
                        "tags_policy_lookup_field_mappings": "(required for lookup/search mode) JSON object mapping lookup/search result fields to entity fields",
                        "tags_policy_lookup_tags_field": "(required for lookup/search mode) The field in the lookup/search results containing tag values",
                        "tags_policy_lookup_tags_separator": "(optional for lookup/search mode) Separator for tag values, default: comma",
                        "tags_policy_lookup_match_mode": "(optional for lookup/search mode) Match mode: 'exact' (default) or 'wildcard'",
                        "search_query": "(required for search mode) The SPL search query to execute",
                        "earliest": "(optional for search mode, default: -5m) The earliest time for the search",
                        "latest": "(optional for search mode, default: now) The latest time for the search",
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

        # Account for remote Splunk deployment support (resolved lazily in lookup/search branches)
        account = resp_dict.get("account", "local") if resp_dict else "local"

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
        # Handle policies
        #

        # Counters and error list
        entities_failures_count = 0
        entities_exceptions_list = []
        entities_tags_matched = []
        entities_matched = []

        if tags_policy_type == "regex":
            #
            # Regex mode simulation
            #

            tags_policies_records = [
                {
                    "tags_policy_regex": regex_value,
                    "tags_policy_value": tags_list,
                }
            ]

            # only proceed if we have entities
            if len(data_records) > 0:

                # loop through records and apply policies
                for entity_record in data_records:

                    entity_key = entity_record["_key"]
                    entity_object = entity_record["object"]

                    # apply policies
                    if len(tags_policies_records) > 0:
                        for policy_record in tags_policies_records:

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
                                regex = policy_record["tags_policy_regex"]
                                values = policy_record["tags_policy_value"]

                                # if values is a string, turn into a list and make it lower case
                                if isinstance(values, str):
                                    values = values.lower()
                                    values = values.split(",")
                                else:
                                    values = [x.lower() for x in values]

                                if re.match(regex, entity_record["object"]):
                                    logger.info(
                                        f'tenant_id="{tenant_id}", object="{entity_object}", regex has matched this entity, regex="{regex}", values="{values}"'
                                    )

                                    # append to our list
                                    if entity_object not in entities_matched:
                                        entities_matched.append(entity_object)

                                    # loop through tags
                                    for value in values:
                                        if value not in entities_tags_matched:
                                            entities_tags_matched.append(value)
                                else:
                                    logger.info(
                                        f'tenant_id="{tenant_id}", object="{entity_object}", regex has not matched this entity, regex="{regex}", values="{values}"'
                                    )

                            except Exception as e:
                                logger.error(
                                    f'context="exception", failed to apply policy, exception="{str(e)}"'
                                )

        elif tags_policy_type == "lookup":
            #
            # Lookup mode simulation
            #

            # Resolve remote account for lookup operations
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

            # Validate the lookup transform exists
            try:
                target_service.confs["transforms"][lookup_name]
            except Exception:
                return {
                    "payload": {
                        "response": f'The lookup transform "{lookup_name}" was not found in Splunk',
                        "status": 400,
                    },
                    "status": 400,
                }

            # Load lookup content
            try:
                lookup_rows = load_lookup_content(target_service, lookup_name, max_rows=50000)
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Failed to load lookup "{lookup_name}": {str(e)}',
                        "status": 500,
                    },
                    "status": 500,
                }

            # Validate tags field exists in lookup
            if lookup_rows:
                lookup_fields = collect_all_fields(lookup_rows)
                if tags_field not in lookup_fields:
                    return {
                        "payload": {
                            "response": f'Tags field "{tags_field}" not found in lookup columns: {lookup_fields}',
                            "status": 400,
                        },
                        "status": 400,
                    }

            # Iterate entities
            if len(data_records) > 0:
                for entity_record in data_records:
                    entity_object = entity_record["object"]
                    entity_tags = []

                    for row in lookup_rows:
                        try:
                            if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                raw_tags = row.get(tags_field, "")
                                resolved = resolve_lookup_tags(raw_tags, tags_separator)
                                for t in resolved:
                                    if t not in entity_tags:
                                        entity_tags.append(t)
                        except Exception as e:
                            msg = f'Failed to process lookup row for entity="{entity_object}", exception="{str(e)}"'
                            logger.error(msg)
                            if msg not in entities_exceptions_list:
                                entities_exceptions_list.append(msg)

                    if entity_tags:
                        if entity_object not in entities_matched:
                            entities_matched.append(entity_object)
                        for t in entity_tags:
                            if t not in entities_tags_matched:
                                entities_tags_matched.append(t)

        elif tags_policy_type == "search":
            #
            # Search mode simulation
            #

            # Resolve remote account for search operations
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
                        "entities_tags_matched_count": 0,
                        "entities_tags_matched": [],
                        "result_summary": "The search query returned no results.",
                    },
                    "status": 200,
                }

            # Validate that tags_field exists in search results
            search_fields = collect_all_fields(search_rows)
            if tags_field not in search_fields:
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'Tags field "{tags_field}" not found in search result fields: {search_fields}',
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

            # Iterate entities
            if len(data_records) > 0:
                for entity_record in data_records:
                    entity_object = entity_record["object"]
                    entity_tags = []

                    for row in search_rows:
                        try:
                            if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                raw_tags = row.get(tags_field, "")
                                resolved = resolve_lookup_tags(raw_tags, tags_separator)
                                for t in resolved:
                                    if t not in entity_tags:
                                        entity_tags.append(t)
                        except Exception as e:
                            msg = f'Failed to process search result row for entity="{entity_object}", exception="{str(e)}"'
                            logger.error(msg)
                            if msg not in entities_exceptions_list:
                                entities_exceptions_list.append(msg)

                    if entity_tags:
                        if entity_object not in entities_matched:
                            entities_matched.append(entity_object)
                        for t in entity_tags:
                            if t not in entities_tags_matched:
                                entities_tags_matched.append(t)

        # set action
        if entities_failures_count == 0:
            action = "success"
        else:
            action = "failure"

        # get run_time
        run_time = round((time.time() - main_start), 3)

        # create a result summary based on policy type
        if tags_policy_type == "regex":
            if len(entities_matched) > 0:
                result_summary = f"The regex has matched {len(entities_matched)} entities and {len(entities_tags_matched)} tags"
            else:
                result_summary = "The regex has not matched any entities, verify your inputs and try again."

            req_summary = {
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "entities_tags_matched_count": len(entities_tags_matched),
                "entities_tags_matched": entities_tags_matched,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
                "regex_is_valid": "true",
            }
        elif tags_policy_type == "lookup":
            if len(entities_matched) > 0:
                result_summary = f"The lookup has matched {len(entities_matched)} entities and {len(entities_tags_matched)} tags"
            else:
                result_summary = "The lookup has not matched any entities, verify your field mappings and try again."

            req_summary = {
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "entities_tags_matched_count": len(entities_tags_matched),
                "entities_tags_matched": entities_tags_matched,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
            }
        elif tags_policy_type == "search":
            if len(entities_matched) > 0:
                result_summary = f"The search query matched {len(entities_matched)} entities and {len(entities_tags_matched)} tags"
            else:
                result_summary = "The search query did not match any entities, verify your field mappings and search query."

            req_summary = {
                "search_query": search_query,
                "search_rows_count": len(search_rows),
                "kvstore_collection_entities_count": len(data_records),
                "entities_matched_count": len(entities_matched),
                "entities_matched": entities_matched,
                "entities_tags_matched_count": len(entities_tags_matched),
                "entities_tags_matched": entities_tags_matched,
                "result_summary": result_summary,
                "error_messages": entities_exceptions_list,
            }

        # render response
        if action == "success":
            logger.info(
                f'tags simulation operation has terminated, action="{action}", tenant_id="{tenant_id}", run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}

        else:
            logger.error(
                f'tags simulation operation has failed, action="{action}", tenant_id="{tenant_id}", req_summary="{json.dumps(req_summary, indent=2)}"'
            )
            return {"payload": req_summary, "status": 500}

    # Apply tags
    def post_tag_policies_apply(self, request_info, **kwargs):
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
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }
                # value must be either: dsm,dhm,mhm,wlk,flx,fqm
                if component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "response": "The component must be either: dsm,dhm,mhm,wlk,flx,fqm",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint applies tags policies, it requires a POST call with the following information:",
                "resource_desc": "Immediately apply and update tags policies",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_tag_policies/write/tag_policies_apply\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component identifier, must be either: dsm,dhm,mhm,wlk,flx,fqm",
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
        # KV tags policies
        #

        # tags policies KV collection
        tags_policies_collection_name = (
            f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
        )
        tags_policies_collection = service.kvstore[tags_policies_collection_name]

        # get records
        tags_policies_records, tags_collection_keys, tags_collection_dict = (
            get_kv_collection(tags_policies_collection, tags_policies_collection_name)
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
        # KV tags
        #

        # entities KV collection
        tags_collection_name = f"kv_trackme_{component}_tags_tenant_{tenant_id}"
        tags_collection = service.kvstore[tags_collection_name]

        # get records
        tags_records, tags_collection_keys, tags_collection_dict = get_kv_collection(
            tags_collection, tags_collection_name
        )

        #
        # Handle policies
        #

        # Separate policies by type: regex vs lookup vs search
        regex_policies = []
        lookup_policies = []
        search_policies = []
        for policy_record in tags_policies_records:
            policy_type = policy_record.get("tags_policy_type", "regex")
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
            lookup_policies, "tags_policy_lookup_name",
            remote_services_cache, service, request_info, tenant_id, logger
        )

        # Pre-parse lookup policy JSON fields once (outside entity loop)
        parsed_lookup_policies = []
        for policy_record in lookup_policies:
            lk_name = policy_record.get("tags_policy_lookup_name", "")
            policy_account = policy_record.get("account", "local")
            lk_rows = lookup_cache.get((policy_account, lk_name), [])
            if not lk_rows:
                continue

            field_mappings_raw = policy_record.get("tags_policy_lookup_field_mappings", "{}")
            try:
                if isinstance(field_mappings_raw, str):
                    field_mappings = json.loads(field_mappings_raw)
                else:
                    field_mappings = field_mappings_raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                continue

            tags_field = policy_record.get("tags_policy_lookup_tags_field", "")
            if not tags_field:
                continue

            tags_separator = policy_record.get("tags_policy_lookup_tags_separator", ",") or ","
            match_mode = policy_record.get("tags_policy_lookup_match_mode", "exact")

            parsed_lookup_policies.append({
                "policy_record": policy_record,
                "lk_rows": lk_rows,
                "field_mappings": field_mappings,
                "tags_field": tags_field,
                "tags_separator": tags_separator,
                "match_mode": match_mode,
            })

        # Pre-execute search queries once per unique (account, query, earliest, latest)
        search_cache = preload_search_cache(
            search_policies, "tags_policy_search_query",
            "tags_policy_search_earliest", "tags_policy_search_latest",
            remote_services_cache, service, request_info, tenant_id, logger
        )

        # Pre-parse search policy JSON fields once (outside entity loop)
        parsed_search_policies = []
        for policy_record in search_policies:
            sq = policy_record.get("tags_policy_search_query", "")
            se = policy_record.get("tags_policy_search_earliest", "-5m")
            sl = policy_record.get("tags_policy_search_latest", "now")
            policy_account = policy_record.get("account", "local")
            cache_key = (policy_account, sq, se, sl)
            sr_rows = search_cache.get(cache_key, [])
            if not sr_rows:
                continue

            field_mappings_raw = policy_record.get("tags_policy_lookup_field_mappings", "{}")
            try:
                if isinstance(field_mappings_raw, str):
                    field_mappings = json.loads(field_mappings_raw)
                else:
                    field_mappings = field_mappings_raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(field_mappings, dict) or len(field_mappings) == 0:
                continue

            tags_field = policy_record.get("tags_policy_lookup_tags_field", "")
            if not tags_field:
                continue

            tags_separator = policy_record.get("tags_policy_lookup_tags_separator", ",") or ","
            match_mode = policy_record.get("tags_policy_lookup_match_mode", "exact")

            parsed_search_policies.append({
                "policy_record": policy_record,
                "sr_rows": sr_rows,
                "field_mappings": field_mappings,
                "tags_field": tags_field,
                "tags_separator": tags_separator,
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
                tags_auto = []
                tags_auto_policies = []

                # Apply regex policies
                if len(regex_policies) > 0:
                    for policy_record in regex_policies:
                        try:
                            # apply regex
                            regex = policy_record["tags_policy_regex"]
                            values = policy_record["tags_policy_value"]

                            # if values is not a list, turn it into a list from comma separated values
                            if isinstance(values, str):
                                values = values.lower()
                                values = values.split(",")
                            else:
                                values = [x.lower() for x in values]

                            if re.match(regex, entity_record["object"]):
                                logger.info(
                                    f'tenant_id="{tenant_id}", object="{entity_object}", policy="{policy_record["tags_policy_id"]}" has matched this entity, regex="{regex}", values="{values}"'
                                )
                                for value in values:
                                    if value not in tags_auto:
                                        tags_auto.append(value)
                                # track the matching policy
                                policy_id = policy_record.get("tags_policy_id", "unknown")
                                if policy_id not in tags_auto_policies:
                                    tags_auto_policies.append(policy_id)
                            else:
                                logger.info(
                                    f'tenant_id="{tenant_id}", object="{entity_object}", policy="{policy_record["tags_policy_id"]}" has not matched this entity, regex="{regex}", values="{values}"'
                                )

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
                            tags_field = parsed_policy["tags_field"]
                            tags_separator = parsed_policy["tags_separator"]
                            match_mode = parsed_policy["match_mode"]

                            # Try each lookup row for this entity
                            policy_matched = False
                            for row in lk_rows:
                                if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                    raw_tags = row.get(tags_field, "")
                                    resolved = resolve_lookup_tags(raw_tags, tags_separator)
                                    for t in resolved:
                                        if t not in tags_auto:
                                            tags_auto.append(t)
                                    if resolved:
                                        policy_matched = True

                            # track the matching policy
                            if policy_matched:
                                policy_id = policy_record.get("tags_policy_id", "unknown")
                                if policy_id not in tags_auto_policies:
                                    tags_auto_policies.append(policy_id)

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
                            tags_field = parsed_policy["tags_field"]
                            tags_separator = parsed_policy["tags_separator"]
                            match_mode = parsed_policy["match_mode"]

                            # Try each search result row for this entity
                            policy_matched = False
                            for row in sr_rows:
                                if match_entity_to_lookup_row(entity_record, row, field_mappings, match_mode):
                                    raw_tags = row.get(tags_field, "")
                                    resolved = resolve_lookup_tags(raw_tags, tags_separator)
                                    for t in resolved:
                                        if t not in tags_auto:
                                            tags_auto.append(t)
                                    if resolved:
                                        policy_matched = True

                            # track the matching policy
                            if policy_matched:
                                policy_id = policy_record.get("tags_policy_id", "unknown")
                                if policy_id not in tags_auto_policies:
                                    tags_auto_policies.append(policy_id)

                        except Exception as e:
                            logger.error(
                                f'context="exception", failed to apply search policy, exception="{str(e)}"'
                            )

                # add to updated_records
                updated_records.append(
                    {
                        "_key": entity_key,
                        "object": entity_object,
                        "tags_auto": tags_auto,
                        "tags_auto_policies": tags_auto_policies,
                    }
                )

            # Update records in batches
            chunks = [
                updated_records[i : i + 500]
                for i in range(0, len(updated_records), 500)
            ]
            for chunk in chunks:
                try:
                    tags_collection.data.batch_save(*chunk)
                    entities_updated_count += len(chunk)
                except Exception as e:
                    entities_failures_count += len(chunk)
                    msg = f'KVstore batch save failed with exception="{str(e)}"'
                    logger.error(msg)
                    entities_exceptions_list.append(msg)

            # for record in tags_records, if the key of the record does not exist in data_collection_keys, delete it
            for record in tags_records:
                if record["_key"] not in data_collection_keys:
                    try:
                        tags_collection.data.delete(
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
            tags_records, tags_collection_keys, tags_collection_dict = (
                get_kv_collection(tags_collection, tags_collection_name)
            )

            # immediately apply tags on the data collection
            # Use data_collection_dict for O(1) key lookups instead of nested loop over all entities
            updated_data_records = []

            for tag_record in tags_records:
                entity_key = tag_record["_key"]
                entity_record = data_collection_dict.get(entity_key)
                if not entity_record:
                    continue

                # get the current tags value, we will only update the KVstore record if the final tags field has changed
                current_tags = entity_record.get("tags", None)

                entity_record["tags_auto"] = tag_record["tags_auto"]
                entity_record["tags_auto_policies"] = tag_record.get("tags_auto_policies", [])

                # get the value of tags_manual (if any), we will need to merge tags_auto and tags_manual into tags (lower case, dedup, sort)
                tags_manual = entity_record.get(
                    "tags_manual", None
                )  # tags_manual could be a CSV string or a list
                if tags_manual:
                    if isinstance(tags_manual, str):
                        tags_manual_list = tags_manual.split(",")
                    elif isinstance(tags_manual, list):
                        tags_manual_list = tags_manual
                    else:
                        tags_manual_list = []
                else:
                    tags_manual_list = []
                tags_auto = entity_record.get("tags_auto", [])

                # merge tags_auto and tags_manual into tags
                tags = ",".join(
                    sorted(
                        list(
                            set(
                                [
                                    x.lower()
                                    for x in tags_auto + tags_manual_list
                                    if x
                                ]
                            )
                        )
                    )
                )
                entity_record["tags"] = tags

                # compare current_tags (CSV string) and tags (CSV string), if they are different, add the record to the updated_data_records list
                if current_tags:
                    if current_tags != tags:
                        entity_record["mtime"] = time.time()
                        updated_data_records.append(entity_record)

                else:  # we have no current tags, we need to update the record
                    entity_record["mtime"] = time.time()
                    updated_data_records.append(entity_record)

            # update the KVstore with the updated_data_records
            if len(updated_data_records) > 0:

                # batch update/insert
                batch_update_collection_start = time.time()

                # process by chunk
                chunks = [
                    updated_data_records[i : i + 500]
                    for i in range(0, len(updated_data_records), 500)
                ]
                for chunk in chunks:
                    try:
                        data_collection.data.batch_save(*chunk)
                        logger.info(
                            f'tenant_id="{tenant_id}", applied tags to {len(chunk)} entities in data collection'
                        )
                    except Exception as e:
                        logger.error(f'KVstore batch failed with exception="{str(e)}"')
                        entities_failures_count += len(chunk)
                        entities_exceptions_list.append(str(e))

                # calculate len(final_records) once
                final_records_len = len(updated_data_records)

                # perf counter for the batch operation
                logger.info(
                    f'context="perf", batch KVstore update terminated, no_records="{final_records_len}", run_time="{round((time.time() - batch_update_collection_start), 3)}"'
                )

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
            "kvstore_lookup_collection": f"trackme_{component}_tags_tenant_{tenant_id}",
            "tags_policies_no_records": len(tags_policies_records),
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
                "apply tag policies",
                "tag_policies",
                f"splk-{component}",
                json.dumps(req_summary, default=str),
                f'Tag policies applied for component="{component}" '
                f'(updated={entities_updated_count}, failed={entities_failures_count}, '
                f'deleted={entities_deleted_count})',
                str(update_comment),
            )
        except Exception as audit_e:
            logger.warning(
                f'function=post_tag_policies_apply, tenant_id="{tenant_id}", '
                f'step="audit", exception="{str(audit_e)}"'
            )

        # render response
        if action == "success":
            logger.info(
                f'tags apply operation has terminated, action="{action}", tenant_id="{tenant_id}", run_time="{run_time}"'
            )
            return {"payload": req_summary, "status": 200}

        else:
            logger.error(
                f'tags apply operation has failed, action="{action}", tenant_id="{tenant_id}", req_summary="{json.dumps(req_summary, indent=2)}"'
            )
            return {"payload": req_summary, "status": 500}
