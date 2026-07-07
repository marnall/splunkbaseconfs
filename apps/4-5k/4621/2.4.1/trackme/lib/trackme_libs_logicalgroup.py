#!/usr/bin/env python
# coding=utf-8

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
import json

# Networking and URL handling imports
import requests
from urllib.parse import urlencode
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def normalize_logical_group_members(members):
    if members is None:
        return []

    if isinstance(members, list):
        items = members
    elif isinstance(members, str):
        items = members.split(",")
    else:
        items = [members]

    normalized = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, str):
            item = item.strip()
            if item == "":
                continue
        normalized.append(item)

    return normalized


"""
Queries and processes records from a collection based on specific criteria.

:param collection: The collection object to query.
:return: Tuple containing collection records and a dictionary of records.
"""


def get_logical_groups_collection_records(collection):
    logical_groups_coll_records = []
    logical_groups_by_group_key_dict = {}
    logical_groups_by_group_name_list = []
    logical_groups_by_member_dict = {}
    logical_groups_by_member_list = []

    end = False
    skip_tracker = 0
    while not end:
        process_collection_records = collection.data.query(skip=skip_tracker)
        if process_collection_records:
            for item in process_collection_records:
                # handle logical_groups_coll_records, logical_groups_by_group_name_list, logical_groups_by_group_name_list

                object_group_members = normalize_logical_group_members(
                    item.get("object_group_members", [])
                )

                object_group_members_green = normalize_logical_group_members(
                    item.get("object_group_members_green", [])
                )

                object_group_members_red = normalize_logical_group_members(
                    item.get("object_group_members_red", [])
                )

                logical_groups_coll_records.append(item)
                logical_groups_by_group_key_dict[item.get("_key")] = {
                    "object_group_name": item.get("object_group_name"),
                    "object_group_mtime": item.get("object_group_mtime"),
                    "object_group_members": object_group_members,
                    "object_group_members_green": object_group_members_green,
                    "object_group_members_red": object_group_members_red,
                    "object_group_min_green_percent": item.get(
                        "object_group_min_green_percent", 0
                    ),
                }
                logical_groups_by_group_name_list.append(item.get("object_group_name"))

                # handle logical_groups_by_member_dict, logical_groups_by_member_list
                # object_group_members is already normalized above, reuse it
                if len(object_group_members) > 0:
                    for member in object_group_members:
                        logical_groups_by_member_dict[member] = {
                            "object_group_key": item.get("_key"),
                            "object_group_name": item.get("object_group_name"),
                        }
                        logical_groups_by_member_list.append(member)

            skip_tracker += len(process_collection_records)
        else:
            end = True

    #

    return (
        logical_groups_coll_records,
        logical_groups_by_group_key_dict,
        logical_groups_by_group_name_list,
        logical_groups_by_member_dict,
        logical_groups_by_member_list,
    )


"""
update list of green and red members for a given logical group
"""


def logical_group_update_green_red_members(
    splunkd_uri,
    session_key,
    tenant_id,
    object_name,
    object_group_key,
    object_group_members_green,
    object_group_members_red,
):
    try:
        data = {
            "tenant_id": tenant_id,
            "object_group_key": object_group_key,
            "object_group_members_green": object_group_members_green,
            "object_group_members_red": object_group_members_red,
        }

        response = requests.post(
            f"{splunkd_uri}/services/trackme/v2/splk_logical_groups/write/logical_groups_update_group_list",
            headers={
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(data),
            verify=False,
            timeout=600,
        )
        if response.status_code not in (200, 201, 204):
            error_msg = f'function logical_group_update_green_red_members object="{object_name}", logical group green/red members update API call has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
            raise Exception(error_msg)

        else:
            msg = f'function logical_group_update_green_red_member sobject="{object_name}", logical group green/red members update API call has succeeded, response.status_code="{response.status_code}", response.text="{response.text}"'
            return msg

    except Exception as e:
        error_msg = f'function logical_group_update_green_red_members object="{object_name}", logical group green/red members update API call has failed, exception="{str(e)}"'


"""
clean up a given entity from logical groups, if any
"""


def logical_group_remove_object_from_groups(
    splunkd_uri,
    session_key,
    tenant_id,
    object_name,
):
    try:
        data = {
            "tenant_id": tenant_id,
            "object_list": object_name,
        }

        response = requests.post(
            f"{splunkd_uri}/services/trackme/v2/splk_logical_groups/write/logical_groups_remove_object_from_groups",
            headers={
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(data),
            verify=False,
            timeout=600,
        )
        if response.status_code not in (200, 201, 204):
            error_msg = f'function logical_group_remove_object_from_groups object="{object_name}", update API call has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
            raise Exception(error_msg)

        else:
            msg = f'function logical_group_remove_object_from_groups sobject="{object_name}", API call has succeeded, response.status_code="{response.status_code}", response.text="{response.text}"'
            return msg

    except Exception as e:
        error_msg = f'function logical_group_remove_object_from_groups object="{object_name}", update API call has failed, exception="{str(e)}"'


def logical_group_delete_group_by_name(
    splunkd_uri,
    session_key,
    tenant_id,
    object_name,
):
    try:
        data = {
            "tenant_id": tenant_id,
            "object_group_name": object_name,
        }

        response = requests.post(
            f"{splunkd_uri}/services/trackme/v2/splk_logical_groups/write/logical_groups_del_grp",
            headers={
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(data),
            verify=False,
            timeout=600,
        )
        if response.status_code not in (200, 201, 204):
            error_msg = f'function logical_group_delete_group_by_name object="{object_name}", update API call has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
            raise Exception(error_msg)

        else:
            msg = f'function logical_group_delete_group_by_name sobject="{object_name}", API call has succeeded, response.status_code="{response.status_code}", response.text="{response.text}"'
            return msg

    except Exception as e:
        error_msg = f'function logical_group_delete_group_by_name object="{object_name}", update API call has failed, exception="{str(e)}"'
